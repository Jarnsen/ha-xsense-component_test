package main

import (
	"context"
	"crypto/tls"
	"encoding/base64"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"

	"github.com/gorilla/websocket"
	"github.com/pion/rtcp"
	"github.com/pion/webrtc/v4"
)

const (
	defaultListenAddr = "127.0.0.1:39091"
	signalName        = "test-123"
	signalMode        = "vicoo"
	viewerType        = "a4x_sdk"
	dataChannelName   = "data-channel-of-"
	startTimeout      = 45 * time.Second
)

type server struct {
	listenAddr string
	api        *webrtc.API
	upgrader   websocket.Upgrader

	mu       sync.RWMutex
	sessions map[string]*xsenseSession
}

type startRequest struct {
	Camera cameraInfo `json:"camera"`
	Ticket ticketInfo `json:"ticket"`
	Debug  bool       `json:"debug"`
}

type cameraInfo struct {
	SerialNumber string `json:"serialNumber"`
	Resolution   string `json:"resolution"`
	Model        string `json:"model"`
}

type ticketInfo struct {
	SignalServer          string      `json:"signalServer"`
	SignalServerIPAddress string      `json:"signalServerIpAddress"`
	GroupID               string      `json:"groupId"`
	Role                  string      `json:"role"`
	ClientID              string      `json:"id"`
	TraceID               string      `json:"traceId"`
	Sign                  string      `json:"sign"`
	Time                  int64       `json:"time"`
	ExpirationTime        int64       `json:"expirationTime"`
	ICEServers            []iceServer `json:"iceServer"`
}

type iceServer struct {
	URL        string   `json:"url"`
	URLs       []string `json:"urls"`
	Username   string   `json:"username"`
	Credential string   `json:"credential"`
	Password   string   `json:"password"`
}

type startResponse struct {
	SessionID string `json:"sessionId"`
	StreamURL string `json:"streamUrl"`
}

type xsenseSession struct {
	id            string
	camera        cameraInfo
	ticket        ticketInfo
	debug         bool
	api           *webrtc.API
	peerSessionID string

	mu        sync.RWMutex
	tracks    []*webrtc.TrackLocalStaticRTP
	ready     chan struct{}
	readyOnce sync.Once
	closed    chan struct{}
}

type signalEnvelope struct {
	MessageType       string          `json:"messageType"`
	MessagePayload    json.RawMessage `json:"messagePayload"`
	RecipientClientID string          `json:"recipientClientId,omitempty"`
	SenderClientID    string          `json:"senderClientId,omitempty"`
	SessionID         string          `json:"sessionId,omitempty"`
	Mode              string          `json:"mode,omitempty"`
	ViewerType        string          `json:"viewerType,omitempty"`
	Resolution        string          `json:"resolution,omitempty"`
}

type signalPayload struct {
	Type          string `json:"type,omitempty"`
	SDP           string `json:"sdp,omitempty"`
	SDPMid        string `json:"sdpMid,omitempty"`
	SDPMLineIndex uint16 `json:"sdpMLineIndex,omitempty"`
	Candidate     string `json:"candidate,omitempty"`
}

type wsMessage struct {
	Type  string `json:"type"`
	Value string `json:"value"`
}

func main() {
	listen := flag.String("listen", defaultListenAddr, "HTTP listen address")
	flag.Parse()

	settingEngine := webrtc.SettingEngine{}
	settingEngine.SetNetworkTypes([]webrtc.NetworkType{
		webrtc.NetworkTypeUDP4,
		webrtc.NetworkTypeUDP6,
	})
	api := webrtc.NewAPI(webrtc.WithSettingEngine(settingEngine))

	s := &server{
		listenAddr: *listen,
		api:        api,
		sessions:   map[string]*xsenseSession{},
		upgrader: websocket.Upgrader{
			CheckOrigin: func(r *http.Request) bool { return true },
		},
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/api/xsense/sessions", s.handleSessions)
	mux.HandleFunc("/api/ws/", s.handleGo2RTCWebSocket)

	log.Printf("xsense bridge listening on http://%s", s.listenAddr)
	if err := http.ListenAndServe(s.listenAddr, mux); err != nil {
		log.Fatal(err)
	}
}

func (s *server) handleSessions(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var req startRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	if req.Camera.SerialNumber == "" || req.Ticket.ClientID == "" {
		http.Error(w, "missing camera serial or ticket id", http.StatusBadRequest)
		return
	}
	if req.Camera.Resolution == "" {
		req.Camera.Resolution = "1280x720"
	}

	id := newSessionID(req.Camera.SerialNumber)
	session := &xsenseSession{
		id:            id,
		camera:        req.Camera,
		ticket:        req.Ticket,
		debug:         req.Debug,
		api:           s.api,
		peerSessionID: fmt.Sprintf("Android-%s-%d", req.Ticket.ClientID, time.Now().UnixMilli()),
		ready:         make(chan struct{}),
		closed:        make(chan struct{}),
	}
	s.mu.Lock()
	s.sessions[id] = session
	s.mu.Unlock()

	session.debugf(
		"session created: camera=%s model=%s resolution=%s signal=%s ice_servers=%d",
		shortID(session.camera.SerialNumber),
		session.camera.Model,
		session.camera.Resolution,
		safeHost(session.ticket.SignalServer),
		len(session.pionICEServers()),
	)

	go func() {
		if err := session.runCameraPeer(context.Background()); err != nil {
			log.Printf("camera session %s failed: %v", id, err)
		}
	}()

	scheme := "ws"
	if r.TLS != nil {
		scheme = "wss"
	}
	streamURL := fmt.Sprintf("webrtc:%s://%s/api/ws/%s", scheme, r.Host, id)
	writeJSON(w, startResponse{SessionID: id, StreamURL: streamURL})
}

func (s *server) handleGo2RTCWebSocket(w http.ResponseWriter, r *http.Request) {
	id := strings.TrimPrefix(r.URL.Path, "/api/ws/")
	s.mu.RLock()
	session := s.sessions[id]
	s.mu.RUnlock()
	if session == nil {
		http.NotFound(w, r)
		return
	}

	conn, err := s.upgrader.Upgrade(w, r, nil)
	if err != nil {
		return
	}
	defer conn.Close()

	var offer wsMessage
	if err := conn.ReadJSON(&offer); err != nil {
		return
	}
	if offer.Type != "webrtc/offer" || offer.Value == "" {
		_ = conn.WriteJSON(wsMessage{Type: "error", Value: "expected webrtc/offer"})
		return
	}
	session.debugf("go2rtc offer received")

	if err := session.waitReady(r.Context()); err != nil {
		_ = conn.WriteJSON(wsMessage{Type: "error", Value: err.Error()})
		return
	}
	pc, err := s.api.NewPeerConnection(webrtc.Configuration{})
	if err != nil {
		_ = conn.WriteJSON(wsMessage{Type: "error", Value: err.Error()})
		return
	}
	defer pc.Close()

	session.mu.RLock()
	for _, track := range session.tracks {
		sender, err := pc.AddTrack(track)
		if err != nil {
			session.mu.RUnlock()
			_ = conn.WriteJSON(wsMessage{Type: "error", Value: err.Error()})
			return
		}
		go readRTCP(sender)
	}
	session.mu.RUnlock()

	pc.OnICECandidate(func(candidate *webrtc.ICECandidate) {
		if candidate == nil {
			return
		}
		_ = conn.WriteJSON(wsMessage{
			Type:  "webrtc/candidate",
			Value: candidate.ToJSON().Candidate,
		})
	})

	if err := pc.SetRemoteDescription(webrtc.SessionDescription{
		Type: webrtc.SDPTypeOffer,
		SDP:  offer.Value,
	}); err != nil {
		_ = conn.WriteJSON(wsMessage{Type: "error", Value: err.Error()})
		return
	}
	answer, err := pc.CreateAnswer(nil)
	if err != nil {
		_ = conn.WriteJSON(wsMessage{Type: "error", Value: err.Error()})
		return
	}
	if err := pc.SetLocalDescription(answer); err != nil {
		_ = conn.WriteJSON(wsMessage{Type: "error", Value: err.Error()})
		return
	}
	_ = conn.WriteJSON(wsMessage{Type: "webrtc/answer", Value: pc.LocalDescription().SDP})
	session.debugf("go2rtc answer sent with %d track(s)", len(session.tracks))

	for {
		var msg wsMessage
		if err := conn.ReadJSON(&msg); err != nil {
			return
		}
		if msg.Type == "webrtc/candidate" && msg.Value != "" {
			_ = pc.AddICECandidate(webrtc.ICECandidateInit{Candidate: msg.Value})
		}
	}
}

func (x *xsenseSession) runCameraPeer(ctx context.Context) error {
	if x.ticket.ExpirationTime > 0 && x.ticket.ExpirationTime < time.Now().UnixMilli() {
		return errors.New("expired WebRTC ticket")
	}
	signalConn, err := x.connectSignal()
	if err != nil {
		return err
	}
	defer signalConn.Close()
	x.debugf("signal websocket connected: host=%s ip_override=%t", safeHost(x.ticket.SignalServer), x.ticket.SignalServerIPAddress != "")

	pc, err := x.api.NewPeerConnection(webrtc.Configuration{
		ICEServers:   x.pionICEServers(),
		SDPSemantics: webrtc.SDPSemanticsUnifiedPlanWithFallback,
	})
	if err != nil {
		return err
	}
	defer pc.Close()

	localICECandidates := 0
	pc.OnICECandidate(func(candidate *webrtc.ICECandidate) {
		if candidate == nil {
			return
		}
		payload, err := x.makeCandidate(candidate)
		if err == nil {
			_ = signalConn.WriteMessage(websocket.TextMessage, payload)
			localICECandidates++
			x.debugCandidate("local ICE candidate sent", localICECandidates)
		}
	})
	pc.OnTrack(func(remote *webrtc.TrackRemote, receiver *webrtc.RTPReceiver) {
		local, err := webrtc.NewTrackLocalStaticRTP(
			remote.Codec().RTPCodecCapability,
			remote.ID(),
			remote.StreamID(),
		)
		if err != nil {
			log.Printf("camera session %s track create failed: %v", x.id, err)
			return
		}
		x.mu.Lock()
		x.tracks = append(x.tracks, local)
		x.readyOnce.Do(func() { close(x.ready) })
		x.mu.Unlock()
		x.debugf("camera track ready: kind=%s codec=%s", remote.Kind(), remote.Codec().MimeType)

		for {
			packet, _, err := remote.ReadRTP()
			if err != nil {
				return
			}
			if err := local.WriteRTP(packet); err != nil {
				return
			}
		}
	})

	dataChannel, err := pc.CreateDataChannel(dataChannelName, nil)
	if err != nil {
		return err
	}
	var startLiveOnce sync.Once
	sendStartLive := func() {
		startLiveOnce.Do(func() {
			start := map[string]any{
				"requestID":    fmt.Sprintf("cmd_%d", time.Now().Unix()),
				"connectionID": "7893feb",
				"timeStamp":    time.Now().Unix(),
				"action":       "startLive",
				"size":         mapVideoSize(x.camera.Resolution),
				"resolution":   x.camera.Resolution,
			}
			b, _ := json.Marshal(start)
			if err := dataChannel.SendText(string(b)); err != nil {
				log.Printf("camera session %s startLive send failed: %v", x.id, err)
				return
			}
			x.debugf("startLive sent: size=%s resolution=%s", start["size"], start["resolution"])
		})
	}
	dataChannel.OnOpen(func() {
		x.debugf("camera data channel open")
	})
	dataChannel.OnMessage(func(msg webrtc.DataChannelMessage) {
		if msg.IsString {
			var payload struct {
				Action string `json:"action"`
			}
			if json.Unmarshal(msg.Data, &payload) == nil && payload.Action == "dataChannelConnected" {
				x.debugf("camera dataChannelConnected received")
				sendStartLive()
			}
		}
	})

	if _, err := pc.AddTransceiverFromKind(
		webrtc.RTPCodecTypeVideo,
		webrtc.RTPTransceiverInit{Direction: webrtc.RTPTransceiverDirectionRecvonly},
	); err != nil {
		return err
	}
	if _, err := pc.AddTransceiverFromKind(
		webrtc.RTPCodecTypeAudio,
		webrtc.RTPTransceiverInit{Direction: webrtc.RTPTransceiverDirectionSendrecv},
	); err != nil {
		return err
	}

	cameraICECandidates := 0
	for {
		_, raw, err := signalConn.ReadMessage()
		if err != nil {
			return err
		}
		event, payload := parseSignalMessage(raw)
		switch event {
		case "PEER_IN":
			if !peerMatches(payload, x.camera.SerialNumber) {
				x.debugf("ignored PEER_IN for another peer")
				continue
			}
			x.debugf("matched camera PEER_IN")
			offer, err := pc.CreateOffer(nil)
			if err != nil {
				return err
			}
			if err := pc.SetLocalDescription(offer); err != nil {
				return err
			}
			msg, err := x.makeOffer(pc.LocalDescription().SDP)
			if err != nil {
				return err
			}
			if err := signalConn.WriteMessage(websocket.TextMessage, msg); err != nil {
				return err
			}
			x.debugf("SDP offer sent to camera")
		case "SDP_ANSWER":
			sdp, err := answerSDP(payload, x.ticket, x.camera.SerialNumber)
			if err != nil {
				x.debugf("ignored SDP answer: %v", err)
				continue
			}
			if err := pc.SetRemoteDescription(webrtc.SessionDescription{
				Type: webrtc.SDPTypeAnswer,
				SDP:  sdp,
			}); err != nil {
				return err
			}
			x.debugf("SDP answer applied")
		case "ICE_CANDIDATE":
			candidate, err := remoteCandidate(payload)
			if err == nil {
				_ = pc.AddICECandidate(candidate)
				cameraICECandidates++
				x.debugCandidate("camera ICE candidate applied", cameraICECandidates)
			}
		case "PEER_OUT":
			if peerMatches(payload, x.camera.SerialNumber) {
				return errors.New("camera peer left signal session")
			}
		}
	}
}

func (x *xsenseSession) waitReady(ctx context.Context) error {
	timer := time.NewTimer(startTimeout)
	defer timer.Stop()
	select {
	case <-x.ready:
		return nil
	case <-timer.C:
		return errors.New("camera tracks not ready")
	case <-ctx.Done():
		return ctx.Err()
	}
}

func (x *xsenseSession) connectSignal() (*websocket.Conn, error) {
	rawURL := x.ticket.signalURL()
	u, err := url.Parse(rawURL)
	if err != nil {
		return nil, err
	}
	hostHeader := u.Host
	dialURL := rawURL
	if x.ticket.SignalServerIPAddress != "" {
		u.Host = x.ticket.SignalServerIPAddress
		dialURL = u.String()
	}
	dialer := websocket.Dialer{
		TLSClientConfig: &tls.Config{ServerName: strings.Split(hostHeader, ":")[0]},
	}
	headers := http.Header{}
	if x.ticket.SignalServerIPAddress != "" {
		headers.Set("Host", hostHeader)
	}
	conn, _, err := dialer.Dial(dialURL, headers)
	return conn, err
}

func (t ticketInfo) signalURL() string {
	base := t.SignalServer
	if !strings.Contains(base, "://") {
		base = "wss://" + base
	}
	base = strings.Replace(base, "https://", "wss://", 1)
	base = strings.Replace(base, "http://", "ws://", 1)
	return fmt.Sprintf(
		"%s/%s/%s/%s?traceId=%s&time=%d&sign=%s&name=%s",
		strings.TrimRight(base, "/"),
		url.PathEscape(t.GroupID),
		url.PathEscape(t.Role),
		url.PathEscape(t.ClientID),
		url.QueryEscape(t.TraceID),
		t.Time,
		url.QueryEscape(t.Sign),
		signalName,
	)
}

func (x *xsenseSession) makeOffer(sdp string) ([]byte, error) {
	payload, err := json.Marshal(signalPayload{Type: "offer", SDP: sdp})
	if err != nil {
		return nil, err
	}
	envelope := signalEnvelope{
		MessageType:       "SDP_OFFER",
		MessagePayload:    json.RawMessage(strJSON(base64.StdEncoding.EncodeToString(payload))),
		Mode:              signalMode,
		RecipientClientID: x.camera.SerialNumber,
		SenderClientID:    x.ticket.ClientID,
		SessionID:         x.sessionID(),
		ViewerType:        viewerType,
		Resolution:        x.camera.Resolution,
	}
	return json.Marshal(envelope)
}

func (x *xsenseSession) makeCandidate(candidate *webrtc.ICECandidate) ([]byte, error) {
	init := candidate.ToJSON()
	mid := ""
	if init.SDPMid != nil {
		mid = *init.SDPMid
	}
	index := uint16(0)
	if init.SDPMLineIndex != nil {
		index = *init.SDPMLineIndex
	}
	payload, err := json.Marshal(signalPayload{
		SDPMid:        mid,
		SDPMLineIndex: index,
		Candidate:     init.Candidate,
	})
	if err != nil {
		return nil, err
	}
	envelope := signalEnvelope{
		MessageType:       "ICE_CANDIDATE",
		MessagePayload:    json.RawMessage(strJSON(base64.StdEncoding.EncodeToString(payload))),
		RecipientClientID: x.camera.SerialNumber,
		SenderClientID:    x.ticket.ClientID,
		SessionID:         x.sessionID(),
	}
	return json.Marshal(envelope)
}

func (x *xsenseSession) sessionID() string {
	return x.peerSessionID
}

func (x *xsenseSession) pionICEServers() []webrtc.ICEServer {
	servers := make([]webrtc.ICEServer, 0, len(x.ticket.ICEServers))
	for _, item := range x.ticket.ICEServers {
		urls := item.URLs
		if item.URL != "" {
			urls = append(urls, item.URL)
		}
		if len(urls) == 0 {
			continue
		}
		credential := item.Credential
		if credential == "" {
			credential = item.Password
		}
		servers = append(servers, webrtc.ICEServer{
			URLs:       urls,
			Username:   item.Username,
			Credential: credential,
		})
	}
	return servers
}

func parseSignalMessage(raw []byte) (string, json.RawMessage) {
	var envelope map[string]json.RawMessage
	if err := json.Unmarshal(raw, &envelope); err != nil {
		return "", raw
	}
	for _, key := range []string{"messageType", "event", "type", "method"} {
		if value, ok := envelope[key]; ok {
			var event string
			if json.Unmarshal(value, &event) == nil {
				if event == "SDP_ANSWER" {
					return event, raw
				}
				payload := raw
				for _, payloadKey := range []string{"messagePayload", "payload", "data", "message", "body", "value"} {
					if found, ok := envelope[payloadKey]; ok {
						payload = decodePayload(found)
						break
					}
				}
				return event, payload
			}
		}
	}
	return "", raw
}

func decodePayload(raw json.RawMessage) json.RawMessage {
	var text string
	if json.Unmarshal(raw, &text) != nil {
		return raw
	}
	if decoded, err := base64.StdEncoding.DecodeString(text); err == nil {
		return decoded
	}
	return raw
}

func answerSDP(raw json.RawMessage, ticket ticketInfo, serialNumber string) (string, error) {
	var envelope signalEnvelope
	if err := json.Unmarshal(raw, &envelope); err != nil {
		return "", err
	}
	if envelope.SenderClientID != "" && envelope.SenderClientID != serialNumber {
		return "", errors.New("sender mismatch")
	}
	if envelope.RecipientClientID != "" && envelope.RecipientClientID != ticket.ClientID {
		return "", errors.New("recipient mismatch")
	}
	var encoded string
	if err := json.Unmarshal(envelope.MessagePayload, &encoded); err != nil {
		return "", err
	}
	decoded, err := base64.StdEncoding.DecodeString(encoded)
	if err != nil {
		return "", err
	}
	var payload signalPayload
	if err := json.Unmarshal(decoded, &payload); err != nil {
		return "", err
	}
	if payload.SDP == "" {
		return "", errors.New("missing SDP")
	}
	return payload.SDP, nil
}

func remoteCandidate(raw json.RawMessage) (webrtc.ICECandidateInit, error) {
	var payload signalPayload
	if err := json.Unmarshal(raw, &payload); err != nil {
		return webrtc.ICECandidateInit{}, err
	}
	if payload.Candidate == "" {
		return webrtc.ICECandidateInit{}, errors.New("missing candidate")
	}
	mid := payload.SDPMid
	index := payload.SDPMLineIndex
	return webrtc.ICECandidateInit{
		Candidate:     payload.Candidate,
		SDPMid:        &mid,
		SDPMLineIndex: &index,
	}, nil
}

func peerMatches(raw json.RawMessage, serial string) bool {
	var text string
	if json.Unmarshal(raw, &text) == nil {
		return strings.TrimSpace(text) == serial
	}
	if strings.Trim(strings.TrimSpace(string(raw)), `"`) == serial {
		return true
	}
	var payload map[string]any
	if json.Unmarshal(raw, &payload) != nil {
		return false
	}
	for _, key := range []string{"clientId", "serialNumber", "deviceSn", "deviceSN", "sn", "id", "name"} {
		if fmt.Sprint(payload[key]) == serial {
			return true
		}
	}
	return false
}

func mapVideoSize(resolution string) string {
	switch resolution {
	case "640x360", "640x480", "960x720", "1280x720", "1280x960":
		return "1280x720"
	case "1920x1080", "2048x1440", "2048x1536", "2304x1296", "2560x1440", "3840x2160", "7680x4320":
		return "1920x1080"
	default:
		return "1280x720"
	}
}

func (x *xsenseSession) debugf(format string, args ...any) {
	if !x.debug {
		return
	}
	log.Printf("camera session %s: %s", x.id, fmt.Sprintf(format, args...))
}

func (x *xsenseSession) debugCandidate(message string, count int) {
	if count == 1 || count == 5 || count%10 == 0 {
		x.debugf("%s: count=%d", message, count)
	}
}

func safeHost(rawURL string) string {
	if rawURL == "" {
		return ""
	}
	if !strings.Contains(rawURL, "://") {
		rawURL = "wss://" + rawURL
	}
	parsed, err := url.Parse(rawURL)
	if err != nil {
		return "invalid"
	}
	return parsed.Host
}

func shortID(value string) string {
	if value == "" {
		return ""
	}
	if len(value) <= 6 {
		return value
	}
	return "..." + value[len(value)-6:]
}

func newSessionID(serial string) string {
	clean := strings.Map(func(r rune) rune {
		if r >= 'a' && r <= 'z' || r >= 'A' && r <= 'Z' || r >= '0' && r <= '9' {
			return r
		}
		return '-'
	}, serial)
	return fmt.Sprintf("%s-%d", clean, time.Now().UnixNano())
}

func writeJSON(w http.ResponseWriter, value any) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(value)
}

func readRTCP(sender *webrtc.RTPSender) {
	buf := make([]byte, 1500)
	for {
		if _, _, err := sender.Read(buf); err != nil {
			return
		}
	}
}

func strJSON(value string) string {
	b, _ := json.Marshal(value)
	return string(b)
}

func sendPLI(pc *webrtc.PeerConnection, ssrc uint32) {
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()
	for range ticker.C {
		_ = pc.WriteRTCP([]rtcp.Packet{&rtcp.PictureLossIndication{MediaSSRC: ssrc}})
	}
}
