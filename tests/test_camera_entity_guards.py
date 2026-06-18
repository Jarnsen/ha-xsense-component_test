import asyncio
import sys
from types import SimpleNamespace

for module_name in list(sys.modules):
    if module_name == "custom_components.xsense" or module_name.startswith(
        "custom_components.xsense."
    ):
        del sys.modules[module_name]
if not hasattr(sys.modules.get("custom_components"), "__path__"):
    sys.modules.pop("custom_components", None)

from custom_components.xsense import (
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


def test_camera_setup_controls_are_not_exposed_in_home_assistant():
    assert not any(
        description.key.startswith("camera_") for description in switch.SWITCHES
    )
    assert select.SELECTS == ()
    assert not any(
        description.key.startswith("camera_") for description in number.NUMBERS
    )


def test_read_only_camera_entities_require_camera_entity():
    non_camera = entity("XS01-WX", {"batteryLevel": 2, "needMotion": 1})
    camera = entity("SSC0A", {"batteryLevel": 2, "needMotion": 1})

    assert not sensor.has_camera_data("batteryLevel")(non_camera)
    assert sensor.has_camera_data("batteryLevel")(camera)


def test_regular_motion_entities_precreate_for_motion_capable_cameras():
    non_camera = entity("XS01-WX", {"needMotion": 1})
    camera = entity("SSC0A", {"needMotion": 1})

    motion = next(item for item in binary_sensor.SENSORS if item.key == "moved")

    assert not motion.exists_fn(non_camera)
    assert motion.exists_fn(camera)
    assert motion.value_fn(camera) is None


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


def test_camera_capabilities_follow_native_ha_webrtc_entity_class():
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseCameraEntity,
        XSenseWebRTCCameraEntity,
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
    webrtc_camera = XSenseWebRTCCameraEntity(
        Coordinator(webrtc_camera_entity), webrtc_camera_entity, CAMERA_DESCRIPTION
    )

    assert {
        stream.value for stream in rtsp_camera.camera_capabilities.frontend_stream_types
    } == {"hls"}
    assert {
        stream.value
        for stream in webrtc_camera.camera_capabilities.frontend_stream_types
    } == {"web_rtc"}

    assert (
        webrtc_camera._async_get_webrtc_client_configuration().data_channel
        == "data-channel-of-"
    )


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


async def test_webrtc_camera_uses_native_ha_signaling_without_stream_source():
    from custom_components.xsense.camera import (
        CAMERA_DESCRIPTION,
        XSenseWebRTCCameraEntity,
    )

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

    camera = XSenseWebRTCCameraEntity(Coordinator(), camera_entity, CAMERA_DESCRIPTION)
    camera.entity_id = "camera.camera_test"

    assert await camera.stream_source() is None
    assert (
        camera._async_get_webrtc_client_configuration().data_channel
        == "data-channel-of-"
    )


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
    assert camera._webrtc_sessions == {}
    assert camera._pending_webrtc_candidates == {}


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
