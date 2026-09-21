"""Focused persistence and lifecycle tests for observed device identities."""

import asyncio
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

import pytest

from custom_components.xsense import identity_store as storage
from custom_components.xsense.entity import _serial_identity, _stable_device_id
from custom_components.xsense.entity import _entity_by_id_or_serial, setup_dynamic_entities


def device(identifier="old", *, serial="SERIAL", model="MODEL", house="house", parent=None):
    return NS(entity_id=identifier, sn=serial, type=model, house=NS(house_id=house), station=parent)


def coordinator(entity):
    return NS(data={"devices" if entity.station else "stations": {entity.entity_id: entity}})


def resolve(current, entity):
    return _stable_device_id(current, entity, _serial_identity(entity))


@pytest.fixture
def stores(monkeypatch):
    instances = []
    disk = {}

    class FakeStore:
        def __init__(self, hass, version, key):
            self.version, self.key = version, key
            self.pending = None
            self.async_load = AsyncMock(side_effect=lambda: deepcopy(disk.get(key)))
            self.async_save = AsyncMock(side_effect=self.save)
            self.async_remove = AsyncMock(side_effect=self.remove)
            instances.append(self)

        def async_delay_save(self, callback, delay):
            self.pending = callback

        async def save(self, data):
            self.pending = None
            disk[self.key] = deepcopy(data)

        async def remove(self):
            self.pending = None
            disk.pop(self.key, None)

    monkeypatch.setattr(storage, "Store", FakeStore)
    return NS(instances=instances, disk=disk)


async def load(current, entry="a"):
    await storage.async_load_identity_store(None, NS(entry_id=entry), current)


@pytest.mark.asyncio
async def test_reload_restores_original_id_and_flushes_delayed_save(stores):
    original = device()
    current = coordinator(original)
    await load(current)
    assert resolve(current, original) == "old"
    store = stores.instances[-1]
    assert store.version == 1
    assert store.key == "xsense.identities.a"
    assert store.pending is not None
    assert not stores.disk
    replacement = device("new")
    current.data = coordinator(replacement).data
    assert resolve(current, replacement) == "old"
    await storage.async_close_identity_store(current)
    assert store.pending is None
    restarted = coordinator(replacement)
    await load(restarted)
    assert resolve(restarted, replacement) == "old"
    stores.instances[-1].async_save.assert_not_awaited()
    await storage.async_close_identity_store(restarted)
    stores.instances[-1].async_save.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("difference", ["entry", "house", "model", "parent"])
async def test_persisted_identity_isolation(stores, difference):
    parent = device("parent", serial="PARENT")
    child = device(parent=parent)
    current = coordinator(child)
    await load(current)
    assert resolve(current, child) == "old"
    await storage.async_close_identity_store(current)
    new_parent = device("parent-new", serial="OTHER" if difference == "parent" else "PARENT",
                        house="other" if difference == "house" else "house")
    replacement = device("new", parent=new_parent, model="OTHER" if difference == "model" else "MODEL")
    restarted = coordinator(replacement)
    await load(restarted, "b" if difference == "entry" else "a")
    assert resolve(restarted, replacement) == "new"
    await storage.async_close_identity_store(restarted)


@pytest.mark.asyncio
async def test_parent_and_child_ids_survive_new_coordinator(stores):
    parent = device("parent", serial="PARENT")
    child = device("child", parent=parent)
    current = NS(data={"stations": {parent.entity_id: parent}, "devices": {child.entity_id: child}})
    await load(current)
    assert resolve(current, parent) == "parent"
    assert resolve(current, child) == "child"
    await storage.async_close_identity_store(current)
    parent2 = device("parent-new", serial="PARENT")
    child2 = device("child-new", parent=parent2)
    restarted = NS(data={"stations": {parent2.entity_id: parent2}, "devices": {child2.entity_id: child2}})
    await load(restarted)
    assert resolve(restarted, parent2) == "parent"
    assert resolve(restarted, child2) == "child"


@pytest.mark.asyncio
async def test_persisted_identity_never_overrides_current_ambiguity(stores):
    original = device()
    current = coordinator(original)
    await load(current)
    resolve(current, original)
    await storage.async_close_identity_store(current)
    first, second = device("first"), device("second")
    restarted = NS(data={"stations": {"first": first, "second": second}})
    await load(restarted)
    assert resolve(restarted, first) == "first"
    assert resolve(restarted, second) == "second"
    assert restarted._xsense_identity_store.identities == {_serial_identity(original): "old"}
    assert stores.instances[-1].pending is None


GOOD = {"entry_id": "a", "identities": [{"identity": [False, "house", None, "MODEL", "SERIAL"], "stable_id": "old"}]}


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [
    [], "bad", {}, {"entry_id": "b", "identities": []},
    {"entry_id": "a", "identities": {}},
    {"entry_id": "a", "identities": [None]},
    {"entry_id": "a", "identities": [{"identity": [False], "stable_id": "old"}]},
    {"entry_id": "a", "identities": [{"identity": [0, "house", None, "MODEL", "SERIAL"], "stable_id": "old"}]},
    {"entry_id": "a", "identities": [{"identity": [True, "house", None, "MODEL", "SERIAL"], "stable_id": "old"}]},
    {"entry_id": "a", "identities": [{"identity": [False, "house", None, "MODEL", "SERIAL"], "stable_id": []}]},
    {"entry_id": "a", "identities": GOOD["identities"] * 2},
])
async def test_bad_payload_disables_writes_without_breaking_setup(stores, bad):
    stores.disk["xsense.identities.a"] = deepcopy(bad)
    current = coordinator(device())
    await load(current)
    assert resolve(current, device()) == "old"
    await storage.async_close_identity_store(current)
    assert stores.disk["xsense.identities.a"] == bad
    stores.instances[-1].async_save.assert_not_awaited()
    assert stores.instances[-1].pending is None


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [OSError("read failed"), ValueError("future version")])
async def test_load_failure_preserves_storage_and_disables_writes(stores, error):
    manager = storage.IdentityStore(None, "a")
    manager._store.async_load.side_effect = error
    await manager.async_load()
    manager.identities[(False, "house", None, "MODEL", "SERIAL")] = "old"
    manager.async_schedule_save()
    await manager.async_close()
    manager._store.async_save.assert_not_awaited()
    assert manager._store.pending is None


@pytest.mark.asyncio
async def test_cancelled_close_joins_flush_and_rejects_late_scheduling(stores):
    current = coordinator(device())
    await load(current)
    resolve(current, device())
    store = stores.instances[-1]
    entered, release = asyncio.Event(), asyncio.Event()

    async def save(data):
        entered.set()
        await release.wait()
        await store.save(data)

    store.async_save.side_effect = save
    task = asyncio.create_task(storage.async_close_identity_store(current))
    await entered.wait()
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    current._xsense_identity_store.async_schedule_save()
    assert store.pending is None
    assert stores.disk[store.key] == GOOD


@pytest.mark.asyncio
async def test_real_ha_store_flush_removes_delay_and_restores(tmp_path):
    from homeassistant.core import HomeAssistant

    hass = HomeAssistant(str(tmp_path))
    current = coordinator(device())
    try:
        await storage.async_load_identity_store(hass, NS(entry_id="real"), current)
        resolve(current, device())
        store = current._xsense_identity_store._store
        assert store._delay_handle is not None
        await storage.async_close_identity_store(current)
        assert store._delay_handle is None
        assert store._unsub_final_write_listener is None
        restarted = coordinator(device("new"))
        await storage.async_load_identity_store(hass, NS(entry_id="real"), restarted)
        assert resolve(restarted, device("new")) == "old"
        await storage.async_close_identity_store(restarted)
        await storage.async_remove_identity_store(hass, NS(entry_id="real"))
        assert not Path(store.path).exists()
    finally:
        await hass.async_stop()


@pytest.mark.asyncio
async def test_reused_api_id_refuses_setup_without_registry_guessing(stores):
    from homeassistant.exceptions import ConfigEntryError

    stores.disk["xsense.identities.a"] = deepcopy(GOOD)
    original = device("new")
    reused = device("old", serial="OTHER")
    current = NS(data={"stations": {"new": original, "old": reused}})
    with pytest.raises(ConfigEntryError, match="reused device ID"):
        await load(current)
    await storage.async_close_identity_store(current)
    assert stores.disk["xsense.identities.a"] == GOOD
    assert stores.instances[-1].pending is None


@pytest.mark.asyncio
async def test_integer_house_ids_normalize_and_survive_reload(stores):
    old = device(house=123)
    current = coordinator(old)
    await load(current)
    assert resolve(current, old) == "old"
    await storage.async_close_identity_store(current)
    replacement = device("new", house="123")
    restarted = coordinator(replacement)
    await load(restarted)
    assert resolve(restarted, replacement) == "old"


@pytest.mark.asyncio
async def test_removal_cancels_pending_save_and_cannot_resurrect(stores):
    current = coordinator(device())
    await load(current)
    resolve(current, device())
    store = stores.instances[-1]
    assert store.pending is not None
    await storage.async_remove_identity_store(None, NS(entry_id="a"), current)
    current._xsense_identity_store.async_schedule_save()
    await storage.async_close_identity_store(current)
    assert store.pending is None
    assert store.key not in stores.disk
    store.async_save.assert_awaited_once()


@pytest.mark.asyncio
async def test_removal_joins_inflight_flush(stores):
    current = coordinator(device())
    await load(current)
    resolve(current, device())
    store = stores.instances[-1]
    entered, release = asyncio.Event(), asyncio.Event()

    async def save(data):
        entered.set()
        await release.wait()
        await store.save(data)

    store.async_save.side_effect = save
    closing = asyncio.create_task(storage.async_close_identity_store(current))
    await entered.wait()
    removing = asyncio.create_task(storage.async_remove_identity_store(None, NS(entry_id="a"), current))
    await asyncio.sleep(0)
    assert not removing.done()
    release.set()
    await asyncio.gather(closing, removing)
    assert store.key not in stores.disk


@pytest.mark.asyncio
async def test_save_failure_does_not_break_close(stores):
    current = coordinator(device())
    await load(current)
    resolve(current, device())
    stores.instances[-1].async_save.side_effect = OSError("disk unavailable")
    await storage.async_close_identity_store(current)


@pytest.mark.asyncio
async def test_real_store_removal_joins_running_delayed_write(tmp_path, monkeypatch):
    from homeassistant.core import HomeAssistant

    hass = HomeAssistant(str(tmp_path))
    current = coordinator(device())
    entered, release = asyncio.Event(), asyncio.Event()
    try:
        await storage.async_load_identity_store(hass, NS(entry_id="real"), current)
        resolve(current, device())
        store = current._xsense_identity_store._store
        original_write = store._async_write_data

        async def write(*args):
            entered.set()
            await release.wait()
            await original_write(*args)

        monkeypatch.setattr(store, "_async_write_data", write)
        writing = asyncio.create_task(store._async_callback_delayed_write())
        await entered.wait()
        removing = asyncio.create_task(storage.async_remove_identity_store(hass, NS(entry_id="real"), current))
        await asyncio.sleep(0)
        assert not removing.done()
        release.set()
        await asyncio.gather(writing, removing)
        assert not Path(store.path).exists()
        assert store._delay_handle is None
        assert store._unsub_final_write_listener is None
        current._xsense_identity_store.async_schedule_save()
        assert store._delay_handle is None
    finally:
        release.set()
        await hass.async_stop()


@pytest.mark.asyncio
async def test_dynamic_reused_id_blocks_lookup_and_assignment_without_corrupting_store(stores):
    stores.disk["xsense.identities.a"] = deepcopy(GOOD)
    original = device("new")
    current = coordinator(original)
    await load(current)
    assert resolve(current, original) == "old"
    other = device("old", serial="OTHER")
    current.data["stations"]["old"] = other
    for item in (original, other):
        with pytest.raises(storage.IdentityConflictError):
            resolve(current, item)
    assert storage._decode(current._xsense_identity_store._snapshot(), "a") == {
        _serial_identity(original): "old"
    }
    assert stores.instances[-1].pending is None
    await storage.async_close_identity_store(current)
    assert stores.disk["xsense.identities.a"] == GOOD


def test_exact_id_reuse_does_not_redirect_existing_wrapper():
    original = device("old")
    replacement = device("new")
    other = device("old", serial="OTHER")
    entities = {"new": replacement, "old": other}
    assert _entity_by_id_or_serial(entities, "old", "SERIAL", _serial_identity(original)) is replacement
    assert _entity_by_id_or_serial({"old": other}, "old", "SERIAL", _serial_identity(original)) is None


@pytest.mark.asyncio
async def test_dynamic_discovery_collision_adds_nothing_then_recovers(stores):
    original = device("new")
    stores.disk["xsense.identities.a"] = deepcopy(GOOD)
    current = coordinator(original)
    await load(current)
    listeners = []
    current.async_add_listener = lambda cb: listeners.append(cb)
    added = []

    def factory():
        return [NS(unique_id=resolve(current, item)) for item in current.data["stations"].values()]

    setup_dynamic_entities(NS(async_on_unload=lambda _: None), current, added.extend, factory)
    assert [item.unique_id for item in added] == ["old"]
    current.data["stations"]["old"] = device("old", serial="OTHER")
    listeners[0]()
    assert [item.unique_id for item in added] == ["old"]
    current.data["stations"].pop("old")
    current.data["stations"]["other"] = device("other", serial="OTHER")
    listeners[0]()
    assert [item.unique_id for item in added] == ["old", "other"]
    await storage.async_close_identity_store(current)


@pytest.mark.asyncio
async def test_discovery_during_flush_cannot_assign_unpersisted_identity(stores):
    current = coordinator(device())
    await load(current)
    listeners, added = [], []
    current.async_add_listener = lambda cb: listeners.append(cb)
    def factory():
        return [NS(unique_id=resolve(current, item)) for item in current.data["stations"].values()]
    setup_dynamic_entities(NS(async_on_unload=lambda _: None), current, added.extend, factory)
    store = stores.instances[-1]
    entered, release = asyncio.Event(), asyncio.Event()
    async def save(data):
        entered.set()
        await release.wait()
        await store.save(data)
    store.async_save.side_effect = save
    closing = asyncio.create_task(storage.async_close_identity_store(current))
    await entered.wait()
    other = device("other", serial="OTHER")
    current.data["stations"]["other"] = other
    listeners[0]()
    with pytest.raises(storage.IdentityStoreClosedError):
        resolve(current, other)
    release.set()
    await closing
    assert [item.unique_id for item in added] == ["old"]
    assert storage._decode(stores.disk[store.key], "a") == current._xsense_identity_store.identities


@pytest.mark.asyncio
async def test_shutdown_blocks_discovery_before_store_closes(stores):
    current = coordinator(device())
    await load(current)
    resolve(current, device())
    current._shutting_down = True
    with pytest.raises(storage.IdentityStoreClosedError):
        resolve(current, device("other", serial="OTHER"))
    assert len(current._xsense_identity_store.identities) == 1
    await storage.async_close_identity_store(current)
