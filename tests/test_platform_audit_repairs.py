"""Behavioral regressions for the bounded September platform audit."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.xsense import (
    binary_sensor,
    button,
    number,
    select,
    sensor,
    switch,
)
from custom_components.xsense.python_xsense.async_xsense import AsyncXSense
from custom_components.xsense.python_xsense.device import Device
from custom_components.xsense.python_xsense.entity_map import EntityType, entities
from custom_components.xsense.python_xsense.station import Station


def station(identifier="old-id", serial="SERIAL", model="SC07-iA", house=None):
    item = Station(
        house, stationId=identifier, stationSn=serial, category=model, online=1
    )
    item.set_data(
        {
            "batInfo": "3",
            "alarmStatus": "0",
            "tempUnit": "1",
            "alarmVol": "75",
            "alarmEnable": "1",
        }
    )
    return item


def description(module, key):
    names = {
        sensor: "SENSORS",
        binary_sensor: "SENSORS",
        button: "BUTTONS",
        number: "NUMBERS",
        select: "SELECTS",
        switch: "SWITCHES",
    }
    return next(item for item in getattr(module, names[module]) if item.key == key)


def control(cls, module, key, device, api):
    result = object.__new__(cls)
    result.entity_description = description(module, key)
    result.coordinator = SimpleNamespace(
        xsense=api, async_update_listeners=lambda: None
    )
    result._current_entity = lambda: device
    return result


@pytest.mark.parametrize("value", ["1", 1, True])
def test_normalized_end_of_life_takes_precedence(value):
    device = station()
    device.set_data({"isLifeEnd": value, "sensorStatus": "1", "batInfo": "0"})
    assert sensor.apk_device_status(device) == "end_of_life"
    assert binary_sensor.life_end_status(device) is True


@pytest.mark.parametrize(
    "model", [m for m, info in entities.items() if info.get("type") == EntityType.COMBI]
)
@pytest.mark.parametrize("code", [0, 1, 2, 3])
def test_combo_alarm_remains_neutral_aggregate(model, code):
    device = station(model=model)
    device.set_data({"alarmStatus": str(code)})
    assert binary_sensor.alarm_status(device) is (code != 0)
    assert binary_sensor.alarm_device_class(device) is None


@pytest.mark.parametrize(
    "model,expected", [("XS01-M", "smoke"), ("XC01-M", "carbon_monoxide")]
)
def test_single_purpose_detectors_keep_device_class(model, expected):
    assert binary_sensor.alarm_device_class(station(model=model)).value == expected


@pytest.mark.asyncio
async def test_radon_temperature_unit_uses_paired_rest_update():
    device = station(model="XR0A-iR")
    device.set_data({"tempUnit": "1", "radonUnit": "2"})
    api = AsyncXSense()
    api.api_call = AsyncMock()
    api.do_thing = AsyncMock()
    entity = control(select.XSenseSelectEntity, select, "temperature_unit", device, api)
    await entity.async_select_option("2")
    api.api_call.assert_awaited_once_with(
        "104115", stationId="old-id", stationSn="SERIAL", tempUnit="2", radonUnit="2"
    )
    api.do_thing.assert_not_awaited()
    assert entity.current_option == "2"


@pytest.mark.asyncio
async def test_radon_temperature_unit_does_not_invent_missing_companion():
    device = station(model="XR0A-iR")
    api = SimpleNamespace(update_radon_unit=AsyncMock())
    entity = control(select.XSenseSelectEntity, select, "temperature_unit", device, api)
    with pytest.raises(HomeAssistantError):
        await entity.async_select_option("2")
    api.update_radon_unit.assert_not_awaited()


@pytest.mark.parametrize("model", ["STH51", "STH0A", "STH0B", "XC0M-iR"])
@pytest.mark.parametrize(
    "key,compact,expanded,canonical",
    [
        ("alarm_enabled", "g", "alarmEnable", "alarmEnabled"),
        ("continued_alarm", "h", "continueAlarm", "continuedAlarm"),
    ],
)
@pytest.mark.parametrize(
    "first,second",
    [
        ("compact", "expanded"),
        ("expanded", "compact"),
        ("canonical", "compact"),
        ("compact", "canonical"),
    ],
)
@pytest.mark.asyncio
async def test_sth_alias_order_and_write_then_report(
    model, key, compact, expanded, canonical, first, second
):
    device = Device(
        station(model="SBS50"), deviceId="D", deviceSn="CHILD", deviceType=model
    )
    keys = {"compact": compact, "expanded": expanded, "canonical": canonical}
    device.set_data({keys[first]: "1"})
    api = SimpleNamespace(update_shadow_setting=AsyncMock())
    entity = control(switch.XSenseSwitchEntity, switch, key, device, api)
    assert entity.is_on is True
    device.set_data({keys[second]: "0"})
    assert entity.is_on is False
    await entity.async_turn_on()
    assert expanded not in device.data
    device.set_data({keys[first]: "0"})
    assert entity.is_on is False
    api.update_shadow_setting.assert_awaited_once_with(device, expanded, "1")


@pytest.mark.parametrize(
    "key,field,model",
    [
        ("driveway_sensitivity", "sensitivity", "SDA51"),
        ("detection_sensitivity", "detcSens", "SWS51"),
    ],
)
@pytest.mark.asyncio
async def test_integer_sensitivity_wire_format(key, field, model):
    device = Device(
        station(model="SBS50"), deviceId="D", deviceSn="CHILD", deviceType=model
    )
    device.set_data({field: "1"})
    api = AsyncXSense()
    api.do_thing = AsyncMock()
    entity = control(number.XSenseNumberEntity, number, key, device, api)
    await entity.async_set_native_value(2.0)
    payload = api.do_thing.call_args.args[2]["state"]["desired"]
    assert payload[field] == "2"
    assert device.data[field] == 2


@pytest.mark.asyncio
async def test_fractional_calibration_is_not_rounded():
    device = Device(
        station(model="SBS50"), deviceId="D", deviceSn="CHILD", deviceType="STH51"
    )
    device.set_data({"tAdjust": 0.0})
    api = AsyncXSense()
    api.do_thing = AsyncMock()
    entity = control(
        number.XSenseNumberEntity, number, "temperature_adjustment", device, api
    )
    await entity.async_set_native_value(1.2)
    assert api.do_thing.call_args.args[2]["state"]["desired"]["tAdjust"] == "1.2"


class Coordinator:
    last_update_success = True

    def __init__(self, stations, devices=None):
        self.data = {"stations": stations, "devices": devices or {}}
        self.listeners = []
        self.xsense = SimpleNamespace(has_action=lambda entity, action: True)

    def async_add_listener(self, callback):
        self.listeners.append(callback)
        return lambda: None


@pytest.mark.parametrize(
    "module", [sensor, binary_sensor, button, number, select, switch]
)
@pytest.mark.asyncio
async def test_rollover_preserves_existing_ids_and_does_not_duplicate(module):
    original = station()
    coordinator = Coordinator({original.entity_id: original})
    entry = SimpleNamespace(entry_id="test", async_on_unload=lambda cb: None)
    hass = SimpleNamespace(data={"xsense": {"test": coordinator}})
    added = []
    await module.async_setup_entry(hass, entry, lambda items: added.extend(items))
    previous_ids = [item.unique_id for item in added]
    assert previous_ids
    replacement = station(identifier="new-id")
    coordinator.data["stations"] = {replacement.entity_id: replacement}
    for callback in coordinator.listeners:
        callback()
    assert [item.unique_id for item in added] == previous_ids
    assert all(item._current_entity() is replacement for item in added)
    assert all(
        item.device_info["identifiers"] == {("xsense", "old-id")} for item in added
    )
    if module is sensor:
        replacement.set_data({"ssid": "new-network"})
        for callback in coordinator.listeners:
            callback()
        late = next(
            item for item in added if item.entity_description.key == "wifi_ssid"
        )
        assert late.unique_id == "old-id-wifi-ssid"
        assert late.device_info["identifiers"] == {("xsense", "old-id")}


@pytest.mark.parametrize("difference", ["parent", "house", "model"])
def test_serial_fallback_does_not_cross_identity_context(difference):
    parent = station(model="SBS50", house=SimpleNamespace(house_id="house-a"))
    old = Device(parent, deviceId="old", deviceSn="CHILD", deviceType="STH51")
    old.set_data({"batInfo": "3"})
    coordinator = Coordinator({parent.entity_id: parent}, {old.entity_id: old})
    entity = sensor.XSenseSensorEntity(
        coordinator, old, description(sensor, "battery"), parent.entity_id
    )
    new_parent = station(
        model="SBS50",
        serial="OTHER" if difference == "parent" else "SERIAL",
        house=SimpleNamespace(
            house_id="house-b" if difference == "house" else "house-a"
        ),
    )
    new = Device(
        new_parent,
        deviceId="new",
        deviceSn="CHILD",
        deviceType="STH0A" if difference == "model" else "STH51",
    )
    coordinator.data["devices"] = {new.entity_id: new}
    assert entity._current_entity() is None


def test_ambiguous_serials_do_not_merge_or_pick_first():
    old = station()
    coordinator = Coordinator({old.entity_id: old})
    entity = sensor.XSenseSensorEntity(coordinator, old, description(sensor, "battery"))
    first, second = station(identifier="first"), station(identifier="second")
    coordinator.data["stations"] = {first.entity_id: first, second.entity_id: second}
    assert entity._current_entity() is None
    assert (
        sensor.XSenseSensorEntity(
            coordinator, first, description(sensor, "battery")
        ).unique_id
        == "first-battery"
    )
    assert (
        sensor.XSenseSensorEntity(
            coordinator, second, description(sensor, "battery")
        ).unique_id
        == "second-battery"
    )


def test_parent_and_child_rollover_keep_original_identifiers(monkeypatch):
    from custom_components.xsense import entity as entity_module

    monkeypatch.setitem(entity_module.DeviceInfo.__annotations__, "via_device_id", str)

    monkeypatch.delattr(
        entity_module.dr, "async_get_device_id_by_identifier", raising=False
    )
    registry = SimpleNamespace(
        async_get_device_by_identifier=lambda identifier, *, config_entry_id: SimpleNamespace(
            id="old-parent-device-id"
        ),
        async_get_or_create=lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("entity construction must not create registry devices")
        ),
    )
    monkeypatch.setattr(entity_module.dr, "async_get", lambda hass: registry)
    parent = station(model="SBS50")
    child = Device(parent, deviceId="old-child", deviceSn="CHILD", deviceType="STH51")
    coordinator = Coordinator({parent.entity_id: parent}, {child.entity_id: child})
    coordinator.hass = object()
    coordinator.entry = SimpleNamespace(entry_id="entry-id")
    original = sensor.XSenseSensorEntity(
        coordinator, child, description(sensor, "battery"), parent.entity_id
    )
    new_parent = station(identifier="new-parent", model="SBS50")
    new_child = Device(
        new_parent, deviceId="new-child", deviceSn="CHILD", deviceType="STH51"
    )
    coordinator.data = {
        "stations": {new_parent.entity_id: new_parent},
        "devices": {new_child.entity_id: new_child},
    }
    replacement = sensor.XSenseSensorEntity(
        coordinator, new_child, description(sensor, "battery"), new_parent.entity_id
    )
    assert original._current_entity() is new_child
    assert replacement.unique_id == original.unique_id == "old-child-battery"
    assert replacement.device_info["identifiers"] == {("xsense", "old-child")}
    assert replacement.device_info["via_device_id"] == "old-parent-device-id"
    assert "via_device" not in replacement.device_info



@pytest.mark.parametrize("module", [binary_sensor, button, number, select, sensor, switch])
@pytest.mark.asyncio
async def test_child_platform_setup_survives_unresolved_parent_device(monkeypatch, module):
    from custom_components.xsense import entity as entity_module

    monkeypatch.setitem(entity_module.DeviceInfo.__annotations__, "via_device_id", str)

    parent = station(model="SBS50")
    child = Device(parent, deviceId="child-id", deviceSn="CHILD", deviceType="STH51")
    child.set_data(
        {
            "batInfo": "3",
            "alarmStatus": "0",
            "tempUnit": "1",
            "alarmVol": "75",
            "alarmEnable": "1",
        }
    )
    coordinator = Coordinator({parent.entity_id: parent}, {child.entity_id: child})
    coordinator.hass = object()
    coordinator.entry = SimpleNamespace(entry_id="entry-id")

    monkeypatch.setattr(
        entity_module.dr,
        "async_get_device_id_by_identifier",
        lambda hass, identifier, *, config_entry_id: (_ for _ in ()).throw(ValueError),
        raising=False,
    )

    class Registry:
        def async_get_device_by_identifier(self, identifier, *, config_entry_id):
            return None

        def async_get_or_create(self, **kwargs):
            raise AssertionError("entity construction must not create registry devices")

    monkeypatch.setattr(entity_module.dr, "async_get", lambda hass: Registry())

    added = []
    entry = SimpleNamespace(entry_id="entry-id", async_on_unload=lambda cb: None)
    hass = SimpleNamespace(data={"xsense": {entry.entry_id: coordinator}})

    await module.async_setup_entry(hass, entry, lambda entities: added.extend(entities))

    assert added
    child_entities = [entity for entity in added if getattr(entity, "_station_id", None)]
    assert child_entities
    assert all("via_device" not in entity.device_info for entity in child_entities)


def test_child_parent_link_resolves_after_station_device_is_registered(monkeypatch):
    from custom_components.xsense import entity as entity_module

    monkeypatch.setitem(entity_module.DeviceInfo.__annotations__, "via_device_id", str)

    parent = station(model="SBS50")
    child = Device(parent, deviceId="child-id", deviceSn="CHILD", deviceType="STH51")
    coordinator = Coordinator({parent.entity_id: parent}, {child.entity_id: child})
    coordinator.hass = object()
    coordinator.entry = SimpleNamespace(entry_id="entry-id")
    registered = {"device_id": None}

    def get_device_id(hass, identifier, *, config_entry_id):
        assert identifier == ("xsense", parent.entity_id)
        assert config_entry_id == "entry-id"
        return registered["device_id"]

    monkeypatch.setattr(
        entity_module.dr,
        "async_get_device_id_by_identifier",
        get_device_id,
        raising=False,
    )

    entity = sensor.XSenseSensorEntity(
        coordinator, child, description(sensor, "battery"), parent.entity_id
    )

    assert "via_device_id" not in entity.device_info
    registered["device_id"] = "registered-parent-device-id"
    assert entity.device_info["via_device_id"] == "registered-parent-device-id"


def test_missing_serial_keeps_api_identifier():
    item = station(serial=None)
    coordinator = Coordinator({item.entity_id: item})
    entity = sensor.XSenseSensorEntity(
        coordinator, item, description(sensor, "battery")
    )
    replacement = station(identifier="new-id", serial=None)
    coordinator.data["stations"] = {replacement.entity_id: replacement}
    assert entity._current_entity() is None
    assert (
        sensor.XSenseSensorEntity(
            coordinator, replacement, description(sensor, "battery")
        ).unique_id
        == "new-id-battery"
    )


def test_production_source_never_uses_deprecated_device_registry_apis():
    forbidden = (
        "ATTR_VIA_DEVICE",
        "async_get_device(",
        "CONCENTRATION_PARTS_PER_MILLION",
    )
    for source_path in Path("custom_components/xsense").rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        for pattern in forbidden:
            assert pattern not in source, f"{pattern} found in {source_path}"

    entity_source = Path("custom_components/xsense/entity.py").read_text(
        encoding="utf-8"
    )
    assert entity_source.count('return "via_device", identifier') == 1
    assert '"via_device_id" not in getattr(DeviceInfo, "__annotations__", {})' in (
        entity_source
    )
