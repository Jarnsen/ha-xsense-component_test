import asyncio
import importlib
import sys
import time
from types import SimpleNamespace

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
from custom_components.xsense.api import mapping
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
    from custom_components.xsense.api.entity_map import EntityType
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


async def test_default_stream_source_mode_skips_webrtc_provider_probe():
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
        raise AssertionError("Default mode should not probe WebRTC providers")

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


def test_webrtc_client_config_uses_cached_ticket_ice_servers():
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
                "expirationTime": int(time.time() * 1000) + 300000,
                "iceServer": [
                    {
                        "url": "turn:turn.example.com:3478",
                        "username": "user",
                        "credential": "secret",
                    }
                ],
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

    camera = XSenseWebRTCCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)

    config = camera._async_get_webrtc_client_configuration().to_frontend_dict()

    assert config["dataChannel"] == "data-channel-of-"
    assert config["configuration"]["iceServers"] == [
        {
            "urls": "turn:turn.example.com:3478",
            "username": "user",
            "credential": "secret",
        }
    ]


def test_webrtc_client_config_ignores_expired_ticket_ice_servers():
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
                "expirationTime": int(time.time() * 1000) - 1000,
                "iceServer": [{"url": "turn:expired.example.com"}],
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
    from custom_components.xsense.api.async_xsense import camera_live_resolution

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


async def test_default_camera_does_not_pass_webrtc_url_to_stream_worker():
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

    assert await camera.stream_source() is None
    assert calls == ["start", "stop"]


async def test_default_camera_returns_none_when_stream_endpoint_no_response():
    from custom_components.xsense.api.exceptions import APIFailure
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

    assert await camera.stream_source() is None


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
