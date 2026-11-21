"""Conservative child-only state serialization without suppressing notifications."""

import json
from unittest.mock import Mock

import pytest
from test_audit_repairs import make_coordinator, make_station

from custom_components.xsense import binary_sensor, sensor
from custom_components.xsense.coordinator import _mqtt_child_write_scope
from custom_components.xsense.entity import _serial_identity


def station_with_children():
    station = make_station()
    station.set_devices({"devices": [
        {"deviceId": str(i), "deviceSn": f"SN-{i}", "deviceType": "SWS51",
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


def test_child_scope_contains_every_reported_child():
    station = station_with_children()
    scope = _mqtt_child_write_scope(station, {
        "stationSN": station.sn, "devs": {"0": {"alarmStatus": "1"}, "SN-1": {"alarmStatus": "0"}}
    })
    assert scope == frozenset(_serial_identity(child) for child in station.devices.values())


@pytest.mark.parametrize("rssi_key", ["wifiRSSI", "wifiRssi"])
def test_station_only_rssi_does_not_write_child_states(monkeypatch, rssi_key):
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
        json.dumps({"state": {"reported": {"stationSN": station.sn, rssi_key: -48}}}).encode(),
    )
    assert station.data["wifiRSSI"] == -48
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
    {"onLine": "0"}, {"safeMode": "Disarmed"}, {"coLevel": 1},
    {"groupId": "group"}, {"newUnknownField": 1},
])
def test_station_fields_disable_child_only_scope(extra):
    station = station_with_children()
    assert _mqtt_child_write_scope(station, {
        "stationSN": station.sn, "devs": {"0": {"alarmStatus": "1"}}, **extra,
    }) is None


@pytest.mark.parametrize("children", [None, {}, [], {"missing": {}}, {"0": 1}, {"0": {}, "missing": {}}])
def test_uncertain_children_require_full_serialization(children):
    station = station_with_children()
    assert _mqtt_child_write_scope(station, {"devs": children}) is None


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
def test_direct_child_shadow_scopes_notifications_to_the_child_it_changes(serial_key):
    station = station_with_children()
    coordinator = make_coordinator(station)
    coordinator.data["devices"] = dict(station.devices)
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
    assert scopes == [frozenset({_serial_identity(station.devices["0"])})]
