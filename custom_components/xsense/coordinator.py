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

# Alleen topics die eindigen op /update verwerken.
# /update/accepted en /update/documents zijn duplicaten van hetzelfde event
# en veroorzaken race conditions als ze in een andere volgorde binnenkomen.
_IGNORED_TOPIC_SUFFIXES = ("/update/accepted", "/update/documents", "/update/rejected")


class XSenseDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """A XSense Data Update Coordinator."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the XSense hub."""
        LOGGER.debug("XSenseDataUpdateCoordinator:__init__")
        self.entry = entry
        self.xsense: AsyncXSense = None
        # Bijhouden of load_all al uitgevoerd is — we doen dat maar één keer
        self._initialized: bool = False
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

    async def _connect(self) -> None:
        email = self.entry.data[CONF_EMAIL]
        password = self.entry.data[CONF_PASSWORD]

        self.xsense = AsyncXSense()
        await self.xsense.init()

        try:
            await self.xsense.login(email, password)
        except AuthFailed as ex:
            raise ConfigEntryAuthFailed(f"Login failed: {ex!s}") from ex

        self._initialized = False

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
        """Zoek station op via zijn shadow_name (bv. 'SBS50161965C2')."""
        if not self.xsense:
            return None
        for h in self.xsense.houses.values():
            for s in h.stations.values():
                if s.shadow_name == shadow_name:
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

        load_all() wordt alleen de eerste keer aangeroepen — daarna enkel
        de device states. Dit voorkomt de traagheid bij elke poll cyclus,
        want load_all() doet 4-5 opeenvolgende API calls.

        De safeMode van de SBS50 wordt via een apart shadow-endpoint opgehaald
        als HTTP-fallback. MQTT pusht de updates realtime, maar de poll
        garandeert dat de state correct is na een HA-herstart of MQTT-disconnect.
        """
        stations = {}
        devices = {}

        try:
            # load_all alleen bij eerste keer of na reconnect
            if not self._initialized:
                await self.xsense.load_all()
                self._initialized = True
                LOGGER.debug("load_all() uitgevoerd, apparaten geladen")
            else:
                # Daarna alleen de huislijst opvragen om nieuwe apparaten te detecteren
                # maar de dure load_all() niet meer herhalen
                pass

            for h in self.xsense.houses.values():
                stations.update(h.stations.items())
                with suppress(NotFoundError):
                    await self.xsense.get_house_state(h)
                for s in h.stations.values():
                    await self.xsense.get_station_state(s)
                    await self.xsense.get_state(s)
                    # HTTP-fallback voor safeMode: altijd pollen als backup voor MQTT
                    if s.type == "SBS50":
                        await self._update_safe_mode(s)
                    devices.update(s.devices.items())

        except (SessionExpired, AuthFailed) as ex:
            if not retry:
                self._initialized = False  # forceer load_all na reconnect
                await self._connect()
                return await self.get_devices(retry=True)
            raise ConfigEntryAuthFailed(
                "Could not update, session no longer valid"
            ) from ex
        except APIFailure as ex:
            raise UpdateFailed(f"XSense API Issue: {ex}") from ex
        else:
            return {"stations": stations, "devices": devices}

    async def _update_safe_mode(self, station) -> None:
        """Haal de safeMode op via het 2nd_safemode AWS IoT shadow (HTTP).

        Dit is de betrouwbare fallback wanneer MQTT niet beschikbaar is.
        Bij normale werking wordt de state al realtime via MQTT bijgewerkt,
        dus deze poll dient enkel als vangnet.
        """
        try:
            res = await self.xsense.get_thing(station, "2nd_safemode")
            reported = res.get("state", {}).get("reported", {})
            safe_mode = reported.get("safeMode")

            if safe_mode is not None:
                _apply_safe_mode(station, safe_mode)
                LOGGER.debug("HTTP poll: station %s safeMode = %s", station.sn, safe_mode)
            else:
                LOGGER.warning(
                    "Station %s: geen safeMode in 2nd_safemode shadow: %s",
                    station.sn, res,
                )
        except Exception as ex:  # noqa: BLE001
            LOGGER.warning(
                "Kon 2nd_safemode niet ophalen voor station %s: %s",
                station.sn, ex,
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

        Elke arm/disarm actie genereert 3 topics:
          - shadow/name/2nd_safemode/update          ← de echte update
          - shadow/name/2nd_safemode/update/accepted ← bevestiging van AWS (duplicaat)
          - shadow/name/2nd_safemode/update/documents← vorige+nieuwe state (duplicaat)

        We filteren /accepted en /documents weg om race conditions te voorkomen.
        """
        # Filter duplicaat topics weg
        if any(topic.endswith(suffix) for suffix in _IGNORED_TOPIC_SUFFIXES):
            LOGGER.debug("MQTT: duplicaat topic genegeerd: %s", topic)
            return

        try:
            data = json.loads(data_str.decode("utf8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as ex:
            LOGGER.warning("Kon MQTT bericht niet parsen: %s", ex)
            return

        station_data = data.get("state", {}).get("reported", {})

        # Probeer station te vinden via stationSN in de payload
        station = self._get_station_by_id(station_data.get("stationSN"))

        # Fallback: leid station af uit het topic zelf
        # Topic: $aws/things/SBS50161965C2/shadow/name/2nd_safemode/update
        #                     ^^^^^^^^^^^^^ parts[2]
        if station is None and isinstance(topic, str):
            parts = topic.split("/")
            if len(parts) > 2:
                station = self._get_station_by_shadow_name(parts[2])

        if station is None:
            LOGGER.debug("Geen station gevonden voor MQTT topic: %s", topic)
            return

        # Verwerk safeMode ALLEEN als het van het 2nd_safemode shadow komt.
        # 2nd_safenotice bevat ook een safeMode veld maar dat is de VORIGE
        # staat als context bij een notificatie, geen echte state update.
        # Zonder deze check springt HA 0.6s na elke actie terug naar de
        # verkeerde staat.
        is_safemode_topic = "/shadow/name/2nd_safemode/update" in topic
        if is_safemode_topic and "safeMode" in station_data:
            safe_mode = station_data["safeMode"]
            _apply_safe_mode(station, safe_mode)
            LOGGER.debug(
                "MQTT: station %s safeMode -> %s (topic: %s)",
                station.sn, safe_mode, topic,
            )

        # Verwerk overige device-data
        children = station_data.pop("devs", {})
        self.xsense.parse_get_state(station, station_data)
        for k, v in children.items():
            if dev := station.get_device_by_sn(k):
                dev.set_data(v)

        self.async_update_listeners()

    async def assure_subscriptions(self, h: House) -> None:
        """Assure there are subscriptions for all relevant topics.

        De wildcard `shadow/name/+/update` vangt ALLE shadow updates op,
        inclusief 2nd_safemode. We voegen geen aparte safemode subscription
        meer toe om dubbele verwerking te vermijden.
        """
        await self.assure_subscription(h.mqtt_server, f"@xsense/events/+/{h.house_id}")
        await self.assure_subscription(
            h.mqtt_server, f"$aws/things/{h.house_id}/shadow/name/+/update"
        )

        for station in h.stations.values():
            # De wildcard /+/update vangt alle shadow types op inclusief 2nd_safemode.
            # Geen aparte safemode subscription nodig — dat zou dubbele
            # verwerking geven en is precies wat we willen vermijden.
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
                dev.sn for dev in s.devices.values() if dev.type in ["STH51", "STH0A"]
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


def _apply_safe_mode(station, safe_mode: str) -> None:
    """Sla safeMode op in het station object.

    Centrale functie zodat HTTP-poll en MQTT-handler altijd
    consistent dezelfde velden bijwerken.
    """
    station.safe_mode = safe_mode
    station._data["safeMode"] = safe_mode