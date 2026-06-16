"""Support for X-Sense camera thumbnails."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass
from importlib import import_module
from urllib.parse import quote

from aiohttp import web
from homeassistant import config_entries
from homeassistant.components.camera import (
    Camera,
    CameraEntityDescription,
    CameraEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.network import get_url

from .api.async_xsense import camera_live_resolution, is_camera_entity
from .const import DOMAIN, LOGGER
from .coordinator import XSenseDataUpdateCoordinator
from .entity import XSenseEntity


@dataclass(kw_only=True, frozen=True)
class XSenseCameraEntityDescription(CameraEntityDescription):
    """Describes XSense camera entity."""


CAMERA_DESCRIPTION = XSenseCameraEntityDescription(
    key="thumbnail",
    name=None,
)

_CAMERA_STREAM_VIEW_REGISTERED = f"{DOMAIN}_camera_stream_view_registered"
_CAMERA_STREAM_TOKENS = f"{DOMAIN}_camera_stream_tokens"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up X-Sense camera entities."""
    coordinator: XSenseDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    if not hass.data.get(_CAMERA_STREAM_VIEW_REGISTERED):
        hass.http.register_view(XSenseCameraStreamView)
        hass.data[_CAMERA_STREAM_VIEW_REGISTERED] = True
    hass.data.setdefault(_CAMERA_STREAM_TOKENS, {})

    async_add_entities(
        XSenseCameraEntity(coordinator, station, CAMERA_DESCRIPTION)
        for station in coordinator.data["stations"].values()
        if is_camera_entity(station)
    )


class XSenseCameraEntity(XSenseEntity, Camera):
    """X-Sense camera thumbnail entity."""

    entity_description: XSenseCameraEntityDescription

    def __init__(
        self,
        coordinator: XSenseDataUpdateCoordinator,
        entity,
        entity_description: XSenseCameraEntityDescription,
    ) -> None:
        """Set up the camera entity."""
        Camera.__init__(self)
        self.entity_description = entity_description
        super().__init__(coordinator, entity)

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
        """Return native stream support for ffmpeg-compatible camera URLs."""
        entity = self._current_entity()
        if entity is not None and (
            _is_native_stream_camera(entity) or _is_webrtc_camera(entity)
        ):
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
        if entity is None:
            return None
        if _is_webrtc_camera(entity):
            token = self.access_tokens[-1]
            self.hass.data.setdefault(_CAMERA_STREAM_TOKENS, {})[
                (self.coordinator.entry.entry_id, self._dev_id)
            ] = token
            source = _camera_stream_source_url(
                self.hass, self.coordinator.entry.entry_id, self._dev_id, token
            )
            LOGGER.debug(
                "X-Sense camera WebRTC go2rtc stream source prepared: %s",
                _camera_debug_context(
                    entity,
                    self.coordinator.entry.entry_id,
                    stream_host=_safe_url_host(source),
                    stream_path="/api/xsense/camera_stream",
                ),
            )
            return source
        source = await self.coordinator.xsense.start_camera_live(entity)
        return source

    async def async_will_remove_from_hass(self) -> None:
        """Stop any live view session when Home Assistant removes the entity."""
        entity = self._current_entity()
        if entity is not None and entity.data.get("cameraLiveUrl"):
            with suppress(Exception):
                await self.coordinator.xsense.stop_camera_live(entity)
        await super().async_will_remove_from_hass()


class XSenseCameraStreamView(HomeAssistantView):
    """Serve an X-Sense WebRTC camera as raw H264 for go2rtc."""

    url = "/api/xsense/camera_stream/{entry_id}/{dev_id}"
    name = "api:xsense:camera_stream"
    requires_auth = False

    async def get(
        self, request: web.Request, entry_id: str, dev_id: str
    ) -> web.StreamResponse:
        """Return a raw H264 stream for the requested X-Sense camera."""
        hass: HomeAssistant = request.app["hass"]
        token = request.query.get("token")
        tokens = hass.data.get(_CAMERA_STREAM_TOKENS, {})
        if not token or tokens.get((entry_id, dev_id)) != token:
            LOGGER.debug(
                "X-Sense H264 stream rejected invalid token: %s",
                {"entry": _short_id(entry_id), "device": _short_id(dev_id)},
            )
            raise web.HTTPForbidden()

        coordinator = hass.data.get(DOMAIN, {}).get(entry_id)
        if coordinator is None:
            LOGGER.debug(
                "X-Sense H264 stream rejected unknown entry: %s",
                {"entry": _short_id(entry_id), "device": _short_id(dev_id)},
            )
            raise web.HTTPNotFound()
        entity = coordinator.data.get("stations", {}).get(dev_id)
        if entity is None or not _is_webrtc_camera(entity):
            LOGGER.debug(
                "X-Sense H264 stream rejected unknown camera: %s",
                {"entry": _short_id(entry_id), "device": _short_id(dev_id)},
            )
            raise web.HTTPNotFound()

        LOGGER.debug(
            "X-Sense H264 stream request accepted: %s",
            _camera_debug_context(
                entity, entry_id, user_agent=request.headers.get("User-Agent")
            ),
        )

        frame_queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=64)
        webrtc_signal = await hass.async_add_import_executor_job(
            import_module, __package__ + ".webrtc_signal"
        )

        ticket_data = await coordinator.xsense.get_camera_webrtc_ticket(
            entity, force_refresh=True
        )
        LOGGER.debug(
            "X-Sense H264 stream ticket response: %s",
            _ticket_data_debug_context(ticket_data),
        )
        if not isinstance(ticket_data, dict):
            raise web.HTTPServiceUnavailable(
                reason="Unable to get X-Sense WebRTC ticket"
            )
        try:
            ticket = webrtc_signal.XSenseWebRTCTicket.from_api(entity.sn, ticket_data)
        except (KeyError, TypeError, ValueError) as err:
            raise web.HTTPServiceUnavailable(
                reason="Unable to parse X-Sense WebRTC ticket"
            ) from err
        if not ticket.is_valid:
            raise web.HTTPServiceUnavailable(reason="X-Sense WebRTC ticket expired")

        async def refresh_ticket():
            refreshed = await coordinator.xsense.get_camera_webrtc_ticket(
                entity, force_refresh=True
            )
            if not isinstance(refreshed, dict):
                return None
            with suppress(KeyError, TypeError, ValueError):
                return webrtc_signal.XSenseWebRTCTicket.from_api(entity.sn, refreshed)
            return None

        session = webrtc_signal.XSenseH264StreamSession(
            session=async_get_clientsession(hass),
            ticket=ticket,
            resolution=_camera_live_resolution(entity),
            frame_queue=frame_queue,
            camera_online=_camera_online(entity),
            refresh_ticket=refresh_ticket,
        )
        if not await session.start():
            raise web.HTTPServiceUnavailable(
                reason="Unable to start X-Sense WebRTC stream"
            )
        LOGGER.debug(
            "X-Sense H264 stream session started: %s",
            _camera_debug_context(entity, entry_id),
        )

        response = web.StreamResponse(
            status=200,
            headers={
                "Content-Type": "video/h264",
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )
        await response.prepare(request)
        LOGGER.debug(
            "X-Sense H264 stream response prepared: %s",
            _camera_debug_context(entity, entry_id, content_type="video/h264"),
        )

        try:
            while True:
                frame = await frame_queue.get()
                if frame is None:
                    LOGGER.debug(
                        "X-Sense H264 stream frame queue ended: %s",
                        _camera_debug_context(entity, entry_id),
                    )
                    break
                await response.write(frame)
        except (asyncio.CancelledError, ConnectionError):
            raise
        except Exception as err:  # noqa: BLE001 - go2rtc may close the source socket
            LOGGER.debug("X-Sense H264 stream response stopped", exc_info=err)
        finally:
            await session.close()
            with suppress(Exception):
                await response.write_eof()
            LOGGER.debug(
                "X-Sense H264 stream response closed: %s",
                _camera_debug_context(entity, entry_id),
            )
        return response


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


def _camera_stream_source_url(
    hass: HomeAssistant, entry_id: str, dev_id: str, token: str
) -> str:
    """Return the raw H264 URL consumed by AlexxIT/WebRTC go2rtc."""
    base_url = get_url(hass, allow_internal=True).rstrip("/")
    safe_entry_id = quote(entry_id, safe="")
    safe_dev_id = quote(dev_id, safe="")
    safe_token = quote(token, safe="")
    return (
        f"{base_url}/api/xsense/camera_stream/"
        f"{safe_entry_id}/{safe_dev_id}?token={safe_token}"
    )


def _safe_url_host(value: str) -> str | None:
    with suppress(Exception):
        from urllib.parse import urlparse

        return urlparse(value).netloc or None
    return None


def _short_id(value):
    """Return a short diagnostic id without logging full serial-like values."""
    if value in (None, ""):
        return None
    text = str(value)
    return text if len(text) <= 6 else f"...{text[-6:]}"


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
