"""Verify the read-only model mappings from X-Sense APK build 7358."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.exceptions import HomeAssistantError

from custom_components.xsense.alarm_control_panel import station_supports_alarm_panel
from custom_components.xsense.binary_sensor import SENSORS, alarm_device_class
from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator
from custom_components.xsense.number import NUMBERS
from custom_components.xsense.python_xsense.async_xsense import (
    AsyncXSense,
    _station_state_shadow_names,
)
from custom_components.xsense.python_xsense.base import XSenseBase
from custom_components.xsense.python_xsense.entity_map import EntityType, entities
from custom_components.xsense.python_xsense.exceptions import APIFailure, XSenseError
from custom_components.xsense.python_xsense.station import Station
from custom_components.xsense.select import SELECTS, shadow_select_options
from custom_components.xsense.sensor import SENSORS as NUMERIC_SENSORS
from custom_components.xsense.switch import SWITCHES


@pytest.mark.asyncio
async def test_paired_schedule_uses_child_request_and_only_matching_mqtt_confirmation():
    house = SimpleNamespace(
        house_id="home", mqtt_server="test-broker", room_name=lambda room: None,
    )
    station = Station(house, category="SBS50", stationId="hub", stationSn="1234ABCD")
    station.set_data({"zoneName": "Europe/Berlin", "timeZoneValid": "1"})
    station.set_devices({"devices": [
        {"deviceType": "XS0AD-MN", "deviceId": "child", "deviceSn": "00000001"},
        {"deviceType": "XS0AD-MN", "deviceId": "other", "deviceSn": "00000002"},
    ]})
    child = station.get_device_by_sn("00000001")
    other = station.get_device_by_sn("00000002")
    original = {"stationId": "hub", "deviceId": "child", "isEnable": "0",
                "startTime": "2100", "endTime": "0700", "weekDays": ["1"]}
    client = object.__new__(AsyncXSense)
    client.api_call = AsyncMock(return_value=[original])
    await client.refresh_paired_night_schedules(station)
    client.api_call.assert_awaited_once_with("406002", stationId="hub", deviceIds=["child", "other"])
    assert child.data["pairedNightMode"] == original
    assert other.data["pairedNightMode"] is None

    listener = None
    unsubscribe = Mock()
    requested = asyncio.Event()

    async def subscribe(topic, callback, qos, *, encoding):
        nonlocal listener
        assert topic == "@xsense/events/house/home"
        listener = callback
        return unsubscribe

    def report(device_id, request_id, *, retained=False):
        listener(SimpleNamespace(payload=json.dumps({
            "eventType": "nightMode",
            "eventData": json.dumps({
                "stationId": "hub", "deviceId": device_id, "requestId": request_id,
            }),
        }), retain=retained))

    async def write(code, **payload):
        assert code == "406001"
        assert payload == {
            "stationId": "hub", "deviceId": "child", "isEnable": "1",
            "timeZone": "Europe/Berlin", "startTime": "2200", "endTime": "0700",
            "weekDays": ["1", "3"], "newTimeZoneMode": "1",
        }
        report("other", "new")
        report("child", "new", retained=True)
        report("child", "old")
        requested.set()
        return {"requestId": "new"}

    client.api_call = AsyncMock(side_effect=write)
    mqtt = SimpleNamespace(connected=True, async_subscribe=subscribe)
    coordinator = SimpleNamespace(
        _pending_paired_schedules=set(), mqtt_server=lambda host: mqtt,
        xsense=client, async_update_listeners=Mock(),
    )
    schedule = {"startTime": "2200", "endTime": "0700", "weekDays": ["1", "3"]}
    update = XSenseDataUpdateCoordinator.async_set_paired_night_schedule
    task = asyncio.create_task(update(coordinator, child, True, "UTC", schedule))
    try:
        await asyncio.wait_for(requested.wait(), 1)
        assert not task.done()
        assert child.data["pairedNightMode"] == original
        report("child", "new")
        await asyncio.wait_for(task, 1)
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    assert child.data["pairedNightMode"] == {**schedule, "isEnable": "1"}
    assert other.data["pairedNightMode"] is None
    unsubscribe.assert_called_once()
    coordinator.async_update_listeners.assert_called_once()
    assert not coordinator._pending_paired_schedules


@pytest.mark.parametrize(
    ("online", "warning", "alarm", "mute", "expected"),
    [
        ("1", "1", "0", "0", True),
        ("1", "0", "0", "0", False),
        ("0", "1", "0", "0", False),
        ("1", "1", "2", "5", False),
        ("1", "1", "4", "8", False),
        ("1", "1", "4", "7", True),
        ("1", "1", "5", "7", False),
        ("1", "1", "1", "4", False),
        ("1", "1", "3", "6", False),
        ("1", "invalid", "0", "0", None),
    ],
)
def test_xcg_low_co_indicator_uses_report_not_warning_preference(
    online, warning, alarm, mute, expected
):
    station = Station(None, category="XCG0A-iA", stationId="gas", stationSn="1234ABCD")
    sensor = next(item for item in SENSORS if item.key == "low_co_warning")
    switch = next(item for item in SWITCHES if item.key == "warning_enabled")
    number = next(item for item in NUMBERS if item.key == "warning_period")
    station.set_data({"warnIsOpen": "1", "warnPeriod": "24"})
    assert not sensor.exists_fn(station)
    assert not switch.exists_fn(station)
    assert not number.exists_fn(station)
    client = object.__new__(XSenseBase)
    client.parse_get_state(station, {
        "online": online, "warnLong": warning, "warnIsOpen": "0",
        "status": {"alarmStatus": alarm, "muteStatus": mute},
    })
    assert sensor.exists_fn(station)
    assert sensor.value_fn(station) is expected
    legacy = Station(None, category="XC04-WX", stationId="co", stationSn="1234ABCE")
    legacy.set_data({"warnLong": "1", "warnIsOpen": "1", "warnPeriod": "24"})
    assert not sensor.exists_fn(legacy)
    assert switch.exists_fn(legacy)
    assert number.exists_fn(legacy)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("model", "serial", "allowed"),
    [
        ("XS0AD-MN", "EN123456", True), ("XS0AD-MN", "31234567", True),
        ("XS0AD-MN", "UL123456", False), ("XS0AD-MN", "21234567", False),
        ("XS0AE-iA", "EN123456", True), ("XS0AE-iA", "UL123456", False),
        ("XS0AE-iA", "12EN3456", False), ("XCG0A-iA", "EN123456", True),
        ("XCG0A-iA", "UL123456", False), ("XCG0A-iA", "12345678", False),
    ],
)
async def test_remote_mute_only_sends_for_apk_proximity_exemption(model, serial, allowed):
    paired = model == "XS0AD-MN"
    station = Station(None, category="SBS50" if paired else model, stationId="hub", stationSn=serial)
    if paired:
        station.set_devices({"devices": [
            {"deviceType": model, "deviceId": "child", "deviceSn": "00000001"},
        ]})
    entity = station.get_device_by_sn("00000001") if paired else station
    entity.set_data({"standard": "1", "coPpm": 42})
    client = object.__new__(AsyncXSense)
    client.userid = "user-id"
    client.do_thing = AsyncMock()
    assert client.has_action(entity, "mute") is allowed
    if not allowed:
        with pytest.raises(XSenseError, match="not supported"):
            await client.action(entity, "mute")
        client.do_thing.assert_not_called()
        return
    await client.action(entity, "mute")
    target, topic, payload = client.do_thing.await_args.args
    assert target.shadow_name == (f"SBS50{serial}" if paired else f"{model}-{serial}")
    assert topic == "2nd_appmute"
    assert payload == {"state": {"desired": {
        "shadow": "appMute", "stationSN": serial, "deviceSN": entity.sn,
        "muteType": "0", "userId": "user-id",
    }}}


@pytest.mark.asyncio
@pytest.mark.parametrize(("ppm", "sends_command"), [(210, True), (211, False), (None, False)])
async def test_xc0m_mute_preserves_apk_high_co_restriction(ppm, sends_command):
    station = Station(None, category="SBS50", stationId="hub", stationSn="1234ABCD")
    station.set_devices({"devices": [
        {"deviceType": "XC0M-MR", "deviceId": "child", "deviceSn": "00000001"},
    ]})
    child = station.get_device_by_sn("00000001")
    child.set_data({"standard": "0", "coPpm": ppm})
    client = object.__new__(AsyncXSense)
    client.userid = "user-id"
    client.do_thing = AsyncMock()
    if not sends_command:
        with pytest.raises(XSenseError, match="cannot be silenced"):
            await client.action(child, "mute")
        client.do_thing.assert_not_called()
        return
    await client.action(child, "mute")
    client.do_thing.assert_awaited_once_with(station, "2nd_appmute", {
        "state": {"desired": {
            "shadow": "app2ndMute", "stationSN": "1234ABCD", "deviceSN": "00000001",
            "muteType": "0", "userId": "user-id",
        }},
    })


@pytest.mark.asyncio
async def test_xs0ae_language_respects_reported_count_and_config_shadow():
    station = Station(None, category="XS0AE-iA", stationId="smoke", stationSn="1234ABCD")
    station.set_data({"languageCount": "3", "languageIndex": "1"})
    select = next(item for item in SELECTS if item.key == "xs0ae_voice_language")
    assert select.exists_fn(station)
    assert shadow_select_options(station, select) == ["English", "Fran\u00e7ais", "Deutsch"]
    client = object.__new__(AsyncXSense)
    client.do_thing = AsyncMock()
    client.get_station_state = AsyncMock()
    with pytest.raises(XSenseError, match="Unsupported"):
        await client.set_xs0ae_language(station, 4)
    client.do_thing.assert_not_called()
    await client.set_xs0ae_language(station, 3)
    client.do_thing.assert_awaited_once_with(station, "2nd_cfg_1234ABCD", {
        "state": {"desired": {
            "shadow": "infoBase", "stationSN": "1234ABCD", "deviceSN": "1234ABCD",
            "languageIndex": "3",
        }},
    })
    client.get_station_state.assert_awaited_once_with(station)


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
    expected_actions = ["test", "firedrill", "mute"]
    assert [action["action"] for action in entities[model]["actions"]] == expected_actions

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
    assert [action["action"] for action in entities["XS0AE-iA"]["actions"]] == ["test", "firedrill", "mute"]
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
    assert [action["action"] for action in entities[station.type]["actions"]] == [
        "test", "gas_drill", "co_drill", "mute",
    ]
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
    assert [call.args[1] for call in client.get_thing.await_args_list] == [
        "2nd_info_1234ABCD", "2nd_mainpage",
    ]
    assert station.data["wifiRSSI"] == -58
    alarm = next(sensor for sensor in SENSORS if sensor.key == "alarm_status")
    assert alarm.value_fn(station.get_device_by_sn("00000001")) is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("key", "value"),
    [("voiceVol", 31), ("alarmVol", 42), ("alarmTone", 3), ("ledBrt", 8),
     ("idleLedOff", 1), ("languageIndex", 4)],
)
async def test_sbs0a_setting_requires_accepted_write_and_matching_report(key, value):
    house = SimpleNamespace(house_id="home", mqtt_server="test-broker")
    station = Station(house, category="SBS0A", stationId="hub", stationSn="1234ABCD")
    subscribed, write_started, accept_write = (asyncio.Event() for _ in range(3))
    unsubscribe = Mock()
    listener = None

    async def subscribe(topic, callback, qos, *, encoding):
        nonlocal listener
        listener = callback
        assert topic == "$aws/things/SBS0A1234ABCD/shadow/name/2nd_info_1234ABCD/update"
        subscribed.set()
        return unsubscribe

    async def write(target, page, payload):
        assert subscribed.is_set()
        assert target is station
        assert page == "2nd_cfg_1234ABCD"
        assert payload == {"state": {"desired": {
            "shadow": "infoBase", "stationSN": station.sn, key: str(value),
        }}}
        write_started.set()
        await accept_write.wait()

    def report(serial, setting, *, retained=False):
        listener(SimpleNamespace(payload=json.dumps({
            "state": {"reported": {"stationSN": serial, key: str(setting)}},
        }), retain=retained))

    mqtt = SimpleNamespace(connected=True, async_subscribe=subscribe)
    coordinator = SimpleNamespace(
        _sbs0a_pending_settings=set(), mqtt_server=lambda host: mqtt,
        xsense=SimpleNamespace(do_thing=write), async_update_listeners=Mock(),
    )
    update = XSenseDataUpdateCoordinator.async_set_sbs0a_setting
    task = asyncio.create_task(update(coordinator, station, key, value))
    try:
        await asyncio.wait_for(write_started.wait(), 1)
        report(station.sn, value)
        assert not task.done()
        assert key not in station.data
        with pytest.raises(HomeAssistantError, match="already pending"):
            await update(coordinator, station, key, value)
        report(station.sn, -1)
        accept_write.set()
        report("other-station", value)
        report(station.sn, value, retained=True)
        await asyncio.sleep(0)
        assert not task.done()
        report(station.sn, value)
        await asyncio.wait_for(task, 1)
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    assert str(station.data[key]) == str(value)
    unsubscribe.assert_called_once()
    coordinator.async_update_listeners.assert_called_once()
    assert not coordinator._sbs0a_pending_settings


@pytest.mark.asyncio
async def test_xcg_night_mode_toggle_preserves_schedule_and_reads_applied_mode():
    station = Station(None, category="XCG0A-iA", stationId="gas", stationSn="1234ABCD")
    station.set_data({"zoneName": "Europe/Berlin", "timeZoneValid": "1"})
    current = {"isEnable": "0", "startTime": "2130", "endTime": "0700", "weekDays": [5, 1, 5]}
    pending = {**current, "isEnable": "1"}
    client = object.__new__(AsyncXSense)
    client.api_call = AsyncMock(side_effect=[
        {"updateState": "0", "currentMode": current}, {},
        {"updateState": "1", "currentMode": current, "updateMode": pending},
    ])
    await client.set_xcg_night_mode_enabled(station, True, "UTC")
    assert [call.args[0] for call in client.api_call.await_args_list] == ["406012", "406011", "406012"]
    assert client.api_call.await_args_list[1].kwargs == {
        "stationId": "gas", "isEnable": "1", "timeZone": "Europe/Berlin",
        "startTime": "2130", "endTime": "0700", "weekDays": "15",
    }
    assert station.data["xcgNightMode"]["isEnable"] == "0"


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["XCG0A-iA", "XS0AE-iA"])
async def test_night_schedule_edit_uses_the_model_specific_payload(model):
    station = Station(None, category=model, stationId="gas", stationSn="1234ABCD")
    station.set_data({"zoneName": "Europe/Berlin", "timeZoneValid": "1"})
    previous = {"isEnable": "1", "startTime": "2100", "endTime": "0700", "weekDays": "1234567"}
    edited = {"startTime": "2230", "endTime": "0605", "weekDays": ["5", "3"]}
    client = object.__new__(AsyncXSense)
    client.api_call = AsyncMock(side_effect=[
        {"currentMode": previous}, {},
        {"currentMode": {**edited, "isEnable": "1"}},
    ])
    await client.set_xcg_night_schedule(station, True, "UTC", schedule=edited)
    assert client.api_call.await_args_list[1].kwargs == {
        "stationId": "gas", "isEnable": "1", "timeZone": "Europe/Berlin",
        "startTime": "2230", "endTime": "0605",
        "weekDays": ["3", "5"] if model == "XS0AE-iA" else "35",
        **({"newTimeZoneMode": "1"} if model == "XS0AE-iA" else {}),
    }
    assert station.data["xcgNightMode"]["startTime"] == "2230"


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["XS0AD-MN", "XC0M-MR"])
@pytest.mark.parametrize(("key", "value"), [("alarmVol", 45), ("alarmTone", 2)])
async def test_paired_detector_alarm_audio_targets_child_config(model, key, value):
    station = Station(None, category="SBS50", stationId="hub", stationSn="1234ABCD")
    station.set_devices({"devices": [
        {"deviceType": model, "deviceId": "child", "deviceSn": "00000001"},
    ]})
    child = station.get_device_by_sn("00000001")
    client = object.__new__(AsyncXSense)
    client.do_thing = AsyncMock()
    await client.update_shadow_setting(child, key, value)
    client.do_thing.assert_awaited_once_with(
        station, "2nd_cfg_00000001",
        {"state": {"desired": {
            "shadow": "infoDev", "stationSN": station.sn, "deviceSN": child.sn,
            key: str(value),
        }}},
    )
@pytest.mark.asyncio
@pytest.mark.parametrize("cancel", [False, True])
async def test_sbs0a_setting_cleans_up_without_applying_on_failure(cancel):
    house = SimpleNamespace(house_id="home", mqtt_server="test-broker")
    station = Station(house, category="SBS0A", stationId="hub", stationSn="1234ABCD")
    unsubscribe = Mock()
    waiting = asyncio.Event()
    listener = None

    async def subscribe(topic, callback, qos, *, encoding):
        nonlocal listener
        listener = callback
        return unsubscribe

    async def write(*args):
        listener(SimpleNamespace(payload=json.dumps({
            "state": {"reported": {"stationSN": station.sn, "voiceVol": "25"}},
        })))
        if cancel:
            waiting.set()
            await asyncio.Future()
        raise APIFailure("write rejected")

    mqtt = SimpleNamespace(connected=True, async_subscribe=subscribe)
    coordinator = SimpleNamespace(
        _sbs0a_pending_settings=set(), mqtt_server=lambda host: mqtt,
        xsense=SimpleNamespace(do_thing=write), async_update_listeners=Mock(),
    )
    update = XSenseDataUpdateCoordinator.async_set_sbs0a_setting
    task = asyncio.create_task(update(coordinator, station, "voiceVol", 25))
    if cancel:
        await asyncio.wait_for(waiting.wait(), 1)
        task.cancel()
    with pytest.raises(asyncio.CancelledError if cancel else APIFailure):
        await task
    assert "voiceVol" not in station.data
    assert not coordinator._sbs0a_pending_settings
    coordinator.async_update_listeners.assert_not_called()
    unsubscribe.assert_called_once()
