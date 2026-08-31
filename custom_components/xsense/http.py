"""HTTP views for the X-Sense recordings sidebar panel."""

from __future__ import annotations

import asyncio
import mimetypes
import re
import secrets
from datetime import datetime
from pathlib import Path
from time import monotonic
from typing import Any
from urllib.parse import quote, urljoin, urlparse

from aiohttp import ClientResponseError, web
from homeassistant.components import http
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import (
    CONF_RECORDING_MEDIA_CLIPS_ORDER,
    CONF_RECORDING_MEDIA_DAYS_ORDER,
    DEFAULT_RECORDING_MEDIA_CLIPS_ORDER,
    DEFAULT_RECORDING_MEDIA_DAYS_ORDER,
    DOMAIN,
    LOGGER,
    RECORDING_PLAYBACK_SESSION_TTL_SECONDS,
)
from .recordings_media import (
    HLS_MIME_TYPE,
    XSenseRecordingsMediaSource,
    _cache_group_key_for_clip,
    async_allow_recording_cache,
    async_clear_recording_caches,
    async_delete_camera_recording_cache,
    async_delete_recording_cache,
    async_recording_cache_suppressed,
    async_release_recording_playback,
    async_touch_recording_cache,
    async_schedule_temporary_recording_cleanup,
    _clip_cache_path,
    _clip_media_playable,
    _clip_start_for_sort,
    _clip_thumbnail_cache_path,
    _hls_playlist_cache_path,
    _hls_playback_fields_for_clip,
    _hls_cache_playback_ready,
    _hls_attribute_uri,
    _local_media_url,
    _is_hls_playlist_uri,
    _mp4_ready,
    _path_ready,
    _recording_media_root,
    _recording_media_root_from_value,
    _recording_cache_suppressed,
    _recording_media_sync_enabled,
    _recording_cache_retained,
    _prepare_hls_proxy_leading_segment,
    _sort_descending,
)

from .recordings_gate import has_any_camera_entities


HLS_SEGMENT_TOKEN_TTL = RECORDING_PLAYBACK_SESSION_TTL_SECONDS


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
    hass.http.register_view(XSenseRecordingsCacheManagementView(hass))
    domain_data["_recordings_http_views_registered"] = True


def _recordings_runtime_available(hass: HomeAssistant) -> bool:
    """Return whether recordings HTTP endpoints should serve data."""
    domain_data = hass.data.get(DOMAIN, {})
    if not domain_data.get("_recordings_http_views_registered"):
        return False
    return has_any_camera_entities(hass)


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
        retained_mode = _recording_cache_retained(hass, entry_id)
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
            hls_cached = await source._async_hls_cache_playback_ready(clip)
            if hls_cached and mp4_cached:
                await source._async_cleanup_legacy_mp4_cache(clip)
                mp4_cached = False
            clip_cached = mp4_cached or hls_cached
            thumb_cached = await source._async_path_ready(thumb_path)
            cache_suppressed = await async_recording_cache_suppressed(hass, clip)
            clip_video_bytes = 0
            clip_thumbnail_bytes = 0
            if clip_cached:
                stats["cached_videos"] += 1
                camera_stats["cached_videos"] += 1
                if hls_cached:
                    clip_video_bytes = await source._async_file_job(
                        _directory_size,
                        _hls_playlist_cache_path(clip).parent,
                    )
                elif mp4_cached:
                    clip_video_bytes = await source._async_file_size(clip_path)
                camera_stats["video_bytes"] += clip_video_bytes
            if thumb_cached:
                stats["cached_thumbnails"] += 1
                camera_stats["cached_thumbnails"] += 1
                clip_thumbnail_bytes = await source._async_file_size(thumb_path)
                camera_stats["thumbnail_bytes"] += clip_thumbnail_bytes
            playable = _clip_media_playable(clip)
            ready = playable and (clip_cached or not retained_mode)
            if ready:
                stats["ready_clips"] += 1
                camera_stats["ready_clips"] += 1
            if not playable:
                continue
            if sync_enabled and not clip_cached and not cache_suppressed:
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
                    "retained": retained_mode,
                    "thumbnail_cached": thumb_cached,
                    "manual_cache_deleted": cache_suppressed,
                    "cache_bytes": clip_video_bytes + clip_thumbnail_bytes,
                    "playable": playable,
                    "sync_enabled": sync_enabled,
                    **_hls_playback_fields_for_clip(clip),
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
        retained_mode = _recording_cache_retained(hass, entry_id)
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
            hls_cached = _hls_cache_playback_ready(clip)
            clip_cached = mp4_cached or hls_cached
            thumb_cached = _path_ready(thumb_path)
            cache_suppressed = _recording_cache_suppressed(clip)
            clip_video_bytes = 0
            clip_thumbnail_bytes = 0
            if clip_cached:
                stats["cached_videos"] += 1
                camera_stats["cached_videos"] += 1
                if hls_cached:
                    clip_video_bytes = _directory_size(
                        _hls_playlist_cache_path(clip).parent
                    )
                elif mp4_cached:
                    clip_video_bytes = _file_size(clip_path)
                camera_stats["video_bytes"] += clip_video_bytes
            if thumb_cached:
                stats["cached_thumbnails"] += 1
                camera_stats["cached_thumbnails"] += 1
                clip_thumbnail_bytes = _file_size(thumb_path)
                camera_stats["thumbnail_bytes"] += clip_thumbnail_bytes
            playable = _clip_media_playable(clip)
            ready = playable and (clip_cached or not retained_mode)
            if ready:
                stats["ready_clips"] += 1
                camera_stats["ready_clips"] += 1
            if not playable:
                continue
            if sync_enabled and not clip_cached and not cache_suppressed:
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
                    "retained": retained_mode,
                    "thumbnail_cached": thumb_cached,
                    "manual_cache_deleted": cache_suppressed,
                    "cache_bytes": clip_video_bytes + clip_thumbnail_bytes,
                    "playable": playable,
                    "sync_enabled": sync_enabled,
                    **_hls_playback_fields_for_clip(clip),
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
        if not _recordings_runtime_available(self.hass):
            raise web.HTTPNotFound()
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
        if not _recordings_runtime_available(self.hass):
            raise web.HTTPNotFound()
        try:
            payload = await request.json()
        except Exception as exc:  # noqa: BLE001
            raise web.HTTPBadRequest(reason="Invalid X-Sense panel debug payload") from exc
        if not isinstance(payload, dict):
            raise web.HTTPBadRequest(reason="Invalid X-Sense panel debug payload")

        LOGGER.debug("X-Sense recordings panel frontend debug payload received")
        return web.json_response({"ok": True})


class XSenseRecordingsPanelPlaybackView(http.HomeAssistantView):
    """Resolve one X-Sense recording for the sidebar player."""

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
        if not _recordings_runtime_available(self.hass):
            raise web.HTTPNotFound()
        serial = str(request.query.get("serial") or "")
        if not serial:
            raise web.HTTPBadRequest(reason="Missing X-Sense camera serial")
        clip = await self._clip(entry_id, serial, start, end)
        started_at = monotonic()
        source = XSenseRecordingsMediaSource(self.hass)
        if not _recording_cache_retained(self.hass, entry_id):
            try:
                token, playlist, profile = await _async_create_hls_proxy_session(
                    self.hass, clip
                )
            except Exception as exc:  # noqa: BLE001
                LOGGER.debug(
                    "X-Sense recordings HLS proxy setup failed: %s",
                    {
                        **_clip_debug_context(entry_id, serial, start, end),
                        "error": _log_safe_error(exc),
                    },
                )
                raise web.HTTPNotFound(
                    reason="X-Sense recording is not ready"
                ) from exc
            LOGGER.debug(
                "X-Sense recordings panel playback proxy ready: %s",
                {
                    **_clip_debug_context(entry_id, serial, start, end),
                    "elapsed_ms": int((monotonic() - started_at) * 1000),
                    "leading_aac": profile.get("leading_aac"),
                    "playback_mode": profile.get("playback_mode"),
                },
            )
            headers = {"Cache-Control": "private, max-age=60"}
            if profile.get("leading_aac"):
                headers["X-XSense-HLS-Leading-AAC"] = str(
                    profile["leading_aac"]
                )
            if profile.get("playback_mode"):
                headers["X-XSense-HLS-Playback-Mode"] = str(
                    profile["playback_mode"]
                )
            headers["Content-Location"] = _hls_proxy_resource_path(
                token, "root.m3u8"
            )
            return web.Response(
                text=playlist,
                content_type=HLS_MIME_TYPE,
                headers=headers,
            )
        cached = await source._async_cached_media_ready(clip)
        cache_suppressed = await async_recording_cache_suppressed(self.hass, clip)
        context = {
            **_clip_debug_context(entry_id, serial, start, end),
            "source": clip.get("source"),
            "quality": clip.get("quality"),
            "cached": cached,
            "format": await source._async_cached_media_format(clip),
        }
        LOGGER.debug("X-Sense recordings panel playback requested: %s", context)
        if (
            _recording_media_sync_enabled(self.hass, entry_id)
            and not cached
            and not cache_suppressed
        ):
            LOGGER.debug(
                "X-Sense recordings panel playback waiting for sync: %s",
                _clip_debug_context(entry_id, serial, start, end),
            )
            raise web.HTTPNotFound(reason="X-Sense recording is waiting for sync")
        if cache_suppressed:
            await async_allow_recording_cache(self.hass, clip)
        try:
            url = await source._async_cached_playback_url(clip)
        except Exception as exc:  # noqa: BLE001
            LOGGER.debug(
                "X-Sense recordings panel playback cache failed: %s",
                {
                    **_clip_debug_context(entry_id, serial, start, end),
                    "error": _log_safe_error(exc),
                },
            )
            raise web.HTTPNotFound(reason="X-Sense recording is not ready") from exc
        output_path = _clip_cache_path(clip)
        if await source._async_hls_ready(clip):
            await async_touch_recording_cache(self.hass, clip)
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
                    **_hls_playback_fields_for_clip(clip),
                },
            )
            headers = {
                "Cache-Control": "private, max-age=300",
                **_hls_playback_response_headers(clip),
            }
            return web.Response(
                text=playlist,
                content_type=HLS_MIME_TYPE,
                headers=headers,
            )
        if await source._async_mp4_ready(output_path):
            await async_touch_recording_cache(self.hass, clip)
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
        if not _recordings_runtime_available(self.hass):
            raise web.HTTPNotFound()
        proxy = _hls_proxy_session(self.hass, token)
        if proxy is not None:
            return await _async_hls_proxy_resource_response(
                self.hass, token, filename, proxy
            )
        root = _hls_segment_root(self.hass, token)
        if root is None:
            raise web.HTTPNotFound(reason="X-Sense HLS recording token expired")
        path = (root / filename).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError as exc:
            raise web.HTTPNotFound(reason="Invalid X-Sense HLS segment") from exc
        source = XSenseRecordingsMediaSource(self.hass)
        if not await source._async_path_ready(path):
            LOGGER.debug(
                "X-Sense recordings HLS cache is incomplete: %s",
                {"filename": _log_safe_str(filename, 160)},
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
                "filename": _log_safe_str(filename, 160),
                "bytes": size,
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
        if not _recordings_runtime_available(self.hass):
            raise web.HTTPNotFound()
        serial = str(request.query.get("serial") or "")
        if not serial:
            raise web.HTTPBadRequest(reason="Missing X-Sense camera serial")
        clip = await XSenseRecordingsPanelPlaybackView(
            self.hass
        )._clip(entry_id, serial, start, end)
        if not _recording_cache_retained(self.hass, entry_id):
            thumbnail_url = str(clip.get("thumbnail_url") or "")
            if not thumbnail_url.startswith(("http://", "https://")):
                raise web.HTTPNotFound(
                    reason="X-Sense recording thumbnail is not ready"
                )
            try:
                payload, content_type, final_url = await _async_fetch_proxy_resource(
                    self.hass, thumbnail_url
                )
            except Exception as exc:  # noqa: BLE001
                raise web.HTTPNotFound(
                    reason="X-Sense recording thumbnail is not ready"
                ) from exc
            return web.Response(
                body=payload,
                content_type=_normalized_content_type(content_type, final_url),
                headers={"Cache-Control": "private, max-age=300"},
            )
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


class XSenseRecordingsCacheManagementView(http.HomeAssistantView):
    """Delete locally cached recordings from the recordings panel."""

    url = f"/api/{DOMAIN}/recordings/cache/{{scope}}/{{entry_id}}"
    name = f"api:{DOMAIN}:recordings:cache"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the cache management view."""
        self.hass = hass

    async def delete(
        self, request: web.Request, scope: str, entry_id: str
    ) -> web.Response:
        """Delete one clip, one camera, or all local recording caches."""
        if not _recordings_runtime_available(self.hass):
            raise web.HTTPNotFound()
        serial = str(request.query.get("serial") or "")
        if scope == "clip":
            start = str(request.query.get("start") or "")
            end = str(request.query.get("end") or "")
            if not serial or not start or not end:
                raise web.HTTPBadRequest(reason="Missing recording cache identifier")
            clip = await XSenseRecordingsPanelPlaybackView(self.hass)._clip(
                entry_id, serial, start, end
            )
            summary = await async_delete_recording_cache(
                self.hass, clip, suppress_recache=True
            )
            if summary.get("skipped_active") and not summary.get("deleted_items"):
                raise web.HTTPConflict(reason="Recording is currently playing")
        elif scope == "playback":
            start = str(request.query.get("start") or "")
            end = str(request.query.get("end") or "")
            if not serial or not start or not end:
                raise web.HTTPBadRequest(reason="Missing recording playback identifier")
            if _recording_cache_retained(self.hass, entry_id):
                return web.json_response({"ok": True, "retained": True})
            try:
                start_value = int(start)
                end_value = int(end)
            except ValueError as exc:
                raise web.HTTPBadRequest(
                    reason="Invalid recording playback identifier"
                ) from exc
            summary = await async_release_recording_playback(
                self.hass,
                entry_id=entry_id,
                serial=serial,
                start=start_value,
                end=end_value,
            )
        elif scope == "camera":
            if not serial:
                raise web.HTTPBadRequest(reason="Missing X-Sense camera serial")
            summary = await async_delete_camera_recording_cache(
                self.hass,
                entry_id=entry_id,
                serial=serial,
                suppress_recache=True,
            )
        elif scope == "all":
            summary = await async_clear_recording_caches(
                self.hass,
                entry_id=None if entry_id == "all" else entry_id,
                suppress_recache=True,
            )
        else:
            raise web.HTTPNotFound(reason="Unknown recording cache scope")
        LOGGER.debug(
            "X-Sense recording cache deleted from panel: %s",
            {"scope": scope, "entry_id": entry_id, **summary},
        )
        return web.json_response({"ok": True, **summary})


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


async def _async_create_hls_proxy_session(
    hass: HomeAssistant,
    clip: dict[str, Any],
) -> tuple[str, str, dict[str, Any]]:
    """Create an on-demand proxy session for one APK-provided HLS recording."""
    source_url = str(clip.get("playback_url") or "")
    if not source_url.startswith(("http://", "https://")):
        raise RuntimeError("X-Sense recording did not include an HLS URL")
    payload, _content_type, final_url = await _async_fetch_proxy_resource(
        hass, source_url
    )
    try:
        playlist_text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise RuntimeError("X-Sense recording was not an HLS playlist") from exc
    if "#EXTM3U" not in playlist_text[:256]:
        raise RuntimeError("X-Sense recording was not an HLS playlist")

    tokens = hass.data.setdefault(DOMAIN, {}).setdefault("_recording_hls_tokens", {})
    now = monotonic()
    for stale_token, data in list(tokens.items()):
        if not isinstance(data, dict) or float(data.get("expires", 0)) <= now:
            tokens.pop(stale_token, None)
    token = secrets.token_urlsafe(24)
    proxy: dict[str, Any] = {
        "mode": "proxy",
        "expires": now + HLS_SEGMENT_TOKEN_TTL,
        "entry_id": str(clip.get("entry_id") or ""),
        "cache_key": _cache_group_key_for_clip(clip),
        "media_root": _recording_media_root_from_value(clip.get("media_root")),
        "resources": {},
        "resource_lookup": {},
        "next_resource": 0,
    }
    tokens[token] = proxy
    try:
        playlist, profile = await _async_rewrite_hls_proxy_playlist(
            hass,
            token,
            proxy,
            playlist_text,
            final_url,
        )
    except Exception:
        tokens.pop(token, None)
        raise
    proxy["resources"]["root.m3u8"] = {
        "kind": "rewritten_playlist",
        "playlist": playlist,
    }
    async_schedule_temporary_recording_cleanup(hass, clip)
    return token, playlist, profile


def _hls_proxy_session(hass: HomeAssistant, token: str) -> dict[str, Any] | None:
    """Return one active on-demand HLS proxy session."""
    tokens = hass.data.setdefault(DOMAIN, {}).setdefault("_recording_hls_tokens", {})
    data = tokens.get(token)
    if not isinstance(data, dict) or data.get("mode") != "proxy":
        return None
    if float(data.get("expires", 0)) <= monotonic():
        tokens.pop(token, None)
        return None
    data["expires"] = monotonic() + HLS_SEGMENT_TOKEN_TTL
    return data


def _hls_proxy_resource_path(token: str, resource_id: str) -> str:
    return f"/api/{DOMAIN}/recordings/hls/{token}/{resource_id}"


def _add_hls_proxy_resource(
    proxy: dict[str, Any],
    url: str,
    kind: str,
) -> str:
    resources = proxy.setdefault("resources", {})
    lookup = proxy.setdefault("resource_lookup", {})
    lookup_key = f"{kind}:{url}"
    existing = lookup.get(lookup_key)
    if isinstance(existing, str) and existing in resources:
        return existing
    resource_number = int(proxy.get("next_resource") or 0)
    proxy["next_resource"] = resource_number + 1
    suffix = Path(urlparse(url).path).suffix.lower()
    if not suffix or len(suffix) > 8:
        suffix = ".m3u8" if kind == "playlist" else ".bin"
    resource_id = f"r{resource_number:04d}{suffix}"
    resources[resource_id] = {"url": url, "kind": kind}
    lookup[lookup_key] = resource_id
    return resource_id


async def _async_rewrite_hls_proxy_playlist(
    hass: HomeAssistant,
    token: str,
    proxy: dict[str, Any],
    playlist_text: str,
    playlist_url: str,
) -> tuple[str, dict[str, Any]]:
    """Rewrite one upstream playlist to token-scoped on-demand resources."""
    rewritten: list[str] = []
    media_resources: list[tuple[int, str]] = []
    variant_uri_pending = False
    for line in playlist_text.splitlines():
        stripped = line.strip()
        if not stripped:
            rewritten.append(line)
            continue
        if stripped.startswith("#"):
            uri = _hls_attribute_uri(line)
            if uri:
                upstream_url = _hls_proxy_upstream_url(playlist_url, uri)
                kind = _hls_attribute_resource_kind(
                    stripped,
                    upstream_url,
                )
                resource_id = _add_hls_proxy_resource(proxy, upstream_url, kind)
                line = line.replace(
                    f'URI="{uri}"',
                    f'URI="{_hls_proxy_resource_path(token, resource_id)}"',
                )
            if stripped.upper().startswith("#EXT-X-STREAM-INF:"):
                variant_uri_pending = True
            rewritten.append(line)
            continue

        upstream_url = _hls_proxy_upstream_url(playlist_url, stripped)
        kind = (
            "playlist"
            if variant_uri_pending or _is_hls_playlist_uri(upstream_url)
            else "media"
        )
        variant_uri_pending = False
        resource_id = _add_hls_proxy_resource(proxy, upstream_url, kind)
        rewritten.append(_hls_proxy_resource_path(token, resource_id))
        if kind == "media":
            media_resources.append((len(rewritten) - 1, resource_id))

    profile: dict[str, Any] = {
        "leading_aac": "unknown",
        "playback_mode": "normal",
    }
    if media_resources:
        resources = proxy["resources"]
        first_line, first_id = media_resources[0]
        first_resource = resources[first_id]
        first_payload, first_type, first_url = await _async_fetch_proxy_resource(
            hass, first_resource["url"]
        )
        first_resource.update(
            {"payload": first_payload, "content_type": first_type, "url": first_url}
        )
        reference_payload = None
        if len(media_resources) > 1:
            reference_id = media_resources[1][1]
            reference_resource = resources[reference_id]
            reference_payload, reference_type, reference_url = (
                await _async_fetch_proxy_resource(hass, reference_resource["url"])
            )
            reference_resource.update(
                {
                    "payload": reference_payload,
                    "content_type": reference_type,
                    "url": reference_url,
                }
            )
        executor = getattr(hass, "async_add_executor_job", None)
        if callable(executor):
            prepared_payload, profile = await executor(
                _prepare_hls_proxy_leading_segment,
                first_payload,
                reference_payload,
            )
        else:
            prepared_payload, profile = await asyncio.to_thread(
                _prepare_hls_proxy_leading_segment,
                first_payload,
                reference_payload,
            )
        first_resource["payload"] = prepared_payload
        if profile.get("playback_mode") != "normal":
            rewritten.insert(first_line + 1, "#EXT-X-DISCONTINUITY")

    return "\n".join(rewritten) + "\n", profile


async def _async_hls_proxy_resource_response(
    hass: HomeAssistant,
    token: str,
    resource_id: str,
    proxy: dict[str, Any],
) -> web.Response:
    """Fetch and return one token-scoped upstream HLS resource."""
    resources = proxy.get("resources")
    resource = resources.get(resource_id) if isinstance(resources, dict) else None
    if not isinstance(resource, dict):
        raise web.HTTPNotFound(reason="Unknown X-Sense HLS resource")
    if resource.get("kind") == "rewritten_playlist":
        playlist = str(resource.get("playlist") or "")
        if not playlist.startswith("#EXTM3U"):
            raise web.HTTPNotFound(reason="Invalid X-Sense HLS playlist")
        return web.Response(
            text=playlist,
            content_type=HLS_MIME_TYPE,
            headers={"Cache-Control": "private, max-age=60"},
        )
    payload = resource.get("payload")
    content_type = str(resource.get("content_type") or "")
    final_url = str(resource.get("url") or "")
    if not isinstance(payload, bytes):
        try:
            payload, content_type, final_url = await _async_fetch_proxy_resource(
                hass, final_url
            )
        except Exception as exc:  # noqa: BLE001
            raise web.HTTPNotFound(
                reason="X-Sense HLS resource is not ready"
            ) from exc
    if resource.get("kind") == "playlist" or b"#EXTM3U" in payload[:256]:
        try:
            playlist_text = payload.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise web.HTTPNotFound(
                reason="Invalid X-Sense HLS playlist"
            ) from exc
        playlist, _profile = await _async_rewrite_hls_proxy_playlist(
            hass,
            token,
            proxy,
            playlist_text,
            final_url,
        )
        resource["kind"] = "rewritten_playlist"
        resource["playlist"] = playlist
        return web.Response(
            text=playlist,
            content_type=HLS_MIME_TYPE,
            headers={"Cache-Control": "private, max-age=60"},
        )
    return web.Response(
        body=payload,
        content_type=_normalized_content_type(content_type, final_url),
        headers={"Cache-Control": "private, max-age=300"},
    )


async def _async_fetch_proxy_resource(
    hass: HomeAssistant,
    url: str,
) -> tuple[bytes, str, str]:
    """Fetch one signed X-Sense media resource without exposing its URL."""
    session = async_get_clientsession(hass)
    async with session.get(url) as response:
        response.raise_for_status()
        return (
            await response.read(),
            response.headers.get("content-type", ""),
            str(response.url),
        )


def _normalized_content_type(content_type: str, url: str) -> str:
    """Return a valid response MIME type for an upstream HLS resource."""
    normalized = str(content_type or "").split(";", 1)[0].strip().lower()
    if normalized:
        return normalized
    guessed, _encoding = mimetypes.guess_type(urlparse(url).path)
    return guessed or "application/octet-stream"


def _hls_proxy_upstream_url(base_url: str, value: str) -> str:
    """Resolve and validate one upstream HLS resource URL."""
    url = urljoin(base_url, value)
    if urlparse(url).scheme.lower() not in {"http", "https"}:
        raise RuntimeError("X-Sense HLS playlist contained an unsupported URL")
    return url


def _hls_attribute_resource_kind(line: str, url: str) -> str:
    """Classify an HLS attribute URI using tag semantics before its suffix."""
    tag = line.split(":", 1)[0].strip().upper()
    if tag in {
        "#EXT-X-I-FRAME-STREAM-INF",
        "#EXT-X-MEDIA",
        "#EXT-X-RENDITION-REPORT",
    }:
        return "playlist"
    return "playlist" if _is_hls_playlist_uri(url) else "asset"


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
        if not stripped:
            rewritten.append(line)
            continue
        if stripped.startswith("#"):
            uri = _hls_attribute_uri(line)
            if uri:
                line = line.replace(
                    f'URI="{uri}"',
                    f'URI="{base}/{quote(uri, safe="/")}"',
                )
            rewritten.append(line)
            continue
        rewritten.append(f"{base}/{quote(stripped, safe='/')}")
    return "\n".join(rewritten) + "\n"


def _hls_playback_response_headers(clip: dict[str, Any]) -> dict[str, str]:
    """Return playback profile headers for one cached HLS clip."""
    fields = _hls_playback_fields_for_clip(clip)
    headers: dict[str, str] = {}
    leading_aac = fields.get("hls_leading_aac")
    playback_mode = fields.get("hls_playback_mode")
    if leading_aac:
        headers["X-XSense-HLS-Leading-AAC"] = leading_aac
    if playback_mode:
        headers["X-XSense-HLS-Playback-Mode"] = playback_mode
    return headers


def _clip_debug_context(
    entry_id: str,
    serial: str,
    start: str | int,
    end: str | int,
) -> dict[str, Any]:
    return {
        "entry_id": _log_safe_str(entry_id, 32),
        "camera": _short_serial(serial),
        "start": start,
        "end": end,
    }


def _short_serial(value: Any) -> str:
    text = _log_safe_str(value, 64)
    if len(text) <= 6:
        return text
    return f"...{text[-6:]}"


def _log_safe_str(value: Any, limit: int) -> str:
    """Return a short single-line string safe for structured debug logs."""
    text = str(value or "").replace("\r", "\\r").replace("\n", "\\n")
    return text[:limit]


def _log_safe_error(exc: Exception) -> str:
    """Return an exception summary without signed URL query parameters."""
    if isinstance(exc, ClientResponseError):
        return _log_safe_str(
            f"{type(exc).__name__}: status={exc.status} message={exc.message}",
            160,
        )
    text = re.sub(
        r"(https?://[^\s?'\"]+)\?[^\s'\"]+",
        r"\1?<redacted>",
        str(exc or ""),
    )
    return _log_safe_str(f"{type(exc).__name__}: {text}", 160)


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
