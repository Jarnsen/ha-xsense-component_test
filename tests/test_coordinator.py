from types import SimpleNamespace

import pytest

from custom_components.xsense.coordinator import _is_self_test_topic


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
        "$aws/things/SBS50sn/shadow/name/2nd_listener_testup/update"
    )
    assert not _is_self_test_topic(
        "$aws/things/SBS50sn/shadow/name/2nd_safemode/update"
    )


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


def test_mqtt_camera_motion_event_maps_to_apk_is_moved_state():
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
    assert data["isMoved"] == "1"
    assert data["lastMotionTime"] == "20260614221512"


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
    assert data["isMoved"] == "1"


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
