"""Conservative child-only state serialization without suppressing notifications."""

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from test_audit_repairs import make_coordinator, make_station

from custom_components.xsense import (
    binary_sensor,
    button,
    number,
    select,
    sensor,
    switch,
)
from custom_components.xsense.coordinator import _mqtt_child_write_scope
from custom_components.xsense.entity import _serial_identity


def station_with_children(model="SWS51"):
    station = make_station()
    station.set_devices({"devices": [
        {"deviceId": str(i), "deviceSn": f"SN-{i}", "deviceType": model,
         "deviceName": f"Leak {i}", "roomName": "Room"}
        for i in range(2)
    ]})
    return station


def test_temperature_request_echo_does_not_dispatch_state_updates():
    station = station_with_children()
    coordinator = make_coordinator(station)
    coordinator.async_update_listeners = Mock()
    topic = f"$aws/things/{station.shadow_name}/shadow/name/2nd_apptempdata/update"
    desired = {"shadow": "appTempData", "stationSN": station.sn, "deviceSN": ["SN-0"]}
    coordinator.async_event_received(topic, json.dumps({"state": {"desired": desired}}).encode())
    coordinator.async_update_listeners.assert_not_called()

    reported = {"stationSN": station.sn, "devs": {"SN-0": {"alarmStatus": "1"}}}
    coordinator.async_event_received(
        topic, json.dumps({"state": {"desired": desired, "reported": reported}}).encode()
    )
    coordinator.async_update_listeners.assert_called_once()


@pytest.mark.parametrize("shadow", ["2nd_mainpage", "2nd_modeconfirm", "2nd_cfg_station"])
@pytest.mark.parametrize("state", [{"desired": {}}, {"reported": {}}, {"reported": []}, {"reported": None}, {}])
def test_empty_shadow_update_does_not_reset_alarm_or_notify_listeners(shadow, state):
    station = station_with_children()
    station.has_alarm = True
    coordinator = make_coordinator(station)
    coordinator.async_update_listeners = Mock()
    topic = f"$aws/things/{station.shadow_name}/shadow/name/{shadow}/update"
    coordinator.async_event_received(topic, json.dumps({"state": state}).encode())
    assert station.has_alarm is True
    coordinator.async_update_listeners.assert_not_called()

    coordinator.async_event_received(
        topic, json.dumps({"state": {
            "desired": {"stationSN": station.sn},
            "reported": {"stationSN": station.sn, "alarmStatus": "0"},
        }}).encode()
    )
    assert station.has_alarm is False
    coordinator.async_update_listeners.assert_called_once()


def test_child_scope_contains_every_reported_child():
    station = station_with_children()
    scope = _mqtt_child_write_scope(station, {
        "stationSN": station.sn, "devs": {"0": {"alarmStatus": "1"}, "SN-1": {"alarmStatus": "0"}}
    })
    assert scope == frozenset(_serial_identity(child) for child in station.devices.values())


@pytest.mark.parametrize("children", [None, {}, []])
def test_mainpage_routing_metadata_alone_does_not_dispatch(children):
    station = station_with_children()
    coordinator = make_coordinator(station)
    coordinator.async_update_listeners = Mock()
    station.has_alarm = True
    topic = f"$aws/things/{station.shadow_name}/shadow/name/2nd_mainpage/update"
    report = {"stationSN": station.sn}
    if children is not None:
        report["devs"] = children
    coordinator.async_event_received(topic, json.dumps({"state": {"reported": report}}).encode())
    coordinator.async_update_listeners.assert_not_called()
    assert station.has_alarm is True

    report["devs"] = {"0": {"alarmStatus": "1"}}
    coordinator.async_event_received(topic, json.dumps({"state": {"reported": report}}).encode())
    coordinator.async_update_listeners.assert_called_once()
    assert station.devices["0"].data["alarmStatus"] is True


@pytest.mark.parametrize(
    "fields",
    [
        {"wifiRSSI": -48},
        {"wifiRssi": -48},
        {"wifiRSSI": -48, "ssid": "fixture", "ip": "192.0.2.1", "wifi_sw": "1.0"},
        {"ssid": "fixture"},
    ],
)
def test_station_only_network_reports_do_not_write_child_states(monkeypatch, fields):
    from homeassistant.helpers.update_coordinator import CoordinatorEntity

    station = station_with_children()
    other_station = make_station(serial="other-station")
    coordinator = make_coordinator(station, other_station)
    coordinator.data["devices"] = dict(station.devices)
    description = next(item for item in sensor.SENSORS if item.key == "wifi_rssi")
    station_sensor = sensor.XSenseSensorEntity(coordinator, station, description)
    station_sensor._coordinator_state_initialized = True
    other_sensor = sensor.XSenseSensorEntity(coordinator, other_station, description)
    other_sensor._coordinator_state_initialized = True
    child = station.devices["0"]
    child_sensor = sensor.XSenseSensorEntity(coordinator, child, description, station.entity_id)
    child_sensor._coordinator_state_initialized = True
    writes = []
    monkeypatch.setattr(CoordinatorEntity, "_handle_coordinator_update", lambda item: writes.append(item))
    coordinator.async_update_listeners = lambda: [
        item._handle_coordinator_update() for item in (station_sensor, child_sensor, other_sensor)
    ]
    coordinator.async_event_received(
        f"$aws/things/{station.shadow_name}/shadow/name/2nd_mainpage/update",
        json.dumps({"state": {"reported": {"stationSN": station.sn, **fields}}}).encode(),
    )
    for key, value in fields.items():
        assert station.data["wifiRSSI" if key == "wifiRssi" else key] == value
    assert writes == [station_sensor]
    coordinator.async_update_listeners()
    assert writes == [station_sensor, station_sensor, child_sensor, other_sensor]


def test_rssi_alias_with_child_keeps_scope_and_timing_count():
    station = station_with_children()
    coordinator = make_coordinator(station)
    scopes = []
    coordinator.async_update_listeners = lambda: scopes.append(coordinator._mqtt_child_write_scope)
    coordinator.async_event_received(
        f"$aws/things/{station.shadow_name}/shadow/name/2nd_mainpage/update",
        json.dumps({"state": {"reported": {
            "stationSn": station.sn, "wifiRssi": -48, "devs": {"0": {"alarmStatus": "1"}},
        }}}).encode(),
    )
    assert scopes == [frozenset({_serial_identity(station.devices["0"])})]
    assert coordinator._mqtt_rssi_child_dispatch_work["slowest"]["reported_child_count"] == 1


def test_resolved_mqtt_message_does_not_build_routing_debug_context_when_disabled(monkeypatch):
    station = station_with_children()
    coordinator = make_coordinator(station)
    namespace = coordinator._async_process_mqtt_event.__func__.__globals__
    coordinator.async_update_listeners = Mock()
    context = Mock(return_value={})
    monkeypatch.setitem(namespace, "_mqtt_event_debug_context", context)
    monkeypatch.setattr(namespace["LOGGER"], "isEnabledFor", lambda _: False)
    coordinator.async_event_received(
        f"$aws/things/{station.shadow_name}/shadow/name/2nd_mainpage/update",
        json.dumps({"state": {"reported": {"stationSN": station.sn, "wifiRSSI": -48}}}).encode(),
    )
    assert station.data["wifiRSSI"] == -48
    context.assert_not_called()


@pytest.mark.parametrize("route", ["unmatched", "self_test"])
@pytest.mark.parametrize("debug", [False, True])
def test_mqtt_debug_context_is_lazy_without_changing_dispatch(monkeypatch, route, debug):
    station = station_with_children()
    coordinator = make_coordinator(station)
    namespace = coordinator._async_process_mqtt_event.__func__.__globals__
    coordinator.async_update_listeners = Mock()
    context = Mock(return_value={})
    fire_self_test_event = Mock()
    monkeypatch.setitem(namespace, "_mqtt_event_debug_context", context)
    monkeypatch.setitem(namespace, "_fire_self_test_event", fire_self_test_event)
    monkeypatch.setattr(namespace["LOGGER"], "isEnabledFor", lambda _: debug)
    if route == "self_test":
        shadow_name, serial, shadow = station.shadow_name, station.sn, "2nd_selftestup"
    else:
        shadow_name, serial, shadow = "unknown-thing", "unknown-serial", "2nd_mainpage"
    coordinator.async_event_received(
        f"$aws/things/{shadow_name}/shadow/name/{shadow}/update",
        json.dumps({"state": {"reported": {"stationSN": serial, "wifiRSSI": -48}}}).encode(),
    )
    expected_calls = 2 if route == "self_test" else 1
    assert context.call_count == (expected_calls if debug else 0)
    if route == "self_test":
        fire_self_test_event.assert_called_once()
        coordinator.async_update_listeners.assert_called_once()
    else:
        fire_self_test_event.assert_not_called()
        coordinator.async_update_listeners.assert_not_called()


def test_repeated_sbs50_presence_keeps_freshness_without_fanning_out():
    station = station_with_children()
    coordinator = make_coordinator(station)
    coordinator.async_update_listeners = Mock()

    def deliver(event, timestamp):
        coordinator.async_event_received(
            f"$aws/events/presence/{event}/{station.shadow_name}",
            json.dumps({
                "clientId": station.shadow_name, "eventType": event, "timestamp": timestamp,
            }).encode(),
        )

    deliver("connected", 1)
    first_revision = station._xsense_presence_revision
    deliver("connected", 3)
    assert station._xsense_presence_revision is not first_revision
    coordinator.async_update_listeners.assert_called_once()
    deliver("disconnected", 2)
    assert station.online is True
    deliver("disconnected", 4)
    assert station.online is False
    assert coordinator.async_update_listeners.call_count == 2


@pytest.mark.parametrize(
    "route", ["presence", "2nd_safemode", "2nd_modeconfirm", "mode_with_children", "mode_with_keyed_child",
              "mode_with_availability", "intrusion", "full", "list"],
)
def test_sbs50_station_notifications_skip_unrelated_writes(monkeypatch, route):
    from homeassistant.helpers.update_coordinator import CoordinatorEntity

    station = station_with_children("SDS0A")
    if route == "mode_with_keyed_child":
        station.devices["0"].sn = "forceReason"
    other = make_station(serial="other-station")
    other.set_devices({"devices": [
        {"deviceId": "other-child", "deviceSn": "other-child", "deviceType": "SWS51",
         "deviceName": "Other leak sensor", "roomName": "Room"}
    ]})
    coordinator = make_coordinator(station, other)
    coordinator.data["devices"] = {**station.devices, **other.devices}
    description = next(item for item in sensor.SENSORS if item.key == "battery")
    affected = [
        sensor.XSenseSensorEntity(coordinator, station, description),
        sensor.XSenseSensorEntity(coordinator, station.devices["0"], description, station.entity_id),
    ]
    unaffected = [
        sensor.XSenseSensorEntity(coordinator, other, description),
        sensor.XSenseSensorEntity(coordinator, other.devices["other-child"], description, other.entity_id),
    ]
    entities = affected + unaffected
    for item in entities:
        item._coordinator_state_initialized = True

    writes = []
    monkeypatch.setattr(CoordinatorEntity, "_handle_coordinator_update", lambda item: writes.append(item))
    coordinator.async_update_listeners = lambda: [item._handle_coordinator_update() for item in entities]
    if route == "presence":
        for timestamp, event in enumerate(("connected", "disconnected"), start=1):
            coordinator.async_event_received(
                f"$aws/events/presence/{event}/{station.shadow_name}",
                json.dumps({
                    "clientId": station.shadow_name, "eventType": event, "timestamp": timestamp,
                }).encode(),
            )
            assert station.online is (event == "connected")
        expected = affected * 2
    elif route == "intrusion":
        coordinator.hass = Mock()
        for value in ("1", "0"):
            coordinator.async_event_received(
                "@xsense/events/safealarm/house",
                json.dumps({"eventData": {
                    "stationSn": station.sn, "deviceSn": "SN-0",
                    "deviceType": "SDS0A", "isAlarm": value,
                }}).encode(),
            )
            assert (station.sn in coordinator.active_intrusion_sensors) is (value == "1")
        coordinator.hass.bus.async_fire.assert_called_once()
        # Each transition updates station listeners before applying child data.
        expected = [affected[0], *affected] * 2
    elif route in ("full", "list"):
        child_report = {"deviceSN": "SN-0", "alarmStatus": "1"}
        reported = [child_report] if route == "list" else {
            "stationSN": station.sn, "onLine": "0", "devs": {"0": child_report},
        }
        coordinator.async_event_received(
            f"$aws/things/{station.shadow_name}/shadow/name/2nd_mainpage/update",
            json.dumps({"state": {"reported": reported}}).encode(),
        )
        assert station.devices["0"].data["alarmStatus"] is True
        if route == "full":
            assert station.online is False
        expected = affected
    else:
        reported = {"stationSN": station.sn, "safeMode": "Away"}
        topic_kind = route
        if route == "2nd_modeconfirm":
            reported["forceReason"] = [{"deviceSN": "SN-0"}]
            reported["exitDelay"] = 15
        if route == "mode_with_children":
            topic_kind = "2nd_safemode"
            reported["devs"] = {"0": {"batInfo": "2"}}
        if route == "mode_with_keyed_child":
            topic_kind = "2nd_safemode"
            station.device_by_sn["forceReason"] = "0"
            reported["forceReason"] = {"batInfo": "2"}
        if route == "mode_with_availability":
            topic_kind = "2nd_safemode"
            reported["onLine"] = "0"
        coordinator.async_event_received(
            f"$aws/things/{station.shadow_name}/shadow/name/{topic_kind}/update",
            json.dumps({"state": {"reported": reported}}).encode(),
        )
        assert station.safe_mode == ("Away" if topic_kind == "2nd_safemode" else "Disarmed")
        if route in ("mode_with_children", "mode_with_keyed_child"):
            assert station.devices["0"].data["batInfo"] == 2
        if route == "mode_with_availability":
            assert station.online is False
        expected = affected if route.startswith("mode_with_") else affected[:1]
    assert writes == expected
    coordinator.async_update_listeners()
    assert writes == expected + entities


@pytest.mark.parametrize("present", [True, False])
@pytest.mark.parametrize("intervening_refresh", [False, True])
def test_combined_scopes_resolve_child_once_and_allow_missing_state_write(
    monkeypatch, present, intervening_refresh
):
    from homeassistant.helpers.update_coordinator import CoordinatorEntity

    station = station_with_children()
    child = station.devices["0"]
    coordinator = make_coordinator(station)
    coordinator.data["devices"] = {"0": child} if present else {}
    coordinator._mqtt_write_station = station
    coordinator._mqtt_child_write_scope = frozenset({_serial_identity(station.devices["1"])})
    description = next(item for item in sensor.SENSORS if item.key == "battery")
    entity = sensor.XSenseSensorEntity(coordinator, child, description, station.entity_id)
    entity._coordinator_state_initialized = True
    lookup = Mock(wraps=entity._current_entity)
    monkeypatch.setattr(entity, "_current_entity", lookup)
    write = Mock()
    monkeypatch.setattr(CoordinatorEntity, "_handle_coordinator_update", write)

    entity._handle_coordinator_update()

    lookup.assert_called_once_with()
    if present:
        write.assert_not_called()
    else:
        write.assert_called_once_with()
        writes_before_recovery = 1
        if intervening_refresh:
            scope = coordinator._mqtt_child_write_scope
            coordinator._mqtt_child_write_scope = None
            coordinator._mqtt_write_station = None
            entity._handle_coordinator_update()
            writes_before_recovery += 1
            coordinator._mqtt_child_write_scope = scope
            coordinator._mqtt_write_station = station
        coordinator.data["devices"]["0"] = child
        entity._handle_coordinator_update()
        assert write.call_count == writes_before_recovery + 1
        entity._handle_coordinator_update()
        assert write.call_count == writes_before_recovery + 1


@pytest.mark.parametrize("shape", ["top_level", "nested_list", "reported_list"])
def test_equivalent_child_collections_get_the_same_scope(shape):
    station = station_with_children()
    rows = [{"_deviceSN": "SN-0", "alarmStatus": "1"}]
    report = {
        "top_level": {"SN-0": {"alarmStatus": "1"}},
        "nested_list": {"stationSN": station.sn, "devs": rows},
        "reported_list": rows,
    }[shape]
    assert _mqtt_child_write_scope(station, report) == frozenset({_serial_identity(station.devices["0"])})


@pytest.mark.parametrize("report", [
    {"unknown": {"alarmStatus": "1"}},
    {"devs": [{"_deviceSN": "SN-0"}, {"_deviceSN": "missing"}]},
    {"devs": [{"_deviceSN": "SN-0"}, 1]},
    [{"_deviceSN": "missing"}],
])
def test_uncertain_collection_shapes_keep_global_fallback(report):
    assert _mqtt_child_write_scope(station_with_children(), report) is None


@pytest.mark.parametrize("extra", [
    {"onLine": "0"}, {"safeMode": "Away"}, {"coLevel": 1},
    {"groupId": "group"}, {"newUnknownField": 1},
])
def test_station_fields_disable_child_only_scope(extra):
    station = station_with_children()
    assert _mqtt_child_write_scope(station, {
        "stationSN": station.sn, "devs": {"0": {"alarmStatus": "1"}}, **extra,
    }) is None


def test_repeated_sbs50_mode_does_not_broaden_child_report():
    station = station_with_children()
    children = {"0": {"alarmStatus": "1"}}
    report = {"stationSN": station.sn, "safeMode": station.safe_mode, "devs": children}
    assert _mqtt_child_write_scope(station, report, published=True) == frozenset({_serial_identity(station.devices["0"])})
    assert report["safeMode"] == station.safe_mode
    assert _mqtt_child_write_scope(station, report) is None


@pytest.mark.parametrize("key", ["online", "onLine"])
def test_repeated_explicit_online_report_can_refresh_restored_children(key):
    station = station_with_children()
    station._set_online(True)
    report = {"stationSN": station.sn, key: "1", "devs": {"0": {"alarmStatus": "1"}}}
    assert _mqtt_child_write_scope(station, report, published=True) is None


@pytest.mark.parametrize("key", ["online", "onLine"])
@pytest.mark.parametrize("child_offline", [False, True])
def test_sbs50_availability_report_updates_controls_without_rewriting_sibling_telemetry(
    monkeypatch, key, child_offline,
):
    from homeassistant.helpers.update_coordinator import CoordinatorEntity

    from custom_components.xsense.python_xsense.async_xsense import AsyncXSense

    station = station_with_children()
    coordinator = make_coordinator(station)
    coordinator.xsense.has_action = AsyncXSense().has_action
    coordinator.data["devices"] = dict(station.devices)
    reported, sibling = station.devices.values()
    for child in (reported, sibling):
        child.set_data({"batInfo": 3, "alarmStatus": "0", "alarmVol": 75, "alarmTone": "1", "alarmEnabled": True})
    if child_offline:
        sibling._set_online(False)
    description = next(item for item in sensor.SENSORS if item.key == "battery")
    batteries = [sensor.XSenseSensorEntity(coordinator, child, description, station.entity_id)
                 for child in (reported, sibling)]
    alarm_description = next(item for item in binary_sensor.SENSORS if item.key == "alarm_status")
    alarms = [binary_sensor.XSenseBinarySensorEntity(coordinator, child, alarm_description, station.entity_id)
              for child in (reported, sibling)]
    controls = [
        factory(coordinator, sibling, next(item for item in descriptions if item.key == field), station.entity_id)
        for factory, descriptions, field in (
            (button.XSenseButtonEntity, button.BUTTONS, "test"),
            (number.XSenseNumberEntity, number.NUMBERS, "alarm_volume"),
            (select.XSenseSelectEntity, select.SELECTS, "alarm_tone"),
            (switch.XSenseSwitchEntity, switch.SWITCHES, "alarm_enabled"),
        )
    ]
    connected = binary_sensor.XSenseMQTTConnectedEntity(coordinator, station, binary_sensor.MQTTSensor)
    entities = [connected, *batteries, *alarms, *controls]
    for item in entities:
        item._coordinator_state_initialized = True
    writes = []
    coordinator.async_update_listeners = lambda: [item._handle_coordinator_update() for item in entities]
    for index, item in enumerate(controls):
        item.entity_id = f"button.fixture_{index}"
    published = {}
    for item in controls:
        item.hass = SimpleNamespace(states=SimpleNamespace(get=published.get))

    def write(item):
        writes.append(item)
        if item in controls:
            published[item.entity_id] = SimpleNamespace(
                state="unknown" if item.available else "unavailable"
            )

    monkeypatch.setattr(CoordinatorEntity, "_handle_coordinator_update", write)

    def deliver(online):
        writes.clear()
        coordinator.async_event_received(
            f"$aws/things/{station.shadow_name}/shadow/name/2nd_mainpage/update",
            json.dumps({"state": {"reported": {
                "stationSN": station.sn, key: "1" if online else "0",
                "devs": {"0": {"batInfo": "2", "alarmStatus": "1"}},
            }}}).encode(),
        )
        assert connected.is_on is online
        expected_availability = online and sibling.online is not False
        assert all(control.available is expected_availability for control in controls)
        assert batteries[0].native_value != batteries[1].native_value
        assert alarms[0].is_on is True
        assert alarms[1].is_on is False

    updated = [connected, batteries[0], alarms[0]]
    if child_offline:
        deliver(True)
        assert writes == updated + controls
        published[controls[0].entity_id] = SimpleNamespace(state="unknown")
        deliver(False)
        assert writes == updated + controls[:1]
        assert all(published[item.entity_id].state == "unavailable" for item in controls)
        deliver(True)
        assert writes == updated
        sibling._set_online(True)
        deliver(True)
        assert writes == updated + controls
        return

    deliver(False)
    assert writes == updated + controls
    published[controls[0].entity_id] = SimpleNamespace(state="unknown")
    deliver(True)
    assert writes == updated + controls
    deliver(True)
    assert writes == updated
    published[controls[0].entity_id] = SimpleNamespace(state="unavailable")
    deliver(True)
    assert writes == updated + controls[:1]
    assert published[controls[0].entity_id].state == "unknown"
    del published[controls[1].entity_id]
    deliver(True)
    assert writes == updated + controls[1:2]

    station._online_from_explicit_flag = False
    deliver(True)
    assert writes == updated + controls

    replacement = station_with_children().devices["1"]
    replacement.station = station
    replacement.set_data({
        "batInfo": 3, "alarmStatus": "0", "alarmVol": 65, "alarmTone": "1", "alarmEnabled": True,
    })
    coordinator.data["devices"][sibling.entity_id] = replacement
    deliver(True)
    assert writes == updated + controls


@pytest.mark.parametrize("children", [None, {}, [], {"missing": {}}, {"0": 1}, {"0": {}, "missing": {}}])
def test_uncertain_children_require_full_serialization(children):
    station = station_with_children()
    assert _mqtt_child_write_scope(station, {"devs": children}) is None


def test_availability_shadow_skips_only_current_unreported_scalar_sensors(monkeypatch):
    from homeassistant.helpers.update_coordinator import CoordinatorEntity

    station = station_with_children()
    station._set_online(True)
    station.set_data({"ssid": "network", "wifiRSSI": -45})
    child = station.devices["0"]
    child.set_data({"rfLevel": 3, "batInfo": 3})
    coordinator = make_coordinator(station)
    coordinator.data["devices"] = dict(station.devices)
    keys = {item.key: item for item in sensor.SENSORS}
    ssid, rssi, signal, battery = [
        sensor.XSenseSensorEntity(coordinator, subject, keys[key], parent)
        for subject, key, parent in (
            (station, "wifi_ssid", None), (station, "wifi_rssi", None),
            (child, "rf_level", station.entity_id), (child, "battery", station.entity_id),
        )
    ]
    entities = [ssid, rssi, signal, battery]
    published = {}
    for item in entities:
        item.entity_id = f"sensor.{item.entity_description.key}"
        item.hass = SimpleNamespace(states=SimpleNamespace(get=published.get))
        item._coordinator_state_initialized = True
        published[item.entity_id] = SimpleNamespace(state=str(item.native_value))

    writes = []

    def write(item):
        writes.append(item)
        published[item.entity_id] = SimpleNamespace(state=str(item.native_value))

    monkeypatch.setattr(CoordinatorEntity, "_handle_coordinator_update", write)
    coordinator.async_update_listeners = lambda: [item._handle_coordinator_update() for item in entities]

    def deliver(online, child_fields, **station_fields):
        writes.clear()
        coordinator.async_event_received(
            f"$aws/things/{station.shadow_name}/shadow/name/2nd_mainpage/update",
            json.dumps({"state": {"reported": {
                "stationSN": station.sn, "onLine": online, "wifiRSSI": -48,
                "devs": {"0": child_fields}, **station_fields,
            }}}).encode(),
        )

    deliver("0", {"batInfo": 2})
    assert writes == [rssi, battery]
    assert published[rssi.entity_id].state == "-48"
    assert published[battery.entity_id].state == "67"

    published[ssid.entity_id] = SimpleNamespace(state="stale-network")
    del published[signal.entity_id]
    deliver("1", {"batInfo": 2})
    assert writes == entities
    assert published[ssid.entity_id].state == "network"
    assert published[signal.entity_id].state == str(signal.native_value)

    deliver("0", {"batInfo": 2}, ssid="network")
    assert writes == [ssid, rssi, battery]

    deliver("1", {"status": {"rfLevel": 1}, "batInfo": 2})
    assert writes == entities
    assert published[signal.entity_id].state == str(signal.native_value)
    assert child.data["rfLevel"] == 1


@pytest.mark.asyncio
async def test_availability_shadow_preserves_alarm_and_status_changes(monkeypatch, tmp_path):
    from homeassistant.core import HomeAssistant, callback
    from homeassistant.helpers.event import async_track_state_report_event
    from homeassistant.helpers.update_coordinator import CoordinatorEntity

    hass = HomeAssistant(str(tmp_path))
    monkeypatch.setattr(sensor.XSenseSensorEntity, "unit_of_measurement", None)
    station = station_with_children(model="SD19-MN")
    station._set_online(True)
    station.set_data({"alarmStatus": False})
    child = station.devices["0"]
    child.set_data({
        "alarmStatus": False, "muteStatus": 0, "isLifeEnd": False, "batInfo": 3,
        "time": "2026-11-22T12:00:00+01:00", "lastSelfTest": "success",
        "lastSelfTestTime": "20261122103000",
    })
    coordinator = make_coordinator(station)
    coordinator.data["devices"] = dict(station.devices)
    targets = {}
    for name, platform, entity_class, subject, key in (
        ("station_alarm", binary_sensor, binary_sensor.XSenseBinarySensorEntity, station, "alarm_status"),
        ("child_alarm", binary_sensor, binary_sensor.XSenseBinarySensorEntity, child, "alarm_status"),
        ("mute", binary_sensor, binary_sensor.XSenseBinarySensorEntity, child, "mute_status"),
        ("life_end", binary_sensor, binary_sensor.XSenseBinarySensorEntity, child, "is_life_end"),
        ("device_status", sensor, sensor.XSenseSensorEntity, child, "device_status"),
        ("time", sensor, sensor.XSenseSensorEntity, child, "time"),
        ("last_self_test", sensor, sensor.XSenseSensorEntity, child, "last_self_test"),
        ("last_self_test_time", sensor, sensor.XSenseSensorEntity, child, "last_self_test_time"),
    ):
        description = next(d for d in platform.SENSORS if d.key == key)
        entity = entity_class(coordinator, subject, description, None if subject is station else station.entity_id)
        entity.entity_id = f"{platform.__name__.rsplit('.', 1)[-1]}.{name}"
        entity.hass = hass
        entity._coordinator_state_initialized = True
        targets[name] = entity
        hass.states.async_set(entity.entity_id, entity.state)

    writes = set()

    def write(entity):
        writes.add(entity.entity_id.split(".", 1)[1])
        hass.states.async_set(entity.entity_id, entity.state)

    monkeypatch.setattr(CoordinatorEntity, "_handle_coordinator_update", write)
    coordinator.async_update_listeners = lambda: [entity._handle_coordinator_update() for entity in targets.values()]

    def deliver(online, child_fields, **station_fields):
        writes.clear()
        coordinator.async_event_received(
            f"$aws/things/{station.shadow_name}/shadow/name/2nd_mainpage/update",
            json.dumps({"state": {"reported": {
                "stationSN": station.sn, "onLine": online, "wifiRSSI": -48,
                "devs": {"0": child_fields}, **station_fields,
            }}}).encode(),
        )

    def state(name):
        return hass.states.get(targets[name].entity_id).state

    assert state("time") == "2026-11-22T11:00:00+00:00"
    deliver("0", {"alarmStatus": False, "batInfo": 3})
    assert writes == {"child_alarm", "mute", "device_status"}

    # A fresh packet with identical data still reports these observations to HA.
    reported_ids = {targets[name].entity_id for name in writes}
    all_ids = {entity.entity_id for entity in targets.values()}
    previous = {
        entity_id: (hass.states.get(entity_id).last_changed, hass.states.get(entity_id).last_reported)
        for entity_id in all_ids
    }
    reports = []

    @callback
    def record_report(event):
        reports.append(event.data["entity_id"])

    unsubscribe = async_track_state_report_event(hass, all_ids, record_report)
    try:
        deliver("0", {"alarmStatus": False, "batInfo": 3})
        await hass.async_block_till_done()
    finally:
        unsubscribe()
    assert set(reports) == reported_ids
    assert len(reports) == len(reported_ids)
    for entity_id, (last_changed, last_reported) in previous.items():
        current = hass.states.get(entity_id)
        assert current.last_changed == last_changed
        if entity_id in reported_ids:
            assert current.last_reported > last_reported
        else:
            assert current.last_reported == last_reported

    deliver("1", {"alarmStatus": True, "batInfo": 1})
    assert writes == {"child_alarm", "mute", "device_status"}
    assert (state("child_alarm"), state("mute"), state("device_status")) == ("on", "on", "low_battery")

    hass.states.async_set(targets["station_alarm"].entity_id, "unavailable")
    hass.states.async_remove(targets["life_end"].entity_id)
    hass.states.async_set(targets["last_self_test_time"].entity_id, "unknown")
    deliver("0", {"alarmStatus": True, "batInfo": 1})
    assert writes == {"station_alarm", "child_alarm", "mute", "life_end", "device_status", "last_self_test_time"}

    deliver("1", {
        "status": {"isLifeEnd": True}, "alarmStatus": False, "time": "20261122113000",
        "lastSelfTest": "failed", "lastSelfTestTime": "20261122113500",
    }, alarmStatus=True)
    assert writes == targets.keys()
    assert (state("station_alarm"), state("child_alarm"), state("mute"), state("life_end")) == (
        "on", "off", "off", "on",
    )
    assert (state("time"), state("last_self_test"), state("last_self_test_time")) == (
        "2026-11-22T11:30:00+00:00", "failed", "2026-11-22T11:35:00+00:00",
    )


def test_camera_station_never_gets_child_only_scope():
    station = make_station(category="SSC0A")
    assert _mqtt_child_write_scope(station, {"devs": {"0": {}}}) is None


@pytest.mark.parametrize("platform, entity_class, descriptions", [
    (sensor, sensor.XSenseSensorEntity, "SENSORS"),
    (binary_sensor, binary_sensor.XSenseBinarySensorEntity, "SENSORS"),
])
def test_camera_state_entities_do_not_opt_into_child_filter(platform, entity_class, descriptions):
    camera = make_station(category="SSC0A")
    coordinator = make_coordinator(camera)
    description = getattr(platform, descriptions)[0]
    entity = entity_class(coordinator, camera, description)
    assert entity._mqtt_child_state_only is False


def test_notification_scope_is_restored_when_listener_raises():
    station = station_with_children()
    coordinator = make_coordinator(station)
    previous = frozenset({("previous",)})
    coordinator._mqtt_child_write_scope = previous
    captured = []

    def notify():
        captured.append(coordinator._mqtt_child_write_scope)
        raise RuntimeError("listener failed")

    coordinator.async_update_listeners = Mock(side_effect=notify)
    with pytest.raises(RuntimeError, match="listener failed"):
        coordinator.async_event_received(
            f"$aws/things/{station.shadow_name}/shadow/name/2nd_mainpage/update",
            json.dumps({"state": {"reported": {"stationSN": station.sn, "devs": {"0": {"alarmStatus": "1"}}}}}).encode(),
        )
    assert captured == [frozenset({_serial_identity(station.devices["0"])})]
    assert coordinator._mqtt_child_write_scope is previous


@pytest.mark.parametrize("serial_key", ["_deviceSN", "deviceSN", "deviceSn"])
def test_direct_child_shadow_scopes_notifications_to_the_child_it_changes(monkeypatch, serial_key):
    station = station_with_children()
    coordinator = make_coordinator(station)
    coordinator.data["devices"] = dict(station.devices)
    namespace = coordinator._async_process_mqtt_event.__func__.__globals__
    select_scope = Mock(wraps=namespace["_mqtt_child_write_scope"])
    monkeypatch.setitem(namespace, "_mqtt_child_write_scope", select_scope)
    scopes = []
    coordinator.async_update_listeners = lambda: scopes.append(coordinator._mqtt_child_write_scope)
    coordinator.async_event_received(
        f"$aws/things/{station.shadow_name}/shadow/name/2nd_deviceinfo/update",
        json.dumps({"state": {"reported": {
            "stationSN": station.sn, serial_key: "SN-0", "alarmVol": "75",
        }}}).encode(),
    )
    assert station.devices["0"].data["alarmVol"] in (75, "75")
    assert "alarmVol" not in station.devices["1"].data
    assert "alarmVol" not in station.data
    select_scope.assert_called_once()
    assert scopes == [frozenset({_serial_identity(station.devices["0"])})]
