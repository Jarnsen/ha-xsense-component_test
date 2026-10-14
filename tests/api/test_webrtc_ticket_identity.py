"""Keep history discovery from changing a previously accepted ticket identity."""

import base64
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.xsense.python_xsense.async_xsense import AsyncXSense
from custom_components.xsense.python_xsense.exceptions import APIFailure
from custom_components.xsense.python_xsense.webrtc_signal import (
    XSenseWebRTCSignalSession,
    XSenseWebRTCTicket,
)


@pytest.mark.asyncio
@pytest.mark.parametrize("reject_previous", [False, True])
async def test_history_lookup_does_not_replace_ticket_identity(reject_previous):
    client = AsyncXSense()
    home = SimpleNamespace(house_id="home-1", mqtt_region="eu-central-1")
    client.houses = {"home-1": home}
    data = {"addxSerialNumber": "live-id"}
    camera = SimpleNamespace(
        sn="label-id", entity_id="history-id", data=data,
        house=home, set_data=data.update,
    )
    calls = []

    async def addx_call(endpoint, **kwargs):
        assert endpoint == "/device/getWebrtcTicket"
        assert kwargs["_house"] is home
        assert kwargs["verifyDormancyStatus"] is True
        serial = kwargs["serialNumber"]
        calls.append(serial)
        if reject_previous and len(calls) > 1 and serial == "live-id":
            raise APIFailure("error -2002/DEVICE_NO_ACCESS")
        return {"signalServer": "https://signal.example"}

    async def history_pages(serials, *args, **kwargs):
        assert kwargs["house"] is home
        return {"list": (
            [{"serialNumber": "history-id", "videoEvent": "motion"}]
            if serials == ["history-id"] else []
        )}

    client.addx_call = addx_call
    client._get_camera_library_pages = history_pages
    first = await client.get_camera_webrtc_ticket(camera, force_refresh=True)
    assert first["serialNumber"] == "live-id"

    history = await client.get_camera_library_history_for_cameras([camera], 1, 2)
    assert len(history["list"]) == 1
    assert data["addxAccessSerialNumber"] == "live-id"
    assert data["cameraLibrarySerialNumber"] == "history-id"

    refreshed = await client.get_camera_webrtc_ticket(camera, force_refresh=True)
    expected = ["live-id", "live-id"]
    if reject_previous:
        expected.append("history-id")
    assert calls == expected
    assert refreshed["serialNumber"] == expected[-1]


@pytest.mark.asyncio
@pytest.mark.parametrize("history_kind", ["library", "event"])
@pytest.mark.parametrize("history_first", [True, False])
async def test_history_identity_is_independent_of_live_startup(history_kind, history_first):
    client = AsyncXSense()
    home = SimpleNamespace(house_id="home-1", mqtt_region="eu-central-1")
    client.houses = {"home-1": home}
    data = {"addxSerialNumber": "live-id"}
    camera = SimpleNamespace(
        sn="label-id", entity_id="history-id", data=data,
        house=home, set_data=data.update,
    )
    ticket_calls = []
    history_calls = []

    async def addx_call(endpoint, **kwargs):
        assert endpoint == "/device/getWebrtcTicket"
        assert kwargs["_house"] is home
        ticket_calls.append(kwargs["serialNumber"])
        return {"signalServer": "https://signal.example"}

    async def history_pages(serials, *args, **kwargs):
        assert kwargs["house"] is home
        history_calls.append(serials)
        return {"list": (
            [{"serialNumber": "history-id", "videoEvent": "motion"}]
            if serials == ["history-id"] else []
        )}

    client.addx_call = addx_call
    client._get_camera_library_pages = history_pages
    client.get_camera_event_record_history = history_pages
    history_method = (
        client.get_camera_library_history_for_cameras
        if history_kind == "library" else client.get_camera_event_record_history_for_cameras
    )
    if not history_first:
        await client.get_camera_webrtc_ticket(camera, force_refresh=True)
    assert len((await history_method([camera], 1, 2))["list"]) == 1
    assert data["addxSerialNumber"] == "live-id"
    ticket = await client.get_camera_webrtc_ticket(camera, force_refresh=True)
    assert ticket["serialNumber"] == "live-id"
    assert set(ticket_calls) == {"live-id"}
    signal_ticket = XSenseWebRTCTicket.from_api(ticket["serialNumber"], {
        **ticket, "groupId": "group", "role": "viewer", "id": "viewer-id",
        "traceId": "trace", "sign": "signature", "time": 1,
    })
    session = XSenseWebRTCSignalSession(
        session=SimpleNamespace(), ticket=signal_ticket,
        offer_sdp="v=0\r\nm=video 9 UDP/TLS/RTP/SAVPF 99\r\na=mid:0\r\n",
        resolution="1920x1080", camera_online=True,
    )
    ws = SimpleNamespace(closed=False, send_str=AsyncMock(), close=AsyncMock())
    session._ws = ws
    try:
        await session._handle_signal_event("PEER_IN", "other-camera")
        ws.send_str.assert_not_awaited()
        await session._handle_signal_event("PEER_IN", "live-id")
        assert session._camera_peer_ready
        offer = json.loads(ws.send_str.await_args.args[0])
        assert offer["messageType"] == "SDP_OFFER"
        assert offer["recipientClientId"] == "live-id"
        answer = "v=0\r\nm=video 9 UDP/TLS/RTP/SAVPF 99\r\na=mid:0\r\n"
        await session._handle_signal_event("SDP_ANSWER", {
            "senderClientId": "live-id", "recipientClientId": "viewer-id",
            "messagePayload": base64.b64encode(json.dumps({
                "type": "answer", "sdp": answer,
            }).encode()).decode(),
        })
        assert session._answer.done()
        assert "m=video" in session._answer.result()
    finally:
        await session.close()
    history_calls.clear()
    assert len((await history_method([camera], 2, 3))["list"]) == 1
    assert history_calls == [["history-id"]]


@pytest.mark.asyncio
@pytest.mark.parametrize("history_kind", ["library", "event"])
async def test_ticket_fallback_preserves_discovered_history_identity(history_kind):
    client = AsyncXSense()
    home = SimpleNamespace(house_id="home-1", mqtt_region="eu-central-1")
    client.houses = {"home-1": home}
    data = {"addxSerialNumber": "recording-id"}
    camera = SimpleNamespace(
        sn="label-id", entity_id="live-id", data=data,
        house=home, set_data=data.update,
    )
    history_calls = []

    async def addx_call(endpoint, **kwargs):
        assert kwargs["_house"] is home
        if kwargs["serialNumber"] == "recording-id":
            raise APIFailure("error -2002/DEVICE_NO_ACCESS")
        return {"signalServer": "https://signal.example"}

    async def history_pages(serials, *args, **kwargs):
        history_calls.append(serials)
        return {"list": (
            [{"serialNumber": "recording-id", "videoEvent": "motion"}]
            if serials == ["recording-id"] else []
        )}

    client.addx_call = addx_call
    client._get_camera_library_pages = history_pages
    client.get_camera_event_record_history = history_pages
    history_method = (
        client.get_camera_library_history_for_cameras
        if history_kind == "library"
        else client.get_camera_event_record_history_for_cameras
    )
    assert len((await history_method([camera], 1, 2))["list"]) == 1
    ticket = await client.get_camera_webrtc_ticket(camera, force_refresh=True)
    assert ticket["serialNumber"] == "live-id"
    history_calls.clear()
    assert len((await history_method([camera], 2, 3))["list"]) == 1
    assert history_calls == [["recording-id"]]
