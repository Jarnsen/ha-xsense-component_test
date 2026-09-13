"""Exercise the camera adapter and real signal reader across a delayed answer."""

import asyncio
import base64
import importlib
import json
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import aiohttp
import pytest
from homeassistant.components.camera import Camera


@pytest.mark.parametrize("close_requested", [False, True, "task"])
async def test_pending_offer_survives_until_answer_or_explicit_close(monkeypatch, caplog, close_requested):
    caplog.set_level(logging.DEBUG, logger="custom_components.xsense")
    camera_module = importlib.import_module("custom_components.xsense.camera")
    messages = []
    frames = asyncio.Queue()
    offer_sent = asyncio.Event()
    sent = []

    class Socket:
        closed = False
        close_code = None

        def __aiter__(self):
            return self

        async def __anext__(self):
            frame = await frames.get()
            if frame is None:
                raise StopAsyncIteration
            return SimpleNamespace(type=aiohttp.WSMsgType.TEXT, data=json.dumps(frame))

        async def send_str(self, data):
            sent.append(json.loads(data))
            offer_sent.set()

        async def close(self):
            self.closed = True
            frames.put_nowait(None)

    socket = Socket()
    client = SimpleNamespace(ws_connect=AsyncMock(return_value=socket))
    monkeypatch.setattr(camera_module, "async_get_clientsession", lambda hass: client)
    entity = SimpleNamespace(
        type="SSC0A", sn="CAMERA_A", online=True,
        data={"streamProtocol": "webrtc", "resolution": "1920x1080"},
    )
    ticket = {
        "serialNumber": "CAMERA_A", "signalServer": "https://signal.example",
        "groupId": "CAMERA_A", "role": "viewer", "id": "viewer",
        "traceId": "trace", "sign": "private", "time": 1,
        "expirationTime": 9999999999999,
    }
    camera = object.__new__(camera_module.XSenseWebRTCCameraEntity)
    Camera.__init__(camera)
    camera._current_entity = lambda: entity
    camera.coordinator = SimpleNamespace(
        xsense=SimpleNamespace(get_camera_webrtc_ticket=AsyncMock(return_value=ticket)),
    )
    cleanup_tasks = []

    def create_task(coro):
        task = asyncio.create_task(coro)
        cleanup_tasks.append(task)
        return task

    async def import_job(func, name):
        return func(name)

    camera.hass = SimpleNamespace(
        async_add_import_executor_job=import_job, async_create_task=create_task,
    )
    camera._webrtc_sessions = {}
    camera._pending_webrtc_candidates = {}
    offer = "v=0\r\nm=video 9 UDP/TLS/RTP/SAVPF 96\r\na=mid:0\r\na=recvonly\r\na=rtpmap:96 H264/90000\r\n"
    task = asyncio.create_task(camera.async_handle_async_webrtc_offer(offer, "test-session", messages.append))
    try:
        frames.put_nowait({"messageType": "PEER_IN", "messagePayload": {"id": "CAMERA_A"}})
        await asyncio.wait_for(offer_sent.wait(), 2)
        assert sent[0]["messageType"] == "SDP_OFFER"
        # Real elapsed time crosses the reported 3-6 second cleanup interval.
        await asyncio.sleep(6.2)
        assert not task.done()
        assert not socket.closed
        assert messages == []
        if close_requested:
            if close_requested == "task":
                task.cancel()
            else:
                camera.close_webrtc_session("test-session")
            await asyncio.gather(*cleanup_tasks)
            with pytest.raises(asyncio.CancelledError):
                await task
            assert messages == []
            assert socket.closed
            reason = "offer_task_cancelled" if close_requested == "task" else "answer_wait_cancelled"
            assert f"'close_reason': '{reason}'" in caplog.text
        else:
            answer = offer.replace("recvonly", "sendonly")
            frames.put_nowait({
                "messageType": "SDP_ANSWER", "senderClientId": "CAMERA_A",
                "recipientClientId": "viewer",
                "messagePayload": base64.b64encode(json.dumps({"sdp": answer}).encode()).decode(),
            })
            await asyncio.wait_for(task, 2)
            assert len(messages) == 1
            assert messages[0].answer == answer
            assert not socket.closed
    finally:
        for session in list(camera._webrtc_sessions.values()):
            await session.close()
        task.cancel()
        await asyncio.gather(task, *cleanup_tasks, return_exceptions=True)
