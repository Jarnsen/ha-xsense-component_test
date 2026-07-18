"""HTTP views for the X-Sense recordings sidebar panel."""

from __future__ import annotations

import asyncio
import secrets
from datetime import datetime
from pathlib import Path
from time import monotonic
from typing import Any
from urllib.parse import quote

from aiohttp import web
from homeassistant.components import http
from homeassistant.core import HomeAssistant

from .const import (
    CONF_RECORDING_MEDIA_CLIPS_ORDER,
    CONF_RECORDING_MEDIA_DAYS_ORDER,
    DEFAULT_RECORDING_MEDIA_CLIPS_ORDER,
    DEFAULT_RECORDING_MEDIA_DAYS_ORDER,
    DOMAIN,
    LOGGER,
)
from .media_source import (
    HLS_MIME_TYPE,
    XSenseRecordingsMediaSource,
    _clip_cache_path,
    _clip_media_playable,
    _clip_start_for_sort,
    _clip_thumbnail_cache_path,
    _hls_playlist_cache_path,
    _hls_ready,
    _local_media_url,
    _mp4_ready,
    _path_ready,
    _recording_media_root,
    _recording_media_sync_enabled,
    _sort_descending,
    _unlink_missing_ok,
)

HLS_SEGMENT_TOKEN_TTL = 3600
HLS_SEGMENT_WAIT_TIMEOUT = 10
HLS_SEGMENT_WAIT_INTERVAL = 0.25


async def async_register_recordings_http_views(hass: HomeAssistant) -> None:
    """Register X-Sense recordings panel API routes once."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get("_recordings_http_views_registered"):
        return
    hass.http.register_view(XSenseRecordingsPanelDataView(hass))
    hass.http.register_view(XSenseRecordingsPanelDebugView(hass))
    hass.http.register_view(XSenseRecordingsPanelPlaybackView(hass))
    hass.http.register_view(XSenseRecordingsPanelThumbnailView(hass))
    hass.http.register_view(XSenseRecordingsHlsSegmentView(hass))
    domain_data["_recordings_http_views_registered"] = True


async def async_build_panel_data(hass: HomeAssistant) -> dict[str, Any]:
    """Build sidebar panel data from the X-Sense recording index."""
    source = XSenseRecordingsMediaSource(hass)
    index = await source._async_load_index()
    return await _async_build_panel_data_from_index(hass, source, index)


async def _async_build_panel_data_from_index(
    hass: HomeAssistant,
    source: XSenseRecordingsMediaSource,
    index: dict[str, Any],
) -> dict[str, Any]:
    """Build cache-backed panel data without blocking the event loop."""
    cameras: list[dict[str, Any]] = []
    stats = _empty_stats(hass)
    for camera in index.get("cameras", []):
        entry_id = str(camera.get("entry_id") or "")
        serial = str(camera.get("serial") or "")
        if not entry_id or not serial:
            continue
        stats["total_cameras"] += 1
        if camera.get("online"):
            stats["online_cameras"] += 1

        clips = []
        dates: set[str] = set()
        camera_stats = {
            "entry_id": entry_id,
            "serial": serial,
            "name": str(camera.get("name") or serial),
            "indexed_clips": 0,
            "cached_videos": 0,
            "cached_thumbnails": 0,
            "ready_clips": 0,
            "pending_clips": 0,
            "video_bytes": 0,
            "thumbnail_bytes": 0,
        }
        media_root = _recording_media_root(hass, entry_id)
        stats["media_roots"].add(media_root.as_posix())
        sync_enabled = _recording_media_sync_enabled(hass, entry_id)
        for clip in camera.get("clips", []):
            if not isinstance(clip, dict):
                continue
            start = _clip_start_for_sort(clip)
            end = _clip_end_for_panel(clip, start)
            clip_date = str(clip.get("date") or "")
            if not start or not end or not clip_date:
                continue
            stats["indexed_clips"] += 1
            camera_stats["indexed_clips"] += 1
            clip_path = _clip_cache_path(clip)
            thumb_path = _clip_thumbnail_cache_path(clip)
            mp4_cached = await source._async_mp4_ready(clip_path)
            hls_cached = await source._async_hls_ready(clip)
            if hls_cached and mp4_cached:
                await source._async_cleanup_legacy_mp4_cache(clip)
                mp4_cached = False
            clip_cached = mp4_cached or hls_cached
            thumb_cached = await source._async_path_ready(thumb_path)
            if clip_cached:
                stats["cached_videos"] += 1
                camera_stats["cached_videos"] += 1
                if hls_cached:
                    camera_stats["video_bytes"] += await source._async_file_job(
                        _directory_size,
                        _hls_playlist_cache_path(clip).parent,
                    )
                elif mp4_cached:
                    camera_stats["video_bytes"] += await source._async_file_size(
                        clip_path
                    )
            if thumb_cached:
                stats["cached_thumbnails"] += 1
                camera_stats["cached_thumbnails"] += 1
                camera_stats["thumbnail_bytes"] += await source._async_file_size(
                    thumb_path
                )
            playable = _clip_media_playable(clip)
            ready = playable and clip_cached
            if ready:
                stats["ready_clips"] += 1
                camera_stats["ready_clips"] += 1
            if not playable:
                continue
            if sync_enabled and not clip_cached:
                continue

            dates.add(clip_date)
            stats["visible_clips"] += 1
            _update_latest_clip(
                stats,
                entry_id,
                serial,
                str(camera.get("name") or serial),
                start,
                end,
            )
            clips.append(
                {
                    "entry_id": entry_id,
                    "serial": serial,
                    "date": clip_date,
                    "start": start,
                    "end": end,
                    "duration": max(0, end - start),
                    "title": str(clip.get("title") or _clip_title(start, end)),
                    "cached": clip_cached,
                    "thumbnail_cached": thumb_cached,
                    "playable": playable,
                    "sync_enabled": sync_enabled,
                    "playback_url": _playback_api_url(entry_id, serial, start, end)
                    if hls_cached
                    else _local_media_url(clip_path)
                    if mp4_cached
                    else _playback_api_url(entry_id, serial, start, end),
                    "thumbnail_url": _panel_thumbnail_url(
                        clip,
                        thumb_path,
                        thumb_cached,
                        entry_id,
                        serial,
                        start,
                        end,
                    ),
                }
            )
        camera_stats["pending_clips"] = max(
            0,
            len(clips) - camera_stats["ready_clips"],
        )
        stats["pending_clips"] += camera_stats["pending_clips"]
        stats["video_bytes"] += camera_stats["video_bytes"]
        stats["thumbnail_bytes"] += camera_stats["thumbnail_bytes"]
        stats["camera_stats"].append(camera_stats)
        clips.sort(
            key=lambda item: int(item["start"]),
            reverse=_sort_descending(
                hass,
                entry_id,
                CONF_RECORDING_MEDIA_CLIPS_ORDER,
                DEFAULT_RECORDING_MEDIA_CLIPS_ORDER,
            ),
        )
        cameras.append(
            {
                "entry_id": entry_id,
                "serial": serial,
                "name": str(camera.get("name") or serial),
                "online": bool(camera.get("online")),
                "dates": sorted(
                    dates,
                    reverse=_sort_descending(
                        hass,
                        entry_id,
                        CONF_RECORDING_MEDIA_DAYS_ORDER,
                        DEFAULT_RECORDING_MEDIA_DAYS_ORDER,
                    ),
                ),
                "clips": clips,
            }
        )
    stats["total_bytes"] = stats["video_bytes"] + stats["thumbnail_bytes"]
    stats["media_roots"] = sorted(stats["media_roots"])
    stats["cache_only"] = any(
        _recording_media_sync_enabled(hass, str(camera.get("entry_id") or ""))
        for camera in index.get("cameras", [])
        if isinstance(camera, dict)
    )
    return {
        "title": "X-Sense Recordings",
        "generated_at": index.get("generated_at"),
        "warning": index.get("warning"),
        "stats": stats,
        "cameras": cameras,
    }


def build_panel_data(hass: HomeAssistant, index: dict[str, Any]) -> dict[str, Any]:
    """Build cache-backed panel data from the recording index."""
    cameras: list[dict[str, Any]] = []
    stats = _empty_stats(hass)
    for camera in index.get("cameras", []):
        entry_id = str(camera.get("entry_id") or "")
        serial = str(camera.get("serial") or "")
        if not entry_id or not serial:
            continue
        stats["total_cameras"] += 1
        if camera.get("online"):
            stats["online_cameras"] += 1

        clips = []
        dates: set[str] = set()
        camera_stats = {
            "entry_id": entry_id,
            "serial": serial,
            "name": str(camera.get("name") or serial),
            "indexed_clips": 0,
            "cached_videos": 0,
            "cached_thumbnails": 0,
            "ready_clips": 0,
            "pending_clips": 0,
            "video_bytes": 0,
            "thumbnail_bytes": 0,
        }
        media_root = _recording_media_root(hass, entry_id)
        stats["media_roots"].add(media_root.as_posix())
        sync_enabled = _recording_media_sync_enabled(hass, entry_id)
        for clip in camera.get("clips", []):
            if not isinstance(clip, dict):
                continue
            start = _clip_start_for_sort(clip)
            end = _clip_end_for_panel(clip, start)
            clip_date = str(clip.get("date") or "")
            if not start or not end or not clip_date:
                continue
            stats["indexed_clips"] += 1
            camera_stats["indexed_clips"] += 1
            clip_path = _clip_cache_path(clip)
            thumb_path = _clip_thumbnail_cache_path(clip)
            mp4_cached = _mp4_ready(clip_path)
            hls_cached = _hls_ready(clip)
            clip_cached = mp4_cached or hls_cached
            thumb_cached = _path_ready(thumb_path)
            if clip_cached:
                stats["cached_videos"] += 1
                camera_stats["cached_videos"] += 1
                if hls_cached:
                    camera_stats["video_bytes"] += _directory_size(
                        _hls_playlist_cache_path(clip).parent
                    )
                elif mp4_cached:
                    camera_stats["video_bytes"] += _file_size(clip_path)
            if thumb_cached:
                stats["cached_thumbnails"] += 1
                camera_stats["cached_thumbnails"] += 1
                camera_stats["thumbnail_bytes"] += _file_size(thumb_path)
            playable = _clip_media_playable(clip)
            ready = playable and clip_cached
            if ready:
                stats["ready_clips"] += 1
                camera_stats["ready_clips"] += 1
            if not playable:
                continue
            if sync_enabled and not clip_cached:
                continue

            dates.add(clip_date)
            stats["visible_clips"] += 1
            _update_latest_clip(stats, entry_id, serial, str(camera.get("name") or serial), start, end)
            clips.append(
                {
                    "entry_id": entry_id,
                    "serial": serial,
                    "date": clip_date,
                    "start": start,
                    "end": end,
                    "duration": max(0, end - start),
                    "title": str(clip.get("title") or _clip_title(start, end)),
                    "cached": clip_cached,
                    "thumbnail_cached": thumb_cached,
                    "playable": playable,
                    "sync_enabled": sync_enabled,
                    "playback_url": _playback_api_url(entry_id, serial, start, end)
                    if hls_cached
                    else _local_media_url(clip_path)
                    if mp4_cached
                    else _playback_api_url(entry_id, serial, start, end),
                    "thumbnail_url": _panel_thumbnail_url(
                        clip,
                        thumb_path,
                        thumb_cached,
                        entry_id,
                        serial,
                        start,
                        end,
                    ),
                }
            )
        camera_stats["pending_clips"] = max(
            0,
            len(clips) - camera_stats["ready_clips"],
        )
        stats["pending_clips"] += camera_stats["pending_clips"]
        stats["video_bytes"] += camera_stats["video_bytes"]
        stats["thumbnail_bytes"] += camera_stats["thumbnail_bytes"]
        stats["camera_stats"].append(camera_stats)
        clips.sort(
            key=lambda item: int(item["start"]),
            reverse=_sort_descending(
                hass,
                entry_id,
                CONF_RECORDING_MEDIA_CLIPS_ORDER,
                DEFAULT_RECORDING_MEDIA_CLIPS_ORDER,
            ),
        )
        cameras.append(
            {
                "entry_id": entry_id,
                "serial": serial,
                "name": str(camera.get("name") or serial),
                "online": bool(camera.get("online")),
                "dates": sorted(
                    dates,
                    reverse=_sort_descending(
                        hass,
                        entry_id,
                        CONF_RECORDING_MEDIA_DAYS_ORDER,
                        DEFAULT_RECORDING_MEDIA_DAYS_ORDER,
                    ),
                ),
                "clips": clips,
            }
        )
    stats["total_bytes"] = stats["video_bytes"] + stats["thumbnail_bytes"]
    stats["media_roots"] = sorted(stats["media_roots"])
    stats["cache_only"] = any(
        _recording_media_sync_enabled(hass, str(camera.get("entry_id") or ""))
        for camera in index.get("cameras", [])
        if isinstance(camera, dict)
    )
    return {
        "title": "X-Sense Recordings",
        "generated_at": index.get("generated_at"),
        "warning": index.get("warning"),
        "stats": stats,
        "cameras": cameras,
    }


class XSenseRecordingsPanelDataView(http.HomeAssistantView):
    """Serve cache-backed data for the X-Sense Recordings panel."""

    url = f"/api/{DOMAIN}/recordings/panel"
    name = f"api:{DOMAIN}:recordings:panel"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the panel data view."""
        self.hass = hass

    async def get(self, request: web.Request) -> web.Response:
        """Return panel data."""
        data = await async_build_panel_data(self.hass)
        LOGGER.debug(
            "X-Sense recordings panel data served: %s",
            {
                "cameras": len(data.get("cameras", [])),
                "visible_clips": data.get("stats", {}).get("visible_clips"),
                "ready_clips": data.get("stats", {}).get("ready_clips"),
                "pending_clips": data.get("stats", {}).get("pending_clips"),
                "cache_only": data.get("stats", {}).get("cache_only"),
            },
        )
        return web.json_response(data)


class XSenseRecordingsPanelDebugView(http.HomeAssistantView):
    """Receive frontend playback diagnostics from the recordings panel."""

    url = f"/api/{DOMAIN}/recordings/panel/debug"
    name = f"api:{DOMAIN}:recordings:panel:debug"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the panel debug view."""
        self.hass = hass

    async def post(self, request: web.Request) -> web.Response:
        """Log one recordings panel frontend diagnostic event."""
        try:
            payload = await request.json()
        except Exception as exc:  # noqa: BLE001
            raise web.HTTPBadRequest(reason="Invalid X-Sense panel debug payload") from exc
        if not isinstance(payload, dict):
            raise web.HTTPBadRequest(reason="Invalid X-Sense panel debug payload")

        LOGGER.debug(
            "X-Sense recordings panel frontend event: %s",
            {
                "event": str(payload.get("event") or "unknown")[:80],
                "entry_id": str(payload.get("entry_id") or "")[:32],
                "camera": _short_serial(payload.get("serial")),
                "start": _safe_int(payload.get("start")),
                "end": _safe_int(payload.get("end")),
                "cached": _safe_bool(payload.get("cached")),
                "playback_url_kind": _url_kind(payload.get("playback_url")),
                "status": _safe_int(payload.get("status")),
                "ok": _safe_bool(payload.get("ok")),
                "bytes": _safe_int(payload.get("bytes")),
                "content_type": str(payload.get("content_type") or "")[:80],
                "blob_type": str(payload.get("blob_type") or "")[:80],
                "elapsed_ms": _safe_int(payload.get("elapsed_ms")),
                "duration_ms": _safe_int(payload.get("duration")),
                "ready_state": _safe_int(payload.get("ready_state")),
                "network_state": _safe_int(payload.get("network_state")),
                "error_code": _safe_int(payload.get("error_code")),
                "message": str(payload.get("message") or "")[:240],
                "hls_type": str(payload.get("type") or "")[:80],
                "hls_details": str(payload.get("details") or "")[:160],
                "hls_fatal": _safe_bool(payload.get("fatal")),
            },
        )
        return web.json_response({"ok": True})


class XSenseRecordingsPanelPlaybackView(http.HomeAssistantView):
    """Resolve and redirect one X-Sense recording for the sidebar player."""

    url = f"/api/{DOMAIN}/recordings/play/{{entry_id}}/{{start}}/{{end}}"
    name = f"api:{DOMAIN}:recordings:play"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the playback view."""
        self.hass = hass

    async def get(
        self,
        request: web.Request,
        entry_id: str,
        start: str,
        end: str,
    ) -> web.Response:
        """Return a redirect to a cached or direct recording URL."""
        serial = str(request.query.get("serial") or "")
        if not serial:
            raise web.HTTPBadRequest(reason="Missing X-Sense camera serial")
        clip = await self._clip(entry_id, serial, start, end)
        started_at = monotonic()
        source = XSenseRecordingsMediaSource(self.hass)
        cached = await source._async_cached_media_ready(clip)
        context = {
            **_clip_debug_context(entry_id, serial, start, end),
            "source": clip.get("source"),
            "quality": clip.get("quality"),
            "cached": cached,
            "format": await source._async_cached_media_format(clip),
        }
        LOGGER.debug("X-Sense recordings panel playback requested: %s", context)
        if _recording_media_sync_enabled(self.hass, entry_id) and not cached:
            LOGGER.debug(
                "X-Sense recordings panel playback waiting for sync: %s",
                _clip_debug_context(entry_id, serial, start, end),
            )
            raise web.HTTPNotFound(reason="X-Sense recording is waiting for sync")
        try:
            url = await source._async_cached_playback_url(clip)
        except Exception as exc:  # noqa: BLE001
            LOGGER.debug(
                "X-Sense recordings panel playback cache failed: %s",
                {**_clip_debug_context(entry_id, serial, start, end), "error": str(exc)},
            )
            raise web.HTTPNotFound(reason="X-Sense recording is not ready") from exc
        output_path = _clip_cache_path(clip)
        if await source._async_hls_ready(clip):
            playlist_path = _hls_playlist_cache_path(clip)
            token = _create_hls_segment_token(self.hass, playlist_path.parent)
            playlist = await source._async_file_job(
                _hls_playlist_for_response,
                playlist_path,
                f"/api/{DOMAIN}/recordings/hls/{token}",
            )
            LOGGER.debug(
                "X-Sense recordings panel playback served cached HLS: %s",
                {
                    **context,
                    "elapsed_ms": int((monotonic() - started_at) * 1000),
                    "content_type": HLS_MIME_TYPE,
                },
            )
            return web.Response(
                text=playlist,
                content_type=HLS_MIME_TYPE,
                headers={"Cache-Control": "private, max-age=300"},
            )
        if await source._async_mp4_ready(output_path):
            output_bytes = await source._async_file_size(output_path)
            LOGGER.debug(
                "X-Sense recordings panel playback served cached file: %s",
                {
                    **context,
                    "elapsed_ms": int((monotonic() - started_at) * 1000),
                    "bytes": output_bytes,
                },
            )
            return web.FileResponse(
                output_path,
                headers={"Cache-Control": "private, max-age=3600"},
            )
        if not url:
            LOGGER.debug(
                "X-Sense recordings panel playback missing media URL: %s",
                _clip_debug_context(entry_id, serial, start, end),
            )
            raise web.HTTPNotFound(reason="X-Sense recording is not ready")
        LOGGER.debug(
            "X-Sense recordings panel playback did not produce cached media: %s",
            {
                **context,
                "elapsed_ms": int((monotonic() - started_at) * 1000),
            },
        )
        raise web.HTTPNotFound(reason="X-Sense recording is not ready")

    async def _clip(
        self,
        entry_id: str,
        serial: str,
        start: str,
        end: str,
    ) -> dict[str, Any]:
        try:
            start_int = int(start)
            end_int = int(end)
        except ValueError as exc:
            raise web.HTTPBadRequest(reason="Invalid recording time") from exc
        source = XSenseRecordingsMediaSource(self.hass)
        index = await source._async_load_index()
        camera = source._find_camera(index, entry_id, serial)
        if camera is None:
            raise web.HTTPNotFound(reason="X-Sense recording camera is not ready")
        clip = source._find_clip(camera, start_int)
        if clip is None:
            raise web.HTTPNotFound(reason="X-Sense recording is not ready")
        clip_end = _clip_end_for_panel(clip, start_int)
        if clip_end != end_int:
            raise web.HTTPNotFound(reason="X-Sense recording time does not match")
        return clip


class XSenseRecordingsHlsSegmentView(http.HomeAssistantView):
    """Serve token-scoped cached HLS segments for the recordings player."""

    url = f"/api/{DOMAIN}/recordings/hls/{{token}}/{{filename:.+}}"
    name = f"api:{DOMAIN}:recordings:hls"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the HLS segment view."""
        self.hass = hass

    async def get(
        self,
        request: web.Request,
        token: str,
        filename: str,
    ) -> web.Response:
        """Return one token-scoped HLS segment, map, key, or child playlist."""
        root = _hls_segment_root(self.hass, token)
        if root is None:
            raise web.HTTPNotFound(reason="X-Sense HLS recording token expired")
        path = (root / filename).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError as exc:
            raise web.HTTPNotFound(reason="Invalid X-Sense HLS segment") from exc
        source = XSenseRecordingsMediaSource(self.hass)
        waited_ms = await _async_wait_for_hls_path(source, path)
        if waited_ms is None:
            LOGGER.debug(
                "X-Sense recordings HLS segment not ready after wait: %s",
                {"filename": filename, "wait_timeout_s": HLS_SEGMENT_WAIT_TIMEOUT},
            )
            raise web.HTTPNotFound(reason="X-Sense HLS segment is not ready")
        headers = {"Cache-Control": "private, max-age=3600"}
        if path.suffix.lower() in {".m3u8", ".m3u"}:
            parent = Path(filename).parent.as_posix()
            segment_base = f"/api/{DOMAIN}/recordings/hls/{token}"
            if parent and parent != ".":
                segment_base = f"{segment_base}/{parent}"
            playlist = await source._async_file_job(
                _hls_playlist_for_response,
                path,
                segment_base,
            )
            return web.Response(
                text=playlist,
                content_type=HLS_MIME_TYPE,
                headers=headers,
            )
        size = await source._async_file_size(path)
        LOGGER.debug(
            "X-Sense recordings HLS segment served: %s",
            {
                "filename": filename,
                "bytes": size,
                "waited_ms": waited_ms,
            },
        )
        return web.FileResponse(path, headers=headers)


class XSenseRecordingsPanelThumbnailView(http.HomeAssistantView):
    """Serve X-Sense recording thumbnails for the sidebar panel."""

    url = f"/api/{DOMAIN}/recordings/thumb/{{entry_id}}/{{start}}/{{end}}"
    name = f"api:{DOMAIN}:recordings:thumb"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the thumbnail view."""
        self.hass = hass

    async def get(
        self,
        request: web.Request,
        entry_id: str,
        start: str,
        end: str,
    ) -> web.Response:
        """Return a cached thumbnail or redirect to the direct thumbnail."""
        serial = str(request.query.get("serial") or "")
        if not serial:
            raise web.HTTPBadRequest(reason="Missing X-Sense camera serial")
        clip = await XSenseRecordingsPanelPlaybackView(
            self.hass
        )._clip(entry_id, serial, start, end)
        output_path = _clip_thumbnail_cache_path(clip)
        source = XSenseRecordingsMediaSource(self.hass)
        if not await source._async_path_ready(output_path):
            try:
                await source._async_cache_thumbnail(clip)
            except Exception:  # noqa: BLE001
                pass
        if await source._async_path_ready(output_path):
            LOGGER.debug(
                "X-Sense recordings panel thumbnail served cached file: %s",
                _clip_debug_context(entry_id, serial, start, end),
            )
            return web.FileResponse(
                output_path,
                headers={"Cache-Control": "private, max-age=3600"},
            )
        LOGGER.debug(
            "X-Sense recordings panel thumbnail not ready: %s",
            _clip_debug_context(entry_id, serial, start, end),
        )
        raise web.HTTPNotFound(reason="X-Sense recording thumbnail is not ready")


def _empty_stats(hass: HomeAssistant) -> dict[str, Any]:
    return {
        "indexed_clips": 0,
        "cached_videos": 0,
        "cached_thumbnails": 0,
        "ready_clips": 0,
        "pending_clips": 0,
        "visible_clips": 0,
        "total_cameras": 0,
        "online_cameras": 0,
        "latest_clip": None,
        "video_bytes": 0,
        "thumbnail_bytes": 0,
        "total_bytes": 0,
        "media_roots": set(),
        "camera_stats": [],
        "cache_only": False,
    }


def _update_latest_clip(
    stats: dict[str, Any],
    entry_id: str,
    serial: str,
    camera_name: str,
    start: int,
    end: int,
) -> None:
    latest = stats.get("latest_clip")
    if isinstance(latest, dict) and int(latest.get("start") or 0) >= start:
        return
    stats["latest_clip"] = {
        "entry_id": entry_id,
        "serial": serial,
        "camera_name": camera_name,
        "start": start,
        "end": end,
        "duration": max(0, end - start),
    }


def _clip_end_for_panel(clip: dict[str, Any], start: int) -> int:
    try:
        return int(clip.get("end") or clip.get("start") or start)
    except (TypeError, ValueError):
        return start


def _playback_api_url(
    entry_id: str,
    serial: str,
    start: int,
    end: int,
) -> str:
    return (
        f"/api/{DOMAIN}/recordings/play/"
        f"{quote(entry_id, safe='')}/{start}/{end}?serial={quote(serial, safe='')}"
    )


def _thumbnail_api_url(entry_id: str, serial: str, start: int, end: int) -> str:
    return (
        f"/api/{DOMAIN}/recordings/thumb/"
        f"{quote(entry_id, safe='')}/{start}/{end}?serial={quote(serial, safe='')}"
    )


def _panel_thumbnail_url(
    clip: dict[str, Any],
    thumb_path: Path,
    thumb_cached: bool,
    entry_id: str,
    serial: str,
    start: int,
    end: int,
) -> str:
    if thumb_cached:
        return _local_media_url(thumb_path)
    if clip.get("thumbnail_url"):
        return _thumbnail_api_url(entry_id, serial, start, end)
    return ""


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _directory_size(path: Path) -> int:
    """Return the total size of cached files under a directory."""
    try:
        paths = list(path.rglob("*"))
    except OSError:
        return 0
    total = 0
    for child in paths:
        if child.is_file():
            total += _file_size(child)
    return total


def _create_hls_segment_token(hass: HomeAssistant, root: Path) -> str:
    """Create a short-lived token for cached HLS segment playback."""
    tokens = hass.data.setdefault(DOMAIN, {}).setdefault("_recording_hls_tokens", {})
    now = monotonic()
    for token, data in list(tokens.items()):
        if float(data.get("expires", 0)) <= now:
            tokens.pop(token, None)
    token = secrets.token_urlsafe(24)
    tokens[token] = {
        "root": root.resolve(),
        "expires": now + HLS_SEGMENT_TOKEN_TTL,
    }
    return token


async def _async_wait_for_hls_path(
    source: XSenseRecordingsMediaSource,
    path: Path,
) -> int | None:
    """Wait briefly for the progressive HLS cache to produce a requested path."""
    started_at = monotonic()
    deadline = monotonic() + HLS_SEGMENT_WAIT_TIMEOUT
    while True:
        if await source._async_path_ready(path):
            return int((monotonic() - started_at) * 1000)
        if monotonic() >= deadline:
            return None
        await asyncio.sleep(HLS_SEGMENT_WAIT_INTERVAL)


def _hls_segment_root(hass: HomeAssistant, token: str) -> Path | None:
    """Return a token-scoped HLS root when the token is still valid."""
    tokens = hass.data.setdefault(DOMAIN, {}).setdefault("_recording_hls_tokens", {})
    data = tokens.get(token)
    if not isinstance(data, dict):
        return None
    if float(data.get("expires", 0)) <= monotonic():
        tokens.pop(token, None)
        return None
    root = data.get("root")
    return root if isinstance(root, Path) else None


def _hls_playlist_for_response(playlist_path: Path, segment_base_url: str) -> str:
    """Return a cached HLS playlist rewritten to tokenized segment URLs."""
    base = segment_base_url.rstrip("/")
    rewritten = []
    for line in playlist_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            rewritten.append(line)
            continue
        rewritten.append(f"{base}/{quote(stripped, safe='/')}")
    return "\n".join(rewritten) + "\n"


def _clip_debug_context(
    entry_id: str,
    serial: str,
    start: str | int,
    end: str | int,
) -> dict[str, Any]:
    return {
        "entry_id": entry_id,
        "camera": _short_serial(serial),
        "start": start,
        "end": end,
    }


def _short_serial(value: Any) -> str:
    text = str(value or "")
    if len(text) <= 6:
        return text
    return f"...{text[-6:]}"


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return None
    return bool(value)


def _url_kind(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    if text.startswith("/api/"):
        return "api"
    if text.startswith("/media/local/"):
        return "local_media"
    if text.startswith("/xsense-recordings"):
        return "panel"
    if text.startswith(("http://", "https://")):
        return "external"
    return "other"


def _clip_title(start: int, end: int) -> str:
    return f"{datetime.fromtimestamp(start):%H:%M:%S} - {datetime.fromtimestamp(end):%H:%M:%S}"
