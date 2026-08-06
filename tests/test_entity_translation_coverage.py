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


ENTITY_DESCRIPTIONS = {
    "binary_sensor": binary_sensor._ALL_SENSORS,
    "button": button.BUTTONS,
    "number": number.NUMBERS,
    "select": select.SELECTS,
    "sensor": sensor._ALL_SENSORS,
    "switch": switch.SWITCHES,
}


DEVICE_CLASS_ONLY_SENSOR_KEYS = {"temperature", "humidity", "battery"}


def _entity_strings() -> dict:
    return json.loads(STRINGS.read_text(encoding="utf-8"))["entity"]


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
