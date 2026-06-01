import sys
from types import SimpleNamespace

for module_name in list(sys.modules):
    if module_name == "custom_components.xsense" or module_name.startswith(
        "custom_components.xsense."
    ):
        del sys.modules[module_name]
if not hasattr(sys.modules.get("custom_components"), "__path__"):
    sys.modules.pop("custom_components", None)

from custom_components.xsense import binary_sensor, number, select, sensor, switch


def entity(device_type, data):
    return SimpleNamespace(type=device_type, data=data)


def test_switch_camera_controls_require_camera_entity():
    non_camera = entity("XS01-WX", {"needMotion": 1, "isAdmin": True})
    camera = entity("SSC0A", {"needMotion": 1, "isAdmin": True})

    assert not switch.has_camera_data("needMotion")(non_camera)
    assert switch.has_camera_data("needMotion")(camera)


def test_switch_supported_camera_controls_require_camera_entity():
    non_camera = entity("XS01-WX", {"recLamp": 1, "supportRecLamp": True})
    camera = entity("SSC0B", {"recLamp": 1, "supportRecLamp": True})

    assert not switch.has_supported_data("recLamp", "supportRecLamp")(non_camera)
    assert switch.has_supported_data("recLamp", "supportRecLamp")(camera)


def test_select_camera_controls_require_camera_entity():
    non_camera = entity(
        "XS01-WX",
        {"deviceLanguage": "en", "deviceSupportLanguage": ["en"], "isAdmin": True},
    )
    camera = entity(
        "SSC0A",
        {"deviceLanguage": "en", "deviceSupportLanguage": ["en"], "isAdmin": True},
    )

    assert not select.has_data("deviceLanguage", "deviceSupportLanguage")(non_camera)
    assert select.has_data("deviceLanguage", "deviceSupportLanguage")(camera)


def test_all_select_camera_controls_require_camera_entity():
    non_camera = entity(
        "XS01-WX",
        {
            "antiflicker": 50,
            "cooldownOptions": [5, 10],
            "cooldownSupported": True,
            "cooldownValue": 5,
            "defaultCodec": "h264",
            "isAdmin": True,
            "showCodecChange": True,
            "supportAntiFlicker": True,
            "supportPirCooldown": True,
        },
    )

    assert not any(
        description.exists_fn(non_camera) for description in select.SELECTS
    )


def test_number_camera_controls_require_camera_entity():
    non_camera = entity("XS01-WX", {"nightThresholdLevel": 2, "isAdmin": True})
    camera = entity("SSC0B", {"nightThresholdLevel": 2, "isAdmin": True})

    assert not number.has_data("nightThresholdLevel")(non_camera)
    assert number.has_data("nightThresholdLevel")(camera)


def test_read_only_camera_entities_require_camera_entity():
    non_camera = entity("XS01-WX", {"batteryLevel": 2, "needMotion": 1})
    camera = entity("SSC0A", {"batteryLevel": 2, "needMotion": 1})

    assert not sensor.has_camera_data("batteryLevel")(non_camera)
    assert sensor.has_camera_data("batteryLevel")(camera)
    assert not binary_sensor.has_camera_data("needMotion")(non_camera)
    assert binary_sensor.has_camera_data("needMotion")(camera)
