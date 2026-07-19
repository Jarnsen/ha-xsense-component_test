import json
from pathlib import Path

from custom_components.xsense import binary_sensor, button, number, select, sensor, switch


ROOT = Path(__file__).parents[1]


def _translation_name(domain: str, key: str) -> str:
    strings = json.loads(
        (ROOT / "custom_components/xsense/strings.json").read_text(encoding="utf-8")
    )
    return strings["entity"][domain][key]["name"]


def _description_name(domain: str, descriptions, key: str) -> str:
    description = next(item for item in descriptions if item.key == key)
    if description.translation_key:
        return _translation_name(domain, description.translation_key)
    return description.name


def test_shipped_english_entity_names_match_source_strings():
    source = json.loads(
        (ROOT / "custom_components/xsense/strings.json").read_text(encoding="utf-8")
    )
    english = json.loads(
        (ROOT / "custom_components/xsense/translations/en.json").read_text(
            encoding="utf-8"
        )
    )

    assert english["entity"] == source["entity"]


def test_detector_names_match_apk_1400_terms():
    assert _description_name(
        "sensor", sensor.SENSORS, "device_status"
    ) == "Device Status"
    assert _description_name(
        "binary_sensor", binary_sensor.SENSORS, "mute_status"
    ) == "Device Silenced"
    assert _description_name("button", button.BUTTONS, "test") == "Device Test"
    assert _description_name("button", button.BUTTONS, "fire_drill") == "Alarm Drill"
    assert _description_name("sensor", sensor.SENSORS, "co") == "CO Reading"
    assert _description_name("sensor", sensor.SENSORS, "co_level") == "CO Level"
    assert _description_name(
        "sensor", sensor.SENSORS, "co_peak"
    ) == "Peak CO Level"


def test_device_setting_names_match_apk_1400_terms():
    assert next(item for item in switch.SWITCHES if item.key == "led_light").name == (
        "LED Indicator"
    )
    assert _description_name(
        "select", select.SELECTS, "mailbox_report_interval"
    ) == "Data Reporting Interval"
    assert _description_name(
        "number", number.NUMBERS, "radon_minimum_threshold"
    ) == "Green Line Threshold"
    assert _description_name(
        "number", number.NUMBERS, "radon_maximum_threshold"
    ) == "Red Line Threshold"
    assert _description_name(
        "number", number.NUMBERS, "temperature_adjustment"
    ) == "Temperature Calibration"
    assert _description_name(
        "number", number.NUMBERS, "humidity_adjustment"
    ) == "Relative Humidity Calibration"


def test_camera_names_match_apk_1400_terms():
    assert next(
        item for item in button.BUTTONS if item.key == "camera_wake"
    ).name == "Wake Up"
    assert next(
        item for item in switch.SWITCHES if item.key == "camera_sleep"
    ).name == "Sleep Mode"
    assert next(
        item for item in switch.SWITCHES if item.key == "camera_mirror_flip"
    ).name == "Rotate Image"
    assert next(
        item for item in select.SELECTS if item.key == "camera_antiflicker_rate"
    ).name == "Flicker Frequency"
    assert next(
        item for item in number.NUMBERS if item.key == "camera_alarm_seconds"
    ).name == "Alarm Duration"
