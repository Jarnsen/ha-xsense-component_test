"""DataUpdateCoordinator for the XSense integration."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime, timedelta, timezone
import json
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.logging import catch_log_exception

from .api import AsyncXSense, House
from .api.async_xsense import is_camera_entity
from .api.exceptions import APIFailure, AuthFailed, NotFoundError, SessionExpired
from .const import (
    DEFAULT_SCAN_INTERVAL,
    CAMERA_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    POLL_INTERVAL_MIN,
)
from .mqtt import DEFAULT_ENCODING, DEFAULT_SUBSCRIBE_QOS, XSenseMQTT

_IGNORED_TOPIC_SUFFIXES = ("/update/accepted", "/update/documents", "/update/rejected")

_APK_AI_DETECTION_OBJECTS = {
    "person",
    "pet",
    "vehicle",
    "vehicle_enter",
    "vehicle_out",
    "vehicle_held_up",
    "package",
    "package_drop_off",
    "package_pick_up",
    "package_exist",
    "other",
}

_APK_AI_DETECTION_GROUPS = {
    "person": {"person"},
    "pet": {"pet"},
    "vehicle": {"vehicle", "vehicle_enter", "vehicle_out", "vehicle_held_up"},
    "package": {"package", "package_drop_off", "package_pick_up", "package_exist"},
    "other": {"other"},
}

_APK_AI_DETECTION_DATA_KEYS = {
    "person": "person",
    "pet": "pet",
    "vehicle_enter": "vehicleEnter",
    "vehicle_out": "vehicleOut",
    "vehicle_held_up": "vehicleHeldUp",
    "package_drop_off": "packageDropOff",
    "package_pick_up": "packagePickUp",
    "package_exist": "packageExist",
    "other": "other",
}

_APK_MOTION_DETECTION_NAMES = {
    "motion",
    "motion_detected",
    "motion_detection",
    "motion_detection_camera",
    "pir_motion",
    "camera_motion",
}


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
        mqtt_servers = list(self.mqtt_servers.values())
        self.mqtt_servers.clear()

        for mqtt in mqtt_servers:
            try:
                await mqtt.async_disconnect(disconnect_paho_client=True)
            except Exception as ex:  # noqa: BLE001
                LOGGER.warning("Could not disconnect XSense MQTT client: %s", ex)

        if self.xsense is not None:
            await self.xsense.close()

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
        devices = await self.get_devices()

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

    async def get_devices(self, retry=False):
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

            camera_data_refreshed = await self._update_cameras()
            if camera_data_refreshed:
                self._cache_camera_stations()

            for h in self.xsense.houses.values():
                stations.update(h.stations.items())
                with suppress(NotFoundError):
                    await self.xsense.get_house_state(h)
                for s in h.stations.values():
                    if not is_camera_entity(s):
                        await self.xsense.get_station_state(s)
                        await self.xsense.get_state(s)
                    if s.type == "SBS50":
                        await self._update_safe_mode(s)
                    devices.update(s.devices.items())

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
                return await self.get_devices(retry=True)
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
            self._camera_initialized = False
            self._last_camera_update_attempt = None
            LOGGER.warning("Could not update X-Sense camera data: %s", ex)
            return False
        else:
            self._camera_initialized = True
            LOGGER.debug("X-Sense camera metadata refresh completed")
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
            station_sn = (
                station_data.get("stationSN")
                or station_data.get("_stationSN")
                or station_data.get("serialNumber")
            )
            device_sn = (
                station_data.get("deviceSN")
                or station_data.get("_deviceSN")
                or station_data.get("serialNumber")
            )

        station = self._get_station_by_id(station_sn)
        if station is None:
            station = self._get_station_by_device_sn(device_sn)

        if station is None and _is_presence_topic(topic):
            station = self._get_station_by_shadow_name(data.get("clientId"))

        if station is None and isinstance(topic, str):
            parts = topic.split("/")
            if len(parts) > 2:
                station = self._get_station_by_shadow_name(parts[2])

        if station is None:
            LOGGER.debug("No station found for MQTT topic: %s", topic)
            return

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

        children = station_data.pop("devs", {}) or {}
        target_device_sn = (
            station_data.get("deviceSN")
            or station_data.get("_deviceSN")
            or station_data.get("serialNumber")
        )
        if (
            target_device_sn
            and target_device_sn != station.sn
            and (dev := station.get_device_by_sn(target_device_sn))
        ):
            dev.set_data(station_data)
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


def _mqtt_reported_data(data: dict[str, Any]) -> dict[str, Any] | list[Any]:
    """Return device data from either shadow reports or X-Sense event payloads."""
    reported = data.get("state", {}).get("reported")
    if isinstance(reported, dict):
        return reported.copy()
    if isinstance(reported, list):
        return list(reported)

    event_data = data.get("eventData")
    if isinstance(event_data, str):
        try:
            event_data = json.loads(event_data)
        except json.JSONDecodeError:
            event_data = None
    if isinstance(event_data, dict):
        result = event_data.copy()
        if event_time := data.get("eventTime"):
            result.setdefault("time", event_time)
        if event_type := data.get("eventType") or result.get("eventType"):
            result.setdefault("eventType", event_type)
        _apply_apk_dispatch_aliases(result)
        _apply_apk_event_aliases(result)
        return result

    if any(
        key in data
        for key in (
            "dispatchDevs",
            "eventItems",
            "eventObjectType",
            "eventType",
            "lastType",
            "serialNumber",
        )
    ):
        result = data.copy()
        if event_time := data.get("eventTime"):
            result.setdefault("time", event_time)
        _apply_apk_dispatch_aliases(result)
        _apply_apk_event_aliases(result)
        return result

    return {}


def _apply_apk_dispatch_aliases(data: dict[str, Any]) -> None:
    """Apply APK dispatch device identifiers to normal MQTT lookup keys."""
    dispatch_devs = data.get("dispatchDevs")
    if not isinstance(dispatch_devs, list):
        return

    dispatch_dev = next(
        (item for item in dispatch_devs if isinstance(item, dict)),
        None,
    )
    if dispatch_dev is None:
        return

    if station_sn := dispatch_dev.get("stationSn"):
        data.setdefault("stationSN", station_sn)
    if device_sn := dispatch_dev.get("deviceSn"):
        data.setdefault("deviceSN", device_sn)
        data.setdefault("serialNumber", device_sn)
    if event_time := dispatch_dev.get("eventTime"):
        data.setdefault("time", event_time)


def _apply_apk_event_aliases(data: dict[str, Any]) -> None:
    """Apply APK event aliases that are not reported as shadow keys."""
    _apply_apk_ai_detection_aliases(data)

    event_type = data.get("eventType")
    try:
        numeric_event_type = int(event_type)
    except (TypeError, ValueError):
        numeric_event_type = None

    # APK history event 92 is Motion Detected. The device UI uses isMoved for
    # the live motion state, so expose the event through that same key.
    if (
        numeric_event_type == 92
        or _apk_motion_detection_names(data)
        or data.get("lastAiDetection")
    ):
        _apply_apk_motion_detected_aliases(data)


def _apply_apk_motion_detected_aliases(data: dict[str, Any]) -> None:
    """Expose APK camera motion events through the live motion state key."""
    data.setdefault("isMoved", "1")
    if time_value := data.get("time") or data.get("eventTime"):
        data.setdefault("lastMotionTime", time_value)


def _apply_apk_ai_detection_aliases(data: dict[str, Any]) -> None:
    """Apply APK AI detection object names from camera event payloads."""
    fallback_time = data.get("time") or data.get("eventTime")
    object_times = _apk_ai_detection_object_times(data, fallback_time)
    objects = set(object_times)
    if not objects:
        return

    data["lastAiDetection"] = ",".join(sorted(objects))
    for group, object_names in _APK_AI_DETECTION_GROUPS.items():
        detected_objects = objects & object_names
        detected = bool(detected_objects)
        data[f"{group}Detected"] = detected
        if detected:
            time_value = _latest_apk_detection_time(
                object_times.get(name) for name in detected_objects
            )
            if time_value:
                data[f"last{group.title()}DetectionTime"] = time_value
    for object_name, data_key in _APK_AI_DETECTION_DATA_KEYS.items():
        detected = object_name in objects
        data[f"{data_key}Detected"] = detected
        if detected and object_times.get(object_name):
            data[f"last{data_key[0].upper()}{data_key[1:]}DetectionTime"] = object_times[
                object_name
            ]


def _apk_ai_detection_object_times(
    data: dict[str, Any], fallback_time: Any = None
) -> dict[str, Any]:
    """Return APK AI detection object names and their best event timestamp."""
    raw_values: list[Any] = [
        data.get("eventObjectType"),
        data.get("eventItems"),
        data.get("lastType"),
    ]
    objects: dict[str, Any] = {}
    for raw_value in raw_values:
        for name, time_value in _apk_ai_detection_name_times(
            raw_value, fallback_time
        ).items():
            objects[name] = _latest_apk_detection_time((objects.get(name), time_value))
    return objects


def _apk_ai_detection_name_times(value: Any, fallback_time: Any = None) -> dict[str, Any]:
    """Return APK AI detection object names with timestamps from nested payloads."""
    if value is None:
        return {}
    if isinstance(value, str):
        text = value.strip()
        if text.startswith(("{", "[")):
            with suppress(json.JSONDecodeError):
                return _apk_ai_detection_name_times(json.loads(text), fallback_time)
        return {name: fallback_time for name in _apk_ai_detection_names(text)}
    if isinstance(value, dict):
        item_time = value.get("eventTime") or value.get("time") or fallback_time
        objects: dict[str, Any] = {}
        for key in (
            "eventType",
            "eventObjectType",
            "eventItems",
            "lastType",
        ):
            for name, time_value in _apk_ai_detection_name_times(
                value.get(key), item_time
            ).items():
                objects[name] = _latest_apk_detection_time(
                    (objects.get(name), time_value)
                )
        for key, nested_value in value.items():
            key_name = str(key).strip().lower()
            if key_name in _APK_AI_DETECTION_GROUPS:
                nested = _apk_ai_detection_name_times(nested_value, item_time)
                if nested:
                    for name, time_value in nested.items():
                        objects[name] = _latest_apk_detection_time(
                            (objects.get(name), time_value)
                        )
                elif nested_value not in (None, False):
                    for name in _APK_AI_DETECTION_GROUPS[key_name]:
                        objects[name] = _latest_apk_detection_time(
                            (objects.get(name), item_time)
                        )
                continue
            if key_name in _APK_AI_DETECTION_OBJECTS and nested_value not in (
                None,
                False,
            ):
                objects[key_name] = _latest_apk_detection_time(
                    (objects.get(key_name), item_time)
                )
                continue
            if key in {
                "eventType",
                "eventObjectType",
                "eventItems",
                "lastType",
            }:
                continue
            for name, time_value in _apk_ai_detection_name_times(
                nested_value, item_time
            ).items():
                objects[name] = _latest_apk_detection_time(
                    (objects.get(name), time_value)
                )
        return objects
    if isinstance(value, (list, tuple, set)):
        objects: dict[str, Any] = {}
        for item in value:
            for name, time_value in _apk_ai_detection_name_times(
                item, fallback_time
            ).items():
                objects[name] = _latest_apk_detection_time(
                    (objects.get(name), time_value)
                )
        return objects
    return {}


def _apk_motion_detection_names(value: Any) -> set[str]:
    """Return APK camera motion names from scalar or nested event payloads."""
    if value is None:
        return set()
    if isinstance(value, str):
        text = value.strip()
        if text.startswith(("{", "[")):
            with suppress(json.JSONDecodeError):
                return _apk_motion_detection_names(json.loads(text))
        normalized = text.lower().replace("-", "_").replace(" ", "_")
        return {normalized} if normalized in _APK_MOTION_DETECTION_NAMES else set()
    if isinstance(value, dict):
        names: set[str] = set()
        for key, nested_value in value.items():
            key_name = str(key).strip().lower()
            if key_name in {
                "eventtype",
                "eventname",
                "eventcode",
                "eventsubtype",
                "notificationtype",
                "alarmtype",
                "type",
                "lasttype",
            }:
                names.update(_apk_motion_detection_names(nested_value))
                continue
            if key_name in {"eventitems", "eventdata", "events"}:
                names.update(_apk_motion_detection_names(nested_value))
        return names
    if isinstance(value, (list, tuple, set)):
        names: set[str] = set()
        for item in value:
            names.update(_apk_motion_detection_names(item))
        return names
    return set()


def _latest_apk_detection_time(values) -> Any:
    """Return the newest compact X-Sense time value from an iterable."""
    candidates = [value for value in values if value not in (None, "")]
    if not candidates:
        return None
    return max(candidates, key=str)


def _apk_ai_detection_names(value: Any) -> set[str]:
    """Return APK AI detection object names from a scalar/list/dict value."""
    if value is None:
        return set()
    if isinstance(value, str):
        text = value.strip()
        if text.startswith(("{", "[")):
            with suppress(json.JSONDecodeError):
                return _apk_ai_detection_names(json.loads(text))
        candidates = [
            part.strip().lower()
            for part in text.replace(";", ",").replace("|", ",").split(",")
        ]
        return {name for name in candidates if name in _APK_AI_DETECTION_OBJECTS}
    if isinstance(value, dict):
        names: set[str] = set()
        for key, nested_value in value.items():
            key_name = str(key).strip().lower()
            if key_name in _APK_AI_DETECTION_GROUPS:
                nested_names = _apk_ai_detection_names(nested_value)
                if nested_names:
                    names.update(nested_names)
                elif nested_value not in (None, False):
                    names.update(_APK_AI_DETECTION_GROUPS[key_name])
                continue
            if key_name in _APK_AI_DETECTION_OBJECTS and nested_value not in (
                None,
                False,
            ):
                names.add(key_name)
            names.update(_apk_ai_detection_names(nested_value))
        return names
    if isinstance(value, (list, tuple, set)):
        names: set[str] = set()
        for item in value:
            names.update(_apk_ai_detection_names(item))
        return names
    return set()

def _is_self_test_topic(topic: str) -> bool:
    """Return if an MQTT update is an X-Sense self-test report topic."""
    return any(
        marker in topic
        for marker in (
            "_testup/update",
            "selftestup/update",
            "selftestup_v2/update",
        )
    )


_SELF_TEST_RESULT_KEYS = (
    "lastSelfTest",
    "selfTest",
    "selfTestResult",
    "selfTestStatus",
    "testResult",
    "testStatus",
    "result",
)

_SELF_TEST_TIME_KEYS = (
    "lastSelfTestTime",
    "selfTestTime",
    "testTime",
    "eventTime",
    "timestamp",
    "time",
)


def _normalize_self_test_report(data: dict[str, Any]) -> None:
    """Normalize APK self-test report fields into HA sensor keys."""
    for key in _SELF_TEST_RESULT_KEYS:
        value = data.get(key)
        if value not in (None, ""):
            data["lastSelfTest"] = _normalize_self_test_result(value)
            break

    for key in _SELF_TEST_TIME_KEYS:
        value = data.get(key)
        if value not in (None, ""):
            data["lastSelfTestTime"] = value
            break


def _normalize_self_test_result(value: Any) -> Any:
    """Return the app-style success code when the report uses readable text."""
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"success", "successful", "ok", "pass", "passed"}:
            return "0"
        if normalized in {"fail", "failed", "failure", "error"}:
            return "1"
    return value


def _is_presence_topic(topic: str) -> bool:
    """Return if an MQTT topic is an AWS IoT presence update."""
    return "/events/presence/" in topic
