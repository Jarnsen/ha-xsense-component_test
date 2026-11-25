"""Keep repeated MQTT discovery from reconstructing registered entities."""

from copy import copy
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
from custom_components.xsense import entity as entity_module
from custom_components.xsense.entity import (
    _serial_identity,
    device_station_id,
    setup_dynamic_entities,
)
from custom_components.xsense.python_xsense.async_xsense import AsyncXSense
from custom_components.xsense.python_xsense.entity_map import EntityType
from custom_components.xsense.python_xsense.station import Station


def test_range_endpoints_avoid_repeat_parent_lookup_but_see_live_connectivity():
    class CountedStations(dict):
        lookups = 0

        def get(self, key, default=None):
            self.lookups += 1
            return super().get(key, default)

    station = station_with_children("STH51")
    child = station.devices["0"]
    station._set_online(True)
    child._set_online(True)
    child.set_data({"tRange": [15, 25]})
    stations = CountedStations({station.entity_id: station})
    coordinator = NS(
        data={"stations": stations, "devices": {child.entity_id: child}},
        last_update_success=True,
    )
    minimum, maximum = [
        number.XSenseNumberEntity(coordinator, child, item, station_id=device_station_id(child))
        for item in number.NUMBERS if item.shadow_array_key == "tRange"
    ]
    assert minimum.available
    assert stations.lookups == 1
    station._set_online(False)
    assert not maximum.available
    assert stations.lookups == 2

    station._set_online(True)
    replacement = copy(station)
    replacement._data = station.data.copy()
    replacement._set_online(False)
    stations[station.entity_id] = replacement
    assert not minimum.available
    assert not maximum.available
    replacement._set_online(True)
    original_id = replacement.entity_id
    replacement.entity_id = "new-station-id"
    stations[replacement.entity_id] = stations.pop(original_id)
    assert minimum.available
    assert minimum._lookup_station_id == replacement.entity_id
    stations.lookups = 0
    assert minimum.available
    assert stations.lookups == 1

    unrelated = copy(replacement)
    unrelated.sn = "WRONG-PARENT"
    stations[replacement.entity_id] = unrelated
    assert not minimum.available
    assert not maximum.available


def test_sbs50_shadow_name_reuses_only_current_station_serial():
    station = station_with_children("STH51")
    child = station.devices["0"]
    initial = station.shadow_name
    assert initial == f"SBS50{station.sn}"
    assert station.shadow_name is initial
    assert number._has_shadow_write_route(child)

    station.sn = "NEW-STATION-SERIAL"
    changed = station.shadow_name
    assert changed == "SBS50NEW-STATION-SERIAL"
    assert station.shadow_name is changed
    station.station = NS(sn="NEW-PARENT-SERIAL")
    assert station.shadow_name is changed
    station.station.sn = None
    assert station.shadow_name == changed

    station.sn = None
    assert not number._has_shadow_write_route(child)
    assert station.shadow_name == "SBS50None"
    station.sn = "RESTORED"
    assert number._has_shadow_write_route(child)
    station.type = "SBS10"
    assert station.shadow_name == "RESTORED"
    station.type = "SBS50"
    assert station.shadow_name == "SBS50RESTORED"


def test_sbs50_shadow_name_does_not_cache_dynamic_serial_formatting():
    class DynamicSerial(str):
        value = "FIRST"

        def __format__(self, spec):
            return format(self.value, spec)

    station = station_with_children()
    station.sn = DynamicSerial("serial")
    assert station.shadow_name == "SBS50FIRST"
    station.sn.value = "SECOND"
    assert station.shadow_name == "SBS50SECOND"


def test_range_availability_resolves_once_but_rechecks_live_device_and_route(monkeypatch):
    station = station_with_children("STH51")
    child = station.devices["0"]
    station._set_online(True)
    child._set_online(True)
    child.set_data({"tRange": [15, 25]})
    coordinator = NS(
        data={"stations": {station.entity_id: station}, "devices": {child.entity_id: child}},
        last_update_success=True,
    )
    description = next(item for item in number.NUMBERS if item.key == "temperature_min")
    entity = number.XSenseNumberEntity(coordinator, child, description, station_id=device_station_id(child))
    lookup = Mock(wraps=entity._current_entity)
    monkeypatch.setattr(entity, "_current_entity", lookup)
    assert entity.available
    lookup.assert_called_once_with()

    replacement = copy(child)
    replacement.entity_id = "new-child-id"
    replacement._data = {}
    coordinator.data["devices"] = {replacement.entity_id: replacement}
    assert not entity.available
    replacement.set_data({"tRange": [16, 24]})
    assert entity.available
    assert entity.native_value == 16.0

    # A current child may still point to the old station record. Use the
    # coordinator's current parent for connectivity and the child's write route.
    parent_replacement = copy(station)
    parent_replacement._data = station.data.copy()
    parent_replacement.entity_id = "new-parent-id"
    parent_replacement._set_online(False)
    coordinator.data["stations"] = {parent_replacement.entity_id: parent_replacement}
    assert not entity.available
    parent_replacement._set_online(True)
    assert entity.available
    del coordinator.data["stations"]
    assert not entity.available
    coordinator.data["stations"] = {parent_replacement.entity_id: parent_replacement}
    shadow = station.shadow_name
    monkeypatch.setattr(type(station), "shadow_name", property(lambda self: None if self is station else shadow))
    assert not entity.available
    coordinator.data["devices"].clear()
    assert not entity.available


def test_range_state_reads_reuse_normalized_endpoints_without_building_a_pair(monkeypatch):
    child = station_with_children().devices["0"]
    child.set_data({"tRange": ["0", 25]})
    pair = child.data["tRange"]
    assert all(type(value) is float for value in pair)
    endpoints = [item for item in number.NUMBERS if item.shadow_array_key == "tRange"]
    build = Mock(wraps=number._number_pair)
    monkeypatch.setattr(number, "_number_pair", build)
    parse = Mock(wraps=number.safe_float)
    monkeypatch.setattr(number, "safe_float", parse)
    for description, expected in zip(endpoints, (0.0, 25.0), strict=True):
        entity = NS(_current_entity=lambda: child, entity_description=description)
        assert description.exists_fn(child)
        assert number.XSenseNumberEntity.native_value.__get__(entity) == expected
    build.assert_not_called()
    parse.assert_not_called()

    pair[0] = 12.0
    assert number._shadow_array_value(child, endpoints[0]) == 12.0
    build.assert_not_called()
    assert number._updated_shadow_array_values(child, endpoints[0], 14) == [14.0, 25.0]
    assert pair == [12.0, 25.0]
    build.assert_called_once_with(pair)


@pytest.mark.parametrize("array,extra,index,expected", [
    ([0.0, float("inf")], {}, 0, None),
    ([float("nan"), 25.0], {}, 1, None),
    (["0", 25], {}, 0, 0.0),
    ([float("inf"), 25.0], {"tempRangeMin": 2, "tempRangeMax": 24}, 0, 2.0),
])
def test_range_state_keeps_validation_and_split_fallback(array, extra, index, expected):
    child = station_with_children().devices["0"]
    child.data.update({"tRange": array, **extra})
    description = next(
        item for item in number.NUMBERS if item.shadow_array_key == "tRange" and item.shadow_array_index == index
    )
    assert number._shadow_array_value(child, description) == expected


@pytest.mark.parametrize("array_key,array_fields", [
    ("tRange", {"tempRangeMin": 0, "tempRangeMax": 25}),
    ("hRange", {"hRange": ["20", 60]}),
    ("tComfort", {"comfortType": "1"}),
    ("hComfort", {"hComfort": ["20", 60]}),
])
async def test_broad_number_discovery_checks_each_range_once_per_record_and_scan(
    monkeypatch, array_key, array_fields,
):
    station = station_with_children()
    child, sibling = station.devices.values()
    descriptions = tuple(item for item in number.NUMBERS if item.shadow_array_key == array_key)
    monkeypatch.setattr(number, "NUMBERS", descriptions)
    check = Mock(wraps=number._has_shadow_range_number)
    monkeypatch.setattr(number, "_has_shadow_range_number", check)
    callbacks, added = [], []
    coordinator = NS(
        data={"stations": {station.entity_id: station}, "devices": dict(station.devices)},
        xsense=AsyncXSense(), last_update_success=True,
        async_add_listener=lambda cb: callbacks.append(cb) or (lambda: None),
    )
    entry = NS(entry_id="test", async_on_unload=lambda _: None)
    hass = NS(data={"xsense": {"test": coordinator}})
    original_shadow = station.shadow_name
    shadow_name = None
    monkeypatch.setattr(type(station), "shadow_name", property(lambda _: shadow_name))

    await number.async_setup_entry(hass, entry, added.extend)
    assert [call.args[0] for call in check.call_args_list] == [station, child, sibling]
    assert not added

    child.data.update(array_fields)
    callbacks[0]()
    assert not added

    shadow_name = original_shadow
    check.reset_mock()
    callbacks[0]()
    assert [call.args[0] for call in check.call_args_list] == [station, child, sibling]
    assert [entity.entity_description.key for entity in added] == [item.key for item in descriptions]

    sibling.data[array_key] = ["bad", 60]
    callbacks[0]()
    assert len(added) == 2
    sibling.data[array_key][0] = "20"
    callbacks[0]()
    assert [entity._dev_id for entity in added] == [child.entity_id] * 2 + [sibling.entity_id] * 2


def test_range_eligibility_does_not_build_numeric_values(monkeypatch):
    station = station_with_children()
    child = station.devices["0"]
    values = Mock(side_effect=AssertionError("range eligibility constructed values"))
    monkeypatch.setattr(number, "_number_pair", values)
    child.data["tRange"] = ["0", 25]
    assert number._has_shadow_range_number(child, "tRange")
    for invalid in (None, [25], ["bad", 25], [0, float("inf")], "0,25"):
        child.data["tRange"] = invalid
        assert not number._has_shadow_range_number(child, "tRange")
    values.assert_not_called()


@pytest.mark.parametrize("platform,table,key,fields,category", [
    (number, "NUMBERS", "temperature_min", {"tRange": [15, 25]}, None),
    (number, "NUMBERS", "temperature_min", {"tempRangeMin": 0, "tempRangeMax": 25}, None),
    (number, "NUMBERS", "temperature_comfort_min", {"comfortType": "1"}, None),
    (switch, "SWITCHES", "led_light", {"ledLight": False}, None),
    (switch, "SWITCHES", "alarm_enabled", {"alarmEnabled": False}, None),
    (switch, "SWITCHES", "continued_alarm", {"continuedAlarm": False}, None),
    (switch, "SWITCHES", "mail_notice", {"mailNotice": False}, EntityType.MAILBOX),
])
async def test_broad_discovery_checks_shadow_route_only_after_fields_arrive(
    monkeypatch, platform, table, key, fields, category,
):
    station = station_with_children()
    child = station.devices["0"]
    if category is not None:
        child.entity_type = category
    description = next(item for item in getattr(platform, table) if item.key == key)
    monkeypatch.setattr(platform, table, (description,))
    route = Mock(wraps=platform._has_shadow_write_route)
    monkeypatch.setattr(platform, "_has_shadow_write_route", route)
    callbacks, added = [], []
    coordinator = NS(
        data={"stations": {station.entity_id: station}, "devices": {child.entity_id: child}},
        xsense=AsyncXSense(), last_update_success=True,
        async_add_listener=lambda cb: callbacks.append(cb) or (lambda: None),
    )
    entry = NS(entry_id="test", async_on_unload=lambda _: None)
    hass = NS(data={"xsense": {"test": coordinator}})
    original_shadow = station.shadow_name
    shadow_name = None
    monkeypatch.setattr(type(station), "shadow_name", property(lambda _: shadow_name))
    await platform.async_setup_entry(hass, entry, added.extend)
    callbacks[0]()
    route.assert_not_called()
    assert not added

    child.data.update(fields)
    callbacks[0]()
    route.assert_called_once_with(child)
    assert not added

    shadow_name = original_shadow
    callbacks[0]()
    assert [entity.entity_description.key for entity in added] == [key]


def test_shadow_select_keeps_sbs50_defaults_and_live_route():
    default = select.has_shadow_select("alarmTone")
    ordinary = select.has_shadow_select("chirpTone")
    device = NS(type="SBS50", data={}, sn="serial", shadow_name=None)
    assert not default(device)
    device.shadow_name = "shadow"
    assert default(device)
    assert not ordinary(device)
    device.data["chirpTone"] = 1
    assert ordinary(device)
    device.type = "SWS51"
    assert not default(device)
    assert ordinary(device)


@pytest.mark.parametrize("platform,table,camera_key,camera_fields,cloud_key,cloud_field", [
    (number, "NUMBERS", "camera_night_threshold", {"nightThresholdLevel": 2}, "warning_period", "warnPeriod"),
    (
        select, "SELECTS", "camera_motion_sensitivity", {"motionSensitivity": 2},
        "chirp_tone", "chirpTone",
    ),
    (switch, "SWITCHES", "camera_motion_detection", {"needMotion": 1}, "warning_enabled", "warnIsOpen"),
])
async def test_broad_discovery_skips_camera_predicates_but_sees_late_fields(
    monkeypatch, platform, table, camera_key, camera_fields, cloud_key, cloud_field,
):
    station = station_with_children()
    child, camera = station.devices["0"], station.devices["1"]
    camera.entity_type = EntityType.CAMERA
    checked, callbacks, added = [], [], []
    entries = getattr(platform, table)

    def observe(description):
        def exists(item):
            checked.append(item)
            return description.exists_fn(item)
        return replace(description, exists_fn=exists)

    monkeypatch.setattr(platform, table, tuple(
        observe(item) if item.key == camera_key else item for item in entries
    ))
    coordinator = NS(
        data={"stations": {station.entity_id: station}, "devices": dict(station.devices)},
        xsense=AsyncXSense(), last_update_success=True,
        async_add_listener=lambda cb: callbacks.append(cb) or (lambda: None),
    )
    entry = NS(entry_id="test", async_on_unload=lambda _: None)
    hass = NS(data={"xsense": {"test": coordinator}})
    camera.data["isAdmin"] = False
    # Even a matching field name cannot make an ordinary shadow an ADDX camera.
    child.data.update({"isAdmin": True, **camera_fields})
    await platform.async_setup_entry(hass, entry, added.extend)
    for _ in range(3):
        callbacks[0]()
    assert checked == [camera] * 4
    assert camera_key not in {entity.entity_description.key for entity in added}
    assert cloud_key not in {entity.entity_description.key for entity in added}

    camera.data["isAdmin"] = True
    callbacks[0]()
    assert camera_key not in {entity.entity_description.key for entity in added}

    camera.data.update(camera_fields)
    child.data[cloud_field] = 1
    callbacks[0]()
    assert {camera_key, cloud_key} <= {entity.entity_description.key for entity in added}

    # A camera classification can arrive later on an existing live record.
    child.entity_type = EntityType.CAMERA
    callbacks[0]()
    assert sum(entity.entity_description.key == camera_key for entity in added) == 2


@pytest.mark.parametrize("platform,descriptions,factory,key,field,model,category", [
    (number, "NUMBERS", "has_shadow_number", "warning_period", "warnPeriod", "SBS50", None),
    (number, "NUMBERS", "has_shadow_number", "trigger_brightness", "triggerBrightness", "LIGHT", EntityType.LIGHT),
    (select, "SELECTS", "has_shadow_select", "light_scene", "lightScene", "LIGHT", EntityType.LIGHT),
    (switch, "SWITCHES", "has_shadow_data", "warning_enabled", "warnIsOpen", "SBS50", None),
])
def test_shadow_capability_reuses_predicate_but_sees_late_fields(
    monkeypatch, platform, descriptions, factory, key, field, model, category,
):
    def unexpected_factory(*args, **kwargs):
        pytest.fail("discovery rebuilt a static shadow capability predicate")

    monkeypatch.setattr(platform, factory, unexpected_factory)
    predicate = next(item.exists_fn for item in getattr(platform, descriptions) if item.key == key)
    item = NS(type=model, entity_type=category, data={}, sn="fixture", shadow_name="fixture", entity_id="fixture")
    assert not predicate(item)
    item.data[field] = 1
    assert predicate(item)
    item.shadow_name = None
    assert not predicate(item)
    item.shadow_name = "fixture"
    if category is EntityType.LIGHT:
        item.entity_type = EntityType.MAILBOX
    else:
        item.type = "XCG0A-iA"
    assert not predicate(item)


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


@pytest.mark.parametrize("scope_kind", ["station", "child", "multiple"])
def test_scoped_discovery_does_not_rebuild_identity_for_unreported_sibling(monkeypatch, scope_kind):
    station = station_with_children()
    target, sibling = station.devices["0"], station.devices["1"]
    other_parent = copy(target)
    other_parent.entity_id = "different-parent"
    other_parent.station = copy(station)
    other_parent.station.sn = "OTHER"
    incomplete = copy(sibling)
    incomplete.entity_id = "incomplete"
    incomplete.station = copy(station)
    incomplete.station.sn = None
    camera = copy(sibling)
    camera.entity_id = "camera"
    camera.entity_type = EntityType.CAMERA
    callbacks, scanned = [], []
    coordinator = NS(
        data={
            "stations": {station.entity_id: station},
            "devices": {item.entity_id: item for item in (target, sibling, other_parent, incomplete, camera)},
        },
        async_add_listener=lambda cb: callbacks.append(cb) or (lambda: None),
    )

    def discover(_should_add, devices):
        scanned.append(list(devices))
        return []

    setup_dynamic_entities(NS(async_on_unload=lambda _: None), coordinator, lambda _: None, discover)
    identities = set()
    if scope_kind != "station":
        identities.add(_serial_identity(target))
    if scope_kind == "multiple":
        another = copy(target)
        another.sn = "ANOTHER"
        identities.add(_serial_identity(another))
    coordinator._mqtt_child_write_scope = frozenset(identities)
    identity = Mock(wraps=entity_module._serial_identity)
    monkeypatch.setattr(entity_module, "_serial_identity", identity)
    callbacks[0]()

    assert scanned[-1] == (["incomplete", "camera"] if scope_kind == "station" else ["0", "incomplete", "camera"])
    assert sum(call.args[0] is sibling for call in identity.call_args_list) == 1
    initial_scan = scanned[-1]
    coordinator._mqtt_child_write_scope = frozenset({_serial_identity(sibling)})
    callbacks[0]()
    assert scanned[-1] == ["1", "incomplete", "camera"]
    coordinator._mqtt_child_write_scope = frozenset(identities)
    callbacks[0]()
    assert scanned[-1] == initial_scan


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
    format_id = Mock(wraps=entity_module._entity_unique_id)
    monkeypatch.setattr(entity_module, "_entity_unique_id", format_id)
    names = {
        binary_sensor: ("SENSORS",), sensor: ("SENSORS",), button: ("BUTTONS",),
        number: ("NUMBERS",), select: ("SELECTS",), switch: ("SWITCHES",),
        event: ("AI_DETECTION_DESCRIPTION", "MOTION_DESCRIPTION", "MAILBOX_ALARM_DESCRIPTION"),
    }
    eligible_checks, checked = set(), []

    def observe_capability(description):
        def exists(item, *args):
            candidate = (id(item), description.key)
            checked.append(candidate)
            result = description.exists_fn(item, *args)
            if result:
                eligible_checks.add(candidate)
            return result
        return replace(description, exists_fn=exists)

    for name in names[platform]:
        descriptions = getattr(platform, name)
        monkeypatch.setattr(platform, name, (
            tuple(observe_capability(item) for item in descriptions)
            if isinstance(descriptions, tuple) else observe_capability(descriptions)
        ))
    spies = []
    for name in classes:
        spy = Mock(wraps=getattr(platform, name))
        monkeypatch.setattr(platform, name, spy)
        spies.append(spy)
    await platform.async_setup_entry(hass, entry, added.extend)
    assert added
    initial_ids = [item.unique_id for item in added]
    confirmed = eligible_checks.copy()
    assert confirmed
    checked.clear()
    for spy in spies:
        spy.reset_mock()
    format_id.reset_mock()
    for _ in range(3):
        for callback in callbacks:
            callback()
    assert [item.unique_id for item in added] == initial_ids
    assert all(spy.call_count == 0 for spy in spies)
    format_id.assert_not_called()
    assert checked, "Missing capabilities must still be checked"
    assert confirmed.isdisjoint(checked)


def test_cached_discovery_id_does_not_hide_late_capability_or_replacement():
    station = station_with_children()
    original = station.devices["0"]
    added, callbacks = [], []
    coordinator = NS(
        data={"stations": {station.entity_id: station}, "devices": {"0": original}},
        async_add_listener=lambda cb: callbacks.append(cb) or (lambda: None),
    )
    eligible = set()
    publish_candidates = False

    def has_capability(item):
        return item.entity_id in eligible

    def entities(should_add, devices):
        return [
            NS(unique_id=f"{item.entity_id}-late-test")
            for item in devices.values()
            if should_add(item, "late_test", has_capability) and publish_candidates
        ]

    setup_dynamic_entities(NS(async_on_unload=lambda _: None), coordinator, added.extend, entities)
    assert not added
    assert not getattr(coordinator, "_xsense_stable_device_ids", {})
    eligible.add("0")
    callbacks[0]()
    assert not added
    publish_candidates = True
    callbacks[0]()
    assert [item.unique_id for item in added] == ["0-late-test"]

    replacement_station = station_with_children()
    replacement = replacement_station.devices["1"]
    coordinator.data["devices"] = {"1": replacement}
    callbacks[0]()
    assert _serial_identity(replacement) not in coordinator._xsense_stable_device_ids
    eligible.add("1")
    callbacks[0]()
    callbacks[0]()
    assert [item.unique_id for item in added] == ["0-late-test", "1-late-test"]


def test_registered_capability_is_checked_if_rollover_becomes_ambiguous():
    station = station_with_children()
    original = station.devices["0"]
    replacement = copy(original)
    replacement.entity_id = "replacement"
    added, callbacks, checked = [], [], []
    coordinator = NS(
        data={"stations": {station.entity_id: station}, "devices": {"0": original}},
        async_add_listener=lambda cb: callbacks.append(cb) or (lambda: None),
    )

    def exists(item):
        checked.append(item.entity_id)
        return True

    def entities(should_add, devices):
        return [
            NS(unique_id=entity_module._entity_unique_id(
                entity_module._stable_device_id(coordinator, item, _serial_identity(item)), "test",
            ))
            for item in devices.values() if should_add(item, "test", exists)
        ]

    setup_dynamic_entities(NS(async_on_unload=lambda _: None), coordinator, added.extend, entities)
    coordinator.data["devices"] = {"replacement": replacement}
    callbacks[0]()
    assert checked == ["0"]
    assert [item.unique_id for item in added] == ["0-test"]
    coordinator.data["devices"]["0"] = original
    callbacks[0]()
    assert checked == ["0", "replacement"]
    assert [item.unique_id for item in added] == ["0-test", "replacement-test"]
