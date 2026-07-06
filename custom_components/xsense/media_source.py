"""Home Assistant media source support for X-Sense camera recordings."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import monotonic
from typing import Any
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.media_player import MediaClass
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
)
from homeassistant.components.media_source.error import Unresolvable
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.helpers.storage import Store

from .api.async_xsense import is_camera_entity
from .const import (
    CONF_RECORDING_MEDIA_CLIPS_ORDER,
    CONF_RECORDING_MEDIA_DAYS_ORDER,
    CONF_RECORDING_MEDIA_STORAGE_PATH,
    CONF_RECORDING_NOTIFICATION_QUALITY,
    DEFAULT_RECORDING_MEDIA_CLIPS_ORDER,
    DEFAULT_RECORDING_MEDIA_DAYS_ORDER,
    DEFAULT_RECORDING_MEDIA_STORAGE_PATH,
    DEFAULT_RECORDING_NOTIFICATION_QUALITY,
    CONF_RECORDING_MEDIA_SYNC_ENABLED,
    CONF_RECORDING_MEDIA_SYNC_HOURS,
    DEFAULT_RECORDING_MEDIA_SYNC_HOURS,
    DOMAIN,
    LOGGER,
)
from .coordinator import (
    _camera_event_history_playback_data,
    _camera_event_history_records,
)
from .playback import recording_media_url
from .pion_adapter import async_capture_sd_recording

MIME_TYPE = "video/mp4"
HLS_MIME_TYPE = "application/vnd.apple.mpegurl"
RECORDING_CACHE_VERSION = 1
RECORDING_CACHE_TTL = timedelta(minutes=5)
RECORDING_LOOKBACK_DAYS = 7
RECORDING_PAGE_LIMIT = 100
RECORDING_MEDIA_SYNC_STARTUP_DELAY = 30
RECORDING_MEDIA_RECENT_SYNC_INTERVAL = timedelta(minutes=2)
RECORDING_MEDIA_RECENT_LOOKBACK = timedelta(minutes=10)
THUMBNAIL_WARMUP_LIMIT = 10
EVENT_RECORDING_CLIP_LIMIT = 50
HLS_INITIAL_SEGMENT_COUNT = 2
SERVICE_REFRESH_RECORDINGS = "refresh_recordings"
SERVICE_CACHE_RECORDINGS = "cache_recordings"
SERVICE_CLEAR_RECORDINGS_CACHE = "clear_recordings_cache"
SERVICE_REFRESH_RECORDINGS_SCHEMA = vol.Schema({vol.Optional("entry_id"): str})


async def async_get_media_source(hass: HomeAssistant) -> MediaSource:
    """Return the X-Sense camera recordings media source."""
    return XSenseRecordingsMediaSource(hass)


async def async_register_recording_services(hass: HomeAssistant) -> None:
    """Register X-Sense recording services once."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get("_recording_services_registered"):
        return

    async def _async_refresh_recordings(call) -> None:
        await async_refresh_recording_indexes(
            hass,
            entry_id=call.data.get("entry_id"),
            force_refresh=True,
        )

    async def _async_cache_recordings(call) -> None:
        await async_cache_recording_media(
            hass,
            entry_id=call.data.get("entry_id"),
        )

    async def _async_clear_recordings_cache(call) -> None:
        await async_clear_recording_caches(
            hass,
            entry_id=call.data.get("entry_id"),
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_RECORDINGS,
        _async_refresh_recordings,
        schema=SERVICE_REFRESH_RECORDINGS_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CACHE_RECORDINGS,
        _async_cache_recordings,
        schema=SERVICE_REFRESH_RECORDINGS_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_RECORDINGS_CACHE,
        _async_clear_recordings_cache,
        schema=SERVICE_REFRESH_RECORDINGS_SCHEMA,
    )
    domain_data["_recording_services_registered"] = True


def async_unregister_recording_services(hass: HomeAssistant) -> None:
    """Remove X-Sense recording services if they were registered."""
    for service in (
        SERVICE_REFRESH_RECORDINGS,
        SERVICE_CACHE_RECORDINGS,
        SERVICE_CLEAR_RECORDINGS_CACHE,
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
    hass.data.setdefault(DOMAIN, {}).pop("_recording_services_registered", None)


async def async_refresh_recording_indexes(
    hass: HomeAssistant,
    *,
    entry_id: str | None = None,
    force_refresh: bool = False,
) -> list[dict[str, Any]]:
    """Refresh cached recording indexes for configured X-Sense entries."""
    refreshed: list[dict[str, Any]] = []
    domain_items = list(hass.data.get(DOMAIN, {}).items())
    for current_entry_id, coordinator in domain_items:
        if entry_id and current_entry_id != entry_id:
            continue
        if not _looks_like_coordinator(coordinator):
            continue
        manager = _recording_index_manager(hass, current_entry_id, coordinator)
        refreshed.append(await manager.async_index(force_refresh=force_refresh))
    LOGGER.debug(
        "X-Sense recording indexes refreshed: %s",
        {"requested_entry_id": entry_id, "entries": len(refreshed)},
    )
    return refreshed


async def async_cache_recording_media(
    hass: HomeAssistant,
    *,
    entry_id: str | None = None,
    recent_only: bool = False,
    force_refresh: bool = False,
) -> dict[str, int]:
    """Pre-cache X-Sense recording media for configured entries."""
    summary = {"downloaded": 0, "thumbnails": 0, "skipped": 0, "failed": 0}
    media_source = XSenseRecordingsMediaSource(hass)
    recent_cutoff = _recent_recording_cutoff() if recent_only else None
    indexes = await async_refresh_recording_indexes(
        hass,
        entry_id=entry_id,
        force_refresh=force_refresh,
    )
    LOGGER.debug(
        "X-Sense recording media cache started: %s",
        {
            "requested_entry_id": entry_id,
            "entries": len(indexes),
            "recent_only": recent_only,
            "force_refresh": force_refresh,
        },
    )
    media_source = XSenseRecordingsMediaSource(hass)
    for index in indexes:
        clips = _recording_cache_candidates(index)
        for clip in clips:
            if recent_cutoff is not None and not _clip_is_recent(
                clip,
                recent_cutoff,
            ):
                summary["skipped"] += 1
                continue
            if await media_source._async_cache_thumbnail(clip):
                summary["thumbnails"] += 1
            if not _clip_media_playable(clip):
                summary["skipped"] += 1
                continue
            if await media_source._async_cached_media_ready(clip):
                summary["skipped"] += 1
                continue
            try:
                await media_source._async_cached_playback_url(clip)
            except Exception as exc:  # noqa: BLE001
                LOGGER.debug(
                    "Could not cache X-Sense recording media: %s",
                    {
                        "entry_id": clip.get("entry_id"),
                        "camera": _short_serial(clip.get("serial")),
                        "start": clip.get("start"),
                        "source": clip.get("source"),
                        "error": str(exc),
                    },
                )
                summary["failed"] += 1
                continue
            if await media_source._async_cached_media_ready(clip):
                summary["downloaded"] += 1
            else:
                summary["failed"] += 1
    LOGGER.debug(
        "X-Sense recording media cache finished: %s",
        {
            **summary,
            "requested_entry_id": entry_id,
            "recent_only": recent_only,
            "force_refresh": force_refresh,
        },
    )
    return summary


async def async_cache_recording_playback(
    hass: HomeAssistant,
    *,
    entry_id: str,
    entity: Any,
    playback: dict[str, Any],
    camera_entity_id: str = "",
) -> str:
    """Cache one motion-event recording from APK playback metadata."""
    if not getattr(entity, "sn", None):
        return ""
    started_at = monotonic()

    media_root = _recording_media_root(hass, entry_id)
    clip = _recording_clip_from_playback(
        entry_id,
        str(entity.sn),
        camera_entity_id,
        playback,
        media_root,
        quality=_recording_notification_quality(hass, entry_id),
    )
    if clip is None or not _clip_media_playable(clip):
        LOGGER.debug(
            "X-Sense motion recording cache skipped: %s",
            {
                "camera": _short_serial(getattr(entity, "sn", "")),
                "source": playback.get("source"),
                "reason": "no_playable_clip",
                "elapsed_ms": int((monotonic() - started_at) * 1000),
            },
        )
        return ""
    _remember_event_recording_clip(hass, clip)

    media_source = XSenseRecordingsMediaSource(hass)
    cached_url = await media_source._async_cached_media_url(clip)
    if cached_url:
        LOGGER.debug(
            "X-Sense motion recording cache already ready: %s",
            {
                "camera": _short_serial(clip.get("serial")),
                "source": clip.get("source"),
                "start": clip.get("start"),
                "format": await media_source._async_cached_media_format(clip),
                "elapsed_ms": int((monotonic() - started_at) * 1000),
            },
        )
        return cached_url

    await media_source._async_cached_playback_url(clip)
    cached_url = await media_source._async_cached_media_url(clip)
    if cached_url:
        if not cached_url:
            LOGGER.debug(
                "X-Sense motion recording cache not linkable from Home Assistant media: %s",
                {
                    "camera": _short_serial(clip.get("serial")),
                    "source": clip.get("source"),
                    "start": clip.get("start"),
                    "elapsed_ms": int((monotonic() - started_at) * 1000),
                },
            )
            return ""
        LOGGER.debug(
            "X-Sense motion recording cache ready: %s",
            {
                "camera": _short_serial(clip.get("serial")),
                "source": clip.get("source"),
                "start": clip.get("start"),
                "duration": _clip_duration(clip),
                "format": await media_source._async_cached_media_format(clip),
                "elapsed_ms": int((monotonic() - started_at) * 1000),
            },
        )
        return cached_url
    LOGGER.debug(
        "X-Sense motion recording cache missing output after cache attempt: %s",
        {
            "camera": _short_serial(clip.get("serial")),
            "source": clip.get("source"),
            "start": clip.get("start"),
            "duration": _clip_duration(clip),
            "elapsed_ms": int((monotonic() - started_at) * 1000),
        },
    )
    return ""


async def async_cache_recent_recording_media(
    hass: HomeAssistant,
    *,
    entry_id: str | None = None,
) -> dict[str, int]:
    """Force-refresh recording history and pre-cache recent clips."""
    return await async_cache_recording_media(
        hass,
        entry_id=entry_id,
        recent_only=True,
        force_refresh=True,
    )


async def async_clear_recording_caches(
    hass: HomeAssistant,
    *,
    entry_id: str | None = None,
) -> None:
    """Clear X-Sense recording index caches and cached recording media."""
    managers = hass.data.get(DOMAIN, {}).get("_recording_indexes")
    if isinstance(managers, dict):
        for current_entry_id, manager in list(managers.items()):
            if entry_id and current_entry_id != entry_id:
                continue
            if hasattr(manager, "async_clear"):
                await manager.async_clear()
                managers.pop(current_entry_id, None)
        if not managers:
            hass.data.get(DOMAIN, {}).pop("_recording_indexes", None)
    roots = (
        [_recording_media_root(hass, entry_id)]
        if entry_id
        else _configured_recording_media_roots(hass)
    )
    _clear_recording_capture_locks(hass, roots)
    await hass.async_add_executor_job(_clear_media_cache, roots)


def async_remove_recording_index(hass: HomeAssistant, entry_id: str) -> None:
    """Remove the cached recording manager for an unloaded X-Sense entry."""
    managers = hass.data.get(DOMAIN, {}).get("_recording_indexes")
    if not isinstance(managers, dict):
        return
    managers.pop(entry_id, None)
    if not managers:
        hass.data.get(DOMAIN, {}).pop("_recording_indexes", None)


def _clear_recording_capture_locks(hass: HomeAssistant, roots: list[Path]) -> None:
    """Remove cached capture locks for cleared recording roots."""
    locks = hass.data.get(DOMAIN, {}).get("_recording_capture_locks")
    if not isinstance(locks, dict):
        return
    root_values = tuple(root.as_posix().rstrip("/") for root in roots)
    for key in list(locks):
        lock_path = Path(str(key)).as_posix()
        if any(lock_path == root or lock_path.startswith(f"{root}/") for root in root_values):
            locks.pop(key, None)
    if not locks:
        hass.data.get(DOMAIN, {}).pop("_recording_capture_locks", None)


def async_start_recording_media_sync(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Start optional background caching of recording media."""
    if not entry.options.get(CONF_RECORDING_MEDIA_SYNC_ENABLED):
        return

    hours = int(
        entry.options.get(
            CONF_RECORDING_MEDIA_SYNC_HOURS,
            DEFAULT_RECORDING_MEDIA_SYNC_HOURS,
        )
    )
    interval = timedelta(hours=max(1, hours))

    async def _async_run_media_sync(now=None) -> None:
        try:
            await async_cache_recording_media(hass, entry_id=entry.entry_id)
        except Exception as exc:  # noqa: BLE001
            LOGGER.debug("X-Sense recording media sync failed: %s", exc)

    async def _async_run_recent_media_sync(now=None) -> None:
        try:
            await async_cache_recent_recording_media(hass, entry_id=entry.entry_id)
        except Exception as exc:  # noqa: BLE001
            LOGGER.debug("X-Sense recent recording media sync failed: %s", exc)

    entry.async_on_unload(
        async_call_later(
            hass,
            RECORDING_MEDIA_SYNC_STARTUP_DELAY,
            _async_run_media_sync,
        )
    )
    entry.async_on_unload(
        async_track_time_interval(hass, _async_run_media_sync, interval)
    )
    entry.async_on_unload(
        async_track_time_interval(
            hass,
            _async_run_recent_media_sync,
            RECORDING_MEDIA_RECENT_SYNC_INTERVAL,
        )
    )
    LOGGER.debug(
        "X-Sense recording media sync started: %s",
        {
            "entry_id": entry.entry_id,
            "interval_hours": hours,
            "recent_interval_seconds": int(
                RECORDING_MEDIA_RECENT_SYNC_INTERVAL.total_seconds()
            ),
        },
    )


def build_identifier(params: dict[str, str] | None = None) -> str:
    """Return a stable X-Sense media-source identifier."""
    if params is None:
        return DOMAIN
    return f"{DOMAIN}/?{urlencode(params)}"


def parse_identifier(identifier: str) -> dict[str, str]:
    """Parse an X-Sense media-source identifier."""
    return dict(parse_qsl(urlparse(identifier).query, keep_blank_values=True))


class XSenseRecordingsMediaSource(MediaSource):
    """Browse and resolve X-Sense camera SD-card recordings."""

    name = "X-Sense Recordings"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the media source."""
        super().__init__(DOMAIN)
        self.hass = hass

    async def async_browse_media(
        self, item: MediaSourceItem
    ) -> BrowseMediaSource:
        """Browse X-Sense cameras, recording dates, and clips."""
        index = await self._async_load_index()
        identifier = item.identifier or ""
        query = parse_identifier(identifier)

        if not query:
            children = [
                self._directory(
                    build_identifier(
                        {
                            "entry_id": camera["entry_id"],
                            "serial": camera["serial"],
                        }
                    ),
                    camera.get("name") or camera["serial"],
                )
                for camera in index.get("cameras", [])
                if camera.get("serial")
            ]
            return self._root(children, index)

        entry_id = query.get("entry_id", "")
        serial = query.get("serial", "")
        clip_date = query.get("date")
        start = query.get("start")

        camera = self._find_camera(index, entry_id, serial)
        if camera is None:
            raise Unresolvable("Unknown X-Sense camera")

        if entry_id and serial and not clip_date and not start:
            dated_clips = []
            for clip in camera.get("clips", []):
                if clip.get("date") and await self._async_clip_visible_for_media_mode(
                    entry_id,
                    clip,
                ):
                    dated_clips.append(clip)
            dates = sorted(
                {clip.get("date") for clip in dated_clips},
                reverse=_sort_descending(
                    self.hass,
                    entry_id,
                    CONF_RECORDING_MEDIA_DAYS_ORDER,
                    DEFAULT_RECORDING_MEDIA_DAYS_ORDER,
                ),
            )
            children = [
                self._directory(
                    build_identifier(
                        {"entry_id": entry_id, "serial": serial, "date": date_value}
                    ),
                    date_value,
                )
                for date_value in dates
            ]
            if not children:
                children = [
                    self._directory(
                        build_identifier(
                            {
                                "entry_id": entry_id,
                                "serial": serial,
                                "empty": "1",
                            }
                        ),
                        "No cached recordings found yet",
                        can_expand=False,
                    )
                ]
            return self._directory_node(
                identifier=identifier,
                title=camera.get("name") or serial,
                children=children,
            )

        if entry_id and serial and clip_date and not start:
            clips = [
                clip
                for clip in camera.get("clips", [])
                if clip.get("date") == clip_date
            ]
            clips.sort(
                key=_clip_start_for_sort,
                reverse=_sort_descending(
                    self.hass,
                    entry_id,
                    CONF_RECORDING_MEDIA_CLIPS_ORDER,
                    DEFAULT_RECORDING_MEDIA_CLIPS_ORDER,
                ),
            )
            visible_clips = []
            for clip in clips:
                if clip.get("start") and await self._async_clip_visible_for_media_mode(
                    entry_id,
                    clip,
                ):
                    visible_clips.append(clip)
            children = []
            for clip in visible_clips:
                children.append(
                    await self._async_clip_node(
                        entry_id=entry_id,
                        serial=serial,
                        camera_entity_id=str(camera.get("entity_id") or ""),
                        clip=clip,
                    )
                )
            self._schedule_thumbnail_warmup(clips)
            return self._directory_node(
                identifier=identifier,
                title=clip_date,
                children=children,
            )

        if entry_id and serial and start:
            clip = self._find_clip(camera, int(start))
            if clip is None:
                raise Unresolvable("Unknown X-Sense recording")
            if not await self._async_clip_visible_for_media_mode(entry_id, clip):
                raise Unresolvable("X-Sense recording is waiting for background sync")
            can_play = _clip_media_playable(clip)
            return BrowseMediaSource(
                domain=DOMAIN,
                identifier=identifier,
                media_class=MediaClass.VIDEO,
                media_content_type=MIME_TYPE,
                title=str(clip.get("title") or start),
                can_play=can_play,
                can_expand=False,
                children=[],
                thumbnail=await self._async_clip_thumbnail_url(clip) or None,
            )

        if query.get("empty"):
            return self._directory_node(identifier=identifier, title="No clips", children=[])

        raise Unresolvable("Unknown X-Sense recordings media identifier")

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve one X-Sense recording to a playable HA URL."""
        index = await self._async_load_index()
        query = parse_identifier(item.identifier or "")
        entry_id = query.get("entry_id", "")
        serial = query.get("serial", "")
        camera = self._find_camera(index, entry_id, serial)
        if camera is None:
            raise Unresolvable("Unknown X-Sense camera")
        try:
            start = int(query.get("start") or "")
        except ValueError as exc:
            raise Unresolvable("Invalid X-Sense recording identifier") from exc

        clip = self._find_clip(camera, start)
        if clip is None:
            raise Unresolvable("Unknown X-Sense recording")
        if _recording_media_sync_enabled(
            self.hass, entry_id
        ) and not await self._async_cached_media_ready(clip):
            raise Unresolvable("X-Sense recording is waiting for background sync")
        resolved_url = await self._async_cached_playback_url(clip)
        output_path = _clip_cache_path(clip)
        local_path = output_path if await self._async_mp4_ready(output_path) else None
        mime_type = HLS_MIME_TYPE if await self._async_hls_ready(clip) else MIME_TYPE
        return PlayMedia(str(resolved_url), mime_type, path=local_path)

    async def _async_cached_playback_url(self, clip: dict[str, Any]) -> str:
        """Return a cached media URL for a recording, falling back safely."""
        direct_url = str(clip.get("playback_url") or "")
        if clip.get("source") != "video_url" or not direct_url:
            return await self._async_cached_sd_playback_url(clip)

        output_path = _clip_cache_path(clip)
        if await self._async_mp4_ready(output_path):
            return _local_media_url(output_path)
        if await self._async_hls_ready(clip):
            return _local_media_url(_hls_playlist_cache_path(clip))
        if await self._async_path_ready(output_path):
            LOGGER.debug(
                "X-Sense direct recording cache is not browser-playable; replacing it: %s",
                _clip_log_context(clip),
            )
            await self._async_file_job(_unlink_missing_ok, output_path)

        try:
            download = await self._async_download_direct_clip(direct_url, output_path)
            if not isinstance(download, dict):
                download = {}
        except Exception as exc:  # noqa: BLE001
            LOGGER.debug(
                "Could not cache X-Sense direct recording: %s",
                {**_clip_log_context(clip), "error": str(exc)},
            )
            return await self._async_cached_sd_playback_url(
                _fallback_capture_clip(clip)
            )

        if await self._async_mp4_ready(output_path):
            output_bytes = await self._async_file_size(output_path)
            LOGGER.debug(
                "X-Sense direct recording cache ready: %s",
                {
                    **_clip_log_context(clip),
                    "content_type": download.get("content_type"),
                    "bytes": download.get("bytes"),
                    "output_bytes": output_bytes,
                    "mp4_signature": download.get("mp4_signature"),
                    "download_elapsed_ms": download.get("elapsed_ms"),
                },
            )
            return _local_media_url(output_path)
        mp4_signature = await self._async_mp4_signature_present(output_path)
        if _is_hls_content_type(download.get("content_type")):
            try:
                hls = await self._async_cache_hls_clip(direct_url, clip)
            except Exception as exc:  # noqa: BLE001
                LOGGER.debug(
                    "Could not cache X-Sense HLS recording; using SD capture fallback: %s",
                    {**_clip_log_context(clip), "error": str(exc)},
                )
            else:
                LOGGER.debug(
                    "X-Sense HLS recording cache ready: %s",
                    {
                        **_clip_log_context(clip),
                        "content_type": download.get("content_type"),
                        "segments": hls.get("segments"),
                        "initial_segments": hls.get("initial_segments"),
                        "deferred_segments": hls.get("deferred_segments"),
                        "playlists": hls.get("playlists"),
                        "bytes": hls.get("bytes"),
                        "download_elapsed_ms": hls.get("elapsed_ms"),
                    },
                )
                await self._async_file_job(_unlink_missing_ok, output_path)
                return _local_media_url(_hls_playlist_cache_path(clip))
        LOGGER.debug(
            "X-Sense direct recording download was not playable; using SD capture fallback: %s",
            {
                **_clip_log_context(clip),
                "content_type": download.get("content_type"),
                "bytes": download.get("bytes"),
                "mp4_signature": mp4_signature,
                "download_elapsed_ms": download.get("elapsed_ms"),
            },
        )
        await self._async_file_job(_unlink_missing_ok, output_path)
        return await self._async_cached_sd_playback_url(_fallback_capture_clip(clip))

    async def _async_cached_sd_playback_url(self, clip: dict[str, Any]) -> str:
        """Capture an SD-only X-Sense clip to cached MP4 media."""
        output_path = _clip_cache_path(clip)
        if await self._async_mp4_ready(output_path):
            return _local_media_url(output_path)

        entry_id = str(clip.get("entry_id") or "")
        serial = str(clip.get("serial") or "")
        coordinator = getattr(self.hass, "data", {}).get(DOMAIN, {}).get(entry_id)
        if not _looks_like_coordinator(coordinator):
            raise Unresolvable("X-Sense recording account is not loaded")
        camera = _coordinator_camera_entity(coordinator, serial)
        if camera is None:
            raise Unresolvable("X-Sense recording camera is not loaded")

        LOGGER.debug(
            "X-Sense SD recording cache starting: %s",
            {
                "entry_id": entry_id,
                "camera": _short_serial(serial),
                "start": clip.get("start"),
                "end": clip.get("end"),
                "duration": _clip_duration(clip),
            },
        )
        try:
            await async_capture_sd_recording(
                self.hass,
                coordinator=coordinator,
                camera=camera,
                start_time=_clip_start_for_sort(clip),
                output_path=output_path,
                duration_seconds=_clip_duration(clip),
            )
        except Exception as exc:  # noqa: BLE001
            LOGGER.debug(
                "Could not cache X-Sense SD recording through Pion: %s",
                {
                    "entry_id": entry_id,
                    "camera": _short_serial(serial),
                    "start": clip.get("start"),
                    "end": clip.get("end"),
                    "error": str(exc),
                },
            )
            raise Unresolvable(
                "X-Sense SD recording could not be cached as media yet"
            ) from exc
        if await self._async_mp4_ready(output_path):
            cached_url = _local_media_url(output_path)
            output_bytes = await self._async_file_size(output_path)
            LOGGER.debug(
                "X-Sense SD recording cache ready: %s",
                {
                    "entry_id": entry_id,
                    "camera": _short_serial(serial),
                    "start": clip.get("start"),
                    "bytes": output_bytes,
                },
            )
            return cached_url
        raise Unresolvable("X-Sense SD recording cache did not create media")

    async def _async_download_direct_clip(
        self, url: str, output_path: Path
    ) -> dict[str, Any]:
        """Download one direct X-Sense recording into the media cache."""
        temp_path = output_path.with_name(f"{output_path.name}.direct")
        await self._async_file_job(_unlink_missing_ok, temp_path)
        started_at = monotonic()
        try:
            result = await self._async_download_url(url, temp_path)
            result["mp4_signature"] = await self._async_mp4_signature_present(
                temp_path
            )
            result["elapsed_ms"] = int((monotonic() - started_at) * 1000)
            if await self._async_mp4_ready(temp_path):
                await self._async_file_job(_replace_cache_file, temp_path, output_path)
            return result
        finally:
            await self._async_file_job(_unlink_missing_ok, temp_path)

    async def _async_cache_hls_clip(
        self,
        url: str,
        clip: dict[str, Any],
    ) -> dict[str, Any]:
        """Cache one HLS playlist and its referenced media files."""
        cache_dir = _hls_cache_dir(clip)
        started_at = monotonic()
        state = {
            "remaining_initial_segments": HLS_INITIAL_SEGMENT_COUNT,
            "initial_segments_cached": 0,
            "deferred": [],
            "playlists": 0,
        }
        LOGGER.debug(
            "X-Sense HLS recording cache starting: %s",
            {
                **_clip_log_context(clip),
                "initial_segment_target": HLS_INITIAL_SEGMENT_COUNT,
            },
        )
        await self._async_file_job(_clear_directory, cache_dir)
        result = await self._async_cache_hls_playlist(
            url,
            _hls_playlist_cache_path(clip),
            cache_dir,
            prefix="segment",
            depth=0,
            state=state,
        )
        if not await self._async_hls_ready(clip):
            raise Unresolvable("X-Sense HLS recording cache did not create media")
        deferred = [
            item for item in state["deferred"] if isinstance(item, tuple) and len(item) == 2
        ]
        if deferred:
            self._schedule_hls_background_cache(clip, deferred)
        result["elapsed_ms"] = int((monotonic() - started_at) * 1000)
        result["deferred_segments"] = len(deferred)
        result["initial_segments"] = int(state.get("initial_segments_cached") or 0)
        result["playlists"] = int(state.get("playlists") or 0)
        return result

    async def _async_cache_hls_playlist(
        self,
        url: str,
        playlist_path: Path,
        cache_dir: Path,
        *,
        prefix: str,
        depth: int,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Download and rewrite one HLS playlist for local cached playback."""
        session = async_get_clientsession(self.hass)
        async with session.get(url) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            playlist_text = await response.text()
        if "#EXTM3U" not in playlist_text[:256]:
            raise Unresolvable("X-Sense direct recording was not an HLS playlist")

        state["playlists"] = int(state.get("playlists") or 0) + 1
        rewritten: list[str] = []
        total_bytes = 0
        segment_count = 0
        key_count = 0
        child_playlist_count = 0
        for index, line in enumerate(playlist_text.splitlines()):
            stripped = line.strip()
            if not stripped:
                rewritten.append(line)
                continue
            if stripped.startswith("#EXT-X-KEY") and "URI=" in stripped:
                updated, key_bytes, cached = await self._async_cache_hls_attribute_uri(
                    line,
                    url,
                    cache_dir,
                    f"{prefix}_key_{key_count}.key",
                )
                key_count += 1 if cached else 0
                total_bytes += key_bytes
                rewritten.append(updated)
                continue
            if stripped.startswith("#EXT-X-MAP") and "URI=" in stripped:
                updated, map_bytes, cached = await self._async_cache_hls_attribute_uri(
                    line,
                    url,
                    cache_dir,
                    f"{prefix}_map_{index}{_hls_uri_suffix(stripped, '.mp4')}",
                )
                segment_count += 1 if cached else 0
                total_bytes += map_bytes
                rewritten.append(updated)
                continue
            if stripped.startswith("#"):
                rewritten.append(line)
                continue

            media_url = urljoin(url, stripped)
            if depth == 0 and _is_hls_playlist_uri(media_url):
                child_dir = cache_dir / f"{prefix}_{index}"
                child_playlist = child_dir / "index.m3u8"
                child_result = await self._async_cache_hls_playlist(
                    media_url,
                    child_playlist,
                    child_dir,
                    prefix=f"{prefix}_{index}",
                    depth=depth + 1,
                    state=state,
                )
                total_bytes += int(child_result.get("bytes") or 0)
                segment_count += int(child_result.get("segments") or 0)
                child_playlist_count += 1
                rewritten.append(f"{prefix}_{index}/index.m3u8")
                continue

            suffix = _hls_uri_suffix(media_url, ".ts")
            segment_name = f"{prefix}_{index:04d}{suffix}"
            segment_count += 1
            segment_path = cache_dir / segment_name
            if int(state.get("remaining_initial_segments") or 0) > 0:
                payload = await self._async_download_hls_part(media_url)
                await self._async_file_job(
                    _write_cache_file,
                    segment_path,
                    payload,
                )
                total_bytes += len(payload)
                state["remaining_initial_segments"] = (
                    int(state.get("remaining_initial_segments") or 0) - 1
                )
                state["initial_segments_cached"] = (
                    int(state.get("initial_segments_cached") or 0) + 1
                )
            else:
                state.setdefault("deferred", []).append((media_url, segment_path))
            rewritten.append(segment_name)

        LOGGER.debug(
            "X-Sense HLS playlist cached: %s",
            {
                "content_type": content_type,
                "depth": depth,
                "lines": len(playlist_text.splitlines()),
                "segments": segment_count,
                "child_playlists": child_playlist_count,
                "keys": key_count,
                "initial_segments_cached": int(
                    state.get("initial_segments_cached") or 0
                ),
                "deferred_segments": len(state.get("deferred", [])),
            },
        )
        await self._async_file_job(
            _write_cache_file,
            playlist_path,
            ("\n".join(rewritten) + "\n").encode(),
        )
        return {
            "content_type": content_type,
            "bytes": total_bytes,
            "segments": segment_count,
        }

    def _schedule_hls_background_cache(
        self,
        clip: dict[str, Any],
        deferred: list[tuple[str, Path]],
    ) -> None:
        """Continue caching HLS segments after the first playable buffer exists."""
        if not hasattr(self.hass, "async_create_task"):
            return

        async def _async_background_cache() -> None:
            started_at = monotonic()
            cached = 0
            failed = 0
            bytes_written = 0
            for url, path in deferred:
                if await self._async_path_ready(path):
                    cached += 1
                    continue
                try:
                    payload = await self._async_download_hls_part(url)
                    await self._async_file_job(_write_cache_file, path, payload)
                except Exception as exc:  # noqa: BLE001
                    failed += 1
                    LOGGER.debug(
                        "Could not cache deferred X-Sense HLS segment: %s",
                        {**_clip_log_context(clip), "error": str(exc)},
                    )
                    continue
                cached += 1
                bytes_written += len(payload)
            LOGGER.debug(
                "X-Sense HLS recording background cache finished: %s",
                {
                    **_clip_log_context(clip),
                    "cached_segments": cached,
                    "failed_segments": failed,
                    "bytes": bytes_written,
                    "elapsed_ms": int((monotonic() - started_at) * 1000),
                },
            )

        self.hass.async_create_task(_async_background_cache())

    async def _async_cache_hls_attribute_uri(
        self,
        line: str,
        base_url: str,
        cache_dir: Path,
        filename: str,
    ) -> tuple[str, int, bool]:
        """Cache an HLS tag URI attribute and rewrite it to a local filename."""
        uri = _hls_attribute_uri(line)
        if not uri:
            return line, 0, False
        payload = await self._async_download_hls_part(urljoin(base_url, uri))
        await self._async_file_job(_write_cache_file, cache_dir / filename, payload)
        return line.replace(f'URI="{uri}"', f'URI="{filename}"'), len(payload), True

    async def _async_download_hls_part(self, url: str) -> bytes:
        """Download one HLS segment, map, or key file."""
        session = async_get_clientsession(self.hass)
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.read()

    async def _async_cache_thumbnail(self, clip: dict[str, Any]) -> bool:
        """Cache one recording thumbnail when X-Sense provides a direct image URL."""
        thumbnail_url = str(clip.get("thumbnail_url") or "")
        if not thumbnail_url.startswith(("http://", "https://")):
            return False
        output_path = _clip_thumbnail_cache_path(clip)
        if await self._async_path_ready(output_path):
            return False
        try:
            await self._async_download_url(thumbnail_url, output_path)
        except Exception as exc:  # noqa: BLE001
            LOGGER.debug("Could not cache X-Sense recording thumbnail: %s", exc)
            return False
        return await self._async_path_ready(output_path)

    async def _async_download_url(self, url: str, output_path: Path) -> dict[str, Any]:
        """Download one URL into the recording media cache."""
        session = async_get_clientsession(self.hass)
        async with session.get(url) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            payload = await response.read()
        await self.hass.async_add_executor_job(_write_cache_file, output_path, payload)
        return {"content_type": content_type, "bytes": len(payload)}

    async def _async_path_ready(self, path: Path) -> bool:
        """Return whether a cached path is present without blocking the loop."""
        return await self._async_file_job(_path_ready, path)

    async def _async_mp4_ready(self, path: Path) -> bool:
        """Return whether a cached path is playable MP4 without blocking the loop."""
        return await self._async_file_job(_mp4_ready, path)

    async def _async_hls_ready(self, clip: dict[str, Any]) -> bool:
        """Return whether a cached HLS playlist and its media files are present."""
        return await self._async_file_job(_hls_ready, clip)

    async def _async_cached_media_ready(self, clip: dict[str, Any]) -> bool:
        """Return whether cached MP4 or HLS media exists for a clip."""
        return await self._async_mp4_ready(_clip_cache_path(clip)) or await self._async_hls_ready(
            clip
        )

    async def _async_cached_media_url(self, clip: dict[str, Any]) -> str:
        """Return a local media URL for cached MP4 or HLS media."""
        if await self._async_mp4_ready(_clip_cache_path(clip)):
            return _local_media_url(_clip_cache_path(clip))
        if await self._async_hls_ready(clip):
            return _local_media_url(_hls_playlist_cache_path(clip))
        return ""

    async def _async_cached_media_format(self, clip: dict[str, Any]) -> str:
        """Return the cached media format for diagnostics."""
        if await self._async_mp4_ready(_clip_cache_path(clip)):
            return "mp4"
        if await self._async_hls_ready(clip):
            return "hls"
        return ""

    async def _async_mp4_signature_present(self, path: Path) -> bool:
        """Return whether a path has an MP4 signature without blocking the loop."""
        return await self._async_file_job(_mp4_signature_present, path)

    async def _async_file_size(self, path: Path) -> int:
        """Return a file size without blocking the loop."""
        return await self._async_file_job(_file_size, path)

    async def _async_clip_visible_for_media_mode(
        self,
        entry_id: str,
        clip: dict[str, Any],
    ) -> bool:
        """Return whether a clip should appear without blocking the loop."""
        if not _recording_media_sync_enabled(self.hass, entry_id):
            return True
        return await self._async_cached_media_ready(clip)

    async def _async_clip_thumbnail_url(self, clip: dict[str, Any]) -> str:
        """Return a cached thumbnail URL when available without blocking the loop."""
        thumbnail_path = _clip_thumbnail_cache_path(clip)
        if await self._async_path_ready(thumbnail_path):
            return _local_media_url(thumbnail_path)
        return str(clip.get("thumbnail_url") or "")

    async def _async_file_job(self, func, *args):
        """Run a small filesystem helper off the event loop."""
        async_add_executor_job = getattr(self.hass, "async_add_executor_job", None)
        if async_add_executor_job is not None:
            return await async_add_executor_job(func, *args)
        return await asyncio.to_thread(func, *args)

    def _schedule_thumbnail_warmup(self, clips: list[dict[str, Any]]) -> None:
        """Warm up missing thumbnails for a browsed date folder."""
        if not hasattr(self.hass, "async_create_task"):
            return
        pending = [clip for clip in clips if clip.get("thumbnail_url")]
        if not pending:
            return

        async def _async_warmup() -> None:
            cached = 0
            requested = 0
            for clip in pending:
                if await self._async_path_ready(_clip_thumbnail_cache_path(clip)):
                    continue
                requested += 1
                if requested > THUMBNAIL_WARMUP_LIMIT:
                    break
                if await self._async_cache_thumbnail(clip):
                    cached += 1
            LOGGER.debug(
                "X-Sense recording thumbnail warmup finished: %s",
                {"requested": requested, "cached": cached},
            )

        self.hass.async_create_task(_async_warmup())

    async def _async_load_index(self) -> dict[str, Any]:
        domain_items = list(self.hass.data.get(DOMAIN, {}).items())
        managers = [
            _recording_index_manager(self.hass, entry_id, coordinator)
            for entry_id, coordinator in domain_items
            if _looks_like_coordinator(coordinator)
        ]
        if not managers:
            return {"warning": "X-Sense is not configured.", "cameras": []}

        cameras: list[dict[str, Any]] = []
        warnings: list[str] = []
        generated_at: str | None = None
        for manager in managers:
            index = await manager.async_index()
            cameras.extend(index.get("cameras", []))
            if warning := index.get("warning"):
                warnings.append(str(warning))
            generated_at = generated_at or index.get("generated_at")
        return {
            "generated_at": generated_at,
            "warning": "; ".join(warnings) if warnings else None,
            "cameras": _merge_event_recording_clips(self.hass, cameras),
        }

    @staticmethod
    def _find_camera(
        index: dict[str, Any], entry_id: str, serial: str
    ) -> dict[str, Any] | None:
        for camera in index.get("cameras", []):
            if camera.get("entry_id") == entry_id and camera.get("serial") == serial:
                return camera
        return None

    @staticmethod
    def _find_clip(camera: dict[str, Any], start: int) -> dict[str, Any] | None:
        for clip in camera.get("clips", []):
            if _clip_start_for_sort(clip) == start:
                return clip
        return None

    def _root(
        self, children: list[BrowseMediaSource], index: dict[str, Any]
    ) -> BrowseMediaSource:
        if not children and index.get("warning"):
            children = [self._directory("warning", str(index["warning"]), can_expand=False)]
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=None,
            media_class=MediaClass.DIRECTORY,
            media_content_type="",
            title=self.name,
            can_play=False,
            can_expand=True,
            children=children,
        )

    @staticmethod
    def _directory(
        identifier: str, title: str, can_expand: bool = True
    ) -> BrowseMediaSource:
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=identifier,
            media_class=MediaClass.DIRECTORY,
            media_content_type="",
            title=title,
            can_play=False,
            can_expand=can_expand,
            children=[],
        )

    @staticmethod
    def _directory_node(
        identifier: str, title: str, children: list[BrowseMediaSource]
    ) -> BrowseMediaSource:
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=identifier,
            media_class=MediaClass.DIRECTORY,
            media_content_type="",
            title=title,
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _async_clip_node(
        self,
        entry_id: str,
        serial: str,
        camera_entity_id: str,
        clip: dict[str, Any],
    ) -> BrowseMediaSource:
        identifier = build_identifier(
            {
                "entry_id": entry_id,
                "serial": serial,
                "start": str(_clip_start_for_sort(clip)),
                "camera_entity_id": camera_entity_id,
            }
        )
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=identifier,
            media_class=MediaClass.VIDEO,
            media_content_type=MIME_TYPE,
            title=str(clip.get("title") or clip.get("start")),
            can_play=_clip_media_playable(clip),
            can_expand=False,
            children=[],
            thumbnail=await self._async_clip_thumbnail_url(clip) or None,
        )


class XSenseRecordingIndex:
    """Cached APK SD-card recording index for one X-Sense config entry."""

    def __init__(self, hass: HomeAssistant, entry_id: str, coordinator: Any) -> None:
        """Initialize the recording index."""
        self.hass = hass
        self.entry_id = entry_id
        self.coordinator = coordinator
        self._store = Store(
            hass,
            RECORDING_CACHE_VERSION,
            f"{DOMAIN}.recordings.{entry_id}",
        )
        self._loaded = False
        self._cache: dict[str, Any] | None = None

    async def async_index(self, *, force_refresh: bool = False) -> dict[str, Any]:
        """Return the cached recording index, refreshing when stale."""
        await self._async_load()
        if (
            not force_refresh
            and self._cache
            and not _cache_expired(self._cache.get("generated_at"))
        ):
            cached = dict(self._cache)
            cached["cached"] = True
            return cached

        try:
            index = await self._async_refresh()
        except Exception as exc:  # noqa: BLE001
            LOGGER.debug("Could not refresh X-Sense recording index: %s", exc)
            if self._cache:
                stale = dict(self._cache)
                stale["cached"] = True
                stale["stale"] = True
                stale["warning"] = f"Using stale recordings cache: {exc}"
                return stale
            return {"warning": f"Could not refresh X-Sense recordings: {exc}", "cameras": []}

        self._cache = index
        await self._store.async_save(index)
        return index

    async def _async_load(self) -> None:
        if self._loaded:
            return
        loaded = await self._store.async_load()
        self._cache = loaded if isinstance(loaded, dict) else None
        self._loaded = True

    async def async_clear(self) -> None:
        """Clear this entry's stored recording index."""
        self._cache = None
        self._loaded = True
        await self._store.async_remove()

    async def _async_refresh(self) -> dict[str, Any]:
        cameras = _coordinator_cameras(self.coordinator, self.entry_id)
        serials = [camera["serial"] for camera in cameras if camera.get("serial")]
        if not serials:
            return {
                "generated_at": _utc_now_iso(),
                "entry_id": self.entry_id,
                "cameras": [],
                "warning": "No X-Sense cameras with SD-card recording support found.",
            }

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=RECORDING_LOOKBACK_DAYS)
        history = await self.coordinator.xsense.get_camera_event_history(
            serials,
            int(start.timestamp()),
            int(end.timestamp()),
            limit=RECORDING_PAGE_LIMIT,
        )
        records = _camera_event_history_records(history)
        clips_by_serial: dict[str, list[dict[str, Any]]] = {serial: [] for serial in serials}
        media_root = _recording_media_root(self.hass, self.entry_id)
        for record in records:
            clip = _recording_clip_from_record(
                self.entry_id, cameras, record, media_root
            )
            if clip is not None:
                clips_by_serial.setdefault(clip["serial"], []).append(clip)

        indexed_cameras = []
        sort_reverse = _sort_descending(
            self.hass,
            self.entry_id,
            CONF_RECORDING_MEDIA_CLIPS_ORDER,
            DEFAULT_RECORDING_MEDIA_CLIPS_ORDER,
        )
        for camera in cameras:
            clips = clips_by_serial.get(camera["serial"], [])
            clips.sort(key=_clip_start_for_sort, reverse=sort_reverse)
            indexed_cameras.append({**camera, "clips": clips})

        LOGGER.debug(
            "X-Sense recording index refreshed: %s",
            {
                "entry_id": self.entry_id,
                "cameras": len(indexed_cameras),
                "records": len(records),
                "clips": sum(len(camera["clips"]) for camera in indexed_cameras),
                "lookback_days": RECORDING_LOOKBACK_DAYS,
            },
        )
        return {
            "generated_at": _utc_now_iso(),
            "entry_id": self.entry_id,
            "lookback_days": RECORDING_LOOKBACK_DAYS,
            "cameras": indexed_cameras,
        }


def _recording_index_manager(
    hass: HomeAssistant, entry_id: str, coordinator: Any
) -> XSenseRecordingIndex:
    domain_data = hass.data.setdefault(DOMAIN, {})
    managers = domain_data.setdefault("_recording_indexes", {})
    manager = managers.get(entry_id)
    if not isinstance(manager, XSenseRecordingIndex):
        manager = XSenseRecordingIndex(hass, entry_id, coordinator)
        managers[entry_id] = manager
    return manager


def _looks_like_coordinator(value: Any) -> bool:
    return hasattr(value, "xsense") and hasattr(value, "data")


def _coordinator_cameras(coordinator: Any, entry_id: str) -> list[dict[str, Any]]:
    data = getattr(coordinator, "data", None)
    if not isinstance(data, dict):
        return []

    cameras: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entity in (
        *(data.get("stations") or {}).values(),
        *(data.get("devices") or {}).values(),
    ):
        if not is_camera_entity(entity):
            continue
        serial = str(getattr(entity, "sn", "") or "")
        if not serial or serial in seen:
            continue
        seen.add(serial)
        cameras.append(
            {
                "entry_id": entry_id,
                "serial": serial,
                "entity_id": str(getattr(entity, "entity_id", "") or ""),
                "name": str(getattr(entity, "name", "") or serial),
                "online": bool(getattr(entity, "online", False)),
                "model": str(getattr(entity, "type", "") or ""),
            }
        )
    return cameras


def _coordinator_camera_entity(coordinator: Any, serial: str) -> Any | None:
    """Return the loaded camera entity for a serial number."""
    data = getattr(coordinator, "data", None)
    if not isinstance(data, dict):
        return None
    for entity in (
        *(data.get("stations") or {}).values(),
        *(data.get("devices") or {}).values(),
    ):
        if str(getattr(entity, "sn", "") or "") == serial and is_camera_entity(entity):
            return entity
    return None


def _recording_clip_from_record(
    entry_id: str,
    cameras: list[dict[str, Any]],
    record: dict[str, Any],
    media_root: Path | None = None,
) -> dict[str, Any] | None:
    serial = str(
        record.get("serialNumber") or record.get("deviceSn") or record.get("sn") or ""
    )
    if not serial:
        return None
    camera = next((item for item in cameras if item.get("serial") == serial), None)
    if camera is None:
        return None
    media_root = media_root or _recording_media_root_from_value(None)

    playback = _camera_event_history_playback_data(record)
    start = playback.get("start_time_s") or playback.get("timestamp_s")
    if not start:
        return None
    end = playback.get("end_time_s") or _clip_end_from_period(start, playback.get("period"))
    source = playback.get("source") or "sd_playback"
    camera_entity_id = str(camera.get("entity_id") or "")
    return _recording_clip_from_playback(
        entry_id,
        serial,
        camera_entity_id,
        {
            **playback,
            "start_time_s": start,
            "end_time_s": end,
            "source": source,
        },
        media_root,
    )


def _recording_clip_from_playback(
    entry_id: str,
    serial: str,
    camera_entity_id: str,
    playback: dict[str, Any],
    media_root: Path | None = None,
    quality: str | None = None,
) -> dict[str, Any] | None:
    """Build one cacheable recording clip from APK playback metadata."""
    media_root = media_root or _recording_media_root_from_value(None)
    quality = _safe_recording_quality(quality)
    start = _playback_epoch_seconds(
        _first_present(
            playback,
            "start_time_s",
            "start_time",
            "timestamp_s",
            "timestamp",
        )
    )
    if not start:
        return None
    end = _playback_epoch_seconds(
        _first_present(playback, "end_time_s", "end_time")
    ) or _clip_end_from_period(start, playback.get("period"))
    requested_source = playback.get("source") or "sd_playback"
    direct_url = _preferred_recording_video_url(playback, quality)
    use_sd_playback = quality == "SD" and _sd_playback_available(playback)
    source = (
        "sd_playback"
        if use_sd_playback or not direct_url
        else "video_url"
    )
    resolved_url = (
        None
        if use_sd_playback
        else direct_url
    ) or recording_media_url(
        entry_id,
        serial,
        int(start),
        end_time=int(end or start),
    )
    thumbnail_url = playback.get("image_url") or playback.get("package_image_url") or ""
    return {
        "entry_id": entry_id,
        "serial": serial,
        "camera_entity_id": camera_entity_id,
        "start": int(start),
        "end": int(end or start),
        "date": _clip_date(int(start)),
        "title": _clip_title(int(start), int(end or start)),
        "source": source,
        "requested_source": requested_source,
        "quality": quality,
        "playback_url": resolved_url,
        "thumbnail_url": thumbnail_url,
        "cached_thumbnail_url": _local_media_url(
            _clip_thumbnail_cache_path_from_values(
                serial, int(start), int(end or start), media_root
            )
        )
        if thumbnail_url
        else "",
        "cached_url": _local_media_url(
            _clip_cache_path_from_values(
                serial, int(start), int(end or start), media_root
            )
        )
        if direct_url
        else "",
        "media_root": media_root.as_posix(),
    }


def _recording_cache_candidates(index: dict[str, Any]) -> list[dict[str, Any]]:
    """Return all recording clips newest-first for cache work."""
    clips = [
        clip
        for camera in index.get("cameras", [])
        for clip in camera.get("clips", [])
        if isinstance(clip, dict)
    ]
    clips.sort(key=_clip_start_for_sort, reverse=True)
    return clips


def _remember_event_recording_clip(hass: HomeAssistant, clip: dict[str, Any]) -> None:
    """Keep fresh motion-event clips visible before the history index catches up."""
    entry_id = str(clip.get("entry_id") or "")
    serial = str(clip.get("serial") or "")
    start = _clip_start_for_sort(clip)
    if not entry_id or not serial or not start:
        return
    event_clips = hass.data.setdefault(DOMAIN, {}).setdefault(
        "_recording_event_clips",
        {},
    )
    entry_clips = event_clips.setdefault(entry_id, {})
    camera_clips = entry_clips.setdefault(serial, {})
    camera_clips[start] = dict(clip)
    while len(camera_clips) > EVENT_RECORDING_CLIP_LIMIT:
        oldest_start = min(camera_clips)
        camera_clips.pop(oldest_start, None)


def _merge_event_recording_clips(
    hass: HomeAssistant,
    cameras: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return cameras with fresh event clips merged into the recording index."""
    event_clips = hass.data.get(DOMAIN, {}).get("_recording_event_clips")
    if not isinstance(event_clips, dict) or not event_clips:
        return cameras
    merged = [dict(camera) for camera in cameras]
    camera_by_key = {
        (str(camera.get("entry_id") or ""), str(camera.get("serial") or "")): camera
        for camera in merged
    }
    for entry_id, entry_clips in event_clips.items():
        if not isinstance(entry_clips, dict):
            continue
        for serial, clips_by_start in entry_clips.items():
            if not isinstance(clips_by_start, dict):
                continue
            key = (str(entry_id), str(serial))
            camera = camera_by_key.get(key)
            if camera is None:
                camera = {
                    "entry_id": str(entry_id),
                    "serial": str(serial),
                    "name": str(serial),
                    "online": True,
                    "clips": [],
                }
                camera_by_key[key] = camera
                merged.append(camera)
            clips = [dict(clip) for clip in camera.get("clips", [])]
            clip_indexes_by_start = {
                _clip_start_for_sort(clip): index
                for index, clip in enumerate(clips)
                if _clip_start_for_sort(clip)
            }
            for start, clip in clips_by_start.items():
                try:
                    start_int = int(start)
                except (TypeError, ValueError):
                    start_int = _clip_start_for_sort(clip)
                if not start_int or not isinstance(clip, dict):
                    continue
                if start_int in clip_indexes_by_start:
                    index = clip_indexes_by_start[start_int]
                    clips[index] = {**clips[index], **dict(clip)}
                    continue
                clip_indexes_by_start[start_int] = len(clips)
                clips.append(dict(clip))
            clips.sort(key=_clip_start_for_sort, reverse=True)
            camera["clips"] = clips
    return merged


def _clip_start_for_sort(clip: dict[str, Any]) -> int:
    """Return a safe clip start timestamp for cache ordering."""
    try:
        return int(clip.get("start") or 0)
    except (TypeError, ValueError):
        return 0


def _clip_end_for_path(clip: dict[str, Any], fallback: int) -> int:
    """Return a safe clip end timestamp for cache paths."""
    try:
        return int(clip.get("end") or clip.get("start") or fallback)
    except (TypeError, ValueError):
        return fallback


def _clip_end_from_period(start: int, period: Any) -> int:
    try:
        return int(start) + max(0, int(period))
    except (TypeError, ValueError):
        return int(start)


def _clip_duration(clip: dict[str, Any]) -> int | None:
    """Return a positive clip duration from normalized start/end values."""
    try:
        duration = int(clip.get("end") or 0) - int(clip.get("start") or 0)
    except (TypeError, ValueError):
        return None
    return duration if duration > 0 else None


def _recent_recording_cutoff() -> int:
    """Return the oldest clip start time for the fast recent sync lane."""
    return int((datetime.now(timezone.utc) - RECORDING_MEDIA_RECENT_LOOKBACK).timestamp())


def _clip_is_recent(clip: dict[str, Any], cutoff: int) -> bool:
    """Return whether a clip is recent enough for fast sync."""
    try:
        return int(clip.get("start") or 0) >= cutoff
    except (TypeError, ValueError):
        return False


def _first_present(data: dict[str, Any], *keys: str) -> Any:
    """Return the first non-empty value from data."""
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None


def _playback_epoch_seconds(value: Any) -> int | None:
    """Return epoch seconds for APK playback values that may be ms or seconds."""
    if value in (None, ""):
        return None
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return None
    if timestamp > 10_000_000_000:
        timestamp //= 1000
    return timestamp


def _clip_media_playable(clip: dict[str, Any]) -> bool:
    """Return whether a clip resolves to media, not an HTML playback page."""
    return bool(clip.get("playback_url"))


def _fallback_capture_clip(clip: dict[str, Any]) -> dict[str, Any]:
    """Return a clip that forces the camera playback capture path."""
    start = _clip_start_for_sort(clip)
    return {
        **clip,
        "source": "sd_playback",
        "playback_url": recording_media_url(
            str(clip.get("entry_id") or ""),
            str(clip.get("serial") or ""),
            start,
            end_time=_clip_end_for_path(clip, start),
        ),
    }


def _recording_media_sync_enabled(hass: HomeAssistant, entry_id: str) -> bool:
    """Return whether recording media browsing is limited to synced clips."""
    config_entries = getattr(hass, "config_entries", None)
    if config_entries is None or not hasattr(config_entries, "async_get_entry"):
        return False
    entry = config_entries.async_get_entry(entry_id)
    if entry is None:
        return False
    return bool(getattr(entry, "options", {}).get(CONF_RECORDING_MEDIA_SYNC_ENABLED))


def _recording_notification_quality(hass: HomeAssistant, entry_id: str) -> str:
    """Return the preferred recording quality for mobile notification clips."""
    config_entries = getattr(hass, "config_entries", None)
    if config_entries is None or not hasattr(config_entries, "async_get_entry"):
        return DEFAULT_RECORDING_NOTIFICATION_QUALITY
    entry = config_entries.async_get_entry(entry_id)
    if entry is None:
        return DEFAULT_RECORDING_NOTIFICATION_QUALITY
    return _safe_recording_quality(
        getattr(entry, "options", {}).get(
            CONF_RECORDING_NOTIFICATION_QUALITY,
            DEFAULT_RECORDING_NOTIFICATION_QUALITY,
        )
    )


def _safe_recording_quality(value: Any) -> str:
    """Return a supported recording quality option."""
    quality = str(value or DEFAULT_RECORDING_NOTIFICATION_QUALITY).strip().upper()
    if quality in {"HD", "SD"}:
        return quality
    return DEFAULT_RECORDING_NOTIFICATION_QUALITY


def _preferred_recording_video_url(
    playback: dict[str, Any], quality: str | None = None
) -> str:
    """Return the preferred APK-provided direct video URL for a recording."""
    quality = _safe_recording_quality(quality)
    candidates = _recording_video_candidates(playback)
    if not candidates:
        return ""
    candidates.sort(
        key=lambda item: _recording_video_candidate_score(item, quality),
        reverse=True,
    )
    return candidates[0]["url"]


def _recording_video_candidates(playback: dict[str, Any]) -> list[dict[str, Any]]:
    """Return direct video candidates from APK playback metadata."""
    candidates: list[dict[str, Any]] = []
    if url := _direct_video_url_from_item(playback):
        candidates.append(
            {
                "url": url,
                "resolution": playback.get("resolution")
                or playback.get("resolution_info"),
                "quality": playback.get("quality") or playback.get("video_type"),
                "default": True,
            }
        )
    for key in ("multi_resolution_videos", "sub_videos"):
        values = playback.get(key)
        if not isinstance(values, list):
            continue
        for item in values:
            if not isinstance(item, dict):
                continue
            if url := _direct_video_url_from_item(item):
                candidates.append(
                    {
                        "url": url,
                        "resolution": item.get("resolution")
                        or item.get("resolutionInfo")
                        or item.get("videoResolution"),
                        "quality": item.get("quality")
                        or item.get("videoType")
                        or item.get("type")
                        or item.get("name"),
                        "default": False,
                    }
                )
    return candidates


def _direct_video_url_from_item(item: dict[str, Any]) -> str:
    """Return a direct video URL from one APK video metadata object."""
    for key in (
        "video_url",
        "videoUrl",
        "url",
        "playUrl",
        "playbackUrl",
        "downloadUrl",
        "fileUrl",
    ):
        value = item.get(key)
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return value
    return ""


def _recording_video_candidate_score(item: dict[str, Any], quality: str) -> int:
    """Return a preference score for one direct video candidate."""
    text = " ".join(
        str(item.get(key) or "") for key in ("resolution", "quality", "url")
    ).lower()
    score = 0
    if item.get("default"):
        score += 10
    if "1920" in text or "1080" in text or "hd" in text:
        score += 100 if quality == "HD" else -20
    if "1280" in text or "720" in text:
        score += 60 if quality == "HD" else 20
    if "640" in text or "480" in text or "sd" in text or "sub" in text:
        score += 100 if quality == "SD" else -20
    return score


def _sd_playback_available(playback: dict[str, Any]) -> bool:
    """Return whether APK metadata has enough timing to request SD playback."""
    return _playback_epoch_seconds(
        _first_present(
            playback,
            "start_time_s",
            "start_time",
            "timestamp_s",
            "timestamp",
        )
    ) is not None


def _clip_cache_path(clip: dict[str, Any]) -> Path:
    """Return the cache path for one clip."""
    start = _clip_start_for_sort(clip)
    return _clip_cache_path_from_values(
        str(clip.get("serial") or ""),
        start,
        _clip_end_for_path(clip, start),
        _recording_media_root_from_value(clip.get("media_root")),
    )


def _hls_cache_dir(clip: dict[str, Any]) -> Path:
    """Return the cache directory for one HLS recording."""
    start = _clip_start_for_sort(clip)
    end = _clip_end_for_path(clip, start)
    root = _recording_media_root_from_value(clip.get("media_root"))
    return (
        root
        / "hls"
        / f"{_safe_segment(str(clip.get('serial') or ''))}_{start}_{end}"
    )


def _hls_playlist_cache_path(clip: dict[str, Any]) -> Path:
    """Return the cached HLS playlist path for one recording."""
    return _hls_cache_dir(clip) / "index.m3u8"


def _clip_cache_path_from_values(
    serial: str, start: int, end: int, media_root: Path | str | None = None
) -> Path:
    """Return the cache path for one recording video."""
    root = _recording_media_root_from_value(media_root)
    return root / "videos" / f"{_safe_segment(serial)}_{start}_{end}.mp4"


def _clip_thumbnail_cache_path(clip: dict[str, Any]) -> Path:
    """Return the cache path for one recording thumbnail."""
    start = _clip_start_for_sort(clip)
    return _clip_thumbnail_cache_path_from_values(
        str(clip.get("serial") or ""),
        start,
        _clip_end_for_path(clip, start),
        _recording_media_root_from_value(clip.get("media_root")),
    )


def _clip_thumbnail_cache_path_from_values(
    serial: str, start: int, end: int, media_root: Path | str | None = None
) -> Path:
    """Return the cache path for one recording thumbnail."""
    root = _recording_media_root_from_value(media_root)
    return root / "thumbs" / f"{_safe_segment(serial)}_{start}_{end}.jpg"


def _write_cache_file(path: Path, payload: bytes) -> None:
    """Atomically write one cached recording file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.stem}.tmp{path.suffix}")
    temp_path.write_bytes(payload)
    temp_path.replace(path)


def _replace_cache_file(source: Path, target: Path) -> None:
    """Replace one cached recording file."""
    target.parent.mkdir(parents=True, exist_ok=True)
    source.replace(target)


def _unlink_missing_ok(path: Path) -> None:
    """Remove one cached file when present."""
    path.unlink(missing_ok=True)


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _path_ready(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def _mp4_ready(path: Path) -> bool:
    return _path_ready(path) and _mp4_signature_present(path)


def _hls_ready(clip: dict[str, Any]) -> bool:
    return _hls_playlist_ready(_hls_playlist_cache_path(clip))


def _hls_playlist_ready(playlist_path: Path) -> bool:
    if not _path_ready(playlist_path):
        return False
    try:
        lines = playlist_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    media_lines = [
        line.strip()
        for line in lines
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not media_lines:
        return False
    child_playlist_seen = False
    for line in media_lines:
        path = playlist_path.parent / line
        if _is_hls_playlist_uri(line):
            child_playlist_seen = True
            if _hls_playlist_ready(path):
                return True
            continue
        if not _path_ready(path):
            return False
        return True
    return False


def _mp4_signature_present(path: Path) -> bool:
    try:
        with path.open("rb") as file:
            header = file.read(12)
    except OSError:
        return False
    if len(header) < 12 or header[4:8] != b"ftyp":
        return False
    box_size = int.from_bytes(header[:4], "big")
    try:
        file_size = path.stat().st_size
    except OSError:
        return False
    return 8 <= box_size <= file_size


def _clip_log_context(clip: dict[str, Any]) -> dict[str, Any]:
    return {
        "entry_id": clip.get("entry_id"),
        "camera": _short_serial(clip.get("serial")),
        "start": clip.get("start"),
        "end": clip.get("end"),
        "source": clip.get("source"),
        "quality": clip.get("quality"),
    }


def _is_hls_content_type(value: Any) -> bool:
    text = str(value or "").lower()
    return "mpegurl" in text or "application/x-mpegurl" in text


def _is_hls_playlist_uri(value: Any) -> bool:
    path = urlparse(str(value or "")).path.lower()
    return path.endswith(".m3u8") or path.endswith(".m3u")


def _hls_uri_suffix(value: str, default: str) -> str:
    suffix = Path(urlparse(value).path).suffix
    if not suffix or len(suffix) > 8:
        return default
    return suffix


def _hls_attribute_uri(line: str) -> str:
    marker = 'URI="'
    start = line.find(marker)
    if start == -1:
        return ""
    start += len(marker)
    end = line.find('"', start)
    if end == -1:
        return ""
    return line[start:end]


def _clear_directory(path: Path) -> None:
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        return
    for child in path.rglob("*"):
        if child.is_file():
            child.unlink(missing_ok=True)
    for child in sorted(path.rglob("*"), reverse=True):
        if child.is_dir():
            child.rmdir()
    path.mkdir(parents=True, exist_ok=True)


def _clear_media_cache(roots: list[Path]) -> None:
    """Remove cached recording media files."""
    for root in roots:
        for folder in (root / "videos", root / "thumbs"):
            if not folder.exists():
                continue
            for path in folder.glob("*"):
                if path.is_file() and path.suffix in {".h264", ".jpg", ".mp4"}:
                    path.unlink(missing_ok=True)
        hls_root = root / "hls"
        if hls_root.exists():
            _clear_directory(hls_root)


def _configured_recording_media_roots(hass: HomeAssistant) -> list[Path]:
    """Return all configured recording cache roots."""
    roots = {_recording_media_root_from_value(DEFAULT_RECORDING_MEDIA_STORAGE_PATH)}
    for entry in hass.config_entries.async_entries(DOMAIN):
        roots.add(_recording_media_root(hass, entry.entry_id))
    return sorted(roots, key=lambda path: str(path))


def _recording_media_root(hass: HomeAssistant, entry_id: str | None) -> Path:
    """Return the media cache root for one config entry."""
    entry = hass.config_entries.async_get_entry(entry_id) if entry_id else None
    if entry is None:
        return _recording_media_root_from_value(None)
    return _recording_media_root_from_value(
        entry.options.get(
            CONF_RECORDING_MEDIA_STORAGE_PATH,
            entry.data.get(
                CONF_RECORDING_MEDIA_STORAGE_PATH,
                DEFAULT_RECORDING_MEDIA_STORAGE_PATH,
            ),
        )
    )


def _recording_media_root_from_value(value: Any) -> Path:
    """Return a safe media cache root under /media."""
    root = str(value or DEFAULT_RECORDING_MEDIA_STORAGE_PATH).strip()
    if root != "/media" and not root.startswith("/media/"):
        root = DEFAULT_RECORDING_MEDIA_STORAGE_PATH
    return Path(root)


def _sort_descending(
    hass: HomeAssistant, entry_id: str, option_name: str, default: str
) -> bool:
    """Return whether a Tapo-style media order option is descending."""
    entry = hass.config_entries.async_get_entry(entry_id) if entry_id else None
    if entry is None:
        return default == "Descending"
    value = entry.options.get(option_name, entry.data.get(option_name, default))
    return value == "Descending"


def _local_media_url(path: Path) -> str:
    """Return the Home Assistant /media/local URL for a cached media path."""
    try:
        relative = path.resolve().relative_to(Path("/media").resolve())
    except ValueError:
        return ""
    return f"/media/local/{quote(relative.as_posix())}"


def _safe_segment(value: str) -> str:
    return "".join(
        character if character.isalnum() or character in {"-", "_"} else "_"
        for character in str(value)
    )


def _short_serial(value: Any) -> str:
    """Return a redacted camera serial for debug logs."""
    text = str(value or "")
    if len(text) <= 6:
        return "..."
    return f"...{text[-6:]}"


def _clip_date(start: int) -> str:
    return datetime.fromtimestamp(start, timezone.utc).strftime("%Y-%m-%d")


def _clip_title(start: int, end: int) -> str:
    try:
        time_zone = ZoneInfo("UTC")
        start_dt = datetime.fromtimestamp(start, time_zone)
        end_dt = datetime.fromtimestamp(end, time_zone)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return f"{start}-{end}"
    return f"{start_dt:%H:%M:%S} - {end_dt:%H:%M:%S}"


def _cache_expired(generated_at: Any) -> bool:
    if not generated_at:
        return True
    try:
        generated = datetime.fromisoformat(str(generated_at))
    except ValueError:
        return True
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - generated > RECORDING_CACHE_TTL


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
