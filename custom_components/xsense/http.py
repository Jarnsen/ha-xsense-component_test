"""HTTP views for the X-Sense recordings sidebar panel."""

from __future__ import annotations

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
    XSenseRecordingsMediaSource,
    _clip_cache_path,
    _clip_media_playable,
    _clip_start_for_sort,
    _clip_thumbnail_cache_path,
    _clip_visible_for_media_mode,
    _fallback_capture_clip,
    _local_media_url,
    _mp4_ready,
    _path_ready,
    _recording_media_root,
    _recording_media_sync_enabled,
    _sort_descending,
)


async def async_register_recordings_http_views(hass: HomeAssistant) -> None:
    """Register X-Sense recordings panel API routes once."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get("_recordings_http_views_registered"):
        return
    hass.http.register_view(XSenseRecordingsPanelDataView(hass))
    hass.http.register_view(XSenseRecordingsPanelDebugView(hass))
    hass.http.register_view(XSenseRecordingsPanelPlaybackView(hass))
    hass.http.register_view(XSenseRecordingsPanelThumbnailView(hass))
    domain_data["_recordings_http_views_registered"] = True


async def async_build_panel_data(hass: HomeAssistant) -> dict[str, Any]:
    """Build sidebar panel data from the X-Sense recording index."""
    source = XSenseRecordingsMediaSource(hass)
    index = await source._async_load_index()
    return build_panel_data(hass, index)


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
            clip_cached = _mp4_ready(clip_path)
            thumb_cached = _path_ready(thumb_path)
            if clip_cached:
                stats["cached_videos"] += 1
                camera_stats["cached_videos"] += 1
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
            if not _clip_visible_for_media_mode(hass, entry_id, clip):
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
                    "playback_url": _local_media_url(clip_path)
                    if clip_cached
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
        capture_requested = str(request.query.get("capture") or "") == "1"
        if capture_requested:
            replacing_direct_cache = clip.get("source") == "video_url"
            clip = _fallback_capture_clip(clip)
            output_path = _clip_cache_path(clip)
            if replacing_direct_cache and _path_ready(output_path):
                output_path.unlink(missing_ok=True)
        context = {
            **_clip_debug_context(entry_id, serial, start, end),
            "source": clip.get("source"),
            "quality": clip.get("quality"),
            "capture_requested": capture_requested,
            "cached": _mp4_ready(_clip_cache_path(clip)),
        }
        LOGGER.debug("X-Sense recordings panel playback requested: %s", context)
        if _recording_media_sync_enabled(self.hass, entry_id) and not _mp4_ready(
            _clip_cache_path(clip)
        ):
            LOGGER.debug(
                "X-Sense recordings panel playback waiting for sync: %s",
                _clip_debug_context(entry_id, serial, start, end),
            )
            raise web.HTTPNotFound(reason="X-Sense recording is waiting for sync")
        source = XSenseRecordingsMediaSource(self.hass)
        try:
            url = await source._async_cached_playback_url(clip)
        except Exception as exc:  # noqa: BLE001
            LOGGER.debug(
                "X-Sense recordings panel playback cache failed: %s",
                {**_clip_debug_context(entry_id, serial, start, end), "error": str(exc)},
            )
            raise web.HTTPNotFound(reason="X-Sense recording is not ready") from exc
        output_path = _clip_cache_path(clip)
        if _mp4_ready(output_path):
            LOGGER.debug(
                "X-Sense recordings panel playback served cached file: %s",
                {
                    **context,
                    "elapsed_ms": int((monotonic() - started_at) * 1000),
                    "bytes": output_path.stat().st_size,
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
        if not _path_ready(output_path):
            try:
                await XSenseRecordingsMediaSource(self.hass)._async_cache_thumbnail(clip)
            except Exception:  # noqa: BLE001
                pass
        if _path_ready(output_path):
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
    *,
    capture: bool = False,
) -> str:
    url = (
        f"/api/{DOMAIN}/recordings/play/"
        f"{quote(entry_id, safe='')}/{start}/{end}?serial={quote(serial, safe='')}"
    )
    if capture:
        url = f"{url}&capture=1"
    return url


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
