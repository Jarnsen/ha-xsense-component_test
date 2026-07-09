"""Support for X-Sense camera thumbnails."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass
from importlib import import_module

from homeassistant import config_entries
from homeassistant.components.camera import (
    Camera,
    CameraEntityDescription,
    CameraEntityFeature,
)
from homeassistant.components.camera.webrtc import (
    WebRTCAnswer,
    WebRTCCandidate,
    WebRTCClientConfiguration,
    WebRTCError,
    WebRTCSendMessage,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from webrtc_models import RTCIceCandidateInit

from .python_xsense.async_xsense import camera_live_resolution, is_camera_entity
from .const import DOMAIN, LOGGER
from .coordinator import XSenseDataUpdateCoordinator
from .entity import (
    DEVICE_ENTITY_WITHOUT_STATION,
    XSenseEntity,
    coordinator_devices,
    coordinator_stations,
)


@dataclass(kw_only=True, frozen=True)
class XSenseCameraEntityDescription(CameraEntityDescription):
    """Describes XSense camera entity."""


CAMERA_DESCRIPTION = XSenseCameraEntityDescription(
    key="thumbnail",
    icon="mdi:video",
    name=None,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up X-Sense camera entities."""
    coordinator: XSenseDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(_camera_entities(coordinator))


def _camera_entities(
    coordinator: XSenseDataUpdateCoordinator,
) -> list[XSenseCameraEntity]:
    """Return X-Sense camera entities from station and device records."""
    entities: list[XSenseCameraEntity] = []
    seen_entity_ids: set[str] = set()
    seen_camera_serials: set[str] = set()

    for station in coordinator_stations(coordinator).values():
        if is_camera_entity(station):
            entities.append(_camera_entity(coordinator, station))
            seen_entity_ids.add(station.entity_id)
            if serial := _camera_serial(station):
                seen_camera_serials.add(serial)

    for device in coordinator_devices(coordinator).values():
        serial = _camera_serial(device)
        if (
            not is_camera_entity(device)
            or device.entity_id in seen_entity_ids
            or (serial is not None and serial in seen_camera_serials)
        ):
            continue
        entities.append(
            _camera_entity(
                coordinator, device, station_id=DEVICE_ENTITY_WITHOUT_STATION
            )
        )

    return entities


def _camera_entity(
    coordinator: XSenseDataUpdateCoordinator,
    entity,
    station_id: str | None = None,
) -> XSenseCameraEntity:
    """Return the Home Assistant camera entity for an X-Sense camera."""
    entity_cls = (
        XSenseWebRTCCameraEntity if _is_webrtc_camera(entity) else XSenseCameraEntity
    )
    return entity_cls(coordinator, entity, CAMERA_DESCRIPTION, station_id=station_id)


def _camera_serial(entity) -> str | None:
    """Return a normalized camera serial for station/device de-duplication."""
    serial = getattr(entity, "sn", None)
    if serial is None:
        serial = entity.data.get("serialNumber") if isinstance(entity.data, dict) else None
    normalized = str(serial or "").strip().upper()
    return normalized or None


class XSenseCameraEntity(XSenseEntity, Camera):
    """X-Sense camera thumbnail entity."""

    entity_description: XSenseCameraEntityDescription

    def __init__(
        self,
        coordinator: XSenseDataUpdateCoordinator,
        entity,
        entity_description: XSenseCameraEntityDescription,
        station_id: str | None = None,
    ) -> None:
        """Set up the camera entity."""
        Camera.__init__(self)
        self.entity_description = entity_description
        super().__init__(coordinator, entity, station_id=station_id)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle camera data updates and refresh HA stream capabilities."""
        self._invalidate_camera_capabilities_cache()
        super()._handle_coordinator_update()

    @property
    def model(self) -> str | None:
        """Return the camera model."""
        entity = self._current_entity()
        if entity is None:
            return None
        return entity.data.get("cameraModel") or entity.data.get("modelNo")

    @property
    def supported_features(self) -> CameraEntityFeature:
        """Return native stream support for direct camera streams."""
        entity = self._current_entity()
        if entity is not None and _is_native_stream_camera(entity):
            return CameraEntityFeature.STREAM
        return CameraEntityFeature(0)

    @property
    def is_streaming(self) -> bool:
        """Return whether the camera has an active live stream session."""
        entity = self._current_entity()
        return entity is not None and bool(entity.data.get("cameraLiveUrl"))

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return the latest camera thumbnail."""
        entity = self._current_entity()
        if entity is None:
            return None

        thumbnail_url = entity.data.get("thumbImgUrl")
        if not thumbnail_url:
            return None

        session = async_get_clientsession(self.hass)
        async with session.get(thumbnail_url) as response:
            if response.status >= 400:
                return None
            return await response.read()

    async def stream_source(self) -> str | None:
        """Return a live stream URL when the X-Sense camera service provides one."""
        entity = self._current_entity()
        if entity is None or not _is_native_stream_camera(entity):
            return None
        source = await self.coordinator.xsense.start_camera_live(entity)
        return source

    async def async_will_remove_from_hass(self) -> None:
        """Stop any live view session when Home Assistant removes the entity."""
        entity = self._current_entity()
        if entity is not None and entity.data.get("cameraLiveUrl"):
            with suppress(Exception):
                await self.coordinator.xsense.stop_camera_live(entity)
        await super().async_will_remove_from_hass()


class XSenseWebRTCCameraEntity(XSenseCameraEntity):
    """X-Sense camera entity that supports native Home Assistant WebRTC."""

    def __init__(
        self,
        coordinator: XSenseDataUpdateCoordinator,
        entity,
        entity_description: XSenseCameraEntityDescription,
        station_id: str | None = None,
    ) -> None:
        """Set up the WebRTC camera entity."""
        super().__init__(
            coordinator, entity, entity_description, station_id=station_id
        )
        self._webrtc_sessions: dict[str, object] = {}
        self._pending_webrtc_candidates: dict[str, list[object]] = {}
        self._webrtc_keepalive_tasks: dict[str, asyncio.Task] = {}

    @property
    def supported_features(self) -> CameraEntityFeature:
        """Return native WebRTC stream support."""
        entity = self._current_entity()
        if entity is not None and _is_webrtc_camera(entity):
            return CameraEntityFeature.STREAM
        return CameraEntityFeature(0)

    @property
    def is_streaming(self) -> bool:
        """Return whether the camera has an active WebRTC live stream."""
        entity = self._current_entity()
        return entity is not None and bool(self._webrtc_sessions)

    async def stream_source(self) -> str | None:
        """Return no ffmpeg stream source for native WebRTC cameras."""
        entity = self._current_entity()
        if entity is not None:
            LOGGER.debug(
                "X-Sense camera WebRTC uses native Home Assistant signaling: %s",
                _camera_debug_context(entity, None),
            )
        return None

    @callback
    def _async_get_webrtc_client_configuration(self) -> WebRTCClientConfiguration:
        """Return the Home Assistant browser WebRTC client configuration."""
        return WebRTCClientConfiguration(data_channel="data-channel-of-")

    async def async_handle_async_webrtc_offer(
        self, offer_sdp: str, session_id: str, send_message: WebRTCSendMessage
    ) -> None:
        """Handle a Home Assistant WebRTC offer with X-Sense signaling."""
        entity = self._current_entity()
        if entity is None or not _is_webrtc_camera(entity):
            send_message(
                WebRTCError(
                    "xsense_webrtc_unsupported",
                    "Camera does not support X-Sense WebRTC",
                )
            )
            return

        LOGGER.debug(
            "X-Sense camera WebRTC offer received for signal relay: %s",
            _camera_debug_context(
                entity, session_id, offer_sdp=_sdp_debug_context(offer_sdp)
            ),
        )
        self._pending_webrtc_candidates[session_id] = []
        await self._close_existing_webrtc_sessions(
            preserve_pending_session_id=session_id
        )

        ticket_data = await self.coordinator.xsense.get_camera_webrtc_ticket(
            entity, force_refresh=True
        )
        LOGGER.debug(
            "X-Sense camera WebRTC ticket response: %s",
            _ticket_data_debug_context(ticket_data),
        )
        if not isinstance(ticket_data, dict):
            send_message(
                WebRTCError(
                    "xsense_webrtc_ticket_failed",
                    "Unable to get X-Sense WebRTC ticket",
                )
            )
            self._pending_webrtc_candidates.pop(session_id, None)
            return

        webrtc_signal = await self.hass.async_add_import_executor_job(
            import_module, __package__ + ".webrtc_signal"
        )
        try:
            ticket = webrtc_signal.XSenseWebRTCTicket.from_api(entity.sn, ticket_data)
        except (KeyError, TypeError, ValueError) as err:
            LOGGER.debug(
                "X-Sense camera WebRTC ticket parse failed: %s",
                _camera_debug_context(entity, session_id, error=type(err).__name__),
            )
            send_message(
                WebRTCError(
                    "xsense_webrtc_ticket_failed",
                    "Unable to parse X-Sense WebRTC ticket",
                )
            )
            self._pending_webrtc_candidates.pop(session_id, None)
            return
        if not ticket.is_valid:
            LOGGER.debug(
                "X-Sense camera WebRTC ticket expired or incomplete: %s",
                _camera_debug_context(entity, session_id),
            )
            send_message(
                WebRTCError(
                    "xsense_webrtc_ticket_expired",
                    "X-Sense WebRTC ticket expired",
                )
            )
            self._pending_webrtc_candidates.pop(session_id, None)
            return

        session = webrtc_signal.XSenseWebRTCSignalSession(
            session=async_get_clientsession(self.hass),
            ticket=ticket,
            offer_sdp=offer_sdp,
            resolution=_camera_live_resolution(entity),
            camera_online=_camera_online(entity),
            remote_candidate_callback=lambda candidate: _send_remote_candidate(
                send_message, entity, session_id, candidate
            ),
        )
        self._webrtc_sessions[session_id] = session
        _mark_camera_webrtc_live(self.hass, getattr(entity, "sn", None))
        self._start_webrtc_keepalive(entity, session_id, ticket)
        await self._flush_pending_webrtc_candidates(entity, session_id, session)
        try:
            answer = await session.start()
        except Exception as err:  # noqa: BLE001 - HA frontend needs a clean error
            removed_session = self._webrtc_sessions.pop(session_id, None)
            self._pending_webrtc_candidates.pop(session_id, None)
            self._stop_webrtc_keepalive(session_id)
            if removed_session is not None:
                _unmark_camera_webrtc_live(self.hass, getattr(entity, "sn", None))
            await session.close()
            LOGGER.debug(
                "X-Sense camera WebRTC signal relay failed: %s",
                _camera_debug_context(
                    entity, session_id, error=_error_debug_context(err)
                ),
            )
            send_message(WebRTCError("xsense_webrtc_start_failed", str(err)))
            return

        LOGGER.debug(
            "X-Sense camera WebRTC answer ready for Home Assistant: %s",
            _camera_debug_context(
                entity, session_id, answer_sdp=_sdp_debug_context(answer)
            ),
        )
        send_message(WebRTCAnswer(answer))
        session.start_forwarding_remote_candidates()

    async def _close_existing_webrtc_sessions(
        self, preserve_pending_session_id: str | None = None
    ) -> None:
        """Close previous X-Sense signaling sessions before a new live view."""
        sessions = list(self._webrtc_sessions.values())
        preserved_pending = (
            self._pending_webrtc_candidates.get(preserve_pending_session_id)
            if preserve_pending_session_id is not None
            else None
        )
        self._pending_webrtc_candidates.clear()
        if preserve_pending_session_id is not None and preserved_pending is not None:
            self._pending_webrtc_candidates[preserve_pending_session_id] = (
                preserved_pending
            )
        for keepalive_session_id in list(self._webrtc_keepalive_tasks):
            if keepalive_session_id != preserve_pending_session_id:
                self._stop_webrtc_keepalive(keepalive_session_id)
        if not sessions:
            return
        entity = self._current_entity()
        for _session in sessions:
            _unmark_camera_webrtc_live(self.hass, getattr(entity, "sn", None))
        LOGGER.debug(
            "X-Sense camera closing previous WebRTC signal sessions before new offer: %s",
            {"count": len(sessions)},
        )
        self._webrtc_sessions.clear()
        for session in sessions:
            await session.close()

    async def _flush_pending_webrtc_candidates(
        self, entity, session_id: str, session
    ) -> None:
        """Forward HA candidates that arrived before the signal session existed."""
        candidates = self._pending_webrtc_candidates.pop(session_id, [])
        if not candidates:
            return
        LOGGER.debug(
            "X-Sense camera WebRTC forwarding queued HA ICE candidates: %s",
            _camera_debug_context(
                entity,
                session_id,
                queued_candidate_count=len(candidates),
            ),
        )
        for candidate in candidates:
            await session.add_candidate(candidate)

    async def async_on_webrtc_candidate(self, session_id, candidate) -> None:
        """Forward a Home Assistant WebRTC candidate to X-Sense signaling."""
        entity = self._current_entity()
        if session := self._webrtc_sessions.get(session_id):
            await session.add_candidate(candidate)
            return
        if session_id in self._pending_webrtc_candidates:
            self._pending_webrtc_candidates[session_id].append(candidate)
            return
        candidate_context = _webrtc_candidate_debug_context(candidate)
        LOGGER.debug(
            "X-Sense camera WebRTC HA ICE candidate ignored for missing session: %s",
            _camera_debug_context(entity, session_id, **candidate_context)
            if entity is not None
            else {"session": _short_id(session_id), **candidate_context},
        )

    @callback
    def close_webrtc_session(self, session_id: str) -> None:
        """Close an X-Sense WebRTC signaling session."""
        entity = self._current_entity()
        session = self._webrtc_sessions.pop(session_id, None)
        self._pending_webrtc_candidates.pop(session_id, None)
        self._stop_webrtc_keepalive(session_id)
        if session is not None:
            _unmark_camera_webrtc_live(self.hass, getattr(entity, "sn", None))
        LOGGER.debug(
            "X-Sense camera WebRTC session close requested: %s",
            _camera_debug_context(
                entity,
                session_id,
                had_session=session is not None,
                remaining_sessions=len(self._webrtc_sessions),
            )
            if entity is not None
            else {
                "session": _short_id(session_id),
                "had_session": session is not None,
                "remaining_sessions": len(self._webrtc_sessions),
            },
        )
        if session is not None:
            self.hass.async_create_task(session.close())
        super().close_webrtc_session(session_id)

    async def async_will_remove_from_hass(self) -> None:
        """Stop any WebRTC live view session when Home Assistant removes the entity."""
        sessions = list(self._webrtc_sessions.values())
        self._webrtc_sessions.clear()
        self._pending_webrtc_candidates.clear()
        for keepalive_session_id in list(self._webrtc_keepalive_tasks):
            self._stop_webrtc_keepalive(keepalive_session_id)
        entity = self._current_entity()
        for _session in sessions:
            _unmark_camera_webrtc_live(self.hass, getattr(entity, "sn", None))
        for session in sessions:
            await session.close()
        await super().async_will_remove_from_hass()

    def _start_webrtc_keepalive(self, entity, session_id: str, ticket) -> None:
        """Keep an APK WebRTC live session awake while HA owns the offer."""
        self._stop_webrtc_keepalive(session_id)
        interval = _webrtc_keepalive_interval(ticket)
        task = self.hass.async_create_task(
            self._async_webrtc_keepalive_loop(entity, session_id, interval)
        )
        self._webrtc_keepalive_tasks[session_id] = task
        LOGGER.debug(
            "X-Sense camera WebRTC keepalive started: %s",
            _camera_debug_context(
                entity,
                session_id,
                keepalive_interval_s=interval,
                app_stop_live_timeout=getattr(ticket, "app_stop_live_timeout", None),
            ),
        )

    def _stop_webrtc_keepalive(self, session_id: str) -> None:
        """Cancel an active WebRTC keepalive task."""
        task = self._webrtc_keepalive_tasks.pop(session_id, None)
        if task is not None and not task.done():
            task.cancel()

    async def _async_webrtc_keepalive_loop(
        self, entity, session_id: str, interval: int
    ) -> None:
        """Send periodic APK live-view keepalives for the native WebRTC path."""
        try:
            while session_id in self._webrtc_sessions:
                await asyncio.sleep(interval)
                if session_id not in self._webrtc_sessions:
                    return
                try:
                    await self.coordinator.xsense.keep_camera_live_alive(entity)
                except Exception as err:  # noqa: BLE001 - keep trying until session closes
                    LOGGER.debug(
                        "X-Sense camera WebRTC keepalive failed: %s",
                        _camera_debug_context(
                            entity,
                            session_id,
                            error=_error_debug_context(err),
                        ),
                    )
                    continue
                else:
                    LOGGER.debug(
                        "X-Sense camera WebRTC keepalive sent: %s",
                        _camera_debug_context(
                            entity,
                            session_id,
                            keepalive_interval_s=interval,
                        ),
                    )
        except asyncio.CancelledError:
            raise
        finally:
            current_task = asyncio.current_task()
            if self._webrtc_keepalive_tasks.get(session_id) is current_task:
                self._webrtc_keepalive_tasks.pop(session_id, None)


def _camera_online(entity) -> bool:
    """Return whether ADDX currently reports the camera online."""
    if entity.online is not None:
        return entity.online is True
    return entity.data.get("online") == 1


def _stream_protocol(entity) -> str | None:
    """Return the ADDX stream protocol from the camera device model."""
    protocol = entity.data.get("streamProtocol")
    if protocol is None:
        return None
    return str(protocol).lower()


def _is_native_stream_camera(entity) -> bool:
    """Return whether the camera has a Home Assistant native stream protocol."""
    protocol = _stream_protocol(entity)
    if protocol is None:
        return False
    return "rtsp" in protocol or "rtmp" in protocol


def _is_webrtc_camera(entity) -> bool:
    """Return whether the ADDX device model says this camera streams over WebRTC."""
    protocol = _stream_protocol(entity)
    if protocol is None:
        return True
    return "rtsp" not in protocol and "rtmp" not in protocol


def _camera_live_resolution(entity) -> str:
    """Return the live resolution string used by the ADDX player."""
    return camera_live_resolution(entity)


def _webrtc_keepalive_interval(ticket) -> int:
    """Return an APK live-view keepalive cadence for a WebRTC ticket."""
    try:
        timeout = int(getattr(ticket, "app_stop_live_timeout", 0) or 0)
    except (TypeError, ValueError):
        timeout = 0
    if timeout > 10:
        return max(5, min(25, timeout // 2))
    return 15


def _set_camera_data(entity, data: dict[str, object]) -> None:
    """Set camera data on real entities and lightweight test doubles."""
    if hasattr(entity, "set_data"):
        entity.set_data(data)
        return
    if isinstance(getattr(entity, "data", None), dict):
        entity.data.update(data)


def _short_id(value):
    """Return a short diagnostic id without logging full serial-like values."""
    if value in (None, ""):
        return None
    text = str(value)
    return text if len(text) <= 6 else f"...{text[-6:]}"


def _active_webrtc_camera_counts(hass) -> dict[str, int]:
    """Return active native-WebRTC camera session counts by serial."""
    return hass.data.setdefault(DOMAIN, {}).setdefault(
        "_active_webrtc_camera_counts",
        {},
    )


def _mark_camera_webrtc_live(hass, serial: object) -> None:
    """Mark one camera as actively using the native live WebRTC path."""
    if not serial:
        return
    counts = _active_webrtc_camera_counts(hass)
    key = str(serial)
    counts[key] = int(counts.get(key) or 0) + 1


def _unmark_camera_webrtc_live(hass, serial: object) -> None:
    """Clear one active native live WebRTC session marker."""
    if not serial:
        return
    domain_data = hass.data.get(DOMAIN, {})
    counts = domain_data.get("_active_webrtc_camera_counts")
    if not isinstance(counts, dict):
        return
    key = str(serial)
    remaining = int(counts.get(key) or 0) - 1
    if remaining > 0:
        counts[key] = remaining
        return
    counts.pop(key, None)
    if not counts:
        domain_data.pop("_active_webrtc_camera_counts", None)


def _camera_debug_context(entity, session_id, **extra):
    """Return debug-only camera context without SDP, tokens, or full serials."""
    context = {
        "camera": _short_id(getattr(entity, "sn", None)),
        "session": _short_id(session_id),
        "model": entity.data.get("cameraModel") or entity.data.get("modelNo"),
        "protocol": entity.data.get("streamProtocol"),
        "online": getattr(entity, "online", None),
        "device_status": entity.data.get("deviceStatus"),
        "awake": entity.data.get("awake"),
        "support_webrtc": entity.data.get("supportWebrtc"),
        "codec": entity.data.get("codec"),
        "default_codec": entity.data.get("defaultCodec"),
        "resolution": _camera_live_resolution(entity),
    }
    context.update(extra)
    return context


def _ticket_data_debug_context(ticket_data):
    """Return safe ticket metadata for debug logs."""
    if not isinstance(ticket_data, dict):
        return {"type": type(ticket_data).__name__}
    return {
        "keys": sorted(key for key in ticket_data if key not in {"sign"}),
        "has_sign": bool(ticket_data.get("sign")),
        "has_signal_ip": bool(ticket_data.get("signalServerIpAddress")),
        "ice_servers": len(ticket_data.get("iceServer") or []),
        "has_expiration": ticket_data.get("expirationTime") not in (None, ""),
        "ticket_id": _short_id(ticket_data.get("id")),
        "real_camera": _short_id(ticket_data.get("realCxSerialNumber")),
    }


def _send_remote_candidate(send_message, entity, session_id, candidate) -> None:
    """Forward an X-Sense ICE candidate to the Home Assistant WebRTC client."""
    try:
        send_message(
            WebRTCCandidate(
                RTCIceCandidateInit(
                    candidate["candidate"],
                    sdp_mid=candidate.get("sdpMid"),
                    sdp_m_line_index=candidate.get("sdpMLineIndex"),
                )
            )
        )
    except (KeyError, TypeError, ValueError) as err:
        LOGGER.debug(
            "X-Sense camera WebRTC remote ICE candidate forward failed: %s",
            _camera_debug_context(entity, session_id, error=type(err).__name__),
        )


def _sdp_debug_context(sdp: str | None) -> dict:
    """Return safe SDP shape details without logging full SDP or IPs."""
    if not isinstance(sdp, str):
        return {"type": type(sdp).__name__}
    return {
        "sdp_len": len(sdp),
        "media": [
            line.removeprefix("m=")
            for line in sdp.splitlines()
            if line.startswith("m=")
        ],
        "mids": [
            line.removeprefix("a=mid:")
            for line in sdp.splitlines()
            if line.startswith("a=mid:")
        ],
        "candidate_lines": sum(
            1 for line in sdp.splitlines() if line.startswith("a=candidate:")
        ),
    }


def _webrtc_candidate_debug_context(candidate) -> dict:
    """Return safe ICE candidate details without logging IPs or candidate strings."""
    value = getattr(candidate, "candidate", None)
    parts = value.split() if isinstance(value, str) else []
    candidate_type = None
    if "typ" in parts:
        index = parts.index("typ")
        if index + 1 < len(parts):
            candidate_type = parts[index + 1]
    return {
        "candidate_object": type(candidate).__name__,
        "candidate_present": bool(value),
        "candidate_protocol": parts[2].lower() if len(parts) > 2 else None,
        "candidate_type": candidate_type,
        "sdp_mid": getattr(candidate, "sdp_mid", None),
        "sdp_m_line_index": getattr(candidate, "sdp_m_line_index", None),
    }


def _error_debug_context(err: BaseException) -> dict:
    """Return safe exception details for debug logs."""
    text = str(err)
    return {
        "type": type(err).__name__,
        "message_len": len(text),
        "has_message": bool(text),
    }
