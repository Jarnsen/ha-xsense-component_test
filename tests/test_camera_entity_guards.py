import asyncio
import importlib
import logging
import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError

for module_name in list(sys.modules):
    if module_name == "custom_components.xsense" or module_name.startswith(
        "custom_components.xsense."
    ):
        del sys.modules[module_name]
if not hasattr(sys.modules.get("custom_components"), "__path__"):
    sys.modules.pop("custom_components", None)

from custom_components.xsense import (
    PLATFORMS,
    binary_sensor,
    button,
    camera,
    event,
    number,
    select,
    sensor,
    switch,
)
from custom_components.xsense.python_xsense import mapping
from custom_components.xsense.python_xsense.entity_map import EntityType
from homeassistant.const import EntityCategory, Platform


def entity(device_type, data):
    return SimpleNamespace(type=device_type, data=data)


def _recordings_media_source_hass(**kwargs):
    """Return a hass stub that passes recordings media-source camera gating."""
    from custom_components.xsense.const import DOMAIN

    coordinator = SimpleNamespace(
        data={
            "stations": {"camera": SimpleNamespace(type="SSC0A")},
            "devices": {},
        }
    )
    return SimpleNamespace(data={DOMAIN: {"entry-id": coordinator}}, **kwargs)


def routed_entity(device_type, data, *, station_type="SBS50"):
    station = SimpleNamespace(
        type=station_type,
        sn="station-sn",
        shadow_name=f"{station_type}station-sn",
    )
    return SimpleNamespace(
        type=device_type,
        sn="device-sn",
        station=station,
        data=data,
    )


def minimal_entity(device_type, entity_type, data=None, *, station_type="SBS50"):
    device = routed_entity(device_type, data or {}, station_type=station_type)
    device.entity_type = entity_type
    return device


def test_boolean_state_does_not_invent_unknown_values():
    assert binary_sensor.boolean_state(True) is True
    assert binary_sensor.boolean_state(False) is False
    assert binary_sensor.boolean_state(1) is True
    assert binary_sensor.boolean_state(0) is False
    assert binary_sensor.boolean_state("true") is True
    assert binary_sensor.boolean_state("false") is False
    assert binary_sensor.boolean_state(2) is None
    assert binary_sensor.boolean_state("unexpected") is None
    assert switch.boolean_state(2) is None
    assert mapping.bool_state("off") is False
    assert mapping.bool_state("unexpected") is None
    assert mapping.map_type("tComfort", ["20", 26]) == [20.0, 26.0]
    assert mapping.map_type("hComfort", ["30", 60]) == [30.0, 60.0]
    assert mapping.map_type("tComfort", ["bad", 26]) is None


def test_device_status_matches_apk_current_status_precedence():
    description = next(item for item in sensor.SENSORS if item.key == "device_status")

    assert description.value_fn(entity("XS01-WX", {"batInfo": "3"})) == "normal"
    assert description.value_fn(entity("XS01-WX", {"batInfo": "1"})) == "low_battery"
    assert (
        description.value_fn(
            entity("XS01-WX", {"sensorStatus": "1", "batInfo": "1"})
        )
        == "malfunction"
    )
    assert (
        description.value_fn(
            entity(
                "XS01-WX",
                {"isLifeEnd": "1", "sensorStatus": "1", "batInfo": "1"},
            )
        )
        == "end_of_life"
    )


def test_supported_device_status_defaults_to_normal_before_first_report():
    description = next(item for item in sensor.SENSORS if item.key == "device_status")

    assert description.value_fn(entity("XS01-WX", {})) == "normal"
    assert description.value_fn(entity("XC04-WX", {})) == "normal"


def test_mute_button_is_a_visible_device_control():
    description = next(item for item in button.BUTTONS if item.key == "mute")

    assert description.entity_category is None


def test_precreated_sensor_values_are_safe_before_first_payload():
    station = SimpleNamespace(
        type="SBS50",
        sn="station-sn",
        shadow_name="SBS50station-sn",
        data={},
        entity_type=EntityType.BASESTATION,
    )
    samples = [
        station,
        minimal_entity("XS01-WX", EntityType.SMOKE),
        minimal_entity("XC04-WX", EntityType.CO),
        minimal_entity("XP0A-MR", EntityType.COMBI),
        minimal_entity("SDS0A", EntityType.DOOR),
    ]

    for description in (*sensor.SENSORS, *binary_sensor.SENSORS):
        for sample in samples:
            if description.exists_fn(sample):
                description.value_fn(sample)


def test_camera_setup_controls_are_exposed_for_automation_when_supported():
    switch_keys = {description.key for description in switch.SWITCHES}
    select_keys = {description.key for description in select.SELECTS}
    number_keys = {description.key for description in number.NUMBERS}

    assert {
        "camera_motion_detection",
        "camera_person_detection",
        "camera_live_audio",
        "camera_recording_audio",
        "camera_alarm_when_removed",
    }.issubset(switch_keys)
    assert {
        "camera_language",
        "camera_recording_resolution",
        "camera_default_codec",
    }.issubset(select_keys)
    assert {
        "camera_alarm_volume",
        "camera_live_speaker_volume",
        "camera_cooldown",
    }.issubset(number_keys)


def test_select_platform_is_loaded_for_camera_and_non_camera_controls():
    assert Platform.SELECT in PLATFORMS


def test_non_camera_selects_require_shadow_write_route():
    descriptions = {description.key: description for description in select.SELECTS}
    routed = routed_entity(
        "XS01-WX",
        {
            "alarmTone": "1",
            "tempUnit": "1",
            "ledBrt": "6",
        },
    )
    light = routed_entity(
        "SSL51",
        {
            "pirTime": "60",
            "appTime": "300",
            "lightScene": "3",
        },
    )
    light.entity_type = select.EntityType.LIGHT
    missing_station = SimpleNamespace(
        type="XS01-WX",
        sn="device-sn",
        station=SimpleNamespace(type="SBS50", sn="station-sn"),
        data={"alarmTone": "1", "tempUnit": "1"},
    )

    assert descriptions["alarm_tone"].exists_fn(routed)
    assert descriptions["alarm_tone"].fixed_options == ("1", "2", "3")
    assert not descriptions["alarm_tone"].exists_fn(missing_station)
    assert descriptions["temperature_unit"].exists_fn(routed)
    assert descriptions["temperature_unit"].fixed_options == ("1", "2")
    assert descriptions["led_brightness"].exists_fn(routed)
    assert descriptions["led_brightness"].fixed_options == ("2", "4", "6", "8")
    assert descriptions["light_motion_on_time"].exists_fn(light)
    assert descriptions["light_app_on_time"].exists_fn(light)
    assert descriptions["light_scene"].exists_fn(light)
    assert descriptions["light_scene"].fixed_options == ("1", "2", "3")
    assert descriptions["light_motion_on_time"].fixed_options == (
        "30",
        "60",
        "180",
        "300",
        "600",
        "900",
    )


def test_mailbox_controls_match_apk_payload_capabilities():
    select_descriptions = {
        description.key: description for description in select.SELECTS
    }
    binary_descriptions = {
        description.key: description for description in binary_sensor.SENSORS
    }
    switch_descriptions = {
        description.key: description for description in switch.SWITCHES
    }
    mailbox = routed_entity(
        "SMA0A",
        {
            "mailNotice": "1",
            "reportInterval": "30",
            "scheduleStatus": "1",
        },
    )
    mailbox.entity_type = EntityType.MAILBOX
    smoke = routed_entity(
        "XS01-M", {"reportInterval": "30", "scheduleStatus": "1"}
    )
    smoke.entity_type = EntityType.SMOKE

    report_interval = select_descriptions["mailbox_report_interval"]
    schedule_active = binary_descriptions["mailbox_schedule_active"]
    mail_notice = switch_descriptions["mail_notice"]

    assert report_interval.exists_fn(mailbox)
    assert report_interval.fixed_options == (
        "2",
        "5",
        "10",
        "15",
        "30",
        "60",
        "120",
        "240",
        "360",
        "480",
        "720",
    )
    assert schedule_active.exists_fn(mailbox)
    assert schedule_active.value_fn(mailbox) is True
    assert mail_notice.exists_fn(mailbox)
    assert mail_notice.value_fn(mailbox) is True
    assert "mail_notice" not in binary_descriptions
    assert not report_interval.exists_fn(smoke)
    assert not schedule_active.exists_fn(smoke)
    assert not mail_notice.exists_fn(smoke)


async def test_mailbox_report_interval_uses_apk_shadow_writer():
    mailbox = routed_entity("SMA0A", {"reportInterval": "30"})
    mailbox.entity_type = EntityType.MAILBOX
    xsense = SimpleNamespace(update_shadow_setting=AsyncMock())
    coordinator = SimpleNamespace(
        xsense=xsense,
        async_update_listeners=MagicMock(),
    )
    select_entity = SimpleNamespace(
        coordinator=coordinator,
        entity_description=next(
            item
            for item in select.SELECTS
            if item.key == "mailbox_report_interval"
        ),
        _current_entity=lambda: mailbox,
        options=[
            "2",
            "5",
            "10",
            "15",
            "30",
            "60",
            "120",
            "240",
            "360",
            "480",
            "720",
        ],
    )

    await select.XSenseSelectEntity.async_select_option(select_entity, "60")

    xsense.update_shadow_setting.assert_awaited_once_with(
        mailbox, "reportInterval", "60"
    )
    assert mailbox.data["reportInterval"] == 60
    coordinator.async_update_listeners.assert_called_once_with()


async def test_mailbox_mail_notice_uses_apk_shadow_writer():
    mailbox = routed_entity("SMA51", {"mailNotice": "0"})
    mailbox.entity_type = EntityType.MAILBOX
    xsense = SimpleNamespace(update_shadow_setting=AsyncMock())
    coordinator = SimpleNamespace(
        xsense=xsense,
        async_update_listeners=MagicMock(),
    )
    switch_entity = SimpleNamespace(
        coordinator=coordinator,
        entity_description=next(
            item for item in switch.SWITCHES if item.key == "mail_notice"
        ),
        _current_entity=lambda: mailbox,
    )

    await switch.XSenseSwitchEntity._async_set_state(switch_entity, True)

    xsense.update_shadow_setting.assert_awaited_once_with(
        mailbox, "mailNotice", "1"
    )
    assert mailbox.data["mailNotice"] is True
    coordinator.async_update_listeners.assert_called_once_with()


def test_non_camera_numbers_include_apk_setting_controls():
    descriptions = {description.key: description for description in number.NUMBERS}
    routed = routed_entity(
        "STH0B",
        {
            "tAdjust": "0.5",
            "hAdjust": "2",
            "warnPeriod": "5",
            "detcSens": "2",
            "sensitivity": "3",
            "tempRangeMin": 10,
            "tempRangeMax": 30,
            "humRangeMin": 20,
            "humRangeMax": 80,
            "comfortType": "0",
        },
    )
    light = routed_entity(
        "SSL51",
        {
            "triggerBrightness": "60",
            "awaitBrightness": "30",
        },
    )
    light.entity_type = number.EntityType.LIGHT
    missing_station = SimpleNamespace(
        type="STH0B",
        sn="device-sn",
        station=SimpleNamespace(type="SBS50", sn="station-sn"),
        data={"tAdjust": "0.5", "hAdjust": "2", "warnPeriod": "5"},
    )

    assert descriptions["temperature_adjustment"].exists_fn(routed)
    assert descriptions["humidity_adjustment"].exists_fn(routed)
    assert descriptions["warning_period"].exists_fn(routed)
    assert descriptions["detection_sensitivity"].exists_fn(routed)
    assert descriptions["driveway_sensitivity"].exists_fn(routed)
    assert descriptions["trigger_brightness"].exists_fn(light)
    assert descriptions["standby_brightness"].exists_fn(light)
    assert descriptions["temperature_min"].exists_fn(routed)
    assert descriptions["temperature_max"].exists_fn(routed)
    assert descriptions["humidity_min"].exists_fn(routed)
    assert descriptions["humidity_max"].exists_fn(routed)
    assert descriptions["temperature_comfort_min"].exists_fn(routed)
    assert descriptions["temperature_comfort_max"].exists_fn(routed)
    assert descriptions["humidity_comfort_min"].exists_fn(routed)
    assert descriptions["humidity_comfort_max"].exists_fn(routed)
    assert not descriptions["temperature_adjustment"].exists_fn(missing_station)


def test_radon_server_controls_require_apk_station_identity():
    select_descriptions = {
        description.key: description for description in select.SELECTS
    }
    number_descriptions = {
        description.key: description for description in number.NUMBERS
    }
    radon = SimpleNamespace(
        type="XR0A-iR",
        sn="radon-sn",
        entity_id="station-id",
        data={"radonUnit": "2", "minRadon": "75", "maxRadon": "150"},
    )
    missing_identity = SimpleNamespace(
        type="XR0A-iR", sn="radon-sn", entity_id=None, data={}
    )

    assert select_descriptions["radon_unit"].exists_fn(radon)
    assert number_descriptions["radon_minimum_threshold"].exists_fn(radon)
    assert number_descriptions["radon_maximum_threshold"].exists_fn(radon)
    assert not select_descriptions["radon_unit"].exists_fn(missing_identity)
    assert not number_descriptions["radon_minimum_threshold"].exists_fn(
        missing_identity
    )


async def test_radon_unit_select_uses_apk_server_writer():
    radon = SimpleNamespace(
        type="XR0A-iR",
        sn="radon-sn",
        entity_id="station-id",
        data={"radonUnit": "1", "tempUnit": "2"},
    )
    xsense = SimpleNamespace(update_radon_unit=AsyncMock())
    coordinator = SimpleNamespace(
        xsense=xsense,
        async_update_listeners=MagicMock(),
    )
    select_entity = SimpleNamespace(
        coordinator=coordinator,
        entity_description=next(
            item for item in select.SELECTS if item.key == "radon_unit"
        ),
        _current_entity=lambda: radon,
        options=["1", "2"],
    )

    await select.XSenseSelectEntity.async_select_option(select_entity, "2")

    xsense.update_radon_unit.assert_awaited_once_with(radon, "2")
    assert radon.data["radonUnit"] == 2
    coordinator.async_update_listeners.assert_called_once_with()


async def test_radon_threshold_number_preserves_paired_apk_value():
    radon = SimpleNamespace(
        type="XR0A-iR",
        sn="radon-sn",
        entity_id="station-id",
        data={"minRadon": "75", "maxRadon": "150"},
    )
    xsense = SimpleNamespace(update_radon_thresholds=AsyncMock())
    coordinator = SimpleNamespace(
        xsense=xsense,
        async_update_listeners=MagicMock(),
    )
    number_entity = SimpleNamespace(
        coordinator=coordinator,
        entity_description=next(
            item
            for item in number.NUMBERS
            if item.key == "radon_minimum_threshold"
        ),
        _current_entity=lambda: radon,
    )

    await number.XSenseNumberEntity.async_set_native_value(number_entity, 80)

    xsense.update_radon_thresholds.assert_awaited_once_with(
        radon, min_radon=80, max_radon=150
    )
    assert radon.data["minRadon"] == 80
    coordinator.async_update_listeners.assert_called_once_with()


def test_shadow_range_number_values_use_apk_arrays_and_defaults():
    descriptions = {description.key: description for description in number.NUMBERS}
    routed = routed_entity(
        "STH0B",
        {
            "tRange": [9, 31],
            "hRange": [25, 75],
            "comfortType": "0",
        },
    )

    assert number._shadow_array_value(routed, descriptions["temperature_min"]) == 9
    assert number._shadow_array_value(routed, descriptions["temperature_max"]) == 31
    assert number._shadow_array_value(routed, descriptions["humidity_min"]) == 25
    assert number._shadow_array_value(routed, descriptions["humidity_max"]) == 75
    assert (
        number._shadow_array_value(routed, descriptions["temperature_comfort_min"])
        == 20
    )
    assert (
        number._shadow_array_value(routed, descriptions["temperature_comfort_max"])
        == 26
    )


def test_warning_enabled_switch_uses_write_route_guard():
    descriptions = {description.key: description for description in switch.SWITCHES}
    routed = routed_entity("XC0C-MR", {"warnIsOpen": "1"})
    light = routed_entity(
        "SSL51",
        {
            "awaitEnable": "1",
            "pirEnable": "1",
            "sunshineEnable": "0",
        },
    )
    missing_station = SimpleNamespace(
        type="XC0C-MR",
        sn="device-sn",
        station=SimpleNamespace(type="SBS50", sn="station-sn"),
        data={"warnIsOpen": "1"},
    )

    assert descriptions["warning_enabled"].exists_fn(routed)
    assert descriptions["warning_enabled"].value_fn(routed) is True
    assert not descriptions["warning_enabled"].exists_fn(missing_station)
    assert descriptions["await_enabled"].exists_fn(light)
    assert descriptions["await_enabled"].light_on_event == "0"
    assert descriptions["pir_enabled"].light_on_event == "0"
    assert descriptions["sunshine_enabled"].light_on_event == "0"


def test_light_power_switch_is_primary_control_not_config_entity():
    descriptions = {description.key: description for description in switch.SWITCHES}
    light_power = descriptions["light_power"]
    light = routed_entity("SSL51", {"on": "1"})
    light.entity_type = switch.EntityType.LIGHT

    assert light_power.entity_category is None
    assert light_power.exists_fn(light)
    assert light_power.value_fn(light) is True


def test_light_schedule_service_helpers_validate_apk_values():
    assert switch._schedule_time("06:05") == "0605"
    assert switch._schedule_time("2300") == "2300"
    assert switch._schedule_week_days(["1", 7]) == ["1", "7"]
    assert switch._light_schedule_list({"schedList": [{"schedId": "1"}]}) == [
        {"schedId": "1"}
    ]
    assert switch._light_group_list(
        {"reData": {"groupList": [{"groupId": "1"}]}}
    ) == [{"groupId": "1"}]
    assert switch._non_empty_strings([" light-1 ", ""], "device_ids") == ["light-1"]

    with pytest.raises(HomeAssistantError):
        switch._schedule_time("24:00")
    with pytest.raises(HomeAssistantError):
        switch._schedule_week_days(["0"])
    with pytest.raises(HomeAssistantError):
        switch._non_empty_strings([""], "device_ids")


def test_camera_selects_survive_unknown_current_setting_values():
    camera = entity(
        "SSC0A",
        {
            "isAdmin": True,
            "needMotion": True,
            "videoSecondsValues": [-1, 10, 20],
        },
    )

    descriptions = {description.key: description for description in select.SELECTS}

    assert descriptions["camera_motion_sensitivity"].exists_fn(camera)
    assert descriptions["camera_video_seconds"].exists_fn(camera)


def test_camera_motion_sensitivity_matches_apk_labels_and_values():
    description = next(
        item for item in select.SELECTS if item.key == "camera_motion_sensitivity"
    )
    three_level_camera = entity("SSC0A", {"isAdmin": True, "motionSensitivity": 0})
    auto_camera = entity(
        "SSC0A",
        {
            "isAdmin": True,
            "motionSensitivity": 4,
            "motionSensitivityOptionList": [1, 2, 3, 4],
        },
    )

    three_level_select = SimpleNamespace(
        entity_description=description,
        _current_entity=lambda: three_level_camera,
        options=["high", "medium", "low"],
    )
    auto_select = SimpleNamespace(
        entity_description=description,
        _current_entity=lambda: auto_camera,
        options=["high", "medium", "low", "auto"],
    )

    assert select.XSenseSelectEntity.options.fget(three_level_select) == [
        "high",
        "medium",
        "low",
    ]
    assert select.XSenseSelectEntity.current_option.fget(three_level_select) == "high"
    assert select.XSenseSelectEntity.options.fget(auto_select) == [
        "high",
        "medium",
        "low",
        "auto",
    ]
    assert select.XSenseSelectEntity.current_option.fget(auto_select) == "auto"


async def test_camera_motion_sensitivity_writes_apk_value():
    camera = entity("SSC0A", {"isAdmin": True, "motionSensitivity": 1})
    xsense = SimpleNamespace(update_camera_config=AsyncMock())
    coordinator = SimpleNamespace(
        xsense=xsense,
        async_update_listeners=MagicMock(),
    )
    select_entity = SimpleNamespace(
        coordinator=coordinator,
        entity_description=next(
            item
            for item in select.SELECTS
            if item.key == "camera_motion_sensitivity"
        ),
        _current_entity=lambda: camera,
        options=["high", "medium", "low"],
    )

    await select.XSenseSelectEntity.async_select_option(select_entity, "low")

    xsense.update_camera_config.assert_awaited_once_with(camera, motionSensitivity=3)
    assert camera.data["motionSensitivity"] == 3
    coordinator.async_update_listeners.assert_called_once_with()


def test_camera_person_detection_switch_follows_apk_support_flag():
    descriptions = {description.key: description for description in switch.SWITCHES}
    description = descriptions["camera_person_detection"]

    supported = entity("SSC0A", {"isAdmin": True, "supportPersonDetect": True})
    unsupported = entity(
        "SSC0A",
        {
            "isAdmin": True,
            "supportPersonDetect": False,
            "devicePersonDetect": True,
        },
    )

    assert description.exists_fn(supported)
    assert description.value_fn(supported) is None
    assert not description.exists_fn(unsupported)


def test_camera_ai_setting_switches_follow_apk_support_lists():
    descriptions = {description.key: description for description in switch.SWITCHES}
    camera = entity(
        "SSC0A",
        {
            "isAdmin": True,
            "aiNotificationPerson": True,
            "aiNotificationVehicleEnter": False,
            "aiNotificationSupportedTypes": ["person", "vehicle_enter"],
            "aiAssistantPerson": True,
            "aiAssistantVehicle": False,
            "aiAssistantSupportedTypes": ["person", "vehicle"],
        },
    )

    assert descriptions["camera_ai_notification_person"].exists_fn(camera)
    assert descriptions["camera_ai_notification_person"].value_fn(camera) is True
    assert descriptions["camera_ai_notification_vehicle_enter"].exists_fn(camera)
    assert (
        descriptions["camera_ai_notification_vehicle_enter"].value_fn(camera) is False
    )
    assert not descriptions["camera_ai_notification_pet"].exists_fn(camera)
    assert descriptions["camera_ai_assistant_person"].exists_fn(camera)
    assert descriptions["camera_ai_assistant_person"].value_fn(camera) is True
    assert descriptions["camera_ai_assistant_vehicle"].exists_fn(camera)
    assert descriptions["camera_ai_assistant_vehicle"].value_fn(camera) is False
    assert not descriptions["camera_ai_assistant_package"].exists_fn(camera)


@pytest.mark.parametrize("camera_type", ("SSC0A", "SSC0B"))
def test_camera_sleep_switch_follows_apk_support_and_device_status(camera_type):
    descriptions = {description.key: description for description in switch.SWITCHES}
    description = descriptions["camera_sleep"]

    sleeping = entity(
        camera_type, {"isAdmin": True, "supportSleep": True, "deviceStatus": 3}
    )
    awake = entity(
        camera_type, {"isAdmin": True, "supportSleep": True, "deviceStatus": 1001}
    )
    unsupported = entity(
        camera_type, {"isAdmin": True, "supportSleep": False, "deviceStatus": 3}
    )

    assert description.entity_category == EntityCategory.CONFIG
    assert description.exists_fn(sleeping)
    assert description.value_fn(sleeping) is True
    assert description.exists_fn(awake)
    assert description.value_fn(awake) is False
    assert not description.exists_fn(unsupported)


def test_non_camera_switches_require_shadow_write_route():
    descriptions = {description.key: description for description in switch.SWITCHES}
    routed = routed_entity("XS01-WX", {"keySound": "1"})
    missing_station = SimpleNamespace(
        type="XS01-WX",
        sn="device-sn",
        station=SimpleNamespace(type="SBS50", sn="station-sn"),
        data={"keySound": "1"},
    )
    missing_device_serial = routed_entity("XS01-WX", {"keySound": "1"})
    missing_device_serial.sn = None

    assert descriptions["key_sound_enabled"].exists_fn(routed)
    assert not descriptions["key_sound_enabled"].exists_fn(missing_station)
    assert not descriptions["key_sound_enabled"].exists_fn(missing_device_serial)


def test_non_camera_volume_numbers_require_shadow_write_route():
    descriptions = {description.key: description for description in number.NUMBERS}
    routed = routed_entity("XS01-WX", {"voiceVol": 40})
    missing_station = SimpleNamespace(
        type="XS01-WX",
        sn="device-sn",
        station=SimpleNamespace(type="SBS50", sn="station-sn"),
        data={"voiceVol": 40},
    )

    assert descriptions["voice_volume"].exists_fn(routed)
    assert not descriptions["voice_volume"].exists_fn(missing_station)


def test_camera_entities_keep_storage_health_without_raw_apk_metadata():
    descriptions = {description.key: description for description in sensor.SENSORS}
    camera = entity(
        "SSC0A",
        {
            "activatedTime": "20260619120000",
            "cameraStatusCode": 0,
            "deviceDormancyMessage": "sleeping",
            "deviceDormancyWakeTime": "20260619120500",
            "firmwareStatus": 1,
            "firmwareVersion": "1.0.0",
            "networkName": "Front WiFi",
            "offlineTime": "20260619121000",
            "sdCardFormatStatus": 0,
            "sdCardTotal": 128000,
            "sdCardUsed": 64000,
            "thumbImgTime": "20260619121500",
            "timeZoneArea": "America/New_York",
            "wifiChannel": "6",
            "wiredMacAddress": "00:11:22:33:44:55",
        },
    )

    raw_metadata_keys = {
        "camera_activated_time",
        "camera_status_code",
        "camera_dormancy_message",
        "camera_dormancy_wake_time",
        "camera_firmware_status",
        "camera_firmware_version",
        "camera_network_name",
        "camera_offline_time",
        "camera_thumbnail_time",
        "camera_time_zone_area",
        "camera_wifi_channel",
        "camera_wired_mac_address",
    }
    assert raw_metadata_keys.isdisjoint(descriptions)

    for key in {
        "camera_sd_card_status",
        "camera_sd_card_total",
        "camera_sd_card_used",
    }:
        assert descriptions[key].exists_fn(camera)


def test_practical_network_location_fields_remain_diagnostic_entities():
    xsense_init = importlib.import_module("custom_components.xsense")
    from custom_components.xsense.const import NON_ENTITY_DIAGNOSTIC_SENSOR_KEYS

    descriptions = {description.key: description for description in sensor.SENSORS}
    practical_keys = {"ip", "wifi_ssid", "wifi_rssi_level", "zone_name", "location"}
    sample = entity(
        "SBS50",
        {
            "ip": "192.0.2.10",
            "ssid": "Home WiFi",
            "wifiRssiLevel": 3,
            "zoneName": "Garage",
            "location": "Garage",
        },
    )

    assert practical_keys.isdisjoint(NON_ENTITY_DIAGNOSTIC_SENSOR_KEYS)
    assert practical_keys.isdisjoint(xsense_init.OBSOLETE_SENSOR_KEYS)
    assert practical_keys.issubset(descriptions)
    for key in practical_keys:
        assert descriptions[key].entity_category is EntityCategory.DIAGNOSTIC
        assert descriptions[key].exists_fn(sample)


def test_read_only_camera_entities_require_camera_entity():
    non_camera = entity("XS01-WX", {"batteryLevel": 2, "needMotion": 1})
    camera = entity("SSC0A", {"batteryLevel": 2, "needMotion": 1})

    assert not sensor.has_camera_data("batteryLevel")(non_camera)
    assert sensor.has_camera_data("batteryLevel")(camera)


def test_camera_motion_binary_uses_per_camera_event_pulse_not_is_moved():
    non_camera = entity("XS01-WX", {"needMotion": 1})
    camera = entity("SSC0A", {"isMoved": "1"})

    motion = next(item for item in binary_sensor.SENSORS if item.key == "moved")

    assert not motion.exists_fn(non_camera)
    assert motion.exists_fn(camera)
    assert motion.value_fn(camera) is False

    camera.data["cameraMotionDetected"] = True
    assert motion.value_fn(camera) is True

    camera.data["cameraMotionDetected"] = False
    assert motion.value_fn(camera) is False


def test_regular_motion_binary_entity_uses_reported_non_camera_motion_state():
    motion = next(item for item in binary_sensor.SENSORS if item.key == "moved")

    assert motion.value_fn(entity("SMS", {"isMoved": "1"})) is True
    assert motion.value_fn(entity("SMS", {"isMoved": "0"})) is False


def test_ai_detection_event_entity_precreates_for_camera_notifications():
    supported_camera = entity("SSC0A", {"supportPersonDetect": True})
    camera_without_ai_plan = entity("SSC0A", {"supportPersonDetect": False})
    camera_with_event_data = entity(
        "SSC0A", {"supportPersonDetect": False, "lastAiDetection": "person"}
    )
    non_camera = entity("XS01-WX", {"supportPersonDetect": True})

    description = event.AI_DETECTION_DESCRIPTION

    assert description.exists_fn(supported_camera)
    assert description.exists_fn(camera_without_ai_plan)
    assert description.exists_fn(camera_with_event_data)
    assert not description.exists_fn(non_camera)


def test_ai_detection_event_entities_handle_missing_coordinator_data():
    assert event._ai_detection_event_entities(SimpleNamespace(data=None)) == []
    assert event._ai_detection_event_entities(SimpleNamespace(data={})) == []


def test_ai_detection_event_entities_include_device_cameras():
    station = entity("SBS50", {})
    station.entity_id = "station-1"
    station.name = "Station"
    station.online = True

    station_camera = entity("SSC0A", {"supportPersonDetect": True})
    station_camera.entity_id = "station-camera"
    station_camera.name = "Station Camera"
    station_camera.online = True

    device_camera = entity("SSC0A", {"supportPersonDetect": True})
    device_camera.entity_id = "device-camera"
    device_camera.name = "Device Camera"
    device_camera.online = True
    device_camera.station = station

    class Coordinator:
        data = {
            "stations": {
                station.entity_id: station,
                station_camera.entity_id: station_camera,
            },
            "devices": {device_camera.entity_id: device_camera},
        }

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    entities = event._ai_detection_event_entities(Coordinator())

    assert [entity._dev_id for entity in entities] == [
        station_camera.entity_id,
        device_camera.entity_id,
    ]
    assert entities[0]._station_id is None
    assert entities[1]._station_id == station.entity_id
    assert entities[1]._current_entity() is device_camera


def test_ai_detection_event_entity_is_disabled_by_default_without_ai_service():
    from custom_components.xsense.const import CAMERA_AI_SERVICE_AVAILABLE

    camera_without_ai_service = entity(
        "SSC0A", {CAMERA_AI_SERVICE_AVAILABLE: False}
    )
    camera_without_ai_service.entity_id = "camera-without-ai-service"
    camera_without_ai_service.name = "Camera Without AI Service"
    camera_without_ai_service.online = True

    class Coordinator:
        data = {
            "stations": {camera_without_ai_service.entity_id: camera_without_ai_service},
            "devices": {},
        }

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    entities = event._ai_detection_event_entities(Coordinator())

    assert [entity._dev_id for entity in entities] == [
        camera_without_ai_service.entity_id
    ]
    assert entities[0]._attr_entity_registry_enabled_default is False


def test_camera_entities_include_device_cameras():
    station = entity("SBS50", {})
    station.entity_id = "station-1"
    station.name = "Station"
    station.online = True

    station_camera = entity("SSC0A", {"streamProtocol": "webrtc"})
    station_camera.entity_id = "station-camera"
    station_camera.name = "Station Camera"
    station_camera.online = True

    device_camera = entity("SSC0A", {"streamProtocol": "webrtc"})
    device_camera.entity_id = "device-camera"
    device_camera.name = "Device Camera"
    device_camera.online = True
    device_camera.station = station

    class Coordinator:
        last_update_success = True
        data = {
            "stations": {
                station.entity_id: station,
                station_camera.entity_id: station_camera,
            },
            "devices": {device_camera.entity_id: device_camera},
        }

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    entities = camera._camera_entities(Coordinator())

    assert [entity._dev_id for entity in entities] == [
        station_camera.entity_id,
        device_camera.entity_id,
    ]
    assert entities[0]._station_id is None
    assert entities[1]._station_id == ""
    assert entities[1]._current_entity() is device_camera
    assert entities[1].available is True


async def test_camera_platform_adds_cameras_discovered_after_setup():
    added_entities = []
    listeners = []

    class Coordinator:
        last_update_success = True

        def __init__(self):
            self.data = {"stations": {}, "devices": {}}

        def async_add_listener(self, listener):
            listeners.append(listener)
            return lambda: None

    class Entry:
        entry_id = "entry-id"

        def async_on_unload(self, unload):
            assert callable(unload)

    coordinator = Coordinator()
    hass = SimpleNamespace(data={"xsense": {Entry.entry_id: coordinator}})

    def async_add_entities(entities):
        added_entities.append(list(entities))

    await camera.async_setup_entry(hass, Entry(), async_add_entities)

    discovered_camera = entity("SSC0A", {"streamProtocol": "webrtc"})
    discovered_camera.entity_id = "camera-id"
    discovered_camera.name = "Camera"
    discovered_camera.online = True
    coordinator.data["stations"][discovered_camera.entity_id] = discovered_camera

    listeners[0]()
    listeners[0]()

    assert len(added_entities) == 2
    assert added_entities[0] == []
    assert [entity._dev_id for entity in added_entities[1]] == ["camera-id"]


async def test_camera_motion_binary_is_precreated_without_is_moved_state():
    added_entities = []
    listeners = []
    discovered_camera = entity("SSC0A", {})
    discovered_camera.entity_id = "camera-id"
    discovered_camera.name = "Camera"
    discovered_camera.online = True

    class Coordinator:
        last_update_success = True

        def __init__(self):
            self.data = {
                "stations": {discovered_camera.entity_id: discovered_camera},
                "devices": {},
            }

        def async_add_listener(self, listener):
            listeners.append(listener)
            return lambda: None

    class Entry:
        entry_id = "entry-id"

        def async_on_unload(self, unload):
            assert callable(unload)

    coordinator = Coordinator()
    hass = SimpleNamespace(data={"xsense": {Entry.entry_id: coordinator}})

    await binary_sensor.async_setup_entry(
        hass,
        Entry(),
        lambda entities: added_entities.append(list(entities)),
    )

    motion_entities = [
        item
        for item in added_entities[0]
        if getattr(item.entity_description, "key", None) == "moved"
    ]
    assert len(motion_entities) == 1
    assert motion_entities[0]._dev_id == "camera-id"

    discovered_camera.data["isMoved"] = "1"
    listeners[0]()
    listeners[0]()

    assert sum(
        1
        for batch in added_entities
        for item in batch
        if getattr(item.entity_description, "key", None) == "moved"
    ) == 1


async def test_camera_platform_does_not_duplicate_camera_when_serial_appears_later():
    added_entities = []
    listeners = []
    discovered_camera = entity("SSC0A", {"streamProtocol": "webrtc"})
    discovered_camera.entity_id = "camera-id"
    discovered_camera.name = "Camera"
    discovered_camera.online = True

    class Coordinator:
        last_update_success = True

        def __init__(self):
            self.data = {
                "stations": {discovered_camera.entity_id: discovered_camera},
                "devices": {},
            }

        def async_add_listener(self, listener):
            listeners.append(listener)
            return lambda: None

    class Entry:
        entry_id = "entry-id"

        def async_on_unload(self, unload):
            assert callable(unload)

    coordinator = Coordinator()
    hass = SimpleNamespace(data={"xsense": {Entry.entry_id: coordinator}})

    def async_add_entities(entities):
        added_entities.append(list(entities))

    await camera.async_setup_entry(hass, Entry(), async_add_entities)

    discovered_camera.sn = "CAMERA-SN"
    listeners[0]()

    assert len(added_entities) == 1
    assert [entity._dev_id for entity in added_entities[0]] == ["camera-id"]


def test_camera_entity_description_has_icon():
    assert camera.CAMERA_DESCRIPTION.icon == "mdi:video"


def test_entity_descriptions_have_icon_or_device_class():
    descriptions = [
        *binary_sensor.SENSORS,
        binary_sensor.MQTTSensor,
        *button.BUTTONS,
        camera.CAMERA_DESCRIPTION,
        event.AI_DETECTION_DESCRIPTION,
        event.MOTION_DESCRIPTION,
        *number.NUMBERS,
        *select.SELECTS,
        *sensor.SENSORS,
        *switch.SWITCHES,
    ]

    missing = [
        description.key
        for description in descriptions
        if getattr(description, "icon", None) is None
        and getattr(description, "device_class", None) is None
    ]

    assert missing == []


@pytest.mark.parametrize("device_type", ["XS01-WX", "XS0B-iR", "SC06-WX"])
def test_smoke_alarm_mute_status_exists_before_first_status_payload(device_type):
    smoke = entity(device_type, {})
    description = next(
        item for item in binary_sensor.SENSORS if item.key == "mute_status"
    )

    assert description.exists_fn(smoke)
    assert description.value_fn(smoke) is None


@pytest.mark.parametrize("device_type", ["XS01-WX", "XS0B-iR", "SC06-WX"])
def test_smoke_alarm_led_switch_requires_reported_led_payload(device_type):
    smoke = routed_entity(device_type, {})
    description = next(item for item in switch.SWITCHES if item.key == "led_light")

    assert not description.exists_fn(smoke)

    smoke.data["ledLight"] = "1"

    assert description.exists_fn(smoke)
    assert description.value_fn(smoke) is True


def test_sbs50_alarm_volume_is_not_suppressed_when_reported():
    station = routed_entity("SBS50", {"alarmVol": "75", "alarmTone": "2"})
    description = next(item for item in number.NUMBERS if item.key == "alarm_volume")

    assert description.exists_fn(station)


async def test_smoke_alarm_led_switch_uses_apk_shadow_setting_writer():
    calls = []
    station = SimpleNamespace(
        type="SBS50",
        sn="station-sn",
        shadow_name="SBS50station-sn",
    )
    smoke = SimpleNamespace(
        type="XS01-M",
        sn="device-sn",
        station=station,
        data={"ledLight": "0"},
    )
    xsense = SimpleNamespace(
        update_shadow_setting=AsyncMock(side_effect=lambda *args: calls.append(args))
    )
    coordinator = SimpleNamespace(
        xsense=xsense,
        async_update_listeners=lambda: calls.append(("listeners",)),
    )
    entity = SimpleNamespace(
        coordinator=coordinator,
        entity_description=next(
            item for item in switch.SWITCHES if item.key == "led_light"
        ),
        _current_entity=lambda: smoke,
    )

    await switch.XSenseSwitchEntity._async_set_state(entity, True)

    xsense.update_shadow_setting.assert_awaited_once_with(smoke, "ledLight", "1")
    assert smoke.data["ledLight"] is True
    assert calls == [(smoke, "ledLight", "1"), ("listeners",)]


def test_camera_entities_include_standalone_device_cameras():
    device_camera = entity("SSC0A", {"streamProtocol": "webrtc"})
    device_camera.entity_id = "standalone-camera"
    device_camera.name = "Standalone Camera"
    device_camera.online = True

    class Coordinator:
        data = {
            "stations": {},
            "devices": {device_camera.entity_id: device_camera},
        }

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    entities = camera._camera_entities(Coordinator())

    assert [entity._dev_id for entity in entities] == [device_camera.entity_id]
    assert entities[0]._station_id == ""
    assert entities[0]._current_entity() is device_camera


def test_camera_entities_do_not_duplicate_station_backed_cameras():
    station_camera = entity("SSC0A", {"streamProtocol": "webrtc"})
    station_camera.entity_id = "camera-id"
    station_camera.name = "Station Camera"
    station_camera.online = True

    class Coordinator:
        data = {
            "stations": {station_camera.entity_id: station_camera},
            "devices": {station_camera.entity_id: station_camera},
        }

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    entities = camera._camera_entities(Coordinator())

    assert [entity._dev_id for entity in entities] == [station_camera.entity_id]
    assert entities[0]._station_id is None


def test_camera_entities_do_not_duplicate_station_backed_camera_serials():
    station_camera = entity(
        "SSC0A",
        {"streamProtocol": "webrtc", "addxSerialNumber": "physical-camera"},
    )
    station_camera.entity_id = "station-camera-id"
    station_camera.sn = "cam-sn"
    station_camera.name = "Station Camera"
    station_camera.online = True

    device_camera = entity(
        "SSC0A",
        {"streamProtocol": "webrtc", "addxSerialNumber": "physical-camera"},
    )
    device_camera.entity_id = "device-camera-id"
    device_camera.sn = "CAM-SN"
    device_camera.name = "Device Camera"
    device_camera.online = True

    class Coordinator:
        data = {
            "stations": {station_camera.entity_id: station_camera},
            "devices": {device_camera.entity_id: device_camera},
        }

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    entities = camera._camera_entities(Coordinator())

    assert [entity._dev_id for entity in entities] == [station_camera.entity_id]
    assert entities[0]._station_id is None


def test_camera_entities_keep_distinct_cameras_with_shared_secondary_serial():
    cameras = []
    for index in (1, 2):
        camera_entity = entity(
            "SSC0A",
            {
                "streamProtocol": "webrtc",
                "addxSerialNumber": f"physical-camera-{index}",
            },
        )
        camera_entity.entity_id = f"camera-{index}"
        camera_entity.sn = "shared-label"
        camera_entity.name = f"Camera {index}"
        camera_entity.online = True
        cameras.append(camera_entity)

    class Coordinator:
        data = {
            "stations": {camera.entity_id: camera for camera in cameras},
            "devices": {},
        }

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    entities = camera._camera_entities(Coordinator())

    assert [entity._dev_id for entity in entities] == ["camera-1", "camera-2"]


def test_ai_detection_event_entities_include_standalone_device_cameras():
    device_camera = entity("SSC0A", {"supportPersonDetect": True})
    device_camera.entity_id = "standalone-camera"
    device_camera.name = "Standalone Camera"
    device_camera.online = True

    class Coordinator:
        data = {
            "stations": {},
            "devices": {device_camera.entity_id: device_camera},
        }

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    entities = event._ai_detection_event_entities(Coordinator())

    assert [entity._dev_id for entity in entities] == [device_camera.entity_id]
    assert entities[0]._station_id is None
    assert entities[0]._current_entity() is device_camera


def test_motion_event_entities_include_all_camera_shapes():
    station = entity("SBS50", {})
    station.entity_id = "station-1"
    station.name = "Station"
    station.online = True

    station_camera = entity("SSC0A", {})
    station_camera.entity_id = "station-camera"
    station_camera.name = "Station Camera"
    station_camera.online = True

    device_camera = entity("SSC0A", {})
    device_camera.entity_id = "device-camera"
    device_camera.name = "Device Camera"
    device_camera.online = True
    device_camera.station = station

    standalone_camera = entity("SSC0A", {})
    standalone_camera.entity_id = "standalone-camera"
    standalone_camera.name = "Standalone Camera"
    standalone_camera.online = True

    class Coordinator:
        data = {
            "stations": {
                station.entity_id: station,
                station_camera.entity_id: station_camera,
            },
            "devices": {
                device_camera.entity_id: device_camera,
                standalone_camera.entity_id: standalone_camera,
            },
        }

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    entities = event._motion_event_entities(Coordinator())

    assert [entity._dev_id for entity in entities] == [
        station_camera.entity_id,
        device_camera.entity_id,
        standalone_camera.entity_id,
    ]
    assert entities[0]._station_id is None
    assert entities[1]._station_id == station.entity_id
    assert entities[2]._station_id is None
    assert entities[1]._current_entity() is device_camera
    assert entities[2]._current_entity() is standalone_camera


def test_motion_event_data_uses_apk_history_record_time():
    event_data = event.motion_event_data(
        {
            "eventType": "unknown",
            "eventItems": ["unknown"],
            "eventTime": "20260621134144",
            "traceId": "trace-id",
        }
    )

    assert event_data == {"time": "20260621134144"}
    assert event.motion_fingerprint(event_data) == ("20260621134144",)


def test_motion_event_data_ignores_generic_camera_report_time():
    assert event.motion_event_data({"time": "20260621134144"}) is None


def test_motion_event_data_includes_apk_playback_metadata():
    event_data = event.motion_event_data(
        {
            "eventTime": "20260621134144",
            "playback": {
                "source": "sd_playback",
                "trace_id": "trace-id",
                "start_time": 1782049304,
                "end_time": 1782049314,
                "image_url": "https://example.invalid/snap.jpg",
            },
        }
    )

    assert event_data == {
        "time": "20260621134144",
        "playback": {
            "source": "sd_playback",
            "trace_id": "trace-id",
            "start_time": 1782049304,
            "end_time": 1782049314,
            "image_url": "https://example.invalid/snap.jpg",
        },
        "snapshot_url": "https://example.invalid/snap.jpg",
    }
    assert event.motion_fingerprint(event_data) == ("20260621134144",)


def test_motion_fingerprint_ignores_playback_enrichment_for_same_event():
    mqtt_event = event.motion_event_data({"eventTime": "20260621134144"})
    history_event = event.motion_event_data(
        {
            "eventTime": "20260621134144",
            "playback": {
                "trace_id": "refreshed-trace-id",
                "video_url": "https://example.invalid/refreshed.m3u8",
            },
        }
    )

    assert event.motion_fingerprint(mqtt_event) == event.motion_fingerprint(
        history_event
    )


def test_motion_event_entity_adds_ha_sd_playback_url(monkeypatch):
    camera_entity = entity("SSC0A", {"addxSerialNumber": "ADDX-CAMERA-SN"})
    camera_entity.entity_id = "camera-id"
    camera_entity.name = "Garden Camera"
    camera_entity.sn = "CAMERA-SN"
    event_entity = event.XSenseMotionEventEntity.__new__(
        event.XSenseMotionEventEntity
    )
    event_entity.hass = object()
    event_entity.coordinator = SimpleNamespace(
        entry=SimpleNamespace(entry_id="entry-id")
    )

    monkeypatch.setattr(
        event.er,
        "async_get",
        lambda hass: SimpleNamespace(
            async_get_entity_id=lambda platform, domain, unique_id: "camera.garden"
            if unique_id == "camera-id-thumbnail"
            else None
        ),
    )
    event_data = {
        "time": "20260621134144",
        "playback": {
            "source": "sd_playback",
            "start_time_s": 1782049304,
            "end_time_s": 1782049334,
        },
    }

    event_entity._add_camera_event_context(camera_entity, event_data)
    event_entity._add_motion_playback_url(camera_entity, event_data)

    assert event_data["camera_name"] == "Garden Camera"
    assert event_data["camera_serial"] == "ADDX-CAMERA-SN"
    assert event_data["camera_entity_id"] == "camera.garden"
    assert event_data["recording_url"] == (
        "/xsense-recordings#entry_id=entry-id&serial=ADDX-CAMERA-SN"
        "&start=1782049304&end=1782049334"
    )
    assert event_data["recording_source"] == "sd_playback"


def test_motion_event_entity_derives_recording_url_end_from_period(monkeypatch):
    camera_entity = entity("SSC0A", {})
    camera_entity.entity_id = "camera-id"
    camera_entity.sn = "CAMERA-SN"
    event_entity = event.XSenseMotionEventEntity.__new__(
        event.XSenseMotionEventEntity
    )
    event_entity.hass = object()
    event_entity.coordinator = SimpleNamespace(
        entry=SimpleNamespace(entry_id="entry-id")
    )

    monkeypatch.setattr(
        event.er,
        "async_get",
        lambda hass: SimpleNamespace(
            async_get_entity_id=lambda platform, domain, unique_id: "camera.garden"
            if unique_id == "camera-id-thumbnail"
            else None
        ),
    )
    event_data = {
        "time": "20260621134144",
        "playback": {
            "source": "sd_playback",
            "start_time": 1782049304,
            "period": 30,
        },
    }

    event_entity._add_camera_event_context(camera_entity, event_data)
    event_entity._add_motion_playback_url(camera_entity, event_data)

    assert event_data["recording_url"] == (
        "/xsense-recordings#entry_id=entry-id&serial=camera-id"
        "&start=1782049304&end=1782049334"
    )


def test_motion_event_entity_adds_recordings_link_without_camera_entity(monkeypatch):
    camera_entity = entity("SSC0A", {})
    camera_entity.entity_id = "camera-id"
    camera_entity.sn = "CAMERA-SN"
    event_entity = event.XSenseMotionEventEntity.__new__(
        event.XSenseMotionEventEntity
    )
    event_entity.hass = object()
    event_entity.coordinator = SimpleNamespace(
        entry=SimpleNamespace(entry_id="entry-id")
    )

    monkeypatch.setattr(
        event.er,
        "async_get",
        lambda hass: SimpleNamespace(
            async_get_entity_id=lambda platform, domain, unique_id: None
        ),
    )
    event_data = {
        "time": "20260621134144",
        "playback": {
            "source": "sd_playback",
            "start_time": 1782049304,
            "period": 30,
        },
    }

    event_entity._add_camera_event_context(camera_entity, event_data)
    event_entity._add_motion_playback_url(camera_entity, event_data)

    assert "camera_entity_id" not in event_data
    assert event_data["recording_url"] == (
        "/xsense-recordings#entry_id=entry-id&serial=camera-id"
        "&start=1782049304&end=1782049334"
    )


def test_motion_event_entity_normalizes_ms_recording_times(monkeypatch):
    camera_entity = entity("SSC0A", {})
    camera_entity.entity_id = "camera-id"
    camera_entity.sn = "CAMERA-SN"
    event_entity = event.XSenseMotionEventEntity.__new__(
        event.XSenseMotionEventEntity
    )
    event_entity.hass = object()
    event_entity.coordinator = SimpleNamespace(
        entry=SimpleNamespace(entry_id="entry-id")
    )

    monkeypatch.setattr(
        event.er,
        "async_get",
        lambda hass: SimpleNamespace(
            async_get_entity_id=lambda platform, domain, unique_id: "camera.garden"
            if unique_id == "camera-id-thumbnail"
            else None
        ),
    )
    event_data = {
        "time": "20260621134144",
        "playback": {
            "source": "sd_playback",
            "start_time": 1782049304000,
            "end_time": 1782049334000,
        },
    }

    event_entity._add_camera_event_context(camera_entity, event_data)
    event_entity._add_motion_playback_url(camera_entity, event_data)

    assert event_data["recording_url"] == (
        "/xsense-recordings#entry_id=entry-id&serial=camera-id"
        "&start=1782049304&end=1782049334"
    )


def test_motion_event_entity_replaces_direct_recording_url_with_panel_link(monkeypatch):
    camera_entity = entity("SSC0A", {})
    camera_entity.entity_id = "camera-id"
    camera_entity.sn = "CAMERA-SN"
    event_entity = event.XSenseMotionEventEntity.__new__(
        event.XSenseMotionEventEntity
    )
    event_entity.hass = object()
    event_entity.coordinator = SimpleNamespace(
        entry=SimpleNamespace(entry_id="entry-id")
    )

    event_data = {
        "time": "20260621134144",
        "recording_url": "https://example.invalid/clip.mp4",
        "playback": {
            "source": "sd_playback",
            "start_time_s": 1782049304,
        },
    }

    event_entity._add_motion_playback_url(camera_entity, event_data)

    assert event_data["recording_url"] == (
        "/xsense-recordings#entry_id=entry-id&serial=camera-id"
        "&start=1782049304&end=1782049304"
    )


def test_motion_event_entity_caches_recording_before_trigger(monkeypatch, caplog):
    from custom_components.xsense import recordings_media as media_source

    camera_entity = entity(
        "SSC0A",
        {
            "eventTime": "20260621134144",
            "playback": {
                "source": "sd_playback",
                "trace_id": "trace-id-1",
                "start_time_s": 1782049304,
                "end_time_s": 1782049334,
            },
        },
    )
    camera_entity.sn = "CAMERA-SN"
    camera_entity.entity_id = "camera-id"
    event_entity = event.XSenseMotionEventEntity.__new__(
        event.XSenseMotionEventEntity
    )
    event_entity._motion_initialized = True
    event_entity._last_motion_fingerprint = ("20260621134000",)
    scheduled = []
    order = []
    event_entity.hass = SimpleNamespace(
        async_create_task=lambda coro: scheduled.append(coro)
    )
    event_entity.platform = object()
    event_entity.coordinator = SimpleNamespace(
        entry=SimpleNamespace(entry_id="entry-id")
    )
    event_entity._current_entity = lambda: camera_entity
    event_entity._trigger_event = lambda event_type, data: order.append(
        (
            "trigger",
            event_type,
            data["recording_url"],
            data.get("recording_media_url"),
            data.get("recording_source"),
            data.get("recording_cache_pending"),
            data.get("recording_cache_ready"),
        )
    )
    event_entity.async_write_ha_state = lambda: order.append(("write", None))
    monkeypatch.setattr(
        event.er,
        "async_get",
        lambda hass: SimpleNamespace(
            async_get_entity_id=lambda platform, domain, unique_id: "camera.garden"
        ),
    )

    async def fake_cache_recording_playback(hass, **kwargs):
        order.append(("cache", kwargs["playback"]["trace_id"]))
        return "/media/local/xsense_recordings/videos/CAMERA-SN_1782049304_1782049334.mp4"

    monkeypatch.setattr(
        media_source,
        "async_cache_recording_playback",
        fake_cache_recording_playback,
    )
    ticks = iter([10.0, 10.05, 10.3])
    monkeypatch.setattr(event, "monotonic", lambda: next(ticks))
    caplog.set_level(logging.DEBUG, logger="custom_components.xsense")

    event_entity._handle_coordinator_update()

    assert order == [("write", None)]
    assert len(scheduled) == 1
    asyncio.run(scheduled[0])
    assert order == [
        ("write", None),
        ("cache", "trace-id-1"),
        (
            "trigger",
            "motion",
            "/xsense-recordings#entry_id=entry-id&serial=camera-id"
            "&start=1782049304&end=1782049334",
            "/media/local/xsense_recordings/videos/CAMERA-SN_1782049304_1782049334.mp4",
            "cached_media",
            False,
            True,
        ),
        ("write", None),
    ]
    log_text = caplog.text
    assert "X-Sense event recording cache started" in log_text
    assert "X-Sense event recording cache finished; firing ready trigger" in log_text
    assert "'queue_elapsed_ms': 50" in log_text
    assert "'cache_elapsed_ms': 250" in log_text
    assert "'total_elapsed_ms': 300" in log_text


def test_trigger_camera_event_fires_entity_and_rich_bus_event(caplog):
    fired = []

    class Bus:
        def async_fire(self, event_type, payload):
            fired.append(("bus", event_type, payload))

    event_entity = SimpleNamespace(
        hass=SimpleNamespace(bus=Bus()),
        entity_id="event.garden_motion",
        _trigger_event=lambda event_type, data: fired.append(
            ("entity", event_type, dict(data))
        ),
    )

    caplog.set_level(logging.DEBUG, logger="custom_components.xsense")

    event._trigger_camera_event(
        event_entity,
        "motion",
        {
            "camera_name": "Garden",
            "camera_serial": "CAMERA-SN",
            "recording_url": "/xsense-recordings#entry_id=entry-id",
            "recording_media_url": "/media/local/xsense_recordings/videos/clip.mp4",
            "recording_cache_ready": True,
            "recording_cache_elapsed_ms": 250,
            "recording_total_elapsed_ms": 300,
        },
    )

    assert fired == [
        (
            "entity",
            "motion",
            {
                "camera_name": "Garden",
                "camera_serial": "CAMERA-SN",
                "recording_url": "/xsense-recordings#entry_id=entry-id",
                "recording_media_url": "/media/local/xsense_recordings/videos/clip.mp4",
                "recording_cache_ready": True,
                "recording_cache_elapsed_ms": 250,
                "recording_total_elapsed_ms": 300,
            },
        ),
        (
            "bus",
            event.CAMERA_EVENT_BUS_TYPE,
            {
                "camera_name": "Garden",
                "camera_serial": "CAMERA-SN",
                "recording_url": "/xsense-recordings#entry_id=entry-id",
                "recording_media_url": "/media/local/xsense_recordings/videos/clip.mp4",
                "recording_cache_ready": True,
                "recording_cache_elapsed_ms": 250,
                "recording_total_elapsed_ms": 300,
                "event_type": "motion",
                "event_entity_id": "event.garden_motion",
            },
        ),
    ]
    assert "X-Sense camera event fired for automations" in caplog.text
    assert "'event_entity_id': 'event.garden_motion'" in caplog.text
    assert "'has_recording_url': True" in caplog.text
    assert "'has_recording_media_url': True" in caplog.text
    assert "'recording_cache_ready': True" in caplog.text
    assert "CAMERA-SN" not in caplog.text


def test_motion_event_stores_derived_frame_before_firing(monkeypatch):
    from custom_components.xsense import event as event_module
    from custom_components.xsense import recordings_media as media_source

    scheduled = []
    order = []

    class Coordinator:
        entry = SimpleNamespace(entry_id="entry-id")

        def clear_camera_event_snapshot(self, camera_entity):
            order.append(("clear", camera_entity.sn))

        def store_camera_event_snapshot(self, camera_entity, event_time, image):
            order.append(("store", camera_entity.sn, event_time, image))

    event_entity = SimpleNamespace(
        hass=SimpleNamespace(async_create_task=lambda coro: scheduled.append(coro)),
        coordinator=Coordinator(),
        _trigger_event=lambda event_type, data: order.append(
            ("trigger", event_type, data.get("snapshot_url"))
        ),
    )
    camera_entity = SimpleNamespace(sn="CAMERA-SN")
    event_data = {
        "time": "20260903172848",
        "camera_entity_id": "camera.garden",
        "snapshot_url": "https://example.invalid/event.jpg",
        "playback": {
            "video_url": "https://example.invalid/event.m3u8",
            "start_time_s": 1788449308,
            "end_time_s": 1788449326,
        },
    }

    async def cache_recording(*args, **kwargs):
        order.append(("recording", kwargs["playback"]["video_url"]))
        return "/api/xsense/recordings/play/entry-id/1788449308/1788449326"

    async def extract_snapshot(*args, **kwargs):
        order.append(("extract", args[1]["video_url"]))
        return b"high-resolution-event-frame"

    monkeypatch.setattr(media_source, "async_cache_recording_playback", cache_recording)
    monkeypatch.setattr(
        media_source, "async_extract_camera_event_snapshot", extract_snapshot
    )

    assert event_module._trigger_event_after_recording_cache(
        event_entity, "motion", camera_entity, event_data
    )
    asyncio.run(scheduled[0])

    assert order == [
        ("clear", "CAMERA-SN"),
        ("recording", "https://example.invalid/event.m3u8"),
        ("extract", "https://example.invalid/event.m3u8"),
        (
            "store",
            "CAMERA-SN",
            "20260903172848",
            b"high-resolution-event-frame",
        ),
        ("trigger", "motion", "/api/camera_proxy/camera.garden"),
    ]


def test_motion_event_still_fires_when_snapshot_extraction_fails(monkeypatch):
    from custom_components.xsense import event as event_module
    from custom_components.xsense import recordings_media as media_source

    scheduled = []
    triggered = []
    event_entity = SimpleNamespace(
        hass=SimpleNamespace(async_create_task=lambda coro: scheduled.append(coro)),
        coordinator=SimpleNamespace(entry=SimpleNamespace(entry_id="entry-id")),
        _trigger_event=lambda event_type, data: triggered.append(
            (event_type, data.get("snapshot_url"))
        ),
    )
    event_data = {
        "time": "20260903172848",
        "camera_entity_id": "camera.garden",
        "snapshot_url": "https://example.invalid/event.jpg",
        "playback": {
            "video_url": "https://example.invalid/event.m3u8",
            "start_time_s": 1788449308,
            "end_time_s": 1788449326,
        },
    }

    async def cache_recording(*args, **kwargs):
        return "/api/xsense/recordings/play/entry-id/1788449308/1788449326"

    async def fail_snapshot(*args, **kwargs):
        raise RuntimeError("snapshot unavailable")

    monkeypatch.setattr(media_source, "async_cache_recording_playback", cache_recording)
    monkeypatch.setattr(
        media_source, "async_extract_camera_event_snapshot", fail_snapshot
    )

    assert event_module._trigger_event_after_recording_cache(
        event_entity,
        "motion",
        SimpleNamespace(sn="CAMERA-SN"),
        event_data,
    )
    asyncio.run(scheduled[0])

    assert triggered == [("motion", "https://example.invalid/event.jpg")]


def test_motion_event_entity_updates_state_only_when_recording_cache_returns_no_media(
    monkeypatch,
    caplog,
):
    from custom_components.xsense import recordings_media as media_source

    camera_entity = entity(
        "SSC0A",
        {
            "eventTime": "20260621134144",
            "playback": {
                "source": "sd_playback",
                "trace_id": "trace-id-1",
                "start_time_s": 1782049304,
                "end_time_s": 1782049334,
            },
        },
    )
    camera_entity.sn = "CAMERA-SN"
    camera_entity.entity_id = "camera-id"
    event_entity = event.XSenseMotionEventEntity.__new__(
        event.XSenseMotionEventEntity
    )
    event_entity._motion_initialized = True
    event_entity._last_motion_fingerprint = ("20260621134000",)
    scheduled = []
    triggered = []
    event_entity.hass = SimpleNamespace(
        async_create_task=lambda coro: scheduled.append(coro)
    )
    event_entity.platform = object()
    event_entity.coordinator = SimpleNamespace(
        entry=SimpleNamespace(entry_id="entry-id")
    )
    event_entity._current_entity = lambda: camera_entity
    event_entity._trigger_event = lambda event_type, data: triggered.append(
        ("trigger", dict(data))
    )
    event_entity.async_write_ha_state = lambda: triggered.append(("write", None))
    monkeypatch.setattr(
        event.er,
        "async_get",
        lambda hass: SimpleNamespace(
            async_get_entity_id=lambda platform, domain, unique_id: "camera.garden"
        ),
    )

    async def fake_cache_recording_playback(hass, **kwargs):
        return ""

    monkeypatch.setattr(
        media_source,
        "async_cache_recording_playback",
        fake_cache_recording_playback,
    )

    event_entity._handle_coordinator_update()
    caplog.set_level(logging.DEBUG, logger="custom_components.xsense")
    asyncio.run(scheduled[0])

    assert triggered == [("write", None), ("write", None)]
    assert "ready event not fired" in caplog.text


def test_motion_event_cache_replaces_absolute_recordings_panel_url(monkeypatch):
    from custom_components.xsense import event as event_module

    scheduled = []
    triggered = []

    class Hass:
        def async_create_task(self, coro):
            scheduled.append(coro)

    event_entity = SimpleNamespace(
        hass=Hass(),
        coordinator=SimpleNamespace(entry=SimpleNamespace(entry_id="entry-id")),
        _trigger_event=lambda event_type, data: triggered.append(dict(data)),
    )
    entity_obj = SimpleNamespace(sn="CAMERA-SN")
    event_data = {
        "camera_entity_id": "camera.garden",
        "recording_url": (
            "https://ha.example.invalid/xsense-recordings#entry_id=entry-id"
            "&serial=CAMERA-SN&start=1782049304&end=1782049334"
        ),
        "playback": {
            "source": "sd_playback",
            "start_time_s": 1782049304,
            "end_time_s": 1782049334,
        },
    }

    async def cache_recording(*args, **kwargs):
        return "/media/local/xsense_recordings/videos/clip.mp4"

    monkeypatch.setattr(
        "custom_components.xsense.recordings_media.async_cache_recording_playback",
        cache_recording,
    )

    assert event_module._trigger_event_after_recording_cache(
        event_entity,
        "motion",
        entity_obj,
        event_data,
    )
    asyncio.run(scheduled[0])

    assert len(triggered) == 1
    assert triggered[0]["recording_url"] == (
        "/xsense-recordings#entry_id=entry-id&serial=CAMERA-SN"
        "&start=1782049304&end=1782049334"
    )
    assert (
        triggered[0]["recording_media_url"]
        == "/media/local/xsense_recordings/videos/clip.mp4"
    )


def test_motion_event_cache_replaces_raw_recording_url_with_panel_link(
    monkeypatch,
):
    from custom_components.xsense import event as event_module

    scheduled = []
    triggered = []

    class Hass:
        def async_create_task(self, coro):
            scheduled.append(coro)

    event_entity = SimpleNamespace(
        hass=Hass(),
        coordinator=SimpleNamespace(entry=SimpleNamespace(entry_id="entry-id")),
        _trigger_event=lambda event_type, data: triggered.append(dict(data)),
    )
    entity_obj = SimpleNamespace(sn="CAMERA-SN")
    event_data = {
        "recording_url": "https://example.invalid/clip.mp4",
        "playback": {
            "source": "video_url",
            "start_time_s": 1782049304,
            "end_time_s": 1782049334,
        },
    }

    async def cache_recording(*args, **kwargs):
        return "/media/local/xsense_recordings/videos/clip.mp4"

    monkeypatch.setattr(
        "custom_components.xsense.recordings_media.async_cache_recording_playback",
        cache_recording,
    )

    assert event_module._trigger_event_after_recording_cache(
        event_entity,
        "motion",
        entity_obj,
        event_data,
    )
    asyncio.run(scheduled[0])

    assert len(triggered) == 1
    assert triggered[0]["recording_url"] == (
        "/xsense-recordings#entry_id=entry-id&serial=CAMERA-SN"
        "&start=1782049304&end=1782049334"
    )
    assert (
        triggered[0]["recording_media_url"]
        == "/media/local/xsense_recordings/videos/clip.mp4"
    )


def test_motion_event_cache_does_not_schedule_without_entry_id():
    from custom_components.xsense import event as event_module

    scheduled = []
    triggered = []
    event_entity = SimpleNamespace(
        hass=SimpleNamespace(async_create_task=lambda coro: scheduled.append(coro)),
        _trigger_event=lambda event_type, data: triggered.append(dict(data)),
    )

    result = event_module._trigger_event_after_recording_cache(
        event_entity,
        "motion",
        SimpleNamespace(sn="CAMERA-SN"),
        {
            "playback": {
                "source": "sd_playback",
                "start_time_s": 1782049304,
                "end_time_s": 1782049334,
            },
        },
    )

    assert result is False
    assert scheduled == []
    assert triggered == []


def test_recordings_panel_url_detection_rejects_lookalikes():
    assert event._is_recordings_panel_url("/xsense-recordings")
    assert event._is_recordings_panel_url(
        "/xsense-recordings#entry_id=entry-id&serial=CAMERA-SN"
    )
    assert not event._is_recordings_panel_url(
        "https://ha.example.invalid/xsense-recordings#entry_id=entry-id"
    )
    assert not event._is_recordings_panel_url("/xsense-recordings-bad#entry_id=x")
    assert not event._is_recordings_panel_url("https://example.invalid/clip.mp4")


def test_recording_media_source_ignores_time_only_record_without_direct_video_url():
    from custom_components.xsense import recordings_media as media_source

    cameras = [
        {
            "entry_id": "entry-id",
            "serial": "CAMERA-SN",
            "entity_id": "camera.garden",
            "name": "Garden",
        }
    ]
    clip = media_source._recording_clip_from_record(
        "entry-id",
        cameras,
        {
            "serialNumber": "CAMERA-SN",
            "startTime": 1782049304000,
            "endTime": 1782049334000,
            "imageUrl": "https://example.invalid/snap.jpg",
        },
    )

    assert clip is None


def test_recording_clip_from_playback_accepts_raw_apk_time_fields():
    from custom_components.xsense import recordings_media as media_source

    clip = media_source._recording_clip_from_playback(
        "entry-id",
        "CAMERA-SN",
        "camera.garden",
        {
            "source": "video_url",
            "start_time": 1782049304,
            "period": 30,
            "video_url": "https://example.invalid/clip.m3u8",
        },
    )

    assert clip["start"] == 1782049304
    assert clip["end"] == 1782049334
    assert clip["playback_url"] == "https://example.invalid/clip.m3u8"
    assert clip["source"] == "video_url"


def test_recording_clip_from_playback_normalizes_ms_time_fields():
    from custom_components.xsense import recordings_media as media_source

    clip = media_source._recording_clip_from_playback(
        "entry-id",
        "CAMERA-SN",
        "camera.garden",
        {
            "source": "video_url",
            "start_time": 1782049304000,
            "end_time": 1782049334000,
            "video_url": "https://example.invalid/clip.m3u8",
        },
    )

    assert clip["start"] == 1782049304
    assert clip["end"] == 1782049334
    assert clip["playback_url"] == "https://example.invalid/clip.m3u8"


def test_recording_media_source_preserves_direct_video_url():
    from custom_components.xsense import recordings_media as media_source

    clip = media_source._recording_clip_from_record(
        "entry-id",
        [
            {
                "entry_id": "entry-id",
                "serial": "CAMERA-SN",
                "entity_id": "camera.garden",
            }
        ],
        {
            "serialNumber": "CAMERA-SN",
            "timestamp": 1782049304000,
            "videoUrl": "https://example.invalid/clip.mp4",
        },
    )

    assert clip["source"] == "video_url"
    assert clip["quality"] == "HD"
    assert clip["playback_url"] == "https://example.invalid/clip.mp4"
    assert clip["cached_url"].endswith(
        "/media/local/xsense_recordings/videos/CAMERA-SN_1782049304_1782049304.mp4"
    )


def test_recording_media_source_matches_addx_camera_serial_alias():
    from custom_components.xsense import recordings_media as media_source

    clip = media_source._recording_clip_from_record(
        "entry-id",
        [
            {
                "entry_id": "entry-id",
                "serial": "IPC-CAMERA-SN",
                "addx_serial": "addx-camera-sn",
                "entity_id": "camera.garden",
            }
        ],
        {
            "serialNumber": "ADDX_CAMERA_SN",
            "timestamp": 1782049304000,
            "videoUrl": "https://example.invalid/clip.m3u8",
        },
    )

    assert clip is not None
    assert clip["serial"] == "IPC-CAMERA-SN"


def test_recording_media_rejects_shared_secondary_camera_label():
    from custom_components.xsense import recordings_media as media_source

    cameras = [
        {
            "entry_id": "entry-id",
            "serial": f"camera-{index}",
            "entity_id": f"camera-{index}",
            "identifiers": [f"camera-{index}", "shared-label"],
        }
        for index in (1, 2)
    ]

    assert (
        media_source._recording_camera_for_identifier(cameras, "shared-label")
        is None
    )
    assert (
        media_source._recording_camera_for_identifier(cameras, "camera-2")
        is cameras[1]
    )


def test_recording_index_rejects_legacy_weak_camera_identity():
    from custom_components.xsense import recordings_media as media_source

    current = [
        {
            "entry_id": "entry-id",
            "serial": "physical-camera-1",
            "entity_id": "camera-1",
            "identifiers": ["physical-camera-1", "shared-label"],
        },
        {
            "entry_id": "entry-id",
            "serial": "physical-camera-2",
            "entity_id": "camera-2",
            "identifiers": ["physical-camera-2", "shared-label"],
        },
    ]
    legacy_index = {
        "cameras": [{"entry_id": "entry-id", "serial": "shared-label"}]
    }
    current_index = {"cameras": current}

    assert not media_source._recording_index_matches_cameras(
        legacy_index, current
    )
    assert media_source._recording_index_matches_cameras(current_index, current)


def test_recording_media_keeps_cameras_with_shared_secondary_label_separate():
    from custom_components.xsense import recordings_media as media_source

    cameras = [
        SimpleNamespace(
            type="SSC0A",
            entity_type=None,
            entity_id=f"camera-{index}",
            sn="shared-label",
            data={"addxSerialNumber": f"camera-{index}"},
            name=f"Camera {index}",
            online=True,
        )
        for index in (1, 2)
    ]
    coordinator = SimpleNamespace(
        data={"stations": {camera.entity_id: camera for camera in cameras}}
    )

    indexed = media_source._coordinator_cameras(coordinator, "entry-id")

    assert [camera["serial"] for camera in indexed] == ["camera-1", "camera-2"]
    assert all("shared-label" in camera["identifiers"] for camera in indexed)


def test_recording_media_source_prefers_hd_direct_video_candidate():
    from custom_components.xsense import recordings_media as media_source

    clip = media_source._recording_clip_from_playback(
        "entry-id",
        "CAMERA-SN",
        "camera.garden",
        {
            "source": "sd_playback",
            "start_time_s": 1782049304,
            "end_time_s": 1782049334,
            "video_url": "https://example.invalid/default.mp4",
            "multi_resolution_videos": [
                {
                    "resolution": "640x360",
                    "url": "https://example.invalid/sd.mp4",
                },
                {
                    "resolution": "1920x1080",
                    "url": "https://example.invalid/hd.mp4",
                },
            ],
        },
    )

    assert clip["quality"] == "HD"
    assert clip["source"] == "video_url"
    assert clip["playback_url"] == "https://example.invalid/hd.mp4"


def test_recording_media_source_prefers_sd_direct_video_candidate_when_requested():
    from custom_components.xsense import recordings_media as media_source

    clip = media_source._recording_clip_from_playback(
        "entry-id",
        "CAMERA-SN",
        "camera.garden",
        {
            "source": "video_url",
            "start_time_s": 1782049304,
            "end_time_s": 1782049334,
            "video_url": "https://example.invalid/hd.mp4",
            "multi_resolution_videos": [
                {
                    "resolution": "640x360",
                    "url": "https://example.invalid/sd.mp4",
                },
                {
                    "resolution": "1920x1080",
                    "url": "https://example.invalid/hd.mp4",
                },
            ],
        },
        quality="SD",
    )

    assert clip["quality"] == "SD"
    assert clip["source"] == "video_url"
    assert clip["requested_source"] == "video_url"
    assert clip["playback_url"] == "https://example.invalid/sd.mp4"


def test_recording_media_source_requires_direct_url_for_playable_clip():
    from custom_components.xsense import recordings_media as media_source

    assert media_source._clip_media_playable(
        {"source": "video_url", "playback_url": "https://example.invalid/clip.mp4"}
    )
    assert not media_source._clip_media_playable(
        {"source": "sd_playback", "playback_url": "/xsense/recording/entry/sn/1"}
    )


def test_recording_media_source_clip_duration_uses_normalized_bounds():
    from custom_components.xsense import recordings_media as media_source

    assert media_source._clip_duration({"start": 100, "end": 130}) == 30
    assert media_source._clip_duration({"start": 100, "end": 100}) is None
    assert media_source._clip_duration({"start": 100, "end": "bad"}) is None


def test_cache_recording_playback_returns_cached_media_url(monkeypatch, tmp_path):
    from custom_components.xsense import recordings_media as media_source
    from custom_components.xsense.const import CONF_RECORDING_CACHE_MODE

    ready = False

    async def cached_url(self, clip):
        nonlocal ready
        ready = True
        return "/media/local/xsense_custom/videos/CAMERA-SN_1782049304_1782049334.mp4"

    monkeypatch.setattr(
        media_source,
        "_recording_media_root",
        lambda hass, entry_id: tmp_path,
    )
    monkeypatch.setattr(
        media_source.XSenseRecordingsMediaSource,
        "_async_cached_playback_url",
        cached_url,
    )
    monkeypatch.setattr(media_source, "_path_ready", lambda path: ready)
    monkeypatch.setattr(media_source, "_mp4_ready", lambda path: ready)
    monkeypatch.setattr(
        media_source,
        "_local_media_url",
        lambda path: "/media/local/xsense_custom/videos/CAMERA-SN_1782049304_1782049334.mp4",
    )

    entry = SimpleNamespace(options={CONF_RECORDING_CACHE_MODE: "retained"})
    result = asyncio.run(
        media_source.async_cache_recording_playback(
            SimpleNamespace(
                data={media_source.DOMAIN: {}},
                config_entries=SimpleNamespace(
                    async_get_entry=lambda entry_id: entry
                ),
            ),
            entry_id="entry-id",
            entity=SimpleNamespace(sn="CAMERA-SN"),
            playback={
                "source": "video_url",
                "start_time_s": 1782049304,
                "end_time_s": 1782049334,
                "video_url": "https://example.invalid/clip.m3u8",
            },
            camera_entity_id="camera.garden",
        )
    )

    assert result == (
        "/media/local/xsense_custom/videos/CAMERA-SN_1782049304_1782049334.mp4"
    )


def test_recording_playback_only_returns_proxy_url_without_caching(monkeypatch, tmp_path):
    from custom_components.xsense import recordings_media as media_source

    monkeypatch.setattr(
        media_source,
        "_recording_media_root",
        lambda hass, entry_id: tmp_path,
    )
    monkeypatch.setattr(
        media_source.XSenseRecordingsMediaSource,
        "_async_cached_playback_url",
        lambda *args: pytest.fail("playback-only events must not download the clip"),
    )
    hass = SimpleNamespace(
        data={media_source.DOMAIN: {}},
        config_entries=SimpleNamespace(
            async_get_entry=lambda entry_id: SimpleNamespace(options={})
        ),
    )

    result = asyncio.run(
        media_source.async_cache_recording_playback(
            hass,
            entry_id="entry-id",
            entity=SimpleNamespace(sn="CAMERA-SN"),
            playback={
                "source": "video_url",
                "start_time_s": 1782049304,
                "end_time_s": 1782049334,
                "video_url": "https://example.invalid/clip.m3u8",
            },
        )
    )

    assert result == (
        "/api/xsense/recordings/play/entry-id/1782049304/1782049334"
        "?serial=CAMERA-SN"
    )


def test_cache_recording_playback_does_not_trust_unvalidated_cache_url(
    monkeypatch,
    tmp_path,
):
    from custom_components.xsense import recordings_media as media_source

    async def cached_url(self, clip):
        return "/media/local/xsense_custom/videos/not-actually-ready.mp4"

    monkeypatch.setattr(
        media_source,
        "_recording_media_root",
        lambda hass, entry_id: tmp_path,
    )
    monkeypatch.setattr(
        media_source.XSenseRecordingsMediaSource,
        "_async_cached_playback_url",
        cached_url,
    )
    monkeypatch.setattr(media_source, "_mp4_ready", lambda path: False)

    result = asyncio.run(
        media_source.async_cache_recording_playback(
            SimpleNamespace(data={media_source.DOMAIN: {}}),
            entry_id="entry-id",
            entity=SimpleNamespace(sn="CAMERA-SN"),
            playback={
                "source": "sd_playback",
                "start_time_s": 1782049304,
                "end_time_s": 1782049334,
            },
            camera_entity_id="camera.garden",
        )
    )

    assert result == ""


def test_cache_recording_playback_requires_linkable_media_url(monkeypatch, tmp_path):
    from custom_components.xsense import recordings_media as media_source

    async def cached_url(self, clip):
        return "/media/local/xsense_custom/videos/clip.mp4"

    monkeypatch.setattr(
        media_source,
        "_recording_media_root",
        lambda hass, entry_id: tmp_path,
    )
    monkeypatch.setattr(
        media_source.XSenseRecordingsMediaSource,
        "_async_cached_playback_url",
        cached_url,
    )
    monkeypatch.setattr(media_source, "_mp4_ready", lambda path: True)
    monkeypatch.setattr(media_source, "_local_media_url", lambda path: "")

    result = asyncio.run(
        media_source.async_cache_recording_playback(
            SimpleNamespace(data={media_source.DOMAIN: {}}),
            entry_id="entry-id",
            entity=SimpleNamespace(sn="CAMERA-SN"),
            playback={
                "source": "sd_playback",
                "start_time_s": 1782049304,
                "end_time_s": 1782049334,
            },
            camera_entity_id="camera.garden",
        )
    )

    assert result == ""


def test_recording_media_source_resolve_includes_local_path(monkeypatch, tmp_path):
    from custom_components.xsense import recordings_media as media_source
    from custom_components.xsense.const import CONF_RECORDING_CACHE_MODE

    entry = SimpleNamespace(options={CONF_RECORDING_CACHE_MODE: "retained"})
    source = media_source.XSenseRecordingsMediaSource(
        _recordings_media_source_hass(
            config_entries=SimpleNamespace(
                async_get_entry=lambda entry_id: entry
            )
        )
    )
    output_path = tmp_path / "clip.mp4"
    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "start": 1782049304,
        "end": 1782049334,
        "playback_url": "/xsense/recording/entry-id/1782049304?serial=CAMERA-SN",
        "media_root": tmp_path.as_posix(),
    }

    async def load_index():
        return {
            "cameras": [
                {
                    "entry_id": "entry-id",
                    "serial": "CAMERA-SN",
                    "clips": [clip],
                }
            ]
        }

    async def cached_url(current_clip):
        assert current_clip is clip
        return "/media/local/custom.mp4"

    monkeypatch.setattr(source, "_async_load_index", load_index)
    monkeypatch.setattr(source, "_async_cached_playback_url", cached_url)
    monkeypatch.setattr(media_source, "_clip_cache_path", lambda current_clip: output_path)
    monkeypatch.setattr(media_source, "_path_ready", lambda path: path == output_path)
    monkeypatch.setattr(media_source, "_mp4_ready", lambda path: path == output_path)

    resolved = asyncio.run(
        source.async_resolve_media(
            SimpleNamespace(
                identifier=media_source.build_identifier(
                    {
                        "entry_id": "entry-id",
                        "serial": "CAMERA-SN",
                        "start": "1782049304",
                    }
                )
            )
        )
    )

    assert resolved.url == "/media/local/custom.mp4"
    assert resolved.mime_type == media_source.MIME_TYPE
    assert resolved.path == output_path


def test_recording_media_source_playback_only_resolves_proxy_without_local_path(
    monkeypatch,
):
    from custom_components.xsense import recordings_media as media_source

    source = media_source.XSenseRecordingsMediaSource(
        _recordings_media_source_hass(
            config_entries=SimpleNamespace(
                async_get_entry=lambda entry_id: SimpleNamespace(options={})
            )
        )
    )
    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "start": 1782049304,
        "end": 1782049334,
        "source": "video_url",
        "playback_url": "https://example.invalid/clip.m3u8",
    }

    async def load_index():
        return {
            "cameras": [
                {
                    "entry_id": "entry-id",
                    "serial": "CAMERA-SN",
                    "clips": [clip],
                }
            ]
        }

    monkeypatch.setattr(source, "_async_load_index", load_index)
    monkeypatch.setattr(
        source,
        "_async_cached_playback_url",
        lambda *args: pytest.fail("playback-only media must not download the clip"),
    )

    resolved = asyncio.run(
        source.async_resolve_media(
            SimpleNamespace(
                identifier=media_source.build_identifier(
                    {
                        "entry_id": "entry-id",
                        "serial": "CAMERA-SN",
                        "start": "1782049304",
                    }
                )
            )
        )
    )

    assert resolved.url.endswith(
        "/entry-id/1782049304/1782049334?serial=CAMERA-SN"
    )
    assert resolved.mime_type == media_source.HLS_MIME_TYPE
    assert resolved.path is None


def test_recording_media_source_does_not_fall_back_to_external_video_url(
    monkeypatch,
    tmp_path,
):
    from custom_components.xsense import recordings_media as media_source

    source = media_source.XSenseRecordingsMediaSource(_recordings_media_source_hass())
    clip = {
        "source": "video_url",
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "start": 1782049304,
        "end": 1782049334,
        "playback_url": "https://example.invalid/clip.mp4",
        "media_root": tmp_path.as_posix(),
    }

    async def download_direct_clip(url, output_path):
        raise RuntimeError("download failed")

    monkeypatch.setattr(source, "_async_download_direct_clip", download_direct_clip)
    monkeypatch.setattr(media_source, "_path_ready", lambda path: False)

    with pytest.raises(media_source.Unresolvable):
        asyncio.run(source._async_cached_playback_url(clip))


def test_recording_media_source_rejects_non_mp4_direct_cache(tmp_path):
    from custom_components.xsense import recordings_media as media_source

    empty_path = tmp_path / "empty.mp4"
    empty_path.write_bytes(b"")
    html_path = tmp_path / "clip.mp4"
    html_path.write_bytes(b"<html>not video</html>")
    fake_path = tmp_path / "fake.mp4"
    fake_path.write_bytes(b"not really an mp4 ftyp nope")
    mp4_path = tmp_path / "ready.mp4"
    mp4_path.write_bytes(b"\x00\x00\x00\x10ftypmp42\x00\x00\x00\x00video")

    assert not media_source._mp4_ready(empty_path)
    assert not media_source._mp4_ready(html_path)
    assert not media_source._mp4_ready(fake_path)
    assert media_source._mp4_ready(mp4_path)


def test_recording_media_source_does_not_fall_back_to_sd_when_direct_download_not_media(
    monkeypatch,
    tmp_path,
):
    from homeassistant.components.media_source.error import Unresolvable

    from custom_components.xsense import recordings_media as media_source

    source = media_source.XSenseRecordingsMediaSource(_recordings_media_source_hass())
    output_path = tmp_path / "clip.mp4"
    clip = {
        "source": "video_url",
        "quality": "HD",
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "start": 1782049304,
        "end": 1782049334,
        "playback_url": "https://example.invalid/clip.mp4",
        "media_root": tmp_path.as_posix(),
    }
    class Response:
        headers = {"content-type": "text/html"}

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self):
            return None

        async def read(self):
            return b"<html>expired</html>"

    class Session:
        def get(self, url):
            return Response()

    class Hass:
        async def async_add_executor_job(self, func, *args):
            return func(*args)

    source.hass = Hass()

    monkeypatch.setattr(
        media_source,
        "_hls_cache_dir",
        lambda current_clip: tmp_path / "hls",
    )
    monkeypatch.setattr(
        media_source,
        "_hls_playlist_cache_path",
        lambda current_clip: tmp_path / "hls" / "index.m3u8",
    )
    monkeypatch.setattr(
        media_source,
        "_clip_cache_path",
        lambda current_clip: output_path,
    )
    monkeypatch.setattr(
        media_source,
        "async_get_clientsession",
        lambda hass: Session(),
    )
    with pytest.raises(Unresolvable):
        asyncio.run(source._async_cached_playback_url(clip))

    assert not output_path.exists()


def test_recording_media_source_caches_hd_hls_without_sd_fallback(
    monkeypatch,
    tmp_path,
):
    from custom_components.xsense import recordings_media as media_source

    monkeypatch.setattr(
        media_source,
        "_categorize_hls_leading_segment",
        lambda path, **kwargs: {
            "leading_aac": media_source.HLS_LEADING_AAC_OK,
            "leading_segment": path.name,
            "playback_mode": media_source.HLS_PLAYBACK_MODE_NORMAL,
        },
    )
    source = media_source.XSenseRecordingsMediaSource(_recordings_media_source_hass())
    output_path = tmp_path / "clip.mp4"
    clip = {
        "source": "video_url",
        "quality": "HD",
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "start": 1782049304,
        "end": 1782049334,
        "playback_url": "https://example.invalid/index.m3u8",
        "media_root": tmp_path.as_posix(),
    }
    responses = {
        "https://example.invalid/index.m3u8": (
            "application/vnd.apple.mpegurl;charset=utf-8",
            b"#EXTM3U\n#EXT-X-TARGETDURATION:4\nseg-1.ts\nseg-2.ts\nseg-3.ts\n#EXT-X-ENDLIST\n",
        ),
        "https://example.invalid/seg-1.ts": ("video/mp2t", b"segment-one"),
        "https://example.invalid/seg-2.ts": ("video/mp2t", b"segment-two"),
        "https://example.invalid/seg-3.ts": ("video/mp2t", b"segment-three"),
    }

    class Response:
        def __init__(self, url):
            self.content_type, self.payload = responses[url]
            self.headers = {"content-type": self.content_type}

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self):
            return None

        async def read(self):
            return self.payload

        async def text(self):
            return self.payload.decode()

    class Session:
        def get(self, url):
            return Response(url)

    class Hass:
        async def async_add_executor_job(self, func, *args):
            return func(*args)

    source.hass = Hass()
    monkeypatch.setattr(
        media_source,
        "_hls_cache_dir",
        lambda current_clip: tmp_path / "hls",
    )
    monkeypatch.setattr(
        media_source,
        "_hls_playlist_cache_path",
        lambda current_clip: tmp_path / "hls" / "index.m3u8",
    )
    monkeypatch.setattr(
        media_source,
        "_local_media_url",
        lambda path: f"/media/local/test/{path.name}",
    )
    monkeypatch.setattr(
        media_source,
        "_clip_cache_path",
        lambda current_clip: output_path,
    )
    monkeypatch.setattr(
        media_source,
        "async_get_clientsession",
        lambda hass: Session(),
    )
    result = asyncio.run(source._async_cached_playback_url(clip))

    playlist = media_source._hls_playlist_cache_path(clip)
    assert result == "/media/local/test/index.m3u8"
    assert media_source._hls_ready(clip)
    assert playlist.read_text(encoding="utf-8") == (
        "#EXTM3U\n"
        "#EXT-X-TARGETDURATION:4\n"
        "segment_0002.ts\n"
        "segment_0003.ts\n"
        "segment_0004.ts\n"
        "#EXT-X-ENDLIST\n"
    )
    assert (playlist.parent / "segment_0002.ts").read_bytes() == b"segment-one"
    assert (playlist.parent / "segment_0003.ts").read_bytes() == b"segment-two"
    assert (playlist.parent / "segment_0004.ts").read_bytes() == b"segment-three"


def test_recording_media_source_preserves_original_leading_hls_ts_segment(
    monkeypatch,
    tmp_path,
):
    from custom_components.xsense import recordings_media as media_source

    monkeypatch.setattr(
        media_source,
        "_categorize_hls_leading_segment",
        lambda path, **kwargs: {
            "leading_aac": media_source.HLS_LEADING_AAC_OK,
            "leading_segment": path.name,
            "playback_mode": media_source.HLS_PLAYBACK_MODE_NORMAL,
        },
    )
    source = media_source.XSenseRecordingsMediaSource(_recordings_media_source_hass())
    output_path = tmp_path / "clip.mp4"
    clip = {
        "source": "video_url",
        "quality": "HD",
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "start": 1782049304,
        "end": 1782049334,
        "playback_url": "https://example.invalid/index.m3u8",
        "media_root": tmp_path.as_posix(),
    }
    responses = {
        "https://example.invalid/index.m3u8": (
            "application/vnd.apple.mpegurl;charset=utf-8",
            b"#EXTM3U\n#EXT-X-TARGETDURATION:4\nseg-1.ts\nseg-2.ts\n#EXT-X-ENDLIST\n",
        ),
        "https://example.invalid/seg-1.ts": ("video/mp2t", b"bad-leading-audio"),
        "https://example.invalid/seg-2.ts": ("video/mp2t", b"good-audio-video"),
    }
    class Response:
        def __init__(self, url):
            self.content_type, self.payload = responses[url]
            self.headers = {"content-type": self.content_type}

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self):
            return None

        async def read(self):
            return self.payload

        async def text(self):
            return self.payload.decode()

    class Session:
        def get(self, url):
            return Response(url)

    class Hass:
        async def async_add_executor_job(self, func, *args):
            return func(*args)

    source.hass = Hass()
    monkeypatch.setattr(
        media_source,
        "_hls_cache_dir",
        lambda current_clip: tmp_path / "hls",
    )
    monkeypatch.setattr(
        media_source,
        "_hls_playlist_cache_path",
        lambda current_clip: tmp_path / "hls" / "index.m3u8",
    )
    monkeypatch.setattr(
        media_source,
        "_local_media_url",
        lambda path: f"/media/local/test/{path.name}",
    )
    monkeypatch.setattr(
        media_source,
        "_clip_cache_path",
        lambda current_clip: output_path,
    )
    monkeypatch.setattr(
        media_source,
        "async_get_clientsession",
        lambda hass: Session(),
    )
    playlist = media_source._hls_playlist_cache_path(clip)
    playlist.parent.mkdir(parents=True)
    stale_file = playlist.parent / "stale_segment.ts"
    stale_file.write_bytes(b"stale")

    result = asyncio.run(source._async_cached_playback_url(clip))

    assert result == "/media/local/test/index.m3u8"
    assert not stale_file.exists()
    assert playlist.read_text(encoding="utf-8") == (
        "#EXTM3U\n"
        "#EXT-X-TARGETDURATION:4\n"
        "segment_0002.ts\n"
        "segment_0003.ts\n"
        "#EXT-X-ENDLIST\n"
    )
    assert (playlist.parent / "segment_0002.ts").read_bytes() == b"bad-leading-audio"
    assert (playlist.parent / "segment_0003.ts").read_bytes() == b"good-audio-video"
    profile = media_source._read_hls_playback_profile(playlist.parent)
    assert profile["leading_aac"] == media_source.HLS_LEADING_AAC_OK
    assert profile["playback_mode"] == media_source.HLS_PLAYBACK_MODE_NORMAL


def test_recording_media_source_prepares_broken_leading_hls_segment_for_playback(
    monkeypatch,
    tmp_path,
):
    from custom_components.xsense import recordings_media as media_source

    def _broken_leading_profile(path, **kwargs):
        sidecar = media_source._hls_leading_playback_segment_path(path)
        sidecar.write_bytes(b"silent-aac-sidecar")
        return {
            "leading_aac": media_source.HLS_LEADING_AAC_BROKEN,
            "leading_segment": path.name,
            "leading_playback_segment": sidecar.name,
            "playback_mode": media_source.HLS_PLAYBACK_MODE_IGNORE_LEADING_AAC,
            "leading_playback_verified": True,
        }

    monkeypatch.setattr(
        media_source,
        "_probe_hls_ts_aac",
        lambda path: (
            media_source.HLS_LEADING_AAC_OK,
            {
                "stream": {
                    "codec_name": "aac",
                    "profile": "lc",
                    "sample_rate": "16000",
                    "channels": 1,
                }
            },
        )
        if ".playback." in path.name
        else (media_source.HLS_LEADING_AAC_BROKEN, {}),
    )
    monkeypatch.setattr(
        media_source,
        "_categorize_hls_leading_segment",
        _broken_leading_profile,
    )
    source = media_source.XSenseRecordingsMediaSource(_recordings_media_source_hass())
    output_path = tmp_path / "clip.mp4"
    clip = {
        "source": "video_url",
        "quality": "HD",
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "start": 1782049304,
        "end": 1782049334,
        "playback_url": "https://example.invalid/index.m3u8",
        "media_root": tmp_path.as_posix(),
    }
    responses = {
        "https://example.invalid/index.m3u8": (
            "application/vnd.apple.mpegurl;charset=utf-8",
            b"#EXTM3U\n#EXT-X-TARGETDURATION:4\nseg-1.ts\nseg-2.ts\n#EXT-X-ENDLIST\n",
        ),
        "https://example.invalid/seg-1.ts": ("video/mp2t", b"bad-leading-audio"),
        "https://example.invalid/seg-2.ts": ("video/mp2t", b"good-audio-video"),
    }

    class Response:
        def __init__(self, url):
            self.content_type, self.payload = responses[url]
            self.headers = {"content-type": self.content_type}

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self):
            return None

        async def read(self):
            return self.payload

        async def text(self):
            return self.payload.decode()

    class Session:
        def get(self, url):
            return Response(url)

    class Hass:
        async def async_add_executor_job(self, func, *args):
            return func(*args)

    source.hass = Hass()
    monkeypatch.setattr(
        media_source,
        "_hls_cache_dir",
        lambda current_clip: tmp_path / "hls",
    )
    monkeypatch.setattr(
        media_source,
        "_hls_playlist_cache_path",
        lambda current_clip: tmp_path / "hls" / "index.m3u8",
    )
    monkeypatch.setattr(
        media_source,
        "_local_media_url",
        lambda path: f"/media/local/test/{path.name}",
    )
    monkeypatch.setattr(
        media_source,
        "_clip_cache_path",
        lambda current_clip: output_path,
    )
    monkeypatch.setattr(
        media_source,
        "async_get_clientsession",
        lambda hass: Session(),
    )

    asyncio.run(source._async_cached_playback_url(clip))

    playlist = media_source._hls_playlist_cache_path(clip)
    profile = media_source._read_hls_playback_profile(playlist.parent)
    assert profile["leading_aac"] == media_source.HLS_LEADING_AAC_BROKEN
    assert profile["playback_mode"] == media_source.HLS_PLAYBACK_MODE_IGNORE_LEADING_AAC
    assert (playlist.parent / "segment_0002.ts").read_bytes() == b"bad-leading-audio"
    assert (playlist.parent / "segment_0002.playback.ts").read_bytes() == b"silent-aac-sidecar"
    assert playlist.read_text(encoding="utf-8") == (
        "#EXTM3U\n"
        "#EXT-X-TARGETDURATION:4\n"
        "segment_0002.playback.ts\n"
        "#EXT-X-DISCONTINUITY\n"
        "segment_0003.ts\n"
        "#EXT-X-ENDLIST\n"
    )
    assert media_source._hls_playback_fields_for_clip(clip) == {
        "hls_leading_aac": media_source.HLS_LEADING_AAC_BROKEN,
        "hls_playback_mode": media_source.HLS_PLAYBACK_MODE_IGNORE_LEADING_AAC,
    }


def test_ensure_hls_playback_profile_backfills_leading_playback_verified(monkeypatch, tmp_path):
    from custom_components.xsense import recordings_media as media_source

    cache_dir = tmp_path / "clip"
    cache_dir.mkdir()
    playlist = cache_dir / "index.m3u8"
    sidecar = cache_dir / "segment_0007.playback.ts"
    sidecar.write_bytes(b"silent-aac")
    playlist.write_text(
        "#EXTM3U\nsegment_0007.playback.ts\n#EXT-X-DISCONTINUITY\nsegment_0009.ts\n"
    )
    (cache_dir / "segment_0009.ts").write_bytes(b"good")
    (cache_dir / media_source.HLS_CACHE_VERSION_FILE).write_text("3\n")
    media_source._write_hls_playback_profile(
        cache_dir,
        {
            "leading_aac": media_source.HLS_LEADING_AAC_BROKEN,
            "leading_segment": "segment_0007.ts",
            "leading_playback_segment": sidecar.name,
            "playback_mode": media_source.HLS_PLAYBACK_MODE_IGNORE_LEADING_AAC,
            "reference_audio": {"sample_rate": 16000, "channels": 1},
        },
    )
    ffmpeg_calls = []

    def _fail_ffmpeg(*args, **kwargs):
        ffmpeg_calls.append(args)
        raise AssertionError("ffmpeg must not run when sidecar already probes OK")

    monkeypatch.setattr(
        media_source,
        "_probe_hls_ts_aac",
        lambda path: (
            media_source.HLS_LEADING_AAC_OK,
            {
                "stream": {
                    "codec_name": "aac",
                    "profile": "lc",
                    "sample_rate": "16000",
                    "channels": 1,
                }
            },
        ),
    )
    monkeypatch.setattr(media_source.subprocess, "run", _fail_ffmpeg)

    assert media_source._ensure_hls_playback_profile(cache_dir, playlist)
    profile = media_source._read_hls_playback_profile(cache_dir)
    assert profile["leading_playback_verified"] is True
    assert ffmpeg_calls == []


def test_hls_cache_present_does_not_run_migration(monkeypatch, tmp_path):
    from custom_components.xsense import recordings_media as media_source

    cache_dir = tmp_path / "clip"
    cache_dir.mkdir()
    playlist = cache_dir / "index.m3u8"
    playlist.write_text("#EXTM3U\nsegment_0001.ts\n")
    (cache_dir / "segment_0001.ts").write_bytes(b"segment")
    (cache_dir / media_source.HLS_CACHE_VERSION_FILE).write_text("3\n")
    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "start": 1782049304,
        "end": 1782049334,
        "media_root": tmp_path.as_posix(),
    }
    monkeypatch.setattr(
        media_source,
        "_hls_playlist_cache_path",
        lambda current_clip: playlist,
    )
    monkeypatch.setattr(
        media_source,
        "_ensure_hls_playback_profile",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("_ensure_hls_playback_profile must not run")
        ),
    )

    assert media_source._hls_cache_present(clip)


def test_hls_cache_playback_ready_requires_persisted_profile(
    monkeypatch,
    tmp_path,
):
    from custom_components.xsense import recordings_media as media_source

    cache_dir = tmp_path / "clip"
    cache_dir.mkdir()
    playlist = cache_dir / "index.m3u8"
    playlist.write_text("#EXTM3U\nsegment_0001.ts\n")
    (cache_dir / "segment_0001.ts").write_bytes(b"segment")
    (cache_dir / media_source.HLS_CACHE_VERSION_FILE).write_text("3\n")
    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "start": 1782049304,
        "end": 1782049334,
        "media_root": tmp_path.as_posix(),
    }
    monkeypatch.setattr(
        media_source,
        "_hls_playlist_cache_path",
        lambda current_clip: playlist,
    )
    monkeypatch.setattr(
        media_source,
        "_ensure_hls_playback_profile",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("_ensure_hls_playback_profile must not run")
        ),
    )

    assert media_source._hls_cache_present(clip)
    assert not media_source._hls_cache_playback_ready(clip)


def test_hls_cache_playback_ready_rejects_incomplete_sidecar_profile(
    monkeypatch,
    tmp_path,
):
    from custom_components.xsense import recordings_media as media_source

    cache_dir = tmp_path / "clip"
    cache_dir.mkdir()
    playlist = cache_dir / "index.m3u8"
    sidecar = cache_dir / "segment_0007.playback.ts"
    sidecar.write_bytes(b"video-only")
    playlist.write_text(
        "#EXTM3U\nsegment_0007.playback.ts\n#EXT-X-DISCONTINUITY\nsegment_0009.ts\n"
    )
    (cache_dir / "segment_0009.ts").write_bytes(b"good")
    (cache_dir / media_source.HLS_CACHE_VERSION_FILE).write_text("3\n")
    media_source._write_hls_playback_profile(
        cache_dir,
        {
            "leading_aac": media_source.HLS_LEADING_AAC_BROKEN,
            "leading_playback_segment": sidecar.name,
            "playback_mode": media_source.HLS_PLAYBACK_MODE_IGNORE_LEADING_AAC,
        },
    )
    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "start": 1782049304,
        "end": 1782049334,
        "media_root": tmp_path.as_posix(),
    }
    monkeypatch.setattr(
        media_source,
        "_hls_playlist_cache_path",
        lambda current_clip: playlist,
    )
    monkeypatch.setattr(
        media_source,
        "_probe_hls_ts_aac",
        lambda path: (_ for _ in ()).throw(
            AssertionError("_probe_hls_ts_aac must not run on panel readiness checks")
        ),
    )

    assert media_source._hls_cache_present(clip)
    assert not media_source._hls_cache_playback_ready(clip)


def test_hls_cache_playback_ready_accepts_legacy_silent_aac_profile(
    monkeypatch,
    tmp_path,
):
    from custom_components.xsense import recordings_media as media_source

    cache_dir = tmp_path / "clip"
    cache_dir.mkdir()
    playlist = cache_dir / "index.m3u8"
    sidecar = cache_dir / "segment_0007.playback.ts"
    sidecar.write_bytes(b"silent-aac")
    playlist.write_text(
        "#EXTM3U\nsegment_0007.playback.ts\n#EXT-X-DISCONTINUITY\nsegment_0009.ts\n"
    )
    (cache_dir / "segment_0009.ts").write_bytes(b"good")
    (cache_dir / media_source.HLS_CACHE_VERSION_FILE).write_text("3\n")
    media_source._write_hls_playback_profile(
        cache_dir,
        {
            "leading_aac": media_source.HLS_LEADING_AAC_BROKEN,
            "leading_playback_segment": sidecar.name,
            "playback_mode": media_source.HLS_PLAYBACK_MODE_IGNORE_LEADING_AAC,
            "reference_audio": {"sample_rate": 16000, "channels": 1},
        },
    )
    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "start": 1782049304,
        "end": 1782049334,
        "media_root": tmp_path.as_posix(),
    }
    monkeypatch.setattr(
        media_source,
        "_hls_playlist_cache_path",
        lambda current_clip: playlist,
    )
    monkeypatch.setattr(
        media_source,
        "_probe_hls_ts_aac",
        lambda path: (_ for _ in ()).throw(
            AssertionError("_probe_hls_ts_aac must not run on panel readiness checks")
        ),
    )

    assert media_source._hls_cache_playback_ready(clip)


def test_hls_cache_playback_ready_accepts_persisted_verification_flag(
    monkeypatch,
    tmp_path,
):
    from custom_components.xsense import recordings_media as media_source

    cache_dir = tmp_path / "clip"
    cache_dir.mkdir()
    playlist = cache_dir / "index.m3u8"
    sidecar = cache_dir / "segment_0007.playback.ts"
    sidecar.write_bytes(b"silent-aac")
    playlist.write_text(
        "#EXTM3U\nsegment_0007.playback.ts\n#EXT-X-DISCONTINUITY\nsegment_0009.ts\n"
    )
    (cache_dir / "segment_0009.ts").write_bytes(b"good")
    (cache_dir / media_source.HLS_CACHE_VERSION_FILE).write_text("3\n")
    media_source._write_hls_playback_profile(
        cache_dir,
        {
            "leading_aac": media_source.HLS_LEADING_AAC_BROKEN,
            "leading_playback_segment": sidecar.name,
            "playback_mode": media_source.HLS_PLAYBACK_MODE_IGNORE_LEADING_AAC,
            "leading_playback_verified": True,
        },
    )
    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "start": 1782049304,
        "end": 1782049334,
        "media_root": tmp_path.as_posix(),
    }
    monkeypatch.setattr(
        media_source,
        "_hls_playlist_cache_path",
        lambda current_clip: playlist,
    )
    monkeypatch.setattr(
        media_source,
        "_probe_hls_ts_aac",
        lambda path: (_ for _ in ()).throw(
            AssertionError("_probe_hls_ts_aac must not run on panel readiness checks")
        ),
    )

    assert media_source._hls_cache_playback_ready(clip)


def test_recording_media_source_migrates_v2_hls_cache_in_place(
    monkeypatch,
    tmp_path,
):
    from custom_components.xsense import recordings_media as media_source

    def _broken_leading_profile(path, **kwargs):
        sidecar = media_source._hls_leading_playback_segment_path(path)
        sidecar.write_bytes(b"silent-aac-sidecar")
        return {
            "leading_aac": media_source.HLS_LEADING_AAC_BROKEN,
            "leading_segment": path.name,
            "leading_playback_segment": sidecar.name,
            "playback_mode": media_source.HLS_PLAYBACK_MODE_IGNORE_LEADING_AAC,
            "leading_playback_verified": True,
        }

    monkeypatch.setattr(
        media_source,
        "_probe_hls_ts_aac",
        lambda path: (
            media_source.HLS_LEADING_AAC_OK,
            {
                "stream": {
                    "codec_name": "aac",
                    "profile": "lc",
                    "sample_rate": "16000",
                    "channels": 1,
                }
            },
        )
        if ".playback." in path.name
        else (media_source.HLS_LEADING_AAC_BROKEN, {}),
    )
    monkeypatch.setattr(
        media_source,
        "_categorize_hls_leading_segment",
        _broken_leading_profile,
    )
    playlist = tmp_path / "hls" / "index.m3u8"
    playlist.parent.mkdir(parents=True)
    playlist.write_text(
        "#EXTM3U\n#EXT-X-TARGETDURATION:4\nsegment_0002.ts\nsegment_0003.ts\n#EXT-X-ENDLIST\n"
    )
    (playlist.parent / "segment_0002.ts").write_bytes(b"bad-leading-audio")
    (playlist.parent / "segment_0003.ts").write_bytes(b"good-audio-video")
    (playlist.parent / media_source.HLS_CACHE_VERSION_FILE).write_text("2\n")
    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "start": 1782049304,
        "end": 1782049334,
        "media_root": tmp_path.as_posix(),
    }
    monkeypatch.setattr(
        media_source,
        "_hls_playlist_cache_path",
        lambda current_clip: playlist,
    )

    assert media_source._hls_ready(clip)
    assert (
        playlist.parent / media_source.HLS_CACHE_VERSION_FILE
    ).read_text(encoding="utf-8").strip() == "3"
    assert (playlist.parent / "segment_0002.ts").read_bytes() == b"bad-leading-audio"
    assert (playlist.parent / "segment_0002.playback.ts").read_bytes() == b"silent-aac-sidecar"
    assert "segment_0002.playback.ts" in playlist.read_text(encoding="utf-8")


def test_hls_playback_profile_migration_reschedules_on_reload(monkeypatch):
    from custom_components.xsense import recordings_media as media_source
    from custom_components.xsense.const import DOMAIN

    scheduled = []
    cancelled = []

    def async_call_later(hass, delay, action):
        scheduled.append(action)
        return lambda: cancelled.append("pending")

    class Task:
        def __init__(self, coro):
            self._coro = coro
            self.done = MagicMock(return_value=False)
            self.cancel = MagicMock()

        def __await__(self):
            return self._coro.__await__()

    created_tasks = []

    def async_create_task(coro):
        task = Task(coro)
        created_tasks.append(task)
        return task

    async def noop_migration(*args, **kwargs):
        return None

    monkeypatch.setattr(media_source, "async_call_later", async_call_later)
    monkeypatch.setattr(
        media_source,
        "_configured_recording_media_roots",
        lambda hass: [],
    )
    monkeypatch.setattr(
        media_source,
        "_list_hls_cache_dirs",
        lambda roots: [],
    )

    unloads = []
    entry = SimpleNamespace(
        entry_id="entry-id",
        async_on_unload=unloads.append,
    )
    hass = SimpleNamespace(
        data={DOMAIN: {}},
        is_running=True,
        bus=SimpleNamespace(
            async_listen_once=lambda event, callback: lambda: cancelled.append(
                "start-listener"
            )
        ),
        async_add_executor_job=noop_migration,
        async_create_task=async_create_task,
    )

    media_source.async_schedule_hls_playback_profile_migration(hass, entry)
    first_generation = hass.data[DOMAIN]["_hls_playback_profile_migration"]["generation"]
    assert len(scheduled) == 1

    media_source.async_schedule_hls_playback_profile_migration(hass, entry)
    second_generation = hass.data[DOMAIN]["_hls_playback_profile_migration"]["generation"]
    assert second_generation == first_generation + 1
    assert cancelled == ["pending"]
    assert len(scheduled) == 2
    assert len(unloads) == 2


def test_hls_playback_profile_migration_skips_completed_cache_dirs(
    monkeypatch,
    tmp_path,
):
    from custom_components.xsense import recordings_media as media_source

    def _ok_profile(path, **kwargs):
        return {
            "leading_aac": media_source.HLS_LEADING_AAC_OK,
            "leading_segment": path.name,
            "playback_mode": media_source.HLS_PLAYBACK_MODE_NORMAL,
        }

    monkeypatch.setattr(
        media_source,
        "_categorize_hls_leading_segment",
        _ok_profile,
    )

    ready_dir = tmp_path / "hls" / "ready_clip"
    ready_dir.mkdir(parents=True)
    ready_playlist = ready_dir / "index.m3u8"
    ready_playlist.write_text(
        "#EXTM3U\n#EXT-X-TARGETDURATION:4\nsegment_0001.ts\n#EXT-X-ENDLIST\n"
    )
    (ready_dir / "segment_0001.ts").write_bytes(b"good-audio-video")
    (ready_dir / media_source.HLS_CACHE_VERSION_FILE).write_text("3\n")
    media_source._write_hls_playback_profile(ready_dir, _ok_profile(ready_dir / "segment_0001.ts"))

    pending_dir = tmp_path / "hls" / "pending_clip"
    pending_dir.mkdir(parents=True)
    pending_playlist = pending_dir / "index.m3u8"
    pending_playlist.write_text(
        "#EXTM3U\n#EXT-X-TARGETDURATION:4\nsegment_0002.ts\n#EXT-X-ENDLIST\n"
    )
    (pending_dir / "segment_0002.ts").write_bytes(b"bad-leading-audio")
    (pending_dir / media_source.HLS_CACHE_VERSION_FILE).write_text("2\n")

    cache_dirs = media_source._list_hls_cache_dirs([tmp_path])
    assert cache_dirs == [pending_dir, ready_dir]

    assert media_source._hls_cache_dir_needs_playback_profile_migration(
        ready_dir,
        ready_playlist,
    ) is False
    assert media_source._hls_cache_dir_needs_playback_profile_migration(
        pending_dir,
        pending_playlist,
    ) is True

    assert media_source._migrate_hls_cache_dir(ready_dir) == "skipped"
    assert media_source._migrate_hls_cache_dir(pending_dir) == "migrated"
    assert (
        pending_dir / media_source.HLS_CACHE_VERSION_FILE
    ).read_text(encoding="utf-8").strip() == "3"


def test_hls_leading_playback_segment_uses_silent_aac_from_reference(
    monkeypatch,
    tmp_path,
):
    from custom_components.xsense import recordings_media as media_source

    leading = tmp_path / "segment_0007.ts"
    reference = tmp_path / "segment_0009.ts"
    leading.write_bytes(b"broken-leading")
    reference.write_bytes(b"good-audio-video")
    playlist = tmp_path / "index.m3u8"
    playlist.write_text(
        "#EXTM3U\n#EXT-X-TARGETDURATION:4\n"
        "segment_0007.ts\nsegment_0009.ts\n#EXT-X-ENDLIST\n"
    )

    monkeypatch.setattr(
        media_source,
        "_probe_hls_ts_aac",
        lambda path: (
            (
                media_source.HLS_LEADING_AAC_BROKEN,
                {"stream": {"codec_name": "aac", "profile": "unknown"}},
            )
            if path == leading
            else (
                media_source.HLS_LEADING_AAC_OK,
                {
                    "stream": {
                        "codec_name": "aac",
                        "profile": "lc",
                        "sample_rate": "16000",
                        "channels": 1,
                    }
                },
            )
        ),
    )
    commands = []

    def _run(command, **kwargs):
        commands.append(command)
        sidecar = media_source._hls_leading_playback_segment_path(leading)
        sidecar.write_bytes(b"silent-aac-sidecar")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(media_source.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(media_source.subprocess, "run", _run)

    profile = media_source._categorize_hls_leading_segment(
        leading,
        playlist_path=playlist,
    )

    assert profile["reference_audio_segment"] == "segment_0009.ts"
    assert profile["reference_audio"] == {
        "sample_rate": 16000,
        "channels": 1,
    }
    assert profile["leading_playback_segment"] == "segment_0007.playback.ts"
    assert commands
    command = commands[0]
    assert "anullsrc=channel_layout=mono:sample_rate=16000" in command
    assert command.count("-map") == 2
    assert "-map" in command and "1:a:0" in command and "0:v:0" in command
    assert "-c:a" in command and "aac" in command


def test_hls_playback_profile_ready_rejects_video_only_sidecar(tmp_path):
    from custom_components.xsense import recordings_media as media_source

    cache_dir = tmp_path / "clip"
    cache_dir.mkdir()
    sidecar = cache_dir / "segment_0007.playback.ts"
    sidecar.write_bytes(b"video-only")
    media_source._write_hls_playback_profile(
        cache_dir,
        {
            "leading_aac": media_source.HLS_LEADING_AAC_BROKEN,
            "leading_playback_segment": sidecar.name,
            "playback_mode": media_source.HLS_PLAYBACK_MODE_IGNORE_LEADING_AAC,
        },
    )

    assert media_source._hls_playback_profile_ready(cache_dir) is False


def test_hls_playback_fields_for_clip_reads_profile_without_subprocess(
    monkeypatch,
    tmp_path,
):
    from custom_components.xsense import recordings_media as media_source

    def _fail_subprocess(*args, **kwargs):
        raise AssertionError("subprocess must not run on panel profile reads")

    monkeypatch.setattr(media_source.subprocess, "run", _fail_subprocess)
    monkeypatch.setattr(
        media_source,
        "_hls_ready",
        lambda clip: (_ for _ in ()).throw(
            AssertionError("_hls_ready must not run on panel profile reads")
        ),
    )

    playlist = tmp_path / "hls" / "index.m3u8"
    playlist.parent.mkdir(parents=True)
    playlist.write_text("#EXTM3U\nsegment_0001.ts\n")
    (playlist.parent / "segment_0001.ts").write_bytes(b"segment")
    media_source._write_hls_playback_profile(
        playlist.parent,
        {
            "leading_aac": media_source.HLS_LEADING_AAC_BROKEN,
            "leading_playback_segment": "segment_0001.playback.ts",
            "playback_mode": media_source.HLS_PLAYBACK_MODE_IGNORE_LEADING_AAC,
            "leading_playback_verified": True,
        },
    )
    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "start": 1782049304,
        "end": 1782049334,
        "media_root": tmp_path.as_posix(),
    }
    monkeypatch.setattr(
        media_source,
        "_hls_playlist_cache_path",
        lambda current_clip: playlist,
    )

    assert media_source._hls_playback_fields_for_clip(clip) == {
        "hls_leading_aac": media_source.HLS_LEADING_AAC_BROKEN,
        "hls_playback_mode": media_source.HLS_PLAYBACK_MODE_IGNORE_LEADING_AAC,
    }


def test_recording_media_source_rejects_unversioned_hls_cache(
    monkeypatch,
    tmp_path,
):
    from custom_components.xsense import recordings_media as media_source

    source = media_source.XSenseRecordingsMediaSource(_recordings_media_source_hass())
    output_path = tmp_path / "clip.mp4"
    playlist = tmp_path / "hls" / "index.m3u8"
    playlist.parent.mkdir(parents=True)
    playlist.write_text("#EXTM3U\n#EXT-X-TARGETDURATION:4\nsegment_0001.ts\n")
    (playlist.parent / "segment_0001.ts").write_bytes(b"segment")
    clip = {
        "source": "video_url",
        "quality": "HD",
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "start": 1782049304,
        "end": 1782049334,
        "playback_url": "https://example.invalid/index.m3u8",
        "media_root": tmp_path.as_posix(),
    }
    monkeypatch.setattr(
        media_source,
        "_hls_playlist_cache_path",
        lambda current_clip: playlist,
    )
    monkeypatch.setattr(
        media_source,
        "_clip_cache_path",
        lambda current_clip: output_path,
    )
    monkeypatch.setattr(
        media_source,
        "_local_media_url",
        lambda path: f"/media/local/test/{path.name}",
    )

    assert not media_source._hls_ready(clip)
    assert not playlist.parent.exists()
    assert asyncio.run(source._async_cached_media_url(clip)) == ""


def test_recording_media_source_prefers_hls_cache_over_legacy_mp4(
    monkeypatch,
    tmp_path,
):
    from custom_components.xsense import recordings_media as media_source

    source = media_source.XSenseRecordingsMediaSource(_recordings_media_source_hass())
    output_path = tmp_path / "clip.mp4"
    output_path.write_bytes(b"\x00\x00\x00\x10ftypmp42\x00\x00\x00\x00legacy")
    playlist = tmp_path / "hls" / "index.m3u8"
    playlist.parent.mkdir(parents=True)
    playlist.write_text("#EXTM3U\n#EXT-X-TARGETDURATION:4\nsegment_0001.ts\n")
    (playlist.parent / "segment_0001.ts").write_bytes(b"segment")
    media_source._write_hls_cache_version(playlist.parent)
    media_source._write_hls_playback_profile(
        playlist.parent,
        {
            "leading_aac": media_source.HLS_LEADING_AAC_OK,
            "leading_segment": "segment_0001.ts",
            "playback_mode": media_source.HLS_PLAYBACK_MODE_NORMAL,
        },
    )
    clip = {
        "source": "video_url",
        "quality": "HD",
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "start": 1782049304,
        "end": 1782049334,
        "playback_url": "https://example.invalid/index.m3u8",
        "media_root": tmp_path.as_posix(),
    }

    monkeypatch.setattr(
        media_source,
        "_hls_playlist_cache_path",
        lambda current_clip: playlist,
    )
    monkeypatch.setattr(
        media_source,
        "_clip_cache_path",
        lambda current_clip: output_path,
    )
    monkeypatch.setattr(
        media_source,
        "_local_media_url",
        lambda path: f"/media/local/test/{path.name}",
    )

    result = asyncio.run(source._async_cached_playback_url(clip))
    media_url = asyncio.run(source._async_cached_media_url(clip))
    media_format = asyncio.run(source._async_cached_media_format(clip))

    assert result == "/media/local/test/index.m3u8"
    assert media_url == "/media/local/test/index.m3u8"
    assert media_format == "hls"
    assert not output_path.exists()


def test_recording_media_source_hls_master_requires_every_variant_and_segment(
    monkeypatch,
    tmp_path,
):
    from custom_components.xsense import recordings_media as media_source

    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "start": 1782049304,
        "end": 1782049334,
        "media_root": tmp_path.as_posix(),
    }
    root = tmp_path / "hls"
    variant_a = root / "variant-a"
    variant_b = root / "variant-b"
    variant_a.mkdir(parents=True)
    variant_b.mkdir(parents=True)
    (root / "index.m3u8").write_text(
        "#EXTM3U\n"
        "#EXT-X-STREAM-INF:BANDWIDTH=1000000\n"
        "variant-a/index.m3u8\n"
        "#EXT-X-STREAM-INF:BANDWIDTH=2000000\n"
        "variant-b/index.m3u8\n",
        encoding="utf-8",
    )
    (variant_a / "index.m3u8").write_text(
        "#EXTM3U\n#EXT-X-TARGETDURATION:4\nsegment_0002.ts\nsegment_0003.ts\n",
        encoding="utf-8",
    )
    (variant_a / "segment_0002.ts").write_bytes(b"segment-one")
    (variant_b / "index.m3u8").write_text(
        "#EXTM3U\n#EXT-X-TARGETDURATION:4\nsegment_0004.ts\n",
        encoding="utf-8",
    )
    media_source._write_hls_cache_version(root)
    media_source._write_hls_playback_profile(
        root,
        {
            "leading_aac": media_source.HLS_LEADING_AAC_OK,
            "leading_segment": "segment_0002.ts",
            "playback_mode": media_source.HLS_PLAYBACK_MODE_NORMAL,
        },
    )
    monkeypatch.setattr(
        media_source,
        "_hls_playlist_cache_path",
        lambda current_clip: root / "index.m3u8",
    )

    assert not media_source._hls_playlist_ready(root / "index.m3u8")
    (variant_a / "segment_0003.ts").write_bytes(b"segment-two")
    (variant_b / "segment_0004.ts").write_bytes(b"segment-three")
    assert media_source._hls_ready(clip)

    (variant_a / "segment_0003.ts").unlink()
    assert not media_source._hls_ready(clip)
    assert not root.exists()


def test_recording_media_source_hls_ready_requires_attribute_playlists_and_keys(
    tmp_path,
):
    from custom_components.xsense import recordings_media as media_source

    root = tmp_path / "hls"
    audio = root / "audio"
    video = root / "video"
    audio.mkdir(parents=True)
    video.mkdir(parents=True)
    (root / "index.m3u8").write_text(
        '#EXTM3U\n#EXT-X-SESSION-DATA:DATA-ID="metadata",URI="https://example.invalid/info.json"\n'
        '#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",URI="audio/index.m3u8"\n'
        '#EXT-X-STREAM-INF:BANDWIDTH=1000000,AUDIO="audio"\nvideo/index.m3u8\n',
        encoding="utf-8",
    )
    (audio / "index.m3u8").write_text(
        "#EXTM3U\naudio_0001.ts\n#EXT-X-ENDLIST\n",
        encoding="utf-8",
    )
    (audio / "audio_0001.ts").write_bytes(b"audio")
    (video / "index.m3u8").write_text(
        '#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI="key.bin"\n'
        "video_0001.ts\n#EXT-X-ENDLIST\n",
        encoding="utf-8",
    )
    (video / "video_0001.ts").write_bytes(b"video")

    assert not media_source._hls_playlist_ready(root / "index.m3u8")
    (video / "key.bin").write_bytes(b"key")
    assert media_source._hls_playlist_ready(root / "index.m3u8")


def test_recording_media_source_lazy_shows_uncached_direct_clips_when_sync_disabled(
    monkeypatch,
    tmp_path,
):
    from custom_components.xsense import recordings_media as media_source

    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "date": "2026-06-25",
        "start": 1782049304,
        "end": 1782049334,
        "source": "video_url",
        "playback_url": "https://example.invalid/clip.m3u8",
        "media_root": tmp_path.as_posix(),
    }
    source = media_source.XSenseRecordingsMediaSource(
        _recordings_media_source_hass(
            config_entries=SimpleNamespace(
                async_get_entry=lambda entry_id: SimpleNamespace(data={}, options={})
            )
        )
    )

    async def load_index():
        return {
            "cameras": [
                {
                    "entry_id": "entry-id",
                    "serial": "CAMERA-SN",
                    "entity_id": "camera.garden",
                    "clips": [clip],
                }
            ]
        }

    monkeypatch.setattr(source, "_async_load_index", load_index)
    monkeypatch.setattr(media_source, "_path_ready", lambda path: False)

    browsed = asyncio.run(
        source.async_browse_media(
            SimpleNamespace(
                identifier=media_source.build_identifier(
                    {
                        "entry_id": "entry-id",
                        "serial": "CAMERA-SN",
                        "date": "2026-06-25",
                    }
                )
            )
        )
    )

    assert [child.title for child in browsed.children] == ["1782049304"]
    assert browsed.children[0].can_play is True


def test_recording_media_source_sync_hides_uncached_clips(monkeypatch, tmp_path):
    from custom_components.xsense import recordings_media as media_source
    from custom_components.xsense.const import (
        CONF_RECORDING_CACHE_MODE,
        CONF_RECORDING_MEDIA_SYNC_ENABLED,
    )

    clips = [
        {
            "entry_id": "entry-id",
            "serial": "CAMERA-SN",
            "date": "2026-06-25",
            "start": 1782049304,
            "end": 1782049334,
            "playback_url": "/xsense/recording/entry-id/1782049304?serial=CAMERA-SN",
            "media_root": tmp_path.as_posix(),
        },
        {
            "entry_id": "entry-id",
            "serial": "CAMERA-SN",
            "date": "2026-06-25",
            "start": 1782049400,
            "end": 1782049430,
            "playback_url": "/xsense/recording/entry-id/1782049400?serial=CAMERA-SN",
            "media_root": tmp_path.as_posix(),
        },
    ]
    source = media_source.XSenseRecordingsMediaSource(
        _recordings_media_source_hass(
            config_entries=SimpleNamespace(
                async_get_entry=lambda entry_id: SimpleNamespace(
                    data={},
                    options={
                        CONF_RECORDING_CACHE_MODE: "retained",
                        CONF_RECORDING_MEDIA_SYNC_ENABLED: True,
                    }
                )
            ),
            async_create_task=lambda coro: None,
        )
    )

    async def load_index():
        return {
            "cameras": [
                {
                    "entry_id": "entry-id",
                    "serial": "CAMERA-SN",
                    "entity_id": "camera.garden",
                    "clips": clips,
                }
            ]
        }

    def path_ready(path):
        return str(path).endswith("CAMERA-SN_1782049400_1782049430.mp4")

    monkeypatch.setattr(source, "_async_load_index", load_index)
    monkeypatch.setattr(media_source, "_path_ready", path_ready)
    monkeypatch.setattr(media_source, "_mp4_ready", path_ready)

    browsed = asyncio.run(
        source.async_browse_media(
            SimpleNamespace(
                identifier=media_source.build_identifier(
                    {
                        "entry_id": "entry-id",
                        "serial": "CAMERA-SN",
                        "date": "2026-06-25",
                    }
                )
            )
        )
    )

    assert [child.title for child in browsed.children] == ["1782049400"]


def test_recording_media_source_sync_hides_uncached_dates(monkeypatch, tmp_path):
    from custom_components.xsense import recordings_media as media_source
    from custom_components.xsense.const import (
        CONF_RECORDING_CACHE_MODE,
        CONF_RECORDING_MEDIA_SYNC_ENABLED,
    )

    clips = [
        {
            "entry_id": "entry-id",
            "serial": "CAMERA-SN",
            "date": "2026-06-24",
            "start": 1781962900,
            "end": 1781962930,
            "playback_url": "/xsense/recording/entry-id/1781962900?serial=CAMERA-SN",
            "media_root": tmp_path.as_posix(),
        },
        {
            "entry_id": "entry-id",
            "serial": "CAMERA-SN",
            "date": "2026-06-25",
            "start": 1782049400,
            "end": 1782049430,
            "playback_url": "/xsense/recording/entry-id/1782049400?serial=CAMERA-SN",
            "media_root": tmp_path.as_posix(),
        },
    ]
    source = media_source.XSenseRecordingsMediaSource(
        _recordings_media_source_hass(
            config_entries=SimpleNamespace(
                async_get_entry=lambda entry_id: SimpleNamespace(
                    data={},
                    options={
                        CONF_RECORDING_CACHE_MODE: "retained",
                        CONF_RECORDING_MEDIA_SYNC_ENABLED: True,
                    },
                )
            )
        )
    )

    async def load_index():
        return {
            "cameras": [
                {
                    "entry_id": "entry-id",
                    "serial": "CAMERA-SN",
                    "clips": clips,
                }
            ]
        }

    monkeypatch.setattr(source, "_async_load_index", load_index)
    monkeypatch.setattr(
        media_source,
        "_path_ready",
        lambda path: str(path).endswith("CAMERA-SN_1782049400_1782049430.mp4"),
    )
    monkeypatch.setattr(
        media_source,
        "_mp4_ready",
        lambda path: str(path).endswith("CAMERA-SN_1782049400_1782049430.mp4"),
    )

    browsed = asyncio.run(
        source.async_browse_media(
            SimpleNamespace(
                identifier=media_source.build_identifier(
                    {
                        "entry_id": "entry-id",
                        "serial": "CAMERA-SN",
                    }
                )
            )
        )
    )

    assert [child.title for child in browsed.children] == ["2026-06-25"]


def test_recording_media_source_sync_rejects_uncached_resolve(monkeypatch, tmp_path):
    from homeassistant.components.media_source.error import Unresolvable

    from custom_components.xsense import recordings_media as media_source
    from custom_components.xsense.const import (
        CONF_RECORDING_CACHE_MODE,
        CONF_RECORDING_MEDIA_SYNC_ENABLED,
    )

    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "start": 1782049304,
        "end": 1782049334,
        "playback_url": "/xsense/recording/entry-id/1782049304?serial=CAMERA-SN",
        "media_root": tmp_path.as_posix(),
    }
    source = media_source.XSenseRecordingsMediaSource(
        _recordings_media_source_hass(
            config_entries=SimpleNamespace(
                async_get_entry=lambda entry_id: SimpleNamespace(
                    data={},
                    options={
                        CONF_RECORDING_CACHE_MODE: "retained",
                        CONF_RECORDING_MEDIA_SYNC_ENABLED: True,
                    }
                )
            )
        )
    )

    async def load_index():
        return {
            "cameras": [
                {
                    "entry_id": "entry-id",
                    "serial": "CAMERA-SN",
                    "clips": [clip],
                }
            ]
        }

    async def cached_url(current_clip):
        raise AssertionError("sync mode should not lazy-cache uncached media")

    monkeypatch.setattr(source, "_async_load_index", load_index)
    monkeypatch.setattr(source, "_async_cached_playback_url", cached_url)
    monkeypatch.setattr(media_source, "_path_ready", lambda path: False)

    with pytest.raises(Unresolvable, match="waiting for background sync"):
        asyncio.run(
            source.async_resolve_media(
                SimpleNamespace(
                    identifier=media_source.build_identifier(
                        {
                            "entry_id": "entry-id",
                            "serial": "CAMERA-SN",
                            "start": "1782049304",
                        }
                    )
                )
            )
        )


def test_recording_media_source_cache_path_uses_safe_filename():
    from custom_components.xsense import recordings_media as media_source

    path = media_source._clip_cache_path_from_values("CAM/ERA SN", 1782049304, 1782049334)
    thumb_path = media_source._clip_thumbnail_cache_path_from_values(
        "CAM/ERA SN", 1782049304, 1782049334
    )

    assert path.as_posix().endswith(
        "/xsense_recordings/videos/CAM_ERA_SN_1782049304_1782049334.mp4"
    )
    assert thumb_path.as_posix().endswith(
        "/xsense_recordings/thumbs/CAM_ERA_SN_1782049304_1782049334.jpg"
    )


def test_recording_media_root_rejects_media_prefix_lookalikes():
    from custom_components.xsense import recordings_media as media_source

    assert media_source._recording_media_root_from_value("/media").as_posix() == "/media"
    assert (
        media_source._recording_media_root_from_value("/media/xsense").as_posix()
        == "/media/xsense"
    )
    assert (
        media_source._recording_media_root_from_value("/mediaevil").as_posix()
        == "/media/xsense_recordings"
    )

    entry = SimpleNamespace(
        data={},
        options={media_source.CONF_RECORDING_MEDIA_STORAGE_PATH: "/mediaevil"},
    )
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_get_entry=lambda entry_id: entry)
    )

    assert media_source._recording_media_root(hass, "entry-id").as_posix() == (
        "/media/xsense_recordings"
    )


def test_refresh_recording_indexes_filters_config_entry(monkeypatch):
    from custom_components.xsense import recordings_media as media_source

    refreshed = []

    class Manager:
        def __init__(self, entry_id):
            self.entry_id = entry_id

        async def async_index(self, *, force_refresh=False):
            refreshed.append((self.entry_id, force_refresh))
            return {"entry_id": self.entry_id, "cameras": []}

    def manager_factory(hass, entry_id, coordinator):
        return Manager(entry_id)

    monkeypatch.setattr(media_source, "_recording_index_manager", manager_factory)
    hass = SimpleNamespace(
        data={
            media_source.DOMAIN: {
                "entry-one": SimpleNamespace(xsense=object(), data={}),
                "entry-two": SimpleNamespace(xsense=object(), data={}),
                "_recording_indexes": {},
            }
        }
    )

    result = asyncio.run(
        media_source.async_refresh_recording_indexes(
            hass,
            entry_id="entry-two",
            force_refresh=True,
        )
    )

    assert result == [{"entry_id": "entry-two", "cameras": []}]
    assert refreshed == [("entry-two", True)]


def test_remove_recording_index_cleans_empty_manager_store():
    from custom_components.xsense import recordings_media as media_source

    hass = SimpleNamespace(
        data={media_source.DOMAIN: {"_recording_indexes": {"entry-id": object()}}}
    )

    media_source.async_remove_recording_index(hass, "entry-id")

    assert "_recording_indexes" not in hass.data[media_source.DOMAIN]


def test_cache_recording_media_caches_direct_and_skips_sd_capture(monkeypatch):
    from custom_components.xsense import recordings_media as media_source
    from custom_components.xsense.const import CONF_RECORDING_CACHE_MODE

    async def refresh_indexes(hass, *, entry_id=None, force_refresh=False):
        return [
            {
                "cameras": [
                    {
                        "clips": [
                            {
                                "entry_id": "entry-id",
                                "source": "video_url",
                                "playback_url": "https://example.invalid/clip.mp4",
                                "thumbnail_url": "https://example.invalid/thumb.jpg",
                                "serial": "CAMERA-SN",
                                "start": 1,
                                "end": 2,
                            },
                            {
                                "entry_id": "entry-id",
                                "source": "sd_playback",
                                "playback_url": "/xsense/recording/entry/3?serial=CAMERA-SN",
                                "serial": "CAMERA-SN",
                                "start": 3,
                                "end": 4,
                            },
                        ]
                    }
                ]
            }
        ]

    async def cached_url(self, clip):
        cached.append(clip["start"])
        ready.add(clip["start"])
        return "/media/local/xsense_recordings/videos/CAMERA-SN_1_2.mp4"

    async def cache_thumbnail(self, clip):
        if not clip.get("thumbnail_url"):
            return False
        thumbs.append(clip["start"])
        return True

    cached = []
    thumbs = []
    ready = set()
    monkeypatch.setattr(media_source, "async_refresh_recording_indexes", refresh_indexes)
    monkeypatch.setattr(
        media_source.XSenseRecordingsMediaSource,
        "_async_cached_playback_url",
        cached_url,
    )
    monkeypatch.setattr(
        media_source.XSenseRecordingsMediaSource,
        "_async_cache_thumbnail",
        cache_thumbnail,
    )
    monkeypatch.setattr(
        media_source,
        "_path_ready",
        lambda path: any(str(path).endswith(f"CAMERA-SN_{start}_{start + 1}.mp4") for start in ready),
    )
    monkeypatch.setattr(
        media_source,
        "_mp4_ready",
        lambda path: any(str(path).endswith(f"CAMERA-SN_{start}_{start + 1}.mp4") for start in ready),
    )
    entry = SimpleNamespace(options={CONF_RECORDING_CACHE_MODE: "retained"})
    hass = SimpleNamespace(
        data={media_source.DOMAIN: {}},
        config_entries=SimpleNamespace(
            async_get_entry=lambda entry_id: entry
        ),
    )

    summary = asyncio.run(media_source.async_cache_recording_media(hass))

    assert summary == {"downloaded": 1, "thumbnails": 1, "skipped": 1, "failed": 0}
    assert cached == [1]
    assert thumbs == [1]


def test_cache_recording_media_skips_downloads_in_playback_only_mode(monkeypatch):
    from custom_components.xsense import recordings_media as media_source

    async def refresh_indexes(hass, *, entry_id=None, force_refresh=False):
        return [
            {
                "cameras": [
                    {
                        "clips": [
                            {
                                "entry_id": "entry-id",
                                "source": "video_url",
                                "playback_url": "https://example.invalid/clip.m3u8",
                                "thumbnail_url": "https://example.invalid/thumb.jpg",
                                "serial": "CAMERA-SN",
                                "start": 1,
                                "end": 2,
                            }
                        ]
                    }
                ]
            }
        ]

    monkeypatch.setattr(media_source, "async_refresh_recording_indexes", refresh_indexes)
    monkeypatch.setattr(
        media_source.XSenseRecordingsMediaSource,
        "_async_cached_playback_url",
        lambda *args: pytest.fail("playback-only mode must not download recordings"),
    )
    monkeypatch.setattr(
        media_source.XSenseRecordingsMediaSource,
        "_async_cache_thumbnail",
        lambda *args: pytest.fail("playback-only mode must not cache thumbnails"),
    )
    hass = SimpleNamespace(
        data={media_source.DOMAIN: {}},
        config_entries=SimpleNamespace(
            async_get_entry=lambda entry_id: SimpleNamespace(options={})
        ),
    )

    summary = asyncio.run(media_source.async_cache_recording_media(hass))

    assert summary == {"downloaded": 0, "thumbnails": 0, "skipped": 1, "failed": 0}


def test_cache_recording_media_skips_manually_deleted_clip(monkeypatch):
    from custom_components.xsense import recordings_media as media_source
    from custom_components.xsense.const import CONF_RECORDING_CACHE_MODE

    clip = {
        "entry_id": "entry-id",
        "source": "video_url",
        "playback_url": "https://example.invalid/clip.m3u8",
        "thumbnail_url": "https://example.invalid/thumb.jpg",
        "serial": "CAMERA-SN",
        "start": 1,
        "end": 2,
    }

    async def refresh_indexes(hass, *, entry_id=None, force_refresh=False):
        return [{"cameras": [{"clips": [clip]}]}]

    async def suppressed(hass, current_clip):
        return current_clip is clip

    monkeypatch.setattr(media_source, "async_refresh_recording_indexes", refresh_indexes)
    monkeypatch.setattr(media_source, "async_recording_cache_suppressed", suppressed)
    monkeypatch.setattr(
        media_source.XSenseRecordingsMediaSource,
        "_async_cached_playback_url",
        lambda *args: pytest.fail("manual deletion must block background download"),
    )
    monkeypatch.setattr(
        media_source.XSenseRecordingsMediaSource,
        "_async_cache_thumbnail",
        lambda *args: pytest.fail("manual deletion must block thumbnail warmup"),
    )
    hass = SimpleNamespace(
        data={media_source.DOMAIN: {}},
        config_entries=SimpleNamespace(
            async_get_entry=lambda entry_id: SimpleNamespace(
                options={CONF_RECORDING_CACHE_MODE: "retained"}
            )
        ),
    )

    summary = asyncio.run(media_source.async_cache_recording_media(hass))

    assert summary == {"downloaded": 0, "thumbnails": 0, "skipped": 1, "failed": 0}


def test_cache_recording_media_does_not_start_sd_capture_for_background_sync(monkeypatch):
    from custom_components.xsense import recordings_media as media_source

    async def refresh_indexes(hass, *, entry_id=None, force_refresh=False):
        return [
            {
                "cameras": [
                    {
                        "clips": [
                            {
                                "source": "sd_playback",
                                "playback_url": "/xsense/recording/entry/100?serial=CAMERA-SN",
                                "serial": "CAMERA-SN",
                                "start": 100,
                                "end": 101,
                            }
                        ]
                    },
                    {
                        "clips": [
                            {
                                "source": "sd_playback",
                                "playback_url": "/xsense/recording/entry/300?serial=CAMERA-SN",
                                "serial": "CAMERA-SN",
                                "start": 300,
                                "end": 301,
                            },
                            {
                                "source": "sd_playback",
                                "playback_url": "/xsense/recording/entry/200?serial=CAMERA-SN",
                                "serial": "CAMERA-SN",
                                "start": 200,
                                "end": 201,
                            },
                        ]
                    },
                ]
            }
        ]

    async def cached_url(self, clip):
        cached.append(clip["start"])
        ready.add(clip["start"])
        return "/media/local/clip.mp4"

    cached = []
    ready = set()
    monkeypatch.setattr(media_source, "async_refresh_recording_indexes", refresh_indexes)
    monkeypatch.setattr(
        media_source.XSenseRecordingsMediaSource,
        "_async_cached_playback_url",
        cached_url,
    )
    monkeypatch.setattr(
        media_source,
        "_path_ready",
        lambda path: any(str(path).endswith(f"CAMERA-SN_{start}_{start + 1}.mp4") for start in ready),
    )
    hass = SimpleNamespace(data={media_source.DOMAIN: {}})

    asyncio.run(media_source.async_cache_recording_media(hass))

    assert cached == []


def test_cache_recent_recording_media_force_refreshes_without_sd_capture(monkeypatch):
    from custom_components.xsense import recordings_media as media_source

    now = 1_782_049_400
    calls = []
    cached = []
    ready = set()

    async def refresh_indexes(hass, *, entry_id=None, force_refresh=False):
        calls.append((entry_id, force_refresh))
        return [
            {
                "cameras": [
                    {
                        "clips": [
                            {
                                "source": "sd_playback",
                                "playback_url": "/xsense/recording/entry/old?serial=CAMERA-SN",
                                "serial": "CAMERA-SN",
                                "start": now - 3_600,
                                "end": now - 3_570,
                            },
                            {
                                "source": "sd_playback",
                                "playback_url": "/xsense/recording/entry/new?serial=CAMERA-SN",
                                "serial": "CAMERA-SN",
                                "start": now - 60,
                                "end": now - 30,
                            },
                        ]
                    }
                ]
            }
        ]

    async def cached_url(self, clip):
        cached.append(clip["start"])
        ready.add(clip["start"])
        return "/media/local/clip.mp4"

    monkeypatch.setattr(media_source, "async_refresh_recording_indexes", refresh_indexes)
    monkeypatch.setattr(media_source, "_recent_recording_cutoff", lambda: now - 600)
    monkeypatch.setattr(
        media_source.XSenseRecordingsMediaSource,
        "_async_cached_playback_url",
        cached_url,
    )
    monkeypatch.setattr(
        media_source,
        "_path_ready",
        lambda path: any(
            str(path).endswith(f"CAMERA-SN_{start}_{start + 30}.mp4")
            for start in ready
        ),
    )
    monkeypatch.setattr(
        media_source,
        "_mp4_ready",
        lambda path: any(
            str(path).endswith(f"CAMERA-SN_{start}_{start + 30}.mp4")
            for start in ready
        ),
    )
    hass = SimpleNamespace(data={media_source.DOMAIN: {}})

    summary = asyncio.run(
        media_source.async_cache_recent_recording_media(hass, entry_id="entry-id")
    )

    assert calls == [("entry-id", True)]
    assert cached == []
    assert summary == {"downloaded": 0, "thumbnails": 0, "skipped": 2, "failed": 0}


def test_event_recording_clip_does_not_create_camera_without_index():
    from custom_components.xsense import recordings_media as media_source

    hass = SimpleNamespace(data={media_source.DOMAIN: {}})
    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "date": "2026-06-30",
        "start": 1782049304,
        "end": 1782049334,
        "playback_url": "/xsense-recordings#entry_id=entry-id",
    }

    media_source._remember_event_recording_clip(hass, clip)
    merged = media_source._merge_event_recording_clips(hass, [])

    assert merged == []


def test_recording_media_source_rejects_browse_without_cameras():
    from homeassistant.components.media_source.error import Unresolvable

    from custom_components.xsense import recordings_media as media_source

    source = media_source.XSenseRecordingsMediaSource(
        SimpleNamespace(data={media_source.DOMAIN: {}})
    )

    with pytest.raises(Unresolvable):
        asyncio.run(source.async_browse_media(SimpleNamespace(identifier="")))


def test_event_recording_clip_merges_into_recording_index():
    from custom_components.xsense import recordings_media as media_source

    hass = SimpleNamespace(data={media_source.DOMAIN: {}})
    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "date": "2026-06-30",
        "start": 1782049304,
        "end": 1782049334,
        "playback_url": "/xsense-recordings#entry_id=entry-id",
    }

    media_source._remember_event_recording_clip(hass, clip)
    merged = media_source._merge_event_recording_clips(
        hass,
        [
            {
                "entry_id": "entry-id",
                "serial": "CAMERA-SN",
                "name": "Garden",
                "clips": [],
            }
        ],
    )

    assert merged[0]["name"] == "Garden"
    assert merged[0]["clips"] == [clip]


def test_event_recording_clip_updates_matching_index_clip():
    from custom_components.xsense import recordings_media as media_source

    hass = SimpleNamespace(data={media_source.DOMAIN: {}})
    indexed_clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "date": "2026-06-30",
        "start": 1782049304,
        "end": 1782049330,
        "title": "Indexed clip",
        "source": "sd_playback",
        "playback_url": "/xsense/recording/entry-id/1782049304?serial=CAMERA-SN",
    }
    event_clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "date": "2026-06-30",
        "start": 1782049304,
        "end": 1782049334,
        "title": "Event clip",
        "source": "video_url",
        "playback_url": "https://example.invalid/event.m3u8",
        "cached_url": "/media/local/xsense_recordings/videos/CAMERA-SN_1782049304_1782049334.mp4",
    }

    media_source._remember_event_recording_clip(hass, event_clip)
    merged = media_source._merge_event_recording_clips(
        hass,
        [
            {
                "entry_id": "entry-id",
                "serial": "CAMERA-SN",
                "name": "Garden",
                "clips": [indexed_clip],
            }
        ],
    )

    assert len(merged[0]["clips"]) == 1
    assert merged[0]["clips"][0]["end"] == event_clip["end"]
    assert merged[0]["clips"][0]["source"] == "video_url"
    assert merged[0]["clips"][0]["playback_url"] == event_clip["playback_url"]
    assert merged[0]["clips"][0]["cached_url"] == event_clip["cached_url"]


def test_event_recording_clip_memory_is_bounded():
    from custom_components.xsense import recordings_media as media_source

    hass = SimpleNamespace(data={media_source.DOMAIN: {}})
    for start in range(100, 160):
        media_source._remember_event_recording_clip(
            hass,
            {
                "entry_id": "entry-id",
                "serial": "CAMERA-SN",
                "date": "2026-06-30",
                "start": start,
                "end": start + 30,
                "playback_url": "/xsense-recordings#entry_id=entry-id",
            },
        )

    clips = hass.data[media_source.DOMAIN]["_recording_event_clips"]["entry-id"][
        "CAMERA-SN"
    ]

    assert len(clips) == media_source.EVENT_RECORDING_CLIP_LIMIT
    assert min(clips) == 110
    assert max(clips) == 159


def test_recording_thumbnail_warmup_schedules_missing_thumbnails(monkeypatch):
    from custom_components.xsense import recordings_media as media_source
    from custom_components.xsense.const import CONF_RECORDING_CACHE_MODE

    scheduled = []
    cached = []

    async def cache_thumbnail(self, clip):
        cached.append(clip["start"])
        return True

    monkeypatch.setattr(
        media_source.XSenseRecordingsMediaSource,
        "_async_cache_thumbnail",
        cache_thumbnail,
    )
    monkeypatch.setattr(
        media_source,
        "_path_ready",
        lambda path: str(path).endswith("1_2.jpg"),
    )
    entry = SimpleNamespace(options={CONF_RECORDING_CACHE_MODE: "retained"})
    source = media_source.XSenseRecordingsMediaSource(
        _recordings_media_source_hass(
            async_create_task=lambda coro: scheduled.append(coro),
            config_entries=SimpleNamespace(
                async_get_entry=lambda entry_id: entry
            ),
        )
    )
    clips = [
        {
            "thumbnail_url": "https://example.invalid/already.jpg",
            "serial": "CAMERA-SN",
            "start": 1,
            "end": 2,
        },
        *[
            {
                "thumbnail_url": f"https://example.invalid/{index}.jpg",
                "serial": "CAMERA-SN",
                "start": index,
                "end": index + 1,
            }
            for index in range(2, 14)
        ],
        {"serial": "CAMERA-SN", "start": 99, "end": 100},
    ]

    source._schedule_thumbnail_warmup(clips)

    assert len(scheduled) == 1
    asyncio.run(scheduled[0])
    assert cached == list(range(2, 12))


def test_clear_recording_caches_removes_managers_and_media(monkeypatch):
    from custom_components.xsense import recordings_media as media_source

    cleared_media = []

    class Manager:
        def __init__(self):
            self.removed = False

        async def async_clear(self):
            self.removed = True

    async def async_add_executor_job(func, *args):
        return func(*args)

    manager = Manager()
    hass = SimpleNamespace(
        data={media_source.DOMAIN: {"_recording_indexes": {"entry-id": manager}}},
        config_entries=SimpleNamespace(async_entries=lambda domain: []),
        async_add_executor_job=async_add_executor_job,
    )
    def delete_groups(root, protected, keys, prefixes, suppress_recache=False):
        cleared_media.append([root])
        return media_source._empty_cache_cleanup_summary()

    monkeypatch.setattr(media_source, "_delete_media_cache_groups", delete_groups)

    asyncio.run(media_source.async_clear_recording_caches(hass))

    assert manager.removed
    assert "_recording_indexes" not in hass.data[media_source.DOMAIN]
    assert len(cleared_media) == 1
    assert [path.as_posix() for path in cleared_media[0]] == ["/media/xsense_recordings"]


def test_clear_recording_caches_scopes_media_to_entry(monkeypatch):
    from custom_components.xsense import recordings_media as media_source
    from custom_components.xsense.const import CONF_RECORDING_MEDIA_STORAGE_PATH

    cleared_media = []

    async def async_add_executor_job(func, *args):
        return func(*args)

    entry = SimpleNamespace(
        entry_id="entry-id",
        data={},
        options={CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/xsense_custom"},
    )
    hass = SimpleNamespace(
        data={media_source.DOMAIN: {"_recording_indexes": {}}},
        config_entries=SimpleNamespace(async_get_entry=lambda entry_id: entry),
        async_add_executor_job=async_add_executor_job,
    )
    def delete_groups(root, protected, keys, prefixes, suppress_recache=False):
        cleared_media.append([root])
        return media_source._empty_cache_cleanup_summary()

    monkeypatch.setattr(media_source, "_delete_media_cache_groups", delete_groups)

    asyncio.run(media_source.async_clear_recording_caches(hass, entry_id="entry-id"))

    assert len(cleared_media) == 1
    assert [path.as_posix() for path in cleared_media[0]] == ["/media/xsense_custom"]


def test_clear_recording_caches_removes_scoped_capture_locks(monkeypatch):
    from custom_components.xsense import recordings_media as media_source
    from custom_components.xsense.const import CONF_RECORDING_MEDIA_STORAGE_PATH

    async def async_add_executor_job(func, *args):
        return func(*args)

    entry = SimpleNamespace(
        entry_id="entry-id",
        data={},
        options={CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/xsense_custom"},
    )
    locks = {
        "/media/xsense_custom/videos/camera_1_2.mp4": object(),
        "/media/xsense_other/videos/camera_1_2.mp4": object(),
    }
    hass = SimpleNamespace(
        data={
            media_source.DOMAIN: {
                "_recording_indexes": {},
                "_recording_capture_locks": locks,
            }
        },
        config_entries=SimpleNamespace(async_get_entry=lambda entry_id: entry),
        async_add_executor_job=async_add_executor_job,
    )
    asyncio.run(media_source.async_clear_recording_caches(hass, entry_id="entry-id"))

    assert hass.data[media_source.DOMAIN]["_recording_capture_locks"] == {
        "/media/xsense_other/videos/camera_1_2.mp4": locks[
            "/media/xsense_other/videos/camera_1_2.mp4"
        ]
    }


def test_recording_cache_prune_removes_expired_clip_as_one_group(tmp_path):
    from custom_components.xsense import recordings_media as media_source

    key = "CAMERA_100_120"
    hls = tmp_path / "hls" / key
    thumb = tmp_path / "thumbs" / f"{key}.jpg"
    hls.mkdir(parents=True)
    thumb.parent.mkdir(parents=True)
    (hls / "index.m3u8").write_bytes(b"playlist")
    thumb.write_bytes(b"thumb")
    old = media_source.time() - 10 * 86400
    os.utime(hls, (old, old))
    os.utime(thumb, (old, old))

    result = media_source._prune_media_cache(
        tmp_path, retention_days=7, max_size_bytes=1024, protected=set()
    )

    assert result["deleted_items"] == 1
    assert result["deleted_bytes"] == len(b"playlistthumb")
    assert not hls.exists()
    assert not thumb.exists()


def test_recording_cache_prune_evicts_oldest_group_for_size(tmp_path):
    from custom_components.xsense import recordings_media as media_source

    video_root = tmp_path / "videos"
    video_root.mkdir()
    old = video_root / "CAMERA_100_120.mp4"
    recent = video_root / "CAMERA_200_220.mp4"
    old.write_bytes(b"a" * 80)
    recent.write_bytes(b"b" * 80)
    now = media_source.time()
    os.utime(old, (now - 60, now - 60))
    os.utime(recent, (now, now))

    result = media_source._prune_media_cache(
        tmp_path, retention_days=7, max_size_bytes=100, protected=set()
    )

    assert result["deleted_items"] == 1
    assert not old.exists()
    assert recent.exists()
    assert result["remaining_bytes"] == 80


def test_recording_cache_prune_protects_active_hls(tmp_path):
    from custom_components.xsense import recordings_media as media_source

    hls = tmp_path / "hls" / "CAMERA_100_120"
    hls.mkdir(parents=True)
    (hls / "index.m3u8").write_bytes(b"playlist")
    old = media_source.time() - 10 * 86400
    os.utime(hls, (old, old))

    result = media_source._prune_media_cache(
        tmp_path,
        retention_days=7,
        max_size_bytes=1024,
        protected={hls.resolve()},
    )

    assert result["deleted_items"] == 0
    assert result["skipped_active"] == 1
    assert hls.exists()


def test_recording_cache_prune_supports_playback_session_ttl(tmp_path):
    from custom_components.xsense import recordings_media as media_source

    video = tmp_path / "videos" / "CAMERA_100_120.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"video")
    old = media_source.time() - 1900
    os.utime(video, (old, old))

    result = media_source._prune_media_cache(
        tmp_path,
        retention_days=7,
        max_size_bytes=1024,
        protected=set(),
        retention_seconds=1800,
    )

    assert result["deleted_items"] == 1
    assert not video.exists()


def test_recording_cache_release_revokes_matching_proxy_token(tmp_path):
    from custom_components.xsense import recordings_media as media_source

    key = "CAMERA_100_120"
    tokens = {
        "matching": {
            "mode": "proxy",
            "media_root": tmp_path,
            "cache_key": key,
            "expires": media_source.monotonic() + 60,
        },
        "other": {
            "mode": "proxy",
            "media_root": tmp_path,
            "cache_key": "OTHER_100_120",
            "expires": media_source.monotonic() + 60,
        },
    }
    hass = SimpleNamespace(
        data={media_source.DOMAIN: {"_recording_hls_tokens": tokens}}
    )

    media_source._revoke_hls_tokens(
        hass,
        [tmp_path],
        keys={key},
        key_prefixes=None,
    )

    assert "matching" not in tokens
    assert "other" in tokens


def test_delete_camera_cache_only_removes_matching_serial(tmp_path):
    from custom_components.xsense import recordings_media as media_source

    hls_root = tmp_path / "hls"
    first = hls_root / "CAMERA_A_100_120"
    second = hls_root / "CAMERA_B_100_120"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    (first / "index.m3u8").write_bytes(b"first")
    (second / "index.m3u8").write_bytes(b"second")

    result = media_source._delete_media_cache_groups(
        tmp_path, set(), None, {"CAMERA_A_"}
    )

    assert result["deleted_items"] == 1
    assert not first.exists()
    assert second.exists()


def test_manual_recording_cache_delete_suppresses_background_recaching(
    monkeypatch, tmp_path
):
    from custom_components.xsense import recordings_media as media_source

    monkeypatch.setattr(
        media_source, "_recording_media_root_from_value", lambda value: tmp_path
    )

    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-A",
        "start": 100,
        "end": 120,
        "media_root": tmp_path,
    }
    hls = media_source._hls_cache_dir(clip)
    hls.mkdir(parents=True)
    (hls / "index.m3u8").write_bytes(b"playlist")

    async def async_add_executor_job(func, *args):
        return func(*args)

    hass = SimpleNamespace(data={}, async_add_executor_job=async_add_executor_job)

    result = asyncio.run(
        media_source.async_delete_recording_cache(
            hass, clip, suppress_recache=True
        )
    )

    assert result["deleted_items"] == 1
    assert not hls.exists()
    assert asyncio.run(media_source.async_recording_cache_suppressed(hass, clip))

    asyncio.run(media_source.async_allow_recording_cache(hass, clip))

    assert not asyncio.run(media_source.async_recording_cache_suppressed(hass, clip))


def test_automatic_recording_cache_cleanup_does_not_suppress_recaching(
    monkeypatch, tmp_path
):
    from custom_components.xsense import recordings_media as media_source

    monkeypatch.setattr(
        media_source, "_recording_media_root_from_value", lambda value: tmp_path
    )

    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-A",
        "start": 100,
        "end": 120,
        "media_root": tmp_path,
    }
    hls = media_source._hls_cache_dir(clip)
    hls.mkdir(parents=True)
    (hls / "index.m3u8").write_bytes(b"playlist")

    media_source._delete_media_cache_groups(
        tmp_path,
        set(),
        {media_source._cache_group_key_for_clip(clip)},
        None,
    )

    assert not media_source._recording_cache_suppressed(clip)


def test_recording_media_sync_starts_only_when_enabled(monkeypatch):
    from custom_components.xsense import recordings_media as media_source
    from custom_components.xsense.const import (
        CONF_RECORDING_CACHE_MODE,
        CONF_RECORDING_MEDIA_SYNC_ENABLED,
        CONF_RECORDING_MEDIA_SYNC_HOURS,
    )

    calls = []

    def async_call_later(hass, delay, action):
        calls.append(("later", delay, action))
        return lambda: None

    def async_track_time_interval(hass, action, interval):
        calls.append(("interval", interval, action))
        return lambda: None

    monkeypatch.setattr(media_source, "async_call_later", async_call_later)
    monkeypatch.setattr(media_source, "async_track_time_interval", async_track_time_interval)

    unloads = []
    entries = {}
    hass = SimpleNamespace(
        data={},
        config_entries=SimpleNamespace(async_get_entry=entries.get),
    )
    disabled_entry = SimpleNamespace(
        entry_id="entry-disabled",
        options={},
        async_on_unload=unloads.append,
    )
    entries[disabled_entry.entry_id] = disabled_entry
    media_source.async_start_recording_media_sync(hass, disabled_entry)
    assert calls[0][0:2] == ("later", 60)
    assert calls[1][0] == "interval"
    assert calls[1][1].total_seconds() == 3600
    assert len(unloads) == 1

    enabled_entry = SimpleNamespace(
        entry_id="entry-enabled",
        options={
            CONF_RECORDING_CACHE_MODE: "retained",
            CONF_RECORDING_MEDIA_SYNC_ENABLED: True,
            CONF_RECORDING_MEDIA_SYNC_HOURS: 6,
        },
        async_on_unload=unloads.append,
    )
    entries[enabled_entry.entry_id] = enabled_entry
    media_source.async_start_recording_media_sync(hass, enabled_entry)

    assert calls[2][0:2] == ("later", 60)
    assert calls[3][0] == "interval"
    assert calls[3][1].total_seconds() == 3600
    assert calls[4][0:2] == ("later", 30)
    assert calls[5][0] == "interval"
    assert calls[5][1].total_seconds() == 21600
    assert calls[6][0] == "interval"
    assert calls[6][1].total_seconds() == 120
    assert len(unloads) == 2
    assert callable(unloads[0])


def test_playback_only_cache_schedules_cleanup(monkeypatch):
    from custom_components.xsense import recordings_media as media_source

    calls = []
    deleted = []
    entry = SimpleNamespace(entry_id="entry-id", options={})
    hass = SimpleNamespace(
        data={},
        loop=object(),
        config_entries=SimpleNamespace(async_get_entry=lambda entry_id: entry),
    )

    def call_later(hass_arg, delay, action):
        calls.append((delay, action))
        return lambda: None

    async def delete_cache(hass_arg, clip):
        deleted.append(clip)
        return media_source._empty_cache_cleanup_summary()

    monkeypatch.setattr(media_source, "async_call_later", call_later)
    monkeypatch.setattr(media_source, "async_delete_recording_cache", delete_cache)
    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA",
        "start": 100,
        "end": 120,
    }

    media_source.async_schedule_temporary_recording_cleanup(hass, clip)

    assert calls[0][0] == 1800
    asyncio.run(calls[0][1]())
    assert deleted == [clip]
    assert "_recording_temporary_cleanup_unsubs" not in hass.data[media_source.DOMAIN]


def test_retained_cache_does_not_schedule_temporary_cleanup(monkeypatch):
    from custom_components.xsense import recordings_media as media_source
    from custom_components.xsense.const import CONF_RECORDING_CACHE_MODE

    entry = SimpleNamespace(options={CONF_RECORDING_CACHE_MODE: "retained"})
    hass = SimpleNamespace(
        data={},
        loop=object(),
        config_entries=SimpleNamespace(async_get_entry=lambda entry_id: entry),
    )
    monkeypatch.setattr(
        media_source,
        "async_call_later",
        lambda *args: pytest.fail("retained cache must not schedule cleanup"),
    )

    media_source.async_schedule_temporary_recording_cleanup(
        hass,
        {"entry_id": "entry-id", "serial": "CAMERA", "start": 100, "end": 120},
    )


def test_motion_event_data_exposes_direct_recording_url_aliases():
    event_data = event.motion_event_data(
        {
            "eventTime": "20260621134144",
            "playback": {
                "source": "video_url",
                "trace_id": "trace-id",
                "video_url": "https://example.invalid/clip.mp4",
                "image_url": "https://example.invalid/still.jpg",
                "package_image_url": "https://example.invalid/package.jpg",
            },
        }
    )

    assert event_data == {
        "time": "20260621134144",
        "playback": {
            "source": "video_url",
            "trace_id": "trace-id",
            "video_url": "https://example.invalid/clip.mp4",
            "image_url": "https://example.invalid/still.jpg",
            "package_image_url": "https://example.invalid/package.jpg",
        },
        "recording_direct_url": "https://example.invalid/clip.mp4",
        "snapshot_url": "https://example.invalid/still.jpg",
        "recording_source": "video_url",
    }
    assert event.motion_fingerprint(event_data) == ("20260621134144",)


def test_motion_event_entity_triggers_repeated_motion_with_new_time():
    camera_entity = entity("SSC0A", {"eventTime": "20260621134144"})
    event_entity = event.XSenseMotionEventEntity.__new__(
        event.XSenseMotionEventEntity
    )
    event_entity._motion_initialized = False
    event_entity._last_motion_fingerprint = None
    event_entity.hass = object()
    event_entity.platform = object()
    event_entity._current_entity = lambda: camera_entity
    triggered = []
    event_entity._trigger_event = lambda event_type, data: triggered.append(
        (event_type, data["time"])
    )
    event_entity.async_write_ha_state = lambda: None

    event_entity._handle_coordinator_update()
    camera_entity.data["eventTime"] = "20260621134200"
    event_entity._handle_coordinator_update()
    event_entity._handle_coordinator_update()

    assert triggered == [("motion", "20260621134200")]


def test_motion_event_entity_does_not_retrigger_when_history_enriches_mqtt_event():
    camera_entity = entity("SSC0A", {"eventTime": "20260621134144"})
    event_entity = event.XSenseMotionEventEntity.__new__(
        event.XSenseMotionEventEntity
    )
    event_entity._motion_initialized = False
    event_entity._last_motion_fingerprint = None
    event_entity.hass = object()
    event_entity.platform = object()
    event_entity._current_entity = lambda: camera_entity
    triggered = []
    event_entity._trigger_event = lambda event_type, data: triggered.append(
        (event_type, data["time"])
    )
    event_entity.async_write_ha_state = lambda: None

    event_entity._handle_coordinator_update()
    camera_entity.data["playback"] = {
        "trace_id": "history-trace-id",
        "video_url": "https://example.invalid/history.m3u8",
    }
    event_entity._handle_coordinator_update()

    assert triggered == []


def test_motion_event_entity_baselines_latest_apk_history_without_triggering():
    camera_entity = entity(
        "SSC0A",
        {
            "eventTime": "20260621134144",
            "cameraEventBaseline": True,
            "playback": {"image_url": "https://example.invalid/latest.jpg"},
        },
    )
    event_entity = event.XSenseMotionEventEntity.__new__(
        event.XSenseMotionEventEntity
    )
    event_entity._motion_initialized = True
    event_entity._last_motion_fingerprint = ("20260620120000",)
    event_entity.hass = object()
    event_entity.platform = object()
    event_entity._current_entity = lambda: camera_entity
    triggered = []
    event_entity._trigger_event = lambda *args: triggered.append(args)
    event_entity.async_write_ha_state = lambda: None

    event_entity._handle_coordinator_update()

    assert triggered == []
    assert event_entity._last_motion_fingerprint == ("20260621134144",)
    assert camera_entity.data["cameraEventBaseline"] is False

    camera_entity.data["eventTime"] = "20260621134200"
    event_entity._handle_coordinator_update()

    assert len(triggered) == 1


def test_camera_entity_rebinds_by_strong_addx_identity_only():
    original = entity("SSC0A", {"addxSerialNumber": "physical-camera-1"})
    original.entity_id = "old-camera-id"
    original.sn = "shared-label"
    refreshed = entity("SSC0A", {"addxSerialNumber": "physical-camera-1"})
    refreshed.entity_id = "new-camera-id"
    refreshed.sn = "shared-label"
    other = entity("SSC0A", {"addxSerialNumber": "physical-camera-2"})
    other.entity_id = "other-camera-id"
    other.sn = "shared-label"
    camera_entity = camera.XSenseCameraEntity.__new__(camera.XSenseCameraEntity)
    camera_entity.coordinator = SimpleNamespace(
        data={"stations": {refreshed.entity_id: refreshed, other.entity_id: other}}
    )
    camera_entity._station_id = None
    camera_entity._dev_id = original.entity_id
    camera_entity._camera_identity = "physical-camera-1"

    assert camera_entity._current_entity() is refreshed


def test_camera_event_entity_rejects_ambiguous_weak_identity():
    camera_1 = entity("SSC0A", {"addxSerialNumber": "physical-camera-1"})
    camera_1.entity_id = "camera-1"
    camera_1.sn = "shared-label"
    camera_2 = entity("SSC0A", {"addxSerialNumber": "physical-camera-2"})
    camera_2.entity_id = "camera-2"
    camera_2.sn = "shared-label"
    event_entity = event.XSenseMotionEventEntity.__new__(
        event.XSenseMotionEventEntity
    )
    event_entity.coordinator = SimpleNamespace(
        data={"stations": {camera_1.entity_id: camera_1, camera_2.entity_id: camera_2}}
    )
    event_entity._device_entity = False
    event_entity._dev_id = "missing-camera-id"
    event_entity._camera_identity = "shared-label"

    assert event_entity._current_entity() is None


def test_ai_detection_event_data_uses_apk_detection_payload():
    event_data = event.ai_detection_event_data(
        {
            "lastAiDetection": "package_pick_up,person",
            "lastPackagePickUpDetectionTime": "20260614230200",
            "lastPersonDetectionTime": "20260614230100",
        }
    )

    assert event_data == {
        "objects": ["package_pick_up", "person"],
        "last_ai_detection": "package_pick_up,person",
        "object_times": {
            "package_pick_up": "20260614230200",
            "person": "20260614230100",
        },
        "time": "20260614230200",
    }
    assert event.ai_detection_fingerprint(event_data) == (
        ("package_pick_up", "person"),
        (
            ("package_pick_up", "20260614230200"),
            ("person", "20260614230100"),
        ),
        "20260614230200",
    )


def test_ai_detection_event_data_uses_fallback_event_time():
    event_data = event.ai_detection_event_data(
        {
            "lastAiDetection": "person",
            "eventTime": "20260614230300",
        }
    )

    assert event_data == {
        "objects": ["person"],
        "last_ai_detection": "person",
        "object_times": {"person": "20260614230300"},
        "time": "20260614230300",
    }


def test_ai_detection_event_entity_triggers_repeated_same_object_with_new_time():
    camera_entity = entity(
        "SSC0A",
        {
            "supportPersonDetect": True,
            "lastAiDetection": "person",
            "lastPersonDetectionTime": "20260614230100",
        },
    )
    event_entity = event.XSenseEventEntity.__new__(event.XSenseEventEntity)
    event_entity._ai_detection_initialized = False
    event_entity._last_ai_detection_fingerprint = None
    event_entity.hass = object()
    event_entity.platform = object()
    event_entity._current_entity = lambda: camera_entity
    triggered = []
    event_entity._trigger_event = lambda event_type, data: triggered.append(
        (event_type, data["time"])
    )
    event_entity.async_write_ha_state = lambda: None

    event_entity._handle_coordinator_update()
    camera_entity.data["lastPersonDetectionTime"] = "20260614230200"
    event_entity._handle_coordinator_update()

    assert triggered == [("person", "20260614230200")]


def test_ai_detection_event_data_ignores_missing_or_unknown_objects():
    assert event.ai_detection_event_data({}) is None
    assert event.ai_detection_event_data({"lastAiDetection": "unknown"}) is None


def test_ai_detection_event_entity_triggers_first_new_event_after_empty_startup():
    camera_entity = entity("SSC0A", {"supportPersonDetect": True})
    event_entity = event.XSenseEventEntity.__new__(event.XSenseEventEntity)
    event_entity._ai_detection_initialized = False
    event_entity._last_ai_detection_fingerprint = None
    event_entity.hass = object()
    event_entity.platform = object()
    event_entity._current_entity = lambda: camera_entity
    triggered = []
    event_entity._trigger_event = lambda event_type, data: triggered.append(
        (event_type, data)
    )
    event_entity.async_write_ha_state = lambda: triggered.append(("write", None))

    event_entity._handle_coordinator_update()
    assert triggered == [("write", None)]

    camera_entity.data.update(
        {
            "lastAiDetection": "person",
            "lastPersonDetectionTime": "20260614230100",
        }
    )
    event_entity._handle_coordinator_update()
    event_entity._handle_coordinator_update()

    assert triggered == [
        ("write", None),
        (
            "person",
            {
                "objects": ["person"],
                "last_ai_detection": "person",
                "object_times": {"person": "20260614230100"},
                "time": "20260614230100",
            },
        ),
        ("write", None),
        ("write", None),
    ]


def test_ai_detection_event_entity_does_not_write_before_added():
    camera_entity = entity("SSC0A", {"supportPersonDetect": True})
    event_entity = event.XSenseEventEntity.__new__(event.XSenseEventEntity)
    event_entity._ai_detection_initialized = False
    event_entity._last_ai_detection_fingerprint = None
    event_entity._current_entity = lambda: camera_entity
    triggered = []
    event_entity.async_write_ha_state = lambda: triggered.append(("write", None))

    event_entity._handle_coordinator_update()

    assert triggered == []


def test_camera_availability_follows_apk_non_offline_statuses():
    from custom_components.xsense.python_xsense.entity_map import EntityType
    from custom_components.xsense.entity import _apk_entity_is_available

    camera = SimpleNamespace(
        entity_type=EntityType.CAMERA,
        online=False,
        data={"deviceStatus": 11},
    )

    assert _apk_entity_is_available(camera)

    camera.data["deviceStatus"] = 12
    assert _apk_entity_is_available(camera)

    camera.data["deviceStatus"] = 0
    assert not _apk_entity_is_available(camera)

    camera.online = True
    assert _apk_entity_is_available(camera)


async def test_webrtc_offer_uses_ticket_without_direct_stream_keepalive():
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseWebRTCCameraEntity,
    )

    calls = []
    camera_entity = entity("SSC0A", {"streamProtocol": "webrtc"})
    camera_entity.entity_id = "camera-test"
    camera_entity.sn = "SSC0ATEST"
    camera_entity.name = "Camera"
    camera_entity.online = True

    class XSense:
        async def get_camera_webrtc_ticket(self, entity, *, force_refresh=False):
            calls.append(("ticket", entity.sn, force_refresh))
            return None

    class Coordinator:
        def __init__(self):
            self.data = {
                "stations": {camera_entity.entity_id: camera_entity},
                "devices": {},
            }
            self.xsense = XSense()

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    camera = XSenseWebRTCCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)
    messages = []

    await camera.async_handle_async_webrtc_offer(
        "v=0\r\n", "session-1", messages.append
    )

    assert calls == [("ticket", "SSC0ATEST", True)]
    assert messages[0].code == "xsense_webrtc_ticket_failed"


async def test_webrtc_offer_reports_ticket_api_failure_without_raising(caplog):
    from custom_components.xsense.python_xsense.exceptions import APIFailure
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseWebRTCCameraEntity,
    )

    camera_entity = entity("SSC0A", {"streamProtocol": "webrtc"})
    camera_entity.entity_id = "camera-test"
    camera_entity.sn = "SSC0ATEST"
    camera_entity.name = "Camera"
    camera_entity.online = True

    class XSense:
        async def get_camera_webrtc_ticket(self, entity, *, force_refresh=False):
            raise APIFailure(
                "ADDX request for /device/getWebrtcTicket failed with error -2002/DEVICE_NO_ACCESS"
            )

    class Coordinator:
        def __init__(self):
            self.data = {
                "stations": {camera_entity.entity_id: camera_entity},
                "devices": {},
            }
            self.xsense = XSense()

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    camera = XSenseWebRTCCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)
    messages = []

    with caplog.at_level(logging.WARNING):
        await camera.async_handle_async_webrtc_offer(
            "v=0\r\n", "session-1", messages.append
        )

    assert messages[0].code == "xsense_webrtc_ticket_failed"
    assert camera._pending_webrtc_candidates == {}
    assert "X-Sense camera WebRTC ticket request failed" in caplog.text


def test_camera_wake_button_follows_apk_admin_support_and_sleep_state():
    camera = entity(
        "SSC0A",
        {"deviceStatus": 3, "isAdmin": True, "supportSleep": True},
    )

    assert button.can_wake_camera(camera, None)
    assert button.camera_is_sleeping(camera)

    camera.data["deviceStatus"] = 1
    assert button.can_wake_camera(camera, None)
    assert not button.camera_is_sleeping(camera)

    camera.data["deviceStatus"] = 3
    camera.data["isAdmin"] = False
    assert not button.can_wake_camera(camera, None)

    camera.data["isAdmin"] = True
    camera.data["supportSleep"] = False
    assert not button.can_wake_camera(camera, None)

    non_camera = entity(
        "XS01-WX",
        {"deviceStatus": 3, "isAdmin": True, "supportSleep": True},
    )
    assert not button.can_wake_camera(non_camera, None)




def test_alarm_status_is_unknown_until_reported():
    alarm = entity("XS01-WX", {})

    assert binary_sensor.has_alarm_status(alarm)
    assert binary_sensor.alarm_status(alarm) is None

    alarm.data["alarmStatus"] = "1"

    assert binary_sensor.alarm_status(alarm) is True


def test_camera_platform_does_not_load_optional_media_bridge():
    sys.modules.pop("custom_components.xsense.camera", None)
    sys.modules.pop("aiortc", None)

    from custom_components.xsense import camera  # noqa: F401

    assert "aiortc" not in sys.modules


def test_camera_capabilities_use_native_webrtc_path_for_supported_ipc_cameras():
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseWebRTCCameraEntity,
    )

    camera_entities = (
        entity("SSC0A", {"streamProtocol": "webrtc", "supportWebrtc": True}),
        entity("SSC0A", {"streamProtocol": "rtsp"}),
        entity("SSC0B", {"streamProtocol": "rtmp"}),
    )

    class Coordinator:
        def __init__(self, camera_entity):
            self.data = {
                "stations": {camera_entity.entity_id: camera_entity},
                "devices": {},
            }

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    for camera_entity in camera_entities:
        camera_entity.entity_id = (
            f"camera-{camera_entity.type}-{camera_entity.data['streamProtocol']}"
        )
        camera_entity.sn = "SSC0ATEST"
        camera_entity.name = "Camera"
        camera_entity.online = True

    for camera_entity in camera_entities:
        camera = XSenseWebRTCCameraEntity(
            Coordinator(camera_entity), camera_entity, CAMERA_DESCRIPTION
        )
        assert {
            stream.value for stream in camera.camera_capabilities.frontend_stream_types
        } == {"web_rtc"}


def test_camera_factory_uses_native_webrtc_path_by_default():
    camera_module = importlib.import_module("custom_components.xsense.camera")

    camera_entity = entity("SSC0A", {"streamProtocol": "webrtc", "supportWebrtc": True})
    camera_entity.entity_id = "camera-test"
    camera_entity.sn = "SSC0ATEST"
    camera_entity.name = "Camera"
    camera_entity.online = True

    class Coordinator:
        data = {"stations": {}, "devices": {}}

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    created = camera_module._camera_entity(Coordinator(), camera_entity)

    assert isinstance(created, camera_module.XSenseWebRTCCameraEntity)


async def test_base_camera_entity_does_not_probe_stream_provider():
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseCameraEntity,
    )

    camera_entity = entity("SSC0A", {"streamProtocol": "rtsp"})
    camera_entity.entity_id = "camera-test"
    camera_entity.sn = "SSC0ATEST"
    camera_entity.name = "Camera"
    camera_entity.online = True

    class Coordinator:
        data = {"stations": {camera_entity.entity_id: camera_entity}, "devices": {}}

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    async def provider_probe(hass, camera):
        return "provider"

    camera = XSenseCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)
    camera.entity_id = "camera.camera_test"

    assert await camera._async_get_supported_webrtc_provider(provider_probe) is None


async def test_default_native_webrtc_camera_allows_webrtc_provider_probe():
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseWebRTCCameraEntity,
    )

    camera_entity = entity("SSC0A", {"streamProtocol": "webrtc", "supportWebrtc": True})
    camera_entity.entity_id = "camera-test"
    camera_entity.sn = "SSC0ATEST"
    camera_entity.name = "Camera"
    camera_entity.online = True

    class Coordinator:
        data = {"stations": {camera_entity.entity_id: camera_entity}, "devices": {}}

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    async def provider_probe(hass, camera):
        return "provider"

    camera = XSenseWebRTCCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)
    camera.entity_id = "camera.camera_test"

    assert (
        await camera._async_get_supported_webrtc_provider(provider_probe)
        == "provider"
    )


def test_webrtc_client_config_uses_signal_relay_defaults():
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseWebRTCCameraEntity,
    )

    camera_entity = entity("SSC0A", {"streamProtocol": "webrtc", "supportWebrtc": True})
    camera_entity.entity_id = "camera-test"
    camera_entity.sn = "SSC0ATEST"
    camera_entity.name = "Camera"
    camera_entity.online = True

    class Coordinator:
        data = {"stations": {camera_entity.entity_id: camera_entity}, "devices": {}}

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    camera = XSenseWebRTCCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)

    config = camera._async_get_webrtc_client_configuration().to_frontend_dict()

    assert config["dataChannel"] == "data-channel-of-"
    assert "iceServers" not in config["configuration"]


def test_known_good_live_webrtc_path_does_not_reintroduce_drift():
    """Lock the relay architecture confirmed in v1.3.12.10 on June 25."""
    import inspect
    from pathlib import Path

    from custom_components.xsense import camera
    from custom_components.xsense.python_xsense import webrtc_signal
    from custom_components.xsense.python_xsense.async_xsense import AsyncXSense

    camera_source = Path(camera.__file__).read_text(encoding="utf-8")
    camera_entity_source = inspect.getsource(camera.XSenseWebRTCCameraEntity)
    session_source = Path(webrtc_signal.__file__).read_text(encoding="utf-8")
    ticket_source = inspect.getsource(AsyncXSense.get_camera_webrtc_ticket)

    forbidden_camera_patterns = {
        "XSenseCameraStreamView": "raw H264 bridge",
        "/api/xsense/camera_stream": "raw H264 bridge",
        "XSenseH264StreamSession": "raw H264 bridge",
        "_webrtc_ticket_prime_task": "ticket prewarm",
        "_schedule_webrtc_ticket_prime": "ticket prewarm",
        "_async_prime_webrtc_ticket": "ticket prewarm",
        "_webrtc_ticket_ice_servers": "ticket prewarm",
        "_mark_camera_webrtc_live": "active live marker",
        "_unmark_camera_webrtc_live": "active live marker",
        "_active_webrtc_camera_counts": "active live marker",
        "_async_stop_webrtc_camera_live": "extra stoplive layer",
    }

    for pattern, reason in forbidden_camera_patterns.items():
        assert pattern not in camera_source, f"Do not reintroduce {reason}: {pattern}"

    assert "XSenseWebRTCCameraEntity" in camera_source
    assert (
        'WebRTCClientConfiguration(data_channel="data-channel-of-")'
        in camera_entity_source
    )
    assert "async_handle_async_webrtc_offer" in camera_entity_source
    assert "XSenseWebRTCSignalSession(" in camera_entity_source
    assert "remote_candidate_callback=" in camera_entity_source
    assert "send_message(WebRTCAnswer(answer))" in camera_entity_source
    assert "class XSenseWebRTCSignalSession" in session_source
    assert "RTCPeerConnection" not in session_source
    assert "aiortc" not in session_source
    assert "start_forwarding_remote_candidates" in session_source
    assert "_forward_remote_candidate" in session_source
    assert "keep_camera_live_alive" not in camera_entity_source
    assert "XSenseWebRTCSession" not in session_source
    assert "verifyDormancyStatus=True" in ticket_source


def test_supported_ipc_camera_detection_is_model_based_not_transport_based():
    from custom_components.xsense import camera

    assert camera._is_supported_ipc_camera(entity("SSC0A", {}))
    assert camera._is_supported_ipc_camera(
        entity("SSC0A", {"streamProtocol": "webrtc"})
    )
    assert camera._is_supported_ipc_camera(entity("SSC0A", {"streamProtocol": "rtsp"}))
    assert camera._is_supported_ipc_camera(entity("SSC0B", {"streamProtocol": "RTMP"}))
    assert not camera._is_supported_ipc_camera(
        entity("XS01-M", {"streamProtocol": "webrtc"})
    )


def test_webrtc_candidate_debug_context_hides_raw_candidate():
    from custom_components.xsense import camera

    candidate = SimpleNamespace(
        candidate="candidate:1 1 UDP 2122260223 192.0.2.1 54321 typ host",
        sdp_mid="0",
        sdp_m_line_index=0,
    )

    context = camera._webrtc_candidate_debug_context(candidate)

    assert context == {
        "candidate_object": "SimpleNamespace",
        "candidate_present": True,
        "candidate_protocol": "udp",
        "candidate_type": "host",
        "sdp_mid": "0",
        "sdp_m_line_index": 0,
    }
    assert "192.0.2.1" not in str(context)


def test_camera_live_resolution_defaults_to_apk_live_view_default():
    from custom_components.xsense.python_xsense.async_xsense import camera_live_resolution

    camera_entity = entity(
        "SSC0A",
        {
            "supportedRecordingResolutions": ["1920x1080", "1280x720"],
            "deviceSupportResolution": ["1920x1080"],
        },
    )

    assert camera_live_resolution(camera_entity) == "1920x1080"

    camera_entity.data["liveResolution"] = "1920x1080"
    assert camera_live_resolution(camera_entity) == "1920x1080"


@pytest.mark.parametrize(
    ("camera_type", "protocol"),
    (
        ("SSC0A", "webrtc"),
        ("SSC0A", "rtsp"),
        ("SSC0B", "rtmp"),
    ),
)
async def test_supported_ipc_camera_always_uses_native_webrtc_entity(
    camera_type, protocol
):
    from custom_components.xsense import camera as camera_module
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseWebRTCCameraEntity,
    )

    camera_entity = entity(
        camera_type, {"streamProtocol": protocol, "supportWebrtc": True}
    )
    camera_entity.entity_id = "camera-test"
    camera_entity.sn = "SSC0ATEST"
    camera_entity.name = "Camera"
    camera_entity.online = True

    class Coordinator:
        def __init__(self):
            self.entry = SimpleNamespace(entry_id="entry-1")
            self.data = {
                "stations": {camera_entity.entity_id: camera_entity},
                "devices": {},
            }

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    created = camera_module._camera_entity(Coordinator(), camera_entity)
    camera = XSenseWebRTCCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)
    camera.entity_id = "camera.camera_test"

    assert isinstance(created, XSenseWebRTCCameraEntity)
    assert await camera.stream_source() is None


async def test_unsupported_camera_type_has_no_stream_source():
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseCameraEntity,
    )

    camera_entity = entity("XS01-M", {"streamProtocol": "webrtc"})
    camera_entity.entity_id = "camera-test"
    camera_entity.sn = "XS01MTEST"
    camera_entity.name = "Smoke"
    camera_entity.online = True

    class Coordinator:
        def __init__(self):
            self.entry = SimpleNamespace(entry_id="entry-1")
            self.data = {
                "stations": {camera_entity.entity_id: camera_entity},
                "devices": {},
            }

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    camera = XSenseCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)
    camera.entity_id = "camera.camera_test"
    camera.hass = SimpleNamespace(data={})

    assert await camera.stream_source() is None


def test_camera_thumbnail_urls_prefer_full_event_images_over_list_thumbnails():
    from custom_components.xsense.python_xsense.async_xsense import (
        camera_thumbnail_urls,
    )

    camera_entity = entity(
        "SSC0A",
        {
            "thumbImgUrl": "https://example.invalid/current.jpg",
            "playback": {
                "image_url": "https://example.invalid/event.jpg",
                "package_image_url": "https://example.invalid/package.jpg",
            },
            "imageUrl": "https://example.invalid/direct.jpg",
        },
    )

    assert camera_thumbnail_urls(camera_entity) == (
        "https://example.invalid/event.jpg",
        "https://example.invalid/direct.jpg",
        "https://example.invalid/package.jpg",
        "https://example.invalid/current.jpg",
    )


def test_camera_thumbnail_urls_prefer_newer_event_image():
    from custom_components.xsense.python_xsense.async_xsense import (
        camera_thumbnail_urls,
    )

    camera_entity = entity(
        "SSC0A",
        {
            "thumbImgUrl": "https://example.invalid/current.jpg",
            "thumbImgTime": 1_700_000_000,
            "playback": {
                "image_url": "https://example.invalid/event.jpg",
                "timestamp_s": 1_700_000_100,
            },
        },
    )

    assert camera_thumbnail_urls(camera_entity) == (
        "https://example.invalid/event.jpg",
        "https://example.invalid/current.jpg",
    )


def test_camera_thumbnail_urls_keep_durable_event_image_ahead_of_stale_push_image():
    from custom_components.xsense.python_xsense.async_xsense import (
        camera_thumbnail_urls,
    )

    camera_entity = entity(
        "SSC0A",
        {
            "lastEventImageUrl": "https://example.invalid/event.jpg",
            "lastEventImageTime": 1_700_000_100,
            "lastPushImageUrl": "https://example.invalid/push.jpg",
            "lastPushTime": 1_700_000_000,
        },
    )

    assert camera_thumbnail_urls(camera_entity) == (
        "https://example.invalid/event.jpg",
        "https://example.invalid/push.jpg",
    )


async def test_camera_image_uses_adapter_and_keeps_last_good_image():
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseCameraEntity,
    )

    camera_entity = entity("SSC0A", {})
    camera_entity.entity_id = "camera-test"
    camera_entity.sn = "SSC0ATEST"
    camera_entity.name = "Camera"
    images = iter((b"jpeg-image", None))

    async def get_camera_thumbnail(current):
        assert current is camera_entity
        return next(images)

    class Coordinator:
        def __init__(self):
            self.data = {
                "stations": {camera_entity.entity_id: camera_entity},
                "devices": {},
            }
            self.xsense = SimpleNamespace(
                get_camera_thumbnail=get_camera_thumbnail,
            )

        def camera_event_snapshot(self, current):
            assert current is camera_entity
            return None

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    camera = XSenseCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)
    camera.entity_id = "camera.camera_test"

    assert await camera.async_camera_image() == b"jpeg-image"
    assert await camera.async_camera_image() == b"jpeg-image"


async def test_camera_image_prefers_derived_event_frame_over_cloud_thumbnail():
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseCameraEntity,
    )

    camera_entity = entity("SSC0A", {"eventTime": "20260903172848"})
    camera_entity.entity_id = "camera-test"
    camera_entity.sn = "SSC0ATEST"
    camera_entity.name = "Camera"

    async def unexpected_thumbnail(current):
        raise AssertionError("cloud thumbnail must remain a fallback")

    class Coordinator:
        def __init__(self):
            self.data = {
                "stations": {camera_entity.entity_id: camera_entity},
                "devices": {},
            }
            self.xsense = SimpleNamespace(get_camera_thumbnail=unexpected_thumbnail)

        def camera_event_snapshot(self, current):
            assert current is camera_entity
            return b"high-resolution-event-frame"

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    camera = XSenseCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)

    assert await camera.async_camera_image() == b"high-resolution-event-frame"


def test_camera_event_snapshot_extraction_uses_best_video_only_ffmpeg(monkeypatch):
    from custom_components.xsense import recordings_media as media_source

    jpeg = b"\xff\xd8\xff\xc0\x00\x07\x08\x04\x38\x07\x80"
    calls = []

    monkeypatch.setattr(media_source.shutil, "which", lambda executable: "/ffmpeg")

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout=jpeg, stderr=b"")

    monkeypatch.setattr(media_source.subprocess, "run", run)

    result = media_source._extract_camera_event_snapshot(
        "https://example.invalid/event-hd.m3u8"
    )

    assert result == {
        "image": jpeg,
        "width": 1920,
        "height": 1080,
        "returncode": 0,
    }
    command, kwargs = calls[0]
    assert command[command.index("-i") + 1] == "https://example.invalid/event-hd.m3u8"
    assert "-an" in command
    assert "-map" not in command
    assert "-ss" not in command
    assert kwargs == {"capture_output": True, "check": False, "timeout": 10}


async def test_camera_image_waits_for_current_event_frame_before_thumbnail():
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseCameraEntity,
    )

    camera_entity = entity(
        "SSC0A",
        {
            "eventTime": "20260905190000",
            "playback": {"video_url": "https://example.invalid/event.m3u8"},
        },
    )
    camera_entity.entity_id = "camera-test"
    camera_entity.sn = "SSC0ATEST"
    camera_entity.name = "Camera"
    order = []

    async def prepare_snapshot(current):
        assert current is camera_entity
        order.append("extract")
        await asyncio.sleep(0)
        return b"full-resolution-frame"

    async def unexpected_thumbnail(current):
        order.append("thumbnail")
        return b"low-resolution-thumbnail"

    class Coordinator:
        def __init__(self):
            self.data = {
                "stations": {camera_entity.entity_id: camera_entity},
                "devices": {},
            }
            self.xsense = SimpleNamespace(get_camera_thumbnail=unexpected_thumbnail)

        async_camera_event_snapshot = staticmethod(prepare_snapshot)

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    camera = XSenseCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)

    assert await camera.async_camera_image() == b"full-resolution-frame"
    assert order == ["extract"]


def test_camera_event_snapshot_prefers_hd_recording_candidate(monkeypatch):
    from custom_components.xsense import recordings_media as media_source

    extracted = []

    def extract(url):
        extracted.append(url)
        return {"image": b"jpeg", "width": 1920, "height": 1080, "returncode": 0}

    monkeypatch.setattr(media_source, "_extract_camera_event_snapshot", extract)
    hass = SimpleNamespace(
        async_add_executor_job=lambda func, *args: asyncio.to_thread(func, *args)
    )

    image = asyncio.run(
        media_source.async_extract_camera_event_snapshot(
            hass,
            {
                "video_url": "https://example.invalid/event-720.m3u8",
                "resolution": "1280x720",
                "multi_resolution_videos": [
                    {
                        "videoUrl": "https://example.invalid/event-1080.m3u8",
                        "resolutionInfo": "1920x1080",
                    }
                ],
            },
        )
    )

    assert image == b"jpeg"
    assert extracted == ["https://example.invalid/event-1080.m3u8"]


async def test_failed_webrtc_signal_start_is_removed_from_sessions(monkeypatch):
    from custom_components.xsense import camera as camera_module
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseWebRTCCameraEntity,
    )

    camera_entity = entity("SSC0A", {"streamProtocol": "webrtc", "supportWebrtc": True})
    camera_entity.entity_id = "camera-test"
    camera_entity.sn = "SSC0ATEST"
    camera_entity.name = "Camera"
    camera_entity.online = True

    async def get_camera_webrtc_ticket(entity, *, force_refresh=False):
        return {"signalServer": "signal"}

    class Coordinator:
        def __init__(self):
            self.data = {
                "stations": {camera_entity.entity_id: camera_entity},
                "devices": {},
            }
            self.xsense = SimpleNamespace(
                get_camera_webrtc_ticket=get_camera_webrtc_ticket,
            )

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    class FakeSession:
        def __init__(self, **kwargs):
            self.closed = False

        async def start(self):
            raise RuntimeError("signal failed")

        async def close(self):
            self.closed = True

    fake_module = SimpleNamespace(
        XSenseWebRTCTicket=SimpleNamespace(
            from_api=lambda serial_number, data: SimpleNamespace(is_valid=True)
        ),
        XSenseWebRTCSignalSession=FakeSession,
    )

    class FakeHass:
        data = {}

        async def async_add_import_executor_job(self, func, module):
            return fake_module

        def async_create_task(self, coro):
            return asyncio.create_task(coro)

    monkeypatch.setattr(
        camera_module, "async_get_clientsession", lambda hass: SimpleNamespace()
    )

    camera = XSenseWebRTCCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)
    camera.hass = FakeHass()
    messages = []

    await camera.async_handle_async_webrtc_offer(
        "v=0\r\n", "session-1", messages.append
    )

    assert camera._webrtc_sessions == {}
    assert camera.hass.data.get(camera_module.DOMAIN, {}).get(
        "_active_webrtc_camera_counts"
    ) is None
    assert not camera.is_streaming
    assert messages[0].code == "xsense_webrtc_start_failed"


async def test_webrtc_offer_uses_accepted_ticket_serial_for_signal_recipient(
    monkeypatch,
):
    from custom_components.xsense import camera as camera_module
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseWebRTCCameraEntity,
    )
    from homeassistant.components.camera.webrtc import WebRTCAnswer

    camera_entity = entity(
        "SSC0A",
        {
            "streamProtocol": "webrtc",
            "supportWebrtc": True,
            "resolution": "1280x720",
        },
    )
    camera_entity.entity_id = "right-addx-camera-id"
    camera_entity.sn = "label-or-ipc-sn"
    camera_entity.name = "Camera"
    camera_entity.online = True
    captured = {}

    async def get_camera_webrtc_ticket(entity, *, force_refresh=False):
        return {
            "serialNumber": "right-addx-camera-id",
            "signalServer": "wss://signal.example",
        }

    class Coordinator:
        def __init__(self):
            self.data = {
                "stations": {camera_entity.entity_id: camera_entity},
                "devices": {},
            }
            self.xsense = SimpleNamespace(
                get_camera_webrtc_ticket=get_camera_webrtc_ticket,
            )

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    class FakeTicket:
        is_valid = True

    def from_api(serial_number, data):
        captured["ticket_serial"] = serial_number
        return FakeTicket()

    class FakeSession:
        def __init__(self, **kwargs):
            captured["session_ticket"] = kwargs["ticket"]

        async def add_candidate(self, candidate):
            captured.setdefault("candidates", []).append(candidate)

        async def start(self):
            return "v=0\r\n"

        async def close(self):
            captured["closed"] = True

        def start_forwarding_remote_candidates(self):
            captured["forwarding"] = True

    fake_module = SimpleNamespace(
        XSenseWebRTCTicket=SimpleNamespace(from_api=from_api),
        XSenseWebRTCSignalSession=FakeSession,
    )

    class FakeHass:
        data = {}

        async def async_add_import_executor_job(self, func, module):
            return fake_module

        def async_create_task(self, coro):
            return asyncio.create_task(coro)

    monkeypatch.setattr(
        camera_module, "async_get_clientsession", lambda hass: SimpleNamespace()
    )

    camera = XSenseWebRTCCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)
    camera.hass = FakeHass()
    messages = []

    await camera.async_handle_async_webrtc_offer(
        "v=0\r\n", "session-1", messages.append
    )

    assert captured["ticket_serial"] == "right-addx-camera-id"
    assert captured["forwarding"] is True
    assert isinstance(messages[0], WebRTCAnswer)


async def test_webrtc_candidate_is_forwarded_to_matching_signal_session():
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseWebRTCCameraEntity,
    )

    camera_entity = entity("SSC0A", {"streamProtocol": "webrtc", "supportWebrtc": True})
    camera_entity.entity_id = "camera-test"
    camera_entity.sn = "SSC0ATEST"
    camera_entity.name = "Camera"
    camera_entity.online = True

    class Coordinator:
        data = {"stations": {camera_entity.entity_id: camera_entity}, "devices": {}}

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    class FakeSession:
        def __init__(self):
            self.candidates = []

        async def add_candidate(self, candidate):
            self.candidates.append(candidate)

    session = FakeSession()
    camera = XSenseWebRTCCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)
    camera._webrtc_sessions["session-1"] = session
    candidate = SimpleNamespace(candidate="candidate:1 1 udp 1 192.0.2.1 1 typ host")

    await camera.async_on_webrtc_candidate("session-1", candidate)

    assert session.candidates == [candidate]


async def test_early_webrtc_candidate_is_queued_until_signal_session_exists(
    monkeypatch,
):
    from homeassistant.components.camera.webrtc import WebRTCAnswer
    from custom_components.xsense import camera as camera_module
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseWebRTCCameraEntity,
    )

    camera_entity = entity("SSC0A", {"streamProtocol": "webrtc", "supportWebrtc": True})
    camera_entity.entity_id = "camera-test"
    camera_entity.sn = "SSC0ATEST"
    camera_entity.name = "Camera"
    camera_entity.online = True
    ticket_requested = asyncio.Event()
    release_ticket = asyncio.Event()

    async def get_camera_webrtc_ticket(entity, *, force_refresh=False):
        ticket_requested.set()
        await release_ticket.wait()
        return {
            "signalServer": "https://signal.example",
            "groupId": "group",
            "role": "viewer",
            "id": "client123",
            "traceId": "trace",
            "sign": "sig",
            "time": 123456,
            "expirationTime": 9999999999999,
            "iceServer": [],
        }

    class Coordinator:
        def __init__(self):
            self.data = {
                "stations": {camera_entity.entity_id: camera_entity},
                "devices": {},
            }
            self.xsense = SimpleNamespace(
                get_camera_webrtc_ticket=get_camera_webrtc_ticket,
            )

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    created_sessions = []

    class FakeSession:
        def __init__(self, **kwargs):
            self.candidates = []
            created_sessions.append(self)

        async def add_candidate(self, candidate):
            self.candidates.append(candidate)

        async def start(self):
            return "v=0\r\nanswer"

        def start_forwarding_remote_candidates(self):
            pass

        async def close(self):
            pass

    fake_module = SimpleNamespace(
        XSenseWebRTCTicket=SimpleNamespace(
            from_api=lambda serial_number, data: SimpleNamespace(is_valid=True)
        ),
        XSenseWebRTCSignalSession=FakeSession,
    )

    class FakeHass:
        data = {}

        async def async_add_import_executor_job(self, func, module):
            return fake_module

        def async_create_task(self, coro):
            return asyncio.create_task(coro)

    monkeypatch.setattr(
        camera_module, "async_get_clientsession", lambda hass: SimpleNamespace()
    )

    camera = XSenseWebRTCCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)
    camera.hass = FakeHass()
    messages = []
    candidate = SimpleNamespace(candidate="candidate:1 1 udp 1 192.0.2.1 1 typ host")

    offer_task = asyncio.create_task(
        camera.async_handle_async_webrtc_offer("v=0\r\n", "session-1", messages.append)
    )
    await ticket_requested.wait()
    await camera.async_on_webrtc_candidate("session-1", candidate)
    release_ticket.set()
    await offer_task

    assert len(created_sessions) == 1
    assert created_sessions[0].candidates == [candidate]
    assert camera._pending_webrtc_candidates == {}
    assert isinstance(messages[0], WebRTCAnswer)


async def test_new_webrtc_offer_closes_previous_signal_session(monkeypatch):
    from homeassistant.components.camera.webrtc import WebRTCAnswer
    from custom_components.xsense import camera as camera_module
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseWebRTCCameraEntity,
    )

    camera_entity = entity("SSC0A", {"streamProtocol": "webrtc", "supportWebrtc": True})
    camera_entity.entity_id = "camera-test"
    camera_entity.sn = "SSC0ATEST"
    camera_entity.name = "Camera"
    camera_entity.online = True

    async def get_camera_webrtc_ticket(entity, *, force_refresh=False):
        return {
            "signalServer": "https://signal.example",
            "groupId": "group",
            "role": "viewer",
            "id": "client123",
            "traceId": "trace",
            "sign": "sig",
            "time": 123456,
            "expirationTime": 9999999999999,
            "iceServer": [],
        }

    class Coordinator:
        def __init__(self):
            self.data = {
                "stations": {camera_entity.entity_id: camera_entity},
                "devices": {},
            }
            self.xsense = SimpleNamespace(
                get_camera_webrtc_ticket=get_camera_webrtc_ticket,
            )

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    class ExistingSession:
        def __init__(self):
            self.closed = False

        async def close(self):
            self.closed = True

    created_sessions = []

    class NewSession:
        def __init__(self, **kwargs):
            created_sessions.append(kwargs)

        async def start(self):
            return "v=0\r\nanswer"

        def start_forwarding_remote_candidates(self):
            pass

        async def close(self):
            pass

    fake_module = SimpleNamespace(
        XSenseWebRTCTicket=SimpleNamespace(
            from_api=lambda serial_number, data: SimpleNamespace(is_valid=True)
        ),
        XSenseWebRTCSignalSession=NewSession,
    )

    class FakeHass:
        data = {}

        async def async_add_import_executor_job(self, func, module):
            return fake_module

        def async_create_task(self, coro):
            return asyncio.create_task(coro)

    monkeypatch.setattr(
        camera_module, "async_get_clientsession", lambda hass: SimpleNamespace()
    )

    camera = XSenseWebRTCCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)
    camera.hass = FakeHass()
    old_session = ExistingSession()
    camera._webrtc_sessions["old-session"] = old_session
    messages = []

    await camera.async_handle_async_webrtc_offer(
        "v=0\r\n", "new-session", messages.append
    )

    assert old_session.closed is True
    assert list(camera._webrtc_sessions) == ["new-session"]
    assert len(created_sessions) == 1
    assert isinstance(messages[0], WebRTCAnswer)
    assert messages[0].answer == "v=0\r\nanswer"


async def test_frontend_webrtc_close_closes_signal_session():
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseWebRTCCameraEntity,
    )

    camera_entity = entity("SSC0A", {"streamProtocol": "webrtc", "supportWebrtc": True})
    camera_entity.entity_id = "camera-test"
    camera_entity.sn = "SSC0ATEST"
    camera_entity.name = "Camera"
    camera_entity.online = True
    camera_entity.data["cameraWebrtcTicket"] = {"id": "ticket-id"}

    class Coordinator:
        def __init__(self):
            self.data = {
                "stations": {camera_entity.entity_id: camera_entity},
                "devices": {},
            }

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    class Session:
        def __init__(self):
            self.closed = False

        async def close(self):
            self.closed = True

    tasks = []

    class FakeHass:
        data = {}

        def async_create_task(self, coro):
            task = asyncio.create_task(coro)
            tasks.append(task)
            return task

    camera = XSenseWebRTCCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)
    camera.hass = FakeHass()
    session = Session()
    camera._webrtc_sessions["session-1"] = session
    camera._pending_webrtc_candidates["session-1"] = [object()]

    camera.close_webrtc_session("session-1")
    await tasks[0]

    assert session.closed is True
    assert camera_entity.data["cameraWebrtcTicket"] == {"id": "ticket-id"}
    assert camera._webrtc_sessions == {}
    assert camera._pending_webrtc_candidates == {}


async def test_frontend_webrtc_close_keeps_live_when_other_session_exists():
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseWebRTCCameraEntity,
    )

    camera_entity = entity("SSC0A", {"streamProtocol": "webrtc", "supportWebrtc": True})
    camera_entity.entity_id = "camera-test"
    camera_entity.sn = "SSC0ATEST"
    camera_entity.name = "Camera"
    camera_entity.online = True
    camera_entity.data["cameraWebrtcTicket"] = {"id": "ticket-id"}

    class Coordinator:
        data = {"stations": {camera_entity.entity_id: camera_entity}, "devices": {}}

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    class Session:
        def __init__(self):
            self.closed = False

        async def close(self):
            self.closed = True

    tasks = []

    class FakeHass:
        data = {}

        def async_create_task(self, coro):
            task = asyncio.create_task(coro)
            tasks.append(task)
            return task

    camera = XSenseWebRTCCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)
    camera.hass = FakeHass()
    old_session = Session()
    active_session = Session()
    camera._webrtc_sessions["old-session"] = old_session
    camera._webrtc_sessions["active-session"] = active_session

    camera.close_webrtc_session("old-session")
    await tasks[0]

    assert old_session.closed is True
    assert active_session.closed is False
    assert camera_entity.data["cameraWebrtcTicket"] == {"id": "ticket-id"}
    assert list(camera._webrtc_sessions) == ["active-session"]


def test_camera_online_uses_parsed_entity_online_state_like_apk():
    from custom_components.xsense import camera

    camera_entity = entity("SSC0A", {"streamProtocol": "webrtc"})
    camera_entity.online = True
    assert camera._camera_online(camera_entity) is True

    camera_entity.online = False
    camera_entity.data["online"] = 1
    assert camera._camera_online(camera_entity) is False


def test_stale_camera_metadata_fields_are_kept_out_of_entity_registry():
    forbidden = {
        "camera_model",
        "camera_device_status",
        "camera_sleep_message",
        "camera_wake_time",
        "camera_stream_protocol",
        "camera_codec",
        "camera_time_zone",
        "camera_awake",
        "camera_webrtc_supported",
    }
    exposed = {description.key for description in sensor.SENSORS} | {
        description.key for description in binary_sensor.SENSORS
    }

    assert forbidden.isdisjoint(exposed)
