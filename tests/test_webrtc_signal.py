import asyncio
import base64
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

from custom_components.xsense.python_xsense import webrtc_signal


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


class FakeWebSocket:
    def __init__(self):
        self.closed = False
        self.messages = []

    async def send_str(self, message):
        self.messages.append(json.loads(message))


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


def test_webrtc_signal_relay_path_is_locked_to_v1_3_12_10_success_shape():
    """Protect the native relay used by the confirmed June 25 camera test."""
    source = Path(webrtc_signal.__file__).read_text(encoding="utf-8")

    assert "class XSenseWebRTCSignalSession" in source
    assert "aiortc" not in source
    assert "RTCPeerConnection" not in source
    assert "homeassistant" not in source
    assert "_send_offer" in source
    assert "make_sdp_offer_payload" in source
    assert "start_forwarding_remote_candidates" in source
    assert "_forward_remote_candidate" in source
    assert "class XSenseWebRTCSession" not in source


async def test_webrtc_signal_session_constructs_without_local_media_stack():
    session = webrtc_signal.XSenseWebRTCSignalSession(
        session=object(),
        ticket=ticket(),
        offer_sdp="v=0\r\n",
        resolution="1920x1080",
        camera_online=True,
    )

    assert session is not None


async def test_webrtc_signal_online_camera_prefers_peer_in_before_offer(monkeypatch):
    session = webrtc_signal.XSenseWebRTCSignalSession(
        session=object(),
        ticket=ticket(),
        offer_sdp="v=0\r\n",
        resolution="1920x1080",
        camera_online=True,
    )
    offer_calls = 0

    async def connect_signal():
        session._ws = FakeWebSocket()

    monkeypatch.setattr(session, "_connect_signal", connect_signal)
    start_task = asyncio.create_task(session.start())
    await asyncio.sleep(0)

    assert offer_calls == 0

    original_send_offer = session._send_offer

    async def send_offer():
        nonlocal offer_calls
        offer_calls += 1
        await original_send_offer()

    monkeypatch.setattr(session, "_send_offer", send_offer)
    await session._handle_signal_event(
        "PEER_IN", {"id": "SSC0ATEST", "role": "master"}
    )
    session._answer.set_result("v=0\r\nanswer")

    answer = await start_task

    assert offer_calls == 1
    assert answer == "v=0\r\nanswer"


async def test_webrtc_signal_online_camera_falls_back_without_peer_in(monkeypatch):
    session = webrtc_signal.XSenseWebRTCSignalSession(
        session=object(),
        ticket=ticket(),
        offer_sdp="v=0\r\n",
        resolution="1920x1080",
        camera_online=True,
    )

    async def connect_signal():
        session._ws = FakeWebSocket()

    monkeypatch.setattr(session, "_connect_signal", connect_signal)
    monkeypatch.setattr(webrtc_signal, "_ONLINE_PEER_GRACE", 0)
    start_task = asyncio.create_task(session.start())
    for _ in range(10):
        if session._offer_sent:
            break
        await asyncio.sleep(0)

    assert session._offer_sent
    assert session._offer_sent_before_peer_ready
    assert [message["messageType"] for message in session._ws.messages] == [
        "SDP_OFFER"
    ]

    session._answer.set_result("v=0\r\nanswer")
    assert await start_task == "v=0\r\nanswer"


async def test_webrtc_signal_resends_fallback_when_peer_becomes_ready(monkeypatch):
    session = webrtc_signal.XSenseWebRTCSignalSession(
        session=object(),
        ticket=ticket(),
        offer_sdp="v=0\r\n",
        resolution="1920x1080",
        camera_online=True,
    )
    session._ws = FakeWebSocket()

    await session._send_offer()
    await session._handle_signal_event(
        "PEER_IN", {"id": "SSC0ATEST", "role": "master"}
    )

    assert session._offer_attempt_count == 2
    assert not session._offer_sent_before_peer_ready
    assert [message["messageType"] for message in session._ws.messages] == [
        "SDP_OFFER",
        "SDP_OFFER",
    ]


async def test_webrtc_signal_reconnect_clears_stale_peer_and_keeps_fallback(
    monkeypatch,
):
    session = webrtc_signal.XSenseWebRTCSignalSession(
        session=object(),
        ticket=ticket(),
        offer_sdp="v=0\r\n",
        resolution="1920x1080",
        camera_online=True,
    )
    session._camera_peer_ready = True
    session._camera_peer_event.set()
    connect_calls = 0

    async def connect_signal():
        nonlocal connect_calls
        connect_calls += 1
        session._ws = FakeWebSocket()

    async def no_delay(_delay):
        return None

    monkeypatch.setattr(session, "_connect_signal", connect_signal)
    monkeypatch.setattr(webrtc_signal.asyncio, "sleep", no_delay)
    monkeypatch.setattr(webrtc_signal, "_ONLINE_PEER_GRACE", 0)

    await session._reconnect_signal()

    assert connect_calls == 1
    assert not session._camera_peer_ready
    assert not session._camera_peer_event.is_set()
    assert session._offer_sent
    assert session._offer_sent_before_peer_ready


async def test_webrtc_signal_offline_camera_waits_for_peer_in(monkeypatch):
    session = webrtc_signal.XSenseWebRTCSignalSession(
        session=object(),
        ticket=ticket(),
        offer_sdp="v=0\r\n",
        resolution="1920x1080",
        camera_online=False,
    )
    offer_calls = 0

    async def connect_signal():
        session._ws = FakeWebSocket()

    async def send_offer():
        nonlocal offer_calls
        offer_calls += 1

    async def return_answer(_future, *, timeout):
        assert timeout == webrtc_signal._ANSWER_TIMEOUT
        return "v=0\r\nanswer"

    monkeypatch.setattr(session, "_connect_signal", connect_signal)
    monkeypatch.setattr(session, "_send_offer", send_offer)
    monkeypatch.setattr(webrtc_signal.asyncio, "wait_for", return_answer)

    answer = await session.start()

    assert offer_calls == 0
    assert answer == "v=0\r\nanswer"


async def test_webrtc_signal_online_offer_is_guarded_before_websocket_send():
    send_started = asyncio.Event()
    release_send = asyncio.Event()

    class BlockingWebSocket(FakeWebSocket):
        async def send_str(self, message):
            self.messages.append(json.loads(message))
            send_started.set()
            await release_send.wait()

    session = webrtc_signal.XSenseWebRTCSignalSession(
        session=object(),
        ticket=ticket(),
        offer_sdp="v=0\r\n",
        resolution="1920x1080",
        camera_online=True,
    )
    websocket = BlockingWebSocket()
    session._ws = websocket

    first_offer = asyncio.create_task(session._send_offer())
    await send_started.wait()
    await session._send_offer()
    release_send.set()
    await first_offer

    assert session._offer_attempt_count == 1
    assert [message["messageType"] for message in websocket.messages] == ["SDP_OFFER"]


async def test_online_camera_preserves_confirmed_offer_answer_ice_order(monkeypatch):
    """Lock v1.3.12.10 peer, offer, answer, and ICE ordering."""
    websocket = FakeWebSocket()
    session = webrtc_signal.XSenseWebRTCSignalSession(
        session=object(),
        ticket=ticket(),
        offer_sdp="v=0\r\n",
        resolution="1920x1080",
        camera_online=True,
    )

    async def connect_signal():
        session._ws = websocket

    monkeypatch.setattr(session, "_connect_signal", connect_signal)
    start_task = asyncio.create_task(session.start())
    await asyncio.sleep(0)

    assert websocket.messages == []

    await session._handle_signal_event(
        "PEER_IN", {"id": "SSC0ATEST", "role": "master"}
    )

    assert [message["messageType"] for message in websocket.messages] == ["SDP_OFFER"]

    candidate = SimpleNamespace(
        candidate="candidate:1 1 udp 1 192.0.2.1 123 typ host",
        sdp_mid="0",
        sdp_m_line_index=0,
    )
    await session.add_candidate(candidate)

    assert len(session._pending_remote_candidates) == 1
    assert [message["messageType"] for message in websocket.messages] == ["SDP_OFFER"]

    answer_sdp = "v=0\r\n"
    await session._handle_signal_event(
        "SDP_ANSWER",
        {
            "senderClientId": "SSC0ATEST",
            "recipientClientId": "client123",
            "messagePayload": b64_json({"type": "answer", "sdp": answer_sdp}),
        },
    )

    assert await start_task == answer_sdp
    assert [message["messageType"] for message in websocket.messages] == [
        "SDP_OFFER",
        "ICE_CANDIDATE",
    ]


async def test_webrtc_signal_flushes_trickled_ha_candidates_after_answer():
    fake_ws = FakeWebSocket()
    session = webrtc_signal.XSenseWebRTCSignalSession(
        session=object(),
        ticket=ticket(),
        offer_sdp=(
            "v=0\r\n"
            "m=audio 9 UDP/TLS/RTP/SAVPF 0\r\n"
            "a=mid:0\r\n"
            "m=video 9 UDP/TLS/RTP/SAVPF 96\r\n"
            "a=mid:1\r\n"
        ),
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
    assert not session._answer.done()

    session._ws = fake_ws
    session._recipient_client_id = "SSC0ATEST"

    await session._send_offer()

    assert not session._answer.done()
    assert len(session._pending_remote_candidates) == 1
    assert [message["messageType"] for message in fake_ws.messages] == ["SDP_OFFER"]

    session._answer.set_result("v=0\r\nanswer")
    await session._flush_pending_remote_candidates()

    assert len(session._pending_remote_candidates) == 0
    assert [message["messageType"] for message in fake_ws.messages] == [
        "SDP_OFFER",
        "ICE_CANDIDATE",
    ]
    ice_payload = json.loads(
        base64.b64decode(fake_ws.messages[1]["messagePayload"]).decode()
    )
    assert ice_payload == {
        "sdpMid": "0",
        "sdpMLineIndex": 0,
        "candidate": "candidate:1 1 udp 1 192.0.2.1 123 typ host",
    }


async def test_webrtc_signal_queues_ha_candidates_until_answer():
    fake_ws = FakeWebSocket()
    session = webrtc_signal.XSenseWebRTCSignalSession(
        session=object(),
        ticket=ticket(),
        offer_sdp=(
            "v=0\r\n"
            "m=audio 9 UDP/TLS/RTP/SAVPF 0\r\n"
            "a=mid:0\r\n"
            "m=video 9 UDP/TLS/RTP/SAVPF 96\r\n"
            "a=mid:1\r\n"
        ),
        resolution="1920x1080",
        camera_online=True,
    )
    candidate = SimpleNamespace(
        candidate="candidate:2 1 udp 1 192.0.2.2 456 typ host",
        sdp_mid="1",
        sdp_m_line_index=1,
    )
    session._ws = fake_ws
    session._recipient_client_id = "SSC0ATEST"

    await session._send_offer()
    assert [message["messageType"] for message in fake_ws.messages] == ["SDP_OFFER"]
    assert len(session._pending_remote_candidates) == 0
    assert not session._answer.done()

    await session.add_candidate(candidate)

    assert len(session._pending_remote_candidates) == 1
    assert not session._answer.done()
    assert [message["messageType"] for message in fake_ws.messages] == ["SDP_OFFER"]

    session._answer.set_result("v=0\r\nanswer")
    await session._flush_pending_remote_candidates()

    assert len(session._pending_remote_candidates) == 0
    assert [message["messageType"] for message in fake_ws.messages] == [
        "SDP_OFFER",
        "ICE_CANDIDATE",
    ]
    ice_payload = json.loads(
        base64.b64decode(fake_ws.messages[1]["messagePayload"]).decode()
    )
    assert ice_payload == {
        "sdpMid": "1",
        "sdpMLineIndex": 1,
        "candidate": "candidate:2 1 udp 1 192.0.2.2 456 typ host",
    }
