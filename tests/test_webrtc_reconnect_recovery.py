"""Replay the peer-out/socket-reconnect/answer order observed in #182."""
import asyncio
import base64
import json
from types import SimpleNamespace

import aiohttp

from custom_components.xsense.python_xsense import webrtc_signal


async def test_real_reader_recovers_after_peer_out_and_socket_close(monkeypatch):
    monkeypatch.setattr(webrtc_signal, "_SIGNAL_RECONNECT_DELAY", 0)
    sockets = []
    connected = asyncio.Queue()

    class Socket:
        closed = False
        close_code = 1006

        def __init__(self):
            self.frames = asyncio.Queue()
            self.offers = asyncio.Queue()

        def __aiter__(self):
            return self

        async def __anext__(self):
            value = await self.frames.get()
            if value is None:
                self.closed = True
                raise StopAsyncIteration
            return SimpleNamespace(type=aiohttp.WSMsgType.TEXT, data=json.dumps(value))

        async def send_str(self, value):
            await self.offers.put(json.loads(value))

        async def close(self):
            self.closed = True
            self.frames.put_nowait(None)

        def peer(self, kind):
            self.frames.put_nowait({"messageType": kind, "messagePayload": {"id": "CAMERA"}})

    async def connect(*args, **kwargs):
        socket = Socket()
        sockets.append(socket)
        connected.put_nowait(socket)
        return socket

    ticket = webrtc_signal.XSenseWebRTCTicket.from_api("CAMERA", {
        "signalServer": "wss://signal.example", "groupId": "CAMERA",
        "id": "VIEWER", "role": "viewer", "traceId": "trace",
        "sign": "test", "time": 1, "expirationTime": 9999999999999,
    })
    relay = webrtc_signal.XSenseWebRTCSignalSession(
        session=SimpleNamespace(ws_connect=connect), ticket=ticket,
        offer_sdp="v=0\r\n", resolution="1920x1080", camera_online=True,
    )
    task = asyncio.create_task(relay.start())
    try:
        first = await asyncio.wait_for(connected.get(), 2)
        first.peer("PEER_IN")
        offer = await asyncio.wait_for(first.offers.get(), 2)
        first.peer("PEER_OUT")
        first.frames.put_nowait(None)
        second = await asyncio.wait_for(connected.get(), 2)
        assert not task.done()
        assert second.offers.empty()
        second.peer("PEER_IN")
        assert await asyncio.wait_for(second.offers.get(), 2) == offer
        second.frames.put_nowait({
            "messageType": "SDP_ANSWER", "senderClientId": "CAMERA",
            "recipientClientId": "VIEWER",
            "messagePayload": base64.b64encode(json.dumps({"sdp": "v=0\r\n"}).encode()).decode(),
        })
        assert await asyncio.wait_for(task, 2) == "v=0\r\n"
        assert relay._signal_reconnect_count == 1
        assert len(sockets) == 2
    finally:
        await relay.close()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
