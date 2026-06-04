import base64
import json

from webrtc_models import RTCIceCandidateInit

from custom_components.xsense import webrtc_signal
from custom_components.xsense.webrtc_signal import (
    SIGNAL_DATA_CHANNEL,
    XSenseWebRTCTicket,
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
    assert signal_ticket.signal_connect_options() == {
        "url": (
            "wss://203.0.113.10:443/group/viewer/client123"
            "?traceId=trace&time=123456&sign=sig&name=test-123"
        ),
        "headers": {"Host": "signal.example:443"},
        "server_hostname": "signal.example",
    }


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
    assert make_start_live_data_channel_message("auto")["size"] == "1280x720"
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


def test_local_sdp_candidates_extracts_apk_payloads_and_skips_loopback():
    sdp = """v=0
m=video 9 UDP/TLS/RTP/SAVPF 96
a=mid:0
a=candidate:1 1 udp 1 192.0.2.1 123 typ host
a=candidate:2 1 udp 1 127.0.0.1 456 typ host
m=audio 9 UDP/TLS/RTP/SAVPF 111
a=mid:1
a=candidate:3 1 udp 1 2001:db8::1 789 typ host
a=candidate:4 1 udp 1 ::1 790 typ host
"""

    assert webrtc_signal._local_sdp_candidates(sdp) == [
        {
            "sdpMid": "0",
            "sdpMLineIndex": 0,
            "candidate": "candidate:1 1 udp 1 192.0.2.1 123 typ host",
        },
    ]


async def test_send_offer_sends_apk_offer_then_local_ice_candidates():
    class FakeWs:
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
    session._camera_peer_ready = True
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
    assert session._ws.messages[1] | {"messagePayload": "<decoded>"} == {
        "messageType": "ICE_CANDIDATE",
        "messagePayload": "<decoded>",
        "recipientClientId": "SSC0A123",
        "senderClientId": "client123",
        "sessionId": "Android-client123-100000",
    }
    assert session._camera_offer_sent is True


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


def test_parse_signal_message_accepts_apk_peer_event_wrappers():
    assert parse_signal_message(
        json.dumps({"event": "PEER_IN", "data": {"clientId": "SSC0A123"}})
    ) == ("PEER_IN", "SSC0A123")
    assert webrtc_signal._is_owned_peer_message("SSC0A123", "SSC0A123")
    assert not webrtc_signal._is_owned_peer_message("SSC0B456", "SSC0A123")
    assert parse_signal_message(
        json.dumps(
            {"type": "PEER_OUT", "message": json.dumps({"deviceSN": "SSC0B456"})}
        )
    ) == ("PEER_OUT", "SSC0B456")



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


def test_start_live_waits_for_data_channel_and_connected_camera_peer(monkeypatch):
    monkeypatch.setattr(webrtc_signal.time, "time", lambda: 100)
    monkeypatch.setattr(webrtc_signal.random, "randint", lambda start, end: 321)

    class FakeDataChannel:
        def __init__(self):
            self.readyState = "connecting"
            self.messages = []

        def send(self, message):
            self.messages.append(message)

    session = object.__new__(webrtc_signal.XSenseWebRTCSession)
    session._resolution = "2560x1440"
    session._data_channel = FakeDataChannel()
    session._camera_peer_connected = False
    session._start_live_sent = False

    session._send_start_live_if_ready()
    assert session._data_channel.messages == []

    session._data_channel.readyState = "open"
    session._send_start_live_if_ready()
    assert session._data_channel.messages == []

    session._camera_peer_connected = True
    session._send_start_live_if_ready()
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
