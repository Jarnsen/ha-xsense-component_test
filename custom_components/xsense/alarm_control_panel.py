"""Alarm control panel platform for X-Sense SBS50 burglar alarm mode."""

from __future__ import annotations

import json
import logging

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import XSenseDataUpdateCoordinator
from .api.entity_map import EntityType, entities as entity_definitions

LOGGER = logging.getLogger(__name__)

SAFEMODE_TO_STATE: dict[str, AlarmControlPanelState] = {
    "Disarmed": AlarmControlPanelState.DISARMED,
    "Home": AlarmControlPanelState.ARMED_HOME,
    "Away": AlarmControlPanelState.ARMED_AWAY,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up XSense alarm control panel entities from a config entry."""
    coordinator: XSenseDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for house in coordinator.xsense.houses.values():
        for station in house.stations.values():
            if station_supports_alarm_panel(station):
                LOGGER.debug(
                    "Creating alarm control panel for station %s (%s)",
                    station.sn,
                    station.type,
                )
                entities.append(XSenseAlarmControlPanel(coordinator, station))

    if entities:
        async_add_entities(entities)
    else:
        LOGGER.debug(
            "No SBS50 security alarm base station found; alarm control panel skipped"
        )


ALARM_PANEL_DEVICE_TYPES = {
    EntityType.DOOR,
    EntityType.KEYPAD,
    EntityType.MOTION,
    EntityType.REMOTE,
}


def station_supports_alarm_panel(station) -> bool:
    """Return whether the app exposes SBS50 security alarm modes for this station."""
    if station.type != "SBS50":
        return False

    for device in station.devices.values():
        definition = entity_definitions.get(device.type)
        if definition and definition.get("type") in ALARM_PANEL_DEVICE_TYPES:
            return True

    return False


class XSenseAlarmControlPanel(
    CoordinatorEntity[XSenseDataUpdateCoordinator],
    AlarmControlPanelEntity,
):
    """Alarm control panel for the X-Sense SBS50.

    The X-Sense app writes desired state to the `2nd_appmode` AWS IoT shadow.
    The base station confirms the resulting state through `2nd_safemode`.
    """

    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
    )
    _attr_code_arm_required = False
    _attr_has_entity_name = True
    _attr_name = "Alarm"

    def __init__(
        self,
        coordinator: XSenseDataUpdateCoordinator,
        station,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._station_id = station.entity_id
        self._attr_unique_id = f"{station.sn}_alarm"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, station.entity_id)},
            "name": station.name,
            "manufacturer": MANUFACTURER,
            "model": station.type,
        }
        self._safemode: str | None = None

    @property
    def _station(self):
        """Return the current station object from coordinator data."""
        return self.coordinator.data["stations"].get(self._station_id)

    @property
    def available(self) -> bool:
        """Return if the alarm control panel can be used."""
        station = self._station
        if station is None:
            return False

        return station.online is True and super().available

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return the current alarm state."""
        return SAFEMODE_TO_STATE.get(self._safemode)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated coordinator data."""
        station = self._station
        if station is None:
            self._safemode = None
            self.async_write_ha_state()
            return

        safemode = getattr(station, "safe_mode", None)
        if safemode is None:
            safemode = station.data.get("safeMode")

        if safemode != self._safemode:
            LOGGER.debug(
                "Station %s safeMode changed from %s to %s",
                station.sn,
                self._safemode,
                safemode,
            )
            self._safemode = safemode

        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Subscribe to coordinator updates and read initial state."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Disarm the alarm."""
        await self._set_safe_mode("Disarmed")

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Arm in home mode."""
        await self._set_safe_mode("Home")

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Arm in away mode."""
        await self._set_safe_mode("Away")

    async def _set_safe_mode(self, safe_mode: str) -> None:
        """Request a safeMode change through the X-Sense MQTT shadow."""
        station = self._station
        if station is None:
            raise HomeAssistantError("X-Sense station is no longer available")

        LOGGER.debug(
            "Station %s requesting safeMode %s via MQTT appMode",
            station.sn,
            safe_mode,
        )

        coordinator: XSenseDataUpdateCoordinator = self.coordinator
        api = coordinator.xsense

        payload = {
            "state": {
                "desired": {
                    "shadow": "appMode",
                    "safeMode": safe_mode,
                    "stationSN": station.sn,
                    "source": "1",
                    "forceArm": "0",
                    "userId": api.userid,
                    "userParam": "source=1",
                }
            }
        }

        topic = f"$aws/things/{station.shadow_name}/shadow/name/2nd_appmode/update"

        mqtt = coordinator.mqtt_server(station.house.mqtt_server)

        if mqtt is None or not mqtt.connected:
            LOGGER.error(
                "Station %s cannot set safeMode because MQTT is not connected",
                station.sn,
            )
            raise HomeAssistantError("X-Sense MQTT is not connected")

        try:
            await mqtt.async_publish(
                topic,
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                qos=0,
                retain=False,
            )
            LOGGER.debug(
                "Station %s published appMode command %s on %s",
                station.sn,
                safe_mode,
                topic,
            )

        except Exception as ex:  # noqa: BLE001
            LOGGER.exception(
                "Could not set safeMode %s for station %s: %s",
                safe_mode,
                station.sn,
                ex,
            )
            raise HomeAssistantError("Could not publish X-Sense safe mode command") from ex
