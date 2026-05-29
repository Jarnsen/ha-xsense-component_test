"""Alarm control panel platform voor X-Sense burglar alarm (SBS50)."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import XSenseDataUpdateCoordinator

LOGGER = logging.getLogger(__name__)

# Mapping X-Sense safeMode → HA AlarmControlPanelState
SAFEMODE_TO_STATE: dict[str, AlarmControlPanelState] = {
    "Disarmed": AlarmControlPanelState.DISARMED,
    "Home":     AlarmControlPanelState.ARMED_HOME,
    "Away":     AlarmControlPanelState.ARMED_AWAY,
}

# Mapping HA AlarmControlPanelState → X-Sense safeMode
STATE_TO_SAFEMODE: dict[str, str] = {
    "disarm":    "Disarmed",
    "arm_home":  "Home",
    "arm_away":  "Away",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Zet het alarm control panel op vanuit een config entry."""
    coordinator: XSenseDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for house in coordinator.xsense.houses.values():
        for station in house.stations.values():
            if station.type == "SBS50":
                LOGGER.debug(
                    "Alarm control panel aanmaken voor station %s (%s)",
                    station.sn,
                    station.type,
                )
                entities.append(XSenseAlarmControlPanel(coordinator, station))

    if entities:
        async_add_entities(entities)
    else:
        LOGGER.warning(
            "Geen SBS50 base station gevonden — alarm control panel niet aangemaakt."
        )


class XSenseAlarmControlPanel(
    CoordinatorEntity[XSenseDataUpdateCoordinator],
    AlarmControlPanelEntity,
):
    """Alarm control panel voor de X-Sense SBS50.

    Leest én schrijft de safeMode (Disarmed/Home/Away) via het AWS IoT
    Shadow endpoint '2nd_safemode'. Arm/disarm vanuit HA stuurt een
    'desired' state naar de SBS50, net zoals de X-Sense app dat doet.
    """

    # Arm home, arm away en disarm worden ondersteund
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
    )
    # Geen pincode vereist vanuit HA — de SBS50 accepteert cloud-commando's
    # zonder pincode (die validatie gebeurt alleen op het keypad zelf)
    _attr_code_arm_required = False
    _attr_has_entity_name = True
    _attr_name = "Alarm"

    def __init__(
        self,
        coordinator: XSenseDataUpdateCoordinator,
        station,
    ) -> None:
        """Initialiseer de entiteit."""
        super().__init__(coordinator)
        self._station = station
        self._attr_unique_id = f"{station.sn}_alarm"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, station.sn)},
            "name": f"X-Sense {station.type} {station.sn}",
            "manufacturer": "X-Sense",
            "model": station.type,
        }
        self._safemode: str | None = None

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Geef de huidige alarmstatus terug."""
        return SAFEMODE_TO_STATE.get(self._safemode)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Verwerk een update van de coordinator."""
        safemode = getattr(self._station, "safe_mode", None)
        if safemode is None:
            safemode = self._station.data.get("safeMode")

        if safemode != self._safemode:
            LOGGER.debug(
                "Station %s: safeMode gewijzigd van %s naar %s",
                self._station.sn,
                self._safemode,
                safemode,
            )
            self._safemode = safemode

        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Registreer bij de coordinator en haal initiële state op."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Ontwapen het alarm."""
        await self._set_safe_mode("Disarmed")

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Wapen in Home modus."""
        await self._set_safe_mode("Home")

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Wapen in Away modus."""
        await self._set_safe_mode("Away")

    async def _set_safe_mode(self, safe_mode: str) -> None:
        """Stuur een safeMode wijziging naar de X-Sense SBS50 via MQTT.

        Via reverse engineering is vastgesteld dat de X-Sense app een
        'desired' state publiceert naar het shadow topic '2nd_appmode'.
        De SBS50 luistert hierop, voert de modewissel uit, en bevestigt
        daarna via '2nd_safemode'.

        Topic:
            $aws/things/SBS50{sn}/shadow/name/2nd_appmode/update
        Payload:
            {
                "state": {
                    "desired": {
                        "shadow": "appMode",
                        "safeMode": "Away",
                        "stationSN": "161965C2",
                        "source": "1",
                        "forceArm": "0",
                        "userId": "<uuid>",
                        "userParam": "source=1"
                    }
                }
            }
        """
        LOGGER.debug(
            "Station %s: safeMode instellen op %s via MQTT appMode",
            self._station.sn, safe_mode,
        )

        coordinator: XSenseDataUpdateCoordinator = self.coordinator
        api = coordinator.xsense

        # Bouw de MQTT payload exact zoals de app dat doet
        payload = {
            "state": {
                "desired": {
                    "shadow": "appMode",
                    "safeMode": safe_mode,
                    "stationSN": self._station.sn,
                    "source": "1",
                    "forceArm": "0",
                    "userId": api.userid,
                    "userParam": "source=1",
                }
            }
        }

        # Topic waarop de SBS50 luistert voor mode-commando's
        topic = (
            f"$aws/things/{self._station.shadow_name}"
            f"/shadow/name/2nd_appmode/update"
        )

        # Zoek de MQTT verbinding voor dit huis
        mqtt = coordinator.mqtt_server(self._station.house.mqtt_server)

        if mqtt is None or not mqtt.connected:
            LOGGER.error(
                "Station %s: MQTT niet verbonden, kan safeMode niet instellen",
                self._station.sn,
            )
            return

        try:
            import json
            await mqtt.async_publish(topic, json.dumps(payload), qos=0, retain=False)
            LOGGER.debug(
                "Station %s: appMode commando '%s' gepubliceerd op %s",
                self._station.sn, safe_mode, topic,
            )

            # Optimistisch de UI alvast bijwerken — MQTT bevestiging volgt
            from .coordinator import _apply_safe_mode
            _apply_safe_mode(self._station, safe_mode)
            self.async_write_ha_state()

        except Exception as ex:  # noqa: BLE001
            LOGGER.error(
                "Kon safeMode niet instellen op %s voor station %s: %s",
                safe_mode, self._station.sn, ex,
            )