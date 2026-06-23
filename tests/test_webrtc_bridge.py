from types import SimpleNamespace

from custom_components.xsense import webrtc_bridge


def entity(data=None):
    return SimpleNamespace(
        sn="SSC0ATEST",
        data=data or {
            "cameraModel": "SSC0A",
            "liveResolution": "1920x1080",
        },
    )


async def test_bridge_stream_source_posts_ticket_and_returns_stream_url(monkeypatch):
    camera = entity()
    ticket = {
        "signalServer": "wss://signal.example",
        "groupId": "group",
        "role": "viewer",
        "id": "client",
        "traceId": "trace",
        "sign": "signed",
        "time": 123,
        "expirationTime": 9999999999999,
        "iceServer": [],
    }
    calls = []

    class XSense:
        async def get_camera_webrtc_ticket(self, camera_entity, *, force_refresh):
            assert camera_entity is camera
            assert force_refresh is True
            return ticket

    class Response:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def json(self):
            return {"streamUrl": "rtsp://127.0.0.1:39091/xsense/SSC0ATEST"}

    class Session:
        def post(self, url, *, json, timeout):
            calls.append({"url": url, "json": json, "timeout": timeout})
            return Response()

    monkeypatch.setattr(
        webrtc_bridge, "async_get_clientsession", lambda hass: Session()
    )

    source = await webrtc_bridge.async_get_xsense_bridge_stream_source(
        SimpleNamespace(),
        SimpleNamespace(xsense=XSense()),
        camera,
        bridge_url="http://127.0.0.1:39091/",
    )

    assert source == "rtsp://127.0.0.1:39091/xsense/SSC0ATEST"
    assert calls[0]["url"] == "http://127.0.0.1:39091/api/xsense/sessions"
    assert calls[0]["json"]["camera"] == {
        "serialNumber": "SSC0ATEST",
        "resolution": "1920x1080",
        "model": "SSC0A",
    }
    assert calls[0]["json"]["debug"] is True
    assert calls[0]["json"]["ticket"] is ticket


async def test_bridge_stream_source_rejects_missing_ticket():
    class XSense:
        async def get_camera_webrtc_ticket(self, camera_entity, *, force_refresh):
            return None

    source = await webrtc_bridge.async_get_xsense_bridge_stream_source(
        SimpleNamespace(),
        SimpleNamespace(xsense=XSense()),
        entity(),
    )

    assert source is None
