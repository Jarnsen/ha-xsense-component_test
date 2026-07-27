import base64
import json
import sys
import time
from pathlib import Path

from custom_components.xsense import webrtc_signal


def ticket(**overrides):
    data = {
        "signalServer": "wss://signal.example",
        "groupId": "group123",
        "role": "viewer",
        "id": "client123",
        "traceId": "trace123",
        "sign": "signed",
        "time": 123456,
        "expirationTime": int(time.time() * 1000) + 60000,
        "signalServerIpAddress": "192.0.2.10",
        "iceServer": [{"url": "turn:example"}],
    }
    data.update(overrides)
    return webrtc_signal.XSenseWebRTCTicket.from_api("SSC0ATEST", data)


def b64_json(data):
    return base64.b64encode(json.dumps(data, separators=(",", ":")).encode()).decode()


def test_signal_module_does_not_require_local_aiortc_import():
    assert "aiortc" not in sys.modules


def test_sdp_offer_payload_strips_candidates_and_keeps_resolution():
    sdp = (
        "v=0\r\n"
        "m=audio 9 UDP/TLS/RTP/SAVPF 0\r\n"
        "a=mid:0\r\n"
        "a=candidate:1 1 udp 1 192.0.2.1 123 typ host\r\n"
        "a=end-of-candidates\r\n"
    )

    payload = json.loads(
        webrtc_signal.make_sdp_offer_payload(
            offer_sdp=sdp,
            ticket=ticket(),
            recipient_client_id="SSC0ATEST",
            session_id="session123",
            resolution="1920x1080",
        )
    )
    offer = json.loads(base64.b64decode(payload["messagePayload"]).decode())

    assert payload["messageType"] == "SDP_OFFER"
    assert payload["resolution"] == "1920x1080"
    assert "a=candidate:" not in offer["sdp"]
    assert "a=end-of-candidates" not in offer["sdp"]


def test_start_live_data_channel_command_matches_apk_shape():
    payload = json.loads(
        webrtc_signal.make_start_live_data_channel_command_payload(
            "1920x1080", request_id="req-1", timestamp=123
        )
    )

    assert payload == {
        "requestID": "req-1",
        "connectionID": "7893feb",
        "timeStamp": 123,
        "action": "startLive",
        "size": "1920x1080",
        "resolution": "1920x1080",
    }


def test_sd_video_list_data_channel_command_matches_apk_shape():
    payload = json.loads(
        webrtc_signal.make_sd_video_list_command_payload(
            1782049304,
            1782049314,
            request_id="request-id",
            timestamp=1782049300,
        )
    )

    assert payload == {
        "requestID": "request-id",
        "connectionID": "7893feb",
        "timeStamp": 1782049300,
        "action": "getSdVideoList",
        "parameters": {"startTime": 1782049304, "stopTime": 1782049314},
    }


def test_local_sdp_candidates_keep_ha_complete_offer_candidates():
    sdp = (
        "v=0\r\n"
        "m=audio 9 UDP/TLS/RTP/SAVPF 0\r\n"
        "a=mid:0\r\n"
        "a=candidate:1 1 udp 1 192.0.2.1 123 typ host\r\n"
        "a=candidate:2 1 tcp 1 192.0.2.1 9 typ host tcptype active\r\n"
        "m=video 9 UDP/TLS/RTP/SAVPF 99\r\n"
        "a=mid:1\r\n"
        "a=candidate:3 1 udp 1 192.0.2.2 456 typ relay\r\n"
    )

    assert webrtc_signal._local_sdp_candidates(sdp) == [
        {
            "sdpMid": "0",
            "sdpMLineIndex": 0,
            "candidate": "candidate:1 1 udp 1 192.0.2.1 123 typ host",
        },
        {
            "sdpMid": "1",
            "sdpMLineIndex": 1,
            "candidate": "candidate:3 1 udp 1 192.0.2.2 456 typ relay",
        },
    ]


def test_sdp_debug_includes_browser_rejection_shape_without_raw_values():
    sdp = (
        "v=0\r\n"
        "a=group:BUNDLE 0 1\r\n"
        "a=fingerprint:sha-256 AA:BB:CC\r\n"
        "m=audio 9 UDP/TLS/RTP/SAVPF 0\r\n"
        "a=mid:0\r\n"
        "a=setup:passive\r\n"
        "a=sendonly\r\n"
        "a=ice-ufrag:test\r\n"
        "a=ice-pwd:secret\r\n"
        "a=rtcp-mux\r\n"
    )

    context = webrtc_signal._sdp_debug(sdp)

    assert context["media"] == ["audio 9 UDP/TLS/RTP/SAVPF 0"]
    assert context["mids"] == ["0"]
    assert context["directions"] == {"0": "sendonly"}
    assert context["fingerprints"] == ["sha-256"]
    assert context["candidate_lines"] == 0
    assert "secret" not in str(context)


def test_payload_debug_handles_mixed_key_types():
    assert webrtc_signal._payload_debug({1: "a", "b": "c"}) == "dict_keys=['1', 'b']"


def test_parse_owned_sdp_answer_from_signal_envelope():
    answer_sdp = "v=0\r\nm=video 9 UDP/TLS/RTP/SAVPF 99\r\n"
    raw = json.dumps(
        {
            "messageType": "SDP_ANSWER",
            "senderClientId": "SSC0ATEST",
            "recipientClientId": "client123",
            "messagePayload": b64_json({"type": "answer", "sdp": answer_sdp}),
        }
    )

    event, payload = webrtc_signal.parse_signal_message(raw)

    assert event == "SDP_ANSWER"
    assert webrtc_signal._owned_answer_sdp(payload, ticket()) == answer_sdp


def test_webrtc_bridge_path_is_locked_to_known_success_shape():
    source = Path(webrtc_signal.__file__).read_text(encoding="utf-8")

    assert "class XSenseWebRTCSession" in source
    assert "self._ha_pc = RTCPeerConnection()" in source
    assert "self._camera_pc: RTCPeerConnection | None = None" in source
    assert "createDataChannel(SIGNAL_DATA_CHANNEL)" in source
    assert "make_start_live_data_channel_message" in source
    assert "_send_start_live_if_ready" in source
    assert "_mark_first_frame_received" in source
    assert "_first_frame_received" in source
    assert "_send_offer" in source
    assert "make_sdp_offer_payload" in source
    assert "XSenseWebRTCSignalSession" not in source


def test_webrtc_bridge_fails_cleanly_without_ha_media_stack():
    try:
        webrtc_signal.XSenseWebRTCSession(
            session=object(),
            ticket=ticket(),
            offer_sdp="v=0\r\n",
            resolution="1920x1080",
            send_message=lambda message: None,
            on_close=lambda session_id: None,
            camera_online=True,
            refresh_ticket=lambda: ticket(),
        )
    except RuntimeError as err:
        assert str(err) == "Home Assistant WebRTC media stack is not available"
    else:
        assert webrtc_signal.RTCPeerConnection is not None
