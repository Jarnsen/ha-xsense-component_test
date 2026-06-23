"""Support for X-Sense camera thumbnails."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from importlib import import_module
from secrets import token_urlsafe
from types import SimpleNamespace

from aiohttp import WSMsgType, web
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
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.network import get_url
from webrtc_models import RTCIceCandidateInit

from .api.async_xsense import camera_live_resolution, is_camera_entity
from .api.exceptions import APIFailure
from .const import (
    CAMERA_LIVE_VIEW_MODES,
    CAMERA_LIVE_VIEW_MODE_WEBRTC_SIGNAL,
    CONF_CAMERA_LIVE_VIEW_MODE,
    DEFAULT_CAMERA_LIVE_VIEW_MODE,
    DOMAIN,
    LOGGER,
)
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

    for station in coordinator_stations(coordinator).values():
        if is_camera_entity(station):
            entities.append(_camera_entity(coordinator, station))
            seen_entity_ids.add(station.entity_id)

    for device in coordinator_devices(coordinator).values():
        if not is_camera_entity(device) or device.entity_id in seen_entity_ids:
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
    return XSenseCameraEntity(
        coordinator, entity, CAMERA_DESCRIPTION, station_id=station_id
    )


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
        """Return stream support for X-Sense live URLs."""
        entity = self._current_entity()
        if entity is not None and is_camera_entity(entity):
            return CameraEntityFeature.STREAM
        return CameraEntityFeature(0)

    @property
    def is_streaming(self) -> bool:
        """Return whether the camera has an active live stream session."""
        entity = self._current_entity()
        return entity is not None and bool(entity.data.get("cameraLiveUrl"))

    async def _async_get_supported_webrtc_provider(self, fn):
        """Skip HA WebRTC provider probing unless the experimental bridge is enabled."""
        if (
            _camera_live_view_mode(self.coordinator)
            != CAMERA_LIVE_VIEW_MODE_WEBRTC_SIGNAL
        ):
            return None
        return await super()._async_get_supported_webrtc_provider(fn)

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
        if (
            _camera_live_view_mode(self.coordinator)
            == CAMERA_LIVE_VIEW_MODE_WEBRTC_SIGNAL
            and _is_webrtc_camera(entity)
        ):
            source = await _webrtc_bridge_source(self.hass, self.coordinator, entity)
            debug_context = _camera_debug_context(
                entity,
                None,
                live_view_mode=_camera_live_view_mode(self.coordinator),
                source_protocol=_stream_source_protocol(source),
            )
            if source is None:
                LOGGER.debug(
                    "X-Sense camera WebRTC bridge source unavailable: %s",
                    debug_context,
                )
            else:
                LOGGER.debug(
                    "X-Sense camera WebRTC bridge source prepared for go2rtc: %s",
                    debug_context,
                )
            return source

        try:
            source = await self.coordinator.xsense.start_camera_live(entity)
        except APIFailure as err:
            LOGGER.debug(
                "X-Sense camera live source unavailable from stream endpoint: %s",
                _camera_debug_context(
                    entity,
                    None,
                    live_view_mode=_camera_live_view_mode(self.coordinator),
                    error=_error_debug_context(err),
                ),
            )
            return None
        source_protocol = _stream_source_protocol(source)
        if not _home_assistant_stream_source_supported(source):
            with suppress(Exception):
                await self.coordinator.xsense.stop_camera_live(entity)
            LOGGER.debug(
                "X-Sense camera live source rejected by Home Assistant stream path: %s",
                _camera_debug_context(
                    entity,
                    None,
                    live_view_mode=_camera_live_view_mode(self.coordinator),
                    source_protocol=source_protocol,
                ),
            )
            return None
        LOGGER.debug(
            "X-Sense camera live source started: %s",
            _camera_debug_context(
                entity,
                None,
                live_view_mode=_camera_live_view_mode(self.coordinator),
                source_protocol=source_protocol,
            ),
        )
        return source

    async def async_will_remove_from_hass(self) -> None:
        """Stop any live view session when Home Assistant removes the entity."""
        entity = self._current_entity()
        if entity is not None and entity.data.get("cameraLiveUrl"):
            with suppress(Exception):
                await self.coordinator.xsense.stop_camera_live(entity)
        await super().async_will_remove_from_hass()


class XSenseWebRTCCameraEntity(XSenseCameraEntity):
    """X-Sense camera entity that relays the APK WebRTC signaling path."""

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
        self._webrtc_candidate_counts: dict[str, int] = {}

    @property
    def supported_features(self) -> CameraEntityFeature:
        """Return X-Sense WebRTC stream support."""
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
        """Return no live URL because this mode uses X-Sense WebRTC signaling."""
        entity = self._current_entity()
        if entity is not None:
            LOGGER.debug(
                "X-Sense camera WebRTC uses APK signaling relay: %s",
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
        self._webrtc_candidate_counts[session_id] = 0
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
        await self._flush_pending_webrtc_candidates(entity, session_id, session)
        try:
            answer = await session.start()
        except Exception as err:  # noqa: BLE001 - HA frontend needs a clean error
            self._webrtc_sessions.pop(session_id, None)
            self._pending_webrtc_candidates.pop(session_id, None)
            self._webrtc_candidate_counts.pop(session_id, None)
            await self._async_close_webrtc_live_session(
                entity,
                session_id,
                session,
                stop_live=not self._webrtc_sessions,
            )
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
        preserved_candidate_count = (
            self._webrtc_candidate_counts.get(preserve_pending_session_id)
            if preserve_pending_session_id is not None
            else None
        )
        self._pending_webrtc_candidates.clear()
        self._webrtc_candidate_counts.clear()
        if preserve_pending_session_id is not None and preserved_pending is not None:
            self._pending_webrtc_candidates[preserve_pending_session_id] = (
                preserved_pending
            )
        if (
            preserve_pending_session_id is not None
            and preserved_candidate_count is not None
        ):
            self._webrtc_candidate_counts[preserve_pending_session_id] = (
                preserved_candidate_count
            )
        if not sessions:
            return
        LOGGER.debug(
            "X-Sense camera closing previous WebRTC signal sessions before new offer: %s",
            {"count": len(sessions)},
        )
        self._webrtc_sessions.clear()
        for session in sessions:
            await self._async_close_webrtc_live_session(
                self._current_entity(), None, session, stop_live=False
            )

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
        candidate_context = _webrtc_candidate_debug_context(candidate)
        candidate_count = self._webrtc_candidate_counts.get(session_id, 0) + 1
        self._webrtc_candidate_counts[session_id] = candidate_count
        if session := self._webrtc_sessions.get(session_id):
            if _should_log_webrtc_candidate_count(candidate_count):
                LOGGER.debug(
                    "X-Sense camera WebRTC HA ICE candidate received: %s",
                    _camera_debug_context(
                        entity,
                        session_id,
                        candidate_receive_count=candidate_count,
                        **candidate_context,
                    )
                    if entity is not None
                    else {
                        "session": _short_id(session_id),
                        "candidate_receive_count": candidate_count,
                        **candidate_context,
                    },
                )
            await session.add_candidate(candidate)
            return
        if session_id in self._pending_webrtc_candidates:
            self._pending_webrtc_candidates[session_id].append(candidate)
            queued_candidate_count = len(self._pending_webrtc_candidates[session_id])
            if _should_log_webrtc_candidate_count(queued_candidate_count):
                LOGGER.debug(
                    "X-Sense camera WebRTC HA ICE candidate queued before signal session: %s",
                    _camera_debug_context(
                        entity,
                        session_id,
                        queued_candidate_count=queued_candidate_count,
                        **candidate_context,
                    )
                    if entity is not None
                    else {
                        "session": _short_id(session_id),
                        "queued_candidate_count": queued_candidate_count,
                        **candidate_context,
                    },
                )
            return
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
        self._webrtc_candidate_counts.pop(session_id, None)
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
            self.hass.async_create_task(
                self._async_close_webrtc_live_session(
                    entity,
                    session_id,
                    session,
                    stop_live=not self._webrtc_sessions,
                )
            )
        super().close_webrtc_session(session_id)

    async def async_will_remove_from_hass(self) -> None:
        """Stop any WebRTC live view session when Home Assistant removes the entity."""
        entity = self._current_entity()
        sessions = list(self._webrtc_sessions.values())
        self._webrtc_sessions.clear()
        self._pending_webrtc_candidates.clear()
        self._webrtc_candidate_counts.clear()
        for session in sessions:
            await self._async_close_webrtc_live_session(
                entity, None, session, stop_live=True
            )
        await super().async_will_remove_from_hass()

    async def _async_close_webrtc_live_session(
        self, entity, session_id: str | None, session, *, stop_live: bool
    ) -> None:
        """Close the signal session and release the ADDX live session."""
        with suppress(Exception):
            await session.close()
        if entity is None:
            return
        if not stop_live:
            return
        _set_camera_data(entity, {"cameraWebrtcTicket": None})
        with suppress(Exception):
            await self.coordinator.xsense.stop_camera_live(entity)
        LOGGER.debug(
            "X-Sense camera WebRTC live session released: %s",
            _camera_debug_context(entity, session_id),
        )


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


def _camera_live_view_mode(coordinator) -> str:
    """Return the configured camera live view mode."""
    entry = getattr(coordinator, "entry", None)
    options = getattr(entry, "options", {}) if entry is not None else {}
    mode = options.get(CONF_CAMERA_LIVE_VIEW_MODE, DEFAULT_CAMERA_LIVE_VIEW_MODE)
    if mode not in CAMERA_LIVE_VIEW_MODES:
        return DEFAULT_CAMERA_LIVE_VIEW_MODE
    return mode


async def _webrtc_bridge_source(
    hass: HomeAssistant,
    coordinator: XSenseDataUpdateCoordinator,
    entity,
) -> str | None:
    """Return a go2rtc-compatible source from the local X-Sense WebRTC bridge."""
    webrtc_bridge = await hass.async_add_import_executor_job(
        import_module, __package__ + ".webrtc_bridge"
    )
    return await webrtc_bridge.async_get_xsense_bridge_stream_source(
        hass, coordinator, entity
    )


class XSenseWebRTCSignalView(HomeAssistantView):
    """Handle go2rtc WebRTC offers through the X-Sense WebRTC signal path."""

    url = "/api/xsense/webrtc/{token}"
    name = "api:xsense:webrtc"
    requires_auth = False

    async def get(self, request: web.Request, token: str) -> web.WebSocketResponse:
        """Handle go2rtc WebSocket WebRTC signaling."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        hass: HomeAssistant = request.app["hass"]
        context = _pop_webrtc_signal_context(hass, token)
        if context is None:
            await ws.close()
            return ws

        coordinator = context["coordinator"]
        entity = _webrtc_signal_entity(coordinator, context)
        if entity is None:
            await ws.close()
            return ws

        session = None
        try:
            async for msg in ws:
                if msg.type is not WSMsgType.TEXT:
                    continue
                payload = msg.json()
                message_type = payload.get("type")
                if message_type == "webrtc/offer":
                    offer_sdp = str(payload.get("value") or "")
                    session, answer = await _async_xsense_webrtc_session(
                        hass,
                        coordinator,
                        entity,
                        offer_sdp,
                        lambda candidate: hass.async_create_task(
                            _async_send_go2rtc_candidate(ws, candidate)
                        ),
                    )
                    if answer is None:
                        await ws.send_json({"type": "error", "value": "signal failed"})
                        await ws.close()
                        break
                    await ws.send_json({"type": "webrtc/answer", "value": answer})
                    session.start_forwarding_remote_candidates()
                elif message_type == "webrtc/candidate" and session is not None:
                    candidate = _go2rtc_candidate(payload.get("value"))
                    if candidate is not None:
                        await session.add_candidate(candidate)
        finally:
            if session is not None:
                with suppress(Exception):
                    await session.close()
        return ws

    async def post(self, request: web.Request, token: str) -> web.Response:
        """Return an SDP answer for a go2rtc WebRTC source offer."""
        hass: HomeAssistant = request.app["hass"]
        context = _pop_webrtc_signal_context(hass, token)
        if context is None:
            return web.Response(status=404)

        coordinator = context["coordinator"]
        entity = _webrtc_signal_entity(coordinator, context)
        if entity is None:
            return web.Response(status=404)

        offer_sdp = await request.text()
        answer = await _async_xsense_webrtc_answer(hass, coordinator, entity, offer_sdp)
        if answer is None:
            return web.Response(status=502)
        return web.Response(text=answer, content_type="application/sdp")


def register_webrtc_signal_view(hass: HomeAssistant) -> None:
    """Register the X-Sense WebRTC signaling HTTP view once."""
    data = hass.data.setdefault(DOMAIN, {})
    if data.get("_webrtc_signal_view_registered"):
        return
    hass.http.register_view(XSenseWebRTCSignalView)
    data["_webrtc_signal_view_registered"] = True


def _webrtc_signal_source(
    hass: HomeAssistant,
    coordinator: XSenseDataUpdateCoordinator,
    camera_entity: XSenseCameraEntity,
    entity,
) -> str:
    """Return a go2rtc WebRTC source URL for the X-Sense signaling relay."""
    token = token_urlsafe(24)
    hass.data.setdefault(DOMAIN, {}).setdefault("_webrtc_signal_tokens", {})[token] = {
        "coordinator": coordinator,
        "dev_id": camera_entity._dev_id,
        "station_id": camera_entity._station_id,
    }
    base_url = _websocket_base_url(get_url(hass, prefer_external=False))
    return f"webrtc:{base_url}/api/xsense/webrtc/{token}"


def _websocket_base_url(base_url: str) -> str:
    """Return a websocket URL base for go2rtc signaling."""
    if base_url.startswith("https://"):
        return "wss://" + base_url.removeprefix("https://")
    if base_url.startswith("http://"):
        return "ws://" + base_url.removeprefix("http://")
    return base_url


def _pop_webrtc_signal_context(hass: HomeAssistant, token: str) -> dict | None:
    """Pop a one-use WebRTC signal token context."""
    tokens = hass.data.setdefault(DOMAIN, {}).setdefault("_webrtc_signal_tokens", {})
    return tokens.pop(token, None)


def _webrtc_signal_entity(coordinator, context: dict):
    """Return the entity targeted by a WebRTC signal token."""
    data = coordinator.data or {}
    dev_id = context.get("dev_id")
    if context.get("station_id") is not None:
        return data.get("devices", {}).get(dev_id)
    return data.get("stations", {}).get(dev_id)


async def _async_xsense_webrtc_answer(
    hass: HomeAssistant,
    coordinator: XSenseDataUpdateCoordinator,
    entity,
    offer_sdp: str,
) -> str | None:
    """Relay a go2rtc SDP offer through the X-Sense WebRTC signal server."""
    session, answer = await _async_xsense_webrtc_session(
        hass, coordinator, entity, offer_sdp
    )
    if session is not None:
        with suppress(Exception):
            await session.close()
    return answer


async def _async_xsense_webrtc_session(
    hass: HomeAssistant,
    coordinator: XSenseDataUpdateCoordinator,
    entity,
    offer_sdp: str,
    remote_candidate_callback=None,
):
    """Return an active X-Sense WebRTC signal session and SDP answer."""
    ticket_data = await coordinator.xsense.get_camera_webrtc_ticket(
        entity, force_refresh=True
    )
    LOGGER.debug(
        "X-Sense camera WebRTC ticket response: %s",
        _ticket_data_debug_context(ticket_data),
    )
    if not isinstance(ticket_data, dict):
        return None, None

    webrtc_signal = await hass.async_add_import_executor_job(
        import_module, __package__ + ".webrtc_signal"
    )
    try:
        ticket = webrtc_signal.XSenseWebRTCTicket.from_api(entity.sn, ticket_data)
    except (KeyError, TypeError, ValueError) as err:
        LOGGER.debug(
            "X-Sense camera WebRTC ticket parse failed: %s",
            _camera_debug_context(entity, None, error=type(err).__name__),
        )
        return None, None
    if not ticket.is_valid:
        LOGGER.debug(
            "X-Sense camera WebRTC ticket expired or incomplete: %s",
            _camera_debug_context(entity, None),
        )
        return None, None

    session = webrtc_signal.XSenseWebRTCSignalSession(
        session=async_get_clientsession(hass),
        ticket=ticket,
        offer_sdp=offer_sdp,
        resolution=_camera_live_resolution(entity),
        camera_online=_camera_online(entity),
        remote_candidate_callback=remote_candidate_callback,
    )
    try:
        return session, await session.start()
    except Exception as err:  # noqa: BLE001 - go2rtc gets a clean HTTP failure
        LOGGER.debug(
            "X-Sense camera WebRTC signal relay failed: %s",
            _camera_debug_context(entity, None, error=_error_debug_context(err)),
        )
        with suppress(Exception):
            await session.close()
        return None, None


async def _async_send_go2rtc_candidate(
    ws: web.WebSocketResponse, candidate: dict
) -> None:
    """Forward an X-Sense ICE candidate to go2rtc."""
    value = candidate.get("candidate")
    if isinstance(value, str) and value and not ws.closed:
        await ws.send_json({"type": "webrtc/candidate", "value": value})


def _go2rtc_candidate(value):
    """Return a candidate object from go2rtc's candidate string."""
    if not isinstance(value, str) or not value:
        return None
    return SimpleNamespace(candidate=value, sdp_mid="0", sdp_m_line_index=0)


def _stream_source_protocol(source: str | None) -> str | None:
    """Return a stream source protocol without exposing the source URL."""
    if not isinstance(source, str) or "://" not in source:
        return None
    return source.split("://", 1)[0].lower()


def _home_assistant_stream_source_supported(source: str | None) -> bool:
    """Return whether Home Assistant's stream worker can open this source URL."""
    return _stream_source_protocol(source) in {"rtsp", "rtmp"}


def _is_webrtc_camera(entity) -> bool:
    """Return whether the ADDX device model says this camera streams over WebRTC."""
    protocol = _stream_protocol(entity)
    if protocol is None:
        return True
    return "rtsp" not in protocol and "rtmp" not in protocol


def _camera_live_resolution(entity) -> str:
    """Return the live resolution string used by the ADDX player."""
    return camera_live_resolution(entity)


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


def _should_log_webrtc_candidate_count(count: int) -> bool:
    """Return whether a candidate count should emit a per-candidate camera log."""
    return count <= 1 or count in {5, 10, 25, 50, 100}


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
