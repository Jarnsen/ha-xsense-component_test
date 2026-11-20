"""Verify the read-only model mappings from X-Sense APK build 7358."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass

from custom_components.xsense.alarm_control_panel import station_supports_alarm_panel
from custom_components.xsense.binary_sensor import SENSORS, alarm_device_class
from custom_components.xsense.python_xsense.async_xsense import (
    AsyncXSense,
    _station_state_shadow_names,
)
from custom_components.xsense.python_xsense.base import XSenseBase
from custom_components.xsense.python_xsense.entity_map import EntityType, entities
from custom_components.xsense.python_xsense.station import Station
from custom_components.xsense.sensor import SENSORS as NUMERIC_SENSORS


@pytest.mark.parametrize(
    ("model", "kind", "device_class"),
    [
        ("XS0AD-MN", EntityType.SMOKE, BinarySensorDeviceClass.SMOKE),
        ("XC0M-MR", EntityType.CO, BinarySensorDeviceClass.CO),
    ],
)
def test_new_paired_model_reads_sbs50_shadow(model, kind, device_class):
    station = Station(None, category="SBS50", stationId="hub", stationSn="1234ABCD")
    station.set_devices({"devices": [
        {"deviceType": model, "deviceId": "child", "deviceSn": "00000001"},
    ]})
    child = station.get_device_by_sn("00000001")
    assert child.entity_type is kind
    assert alarm_device_class(child) is device_class
    assert not entities[model]["actions"]

    alarm = next(sensor for sensor in SENSORS if sensor.key == "alarm_status")
    assert not alarm.exists_fn(child)
    client = object.__new__(XSenseBase)
    for status, expected in (("1", True), ("0", False)):
        state = {"status": {"alarmStatus": status, "muteStatus": "1"}}
        if kind is EntityType.CO:
            state["coPpm"] = "42"
        client.parse_get_state(station, {"devs": {"00000001": state}})
        assert alarm.exists_fn(child)
        assert alarm.value_fn(child) is expected

    if kind is EntityType.CO:
        ppm = next(sensor for sensor in NUMERIC_SENSORS if sensor.key == "co")
        assert ppm.exists_fn(child)
        assert float(ppm.value_fn(child)) == 42


def test_new_wifi_smoke_model_uses_house_shadow_and_exact_thing_name():
    station = Station(None, category="XS0AE-iA", stationId="smoke", stationSn="1234ABCD")
    assert station.entity_type is EntityType.SMOKE
    assert station.shadow_name == "XS0AE-iA-1234ABCD"
    assert _station_state_shadow_names(station) == ()
    assert not entities["XS0AE-iA"]["actions"]
    alarm = next(sensor for sensor in SENSORS if sensor.key == "alarm_status")
    station.set_data({"status": {"alarmStatus": "1"}})
    assert alarm_device_class(station) is BinarySensorDeviceClass.SMOKE
    assert alarm.exists_fn(station)
    assert alarm.value_fn(station) is True


@pytest.mark.asyncio
async def test_xcg0a_decodes_independent_indicators_from_house_shadow():
    station = Station(None, category="XCG0A-iA", stationId="gas", stationSn="1234ABCD")
    assert station.shadow_name == "XCG0A-iA-1234ABCD"
    assert _station_state_shadow_names(station) == ()
    assert not entities[station.type]["actions"]
    house = SimpleNamespace(get_station_by_sn={station.sn: station}.get)
    client = object.__new__(AsyncXSense)
    client._lastres = SimpleNamespace(status=200)
    descriptions = {sensor.key: sensor for sensor in SENSORS}
    gas, co = (descriptions[key] for key in ("gas_alarm_status", "co_alarm_status"))
    assert gas.exists_fn(station) and co.exists_fn(station)
    assert gas.value_fn(station) is co.value_fn(station) is None
    for alarm, mute, expected in (
        ("5", "8", (True, True)),
        ("2", "5", (False, True)),
        ("2", "0", (False, True)),
        ("2", "2", (False, False)),
        ("4", "8", (True, False)),
        ("4", "7", (True, False)),
        ("4", "0", (True, False)),
        ("1", "4", (False, False)),
        ("3", "6", (False, False)),
        ("0", "0", (False, False)),
    ):
        reported = {station.sn: {
            "status": {"alarmStatus": alarm, "muteStatus": mute}, "coPpm": "42",
        }}
        client.get_house = AsyncMock(side_effect=[
            {"state": {}}, {"state": {"reported": reported}},
        ])
        await client.get_house_state(house)
        client.get_house.assert_awaited_with(house, "2nd_mainpage")
        assert (gas.value_fn(station), co.value_fn(station)) == expected
    assert not descriptions["alarm_status"].exists_fn(station)
    ppm = next(sensor for sensor in NUMERIC_SENSORS if sensor.key == "co")
    assert ppm.exists_fn(station)
    assert float(ppm.value_fn(station)) == 42


@pytest.mark.asyncio
async def test_sbs0a_reads_its_own_mainpage_without_sbs50_controls():
    station = Station(None, category="SBS0A", stationId="hub", stationSn="1234ABCD")
    station.set_devices({"devices": [
        {"deviceType": "XS0AD-MN", "deviceId": "child", "deviceSn": "00000001"},
    ]})
    assert station.entity_type is EntityType.BASESTATION
    assert station.shadow_name == "SBS0A1234ABCD"
    assert not station_supports_alarm_panel(station)
    assert not entities[station.type]["actions"]
    client = object.__new__(AsyncXSense)
    client._lastres = SimpleNamespace(status=200)
    client.get_thing = AsyncMock(return_value={"state": {"reported": {
        "wifiRSSI": "-58", "devs": {"00000001": {"status": {"alarmStatus": "1"}}},
    }}})
    await client.get_station_state(station)
    await client.get_state(station)
    client.get_thing.assert_awaited_once_with(station, "2nd_mainpage")
    assert station.data["wifiRSSI"] == -58
    alarm = next(sensor for sensor in SENSORS if sensor.key == "alarm_status")
    assert alarm.value_fn(station.get_device_by_sn("00000001")) is True
