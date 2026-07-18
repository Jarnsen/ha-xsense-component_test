import asyncio
import inspect
import json
import logging
from types import SimpleNamespace

import pytest

from custom_components.xsense.coordinator import (
    KEYPAD_CODE_EVENT_TYPE,
    SELF_TEST_EVENT_TYPE,
    _is_self_test_topic,
    _normalize_self_test_report,
)


def test_connect_path_does_not_reintroduce_integration_login_timeout():
    import inspect
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    source = inspect.getsource(XSenseDataUpdateCoordinator._connect)

    assert "wait_for" not in source
    assert "LOGIN_TIMEOUT" not in source
    assert "Timed out connecting" not in source


def test_self_test_topic_detection_matches_apk_markers():
    assert _is_self_test_topic(
        "$aws/things/SBS50sn/shadow/name/selftestup/update"
    )
    assert _is_self_test_topic(
        "$aws/things/SBS50sn/shadow/name/2nd_selftestup/update"
    )
    assert _is_self_test_topic(
        "$aws/things/SBS50sn/shadow/name/selftestup_v2/update"
    )
    assert _is_self_test_topic(
        "$aws/things/SBS50sn/shadow/name/2nd_alarmtestup/update"
    )
    assert _is_self_test_topic(
        "$aws/things/SBS50sn/shadow/name/2nd_listener_testup/update"
    )
    assert not _is_self_test_topic(
        "$aws/things/SBS50sn/shadow/name/2nd_safemode/update"
    )


def test_self_test_report_normalizes_apk_result_aliases():
    data = {"result": "successful", "eventTime": "20260619120000"}

    _normalize_self_test_report(data)

    assert data["lastSelfTest"] == "0"
    assert data["lastSelfTestTime"] == "20260619120000"


def test_self_test_report_normalizes_nested_apk_shadow_bean():
    data = {
        "device-sn": {
            "stationSN": "station-sn",
            "deviceSN": "device-sn",
            "userId": "user-id",
            "selfTest": "0",
            "time": "20260711120000",
        }
    }

    _normalize_self_test_report(data)

    assert "lastSelfTest" not in data
    assert data["device-sn"]["lastSelfTest"] == "0"
    assert data["device-sn"]["lastSelfTestTime"] == "20260711120000"
    assert data["device-sn"]["stationSN"] == "station-sn"
    assert data["device-sn"]["deviceSN"] == "device-sn"


def test_self_test_report_normalizes_apk_v2_fault_bean_success():
    data = {
        "stationSN": "station-sn",
        "deviceSN": "device-sn",
        "selfTestCoFault": "0",
        "selfTestSmokeFault": "0",
        "selfTestLowPower": "0",
        "selfTestLifeEnd": "0",
        "time": "20260711120500",
    }

    _normalize_self_test_report(data)

    assert data["lastSelfTest"] == "0"
    assert data["lastSelfTestTime"] == "20260711120500"


def test_self_test_report_normalizes_apk_v2_fault_bean_failure():
    data = {
        "stationSN": "station-sn",
        "deviceSN": "device-sn",
        "selfTestCoFault": "0",
        "selfTestSmokeFault": "1",
        "selfTestLowPower": "0",
        "selfTestLifeEnd": "0",
        "time": "20260711120500",
    }

    _normalize_self_test_report(data)

    assert data["lastSelfTest"] == "1"
    assert data["lastSelfTestTime"] == "20260711120500"


@pytest.mark.asyncio
async def test_subscribe_topic_uses_apk_qos1():
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    calls = []

    class FakeMQTT:
        async def async_subscribe(self, topic, callback, qos, encoding):
            calls.append((topic, qos, encoding))

    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)

    async def callback(topic, payload):
        return None

    await coordinator.subscribe_topic(FakeMQTT(), "topic/name", callback)

    assert calls == [("topic/name", 1, "utf-8")]


class CameraUpdateFailureClient:
    def __init__(self):
        self.calls = 0

    async def update_camera_data(self):
        self.calls += 1
        from custom_components.xsense import coordinator

        raise coordinator.APIFailure("camera update failed")


class NoCameraIpcClient:
    def __init__(self, houses=None):
        self.calls = 0
        self.houses = houses or {}

    async def update_camera_data(self):
        self.calls += 1
        from custom_components.xsense import coordinator

        raise coordinator.APIFailure(
            "Request for IPC code C10101 failed with error "
            "C1000001/500 userName is invalid"
        )


class AddxKickedThenSuccessClient:
    def __init__(self):
        self.calls = 0
        self._addx_session = {"token": "stale-token"}

    async def update_camera_data(self):
        self.calls += 1
        from custom_components.xsense import coordinator

        if self.calls == 1:
            raise coordinator.APIFailure(
                "ADDX request for /device/listuserdevices failed with error -1024/ACCOUNT_GET_KICKED"
            )


class AddxKickedAlwaysClient:
    def __init__(self):
        self.calls = 0
        self._addx_session = {"token": "stale-token"}

    async def update_camera_data(self):
        self.calls += 1
        from custom_components.xsense import coordinator

        raise coordinator.APIFailure(
            "ADDX request for /device/listuserdevices failed with error -1024/ACCOUNT_GET_KICKED"
        )


@pytest.mark.asyncio
async def test_camera_update_failure_does_not_suppress_next_retry():
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.xsense = CameraUpdateFailureClient()
    coordinator._camera_initialized = False
    coordinator._last_camera_update_attempt = None

    await coordinator._update_cameras()
    await coordinator._update_cameras()

    assert coordinator.xsense.calls == 2
    assert coordinator._camera_initialized is False
    assert coordinator._last_camera_update_attempt is None


@pytest.mark.asyncio
async def test_camera_update_recovers_once_after_addx_account_get_kicked():
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.xsense = AddxKickedThenSuccessClient()
    coordinator._camera_initialized = False
    coordinator._last_camera_update_attempt = None

    assert await coordinator._update_cameras() is True

    assert coordinator.xsense.calls == 2
    assert coordinator.xsense._addx_session is None
    assert coordinator._camera_initialized is True
    assert coordinator._last_camera_update_attempt is not None


@pytest.mark.asyncio
async def test_camera_update_preserves_cache_when_addx_account_kick_recovery_fails():
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    camera = SimpleNamespace(entity_id="camera-id", sn="camera-sn", type="SSC0A")
    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.xsense = AddxKickedAlwaysClient()
    coordinator._camera_initialized = True
    coordinator._last_camera_update_attempt = None
    coordinator._camera_station_cache = {"camera-id": camera}

    assert await coordinator._update_cameras() is False

    assert coordinator.xsense.calls == 2
    assert coordinator.xsense._addx_session is None
    assert coordinator._camera_station_cache == {"camera-id": camera}
    assert coordinator._camera_initialized is False
    assert coordinator._last_camera_update_attempt is None


@pytest.mark.asyncio
async def test_no_camera_ipc_registration_failure_is_debug_only(caplog):
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.xsense = NoCameraIpcClient()
    coordinator._camera_initialized = False
    coordinator._last_camera_update_attempt = None
    coordinator._camera_station_cache = {}

    with caplog.at_level(logging.DEBUG):
        assert await coordinator._update_cameras() is False

    assert coordinator.xsense.calls == 1
    assert coordinator._camera_initialized is False
    assert coordinator._last_camera_update_attempt is None
    assert "X-Sense camera metadata skipped: no IPC camera account" in caplog.text
    assert "Could not update X-Sense camera data" not in caplog.text


@pytest.mark.asyncio
async def test_known_camera_ipc_registration_failure_still_warns(caplog):
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator
    from custom_components.xsense.python_xsense.entity_map import EntityType

    camera = SimpleNamespace(entity_type=EntityType.CAMERA, type="SSC0A")
    house = SimpleNamespace(stations={"camera-id": camera})
    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.xsense = NoCameraIpcClient(houses={"house-id": house})
    coordinator._camera_initialized = False
    coordinator._last_camera_update_attempt = None
    coordinator._camera_station_cache = {}

    with caplog.at_level(logging.WARNING):
        assert await coordinator._update_cameras() is False

    assert "Could not update X-Sense camera data" in caplog.text


@pytest.mark.asyncio
async def test_startup_refresh_defers_mqtt_and_camera_history_work():
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    calls = []

    class FakeMQTT:
        connected = True

        async def async_connect(self):
            calls.append(("mqtt_connect",))

    house = SimpleNamespace(mqtt_server="mqtt.example")
    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.xsense = SimpleNamespace(houses={"house-id": house})
    coordinator.mqtt_servers = {}
    coordinator._startup_refresh_complete = False
    coordinator.mqtt_server = lambda _host: None
    coordinator.setup_mqtt = lambda _house: FakeMQTT()

    async def get_devices(
        retry=False,
        include_camera_history=True,
        include_camera_update=True,
        include_state_update=True,
    ):
        calls.append(
            (
                "get_devices",
                include_camera_history,
                include_camera_update,
                include_state_update,
            )
        )
        return {"stations": {}, "devices": {}}

    async def assure_subscriptions(_house):
        calls.append(("assure_subscriptions",))

    async def request_device_updates(_mqtt, _house):
        calls.append(("request_device_updates",))

    coordinator.get_devices = get_devices
    coordinator.assure_subscriptions = assure_subscriptions
    coordinator.request_device_updates = request_device_updates

    assert await XSenseDataUpdateCoordinator._async_update_data(coordinator) == {
        "stations": {},
        "devices": {},
    }

    assert calls == [("get_devices", False, True, True)]
    assert coordinator._startup_refresh_complete is True

    await XSenseDataUpdateCoordinator._async_update_data(coordinator)

    assert calls == [
        ("get_devices", False, True, True),
        ("get_devices", True, True, True),
        ("mqtt_connect",),
        ("assure_subscriptions",),
        ("request_device_updates",),
    ]


@pytest.mark.asyncio
async def test_camera_startup_refresh_loads_camera_metadata_before_platform_setup():
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator
    from custom_components.xsense.python_xsense.entity_map import EntityType

    calls = []
    camera = SimpleNamespace(
        entity_id="camera-id",
        entity_type=EntityType.CAMERA,
        type="SSC0A",
        devices={},
    )
    house = SimpleNamespace(stations={"camera-id": camera})

    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.xsense = SimpleNamespace(houses={"house-id": house})
    coordinator._initialized = False
    coordinator._camera_initialized = False
    coordinator._camera_station_cache = {}
    coordinator._camera_ai_history_seen = set()
    coordinator._camera_ai_history_lock = asyncio.Lock()
    coordinator.mqtt_servers = {}

    async def load_all():
        calls.append(("load_all",))

    async def update_cameras():
        calls.append(("update_cameras",))
        return True

    async def get_house_state(_house):
        calls.append(("get_house_state",))

    coordinator.xsense.load_all = load_all
    coordinator.xsense.get_house_state = get_house_state
    coordinator._update_cameras = update_cameras
    coordinator._cache_camera_stations = lambda: calls.append(("cache_cameras",))

    assert await XSenseDataUpdateCoordinator.get_devices(
        coordinator,
        include_camera_history=False,
        include_camera_update=True,
        include_state_update=False,
    ) == {"stations": {"camera-id": camera}, "devices": {}}

    assert calls == [("load_all",), ("update_cameras",), ("cache_cameras",)]


@pytest.mark.asyncio
async def test_first_refresh_keeps_addx_only_camera_available_for_platform_setup():
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator
    from custom_components.xsense.python_xsense.entity_map import EntityType

    camera = SimpleNamespace(
        entity_id="camera-id",
        entity_type=EntityType.CAMERA,
        type="SSC0A",
        devices={},
    )
    house = SimpleNamespace(stations={})

    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.xsense = SimpleNamespace(houses={"house-id": house})
    coordinator._initialized = False
    coordinator._camera_initialized = False
    coordinator._last_camera_update_attempt = None
    coordinator._camera_station_cache = {}
    coordinator._camera_ai_history_seen = set()
    coordinator._camera_ai_history_lock = asyncio.Lock()
    coordinator.mqtt_servers = {}
    coordinator._startup_refresh_complete = False

    async def load_all():
        return None

    async def update_cameras():
        house.stations["camera-id"] = camera
        return True

    async def get_house_state(_house):
        return None

    coordinator.xsense.load_all = load_all
    coordinator.xsense.get_house_state = get_house_state
    coordinator._update_cameras = update_cameras

    data = await XSenseDataUpdateCoordinator._async_update_data(coordinator)

    assert data["stations"] == {"camera-id": camera}
    assert coordinator._camera_station_cache == {"camera-id": camera}
    assert coordinator._startup_refresh_complete is True


def test_deferred_refresh_waits_until_home_assistant_started(monkeypatch):
    from custom_components.xsense import coordinator as coordinator_module
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    calls = []

    def async_call_later(hass, delay, callback):
        calls.append(("timer", delay, callback))
        return lambda: None

    class Bus:
        def async_listen_once(self, event, callback):
            calls.append(("listen", event, callback))
            return lambda: None

    class Hass:
        is_running = False
        bus = Bus()

        def create_task(self, coro):
            calls.append(("task", coro.cr_code.co_name))
            coro.close()

    async def request_refresh():
        calls.append(("request_refresh",))

    monkeypatch.setattr(coordinator_module, "async_call_later", async_call_later)

    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.hass = Hass()
    coordinator._deferred_refresh_unsub = None
    coordinator.async_request_refresh = request_refresh

    XSenseDataUpdateCoordinator.async_schedule_deferred_refresh(coordinator)

    assert calls[0][0:2] == ("listen", "homeassistant_started")
    assert getattr(calls[0][2], "_hass_callback", False)
    calls[0][2](None)
    assert calls[1][0:2] == ("timer", 30)
    assert getattr(calls[1][2], "_hass_callback", False)
    calls[1][2](None)
    assert calls[2] == ("task", "request_refresh")


class PresenceStation:
    sn = "station-sn"
    shadow_name = "XS01-WXstation-sn"

    def __init__(self):
        self.online = None

    def _set_online(self, value):
        self.online = value


class PresenceHouse:
    def __init__(self, station):
        self.stations = {"station-id": station}

    def get_station_by_sn(self, _identifier):
        return None


def test_mqtt_reported_device_list_is_routed_to_apk_state_parser():
    from types import SimpleNamespace
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    class Station:
        sn = "station-sn"
        shadow_name = "station-sn"

        def get_device_by_sn(self, _identifier):
            return None

    station = Station()
    parsed = []
    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.xsense = SimpleNamespace(
        houses={"house-id": PresenceHouse(station)},
        parse_get_state=lambda station_arg, data: parsed.append((station_arg, data)),
    )
    coordinator.async_update_listeners = lambda: None

    coordinator.async_event_received(
        "$aws/things/station-sn/shadow/name/mainpage/update",
        (
            '{"state":{"reported":[{"deviceSn":"child-sn",'
            '"deviceType":"XS03-iWX","onLine":"1"}]}}'
        ).encode(),
    )

    assert parsed == [
        (
            station,
            [{"deviceSn": "child-sn", "deviceType": "XS03-iWX", "onLine": "1"}],
        )
    ]


def test_mqtt_child_devs_payload_is_routed_to_apk_state_parser():
    from types import SimpleNamespace
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    class Station:
        sn = "station-sn"
        shadow_name = "station-sn"

        def get_device_by_sn(self, _identifier):
            return None

    station = Station()
    parsed = []
    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.xsense = SimpleNamespace(
        houses={"house-id": PresenceHouse(station)},
        parse_get_state=lambda station_arg, data: parsed.append((station_arg, data)),
    )
    coordinator.async_update_listeners = lambda: None

    coordinator.async_event_received(
        "$aws/things/station-sn/shadow/name/mainpage/update",
        (
            '{"state":{"reported":{"stationSN":"station-sn",'
            '"devs":{"shadow-key":{"_deviceSN":"child-sn","onLine":"1"}}}}}'
        ).encode(),
    )

    assert parsed == [
        (
            station,
            {
                "stationSN": "station-sn",
                "devs": {"shadow-key": {"_deviceSN": "child-sn", "onLine": "1"}},
            },
        )
    ]


def test_mqtt_target_device_payload_is_routed_to_apk_state_parser():
    from types import SimpleNamespace
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    class Station:
        sn = "station-sn"
        shadow_name = "station-sn"

        def get_device_by_sn(self, identifier):
            return object() if identifier == "child-sn" else None

    station = Station()
    parsed = []
    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.xsense = SimpleNamespace(
        houses={"house-id": PresenceHouse(station)},
        parse_get_state=lambda station_arg, data: parsed.append((station_arg, data)),
    )
    coordinator.async_update_listeners = lambda: None

    coordinator.async_event_received(
        "$aws/things/station-sn/shadow/name/2nd_alarm/update",
        (
            '{"state":{"reported":{"stationSN":"station-sn",'
            '"deviceSN":"child-sn","type":"XS03-iWX","isAlarm":"1",'
            '"time":"20260701075100"}}}'
        ).encode(),
    )

    assert parsed == [
        (
            station,
            {
                "devs": {
                    "child-sn": {
                        "stationSN": "station-sn",
                        "deviceSN": "child-sn",
                        "type": "XS03-iWX",
                        "isAlarm": "1",
                        "time": "20260701075100",
                    },
                },
            },
        )
    ]


@pytest.mark.parametrize("serial_key", ["deviceSn", "devSerialNumber"])
def test_mqtt_xs01m_alarm_event_routes_apk_serial_alias_to_child(serial_key):
    from types import SimpleNamespace
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    class Station:
        sn = "station-sn"
        shadow_name = "SBS50station-sn"

        def get_device_by_sn(self, identifier):
            return object() if identifier == "xs01m-sn" else None

    station = Station()
    parsed = []
    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.xsense = SimpleNamespace(
        houses={"house-id": PresenceHouse(station)},
        parse_get_state=lambda station_arg, data: parsed.append((station_arg, data)),
    )
    coordinator.async_update_listeners = lambda: None

    coordinator.async_event_received(
        "$aws/things/SBS50station-sn/shadow/name/2nd_alarm/update",
        json.dumps(
            {
                "state": {
                    "reported": {
                        "stationSN": "station-sn",
                        serial_key: "xs01m-sn",
                        "type": "XS01-M",
                        "isAlarm": "1",
                        "time": "20260707082221",
                    }
                }
            }
        ).encode(),
    )

    assert parsed == [
        (
            station,
            {
                "devs": {
                    "xs01m-sn": {
                        "stationSN": "station-sn",
                        serial_key: "xs01m-sn",
                        "type": "XS01-M",
                        "isAlarm": "1",
                        "time": "20260707082221",
                    },
                },
            },
        )
    ]


def test_mqtt_skp0a_safenotice_fires_keypad_code_event(caplog):
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    class Station:
        sn = "15A9862E"
        shadow_name = "SBS50-15A9862E"

        def get_device_by_sn(self, _identifier):
            return None

    class Bus:
        def __init__(self):
            self.events = []

        def async_fire(self, event_type, payload):
            self.events.append((event_type, payload))

    station = Station()
    parsed = []
    bus = Bus()
    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.hass = SimpleNamespace(bus=bus)
    coordinator.xsense = SimpleNamespace(
        houses={"house-id": PresenceHouse(station)},
        parse_get_state=lambda station_arg, data: parsed.append((station_arg, data)),
    )
    coordinator.async_update_listeners = lambda: None

    caplog.set_level(logging.INFO)
    coordinator.async_event_received(
        "$aws/things/SBS50-15A9862E/shadow/name/2nd_safenotice/update",
        (
            '{"state":{"reported":{"type":"SBS50","stationSN":"15A9862E",'
            '"safeMode":"Home","time":"20260706163702",'
            '"zoneName":"Europe/Berlin","notices":[{"type":"SKP0A",'
            '"deviceSN":"C76494F1","eventId":"101",'
            '"eventTime":"20260706163702","eventParam":{"alarmCancel":"0",'
            '"safeModeAim":"Home","forceReason":[{}],"exitDelay":"0",'
            '"pword":"1234"}}]}}}'
        ).encode(),
    )

    assert bus.events == [
        (
            KEYPAD_CODE_EVENT_TYPE,
            {
                "station_sn": "15A9862E",
                "device_sn": "C76494F1",
                "keypad_code": "1234",
                "safe_mode": "Home",
                "safe_mode_aim": "Home",
                "mode_button": "Home",
                "submit_button": "Home",
                "event_id": "101",
                "event_time": "20260706163702",
                "alarm_cancel": "0",
            },
        )
    ]
    assert parsed == [
        (
            station,
            {
                "type": "SBS50",
                "stationSN": "15A9862E",
                "safeMode": "Home",
                "time": "20260706163702",
                "zoneName": "Europe/Berlin",
                "notices": [
                    {
                        "type": "SKP0A",
                        "deviceSN": "C76494F1",
                        "eventId": "101",
                        "eventTime": "20260706163702",
                        "eventParam": {
                            "alarmCancel": "0",
                            "safeModeAim": "Home",
                            "forceReason": [{}],
                            "exitDelay": "0",
                            "pword": "1234",
                        },
                    }
                ],
                "devs": {},
            },
        )
    ]
    assert "code_present=True" in caplog.text
    assert "1234" not in caplog.text


def test_mqtt_skp0a_safenotice_skips_keypad_notice_without_code(caplog):
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    class Station:
        sn = "15A9862E"
        shadow_name = "SBS50-15A9862E"

        def get_device_by_sn(self, _identifier):
            return None

    class Bus:
        def __init__(self):
            self.events = []

        def async_fire(self, event_type, payload):
            self.events.append((event_type, payload))

    station = Station()
    parsed = []
    bus = Bus()
    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.hass = SimpleNamespace(bus=bus)
    coordinator.xsense = SimpleNamespace(
        houses={"house-id": PresenceHouse(station)},
        parse_get_state=lambda station_arg, data: parsed.append((station_arg, data)),
    )
    coordinator.async_update_listeners = lambda: None

    caplog.set_level(logging.DEBUG)
    coordinator.async_event_received(
        "$aws/things/SBS50-15A9862E/shadow/name/2nd_safenotice/update",
        (
            '{"state":{"reported":{"type":"SBS50","stationSN":"15A9862E",'
            '"safeMode":"Home","notices":[{"type":"SKP0A",'
            '"deviceSN":"C76494F1","eventId":"101",'
            '"eventParam":{"safeModeAim":"Home"}}]}}}'
        ).encode(),
    )

    assert bus.events == []
    assert parsed
    assert "keypad notice skipped without code" in caplog.text


def test_mqtt_safenotice_ignores_non_keypad_notices():
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    class Station:
        sn = "station-sn"
        shadow_name = "station-sn"

        def get_device_by_sn(self, _identifier):
            return None

    class Bus:
        def __init__(self):
            self.events = []

        def async_fire(self, event_type, payload):
            self.events.append((event_type, payload))

    station = Station()
    bus = Bus()
    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.hass = SimpleNamespace(bus=bus)
    coordinator.xsense = SimpleNamespace(
        houses={"house-id": PresenceHouse(station)}, parse_get_state=lambda *_: None
    )
    coordinator.async_update_listeners = lambda: None

    coordinator.async_event_received(
        "$aws/things/station-sn/shadow/name/2nd_safenotice/update",
        (
            '{"state":{"reported":{"stationSN":"station-sn",'
            '"notices":[{"type":"XS03-iWX","eventParam":{"pword":"1234"}}]}}}'
        ).encode(),
    )

    assert bus.events == []


def test_presence_topic_updates_station_online_like_apk():
    from types import SimpleNamespace
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    station = PresenceStation()
    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.xsense = SimpleNamespace(
        houses={"house-id": PresenceHouse(station)}, parse_get_state=lambda *_: None
    )
    updates = []
    coordinator.async_update_listeners = lambda: updates.append(True)

    coordinator.async_event_received(
        "/events/presence/connected/XS01-WXstation-sn",
        "{\"clientId\":\"XS01-WXstation-sn\",\"eventType\":\"connected\",\"timestamp\":1}".encode(),
    )
    assert station.online is True

    coordinator.async_event_received(
        "/events/presence/disconnected/XS01-WXstation-sn",
        "{\"clientId\":\"XS01-WXstation-sn\",\"eventType\":\"disconnected\",\"timestamp\":2}".encode(),
    )
    assert station.online is False
    assert len(updates) == 2


def test_standalone_wifi_smoke_physical_self_test_report_updates_station():
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    class Bus:
        def __init__(self):
            self.events = []

        def async_fire(self, event_type, payload):
            self.events.append((event_type, payload))

    station = PresenceStation()
    station.type = "XS01-WX"
    parsed = []
    bus = Bus()
    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.hass = SimpleNamespace(bus=bus)
    coordinator.xsense = SimpleNamespace(
        houses={"house-id": PresenceHouse(station)},
        parse_get_state=lambda station_arg, data: parsed.append((station_arg, data)),
    )
    coordinator.async_update_listeners = lambda: None

    coordinator.async_event_received(
        "$aws/things/XS01-WXstation-sn/shadow/name/2nd_selftestup/update",
        (
            '{"state":{"reported":{"stationSN":"station-sn",'
            '"deviceSN":"station-sn","selfTest":"successful",'
            '"eventTime":"20260711120000"}}}'
        ).encode(),
    )

    assert parsed == [
        (
            station,
            {
                "stationSN": "station-sn",
                "deviceSN": "station-sn",
                "selfTest": "successful",
                "eventTime": "20260711120000",
                "lastSelfTest": "0",
                "lastSelfTestTime": "20260711120000",
                "devs": {},
            },
        )
    ]
    assert bus.events == [
        (
            SELF_TEST_EVENT_TYPE,
            {
                "station_sn": "station-sn",
                "device_sn": "station-sn",
                "device_type": "XS01-WX",
                "result": "success",
                "result_code": "0",
                "success": True,
                "event_time": "20260711120000",
                "topic": "$aws/things/XS01-WXstation-sn/shadow/name/2nd_selftestup/update",
            },
        )
    ]


def test_standalone_wifi_smoke_alarmtestup_report_updates_station():
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    station = PresenceStation()
    station.type = "XS01-WX"
    parsed = []
    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.xsense = SimpleNamespace(
        houses={"house-id": PresenceHouse(station)},
        parse_get_state=lambda station_arg, data: parsed.append((station_arg, data)),
    )
    coordinator.async_update_listeners = lambda: None

    coordinator.async_event_received(
        "$aws/things/XS01-WXstation-sn/shadow/name/2nd_alarmtestup/update",
        (
            '{"state":{"reported":{"stationSN":"station-sn",'
            '"deviceSN":"station-sn","selfTest":"0",'
            '"time":"20260711120500"}}}'
        ).encode(),
    )

    assert parsed == [
        (
            station,
            {
                "stationSN": "station-sn",
                "deviceSN": "station-sn",
                "selfTest": "0",
                "time": "20260711120500",
                "lastSelfTest": "0",
                "lastSelfTestTime": "20260711120500",
                "devs": {},
            },
        )
    ]


def test_sbs50_child_self_test_report_updates_child_payload():
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    class Bus:
        def __init__(self):
            self.events = []

        def async_fire(self, event_type, payload):
            self.events.append((event_type, payload))

    child = SimpleNamespace(sn="child-sn", type="XS01-M")
    station = PresenceStation()
    station.type = "SBS50"
    station.shadow_name = "SBS50station-sn"
    station.devices = {"00000007": child}
    station.get_device_by_sn = lambda serial: child if serial == "child-sn" else None
    station.get_device_by_identifier = (
        lambda identifier: child if identifier == "00000007" else None
    )
    parsed = []
    bus = Bus()
    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.hass = SimpleNamespace(bus=bus)
    coordinator.xsense = SimpleNamespace(
        houses={"house-id": PresenceHouse(station)},
        parse_get_state=lambda station_arg, data: parsed.append((station_arg, data)),
    )
    coordinator.async_update_listeners = lambda: None

    coordinator.async_event_received(
        "$aws/things/SBS50station-sn/shadow/name/2nd_selftestup/update",
        (
            '{"state":{"reported":{"00000007":{'
            '"stationSN":"station-sn",'
            '"deviceSN":"child-sn",'
            '"selfTest":"successful",'
            '"time":"20260711121000"}}}}'
        ).encode(),
    )

    assert parsed == [
        (
            station,
            {
                "00000007": {
                    "stationSN": "station-sn",
                    "deviceSN": "child-sn",
                    "selfTest": "successful",
                    "time": "20260711121000",
                    "lastSelfTest": "0",
                    "lastSelfTestTime": "20260711121000",
                },
                "devs": {},
            },
        )
    ]
    assert bus.events == [
        (
            SELF_TEST_EVENT_TYPE,
            {
                "station_sn": "station-sn",
                "device_sn": "child-sn",
                "device_type": "XS01-M",
                "result": "success",
                "result_code": "0",
                "success": True,
                "event_time": "20260711121000",
                "topic": "$aws/things/SBS50station-sn/shadow/name/2nd_selftestup/update",
            },
        )
    ]


@pytest.mark.parametrize("device_type", ["SAL51", "SWS51", "XC0C-MR"])
def test_sbs50_child_self_test_event_is_not_smoke_specific(device_type):
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    class Bus:
        def __init__(self):
            self.events = []

        def async_fire(self, event_type, payload):
            self.events.append((event_type, payload))

    child = SimpleNamespace(sn="child-sn", type=device_type)
    station = PresenceStation()
    station.type = "SBS50"
    station.shadow_name = "SBS50station-sn"
    station.devices = {"00000007": child}
    station.get_device_by_sn = lambda serial: child if serial == "child-sn" else None
    bus = Bus()
    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.hass = SimpleNamespace(bus=bus)
    coordinator.xsense = SimpleNamespace(
        houses={"house-id": PresenceHouse(station)}, parse_get_state=lambda *_: None
    )
    coordinator.async_update_listeners = lambda: None

    coordinator.async_event_received(
        "$aws/things/SBS50station-sn/shadow/name/2nd_listener_testup/update",
        (
            '{"state":{"reported":{"00000007":{'
            '"stationSN":"station-sn",'
            '"deviceSN":"child-sn",'
            '"selfTest":"failed",'
            '"time":"20260711121500"}}}}'
        ).encode(),
    )

    assert bus.events == [
        (
            SELF_TEST_EVENT_TYPE,
            {
                "station_sn": "station-sn",
                "device_sn": "child-sn",
                "device_type": device_type,
                "result": "failed",
                "result_code": "1",
                "success": False,
                "event_time": "20260711121500",
                "topic": "$aws/things/SBS50station-sn/shadow/name/2nd_listener_testup/update",
            },
        )
    ]


@pytest.mark.asyncio
async def test_cached_addx_cameras_remain_in_coordinator_data_when_camera_refresh_is_skipped():
    from datetime import datetime, timezone
    from types import SimpleNamespace

    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    camera = SimpleNamespace(
        entity_id="camera-id",
        sn="camera-sn",
        type="SSC0A",
        devices={},
        online=True,
    )
    house = SimpleNamespace(stations={"camera-id": camera})
    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.xsense = SimpleNamespace(houses={"house-id": house})
    coordinator._camera_initialized = True
    coordinator._last_camera_update_attempt = datetime.now(timezone.utc)
    coordinator._camera_station_cache = {"camera-id": camera}

    assert await coordinator._update_cameras() is False

    stations = {}
    coordinator._merge_cached_camera_stations(stations)

    assert stations == {"camera-id": camera}


def test_mqtt_camera_motion_event_preserves_apk_event_time():
    from custom_components.xsense.coordinator import _mqtt_reported_data

    data = _mqtt_reported_data(
        {
            "eventType": 92,
            "eventTime": "20260614221512",
            "eventData": {
                "serialNumber": "camera-sn",
                "deviceName": "Altanka",
            },
        }
    )

    assert data["serialNumber"] == "camera-sn"
    assert data["eventType"] == 92
    assert data["time"] == "20260614221512"
    assert data["eventTime"] == "20260614221512"
    assert "isMoved" not in data
    assert "lastMotionTime" not in data


def test_mqtt_camera_motion_event_preserves_reported_is_moved_state():
    from custom_components.xsense.coordinator import _mqtt_reported_data

    data = _mqtt_reported_data(
        {
            "eventType": 92,
            "eventData": {
                "serialNumber": "camera-sn",
                "isMoved": "0",
            },
        }
    )

    assert data["isMoved"] == "0"


def test_mqtt_camera_motion_event_accepts_json_string_event_data():
    from custom_components.xsense.coordinator import _mqtt_reported_data

    data = _mqtt_reported_data(
        {
            "eventType": "92",
            "eventData": '{"serialNumber":"camera-sn"}',
        }
    )

    assert data["serialNumber"] == "camera-sn"
    assert data["eventType"] == "92"
    assert data["eventType"] == "92"
    assert "isMoved" not in data


def test_mqtt_camera_motion_event_accepts_apk_motion_event_names():
    from custom_components.xsense.coordinator import _mqtt_reported_data

    data = _mqtt_reported_data(
        {
            "eventType": "motion_detection",
            "eventTime": "20260614221612",
            "eventData": {
                "serialNumber": "camera-sn",
                "deviceName": "Garden",
            },
        }
    )

    assert data["serialNumber"] == "camera-sn"
    assert data["eventType"] == "motion_detection"
    assert data["eventTime"] == "20260614221612"
    assert "isMoved" not in data
    assert "lastMotionTime" not in data


def test_mqtt_camera_motion_event_accepts_nested_apk_motion_event_items():
    from custom_components.xsense.coordinator import _mqtt_reported_data

    data = _mqtt_reported_data(
        {
            "eventTime": "20260614221712",
            "eventData": {
                "serialNumber": "camera-sn",
                "eventItems": [
                    {"eventType": "motion_detected", "eventTime": "20260614221712"}
                ],
            },
        }
    )

    assert data["serialNumber"] == "camera-sn"
    assert data["eventTime"] == "20260614221712"
    assert "isMoved" not in data
    assert "lastMotionTime" not in data


def test_mqtt_top_level_camera_motion_event_is_not_discarded():
    from custom_components.xsense.coordinator import _mqtt_reported_data

    data = _mqtt_reported_data(
        {
            "eventType": "camera_motion",
            "eventTime": "20260614221812",
            "serialNumber": "camera-sn",
        }
    )

    assert data["serialNumber"] == "camera-sn"
    assert data["eventType"] == "camera_motion"
    assert data["eventTime"] == "20260614221812"
    assert "isMoved" not in data
    assert "lastMotionTime" not in data


def test_mqtt_camera_ai_event_maps_apk_detection_objects():
    from custom_components.xsense.coordinator import _mqtt_reported_data

    data = _mqtt_reported_data(
        {
            "eventTime": "20260614231512",
            "eventData": {
                "serialNumber": "camera-sn",
                "eventItems": [{"eventType": "person", "eventTime": "20260612120000"}],
            },
        }
    )

    assert data["lastAiDetection"] == "person"
    assert data["eventTime"] == "20260614231512"
    assert "isMoved" not in data
    assert "lastMotionTime" not in data
    assert data["personDetected"] is True
    assert data["petDetected"] is False
    assert data["vehicleDetected"] is False
    assert data["packageDetected"] is False
    assert data["otherDetected"] is False
    assert data["lastPersonDetectionTime"] == "20260612120000"
    assert data["vehicleEnterDetected"] is False
    assert data["packagePickUpDetected"] is False


def test_mqtt_camera_ai_event_groups_vehicle_and_package_objects():
    from custom_components.xsense.coordinator import _mqtt_reported_data

    data = _mqtt_reported_data(
        {
            "eventTime": "20260614231612",
            "eventData": {
                "serialNumber": "camera-sn",
                "eventItems": [
                    {"eventType": "vehicle_held_up", "eventTime": "20260612120000"},
                    {"eventType": "package_pick_up", "eventTime": "20260612120001"},
                ],
            },
        }
    )

    assert data["lastAiDetection"] == "package_pick_up,vehicle_held_up"
    assert data["vehicleDetected"] is True
    assert data["packageDetected"] is True
    assert data["personDetected"] is False
    assert data["vehicleHeldUpDetected"] is True
    assert data["vehicleEnterDetected"] is False
    assert data["packagePickUpDetected"] is True
    assert data["packageDropOffDetected"] is False
    assert data["lastVehicleDetectionTime"] == "20260612120000"
    assert data["lastVehicleHeldUpDetectionTime"] == "20260612120000"
    assert data["lastPackageDetectionTime"] == "20260612120001"
    assert data["lastPackagePickUpDetectionTime"] == "20260612120001"


def test_mqtt_camera_ai_event_accepts_apk_event_object_type_payload():
    from custom_components.xsense.coordinator import _mqtt_reported_data

    data = _mqtt_reported_data(
        {
            "eventTime": "20260614231712",
            "eventData": {
                "serialNumber": "camera-sn",
                "eventObjectType": {
                    "person": [],
                    "pet": [],
                    "vehicle": ["vehicle_enter"],
                    "package": ["package_exist"],
                },
            },
        }
    )

    assert data["personDetected"] is True
    assert data["petDetected"] is True
    assert data["vehicleDetected"] is True
    assert data["packageDetected"] is True
    assert data["otherDetected"] is False
    assert data["lastAiDetection"] == "package_exist,person,pet,vehicle_enter"
    assert data["vehicleEnterDetected"] is True
    assert data["packageExistDetected"] is True
    assert data["vehicleOutDetected"] is False
    assert data["packageDropOffDetected"] is False


def test_mqtt_camera_ai_event_accepts_json_encoded_object_values():
    from custom_components.xsense.coordinator import _mqtt_reported_data

    data = _mqtt_reported_data(
        {
            "eventTime": "20260614231812",
            "eventData": {
                "serialNumber": "camera-sn",
                "eventObjectType": '{"vehicle":["vehicle_out"],"package":["package_drop_off"]}',
            },
        }
    )

    assert data["lastAiDetection"] == "package_drop_off,vehicle_out"
    assert data["vehicleDetected"] is True
    assert data["packageDetected"] is True
    assert data["personDetected"] is False
    assert data["petDetected"] is False
    assert data["otherDetected"] is False
    assert data["vehicleOutDetected"] is True
    assert data["packageDropOffDetected"] is True
    assert data["vehicleEnterDetected"] is False
    assert data["packagePickUpDetected"] is False
    assert data["lastVehicleDetectionTime"] == "20260614231812"
    assert data["lastVehicleOutDetectionTime"] == "20260614231812"
    assert data["lastPackageDetectionTime"] == "20260614231812"
    assert data["lastPackageDropOffDetectionTime"] == "20260614231812"


def test_mqtt_camera_ai_event_accepts_apk_nested_event_items():
    from custom_components.xsense.coordinator import _mqtt_reported_data

    data = _mqtt_reported_data(
        {
            "eventType": "ai_event",
            "eventTime": "20260614230000",
            "eventData": {
                "serialNumber": "camera-sn",
                "eventItems": [
                    {
                        "eventType": "person",
                        "eventTime": "20260614230100",
                        "evtParams": {"deviceName": "Front"},
                    },
                    {
                        "eventType": "package_pick_up",
                        "eventTime": "20260614230200",
                    },
                ],
            },
        }
    )

    assert data["lastAiDetection"] == "package_pick_up,person"
    assert data["personDetected"] is True
    assert data["packageDetected"] is True
    assert data["packagePickUpDetected"] is True
    assert data["vehicleDetected"] is False
    assert data["lastPersonDetectionTime"] == "20260614230100"
    assert data["lastPackageDetectionTime"] == "20260614230200"
    assert data["lastPackagePickUpDetectionTime"] == "20260614230200"


def test_mqtt_camera_ai_plan_event_uses_apk_dispatch_device_identity():
    from custom_components.xsense.coordinator import _mqtt_reported_data

    data = _mqtt_reported_data(
        {
            "userId": "user-id",
            "eventType": "ai_event",
            "eventTime": "20260614230000",
            "eventData": {
                "serverId": "service-id",
                "dispatchDevs": [
                    {
                        "stationSn": "station-sn",
                        "deviceSn": "camera-sn",
                        "deviceType": "SSC0A",
                        "eventTime": "20260614230100",
                    }
                ],
                "eventItems": [
                    {
                        "eventType": "person",
                        "eventTime": "20260614230200",
                    }
                ],
            },
        }
    )

    assert data["stationSN"] == "station-sn"
    assert data["deviceSN"] == "camera-sn"
    assert data["serialNumber"] == "camera-sn"
    assert data["lastAiDetection"] == "person"
    assert data["lastPersonDetectionTime"] == "20260614230200"


def test_mqtt_dispatch_event_accepts_apk_serial_aliases():
    from custom_components.xsense.coordinator import _mqtt_reported_data

    data = _mqtt_reported_data(
        {
            "eventType": "ai_event",
            "eventTime": "20260707090000",
            "eventData": {
                "dispatchDevs": [
                    {
                        "stationSN": "station-sn",
                        "devSerialNumber": "device-sn",
                        "deviceType": "XS01-M",
                    }
                ],
            },
        }
    )

    assert data["stationSN"] == "station-sn"
    assert data["deviceSN"] == "device-sn"
    assert data["serialNumber"] == "device-sn"


def test_mqtt_ai_plan_event_routes_by_nested_camera_identity():
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    class Camera:
        sn = "camera-sn"
        shadow_name = "SSC0Acamera-sn"

        def __init__(self):
            self.data = {}

        def get_device_by_sn(self, _identifier):
            return None

        def set_data(self, data):
            self.data.update(data)

    class House:
        stations = {"camera-id": Camera()}

        def get_station_by_sn(self, identifier):
            camera = self.stations["camera-id"]
            return camera if identifier == camera.sn else None

    parsed = []
    updates = []
    house = House()
    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.xsense = SimpleNamespace(
        houses={"house-id": house},
        parse_get_state=lambda station_arg, data: parsed.append((station_arg, data)),
    )
    coordinator.async_update_listeners = lambda: updates.append(True)

    coordinator.async_event_received(
        "@xsense/events/aiplan/user-id-code",
        (
            '{"eventTime":"20260614230400","eventData":{'
            '"eventItems":[{"eventType":"person","serialNumber":"camera-sn",'
            '"eventTime":"20260614230401"}]}}'
        ).encode(),
    )

    assert parsed[0][0] is house.stations["camera-id"]
    assert parsed[0][1]["lastAiDetection"] == "person"
    assert parsed[0][1]["lastPersonDetectionTime"] == "20260614230401"
    assert parsed[0][1]["eventTime"] == "20260614230400"
    assert "isMoved" not in parsed[0][1]
    assert "lastMotionTime" not in parsed[0][1]
    assert updates == [True]


async def test_camera_ai_history_poll_routes_apk_alarm_items():
    from custom_components.xsense.const import CAMERA_AI_SERVICE_AVAILABLE
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    class Camera:
        sn = "camera-sn"
        type = "SSC0A"
        shadow_name = "SSC0Acamera-sn"

        def __init__(self):
            self.data = {}

        def get_device_by_sn(self, _identifier):
            return None

        def set_data(self, data):
            self.data.update(data)

    class House:
        stations = {"camera-id": Camera()}

        def get_station_by_sn(self, identifier):
            camera = self.stations["camera-id"]
            return camera if identifier == camera.sn else None

    parsed = []
    updates = []
    house = House()

    class Client:
        houses = {"house-id": house}

        async def get_ai_service_list(self):
            return [{"serverId": "service-id"}]

        async def get_ai_service_history(self, server_id):
            assert server_id == "service-id"
            return {
                "alarmItems": [
                    {
                        "eventId": "event-id",
                        "createTime": "20260614230500",
                        "dispatchDevs": [
                            {
                                "stationSn": "station-sn",
                                "deviceSn": "camera-sn",
                            }
                        ],
                        "eventItems": [
                            {
                                "eventType": "person",
                                "eventTime": "20260614230501",
                            }
                        ],
                    }
                ]
            }

        async def get_camera_event_history(self, serial_numbers, start_timestamp, end_timestamp):
            return {}

        def parse_get_state(self, station_arg, data):
            parsed.append((station_arg, data))
            station_arg.set_data(data)

    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.xsense = Client()
    coordinator._camera_ai_history_seen = set()
    coordinator._camera_ai_history_lock = asyncio.Lock()
    coordinator.async_update_listeners = lambda: updates.append(True)

    assert await XSenseDataUpdateCoordinator._update_camera_ai_history(coordinator)
    assert not await XSenseDataUpdateCoordinator._update_camera_ai_history(coordinator)

    assert parsed[0][0] is house.stations["camera-id"]
    assert parsed[0][1]["lastAiDetection"] == "person"
    assert parsed[0][1]["lastPersonDetectionTime"] == "20260614230501"
    assert parsed[0][1]["eventTime"] == "20260614230500"
    assert house.stations["camera-id"].data[CAMERA_AI_SERVICE_AVAILABLE] is True
    assert "isMoved" not in parsed[0][1]
    assert "lastMotionTime" not in parsed[0][1]
    assert len(parsed) == 1
    assert updates == []


async def test_camera_event_history_routes_motion_when_ai_service_list_is_empty():
    from custom_components.xsense.const import CAMERA_AI_SERVICE_AVAILABLE
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    class Camera:
        sn = "camera-sn"
        type = "SSC0A"
        shadow_name = "SSC0Acamera-sn"

        def __init__(self):
            self.data = {}

        def get_device_by_sn(self, _identifier):
            return None

        def set_data(self, data):
            self.data.update(data)

    class House:
        stations = {"camera-id": Camera()}

        def get_station_by_sn(self, identifier):
            camera = self.stations["camera-id"]
            return camera if identifier == camera.sn else None

    parsed = []
    house = House()

    class Client:
        houses = {"house-id": house}

        async def get_ai_service_list(self):
            return []

        async def get_camera_event_history(
            self, serial_numbers, start_timestamp, end_timestamp
        ):
            assert serial_numbers == ["camera-sn"]
            assert end_timestamp > start_timestamp
            return {
                "list": [
                    {
                        "serialNumber": "camera-sn",
                        "timestamp": 1781478300,
                        "startTime": 1781478300,
                        "endTime": 1781478310,
                        "traceId": "trace-id",
                        "tags": "motion",
                    }
                ]
            }

        def parse_get_state(self, station_arg, data):
            parsed.append((station_arg, data))
            station_arg.set_data(data)

    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.xsense = Client()
    coordinator._camera_ai_history_seen = set()
    coordinator._camera_ai_history_lock = asyncio.Lock()

    assert await XSenseDataUpdateCoordinator._update_camera_ai_history(coordinator)
    assert not await XSenseDataUpdateCoordinator._update_camera_ai_history(coordinator)

    assert parsed[0][0] is house.stations["camera-id"]
    assert parsed[0][1]["eventTime"] == "20260614230500"
    assert parsed[0][1]["playback"] == {
        "trace_id": "trace-id",
        "start_time": 1781478300,
        "start_time_s": 1781478300,
        "end_time": 1781478310,
        "end_time_s": 1781478310,
        "timestamp": 1781478300,
        "timestamp_s": 1781478300,
        "tags": "motion",
    }
    assert house.stations["camera-id"].data[CAMERA_AI_SERVICE_AVAILABLE] is False
    assert "isMoved" not in parsed[0][1]
    assert "lastMotionTime" not in parsed[0][1]
    assert len(parsed) == 1


def test_camera_event_history_station_data_preserves_direct_video_url():
    from custom_components.xsense.coordinator import (
        _camera_event_history_station_data,
    )

    data = _camera_event_history_station_data(
        {
            "serialNumber": "camera-sn",
            "timestamp": 1781478300,
            "traceId": "trace-id",
            "videoUrl": "https://example.invalid/clip.mp4",
            "imageUrl": "https://example.invalid/still.jpg",
            "videoEvent": "motion",
        }
    )

    assert data["playback"] == {
        "trace_id": "trace-id",
        "video_url": "https://example.invalid/clip.mp4",
        "image_url": "https://example.invalid/still.jpg",
        "timestamp": 1781478300,
        "timestamp_s": 1781478300,
        "video_event": "motion",
        "source": "video_url",
    }


def test_camera_event_history_station_data_normalizes_ms_playback_times():
    from custom_components.xsense.coordinator import (
        _camera_event_history_station_data,
    )

    data = _camera_event_history_station_data(
        {
            "serialNumber": "camera-sn",
            "timestamp": 1781478300000,
            "startTime": 1781478300000,
            "endTime": 1781478310000,
            "traceId": "trace-id",
            "tags": "motion",
        }
    )

    assert data["playback"]["start_time"] == 1781478300000
    assert data["playback"]["start_time_s"] == 1781478300
    assert data["playback"]["end_time"] == 1781478310000
    assert data["playback"]["end_time_s"] == 1781478310
    assert data["playback"]["timestamp"] == 1781478300000
    assert data["playback"]["timestamp_s"] == 1781478300


async def test_camera_event_history_does_not_mark_unapplied_records_seen(caplog):
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    class Camera:
        sn = "camera-sn"
        type = "SSC0A"
        shadow_name = "SSC0Acamera-sn"

        def get_device_by_sn(self, _identifier):
            return None

    class House:
        stations = {"camera-id": Camera()}

        def get_station_by_sn(self, identifier):
            camera = self.stations["camera-id"]
            return camera if identifier == camera.sn else None

    class Client:
        houses = {"house-id": House()}

        async def get_ai_service_list(self):
            return []

        async def get_camera_event_history(
            self, serial_numbers, start_timestamp, end_timestamp
        ):
            return {
                "list": [
                    {
                        "serialNumber": "other-camera-sn",
                        "timestamp": 1781478300,
                        "traceId": "trace-id",
                        "tags": "motion",
                    }
                ]
            }

        def parse_get_state(self, station_arg, data):
            raise AssertionError("unmatched record should not update station state")

    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.xsense = Client()
    coordinator._camera_ai_history_seen = set()
    coordinator._camera_ai_history_lock = asyncio.Lock()

    caplog.set_level(logging.DEBUG, logger="custom_components.xsense")

    assert not await XSenseDataUpdateCoordinator._update_camera_ai_history(coordinator)
    assert not await XSenseDataUpdateCoordinator._update_camera_ai_history(coordinator)

    assert coordinator._camera_ai_history_seen == set()
    assert "X-Sense camera record history item was not applied" in caplog.text
    assert "X-Sense camera record history item skipped as duplicate" not in caplog.text


async def test_camera_ai_history_timer_notifies_only_when_history_changes():
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    updates = []
    calls = []

    async def update_history():
        calls.append(True)
        return len(calls) == 1

    coordinator._update_camera_ai_history = update_history
    coordinator.async_update_listeners = lambda: updates.append(True)

    await XSenseDataUpdateCoordinator._async_poll_camera_ai_history(coordinator, None)
    await XSenseDataUpdateCoordinator._async_poll_camera_ai_history(coordinator, None)

    assert updates == [True]


def test_camera_history_polling_starts_interval_and_immediate_poll(monkeypatch):
    from custom_components.xsense import coordinator as coordinator_module
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    calls = []

    def track_time_interval(hass, callback, interval):
        calls.append(("interval", callback, interval.total_seconds()))
        return lambda: None

    class Hass:
        def async_create_task(self, coro):
            assert inspect.iscoroutine(coro)
            calls.append(("task", coro.cr_code.co_name))
            coro.close()

    monkeypatch.setattr(
        coordinator_module,
        "async_track_time_interval",
        track_time_interval,
    )

    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.hass = Hass()
    coordinator._camera_ai_history_unsub = None

    XSenseDataUpdateCoordinator.async_start_camera_ai_history_polling(coordinator)

    assert calls == [
        ("interval", coordinator._async_poll_camera_ai_history, 60.0),
        ("task", "_async_poll_camera_ai_history"),
    ]


async def test_camera_history_poll_logs_when_no_cameras(caplog):
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.xsense = SimpleNamespace(houses={})
    coordinator._camera_ai_history_seen = set()
    coordinator._camera_ai_history_lock = asyncio.Lock()

    caplog.set_level(logging.DEBUG, logger="custom_components.xsense")

    assert not await XSenseDataUpdateCoordinator._update_camera_ai_history(coordinator)
    assert "X-Sense camera history poll skipped: no cameras" in caplog.text


def test_mqtt_camera_ai_event_uses_last_ai_detection_with_event_time():
    from custom_components.xsense.coordinator import _mqtt_reported_data

    data = _mqtt_reported_data(
        {
            "eventTime": "20260614230300",
            "eventData": {
                "serialNumber": "camera-sn",
                "lastAiDetection": "person",
            },
        }
    )

    assert data["lastAiDetection"] == "person"
    assert data["lastPersonDetectionTime"] == "20260614230300"
    assert data["eventTime"] == "20260614230300"
    assert "isMoved" not in data
    assert "lastMotionTime" not in data


def test_camera_record_history_item_preserves_event_time_without_live_motion():
    from custom_components.xsense.coordinator import _camera_event_history_station_data

    data = _camera_event_history_station_data(
        {
            "serialNumber": "camera-sn",
            "timestamp": 1782049304,
            "traceId": "trace-id",
            "videoEvent": "unknown",
            "tags": ["unknown"],
        }
    )

    assert data["serialNumber"] == "camera-sn"
    assert data["eventTime"] == "20260621134144"
    assert "isMoved" not in data
    assert "lastMotionTime" not in data


async def test_assure_subscriptions_includes_apk_ai_plan_topic():
    from custom_components.xsense.coordinator import XSenseDataUpdateCoordinator

    calls = []

    async def assure_subscription(server, topic):
        calls.append((server, topic))

    coordinator = XSenseDataUpdateCoordinator.__new__(XSenseDataUpdateCoordinator)
    coordinator.xsense = SimpleNamespace(userid="user-id", user_id_code="user-id-code")
    coordinator.assure_subscription = assure_subscription
    house = SimpleNamespace(
        mqtt_server="mqtt.example",
        house_id="house-id",
        stations={},
    )

    await XSenseDataUpdateCoordinator.assure_subscriptions(coordinator, house)

    assert ("mqtt.example", "@xsense/events/+/house-id") in calls
    assert ("mqtt.example", "@xsense/events/aiplan/user-id-code") in calls
