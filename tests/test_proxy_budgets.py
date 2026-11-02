"""Bound recording resource reads without changing playback bytes."""

import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from custom_components.xsense import http


class Response:
    def __init__(self, chunks, length=None):
        self.chunks = chunks
        self.content_length = length
        self.headers = {"content-type": "video/mp2t"}
        self.url = "https://media.invalid/clip.ts"
        self.content = self
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.closed = True

    def raise_for_status(self):
        pass

    async def iter_chunked(self, size):
        for chunk in self.chunks:
            yield chunk


@pytest.mark.asyncio
@pytest.mark.parametrize("length,chunks", [(9, [b"123"]), (None, [b"123", b"456"])])
async def test_proxy_rejects_declared_or_streamed_oversize(monkeypatch, length, chunks):
    response = Response(chunks, length)
    monkeypatch.setattr(http, "PROXY_RESOURCE_MAX_BYTES", 5)
    monkeypatch.setattr(
        http,
        "async_get_clientsession",
        lambda hass: SimpleNamespace(get=lambda url: response),
    )
    with pytest.raises(RuntimeError, match="size limit"):
        await http._async_fetch_proxy_resource(SimpleNamespace(data={}), response.url)
    assert response.closed


@pytest.mark.asyncio
async def test_proxy_preserves_audio_video_bytes(monkeypatch):
    response = Response([b"video", b"audio"])
    monkeypatch.setattr(
        http,
        "async_get_clientsession",
        lambda hass: SimpleNamespace(get=lambda url: response),
    )
    assert await http._async_fetch_proxy_resource(
        SimpleNamespace(data={}), response.url
    ) == (b"videoaudio", "video/mp2t", response.url)
    assert response.closed


@pytest.mark.asyncio
async def test_proxy_cancel_releases_response_and_slot(monkeypatch):
    started = asyncio.Event()
    response = Response([])

    async def blocked(size):
        started.set()
        await asyncio.Event().wait()
        yield b"never"

    response.iter_chunked = blocked
    monkeypatch.setattr(
        http,
        "async_get_clientsession",
        lambda hass: SimpleNamespace(get=lambda url: response),
    )
    hass = SimpleNamespace(data={})
    task = asyncio.create_task(http._async_fetch_proxy_resource(hass, response.url))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert response.closed
    limiter = hass.data[http.DOMAIN]["_recording_proxy_limiter"]
    assert limiter._value == http.PROXY_RESOURCE_CONCURRENCY


@pytest.mark.asyncio
async def test_proxy_timeout_includes_waiting_for_slot(monkeypatch):
    monkeypatch.setattr(http, "PROXY_RESOURCE_TIMEOUT_SECONDS", 0.01)
    get = Mock()
    monkeypatch.setattr(
        http, "async_get_clientsession", lambda hass: SimpleNamespace(get=get)
    )
    hass = SimpleNamespace(
        data={http.DOMAIN: {"_recording_proxy_limiter": asyncio.Semaphore(0)}}
    )
    with pytest.raises(TimeoutError):
        await http._async_fetch_proxy_resource(hass, "https://media.invalid/clip.ts")
    get.assert_not_called()
