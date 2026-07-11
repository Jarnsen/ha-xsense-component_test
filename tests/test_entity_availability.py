import pytest

from custom_components.xsense.alarm_control_panel import (
    XSenseAlarmControlPanel,
    station_supports_alarm_panel,
)
from custom_components.xsense.python_xsense.station import Station
from custom_components.xsense.binary_sensor import (
    XSenseBinarySensorEntity,
    XSenseBinarySensorEntityDescription,
    XSenseMQTTConnectedEntity,
    MQTTSensor,
)
from custom_components.xsense.button import (
    XSenseButtonEntity,
    XSenseButtonEntityDescription,
)
from custom_components.xsense.sensor import (
    XSenseSensorEntity,
    XSenseSensorEntityDescription,
)
from custom_components.xsense.switch import (
    XSenseSwitchEntity,
    XSenseSwitchEntityDescription,
)
from custom_components.xsense.entity import device_station_id


class Coordinator:
    last_update_success = True
    xsense = None
    mqtt_servers = {}

    def __init__(self, entity, devices=None):
        self.data = {"stations": {entity.entity_id: entity}, "devices": devices or {}}
        self.update_listener_calls = 0

    def mqtt_server(self, host):
        return self.mqtt_servers.get(host)

    def async_update_listeners(self):
        self.update_listener_calls += 1


class House:
    mqtt_server = "us-east-1.x-sense-iot.com"


async def _noop_press(entity, xsense):
    return None


def _xs01_wx_from_real_shadow():
    station = Station(
        House(),
        stationId="74C7ADBA59CB11F0ABBF3701E4DE53F0",
        stationName="Smoke Alarm",
        stationSn="00532DA5",
        category="XS01-WX",
        online=0,
    )
    station.set_data(
        {
            "batInfo": "3",
            "houseId": "AE612FA5573411F0A1E7DD41C95847B4",
            "onlineTime": "20260602063003",
            "utcTime": "20260602063103",
            "stationSN": "00532DA5",
            "status": {"alarmStatus": "0", "muteStatus": "1", "time": "20260602063003"},
            "time": "20260602063003",
            "type": "XS01-WX",
            "wifiRssi": "-38",
        }
    )
    station.set_data(
        {
            "_deviceSN": "00532DA5",
            "_stationSN": "00532DA5",
            "ip": "192.168.1.86",
            "ledLight": "1",
            "ssid": "Reid",
            "sw": "v1.1.0",
            "swMain": "v1.9.0",
            "type": "XS01-WX",
        }
    )
    return station


def test_xs01_wx_online_time_report_marks_station_online():
    station = _xs01_wx_from_real_shadow()

    assert station.online is True


def test_xs01_wx_shadow_data_entities_stay_available():
    station = _xs01_wx_from_real_shadow()
    coordinator = Coordinator(station)

    sensor = XSenseSensorEntity(
        coordinator,
        station,
        XSenseSensorEntityDescription(
            key="battery", value_fn=lambda current: current.data["batInfo"]
        ),
    )
    binary_sensor = XSenseBinarySensorEntity(
        coordinator,
        station,
        XSenseBinarySensorEntityDescription(
            key="alarm_status", value_fn=lambda current: current.data["alarmStatus"]
        ),
    )
    connected = XSenseMQTTConnectedEntity(coordinator, station, MQTTSensor)

    assert sensor.available
    assert sensor.native_value == 3
    assert binary_sensor.available
    assert binary_sensor.is_on is False
    assert connected.available
    assert connected.is_on is True


def test_station_sensor_stays_available_when_station_id_alias_changes():
    station = _xs01_wx_from_real_shadow()
    station.entity_id = "old-station-id"
    coordinator = Coordinator(station)
    sensor = XSenseSensorEntity(
        coordinator,
        station,
        XSenseSensorEntityDescription(
            key="battery", value_fn=lambda current: current.data["batInfo"]
        ),
    )

    refreshed_station = _xs01_wx_from_real_shadow()
    refreshed_station.entity_id = "new-station-id"
    refreshed_station.set_data({"batInfo": "2"})
    coordinator.data = {
        "stations": {refreshed_station.entity_id: refreshed_station},
        "devices": {},
    }

    assert sensor.available
    assert sensor.native_value == 2


def test_child_sensor_stays_available_when_device_and_station_id_aliases_change():
    station = _xs01_wx_from_real_shadow()
    station.entity_id = "old-station-id"
    child = Station(
        station.house,
        stationId="old-child-id",
        stationName="Child Smoke",
        stationSn="child-sn",
        category="XS03-iWX",
        online=1,
    )
    child.entity_id = "old-child-id"
    child.station = station
    child.set_data({"rfLevel": "2", "time": "20260705010101"})
    coordinator = Coordinator(station, {child.entity_id: child})
    rf_sensor = XSenseSensorEntity(
        coordinator,
        child,
        XSenseSensorEntityDescription(
            key="rf_level", value_fn=lambda current: current.data["rfLevel"]
        ),
        station_id=station.entity_id,
    )

    refreshed_station = _xs01_wx_from_real_shadow()
    refreshed_station.entity_id = "new-station-id"
    refreshed_child = Station(
        refreshed_station.house,
        stationId="new-child-id",
        stationName="Child Smoke",
        stationSn="child-sn",
        category="XS03-iWX",
        online=1,
    )
    refreshed_child.entity_id = "new-child-id"
    refreshed_child.station = refreshed_station
    refreshed_child.set_data({"rfLevel": "3", "time": "20260705020202"})
    coordinator.data = {
        "stations": {refreshed_station.entity_id: refreshed_station},
        "devices": {refreshed_child.entity_id: refreshed_child},
    }

    assert rf_sensor.available
    assert rf_sensor.native_value == 3


def test_xs01_wx_controls_are_available_when_shadow_reports_online_time():
    station = _xs01_wx_from_real_shadow()
    coordinator = Coordinator(station)

    button = XSenseButtonEntity(
        coordinator,
        station,
        XSenseButtonEntityDescription(key="test", press_fn=_noop_press),
    )
    switch = XSenseSwitchEntity(
        coordinator,
        station,
        XSenseSwitchEntityDescription(
            key="led_light",
            data_key="ledLight",
            exists_fn=lambda current: True,
            value_fn=lambda current: current.data["ledLight"] == "1",
        ),
    )

    assert button.available
    assert switch.available


async def test_test_button_does_not_mark_self_test_success_locally():
    station = _xs01_wx_from_real_shadow()
    coordinator = Coordinator(station)
    presses = []

    async def _record_press(entity, xsense):
        presses.append(entity.sn)

    button = XSenseButtonEntity(
        coordinator,
        station,
        XSenseButtonEntityDescription(key="test", press_fn=_record_press),
    )

    await button.async_press()

    assert presses == [station.sn]
    assert "lastSelfTest" not in station.data
    assert "lastSelfTestTime" not in station.data
    assert coordinator.update_listener_calls == 0


async def test_failed_test_button_does_not_mark_self_test_success_locally():
    station = _xs01_wx_from_real_shadow()
    coordinator = Coordinator(station)

    async def _fail_press(entity, xsense):
        raise RuntimeError("command failed")

    button = XSenseButtonEntity(
        coordinator,
        station,
        XSenseButtonEntityDescription(key="test", press_fn=_fail_press),
    )

    with pytest.raises(RuntimeError):
        await button.async_press()

    assert "lastSelfTest" not in station.data
    assert "lastSelfTestTime" not in station.data
    assert coordinator.update_listener_calls == 0


def test_child_controls_require_parent_station_online():
    station = _xs01_wx_from_real_shadow()
    station.entity_id = "station-id"
    child = station.__class__(
        station.house,
        stationId="child-id",
        stationName="Child Device",
        stationSn="child-sn",
        category="SD11-MR",
        online=1,
    )
    child.entity_id = "child-id"
    child.station = station
    coordinator = Coordinator(station, {child.entity_id: child})
    button = XSenseButtonEntity(
        coordinator,
        child,
        XSenseButtonEntityDescription(key="test", press_fn=_noop_press),
        station_id=station.entity_id,
    )

    assert button.available

    station._set_online(False)

    assert not button.available


def test_child_controls_ignore_timestamp_only_offline_guess():
    station = _xs01_wx_from_real_shadow()
    station.entity_id = "station-id"
    child = station.__class__(
        station.house,
        stationId="child-id",
        stationName="Smoke RF",
        stationSn="child-sn",
        category="XS03-iWX",
    )
    child.entity_id = "child-id"
    child.station = station
    child.set_data({"onlineTime": "20260531010101", "utcTime": "20260602090102"})
    coordinator = Coordinator(station, {child.entity_id: child})
    button = XSenseButtonEntity(
        coordinator,
        child,
        XSenseButtonEntityDescription(key="test", press_fn=_noop_press),
        station_id=device_station_id(child),
    )

    assert child.online is False
    assert not child._online_from_explicit_flag
    assert button.available


def test_standalone_child_control_uses_device_map_without_parent_station():
    station = _xs01_wx_from_real_shadow()
    child = station.__class__(
        station.house,
        stationId="child-id",
        stationName="Standalone Device",
        stationSn="child-sn",
        category="SSC0A",
        online=1,
    )
    child.entity_id = "child-id"
    coordinator = Coordinator(station, {child.entity_id: child})
    button = XSenseButtonEntity(
        coordinator,
        child,
        XSenseButtonEntityDescription(key="test", press_fn=_noop_press),
        station_id=device_station_id(child),
    )

    assert button._station_id == ""
    assert button._current_entity() is child
    assert button.available


def test_controls_are_unavailable_when_online_state_is_unknown():
    station = _xs01_wx_from_real_shadow()
    station.online = None
    coordinator = Coordinator(station)

    button = XSenseButtonEntity(
        coordinator,
        station,
        XSenseButtonEntityDescription(key="test", press_fn=_noop_press),
    )
    switch = XSenseSwitchEntity(
        coordinator,
        station,
        XSenseSwitchEntityDescription(
            key="led_light",
            data_key="ledLight",
            exists_fn=lambda current: True,
            value_fn=lambda current: current.data["ledLight"] == "1",
        ),
    )

    assert not button.available
    assert not switch.available


def test_alarm_control_panel_requires_reported_online_station():
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    coordinator = Coordinator(station)
    panel = XSenseAlarmControlPanel(coordinator, station)

    assert panel.available

    station.online = None
    assert not panel.available

    station.online = False
    assert not panel.available


def test_connected_sensor_does_not_assume_unknown_online_state():
    station = _xs01_wx_from_real_shadow()
    coordinator = Coordinator(station)
    connected = XSenseMQTTConnectedEntity(coordinator, station, MQTTSensor)

    station.online = None

    assert connected.available
    assert connected.is_on is None


def test_malformed_online_time_does_not_invent_online_state():
    station = Station(
        House(),
        stationId="station-id",
        stationName="Smoke Alarm",
        stationSn="station-sn",
        category="XS01-WX",
    )

    station.set_data({"onlineTime": "not-a-time", "utcTime": "20260602063103"})

    assert station.online is None


def test_stale_shadow_online_time_does_not_override_explicit_online_state():
    station = Station(
        House(),
        stationId="station-id",
        stationName="Smoke Alarm",
        stationSn="station-sn",
        category="XS01-WX",
        online=1,
    )

    station.set_data({"onlineTime": "20260601000000", "utcTime": "20260603000000"})

    assert station.online is True


def test_alarm_control_panel_requires_security_device_family():
    smoke_station = _xs01_wx_from_real_shadow()
    smoke_station.type = "SBS50"
    smoke_station.set_devices(
        {
            "devices": [
                {
                    "deviceId": "smoke-id",
                    "deviceName": "Smoke",
                    "deviceSn": "smoke-sn",
                    "deviceType": "XP0A-MR",
                    "roomName": "Kitchen",
                }
            ]
        }
    )

    security_station = _xs01_wx_from_real_shadow()
    security_station.type = "SBS50"
    security_station.set_devices(
        {
            "devices": [
                {
                    "deviceId": "door-id",
                    "deviceName": "Door",
                    "deviceSn": "door-sn",
                    "deviceType": "SDS0A",
                    "roomName": "Kitchen",
                }
            ]
        }
    )

    remote_station = _xs01_wx_from_real_shadow()
    remote_station.type = "SBS50"
    remote_station.set_devices(
        {
            "devices": [
                {
                    "deviceId": "remote-id",
                    "deviceName": "Remote",
                    "deviceSn": "remote-sn",
                    "deviceType": "SKF01",
                    "roomName": "Kitchen",
                }
            ]
        }
    )

    assert not station_supports_alarm_panel(smoke_station)
    assert not station_supports_alarm_panel(remote_station)
    assert station_supports_alarm_panel(security_station)

    for security_type in ("SDS0A", "SMS0A", "SKP0A"):
        security_station.set_devices(
            {
                "devices": [
                    {
                        "deviceId": f"{security_type}-id",
                        "deviceName": security_type,
                        "deviceSn": f"{security_type}-sn",
                        "deviceType": security_type,
                        "roomName": "Kitchen",
                    }
                ]
            }
        )
        assert station_supports_alarm_panel(security_station)
