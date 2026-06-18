import base64
from collections import defaultdict
import hashlib
import importlib
import json
import logging
import sys
import types
from pathlib import Path

import pytest

API_PATH = Path(__file__).resolve().parents[2] / "custom_components" / "xsense" / "api"


def load_api_module(module_name: str):
    """Import the embedded API package without importing the HA integration package."""
    sys.modules.setdefault("custom_components", types.ModuleType("custom_components"))

    xsense_pkg = types.ModuleType("custom_components.xsense")
    xsense_pkg.__path__ = [str(API_PATH.parent)]
    sys.modules["custom_components.xsense"] = xsense_pkg

    api_pkg = types.ModuleType("custom_components.xsense.api")
    api_pkg.__path__ = [str(API_PATH)]
    sys.modules["custom_components.xsense.api"] = api_pkg

    return importlib.import_module(f"custom_components.xsense.api.{module_name}")


async_xsense = load_api_module("async_xsense")
base = importlib.import_module("custom_components.xsense.api.base")
entity = load_api_module("entity")
device_module = load_api_module("device")
entity_map = load_api_module("entity_map")
exceptions = load_api_module("exceptions")
house = load_api_module("house")
mqtt_helper = load_api_module("mqtt_helper")
station = load_api_module("station")
sys.modules["custom_components.xsense.api"].AsyncXSense = async_xsense.AsyncXSense
sys.modules["custom_components.xsense.api"].House = house.House
xsense_mqtt = importlib.import_module("custom_components.xsense.mqtt")


def test_mqtt_helper_defers_tls_context_loading_until_connect_setup(monkeypatch):
    calls = []
    clients = []

    class FakeClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.contexts = []
            self.ws_paths = []
            clients.append(self)

        def username_pw_set(self, username, password):
            self.username = username
            self.password = password

        def tls_set_context(self, context):
            self.contexts.append(context)

        def ws_set_options(self, path):
            self.ws_paths.append(path)

    def fake_create_default_context():
        calls.append("created")
        return "ssl-context"

    monkeypatch.setattr(mqtt_helper.mqtt_client, "Client", FakeClient)
    monkeypatch.setattr(
        mqtt_helper.ssl, "create_default_context", fake_create_default_context
    )

    helper = mqtt_helper.MQTTHelper(
        signer=types.SimpleNamespace(
            presign_url=lambda *args: "wss://mqtt.example/mqtt?sig=abc"
        ),
        house=types.SimpleNamespace(
            mqtt_server="mqtt.example",
            mqtt_region="us-east-1",
        ),
    )

    assert calls == []
    assert clients[0].contexts == []
    assert clients[0].ws_paths == []

    helper.prepare_connection()

    assert calls == ["created"]
    assert clients[0].contexts == ["ssl-context"]
    assert clients[0].ws_paths == ["/mqtt?sig=abc"]

    helper.prepare_connection()

    assert calls == ["created"]
    assert clients[0].contexts == ["ssl-context"]
    assert clients[0].ws_paths == ["/mqtt?sig=abc", "/mqtt?sig=abc"]


def test_mqtt_helper_subscribe_uses_apk_qos1_by_default():
    subscribed = []

    class FakeClient:
        def subscribe(self, topic, qos=0):
            subscribed.append((topic, qos))
            return "subscribed"

    helper = mqtt_helper.MQTTHelper(
        signer=types.SimpleNamespace(
            presign_url=lambda *args: "wss://mqtt.example/mqtt?sig=abc"
        ),
        house=types.SimpleNamespace(
            house_id="house-id",
            mqtt_server="mqtt.example",
            mqtt_region="us-east-1",
            stations={},
        ),
    )
    helper.client = FakeClient()

    assert helper.subscribe("topic/name") == "subscribed"
    assert subscribed == [("topic/name", 1)]


def test_mqtt_helper_publish_uses_compact_utf8_json():
    published = []

    class FakeClient:
        def publish(self, topic, payload, qos=0, retain=False):
            published.append((topic, payload, qos, retain))
            return "published"

    helper = mqtt_helper.MQTTHelper(
        signer=types.SimpleNamespace(
            presign_url=lambda *args: "wss://mqtt.example/mqtt?sig=abc"
        ),
        house=types.SimpleNamespace(
            mqtt_server="mqtt.example",
            mqtt_region="us-east-1",
        ),
    )
    helper.client = FakeClient()
    payload = {"label": "中文", "enabled": True}

    assert helper.publish("topic", payload) == "published"
    assert published == [
        (
            "topic",
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            0,
            False,
        )
    ]


def test_xsense_mqtt_debug_title_redacts_account_email():
    assert (
        xsense_mqtt._redact_account_title("XSense Account user@example.com")
        == "XSense Account <redacted>"
    )
    assert xsense_mqtt._redact_account_title("Other title") == "Other title"


def test_xsense_mqtt_clean_disconnect_is_not_a_warning(caplog):
    caplog.set_level(logging.DEBUG)
    client = object.__new__(xsense_mqtt.XSenseMQTT)
    client.connected = True
    results = []
    client._async_connection_result = results.append

    client._async_on_disconnect(xsense_mqtt.mqtt.MQTT_ERR_SUCCESS)

    assert client.connected is False
    assert results == [False]
    assert "Disconnected from MQTT server (0)" not in caplog.text
    assert "Disconnected from MQTT server cleanly" in caplog.text


def test_xsense_mqtt_nonzero_disconnect_still_warns(caplog):
    client = object.__new__(xsense_mqtt.XSenseMQTT)
    client.connected = True
    results = []
    client._async_connection_result = results.append

    client._async_on_disconnect(7)

    assert client.connected is False
    assert results == [False]
    assert "Disconnected from MQTT server (7)" in caplog.text


def _subscription_test_client():
    client = object.__new__(xsense_mqtt.XSenseMQTT)
    client._simple_subscriptions = defaultdict(set)
    client._wildcard_subscriptions = set()
    client._retained_topics = defaultdict(set)
    client._subscription_id = 0
    client.connected = False
    return client


@pytest.mark.asyncio
async def test_xsense_mqtt_omits_subscription_id_when_ha_signature_lacks_it(
    monkeypatch,
):
    created = []

    class FakeSubscription:
        def __init__(
            self,
            topic,
            is_simple_match,
            complex_matcher,
            job,
            qos=0,
            encoding="utf-8",
        ):
            self.topic = topic
            self.is_simple_match = is_simple_match
            self.complex_matcher = complex_matcher
            self.job = job
            self.qos = qos
            self.encoding = encoding
            created.append(topic)

    monkeypatch.setattr(xsense_mqtt, "Subscription", FakeSubscription)
    client = _subscription_test_client()

    async def callback(msg):
        return None

    await client.async_subscribe("x/sense/one", callback, 0)

    assert created == ["x/sense/one"]
    assert client._subscription_id == 1


@pytest.mark.asyncio
async def test_xsense_mqtt_uses_incrementing_subscription_ids(monkeypatch):
    created = []

    class FakeSubscription:
        def __init__(
            self,
            topic,
            is_simple_match,
            complex_matcher,
            job,
            qos=0,
            encoding="utf-8",
            subscription_id=None,
        ):
            self.topic = topic
            self.is_simple_match = is_simple_match
            self.complex_matcher = complex_matcher
            self.job = job
            self.qos = qos
            self.encoding = encoding
            self.subscription_id = subscription_id
            created.append(subscription_id)

    monkeypatch.setattr(xsense_mqtt, "Subscription", FakeSubscription)
    client = _subscription_test_client()

    async def callback(msg):
        return None

    await client.async_subscribe("x/sense/one", callback, 0)
    await client.async_subscribe("x/sense/two", callback, 1)

    assert created == [1, 2]
    assert client._subscription_id == 2


class FakeAWSSRP:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def get_auth_params(self):
        return {"USERNAME": self.kwargs["username"]}

    def process_challenge(self, challenge_parameters, auth_params):
        return {"PASSWORD_CLAIM": "claim"}


class FakeCognitoClient:
    def __init__(self, *, fail=False):
        self.fail = fail

    def initiate_auth(self, **kwargs):
        if self.fail:
            raise base.BotoCoreError(error_msg="Could not connect to Cognito")
        return {"ChallengeParameters": {"USERNAME": "user-id"}}

    def respond_to_auth_challenge(self, **kwargs):
        return {
            "AuthenticationResult": {
                "AccessToken": "access",
                "IdToken": _test_jwt({"user_id_code": "user-id-code"}),
                "RefreshToken": "refresh",
                "ExpiresIn": 3600,
            }
        }


class FakeBotoSession:
    def __init__(self, *, fail=False):
        self.fail = fail
        self.client_calls = []

    def client(self, service_name, **kwargs):
        self.client_calls.append((service_name, kwargs))
        return FakeCognitoClient(fail=self.fail)


def _login_client():
    client = base.XSenseBase()
    client.region = "us-east-1"
    client.userpool = "pool"
    client.clientid = "client-id"
    client.clientsecret = None
    return client


def _test_jwt(claims):
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode()
    payload = (
        base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    )
    return f"{header}.{payload}."


def test_sync_login_uses_bounded_cognito_network_config(monkeypatch):
    session = FakeBotoSession()
    monkeypatch.setattr(base.boto3, "Session", lambda: session)
    monkeypatch.setattr(base, "AWSSRP", FakeAWSSRP)

    client = _login_client()
    client.sync_login("user@example.com", "password")

    service_name, kwargs = session.client_calls[0]
    config = kwargs["config"]
    assert service_name == "cognito-idp"
    assert kwargs["region_name"] == "us-east-1"
    assert config.connect_timeout == 15
    assert config.read_timeout == 15
    assert config.retries == {"total_max_attempts": 4, "mode": "standard"}
    assert client.access_token == "access"
    assert client.user_id_code == "user-id-code"


def test_restore_session_sets_user_id_code_from_token():
    client = _login_client()

    client.restore_session(
        "user@example.com",
        "access",
        "refresh",
        _test_jwt({"user_id_code": "restored-user-id-code"}),
    )

    assert client.user_id_code == "restored-user-id-code"


def test_restore_session_ignores_malformed_user_id_code_token():
    client = _login_client()

    client.restore_session("user@example.com", "bad-token", "refresh", "also.bad")

    assert client.user_id_code is None


def test_sync_login_maps_cognito_network_errors_to_api_failure(monkeypatch):
    monkeypatch.setattr(base.boto3, "Session", lambda: FakeBotoSession(fail=True))
    monkeypatch.setattr(base, "AWSSRP", FakeAWSSRP)

    with pytest.raises(exceptions.APIFailure, match="Cognito connection failed"):
        _login_client().sync_login("user@example.com", "password")


@pytest.mark.asyncio
async def test_xsense_mqtt_prepares_connection_in_executor():
    calls = []
    prepared = []

    class FakeHass:
        async def async_add_executor_job(self, func, *args):
            calls.append(func)
            return func(*args)

    class FakeHelper:
        def prepare_connection(self):
            prepared.append(True)

    client = object.__new__(xsense_mqtt.XSenseMQTT)
    client.hass = FakeHass()
    client.mqtt_helper = FakeHelper()

    await client._async_prepare_connection()

    assert calls[0].__self__ is client.mqtt_helper
    assert calls[0].__name__ == "prepare_connection"
    assert prepared == [True]


class FakeResponse:
    def __init__(self, status: int, body: str = "body") -> None:
        self.status = status
        self._body = body

    async def text(self) -> str:
        return self._body


class FakeStation:
    def __init__(self, station_type: str = "SBS50") -> None:
        self.type = station_type
        self.sn = "station-sn"
        self.parsed = []
        self.data = {}

    def set_data(self, values):
        self.data.update(values)


def test_station_shadow_names_follow_apk_factory_rules():
    test_house = house.House(None, "house-id", "Home", "US", "us-east-1", "mqtt")

    def make_station(device_type, sn="serial"):
        return station.Station(
            test_house,
            stationId=f"{device_type}-{sn}",
            stationName=device_type,
            stationSn=sn,
            category=device_type,
        )

    assert make_station("SBS10").shadow_name == "serial"
    assert make_station("SBS50").shadow_name == "SBS50serial"
    assert make_station("STH0C").shadow_name == "STH0C-serial"
    assert make_station("SWS0B").shadow_name == "SWS0B-serial"
    assert make_station("XR0A-iR").shadow_name == "XR0A-iR-serial"
    assert make_station("XS0R-iA").shadow_name == "XS0R-iA-serial"
    assert make_station("SC07-WX").shadow_name == "SC07-WX-serial"
    assert make_station("XC04-WX").shadow_name == "XC04-WX-serial"
    assert make_station("XS0E-iR").shadow_name == "XS0E-iRserial"
    assert make_station("XS03-WX").shadow_name == "XS03-WXserial"
    assert make_station("XS01-WX", "ABC123").shadow_name == "XS01-WXABC123"
    assert make_station("XS01-WX", "ABCEN123").shadow_name == "XS01-WX-ABCEN123"


def test_thing_request_uses_apk_sbs10_station_serial_thing_name():
    client = async_xsense.AsyncXSense()
    client.aws_session_token = "token"

    class Signer:
        def sign_headers(self, method, url, region, headers, data):
            return {}

    client.signer = Signer()
    test_house = house.House(None, "house-id", "Home", "US", "us-east-1", "mqtt")
    station_obj = station.Station(
        test_house,
        stationId="station-id",
        stationName="SBS10",
        stationSn="station-sn",
        category="SBS10",
    )

    url, _headers = client._thing_request(station_obj, "mainpage")

    assert "/things/station-sn/shadow?name=mainpage" in url
    assert "SBS10station-sn" not in url


def test_entity_online_state_uses_online_time_report_without_explicit_status():
    device = entity.Entity()

    device.set_data({"onlineTime": "20260531010101", "utcTime": "20260601010101"})
    assert device.online is True

    device.set_data({"onlineTime": "20260531010101", "utcTime": "20260602090102"})
    assert device.online is False

    device.set_data({"online": False})
    assert device.online is False

    device.set_data({"online": 1})
    assert device.online is True

    device.set_data({"online": "unexpected"})
    assert device.online is True


def test_entity_online_time_uses_apk_device_specific_thresholds():
    sws0b = entity.Entity()
    sws0b.type = "SWS0B"
    sws0b.set_data({"onlineTime": "20260531010101", "utcTime": "20260602010100"})
    assert sws0b.online is True

    normal = entity.Entity()
    normal.type = "XS01-WX"
    normal.set_data({"onlineTime": "20260531010101", "utcTime": "20260602010100"})
    assert normal.online is False

    excluded = entity.Entity()
    excluded.type = "STH0C"
    excluded.set_data({"onlineTime": "20260531010101", "utcTime": "20260602010100"})
    assert excluded.online is None


def test_station_set_devices_matches_apk_child_device_normalization():
    station_obj = station.Station(
        None,
        stationId="station-id",
        stationName="Station",
        stationSn="station-sn",
        category="SBS50",
    )

    station_obj.set_devices(
        {
            "deviceSort": ["device-id"],
            "devices": [
                {
                    "deviceId": "device-id",
                    "deviceName": "Smoke",
                    "deviceSn": "device-sn",
                    "deviceType": "XS01-M",
                    "isActivate": "1",
                }
            ],
        }
    )

    device_obj = station_obj.devices["device-id"]
    assert device_obj.online is None
    assert device_obj.station is station_obj
    assert device_obj.data["activate"] is True
    assert device_obj.data["isActivate"] is True


def test_station_set_devices_creates_apk_light_group_devices():
    test_house = house.House(None, "house-id", "Home", "US", "us-east-1", "mqtt")
    station_obj = station.Station(
        test_house,
        stationId="station-id",
        stationName="Station",
        stationSn="station-sn",
        category="SBS50",
        roomId="room-id",
        roomName="Kitchen",
    )

    station_obj.set_devices(
        {
            "deviceSort": ["device-id"],
            "roomId": "room-id",
            "roomName": "Kitchen",
            "devices": [
                {
                    "deviceId": "light-id",
                    "deviceName": "Light",
                    "deviceSn": "light-sn",
                    "deviceType": "SSL51",
                    "groupId": "123",
                    "on": "1",
                }
            ],
            "groupList": [
                {
                    "groupId": "123",
                    "groupName": "Kitchen Lights",
                    "createTime": "20260601",
                    "appTime": "20260601120000",
                    "pirTime": "30",
                }
            ],
        }
    )

    group = station_obj.devices["20260601123"]
    assert group.type == "group-L"
    assert group.name == "Kitchen Lights"
    assert group.sn == "LG000123"
    assert group.station is station_obj
    assert group.data["groupId"] == "123"
    assert group.data["groupName"] == "Kitchen Lights"
    assert group.data["appTime"] == "20260601120000"
    assert group.data["pirTime"] == "30"
    assert group.data["devs"] == ["light-sn"]
    assert group.data["on"] is True
    assert station_obj.device_order == ["device-id"]


def test_station_set_devices_uses_house_room_names_like_apk():
    test_house = house.House(None, "house-id", "Home", "US", "us-east-1", "mqtt")
    test_house.set_rooms(
        {
            "roomSort": ["room-id"],
            "houseRooms": [{"roomId": "room-id", "roomName": "Kitchen"}],
        }
    )
    station_obj = station.Station(
        test_house,
        stationId="station-id",
        stationName="Station",
        stationSn="station-sn",
        category="SBS50",
        roomId="room-id",
    )

    station_obj.set_devices(
        {
            "deviceSort": ["device-id"],
            "roomId": "room-id",
            "devices": [
                {
                    "deviceId": "light-id",
                    "deviceName": "Light",
                    "deviceSn": "light-sn",
                    "deviceType": "SSL51",
                    "roomId": "room-id",
                    "groupId": "123",
                }
            ],
            "groupList": [
                {
                    "groupId": "123",
                    "groupName": "Kitchen Lights",
                    "createTime": "20260601",
                }
            ],
        }
    )

    light = station_obj.devices["light-id"]
    group = station_obj.devices["20260601123"]
    assert light.data["roomName"] == "Kitchen"
    assert group.data["roomName"] == "Kitchen"


def test_initial_online_state_uses_strict_boolean_values():
    station_obj = station.Station(
        None,
        stationId="station-id",
        stationName="Station",
        stationSn="station-sn",
        category="SBS50",
        onLine="0",
    )
    device_obj = device_module.Device(
        station_obj,
        deviceId="device-id",
        deviceName="Device",
        deviceSn="device-sn",
        deviceType="SD11-MR",
        online="1",
    )

    assert station_obj.online is False
    assert device_obj.online is True


def test_online_update_accepts_on_line_without_inventing_unknown_values():
    device_obj = entity.Entity()

    device_obj.set_data({"onLine": "0"})
    assert device_obj.online is False

    device_obj.set_data({"onLine": "unexpected"})
    assert device_obj.online is False


def test_station_alarm_data_preserves_explicit_falsy_values():
    station_obj = station.Station(
        None,
        stationId="station-id",
        stationName="Station",
        stationSn="station-sn",
        category="SBS50",
    )
    station_obj.set_alarm_data({"safeMode": "0", "entryDelay": 0, "forceArm": False})

    assert station_obj.alarm_data["safeMode"] == "0"
    assert station_obj.alarm_data["entryDelay"] == 0
    assert station_obj.alarm_data["forceArm"] is False


def test_parse_get_state_updates_child_from_apk_device_serial_field():
    client = async_xsense.AsyncXSense()
    station_obj = station.Station(
        None,
        stationId="station-id",
        stationName="Station",
        stationSn="station-sn",
        category="SBS10",
    )
    station_obj.set_devices(
        {
            "devices": [
                {
                    "deviceId": "device-id",
                    "deviceName": "Door",
                    "deviceSn": "child-sn",
                    "deviceType": "SDS0A",
                }
            ]
        }
    )

    client.parse_get_state(
        station_obj,
        {"devs": {"state-key": {"_deviceSN": "child-sn", "onLine": "1"}}},
    )

    assert station_obj.devices["device-id"].online is True


def test_parse_get_state_updates_child_when_apk_key_is_device_serial():
    client = async_xsense.AsyncXSense()
    station_obj = station.Station(
        None,
        stationId="station-id",
        stationName="Station",
        stationSn="station-sn",
        category="SBS50",
    )
    station_obj.set_devices(
        {
            "devices": [
                {
                    "deviceId": "device-id",
                    "deviceName": "Sensor",
                    "deviceSn": "child-sn",
                    "deviceType": "XS03-iWX",
                }
            ]
        }
    )

    client.parse_get_state(station_obj, {"devs": {"child-sn": {"onLine": "0"}}})

    assert station_obj.devices["device-id"].online is False


def test_parse_get_state_accepts_apk_reported_device_list():
    client = async_xsense.AsyncXSense()
    station_obj = station.Station(
        None,
        stationId="station-id",
        stationName="Station",
        stationSn="station-sn",
        category="SBS10",
    )
    station_obj.set_devices(
        {
            "devices": [
                {
                    "deviceId": "device-id",
                    "deviceName": "Smoke",
                    "deviceSn": "child-sn",
                    "deviceType": "XS03-iWX",
                }
            ]
        }
    )

    client.parse_get_state(
        station_obj,
        [
            {
                "deviceSn": "child-sn",
                "deviceType": "XS03-iWX",
                "alarmStatus": "0",
                "muteStatus": "1",
                "onLine": "1",
            }
        ],
    )

    child = station_obj.devices["device-id"]
    assert child.online is True
    assert child.data["alarmStatus"] is False
    assert child.data["muteStatus"] is True


def test_parse_get_state_updates_sbs10_child_from_apk_device_list():
    client = async_xsense.AsyncXSense()
    station_obj = station.Station(
        None,
        stationId="station-id",
        stationName="Station",
        stationSn="station-sn",
        category="SBS10",
    )
    station_obj.set_devices(
        {
            "devices": [
                {
                    "deviceId": "device-id",
                    "deviceName": "Smoke",
                    "deviceSn": "child-sn",
                    "deviceType": "XS03-iWX",
                }
            ]
        }
    )

    client.parse_get_state(
        station_obj,
        {
            "stationSN": "station-sn",
            "devs": [
                {
                    "deviceSn": "child-sn",
                    "deviceType": "XS03-iWX",
                    "alarmStatus": "0",
                    "muteStatus": "1",
                    "onLine": "1",
                }
            ],
        },
    )

    child = station_obj.devices["device-id"]
    assert child.online is True
    assert child.data["alarmStatus"] is False
    assert child.data["muteStatus"] is True


def test_parse_get_state_does_not_use_stale_alarm_status_when_missing():
    client = async_xsense.AsyncXSense()
    station_obj = station.Station(
        None,
        stationId="station-id",
        stationName="Station",
        stationSn="station-sn",
        category="SBS50",
    )

    client.parse_get_state(station_obj, {"alarmStatus": "1"})
    assert station_obj.has_alarm is True

    client.parse_get_state(station_obj, {"wifiRSSI": -55})
    assert station_obj.data["alarmStatus"] is True
    assert station_obj.has_alarm is False


def test_parse_get_state_uses_current_activate_without_alarm_status():
    client = async_xsense.AsyncXSense()
    station_obj = station.Station(
        None,
        stationId="station-id",
        stationName="Station",
        stationSn="station-sn",
        category="SBS50",
    )

    client.parse_get_state(station_obj, {"activate": "1"})

    assert station_obj.has_alarm is True


def test_parse_get_state_applies_apk_group_light_result_to_group_device():
    client = async_xsense.AsyncXSense()
    test_house = house.House(None, "house-id", "Home", "US", "us-east-1", "mqtt")
    station_obj = station.Station(
        test_house,
        stationId="station-id",
        stationName="Station",
        stationSn="station-sn",
        category="SBS50",
    )
    group = device_module.Device(
        station_obj,
        deviceId="group-id",
        deviceName="Kitchen Lights",
        deviceSn="LG000123",
        deviceType="group-L",
    )
    group.set_data({"groupId": "123", "on": "0", "devs": ["old-light-sn"]})
    station_obj.devices[group.entity_id] = group

    client.parse_get_state(
        station_obj,
        {
            "stationSN": "station-sn",
            "groupId": 123,
            "isOn": "1",
            "devs": ["light-sn"],
            "shadow": "groupLampPower",
        },
    )

    assert group.data["isOn"] == "1"
    assert group.data["on"] is True
    assert group.data["devs"] == ["light-sn"]
    assert "groupId" not in station_obj.data


def test_parse_get_state_accepts_apk_group_light_devs_list_without_crashing():
    client = async_xsense.AsyncXSense()
    station_obj = station.Station(
        None,
        stationId="station-id",
        stationName="Station",
        stationSn="station-sn",
        category="SBS50",
    )

    client.parse_get_state(station_obj, {"wifiRSSI": -55, "devs": ["light-sn"]})

    assert station_obj.data["wifiRSSI"] == -55


@pytest.mark.asyncio
async def test_get_station_state_uses_legacy_info_for_wifi_smoke_like_apk():
    client = async_xsense.AsyncXSense()
    station = FakeStation("XS01-WX")
    calls = []

    async def get_thing(station_arg, page):
        calls.append(page)
        client._lastres = FakeResponse(200)
        return {"state": {"reported": {"wifiRSSI": -55}}}

    client.get_thing = get_thing

    await client.get_station_state(station)

    assert calls == ["info_station-sn"]
    assert station.data == {"wifiRSSI": -55}


@pytest.mark.asyncio
async def test_get_station_state_uses_second_info_for_new_wifi_devices_like_apk():
    client = async_xsense.AsyncXSense()
    station = FakeStation("STH0C")
    calls = []

    async def get_thing(station_arg, page):
        calls.append(page)
        client._lastres = FakeResponse(200)
        return {"state": {"reported": {"temperature": 21}}}

    client.get_thing = get_thing

    await client.get_station_state(station)

    assert calls == ["2nd_info_station-sn"]
    assert station.data == {"temperature": 21}


@pytest.mark.asyncio
async def test_get_station_state_does_not_guess_second_info_for_unknown_types():
    client = async_xsense.AsyncXSense()
    station = FakeStation("XS01-M")
    calls = []

    async def get_thing(station_arg, page):
        calls.append(page)
        client._lastres = FakeResponse(404, "missing")
        return {"message": "missing"}

    client.get_thing = get_thing

    await client.get_station_state(station)

    assert calls == ["info_station-sn"]
    assert station.data == {}


@pytest.mark.asyncio
@pytest.mark.parametrize("station_type", ["STH0C", "XR0A-iR"])
async def test_get_state_skips_house_level_standalone_device_shadows(station_type):
    client = async_xsense.AsyncXSense()
    station = FakeStation(station_type)
    calls = []

    async def get_thing(station_arg, page):
        calls.append(page)
        raise AssertionError("house-level devices should not query station shadows")

    client.get_thing = get_thing

    await client.get_state(station)

    assert calls == []
    assert station.parsed == []


@pytest.mark.asyncio
async def test_get_state_skips_unknown_station_state_shadow_instead_of_guessing():
    client = async_xsense.AsyncXSense()
    station = FakeStation("UNKNOWN")
    calls = []

    async def get_thing(station_arg, page):
        calls.append(page)
        raise AssertionError("unknown station types should not guess a state shadow")

    client.get_thing = get_thing

    await client.get_state(station)

    assert calls == []
    assert station.parsed == []


@pytest.mark.asyncio
async def test_get_state_uses_sbs50_second_mainpage_shadow():
    client = async_xsense.AsyncXSense()
    station = FakeStation("SBS50")
    calls = []

    async def get_thing(station_arg, page):
        calls.append(page)
        client._lastres = FakeResponse(200)
        return {"state": {"reported": {"alarmStatus": True}}}

    client.get_thing = get_thing
    client.parse_get_state = lambda station_arg, reported: station_arg.parsed.append(
        reported
    )

    await client.get_state(station)

    assert calls == ["2nd_mainpage"]
    assert station.parsed == [{"alarmStatus": True}]


@pytest.mark.asyncio
async def test_get_state_ignores_missing_sbs50_second_mainpage_shadow():
    client = async_xsense.AsyncXSense()
    station = FakeStation("SBS50")
    calls = []

    async def get_thing(station_arg, page):
        calls.append(page)
        client._lastres = FakeResponse(404, "missing")
        return {"message": "missing"}

    client.get_thing = get_thing

    await client.get_state(station)

    assert calls == ["2nd_mainpage"]
    assert station.parsed == []


@pytest.mark.asyncio
async def test_get_state_raises_for_malformed_non_404_response():
    client = async_xsense.AsyncXSense()
    station = FakeStation()

    async def get_thing(station_arg, page):
        client._lastres = FakeResponse(500, "server error")
        return {"state": {}}

    client.get_thing = get_thing

    with pytest.raises(exceptions.APIFailure, match="500/server error"):
        await client.get_state(station)


class FakeXSenseStation:
    def __init__(self, station_type: str, sn: str = "station-sn") -> None:
        self.type = station_type
        self.sn = sn
        self.shadow_name = _expected_station_shadow_name(station_type, sn)
        self.data = {}


def _expected_station_shadow_name(station_type: str, sn: str) -> str:
    if station_type == "SBS10":
        return sn
    if station_type == "SBS50":
        return f"SBS50{sn}"
    if station_type == "XS01-WX":
        separator = "-" if "EN" in sn.upper() or "UL" in sn.upper() else ""
        return f"XS01-WX{separator}{sn}"
    if station_type in {"XS0E-iR", "XS03-WX"}:
        return f"{station_type}{sn}"
    return f"{station_type}-{sn}"


class FakeXSenseDevice:
    def __init__(
        self,
        device_type: str,
        entity_type,
        station: FakeXSenseStation,
    ) -> None:
        self.type = device_type
        self.sn = "device-sn"
        self.station = station
        self.data = {}
        self.entity_type = entity_type


def fake_child_device(
    device_type: str,
    *,
    station: FakeXSenseStation,
    entity_type=None,
) -> FakeXSenseDevice:
    return FakeXSenseDevice(
        device_type, entity_type or entity_map.entities[device_type]["type"], station
    )


async def _capture_action(client, target, action):
    calls = []

    async def do_thing(station_arg, page, data):
        calls.append((station_arg, page, data))
        return {"ok": True}

    client.do_thing = do_thing
    await client.action(target, action)
    assert len(calls) == 1
    station_arg, page, data = calls[0]
    return station_arg, page, data["state"]["desired"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "device_type",
        "entity_type",
        "device_data",
        "station_type",
        "expected_page",
        "expected_shadow",
        "expected_user_param",
        "expected_time_len",
        "expected_station_shadow",
    ),
    [
        (
            "XS0B-MR",
            entity_map.EntityType.SMOKE,
            {},
            "SBS50",
            "2nd_selftest_device-sn",
            "app2ndSelfTest",
            "source=1",
            13,
            "SBS50station-sn",
        ),
        (
            "XS01-WX",
            entity_map.EntityType.SMOKE,
            {},
            "SBS50",
            "2nd_selftest_device-sn",
            "appSelfTest",
            "source=1",
            13,
            "SBS50station-sn",
        ),
        (
            "XS01-WX",
            entity_map.EntityType.SMOKE,
            {"smokeEdition": "9"},
            "SBS50",
            "2nd_selftest_device-sn",
            "app2ndSelfTest",
            "source=1",
            13,
            "SBS50station-sn",
        ),
        (
            "XS01-M",
            entity_map.EntityType.SMOKE,
            {"smokeEdition": "9"},
            "SBS50",
            "2nd_selftest_device-sn",
            "app2ndSelfTest",
            "source=1",
            13,
            "SBS50station-sn",
        ),
        (
            "XS01-M",
            entity_map.EntityType.SMOKE,
            {"smokeEdition": "8"},
            "SBS10",
            "appselftest_device-sn",
            "appSelfTest",
            None,
            None,
            "station-sn",
        ),
        (
            "XS03-iWX",
            entity_map.EntityType.SMOKE,
            {},
            "SBS10",
            "appselftest_device-sn",
            "appSelfTest",
            None,
            None,
            "station-sn",
        ),
        (
            "SD11-MR",
            entity_map.EntityType.SMOKE,
            {},
            "SBS50",
            "2nd_selftest_device-sn",
            "app2ndSelfTest",
            "source=1",
            13,
            "SBS50station-sn",
        ),
        (
            "SWS0A",
            entity_map.EntityType.WATER,
            {},
            "SBS50",
            "2nd_selftest_device-sn",
            "waterSelfTest",
            "source=1",
            13,
            "SBS50station-sn",
        ),
        (
            "SDS0A",
            entity_map.EntityType.DOOR,
            {},
            "SBS50",
            "2nd_selftest_device-sn",
            "app2ndSelfTest",
            "source=1",
            13,
            "SBS50station-sn",
        ),
        (
            "SAL51",
            entity_map.EntityType.LISTENER,
            {},
            "SBS50",
            "2nd_selftest_device-sn",
            "listenerSelfTest",
            None,
            13,
            "SBS50station-sn",
        ),
    ],
)
async def test_self_test_uses_apk_payload_shape(
    device_type,
    entity_type,
    device_data,
    station_type,
    expected_page,
    expected_shadow,
    expected_user_param,
    expected_time_len,
    expected_station_shadow,
):
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    device = fake_child_device(
        device_type, station=FakeXSenseStation(station_type), entity_type=entity_type
    )
    device.data = device_data

    station_arg, page, desired = await _capture_action(client, device, "test")

    if station_type == "SBS10":
        assert station_arg is not device.station
        assert station_arg.shadow_name == expected_station_shadow
    else:
        assert station_arg is device.station
        assert device.station.shadow_name == expected_station_shadow
    assert page == expected_page
    assert desired["shadow"] == expected_shadow
    assert desired["stationSN"] == "station-sn"
    assert desired["deviceSN"] == "device-sn"
    assert desired["userId"] == "user-id"
    if expected_user_param is None:
        assert "userParam" not in desired
    else:
        assert desired["userParam"] == expected_user_param
    if expected_time_len is None:
        assert "time" not in desired
    else:
        assert desired["time"].isdigit()
        assert len(desired["time"]) == expected_time_len


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("station_sn", "expected_thing"),
    [
        ("ABC123", "XS01-WXABC123"),
        ("ABCEN123", "XS01-WX-ABCEN123"),
    ],
)
async def test_xs01_wx_standalone_self_test_uses_own_station_entity_path(
    station_sn, expected_thing
):
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    station = FakeXSenseStation("XS01-WX", station_sn)
    station.entity_type = entity_map.EntityType.SMOKE

    station_arg, page, desired = await _capture_action(client, station, "test")

    assert station_arg is station
    assert station_arg.shadow_name == expected_thing
    assert page == f"2nd_selftest_{station_sn}"
    assert desired["time"].isdigit()
    assert len(desired["time"]) == 13
    desired_without_time = {k: v for k, v in desired.items() if k != "time"}
    assert desired_without_time == {
        "deviceSN": station_sn,
        "shadow": "appSelfTest",
        "stationSN": station_sn,
        "userId": "user-id",
        "userParam": "source=1",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("station_sn", "smoke_edition", "expected_topic", "expected_thing"),
    [
        ("ABC123", "8", "appmute", "XS01-WXABC123"),
        ("ABCEN123", "9", "2nd_appmute", "XS01-WX-ABCEN123"),
    ],
)
async def test_xs01_wx_mute_targets_apk_thing_name(
    station_sn, smoke_edition, expected_topic, expected_thing
):
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    device = fake_child_device("XS01-WX", station=FakeXSenseStation("SBS50", station_sn))
    device.data = {"smokeEdition": smoke_edition}

    station_arg, page, desired = await _capture_action(client, device, "mute")

    assert station_arg.shadow_name == expected_thing
    assert page == expected_topic
    assert desired["shadow"] == "appMute"
    assert desired["stationSN"] == station_sn
    assert desired["deviceSN"] == "device-sn"
    assert desired["muteType"] == "0"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("station_sn", "expected_thing"),
    [
        ("ABC123", "XS01-WXABC123"),
        ("ABCEN123", "XS01-WX-ABCEN123"),
    ],
)
async def test_xs01_wx_standalone_mute_uses_own_station_entity_path(
    station_sn, expected_thing
):
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    station = FakeXSenseStation("XS01-WX", station_sn)
    station.entity_type = entity_map.EntityType.SMOKE

    station_arg, page, desired = await _capture_action(client, station, "mute")

    assert station_arg.shadow_name == expected_thing
    assert page == "appmute"
    assert desired["shadow"] == "appMute"
    assert desired["stationSN"] == station_sn
    assert desired["deviceSN"] == station_sn
    assert desired["muteType"] == "0"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("device_type", "expected_shadow", "expected_topic", "expected_thing"),
    [
        ("SC06-WX", "appMute", "2nd_appmute", "SC06-WX-station-sn"),
        ("SC07-WX", "appMute", "2nd_appmute", "SC07-WX-station-sn"),
        ("XP0H-iR", "appMute", "2nd_appmute", "XP0H-iR-station-sn"),
        ("XP0A-iR", "appMute", "2nd_appmute", "XP0A-iR-station-sn"),
        ("XP0J-iA", "appMute", "2nd_appmute", "XP0J-iA-station-sn"),
        ("XS0B-iR", "appMute", "2nd_appmute", "XS0B-iR-station-sn"),
        ("XS0E-iR", "appMute", "2nd_appmute", "XS0E-iRstation-sn"),
        ("XS03-WX", "appMute", "2nd_appmute", "XS03-WXstation-sn"),
        ("XS0R-iA", "appMute", "2nd_appmute", "XS0R-iA-station-sn"),
        ("XC04-WX", "appMute", "2nd_appmute", "XC04-WX-station-sn"),
        ("XC0C-iA", "appMute", "2nd_appmute", "XC0C-iA-station-sn"),
        ("XC0C-iR", "appMute", "2nd_appmute", "XC0C-iR-station-sn"),
        ("STH0C", "extendMute", "2nd_appmute", "STH0C-station-sn"),
        ("XC0M-iR", "appMute", "2nd_appmute", "XC0M-iR-station-sn"),
        ("XR0A-iR", "extendMute", "2nd_appmute", "XR0A-iR-station-sn"),
        ("SWS0B", "appWater", "2nd_appwater", "SWS0B-station-sn"),
    ],
)
async def test_wifi_device_mute_uses_apk_factory_payload_shape(
    device_type, expected_shadow, expected_topic, expected_thing
):
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    device = FakeXSenseStation(device_type)

    station_arg, page, desired = await _capture_action(client, device, "mute")

    assert station_arg.shadow_name == expected_thing
    assert page == expected_topic
    assert desired["shadow"] == expected_shadow
    assert desired["stationSN"] == "station-sn"
    assert desired["deviceSN"] == "station-sn"
    assert desired["userId"] == "user-id"
    assert desired["muteType"] == "1"
    assert desired["time"].isdigit()
    assert len(desired["time"]) == 14


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("device_type", "entity_type", "expected_thing"),
    [
        ("XP0J-iA", entity_map.EntityType.COMBI, "XP0J-iA-station-sn"),
        ("XS0R-iA", entity_map.EntityType.SMOKE, "XS0R-iA-station-sn"),
    ],
)
async def test_standalone_wifi_self_test_uses_own_station_entity_path(
    device_type, entity_type, expected_thing
):
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    station = FakeXSenseStation(device_type)
    station.entity_type = entity_type

    station_arg, page, desired = await _capture_action(client, station, "test")

    assert station_arg.shadow_name == expected_thing
    assert page == "2nd_selftest_station-sn"
    assert desired["shadow"] == "appSelfTest"
    assert desired["stationSN"] == "station-sn"
    assert desired["deviceSN"] == "station-sn"
    assert desired["userId"] == "user-id"
    assert desired["userParam"] == "source=1"
    assert desired["time"].isdigit()
    assert len(desired["time"]) == 13


@pytest.mark.asyncio
async def test_mailbox_mute_uses_apk_payload_shape():
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    device = fake_child_device("SMA51", station=FakeXSenseStation("SBS50"))

    station_arg, page, desired = await _capture_action(client, device, "mute")

    assert station_arg is device.station
    assert page == "2nd_appmailmute"
    assert desired["shadow"] == "appMailMute"
    assert desired["stationSN"] == "station-sn"
    assert desired["deviceSN"] == "device-sn"
    assert desired["userId"] == "user-id"
    assert desired["muteType"] == "1"
    assert "silenceTime" not in desired
    assert "setType" not in desired
    assert desired["time"].isdigit()
    assert len(desired["time"]) == 14


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("device_type", "expected_shadow"),
    [
        ("SD11-MR", "appMute"),
        ("SD19-MN", "appMute"),
        ("SK0Z-3S", "appMute"),
        ("LP/N-SA-0B", "appMute"),
        ("XP02S-MR", "appMute"),
        ("XS0D-MR", "appMute"),
        ("XC0C-MR", "app2ndMute"),
        ("SC01-MR", "appSc07mrMute"),
        ("XP0H-MR", "appSc07mrMute"),
        ("XP0P-MR", "appSc07mrMute"),
    ],
)
async def test_sbs50_child_mute_uses_apk_payload_shape(device_type, expected_shadow):
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    device = fake_child_device(device_type, station=FakeXSenseStation("SBS50"))

    station_arg, page, desired = await _capture_action(client, device, "mute")

    assert station_arg is device.station
    assert page == "2nd_appmute"
    assert desired["shadow"] == expected_shadow
    assert desired["stationSN"] == "station-sn"
    assert desired["deviceSN"] == "device-sn"
    assert desired["userId"] == "user-id"
    assert desired["muteType"] == "1"
    assert desired["time"].isdigit()
    assert len(desired["time"]) == 14


@pytest.mark.asyncio
async def test_xs03_iwx_mute_uses_apk_station_serial_thing_name():
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    device = fake_child_device("XS03-iWX", station=FakeXSenseStation("SBS10"))

    station_arg, page, desired = await _capture_action(client, device, "mute")

    assert station_arg.shadow_name == "station-sn"
    assert page == "appmute"
    assert desired["shadow"] == "appMute"
    assert desired["stationSN"] == "station-sn"
    assert desired["deviceSN"] == "device-sn"
    assert desired["userId"] == "user-id"
    assert desired["muteType"] == "1"
    assert desired["time"].isdigit()
    assert len(desired["time"]) == 14


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("device_type", "entity_type", "expected_thing"),
    [
        ("XP0J-iA", entity_map.EntityType.COMBI, "XP0J-iA-station-sn"),
        ("XS0R-iA", entity_map.EntityType.SMOKE, "XS0R-iA-station-sn"),
    ],
)
async def test_standalone_wifi_fire_drill_uses_own_station_entity_path(
    device_type, entity_type, expected_thing
):
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    station = FakeXSenseStation(device_type)
    station.entity_type = entity_type

    station_arg, page, desired = await _capture_action(client, station, "firedrill")

    assert station_arg.shadow_name == expected_thing
    assert page == "2nd_firedrill"
    assert desired["stationSN"] == "station-sn"
    assert desired["deviceSN"] == "station-sn"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("device_type", "expected_shadow", "expected_topic", "expected_thing"),
    [
        ("SC06-WX", "appMute", "2nd_appmute", "SC06-WX-station-sn"),
        ("SC07-WX", "appMute", "2nd_appmute", "SC07-WX-station-sn"),
        ("XC04-WX", "appMute", "2nd_appmute", "XC04-WX-station-sn"),
        ("XC0C-iA", "appMute", "2nd_appmute", "XC0C-iA-station-sn"),
        ("XC0C-iR", "appMute", "2nd_appmute", "XC0C-iR-station-sn"),
        ("XC0M-iR", "appMute", "2nd_appmute", "XC0M-iR-station-sn"),
        ("XP0A-iR", "appMute", "2nd_appmute", "XP0A-iR-station-sn"),
        ("XP0H-iR", "appMute", "2nd_appmute", "XP0H-iR-station-sn"),
        ("XP0J-iA", "appMute", "2nd_appmute", "XP0J-iA-station-sn"),
        ("XR0A-iR", "extendMute", "2nd_appmute", "XR0A-iR-station-sn"),
        ("XS03-WX", "appMute", "2nd_appmute", "XS03-WXstation-sn"),
        ("XS0B-iR", "appMute", "2nd_appmute", "XS0B-iR-station-sn"),
        ("XS0E-iR", "appMute", "2nd_appmute", "XS0E-iRstation-sn"),
        ("XS0R-iA", "appMute", "2nd_appmute", "XS0R-iA-station-sn"),
        ("STH0C", "extendMute", "2nd_appmute", "STH0C-station-sn"),
        ("SWS0B", "appWater", "2nd_appwater", "SWS0B-station-sn"),
    ],
)
async def test_standalone_wifi_mute_uses_own_station_entity_path_for_every_model(
    device_type, expected_shadow, expected_topic, expected_thing
):
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    station = FakeXSenseStation(device_type)

    station_arg, page, desired = await _capture_action(client, station, "mute")

    assert station_arg.shadow_name == expected_thing
    assert page == expected_topic
    assert desired["shadow"] == expected_shadow
    assert desired["stationSN"] == station.sn
    assert desired["deviceSN"] == station.sn


@pytest.mark.asyncio
async def test_fire_drill_keeps_datetime_payload_shape():
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    device = fake_child_device("XS0B-MR", station=FakeXSenseStation("SBS50"))
    calls = []

    async def do_thing(station, page, data):
        calls.append((station, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.action(device, "firedrill")

    assert len(calls) == 1
    _, page, data = calls[0]
    desired = data["state"]["desired"]
    assert page == "2nd_firedrill"
    assert desired["shadow"] == "appFireDrill"
    assert desired["stationSN"] == "station-sn"
    assert desired["deviceSN"] == "station-sn"
    assert desired["time"].isdigit()
    assert len(desired["time"]) == 14
    assert desired["drill"] == "1"
    assert desired["drillTime"] == "30"


class FakePostResponse:
    def __init__(self, status: int = 200, body: str = "shadow error") -> None:
        self.status = status
        self._body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self):
        return {"ok": True}

    async def text(self):
        return self._body


class FakePostSession:
    def __init__(self, status: int = 200):
        self.calls = []
        self.status = status

    def post(self, url, data=None, json=None, headers=None):
        self.calls.append({"url": url, "data": data, "json": json, "headers": headers})
        return FakePostResponse(self.status)


@pytest.mark.asyncio
async def test_do_thing_signs_and_sends_same_serialized_body():
    client = async_xsense.AsyncXSense()
    client.aws_access_expiry = async_xsense.datetime.now(async_xsense.timezone.utc)
    session = FakePostSession()
    signed_payloads = []

    client._aws_token_expiring = lambda: False

    async def get_session():
        return session

    client._get_session = get_session

    def thing_request(station, page, data):
        signed_payloads.append(data)
        return "https://example.invalid", {"signed": "yes"}

    client._thing_request = thing_request

    payload = {"state": {"desired": {"b": 2, "a": 1, "label": "中文"}}}
    result = await client.do_thing(
        FakeXSenseStation("SBS50"), "2nd_selftest_device-sn", payload
    )

    assert result == {"ok": True}
    assert len(signed_payloads) == 1
    assert len(session.calls) == 1
    assert session.calls[0]["json"] is None
    assert session.calls[0]["data"] == signed_payloads[0]
    assert session.calls[0]["data"] == async_xsense._shadow_update_body(payload)
    assert session.calls[0]["data"] == json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    )


@pytest.mark.asyncio
async def test_do_thing_raises_on_shadow_update_failure():
    client = async_xsense.AsyncXSense()
    session = FakePostSession(status=403)

    client._aws_token_expiring = lambda: False

    async def get_session():
        return session

    client._get_session = get_session
    client._thing_request = lambda station, page, data: (
        "https://example.invalid",
        {"signed": "yes"},
    )

    with pytest.raises(exceptions.APIFailure, match="403/shadow error"):
        await client.do_thing(
            FakeXSenseStation("SBS50"),
            "2nd_selftest_device-sn",
            {"state": {"desired": {"a": 1}}},
        )


async def _capture_volume_update(client, target, volume_key, volume):
    calls = []

    async def do_thing(station_arg, page, data):
        calls.append((station_arg, page, data))
        return {"ok": True}

    client.do_thing = do_thing
    await client.update_shadow_volume(target, volume_key, volume)
    assert len(calls) == 1
    station_arg, page, data = calls[0]
    return station_arg, page, data["state"]["desired"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "station_type",
        "station_data",
        "volume_key",
        "volume",
        "expected_page",
        "expected_desired",
    ),
    [
        (
            "SBS50",
            {},
            "voiceVol",
            35,
            "2nd_cfg_station-sn",
            {"shadow": "infoBase", "stationSN": "station-sn", "voiceVol": "35"},
        ),
        (
            "SBS10",
            {"voiceVol": 45, "alarmTone": "3"},
            "alarmVol",
            55,
            "info_station-sn",
            {
                "shadow": "infoBase",
                "stationSN": "station-sn",
                "alarmVol": "55",
                "voiceVol": "45",
                "alarmTone": "3",
            },
        ),
    ],
)
async def test_station_volume_uses_apk_station_payload_shape(
    station_type, station_data, volume_key, volume, expected_page, expected_desired
):
    client = async_xsense.AsyncXSense()
    station_obj = FakeXSenseStation(station_type)
    station_obj.data = station_data

    station_arg, page, desired = await _capture_volume_update(
        client, station_obj, volume_key, volume
    )

    assert station_arg is station_obj
    assert page == expected_page
    assert desired == expected_desired


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "device_type",
        "entity_type",
        "device_data",
        "volume_key",
        "volume",
        "expected_desired",
    ),
    [
        (
            "XS0B-MR",
            entity_map.EntityType.SMOKE,
            {"alarmTone": "2"},
            "alarmVol",
            65,
            {
                "shadow": "infoDev",
                "stationSN": "station-sn",
                "alarmVol": "65",
                "deviceSN": "device-sn",
                "alarmTone": "2",
            },
        ),
        (
            "SDS0A",
            entity_map.EntityType.DOOR,
            {"chirpTone": "3"},
            "chirpVol",
            40,
            {
                "shadow": "infoDev",
                "chirpVol": "40",
                "deviceSN": "device-sn",
                "chirpTone": "3",
            },
        ),
        (
            "SDS0A",
            entity_map.EntityType.DOOR,
            {"remindTone": "2"},
            "remindVol",
            30,
            {
                "shadow": "infoDev",
                "remindVol": "30",
                "deviceSN": "device-sn",
                "remindTone": "2",
            },
        ),
        (
            "CB0Z-3S",
            entity_map.EntityType.LIGHT,
            {"alarmTone": "1"},
            "alarmVol",
            70,
            {
                "shadow": "infoDev",
                "alarmVol": "70",
                "deviceSN": "device-sn",
                "alarmTone": "1",
            },
        ),
        (
            "XC0C-MR",
            entity_map.EntityType.CO,
            {"alarmTone": "3"},
            "alarmVol",
            80,
            {
                "shadow": "infoDev",
                "alarmVol": "80",
                "deviceSN": "device-sn",
                "alarmTone": "3",
            },
        ),
        (
            "STH0B",
            entity_map.EntityType.TEMPERATURE,
            {"alarmTone": "2"},
            "alarmVol",
            60,
            {
                "shadow": "infoDev",
                "alarmVol": "60",
                "deviceSN": "device-sn",
                "alarmTone": "2",
            },
        ),
    ],
)
async def test_device_volume_uses_apk_device_payload_shape(
    device_type, entity_type, device_data, volume_key, volume, expected_desired
):
    client = async_xsense.AsyncXSense()
    device = fake_child_device(
        device_type, station=FakeXSenseStation("SBS50"), entity_type=entity_type
    )
    device.data = device_data

    station_arg, page, desired = await _capture_volume_update(
        client, device, volume_key, volume
    )

    assert station_arg is device.station
    assert page == "2nd_cfg_device-sn"
    assert desired == expected_desired


@pytest.mark.asyncio
async def test_light_power_uses_lamp_power_payload_shape():
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    device = fake_child_device("SSL51", station=FakeXSenseStation("SBS50"))
    calls = []

    async def do_thing(station_arg, page, data):
        calls.append((station_arg, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.update_light_power(device, True)

    assert len(calls) == 1
    station_arg, page, data = calls[0]
    desired = data["state"]["desired"]
    assert station_arg is device.station
    assert page == "2nd_lamppower"
    assert desired["shadow"] == "lampPower"
    assert desired["stationSN"] == "station-sn"
    assert desired["dev"] == "device-sn"
    assert desired["isOn"] == "1"
    assert desired["userId"] == "user-id"
    assert desired["userParam"] == "source=1"
    assert desired["time"].isdigit()
    assert len(desired["time"]) == 14


@pytest.mark.asyncio
async def test_group_light_power_uses_apk_group_power_payload_shape():
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    test_house = house.House(None, "house-id", "Home", "US", "us-east-1", "mqtt")
    station_obj = station.Station(
        test_house,
        stationId="station-id",
        stationName="Station",
        stationSn="station-sn",
        category="SBS50",
    )
    group = device_module.Device(
        station_obj,
        deviceId="group-id",
        deviceName="Kitchen Lights",
        deviceSn="LG000123",
        deviceType="group-L",
    )
    group.set_data({"groupId": "123", "devs": ["light-sn"], "on": "0"})
    calls = []

    async def do_thing(station_arg, page, data):
        calls.append((station_arg, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.update_light_power(group, True)

    assert len(calls) == 1
    station_arg, page, data = calls[0]
    desired = data["state"]["desired"]
    assert station_arg is station_obj
    assert page == "2nd_grouppower"
    assert desired["shadow"] == "groupLampPower"
    assert desired["groupId"] == "123"
    assert desired["devs"] == ["light-sn"]
    assert desired["isOn"] == "1"
    assert desired["stationSN"] == "station-sn"
    assert desired["timeOut"] == "180"
    assert desired["userId"] == "user-id"
    assert desired["userParam"] == "source=1"


def test_house_set_stations_maps_apk_camera_list():
    test_house = house.House(None, "house-id", "Home", "US", "us-east-1", "mqtt")

    test_house.set_stations(
        {
            "stationSort": [],
            "stations": [],
            "cameras": [
                {
                    "ipcId": "cam-id",
                    "roomId": "room-id",
                    "ipcSn": "cam-sn",
                    "ipcName": "Front Camera",
                    "category": "SSC0A",
                    "userId": "user-id",
                    "userName": "owner",
                }
            ],
        }
    )

    camera = test_house.stations["cam-id"]
    assert async_xsense.is_camera_entity(camera)
    assert camera.entity_id == "cam-id"
    assert camera.room_id == "room-id"
    assert camera.name == "Front Camera"
    assert camera.sn == "cam-sn"
    assert camera.type == "SSC0A"
    assert camera.online is True
    assert camera.devices == {}
    assert test_house.station_order == []


def test_house_set_stations_preserves_all_apk_camera_entries_before_model_checks():
    test_house = house.House(None, "house-id", "Home", "US", "us-east-1", "mqtt")

    test_house.set_stations(
        {
            "stationSort": [],
            "stations": [],
            "cameras": [
                {
                    "ipcId": "future-cam-id",
                    "ipcSn": "future-cam-sn",
                    "ipcName": "Future Camera",
                    "category": "SSC99",
                }
            ],
        }
    )

    camera = test_house.stations["future-cam-id"]
    assert camera.entity_id == "future-cam-id"
    assert camera.name == "Future Camera"
    assert camera.sn == "future-cam-sn"
    assert camera.type == "SSC99"
    assert camera.online is True
    assert async_xsense.is_camera_entity(camera)


@pytest.mark.asyncio
async def test_update_camera_data_does_not_place_new_camera_without_house_id_in_multi_house_account():
    client = async_xsense.AsyncXSense()
    first_house = house.House(None, "house-a", "Home A", "US", "us-east-1", "mqtt-a")
    second_house = house.House(None, "house-b", "Home B", "US", "us-east-1", "mqtt-b")
    first_house.set_stations({"stationSort": [], "stations": [], "cameras": []})
    second_house.set_stations({"stationSort": [], "stations": [], "cameras": []})
    client.houses = {"house-a": first_house, "house-b": second_house}

    async def addx_call(endpoint, **kwargs):
        if endpoint == "/device/listuserdevices":
            return {
                "list": [
                    {
                        "serialNumber": "cam-sn",
                        "deviceName": "Front Camera",
                        "modelNo": "SSC0A",
                        "online": 1,
                        "deviceModel": {"streamProtocol": "webrtc"},
                    }
                ]
            }
        return {}

    client.addx_call = addx_call

    await client.update_camera_data()

    assert first_house.get_station_by_sn("cam-sn") is None
    assert second_house.get_station_by_sn("cam-sn") is None


@pytest.mark.asyncio
async def test_update_camera_data_does_not_assume_missing_camera_online_state():
    client = async_xsense.AsyncXSense()
    test_house = house.House(None, "house-id", "Home", "US", "us-east-1", "mqtt")
    test_house.set_stations({"stationSort": [], "stations": [], "cameras": []})
    client.houses = {"house-id": test_house}

    async def addx_call(endpoint, **kwargs):
        if endpoint == "/device/listuserdevices":
            return {
                "list": [
                    {
                        "serialNumber": "cam-sn",
                        "deviceName": "Front Camera",
                        "houseId": "house-id",
                        "modelNo": "SSC0A",
                        "deviceModel": {"streamProtocol": "webrtc"},
                    }
                ]
            }
        return {}

    client.addx_call = addx_call

    await client.update_camera_data()

    camera = test_house.get_station_by_sn("cam-sn")
    assert camera is not None
    assert camera.online is None


@pytest.mark.asyncio
async def test_update_camera_data_accepts_addx_camera_list_as_authority():
    client = async_xsense.AsyncXSense()
    test_house = house.House(None, "house-id", "Home", "US", "us-east-1", "mqtt")
    test_house.set_stations({"stationSort": [], "stations": [], "cameras": []})
    client.houses = {"house-id": test_house}

    async def addx_call(endpoint, **kwargs):
        if endpoint == "/device/listuserdevices":
            return {
                "list": [
                    {
                        "serialNumber": "future-camera-sn",
                        "deviceName": "Future Camera",
                        "houseId": "house-id",
                        "modelNo": "SSC99",
                        "online": 1,
                        "deviceModel": {"streamProtocol": "webrtc"},
                    }
                ]
            }
        return {}

    client.addx_call = addx_call

    await client.update_camera_data()

    camera = test_house.get_station_by_sn("future-camera-sn")
    assert camera is not None
    assert camera.entity_type == async_xsense.EntityType.CAMERA
    assert camera.type == "SSC99"
    assert camera.online is True


@pytest.mark.asyncio
async def test_update_camera_data_accepts_addx_camera_without_model_metadata():
    client = async_xsense.AsyncXSense()
    test_house = house.House(None, "house-id", "Home", "US", "us-east-1", "mqtt")
    test_house.set_stations({"stationSort": [], "stations": [], "cameras": []})
    client.houses = {"house-id": test_house}

    async def addx_call(endpoint, **kwargs):
        if endpoint == "/device/listuserdevices":
            return {
                "list": [
                    {
                        "serialNumber": "camera-sn",
                        "deviceName": "Garage Camera",
                        "houseId": "house-id",
                        "online": 1,
                    }
                ]
            }
        return {}

    client.addx_call = addx_call

    await client.update_camera_data()

    camera = test_house.get_station_by_sn("camera-sn")
    assert camera is not None
    assert camera.entity_type == async_xsense.EntityType.CAMERA
    assert camera.name == "Garage Camera"
    assert camera.type is None
    assert camera.online is True


@pytest.mark.asyncio
async def test_update_camera_data_updates_existing_camera_when_addx_house_id_differs():
    client = async_xsense.AsyncXSense()
    test_house = house.House(None, "xsense-house-id", "Home", "US", "us-east-1", "mqtt")
    test_house.set_stations(
        {
            "stationSort": [],
            "stations": [],
            "cameras": [
                {
                    "ipcId": "cam-id",
                    "ipcSn": "cam-sn",
                    "ipcName": "Garage Camera",
                    "category": "SSC0A",
                }
            ],
        }
    )
    client.houses = {"xsense-house-id": test_house}

    async def addx_call(endpoint, **kwargs):
        if endpoint == "/device/listuserdevices":
            return {
                "list": [
                    {
                        "serialNumber": "cam-sn",
                        "deviceName": "Garage Camera",
                        "houseId": "addx-location-id",
                        "modelNo": "SSC0A",
                        "online": 1,
                        "batteryLevel": 4,
                    }
                ]
            }
        return {}

    client.addx_call = addx_call

    await client.update_camera_data()

    camera = test_house.get_station_by_sn("cam-sn")
    assert camera is not None
    assert camera.entity_id == "cam-id"
    assert camera.name == "Garage Camera"
    assert camera.type == "SSC0A"
    assert camera.online is True
    assert camera.data["batteryLevel"] == 4


@pytest.mark.asyncio
async def test_update_camera_data_places_addx_camera_with_mismatched_house_in_single_house_account():
    client = async_xsense.AsyncXSense()
    test_house = house.House(None, "xsense-house-id", "Home", "US", "us-east-1", "mqtt")
    test_house.set_stations({"stationSort": [], "stations": [], "cameras": []})
    client.houses = {"xsense-house-id": test_house}

    async def addx_call(endpoint, **kwargs):
        if endpoint == "/device/listuserdevices":
            return {
                "list": [
                    {
                        "serialNumber": "camera-sn",
                        "deviceName": "Garage Camera",
                        "houseId": "addx-location-id",
                        "modelNo": "SSC0A",
                        "online": 1,
                    }
                ]
            }
        return {}

    client.addx_call = addx_call

    await client.update_camera_data()

    camera = test_house.get_station_by_sn("camera-sn")
    assert camera is not None
    assert camera.entity_type == async_xsense.EntityType.CAMERA
    assert camera.online is True


@pytest.mark.asyncio
async def test_update_camera_data_updates_known_camera_from_addx_device_list():
    client = async_xsense.AsyncXSense()
    test_house = house.House(None, "house-id", "Home", "US", "us-east-1", "mqtt")
    test_house.set_stations(
        {
            "stationSort": [],
            "stations": [],
            "cameras": [
                {
                    "ipcId": "cam-id",
                    "ipcSn": "cam-sn",
                    "ipcName": "Front Camera",
                    "category": "SSC0A",
                }
            ],
        }
    )
    client.houses = {"house-id": test_house}
    calls = []

    async def addx_call(endpoint, **kwargs):
        calls.append((endpoint, kwargs))
        if endpoint == "/device/listuserdevices":
            return {
                "list": [
                    {
                        "serialNumber": "cam-sn",
                        "deviceName": "Front Camera",
                        "houseId": "house-id",
                        "modelNo": "SSC0A",
                        "online": 1,
                        "batteryLevel": 3,
                        "deviceModel": {"streamProtocol": "webrtc"},
                        "deviceSupport": {"supportWebrtc": 1},
                    }
                ]
            }
        return {}

    client.addx_call = addx_call

    await client.update_camera_data()

    camera = test_house.get_station_by_sn("cam-sn")
    assert camera is not None
    assert camera.data["batteryLevel"] == 3
    assert camera.data["streamProtocol"] == "webrtc"
    assert ("/device/listuserdevices", {}) in calls
    assert (
        "/device/getuserconfig",
        {"serialNumber": "cam-sn", "voiceReminder": False},
    ) in calls


@pytest.mark.asyncio
async def test_update_camera_data_keeps_existing_home_camera_entries_not_in_addx_list():
    client = async_xsense.AsyncXSense()
    test_house = house.House(None, "house-id", "Home", "US", "us-east-1", "mqtt")
    test_house.set_stations(
        {
            "stationSort": [],
            "stations": [],
            "cameras": [
                {
                    "ipcId": "home-camera-id",
                    "ipcSn": "home-camera-sn",
                    "ipcName": "Home Camera",
                    "category": "SSC0A",
                }
            ],
        }
    )
    client.houses = {"house-id": test_house}

    async def addx_call(endpoint, **kwargs):
        if endpoint == "/device/listuserdevices":
            return {
                "list": [
                    {
                        "serialNumber": "real-sn",
                        "deviceName": "Front Camera",
                        "houseId": "house-id",
                        "modelNo": "SSC0A",
                        "online": 1,
                        "batteryLevel": 2,
                        "deviceModel": {"streamProtocol": "webrtc"},
                        "deviceSupport": {"supportWebrtc": 1},
                    }
                ]
            }
        return {}

    client.addx_call = addx_call

    await client.update_camera_data()

    assert test_house.get_station_by_sn("home-camera-sn") is not None
    camera = test_house.get_station_by_sn("real-sn")
    assert camera is not None
    assert camera.entity_id == "real-sn"
    assert camera.name == "Front Camera"
    assert camera.type == "SSC0A"
    assert camera.online is True
    assert camera.data["batteryLevel"] == 2
    assert camera.data["streamProtocol"] == "webrtc"


@pytest.mark.asyncio
async def test_update_camera_data_creates_camera_from_addx_without_home_camera_entry():
    client = async_xsense.AsyncXSense()
    test_house = house.House(None, "1234", "Home", "US", "us-east-1", "mqtt")
    test_house.set_stations({"stationSort": [], "stations": [], "cameras": []})
    client.houses = {"1234": test_house}

    async def addx_call(endpoint, **kwargs):
        if endpoint == "/device/listuserdevices":
            return {
                "list": [
                    {
                        "serialNumber": "camera-sn",
                        "deviceName": "Driveway Camera",
                        "houseId": 1234,
                        "displayModelNo": "SSC0B",
                        "online": 1,
                        "deviceModel": {
                            "modelName": "SSC0B",
                            "streamProtocol": "webrtc",
                        },
                        "deviceSupport": {"supportWebrtc": 1},
                    }
                ]
            }
        return {}

    client.addx_call = addx_call

    await client.update_camera_data()

    camera = test_house.get_station_by_sn("camera-sn")
    assert camera is not None
    assert camera.name == "Driveway Camera"
    assert camera.type == "SSC0B"
    assert camera.data["streamProtocol"] == "webrtc"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("camera_data", "expected"),
    [
        ({"liveResolution": "VIDEO_SIZE_1920x1080"}, "1920x1080"),
        ({"liveResolution": "HD"}, "1920x1080"),
        ({"liveResolution": "auto"}, "auto"),
        ({"supportedRecordingResolutions": ["P1296", "P1080"]}, "2304x1296"),
        (
            {
                "liveResolution": "auto",
                "supportedRecordingResolutions": ["P1296", "P1080"],
            },
            "2304x1296",
        ),
        ({"supportedRecordingResolutions": []}, "auto"),
        ({"supportedRecordingResolutions": ["P1296"]}, "2304x1296"),
        ({"deviceSupportResolution": ["bad", "P720"]}, "1280x720"),
        ({"liveResolution": "UNKNOWN_RESOLUTION"}, "auto"),
    ],
)
async def test_start_camera_live_uses_apk_live_resolution(camera_data, expected):
    client = async_xsense.AsyncXSense()
    camera = device_module.Device(
        None,
        deviceId="cam-id",
        deviceName="Camera",
        deviceSn="cam-sn",
        deviceType="SSC0A",
    )
    camera.set_data(camera_data)
    calls = []

    async def addx_call(endpoint, **kwargs):
        calls.append((endpoint, kwargs))
        return {"liveUrl": "rtsp://example/live"}

    client.addx_call = addx_call

    assert await client.start_camera_live(camera) == "rtsp://example/live"
    assert calls == [
        (
            "/device/newstartlive",
            {"serialNumber": "cam-sn", "liveResolution": expected},
        )
    ]


def test_camera_live_url_uses_apk_response_fields_without_scheme_rewrite():
    assert (
        async_xsense._camera_live_url({"liveUrl": "rtmp://example/live"})
        == "rtmp://example/live"
    )
    assert (
        async_xsense._camera_live_url({"url": "rtsp://example/live"})
        == "rtsp://example/live"
    )
    assert async_xsense._camera_live_url({"liveUrl": ""}) is None


@pytest.mark.asyncio
async def test_update_camera_data_loads_apk_form_options():
    client = async_xsense.AsyncXSense()
    test_house = house.House(None, "house-id", "Home", "US", "us-east-1", "mqtt")
    test_house.set_stations({"stationSort": [], "stations": [], "cameras": []})
    client.houses = {"house-id": test_house}
    calls = []

    async def addx_call(endpoint, **kwargs):
        calls.append((endpoint, kwargs))
        if endpoint == "/device/listuserdevices":
            return {
                "list": [
                    {
                        "serialNumber": "cam-sn",
                        "deviceName": "Front Camera",
                        "houseId": "house-id",
                        "modelNo": "SSC0A",
                        "online": 1,
                        "deviceModel": {"streamProtocol": "webrtc"},
                    }
                ]
            }
        if endpoint == "/device/getuserconfig":
            return {"motionSensitivity": 0, "videoSeconds": 0}
        if endpoint == "/user/getFormOptions":
            return {
                "deviceFormOptions": {
                    "videoSeconds": [{"enabled": True, "value": -1}],
                    "cooldown_in_s": [{"enabled": True, "value": 10}],
                }
            }
        return {}

    client.addx_call = addx_call

    await client.update_camera_data()

    camera = test_house.get_station_by_sn("cam-sn")
    assert camera.data["motionSensitivity"] == 1
    assert camera.data["videoSeconds"] == -1
    assert camera.data["videoSecondsValues"] == [-1]
    assert camera.data["cooldownOptions"] == [10]
    assert "cameraWebrtcTicket" not in camera.data
    assert ("/user/getFormOptions", {"serialNumber": "cam-sn"}) in calls
    assert ("/device/getWebrtcTicket", {"serialNumber": "cam-sn", "verifyDormancyStatus": True}) not in calls


@pytest.mark.asyncio
async def test_update_camera_data_queries_audio_when_apk_support_is_unspecified():
    client = async_xsense.AsyncXSense()
    test_house = house.House(None, "house-id", "Home", "US", "us-east-1", "mqtt")
    test_house.set_stations({"stationSort": [], "stations": [], "cameras": []})
    client.houses = {"house-id": test_house}
    calls = []

    async def addx_call(endpoint, **kwargs):
        calls.append((endpoint, kwargs))
        if endpoint == "/device/listuserdevices":
            return {
                "list": [
                    {
                        "serialNumber": "cam-sn",
                        "deviceName": "Front Camera",
                        "houseId": "house-id",
                        "modelNo": "SSC0A",
                        "online": 1,
                        "deviceModel": {"streamProtocol": "webrtc"},
                        "deviceSupport": {},
                    }
                ]
            }
        if endpoint == "/device/config/querydeviceaudio":
            return {
                "liveAudioToggleOn": True,
                "recordingAudioToggleOn": True,
                "liveSpeakerVolume": 80,
            }
        return {}

    client.addx_call = addx_call

    await client.update_camera_data()

    camera = test_house.get_station_by_sn("cam-sn")
    assert camera.data["liveAudioToggleOn"] is True
    assert camera.data["recordingAudioToggleOn"] is True
    assert camera.data["liveSpeakerVolume"] == 80
    assert ("/device/config/querydeviceaudio", {"serialNumber": "cam-sn"}) in calls


@pytest.mark.asyncio
async def test_get_camera_webrtc_ticket_fetches_on_demand_and_reuses_cache():
    client = async_xsense.AsyncXSense()
    camera = entity.Entity()
    camera.sn = "cam-sn"
    camera.type = "SSC0A"
    calls = []

    async def addx_call(endpoint, **kwargs):
        calls.append((endpoint, kwargs))
        return {
            "signalServer": "https://signal.example",
            "groupId": "group",
            "role": "viewer",
            "id": "client123",
            "traceId": "trace",
            "sign": "sig",
            "time": 123456,
            "expirationTime": 4102444800000,
            "iceServer": [],
        }

    client.addx_call = addx_call

    first = await client.get_camera_webrtc_ticket(camera)
    second = await client.get_camera_webrtc_ticket(camera)
    refreshed = await client.get_camera_webrtc_ticket(camera, force_refresh=True)

    assert first == second == refreshed
    assert calls == [
        (
            "/device/getWebrtcTicket",
            {"serialNumber": "cam-sn", "verifyDormancyStatus": True},
        ),
        (
            "/device/getWebrtcTicket",
            {"serialNumber": "cam-sn", "verifyDormancyStatus": True},
        ),
    ]


@pytest.mark.asyncio
async def test_get_camera_webrtc_ticket_refetches_missing_expiration_like_apk():
    client = async_xsense.AsyncXSense()
    camera = entity.Entity()
    camera.sn = "cam-sn"
    camera.type = "SSC0A"
    camera.set_data({"webrtcTicket": {"signalServer": "https://cached.example"}})
    calls = []

    async def addx_call(endpoint, **kwargs):
        calls.append((endpoint, kwargs))
        return {
            "signalServer": "https://signal.example",
            "groupId": "group",
            "role": "viewer",
            "id": "client123",
            "traceId": "trace",
            "sign": "sig",
            "time": 123456,
            "expirationTime": 4102444800000,
            "iceServer": [],
        }

    client.addx_call = addx_call

    ticket_data = await client.get_camera_webrtc_ticket(camera)

    assert ticket_data["signalServer"] == "https://signal.example"
    assert calls == [
        (
            "/device/getWebrtcTicket",
            {"serialNumber": "cam-sn", "verifyDormancyStatus": True},
        )
    ]


def test_addx_body_requires_ipc_country():
    client = async_xsense.AsyncXSense()

    with pytest.raises(
        exceptions.APIFailure, match="Missing ADDX countryNo from IPC registration"
    ):
        client._addx_body({"language": "en"}, {})


def test_addx_body_requires_ipc_language():
    client = async_xsense.AsyncXSense()

    with pytest.raises(
        exceptions.APIFailure, match="Missing ADDX language from IPC registration"
    ):
        client._addx_body({"countryNo": "US"}, {})


class CapturePostResponse:
    def __init__(self, body):
        self.status = 200
        self._body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def json(self):
        return self._body


class CapturePostSession:
    def __init__(self, response_body):
        self.response_body = response_body
        self.posts = []
        self.closed = False

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        return CapturePostResponse(self.response_body)


def test_calculate_mac_uses_compact_gson_json_for_container_values():
    client = async_xsense.AsyncXSense()
    client.clientsecret = b"secret"

    data = {
        "items": [{"name": "é", "value": 1}],
        "settings": {"label": "中文", "enabled": True},
        "plain": "x",
    }

    mac_input = (
        '[{"name":"é","value":1}]' + '{"label":"中文","enabled":true}' + "x" + "secret"
    )
    assert (
        client._calculate_mac(data)
        == hashlib.md5(mac_input.encode("utf-8")).hexdigest()
    )


def test_calculate_mac_uses_java_scalar_text_for_bool_and_null():
    client = async_xsense.AsyncXSense()
    client.clientsecret = b"secret"

    data = {"enabled": True, "disabled": False, "missing": None}

    assert (
        client._calculate_mac(data) == hashlib.md5(b"truefalsenullsecret").hexdigest()
    )


def test_calculate_mac_skips_empty_lists_like_apk():
    client = async_xsense.AsyncXSense()
    client.clientsecret = b"secret"

    data = {"empty": [], "plain": "x"}

    assert client._calculate_mac(data) == hashlib.md5(b"xsecret").hexdigest()


def test_calculate_mac_string_led_lists_use_java_scalar_text():
    client = async_xsense.AsyncXSense()
    client.clientsecret = b"secret"

    data = {"values": ["a", True, None], "plain": "z"}

    assert client._calculate_mac(data) == hashlib.md5(b"atruenullzsecret").hexdigest()


@pytest.mark.asyncio
async def test_get_client_info_uses_apk_1360_client_metadata():
    encoded_secret = base64.b64encode(b"1360secretx").decode()
    session = CapturePostSession(
        {
            "reCode": 200,
            "reData": {
                "clientId": "client-id",
                "clientSecret": encoded_secret,
                "cgtRegion": "us-east-1",
                "userPoolId": "pool-id",
            },
        }
    )
    client = async_xsense.AsyncXSense(session)

    await client.get_client_info()

    body = session.posts[0][1]["json"]
    assert body["bizCode"] == "101001"
    assert body["appCode"] == "1360"
    assert body["appVersion"] == "v1.36.0_20260130"
    assert body["clientType"] == "2"
    assert client.clientid == "client-id"
    assert client.clientsecret == b"secret"


@pytest.mark.asyncio
async def test_authenticated_app_call_uses_apk_1360_client_metadata():
    session = CapturePostSession({"reCode": 200, "reData": {"ok": True}})
    client = async_xsense.AsyncXSense(session)
    client.access_token = "access-token"
    client.access_token_expiry = async_xsense.datetime(
        2099, 1, 1, tzinfo=async_xsense.timezone.utc
    )
    client.clientsecret = b"secret"

    await client.api_call("102007", houseId="house-id")

    body = session.posts[0][1]["json"]
    assert body["bizCode"] == "102007"
    assert body["appCode"] == "1360"
    assert body["appVersion"] == "v1.36.0_20260130"
    assert body["clientType"] == "2"
    assert body["houseId"] == "house-id"
    assert session.posts[0][1]["headers"] == {"Authorization": "access-token"}


@pytest.mark.asyncio
async def test_ipc_call_uses_same_apk_1360_client_metadata():
    session = CapturePostSession({"reCode": 200, "reData": {"token": "token"}})
    client = async_xsense.AsyncXSense(session)
    client.access_token = "access-token"
    client.access_token_expiry = async_xsense.datetime(
        2099, 1, 1, tzinfo=async_xsense.timezone.utc
    )
    client.clientsecret = b"secret"

    await client.ipc_call(
        "C10101", userName="user@example.com", nodeType="US", language="en"
    )

    body = session.posts[0][1]["json"]
    assert body["bizCode"] == "C10101"
    assert body["appCode"] == "1360"
    assert body["appVersion"] == "v1.36.0_20260130"
    assert body["clientType"] == "2"
    assert body["userName"] == "user@example.com"
    assert body["nodeType"] == "US"
    assert body["language"] == "en"
    assert session.posts[0][1]["headers"] == {"Authorization": "access-token"}


@pytest.mark.asyncio
async def test_addx_call_rejects_unknown_node_type():
    client = async_xsense.AsyncXSense()
    client._addx_session = {"token": "token", "nodeType": "XX"}

    with pytest.raises(exceptions.APIFailure, match="Unknown ADDX nodeType: XX"):
        await client.addx_call("/device/listuserdevices")


@pytest.mark.asyncio
async def test_register_ipc_uses_mqtt_region_and_app_language_like_apk():
    client = async_xsense.AsyncXSense(language="de-DE")
    client.username = "user@example.com"
    test_house = house.House(None, "house-id", "Home", "Canada", "eu-central-1", "mqtt")
    client.houses = {"house-id": test_house}
    calls = []

    async def ipc_call(code, **kwargs):
        calls.append((code, kwargs))
        return {"token": "token", "nodeType": kwargs["nodeType"]}

    client.ipc_call = ipc_call

    assert await client.register_ipc() == {"token": "token", "nodeType": "EU"}
    assert calls == [
        (
            "C10101",
            {"userName": "user@example.com", "nodeType": "EU", "language": "de"},
        )
    ]


def test_ipc_language_uses_simple_apk_app_language_code():
    assert async_xsense._ipc_language("de-DE") == "de"
    assert async_xsense._ipc_language("pt_BR") == "pt"
    assert async_xsense._ipc_language("") == "en"
    assert async_xsense._ipc_language(None) == "en"


def test_ipc_node_type_uses_apk_mqtt_region_prefix():
    assert async_xsense._ipc_node_type("eu-central-1") == "EU"
    assert async_xsense._ipc_node_type("us-east-1") == "US"
    assert async_xsense._ipc_node_type("cn-north-1") == "CN"
    assert async_xsense._ipc_node_type("Canada") == "US"
    assert async_xsense._ipc_node_type(None) == "US"


@pytest.mark.asyncio
async def test_register_ipc_requires_house_region_instead_of_defaulting_to_us():
    client = async_xsense.AsyncXSense()
    client.houses = {}

    with pytest.raises(
        exceptions.APIFailure, match="Cannot register IPC without an X-Sense house"
    ):
        await client.register_ipc()


@pytest.mark.asyncio
async def test_update_camera_data_keeps_existing_cameras_on_empty_addx_camera_list():
    client = async_xsense.AsyncXSense()
    test_house = house.House(None, "house-id", "Home", "US", "us-east-1", "mqtt")
    test_house.set_stations(
        {
            "stationSort": [],
            "stations": [],
            "cameras": [
                {
                    "ipcId": "stale-cam-id",
                    "ipcSn": "stale-cam-sn",
                    "ipcName": "Stale Camera",
                    "category": "SSC0A",
                }
            ],
        }
    )
    client.houses = {"house-id": test_house}
    calls = []

    async def addx_call(endpoint, **kwargs):
        calls.append((endpoint, kwargs))
        return {"list": []}

    client.addx_call = addx_call

    await client.update_camera_data()

    assert calls == [("/device/listuserdevices", {})]
    assert test_house.get_station_by_sn("stale-cam-sn") is not None


def test_camera_data_normalizes_apk_integer_support_flags():
    data = async_xsense._camera_data(
        {
            "deviceModel": {
                "canStandby": 1,
                "whiteLight": 1,
                "supportMotionTrack": 1,
                "devicePersonDetect": True,
                "canRotate": 1,
            },
            "deviceSupport": {
                "deviceSupportAlarm": 1,
                "supportAlarmVolume": 1,
                "supportChargeAutoPowerOn": 1,
                "supportCryDetect": 1,
                "supportDeviceCall": 1,
                "supportAlarmWhenRemoveToggle": 1,
                "supportLiveAudioToggle": 1,
                "supportMechanicalDingDong": 1,
                "deviceSupportMirrorFlip": 1,
                "supportPirCooldown": 1,
                "supportRecLamp": 1,
                "supportRecordingAudioToggle": 1,
                "deviceDormancySupport": 1,
                "supportLiveSpeakerVolume": 1,
                "supportVoiceVolume": 1,
                "supportWebrtc": 1,
            },
            "antiflickerSupport": 1,
            "sdCard": {"formatStatus": 0},
        }
    )

    for key in (
        "supportAntiFlicker",
        "supportAlarm",
        "supportAlarmVolume",
        "supportBattery",
        "supportChargeAutoPowerOn",
        "supportCryDetect",
        "supportDeviceCall",
        "supportDoorBellAlarm",
        "supportLiveAudio",
        "supportLight",
        "supportMechanicalDingDong",
        "supportMirrorFlip",
        "supportMotionTrack",
        "supportPirCooldown",
        "supportRecLamp",
        "supportRecordingAudio",
        "supportRocker",
        "supportSdCard",
        "supportSleep",
        "supportLiveSpeakerVolume",
        "supportVoiceVolume",
        "supportWebrtc",
    ):
        assert data[key] is True

    assert data["supportPersonDetect"] is True


def test_camera_data_uses_explicit_apk_webrtc_support_flag():
    assert (
        async_xsense._camera_data({"deviceSupport": {"supportWebrtc": 1}})[
            "supportWebrtc"
        ]
        is True
    )
    assert (
        async_xsense._camera_data({"deviceSupport": {"supportWebrtc": 0}})[
            "supportWebrtc"
        ]
        is False
    )
    assert (
        async_xsense._camera_data({"deviceModel": {"streamProtocol": "webrtc"}})[
            "supportWebrtc"
        ]
        is None
    )


def test_camera_config_data_normalizes_boolean_fields():
    data = async_xsense._camera_config_data(
        {
            "antiflickerSwitch": 1,
            "chargeAutoPowerOnSwitch": 0,
            "cooldown": {"deviceSupport": 1, "userEnable": 1},
            "cryDetect": 1,
            "deviceCallToggleOn": 1,
            "devicePersonDetect": 0,
            "mechanicalDingDongSwitch": 1,
            "mirrorFlip": 1,
            "motionTrack": 1,
            "needAlarm": 1,
            "needMotion": 1,
            "needNightVision": 0,
            "needVideo": 1,
            "recLamp": 1,
            "voiceVolumeSwitch": 1,
            "whiteLightScintillation": 1,
        }
    )

    assert data["antiflickerSwitch"] is True
    assert data["chargeAutoPowerOnSwitch"] is False
    assert data["cooldownSupported"] is True
    assert data["cooldownEnabled"] is True
    assert data["devicePersonDetect"] is False
    assert data["needNightVision"] is False


def test_camera_data_requires_apk_sd_card_support_status():
    assert (
        async_xsense._camera_data({"sdCard": {"formatStatus": 0}})["supportSdCard"]
        is True
    )
    assert (
        async_xsense._camera_data({"sdCard": {"formatStatus": 1}})["supportSdCard"]
        is True
    )
    assert (
        async_xsense._camera_data({"sdCard": {"formatStatus": 23}})["supportSdCard"]
        is False
    )
    assert async_xsense._camera_data({})["supportSdCard"] is False


def test_camera_data_requires_apk_sleep_support_code():
    data = async_xsense._camera_data({"deviceSupport": {"deviceDormancySupport": 2}})

    assert data["supportSleep"] is False


@pytest.mark.asyncio
async def test_update_camera_data_reraises_camera_api_errors_for_known_cameras():
    client = async_xsense.AsyncXSense()
    test_house = house.House(None, "house-id", "Home", "US", "us-east-1", "mqtt")
    test_house.set_stations(
        {
            "stationSort": [],
            "stations": [],
            "cameras": [
                {
                    "ipcId": "cam-id",
                    "ipcSn": "cam-sn",
                    "ipcName": "Front Camera",
                    "category": "SSC0A",
                }
            ],
        }
    )
    client.houses = {"house-id": test_house}

    async def addx_call(endpoint, **kwargs):
        raise exceptions.APIFailure(
            "Request for IPC code C10101 failed with error "
            "10000023/500 clientId is incorrect !"
        )

    client.addx_call = addx_call

    with pytest.raises(exceptions.APIFailure):
        await client.update_camera_data()


@pytest.mark.asyncio
async def test_update_camera_data_reraises_real_camera_api_errors():
    client = async_xsense.AsyncXSense()
    test_house = house.House(None, "house-id", "Home", "US", "us-east-1", "mqtt")
    camera_station = station.Station(
        test_house,
        stationId="cam-id",
        stationName="Front Camera",
        stationSn="cam-sn",
        category="SSC0A",
    )
    test_house.stations = {"cam-id": camera_station}
    test_house.station_order = ["cam-id"]
    client.houses = {"house-id": test_house}

    async def addx_call(endpoint, **kwargs):
        raise exceptions.APIFailure("Request failed with error 123/500 server exploded")

    client.addx_call = addx_call

    with pytest.raises(exceptions.APIFailure):
        await client.update_camera_data()

def test_addx_body_uses_apk_app_info():
    """ADDX camera requests use the app info object from the Android SDK."""
    api = async_xsense.AsyncXSense()

    body = api._addx_body(
        {
            "countryNo": "US",
            "language": "en",
            "tenantId": "ignored-session-tenant",
        },
        {"serialNumber": "SSC0A123"},
    )

    assert body == {
        "serialNumber": "SSC0A123",
        "countryNo": "US",
        "language": "en",
        "app": {
            "appName": "VicoHome",
            "appType": "Android",
            "bundle": "com.ai.vicoo",
            "channelId": 1000,
            "countlyId": "b940908f19b8e858",
            "tenantId": "guard",
            "version": 200700500,
            "versionName": "2.7.5",
        },
    }
