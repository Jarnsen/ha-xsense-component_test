"""DataUpdateCoordinator for the XSense integration."""

from __future__ import annotations

from contextlib import suppress
from datetime import datetime, timedelta
import json
from typing import Any

from xsense import AsyncXSense, House
from xsense.exceptions import APIFailure, AuthFailed, NotFoundError, SessionExpired

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.logging import catch_log_exception

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER, POLL_INTERVAL_MIN
from .mqtt import DEFAULT_ENCODING, DEFAULT_QOS, XSenseMQTT


class XSenseDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """A XSense Data Update Coordinator."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the XSense hub."""
        LOGGER.debug("XSenseDataUpdateCoordinator:__init__")
        self.entry = entry
        self.xsense: AsyncXSense = None
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            always_update=True,
        )
        self.mqtt_servers: dict[str, XSenseMQTT] = {}
        self.client_available = hass.loop.create_future()

    def mqtt_server(self, host: str):
        """Get mqtt server instance for specific host."""
        return self.mqtt_servers.get(host)

    async def _connect(self) -> None:
        email = self.entry.data[CONF_EMAIL]
        password = self.entry.data[CONF_PASSWORD]

        self.xsense = AsyncXSense()
        await self.xsense.init()

        try:
            await self.xsense.login(email, password)
        except AuthFailed as ex:
            raise ConfigEntryAuthFailed(f"Login failed: {str(ex)}") from ex

    async def _async_update_data(self) -> dict[str, Any]:
        if self.xsense is None:
            await self._connect()
        devices = await self.get_devices()

        if self.xsense and self.xsense.houses:
            for h in self.xsense.houses.values():
                mqtt = self.mqtt_server(h.mqtt_server)
                if not mqtt:
                    mqtt = self.setup_mqtt(h)
                    await mqtt.async_connect(self.client_available)

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
        for h in self.xsense.houses.values():
            if s := h.get_station_by_sn(identifier):
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
        """Retrieve all devices from the xsense account."""
        stations = {}
        devices = {}

        try:
            await self.xsense.load_all()

            for h in self.xsense.houses.values():
                stations.update(h.stations.items())
                with suppress(NotFoundError):
                    await self.xsense.get_house_state(h)
                for s in h.stations.values():
                    await self.xsense.get_station_state(s)
                    await self.xsense.get_state(s)
                    devices.update(s.devices.items())

        except (SessionExpired, AuthFailed) as ex:
            if not retry:
                await self._connect()
                return await self.get_devices(retry=True)
            raise ConfigEntryAuthFailed(
                "Could not update, session no longer valid"
            ) from ex
        except APIFailure as ex:
            raise UpdateFailed(f"XSense API Issue: {ex}") from ex
        else:
            return {"stations": stations, "devices": devices}

    def setup_mqtt(self, h: House) -> XSenseMQTT:
        """Create and configure MQTT object for specific house."""
        if not self.mqtt_server(h.mqtt_server):
            mqtt = XSenseMQTT(self.hass, self.entry, {}, h.mqtt)
            mqtt.on_data = self.async_event_received
            mqtt.init_client()
            self.mqtt_servers[h.mqtt_server] = mqtt

        return self.mqtt_servers[h.mqtt_server]

    def async_event_received(self, topic: str, data_str: bytes) -> None:
        """Handle incoming data from MQTT."""
        data = json.loads(data_str.decode("utf8"))
        station_data = data.get("state", {}).get("reported", {})

        if station := self._get_station_by_id(station_data.get("stationSN")):
            children = station_data.pop("devs", {})

            self.xsense.parse_get_state(station, station_data)
            for k, v in children.items():
                if dev := station.get_device_by_sn(k):
                    dev.set_data(v)

        self.async_update_listeners()

    async def assure_subscriptions(self, h: House) -> None:
        """Assure there are subscriptions for all relevant topics for a certain house."""
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
        """Ask MQTT server for updates for all realtime devices, such as temperature sensor."""
        for s in house.stations.values():
            updatable_devices = [
                dev.sn for dev in s.devices.values() if dev.type in ["STH51"]
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
                        "time": datetime.now().strftime("%Y%m%d%H%M%S"),
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
