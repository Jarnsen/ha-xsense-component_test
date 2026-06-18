"""Support for X-Sense switches."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from .api.device import Device
from .api.entity import Entity

from homeassistant import config_entries
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import XSenseDataUpdateCoordinator
from .entity import (
    XSenseEntity,
    coordinator_devices,
    coordinator_stations,
    device_station_id,
)


def boolean_state(value) -> bool | None:
    """Return the normalized state for explicit X-Sense boolean payload values."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value == 1:
            return True
        if value == 0:
            return False
        return None
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "on"}:
            return True
        if normalized in {"0", "false", "off"}:
            return False
    return None


def on_off_value(value: bool) -> str:
    """Return the X-Sense on/off payload value."""
    return "1" if value else "0"


def has_data(key: str) -> Callable[[Entity], bool]:
    """Return an exists function for an X-Sense data key."""
    return lambda entity: key in entity.data


def data_bool(key: str) -> Callable[[Entity], bool | None]:
    """Return a value function for an X-Sense boolean data key."""
    return lambda entity: boolean_state(entity.data[key])


def entity_topic(entity: Entity) -> str:
    """Return the settings shadow topic used by the X-Sense app."""
    station = getattr(entity, "station", None)
    if station and station.type == "SBS50":
        return f"2nd_cfg_{entity.sn}"
    return f"info_{entity.sn}"


@dataclass(kw_only=True, frozen=True)
class XSenseSwitchEntityDescription(SwitchEntityDescription):
    """Describes X-Sense switch entity."""

    data_key: str
    exists_fn: Callable[[Entity], bool]
    value_fn: Callable[[Entity], bool | None]
    read_key: str | None = None
    addx_key: str | None = None
    write_value_fn: Callable[[bool], str] = on_off_value
    entity_category: EntityCategory | None = EntityCategory.CONFIG


SWITCHES: tuple[XSenseSwitchEntityDescription, ...] = (
    XSenseSwitchEntityDescription(
        key="led_light",
        data_key="ledLight",
        name="LED Light",
        icon="mdi:led-on",
        exists_fn=has_data("ledLight"),
        value_fn=data_bool("ledLight"),
    ),
    XSenseSwitchEntityDescription(
        key="light_power",
        data_key="on",
        name="Light Power",
        icon="mdi:lightbulb",
        exists_fn=lambda entity: (
            entity.entity_type is not None
            and entity.entity_type.value == "light"
            and "on" in entity.data
        ),
        value_fn=data_bool("on"),
    ),
    XSenseSwitchEntityDescription(
        key="alarm_enabled",
        data_key="alarmEnable",
        read_key="alarmEnabled",
        name="Alarm Enabled",
        icon="mdi:bell-check",
        exists_fn=lambda entity: (
            "alarmEnable" in entity.data or "alarmEnabled" in entity.data
        ),
        value_fn=lambda entity: boolean_state(
            entity.data.get("alarmEnable", entity.data.get("alarmEnabled"))
        ),
    ),
    XSenseSwitchEntityDescription(
        key="continued_alarm",
        data_key="continueAlarm",
        read_key="continuedAlarm",
        name="Continued Alarm",
        icon="mdi:bell-plus",
        exists_fn=lambda entity: (
            "continueAlarm" in entity.data or "continuedAlarm" in entity.data
        ),
        value_fn=lambda entity: boolean_state(
            entity.data.get("continueAlarm", entity.data.get("continuedAlarm"))
        ),
    ),
    XSenseSwitchEntityDescription(
        key="chirp_tone_enabled",
        data_key="chirpToneEnable",
        name="Chirp Tone Enabled",
        icon="mdi:volume-high",
        exists_fn=has_data("chirpToneEnable"),
        value_fn=data_bool("chirpToneEnable"),
    ),
    XSenseSwitchEntityDescription(
        key="reminder_enabled",
        data_key="remindOn",
        name="Reminder Enabled",
        icon="mdi:bell-clock",
        exists_fn=has_data("remindOn"),
        value_fn=data_bool("remindOn"),
    ),
    XSenseSwitchEntityDescription(
        key="reminder_tone_enabled",
        data_key="remindToneEnable",
        name="Reminder Tone Enabled",
        icon="mdi:volume-high",
        exists_fn=has_data("remindToneEnable"),
        value_fn=data_bool("remindToneEnable"),
    ),
    XSenseSwitchEntityDescription(
        key="await_enabled",
        data_key="awaitEnable",
        name="Await Enabled",
        icon="mdi:timer-sand",
        exists_fn=has_data("awaitEnable"),
        value_fn=data_bool("awaitEnable"),
    ),
    XSenseSwitchEntityDescription(
        key="pir_enabled",
        data_key="pirEnable",
        name="PIR Enabled",
        icon="mdi:motion-sensor",
        exists_fn=has_data("pirEnable"),
        value_fn=data_bool("pirEnable"),
    ),
    XSenseSwitchEntityDescription(
        key="sunshine_enabled",
        data_key="sunshineEnable",
        name="Sunshine Enabled",
        icon="mdi:white-balance-sunny",
        exists_fn=has_data("sunshineEnable"),
        value_fn=data_bool("sunshineEnable"),
    ),
    XSenseSwitchEntityDescription(
        key="key_sound_enabled",
        data_key="keySound",
        name="Key Sound Enabled",
        icon="mdi:volume-high",
        exists_fn=has_data("keySound"),
        value_fn=data_bool("keySound"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the X-Sense switch entry."""
    devices: list[Device] = []
    coordinator: XSenseDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    for station in coordinator_stations(coordinator).values():
        devices.extend(
            XSenseSwitchEntity(coordinator, station, description)
            for description in SWITCHES
            if description.exists_fn(station)
        )

    for dev in coordinator_devices(coordinator).values():
        devices.extend(
            XSenseSwitchEntity(
                coordinator, dev, description, station_id=device_station_id(dev)
            )
            for description in SWITCHES
            if description.exists_fn(dev)
        )

    async_add_entities(devices)


class XSenseSwitchEntity(XSenseEntity, SwitchEntity):
    """Switches for X-Sense settings."""

    entity_description: XSenseSwitchEntityDescription

    def __init__(
        self,
        coordinator: XSenseDataUpdateCoordinator,
        entity: Entity,
        entity_description: XSenseSwitchEntityDescription,
        station_id: str | None = None,
    ) -> None:
        """Set up the instance."""
        self._station_id = station_id
        self.entity_description = entity_description
        self._attr_available = False

        super().__init__(coordinator, entity, station_id)

    @property
    def available(self) -> bool:
        """Return if this control can be used."""
        return self._current_entity_is_online()

    @property
    def is_on(self) -> bool | None:
        """Return the state of the switch."""
        entity = self._current_entity()
        if entity is None:
            return None

        return self.entity_description.value_fn(entity)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the X-Sense setting."""
        await self._async_set_state(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the X-Sense setting."""
        await self._async_set_state(False)

    async def _async_set_state(self, enabled: bool) -> None:
        """Write the switch state through the X-Sense device settings shadow."""
        xsense = self.coordinator.xsense
        entity = self._current_entity()
        if entity is None:
            raise HomeAssistantError("X-Sense entity is no longer available")

        station = getattr(entity, "station", entity)
        if self.entity_description.data_key == "on":
            await xsense.update_light_power(entity, enabled)
            entity.data[self.entity_description.data_key] = enabled
            self.coordinator.async_update_listeners()
            return

        desired = {
            "deviceSN": entity.sn,
            "shadow": "infoDev",
            "stationSN": station.sn,
            "time": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
            "userId": xsense.userid,
            self.entity_description.data_key: self.entity_description.write_value_fn(
                enabled
            ),
        }
        topic = entity_topic(entity)

        await xsense.do_thing(station, topic, {"state": {"desired": desired}})
        entity.data[self.entity_description.data_key] = enabled
        if self.entity_description.read_key:
            entity.data[self.entity_description.read_key] = enabled
        self.coordinator.async_update_listeners()
