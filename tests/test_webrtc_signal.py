from collections import Counter
from contextlib import suppress
import asyncio
import aiohttp
import base64
import json

from webrtc_models import RTCIceCandidateInit

from custom_components.xsense import webrtc_signal
from custom_components.xsense.webrtc_signal import (
    SIGNAL_DATA_CHANNEL,
    XSenseWebRTCTicket,
    make_change_transceiver_offer_command,
    make_data_channel_answer_command,
    make_ice_candidate_payload,
    make_sdp_offer_payload,
    make_start_live_data_channel_message,
    parse_signal_message,
)


def ticket(**overrides):
    data = {
        "signalServer": "https://signal.example",
        "groupId": "group",
        "role": "viewer",
        "id": "client123",
        "traceId": "trace",
        "sign": "sig",
        "time": 123456,
        "expirationTime": 4_102_444_800_000,
        "signalPingInterval": 15,
        "iceServer": [
            {"url": "turn:turn.example", "username": "user", "credential": "secret"}
        ],
    }
    data.update(overrides)
    return XSenseWebRTCTicket.from_api("SSC0A123", data)


def test_ticket_connect_details_match_apk(monkeypatch):
    monkeypatch.setattr(webrtc_signal.time, "time", lambda: 100.123)

    signal_ticket = ticket(
        signalServer="https://signal.example:443", signalServerIpAddress="203.0.113.10"
    )

    assert signal_ticket.session_id == "Android-client123-100123"
    assert signal_ticket.signal_url() == (
        "wss://signal.example:443/group/viewer/client123"
        "?traceId=trace&time=123456&sign=sig&name=test-123"
    )
    assert webrtc_signal._signal_heartbeat(signal_ticket) == 30
    assert webrtc_signal._signal_heartbeat(ticket(signalPingInterval=0)) == 30
    assert signal_ticket.signal_connect_options() == {
        "url": (
            "wss://203.0.113.10:443/group/viewer/client123"
            "?traceId=trace&time=123456&sign=sig&name=test-123"
        ),
        "headers": {"Host": "signal.example:443"},
        "server_hostname": "signal.example",
    }


def test_webrtc_ticket_accepts_unexpired_ticket_like_apk(monkeypatch):
    monkeypatch.setattr(webrtc_signal.time, "time", lambda: 100)

    valid = ticket(expirationTime=100_001)

    assert valid.is_valid is True


def test_webrtc_ticket_rejects_expired_ticket(monkeypatch):
    monkeypatch.setattr(webrtc_signal.time, "time", lambda: 100)

    expired = ticket(expirationTime=99_000)

    assert expired.is_valid is False


def test_webrtc_ticket_rejects_missing_expiration_like_apk(monkeypatch):
    monkeypatch.setattr(webrtc_signal.time, "time", lambda: 100)

    missing_expiration = ticket(expirationTime=None)

    assert missing_expiration.is_valid is False


def test_webrtc_offer_candidate_and_start_live_payloads_match_apk(monkeypatch):
    monkeypatch.setattr(webrtc_signal.time, "time", lambda: 100)
    monkeypatch.setattr(webrtc_signal.random, "randint", lambda start, end: 321)

    offer = json.loads(
        make_sdp_offer_payload(
            offer_sdp="v=0\r\n",
            ticket=ticket(),
            recipient_client_id="SSC0A123",
            session_id="Android-client123-100000",
            resolution="1280x720",
        )
    )
    assert SIGNAL_DATA_CHANNEL == "data-channel-of-"
    assert offer | {"messagePayload": "<decoded>"} == {
        "messageType": "SDP_OFFER",
        "messagePayload": "<decoded>",
        "mode": "vicoo",
        "recipientClientId": "SSC0A123",
        "senderClientId": "client123",
        "sessionId": "Android-client123-100000",
        "viewerType": "a4x_sdk",
        "resolution": "1280x720",
    }
    assert json.loads(base64.b64decode(offer["messagePayload"])) == {
        "type": "offer",
        "sdp": "v=0\r\n",
    }
    assert make_start_live_data_channel_message("2560x1440") == {
        "requestID": "100000-321",
        "connectionID": "7893feb",
        "timeStamp": 100,
        "action": "startLive",
        "size": "1920x1080",
        "resolution": "2560x1440",
    }
    assert make_start_live_data_channel_message("1280x720")["size"] == "1280x720"
    assert (
        webrtc_signal._camera_rtc_configuration(ticket()).bundlePolicy.value
        == "max-bundle"
    )


def test_sdp_offer_payload_strips_local_candidates_like_apk_create_offer():
    sdp = (
        "v=0\r\n"
        "m=video 9 UDP/TLS/RTP/SAVPF 96\r\n"
        "a=mid:0\r\n"
        "a=candidate:1 1 udp 1 192.0.2.1 123 typ host\r\n"
        "a=end-of-candidates\r\n"
    )

    offer = json.loads(
        make_sdp_offer_payload(
            offer_sdp=sdp,
            ticket=ticket(),
            recipient_client_id="SSC0A123",
            session_id="Android-client123-100000",
            resolution="1280x720",
        )
    )

    decoded = json.loads(base64.b64decode(offer["messagePayload"]))
    assert decoded["type"] == "offer"
    assert "a=candidate:" not in decoded["sdp"]
    assert "a=end-of-candidates" not in decoded["sdp"]
    assert decoded["sdp"].endswith("\r\n")


def test_parse_signal_message_accepts_apk_raw_ice_candidate_json():
    raw_candidate = {
        "sdpMid": "0",
        "sdpMLineIndex": 0,
        "candidate": "candidate:1 1 udp 1 192.0.2.1 123 typ host",
    }

    assert webrtc_signal.parse_signal_message(
        json.dumps(
            {
                "messageType": "ICE_CANDIDATE",
                "messagePayload": json.dumps(raw_candidate),
            }
        )
    ) == ("ICE_CANDIDATE", raw_candidate)


def test_parse_signal_message_accepts_apk_base64_ice_without_padding():
    raw_candidate = {
        "sdpMid": "0",
        "sdpMLineIndex": 0,
        "candidate": "candidate:1 1 udp 1 192.0.2.1 123 typ host",
    }
    encoded = base64.b64encode(json.dumps(raw_candidate).encode()).decode().rstrip("=")

    assert webrtc_signal.parse_signal_message(
        json.dumps({"messageType": "ICE_CANDIDATE", "messagePayload": encoded})
    ) == ("ICE_CANDIDATE", raw_candidate)


def test_webrtc_ice_candidate_payload_matches_apk():
    payload = json.loads(
        make_ice_candidate_payload(
            candidate="candidate:1 1 udp 1 192.0.2.1 123 typ host",
            sdp_mid="0",
            sdp_m_line_index=0,
            ticket=ticket(),
            recipient_client_id="SSC0A123",
            session_id="Android-client123-100000",
        )
    )

    assert payload | {"messagePayload": "<decoded>"} == {
        "messageType": "ICE_CANDIDATE",
        "messagePayload": "<decoded>",
        "recipientClientId": "SSC0A123",
        "senderClientId": "client123",
        "sessionId": "Android-client123-100000",
    }
    assert json.loads(base64.b64decode(payload["messagePayload"])) == {
        "sdpMid": "0",
        "sdpMLineIndex": 0,
        "candidate": "candidate:1 1 udp 1 192.0.2.1 123 typ host",
    }


def test_apk_camera_offer_sdp_matches_android_camera_offer_shape():
    sdp = """v=0
m=audio 9 UDP/TLS/RTP/SAVPF 96
a=mid:0
a=rtpmap:96 opus/48000/2
m=video 9 UDP/TLS/RTP/SAVPF 97 98 99 100 101 102
a=mid:1
a=rtpmap:97 VP8/90000
a=rtcp-fb:97 nack
a=rtpmap:98 rtx/90000
a=fmtp:98 apt=97
a=rtpmap:99 H264/90000
a=rtcp-fb:99 nack
a=fmtp:99 profile-level-id=42001f
a=rtpmap:100 rtx/90000
a=fmtp:100 apt=99
a=rtpmap:101 H264/90000
a=rtcp-fb:101 nack
a=fmtp:101 profile-level-id=42e01f
a=rtpmap:102 rtx/90000
a=fmtp:102 apt=101
a=fingerprint:sha-256 AA:BB
a=fingerprint:sha-384 CC:DD
a=fingerprint:sha-512 EE:FF
m=application 9 UDP/DTLS/SCTP webrtc-datachannel
a=mid:2
"""

    apk_sdp = webrtc_signal._apk_camera_offer_sdp(sdp)

    assert "m=video 9 UDP/TLS/RTP/SAVPF 97 98 99 100 101 102" in apk_sdp
    assert "H264" in apk_sdp
    assert "a=rtcp-fb:99 nack pli" in apk_sdp
    assert "a=rtcp-fb:101 nack pli" in apk_sdp
    assert "a=rtcp-fb:100 nack pli" not in apk_sdp
    assert (
        "a=fmtp:99 level-asymmetry-allowed=1;profile-level-id=42001f;"
        "packetization-mode=1"
    ) in apk_sdp
    assert (
        "a=fmtp:101 level-asymmetry-allowed=1;profile-level-id=42e01f;"
        "packetization-mode=1"
    ) in apk_sdp
    assert "a=fingerprint:sha-256" in apk_sdp
    assert "a=fingerprint:sha-384" not in apk_sdp
    assert "a=fingerprint:sha-512" not in apk_sdp
    assert apk_sdp.endswith("\n")


def test_local_sdp_candidates_match_apk_tcp_and_loopback_filter():
    sdp = """v=0
m=video 9 UDP/TLS/RTP/SAVPF 96
a=mid:0
a=candidate:1 1 udp 1 192.0.2.1 123 typ host
a=candidate:2 1 udp 1 127.0.0.1 456 typ host
a=candidate:5 1 tcp 1 192.0.2.1 457 typ host tcptype passive
m=audio 9 UDP/TLS/RTP/SAVPF 111
a=mid:1
a=candidate:3 1 udp 1 2001:db8::2 789 typ host
a=candidate:4 1 udp 1 ::1 790 typ host
"""

    assert webrtc_signal._local_sdp_candidates(sdp) == [
        {
            "sdpMid": "0",
            "sdpMLineIndex": 0,
            "candidate": "candidate:1 1 udp 1 192.0.2.1 123 typ host",
        },
        {
            "sdpMid": "1",
            "sdpMLineIndex": 1,
            "candidate": "candidate:3 1 udp 1 2001:db8::2 789 typ host",
        },
    ]


def test_data_channel_answer_accepts_apk_base64_without_padding():
    encoded = base64.b64encode(json.dumps({"sdp": "answer"}).encode()).decode().rstrip("=")

    assert (
        webrtc_signal._data_channel_answer_sdp({"data": {"answer": encoded}})
        == "answer"
    )


def test_change_transceiver_commands_match_apk(monkeypatch):
    monkeypatch.setattr(webrtc_signal.time, "time", lambda: 100)
    monkeypatch.setattr(webrtc_signal.random, "randint", lambda start, end: 321)

    ack = make_data_channel_answer_command("request-1", "requestChangeTransceiverOffer")
    assert ack == {
        "requestID": "request-1",
        "connectionID": "7893feb",
        "timeStamp": 100,
        "action": "requestChangeTransceiverOffer",
        "parameters": {"returnValue": "0"},
    }

    command = make_change_transceiver_offer_command("v=0\r\n")
    assert command | {"parameters": {"offer": "<decoded>"}} == {
        "requestID": "100000-321",
        "connectionID": "7893feb",
        "timeStamp": 100,
        "action": "changeTransceiverOffer",
        "parameters": {"offer": "<decoded>"},
    }
    assert json.loads(base64.b64decode(command["parameters"]["offer"]).decode()) == {
        "type": "offer",
        "sdp": "v=0\r\n",
    }


async def test_data_channel_request_change_transceiver_offer_matches_apk(monkeypatch):
    monkeypatch.setattr(webrtc_signal.time, "time", lambda: 100)
    monkeypatch.setattr(webrtc_signal.random, "randint", lambda start, end: 321)

    class Offer:
        type = "offer"
        sdp = (
            "v=0\r\n"
            "m=video 9 UDP/TLS/RTP/SAVPF 99\r\n"
            "a=mid:0\r\n"
            "a=rtpmap:99 H264/90000\r\n"
            "a=fingerprint:sha-256 AA:BB\r\n"
            "a=fingerprint:sha-384 CC:DD\r\n"
            "a=candidate:1 1 udp 1 192.0.2.1 123 typ host\r\n"
        )

    class FakePeerConnection:
        connectionState = "connected"

        def __init__(self):
            self.local_descriptions = []
            self.remote_descriptions = []

        async def createOffer(self):
            return Offer()

        async def setLocalDescription(self, offer):
            self.local_descriptions.append(offer)

        async def setRemoteDescription(self, answer):
            self.remote_descriptions.append(answer)

    class FakeDataChannel:
        readyState = "open"

        def __init__(self):
            self.messages = []

        def send(self, message):
            self.messages.append(json.loads(message))

    created_tasks = []

    def create_task(coro):
        task = asyncio.create_task(coro)
        created_tasks.append(task)
        return task

    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._closed = False
    session._camera_pc = FakePeerConnection()
    session._data_channel = FakeDataChannel()
    session._create_task = create_task
    session._debug_context = lambda **kwargs: kwargs

    session._handle_data_channel_message(
        json.dumps({"action": "requestChangeTransceiverOffer", "requestID": "req-1"})
    )
    await asyncio.gather(*created_tasks)

    assert session._data_channel.messages[0] == {
        "requestID": "req-1",
        "connectionID": "7893feb",
        "timeStamp": 100,
        "action": "requestChangeTransceiverOffer",
        "parameters": {"returnValue": "0"},
    }
    second_message = session._data_channel.messages[1]
    assert second_message | {"parameters": {"offer": "<decoded>"}} == {
        "requestID": "100000-321",
        "connectionID": "7893feb",
        "timeStamp": 100,
        "action": "changeTransceiverOffer",
        "parameters": {"offer": "<decoded>"},
    }
    decoded_offer = json.loads(
        base64.b64decode(second_message["parameters"]["offer"]).decode()
    )
    assert decoded_offer["type"] == "offer"
    assert session._camera_pc.local_descriptions[0].sdp == decoded_offer["sdp"]
    assert "a=fingerprint:sha-256" in decoded_offer["sdp"]
    assert "a=fingerprint:sha-384" not in decoded_offer["sdp"]
    assert "a=candidate:" not in decoded_offer["sdp"]

    encoded_answer = base64.b64encode(
        json.dumps({"sdp": "v=0\r\nanswer"}).encode()
    ).decode()
    created_tasks.clear()
    session._handle_data_channel_message(
        json.dumps(
            {
                "action": "changeTransceiverOffer",
                "data": {"answer": encoded_answer},
            }
        )
    )
    await asyncio.gather(*created_tasks)

    assert session._camera_pc.remote_descriptions[0].type == "answer"
    assert session._camera_pc.remote_descriptions[0].sdp == "v=0\r\nanswer"


async def test_change_transceiver_answer_ignores_nonzero_return_value_like_apk(monkeypatch):
    created_tasks = []

    def create_task(coro):
        task = asyncio.create_task(coro)
        created_tasks.append(task)
        return task

    monkeypatch.setattr(webrtc_signal.asyncio, "create_task", create_task)

    class FakePeer:
        def __init__(self):
            self.remote_descriptions = []

        async def setRemoteDescription(self, description):
            self.remote_descriptions.append(description)

    encoded_answer = base64.b64encode(
        json.dumps({"sdp": "v=0\r\nanswer"}).encode()
    ).decode()
    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._camera_pc = FakePeer()
    session._debug_context = lambda **kwargs: kwargs

    session._handle_data_channel_message(
        json.dumps(
            {
                "action": "changeTransceiverOffer",
                "returnValue": 17,
                "data": {"answer": encoded_answer},
            }
        )
    )
    await asyncio.gather(*created_tasks)

    assert session._camera_pc.remote_descriptions == []


async def test_start_camera_peer_uses_apk_receive_media_offer_shape(monkeypatch):
    class FakePeer:
        def __init__(self):
            self.transceivers = []

        def addTransceiver(self, kind, **kwargs):
            self.transceivers.append((kind, kwargs))
            return object()

        async def createOffer(self):
            class Offer:
                sdp = "v=0\r\n"
                type = "offer"

            return Offer()

        async def setLocalDescription(self, offer):
            self.localDescription = offer

    async def noop_send_offer():
        return None

    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._camera_pc = FakePeer()
    session._debug_context = lambda **kwargs: {}
    session._send_offer = noop_send_offer
    session._camera_local_description_task = None
    session._camera_offer_sdp = None

    await session._start_camera_peer()

    assert len(session._camera_pc.transceivers) == 1
    assert session._camera_pc.transceivers[0] == ("video", {"direction": "recvonly"})
    assert session._camera_offer_sdp == "v=0\r\n"
    assert session._camera_local_description_task is not None
    session._camera_local_description_task.cancel()
    with suppress(asyncio.CancelledError):
        await session._camera_local_description_task


async def test_send_offer_sends_apk_offer_then_local_ice_candidates():
    class FakeWs:
        closed = False

        def __init__(self):
            self.messages = []

        async def send_str(self, message):
            self.messages.append(json.loads(message))

    class FakeDescription:
        sdp = """v=0
m=video 9 UDP/TLS/RTP/SAVPF 96
a=mid:0
a=candidate:1 1 udp 1 192.0.2.1 123 typ host
"""

    class FakePeer:
        localDescription = FakeDescription()

    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._ws = FakeWs()
    session._camera_pc = FakePeer()
    session._closed = False
    session._camera_offer_sdp = FakeDescription.sdp
    session._camera_local_description_task = None
    session._camera_peer_ready = False
    session._camera_offer_sent = False
    session._ticket = ticket()
    session._recipient_client_id = "SSC0A123"
    session._session_id = "Android-client123-100000"
    session._resolution = "1280x720"

    await session._send_offer()

    assert [message["messageType"] for message in session._ws.messages] == [
        "SDP_OFFER",
        "ICE_CANDIDATE",
    ]
    candidate_message = session._ws.messages[1]
    assert candidate_message | {"messagePayload": "<decoded>"} == {
        "messageType": "ICE_CANDIDATE",
        "messagePayload": "<decoded>",
        "recipientClientId": "SSC0A123",
        "senderClientId": "client123",
        "sessionId": "Android-client123-100000",
    }
    assert session._camera_offer_sent is True


async def test_proxy_track_stop_wakes_pending_receiver():
    track = webrtc_signal._ProxyTrack("video")

    receive_task = webrtc_signal.asyncio.create_task(track.recv())
    await webrtc_signal.asyncio.sleep(0)

    track.stop()

    with suppress(webrtc_signal.MediaStreamError):
        await receive_task
    assert receive_task.done()


async def test_proxy_track_can_replace_camera_source_after_reconnect():
    class FakeSource:
        def __init__(self, frame):
            self.frame = frame

        async def recv(self):
            return self.frame

    track = webrtc_signal._ProxyTrack("video")

    track.set_source(FakeSource("first"))
    assert await track.recv() == "first"

    track.set_source(FakeSource("second"))
    assert await track.recv() == "second"

    track.stop()


def test_camera_peer_failed_schedules_apk_reconnect_without_ha_error(monkeypatch):
    callbacks = {}

    class FakePeer:
        connectionState = "new"

        def on(self, event):
            def decorator(callback):
                callbacks[event] = callback
                return callback

            return decorator

        def addTransceiver(self, *args, **kwargs):
            pass

        def createDataChannel(self, _label):
            return FakeDataChannel()

    class FakeDataChannel:
        readyState = "connecting"

        def on(self, event):
            def decorator(callback):
                callbacks[f"data_{event}"] = callback
                return callback

            return decorator

    scheduled = []
    sent_messages = []

    fake_peer = FakePeer()
    monkeypatch.setattr(webrtc_signal, "RTCPeerConnection", lambda _config: fake_peer)

    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._camera_pc = None
    session._ticket = ticket()
    session._session_id = None
    session._closed = False
    session._video = object()
    session._audio = object()
    session._debug_context = lambda **kwargs: kwargs
    session._schedule_peer_reconnect = lambda state: scheduled.append(state)
    session._send_ha_message = lambda message: sent_messages.append(message) or True

    session._setup_camera_peer()
    fake_peer.connectionState = "failed"
    callbacks["connectionstatechange"]()

    assert scheduled == ["failed"]
    assert sent_messages == []


def test_send_ha_message_ignores_closed_browser_socket():
    def send_message(message):
        raise ConnectionResetError("browser websocket closed")

    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._closed = False
    session._send_message = send_message

    message = webrtc_signal.WebRTCError("closed", "closed")

    assert session._send_ha_message(message) is False


def test_parse_signal_message_accepts_signal_method_value_events():
    raw = json.dumps(
        {
            "id": "message-1",
            "method": "SDP_ANSWER",
            "name": "test-123",
            "time": 123,
            "value": json.dumps(
                {
                    "messagePayload": base64.b64encode(
                        json.dumps({"type": "answer", "sdp": "v=0\r\n"}).encode()
                    ).decode(),
                    "senderClientId": "SSC0A123",
                    "recipientClientId": "client123",
                    "sessionId": "Android-client123-100000",
                }
            ),
        }
    )

    event, payload = parse_signal_message(raw)

    assert event == "SDP_ANSWER"
    assert payload["senderClientId"] == "SSC0A123"
    assert payload["recipientClientId"] == "client123"


def test_parse_signal_message_keeps_unknown_method_value_for_debug():
    raw = json.dumps(
        {
            "id": "message-2",
            "method": "cameraStatus",
            "name": "test-123",
            "time": 123,
            "value": json.dumps({"value": 1}),
        }
    )

    event, payload = parse_signal_message(raw)

    assert event == "cameraStatus"
    assert payload == json.dumps({"value": 1})


def test_parse_signal_message_preserves_answer_envelope_for_apk_validation():
    encoded = base64.b64encode(json.dumps({"sdp": "answer"}).encode()).decode()
    raw = json.dumps(
        {
            "messageType": "SDP_ANSWER",
            "messagePayload": encoded,
            "senderClientId": "SSC0A123",
            "recipientClientId": "client123",
        }
    )

    event, payload = parse_signal_message(raw)

    assert event == "SDP_ANSWER"
    assert payload["senderClientId"] == "SSC0A123"
    assert payload["recipientClientId"] == "client123"
    assert webrtc_signal._owned_answer_sdp(payload, ticket()) == "answer"


def test_apk_sdp_answer_validation_allows_missing_optional_ids():
    encoded = base64.b64encode(json.dumps({"sdp": "answer"}).encode()).decode()

    assert (
        webrtc_signal._owned_answer_sdp(
            {"messagePayload": encoded, "senderClientId": "SSC0A123"},
            ticket(),
        )
        == "answer"
    )
    assert (
        webrtc_signal._owned_answer_sdp(
            {"messagePayload": encoded, "recipientClientId": "client123"},
            ticket(),
        )
        == "answer"
    )


def test_sdp_answer_validation_accepts_apk_base64_without_padding():
    encoded = base64.b64encode(json.dumps({"sdp": "answer"}).encode()).decode().rstrip("=")

    assert (
        webrtc_signal._owned_answer_sdp(
            {
                "messagePayload": encoded,
                "senderClientId": "SSC0A123",
                "recipientClientId": "client123",
            },
            ticket(),
        )
        == "answer"
    )


def test_apk_sdp_answer_validation_rejects_other_camera_or_viewer():
    encoded = base64.b64encode(json.dumps({"sdp": "answer"}).encode()).decode()

    assert (
        webrtc_signal._owned_answer_sdp(
            {
                "messagePayload": encoded,
                "senderClientId": "SSC0B456",
                "recipientClientId": "client123",
            },
            ticket(),
        )
        is None
    )
    assert (
        webrtc_signal._owned_answer_sdp(
            {
                "messagePayload": encoded,
                "senderClientId": "SSC0A123",
                "recipientClientId": "other-client",
            },
            ticket(),
        )
        is None
    )


def test_sdp_answer_reject_reason_keeps_debug_actionable():
    encoded = base64.b64encode(json.dumps({"sdp": "answer"}).encode()).decode()
    signal_ticket = ticket()

    assert (
        webrtc_signal._answer_reject_reason(
            {
                "messagePayload": encoded,
                "senderClientId": "SSC0B456",
                "recipientClientId": "client123",
            },
            signal_ticket,
        )
        == "sender_mismatch"
    )
    assert (
        webrtc_signal._answer_reject_reason(
            {
                "messagePayload": encoded,
                "senderClientId": "SSC0A123",
                "recipientClientId": "other-client",
            },
            signal_ticket,
        )
        == "recipient_mismatch"
    )
    assert (
        webrtc_signal._answer_reject_reason(
            {"senderClientId": "SSC0A123", "recipientClientId": "client123"},
            signal_ticket,
        )
        == "missing_message_payload"
    )
    assert (
        webrtc_signal._answer_reject_reason(
            {
                "messagePayload": base64.b64encode(b"not-json").decode(),
                "senderClientId": "SSC0A123",
                "recipientClientId": "client123",
            },
            signal_ticket,
        )
        == "invalid_sdp_payload"
    )
    assert (
        webrtc_signal._answer_reject_reason(
            {
                "messagePayload": encoded,
                "senderClientId": "SSC0A123",
                "recipientClientId": "client123",
            },
            signal_ticket,
        )
        == "accepted"
    )


def test_parse_signal_message_accepts_apk_peer_event_wrappers():
    event, payload = parse_signal_message(
        json.dumps({"event": "PEER_IN", "data": {"clientId": "SSC0A123"}})
    )
    assert event == "PEER_IN"
    assert webrtc_signal._is_owned_peer_message(payload, "SSC0A123")
    assert not webrtc_signal._is_owned_peer_message(payload, "SSC0B456")

    event, payload = parse_signal_message(
        json.dumps(
            {"type": "PEER_OUT", "message": json.dumps({"deviceSN": "SSC0B456"})}
        )
    )
    assert event == "PEER_OUT"
    assert webrtc_signal._is_owned_peer_message(payload, "SSC0B456")


def test_parse_signal_message_decodes_base64_peer_events_from_signal_server():
    encoded_serial = base64.b64encode(b"SSC0A123").decode()

    assert parse_signal_message(
        json.dumps({"messageType": "PEER_IN", "messagePayload": encoded_serial})
    ) == ("PEER_IN", "SSC0A123")

    encoded_json = base64.b64encode(
        json.dumps({"serialNumber": "SSC0A123"}).encode()
    ).decode()

    event, payload = parse_signal_message(
        json.dumps({"messageType": "PEER_OUT", "messagePayload": encoded_json})
    )
    assert event == "PEER_OUT"
    assert webrtc_signal._is_owned_peer_message(payload, "SSC0A123")


def test_parse_signal_message_keeps_plain_peer_payloads_from_apk_callback():
    assert parse_signal_message(
        json.dumps({"messageType": "PEER_IN", "messagePayload": "SSC0A123"})
    ) == ("PEER_IN", "SSC0A123")


def test_parse_signal_message_does_not_decode_plain_serial_like_peer_id():
    assert parse_signal_message(
        json.dumps({"messageType": "PEER_IN", "messagePayload": "MTAwMDA0"})
    ) == ("PEER_IN", "MTAwMDA0")


def test_object_peer_event_matches_camera_by_apk_signal_id():
    event, payload = parse_signal_message(
        json.dumps(
            {
                "messageType": "PEER_IN",
                "messagePayload": {
                    "group": "camera-group",
                    "id": "SSC0A123",
                    "name": "test-123",
                    "role": "device",
                },
            }
        )
    )

    assert event == "PEER_IN"
    assert webrtc_signal._is_owned_peer_message(payload, "SSC0A123")
    assert not webrtc_signal._is_owned_peer_message(payload, "SSC0B456")
    assert webrtc_signal._peer_event_debug(payload, "SSC0A123") == {
        "payload": "dict_keys=['group', 'id', 'name', 'role']",
        "payload_fields": {
            "group": "...-group",
            "id": "...C0A123",
            "name": "...st-123",
            "role": "device",
        },
        "payload_matches_camera": True,
        "camera": "...C0A123",
        "peer": "...C0A123",
        "peer_candidates": ["...C0A123", "...st-123"],
    }


def test_object_peer_event_preserves_all_ids_for_camera_match():
    event, payload = parse_signal_message(
        json.dumps(
            {
                "messageType": "PEER_IN",
                "messagePayload": {
                    "clientId": "viewer-client",
                    "serialNumber": "SSC0A123",
                    "role": "device",
                },
            }
        )
    )

    assert event == "PEER_IN"
    assert payload["clientId"] == "viewer-client"
    assert webrtc_signal._is_owned_peer_message(payload, "SSC0A123")


def test_stop_live_data_channel_command_matches_apk(monkeypatch):
    monkeypatch.setattr(webrtc_signal.time, "time", lambda: 100)
    monkeypatch.setattr(webrtc_signal.random, "randint", lambda start, end: 321)

    class FakeDataChannel:
        readyState = "open"

        def __init__(self):
            self.messages = []

        def send(self, message):
            self.messages.append(message)

    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._data_channel = FakeDataChannel()

    session._send_stop_live()

    assert [json.loads(message) for message in session._data_channel.messages] == [
        {
            "requestID": "100000-321",
            "connectionID": "7893feb",
            "timeStamp": 100,
            "action": "stopLive",
        }
    ]


def test_stop_live_is_not_sent_when_data_channel_is_not_open():
    class FakeDataChannel:
        readyState = "connecting"

        def __init__(self):
            self.messages = []

        def send(self, message):
            self.messages.append(message)

    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._data_channel = FakeDataChannel()

    session._send_stop_live()

    assert session._data_channel.messages == []


def test_dns_preload_covers_mdns_nsec_records(monkeypatch):
    calls = []

    def record_call(rdclass, rdtype):
        calls.append((rdclass, rdtype))

    monkeypatch.setattr(webrtc_signal.dns.rdata, "get_rdata_class", record_call)

    webrtc_signal._preload_dns_rdata_classes()

    assert (32769, 47) in calls
    assert (255, 47) in calls
    assert (1440, 41) in calls


def test_sdp_debug_includes_media_directions():
    sdp = (
        "v=0\r\n"
        "m=audio 9 UDP/TLS/RTP/SAVPF 111\r\n"
        "a=mid:0\r\n"
        "a=sendrecv\r\n"
        "m=video 9 UDP/TLS/RTP/SAVPF 102\r\n"
        "a=mid:1\r\n"
        "a=recvonly\r\n"
    )

    assert webrtc_signal._sdp_debug(sdp)["directions"] == {
        "0": "sendrecv",
        "1": "recvonly",
    }


def test_sdp_debug_includes_video_payload_fmtp_and_feedback():
    sdp = (
        "v=0\r\n"
        "m=video 9 UDP/TLS/RTP/SAVPF 101 102\r\n"
        "a=rtpmap:101 H264/90000\r\n"
        "a=rtcp-fb:101 nack\r\n"
        "a=rtcp-fb:101 nack pli\r\n"
        "a=fmtp:101 level-asymmetry-allowed=1;packetization-mode=1;profile-level-id=42e01f\r\n"
        "a=rtpmap:102 rtx/90000\r\n"
        "a=fmtp:102 apt=101\r\n"
    )

    debug = webrtc_signal._sdp_debug(sdp)

    assert debug["video_payloads"] == [
        {
            "payload": "101",
            "codec": "H264",
            "fmtp": "level-asymmetry-allowed=1;packetization-mode=1;profile-level-id=42e01f",
        },
        {"payload": "102", "codec": "RTX", "fmtp": "apt=101"},
    ]
    assert debug["video_feedback"] == {"101": ["nack", "nack pli"]}


def test_data_channel_debug_includes_safe_nested_codec_values():
    debug = webrtc_signal._data_channel_debug(
        {
            "action": "startLive",
            "data": json.dumps(
                {
                    "videoCodec": "H264",
                    "resolution": "1920x1080",
                    "url": "rtsp://example.invalid/secret",
                }
            ),
            "parameters": {"size": "1920x1080", "token": "secret"},
        }
    )

    assert debug["data_videoCodec"] == "H264"
    assert debug["data_resolution"] == "1920x1080"
    assert debug["parameter_size"] == "1920x1080"
    assert "data_url" not in debug
    assert "parameter_token" not in debug


def test_camera_webrtc_resolution_uses_apk_normalization():
    from types import SimpleNamespace

    from custom_components.xsense.camera import _camera_live_resolution

    assert (
        _camera_live_resolution(SimpleNamespace(data={"liveResolution": "HD"}))
        == "1920x1080"
    )
    assert (
        _camera_live_resolution(
            SimpleNamespace(data={"liveResolution": "VIDEO_SIZE_1440P"})
        )
        == "2560x1440"
    )
    assert (
        _camera_live_resolution(SimpleNamespace(data={"liveResolution": "auto"}))
        == "auto"
    )
    assert (
        _camera_live_resolution(
            SimpleNamespace(data={"supportedRecordingResolutions": ["P1296", "P1080"]})
        )
        == "2304x1296"
    )
    assert (
        _camera_live_resolution(
            SimpleNamespace(
                data={
                    "liveResolution": "auto",
                    "supportedRecordingResolutions": ["P1296", "P1080"],
                }
            )
        )
        == "2304x1296"
    )
    assert (
        _camera_live_resolution(
            SimpleNamespace(data={"deviceSupportResolution": ["bad", "P720"]})
        )
        == "bad"
    )
    assert (
        _camera_live_resolution(
            SimpleNamespace(data={"supportedRecordingResolutions": ["P1296"]})
        )
        == "auto"
    )
    assert _camera_live_resolution(SimpleNamespace(data={})) == "auto"


def test_start_live_waits_for_camera_data_channel_connected_like_apk(monkeypatch):
    monkeypatch.setattr(webrtc_signal.time, "time", lambda: 100)
    monkeypatch.setattr(webrtc_signal.random, "randint", lambda start, end: 321)

    class FakeDataChannel:
        def __init__(self):
            self.readyState = "connecting"
            self.messages = []

        def send(self, message):
            self.messages.append(message)

    class FakePeerConnection:
        def __init__(self):
            self.connectionState = "connecting"

    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._resolution = "2560x1440"
    session._camera_pc = FakePeerConnection()
    session._data_channel = FakeDataChannel()
    session._start_live_sent = False
    session._data_channel_connected = False
    session._first_frame_received = False
    session._first_frame_timeout_task = None
    session._first_frame_pli_task = None
    session._closed = False
    created_tasks = []

    class FakeTask:
        def __init__(self, coro):
            self.coro = coro
            self.cancelled = False
            coro.close()

        def cancel(self):
            self.cancelled = True

        def done(self):
            return False

    def create_task(coro):
        task = FakeTask(coro)
        created_tasks.append(task)
        return task

    monkeypatch.setattr(webrtc_signal.asyncio, "create_task", create_task)

    session._send_start_live_if_ready()
    assert session._data_channel.messages == []

    session._data_channel.readyState = "open"
    session._send_start_live_if_ready()
    assert session._data_channel.messages == []

    session._data_channel_connected = True
    session._send_start_live_if_ready()

    assert [json.loads(message) for message in session._data_channel.messages] == [
        {
            "requestID": "100000-321",
            "connectionID": "7893feb",
            "timeStamp": 100,
            "action": "startLive",
            "size": "1920x1080",
            "resolution": "2560x1440",
        }
    ]
    assert len(created_tasks) == 2
    assert session._first_frame_timeout_task is created_tasks[0]
    assert session._first_frame_pli_task is created_tasks[1]


def test_data_channel_connected_message_sends_start_live_like_apk(monkeypatch):
    monkeypatch.setattr(webrtc_signal.time, "time", lambda: 100)
    monkeypatch.setattr(webrtc_signal.random, "randint", lambda start, end: 321)

    class FakeDataChannel:
        readyState = "open"

        def __init__(self):
            self.messages = []

        def send(self, message):
            self.messages.append(json.loads(message))

    class FakeTask:
        def __init__(self, coro):
            self.coro = coro
            coro.close()

        def done(self):
            return False

        def cancel(self):
            return None

    created_tasks = []

    def create_task(coro):
        task = FakeTask(coro)
        created_tasks.append(task)
        return task

    monkeypatch.setattr(webrtc_signal.asyncio, "create_task", create_task)

    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._closed = False
    session._resolution = "1920x1080"
    session._data_channel = FakeDataChannel()
    session._start_live_sent = False
    session._data_channel_connected = False
    session._first_frame_received = False
    session._first_frame_timeout_task = None
    session._first_frame_pli_task = None
    session._debug_context = lambda **kwargs: kwargs

    session._handle_data_channel_message(json.dumps({"action": "dataChannelConnected"}))

    assert session._data_channel_connected is True
    assert session._data_channel.messages[0] | {"requestID": "<id>"} == {
        "requestID": "<id>",
        "connectionID": "7893feb",
        "timeStamp": 100,
        "action": "startLive",
        "size": "1920x1080",
        "resolution": "1920x1080",
    }
    assert len(created_tasks) == 2



async def test_browser_ice_candidates_wait_for_ha_remote_description():
    class FakePeer:
        def __init__(self):
            self.remoteDescription = None
            self.candidates = []

        async def addIceCandidate(self, candidate):
            if self.remoteDescription is None:
                raise AssertionError("candidate added before remote description")
            self.candidates.append(candidate)

    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._ha_pc = FakePeer()
    session._closed = False
    session._pending_ha_candidates = []

    candidate = RTCIceCandidateInit(
        "candidate:1 1 udp 1 192.0.2.1 123 typ host",
        sdp_mid="0",
        sdp_m_line_index=0,
    )

    await session.add_candidate(candidate)

    assert session._pending_ha_candidates
    assert session._ha_pc.candidates == []

    session._ha_pc.remoteDescription = object()
    await session._flush_pending_ha_candidates()

    assert session._pending_ha_candidates == []
    assert len(session._ha_pc.candidates) == 1


async def test_closed_session_ignores_late_browser_ice_candidates():
    class FakePeer:
        remoteDescription = object()

        async def addIceCandidate(self, candidate):
            raise AssertionError("closed session should ignore late candidates")

    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._closed = True
    session._ha_pc = FakePeer()
    session._pending_ha_candidates = []

    candidate = RTCIceCandidateInit(
        "candidate:1 1 udp 1 192.0.2.1 123 typ host",
        sdp_mid="0",
        sdp_m_line_index=0,
    )

    await session.add_candidate(candidate)

    assert session._pending_ha_candidates == []


async def test_send_offer_stops_cleanly_when_signal_closes_during_ice():
    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._closed = False
    session._ticket = ticket()
    session._recipient_client_id = "SSC0A123"
    session._session_id = "Android-client123-100000"
    session._resolution = "auto"
    session._camera_local_candidate_count = 0
    session._camera_offer_sent = False
    session._camera_local_description_task = None
    session._camera_pc = type(
        "FakePeer",
        (),
        {
            "localDescription": type(
                "LocalDescription",
                (),
                {"sdp": """v=0
a=ice-ufrag:test
a=candidate:1 1 udp 1 192.0.2.1 123 typ host
a=candidate:2 1 udp 1 192.0.2.2 124 typ host
"""},
            )()
        },
    )()
    session._debug_context = lambda **kwargs: kwargs
    session._camera_offer_sdp = """v=0
a=ice-ufrag:test
a=candidate:1 1 udp 1 192.0.2.1 123 typ host
a=candidate:2 1 udp 1 192.0.2.2 124 typ host
"""

    class ClosingWebSocket:
        closed = False

        def __init__(self):
            self.messages = []

        async def send_str(self, message):
            self.messages.append(json.loads(message))
            if len(self.messages) > 1:
                raise aiohttp.ClientConnectionResetError(
                    "Cannot write to closing transport"
                )

    session._ws = ClosingWebSocket()

    await session._send_offer()

    assert [message["messageType"] for message in session._ws.messages] == [
        "SDP_OFFER",
        "ICE_CANDIDATE",
    ]


async def test_close_is_idempotent_and_waits_for_reader_task():
    class FakeWs:
        closed = False

        async def close(self):
            self.closed = True

    class FakePeer:
        def __init__(self):
            self.closed = 0

        async def close(self):
            self.closed += 1

    class FakeDataChannel:
        readyState = "open"

        def __init__(self):
            self.closed = False
            self.messages = []

        def send(self, message):
            self.messages.append(json.loads(message))

        def close(self):
            self.closed = True

    async def reader():
        try:
            while True:
                await asyncio.sleep(1)
        finally:
            reader.done = True

    import asyncio

    reader.done = False
    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._closed = False
    session._close_lock = asyncio.Lock()
    session._reader_task = asyncio.create_task(reader())
    session._camera_local_description_task = None
    session._ws = FakeWs()
    session._data_channel = FakeDataChannel()
    session._camera_pc = FakePeer()
    session._ha_pc = FakePeer()
    session._pending_ha_candidates = [object()]
    session._pending_camera_candidates = [object()]

    await asyncio.sleep(0)
    await session.close()
    await session.close()

    assert session._closed is True
    assert reader.done is True
    assert session._ws.closed is True
    assert session._data_channel.closed is True
    assert session._camera_pc.closed == 1
    assert session._ha_pc.closed == 1
    assert session._pending_ha_candidates == []
    assert session._pending_camera_candidates == []
    assert session._data_channel.messages[0]["action"] == "stopLive"


async def test_closed_session_ignores_late_signal_events():
    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._closed = True
    session._ticket = ticket()
    session._recipient_client_id = "SSC0A123"
    session._camera_peer_ready = False

    await session._handle_signal_event("PEER_IN", "SSC0A123")

    assert session._camera_peer_ready is False


async def test_camera_offer_does_not_wait_for_local_ice_gathering():
    class FakeWs:
        closed = False

        def __init__(self):
            self.messages = []

        async def send_str(self, message):
            self.messages.append(json.loads(message))

    async def never_finishes():
        await asyncio.Future()

    import asyncio

    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._closed = False
    session._ws = FakeWs()
    session._camera_offer_sdp = "v=0\r\n"
    session._camera_local_description_task = asyncio.create_task(never_finishes())
    session._camera_pc = object()
    session._camera_peer_ready = False
    session._camera_offer_sent = False
    session._ticket = ticket()
    session._recipient_client_id = "SSC0A123"
    session._session_id = "Android-client123-100000"
    session._resolution = "1280x720"

    task = asyncio.create_task(session._send_offer())
    await asyncio.sleep(0)

    assert [message["messageType"] for message in session._ws.messages] == ["SDP_OFFER"]
    assert session._camera_offer_sent is True

    session._camera_local_description_task.cancel()
    with suppress(asyncio.CancelledError):
        await task


async def test_webrtc_close_does_not_cancel_current_timeout_task():
    import asyncio

    class FakePeerConnection:
        def __init__(self):
            self.closed = False

        async def close(self):
            self.closed = True

    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._closed = False
    session._close_lock = asyncio.Lock()
    session._reader_task = None
    session._keep_alive = None
    session._keep_alive_task = None
    session._play_timeout_task = asyncio.current_task()
    session._camera_local_description_task = None
    session._ws = None
    session._data_channel = None
    session._camera_pc = FakePeerConnection()
    session._ha_pc = FakePeerConnection()
    session._pending_ha_candidates = []
    session._pending_camera_candidates = []

    await session.close()

    assert session._closed is True
    assert session._camera_pc.closed is True
    assert session._ha_pc.closed is True
    assert not asyncio.current_task().cancelled()


async def test_webrtc_close_stops_peer_transports_before_closing():
    import asyncio

    calls = []

    class StopPart:
        def __init__(self, name):
            self.name = name

        async def stop(self):
            calls.append(self.name)

    class FakeTransceiver:
        def __init__(self):
            self.sender = StopPart("transceiver-sender")
            self.receiver = StopPart("transceiver-receiver")

        async def stop(self):
            calls.append("transceiver")

    class FakePeerConnection:
        def __init__(self, name):
            self.name = name
            self.transceiver = FakeTransceiver()
            self.sender = StopPart(f"{name}-sender")
            self.receiver = StopPart(f"{name}-receiver")

        def getTransceivers(self):
            return [self.transceiver]

        def getSenders(self):
            return [self.sender]

        def getReceivers(self):
            return [self.receiver]

        async def close(self):
            calls.append(f"{self.name}-close")

    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._closed = False
    session._close_lock = asyncio.Lock()
    session._reader_task = None
    session._keep_alive = None
    session._keep_alive_task = None
    session._play_timeout_task = None
    session._first_frame_timeout_task = None
    session._camera_local_description_task = None
    session._ws = None
    session._data_channel = None

    class TrackPart:
        def __init__(self, name):
            self.name = name

        def stop(self):
            calls.append(self.name)

    session._video = TrackPart("video")
    session._audio = TrackPart("audio")
    session._camera_pc = FakePeerConnection("camera")
    session._ha_pc = FakePeerConnection("ha")
    session._pending_ha_candidates = []
    session._pending_camera_candidates = []
    session._on_close = None

    await session.close()

    assert calls == [
        "video",
        "audio",
        "transceiver",
        "transceiver-sender",
        "transceiver-receiver",
        "camera-sender",
        "camera-receiver",
        "camera-close",
        "transceiver",
        "transceiver-sender",
        "transceiver-receiver",
        "ha-sender",
        "ha-receiver",
        "ha-close",
    ]


async def test_webrtc_timeout_reports_error_and_closes_session():
    import asyncio

    messages = []
    closed = []
    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._closed = False
    session._send_message = messages.append

    async def close():
        closed.append(True)
        session._closed = True

    session.close = close

    await session._fail_after_timeout(0, "test_timeout", "Timed out")

    assert messages[0].code == "test_timeout"
    assert messages[0].message == "Timed out"
    assert closed == [True]


async def test_first_frame_timeout_debug_includes_camera_sdp_and_receiver_stats():
    messages = []
    closed = []
    debug_contexts = []
    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._closed = False
    session._send_message = messages.append
    session._camera_offer_sdp = (
        "v=0\r\n"
        "m=video 9 UDP/TLS/RTP/SAVPF 101\r\n"
        "a=rtpmap:101 H264/90000\r\n"
        "a=rtcp-fb:101 nack pli\r\n"
        "a=fmtp:101 level-asymmetry-allowed=1;packetization-mode=1;profile-level-id=42e01f\r\n"
    )
    session._camera_answer_sdp = (
        "v=0\r\n"
        "m=video 9 UDP/TLS/RTP/SAVPF 101\r\n"
        "a=rtpmap:101 H264/90000\r\n"
        "a=sendonly\r\n"
    )

    async def stats():
        return {"video_receiver_stats": [{"ssrcs": [1234], "packetsReceived": 10}]}

    async def close():
        closed.append(True)
        session._closed = True

    def debug_context(**extra):
        debug_contexts.append(extra)
        return extra

    session._camera_receiver_stats_debug = stats
    session._debug_context = debug_context
    session.close = close

    await session._fail_after_timeout(
        0, "xsense_webrtc_first_frame_timeout", "Timed out"
    )

    assert messages[0].code == "xsense_webrtc_first_frame_timeout"
    assert debug_contexts[0]["video_receiver_stats"] == [
        {"ssrcs": [1234], "packetsReceived": 10}
    ]
    assert debug_contexts[0]["camera_offer_sdp"]["video_feedback"] == {
        "101": ["nack pli"]
    }
    assert debug_contexts[0]["camera_answer_sdp"]["directions"] == {
        "video": "sendonly"
    }
    assert closed == [True]


def test_signal_close_schedules_apk_style_reconnect():
    scheduled = []
    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._closed = False
    session._signal_reconnect_task = None

    def create_task(coro):
        scheduled.append(coro)
        return SimpleTask()

    class SimpleTask:
        def done(self):
            return False

    session._signal_reconnect_after_delay = lambda close_code: f"reconnect-{close_code}"
    original_create_task = webrtc_signal.asyncio.create_task
    webrtc_signal.asyncio.create_task = create_task
    try:
        session._schedule_signal_reconnect(1000)
        session._schedule_signal_reconnect(1001)
    finally:
        webrtc_signal.asyncio.create_task = original_create_task

    assert scheduled == ["reconnect-1000"]


async def test_signal_reconnect_delay_matches_apk(monkeypatch):
    delays = []
    reconnected = []
    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._closed = False
    session._debug_context = lambda **kwargs: kwargs

    async def reconnect_signal():
        reconnected.append(True)

    async def sleep(delay):
        delays.append(delay)

    session._reconnect_signal = reconnect_signal

    monkeypatch.setattr(webrtc_signal.asyncio, "sleep", sleep)

    await session._signal_reconnect_after_delay(1000)

    assert delays == [5]
    assert reconnected == [True]

def test_signal_close_skips_apk_terminal_close_codes():
    scheduled = []
    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._closed = False
    session._signal_reconnect_task = None

    def create_task(coro):
        scheduled.append(coro)
        return object()

    session._signal_reconnect_after_delay = lambda close_code: f"reconnect-{close_code}"
    original_create_task = webrtc_signal.asyncio.create_task
    webrtc_signal.asyncio.create_task = create_task
    try:
        session._schedule_signal_reconnect(3002)
        session._schedule_signal_reconnect(3004)
    finally:
        webrtc_signal.asyncio.create_task = original_create_task

    assert scheduled == []


async def test_peer_in_timeout_refreshes_ticket_without_terminal_error(monkeypatch):
    messages = []
    refreshed = []
    reconnected = []
    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._closed = False
    session._send_message = messages.append
    session._ticket = ticket()
    session._session_id = "Android-client123-100000"
    session._recipient_client_id = "SSC0A123"
    session._camera_offer_sdp = None
    session._camera_pc = None
    session._ha_pc = None
    session._data_channel = None
    session._camera_online = False
    session._camera_peer_ready = False
    session._camera_offer_sent = False
    session._sdp_answer_received = False
    session._first_frame_received = False
    session._start_live_sent = False
    session._last_signal_event = None
    session._signal_event_counts = Counter()
    session._camera_local_candidate_count = 0
    session._camera_remote_candidate_count = 0
    session._pending_ha_candidates = []
    session._pending_camera_candidates = []

    async def immediate_sleep(_delay):
        return None

    async def refresh_ticket():
        refreshed.append(True)
        return ticket(id="client456")

    async def reconnect_signal():
        reconnected.append(True)

    async def close():
        raise AssertionError("PEER_IN timeout should not close the session")

    session._reconnect_signal = reconnect_signal
    monkeypatch.setattr(webrtc_signal.asyncio, "sleep", immediate_sleep)
    monkeypatch.setattr(webrtc_signal.time, "time", lambda: 101)
    session._refresh_ticket = refresh_ticket
    session.close = close

    await session._handle_peer_in_timeout()

    assert refreshed == [True]
    assert messages == []
    assert session._ticket.client_id == "client456"
    assert session._session_id == "Android-client456-101000"
    assert reconnected == [True]


async def test_first_video_frame_cancels_play_timeout():
    import asyncio

    class FakeSource:
        async def recv(self):
            return object()

    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._first_frame_received = False
    play_timeout_task = asyncio.create_task(asyncio.sleep(60))
    first_frame_timeout_task = asyncio.create_task(asyncio.sleep(60))
    first_frame_pli_task = asyncio.create_task(asyncio.sleep(60))
    session._play_timeout_task = play_timeout_task
    session._first_frame_timeout_task = first_frame_timeout_task
    session._first_frame_pli_task = first_frame_pli_task
    track = webrtc_signal._ProxyTrack("video", session._mark_first_frame_received)
    track.set_source(FakeSource())

    await track.recv()

    assert session._first_frame_received is True
    await asyncio.sleep(0)
    assert play_timeout_task.cancelled()
    assert first_frame_timeout_task.cancelling()
    assert first_frame_pli_task.cancelling()
    assert session._play_timeout_task is None
    assert session._first_frame_timeout_task is None
    assert session._first_frame_pli_task is None


async def test_camera_offer_restarts_play_timeout_for_retry(monkeypatch):
    class FakeWs:
        closed = False

        def __init__(self):
            self.messages = []

        async def send_str(self, message):
            self.messages.append(json.loads(message))

    class FakePeer:
        localDescription = None

    class FakeTask:
        def __init__(self, coro=None):
            self.cancelled = False
            if coro is not None:
                coro.close()

        def cancel(self):
            self.cancelled = True

    created_tasks = []

    def create_task(coro):
        task = FakeTask(coro)
        created_tasks.append(task)
        return task

    monkeypatch.setattr(webrtc_signal.asyncio, "create_task", create_task)

    old_task = FakeTask()
    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._closed = False
    session._ws = FakeWs()
    session._camera_offer_sdp = "v=0\r\n"
    session._camera_offer_sent = False
    session._camera_local_description_task = None
    session._camera_pc = FakePeer()
    session._ticket = ticket()
    session._recipient_client_id = "SSC0A123"
    session._session_id = "Android-client123-100000"
    session._resolution = "1920x1080"
    session._play_timeout_task = old_task

    await session._send_offer()

    assert old_task.cancelled is True
    assert session._play_timeout_task is created_tasks[-1]
    assert session._camera_offer_sent is True
    assert [message["messageType"] for message in session._ws.messages] == [
        "SDP_OFFER"
    ]


def test_reset_camera_peer_state_cancels_stale_attempt_state(monkeypatch):
    monkeypatch.setattr(webrtc_signal.time, "time", lambda: 100)

    class FakeTask:
        def __init__(self):
            self.cancelled = False

        def cancel(self):
            self.cancelled = True

    play_task = FakeTask()
    first_frame_task = FakeTask()
    first_frame_pli_task = FakeTask()
    local_description_task = FakeTask()
    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._ticket = ticket()
    session._session_id = "Android-client123-old"
    session._camera_pc = None
    session._data_channel = object()
    session._camera_offer_sent = True
    session._camera_offer_sdp = "stale-offer"
    session._sdp_answer_received = True
    session._camera_local_description_task = local_description_task
    session._pending_camera_candidates = [object()]
    session._camera_local_candidate_count = 3
    session._camera_remote_candidate_count = 2
    session._start_live_sent = True
    session._first_frame_received = False
    session._play_timeout_task = play_task
    session._first_frame_timeout_task = first_frame_task
    session._first_frame_pli_task = first_frame_pli_task

    session._reset_camera_peer_state()

    assert session._session_id == "Android-client123-100000"
    assert play_task.cancelled is True
    assert first_frame_task.cancelled is True
    assert first_frame_pli_task.cancelled is True
    assert local_description_task.cancelled is True
    assert session._play_timeout_task is None
    assert session._first_frame_timeout_task is None
    assert session._first_frame_pli_task is None
    assert session._camera_local_description_task is None


async def test_camera_keyframe_request_sends_pli_for_video_ssrcs():
    class FakeTrack:
        kind = "video"

    class FakeReceiver:
        track = FakeTrack()

        def __init__(self):
            self._RTCRtpReceiver__active_ssrc = {1234: object()}
            self._RTCRtpReceiver__remote_streams = {5678: object()}
            self.sent = []

        async def _send_rtcp_pli(self, ssrc):
            self.sent.append(ssrc)

    class FakeAudioReceiver:
        class Track:
            kind = "audio"

        track = Track()

        async def _send_rtcp_pli(self, ssrc):
            raise AssertionError("audio receiver should not receive PLI")

    class FakePeer:
        def __init__(self, receivers):
            self.receivers = receivers

        def getReceivers(self):
            return self.receivers

    receiver = FakeReceiver()
    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._camera_pc = FakePeer([receiver, FakeAudioReceiver()])
    session._debug_context = lambda **extra: extra

    assert await session._send_camera_picture_loss_indication() == [5678]
    assert receiver.sent == [5678]


def test_receiver_media_ssrcs_prefers_remote_streams_over_active_ssrcs():
    class FakeReceiver:
        _RTCRtpReceiver__active_ssrc = {1234: object(), "5678": object()}
        _RTCRtpReceiver__remote_streams = {1234: object(), "bad": object()}

    assert webrtc_signal._receiver_media_ssrcs(FakeReceiver()) == [1234]


def test_receiver_media_ssrcs_falls_back_to_active_ssrcs():
    class FakeReceiver:
        _RTCRtpReceiver__active_ssrc = {1234: object(), "5678": object()}
        _RTCRtpReceiver__remote_streams = {}

    assert webrtc_signal._receiver_media_ssrcs(FakeReceiver()) == [1234, 5678]


def test_receiver_media_ssrcs_maps_rtx_to_primary_media_ssrcs():
    class FakeReceiver:
        _RTCRtpReceiver__active_ssrc = {4321: object(), 9999: object()}
        _RTCRtpReceiver__remote_streams = {4321: object(), 9999: object()}
        _RTCRtpReceiver__rtx_ssrc = {9999: 4321}

    assert webrtc_signal._receiver_media_ssrcs(FakeReceiver()) == [4321]


async def test_online_camera_waits_for_peer_in_before_offer_like_apk():
    class FakeWs:
        closed = False

        def __init__(self):
            self.messages = []

        async def send_str(self, message):
            self.messages.append(json.loads(message))

        async def close(self):
            self.closed = True

    class FakeSession:
        def __init__(self):
            self.ws = FakeWs()
            self.connect_url = None

        async def ws_connect(self, url, **kwargs):
            self.connect_url = url
            self.connect_kwargs = kwargs
            return self.ws

    class FakeHaPeer:
        def __init__(self):
            self.localDescription = None
            self.tracks = []

        def addTrack(self, track):
            self.tracks.append(track)

        async def setRemoteDescription(self, description):
            self.remoteDescription = description

        async def createAnswer(self):
            class Answer:
                sdp = "v=0\r\n"

            return Answer()

        async def setLocalDescription(self, answer):
            self.localDescription = answer

        async def close(self):
            return None

    class FakeCameraPeer:
        async def close(self):
            return None

    class FakeTask:
        def __init__(self, coro):
            self.coro = coro
            self.cancelled = False
            coro.close()

        def cancel(self):
            self.cancelled = True

        def done(self):
            return True

    import asyncio

    started = []
    sent_messages = []
    tasks = []

    async def start_camera_peer():
        started.append(True)

    async def noop_async(*args):
        return None

    def create_task(coro):
        task = FakeTask(coro)
        tasks.append(task)
        return task

    aio_session = FakeSession()
    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._session = aio_session
    session._send_message = sent_messages.append
    session._offer_sdp = "v=0\r\n"
    session._ticket = ticket()
    session._camera_online = True
    session._session_id = "Android-client123-100000"
    session._recipient_client_id = "SSC0A123"
    session._resolution = "1280x720"
    session._ws = None
    session._reader_task = None
    session._keep_alive = None
    session._keep_alive_task = None
    session._ha_pc = FakeHaPeer()
    session._camera_pc = FakeCameraPeer()
    session._video = object()
    session._audio = object()
    session._pending_ha_candidates = []
    session._pending_camera_candidates = []
    session._camera_peer_ready = False
    session._data_channel = None
    session._data_channel_connected = False
    session._camera_offer_sent = False
    session._camera_offer_sdp = None
    session._camera_local_description_task = None
    session._peer_in_timeout_task = None
    session._play_timeout_task = None
    session._first_frame_timeout_task = None
    session._start_live_sent = False
    session._first_frame_received = False
    session._closed = False
    session._close_lock = asyncio.Lock()
    session._setup_camera_peer = lambda: None
    session._flush_pending_ha_candidates = noop_async
    session._read_loop = noop_async
    session._fail_after_timeout = noop_async
    session._start_camera_peer = start_camera_peer

    original_create_task = webrtc_signal.asyncio.create_task
    webrtc_signal.asyncio.create_task = create_task
    try:
        assert await session.start() is True
    finally:
        webrtc_signal.asyncio.create_task = original_create_task

    assert aio_session.ws.messages == []
    assert aio_session.connect_kwargs["heartbeat"] == 30
    assert started == []
    assert session._peer_in_timeout_task is not None
    assert len(tasks) == 3
    assert sent_messages[0].answer == "v=0\r\n"


async def test_offline_camera_waits_for_peer_in_before_offer_like_apk():
    class FakeWs:
        closed = False

        def __init__(self):
            self.messages = []

        async def send_str(self, message):
            self.messages.append(json.loads(message))

    class FakePeer:
        localDescription = None

        def addTransceiver(self, *args, **kwargs):
            return None

        async def createOffer(self):
            class Offer:
                sdp = "v=0\r\n"
                type = "offer"

            return Offer()

        async def setLocalDescription(self, offer):
            self.localDescription = offer

    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._closed = False
    session._ws = FakeWs()
    session._camera_pc = FakePeer()
    session._camera_offer_sdp = None
    session._camera_local_description_task = None
    session._camera_peer_ready = False
    session._camera_offer_sent = False
    session._ticket = ticket()
    session._recipient_client_id = "SSC0A123"
    session._session_id = "Android-client123-100000"
    session._resolution = "1280x720"
    session._peer_in_timeout_task = None
    session._restart_play_timeout = lambda: None

    assert session._ws.messages == []

    await session._handle_signal_event("PEER_IN", "SSC0A123")

    assert [message["messageType"] for message in session._ws.messages] == ["SDP_OFFER"]
    assert session._camera_offer_sent is True


async def test_peer_out_before_first_frame_resets_offer_for_next_peer_in_like_apk():
    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._closed = False
    session._ticket = ticket()
    session._recipient_client_id = "SSC0A123"
    session._camera_peer_ready = True
    session._first_frame_received = False
    session._camera_offer_sent = True
    session._camera_offer_sdp = "stale-offer"
    session._signal_event_counts = {}
    session._camera_local_candidate_count = 3
    session._camera_remote_candidate_count = 0
    session._pending_ha_candidates = []
    session._pending_camera_candidates = []
    restarted_peer_in_timeout = []
    session._reset_called = False
    started = []

    def reset_camera_peer_state():
        session._reset_called = True
        session._camera_offer_sent = False
        session._camera_offer_sdp = None

    async def start_camera_peer():
        started.append(True)

    session._reset_camera_peer_state = reset_camera_peer_state
    session._restart_peer_in_timeout = lambda: restarted_peer_in_timeout.append(True)
    session._start_camera_peer = start_camera_peer

    await session._handle_signal_event("PEER_OUT", "SSC0A123")

    assert session._reset_called is True
    assert session._camera_peer_ready is False
    assert session._camera_offer_sent is False
    assert session._camera_offer_sdp is None
    assert restarted_peer_in_timeout == [True]

    await session._handle_signal_event("PEER_IN", "SSC0A123")

    assert session._camera_peer_ready is True
    assert started == [True]
