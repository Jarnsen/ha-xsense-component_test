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
        "iceServer": [{"url": "turn:turn.example", "username": "user", "credential": "secret"}],
    }
    data.update(overrides)
    return XSenseWebRTCTicket.from_api("SSC0A123", data)


def test_ticket_connect_details_match_apk(monkeypatch):
    monkeypatch.setattr(webrtc_signal.time, "time", lambda: 100.123)

    signal_ticket = ticket(signalServer="https://signal.example:443", signalServerIpAddress="203.0.113.10")

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
    candidate = json.loads(
        make_ice_candidate_payload(
            candidate=RTCIceCandidateInit(
                "candidate:1 1 udp 1 192.0.2.1 123 typ host",
                sdp_mid="0",
                sdp_m_line_index=0,
            ),
            ticket=ticket(),
            recipient_client_id="SSC0A123",
            session_id="Android-client123-100000",
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
    assert json.loads(base64.b64decode(offer["messagePayload"])) == {"type": "offer", "sdp": "v=0\r\n"}
    assert candidate | {"messagePayload": "<decoded>"} == {
        "messageType": "ICE_CANDIDATE",
        "messagePayload": "<decoded>",
        "recipientClientId": "SSC0A123",
        "senderClientId": "client123",
        "sessionId": "Android-client123-100000",
    }
    assert json.loads(base64.b64decode(candidate["messagePayload"])) == {
        "sdpMid": "0",
        "sdpMLineIndex": 0,
        "candidate": "candidate:1 1 udp 1 192.0.2.1 123 typ host",
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
        json.dumps({"type": "PEER_OUT", "message": json.dumps({"deviceSN": "SSC0B456"})})
    ) == ("PEER_OUT", "SSC0B456")


def test_localhost_ice_candidates_are_filtered_like_apk():
    assert webrtc_signal._is_localhost_candidate(
        RTCIceCandidateInit(
            "candidate:1 1 udp 1 127.0.0.1 123 typ host",
            sdp_mid="0",
            sdp_m_line_index=0,
        )
    )
    assert webrtc_signal._is_localhost_candidate(
        RTCIceCandidateInit(
            "candidate:1 1 udp 1 ::1 123 typ host",
            sdp_mid="0",
            sdp_m_line_index=0,
        )
    )
    assert not webrtc_signal._is_localhost_candidate(
        RTCIceCandidateInit(
            "candidate:1 1 udp 1 192.0.2.1 123 typ host",
            sdp_mid="0",
            sdp_m_line_index=0,
        )
    )
