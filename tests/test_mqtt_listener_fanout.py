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


def test_child_scope_contains_every_reported_child():
    station = station_with_children()
    scope = _mqtt_child_write_scope(station, {
        "stationSN": station.sn, "devs": {"0": {"alarmStatus": "1"}, "SN-1": {"alarmStatus": "0"}}
    })
    assert scope == frozenset(_serial_identity(child) for child in station.devices.values())


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
