"""Exercise pending live-view cleanup with the real signal helper."""
import asyncio
from types import SimpleNamespace

import pytest
from homeassistant.components.camera import Camera

from custom_components.xsense.camera import XSenseWebRTCCameraEntity
from custom_components.xsense.python_xsense.webrtc_signal import (
    XSenseWebRTCSignalSession,
    XSenseWebRTCTicket,
)


async def test_replacement_and_late_cleanup_do_not_close_current_pending_session():
    sockets = []

    class Socket:
        closed = False
        close_code = None

        def __init__(self):
            self.stopped = asyncio.Event()

        def __aiter__(self):
            return self

        async def __anext__(self):
            await self.stopped.wait()
            raise StopAsyncIteration

        async def close(self):
            self.closed = True
            self.stopped.set()

    async def connect(*args, **kwargs):
        socket = Socket()
        sockets.append(socket)
        return socket

    ticket = XSenseWebRTCTicket.from_api("CAMERA_A", {
        "signalServer": "https://signal.example", "groupId": "group",
        "role": "viewer", "id": "viewer", "traceId": "trace",
        "sign": "test", "time": 1, "expirationTime": 9999999999999,
    })

    def new_session():
        return XSenseWebRTCSignalSession(
            session=SimpleNamespace(ws_connect=connect), ticket=ticket,
            offer_sdp="v=0\r\n", resolution="1280x720", camera_online=True,
        )

    camera = object.__new__(XSenseWebRTCCameraEntity)
    Camera.__init__(camera)
    camera._current_entity = lambda: None
    camera.coordinator = SimpleNamespace()
    close_tasks = []

    def create_task(coro):
        task = asyncio.create_task(coro)
        close_tasks.append(task)
        return task

    camera.hass = SimpleNamespace(async_create_task=create_task)
    camera._pending_webrtc_candidates = {"new": []}
    old = new_session()
    camera._webrtc_sessions = {"old": old}
    old_start = asyncio.create_task(old.start())
    await asyncio.sleep(0)
    await camera._close_existing_webrtc_sessions(preserve_pending_session_id="new")
    with pytest.raises(asyncio.CancelledError):
        await old_start
    assert sockets[0].closed

    current = new_session()
    camera._webrtc_sessions["new"] = current
    current_start = asyncio.create_task(current.start())
    try:
        await asyncio.sleep(0)
        camera.close_webrtc_session("old")
        await asyncio.sleep(0)
        assert not current_start.done()
        assert not sockets[1].closed
        assert camera._webrtc_sessions == {"new": current}
        camera.close_webrtc_session("new")
        await asyncio.gather(*close_tasks)
        with pytest.raises(asyncio.CancelledError):
            await current_start
        assert sockets[1].closed
        assert camera._webrtc_sessions == {}
    finally:
        await current.close()
        await asyncio.gather(current_start, return_exceptions=True)
