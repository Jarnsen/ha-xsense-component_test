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
