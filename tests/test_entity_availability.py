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
    CODED_MUTE_STATUS_DEVICE_TYPES,
    COMMAND_ONLY_MUTE_STATUS_DEVICE_TYPES,
    MUTE_STATUS_DEVICE_TYPES,
    SENSORS as BINARY_SENSORS,
    ZERO_CODE_MUTE_STATUS_DEVICE_TYPES,
    XSenseBinarySensorEntity,
    XSenseBinarySensorEntityDescription,
    XSenseMQTTConnectedEntity,
    MQTTSensor,
    data_bool as binary_data_bool,
)
from custom_components.xsense.button import (
    XSenseButtonEntity,
    XSenseButtonEntityDescription,
)
from custom_components.xsense.number import (
    XSenseNumberEntity,
    XSenseNumberEntityDescription,
)
from custom_components.xsense.select import (
    XSenseSelectEntity,
    XSenseSelectEntityDescription,
)
from custom_components.xsense.sensor import (
    XSenseSensorEntity,
    XSenseSensorEntityDescription,
)
from custom_components.xsense.switch import (
    XSenseSwitchEntity,
    XSenseSwitchEntityDescription,
    data_bool as switch_data_bool,
)
from custom_components.xsense.entity import device_station_id
from homeassistant.exceptions import HomeAssistantError


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


def _patch_alarm_call_later(monkeypatch, replacement):
    """Patch the timer global used by the collected entity class."""
    monkeypatch.setitem(
        XSenseAlarmControlPanel._async_start_arm_request_timeout.__globals__,
        "async_call_later",
        replacement,
    )


def _parse_confirmation(station, data):
    XSenseBase.__new__(XSenseBase).parse_get_state(station, data, mode_result="confirmation")
    station._xsense_mode_result = {**data, "kind": "confirmation"}


def _parse_mode(station, data):
    XSenseBase.__new__(XSenseBase).parse_get_state(station, data, mode_result="mode")
    station._xsense_mode_result = {**data, "kind": "mode"}


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


def test_existing_boolean_entities_tolerate_partial_refresh_payloads():
    entity = SimpleNamespace(data={})

    assert binary_data_bool("missing")(entity) is None
    assert switch_data_bool("missing")(entity) is None


@pytest.mark.asyncio
async def test_existing_controls_become_unavailable_when_support_data_disappears():
    station = _xs01_wx_from_real_shadow()
    station.data["temporarySetting"] = 1
    coordinator = Coordinator(station)
    exists = lambda current: "temporarySetting" in current.data

    number = XSenseNumberEntity(
        coordinator,
        station,
        XSenseNumberEntityDescription(
            key="temporary_number",
            data_key="temporarySetting",
            exists_fn=exists,
        ),
    )
    select = XSenseSelectEntity(
        coordinator,
        station,
        XSenseSelectEntityDescription(
            key="temporary_select",
            data_key="temporarySetting",
            fixed_options=("0", "1"),
            exists_fn=exists,
        ),
    )
    switch = XSenseSwitchEntity(
        coordinator,
        station,
        XSenseSwitchEntityDescription(
            key="temporary_switch",
            data_key="temporarySetting",
            exists_fn=exists,
            value_fn=switch_data_bool("temporarySetting"),
        ),
    )
    button = XSenseButtonEntity(
        coordinator,
        station,
        XSenseButtonEntityDescription(
            key="temporary_button",
            exists_fn=lambda current, api: exists(current),
            press_fn=_noop_press,
        ),
    )

    assert number.available
    assert select.available
    assert switch.available
    assert button.available

    station.data.pop("temporarySetting")

    assert not number.available
    assert not select.available
    assert not switch.available
    assert not button.available
    with pytest.raises(HomeAssistantError):
        await number.async_set_native_value(1)
    with pytest.raises(HomeAssistantError):
        await select.async_select_option("1")
    with pytest.raises(HomeAssistantError):
        await switch.async_turn_on()
    with pytest.raises(HomeAssistantError):
        await button.async_press()


@pytest.mark.parametrize(
    ("alarm_status", "mute_status", "silence_time", "expected"),
    (
        (False, "1", "0", False),
        (False, "0", "0", False),
        (True, "1", "0", False),
        (True, "0", "0", True),
        (True, "0", "600", True),
    ),
)
def test_sws51_uses_apk_alarm_and_silence_conditions(
    alarm_status, mute_status, silence_time, expected
):
    """Mirror APK 1400 S1.F for triggered, silenced, and remind-later states."""
    device = SimpleNamespace(
        type="SWS51",
        data={
            "alarmStatus": alarm_status,
            "muteStatus": mute_status,
            "silenceTime": silence_time,
        },
    )
    descriptions = {description.key: description for description in BINARY_SENSORS}

    assert descriptions["alarm_status"].exists_fn(device)
    assert descriptions["alarm_status"].value_fn(device) is alarm_status
    assert "mute" not in descriptions
    assert descriptions["mute_status"].exists_fn(device)
    assert descriptions["mute_status"].value_fn(device) is expected
    assert not descriptions["water_alarm_status"].exists_fn(device)
    assert not descriptions["water_mute_status"].exists_fn(device)
    assert not descriptions["temperature_alarm_status"].exists_fn(device)
    assert not descriptions["temperature_mute_status"].exists_fn(device)


@pytest.mark.parametrize(
    ("model", "alarm_status", "mute_status", "expected"),
    (
        ("XS01-M", True, "0", True),
        ("XS01-M", True, "1", False),
        ("XS01-M", False, "0", False),
        ("SC07-MR", True, "1", True),
        ("SC07-MR", True, "3", True),
        ("SC07-MR", True, "4", False),
        ("SC07-MR", False, "1", False),
    ),
)
def test_apk_detector_families_use_their_own_mute_status_codes(
    model, alarm_status, mute_status, expected
):
    device = SimpleNamespace(
        type=model,
        data={
            "alarmStatus": alarm_status,
            "muteStatus": mute_status,
        },
    )
    description = next(
        item for item in BINARY_SENSORS if item.key == "mute_status"
    )

    assert description.value_fn(device) is expected


def test_apk_mute_status_model_families_are_exhaustive_and_disjoint():
    assert CODED_MUTE_STATUS_DEVICE_TYPES.isdisjoint(
        ZERO_CODE_MUTE_STATUS_DEVICE_TYPES
    )
    assert (
        CODED_MUTE_STATUS_DEVICE_TYPES
        | ZERO_CODE_MUTE_STATUS_DEVICE_TYPES
    ) == MUTE_STATUS_DEVICE_TYPES
    assert COMMAND_ONLY_MUTE_STATUS_DEVICE_TYPES == {"SMA0A", "SMA51"}


def test_vendored_entity_preserves_raw_apk_mute_status_code():
    station = Station(
        House(),
        stationId="station-id",
        stationName="Water Leak Sensor",
        stationSn="SWS51SN",
        category="SWS51",
        online=1,
    )

    station.set_data(
        {
            "status": {
                "alarmStatus": "0",
                "muteStatus": "1",
                "silenceTime": "0",
            }
        }
    )

    assert station.data["muteStatus"] == 1
    description = next(
        item for item in BINARY_SENSORS if item.key == "mute_status"
    )
    assert description.value_fn(station) is False

    station.set_data(
        {"status": {"alarmStatus": "1", "muteStatus": "0", "silenceTime": "0"}}
    )

    assert station.data["muteStatus"] == 0
    assert description.value_fn(station) is True


def test_sws0b_uses_apk_dual_water_and_temperature_states():
    device = SimpleNamespace(
        type="SWS0B",
        data={
            "waterAlarmStatus": False,
            "waterMuteStatus": 0,
            "tempAlarmStatus": True,
            "tempMuteStatus": 1,
        },
    )
    descriptions = {description.key: description for description in BINARY_SENSORS}

    assert descriptions["water_alarm_status"].value_fn(device) is False
    assert descriptions["water_mute_status"].value_fn(device) is False
    assert descriptions["temperature_alarm_status"].value_fn(device) is True
    assert descriptions["temperature_mute_status"].value_fn(device) is True


@pytest.mark.parametrize(
    ("alarm_key", "mute_key", "alarm_status", "mute_status", "expected"),
    (
        ("waterAlarmStatus", "waterMuteStatus", False, 1, False),
        ("waterAlarmStatus", "waterMuteStatus", True, 0, False),
        ("waterAlarmStatus", "waterMuteStatus", True, 1, True),
        ("waterAlarmStatus", "waterMuteStatus", True, 2, True),
        ("tempAlarmStatus", "tempMuteStatus", False, 2, False),
        ("tempAlarmStatus", "tempMuteStatus", True, 1, True),
    ),
)
def test_sws0b_silence_states_require_the_corresponding_active_alarm(
    alarm_key, mute_key, alarm_status, mute_status, expected
):
    device = SimpleNamespace(
        type="SWS0B",
        data={alarm_key: alarm_status, mute_key: mute_status},
    )
    description_key = (
        "water_mute_status"
        if mute_key == "waterMuteStatus"
        else "temperature_mute_status"
    )
    description = next(
        item for item in BINARY_SENSORS if item.key == description_key
    )

    assert description.value_fn(device) is expected


@pytest.mark.parametrize(
    ("model", "unsupported_key"),
    (
        ("SMS01", "alarm_status"),
        ("SDA51", "mute_status"),
        ("STH0A", "mute_status"),
        ("STH0B", "mute_status"),
        ("STH0C", "mute_status"),
        ("STH51", "mute_status"),
        ("SWS0B", "alarm_status"),
        ("SWS0B", "mute_status"),
        ("XR0A-iR", "mute_status"),
    ),
)
def test_apk_view_does_not_create_unsupported_generic_state(
    model, unsupported_key
):
    device = SimpleNamespace(type=model, data={})
    descriptions = {description.key: description for description in BINARY_SENSORS}

    assert not descriptions[unsupported_key].exists_fn(device)


@pytest.mark.parametrize(
    ("model", "key", "description_key"),
    (
        ("SMS01", "alarmStatus", "alarm_status"),
        ("SWS0B", "alarmStatus", "alarm_status"),
        ("STH51", "muteStatus", "mute_status"),
        ("SWS0B", "muteStatus", "mute_status"),
    ),
)
def test_unexpected_cloud_state_remains_payload_gated(model, key, description_key):
    device = SimpleNamespace(type=model, data={key: True})
    descriptions = {description.key: description for description in BINARY_SENSORS}

    assert descriptions[description_key].exists_fn(device)
    assert descriptions[description_key].value_fn(device) is True


def test_mailbox_mute_command_does_not_create_fake_silence_state():
    device = SimpleNamespace(type="SMA51", data={"mute": True})
    descriptions = {description.key: description for description in BINARY_SENSORS}

    assert not descriptions["mute_status"].exists_fn(device)
    assert "mute" not in descriptions


def test_empty_canonical_mute_status_falls_back_to_raw_mute_state():
    device = SimpleNamespace(type="UNKNOWN", data={"muteStatus": "", "mute": True})
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


async def test_alarm_panel_ignores_overlapping_normal_arm_requests_like_apk(monkeypatch):
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
    panel.hass = object()
    _patch_alarm_call_later(
        monkeypatch, lambda hass, delay, action: lambda: None
    )
    monkeypatch.setattr(
        "custom_components.xsense.alarm_control_panel.persistent_notification.async_dismiss",
        lambda hass, notification_id: None,
    )

    await panel.async_alarm_arm_home()
    await panel.async_alarm_arm_away()

    assert api.calls == [
        (station.sn, "Home", "0"),
    ]
    assert station.alarm_data["requestedSafeMode"] == "Home"


async def test_normal_arm_clears_stale_bypass_state_before_publish(monkeypatch):
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    station.set_alarm_data(
        {
            "forceReason": [{"door-sn": "1"}],
            "safeModeAim": "Home",
            "requestedSafeMode": None,
            "exitDelay": "0",
        }
    )
    state_during_publish = []

    class API:
        async def set_station_mode(self, station, safe_mode, force_arm=None):
            state_during_publish.append(dict(station.alarm_data))

    coordinator = Coordinator(station)
    coordinator.xsense = API()
    panel = XSenseAlarmControlPanel(coordinator, station)
    panel.hass = object()
    _patch_alarm_call_later(
        monkeypatch, lambda hass, delay, action: lambda: None
    )
    monkeypatch.setattr(
        "custom_components.xsense.alarm_control_panel.persistent_notification.async_dismiss",
        lambda hass, notification_id: None,
    )

    await panel.async_alarm_arm_home()

    assert state_during_publish == [
        {
            "forceReason": None,
            "safeModeAim": None,
            "requestedSafeMode": "Home",
            "exitDelay": None,
        }
    ]


async def test_normal_arm_request_expires_after_apk_timeout(monkeypatch):
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    callbacks = []
    cancelled = []

    class API:
        async def set_station_mode(self, station, safe_mode, force_arm=None):
            return None

    def schedule(hass, delay, action):
        callbacks.append((delay, action))

        def cancel():
            cancelled.append(True)

        return cancel

    coordinator = Coordinator(station)
    coordinator.xsense = API()
    panel = XSenseAlarmControlPanel(coordinator, station)
    panel.hass = object()
    panel.async_write_ha_state = lambda: None
    dismissed = []
    _patch_alarm_call_later(monkeypatch, schedule)
    monkeypatch.setattr(
        "custom_components.xsense.alarm_control_panel.persistent_notification.async_dismiss",
        lambda hass, notification_id: dismissed.append(notification_id),
    )

    await panel.async_alarm_arm_away()
    assert callbacks[0][0] == 60
    assert station.alarm_data["requestedSafeMode"] == "Away"

    callbacks[0][1](None)

    assert station.alarm_data["requestedSafeMode"] is None
    assert station.alarm_data["forceReason"] is None
    assert panel._cancel_arm_request_timeout is None
    assert dismissed == [
        f"xsense_force_arm_{station.entity_id}",
        f"xsense_force_arm_{station.entity_id}",
    ]
    assert cancelled == []


async def test_force_arm_prompt_stops_request_timeout(monkeypatch):
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    cancelled = []

    class API:
        async def set_station_mode(self, station, safe_mode, force_arm=None):
            return None

    coordinator = Coordinator(station)
    coordinator.xsense = API()
    panel = XSenseAlarmControlPanel(coordinator, station)
    panel.hass = object()
    panel.async_write_ha_state = lambda: None
    _patch_alarm_call_later(
        monkeypatch, lambda hass, delay, action: lambda: cancelled.append(True)
    )
    monkeypatch.setattr(
        "custom_components.xsense.alarm_control_panel.persistent_notification.async_create",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "custom_components.xsense.alarm_control_panel.persistent_notification.async_dismiss",
        lambda hass, notification_id: None,
    )

    await panel.async_alarm_arm_home()
    _parse_confirmation(
        station,
        {
            "safeMode": "Disarmed",
            "forceReason": [{"door-sn": "1"}],
            "exitDelay": "0",
        },
    )
    panel._handle_coordinator_update()

    assert cancelled == [True]
    assert panel._cancel_arm_request_timeout is None
    assert pending_force_arm_mode(station) == "Home"


@pytest.mark.parametrize("requested_mode", ["Home", "Away"])
async def test_blocked_arm_prompt_survives_empty_acknowledgement_end_to_end(
    monkeypatch, requested_mode
):
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    calls = []
    cancelled = []
    created = []

    class API:
        async def set_station_mode(self, station, safe_mode, force_arm=None):
            calls.append((safe_mode, force_arm))

    coordinator = Coordinator(station)
    coordinator.xsense = API()
    panel = XSenseAlarmControlPanel(coordinator, station)
    panel.entity_id = "alarm_control_panel.base_station_alarm"
    panel.hass = object()
    panel.async_write_ha_state = lambda: None
    _patch_alarm_call_later(
        monkeypatch, lambda hass, delay, action: lambda: cancelled.append(True)
    )
    monkeypatch.setattr(
        "custom_components.xsense.alarm_control_panel.persistent_notification.async_create",
        lambda hass, message, title=None, notification_id=None: created.append(
            (message, title, notification_id)
        ),
    )
    monkeypatch.setattr(
        "custom_components.xsense.alarm_control_panel.persistent_notification.async_dismiss",
        lambda hass, notification_id: None,
    )

    if requested_mode == "Home":
        await panel.async_alarm_arm_home()
    else:
        await panel.async_alarm_arm_away()

    api = XSenseBase.__new__(XSenseBase)
    _parse_confirmation(
        station,
        {"safeMode": "Disarmed", "forceReason": []},
    )
    panel._handle_coordinator_update()

    assert calls == [(requested_mode, "0")]
    assert station.alarm_data["requestedSafeMode"] == requested_mode
    assert panel._cancel_arm_request_timeout is not None
    assert created == []

    _parse_confirmation(
        station,
        {
            "safeMode": "Disarmed",
            "forceReason": [{"deviceSN": "door-sn"}],
            "exitDelay": "0",
        },
    )
    panel._handle_coordinator_update()

    assert pending_force_arm_mode(station) == requested_mode
    assert panel._cancel_arm_request_timeout is None
    assert cancelled == [True]
    assert len(created) == 1
    assert f"mode={requested_mode}" in created[0][0]

    _parse_confirmation(station, {"safeMode": "Disarmed", "forceReason": []})
    panel._handle_coordinator_update()

    assert pending_force_arm_mode(station) == requested_mode
    assert len(created) == 1

    await panel.async_force_arm(requested_mode)

    assert calls == [(requested_mode, "0"), (requested_mode, "1")]
    assert pending_force_arm_mode(station) is None


@pytest.mark.parametrize("requested_mode", ["Home", "Away"])
@pytest.mark.parametrize("reported_mode", ["Disarmed", "requested"])
async def test_blocked_arm_prompt_survives_station_object_refresh(
    monkeypatch, requested_mode, reported_mode
):
    """Keep the APK presenter request while discovery replaces its Station."""
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    cancelled = []
    created = []

    class API:
        async def set_station_mode(self, station, safe_mode, force_arm=None):
            return None

    coordinator = Coordinator(station)
    coordinator.xsense = API()
    panel = XSenseAlarmControlPanel(coordinator, station)
    panel.entity_id = "alarm_control_panel.base_station_alarm"
    panel.hass = object()
    panel.async_write_ha_state = lambda: None
    _patch_alarm_call_later(
        monkeypatch, lambda hass, delay, action: lambda: cancelled.append(True)
    )
    monkeypatch.setattr(
        "custom_components.xsense.alarm_control_panel.persistent_notification.async_create",
        lambda hass, message, title=None, notification_id=None: created.append(
            (message, title, notification_id)
        ),
    )
    monkeypatch.setattr(
        "custom_components.xsense.alarm_control_panel.persistent_notification.async_dismiss",
        lambda hass, notification_id: None,
    )

    if requested_mode == "Home":
        await panel.async_alarm_arm_home()
    else:
        await panel.async_alarm_arm_away()

    refreshed = _xs01_wx_from_real_shadow()
    refreshed.type = "SBS50"
    XSenseBase.__new__(XSenseBase).parse_get_state(
        refreshed,
        {
            "safeMode": (
                requested_mode if reported_mode == "requested" else reported_mode
            ),
            "forceReason": [{"deviceSN": "door-sn"}],
            "exitDelay": "0",
        },
    )
    coordinator.data["stations"][station.entity_id] = refreshed

    panel._handle_coordinator_update()

    # Refresh payloads, including a matching mode, do not impersonate either
    # MQTT listener. The local request survives until a real result or timeout.
    assert pending_force_arm_mode(refreshed) is None
    assert panel._active_normal_arm_mode == requested_mode
    assert panel._cancel_arm_request_timeout is not None
    assert cancelled == []
    assert created == []


async def test_visible_force_arm_prompt_survives_station_object_refresh(monkeypatch):
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    created = []
    dismissed = []

    class API:
        async def set_station_mode(self, station, safe_mode, force_arm=None):
            return None

    coordinator = Coordinator(station)
    coordinator.xsense = API()
    panel = XSenseAlarmControlPanel(coordinator, station)
    panel.entity_id = "alarm_control_panel.base_station_alarm"
    panel.hass = object()
    panel.async_write_ha_state = lambda: None
    _patch_alarm_call_later(monkeypatch, lambda hass, delay, action: lambda: None)
    monkeypatch.setattr(
        "custom_components.xsense.alarm_control_panel.persistent_notification.async_create",
        lambda hass, message, title=None, notification_id=None: created.append(
            notification_id
        ),
    )
    monkeypatch.setattr(
        "custom_components.xsense.alarm_control_panel.persistent_notification.async_dismiss",
        lambda hass, notification_id: dismissed.append(notification_id),
    )

    await panel.async_alarm_arm_home()
    _parse_confirmation(
        station,
        {
            "safeMode": "Disarmed",
            "forceReason": [{"deviceSN": "door-sn"}],
            "exitDelay": "0",
        },
    )
    panel._handle_coordinator_update()
    dismiss_count_after_prompt = len(dismissed)

    refreshed = _xs01_wx_from_real_shadow()
    refreshed.type = "SBS50"
    coordinator.data["stations"][station.entity_id] = refreshed
    panel._handle_coordinator_update()

    assert pending_force_arm_mode(refreshed) == "Home"
    assert refreshed.alarm_data["forceReason"] == [{"deviceSN": "door-sn"}]
    assert panel._pending_force_arm_mode == "Home"
    assert panel._active_normal_arm_mode is None
    assert len(created) == 1
    assert len(dismissed) == dismiss_count_after_prompt


async def test_normal_arm_success_clears_request_after_station_object_refresh(
    monkeypatch,
):
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    cancelled = []

    class API:
        async def set_station_mode(self, station, safe_mode, force_arm=None):
            return None

    coordinator = Coordinator(station)
    coordinator.xsense = API()
    panel = XSenseAlarmControlPanel(coordinator, station)
    panel.hass = object()
    panel.async_write_ha_state = lambda: None
    _patch_alarm_call_later(
        monkeypatch, lambda hass, delay, action: lambda: cancelled.append(True)
    )
    monkeypatch.setattr(
        "custom_components.xsense.alarm_control_panel.persistent_notification.async_dismiss",
        lambda hass, notification_id: None,
    )

    await panel.async_alarm_arm_away()

    refreshed = _xs01_wx_from_real_shadow()
    refreshed.type = "SBS50"
    refreshed.safe_mode = "Away"
    refreshed.set_alarm_data({"safeMode": "Away"})
    _parse_mode(refreshed, {"safeMode": "Away"})
    coordinator.data["stations"][station.entity_id] = refreshed

    panel._handle_coordinator_update()

    assert panel._active_normal_arm_mode is None
    assert panel._cancel_arm_request_timeout is None
    assert pending_force_arm_mode(refreshed) is None
    assert refreshed.alarm_data.get("requestedSafeMode") is None
    assert cancelled == [True]


async def test_normal_arm_is_noop_when_station_already_reports_target_mode(
    monkeypatch,
):
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    station.safe_mode = "Home"
    calls = []

    class API:
        async def set_station_mode(self, station, safe_mode, force_arm=None):
            calls.append((safe_mode, force_arm))

    coordinator = Coordinator(station)
    coordinator.xsense = API()
    panel = XSenseAlarmControlPanel(coordinator, station)
    panel.hass = object()
    monkeypatch.setattr(
        "custom_components.xsense.alarm_control_panel.persistent_notification.async_dismiss",
        lambda hass, notification_id: None,
    )

    await panel.async_alarm_arm_home()

    assert calls == []
    assert station.alarm_data.get("requestedSafeMode") is None


@pytest.mark.parametrize("target", ["Home", "Away"])
@pytest.mark.parametrize("old_field", ["mode", "safeMode"])
async def test_rearm_uses_current_report_not_old_alarm_snapshot(monkeypatch, target, old_field):
    from unittest.mock import AsyncMock

    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    station.set_alarm_data({old_field: target})
    api = XSenseBase.__new__(XSenseBase)
    api.parse_get_state(station, {"safeMode": "Disarmed"}, mode_result="mode")
    api.set_station_mode = AsyncMock()
    coordinator = Coordinator(station)
    coordinator.xsense = api
    panel = XSenseAlarmControlPanel(coordinator, station)
    panel._async_clear_force_arm_notification = lambda: None
    panel._async_start_arm_request_timeout = lambda: None

    await panel._set_safe_mode(target, force_arm="0")

    api.set_station_mode.assert_awaited_once_with(station, target, force_arm="0")
    assert panel._active_normal_arm_mode == target


@pytest.mark.parametrize("target", ["Home", "Away"])
@pytest.mark.parametrize("reported", ["Home", "Away", "Disarmed"])
def test_actual_mode_result_preserves_open_apk_confirmation(target, reported):
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    coordinator = Coordinator(station)
    panel = XSenseAlarmControlPanel(coordinator, station)
    dismissed = []
    panel._async_clear_force_arm_notification = lambda: dismissed.append(True)
    panel.async_write_ha_state = lambda: None
    panel._pending_force_arm_mode = target
    panel._pending_force_arm_data = {
        "requestedSafeMode": target, "forceReason": [{"deviceSN": "door-sn"}]
    }
    station.set_alarm_data(panel._pending_force_arm_data)
    _parse_mode(station, {"safeMode": reported})

    panel._handle_coordinator_update()

    assert panel._pending_force_arm_mode == target
    assert panel._pending_force_arm_data is not None
    assert station.alarm_data["requestedSafeMode"] == target
    assert station.alarm_data["forceReason"] == [{"deviceSN": "door-sn"}]
    assert not dismissed


@pytest.mark.parametrize("target", ["Home", "Away"])
async def test_repeated_normal_and_force_arm_cycles(target):
    from unittest.mock import AsyncMock

    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    api = XSenseBase.__new__(XSenseBase)
    api.set_station_mode = AsyncMock()
    coordinator = Coordinator(station)
    coordinator.xsense = api
    panel = XSenseAlarmControlPanel(coordinator, station)
    prompts = []
    panel._async_clear_force_arm_notification = lambda: None
    panel._async_create_force_arm_notification = lambda station, mode: prompts.append(mode)
    panel._async_start_arm_request_timeout = lambda: None
    panel.async_write_ha_state = lambda: None

    for _ in range(3):
        _parse_mode(station, {"safeMode": "Disarmed"})
        panel._handle_coordinator_update()
        del station._xsense_mode_result
        station.set_alarm_data({"safeMode": target})
        await panel._set_safe_mode(target, force_arm="0")
        _parse_confirmation(station, {"safeMode": target, "forceReason": []})
        panel._handle_coordinator_update()
        assert panel._pending_force_arm_mode is None
        assert panel._active_normal_arm_mode == target
        _parse_confirmation(station, {"forceReason": [{"deviceSN": "door-sn"}]})
        panel._handle_coordinator_update()
        assert panel._pending_force_arm_mode == target
        del station._xsense_mode_result
        await panel.async_force_arm(target)
        assert panel._pending_force_arm_mode is None
        _parse_confirmation(station, {"forceReason": [{"deviceSN": "door-sn"}]})
        panel._handle_coordinator_update()
        assert panel._pending_force_arm_mode is None
        _parse_mode(station, {"safeMode": target})
        panel._handle_coordinator_update()
        assert panel._safemode == target
        with pytest.raises(Exception):
            await panel.async_force_arm(target)

    assert prompts == [target] * 3
    assert [call.kwargs["force_arm"] for call in api.set_station_mode.await_args_list] == ["0", "1"] * 3


@pytest.mark.parametrize("action", ["Home", "Away", "Disarmed", "already_armed", "force"])
@pytest.mark.parametrize("publish_fails", [False, True])
async def test_arm_actions_publish_cleared_pending_attributes(action, publish_fails):
    from homeassistant.exceptions import HomeAssistantError

    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    station.safe_mode = "Home" if action == "already_armed" else "Disarmed"
    writes = []
    calls = []

    class API:
        async def set_station_mode(self, station, safe_mode, force_arm=None):
            # HA must see prompt removal even while the network call is pending.
            assert writes and writes[-1] is None
            calls.append((safe_mode, force_arm))
            if publish_fails:
                raise RuntimeError("simulated publish failure")

    coordinator = Coordinator(station)
    coordinator.xsense = API()
    panel = XSenseAlarmControlPanel(coordinator, station)
    panel._safemode = station.safe_mode
    panel._pending_force_arm_mode = "Away"
    panel._pending_force_arm_data = {
        "requestedSafeMode": "Away", "forceReason": [{"deviceSN": "door-sn"}]
    }
    station.set_alarm_data(panel._pending_force_arm_data)
    panel._async_clear_force_arm_notification = lambda: None
    panel._async_start_arm_request_timeout = lambda: None
    panel.async_write_ha_state = lambda: writes.append(panel.extra_state_attributes)

    async def invoke():
        if action == "force":
            await panel.async_force_arm("Away")
        else:
            await panel._set_safe_mode(
                "Home" if action == "already_armed" else action, force_arm="0"
            )

    if publish_fails and action != "already_armed":
        with pytest.raises(HomeAssistantError):
            await invoke()
    else:
        await invoke()

    assert writes and writes[-1] is None
    assert panel.extra_state_attributes is None
    assert panel._safemode == station.safe_mode
    assert len(calls) == (0 if action == "already_armed" else 1)


async def test_alarm_panel_unload_cancels_request_timeout(monkeypatch):
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    cancelled = []

    class API:
        async def set_station_mode(self, station, safe_mode, force_arm=None):
            return None

    async def super_remove(self):
        return None

    coordinator = Coordinator(station)
    coordinator.xsense = API()
    panel = XSenseAlarmControlPanel(coordinator, station)
    panel.hass = object()
    _patch_alarm_call_later(
        monkeypatch, lambda hass, delay, action: lambda: cancelled.append(True)
    )
    monkeypatch.setattr(
        "custom_components.xsense.alarm_control_panel.persistent_notification.async_dismiss",
        lambda hass, notification_id: None,
    )
    monkeypatch.setattr(
        "homeassistant.helpers.update_coordinator.CoordinatorEntity.async_will_remove_from_hass",
        super_remove,
    )

    await panel.async_alarm_arm_home()
    await panel.async_will_remove_from_hass()

    assert cancelled == [True]


def test_force_arm_prompt_is_parsed_and_cleared_from_sbs50_mode_result():
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    station.set_alarm_data({"requestedSafeMode": "Home"})
    api = XSenseBase.__new__(XSenseBase)

    _parse_confirmation(
        station,
        {
            "safeMode": "Disarmed",
            "safeModeAim": "Home",
            "forceReason": [{"deviceSN": "door-sn"}],
            "exitDelay": "0",
        },
    )

    assert pending_force_arm_mode(station) == "Home"
    assert station.alarm_data["forceReason"] == [{"deviceSN": "door-sn"}]
    assert station.alarm_data["exitDelay"] == "0"

    _parse_mode(station, {"safeMode": "Home"})

    assert pending_force_arm_mode(station) is None
    assert station.alarm_data["forceReason"] is None


def test_force_arm_prompt_preserves_locally_requested_mode_from_apk_response():
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    station.set_alarm_data({"requestedSafeMode": "Away"})
    api = XSenseBase.__new__(XSenseBase)

    _parse_confirmation(
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
    panel._pending_force_arm_mode = "Away"
    panel._pending_force_arm_data = dict(station.alarm_data)
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


async def test_force_arm_now_clears_prompt_before_sending_command(monkeypatch):
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    station.set_alarm_data(
        {
            "forceReason": [{"deviceSN": "door-sn"}],
            "safeModeAim": "Away",
            "requestedSafeMode": "Away",
        }
    )
    states_during_call = []

    class API:
        async def set_station_mode(self, station, safe_mode, force_arm=None):
            states_during_call.append(pending_force_arm_mode(station))

    coordinator = Coordinator(station)
    coordinator.xsense = API()
    panel = XSenseAlarmControlPanel(coordinator, station)
    panel.hass = object()
    panel.async_write_ha_state = lambda: None
    monkeypatch.setattr(
        "custom_components.xsense.alarm_control_panel.persistent_notification.async_dismiss",
        lambda hass, notification_id: None,
    )

    await panel.async_force_arm_now("Away")

    assert states_during_call == [None]


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


def test_mode_result_keeps_request_target_out_of_adapter_payload_state():
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    station.set_alarm_data({"requestedSafeMode": "Home"})
    api = XSenseBase.__new__(XSenseBase)

    _parse_confirmation(
        station,
        {
            "safeMode": "Disarmed",
            "safeModeAim": "Away",
            "forceReason": [{"deviceSN": "door-sn"}],
        },
    )

    assert pending_force_arm_mode(station) == "Home"
    assert "safeModeAim" not in station.alarm_data


def test_force_arm_result_is_retained_but_not_exposed_without_local_request():
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    api = XSenseBase.__new__(XSenseBase)

    _parse_confirmation(
        station,
        {
            "safeMode": "Disarmed",
            "safeModeAim": "Away",
            "forceReason": [{"deviceSN": "door-sn"}],
        },
    )

    assert pending_force_arm_mode(station) is None
    assert station.alarm_data["forceReason"] == [{"deviceSN": "door-sn"}]
    assert station.alarm_data.get("requestedSafeMode") is None


def test_keypad_notice_does_not_create_force_arm_prompt():
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    station.set_alarm_data({"requestedSafeMode": "Away"})
    api = XSenseBase.__new__(XSenseBase)

    api.parse_get_state(
        station,
        {
            "safeMode": "Disarmed",
            "notices": [
                {
                    "type": "SKP0A",
                    "eventParam": {
                        "safeModeAim": "Away",
                        "forceReason": [{"deviceSN": "door-sn"}],
                        "exitDelay": "0",
                    },
                }
            ],
        },
    )

    assert pending_force_arm_mode(station) is None
    assert station.alarm_data.get("forceReason") is None


def test_unscoped_notice_does_not_create_force_arm_prompt():
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    station.set_alarm_data({"requestedSafeMode": "Home"})
    api = XSenseBase.__new__(XSenseBase)

    api.parse_get_state(
        station,
        {
            "safeMode": "Disarmed",
            "notices": [
                {
                    "type": "SKP0A",
                    "eventParam": {
                        "forceReason": [{"deviceSN": "door-sn"}],
                        "exitDelay": "0",
                    },
                }
            ],
        },
    )

    assert pending_force_arm_mode(station) is None
    assert station.alarm_data.get("forceReason") is None


def test_force_arm_prompt_ignores_notice_for_different_local_request():
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    station.set_alarm_data({"requestedSafeMode": "Home"})
    api = XSenseBase.__new__(XSenseBase)

    api.parse_get_state(
        station,
        {
            "safeMode": "Disarmed",
            "notices": [
                {
                    "type": "SKP0A",
                    "eventParam": {
                        "safeModeAim": "Away",
                        "forceReason": [{"deviceSN": "old-door-sn"}],
                    },
                }
            ],
        },
    )

    assert pending_force_arm_mode(station) is None
    assert station.alarm_data.get("forceReason") is None
    assert station.alarm_data["requestedSafeMode"] == "Home"


def test_empty_force_reason_ack_keeps_normal_arm_request_for_blocked_result():
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    station.set_alarm_data({"requestedSafeMode": "Away"})
    api = XSenseBase.__new__(XSenseBase)

    _parse_confirmation(
        station,
        {
            "safeMode": "Disarmed",
            "forceReason": [],
        },
    )

    assert pending_force_arm_mode(station) is None
    assert station.alarm_data["requestedSafeMode"] == "Away"

    _parse_confirmation(
        station,
        {
            "safeMode": "Disarmed",
            "forceReason": [{"deviceSN": "door-sn"}],
            "exitDelay": "0",
        },
    )

    assert pending_force_arm_mode(station) == "Away"
    assert station.alarm_data["forceReason"] == [{"deviceSN": "door-sn"}]


def test_force_arm_prompt_does_not_return_after_request_is_cleared():
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    station.set_alarm_data(
        {
            "requestedSafeMode": None,
            "safeModeAim": None,
            "forceReason": None,
        }
    )
    api = XSenseBase.__new__(XSenseBase)

    api.parse_get_state(
        station,
        {
            "safeMode": "Disarmed",
            "notices": [
                {
                    "type": "SDS0A",
                    "eventParam": {
                        "safeModeAim": "Away",
                        "forceReason": [{"deviceSN": "door-sn"}],
                    },
                }
            ],
        },
    )

    assert pending_force_arm_mode(station) is None
    assert station.alarm_data["forceReason"] is None
    assert station.alarm_data.get("requestedSafeMode") is None


def test_safemode_topic_completes_request_without_opening_confirmation(monkeypatch):
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    coordinator = Coordinator(station)
    panel = XSenseAlarmControlPanel(coordinator, station)
    panel.hass = object()
    panel.async_write_ha_state = lambda: None
    panel._active_normal_arm_mode = "Home"
    panel._cancel_arm_request_timeout = lambda: None
    monkeypatch.setattr(
        "custom_components.xsense.alarm_control_panel.persistent_notification.async_dismiss",
        lambda hass, notification_id: None,
    )

    _parse_mode(
        station,
        {
            "safeMode": "Home",
            "forceReason": [{"deviceSN": "door-sn"}],
        },
    )
    panel._handle_coordinator_update()

    assert panel._active_normal_arm_mode is None
    assert panel._pending_force_arm_mode is None
    assert pending_force_arm_mode(station) is None


def test_empty_force_arm_reason_does_not_dismiss_visible_prompt(monkeypatch):
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    station.set_alarm_data(
        {
            "forceReason": [{"deviceSN": "door-sn"}],
            "safeModeAim": "Home",
            "requestedSafeMode": "Home",
        }
    )
    coordinator = Coordinator(station)
    panel = XSenseAlarmControlPanel(coordinator, station)
    panel.hass = object()
    panel.async_write_ha_state = lambda: None
    panel._pending_force_arm_mode = "Home"
    panel._pending_force_arm_data = dict(station.alarm_data)
    monkeypatch.setattr(
        "custom_components.xsense.alarm_control_panel.persistent_notification.async_dismiss",
        lambda hass, notification_id: None,
    )

    XSenseBase.__new__(XSenseBase).parse_get_state(station, {"forceReason": []})
    panel._handle_coordinator_update()

    assert pending_force_arm_mode(station) == "Home"
    assert station.alarm_data["forceReason"] == [{"deviceSN": "door-sn"}]


def test_force_arm_prompt_creates_and_clears_persistent_notification(monkeypatch):
    station = _xs01_wx_from_real_shadow()
    station.type = "SBS50"
    coordinator = Coordinator(station)
    coordinator.entry = type("Entry", (), {"entry_id": "entry-id"})()
    panel = XSenseAlarmControlPanel(coordinator, station)
    panel.entity_id = "alarm_control_panel.base_station_alarm"
    panel.hass = object()
    panel.async_write_ha_state = lambda: None
    panel._active_normal_arm_mode = "Away"
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

    _parse_confirmation(station, {"forceReason": [{"door-sn": "1"}]})
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

    panel._async_clear_arm_request(station)

    assert dismissed == [(panel.hass, f"xsense_force_arm_{station.entity_id}")]
