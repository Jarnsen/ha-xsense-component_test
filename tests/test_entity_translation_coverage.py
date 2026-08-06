import json
from pathlib import Path

from homeassistant.helpers.entity import UNDEFINED

from custom_components.xsense import (
    binary_sensor,
    button,
    camera,
    number,
    select,
    sensor,
    switch,
)


ROOT = Path(__file__).parents[1]
STRINGS = ROOT / "custom_components/xsense/strings.json"
INTEGRATION = ROOT / "custom_components/xsense"


ENTITY_DESCRIPTIONS = {
    "binary_sensor": binary_sensor._ALL_SENSORS,
    "button": button.BUTTONS,
    "number": number.NUMBERS,
    "select": select.SELECTS,
    "sensor": sensor._ALL_SENSORS,
    "switch": switch.SWITCHES,
}


DEVICE_CLASS_ONLY_SENSOR_KEYS = {"temperature", "humidity", "battery"}
ACTION_ERROR_FILES = (
    "alarm_control_panel.py",
    "button.py",
    "mqtt.py",
    "number.py",
    "select.py",
    "switch.py",
)
EXPECTED_EXCEPTION_KEYS = {
    "cooldown_state_unknown",
    "entity_unavailable",
    "ids_missing",
    "ids_required",
    "invalid_radon_threshold",
    "invalid_schedule_time_format",
    "light_power_switch_required",
    "minimum_greater_than_maximum",
    "mqtt_error",
    "mqtt_not_connected",
    "mqtt_topic_not_string",
    "range_pair_missing",
    "safe_mode_publish_failed",
    "sbs50_station_required",
    "schedule_time_out_of_range",
    "schedule_weekday_range",
    "schedule_weekday_required",
    "select_not_writable",
    "station_unavailable",
    "subscription_remove_twice",
    "unsupported_option",
}


def _entity_strings() -> dict:
    return json.loads(STRINGS.read_text(encoding="utf-8"))["entity"]


def _strings() -> dict:
    return json.loads(STRINGS.read_text(encoding="utf-8"))


def test_entity_descriptions_have_translation_keys_or_core_device_class_names():
    strings = _entity_strings()

    for domain, descriptions in ENTITY_DESCRIPTIONS.items():
        for description in descriptions:
            if domain == "sensor" and description.key in DEVICE_CLASS_ONLY_SENSOR_KEYS:
                assert description.translation_key is None
                assert description.name in (None, UNDEFINED)
                continue

            assert description.translation_key, (
                f"{domain}.{description.key} should use translation_key"
            )
            assert description.name in (None, UNDEFINED), (
                f"{domain}.{description.key} should not keep hardcoded name"
            )
            assert description.translation_key in strings[domain]


def test_camera_entity_description_uses_device_name_only():
    assert camera.XSenseCameraEntityDescription(key="camera", name=None).name is None


def test_action_exception_translation_keys_are_registered():
    exceptions = _strings()["exceptions"]

    assert set(exceptions) == EXPECTED_EXCEPTION_KEYS
    assert all(exceptions[key]["message"] for key in EXPECTED_EXCEPTION_KEYS)


def test_action_modules_do_not_raise_raw_homeassistant_errors():
    for file_name in ACTION_ERROR_FILES:
        source = (INTEGRATION / file_name).read_text(encoding="utf-8")

        assert "HomeAssistantError(" not in source
        assert "xsense_error(" in source
