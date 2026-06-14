import sys
from types import SimpleNamespace

for module_name in list(sys.modules):
    if module_name == "custom_components.xsense" or module_name.startswith(
        "custom_components.xsense."
    ):
        del sys.modules[module_name]
if not hasattr(sys.modules.get("custom_components"), "__path__"):
    sys.modules.pop("custom_components", None)

from custom_components.xsense import binary_sensor, button, camera, number, select, sensor, switch
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
    calls = []

    class FakeXsense:
        async def keep_camera_live_alive(self, entity):
            raise AssertionError("WebRTC path should not call direct-stream keepalive")

        async def get_camera_webrtc_ticket(self, entity):
            calls.append(("ticket", entity.sn))
            return None

    entity = SimpleNamespace(sn="SSC0A123", online=True, data={})
    camera_entity = object.__new__(camera.XSenseCameraEntity)
    camera_entity.coordinator = SimpleNamespace(xsense=FakeXsense())
    camera_entity._current_entity = lambda: entity
    messages = []

    await camera_entity.async_handle_async_webrtc_offer(
        "v=0\r\n", "session-1", messages.append
    )

    assert calls == [("ticket", "SSC0A123")]
    assert messages[0].code == "xsense_webrtc_ticket_failed"


def test_camera_audio_controls_follow_apk_missing_or_enabled_support_rule():
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

    camera.data["supportLiveAudio"] = True
    camera.data["supportRecordingAudio"] = True
    camera.data["supportLiveSpeakerVolume"] = True

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


async def test_failed_webrtc_start_is_removed_from_active_sessions(monkeypatch):
    from custom_components.xsense import camera as camera_module
    from custom_components.xsense.camera import CAMERA_DESCRIPTION, XSenseCameraEntity

    camera_entity = entity("SSC0A", {"streamProtocol": "webrtc", "supportWebrtc": True})
    camera_entity.entity_id = "camera-test"
    camera_entity.sn = "SSC0ATEST"
    camera_entity.name = "Camera"
    camera_entity.online = True

    async def get_camera_webrtc_ticket(entity):
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
            return False

        async def close(self):
            self.closed = True

    fake_module = SimpleNamespace(
        XSenseWebRTCTicket=SimpleNamespace(
            from_api=lambda serial_number, data: SimpleNamespace(is_valid=True)
        ),
        XSenseWebRTCSession=FakeSession,
    )

    class FakeHass:
        async def async_add_import_executor_job(self, func, module):
            return fake_module

    monkeypatch.setattr(
        camera_module, "async_get_clientsession", lambda hass: SimpleNamespace()
    )

    camera = XSenseCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)
    camera.hass = FakeHass()

    await camera.async_handle_async_webrtc_offer(
        "v=0\r\n", "session-1", lambda message: None
    )

    assert camera._webrtc_sessions == {}
    assert not camera.is_streaming


async def test_webrtc_camera_stream_source_does_not_start_native_live_url():
    from custom_components.xsense.camera import CAMERA_DESCRIPTION, XSenseCameraEntity

    camera_entity = entity("SSC0A", {"streamProtocol": "webrtc", "supportWebrtc": True})
    camera_entity.entity_id = "camera-test"
    camera_entity.sn = "SSC0ATEST"
    camera_entity.name = "Camera"
    camera_entity.online = True

    class XSense:
        async def start_camera_live(self, entity):
            raise AssertionError("WebRTC cameras use getWebrtcTicket, not newstartlive")

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

    assert await camera.stream_source() is None


def test_camera_online_uses_parsed_entity_online_state_like_apk():
    from custom_components.xsense import camera

    camera_entity = entity("SSC0A", {"streamProtocol": "webrtc"})
    camera_entity.online = True
    assert camera._camera_online(camera_entity) is True

    camera_entity.online = False
    camera_entity.data["online"] = 1
    assert camera._camera_online(camera_entity) is False


def test_camera_metadata_fields_are_kept_out_of_entity_registry():
    forbidden = {
        "camera_model",
        "camera_status_code",
        "camera_device_status",
        "camera_sleep_message",
        "camera_wake_time",
        "camera_firmware_status",
        "camera_firmware_version",
        "camera_network_name",
        "camera_stream_protocol",
        "camera_codec",
        "camera_time_zone",
        "camera_time_zone_area",
        "camera_awake",
        "camera_webrtc_supported",
    }
    exposed = {description.key for description in sensor.SENSORS} | {
        description.key for description in binary_sensor.SENSORS
    }

    assert forbidden.isdisjoint(exposed)
