import asyncio
import importlib
import logging
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

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
from xsense import mapping
from homeassistant.const import Platform


def entity(device_type, data):
    return SimpleNamespace(type=device_type, data=data)


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


def test_is_life_end_uses_explicit_boolean_parser():
    description = next(
        item for item in binary_sensor.SENSORS if item.key == "is_life_end"
    )

    assert description.value_fn(entity("XS01-WX", {"isLifeEnd": "1"})) is True
    assert description.value_fn(entity("XS01-WX", {"isLifeEnd": "0"})) is False
    assert description.value_fn(entity("XS01-WX", {"isLifeEnd": "unknown"})) is None


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


def test_camera_diagnostic_sensors_expose_apk_metadata():
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

    for key in {
        "camera_activated_time",
        "camera_status_code",
        "camera_dormancy_message",
        "camera_dormancy_wake_time",
        "camera_firmware_status",
        "camera_firmware_version",
        "camera_network_name",
        "camera_offline_time",
        "camera_sd_card_status",
        "camera_sd_card_total",
        "camera_sd_card_used",
        "camera_thumbnail_time",
        "camera_time_zone_area",
        "camera_wifi_channel",
        "camera_wired_mac_address",
    }:
        assert descriptions[key].exists_fn(camera)


def test_read_only_camera_entities_require_camera_entity():
    non_camera = entity("XS01-WX", {"batteryLevel": 2, "needMotion": 1})
    camera = entity("SSC0A", {"batteryLevel": 2, "needMotion": 1})

    assert not sensor.has_camera_data("batteryLevel")(non_camera)
    assert sensor.has_camera_data("batteryLevel")(camera)


def test_regular_motion_binary_entity_is_not_created_for_cameras():
    non_camera = entity("XS01-WX", {"needMotion": 1})
    camera = entity("SSC0A", {"needMotion": 1})

    motion = next(item for item in binary_sensor.SENSORS if item.key == "moved")

    assert not motion.exists_fn(non_camera)
    assert not motion.exists_fn(camera)


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
    station_camera = entity("SSC0A", {"streamProtocol": "webrtc"})
    station_camera.entity_id = "station-camera-id"
    station_camera.sn = "cam-sn"
    station_camera.name = "Station Camera"
    station_camera.online = True

    device_camera = entity("SSC0A", {"streamProtocol": "webrtc"})
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
    assert event.motion_fingerprint(event_data) == ("20260621134144", None)


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
    assert event.motion_fingerprint(event_data) == ("20260621134144", "trace-id")


def test_motion_event_entity_adds_ha_sd_playback_url(monkeypatch):
    camera_entity = entity("SSC0A", {})
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
    assert event_data["camera_serial"] == "CAMERA-SN"
    assert event_data["camera_entity_id"] == "camera.garden"
    assert event_data["recording_url"] == (
        "/xsense-recordings#entry_id=entry-id&serial=CAMERA-SN"
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
        "/xsense-recordings#entry_id=entry-id&serial=CAMERA-SN"
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
        "/xsense-recordings#entry_id=entry-id&serial=CAMERA-SN"
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
        "/xsense-recordings#entry_id=entry-id&serial=CAMERA-SN"
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
        "/xsense-recordings#entry_id=entry-id&serial=CAMERA-SN"
        "&start=1782049304&end=1782049304"
    )


def test_motion_event_entity_caches_recording_before_trigger(monkeypatch, caplog):
    from custom_components.xsense import media_source

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
    event_entity._last_motion_fingerprint = ("20260621134000", "old-trace")
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
            "/xsense-recordings#entry_id=entry-id&serial=CAMERA-SN"
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


def test_motion_event_entity_updates_state_only_when_recording_cache_returns_no_media(
    monkeypatch,
    caplog,
):
    from custom_components.xsense import media_source

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
    event_entity._last_motion_fingerprint = ("20260621134000", "old-trace")
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
        "custom_components.xsense.media_source.async_cache_recording_playback",
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
        "custom_components.xsense.media_source.async_cache_recording_playback",
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


def test_playback_page_uses_ha_webrtc_answer_and_sd_command():
    from custom_components.xsense import playback

    html = playback._playback_html(
        "camera.garden",
        '{"action":"startPlaySdVideo"}',
        '{"action":"stopPlaySdVideo"}',
    )

    assert 'type: "camera/webrtc/offer"' in html
    assert 'type: "camera/webrtc/candidate", entity_id: cameraEntityId' in html
    assert "payload.answer" in html
    assert "payload.sdp" not in html
    assert "pendingCandidates" in html
    assert "startPlaySdVideo" in html
    assert "stopPlaySdVideo" in html


def test_playback_url_uses_recordings_sidebar_panel():
    from custom_components.xsense import playback

    url = playback.playback_url(
        "entry-id",
        "CAMERA/SN",
        1782049304,
        "camera.garden",
        end_time=1782049334,
    )

    assert url == (
        "/xsense-recordings#entry_id=entry-id&serial=CAMERA%2FSN"
        "&start=1782049304&end=1782049334"
    )


def test_recording_media_url_uses_backend_recording_route():
    from custom_components.xsense import playback

    url = playback.recording_media_url(
        "entry-id",
        "CAMERA/SN",
        1782049304,
        end_time=1782049334,
    )

    assert url == (
        "/xsense/recording/entry-id/1782049304"
        "?serial=CAMERA%2FSN&end_time=1782049334"
    )


def test_frontend_playback_panel_has_recording_mode():
    from pathlib import Path

    panel = Path(
        "custom_components/xsense/frontend/xsense-playback-panel.js"
    ).read_text(encoding="utf-8")

    assert 'params.get("mode") || "webrtc"' in panel
    assert 'mode === "recording"' in panel
    assert "renderRecordingPlayer" in panel
    assert "<video" in panel
    assert "/xsense/recording/" in panel


def test_recording_media_view_redirects_cached_clip(monkeypatch, tmp_path):
    from custom_components.xsense import playback

    camera_entity = entity("SSC0A", {})
    camera_entity.sn = "CAMERA-SN"
    output_path = tmp_path / "clip.mp4"
    output_path.write_bytes(b"\x00\x00\x00\x10ftypmp42\x00\x00\x00\x00cached")
    captures = []
    coordinator = SimpleNamespace(
        xsense=object(),
        data={"devices": {"camera": camera_entity}, "stations": {}},
    )
    hass = SimpleNamespace(data={playback.DOMAIN: {"entry-id": coordinator}})
    request = SimpleNamespace(
        app={"hass": hass},
        query={"serial": "CAMERA-SN", "end_time": "1782049334"},
    )

    async def fake_capture(*args, **kwargs):
        captures.append((args, kwargs))

    monkeypatch.setattr(
        playback,
        "_recording_cache_path",
        lambda *args: output_path,
    )
    monkeypatch.setattr(
        playback,
        "_local_media_url",
        lambda path: "/media/local/xsense_recordings/videos/clip.mp4",
    )
    monkeypatch.setattr(playback, "async_capture_sd_recording", fake_capture)

    with pytest.raises(playback.web.HTTPFound) as err:
        asyncio.run(
            playback.XSenseRecordingMediaView().get(
                request,
                "entry-id",
                "1782049304",
            )
        )

    assert err.value.location == "/media/local/xsense_recordings/videos/clip.mp4"
    assert captures == []


def test_recording_media_view_captures_missing_clip_before_redirect(
    monkeypatch, tmp_path
):
    from custom_components.xsense import playback

    camera_entity = entity("SSC0A", {})
    camera_entity.sn = "CAMERA-SN"
    output_path = tmp_path / "clip.mp4"
    captures = []
    coordinator = SimpleNamespace(
        xsense=object(),
        data={"devices": {"camera": camera_entity}, "stations": {}},
    )
    hass = SimpleNamespace(data={playback.DOMAIN: {"entry-id": coordinator}})
    request = SimpleNamespace(
        app={"hass": hass},
        query={"serial": "CAMERA-SN", "end_time": "1782049334"},
    )

    async def fake_capture(hass, **kwargs):
        captures.append({"hass": hass, **kwargs})
        kwargs["output_path"].write_bytes(
            b"\x00\x00\x00\x10ftypmp42\x00\x00\x00\x00captured"
        )

    monkeypatch.setattr(
        playback,
        "_recording_cache_path",
        lambda *args: output_path,
    )
    monkeypatch.setattr(
        playback,
        "_local_media_url",
        lambda path: "/media/local/xsense_recordings/videos/clip.mp4",
    )
    monkeypatch.setattr(playback, "async_capture_sd_recording", fake_capture)

    with pytest.raises(playback.web.HTTPFound) as err:
        asyncio.run(
            playback.XSenseRecordingMediaView().get(
                request,
                "entry-id",
                "1782049304",
            )
        )

    assert err.value.location == "/media/local/xsense_recordings/videos/clip.mp4"
    assert captures == [
        {
            "hass": hass,
            "coordinator": coordinator,
            "camera": camera_entity,
            "start_time": 1782049304,
            "output_path": output_path,
            "duration_seconds": 30,
        }
    ]


def test_pion_capture_skips_ready_output(monkeypatch, tmp_path):
    from custom_components.xsense import pion_adapter

    output_path = tmp_path / "ready.mp4"
    output_path.write_bytes(b"\x00\x00\x00\x10ftypmp42\x00\x00\x00\x00ready")
    captures = []
    hass = SimpleNamespace(data={pion_adapter.DOMAIN: {}})

    async def fake_capture(*args, **kwargs):
        captures.append((args, kwargs))

    monkeypatch.setattr(
        pion_adapter,
        "_async_capture_sd_recording_unlocked",
        fake_capture,
    )

    result = asyncio.run(
        pion_adapter.async_capture_sd_recording(
            hass,
            coordinator=object(),
            camera=object(),
            start_time=1782049304,
            output_path=output_path,
        )
    )

    assert result == output_path
    assert captures == []


def test_pion_capture_passes_duration_timeout_to_helper_wait(monkeypatch, tmp_path):
    from custom_components.xsense import pion_adapter

    output_path = tmp_path / "clip.mp4"
    h264_path = output_path.with_name(f"{output_path.name}.h264")
    temp_output_path = output_path.with_suffix(".tmp.mp4")
    wait_calls = []

    class Stdin:
        def is_closing(self):
            return False

        def write(self, value):
            self.value = value

        async def drain(self):
            pass

    class Proc:
        returncode = 0
        stdin = Stdin()

        async def wait(self):
            return 0

    class SignalSession:
        def __init__(self, **kwargs):
            pass

        async def start(self):
            return "v=0"

        def start_forwarding_remote_candidates(self):
            pass

        async def close(self):
            pass

    async def start_helper(helper_path, raw_path, start_time, ticket, timeout):
        wait_calls.append(("start", timeout))
        raw_path.write_bytes(b"raw h264")
        return Proc()

    async def wait_for_helper(proc, timeout):
        wait_calls.append(("wait", timeout))
        return {"packets": 1, "bytes": 10, "h264Samples": 1, "h264Bytes": 10}

    async def remux(ffmpeg_binary, raw_path, final_path):
        assert final_path == temp_output_path
        final_path.write_bytes(
            b"\x00\x00\x00\x10ftypmp42\x00\x00\x00\x00final-video"
        )

    ticket_factory = SimpleNamespace(
        from_api=lambda serial, data: SimpleNamespace(ice_servers=[])
    )
    monkeypatch.setattr(pion_adapter, "_pion_helper_path", lambda: tmp_path / "helper")
    monkeypatch.setattr(pion_adapter, "_ffmpeg_binary", lambda hass: "ffmpeg")
    monkeypatch.setattr(pion_adapter, "_start_helper", start_helper)
    monkeypatch.setattr(pion_adapter, "_read_helper_offer", AsyncMock(return_value="v=0"))
    monkeypatch.setattr(pion_adapter, "_wait_for_helper", wait_for_helper)
    monkeypatch.setattr(pion_adapter, "_remux_h264_to_mp4", remux)
    monkeypatch.setattr(pion_adapter, "async_get_clientsession", lambda hass: object())
    monkeypatch.setattr(pion_adapter, "XSenseWebRTCTicket", ticket_factory)
    monkeypatch.setattr(pion_adapter, "XSenseWebRTCSignalSession", SignalSession)

    hass = SimpleNamespace(
        data={pion_adapter.DOMAIN: {}},
        async_create_task=lambda coro: asyncio.create_task(coro),
    )
    coordinator = SimpleNamespace(
        xsense=SimpleNamespace(
            get_camera_webrtc_ticket=AsyncMock(return_value={"ticket": "data"})
        )
    )
    camera_entity = SimpleNamespace(sn="CAMERA-SN", online=True, data={})

    result = asyncio.run(
        pion_adapter.async_capture_sd_recording(
            hass,
            coordinator=coordinator,
            camera=camera_entity,
            start_time=1782049304,
            output_path=output_path,
            duration_seconds=60,
        )
    )

    assert result == output_path
    assert output_path.exists()
    assert not h264_path.exists()
    assert not temp_output_path.exists()
    assert wait_calls == [("start", 70), ("wait", 70)]


def test_pion_capture_does_not_promote_invalid_remux_output(monkeypatch, tmp_path):
    from custom_components.xsense import pion_adapter

    output_path = tmp_path / "clip.mp4"

    class Stdin:
        def is_closing(self):
            return False

        def write(self, value):
            self.value = value

        async def drain(self):
            pass

    class Proc:
        returncode = 0
        stdin = Stdin()

        async def wait(self):
            return 0

    class SignalSession:
        def __init__(self, **kwargs):
            pass

        async def start(self):
            return "v=0"

        def start_forwarding_remote_candidates(self):
            pass

        async def close(self):
            pass

    async def start_helper(helper_path, raw_path, start_time, ticket, timeout):
        raw_path.write_bytes(b"raw h264")
        return Proc()

    async def remux(ffmpeg_binary, raw_path, final_path):
        final_path.write_bytes(b"not an mp4")

    ticket_factory = SimpleNamespace(
        from_api=lambda serial, data: SimpleNamespace(ice_servers=[])
    )
    monkeypatch.setattr(pion_adapter, "_pion_helper_path", lambda: tmp_path / "helper")
    monkeypatch.setattr(pion_adapter, "_ffmpeg_binary", lambda hass: "ffmpeg")
    monkeypatch.setattr(pion_adapter, "_start_helper", start_helper)
    monkeypatch.setattr(pion_adapter, "_read_helper_offer", AsyncMock(return_value="v=0"))
    monkeypatch.setattr(
        pion_adapter,
        "_wait_for_helper",
        AsyncMock(return_value={"packets": 1, "bytes": 10, "h264Samples": 1}),
    )
    monkeypatch.setattr(pion_adapter, "_remux_h264_to_mp4", remux)
    monkeypatch.setattr(pion_adapter, "async_get_clientsession", lambda hass: object())
    monkeypatch.setattr(pion_adapter, "XSenseWebRTCTicket", ticket_factory)
    monkeypatch.setattr(pion_adapter, "XSenseWebRTCSignalSession", SignalSession)

    hass = SimpleNamespace(
        data={pion_adapter.DOMAIN: {}},
        async_create_task=lambda coro: asyncio.create_task(coro),
    )
    coordinator = SimpleNamespace(
        xsense=SimpleNamespace(
            get_camera_webrtc_ticket=AsyncMock(return_value={"ticket": "data"})
        )
    )
    camera_entity = SimpleNamespace(sn="CAMERA-SN", online=True, data={})

    with pytest.raises(RuntimeError, match="did not create a playable MP4"):
        asyncio.run(
            pion_adapter.async_capture_sd_recording(
                hass,
                coordinator=coordinator,
                camera=camera_entity,
                start_time=1782049304,
                output_path=output_path,
                duration_seconds=60,
            )
        )

    assert not output_path.exists()
    assert not output_path.with_suffix(".tmp.mp4").exists()
    assert not output_path.with_name(f"{output_path.name}.h264").exists()


def test_pion_ice_servers_env_normalizes_xsense_ticket_shape():
    from custom_components.xsense import pion_adapter

    ticket = SimpleNamespace(
        ice_servers=[
            {"url": "turn:one.example", "username": "user", "password": "pass"},
            {"urls": ["stun:two.example", "turn:two.example"], "credential": "cred"},
            {"unexpected": "ignored"},
        ]
    )

    assert pion_adapter.json.loads(pion_adapter._ice_servers_env(ticket)) == [
        {
            "urls": "turn:one.example",
            "username": "user",
            "credential": "pass",
        },
        {
            "urls": ["stun:two.example", "turn:two.example"],
            "credential": "cred",
        },
    ]


def test_pion_capture_timeout_uses_clip_duration():
    from custom_components.xsense import pion_adapter

    assert pion_adapter._capture_timeout(None) == pion_adapter.HELPER_TIMEOUT
    assert pion_adapter._capture_timeout(5) == pion_adapter.HELPER_TIMEOUT
    assert pion_adapter._capture_timeout(60) == 70
    assert pion_adapter._capture_timeout(600) == 180


def test_pion_start_helper_passes_ice_servers(monkeypatch, tmp_path):
    from custom_components.xsense import pion_adapter

    captured = {}

    async def fake_create_subprocess_exec(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return object()

    monkeypatch.setattr(
        pion_adapter.asyncio,
        "create_subprocess_exec",
        fake_create_subprocess_exec,
    )
    ticket = SimpleNamespace(ice_servers=[{"url": "turn:example"}])

    result = asyncio.run(
        pion_adapter._start_helper(
            tmp_path / "helper",
            tmp_path / "clip.h264",
            1782049304,
            ticket,
            70,
        )
    )

    assert result is not None
    assert "--timeout" in captured["args"]
    assert captured["args"][captured["args"].index("--timeout") + 1] == "70s"
    env = captured["kwargs"]["env"]
    assert env["XSENSE_RECORDINGS_ICE_SERVERS"] == (
        '[{"urls":"turn:example"}]'
    )
    assert env["XSENSE_RECORDINGS_DATA_CHANNEL"] == "1"
    assert env["XSENSE_RECORDINGS_DATA_CHANNEL_LABEL"] == "data-channel-of-"
    assert env["XSENSE_RECORDINGS_CHROME_SDP"] == "1"
    assert env["XSENSE_RECORDINGS_REMOTE_SDP_TYPE"] == "answer"
    assert env["XSENSE_RECORDINGS_H264_OUTPUT"] == str(tmp_path / "clip.h264")
    assert '"action":"startPlaySdVideo"' in env[
        "XSENSE_RECORDINGS_DATA_CHANNEL_START_PAYLOAD"
    ]


def test_recording_media_source_builds_sd_playback_clip_url():
    from custom_components.xsense import media_source

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

    assert clip == {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "camera_entity_id": "camera.garden",
        "start": 1782049304,
        "end": 1782049334,
        "date": "2026-06-21",
        "title": "13:41:44 - 13:42:14",
        "source": "sd_playback",
        "requested_source": "sd_playback",
        "quality": "HD",
        "playback_url": (
            "/xsense/recording/entry-id/1782049304"
            "?serial=CAMERA-SN&end_time=1782049334"
        ),
        "thumbnail_url": "https://example.invalid/snap.jpg",
        "cached_thumbnail_url": (
            "/media/local/xsense_recordings/thumbs/"
            "CAMERA-SN_1782049304_1782049334.jpg"
        ),
        "cached_url": "",
        "media_root": "/media/xsense_recordings",
    }


def test_recording_clip_from_playback_accepts_raw_apk_time_fields():
    from custom_components.xsense import media_source

    clip = media_source._recording_clip_from_playback(
        "entry-id",
        "CAMERA-SN",
        "camera.garden",
        {
            "source": "sd_playback",
            "start_time": 1782049304,
            "period": 30,
        },
    )

    assert clip["start"] == 1782049304
    assert clip["end"] == 1782049334
    assert clip["playback_url"] == (
        "/xsense/recording/entry-id/1782049304"
        "?serial=CAMERA-SN&end_time=1782049334"
    )
    assert clip["cached_url"] == ""


def test_recording_clip_from_playback_normalizes_ms_time_fields():
    from custom_components.xsense import media_source

    clip = media_source._recording_clip_from_playback(
        "entry-id",
        "CAMERA-SN",
        "camera.garden",
        {
            "source": "sd_playback",
            "start_time": 1782049304000,
            "end_time": 1782049334000,
        },
    )

    assert clip["start"] == 1782049304
    assert clip["end"] == 1782049334
    assert clip["playback_url"] == (
        "/xsense/recording/entry-id/1782049304"
        "?serial=CAMERA-SN&end_time=1782049334"
    )


def test_recording_media_source_preserves_direct_video_url():
    from custom_components.xsense import media_source

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


def test_recording_media_source_prefers_hd_direct_video_candidate():
    from custom_components.xsense import media_source

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


def test_recording_media_source_uses_sd_capture_when_requested():
    from custom_components.xsense import media_source

    clip = media_source._recording_clip_from_playback(
        "entry-id",
        "CAMERA-SN",
        "camera.garden",
        {
            "source": "video_url",
            "start_time_s": 1782049304,
            "end_time_s": 1782049334,
            "video_url": "https://example.invalid/hd.mp4",
        },
        quality="SD",
    )

    assert clip["quality"] == "SD"
    assert clip["source"] == "sd_playback"
    assert clip["requested_source"] == "video_url"
    assert clip["playback_url"] == (
        "/xsense/recording/entry-id/1782049304"
        "?serial=CAMERA-SN&end_time=1782049334"
    )


def test_recording_media_source_marks_sd_playback_as_playable():
    from custom_components.xsense import media_source

    assert media_source._clip_media_playable(
        {"source": "video_url", "playback_url": "https://example.invalid/clip.mp4"}
    )
    assert media_source._clip_media_playable(
        {"source": "sd_playback", "playback_url": "/xsense/recording/entry/sn/1"}
    )


def test_recording_media_source_clip_duration_uses_normalized_bounds():
    from custom_components.xsense import media_source

    assert media_source._clip_duration({"start": 100, "end": 130}) == 30
    assert media_source._clip_duration({"start": 100, "end": 100}) is None
    assert media_source._clip_duration({"start": 100, "end": "bad"}) is None


def test_cache_recording_playback_returns_cached_media_url(monkeypatch, tmp_path):
    from custom_components.xsense import media_source

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

    assert result == (
        "/media/local/xsense_custom/videos/CAMERA-SN_1782049304_1782049334.mp4"
    )


def test_cache_recording_playback_does_not_trust_unvalidated_cache_url(
    monkeypatch,
    tmp_path,
):
    from custom_components.xsense import media_source

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
    from custom_components.xsense import media_source

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
    from custom_components.xsense import media_source

    source = media_source.XSenseRecordingsMediaSource(SimpleNamespace())
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


def test_recording_media_source_does_not_fall_back_to_external_video_url(
    monkeypatch,
    tmp_path,
):
    from custom_components.xsense import media_source

    source = media_source.XSenseRecordingsMediaSource(SimpleNamespace())
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
    from custom_components.xsense import media_source

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


def test_recording_media_source_falls_back_to_sd_when_direct_download_not_mp4(
    monkeypatch,
    tmp_path,
):
    from custom_components.xsense import media_source

    source = media_source.XSenseRecordingsMediaSource(SimpleNamespace())
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
    seen = {}

    async def cached_sd_playback_url(current_clip):
        seen.update(current_clip)
        assert not output_path.exists()
        output_path.write_bytes(
            b"\x00\x00\x00\x10ftypmp42\x00\x00\x00\x00fallback"
        )
        return "/media/local/xsense_recordings/videos/fallback.mp4"

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
    monkeypatch.setattr(source, "_async_cached_sd_playback_url", cached_sd_playback_url)

    result = asyncio.run(source._async_cached_playback_url(clip))

    assert result == "/media/local/xsense_recordings/videos/fallback.mp4"
    assert seen["source"] == "sd_playback"
    assert seen["quality"] == "HD"
    assert media_source._mp4_ready(output_path)


def test_recording_media_source_caches_hd_hls_without_sd_fallback(
    monkeypatch,
    tmp_path,
):
    from custom_components.xsense import media_source

    source = media_source.XSenseRecordingsMediaSource(SimpleNamespace())
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

    async def cached_sd_playback_url(current_clip):
        raise AssertionError("HD HLS should not use SD capture fallback")

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
    monkeypatch.setattr(source, "_async_cached_sd_playback_url", cached_sd_playback_url)

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
    assert not (playlist.parent / "segment_0004.ts").exists()


def test_recording_media_source_hls_master_ready_with_one_buffered_variant(
    monkeypatch,
    tmp_path,
):
    from custom_components.xsense import media_source

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
    monkeypatch.setattr(
        media_source,
        "_hls_playlist_cache_path",
        lambda current_clip: root / "index.m3u8",
    )

    assert media_source._hls_ready(clip)


def test_recording_media_source_lazy_shows_uncached_clips_when_sync_disabled(
    monkeypatch,
    tmp_path,
):
    from custom_components.xsense import media_source

    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "date": "2026-06-25",
        "start": 1782049304,
        "end": 1782049334,
        "playback_url": "/xsense/recording/entry-id/1782049304?serial=CAMERA-SN",
        "media_root": tmp_path.as_posix(),
    }
    source = media_source.XSenseRecordingsMediaSource(
        SimpleNamespace(
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
    from custom_components.xsense import media_source
    from custom_components.xsense.const import CONF_RECORDING_MEDIA_SYNC_ENABLED

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
        SimpleNamespace(
            config_entries=SimpleNamespace(
                async_get_entry=lambda entry_id: SimpleNamespace(
                    data={},
                    options={CONF_RECORDING_MEDIA_SYNC_ENABLED: True}
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
    from custom_components.xsense import media_source
    from custom_components.xsense.const import CONF_RECORDING_MEDIA_SYNC_ENABLED

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
        SimpleNamespace(
            config_entries=SimpleNamespace(
                async_get_entry=lambda entry_id: SimpleNamespace(
                    data={},
                    options={CONF_RECORDING_MEDIA_SYNC_ENABLED: True},
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

    from custom_components.xsense import media_source
    from custom_components.xsense.const import CONF_RECORDING_MEDIA_SYNC_ENABLED

    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "start": 1782049304,
        "end": 1782049334,
        "playback_url": "/xsense/recording/entry-id/1782049304?serial=CAMERA-SN",
        "media_root": tmp_path.as_posix(),
    }
    source = media_source.XSenseRecordingsMediaSource(
        SimpleNamespace(
            config_entries=SimpleNamespace(
                async_get_entry=lambda entry_id: SimpleNamespace(
                    data={},
                    options={CONF_RECORDING_MEDIA_SYNC_ENABLED: True}
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
    from custom_components.xsense import media_source

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
    from custom_components.xsense import media_source, playback

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
        options={playback.CONF_RECORDING_MEDIA_STORAGE_PATH: "/mediaevil"},
    )
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_get_entry=lambda entry_id: entry)
    )

    assert playback._recording_media_root(hass, "entry-id").as_posix() == (
        "/media/xsense_recordings"
    )


def test_refresh_recording_indexes_filters_config_entry(monkeypatch):
    from custom_components.xsense import media_source

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
    from custom_components.xsense import media_source

    hass = SimpleNamespace(
        data={media_source.DOMAIN: {"_recording_indexes": {"entry-id": object()}}}
    )

    media_source.async_remove_recording_index(hass, "entry-id")

    assert "_recording_indexes" not in hass.data[media_source.DOMAIN]


def test_cache_recording_media_counts_direct_and_sd_playback(monkeypatch):
    from custom_components.xsense import media_source

    async def refresh_indexes(hass, *, entry_id=None, force_refresh=False):
        return [
            {
                "cameras": [
                    {
                        "clips": [
                            {
                                "source": "video_url",
                                "playback_url": "https://example.invalid/clip.mp4",
                                "thumbnail_url": "https://example.invalid/thumb.jpg",
                                "serial": "CAMERA-SN",
                                "start": 1,
                                "end": 2,
                            },
                            {
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
    hass = SimpleNamespace(data={media_source.DOMAIN: {}})

    summary = asyncio.run(media_source.async_cache_recording_media(hass))

    assert summary == {"downloaded": 2, "thumbnails": 1, "skipped": 0, "failed": 0}
    assert cached == [3, 1]
    assert thumbs == [1]


def test_cache_recording_media_prefers_newest_clips(monkeypatch):
    from custom_components.xsense import media_source

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

    assert cached == [300, 200, 100]


def test_cache_recent_recording_media_force_refreshes_and_skips_old_clips(monkeypatch):
    from custom_components.xsense import media_source

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
    assert cached == [now - 60]
    assert summary == {"downloaded": 1, "thumbnails": 0, "skipped": 1, "failed": 0}


def test_event_recording_clip_merges_into_recording_index():
    from custom_components.xsense import media_source

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
    from custom_components.xsense import media_source

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
    from custom_components.xsense import media_source

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
    from custom_components.xsense import media_source

    scheduled = []
    cached = []

    class Hass:
        def async_create_task(self, coro):
            scheduled.append(coro)

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
    source = media_source.XSenseRecordingsMediaSource(Hass())
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
    from custom_components.xsense import media_source

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
    monkeypatch.setattr(
        media_source,
        "_clear_media_cache",
        lambda roots: cleared_media.append(roots),
    )

    asyncio.run(media_source.async_clear_recording_caches(hass))

    assert manager.removed
    assert "_recording_indexes" not in hass.data[media_source.DOMAIN]
    assert len(cleared_media) == 1
    assert [path.as_posix() for path in cleared_media[0]] == ["/media/xsense_recordings"]


def test_clear_recording_caches_scopes_media_to_entry(monkeypatch):
    from custom_components.xsense import media_source
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
    monkeypatch.setattr(
        media_source,
        "_clear_media_cache",
        lambda roots: cleared_media.append(roots),
    )

    asyncio.run(media_source.async_clear_recording_caches(hass, entry_id="entry-id"))

    assert len(cleared_media) == 1
    assert [path.as_posix() for path in cleared_media[0]] == ["/media/xsense_custom"]


def test_clear_recording_caches_removes_scoped_capture_locks(monkeypatch):
    from custom_components.xsense import media_source
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
    monkeypatch.setattr(media_source, "_clear_media_cache", lambda roots: None)

    asyncio.run(media_source.async_clear_recording_caches(hass, entry_id="entry-id"))

    assert hass.data[media_source.DOMAIN]["_recording_capture_locks"] == {
        "/media/xsense_other/videos/camera_1_2.mp4": locks[
            "/media/xsense_other/videos/camera_1_2.mp4"
        ]
    }


def test_clear_media_cache_removes_recording_outputs(tmp_path):
    from custom_components.xsense import media_source

    videos = tmp_path / "videos"
    thumbs = tmp_path / "thumbs"
    videos.mkdir()
    thumbs.mkdir()
    removable = [
        videos / "clip.mp4",
        videos / "clip.mp4.h264",
        thumbs / "clip.jpg",
    ]
    keep = videos / "notes.txt"
    for path in [*removable, keep]:
        path.write_text("cached")

    media_source._clear_media_cache([tmp_path])

    assert [path.exists() for path in removable] == [False, False, False]
    assert keep.exists()


def test_recording_media_sync_starts_only_when_enabled(monkeypatch):
    from custom_components.xsense import media_source
    from custom_components.xsense.const import (
        CONF_RECORDING_MEDIA_SYNC_ENABLED,
        CONF_RECORDING_MEDIA_SYNC_HOURS,
    )

    calls = []

    def async_call_later(hass, delay, action):
        calls.append(("later", delay, action))
        return "unsub-later"

    def async_track_time_interval(hass, action, interval):
        calls.append(("interval", interval, action))
        return "unsub-interval"

    monkeypatch.setattr(media_source, "async_call_later", async_call_later)
    monkeypatch.setattr(media_source, "async_track_time_interval", async_track_time_interval)

    unloads = []
    hass = SimpleNamespace()
    disabled_entry = SimpleNamespace(
        entry_id="entry-disabled",
        options={},
        async_on_unload=unloads.append,
    )
    media_source.async_start_recording_media_sync(hass, disabled_entry)
    assert calls == []
    assert unloads == []

    enabled_entry = SimpleNamespace(
        entry_id="entry-enabled",
        options={
            CONF_RECORDING_MEDIA_SYNC_ENABLED: True,
            CONF_RECORDING_MEDIA_SYNC_HOURS: 6,
        },
        async_on_unload=unloads.append,
    )
    media_source.async_start_recording_media_sync(hass, enabled_entry)

    assert calls[0][0:2] == ("later", 30)
    assert calls[1][0] == "interval"
    assert calls[1][1].total_seconds() == 21600
    assert calls[2][0] == "interval"
    assert calls[2][1].total_seconds() == 120
    assert unloads == ["unsub-later", "unsub-interval", "unsub-interval"]


def test_register_playback_routes_adds_hidden_frontend_panel(monkeypatch):
    from custom_components.xsense import playback

    static_paths = []
    registered_views = []
    panels = []

    class Http:
        async def async_register_static_paths(self, configs):
            static_paths.extend(configs)

        def register_view(self, view):
            registered_views.append(view)

    hass = SimpleNamespace(data={}, http=Http())
    monkeypatch.setattr(
        playback.frontend,
        "async_register_built_in_panel",
        lambda *args, **kwargs: panels.append((args, kwargs)),
    )

    asyncio.run(playback.async_register_playback_view(hass))
    asyncio.run(playback.async_register_playback_view(hass))

    assert len(static_paths) == 1
    assert static_paths[0].url_path == "/xsense_static"
    assert len(registered_views) == 2
    assert isinstance(registered_views[0], playback.XSensePlaybackView)
    assert isinstance(registered_views[1], playback.XSenseRecordingMediaView)
    assert len(panels) == 1
    panel_args, panel_kwargs = panels[0]
    assert panel_args == (hass,)
    assert panel_kwargs["component_name"] == "custom"
    assert panel_kwargs["frontend_url_path"] == "xsense-playback"
    assert panel_kwargs["show_in_sidebar"] is False
    assert panel_kwargs["config"]["_panel_custom"]["name"] == "xsense-playback-panel"
    assert panel_kwargs["config"]["_panel_custom"]["module_url"] == (
        "/xsense_static/xsense-playback-panel.js"
    )


def test_register_playback_routes_adds_recording_view_after_legacy_upgrade(
    monkeypatch,
):
    from custom_components.xsense import playback

    registered_views = []

    class Http:
        async def async_register_static_paths(self, configs):
            raise AssertionError("static path should already be registered")

        def register_view(self, view):
            registered_views.append(view)

    hass = SimpleNamespace(
        data={
            playback.DOMAIN: {
                "_playback_static_registered": True,
                "_playback_panel_registered": True,
                "_playback_view_registered": True,
            }
        },
        http=Http(),
    )
    monkeypatch.setattr(
        playback.frontend,
        "async_register_built_in_panel",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("panel should already be registered")
        ),
    )

    asyncio.run(playback.async_register_playback_view(hass))

    assert len(registered_views) == 1
    assert isinstance(registered_views[0], playback.XSenseRecordingMediaView)
    assert hass.data[playback.DOMAIN]["_recording_media_view_registered"] is True


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
    assert event.motion_fingerprint(event_data) == ("20260621134144", "trace-id")


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
    from xsense.entity_map import EntityType
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
        async def start_camera_live(self, entity):
            raise AssertionError("WebRTC path should not start direct stream")

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


def test_camera_capabilities_use_stream_path_only_for_direct_stream_cameras():
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseCameraEntity,
    )

    rtsp_camera_entity = entity("SSC0A", {"streamProtocol": "rtsp"})
    webrtc_camera_entity = entity(
        "SSC0A", {"streamProtocol": "webrtc", "supportWebrtc": True}
    )

    class Coordinator:
        def __init__(self, camera_entity):
            self.data = {
                "stations": {camera_entity.entity_id: camera_entity},
                "devices": {},
            }

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    for camera_entity in (rtsp_camera_entity, webrtc_camera_entity):
        camera_entity.entity_id = f"camera-{camera_entity.data['streamProtocol']}"
        camera_entity.sn = "SSC0ATEST"
        camera_entity.name = "Camera"
        camera_entity.online = True

    rtsp_camera = XSenseCameraEntity(
        Coordinator(rtsp_camera_entity), rtsp_camera_entity, CAMERA_DESCRIPTION
    )
    webrtc_camera = XSenseCameraEntity(
        Coordinator(webrtc_camera_entity), webrtc_camera_entity, CAMERA_DESCRIPTION
    )

    assert {
        stream.value for stream in rtsp_camera.camera_capabilities.frontend_stream_types
    } == {"hls"}
    assert {
        stream.value
        for stream in webrtc_camera.camera_capabilities.frontend_stream_types
    } == set()


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


async def test_default_stream_source_mode_keeps_ha_provider_probe_behavior():
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

    assert await camera._async_get_supported_webrtc_provider(provider_probe) == "provider"


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


def test_webrtc_client_config_uses_data_channel_only():
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


def test_webrtc_client_config_ignores_cached_ticket_ice_servers():
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseWebRTCCameraEntity,
    )

    camera_entity = entity(
        "SSC0A",
        {
            "streamProtocol": "webrtc",
            "supportWebrtc": True,
            "cameraWebrtcTicket": {
                "expirationTime": 9999999999999,
                "iceServer": [{"url": "turn:turn.example.com"}],
            },
        },
    )
    camera_entity.entity_id = "camera-test"
    camera_entity.sn = "SSC0ATEST"
    camera_entity.name = "Camera"
    camera_entity.online = True

    class Coordinator:
        data = {"stations": {camera_entity.entity_id: camera_entity}, "devices": {}}

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    class FakeHass:
        def async_create_task(self, coro):
            coro.close()
            return SimpleNamespace(done=lambda: True)

    camera = XSenseWebRTCCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)
    camera.hass = FakeHass()

    config = camera._async_get_webrtc_client_configuration().to_frontend_dict()

    assert "iceServers" not in config["configuration"]


def test_camera_entity_webrtc_protocol_default_matches_apk():
    from custom_components.xsense import camera

    assert camera._is_webrtc_camera(entity("SSC0A", {}))
    assert camera._is_webrtc_camera(entity("SSC0A", {"streamProtocol": "webrtc"}))
    assert not camera._is_webrtc_camera(entity("SSC0A", {"streamProtocol": "rtsp"}))
    assert not camera._is_webrtc_camera(entity("SSC0A", {"streamProtocol": "RTMP"}))


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
    from xsense.async_xsense import camera_live_resolution

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


async def test_default_camera_uses_ha_supported_apk_live_url_stream_source():
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseCameraEntity,
    )

    camera_entity = entity("SSC0A", {"streamProtocol": "rtsp"})
    camera_entity.entity_id = "camera-test"
    camera_entity.sn = "SSC0ATEST"
    camera_entity.name = "Camera"
    camera_entity.online = True

    class XSense:
        async def start_camera_live(self, entity):
            assert entity is camera_entity
            return "rtsp://example/live"

    class Coordinator:
        def __init__(self):
            self.data = {
                "stations": {camera_entity.entity_id: camera_entity},
                "devices": {},
            }
            self.xsense = XSense()

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    camera = XSenseCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)
    camera.entity_id = "camera.camera_test"

    assert await camera.stream_source() == "rtsp://example/live"


async def test_plain_stream_source_entity_does_not_start_webrtc_camera_live_url():
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseCameraEntity,
    )

    camera_entity = entity("SSC0A", {"streamProtocol": "webrtc", "supportWebrtc": True})
    camera_entity.entity_id = "camera-test"
    camera_entity.sn = "SSC0ATEST"
    camera_entity.name = "Camera"
    camera_entity.online = True
    calls = []

    class XSense:
        async def start_camera_live(self, entity):
            assert entity is camera_entity
            calls.append("start")
            return "rtsp://example/live"

        async def stop_camera_live(self, entity):
            raise AssertionError("RTSP stream source should not be stopped")

    class Coordinator:
        def __init__(self):
            self.data = {
                "stations": {camera_entity.entity_id: camera_entity},
                "devices": {},
            }
            self.xsense = XSense()

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    camera = XSenseCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)
    camera.entity_id = "camera.camera_test"

    assert await camera.stream_source() is None
    assert calls == []


async def test_default_camera_returns_live_url_from_stream_endpoint():
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseCameraEntity,
    )

    camera_entity = entity("SSC0A", {"streamProtocol": "rtsp"})
    camera_entity.entity_id = "camera-test"
    camera_entity.sn = "SSC0ATEST"
    camera_entity.name = "Camera"
    camera_entity.online = True
    calls = []

    class XSense:
        async def start_camera_live(self, entity):
            assert entity is camera_entity
            calls.append("start")
            return "webrtc://3.65.49.157/live/camera_live"

        async def stop_camera_live(self, entity):
            assert entity is camera_entity
            calls.append("stop")

    class Coordinator:
        def __init__(self):
            self.data = {
                "stations": {camera_entity.entity_id: camera_entity},
                "devices": {},
            }
            self.xsense = XSense()

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    camera = XSenseCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)
    camera.entity_id = "camera.camera_test"

    assert await camera.stream_source() == "webrtc://3.65.49.157/live/camera_live"
    assert calls == ["start"]


async def test_default_camera_raises_when_stream_endpoint_no_response():
    from xsense.exceptions import APIFailure
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseCameraEntity,
    )

    camera_entity = entity("SSC0A", {"streamProtocol": "rtsp"})
    camera_entity.entity_id = "camera-test"
    camera_entity.sn = "SSC0ATEST"
    camera_entity.name = "Camera"
    camera_entity.online = True

    class XSense:
        async def start_camera_live(self, entity):
            assert entity is camera_entity
            raise APIFailure(
                "ADDX request for /device/newstartlive failed with error -3021/DEVICE_NO_RESPONSE"
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

    camera = XSenseCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)
    camera.entity_id = "camera.camera_test"

    with pytest.raises(APIFailure):
        await camera.stream_source()


async def test_failed_webrtc_signal_start_is_removed_from_active_sessions(monkeypatch):
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
                get_camera_webrtc_ticket=get_camera_webrtc_ticket
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
        async def async_add_import_executor_job(self, func, module):
            return fake_module

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
    assert not camera.is_streaming
    assert messages[0].code == "xsense_webrtc_start_failed"


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
                get_camera_webrtc_ticket=get_camera_webrtc_ticket
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
        async def async_add_import_executor_job(self, func, module):
            return fake_module

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

    stop_calls = []

    async def stop_camera_live(entity):
        stop_calls.append(entity.sn)

    class Coordinator:
        def __init__(self):
            self.data = {
                "stations": {camera_entity.entity_id: camera_entity},
                "devices": {},
            }
            self.xsense = SimpleNamespace(
                get_camera_webrtc_ticket=get_camera_webrtc_ticket,
                stop_camera_live=stop_camera_live,
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
        async def async_add_import_executor_job(self, func, module):
            return fake_module

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
    assert stop_calls == []
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
