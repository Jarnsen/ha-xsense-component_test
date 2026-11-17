"""Keep repeated MQTT discovery from reconstructing registered entities."""

from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest

from custom_components.xsense import (
    binary_sensor,
    button,
    event,
    number,
    select,
    sensor,
    switch,
)
from custom_components.xsense.python_xsense.async_xsense import AsyncXSense
from custom_components.xsense.python_xsense.station import Station


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
