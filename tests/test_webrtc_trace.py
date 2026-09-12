"""Privacy and shape checks for ticket-to-peer traces."""
import base64
import json

import pytest

from custom_components.xsense.python_xsense.webrtc_trace import frame_context, trace_host, trace_id


@pytest.mark.parametrize("encoded", [False, True])
def test_peer_trace_preserves_identity_suffixes_without_payload_secrets(encoded):
    peer = {"id": "camera-123456", "name": "camera-123456", "group": "camera-123456",
            "role": "device", "sign": "PRIVATE_SIGNATURE", "token": "PRIVATE_TOKEN"}
    payload = json.dumps(peer)
    if encoded:
        payload = base64.b64encode(payload.encode()).decode()
    result = frame_context(json.dumps({"messageType": "PEER_IN", "messagePayload": payload,
                                      "Authorization": "PRIVATE_AUTH"}))
    assert result["peer"] == {"id": "...123456", "name": "...123456", "group": "...123456", "role": "device"}
    assert result["messageType"] == "PEER_IN"
    assert "PRIVATE" not in str(result)
    assert "camera-" not in str(result)


def test_answer_trace_does_not_decode_sdp_or_ice():
    result = frame_context(json.dumps({"messageType": "SDP_ANSWER",
        "senderClientId": "camera-123456", "recipientClientId": "viewer-654321",
        "messagePayload": "PRIVATE_SDP", "candidate": "PRIVATE_ICE"}))
    assert result["envelope"]["senderClientId"] == "...123456"
    assert "PRIVATE" not in str(result)


@pytest.mark.parametrize("raw", [b"\xff", "[]", "123", "null", "PRIVATE" * 20000,
                                   '{"messageType":{"secret":"PRIVATE"}}'])
def test_unrecognized_frames_remain_safe(raw):
    assert "PRIVATE" not in str(frame_context(raw))


def test_trace_host_excludes_credentials_and_query():
    assert trace_host("wss://user:PRIVATE@signal.example/path?sign=PRIVATE") == "signal.example"
    assert trace_host("wss://[") is None
    assert trace_id("123456") == "...23456"
    assert trace_id("x") == "..."


async def test_ticket_trace_uses_actual_request_identity(caplog):
    from custom_components.xsense.python_xsense.async_xsense import AsyncXSense
    from custom_components.xsense.python_xsense.entity import Entity
    caplog.set_level("DEBUG")
    client = AsyncXSense()
    camera = Entity()
    camera.sn = "camera-123456"
    camera.type = "SSC0A"
    calls = []

    async def call(endpoint, **kwargs):
        calls.append(kwargs["serialNumber"])
        return {"id": "viewer-654321", "groupId": camera.sn, "role": "viewer",
                "realCxSerialNumber": camera.sn, "sign": "PRIVATE_SIGNATURE",
                "accessToken": "PRIVATE_TOKEN", "signalServer": "wss://signal.example/path?token=PRIVATE",
                "expirationTime": 9999999999999}

    client.addx_call = call
    await client.get_camera_webrtc_ticket(camera, force_refresh=True)
    assert calls == [camera.sn]
    assert "request_serial': '...123456'" in caplog.text
    assert "groupId': '...123456'" in caplog.text
    assert "PRIVATE" not in caplog.text
    assert camera.sn not in caplog.text
