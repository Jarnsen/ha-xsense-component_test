"""Persist observed physical identities without guessing registry mappings."""

import asyncio
import logging

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


def validate_current_identities(coordinator):
    """Reject reused IDs at startup and on subsequent dynamic discovery."""
    # A reused API ID cannot safely be assigned to either registry device by
    # guessing. Refuse setup instead of silently merging physical devices.
    from .entity import _serial_identity

    identities = getattr(coordinator, "_xsense_stable_device_ids", {})
    if not identities:
        return
    owners = {stable_id: identity for identity, stable_id in identities.items()}
    for collection in ("stations", "devices"):
        for entity in (coordinator.data or {}).get(collection, {}).values():
            owner = owners.get(entity.entity_id)
            if owner is not None and owner != _serial_identity(entity):
                raise IdentityConflictError(
                    "Stored X-Sense identity conflicts with a reused device ID; "
                    "automatic registry reassignment is refused"
                )


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
