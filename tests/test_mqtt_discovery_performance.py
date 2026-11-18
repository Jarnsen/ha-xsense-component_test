"""Keep repeated MQTT discovery from reconstructing registered entities."""

from dataclasses import replace
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest
from test_mqtt_listener_fanout import station_with_children

from custom_components.xsense import (
    binary_sensor,
    button,
    event,
    number,
    select,
    sensor,
    switch,
)
from custom_components.xsense.entity import _serial_identity
from custom_components.xsense.python_xsense.async_xsense import AsyncXSense
from custom_components.xsense.python_xsense.station import Station


@pytest.mark.asyncio
@pytest.mark.parametrize("platform, descriptions", [
    (binary_sensor, ("SENSORS",)), (sensor, ("SENSORS",)),
    (button, ("BUTTONS",)), (number, ("NUMBERS",)),
    (select, ("SELECTS",)), (switch, ("SWITCHES",)),
    (event, ("AI_DETECTION_DESCRIPTION", "MOTION_DESCRIPTION", "MAILBOX_ALARM_DESCRIPTION")),
])
async def test_child_shadow_does_not_repeat_eligibility_checks_for_known_siblings(monkeypatch, platform, descriptions):
    station = station_with_children()
    callbacks, checked = [], []
    coordinator = NS(
        data={"stations": {station.entity_id: station}, "devices": dict(station.devices)},
        xsense=AsyncXSense(), last_update_success=True,
        async_add_listener=lambda cb: callbacks.append(cb) or (lambda: None),
    )

    def observed(description):
        def exists(item, *args):
            checked.append(item)
            return description.exists_fn(item, *args)
        return replace(description, exists_fn=exists)

    for name in descriptions:
        original = getattr(platform, name)
        replacement = tuple(observed(item) for item in original) if isinstance(original, tuple) else observed(original)
        monkeypatch.setattr(platform, name, replacement)
    entry = NS(entry_id="test", async_on_unload=lambda _: None)
    hass = NS(data={"xsense": {"test": coordinator}})
    await platform.async_setup_entry(hass, entry, lambda _: None)
    checked.clear()
    target, sibling = station.devices["0"], station.devices["1"]
    coordinator._mqtt_child_write_scope = frozenset({_serial_identity(target)})
    for callback in callbacks:
        callback()
    assert not any(item is sibling for item in checked)
    assert any(item is target for item in checked)
    # A full refresh must still reconsider every device and late capability.
    checked.clear()
    coordinator._mqtt_child_write_scope = None
    for callback in callbacks:
        callback()
    assert any(item is sibling for item in checked)

    # A newly discovered or replaced object must not be hidden by a different
    # child's notification scope, even when its API key was already known.
    coordinator._mqtt_child_write_scope = frozenset({_serial_identity(target)})
    replacement_station = station_with_children()
    replacement = replacement_station.devices["1"]
    coordinator.data["devices"]["1"] = replacement
    checked.clear()
    for callback in callbacks:
        callback()
    assert any(item is replacement for item in checked)
    replacement_station.set_devices({"devices": [{
        "deviceId": "new-api-key", "deviceSn": "new-physical-device",
        "deviceType": "SWS51", "deviceName": "New leak", "roomName": "Room",
    }]})
    new_device = replacement_station.devices["new-api-key"]
    coordinator.data["devices"]["new-api-key"] = new_device
    checked.clear()
    for callback in callbacks:
        callback()
    assert any(item is new_device for item in checked)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("platform", "classes"),
    [
        (binary_sensor, ("XSenseBinarySensorEntity", "XSenseMQTTConnectedEntity")),
        (button, ("XSenseButtonEntity",)),
        (number, ("XSenseNumberEntity",)),
        (select, ("XSenseSelectEntity",)),
        (sensor, ("XSenseSensorEntity",)),
        (switch, ("XSenseSwitchEntity",)),
        (event, ("XSenseMailboxAlarmEventEntity",)),
    ],
)
async def test_repeated_platform_discovery_constructs_only_new_entities(
    monkeypatch, platform, classes
):
    station = Station(
        NS(house_id="house", mqtt_server="broker"),
        stationId="station", stationSn="station", stationName="Base",
        category="SBS50", safeMode="Disarmed",
    )
    records = [
        {
            "deviceId": model, "deviceSn": model, "deviceType": model,
            "deviceName": model, "roomName": "Room",
        }
        for model in ("SWS51", "STH51", "SMS0A", "SDS0A", "SMA51")
    ]
    station.set_devices({"devices": records})
    for device in station.devices.values():
        device.set_data({
            "batInfo": 3, "rfLevel": 3, "alarmStatus": "0",
            "alarmVol": 75, "alarmTone": 1, "temperature": 20, "humidity": 50,
            "alarmEnabled": "1",
        })
    callbacks, added = [], []
    coordinator = NS(
        data={"stations": {"station": station}, "devices": dict(station.devices)},
        xsense=AsyncXSense(),
        last_update_success=True,
        async_add_listener=lambda cb: callbacks.append(cb) or (lambda: None),
    )
    hass = NS(data={"xsense": {"test": coordinator}})
    entry = NS(entry_id="test", async_on_unload=lambda _: None)
    spies = []
    for name in classes:
        spy = Mock(wraps=getattr(platform, name))
        monkeypatch.setattr(platform, name, spy)
        spies.append(spy)
    await platform.async_setup_entry(hass, entry, added.extend)
    assert added
    initial_ids = [item.unique_id for item in added]
    for spy in spies:
        spy.reset_mock()
    for _ in range(3):
        for callback in callbacks:
            callback()
    assert [item.unique_id for item in added] == initial_ids
    assert all(spy.call_count == 0 for spy in spies)
