"""Alarm control panel platform for X-Sense SBS50 burglar alarm mode."""

from __future__ import annotations

import logging
from urllib.parse import urlencode

import voluptuous as vol
from homeassistant.components import persistent_notification
from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import XSenseDataUpdateCoordinator
from .entity import _device_info_str, coordinator_stations
from .errors import xsense_error
from .frontend import (
    FORCE_ARM_FRONTEND_URL_PATH,
    async_register_force_arm_panel,
    async_unregister_force_arm_panel,
)

LOGGER = logging.getLogger(__name__)

SAFEMODE_TO_STATE: dict[str, AlarmControlPanelState] = {
    "Disarmed": AlarmControlPanelState.DISARMED,
    "Home": AlarmControlPanelState.ARMED_HOME,
    "Away": AlarmControlPanelState.ARMED_AWAY,
}
FORCE_ARM_NOTIFICATION_ID_PREFIX = "xsense_force_arm_"
ARM_REQUEST_TIMEOUT_SECONDS = 60
FORCE_ARM_SERVICE = "force_arm"
FORCE_ARM_NOW_SERVICE = "force_arm_now"
TRIGGER_SOS_SERVICE = "trigger_sos"
CANCEL_SOS_SERVICE = "cancel_sos"
CANCEL_ALARM_SERVICE = "cancel_alarm"
SET_SOS_SOUND_SERVICE = "set_sos_sound"
FORCE_ARM_SCHEMA = {vol.Required("mode"): vol.In(("Home", "Away"))}
SET_SOS_SOUND_SCHEMA = {vol.Required("audible"): cv.boolean}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up XSense alarm control panel entities from a config entry."""
    coordinator: XSenseDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    xsense = getattr(coordinator, "xsense", None)
    houses = getattr(xsense, "houses", {}) or {}
    for house in houses.values():
        for station in house.stations.values():
            if station_supports_alarm_panel(station):
                LOGGER.debug(
                    "Creating alarm control panel for station %s (%s)",
                    station.sn,
                    station.type,
                )
                entities.append(XSenseAlarmControlPanel(coordinator, station))

    if entities:
        platform = entity_platform.current_platform.get()
        if platform is not None:
            platform.async_register_entity_service(
                FORCE_ARM_SERVICE,
                FORCE_ARM_SCHEMA,
                "async_force_arm",
            )
            platform.async_register_entity_service(
                FORCE_ARM_NOW_SERVICE,
                FORCE_ARM_SCHEMA,
                "async_force_arm_now",
            )
            platform.async_register_entity_service(
                TRIGGER_SOS_SERVICE,
                {},
                "async_trigger_sos",
            )
            platform.async_register_entity_service(
                CANCEL_SOS_SERVICE,
                {},
                "async_cancel_sos",
            )
            platform.async_register_entity_service(
                CANCEL_ALARM_SERVICE,
                {},
                "async_cancel_alarm",
            )
            platform.async_register_entity_service(
                SET_SOS_SOUND_SERVICE,
                SET_SOS_SOUND_SCHEMA,
                "async_set_sos_sound",
            )
        await async_register_force_arm_panel(hass, entry.entry_id)
        entry.async_on_unload(
            lambda: async_unregister_force_arm_panel(hass, entry.entry_id)
        )
        async_add_entities(entities)
    else:
        LOGGER.debug(
            "No SBS50 security alarm base station found; alarm control panel skipped"
        )


ALARM_PANEL_SECURITY_DEVICE_TYPES = {"SDS0A", "SMS0A", "SKP0A"}


def station_supports_alarm_panel(station) -> bool:
    """Return whether the APK exposes SBS50 security alarm modes."""
    if station.type != "SBS50":
        return False

    return any(
        device.type in ALARM_PANEL_SECURITY_DEVICE_TYPES
        for device in station.devices.values()
    )


def pending_force_arm_mode(station) -> str | None:
    """Return the arm mode waiting for app-style force-arm confirmation."""
    alarm_data = getattr(station, "alarm_data", {}) or {}
    force_reason = alarm_data.get("forceReason")
    if not force_reason:
        return None

    mode = alarm_data.get("requestedSafeMode")
    if mode in ("Home", "Away"):
        return mode
    return None


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
    _attr_translation_key = "alarm"

    def __init__(
        self,
        coordinator: XSenseDataUpdateCoordinator,
        station,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._station_id = station.entity_id
        self._entry_id = getattr(getattr(coordinator, "entry", None), "entry_id", "")
        self._attr_unique_id = f"{station.sn}_alarm"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, station.entity_id)},
            "name": _device_info_str(station.name),
            "manufacturer": MANUFACTURER,
            "model": _device_info_str(station.type),
        }
        self._safemode: str | None = None
        self._pending_force_arm_mode: str | None = None
        self._cancel_arm_request_timeout = None

    @property
    def _station(self):
        """Return the current station object from coordinator data."""
        return coordinator_stations(self.coordinator).get(self._station_id)

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

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return SBS50 bypass confirmation details."""
        station = self._station
        if station is None:
            return None

        mode = pending_force_arm_mode(station)
        if mode is None:
            return None

        alarm_data = getattr(station, "alarm_data", {}) or {}
        force_reason = alarm_data.get("forceReason")
        return {
            "force_arm_pending": True,
            "force_arm_mode": mode,
            "force_reason_count": len(force_reason)
            if isinstance(force_reason, list)
            else None,
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated coordinator data."""
        station = self._station
        if station is None:
            self._safemode = None
            self._async_cancel_arm_request_timeout()
            self._async_clear_force_arm_notification()
            self.async_write_ha_state()
            return

        pending_mode = pending_force_arm_mode(station)
        alarm_data = getattr(station, "alarm_data", {}) or {}
        if pending_mode is not None or not alarm_data.get("requestedSafeMode"):
            self._async_cancel_arm_request_timeout()
        if pending_mode != self._pending_force_arm_mode:
            self._pending_force_arm_mode = pending_mode
            if pending_mode is None:
                self._async_clear_force_arm_notification()
            else:
                self._async_create_force_arm_notification(station, pending_mode)

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

    @callback
    def _async_create_force_arm_notification(self, station, safe_mode: str) -> None:
        """Create/update the HA notification for an SBS50 bypass prompt."""
        button_name = f"Force Arm {safe_mode}"
        action_url = self._force_arm_url(safe_mode)
        persistent_notification.async_create(
            self.hass,
            (
                "One or more sensors are open.\n\n"
                f"[**{button_name}**]({action_url})\n\n"
                "Select the link to confirm the pending X-Sense arm request."
            ),
            title="X-Sense arm blocked",
            notification_id=self._force_arm_notification_id,
        )
        LOGGER.debug(
            "X-Sense SBS50 force-arm notification created: station=%s mode=%s",
            station.sn,
            safe_mode,
        )

    @callback
    def _async_clear_force_arm_notification(self) -> None:
        """Dismiss the HA notification for a cleared SBS50 bypass prompt."""
        persistent_notification.async_dismiss(
            self.hass, self._force_arm_notification_id
        )

    @property
    def _force_arm_notification_id(self) -> str:
        """Return the stable notification id for this SBS50 alarm panel."""
        return f"{FORCE_ARM_NOTIFICATION_ID_PREFIX}{self._station_id}"

    def _force_arm_url(self, safe_mode: str) -> str:
        """Return the hidden HA action-panel URL for force-arm confirmation."""
        params = urlencode(
            {
                "entity_id": self.entity_id,
                "mode": safe_mode,
            }
        )
        return f"/{FORCE_ARM_FRONTEND_URL_PATH}#{params}"

    async def async_added_to_hass(self) -> None:
        """Subscribe to coordinator updates and read initial state."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    async def async_will_remove_from_hass(self) -> None:
        """Dismiss entry-owned notifications when the entity unloads."""
        self._async_cancel_arm_request_timeout()
        self._async_clear_force_arm_notification()
        await super().async_will_remove_from_hass()

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Disarm the alarm."""
        await self._set_safe_mode("Disarmed", force_arm="0")

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Arm in home mode."""
        await self._set_safe_mode("Home", force_arm="0")

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Arm in away mode."""
        await self._set_safe_mode("Away", force_arm="0")

    async def async_force_arm(self, mode: str) -> None:
        """Confirm the exact Home or Away request currently awaiting bypass."""
        station = self._station
        if station is None:
            raise xsense_error("station_unavailable")

        pending_mode = pending_force_arm_mode(station)
        if pending_mode != mode:
            raise xsense_error("force_arm_not_pending", mode=mode)

        await self._async_force_arm_mode(mode)

    async def async_force_arm_now(self, mode: str) -> None:
        """Force arm directly for a Home Assistant automation."""
        if self._station is None:
            raise xsense_error("station_unavailable")

        await self._async_force_arm_mode(mode)

    async def async_trigger_sos(self) -> None:
        """Trigger the SBS50 SOS alarm using the APK command."""
        station = self._station
        if station is None:
            raise xsense_error("station_unavailable")
        await self.coordinator.xsense.trigger_sos(station, sos_type="1")

    async def async_cancel_sos(self) -> None:
        """Cancel the SBS50 SOS alarm using the APK command."""
        station = self._station
        if station is None:
            raise xsense_error("station_unavailable")
        await self.coordinator.xsense.cancel_sos(station)

    async def async_cancel_alarm(self) -> None:
        """Cancel the active SBS50 sensor alarm using the APK command."""
        station = self._station
        if station is None:
            raise xsense_error("station_unavailable")
        await self.coordinator.xsense.cancel_alarm(station)

    async def async_set_sos_sound(self, audible: bool) -> None:
        """Choose flashing light only or flashing light plus buzzer for SOS."""
        station = self._station
        if station is None:
            raise xsense_error("station_unavailable")
        await self.coordinator.xsense.set_sos_sound(
            station, "1" if audible else "0"
        )

    async def _async_force_arm_mode(self, mode: str) -> None:
        """Send an APK force-arm command and clear any pending prompt."""
        station = self._station
        if station is None:
            raise xsense_error("station_unavailable")

        self._async_clear_arm_request(station)
        await self._set_safe_mode(mode, force_arm="1")
        self.async_write_ha_state()

    @callback
    def _async_clear_arm_request(self, station) -> None:
        """Clear local state for an APK-style mode request."""
        self._async_cancel_arm_request_timeout()
        station.set_alarm_data(
            {
                "forceReason": None,
                "safeModeAim": None,
                "requestedSafeMode": None,
                "exitDelay": None,
            }
        )
        self._pending_force_arm_mode = None
        self._async_clear_force_arm_notification()

    @callback
    def _async_cancel_arm_request_timeout(self) -> None:
        """Cancel the active normal-arm response timeout."""
        if self._cancel_arm_request_timeout is not None:
            self._cancel_arm_request_timeout()
            self._cancel_arm_request_timeout = None

    @callback
    def _async_arm_request_timed_out(self, _now) -> None:
        """Expire an unanswered mode request like the APK's 60-second timer."""
        self._cancel_arm_request_timeout = None
        station = self._station
        if station is None:
            return
        alarm_data = getattr(station, "alarm_data", {}) or {}
        if not alarm_data.get("requestedSafeMode") or alarm_data.get("forceReason"):
            return
        LOGGER.debug("Station %s arm request timed out", station.sn)
        self._async_clear_arm_request(station)
        self.async_write_ha_state()

    @callback
    def _async_start_arm_request_timeout(self) -> None:
        """Start the APK-aligned normal-arm response timeout."""
        self._async_cancel_arm_request_timeout()
        self._cancel_arm_request_timeout = async_call_later(
            self.hass,
            ARM_REQUEST_TIMEOUT_SECONDS,
            self._async_arm_request_timed_out,
        )

    async def _set_safe_mode(self, safe_mode: str, *, force_arm: str) -> None:
        """Request a safeMode change through the APK app-mode shadow."""
        station = self._station
        if station is None:
            raise xsense_error("station_unavailable")

        LOGGER.debug(
            "Station %s requesting safeMode %s via appMode forceArm=%s",
            station.sn,
            safe_mode,
            force_arm,
        )

        coordinator: XSenseDataUpdateCoordinator = self.coordinator
        api = coordinator.xsense

        if safe_mode in ("Home", "Away") and force_arm == "0":
            current_mode = getattr(station, "alarm_mode", None)
            if current_mode == safe_mode:
                self._async_clear_arm_request(station)
                return
            station.set_alarm_data(
                {
                    "forceReason": None,
                    "safeModeAim": None,
                    "requestedSafeMode": safe_mode,
                    "exitDelay": None,
                }
            )
            self._pending_force_arm_mode = None
            self._async_clear_force_arm_notification()
            self._async_start_arm_request_timeout()
        elif safe_mode == "Disarmed":
            self._async_clear_arm_request(station)

        try:
            await api.set_station_mode(station, safe_mode, force_arm=force_arm)
            LOGGER.debug(
                "Station %s sent appMode command %s forceArm=%s",
                station.sn,
                safe_mode,
                force_arm,
            )

        except Exception as ex:  # noqa: BLE001
            if force_arm == "0":
                self._async_clear_arm_request(station)
            LOGGER.exception(
                "Could not set safeMode %s forceArm=%s for station %s: %s",
                safe_mode,
                force_arm,
                station.sn,
                ex,
            )
            raise xsense_error("safe_mode_publish_failed") from ex
