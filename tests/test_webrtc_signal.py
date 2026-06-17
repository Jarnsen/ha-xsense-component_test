import base64
import json
import sys
import time
from types import SimpleNamespace

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


def test_signal_module_does_not_import_aiortc():
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


def test_candidate_init_payload_matches_home_assistant_model_shape():
    candidate = SimpleNamespace(
        candidate="candidate:1 1 udp 1 192.0.2.1 123 typ host",
        sdp_mid="0",
        sdp_m_line_index=0,
    )

    assert webrtc_signal._candidate_init_payload(candidate) == {
        "sdpMid": "0",
        "sdpMLineIndex": 0,
        "candidate": "candidate:1 1 udp 1 192.0.2.1 123 typ host",
    }


async def test_trickled_candidate_is_queued_until_offer_is_sent():
    class FakeWs:
        closed = False

        def __init__(self):
            self.messages = []

        async def send_str(self, message):
            self.messages.append(json.loads(message))

    session = webrtc_signal.XSenseWebRTCSignalSession(
        session=object(),
        ticket=ticket(),
        offer_sdp="v=0\r\n",
        resolution="1920x1080",
        camera_online=True,
    )
    candidate = SimpleNamespace(
        candidate="candidate:1 1 udp 1 192.0.2.1 123 typ host",
        sdp_mid="0",
        sdp_m_line_index=0,
    )

    await session.add_candidate(candidate)

    assert len(session._pending_remote_candidates) == 1

    session._ws = FakeWs()
    session._offer_sent = True
    await session._flush_pending_remote_candidates()

    assert session._pending_remote_candidates == []
    assert session._ws.messages[0]["messageType"] == "ICE_CANDIDATE"
    assert session._sent_candidate_count == 1


async def test_debug_context_handles_cancelled_answer_future():
    session = webrtc_signal.XSenseWebRTCSignalSession(
        session=object(),
        ticket=ticket(),
        offer_sdp="v=0\r\n",
        resolution="1920x1080",
        camera_online=True,
    )
    session._answer.cancel()

    context = session._debug_context()

    assert context["sdp_answer_received"] is False


def test_payload_debug_handles_mixed_key_types():
    assert webrtc_signal._payload_debug({1: "a", "b": "c"}) == "dict_keys=['1', 'b']"


async def test_signal_event_debug_throttles_repeated_peer_events():
    session = webrtc_signal.XSenseWebRTCSignalSession(
        session=object(),
        ticket=ticket(),
        offer_sdp="v=0\r\n",
        resolution="1920x1080",
        camera_online=True,
    )

    session._signal_event_counts["PEER_IN"] = 1
    assert session._should_log_signal_event("PEER_IN") is True

    session._signal_event_counts["PEER_IN"] = 4
    assert session._should_log_signal_event("PEER_IN") is False

    session._signal_event_counts["PEER_IN"] = 10
    assert session._should_log_signal_event("PEER_IN") is True

    assert session._should_log_signal_event("SDP_ANSWER") is True


async def test_remote_ice_candidate_is_queued_until_answer_is_sent():
    forwarded = []
    session = webrtc_signal.XSenseWebRTCSignalSession(
        session=object(),
        ticket=ticket(),
        offer_sdp="v=0\r\n",
        resolution="1920x1080",
        camera_online=True,
        remote_candidate_callback=forwarded.append,
    )
    payload = {
        "candidate": "candidate:1 1 udp 1 192.0.2.10 123 typ host",
        "sdpMid": "0",
        "sdpMLineIndex": 0,
    }

    await session._handle_signal_event("ICE_CANDIDATE", payload)

    assert forwarded == []
    assert session._pending_client_candidates == [payload]

    session.start_forwarding_remote_candidates()

    assert forwarded == [payload]
    assert session._pending_client_candidates == []


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
