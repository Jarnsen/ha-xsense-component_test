"""Late security-device discovery must not require an entry reload."""

import asyncio
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.xsense import alarm_control_panel as alarm


@pytest.mark.asyncio
@pytest.mark.parametrize("initially_supported", [False, True])
async def test_alarm_discovery_registers_once_and_stops_on_unload(
    monkeypatch, initially_supported
):
    station = NS(type="SBS50", sn="BASE", entity_id="base", devices={})
    if initially_supported:
        station.devices["door"] = NS(type="SDS0A")
    listeners, unloads, added, tasks = [], [], [], []

    def subscribe(listener):
        listeners.append(listener)
        return lambda: listeners.remove(listener)

    coordinator = NS(
        xsense=NS(houses={"house": NS(stations={"base": station})}),
        async_add_listener=subscribe,
    )
    platform = NS(async_register_entity_service=Mock())
    register, unregister = AsyncMock(), Mock()
    monkeypatch.setattr(alarm, "async_register_force_arm_panel", register)
    monkeypatch.setattr(alarm, "async_unregister_force_arm_panel", unregister)
    monkeypatch.setattr(
        alarm.entity_platform, "current_platform", NS(get=lambda: platform)
    )
    monkeypatch.setattr(
        alarm, "XSenseAlarmControlPanel", lambda c, s: NS(unique_id=f"{s.sn}_alarm")
    )

    def create_task(coro):
        task = asyncio.create_task(coro)
        tasks.append(task)
        return task

    hass = NS(data={"xsense": {"entry": coordinator}}, async_create_task=create_task)
    entry = NS(entry_id="entry", async_on_unload=unloads.append)
    await alarm.async_setup_entry(hass, entry, lambda entities: added.extend(entities))
    assert len(added) == int(initially_supported)
    assert listeners
    station.devices["door"] = NS(type="SDS0A")
    listener = listeners[0]
    listener()
    listener()
    await asyncio.gather(*tasks)
    assert len(added) == 1
    assert added[0].unique_id == "BASE_alarm"
    register.assert_awaited_once()
    assert platform.async_register_entity_service.call_count == 6
    second = NS(
        type="SBS50",
        sn="SECOND",
        entity_id="second",
        devices={"motion": NS(type="SMS0A")},
    )
    coordinator.xsense.houses["house"].stations["second"] = second
    listener()
    await asyncio.gather(*tasks)
    assert [item.unique_id for item in added] == ["BASE_alarm", "SECOND_alarm"]
    register.assert_awaited_once()
    for cleanup in reversed(unloads):
        cleanup()
    assert not listeners
    listener()
    await asyncio.sleep(0)
    assert len(added) == 2
    unregister.assert_called_once()


@pytest.mark.asyncio
async def test_alarm_discovery_cancels_registration_when_entry_unloads(monkeypatch):
    listeners, unloads, tasks, added = [], [], [], []
    station = NS(type="SBS50", sn="BASE", devices={})
    started = asyncio.Event()

    async def register(*args):
        started.set()
        await asyncio.Event().wait()

    def subscribe(listener):
        listeners.append(listener)
        return lambda: listeners.remove(listener)

    def create_task(coro):
        task = asyncio.create_task(coro)
        tasks.append(task)
        return task

    coordinator = NS(
        xsense=NS(houses={"house": NS(stations={"base": station})}),
        async_add_listener=subscribe,
    )
    unregister = Mock()
    monkeypatch.setattr(alarm, "async_register_force_arm_panel", register)
    monkeypatch.setattr(alarm, "async_unregister_force_arm_panel", unregister)
    monkeypatch.setattr(alarm.entity_platform, "current_platform", NS(get=lambda: None))
    monkeypatch.setattr(
        alarm, "XSenseAlarmControlPanel", lambda c, s: NS(unique_id=f"{s.sn}_alarm")
    )
    hass = NS(data={"xsense": {"entry": coordinator}}, async_create_task=create_task)
    await alarm.async_setup_entry(
        hass,
        NS(entry_id="entry", async_on_unload=unloads.append),
        lambda entities: added.extend(entities),
    )
    station.devices["door"] = NS(type="SDS0A")
    listeners[0]()
    await started.wait()
    for cleanup in reversed(unloads):
        cleanup()
    await asyncio.gather(*tasks, return_exceptions=True)
    assert all(task.cancelled() for task in tasks)
    assert not added
    assert not listeners
    unregister.assert_called_once()
