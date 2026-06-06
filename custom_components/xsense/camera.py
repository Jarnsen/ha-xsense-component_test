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
    WebRTCClientConfiguration,
    WebRTCError,
    WebRTCSendMessage,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api.async_xsense import camera_live_resolution, is_camera_entity
from .const import DOMAIN
from .coordinator import XSenseDataUpdateCoordinator
from .entity import XSenseEntity


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
        self._webrtc_sessions: dict[str, object] = {}
        self._webrtc_close_tasks: set[asyncio.Task] = set()
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
        if _is_webrtc_camera(entity):
            return None
        source = await self.coordinator.xsense.start_camera_live(entity)
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

        # Import the WebRTC bridge only when Home Assistant actually starts a
        # camera WebRTC session. This keeps optional media-stack imports out of
        # normal camera discovery and mirrors the app on-demand live-view path.
        webrtc_signal = await self.hass.async_add_import_executor_job(
            import_module, __package__ + ".webrtc_signal"
        )

        ticket = webrtc_signal.XSenseWebRTCTicket.from_api(entity.sn, ticket_data)
        if not ticket.is_valid:
            send_message(
                WebRTCError(
                    "xsense_webrtc_ticket_expired",
                    "X-Sense WebRTC ticket expired",
                )
            )
            return

        def remove_session() -> None:
            if self._webrtc_sessions.get(session_id) is session:
                self._webrtc_sessions.pop(session_id, None)

        session = webrtc_signal.XSenseWebRTCSession(
            session=async_get_clientsession(self.hass),
            ticket=ticket,
            offer_sdp=offer_sdp,
            resolution=_camera_live_resolution(entity),
            send_message=send_message,
            on_close=remove_session,
        )
        self._webrtc_sessions[session_id] = session
        if not await session.start():
            await session.close()
            remove_session()

    async def async_on_webrtc_candidate(self, session_id, candidate) -> None:
        """Forward a Home Assistant WebRTC candidate to X-Sense."""
        if session := self._webrtc_sessions.get(session_id):
            await session.add_candidate(candidate)

    @callback
    def close_webrtc_session(self, session_id: str) -> None:
        """Close an X-Sense WebRTC session."""
        if session := self._webrtc_sessions.pop(session_id, None):
            task = self.hass.async_create_task(session.close())
            self._webrtc_close_tasks.add(task)
            task.add_done_callback(self._webrtc_close_tasks.discard)
        super().close_webrtc_session(session_id)

    async def async_will_remove_from_hass(self) -> None:
        """Stop any live view session when Home Assistant removes the entity."""
        sessions = list(self._webrtc_sessions.values())
        self._webrtc_sessions.clear()
        for session in sessions:
            await session.close()
        close_tasks = list(self._webrtc_close_tasks)
        self._webrtc_close_tasks.clear()
        for task in close_tasks:
            with suppress(asyncio.CancelledError, Exception):
                await task
        entity = self._current_entity()
        if entity is not None and entity.data.get("cameraLiveUrl"):
            with suppress(Exception):
                await self.coordinator.xsense.stop_camera_live(entity)
        await super().async_will_remove_from_hass()


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
    return (
        protocol not in {"rtsp", "rtmp"}
        and "rtsp" not in protocol
        and "rtmp" not in protocol
    )


def _camera_live_resolution(entity) -> str:
    """Return the live resolution string used by the ADDX player."""
    return camera_live_resolution(entity)
