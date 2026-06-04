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
from custom_components.xsense.api import mapping


def entity(device_type, data):
    return SimpleNamespace(type=device_type, data=data)


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


def test_is_life_end_uses_explicit_boolean_parser():
    description = next(
        item for item in binary_sensor.SENSORS if item.key == "is_life_end"
    )

    assert description.value_fn(entity("XS01-WX", {"isLifeEnd": "1"})) is True
    assert description.value_fn(entity("XS01-WX", {"isLifeEnd": "0"})) is False
    assert description.value_fn(entity("XS01-WX", {"isLifeEnd": "unknown"})) is None


def test_switch_camera_controls_require_camera_entity():
    non_camera = entity("XS01-WX", {"needMotion": 1, "isAdmin": True})
    camera = entity("SSC0A", {"needMotion": 1, "isAdmin": True})

    assert not switch.has_camera_data("needMotion")(non_camera)
    assert switch.has_camera_data("needMotion")(camera)


def test_switch_supported_camera_controls_require_camera_entity():
    non_camera = entity("XS01-WX", {"recLamp": 1, "supportRecLamp": True})
    camera = entity("SSC0B", {"recLamp": 1, "supportRecLamp": True, "isAdmin": True})

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

    assert not any(description.exists_fn(non_camera) for description in select.SELECTS)


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


def test_camera_audio_controls_follow_apk_unspecified_support_rule():
    live_audio = next(
        description
        for description in switch.SWITCHES
        if description.key == "camera_live_audio"
    )
    recording_audio = next(
        description
        for description in switch.SWITCHES
        if description.key == "camera_recording_audio"
    )
    live_speaker = next(
        description
        for description in number.NUMBERS
        if description.key == "camera_live_speaker_volume"
    )
    camera = entity(
        "SSC0A",
        {
            "isAdmin": True,
            "liveAudioToggleOn": True,
            "recordingAudioToggleOn": True,
            "liveSpeakerVolume": 80,
        },
    )

    assert live_audio.exists_fn(camera)
    assert recording_audio.exists_fn(camera)
    assert live_speaker.exists_fn(camera)

    camera.data["supportLiveAudio"] = False
    camera.data["supportRecordingAudio"] = False
    camera.data["supportLiveSpeakerVolume"] = False

    assert not live_audio.exists_fn(camera)
    assert not recording_audio.exists_fn(camera)
    assert not live_speaker.exists_fn(camera)


def test_supported_camera_controls_require_explicit_support_flag():
    camera = entity(
        "SSC0B",
        {"recLamp": 1, "alarmVol": 50, "antiflicker": 50, "isAdmin": True},
    )

    assert not switch.has_supported_data("recLamp", "supportRecLamp")(camera)
    assert not number.has_supported_data("alarmVol", "supportAlarmVolume")(camera)
    assert not select.has_supported_data(
        "antiflicker", support_key="supportAntiFlicker"
    )(camera)

    camera.data["supportRecLamp"] = True
    camera.data["supportAlarmVolume"] = True
    camera.data["supportAntiFlicker"] = True

    assert switch.has_supported_data("recLamp", "supportRecLamp")(camera)
    assert number.has_supported_data("alarmVol", "supportAlarmVolume")(camera)
    assert select.has_supported_data("antiflicker", support_key="supportAntiFlicker")(
        camera
    )


def test_camera_write_controls_require_explicit_admin_flag():
    camera = entity(
        "SSC0A",
        {
            "needMotion": 1,
            "alarmVol": 50,
            "deviceLanguage": "en",
            "deviceSupportLanguage": ["en"],
            "supportAlarmVolume": True,
        },
    )

    assert not switch.has_camera_data("needMotion")(camera)
    assert not number.has_supported_data("alarmVol", "supportAlarmVolume")(camera)
    assert not select.has_data("deviceLanguage", "deviceSupportLanguage")(camera)

    camera.data["isAdmin"] = True

    assert switch.has_camera_data("needMotion")(camera)
    assert number.has_supported_data("alarmVol", "supportAlarmVolume")(camera)
    assert select.has_data("deviceLanguage", "deviceSupportLanguage")(camera)


def test_camera_default_codec_requires_explicit_codec_change_support():
    codec = next(
        description
        for description in select.SELECTS
        if description.key == "camera_default_codec"
    )
    camera = entity(
        "SSC0A",
        {"defaultCodec": "h264", "isAdmin": True, "showCodecChange": 1},
    )

    assert not codec.exists_fn(camera)

    camera.data["showCodecChange"] = True

    assert codec.exists_fn(camera)


def test_camera_cooldown_switch_requires_current_value():
    cooldown = next(
        description
        for description in switch.SWITCHES
        if description.key == "camera_cooldown"
    )
    camera = entity(
        "SSC0A",
        {
            "cooldownEnabled": True,
            "cooldownSupported": True,
            "isAdmin": True,
            "supportPirCooldown": True,
        },
    )

    assert not cooldown.exists_fn(camera)

    camera.data["cooldownValue"] = 10

    assert cooldown.exists_fn(camera)


def test_alarm_status_is_unknown_until_reported():
    alarm = entity("XS01-WX", {})

    assert binary_sensor.has_alarm_status(alarm)
    assert binary_sensor.alarm_status(alarm) is None

    alarm.data["alarmStatus"] = "1"

    assert binary_sensor.alarm_status(alarm) is True


def test_camera_platform_import_does_not_load_webrtc_bridge():
    sys.modules.pop("custom_components.xsense.camera", None)
    sys.modules.pop("custom_components.xsense.webrtc_signal", None)

    from custom_components.xsense import camera  # noqa: F401

    assert "custom_components.xsense.webrtc_signal" not in sys.modules


def test_camera_update_invalidates_capability_cache():
    from custom_components.xsense.camera import XSenseCameraEntity, CAMERA_DESCRIPTION
    from homeassistant.components.camera.const import StreamType

    camera_entity = entity("SSC0A", {"streamProtocol": "rtsp"})

    class Coordinator:
        def __init__(self):
            self.data = {
                "stations": {camera_entity.entity_id: camera_entity},
                "devices": {},
            }

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    camera_entity.entity_id = "camera-test"
    camera_entity.sn = "SSC0ATEST"
    camera_entity.name = "Camera"
    camera_entity.online = True
    camera = XSenseCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)

    initial_capabilities = camera.camera_capabilities

    camera_entity.data.update({"streamProtocol": "webrtc", "supportWebrtc": True})
    camera._invalidate_camera_capabilities_cache()

    assert camera.camera_capabilities is not initial_capabilities
    assert camera.camera_capabilities.frontend_stream_types == {StreamType.WEB_RTC}


def test_camera_entity_webrtc_protocol_default_matches_apk():
    from custom_components.xsense import camera

    assert camera._is_webrtc_camera(entity("SSC0A", {}))
    assert camera._is_webrtc_camera(entity("SSC0A", {"streamProtocol": "webrtc"}))
    assert not camera._is_webrtc_camera(entity("SSC0A", {"streamProtocol": "rtsp"}))
    assert not camera._is_webrtc_camera(entity("SSC0A", {"streamProtocol": "RTMP"}))
