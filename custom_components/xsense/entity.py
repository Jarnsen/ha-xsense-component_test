"""Generic XSense Entity Class."""

from __future__ import annotations

from collections.abc import Callable
import logging
from typing import TYPE_CHECKING, Any

from .python_xsense.entity import Entity
from .python_xsense.entity_map import EntityType
from .python_xsense.async_xsense import (
    camera_addx_serial,
    camera_for_identifier,
    is_camera_entity,
)

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .identity_store import (
    IdentityConflictError,
    IdentityStoreClosedError,
    validate_current_identities,
)

LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .coordinator import XSenseDataUpdateCoordinator


OFFLINE_STATES = {False, 0, "0", "false", "False", "offline", "Offline"}
_APK_CAMERA_NON_OFFLINE_STATUSES = {11, 12}
DEVICE_ENTITY_WITHOUT_STATION = ""


def setup_dynamic_entities(
    entry,
    coordinator: XSenseDataUpdateCoordinator,
    async_add_entities,
    entity_factory: Callable[[], list[Any]],
) -> None:
    """Add current entities and any new entities discovered on later refreshes."""
    added_unique_ids: set[str] = set()

    def _new_entities() -> list[Any]:
        entities = []
        for entity in entity_factory():
            unique_id = str(entity.unique_id)
            if unique_id in added_unique_ids:
                continue
            added_unique_ids.add(unique_id)
            entities.append(entity)
        return entities

    async_add_entities(_new_entities())

    def _async_add_new_entities() -> None:
        manager = getattr(coordinator, "_xsense_identity_store", None)
        if getattr(coordinator, "_shutting_down", False) or (manager is not None and manager.closed):
            return
        try:
            entities = _new_entities()
        except IdentityConflictError:
            LOGGER.error("X-Sense discovery stopped: conflicting physical device identifiers")
            return
        if entities:
            async_add_entities(entities)

    if hasattr(entry, "async_on_unload") and hasattr(coordinator, "async_add_listener"):
        entry.async_on_unload(coordinator.async_add_listener(_async_add_new_entities))


def _device_info_str(value: object) -> str | None:
    """Return a Home Assistant DeviceInfo-safe string value."""
    if value in (None, ""):
        return None
    return str(value)


def _software_version(value: object) -> str | None:
    """Return a normalized firmware/software version string."""
    version = _device_info_str(value)
    if version is None:
        return None
    return version.removeprefix("v")


def _parent_device_info(
    coordinator: XSenseDataUpdateCoordinator,
    station: Entity | None,
    station_id: str,
) -> tuple[str, object] | None:
    """Return the non-deprecated parent-device field and value."""
    if not hasattr(coordinator, "entry") or not hasattr(coordinator, "hass"):
        return None

    identifier = (DOMAIN, station_id)
    entry_id = coordinator.entry.entry_id
    registry = dr.async_get(coordinator.hass)

    get_device_id = getattr(dr, "async_get_device_id_by_identifier", None)
    if get_device_id is not None:
        try:
            device_id = get_device_id(
                coordinator.hass,
                identifier,
                config_entry_id=entry_id,
            )
        except ValueError:
            device_id = None
        else:
            if device_id is not None:
                return "via_device_id", device_id

    get_device = getattr(registry, "async_get_device_by_identifier", None)
    if get_device is not None:
        device = get_device(identifier, config_entry_id=entry_id)
        if device is not None:
            return "via_device_id", device.id

    parent_info: dict[str, Any] = {
        "config_entry_id": entry_id,
        "identifiers": {identifier},
        "manufacturer": MANUFACTURER,
    }
    if station is not None:
        parent_info.update(
            model=_device_info_str(station.type),
            name=_device_info_str(station.name),
        )
        if sw_version := _software_version(station.data.get("sw")):
            parent_info["sw_version"] = sw_version
    return "via_device_id", registry.async_get_or_create(**parent_info).id


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
        self._camera_identity = (
            camera_addx_serial(entity) if is_camera_entity(entity) else None
        )
        station = getattr(entity, "station", None)
        self._station_serial = _entity_serial(station)
        self._physical_identity = (
            _serial_identity(entity) if not self._camera_identity else None
        )
        self._parent_identity = _serial_identity(station)
        stable_id = _stable_device_id(coordinator, entity, self._physical_identity)

        self._attr_unique_id = f"{stable_id}-{self.entity_description.key}".replace(
            "_", "-"
        ).lower()

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, stable_id)},
            manufacturer=MANUFACTURER,
            model=_device_info_str(entity.type),
            name=_device_info_str(entity.name),
        )
        if sw_version := _software_version(entity.data.get("sw")):
            self._attr_device_info["sw_version"] = sw_version
        if station_id:
            parent_id = (
                _stable_device_id(coordinator, station, self._parent_identity)
                if station is not None
                else station_id
            )
            parent_info = _parent_device_info(
                coordinator,
                station,
                parent_id,
            )
            if parent_info is not None:
                parent_field, parent_value = parent_info
                self._attr_device_info[parent_field] = parent_value

    def _current_entity(self) -> Entity | None:
        """Return the current coordinator entity for this Home Assistant entity."""
        data = self.coordinator.data or {}
        if self._station_id is not None:
            entities = data.get("devices", {})
        else:
            entities = data.get("stations", {})
        return self._current_entity_from(entities)

    def _current_entity_from(self, entities: dict[str, Entity]) -> Entity | None:
        """Resolve this entity from one coordinator collection."""
        if self._camera_identity:
            if entity := entities.get(self._dev_id):
                return entity
            return camera_for_identifier(
                [entity for entity in entities.values() if is_camera_entity(entity)],
                self._camera_identity,
            )
        return _entity_by_id_or_serial(
            entities, self._dev_id, self._entity_serial, self._physical_identity
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
                self._parent_identity,
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
    entities: dict[str, Entity],
    entity_id: str | None,
    serial: str | None,
    identity: tuple | None = None,
) -> Entity | None:
    """Return an entity by stable ID, falling back to its physical serial."""
    if entity_id is not None and (entity := entities.get(entity_id)):
        if identity is None or _serial_identity(entity) == identity:
            return entity
    if serial is None:
        return None
    matches = [
        entity
        for entity in entities.values()
        if _entity_serial(entity) == serial
        and (identity is None or _serial_identity(entity) == identity)
    ]
    return matches[0] if len(matches) == 1 else None


def _serial_identity(entity: Entity | None) -> tuple | None:
    """Scope serial fallback to the same model, house, and physical parent."""
    serial = _entity_serial(entity)
    if serial is None:
        return None
    station = getattr(entity, "station", None)
    if station is not None and _entity_serial(station) is None:
        return None
    house = getattr(station if station is not None else entity, "house", None)
    return (
        station is not None,
        str(house.house_id) if getattr(house, "house_id", None) is not None else None,
        _entity_serial(station),
        getattr(entity, "type", None),
        serial,
    )


def _stable_device_id(coordinator, entity: Entity, identity: tuple | None):
    """Preserve observed IDs across unambiguous physical identity rollovers."""
    manager = getattr(coordinator, "_xsense_identity_store", None)
    if getattr(coordinator, "_shutting_down", False) or (manager is not None and manager.closed):
        raise IdentityStoreClosedError("Cannot assign identities while entry unloads")
    validate_current_identities(coordinator)
    if identity is None:
        return entity.entity_id
    collection = "devices" if identity[0] else "stations"
    current = (getattr(coordinator, "data", None) or {}).get(collection, {})
    matches = [item for item in current.values() if _serial_identity(item) == identity]
    if len(matches) != 1:
        return entity.entity_id
    stable_ids = getattr(coordinator, "_xsense_stable_device_ids", None)
    if stable_ids is None:
        stable_ids = coordinator._xsense_stable_device_ids = {}
    if identity not in stable_ids:
        stable_ids[identity] = entity.entity_id
        manager = getattr(coordinator, "_xsense_identity_store", None)
        if manager is not None:
            manager.async_schedule_save()
    return stable_ids[identity]


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
