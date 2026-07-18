"""DataUpdateCoordinator for the XSense integration."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.logging import catch_log_exception

from .python_xsense import AsyncXSense, House
from .python_xsense.async_xsense import is_camera_entity
from .python_xsense.event_parser import (
    camera_ai_history_event_key as _camera_ai_history_event_key,
    camera_event_history_event_key as _camera_event_history_event_key,
    camera_event_history_records as _camera_event_history_records,
    camera_event_history_station_data as _camera_event_history_station_data,
    is_presence_topic as _is_presence_topic,
    is_self_test_topic as _is_self_test_topic,
    mqtt_identifier_candidates as _mqtt_identifier_candidates,
    mqtt_reported_data as _mqtt_reported_data,
    mqtt_topic_kind as _mqtt_topic_kind,
    normalize_self_test_report as _normalize_self_test_report,
    self_test_report_payload as _self_test_report_payload,
)
from .python_xsense.exceptions import APIFailure, AuthFailed, NotFoundError, SessionExpired
from .const import (
    CAMERA_AI_HISTORY_SCAN_INTERVAL,
    CAMERA_AI_SERVICE_AVAILABLE,
    CAMERA_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    POLL_INTERVAL_MIN,
)
from .mqtt import DEFAULT_ENCODING, DEFAULT_SUBSCRIBE_QOS, XSenseMQTT

_IGNORED_TOPIC_SUFFIXES = ("/update/accepted", "/update/documents", "/update/rejected")

KEYPAD_CODE_EVENT_TYPE = "xsense_keypad_code"
SELF_TEST_EVENT_TYPE = "xsense_self_test"


async def _async_init_and_login(xsense: AsyncXSense, email: str, password: str) -> None:
    """Initialize the X-Sense client and log in."""
    await xsense.init()
    await xsense.login(email, password)


class XSenseDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """A XSense Data Update Coordinator."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the XSense hub."""
        LOGGER.debug("XSenseDataUpdateCoordinator:__init__")
        self.entry = entry
        self.xsense: AsyncXSense = None
        self._initialized: bool = False
        self._camera_initialized: bool = False
        self._last_camera_update_attempt: datetime | None = None
        self._camera_station_cache: dict[str, Any] = {}
        self._camera_ai_history_seen: set[str] = set()
        self._camera_ai_history_unsub = None
        self._camera_ai_history_lock = asyncio.Lock()
        self._startup_refresh_complete = False
        self._deferred_refresh_unsub = None
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            always_update=True,
        )
        self.mqtt_servers: dict[str, XSenseMQTT] = {}

    def mqtt_server(self, host: str):
        """Get mqtt server instance for specific host."""
        return self.mqtt_servers.get(host)

    async def async_shutdown(self) -> None:
        """Disconnect all MQTT clients owned by this coordinator."""
        if self._deferred_refresh_unsub is not None:
            self._deferred_refresh_unsub()
            self._deferred_refresh_unsub = None

        if self._camera_ai_history_unsub is not None:
            self._camera_ai_history_unsub()
            self._camera_ai_history_unsub = None

        mqtt_servers = list(self.mqtt_servers.values())
        self.mqtt_servers.clear()

        for mqtt in mqtt_servers:
            try:
                await mqtt.async_disconnect(disconnect_paho_client=True)
            except Exception as ex:  # noqa: BLE001
                LOGGER.warning("Could not disconnect XSense MQTT client: %s", ex)

        if self.xsense is not None:
            await self.xsense.close()

    def async_start_camera_ai_history_polling(self, *, immediate: bool = True) -> None:
        """Start the lightweight camera AI-history poller."""
        if self._camera_ai_history_unsub is not None:
            LOGGER.debug("X-Sense camera history polling already started")
            return

        self._camera_ai_history_unsub = async_track_time_interval(
            self.hass,
            self._async_poll_camera_ai_history,
            timedelta(seconds=CAMERA_AI_HISTORY_SCAN_INTERVAL),
        )
        LOGGER.debug(
            "X-Sense camera history polling started: interval_s=%s",
            CAMERA_AI_HISTORY_SCAN_INTERVAL,
        )
        if immediate and hasattr(self.hass, "async_create_task"):
            self.hass.async_create_task(self._async_poll_camera_ai_history(None))

    def async_schedule_deferred_refresh(self) -> None:
        """Schedule live cloud/MQTT refresh work after HA startup."""
        if self._deferred_refresh_unsub is not None:
            return

        @callback
        def _schedule_refresh(_event_or_now) -> None:
            self._deferred_refresh_unsub = None
            self._deferred_refresh_unsub = async_call_later(
                self.hass, 30, _request_refresh
            )

        @callback
        def _request_refresh(_now) -> None:
            self._deferred_refresh_unsub = None
            self.hass.create_task(self.async_request_refresh())

        if getattr(self.hass, "is_running", False):
            _schedule_refresh(None)
        else:
            self._deferred_refresh_unsub = self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED,
                _schedule_refresh,
            )

    async def _async_poll_camera_ai_history(self, _now) -> None:
        """Poll camera AI history outside the heavy coordinator refresh."""
        try:
            updated = await self._update_camera_ai_history()
        except (SessionExpired, AuthFailed):
            LOGGER.debug("X-Sense camera history poll requested auth refresh")
            await self.async_request_refresh()
            return
        except Exception as ex:  # noqa: BLE001
            LOGGER.warning("Could not poll X-Sense camera history: %s", ex)
            return
        LOGGER.debug("X-Sense camera history poll finished: updated=%s", updated)
        if updated:
            self.async_update_listeners()

    async def _connect(self) -> None:
        email = self.entry.data[CONF_EMAIL]
        password = self.entry.data[CONF_PASSWORD]

        if self.xsense is not None:
            await self.xsense.close()

        xsense = AsyncXSense(
            async_get_clientsession(self.hass), language=self.hass.config.language
        )

        try:
            await _async_init_and_login(xsense, email, password)
        except AuthFailed as ex:
            raise ConfigEntryAuthFailed(f"Login failed: {ex!s}") from ex
        except APIFailure as ex:
            raise UpdateFailed(f"XSense API Issue: {ex}") from ex

        self.xsense = xsense
        self._initialized = False
        self._camera_initialized = False
        self._last_camera_update_attempt = None
        self._camera_station_cache = {}

    async def _async_update_data(self) -> dict[str, Any]:
        if self.xsense is None:
            await self._connect()
        startup_refresh = not self._startup_refresh_complete
        devices = await self.get_devices(
            include_camera_history=not startup_refresh,
            include_camera_update=True,
            include_state_update=True,
        )
        self._startup_refresh_complete = True

        if startup_refresh:
            LOGGER.debug("X-Sense startup refresh skipped MQTT live update request")
            return devices

        if self.xsense and self.xsense.houses:
            for h in self.xsense.houses.values():
                mqtt = self.mqtt_server(h.mqtt_server)
                if not mqtt:
                    mqtt = self.setup_mqtt(h)
                    await mqtt.async_connect()

                await self.assure_subscriptions(h)

                if mqtt.connected:
                    await self.request_device_updates(mqtt, h)

        return devices

    async def get_all_devices(self, retry=False):
        """Retrieve all devices as a dict."""
        devices = {}
        try:
            await self.xsense.load_all()
            for h in self.xsense.houses.values():
                for s in h.stations.values():
                    await self.xsense.get_state(s)
                    devices.update(s.devices.items())
        except (SessionExpired, AuthFailed) as ex:
            if not retry:
                await self._connect()
                return await self.get_all_devices(retry=True)
            raise ConfigEntryAuthFailed(
                "Could not update, session no longer valid"
            ) from ex
        except APIFailure as ex:
            raise UpdateFailed(f"XSense API Issue: {ex}") from ex
        else:
            return devices

    def _get_station_by_id(self, identifier: str):
        if not self.xsense:
            return None
        for h in self.xsense.houses.values():
            if s := h.get_station_by_sn(identifier):
                return s
        return None

    def _get_station_by_shadow_name(self, shadow_name: str):
        """Return the station matching an AWS IoT shadow thing name."""
        if not self.xsense:
            return None
        for h in self.xsense.houses.values():
            for s in h.stations.values():
                if s.shadow_name == shadow_name:
                    return s
        return None

    def _get_station_by_device_sn(self, device_sn: str | None):
        """Return the station containing the device serial number."""
        if not self.xsense or not device_sn:
            return None
        for h in self.xsense.houses.values():
            for s in h.stations.values():
                if s.sn == device_sn or s.get_device_by_sn(device_sn):
                    return s
        return None

    async def get_stations(self, retry=False):
        """Retrieve all stations."""
        stations = []
        try:
            await self.xsense.load_all()
            for h in self.xsense.houses.values():
                for s in h.stations.values():
                    await self.xsense.get_station_state(s)
                    await self.xsense.get_state(s)
                    stations.append(s)
        except (SessionExpired, AuthFailed) as ex:
            if not retry:
                await self._connect()
                return await self.get_stations(retry=True)
            raise ConfigEntryAuthFailed(
                "Could not update, session no longer valid"
            ) from ex
        except APIFailure as ex:
            raise UpdateFailed(f"XSense API Issue: {ex}") from ex
        else:
            return stations

    async def get_devices(
        self,
        retry=False,
        include_camera_history=True,
        include_camera_update=True,
        include_state_update=True,
    ):
        """Retrieve all devices from the xsense account.

        The expensive load_all() call is only needed on initial setup or after
        reconnect. Regular refreshes keep device state current without repeating
        the full discovery chain.
        """
        stations = {}
        devices = {}

        try:
            if not self._initialized:
                await self.xsense.load_all()
                self._initialized = True
                LOGGER.debug("Initial XSense discovery complete")

            camera_data_refreshed = False
            if include_camera_update:
                camera_data_refreshed = await self._update_cameras()
            else:
                LOGGER.debug("X-Sense camera metadata skipped during startup refresh")
            if camera_data_refreshed:
                self._cache_camera_stations()
            if include_camera_history:
                await self._update_camera_ai_history()
            else:
                LOGGER.debug("X-Sense camera history skipped during startup refresh")

            for h in self.xsense.houses.values():
                stations.update(h.stations.items())
                if include_state_update:
                    with suppress(NotFoundError):
                        await self.xsense.get_house_state(h)
                for s in h.stations.values():
                    if include_state_update and not is_camera_entity(s):
                        await self.xsense.get_station_state(s)
                        await self.xsense.get_state(s)
                    if include_state_update and s.type == "SBS50":
                        await self._update_safe_mode(s)
                    devices.update(s.devices.items())
            if not include_state_update:
                LOGGER.debug("X-Sense device state polling skipped during startup refresh")

            self._merge_cached_camera_stations(stations)
            LOGGER.debug(
                "X-Sense coordinator refresh summary: stations=%s devices=%s camera_initialized=%s camera_cache=%s mqtt_servers=%s mqtt_connected=%s",
                len(stations),
                len(devices),
                self._camera_initialized,
                len(self._camera_station_cache),
                len(self.mqtt_servers),
                sum(1 for mqtt in self.mqtt_servers.values() if mqtt.connected),
            )

        except (SessionExpired, AuthFailed) as ex:
            if not retry:
                self._initialized = False
                await self._connect()
                return await self.get_devices(
                    retry=True,
                    include_camera_history=include_camera_history,
                    include_camera_update=include_camera_update,
                    include_state_update=include_state_update,
                )
            raise ConfigEntryAuthFailed(
                "Could not update, session no longer valid"
            ) from ex
        except APIFailure as ex:
            raise UpdateFailed(f"XSense API Issue: {ex}") from ex
        else:
            return {"stations": stations, "devices": devices}

    async def _update_cameras(self) -> bool:
        """Fetch camera metadata from the Android app IPC/ADDX APIs when present.

        Return True only when the camera API was actually refreshed. Normal
        coordinator refreshes may skip this expensive path, but cached ADDX
        camera stations still need to stay in coordinator data so Home Assistant
        does not mark their entities unavailable.
        """
        now = datetime.now(timezone.utc)
        if (
            self._camera_initialized
            and self._last_camera_update_attempt is not None
            and now - self._last_camera_update_attempt
            < timedelta(seconds=CAMERA_SCAN_INTERVAL)
        ):
            return False

        self._last_camera_update_attempt = now
        try:
            await self.xsense.update_camera_data()
        except APIFailure as ex:
            if _is_addx_account_kicked_error(ex) and await self._retry_camera_update_after_kick():
                self._camera_initialized = True
                LOGGER.debug("X-Sense camera metadata refresh completed after session recovery")
                return True
            self._camera_initialized = False
            self._last_camera_update_attempt = None
            if _is_no_camera_ipc_registration_error(ex) and not (
                _camera_entities(self) or self._camera_station_cache
            ):
                LOGGER.debug("X-Sense camera metadata skipped: no IPC camera account")
                return False
            LOGGER.warning("Could not update X-Sense camera data: %s", ex)
            return False
        else:
            self._camera_initialized = True
            LOGGER.debug("X-Sense camera metadata refresh completed")
            return True

    async def _retry_camera_update_after_kick(self) -> bool:
        """Retry camera metadata once after the ADDX account session is kicked."""
        if self.xsense is None:
            return False
        if hasattr(self.xsense, "_addx_session"):
            self.xsense._addx_session = None
        try:
            await self.xsense.update_camera_data()
        except APIFailure as ex:
            LOGGER.warning("Could not recover X-Sense camera session after kick: %s", ex)
            return False
        return True

    async def _update_camera_ai_history(self) -> bool:
        """Poll APK AI-notification history for camera events missed by MQTT."""
        async with self._camera_ai_history_lock:
            return await self._update_camera_ai_history_locked()

    async def _update_camera_ai_history_locked(self) -> bool:
        """Poll APK AI-notification history while holding the history lock."""
        cameras = _camera_entities(self)
        if not self.xsense:
            LOGGER.debug("X-Sense camera history poll skipped: no client")
            return False
        if not cameras:
            LOGGER.debug("X-Sense camera history poll skipped: no cameras")
            return False

        updated = False
        try:
            services = await self.xsense.get_ai_service_list()
        except APIFailure as ex:
            LOGGER.debug("Could not update X-Sense camera AI history: %s", ex)
            services = []
            service_list_available = False
        else:
            service_list_available = True

        server_ids = [
            str(service.get("serverId"))
            for service in services
            if isinstance(service, dict) and service.get("serverId")
        ]
        if service_list_available:
            _set_camera_ai_service_available(cameras, bool(server_ids))
        if not server_ids:
            LOGGER.debug(
                "X-Sense camera AI history poll skipped: no services %s",
                {
                    "service_count": len(services) if isinstance(services, list) else None,
                    "service_shapes": [
                        sorted(str(key) for key in service)
                        for service in services
                        if isinstance(service, dict)
                    ][:5],
                },
            )
        else:
            updated = await self._update_camera_ai_service_history(server_ids)

        return await self._update_camera_event_history(cameras) or updated

    async def _update_camera_ai_service_history(self, server_ids: list[str]) -> bool:
        """Poll APK AI service history for camera events."""
        first_poll = not self._camera_ai_history_seen
        applied = 0
        skipped = 0
        seen_now: set[str] = set()
        for server_id in server_ids:
            try:
                history = await self.xsense.get_ai_service_history(server_id)
            except APIFailure as ex:
                LOGGER.debug(
                    "Could not update X-Sense camera AI history service: %s",
                    ex,
                )
                continue

            alarm_items = history.get("alarmItems")
            if not isinstance(alarm_items, list):
                continue
            for alarm_item in reversed(alarm_items):
                if not isinstance(alarm_item, dict):
                    continue
                event_key = _camera_ai_history_event_key(server_id, alarm_item)
                if event_key in self._camera_ai_history_seen and not first_poll:
                    skipped += 1
                    continue
                if self._apply_camera_ai_history_item(server_id, alarm_item):
                    applied += 1
                    seen_now.add(event_key)

        self._camera_ai_history_seen.update(seen_now)
        LOGGER.debug(
            "X-Sense camera AI history poll: services=%s seen=%s applied=%s skipped=%s first_poll=%s",
            len(server_ids),
            len(self._camera_ai_history_seen),
            applied,
            skipped,
            first_poll,
        )
        return applied > 0

    async def _update_camera_event_history(self, cameras: list[Any]) -> bool:
        """Poll APK ADDX camera record history for regular motion events."""
        serial_numbers = [
            str(camera.sn) for camera in cameras if getattr(camera, "sn", None)
        ]
        if not serial_numbers:
            LOGGER.debug(
                "X-Sense camera record history poll skipped: no serial numbers"
            )
            return False

        first_poll = not self._camera_ai_history_seen
        applied = 0
        skipped = 0
        seen_now: set[str] = set()
        now = int(datetime.now(timezone.utc).timestamp())
        try:
            history = await self.xsense.get_camera_event_history(
                serial_numbers,
                now - 3600,
                now,
            )
        except APIFailure as ex:
            LOGGER.debug("Could not update X-Sense camera record history: %s", ex)
            return False

        records = _camera_event_history_records(history)
        for record in reversed(records):
            event_key = _camera_event_history_event_key(record)
            if event_key in self._camera_ai_history_seen and not first_poll:
                skipped += 1
                continue
            if self._apply_camera_event_history_item(record):
                applied += 1
                seen_now.add(event_key)
            else:
                LOGGER.debug(
                    "X-Sense camera record history item was not applied: %s",
                    _camera_record_history_debug_context(record, event_key),
                )

        self._camera_ai_history_seen.update(seen_now)
        LOGGER.debug(
            "X-Sense camera record history poll: cameras=%s records=%s seen=%s applied=%s skipped=%s first_poll=%s",
            len(serial_numbers),
            len(records),
            len(self._camera_ai_history_seen),
            applied,
            skipped,
            first_poll,
        )
        return applied > 0

    def _apply_camera_ai_history_item(
        self, server_id: str, alarm_item: dict[str, Any]
    ) -> bool:
        """Apply one APK AI-history alarm item to the matching camera entity."""
        payload = dict(alarm_item)
        payload.setdefault("serverId", server_id)
        if create_time := alarm_item.get("createTime"):
            payload.setdefault("eventTime", create_time)
        station_data = _mqtt_reported_data(payload)
        if not isinstance(station_data, dict) or not station_data:
            return False

        station = _camera_station_for_event_data(self, station_data, payload)
        if station is None:
            LOGGER.debug(
                "No X-Sense camera found for AI history event: %s",
                {
                    "server_id_present": bool(server_id),
                    "payload_keys": sorted(str(key) for key in payload),
                    "station_data_keys": sorted(str(key) for key in station_data),
                },
            )
            return False

        LOGGER.debug(
            "X-Sense camera AI history event routed: %s",
            {
                "station_type": station.type,
                "station_data_keys": sorted(str(key) for key in station_data),
                "has_ai_detection": "lastAiDetection" in station_data,
                "has_motion_event_time": "eventTime" in station_data,
            },
        )
        self.xsense.parse_get_state(station, station_data)
        return True

    def _apply_camera_event_history_item(self, record: dict[str, Any]) -> bool:
        """Apply one APK ADDX camera record to the matching camera entity."""
        station_data = _camera_event_history_station_data(record)
        if not station_data:
            return False

        station = _camera_station_for_event_data(self, station_data, record)
        if station is None:
            LOGGER.debug(
                "No X-Sense camera found for record history item: %s",
                {
                    "payload_keys": sorted(str(key) for key in record),
                    "station_data_keys": sorted(str(key) for key in station_data),
                },
            )
            return False

        LOGGER.debug(
            "X-Sense camera record history item routed: %s",
            {
                "station_type": station.type,
                "station_data_keys": sorted(str(key) for key in station_data),
                "has_ai_detection": "lastAiDetection" in station_data,
                "has_motion_event_time": "eventTime" in station_data,
            },
        )
        self.xsense.parse_get_state(station, station_data)
        return True

    def _cache_camera_stations(self) -> None:
        """Remember ADDX camera stations between camera API refreshes."""
        self._camera_station_cache = {
            station.entity_id: station
            for house in self.xsense.houses.values()
            for station in house.stations.values()
            if is_camera_entity(station)
        }

    def _merge_cached_camera_stations(self, stations: dict[str, Any]) -> None:
        """Keep ADDX-only cameras present when the camera API refresh is skipped."""
        stations.update(self._camera_station_cache)

    async def _update_safe_mode(self, station) -> None:
        """Fetch safeMode from the 2nd_safemode AWS IoT shadow as a fallback."""
        try:
            res = await self.xsense.get_thing(station, "2nd_safemode")
            reported = res.get("state", {}).get("reported", {})
            safe_mode = reported.get("safeMode")

            if safe_mode is not None:
                _apply_safe_mode(station, safe_mode)
                LOGGER.debug(
                    "HTTP poll: station %s safeMode = %s", station.sn, safe_mode
                )
            else:
                LOGGER.warning(
                    "Station %s has no safeMode in 2nd_safemode shadow: %s",
                    station.sn,
                    res,
                )
        except Exception as ex:  # noqa: BLE001
            LOGGER.warning(
                "Could not fetch 2nd_safemode for station %s: %s",
                station.sn,
                ex,
            )

    def setup_mqtt(self, h: House) -> XSenseMQTT:
        """Create and configure MQTT object for specific house."""
        if not self.mqtt_server(h.mqtt_server):
            mqtt = XSenseMQTT(self.hass, self.entry, h.mqtt)
            mqtt.on_data = self.async_event_received
            mqtt.init_client()
            self.mqtt_servers[h.mqtt_server] = mqtt

        return self.mqtt_servers[h.mqtt_server]

    def async_event_received(self, topic: str, data_str: bytes) -> None:
        """Handle incoming data from MQTT.

        AWS IoT shadow updates are delivered on update plus accepted/documents
        topics. Only the update topic should mutate local state.
        """
        if any(topic.endswith(suffix) for suffix in _IGNORED_TOPIC_SUFFIXES):
            LOGGER.debug("Ignoring duplicate MQTT shadow topic: %s", topic)
            return

        try:
            data = json.loads(data_str.decode("utf8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as ex:
            LOGGER.warning("Could not parse MQTT message: %s", ex)
            return

        station_data = _mqtt_reported_data(data)

        station_sn = None
        device_sn = None
        if isinstance(station_data, dict):
            station_sn = _mqtt_target_station_sn(station_data)
            device_sn = _mqtt_target_device_sn(station_data)

        station = self._get_station_by_id(station_sn)
        if station is None:
            station = self._get_station_by_device_sn(device_sn)
        identifier_candidates: list[str] = []
        if isinstance(station_data, dict):
            identifier_candidates.extend(_mqtt_identifier_candidates(station_data))
        identifier_candidates.extend(_mqtt_identifier_candidates(data))
        if station is None:
            for identifier in identifier_candidates:
                station = self._get_station_by_id(identifier)
                if station is None:
                    station = self._get_station_by_device_sn(identifier)
                if station is not None:
                    break

        if station is None and _is_presence_topic(topic):
            station = self._get_station_by_shadow_name(data.get("clientId"))

        if station is None and isinstance(topic, str):
            parts = topic.split("/")
            if len(parts) > 2:
                station = self._get_station_by_shadow_name(parts[2])

        if station is None:
            LOGGER.debug(
                "No X-Sense station found for MQTT event: %s",
                _mqtt_event_debug_context(topic, data, station_data, identifier_candidates),
            )
            return

        LOGGER.debug(
            "X-Sense MQTT event routed: %s",
            _mqtt_event_debug_context(topic, data, station_data, identifier_candidates),
        )

        if _is_presence_topic(topic):
            if event_type := data.get("eventType"):
                station._set_online(event_type == "connected")
                self.async_update_listeners()
            return

        if isinstance(station_data, list):
            self.xsense.parse_get_state(station, station_data)
            self.async_update_listeners()
            return

        is_safemode_topic = "/shadow/name/2nd_safemode/update" in topic
        if is_safemode_topic and "safeMode" in station_data:
            safe_mode = station_data["safeMode"]
            _apply_safe_mode(station, safe_mode)
            LOGGER.debug(
                "MQTT: station %s safeMode -> %s (topic: %s)",
                station.sn,
                safe_mode,
                topic,
            )

        if _is_self_test_topic(topic):
            _normalize_self_test_report(station_data)
            self_test_report = _self_test_report_payload(station_data)
            self_test_device_sn = _mqtt_target_device_sn(self_test_report)
            _fire_self_test_event(
                getattr(self, "hass", None),
                topic=topic,
                station=station,
                report=self_test_report,
            )
            LOGGER.debug(
                "X-Sense self-test report normalized: %s",
                _mqtt_event_debug_context(
                    topic, data, station_data, identifier_candidates
                )
                | {
                    "has_last_self_test": self_test_report.get("lastSelfTest")
                    not in (None, ""),
                    "has_last_self_test_time": self_test_report.get("lastSelfTestTime")
                    not in (None, ""),
                    "target_is_station": self_test_device_sn in (None, "", station.sn),
                    "target_device_present": self_test_device_sn not in (None, ""),
                },
            )

        if _is_keypad_notice_topic(topic):
            _fire_keypad_code_events(self.hass, station_data)

        children = station_data.pop("devs", {}) or {}
        target_device_sn = _mqtt_target_device_sn(station_data)
        if (
            target_device_sn
            and target_device_sn != station.sn
            and station.get_device_by_sn(target_device_sn)
        ):
            self.xsense.parse_get_state(
                station,
                {
                    "devs": {
                        target_device_sn: station_data,
                    },
                },
            )
        else:
            if isinstance(children, (dict, list)):
                station_data["devs"] = children
            self.xsense.parse_get_state(station, station_data)

        self.async_update_listeners()

    async def assure_subscriptions(self, h: House) -> None:
        """Assure there are subscriptions for all relevant topics.

        The wildcard `shadow/name/+/update` covers all shadow updates, including
        2nd_safemode, without creating duplicate per-shadow subscriptions.
        """
        await self.assure_subscription(h.mqtt_server, f"@xsense/events/+/{h.house_id}")
        if user_id := getattr(self.xsense, "user_id_code", None) or getattr(
            self.xsense, "userid", None
        ):
            await self.assure_subscription(
                h.mqtt_server, f"@xsense/events/aiplan/{user_id}"
            )
        await self.assure_subscription(
            h.mqtt_server, f"$aws/things/{h.house_id}/shadow/name/+/update"
        )

        for station in h.stations.values():
            await self.assure_subscription(
                h.mqtt_server, f"$aws/things/{station.shadow_name}/shadow/name/+/update"
            )
            await self.assure_subscription(
                h.mqtt_server, f"$aws/events/presence/+/{station.shadow_name}"
            )

    async def assure_subscription(self, server: str, topic: str) -> None:
        """Assure there is a subscription for a single topic on given server."""
        mqtt = self.mqtt_server(server)
        if not mqtt:
            LOGGER.error(f"Unknown mqtt server {server}")
            return

        if not mqtt.is_subscribed(topic):
            await self.subscribe_topic(mqtt, topic, self.async_event_received)

    async def subscribe_topic(self, mqtt, topic, msg_callback):
        """Call subscribe function of MQTT client."""
        await mqtt.async_subscribe(
            topic,
            catch_log_exception(
                msg_callback,
                lambda msg: (
                    f"Exception in {msg_callback.__name__} when handling msg on "
                    f"'{msg.topic}': '{msg.payload}'"
                ),
            ),
            DEFAULT_SUBSCRIBE_QOS,
            DEFAULT_ENCODING,
        )

    async def request_device_updates(self, mqtt, house):
        """Ask MQTT server for updates for all realtime devices."""
        for s in house.stations.values():
            updatable_devices = [
                dev.sn
                for dev in s.devices.values()
                if dev.type in ["STH51", "STH0A", "STH0B"]
            ]

            if not updatable_devices:
                continue

            msg = {
                "state": {
                    "desired": {
                        "shadow": "appTempData",
                        "deviceSN": updatable_devices,
                        "source": "1",
                        "report": "1",
                        "reportDst": "1",
                        "timeoutM": str(POLL_INTERVAL_MIN),
                        "userId": self.xsense.userid,
                        "time": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
                        "stationSN": s.sn,
                    }
                }
            }
            await mqtt.async_publish(
                f"$aws/things/{s.shadow_name}/shadow/name/2nd_apptempdata/update",
                json.dumps(msg, ensure_ascii=False, separators=(",", ":")),
                0,
                False,
            )


def _apply_safe_mode(station, safe_mode: str) -> None:
    """Store safeMode consistently for HTTP polling and MQTT updates."""
    station.safe_mode = safe_mode
    station._data["safeMode"] = safe_mode


def _mqtt_target_device_sn(data: dict[str, Any]) -> str | None:
    """Return the child device serial from APK MQTT payload variants."""
    for key in (
        "deviceSN",
        "deviceSn",
        "_deviceSN",
        "_deviceSn",
        "devSerialNumber",
        "serialNumber",
        "sn",
    ):
        value = data.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _mqtt_target_station_sn(data: dict[str, Any]) -> str | None:
    """Return the station serial from APK MQTT payload variants."""
    for key in (
        "stationSN",
        "stationSn",
        "_stationSN",
        "_stationSn",
        "stationSerialNumber",
    ):
        value = data.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _mqtt_event_debug_context(
    topic: str,
    data: dict[str, Any],
    station_data: dict[str, Any] | list[Any],
    identifiers: list[str],
) -> dict[str, Any]:
    """Return a redacted debug context for MQTT event routing."""
    if isinstance(station_data, dict):
        station_data_keys: list[str] | None = sorted(str(key) for key in station_data)
    else:
        station_data_keys = None
    return {
        "topic_kind": _mqtt_topic_kind(topic),
        "payload_keys": sorted(str(key) for key in data),
        "station_data_keys": station_data_keys,
        "identifier_count": len(identifiers),
        "has_event_data": "eventData" in data,
    }


def _camera_entities(coordinator: XSenseDataUpdateCoordinator) -> list[Any]:
    """Return camera entities known to the coordinator."""
    if not coordinator.xsense:
        return []
    return [
        station
        for house in coordinator.xsense.houses.values()
        for station in house.stations.values()
        if is_camera_entity(station)
    ]


def _is_no_camera_ipc_registration_error(error: Exception) -> bool:
    """Return if IPC registration failed because the account has no camera user."""
    text = str(error)
    return (
        "IPC code C10101" in text
        and "C1000001/500" in text
        and "userName is invalid" in text
    )


def _is_addx_account_kicked_error(error: Exception) -> bool:
    """Return if ADDX reported that the camera account session was kicked."""
    text = str(error)
    return "-1024/ACCOUNT_GET_KICKED" in text


def _set_camera_ai_service_available(cameras: list[Any], available: bool) -> None:
    """Store whether the APK reports AI-notification service support."""
    for camera in cameras:
        data = getattr(camera, "data", None)
        if isinstance(data, dict):
            data[CAMERA_AI_SERVICE_AVAILABLE] = available


def _camera_record_history_debug_context(
    record: dict[str, Any], event_key: str
) -> dict[str, Any]:
    """Return redacted debug context for one ADDX camera history record."""
    timestamp = record.get("timestamp") or record.get("startTime") or record.get("date")
    return {
        "event_key_hash": hashlib.sha256(event_key.encode()).hexdigest()[:12],
        "record_keys": sorted(str(key) for key in record),
        "serial_present": bool(
            record.get("serialNumber") or record.get("deviceSn") or record.get("sn")
        ),
        "trace_present": bool(record.get("traceId") or record.get("traceIds")),
        "timestamp": timestamp,
        "tags_present": "tags" in record,
        "video_event_present": "videoEvent" in record,
        "video_url_present": bool(record.get("videoUrl")),
        "start_time_present": record.get("startTime") not in (None, ""),
        "end_time_present": record.get("endTime") not in (None, ""),
        "event_info_count": len(record.get("eventInfoList") or [])
        if isinstance(record.get("eventInfoList"), list)
        else None,
    }


def _camera_station_for_event_data(
    coordinator: XSenseDataUpdateCoordinator,
    station_data: dict[str, Any],
    payload: dict[str, Any],
):
    """Return the camera station matched by APK event identifiers."""
    identifiers = _mqtt_identifier_candidates(station_data, payload)
    for identifier in identifiers:
        station = coordinator._get_station_by_id(identifier)
        if station is None:
            station = coordinator._get_station_by_device_sn(identifier)
        if station is not None and is_camera_entity(station):
            return station
    return None


def _is_keypad_notice_topic(topic: str) -> bool:
    """Return if an MQTT update is an X-Sense keypad notice topic."""
    return "/shadow/name/2nd_safenotice/update" in topic


def _fire_keypad_code_events(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Fire HA bus events for submitted SKP0A keypad codes."""
    notices = data.get("notices")
    if not isinstance(notices, list):
        return

    for notice in notices:
        if not isinstance(notice, dict) or notice.get("type") != "SKP0A":
            continue
        event_param = notice.get("eventParam")
        if not isinstance(event_param, dict):
            event_param = {}
        keypad_code = event_param.get("pword")
        if keypad_code in (None, ""):
            LOGGER.debug(
                "X-Sense keypad notice skipped without code: device=%s aim=%s",
                notice.get("deviceSN"),
                event_param.get("safeModeAim"),
            )
            continue
        mode_button = event_param.get("safeModeAim")
        payload = {
            "station_sn": data.get("stationSN"),
            "device_sn": notice.get("deviceSN"),
            "keypad_code": str(keypad_code),
            "safe_mode": data.get("safeMode"),
            "safe_mode_aim": mode_button,
            "mode_button": mode_button,
            "submit_button": mode_button,
            "event_id": notice.get("eventId"),
            "event_time": notice.get("eventTime"),
            "alarm_cancel": event_param.get("alarmCancel"),
        }
        hass.bus.async_fire(KEYPAD_CODE_EVENT_TYPE, payload)
        LOGGER.info(
            "X-Sense keypad code event: device=%s safeMode=%s aim=%s code_present=%s",
            notice.get("deviceSN"),
            data.get("safeMode"),
            event_param.get("safeModeAim"),
            keypad_code not in (None, ""),
        )


def _fire_self_test_event(
    hass: HomeAssistant,
    *,
    topic: str,
    station,
    report: dict[str, Any],
) -> None:
    """Fire a HA bus event for a physical/app-reported self-test result."""
    if hass is None:
        return
    result = report.get("lastSelfTest")
    event_time = report.get("lastSelfTestTime")
    if result in (None, "") and event_time in (None, ""):
        return

    device_sn = _mqtt_target_device_sn(report) or getattr(station, "sn", None)
    result_text = _self_test_event_result(result)
    payload = {
        "station_sn": report.get("stationSN") or getattr(station, "sn", None),
        "device_sn": device_sn,
        "device_type": getattr(station.get_device_by_sn(device_sn), "type", None)
        if device_sn and hasattr(station, "get_device_by_sn")
        else getattr(station, "type", None),
        "result": result_text,
        "result_code": result,
        "success": result_text == "success" if result_text is not None else None,
        "event_time": event_time,
        "topic": topic,
    }
    hass.bus.async_fire(SELF_TEST_EVENT_TYPE, payload)
    LOGGER.info(
        "X-Sense self-test event: device=%s result=%s time=%s",
        device_sn,
        result_text,
        event_time,
    )


def _self_test_event_result(result: Any) -> str | None:
    """Return a readable event result for normalized self-test report codes."""
    if result in (None, ""):
        return None
    return "success" if str(result).strip().lower() == "0" else "failed"
