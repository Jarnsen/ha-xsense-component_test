"""Persist observed physical identities without guessing registry mappings."""

import asyncio
import logging
from types import MappingProxyType

from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers.storage import Store

from .const import DOMAIN

LOGGER = logging.getLogger(__name__)
STORAGE_VERSION = 1
SAVE_DELAY = 10


class IdentityConflictError(ConfigEntryError):
    """Physical identities cannot safely share a Home Assistant identifier."""


class IdentityStoreClosedError(RuntimeError):
    """An unloading entry must not discover or assign more identities."""


def _decode(data, entry_id):
    if data is None:
        return {}
    if not isinstance(data, dict) or data.get("entry_id") != entry_id:
        raise ValueError("Invalid identity store owner")
    records = data.get("identities")
    if not isinstance(records, list):
        raise TypeError("Invalid identity records")
    identities = {}
    used_ids = set()
    for record in records:
        if not isinstance(record, dict):
            raise TypeError("Invalid identity record")
        identity = record.get("identity")
        stable_id = record.get("stable_id")
        if (
            not isinstance(identity, list)
            or len(identity) != 5
            or type(identity[0]) is not bool
            or any(value is not None and not isinstance(value, str) for value in identity[1:4])
            or not isinstance(identity[4], str)
            or not identity[4]
            or not isinstance(stable_id, str)
            or not stable_id
            or (identity[0] and not identity[2])
            or (not identity[0] and identity[2] is not None)
        ):
            raise ValueError("Invalid physical identity")
        key = tuple(identity)
        if key in identities or stable_id in used_ids:
            raise ValueError("Conflicting identity records")
        identities[key] = stable_id
        used_ids.add(stable_id)
    return identities


class IdentityStore:
    """Own one entry's mapping and its delayed writes."""

    def __init__(self, hass, entry_id):
        self.entry_id = entry_id
        self.identities = {}
        self._store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.identities.{entry_id}")
        self._writable = True
        self._changed = False
        self._closed = False
        self._removed = False
        self._lock = asyncio.Lock()

    async def async_load(self):
        try:
            self.identities = _decode(await self._store.async_load(), self.entry_id)
        except Exception:
            # Leave unreadable/newer data intact; this run uses in-memory IDs.
            self._writable = False
            LOGGER.warning("Could not restore X-Sense identity storage for %s", self.entry_id, exc_info=True)

    def _snapshot(self):
        return {
            "entry_id": self.entry_id,
            "identities": [
                {"identity": list(identity), "stable_id": stable_id}
                for identity, stable_id in self.identities.items()
            ],
        }

    @property
    def closed(self):
        return self._closed

    def async_schedule_save(self):
        if self._closed or not self._writable:
            return
        self._changed = True
        # Capture on the event loop; Store may serialize on an executor thread.
        snapshot = self._snapshot()
        self._store.async_delay_save(lambda: snapshot, SAVE_DELAY)

    async def async_close(self):
        self._closed = True
        if not self._writable or not self._changed:
            return
        # async_save replaces the pending delayed write. Join it before reload
        # can create another Store for the same key, even if unload is cancelled.
        task = asyncio.create_task(self._async_flush())
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            await asyncio.shield(task)
            raise

    async def _async_flush(self):
        async with self._lock:
            if self._removed:
                return
            try:
                await self._store.async_save(self._snapshot())
            except Exception:
                LOGGER.warning("Could not save X-Sense identity storage for %s", self.entry_id, exc_info=True)

    async def async_remove(self):
        # Store.async_remove cancels timers but does not join an active write.
        # Flush first to pass through Store's write lock before unlinking.
        await self.async_close()
        self._writable = False
        async with self._lock:
            self._removed = True
            await self._store.async_remove()


async def async_load_identity_store(hass, entry, coordinator):
    """Restore IDs before entities are constructed."""
    manager = IdentityStore(hass, entry.entry_id)
    await manager.async_load()
    coordinator._xsense_identity_store = manager
    coordinator._xsense_stable_device_ids = manager.identities
    validate_current_identities(coordinator)


class MQTTDiscoveryValidation:
    """Reuse verified discovery inputs during one synchronous notification."""

    __slots__ = ("_counts", "_device_types", "_inventory", "_owners", "_selection", "_stable_ids", "devices")

    def __init__(self) -> None:
        self._counts = None
        self._device_types = None
        self._inventory = {}
        self._owners = None
        self._selection = None
        self._stable_ids = None
        self.devices = None

    def counts_for(self, coordinator, validate) -> dict[tuple, int]:
        owners = getattr(coordinator, "_xsense_stable_device_ids", None)
        if coordinator.__dict__.get("_local_only_devices"):
            # Local collision resolution also depends on records outside the
            # cloud inventory, so leave it on the ordinary validation path.
            self._counts = None
            self._selection = None
            self._stable_ids = None
            self.devices = None
            self._device_types = None
            counts: dict[tuple, int] = {}
            validate(coordinator, counts=counts)
            return counts
        scoped = getattr(coordinator, "_mqtt_child_write_scope", None) is not None
        if (
            self._counts is not None
            and (not scoped or self._device_types is not None)
            and self._owners == (owners or None)
            and self._matches_inventory(coordinator, scoped=scoped)
        ):
            return self._counts

        self._counts = None
        self._selection = None
        self._stable_ids = None
        self.devices = None
        counts = {}
        inventory: dict[str, list[tuple]] = {}
        validate(coordinator, counts=counts, snapshot=inventory)
        self._inventory = inventory
        self._owners = owners.copy() if owners else None
        devices = dict((coordinator.data or {}).get("devices", {}))
        self.devices = MappingProxyType(devices)
        self._device_types = (
            tuple(getattr(record, "entity_type", None) for record in devices.values()) if scoped else None
        )
        self._counts = counts
        return counts

    def stable_id_cache(self, counts):
        if counts is not self._counts:
            return None
        if self._stable_ids is None:
            self._stable_ids = {}
        return self._stable_ids

    def scoped_devices(self, previous, scope, serials, select):
        selection = self._selection
        if selection is not None and selection[0] is previous and selection[1] == scope:
            return selection[2]
        devices = MappingProxyType(select(self.devices, previous, scope, serials))
        self._selection = (previous, scope, devices)
        return devices

    def _matches_inventory(self, coordinator, *, scoped: bool) -> bool:
        from .entity import _matches_serial_identity

        data = coordinator.data or {}
        for collection, snapshot in self._inventory.items():
            records = data.get(collection, {})
            if len(records) != len(snapshot):
                return False
            if collection == "devices" and scoped:
                for (key, record), (previous, api_id, identity), entity_type in zip(
                    records.items(), snapshot, self._device_types, strict=True,
                ):
                    if record is not previous or record.entity_id != api_id:
                        return False
                    if self.devices.get(key) is not record or getattr(record, "entity_type", None) != entity_type:
                        return False
                    if identity is None or not _matches_serial_identity(record, identity):
                        return False
                continue
            if collection == "devices":
                # Broad discovery also consumes the keys and iteration order.
                for key, saved_key, (previous, api_id, identity) in zip(
                    records, self.devices, snapshot, strict=True,
                ):
                    if key != saved_key:
                        return False
                    record = records[key]
                    if record is not previous or record.entity_id != api_id:
                        return False
                    if identity is None or not _matches_serial_identity(record, identity):
                        return False
                continue
            for record, (previous, api_id, identity) in zip(records.values(), snapshot, strict=True):
                if record is not previous or record.entity_id != api_id:
                    return False
                if identity is None or not _matches_serial_identity(record, identity):
                    return False
        return True


def validate_current_identities(
    coordinator, *, counts: dict[tuple, int] | None = None,
    snapshot: dict[str, list[tuple]] | None = None,
):
    """Reject reused IDs, optionally indexing identities for discovery."""
    # A reused API ID cannot safely be assigned to either registry device by
    # guessing. Refuse setup instead of silently merging physical devices.
    from .entity import _local_mqtt_collision_id, _local_mqtt_id_owner, _serial_identity

    identities = getattr(coordinator, "_xsense_stable_device_ids", {})
    if not identities and counts is None:
        return
    owners = {stable_id: identity for identity, stable_id in identities.items()}
    for collection in ("stations", "devices"):
        captured = None if snapshot is None else snapshot.setdefault(collection, [])
        for entity in (coordinator.data or {}).get(collection, {}).values():
            owner = owners.get(entity.entity_id)
            if owner is None and counts is None:
                continue
            identity = _serial_identity(entity)
            if captured is not None:
                captured.append((entity, entity.entity_id, identity))
            if owner is not None and owner != identity:
                resolved = identity is not None and identities.get(identity) == _local_mqtt_collision_id(identity)
                if not resolved and owner != _local_mqtt_id_owner(coordinator, entity):
                    raise IdentityConflictError(
                        "Stored X-Sense identity conflicts with a reused device ID; "
                        "automatic registry reassignment is refused"
                    )
            if counts is not None:
                key = (collection, identity)
                counts[key] = counts.get(key, 0) + 1


async def async_close_identity_store(coordinator):
    """Flush an entry's IDs on successful unload or setup rollback."""
    manager = getattr(coordinator, "_xsense_identity_store", None)
    if manager is not None:
        await manager.async_close()


async def async_remove_identity_store(hass, entry, coordinator=None):
    """Delete entry storage after unload has joined its delayed writes."""
    manager = getattr(coordinator, "_xsense_identity_store", None)
    if manager is not None:
        await manager.async_remove()
    else:
        await Store(hass, STORAGE_VERSION, f"{DOMAIN}.identities.{entry.entry_id}").async_remove()
