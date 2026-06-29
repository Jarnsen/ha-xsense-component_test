package main

import (
	"bufio"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net"
	"os"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/pion/ice/v4"
	"github.com/pion/interceptor"
	"github.com/pion/rtp"
	"github.com/pion/rtp/codecs"
	"github.com/pion/stun/v3"
	"github.com/pion/webrtc/v4"
)

var stdoutMu sync.Mutex

func main() {
	interactive := flag.Bool("interactive", false, "keep the peer connection alive, read a remote SDP answer from stdin, and report received media")
	timeout := flag.Duration("timeout", 20*time.Second, "interactive receive timeout")
	flag.Parse()

	mediaEngine := &webrtc.MediaEngine{}
	if err := mediaEngine.RegisterDefaultCodecs(); err != nil {
		log.Fatal(err)
	}
	interceptors := &interceptor.Registry{}
	if err := webrtc.RegisterDefaultInterceptors(mediaEngine, interceptors); err != nil {
		log.Fatal(err)
	}

	settingEngine := webrtc.SettingEngine{}
	applyICESettingsFromEnv(&settingEngine)
	settingEngine.SetICEBindingRequestHandler(func(m *stun.Message, local, remote ice.Candidate, pair *ice.CandidatePair) bool {
		_ = writeJSON(map[string]any{
			"type":              "iceBindingRequest",
			"hasICEControlling": m.Contains(stun.AttrICEControlling),
			"hasICEControlled":  m.Contains(stun.AttrICEControlled),
			"hasUseCandidate":   m.Contains(stun.AttrUseCandidate),
			"local":             candidateSummary(local),
			"remote":            candidateSummary(remote),
			"pair":              pairSummary(pair),
		})
		return true
	})

	api := webrtc.NewAPI(
		webrtc.WithMediaEngine(mediaEngine),
		webrtc.WithInterceptorRegistry(interceptors),
		webrtc.WithSettingEngine(settingEngine),
	)
	peer, err := api.NewPeerConnection(webrtc.Configuration{
		ICEServers:         iceServersFromEnv(),
		BundlePolicy:       webrtc.BundlePolicyMaxBundle,
		ICETransportPolicy: iceTransportPolicyFromEnv(),
	})
	if err != nil {
		log.Fatal(err)
	}
	defer peer.Close()

	audioDirection := webrtc.RTPTransceiverDirectionRecvonly
	replayDataChannelOnly := os.Getenv("XSENSE_RECORDINGS_REPLAY_DATACHANNEL_ONLY") == "1"
	dummyAudioSendrecv := os.Getenv("XSENSE_RECORDINGS_DUMMY_AUDIO_SENDRECV") == "1"
	if os.Getenv("XSENSE_RECORDINGS_AUDIO_SENDRECV") == "1" {
		audioDirection = webrtc.RTPTransceiverDirectionSendrecv
	}
	if replayDataChannelOnly {
		// Some replay paths use data channels instead of RTP media tracks.
	} else if dummyAudioSendrecv {
		audioTrack, err := webrtc.NewTrackLocalStaticRTP(webrtc.RTPCodecCapability{
			MimeType:  webrtc.MimeTypePCMU,
			ClockRate: 8000,
		}, "audio", "xsense-recordings")
		if err != nil {
			log.Fatal(err)
		}
		sender, err := peer.AddTrack(audioTrack)
		if err != nil {
			log.Fatal(err)
		}
		go func() {
			rtcpBuf := make([]byte, 1500)
			for {
				if _, _, err := sender.Read(rtcpBuf); err != nil {
					return
				}
			}
		}()
		go sendSilentPCMU(audioTrack)
	} else {
		if _, err = peer.AddTransceiverFromKind(webrtc.RTPCodecTypeAudio, webrtc.RTPTransceiverInit{
			Direction: audioDirection,
		}); err != nil {
			log.Fatal(err)
		}
	}

	if !replayDataChannelOnly {
		if _, err = peer.AddTransceiverFromKind(webrtc.RTPCodecTypeVideo, webrtc.RTPTransceiverInit{
			Direction: webrtc.RTPTransceiverDirectionRecvonly,
		}); err != nil {
			log.Fatal(err)
		}
	}

	var dataChannel *webrtc.DataChannel
	if replayDataChannelOnly || os.Getenv("XSENSE_RECORDINGS_DATA_CHANNEL") == "1" {
		maxRetransmits := uint16(5)
		label := strings.TrimSpace(os.Getenv("XSENSE_RECORDINGS_DATA_CHANNEL_LABEL"))
		if label == "" {
			label = "data-channel-of-"
		}
		dataChannel, err = peer.CreateDataChannel(label, &webrtc.DataChannelInit{
			MaxRetransmits: &maxRetransmits,
		})
		if err != nil {
			log.Fatal(err)
		}
	}

	trickleCandidates := os.Getenv("XSENSE_RECORDINGS_TRICKLE_CANDIDATES") == "1"
	if trickleCandidates {
		peer.OnICECandidate(func(candidate *webrtc.ICECandidate) {
			if candidate == nil {
				_ = writeJSON(map[string]any{
					"type": "localCandidateEnd",
				})
				return
			}
			candidateInit := candidate.ToJSON()
			_ = writeJSON(map[string]any{
				"type":      "localCandidate",
				"candidate": candidateInit.Candidate,
				"sdpMid":    candidateInit.SDPMid,
				"mLine":     candidateInit.SDPMLineIndex,
			})
		})
	}

	offer, err := peer.CreateOffer(nil)
	if err != nil {
		log.Fatal(err)
	}

	gatherComplete := webrtc.GatheringCompletePromise(peer)
	if err = peer.SetLocalDescription(offer); err != nil {
		log.Fatal(err)
	}
	if !trickleCandidates {
		<-gatherComplete
	}

	localDescription := peer.LocalDescription()
	if localDescription == nil {
		log.Fatal("local description was not created")
	}
	outputSDP := localDescription.SDP
	if os.Getenv("XSENSE_RECORDINGS_CHROME_SDP") == "1" {
		outputSDP = chromeLikeSDP(outputSDP)
	}
	if *interactive {
		runInteractive(peer, dataChannel, outputSDP, *timeout)
		return
	}
	fmt.Print(outputSDP)
}

type iceServerConfig struct {
	URLs       any    `json:"urls"`
	Username   string `json:"username"`
	Credential string `json:"credential"`
}

func iceServersFromEnv() []webrtc.ICEServer {
	raw := os.Getenv("XSENSE_RECORDINGS_ICE_SERVERS")
	if raw == "" {
		return nil
	}
	var configs []iceServerConfig
	if err := json.Unmarshal([]byte(raw), &configs); err != nil {
		log.Fatalf("invalid XSENSE_RECORDINGS_ICE_SERVERS: %v", err)
	}
	servers := make([]webrtc.ICEServer, 0, len(configs))
	for _, config := range configs {
		urls := iceURLs(config.URLs)
		if len(urls) == 0 {
			continue
		}
		servers = append(servers, webrtc.ICEServer{
			URLs:       urls,
			Username:   config.Username,
			Credential: config.Credential,
		})
	}
	return servers
}

func iceURLs(value any) []string {
	switch typed := value.(type) {
	case string:
		return []string{typed}
	case []any:
		urls := make([]string, 0, len(typed))
		for _, item := range typed {
			if text, ok := item.(string); ok {
				urls = append(urls, text)
			}
		}
		return urls
	default:
		return nil
	}
}

func iceTransportPolicyFromEnv() webrtc.ICETransportPolicy {
	switch strings.ToLower(strings.TrimSpace(os.Getenv("XSENSE_RECORDINGS_ICE_TRANSPORT_POLICY"))) {
	case "relay":
		return webrtc.ICETransportPolicyRelay
	default:
		return webrtc.ICETransportPolicyAll
	}
}

func applyICESettingsFromEnv(settingEngine *webrtc.SettingEngine) {
	if os.Getenv("XSENSE_RECORDINGS_ICE_LITE") == "1" {
		settingEngine.SetLite(true)
	}
	if os.Getenv("XSENSE_RECORDINGS_DISABLE_MDNS") == "1" {
		settingEngine.SetICEMulticastDNSMode(ice.MulticastDNSModeDisabled)
	}
	if networkTypes := iceNetworkTypesFromEnv(); len(networkTypes) > 0 {
		settingEngine.SetNetworkTypes(networkTypes)
	}
	if minPort, maxPort, ok := udpPortRangeFromEnv(); ok {
		if err := settingEngine.SetEphemeralUDPPortRange(minPort, maxPort); err != nil {
			log.Fatalf("invalid XSENSE_RECORDINGS_UDP_PORT_RANGE: %v", err)
		}
	}
}

func iceNetworkTypesFromEnv() []webrtc.NetworkType {
	raw := strings.TrimSpace(os.Getenv("XSENSE_RECORDINGS_ICE_NETWORK_TYPES"))
	if raw == "" {
		return nil
	}
	var networkTypes []webrtc.NetworkType
	for _, item := range strings.Split(raw, ",") {
		switch strings.ToLower(strings.TrimSpace(item)) {
		case "udp4":
			networkTypes = append(networkTypes, webrtc.NetworkTypeUDP4)
		case "udp6":
			networkTypes = append(networkTypes, webrtc.NetworkTypeUDP6)
		case "tcp4":
			networkTypes = append(networkTypes, webrtc.NetworkTypeTCP4)
		case "tcp6":
			networkTypes = append(networkTypes, webrtc.NetworkTypeTCP6)
		case "":
		default:
			log.Fatalf("invalid XSENSE_RECORDINGS_ICE_NETWORK_TYPES entry: %s", item)
		}
	}
	return networkTypes
}

func udpPortRangeFromEnv() (uint16, uint16, bool) {
	raw := strings.TrimSpace(os.Getenv("XSENSE_RECORDINGS_UDP_PORT_RANGE"))
	if raw == "" {
		return 0, 0, false
	}
	parts := strings.Split(raw, "-")
	if len(parts) != 2 {
		log.Fatalf("invalid XSENSE_RECORDINGS_UDP_PORT_RANGE: %s", raw)
	}
	minPort, err := strconv.ParseUint(strings.TrimSpace(parts[0]), 10, 16)
	if err != nil {
		log.Fatalf("invalid XSENSE_RECORDINGS_UDP_PORT_RANGE minimum: %v", err)
	}
	maxPort, err := strconv.ParseUint(strings.TrimSpace(parts[1]), 10, 16)
	if err != nil {
		log.Fatalf("invalid XSENSE_RECORDINGS_UDP_PORT_RANGE maximum: %v", err)
	}
	return uint16(minPort), uint16(maxPort), true
}

func chromeLikeSDP(input string) string {
	lines := strings.Split(strings.ReplaceAll(input, "\r\n", "\n"), "\n")
	output := make([]string, 0, len(lines)+8)
	inMedia := false
	mediaHasRTCP := false
	for _, line := range lines {
		if strings.HasPrefix(line, "o=- ") {
			parts := strings.Split(line, " ")
			if len(parts) >= 6 {
				parts[len(parts)-1] = "127.0.0.1"
				line = strings.Join(parts, " ")
			}
		}
		if strings.HasPrefix(line, "m=") {
			inMedia = true
			mediaHasRTCP = false
		}
		output = append(output, line)
		if inMedia && strings.HasPrefix(line, "c=IN IP4 ") && !mediaHasRTCP {
			output = append(output, "a=rtcp:9 IN IP4 0.0.0.0")
			mediaHasRTCP = true
		}
		if inMedia && strings.HasPrefix(line, "a=ice-pwd:") {
			output = append(output, "a=ice-options:trickle")
		}
	}
	return strings.TrimRight(strings.Join(output, "\r\n"), "\r\n") + "\r\n"
}

func candidateSummary(candidate ice.Candidate) string {
	if candidate == nil {
		return ""
	}
	return candidate.String()
}

func pairSummary(pair *ice.CandidatePair) string {
	if pair == nil {
		return ""
	}
	return pair.String()
}

func runInteractive(peer *webrtc.PeerConnection, dataChannel *webrtc.DataChannel, offer string, timeout time.Duration) {
	var packets atomic.Uint64
	var bytes atomic.Uint64
	var tracks atomic.Uint64
	var h264Samples atomic.Uint64
	var h264Bytes atomic.Uint64
	var dataMessages atomic.Uint64
	var dataBytes atomic.Uint64
	var lastMediaUnixNano atomic.Int64
	rtpForwarders := rtpForwardersFromEnv()
	h264File := h264FileFromEnv()
	if h264File != nil {
		defer h264File.Close()
	}
	var iceState atomic.Value
	var connectionState atomic.Value
	iceState.Store("")
	connectionState.Store("")

	peer.OnTrack(func(track *webrtc.TrackRemote, _ *webrtc.RTPReceiver) {
		tracks.Add(1)
		codec := track.Codec()
		_ = writeJSON(map[string]any{
			"type":        "track",
			"kind":        track.Kind().String(),
			"mimeType":    codec.MimeType,
			"payloadType": codec.PayloadType,
			"clockRate":   codec.ClockRate,
			"ssrc":        uint32(track.SSRC()),
		})
		forwarder := rtpForwarders[track.Kind()]
		var h264Depacketizer codecs.H264Packet
		firstPacket := true
		for {
			packet, _, err := track.ReadRTP()
			if err != nil {
				return
			}
			if firstPacket {
				firstPacket = false
				_ = writeJSON(map[string]any{
					"type":        "firstRTP",
					"kind":        track.Kind().String(),
					"payloadType": packet.PayloadType,
					"sequence":    packet.SequenceNumber,
					"timestamp":   packet.Timestamp,
					"ssrc":        packet.SSRC,
				})
			}
			if forwarder != nil {
				if raw, err := packet.Marshal(); err == nil {
					_, _ = forwarder.Write(raw)
				}
			}
			if h264File != nil && strings.EqualFold(codec.MimeType, webrtc.MimeTypeH264) {
				if sample, err := h264Depacketizer.Unmarshal(packet.Payload); err == nil && len(sample) > 0 {
					_, _ = h264File.Write(sample)
					h264Samples.Add(1)
					h264Bytes.Add(uint64(len(sample)))
				}
			}
			packets.Add(1)
			bytes.Add(uint64(packet.MarshalSize()))
			lastMediaUnixNano.Store(time.Now().UnixNano())
		}
	})
	peer.OnICEConnectionStateChange(func(state webrtc.ICEConnectionState) {
		iceState.Store(state.String())
		writeEvent("iceState", state.String())
	})
	peer.OnConnectionStateChange(func(state webrtc.PeerConnectionState) {
		connectionState.Store(state.String())
		writeEvent("connectionState", state.String())
	})
	if dataChannel != nil {
		dataChannel.OnOpen(func() {
			writeEvent("dataChannelState", "open")
			if payload := strings.TrimSpace(os.Getenv("XSENSE_RECORDINGS_DATA_CHANNEL_START_PAYLOAD")); payload != "" {
				_ = dataChannel.SendText(payload)
			}
		})
		dataChannel.OnMessage(func(message webrtc.DataChannelMessage) {
			dataMessages.Add(1)
			dataBytes.Add(uint64(len(message.Data)))
			lastMediaUnixNano.Store(time.Now().UnixNano())
			if !message.IsString {
				return
			}
			var payload struct {
				Type string `json:"type"`
				Msg  string `json:"msg"`
			}
			if err := json.Unmarshal(message.Data, &payload); err != nil {
				return
			}
			switch payload.Type {
			case "codec":
				_ = dataChannel.SendText(`{"type":"start","msg":"fmp4"}`)
			case "recv":
				_ = dataChannel.SendText(`{"type":"complete","msg":""}`)
			}
		})
	}

	if err := writeJSON(map[string]any{
		"type":       "offer",
		"sdp":        offer,
		"candidates": candidateLines(offer),
	}); err != nil {
		log.Fatal(err)
	}

	answer, scanner := readAnswer()
	answerType := webrtc.SDPTypeAnswer
	if os.Getenv("XSENSE_RECORDINGS_REMOTE_SDP_TYPE") == "pranswer" {
		answerType = webrtc.SDPTypePranswer
	}
	if err := peer.SetRemoteDescription(webrtc.SessionDescription{
		Type: answerType,
		SDP:  answer,
	}); err != nil {
		log.Fatal(err)
	}
	go readCandidates(peer, scanner)

	deadline := time.After(timeout)
	ticker := time.NewTicker(200 * time.Millisecond)
	defer ticker.Stop()
	for {
		select {
		case <-deadline:
			writeResult(peer, tracks.Load(), packets.Load(), bytes.Load(), h264Samples.Load(), h264Bytes.Load(), dataMessages.Load(), dataBytes.Load(), iceState.Load().(string), connectionState.Load().(string))
			return
		case <-ticker.C:
			lastMedia := lastMediaUnixNano.Load()
			if lastMedia > 0 && time.Since(time.Unix(0, lastMedia)) > 2*time.Second {
				writeResult(peer, tracks.Load(), packets.Load(), bytes.Load(), h264Samples.Load(), h264Bytes.Load(), dataMessages.Load(), dataBytes.Load(), iceState.Load().(string), connectionState.Load().(string))
				return
			}
		}
	}
}

func rtpForwardersFromEnv() map[webrtc.RTPCodecType]net.Conn {
	forwarders := map[webrtc.RTPCodecType]net.Conn{}
	addForwarder := func(kind webrtc.RTPCodecType, envName string) {
		port := strings.TrimSpace(os.Getenv(envName))
		if port == "" {
			return
		}
		conn, err := net.Dial("udp", "127.0.0.1:"+port)
		if err != nil {
			log.Fatalf("failed to open RTP forwarder %s=%s: %v", envName, port, err)
		}
		forwarders[kind] = conn
	}
	addForwarder(webrtc.RTPCodecTypeVideo, "XSENSE_RECORDINGS_VIDEO_RTP_PORT")
	addForwarder(webrtc.RTPCodecTypeAudio, "XSENSE_RECORDINGS_AUDIO_RTP_PORT")
	return forwarders
}

func h264FileFromEnv() *os.File {
	path := strings.TrimSpace(os.Getenv("XSENSE_RECORDINGS_H264_OUTPUT"))
	if path == "" {
		return nil
	}
	file, err := os.Create(path)
	if err != nil {
		log.Fatalf("failed to open XSENSE_RECORDINGS_H264_OUTPUT=%s: %v", path, err)
	}
	return file
}

func writeEvent(eventType string, state string) {
	if err := writeJSON(map[string]any{
		"type":  eventType,
		"state": state,
	}); err != nil {
		log.Fatal(err)
	}
}

type stdinCommand struct {
	Type          string  `json:"type"`
	SDP           string  `json:"sdp"`
	Candidate     string  `json:"candidate"`
	SDPMid        string  `json:"sdpMid"`
	SDPMLineIndex *uint16 `json:"sdpMLineIndex"`
}

func readAnswer() (string, *bufio.Scanner) {
	scanner := bufio.NewScanner(os.Stdin)
	if !scanner.Scan() {
		if err := scanner.Err(); err != nil {
			log.Fatal(err)
		}
		log.Fatal("missing remote SDP answer")
	}
	line := scanner.Text()
	var command stdinCommand
	if err := json.Unmarshal([]byte(line), &command); err == nil && command.Type == "answer" {
		return command.SDP, scanner
	}
	var builder strings.Builder
	builder.WriteString(line)
	builder.WriteString("\n")
	for scanner.Scan() {
		builder.WriteString(scanner.Text())
		builder.WriteString("\n")
	}
	return builder.String(), scanner
}

func readCandidates(peer *webrtc.PeerConnection, scanner *bufio.Scanner) {
	for scanner.Scan() {
		var command stdinCommand
		if err := json.Unmarshal([]byte(scanner.Text()), &command); err != nil {
			continue
		}
		if command.Type != "candidate" {
			continue
		}
		candidate := strings.TrimSpace(command.Candidate)
		candidate = strings.TrimPrefix(candidate, "a=")
		sdpMid := command.SDPMid
		if sdpMid == "" {
			sdpMid = strings.TrimSpace(os.Getenv("XSENSE_RECORDINGS_REMOTE_CANDIDATE_MID"))
		}
		if sdpMid == "" {
			sdpMid = "0"
		}
		sdpMLineIndex := uint16(0)
		if command.SDPMLineIndex != nil {
			sdpMLineIndex = *command.SDPMLineIndex
		}
		init := webrtc.ICECandidateInit{
			Candidate:     candidate,
			SDPMid:        &sdpMid,
			SDPMLineIndex: &sdpMLineIndex,
		}
		if candidate == "" {
			init = webrtc.ICECandidateInit{
				SDPMid:        &sdpMid,
				SDPMLineIndex: &sdpMLineIndex,
			}
		}
		if err := peer.AddICECandidate(init); err != nil {
			_ = writeJSON(map[string]any{
				"type":      "candidateAddError",
				"candidate": candidate,
				"sdpMid":    sdpMid,
				"mLine":     sdpMLineIndex,
				"error":     err.Error(),
			})
			continue
		}
		_ = writeJSON(map[string]any{
			"type":      "candidateAdded",
			"candidate": candidate,
			"sdpMid":    sdpMid,
			"mLine":     sdpMLineIndex,
			"iceStats":  iceStats(peer),
		})
	}
}

func writeResult(peer *webrtc.PeerConnection, tracks uint64, packets uint64, bytes uint64, h264Samples uint64, h264Bytes uint64, dataMessages uint64, dataBytes uint64, iceState string, connectionState string) {
	if err := writeJSON(map[string]any{
		"type":            "result",
		"tracks":          tracks,
		"packets":         packets,
		"bytes":           bytes,
		"h264Samples":     h264Samples,
		"h264Bytes":       h264Bytes,
		"dataMessages":    dataMessages,
		"dataBytes":       dataBytes,
		"iceState":        iceState,
		"connectionState": connectionState,
		"iceStats":        iceStats(peer),
	}); err != nil {
		log.Fatal(err)
	}
}

func iceStats(peer *webrtc.PeerConnection) []map[string]any {
	report := peer.GetStats()
	rows := []map[string]any{}
	for id, stat := range report {
		switch typed := stat.(type) {
		case webrtc.TransportStats:
			rows = append(rows, map[string]any{
				"type":                    "transport",
				"id":                      id,
				"iceRole":                 typed.ICERole.String(),
				"iceState":                typed.ICEState.String(),
				"selectedCandidatePairId": typed.SelectedCandidatePairID,
				"packetsSent":             typed.PacketsSent,
				"packetsReceived":         typed.PacketsReceived,
				"bytesSent":               typed.BytesSent,
				"bytesReceived":           typed.BytesReceived,
			})
		case webrtc.ICECandidatePairStats:
			rows = append(rows, map[string]any{
				"type":              "candidate-pair",
				"id":                id,
				"state":             string(typed.State),
				"nominated":         typed.Nominated,
				"localCandidateId":  typed.LocalCandidateID,
				"remoteCandidateId": typed.RemoteCandidateID,
				"requestsSent":      typed.RequestsSent,
				"responsesReceived": typed.ResponsesReceived,
				"requestsReceived":  typed.RequestsReceived,
				"responsesSent":     typed.ResponsesSent,
				"bytesSent":         typed.BytesSent,
				"bytesReceived":     typed.BytesReceived,
			})
		}
	}
	return rows
}

func writeJSON(value any) error {
	stdoutMu.Lock()
	defer stdoutMu.Unlock()
	writer := bufio.NewWriter(os.Stdout)
	if err := json.NewEncoder(writer).Encode(value); err != nil {
		return err
	}
	return writer.Flush()
}

func discardRTCP(sender *webrtc.RTPSender) {
	buffer := make([]byte, 1500)
	for {
		if _, _, err := sender.Read(buffer); err != nil {
			return
		}
	}
}

func sendSilentPCMU(track *webrtc.TrackLocalStaticRTP) {
	ticker := time.NewTicker(20 * time.Millisecond)
	defer ticker.Stop()
	var sequence uint16
	var timestamp uint32
	payload := make([]byte, 160)
	for index := range payload {
		payload[index] = 0xff
	}
	for range ticker.C {
		packet := &rtp.Packet{
			Header: rtp.Header{
				Version:        2,
				PayloadType:    0,
				SequenceNumber: sequence,
				Timestamp:      timestamp,
			},
			Payload: payload,
		}
		if err := track.WriteRTP(packet); err != nil {
			return
		}
		sequence++
		timestamp += 160
	}
}

func candidateLines(sdp string) []string {
	var candidates []string
	for _, line := range strings.Split(sdp, "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "a=candidate:") {
			candidates = append(candidates, line)
		}
	}
	return candidates
}
