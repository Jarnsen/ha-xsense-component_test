"""Regression coverage for the remaining APK-backed audit repairs."""

import asyncio
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from custom_components.xsense import diagnostics, number, select, switch
from custom_components.xsense.python_xsense.async_xsense import AsyncXSense
from custom_components.xsense.python_xsense.entity_map import entities
from custom_components.xsense.python_xsense.exceptions import APIFailure


def sth0c():
    return SimpleNamespace(
        type="STH0C",
        sn="serial",
        entity_id="station-id",
        house=SimpleNamespace(house_id="house-id"),
        data={},
        set_data=lambda values: None,
    )


@pytest.mark.asyncio
async def test_sth0c_write_fetches_companions_and_uses_rest():
    client = AsyncXSense()
    settings = {
        "dataIntervalM": "5",
        "tempUnit": "1",
        "tRange": ["10", "30"],
        "hRange": ["20", "80"],
        "tAdjust": "0",
        "hAdjust": "0",
        "tAlarmTimeS": "60",
        "hAlarmTimeS": "60",
    }
    client.api_call = AsyncMock(side_effect=[settings, {}])
    client.do_thing = AsyncMock()
    await client.update_shadow_setting(sth0c(), "tAdjust", 1.5)
    assert client.api_call.await_args_list[0].args == ("104111",)
    write = client.api_call.await_args_list[1]
    assert write.args == ("104110",)
    assert write.kwargs == {
        **settings,
        "tRange": ["10.0", "30.0"],
        "hRange": ["20.0", "80.0"],
        "tAdjust": "1.5",
        "houseId": "house-id",
        "stationId": "station-id",
        "category": "STH0C",
        "return_envelope": True,
    }
    client.do_thing.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [float("nan"), float("inf"), 3.1, -3.1])
async def test_sth0c_invalid_calibration_never_writes(value):
    client = AsyncXSense()
    client.api_call = AsyncMock()
    client.do_thing = AsyncMock()
    with pytest.raises(ValueError):
        await client.update_shadow_setting(sth0c(), "tAdjust", value)
    client.api_call.assert_not_awaited()
    client.do_thing.assert_not_awaited()


@pytest.mark.asyncio
async def test_sth0c_incomplete_companions_do_not_write():
    client = AsyncXSense()
    client.api_call = AsyncMock(return_value={"tAdjust": "0"})
    with pytest.raises(APIFailure, match="companion"):
        await client.update_shadow_setting(sth0c(), "tAdjust", 1)
    assert client.api_call.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [float("nan"), float("inf"), "NaN", "-Infinity"])
async def test_advanced_settings_reject_nonfinite_nested_values(value):
    client = AsyncXSense()
    client.do_thing = AsyncMock()
    with pytest.raises(ValueError, match="finite"):
        await client.update_shadow_settings(sth0c(), {"tRange": [0, value]})
    client.do_thing.assert_not_awaited()


@pytest.mark.parametrize("model", ["XP0A-MR", "CB0T-3B", "LP/R-SCA(VL)-0G"])
@pytest.mark.parametrize("edition,expected", [(0, "appXp0amrMute"), (9, "app2ndMute")])
def test_combo_mute_follows_apk_direct_device_firmware_route(model, edition, expected):
    entity = SimpleNamespace(data={"smokeEdition": edition})
    action = next(
        item for item in entities[model]["actions"] if item["action"] == "mute"
    )
    assert action["shadow"](entity) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model,target", [("XC01-M", "SBS50base"), ("XC04-WX", "XC04-WX-serial")]
)
async def test_co_peak_reset_has_distinct_child_and_standalone_targets(model, target):
    client = AsyncXSense()
    client.userid = "user"
    entity = sth0c()
    entity.type = model
    if model == "XC01-M":
        entity.station = SimpleNamespace(sn="base", house=entity.house, type="SBS50")
    client.do_thing = AsyncMock()
    await client.reset_co_peak(entity)
    args = client.do_thing.await_args.args
    assert args[0].shadow_name == target
    assert args[1] == "2nd_appco_reset"
    desired = args[2]["state"]["desired"]
    assert desired["shadow"] == "appCoReset"
    assert desired["deviceSN"] == "serial"
    assert desired["userId"] == "user"
    assert len(desired["time"]) == 13


@pytest.mark.asyncio
async def test_low_temperature_read_keeps_current_and_pending_distinct():
    client = AsyncXSense()
    entity = sth0c()
    entity.type = "SWS0B"
    client.api_call = AsyncMock(
        return_value={
            "currentMode": {"isEnable": "0"},
            "updateMode": {"isEnable": "1"},
            "updateState": "1",
        }
    )
    await client.refresh_alarm_settings(entity)
    assert entity.data["lowTempAlarmEnabled"] == "0"
    assert entity.data["lowTempAlarmPending"] == "1"
    assert client.api_call.await_args.args == ("406015",)


@pytest.mark.asyncio
async def test_radon_alarm_write_preserves_companions_and_never_uses_chart_api():
    client = AsyncXSense()
    entity = sth0c()
    entity.type = "XR0A-iR"
    client.api_call = AsyncMock(
        side_effect=[{"isEnable": "1", "monitorDay": "7", "alarmThreshold": "148"}, {}]
    )
    await client.update_alarm_settings(entity, monitorDay="30")
    write = client.api_call.await_args
    assert write.args == ("104120",)
    assert write.kwargs == {
        "stationId": "station-id",
        "stationSn": "serial",
        "isEnable": "1",
        "monitorDay": "30",
        "alarmThreshold": "148",
        "return_envelope": True,
    }
    assert entity.data == {}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "updates",
    [{"monitorDay": "2"}, {"alarmThreshold": float("nan")}, {"alarmThreshold": 10000}],
)
async def test_invalid_radon_alarm_settings_never_write(updates):
    client = AsyncXSense()
    entity = sth0c()
    entity.type = "XR0A-iR"
    client.api_call = AsyncMock(
        return_value={"isEnable": "1", "monitorDay": "7", "alarmThreshold": "148"}
    )
    with pytest.raises(ValueError):
        await client.update_alarm_settings(entity, **updates)
    assert client.api_call.await_count == 1


@pytest.mark.parametrize("key", ["cameraLiveUrl", "cameraAudioUrl"])
def test_diagnostic_urls_do_not_leak_query_or_userinfo(key):
    result = diagnostics._diagnostic_data(
        {key: "https://user:secret@host.test/media?sign=secret#token"}
    )
    assert result[key] == "https://host.test/media"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,response",
    [(403, {}), (200, {"state": None}), (200, {"state": {"reported": []}})],
)
async def test_alarm_shadow_rejects_failures_without_mutating_state(status, response):
    client = AsyncXSense()
    client._lastres = SimpleNamespace(status=status)
    client.get_thing = AsyncMock(return_value=response)
    entity = SimpleNamespace(set_alarm_data=Mock())
    with pytest.raises(APIFailure):
        await client.get_alarm_state(entity)
    entity.set_alarm_data.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("status,response", [(404, {}), (200, {"state": {}})])
async def test_optional_alarm_shadow_absence_remains_allowed(status, response):
    client = AsyncXSense()
    client._lastres = SimpleNamespace(status=status)
    client.get_thing = AsyncMock(return_value=response)
    await client.get_alarm_state(SimpleNamespace(set_alarm_data=Mock()))


@pytest.mark.asyncio
@pytest.mark.parametrize("key,value", [("tAdjust", 1.2), ("hAdjust", 2.1)])
async def test_sth0c_number_write_waits_for_server_readback(key, value):
    entity = sth0c()
    entity.data[key] = 0
    client = SimpleNamespace(update_shadow_setting=AsyncMock())
    instance = SimpleNamespace(
        _current_entity=lambda: entity,
        entity_description=replace(
            next(item for item in number.NUMBERS if item.data_key == key),
            exists_fn=lambda _: True,
        ),
        coordinator=SimpleNamespace(xsense=client, async_update_listeners=Mock()),
    )
    await number.XSenseNumberEntity.async_set_native_value(instance, value)
    assert entity.data[key] == 0
    client.update_shadow_setting.assert_awaited_once_with(entity, key, value)


@pytest.mark.asyncio
async def test_radon_monitor_select_refreshes_instead_of_optimistic_assignment():
    entity = sth0c()
    entity.type = "XR0A-iR"
    entity.data["radonAlarmMonitorDay"] = "7"
    client = SimpleNamespace(
        update_alarm_settings=AsyncMock(), refresh_alarm_settings=AsyncMock()
    )
    instance = SimpleNamespace(
        _current_entity=lambda: entity,
        entity_description=next(
            item for item in select.SELECTS if item.key == "radon_alarm_monitor_days"
        ),
        coordinator=SimpleNamespace(xsense=client, async_update_listeners=Mock()),
        options=["1", "7", "30", "90"],
    )
    await select.XSenseSelectEntity.async_select_option(instance, "30")
    assert entity.data["radonAlarmMonitorDay"] == "7"
    client.update_alarm_settings.assert_awaited_once_with(entity, monitorDay="30")


@pytest.mark.asyncio
async def test_walk_test_start_stop_and_unload_cleanup():
    instance = object.__new__(switch.XSenseSwitchEntity)
    entity = sth0c()
    entity.type = "SMS01"
    client = SimpleNamespace(set_motion_test=AsyncMock())
    instance.coordinator = SimpleNamespace(xsense=client)
    instance.hass = SimpleNamespace(
        async_create_background_task=lambda coro, name: asyncio.create_task(coro)
    )
    instance._motion_test_task = None
    instance._motion_test_entity = None
    instance._motion_test_lock = asyncio.Lock()
    instance.async_write_ha_state = Mock()
    await instance._async_motion_test(entity, True)
    timer = instance._motion_test_task
    assert instance._motion_test_entity is entity
    await instance._async_motion_test(entity, False)
    await asyncio.sleep(0)
    assert timer.cancelled()
    assert instance._motion_test_entity is None
    client.set_motion_test.assert_awaited_with(entity, False)


@pytest.mark.asyncio
async def test_walk_test_failed_start_does_not_create_timer():
    instance = object.__new__(switch.XSenseSwitchEntity)
    client = SimpleNamespace(
        set_motion_test=AsyncMock(side_effect=APIFailure("offline"))
    )
    instance.coordinator = SimpleNamespace(xsense=client)
    instance._motion_test_task = None
    instance._motion_test_entity = None
    instance._motion_test_lock = asyncio.Lock()
    with pytest.raises(APIFailure):
        await instance._async_motion_test(sth0c(), True)
    assert instance._motion_test_task is None
    assert instance._motion_test_entity is None


@pytest.mark.asyncio
async def test_walk_test_shutdown_stops_device_and_cancels_timer():
    instance = object.__new__(switch.XSenseSwitchEntity)
    client = SimpleNamespace(set_motion_test=AsyncMock())
    instance.coordinator = SimpleNamespace(xsense=client)
    instance._motion_test_entity = sth0c()
    instance._motion_test_lock = asyncio.Lock()
    instance.async_write_ha_state = Mock()
    instance._motion_test_task = asyncio.create_task(asyncio.sleep(600))
    timer = instance._motion_test_task
    await instance._async_stop_motion_test()
    await asyncio.sleep(0)
    assert timer.cancelled()
    assert instance._motion_test_entity is None
    client.set_motion_test.assert_awaited_once()
    assert client.set_motion_test.await_args.args[1] is False


@pytest.mark.parametrize(
    "version,supported",
    [("v1.3.9", False), ("v1.4.0", True), ("1.5.1", True), (None, False)],
)
def test_sws0b_low_temperature_firmware_gate(version, supported):
    from custom_components.xsense.python_xsense.async_xsense import (
        supports_low_temperature_alarm,
    )

    entity = SimpleNamespace(type="SWS0B", data={"sw": version})
    assert supports_low_temperature_alarm(entity) is supported


@pytest.mark.asyncio
async def test_sth0c_writes_are_serialized():
    client = AsyncXSense()
    first_read = asyncio.Event()
    release = asyncio.Event()
    fields = {
        "dataIntervalM": "5",
        "tempUnit": "1",
        "tRange": ["10", "30"],
        "hRange": ["20", "80"],
        "tAdjust": "0",
        "hAdjust": "0",
        "tAlarmTimeS": "60",
        "hAlarmTimeS": "60",
    }

    async def api(operation, **kwargs):
        if operation == "104111":
            first_read.set()
            await release.wait()
            return dict(fields)
        fields.update({key: value for key, value in kwargs.items() if key in fields})
        return {}

    client.api_call = AsyncMock(side_effect=api)
    entity = sth0c()
    one = asyncio.create_task(client.update_shadow_setting(entity, "tAdjust", 1))
    await first_read.wait()
    two = asyncio.create_task(client.update_shadow_setting(entity, "hAdjust", 2))
    await asyncio.sleep(0)
    assert client.api_call.await_count == 1
    release.set()
    await asyncio.gather(one, two)
    assert fields["tAdjust"] == "1"
    assert fields["hAdjust"] == "2"


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["SWS0B", "XR0A-iR", "STH0C"])
async def test_settings_write_accepts_apk_no_body_success(model):
    client = AsyncXSense()
    response = MagicMock(status=200)
    response.__aenter__.return_value = response
    response.json = AsyncMock(return_value={"reCode": 200})
    client._get_session = AsyncMock(
        return_value=SimpleNamespace(post=lambda *args, **kwargs: response)
    )
    client._access_token_expiring = Mock(return_value=False)
    client._calculate_mac = Mock(return_value="mac")
    entity = sth0c()
    entity.type = model
    entity.data["sw"] = "v1.4.0"
    if model == "STH0C":
        client.get_sth0c_settings = AsyncMock(
            return_value={
                "dataIntervalM": "5",
                "tempUnit": "1",
                "tRange": ["10", "30"],
                "hRange": ["20", "80"],
                "tAdjust": "0",
                "hAdjust": "0",
                "tAlarmTimeS": "60",
                "hAlarmTimeS": "60",
            }
        )
        result = await client.update_shadow_setting(entity, "tAdjust", 1)
    else:
        if model == "XR0A-iR":
            client.query_alarm_settings = AsyncMock(
                return_value={
                    "isEnable": "0",
                    "monitorDay": "7",
                    "alarmThreshold": "148",
                }
            )
        result = await client.update_alarm_settings(entity, isEnable="1")
    assert result == {"reCode": 200}


@pytest.mark.asyncio
async def test_sth0c_other_settings_keep_existing_shadow_route():
    client = AsyncXSense()
    client.do_thing = AsyncMock()
    client.api_call = AsyncMock()
    entity = sth0c()
    await client.update_shadow_setting(entity, "ledLight", "1")
    client.api_call.assert_not_awaited()
    assert client.do_thing.await_args.args[2]["state"]["desired"]["ledLight"] == "1"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model,payload", [("SWS0B", {"currentMode": {}}), ("XR0A-iR", {})]
)
async def test_malformed_optional_settings_do_not_create_unknown_controls(
    model, payload
):
    client = AsyncXSense()
    client.api_call = AsyncMock(return_value=payload)
    entity = sth0c()
    entity.type = model
    with pytest.raises(APIFailure):
        await client.refresh_alarm_settings(entity)
    assert entity.data == {}
