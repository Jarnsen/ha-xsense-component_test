"""Generic XSense Entity Class."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .python_xsense.entity import Entity
from .python_xsense.entity_map import EntityType

from homeassistant.const import ATTR_VIA_DEVICE
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER

if TYPE_CHECKING:
    from .coordinator import XSenseDataUpdateCoordinator


OFFLINE_STATES = {False, 0, "0", "false", "False", "offline", "Offline"}
_APK_CAMERA_NON_OFFLINE_STATUSES = {11, 12}
DEVICE_ENTITY_WITHOUT_STATION = ""


def _apk_entity_is_available(entity: Entity) -> bool:
    """Return whether the APK treats this entity as not offline."""
    if getattr(entity, "entity_type", None) == EntityType.CAMERA:
        if (
            entity.online is False
            and entity.data.get("deviceStatus") in _APK_CAMERA_NON_OFFLINE_STATUSES
        ):
            return True
    return entity.online is True


def _entity_is_not_explicitly_offline(entity: Entity) -> bool:
    """Return whether the entity has not reported an authoritative offline flag."""
    return entity.online is not False or not getattr(
        entity, "_online_from_explicit_flag", False
    )


class XSenseEntity(CoordinatorEntity):
    """Represent a XSense Entity."""

    _attr_has_entity_name = True
    _station_id: str | None = None

    def __init__(
        self,
        coordinator: XSenseDataUpdateCoordinator,
        entity: Entity,
        station_id: str | None = None,
    ) -> None:
        """Initialise the gateway."""
        super().__init__(coordinator)
        self._dev_id = entity.entity_id
        self._station_id = station_id
        self._entity_serial = _entity_serial(entity)
        station = getattr(entity, "station", None)
        self._station_serial = _entity_serial(station)

        self._attr_unique_id = (
            f"{entity.entity_id}-{self.entity_description.key}".replace(
                "_", "-"
            ).lower()
        )

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entity.entity_id)},
            manufacturer=MANUFACTURER,
            model=entity.type,
            name=entity.name,
        )
        if "sw" in entity.data and entity.data["sw"]:
            self._attr_device_info["sw_version"] = entity.data["sw"].removeprefix("v")
        if station_id:
            parent = (DOMAIN, station_id)
            self._attr_device_info.update({ATTR_VIA_DEVICE: parent})

    def _current_entity(self) -> Entity | None:
        """Return the current coordinator entity for this Home Assistant entity."""
        data = self.coordinator.data or {}
        if self._station_id is not None:
            return _entity_by_id_or_serial(
                data.get("devices", {}), self._dev_id, self._entity_serial
            )
        return _entity_by_id_or_serial(
            data.get("stations", {}), self._dev_id, self._entity_serial
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to updates."""
        self._handle_coordinator_update()
        await super().async_added_to_hass()

    def _current_entity_is_online(self) -> bool:
        """Return if the current X-Sense entity and parent station are online."""
        entity = self._current_entity()
        if entity is None or not super().available:
            return False

        if self._station_id:
            station = _entity_by_id_or_serial(
                (self.coordinator.data or {}).get("stations", {}),
                self._station_id,
                self._station_serial,
            )
            return (
                station is not None
                and _entity_is_not_explicitly_offline(station)
                and _entity_is_not_explicitly_offline(entity)
            )

        return _apk_entity_is_available(entity)

    @property
    def available(self) -> bool:
        """Return if entity data is available."""
        return self._current_entity() is not None and super().available


def coordinator_stations(coordinator: XSenseDataUpdateCoordinator) -> dict:
    """Return coordinator station records, tolerating partial refresh state."""
    return (coordinator.data or {}).get("stations", {})


def coordinator_devices(coordinator: XSenseDataUpdateCoordinator) -> dict:
    """Return coordinator device records, tolerating partial refresh state."""
    return (coordinator.data or {}).get("devices", {})


def _entity_by_id_or_serial(
    entities: dict[str, Entity], entity_id: str | None, serial: str | None
) -> Entity | None:
    """Return an entity by stable ID, falling back to its physical serial."""
    if entity_id is not None and (entity := entities.get(entity_id)):
        return entity
    if serial is None:
        return None
    return next(
        (entity for entity in entities.values() if _entity_serial(entity) == serial),
        None,
    )


def _entity_serial(entity: Entity | None) -> str | None:
    """Return a normalized X-Sense entity serial."""
    if entity is None:
        return None
    serial = getattr(entity, "sn", None)
    if serial in (None, ""):
        return None
    return str(serial)


def device_station_id(device: Entity) -> str:
    """Return a device parent station ID or a device-entity sentinel."""
    station = getattr(device, "station", None)
    return getattr(station, "entity_id", None) or DEVICE_ENTITY_WITHOUT_STATION
