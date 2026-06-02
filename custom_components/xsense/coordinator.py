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
    LOGIN_TIMEOUT,
    POLL_INTERVAL_MIN,
)
from .mqtt import DEFAULT_ENCODING, DEFAULT_QOS, XSenseMQTT

_IGNORED_TOPIC_SUFFIXES = ("/update/accepted", "/update/documents", "/update/rejected")


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

        xsense = AsyncXSense(async_get_clientsession(self.hass))

        try:
            await asyncio.wait_for(
                _async_init_and_login(xsense, email, password), timeout=LOGIN_TIMEOUT
            )
        except AuthFailed as ex:
            raise ConfigEntryAuthFailed(f"Login failed: {ex!s}") from ex
        except APIFailure as ex:
            raise UpdateFailed(f"XSense API Issue: {ex}") from ex
        except TimeoutError as ex:
            raise UpdateFailed("Timed out connecting to X-Sense") from ex

        self.xsense = xsense
        self._initialized = False
        self._camera_initialized = False
        self._last_camera_update_attempt = None

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

            await self._update_cameras()

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

    async def _update_cameras(self) -> None:
        """Fetch camera metadata from the Android app IPC/ADDX APIs when present."""
        now = datetime.now(timezone.utc)
        if (
            self._camera_initialized
            and self._last_camera_update_attempt is not None
            and now - self._last_camera_update_attempt
            < timedelta(seconds=CAMERA_SCAN_INTERVAL)
        ):
            return

        self._camera_initialized = True
        self._last_camera_update_attempt = now
        try:
            await self.xsense.update_camera_data()
        except APIFailure as ex:
            LOGGER.warning("Could not update X-Sense camera data: %s", ex)

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

        station_sn = station_data.get("stationSN") or station_data.get("_stationSN")
        device_sn = station_data.get("deviceSN") or station_data.get("_deviceSN")

        station = self._get_station_by_id(station_sn)
        if station is None:
            station = self._get_station_by_device_sn(device_sn)

        if station is None and isinstance(topic, str):
            parts = topic.split("/")
            if len(parts) > 2:
                station = self._get_station_by_shadow_name(parts[2])

        if station is None:
            LOGGER.debug("No station found for MQTT topic: %s", topic)
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

        if _is_self_test_topic(topic) and "selfTest" in station_data:
            station_data["lastSelfTest"] = station_data.pop("selfTest")
            if test_time := station_data.pop("time", None):
                station_data["lastSelfTestTime"] = test_time

        children = station_data.pop("devs", {}) or {}
        target_device_sn = station_data.get("deviceSN") or station_data.get(
            "_deviceSN"
        )
        if (
            target_device_sn
            and target_device_sn != station.sn
            and (dev := station.get_device_by_sn(target_device_sn))
        ):
            dev.set_data(station_data)
        else:
            if isinstance(children, list):
                station_data["devs"] = children
            self.xsense.parse_get_state(station, station_data)
        if isinstance(children, dict):
            for k, v in children.items():
                if dev := station.get_device_by_sn(k):
                    dev.set_data(v)

        self.async_update_listeners()

    async def assure_subscriptions(self, h: House) -> None:
        """Assure there are subscriptions for all relevant topics.

        The wildcard `shadow/name/+/update` covers all shadow updates, including
        2nd_safemode, without creating duplicate per-shadow subscriptions.
        """
        await self.assure_subscription(h.mqtt_server, f"@xsense/events/+/{h.house_id}")
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
            DEFAULT_QOS,
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
                json.dumps(msg),
                0,
                False,
            )


def _apply_safe_mode(station, safe_mode: str) -> None:
    """Store safeMode consistently for HTTP polling and MQTT updates."""
    station.safe_mode = safe_mode
    station._data["safeMode"] = safe_mode


def _mqtt_reported_data(data: dict[str, Any]) -> dict[str, Any]:
    """Return device data from either shadow reports or X-Sense event payloads."""
    reported = data.get("state", {}).get("reported")
    if isinstance(reported, dict):
        return reported.copy()

    event_data = data.get("eventData")
    if isinstance(event_data, dict):
        result = event_data.copy()
        if event_time := data.get("eventTime"):
            result.setdefault("time", event_time)
        if event_type := data.get("eventType"):
            result.setdefault("eventType", event_type)
        return result

    return {}


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
