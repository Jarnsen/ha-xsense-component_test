"""Support for X-Sense camera thumbnails."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass

from homeassistant import config_entries
from homeassistant.components.camera import (
    Camera,
    CameraEntityDescription,
    CameraEntityFeature,
)
from homeassistant.components.camera.webrtc import (
    WebRTCClientConfiguration,
    WebRTCError,
    WebRTCSendMessage,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api.async_xsense import is_camera_entity
from .const import DOMAIN, LOGGER
from .coordinator import XSenseDataUpdateCoordinator
from .entity import XSenseEntity
from .webrtc_signal import (
    XSenseWebRTCSession,
    XSenseWebRTCTicket,
)


@dataclass(kw_only=True, frozen=True)
class XSenseCameraEntityDescription(CameraEntityDescription):
    """Describes XSense camera entity."""


CAMERA_DESCRIPTION = XSenseCameraEntityDescription(
    key="thumbnail",
    name=None,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up X-Sense camera entities."""
    coordinator: XSenseDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

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
        self._webrtc_sessions: dict[str, XSenseWebRTCSession] = {}
        super().__init__(coordinator, entity)

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
        return entity is not None and (
            bool(entity.data.get("cameraLiveUrl")) or bool(self._webrtc_sessions)
        )

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
        source = await self.coordinator.xsense.start_camera_live(entity)
        if _url_scheme(source) == "webrtc":
            LOGGER.info(
                "X-Sense camera %s returned an ADDX WebRTC stream that Home Assistant's native stream worker cannot open",
                entity.entity_id,
            )
            return None
        return source

    @callback
    def _async_get_webrtc_client_configuration(self) -> WebRTCClientConfiguration:
        """Return the Home Assistant browser WebRTC client configuration."""
        return WebRTCClientConfiguration()

    async def async_handle_async_webrtc_offer(
        self, offer_sdp: str, session_id: str, send_message: WebRTCSendMessage
    ) -> None:
        """Handle a Home Assistant WebRTC offer with ADDX signaling."""
        entity = self._current_entity()
        if entity is None or not _is_webrtc_camera(entity):
            send_message(
                WebRTCError(
                    "xsense_webrtc_unsupported",
                    "Camera does not support X-Sense WebRTC",
                )
            )
            return

        ticket_data = await self.coordinator.xsense.get_camera_webrtc_ticket(entity)
        if not isinstance(ticket_data, dict):
            send_message(
                WebRTCError(
                    "xsense_webrtc_ticket_failed",
                    "Unable to get X-Sense WebRTC ticket",
                )
            )
            return

        session = XSenseWebRTCSession(
            session=async_get_clientsession(self.hass),
            ticket=XSenseWebRTCTicket.from_api(entity.sn, ticket_data),
            offer_sdp=offer_sdp,
            resolution=_camera_live_resolution(entity),
            send_message=send_message,
        )
        self._webrtc_sessions[session_id] = session
        await session.start()

    async def async_on_webrtc_candidate(self, session_id, candidate) -> None:
        """Forward a Home Assistant WebRTC candidate to X-Sense."""
        if session := self._webrtc_sessions.get(session_id):
            await session.add_candidate(candidate)

    @callback
    def close_webrtc_session(self, session_id: str) -> None:
        """Close an X-Sense WebRTC session."""
        if session := self._webrtc_sessions.pop(session_id, None):
            self.hass.async_create_task(session.close())
        super().close_webrtc_session(session_id)

    async def async_will_remove_from_hass(self) -> None:
        """Stop any live view session when Home Assistant removes the entity."""
        for session_id in list(self._webrtc_sessions):
            self.close_webrtc_session(session_id)
        entity = self._current_entity()
        if entity is not None and entity.data.get("cameraLiveUrl"):
            with suppress(Exception):
                await self.coordinator.xsense.stop_camera_live(entity)
        await super().async_will_remove_from_hass()


def _url_scheme(url: str | None) -> str | None:
    """Return the URL scheme without exposing the full stream URL."""
    if not isinstance(url, str) or "://" not in url:
        return None
    return url.split("://", 1)[0].lower()


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
        return entity.data.get("supportWebrtc") is True
    return (
        protocol not in {"rtsp", "rtmp"}
        and "rtsp" not in protocol
        and "rtmp" not in protocol
    )


def _camera_live_resolution(entity) -> str:
    """Return the live resolution string used by the ADDX player."""
    value = entity.data.get("liveResolution") or entity.data.get("recResolution")
    if isinstance(value, str) and "x" in value:
        return value
    return "auto"
