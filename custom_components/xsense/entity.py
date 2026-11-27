"""Generic XSense Entity Class."""

from __future__ import annotations

import logging
from collections.abc import Callable, Collection, Mapping
from functools import lru_cache
from time import perf_counter
from typing import TYPE_CHECKING, Any
from weakref import ReferenceType, ref

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .identity_store import (
    IdentityConflictError,
    IdentityStoreClosedError,
    validate_current_identities,
)
from .python_xsense.async_xsense import (
    camera_addx_serial,
    camera_for_identifier,
    is_camera_entity,
)
from .python_xsense.entity import Entity
from .python_xsense.entity_map import EntityType

LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .coordinator import XSenseDataUpdateCoordinator


OFFLINE_STATES = {False, "0", "false", "False", "offline", "Offline"}
_APK_CAMERA_NON_OFFLINE_STATUSES = {11, 12}
DEVICE_ENTITY_WITHOUT_STATION = ""
_UNREGISTERED_DEVICE_ID = object()
_NO_CAPABILITY_CONTEXT = object()


def setup_dynamic_entities(
    entry,
    coordinator: XSenseDataUpdateCoordinator,
    async_add_entities,
    entity_factory: Callable[[Callable[..., bool], Mapping[str, Entity]], list[Any]],
    *,
    include_local_only: bool = False,
) -> None:
    """Add current entities and any new entities discovered on later refreshes."""
    added_unique_ids: set[str] = set()
    registered_keys: dict[str, set[str]] = {}
    known_devices: Mapping[str, Entity] = {}
    last_scope: frozenset[tuple] | None = None
    scoped_serials: Collection[str] = ()

    @lru_cache(maxsize=1024)
    def discovery_unique_id(stable_id: str, key: str) -> str:
        # Cache the string, not eligibility or whether it was added.
        return _entity_unique_id(stable_id, key)

    def _new_entities() -> list[Any]:
        nonlocal known_devices, last_scope, scoped_serials
        # Discovery runs synchronously inside MQTT delivery. Share one identity
        # index across constructors instead of scanning every device per entity.
        identity_count = len(getattr(coordinator, "_xsense_stable_device_ids", ()))
        scope = getattr(coordinator, "_mqtt_child_write_scope", None)
        validation = coordinator.__dict__.get("_mqtt_discovery_validation")
        shared_ids = None
        if validation is None:
            counts: dict[tuple, int] = {}
            validate_current_identities(coordinator, counts=counts)
        else:
            counts = validation.counts_for(coordinator, validate_current_identities)
            if scope is None:
                shared_ids = validation.stable_id_cache(counts)
        previous = coordinator.__dict__.get("_xsense_discovery_identity_counts")
        coordinator._xsense_discovery_identity_counts = counts
        try:
            stable_ids = {}
            requested_ids = None

            def resolve_id(item: Entity, *, register: bool):
                api_id = item.entity_id
                cached = stable_ids.get(api_id)
                if cached is not None and cached[0] is item and (
                    not register or cached[1] is not _UNREGISTERED_DEVICE_ID
                ):
                    return cached[1]
                camera = is_camera_entity(item)
                if (
                    shared_ids is not None and not register and not camera
                    and (verified := shared_ids.get(api_id)) is not None and verified[0] is item
                ):
                    _, saved_id, identity = verified
                    owners = getattr(coordinator, "_xsense_stable_device_ids", None)
                    manager = getattr(coordinator, "_xsense_identity_store", None)
                    if (
                        owners is not None and owners.get(identity, _UNREGISTERED_DEVICE_ID) == saved_id
                        and not getattr(coordinator, "_shutting_down", False)
                        and not (manager is not None and manager.closed)
                        and _matches_serial_identity(item, identity)
                    ):
                        stable_ids[api_id] = verified
                        return saved_id
                camera_identity = camera_addx_serial(item) if camera else None
                identity = None if camera_identity else _serial_identity(item)
                stable_id = _stable_device_id(coordinator, item, identity, register=register)
                resolved = None
                if (
                    shared_ids is not None and not register and not camera
                    and identity is not None and stable_id is not _UNREGISTERED_DEVICE_ID
                ):
                    collection = "devices" if identity[0] else "stations"
                    if counts.get((collection, identity)) == 1:
                        resolved = shared_ids[api_id] = (item, stable_id, identity)
                stable_ids[api_id] = resolved if resolved is not None else (item, stable_id)
                return stable_id

            def should_add(item: Entity, key: str, eligible=None, context=_NO_CAPABILITY_CONTEXT) -> bool:
                nonlocal requested_ids
                stable_id = _UNREGISTERED_DEVICE_ID
                if eligible is not None:
                    if (registered := registered_keys.get(key)) is not None:
                        stable_id = resolve_id(item, register=False)
                        if stable_id in registered:
                            return False
                    if not (eligible(item) if context is _NO_CAPABILITY_CONTEXT else eligible(item, context)):
                        return False
                if stable_id is _UNREGISTERED_DEVICE_ID:
                    stable_id = resolve_id(item, register=True)
                unique_id = discovery_unique_id(stable_id, key)
                if unique_id in added_unique_ids:
                    return False
                if requested_ids is None:
                    requested_ids = {}
                requested_ids[unique_id] = (stable_id, key)
                return True

            shared_devices = validation.devices if validation is not None else None
            devices = shared_devices
            if devices is None:
                live_devices = coordinator_devices(coordinator)
                if not include_local_only and coordinator.__dict__.get("_local_only_devices"):
                    devices = {
                        key: item for key, item in live_devices.items()
                        if not getattr(item, "local_mqtt_only", False)
                    }
                else:
                    devices = dict(live_devices)
            scan_devices = devices
            if scope is not None:
                if scope != last_scope:
                    scoped_serials = {identity[-1] for identity in scope}
                    last_scope = scope
                if shared_devices is not None:
                    scan_devices = validation.scoped_devices(
                        known_devices, scope, scoped_serials, _scoped_discovery_devices,
                    )
                else:
                    scan_devices = _scoped_discovery_devices(devices, known_devices, scope, scoped_serials)
            candidates = entity_factory(should_add, scan_devices)
            # Constructors can assign new stable IDs. Check them before adding
            # anything to HA, preserving conflict detection for the whole batch.
            if candidates or len(getattr(coordinator, "_xsense_stable_device_ids", ())) != identity_count:
                validate_current_identities(coordinator)
            known_devices = devices
        finally:
            if previous is None:
                coordinator.__dict__.pop("_xsense_discovery_identity_counts", None)
            else:
                coordinator._xsense_discovery_identity_counts = previous
        entities = []
        for entity in candidates:
            unique_id = str(entity.unique_id)
            if unique_id in added_unique_ids:
                continue
            added_unique_ids.add(unique_id)
            # A candidate may be rejected by its factory. Skip future checks
            # only after that exact ID makes it into the addition batch.
            if requested_ids is not None and (requested := requested_ids.get(unique_id)) is not None:
                stable_id, key = requested
                registered_keys.setdefault(key, set()).add(stable_id)
            entities.append(entity)
        return entities

    async_add_entities(_new_entities())

    def _async_add_new_entities() -> None:
        manager = getattr(coordinator, "_xsense_identity_store", None)
        if getattr(coordinator, "_shutting_down", False) or (manager is not None and manager.closed):
            return
        timing = getattr(coordinator, "_mqtt_callback_timing", None)
        started = perf_counter() if timing is not None else 0.0
        try:
            entities = _new_entities()
        except IdentityConflictError:
            LOGGER.error("X-Sense discovery stopped: conflicting physical device identifiers")
            return
        finally:
            if timing is not None:
                timing.discovery_seconds += perf_counter() - started
                timing.discovery_calls += 1
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
    station_id: str,
) -> tuple[str, object] | None:
    """Return a parent-device link supported by the running HA version."""
    if not hasattr(coordinator, "entry") or not hasattr(coordinator, "hass"):
        return None

    identifier = (DOMAIN, station_id)
    entry_id = coordinator.entry.entry_id

    # DeviceInfo gained via_device_id in HA 2026.8. Older supported releases
    # require the identifier-based field and reject the newer key entirely.
    if "via_device_id" not in getattr(DeviceInfo, "__annotations__", {}):
        return "via_device", identifier

    get_device_id = getattr(dr, "async_get_device_id_by_identifier", None)
    if get_device_id is not None:
        try:
            device_id = get_device_id(
                coordinator.hass,
                identifier,
                config_entry_id=entry_id,
            )
        except ValueError:
            return None
        if device_id is not None:
            return "via_device_id", device_id
        return None

    try:
        registry = dr.async_get(coordinator.hass)
    except RuntimeError:
        return None

    get_device = getattr(registry, "async_get_device_by_identifier", None)
    if get_device is None:
        return None

    device = get_device(identifier, config_entry_id=entry_id)
    if device is None:
        return None
    return "via_device_id", device.id


def _apk_entity_is_available(entity: Entity) -> bool:
    """Return whether the APK treats this entity as not offline."""
    if getattr(entity, "entity_type", None) == EntityType.CAMERA and (
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
    _mqtt_child_state_only = False
    _accepts_local_only = False
    _mqtt_parent_availability_independent = False
    _last_control_record: ReferenceType[Entity] | None = None

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
        if is_camera_entity(entity):
            self._mqtt_child_state_only = False
        station = getattr(entity, "station", None)
        self._station_serial = _entity_serial(station)
        self._physical_identity = (
            _serial_identity(entity) if not self._camera_identity else None
        )
        self._parent_identity = _serial_identity(station)
        stable_id = _stable_device_id(coordinator, entity, self._physical_identity)
        self._parent_device_stable_id = (
            _stable_device_id(coordinator, station, self._parent_identity)
            if station_id and station is not None
            else station_id or None
        )

        self._attr_unique_id = _entity_unique_id(stable_id, self.entity_description.key)

        self._device_info_fields = {
            "identifiers": {(DOMAIN, stable_id)},
            "manufacturer": MANUFACTURER,
            "model": _device_info_str(entity.type),
            "name": _device_info_str(entity.name),
        }
        if sw_version := _software_version(entity.data.get("sw")):
            self._device_info_fields["sw_version"] = sw_version

    @property
    def device_info(self) -> DeviceInfo:
        """Return device metadata with a late-bound registered parent link."""
        if self._parent_device_stable_id:
            parent_info = _parent_device_info(
                self.coordinator,
                self._parent_device_stable_id,
            )
            if parent_info is not None:
                parent_field, parent_value = parent_info
                return DeviceInfo(
                    **self._device_info_fields, **{parent_field: parent_value}
                )
        return DeviceInfo(**self._device_info_fields)

    def _current_entity(self) -> Entity | None:
        """Return the current coordinator entity for this Home Assistant entity."""
        if not (data := self.coordinator.data):
            return None
        entities = data.get("devices" if self._station_id is not None else "stations")
        if entities is None:
            return None
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
        entity = _entity_by_id_or_serial(
            entities, getattr(self, "_lookup_dev_id", self._dev_id),
            self._entity_serial, self._physical_identity
        )
        if getattr(entity, "local_mqtt_only", False) and not self._accepts_local_only:
            return None
        # Remember only the lookup key, not the object or HA identifier. Each
        # subsequent read still verifies the current physical identity.
        if entity is not None and entities.get(entity.entity_id) is entity:
            self._lookup_dev_id = entity.entity_id
        return entity

    async def async_added_to_hass(self) -> None:
        """Subscribe to updates."""
        self._handle_coordinator_update()
        await super().async_added_to_hass()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Skip unrelated notifications, never an entity's explicit state write."""
        scope = getattr(self.coordinator, "_mqtt_child_write_scope", None)
        rssi_station = getattr(self.coordinator, "_mqtt_rssi_write_station", None)
        write_station = getattr(self.coordinator, "_mqtt_write_station", None)
        initialized = getattr(self, "_coordinator_state_initialized", False)
        resolved = True
        current = None
        track_control = False
        if (
            self._mqtt_child_state_only
            and self._physical_identity is not None
        ):
            track_control = bool(self._station_id) and not self._mqtt_parent_availability_independent
            refresh_parent_availability = (
                scope is not None and not self._mqtt_parent_availability_independent
                and scope is getattr(self.coordinator, "_mqtt_parent_availability_scope", None)
            )
            outside_child_scope = scope is not None and (
                (self._station_id and not refresh_parent_availability and self._physical_identity not in scope)
                or (self._station_id is None and rssi_station is not None)
            )
            # A refresh while a child is absent must not mark it ready for
            # filtering again. Recheck it until a write sees the child return.
            if write_station is not None or outside_child_scope or not initialized:
                current = self._current_entity()
                resolved = current is not None
                if initialized and current is not None:
                    if outside_child_scope and current is not rssi_station:
                        return
                    if write_station is not None:
                        parent = getattr(current, "station", None) if self._station_id else current
                        if parent is not None and parent is not write_station:
                            parent_identity = _serial_identity(parent)
                            if parent_identity is not None and parent_identity != _serial_identity(write_station):
                                return
                    if track_control and refresh_parent_availability and self._physical_identity not in scope:
                        dedup = getattr(self.coordinator, "_mqtt_parent_availability_dedup", None)
                        if dedup is not None and dedup[0] is scope and self._control_availability_is_published(
                            current, available=dedup[1],
                        ):
                            return
                    if scope is not None and self._mqtt_parent_availability_independent:
                        observations = getattr(self.coordinator, "_mqtt_availability_observations", None)
                        if (
                            observations is not None and observations[0] is scope
                            and self._mqtt_unreported_observation_is_current(current, observations[1])
                        ):
                            return
        timing = getattr(self.coordinator, "_mqtt_callback_timing", None)
        started = perf_counter() if timing is not None else 0.0
        try:
            super()._handle_coordinator_update()
            # A returning entity needs one write before it can be filtered again.
            self._coordinator_state_initialized = resolved
            if track_control and current is not None:
                try:
                    self._last_control_record = ref(current)
                except TypeError:
                    self._last_control_record = None
        finally:
            if timing is not None:
                elapsed = perf_counter() - started
                timing.entity_write_seconds += elapsed
                timing.entity_write_calls += 1
                if elapsed > timing.slowest_entity_write_seconds:
                    timing.slowest_entity_write_seconds = elapsed
                    timing.slowest_entity_write_class = type(self).__name__

    def _control_availability_is_published(self, current: Entity, *, available: bool) -> bool:
        """Only skip if this control's record and published availability both match."""
        if self._last_control_record is None or self._last_control_record() is not current:
            return False
        if self.hass is None or self.entity_id is None:
            return False
        published = self.hass.states.get(self.entity_id)
        return (
            published is not None
            and (published.state != STATE_UNAVAILABLE) is available
            and self.available is available
        )

    def _mqtt_unreported_observation_is_current(self, current: Entity, station_fields: Collection[str]) -> bool:
        return False

    def _mqtt_observation_state_is_published(self, expected: str) -> bool:
        if expected == STATE_UNAVAILABLE or self.hass is None or self.entity_id is None:
            return False
        published = self.hass.states.get(self.entity_id)
        return published is not None and published.state == expected and self.available

    def _current_entity_is_online(self) -> bool:
        """Return if the current X-Sense entity and parent station are online."""
        return self._entity_is_online(self._current_entity())

    def _entity_is_online(self, entity: Entity | None) -> bool:
        """Check connectivity for a freshly resolved record."""
        if entity is None or not super().available:
            return False

        if self._station_id:
            data = self.coordinator.data
            if not data or not (stations := data.get("stations")):
                return False
            lookup_id = getattr(self, "_lookup_station_id", self._station_id)
            station = _entity_by_id_or_serial(
                stations,
                lookup_id,
                self._station_serial,
                self._parent_identity,
            )
            if (
                station is not None
                and (station_id := station.entity_id) != lookup_id
                and stations.get(station_id) is station
            ):
                self._lookup_station_id = station_id
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
    if (
        entity_id is not None
        and (entity := entities.get(entity_id))
        and (identity is None or _matches_serial_identity(entity, identity))
    ):
        return entity
    if serial is None:
        return None
    match = None
    for entity in entities.values():
        if _entity_serial(entity) != serial or (
            identity is not None and not _matches_serial_identity(entity, identity)
        ):
            continue
        if match is not None:
            return None
        match = entity
    return match


def _identity_house_id(entity: Entity) -> str | None:
    house_id = getattr(getattr(entity, "house", None), "house_id", None)
    return str(house_id) if house_id is not None else None


def _matches_serial_identity(entity: Entity, identity: tuple) -> bool:
    """Check a live registry record without rebuilding its identity tuple."""
    is_child, house_id, parent_serial, model, serial = identity
    if serial is None or _entity_serial(entity) != serial or getattr(entity, "type", None) != model:
        return False
    station = getattr(entity, "station", None)
    if (station is not None) != is_child:
        return False
    if (is_child and parent_serial is None) or _entity_serial(station) != parent_serial:
        return False
    return _identity_house_id(station if station is not None else entity) == house_id


def _serial_identity(entity: Entity | None) -> tuple | None:
    """Scope serial fallback to the same model, house, and physical parent."""
    serial = _entity_serial(entity)
    if serial is None:
        return None
    station = getattr(entity, "station", None)
    parent_serial = _entity_serial(station)
    if station is not None and parent_serial is None:
        return None
    return (
        station is not None,
        _identity_house_id(station if station is not None else entity),
        parent_serial,
        getattr(entity, "type", None),
        serial,
    )


def _identity_in_discovery_scope(entity: Entity, scope: frozenset[tuple], serials: Collection[str]) -> bool:
    serial = _entity_serial(entity)
    if serial is None:
        return True
    if serial in serials:
        identity = _serial_identity(entity)
        return identity is None or identity in scope
    # Incomplete identities fall back to discovery even if the child serial differs.
    station = getattr(entity, "station", None)
    return station is not None and _entity_serial(station) is None


def _scoped_discovery_devices(devices, known_devices, scope, serials):
    return {
        key: item for key, item in devices.items()
        if known_devices.get(key) is not item
        or is_camera_entity(item)
        or _identity_in_discovery_scope(item, scope, serials)
    }


def _entity_unique_id(stable_id: str, key: str) -> str:
    return f"{stable_id}-{key}".replace("_", "-").lower()


def _local_mqtt_id_owner(coordinator, entity: Entity) -> tuple | None:
    """Find the original owner when a cloud record reuses a saved local ID."""
    local = coordinator.__dict__.get("_local_only_devices", {}).get(entity.entity_id)
    if local is None or local is entity:
        return None
    owner = _serial_identity(local)
    return owner if owner != _serial_identity(entity) else None


def _local_mqtt_collision_id(identity: tuple) -> str:
    from hashlib import sha256

    return "xsense-" + sha256(repr(identity).encode()).hexdigest()


def _stable_device_id(coordinator, entity: Entity, identity: tuple | None, *, register: bool = True):
    """Preserve observed IDs across unambiguous physical identity rollovers."""
    manager = getattr(coordinator, "_xsense_identity_store", None)
    if getattr(coordinator, "_shutting_down", False) or (manager is not None and manager.closed):
        raise IdentityStoreClosedError("Cannot assign identities while entry unloads")
    counts = coordinator.__dict__.get("_xsense_discovery_identity_counts")
    if counts is None:
        validate_current_identities(coordinator)
    if identity is None:
        return entity.entity_id
    collection = "devices" if identity[0] else "stations"
    if counts is None:
        current = (getattr(coordinator, "data", None) or {}).get(collection, {})
        matches = sum(_serial_identity(item) == identity for item in current.values())
    else:
        matches = counts.get((collection, identity), 0)
    if matches != 1:
        return entity.entity_id
    stable_ids = getattr(coordinator, "_xsense_stable_device_ids", None)
    if not register:
        return _UNREGISTERED_DEVICE_ID if stable_ids is None else stable_ids.get(identity, _UNREGISTERED_DEVICE_ID)
    if stable_ids is None:
        stable_ids = coordinator._xsense_stable_device_ids = {}
    if identity not in stable_ids:
        if _local_mqtt_id_owner(coordinator, entity) is not None:
            stable_ids[identity] = _local_mqtt_collision_id(identity)
        else:
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
