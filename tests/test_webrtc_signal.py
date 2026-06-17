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


def test_answer_sdp_normalization_replaces_invalid_actpass_answer_setup():
    sdp = (
        "v=0\r\n"
        "m=audio 9 UDP/TLS/RTP/SAVPF 0\r\n"
        "a=setup:actpass\r\n"
        "m=video 9 UDP/TLS/RTP/SAVPF 103\r\n"
        "a=setup:passive\r\n"
    )

    normalized, context = webrtc_signal._normalize_answer_sdp(sdp)

    assert "a=setup:actpass" not in normalized
    assert normalized.count("a=setup:passive") == 2
    assert context == {"setup_actpass_replaced": 1}


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

    assert context["groups"] == ["BUNDLE 0 1"]
    assert context["setup"] == ["passive"]
    assert context["directions"] == ["sendonly"]
    assert context["ice_ufrag_count"] == 1
    assert context["ice_pwd_count"] == 1
    assert context["fingerprint_count"] == 1
    assert context["rtcp_mux_count"] == 1
    assert "secret" not in str(context)


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


async def test_online_camera_waits_for_peer_in_before_sending_offer():
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
    session._ws = FakeWs()

    assert session._ws.messages == []

    await session._handle_signal_event("PEER_IN", "SSC0ATEST")

    assert [message["messageType"] for message in session._ws.messages] == [
        "SDP_OFFER"
    ]
    assert session._offer_sent is True
    assert session._debug_context()["offer_attempt_count"] == 1


async def test_peer_out_before_answer_resets_offer_for_next_peer_in():
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
    session._ws = FakeWs()
    peer_payload = {"id": "SSC0ATEST", "name": "SSC0ATEST", "role": "master"}

    await session._handle_signal_event("PEER_IN", peer_payload)
    await session._handle_signal_event("PEER_OUT", peer_payload)
    await session._handle_signal_event("PEER_IN", peer_payload)

    assert [message["messageType"] for message in session._ws.messages] == [
        "SDP_OFFER",
        "SDP_OFFER",
    ]
    assert session._offer_sent is True
    assert session._camera_peer_ready is True
    assert session._debug_context()["offer_attempt_count"] == 2


async def test_signal_close_schedules_reconnect_before_answer(monkeypatch):
    scheduled = []
    session = webrtc_signal.XSenseWebRTCSignalSession(
        session=object(),
        ticket=ticket(),
        offer_sdp="v=0\r\n",
        resolution="1920x1080",
        camera_online=True,
    )

    class FakeTask:
        def done(self):
            return False

    def create_task(coro):
        scheduled.append(coro)
        coro.close()
        return FakeTask()

    monkeypatch.setattr(webrtc_signal.asyncio, "create_task", create_task)

    session._schedule_signal_reconnect(1006)

    assert len(scheduled) == 1
    assert session._debug_context()["signal_reconnect_count"] == 0


async def test_signal_close_skips_terminal_reconnect_codes(monkeypatch):
    scheduled = []
    session = webrtc_signal.XSenseWebRTCSignalSession(
        session=object(),
        ticket=ticket(),
        offer_sdp="v=0\r\n",
        resolution="1920x1080",
        camera_online=True,
    )

    def create_task(coro):
        scheduled.append(coro)
        coro.close()
        return object()

    monkeypatch.setattr(webrtc_signal.asyncio, "create_task", create_task)

    session._schedule_signal_reconnect(3002)
    session._schedule_signal_reconnect(3004)

    assert scheduled == []


async def test_read_loop_uses_local_websocket_when_session_ws_is_cleared():
    session = webrtc_signal.XSenseWebRTCSignalSession(
        session=object(),
        ticket=ticket(),
        offer_sdp="v=0\r\n",
        resolution="1920x1080",
        camera_online=True,
    )

    class FakeWs:
        close_code = 1000
        closed = False

        def __aiter__(self):
            return self

        async def __anext__(self):
            session._ws = None
            raise StopAsyncIteration

    session._ws = FakeWs()
    session._answer.set_result("v=0\r\nanswer")

    await session._read_loop()

    assert session._answer.result() == "v=0\r\nanswer"


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
