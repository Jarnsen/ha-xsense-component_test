from types import SimpleNamespace

import pytest

from custom_components.xsense.alarm_control_panel import (
    XSenseAlarmControlPanel,
    pending_force_arm_mode,
    station_supports_alarm_panel,
)
from custom_components.xsense.python_xsense.base import XSenseBase
from custom_components.xsense.python_xsense.station import Station
from custom_components.xsense.binary_sensor import (
    SENSORS as BINARY_SENSORS,
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


def test_reported_test_active_state_is_exposed_from_device_data():
    station = _xs01_wx_from_real_shadow()
    description = next(item for item in BINARY_SENSORS if item.key == "test_active")

    assert not description.exists_fn(station)

    station.set_data({"test": "1"})

    assert description.exists_fn(station)
    assert description.value_fn(station) is True

    station.set_data({"test": "0"})

    assert description.exists_fn(station)
    assert description.value_fn(station) is False


def test_sws51_exposes_specific_alarm_states_without_generic_duplicates():
    """SWS51 uses separate APK water and temperature alarm states."""
    device = SimpleNamespace(
        type="SWS51",
        data={
            "alarmStatus": True,
            "mute": True,
            "muteStatus": True,
            "waterAlarmStatus": False,
            "waterMuteStatus": False,
            "tempAlarmStatus": True,
            "tempMuteStatus": True,
        },
    )
    descriptions = {description.key: description for description in BINARY_SENSORS}

    assert not descriptions["alarm_status"].exists_fn(device)
    assert "mute" not in descriptions
    assert not descriptions["mute_status"].exists_fn(device)
    assert descriptions["water_alarm_status"].exists_fn(device)
    assert descriptions["water_alarm_status"].value_fn(device) is False
    assert descriptions["water_mute_status"].exists_fn(device)
    assert descriptions["water_mute_status"].value_fn(device) is False
    assert descriptions["temperature_alarm_status"].exists_fn(device)
    assert descriptions["temperature_alarm_status"].value_fn(device) is True
    assert descriptions["temperature_mute_status"].exists_fn(device)
    assert descriptions["temperature_mute_status"].value_fn(device) is True


def test_generic_mute_payload_uses_single_canonical_silence_entity():
    device = SimpleNamespace(type="SMA51", data={"mute": True})
    descriptions = {description.key: description for description in BINARY_SENSORS}

    assert descriptions["mute_status"].exists_fn(device)
    assert descriptions["mute_status"].value_fn(device) is True
    assert "mute" not in descriptions


def test_empty_canonical_mute_status_falls_back_to_raw_mute_state():
    device = SimpleNamespace(type="SMA51", data={"muteStatus": "", "mute": True})
    descriptions = {description.key: description for description in BINARY_SENSORS}

    assert descriptions["mute_status"].value_fn(device) is True


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


async def test_alarm_panel_uses_strict_arm_before_force_arm_confirmation():
    class Api:
        def __init__(self):
            self.calls = []

        async def set_station_mode(self, station, safe_mode, force_arm=None):
            self.calls.append((station.sn, safe_mode, force_arm))

    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    station.set_devices(
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
    api = Api()
    coordinator = Coordinator(station)
    coordinator.xsense = api
    panel = XSenseAlarmControlPanel(coordinator, station)

    await panel.async_alarm_arm_home()
    await panel.async_alarm_arm_away()

    assert api.calls == [
        (station.sn, "Home", "0"),
        (station.sn, "Away", "0"),
    ]
    assert station.alarm_data["requestedSafeMode"] == "Away"


def test_force_arm_prompt_is_parsed_and_cleared_from_sbs50_notice():
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    api = XSenseBase.__new__(XSenseBase)

    api.parse_get_state(
        station,
        {
            "safeMode": "Disarmed",
            "notices": [
                {
                    "type": "SKP0A",
                    "eventParam": {
                        "safeModeAim": "Home",
                        "forceReason": [{"deviceSN": "door-sn"}],
                        "exitDelay": "0",
                    },
                }
            ],
        },
    )

    assert pending_force_arm_mode(station) == "Home"
    assert station.alarm_data["forceReason"] == [{"deviceSN": "door-sn"}]
    assert station.alarm_data["exitDelay"] == "0"

    api.parse_get_state(station, {"safeMode": "Home"})

    assert pending_force_arm_mode(station) is None
    assert station.alarm_data["forceReason"] is None


def test_force_arm_prompt_preserves_locally_requested_mode_from_apk_response():
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    station.set_alarm_data({"requestedSafeMode": "Away"})
    api = XSenseBase.__new__(XSenseBase)

    api.parse_get_state(
        station,
        {
            "safeMode": "Disarmed",
            "forceReason": [{"deviceSN": "door-sn"}],
            "exitDelay": "0",
        },
    )

    assert pending_force_arm_mode(station) == "Away"
    assert station.alarm_data["requestedSafeMode"] == "Away"


async def test_alarm_panel_force_arm_requires_matching_pending_mode(monkeypatch):
    class Api:
        def __init__(self):
            self.calls = []

        async def set_station_mode(self, station, safe_mode, force_arm=None):
            self.calls.append((station.sn, safe_mode, force_arm))

    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    station.set_alarm_data(
        {
            "forceReason": [{"deviceSN": "door-sn"}],
            "requestedSafeMode": "Away",
        }
    )
    coordinator = Coordinator(station)
    coordinator.xsense = Api()
    panel = XSenseAlarmControlPanel(coordinator, station)
    panel.hass = object()
    panel.async_write_ha_state = lambda: None
    dismissed = []
    monkeypatch.setattr(
        "custom_components.xsense.alarm_control_panel.persistent_notification.async_dismiss",
        lambda hass, notification_id: dismissed.append(notification_id),
    )

    with pytest.raises(Exception):
        await panel.async_force_arm("Home")

    assert coordinator.xsense.calls == []
    await panel.async_force_arm("Away")

    assert coordinator.xsense.calls == [(station.sn, "Away", "1")]
    assert station.alarm_data["forceReason"] is None
    assert station.alarm_data["requestedSafeMode"] is None
    assert dismissed == [f"xsense_force_arm_{station.entity_id}"]

    with pytest.raises(Exception):
        await panel.async_force_arm("Away")
    assert coordinator.xsense.calls == [(station.sn, "Away", "1")]


async def test_alarm_panel_force_arm_now_does_not_require_pending_prompt(monkeypatch):
    """The automation action force arms without first creating a prompt."""

    class API:
        def __init__(self):
            self.calls = []

        async def set_station_mode(self, station, safe_mode, force_arm=None):
            self.calls.append((station.sn, safe_mode, force_arm))

    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    station.set_alarm_data(
        {
            "forceReason": None,
            "safeModeAim": None,
            "requestedSafeMode": None,
        }
    )
    assert pending_force_arm_mode(station) is None
    api = API()
    coordinator = Coordinator(station)
    coordinator.xsense = api
    panel = XSenseAlarmControlPanel(coordinator, station)
    panel.hass = object()
    panel.async_write_ha_state = lambda: None
    dismissed = []
    monkeypatch.setattr(
        "custom_components.xsense.alarm_control_panel.persistent_notification.async_dismiss",
        lambda hass, notification_id: dismissed.append(notification_id),
    )

    await panel.async_force_arm_now("Away")

    assert api.calls == [(station.sn, "Away", "1")]
    assert station.alarm_data["forceReason"] is None
    assert station.alarm_data["requestedSafeMode"] is None
    assert dismissed == [f"xsense_force_arm_{station.entity_id}"]


async def test_alarm_panel_exposes_apk_sos_and_alarm_actions():
    """Security actions use the exact SBS50 APK client commands."""

    class API:
        def __init__(self):
            self.calls = []

        async def trigger_sos(self, station, sos_type="1"):
            self.calls.append(("trigger_sos", station.sn, sos_type))

        async def cancel_sos(self, station):
            self.calls.append(("cancel_sos", station.sn))

        async def cancel_alarm(self, station):
            self.calls.append(("cancel_alarm", station.sn))

        async def set_sos_sound(self, station, sound):
            self.calls.append(("set_sos_sound", station.sn, sound))

    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    api = API()
    coordinator = Coordinator(station)
    coordinator.xsense = api
    panel = XSenseAlarmControlPanel(coordinator, station)

    await panel.async_trigger_sos()
    await panel.async_cancel_sos()
    await panel.async_cancel_alarm()
    await panel.async_set_sos_sound(audible=False)
    await panel.async_set_sos_sound(audible=True)

    assert api.calls == [
        ("trigger_sos", station.sn, "1"),
        ("cancel_sos", station.sn),
        ("cancel_alarm", station.sn),
        ("set_sos_sound", station.sn, "0"),
        ("set_sos_sound", station.sn, "1"),
    ]


async def test_light_group_power_action_uses_apk_group_shadow():
    """The light-group action resolves the SBS50 parent and member serials."""

    class API:
        def __init__(self):
            self.calls = []

        async def set_light_group_power(
            self, station, group_id, device_sns, on
        ):
            self.calls.append((station.sn, group_id, device_sns, on))

    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    station.set_devices(
        {
            "devices": [
                {
                    "deviceId": "light-id",
                    "deviceName": "Porch Light",
                    "deviceSn": "light-sn",
                    "deviceType": "SPL51",
                    "roomName": "Porch",
                }
            ]
        }
    )
    light = station.get_device_by_sn("light-sn")
    api = API()
    coordinator = Coordinator(station, {light.entity_id: light})
    coordinator.xsense = api
    switch = XSenseSwitchEntity(
        coordinator,
        light,
        XSenseSwitchEntityDescription(
            key="light_power",
            data_key="on",
            exists_fn=lambda current: True,
            value_fn=lambda current: False,
        ),
        station_id=station.entity_id,
    )

    await switch.async_set_light_group_power(
        group_id=" group-1 ", device_ids=[" light-sn ", "light-2"], enabled=True
    )

    assert api.calls == [
        (station.sn, "group-1", ["light-sn", "light-2"], True)
    ]
    assert coordinator.update_listener_calls == 1


def test_force_arm_prompt_prefers_locally_requested_home_over_stale_away_target():
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    station.set_alarm_data({"requestedSafeMode": "Home"})
    api = XSenseBase.__new__(XSenseBase)

    api.parse_get_state(
        station,
        {
            "safeMode": "Disarmed",
            "safeModeAim": "Away",
            "forceReason": [{"deviceSN": "door-sn"}],
        },
    )

    assert pending_force_arm_mode(station) == "Home"
    assert station.alarm_data["safeModeAim"] == "Home"


def test_empty_force_arm_reason_clears_pending_request_without_mode_change():
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    station.set_alarm_data(
        {
            "forceReason": [{"deviceSN": "door-sn"}],
            "safeModeAim": "Home",
            "requestedSafeMode": "Home",
        }
    )
    api = XSenseBase.__new__(XSenseBase)

    api.parse_get_state(station, {"forceReason": []})

    assert pending_force_arm_mode(station) is None
    assert station.alarm_data["requestedSafeMode"] is None


def test_force_arm_prompt_creates_and_clears_persistent_notification(monkeypatch):
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    coordinator = Coordinator(station)
    coordinator.entry = type("Entry", (), {"entry_id": "entry-id"})()
    panel = XSenseAlarmControlPanel(coordinator, station)
    panel.entity_id = "alarm_control_panel.base_station_alarm"
    panel.hass = object()
    panel.async_write_ha_state = lambda: None
    created = []
    dismissed = []
    monkeypatch.setattr(
        "custom_components.xsense.alarm_control_panel.persistent_notification.async_create",
        lambda hass, message, title=None, notification_id=None: created.append(
            {
                "hass": hass,
                "message": message,
                "title": title,
                "notification_id": notification_id,
            }
        ),
    )
    monkeypatch.setattr(
        "custom_components.xsense.alarm_control_panel.persistent_notification.async_dismiss",
        lambda hass, notification_id: dismissed.append((hass, notification_id)),
    )

    station.set_alarm_data(
        {"forceReason": [{"deviceSN": "door-sn"}], "safeModeAim": "Away"}
    )
    panel._handle_coordinator_update()

    assert created == [
        {
            "hass": panel.hass,
            "message": (
                "One or more sensors are open.\n\n"
                "[**Force Arm Away**](/xsense-force-arm#"
                "entity_id=alarm_control_panel.base_station_alarm&mode=Away)\n\n"
                "Select the link to confirm the pending X-Sense arm request."
            ),
            "title": "X-Sense arm blocked",
            "notification_id": f"xsense_force_arm_{station.entity_id}",
        }
    ]

    panel._handle_coordinator_update()

    assert len(created) == 1

    station.set_alarm_data({"forceReason": None, "safeModeAim": None})
    panel._handle_coordinator_update()

    assert dismissed == [(panel.hass, f"xsense_force_arm_{station.entity_id}")]
