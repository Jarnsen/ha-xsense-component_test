"""Generic XSense Entity Class."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .api.entity import Entity
from .api.entity_map import EntityType

from homeassistant.const import ATTR_VIA_DEVICE
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER

if TYPE_CHECKING:
    from .coordinator import XSenseDataUpdateCoordinator


OFFLINE_STATES = {False, 0, "0", "false", "False", "offline", "Offline"}
_APK_CAMERA_NON_OFFLINE_STATUSES = {11, 12}


def _apk_entity_is_available(entity: Entity) -> bool:
    """Return whether the APK treats this entity as not offline."""
    if getattr(entity, "entity_type", None) == EntityType.CAMERA:
        if (
            entity.online is False
            and entity.data.get("deviceStatus") in _APK_CAMERA_NON_OFFLINE_STATUSES
        ):
            return True
    return entity.online is True


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
        if self._station_id:
            return self.coordinator.data["devices"].get(self._dev_id)
        return self.coordinator.data["stations"].get(self._dev_id)

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
            station = self.coordinator.data["stations"].get(self._station_id)
            return (
                station is not None
                and _apk_entity_is_available(station)
                and entity.online is not False
            )

        return _apk_entity_is_available(entity)

    @property
    def available(self) -> bool:
        """Return if entity data is available."""
        return self._current_entity() is not None and super().available
