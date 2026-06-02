import base64
import hashlib
import importlib
import json
import sys
import types
from pathlib import Path

import pytest


API_PATH = (
    Path(__file__).resolve().parents[2] / "custom_components" / "xsense" / "api"
)


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
    assert device_obj.online is True
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
        stationId='station-id',
        stationName='Station',
        stationSn='station-sn',
        category='SBS50',
        onLine='0',
    )
    device_obj = device_module.Device(
        station_obj,
        deviceId='device-id',
        deviceName='Device',
        deviceSn='device-sn',
        deviceType='SD11-MR',
        online='1',
    )

    assert station_obj.online is False
    assert device_obj.online is True


def test_online_update_accepts_on_line_without_inventing_unknown_values():
    device_obj = entity.Entity()

    device_obj.set_data({'onLine': '0'})
    assert device_obj.online is False

    device_obj.set_data({'onLine': 'unexpected'})
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


def test_parse_get_state_does_not_use_stale_alarm_status_when_missing():
    client = async_xsense.AsyncXSense()
    station_obj = station.Station(
        None,
        stationId='station-id',
        stationName='Station',
        stationSn='station-sn',
        category='SBS50',
    )

    client.parse_get_state(station_obj, {"alarmStatus": "1"})
    assert station_obj.has_alarm is True

    client.parse_get_state(station_obj, {'wifiRSSI': -55})
    assert station_obj.data['alarmStatus'] is True
    assert station_obj.has_alarm is False


def test_parse_get_state_uses_current_activate_without_alarm_status():
    client = async_xsense.AsyncXSense()
    station_obj = station.Station(
        None,
        stationId='station-id',
        stationName='Station',
        stationSn='station-sn',
        category='SBS50',
    )

    client.parse_get_state(station_obj, {'activate': '1'})

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
async def test_get_station_state_falls_back_to_second_info_for_unknown_legacy_types():
    client = async_xsense.AsyncXSense()
    station = FakeStation("XS01-M")
    calls = []

    async def get_thing(station_arg, page):
        calls.append(page)
        if page == "info_station-sn":
            client._lastres = FakeResponse(404, "missing")
            return {"message": "missing"}
        client._lastres = FakeResponse(200)
        return {"state": {"reported": {"rfLevel": 2}}}

    client.get_thing = get_thing

    await client.get_station_state(station)

    assert calls == ["info_station-sn", "2nd_info_station-sn"]
    assert station.data == {"rfLevel": 2}


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
    def __init__(self, station_type: str = "SBS50") -> None:
        self.type = station_type
        self.sn = "station-sn"
        self.shadow_name = "SBS50station-sn" if station_type == "SBS50" else "station-sn"
        self.data = {}


class FakeXSenseDevice:
    def __init__(
        self,
        device_type: str = "XS0B-MR",
        entity_type=entity_map.EntityType.SMOKE,
    ) -> None:
        self.type = device_type
        self.sn = "device-sn"
        self.station = FakeXSenseStation()
        self.data = {}
        self.entity_type = entity_type


@pytest.mark.asyncio
async def test_second_gen_self_test_uses_apk_payload_shape():
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    device = FakeXSenseDevice("XS0B-MR")
    calls = []

    async def do_thing(station, page, data):
        calls.append((station, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.action(device, "test")

    assert len(calls) == 1
    station, page, data = calls[0]
    desired = data["state"]["desired"]
    assert station is device.station
    assert page == "2nd_selftest_device-sn"
    assert desired["shadow"] == "app2ndSelfTest"
    assert desired["stationSN"] == "station-sn"
    assert desired["deviceSN"] == "device-sn"
    assert desired["userId"] == "user-id"
    assert desired["userParam"] == "source=1"
    assert desired["time"].isdigit()
    assert len(desired["time"]) == 13


@pytest.mark.asyncio
async def test_xs01_wx_standalone_self_test_uses_apk_payload_shape():
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    device = FakeXSenseDevice("XS01-WX")
    device.station = FakeXSenseStation("XS01-WX")
    calls = []

    async def do_thing(station, page, data):
        calls.append((station, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.action(device, "test")

    assert len(calls) == 1
    station, page, data = calls[0]
    desired = data["state"]["desired"]
    assert station is device.station
    assert page == "appselftest_device-sn"
    assert desired == {
        "shadow": "appSelfTest",
        "stationSN": "station-sn",
        "deviceSN": "device-sn",
        "userId": "user-id",
    }


@pytest.mark.asyncio
async def test_xs01_wx_sbs50_linked_self_test_uses_apk_payload_shape():
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    device = FakeXSenseDevice("XS01-WX")
    calls = []

    async def do_thing(station, page, data):
        calls.append((station, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.action(device, "test")

    assert len(calls) == 1
    station, page, data = calls[0]
    desired = data["state"]["desired"]
    assert station is device.station
    assert page == "2nd_selftest_device-sn"
    assert desired["shadow"] == "appSelfTest"
    assert desired["stationSN"] == "station-sn"
    assert desired["deviceSN"] == "device-sn"
    assert desired["userId"] == "user-id"
    assert desired["time"].isdigit()
    assert len(desired["time"]) == 13


@pytest.mark.asyncio
async def test_smoke_rf_v9_self_test_uses_apk_device_test_v2_payload_shape():
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    device = FakeXSenseDevice("XS01-M")
    device.data = {"smokeEdition": "9"}
    calls = []

    async def do_thing(station, page, data):
        calls.append((station, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.action(device, "test")

    assert len(calls) == 1
    station, page, data = calls[0]
    desired = data["state"]["desired"]
    assert station is device.station
    assert page == "2nd_selftest_device-sn"
    assert desired["shadow"] == "app2ndSelfTest"
    assert desired["stationSN"] == "station-sn"
    assert desired["deviceSN"] == "device-sn"
    assert desired["userId"] == "user-id"
    assert desired["userParam"] == "source=1"
    assert desired["time"].isdigit()
    assert len(desired["time"]) == 13


@pytest.mark.asyncio
async def test_smoke_rf_older_self_test_keeps_apk_smoke_test_payload_shape():
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    device = FakeXSenseDevice("XS01-M")
    device.data = {"smokeEdition": "8"}
    calls = []

    async def do_thing(station, page, data):
        calls.append((station, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.action(device, "test")

    assert len(calls) == 1
    station, page, data = calls[0]
    desired = data["state"]["desired"]
    assert station is device.station
    assert page == "2nd_selftest_device-sn"
    assert desired["shadow"] == "appSelfTest"
    assert "userParam" not in desired
    assert desired["time"].isdigit()
    assert len(desired["time"]) == 13


@pytest.mark.asyncio
async def test_wifi_device_test_v2_targets_wifi_thing_like_apk():
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    device = FakeXSenseDevice("XP0J-iA", entity_map.EntityType.COMBI)
    calls = []

    async def do_thing(station, page, data):
        calls.append((station, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.action(device, "test")

    assert len(calls) == 1
    station, page, data = calls[0]
    desired = data["state"]["desired"]
    assert station.shadow_name == "XP0J-iA-station-sn"
    assert page == "2nd_selftest_device-sn"
    assert desired["shadow"] == "appSelfTest"
    assert desired["stationSN"] == "station-sn"
    assert desired["deviceSN"] == "device-sn"
    assert desired["userParam"] == "source=1"
    assert desired["time"].isdigit()
    assert len(desired["time"]) == 13


@pytest.mark.asyncio
async def test_sd11_mr_self_test_uses_device_test_v2_payload_shape():
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    device = FakeXSenseDevice("SD11-MR")
    calls = []

    async def do_thing(station, page, data):
        calls.append((station, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.action(device, "test")

    assert len(calls) == 1
    station, page, data = calls[0]
    desired = data["state"]["desired"]
    assert station is device.station
    assert page == "2nd_selftest_device-sn"
    assert desired["shadow"] == "app2ndSelfTest"
    assert desired["stationSN"] == "station-sn"
    assert desired["deviceSN"] == "device-sn"
    assert desired["userId"] == "user-id"
    assert desired["userParam"] == "source=1"
    assert desired["time"].isdigit()
    assert len(desired["time"]) == 13


@pytest.mark.asyncio
async def test_sws0a_self_test_uses_apk_payload_shape():
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    device = FakeXSenseDevice("SWS0A", entity_map.EntityType.WATER)
    calls = []

    async def do_thing(station, page, data):
        calls.append((station, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.action(device, "test")

    assert len(calls) == 1
    station, page, data = calls[0]
    desired = data["state"]["desired"]
    assert station is device.station
    assert page == "2nd_selftest_device-sn"
    assert desired["shadow"] == "waterSelfTest"
    assert desired["stationSN"] == "station-sn"
    assert desired["deviceSN"] == "device-sn"
    assert desired["userId"] == "user-id"
    assert desired["userParam"] == "source=1"
    assert desired["time"].isdigit()
    assert len(desired["time"]) == 13


@pytest.mark.asyncio
async def test_sbs50_accessory_self_test_uses_apk_payload_shape():
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    device = FakeXSenseDevice("SDS0A", entity_map.EntityType.DOOR)
    calls = []

    async def do_thing(station, page, data):
        calls.append((station, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.action(device, "test")

    assert len(calls) == 1
    station, page, data = calls[0]
    desired = data["state"]["desired"]
    assert station is device.station
    assert page == "2nd_selftest_device-sn"
    assert desired["shadow"] == "app2ndSelfTest"
    assert desired["stationSN"] == "station-sn"
    assert desired["deviceSN"] == "device-sn"
    assert desired["userId"] == "user-id"
    assert desired["userParam"] == "source=1"
    assert desired["time"].isdigit()
    assert len(desired["time"]) == 13


@pytest.mark.asyncio
async def test_listener_self_test_uses_apk_payload_shape():
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    device = FakeXSenseDevice("SAL51", entity_map.EntityType.LISTENER)
    calls = []

    async def do_thing(station, page, data):
        calls.append((station, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.action(device, "test")

    assert len(calls) == 1
    station, page, data = calls[0]
    desired = data["state"]["desired"]
    assert station is device.station
    assert page == "2nd_selftest_device-sn"
    assert desired["shadow"] == "listenerSelfTest"
    assert desired["stationSN"] == "station-sn"
    assert desired["deviceSN"] == "device-sn"
    assert desired["userId"] == "user-id"
    assert desired["time"].isdigit()
    assert len(desired["time"]) == 13


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
    device = FakeXSenseDevice("XS01-WX")
    device.station.sn = station_sn
    device.data = {"smokeEdition": smoke_edition}
    calls = []

    async def do_thing(station, page, data):
        calls.append((station, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.action(device, "mute")

    assert len(calls) == 1
    station, page, data = calls[0]
    desired = data["state"]["desired"]
    assert station.shadow_name == expected_thing
    assert page == expected_topic
    assert desired["shadow"] == "appMute"
    assert desired["stationSN"] == station_sn
    assert desired["deviceSN"] == "device-sn"
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
    calls = []

    async def do_thing(station_arg, page, data):
        calls.append((station_arg, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.action(device, "mute")

    assert len(calls) == 1
    station, page, data = calls[0]
    desired = data["state"]["desired"]
    assert station.shadow_name == expected_thing
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
    ("device_type", "expected_shadow"),
    [
        ("SD11-MR", "appMute"),
        ("SD19-MN", "appMute"),
        ("SK0Z-3S", "appMute"),
        ("LP/N-SA-0B", "appMute"),
        ("XP02S-MR", "appMute"),
        ("XS0D-MR", "appMute"),
        ("XC0C-MR", "app2ndMute"),
    ],
)
async def test_sbs50_child_mute_uses_apk_payload_shape(
    device_type, expected_shadow
):
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    device = FakeXSenseDevice(device_type)
    calls = []

    async def do_thing(station, page, data):
        calls.append((station, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.action(device, "mute")

    assert len(calls) == 1
    station, page, data = calls[0]
    desired = data["state"]["desired"]
    assert station is device.station
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
    device = FakeXSenseDevice("XS03-iWX")
    calls = []

    async def do_thing(station, page, data):
        calls.append((station, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.action(device, "mute")

    assert len(calls) == 1
    station, page, data = calls[0]
    desired = data["state"]["desired"]
    assert station.shadow_name == "station-sn"
    assert page == "appmute"
    assert desired["shadow"] == "appMute"
    assert desired["stationSN"] == "station-sn"
    assert desired["deviceSN"] == "device-sn"
    assert desired["userId"] == "user-id"
    assert desired["muteType"] == "1"
    assert desired["time"].isdigit()
    assert len(desired["time"]) == 14


@pytest.mark.asyncio
@pytest.mark.parametrize("device_type", ["XP0J-iA", "XS0R-iA"])
async def test_wifi_fire_drill_targets_apk_wifi_thing_name(device_type):
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    device = FakeXSenseDevice(device_type, entity_map.EntityType.COMBI)
    calls = []

    async def do_thing(station, page, data):
        calls.append((station, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.action(device, "firedrill")

    assert len(calls) == 1
    station, page, data = calls[0]
    desired = data["state"]["desired"]
    assert station.shadow_name == f"{device_type}-station-sn"
    assert page == "2nd_firedrill"
    assert desired["stationSN"] == "station-sn"
    assert desired["deviceSN"] == "station-sn"


@pytest.mark.asyncio
async def test_fire_drill_keeps_datetime_payload_shape():
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    device = FakeXSenseDevice("XS0B-MR")
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
        FakeXSenseStation(), "2nd_selftest_device-sn", payload
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
            FakeXSenseStation(),
            "2nd_selftest_device-sn",
            {"state": {"desired": {"a": 1}}},
        )


@pytest.mark.asyncio
async def test_sbs50_station_voice_volume_uses_station_config_shadow():
    client = async_xsense.AsyncXSense()
    station = FakeXSenseStation("SBS50")
    calls = []

    async def do_thing(station_arg, page, data):
        calls.append((station_arg, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.update_shadow_volume(station, "voiceVol", 35)

    assert len(calls) == 1
    station_arg, page, data = calls[0]
    desired = data["state"]["desired"]
    assert station_arg is station
    assert page == "2nd_cfg_station-sn"
    assert desired == {
        "shadow": "infoBase",
        "stationSN": "station-sn",
        "voiceVol": "35",
    }


@pytest.mark.asyncio
async def test_sbs50_child_alarm_volume_uses_device_config_shadow():
    client = async_xsense.AsyncXSense()
    device = FakeXSenseDevice("XS0B-MR")
    device.data = {"alarmTone": "2"}
    calls = []

    async def do_thing(station_arg, page, data):
        calls.append((station_arg, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.update_shadow_volume(device, "alarmVol", 65)

    assert len(calls) == 1
    station_arg, page, data = calls[0]
    desired = data["state"]["desired"]
    assert station_arg is device.station
    assert page == "2nd_cfg_device-sn"
    assert desired == {
        "shadow": "infoDev",
        "stationSN": "station-sn",
        "alarmVol": "65",
        "deviceSN": "device-sn",
        "alarmTone": "2",
    }


@pytest.mark.asyncio
async def test_sbs10_station_alarm_volume_keeps_companion_voice_value():
    client = async_xsense.AsyncXSense()
    station = FakeXSenseStation("SBS10")
    station.data = {"voiceVol": 45, "alarmTone": "3"}
    calls = []

    async def do_thing(station_arg, page, data):
        calls.append((station_arg, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.update_shadow_volume(station, "alarmVol", 55)

    assert len(calls) == 1
    station_arg, page, data = calls[0]
    desired = data["state"]["desired"]
    assert station_arg is station
    assert page == "info_station-sn"
    assert desired == {
        "shadow": "infoBase",
        "stationSN": "station-sn",
        "alarmVol": "55",
        "voiceVol": "45",
        "alarmTone": "3",
    }


@pytest.mark.asyncio
async def test_light_power_uses_lamp_power_payload_shape():
    client = async_xsense.AsyncXSense()
    client.userid = "user-id"
    device = FakeXSenseDevice("SSL51", entity_map.EntityType.LIGHT)
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
async def test_sbs50_child_chirp_volume_uses_device_info_payload_without_station_sn():
    client = async_xsense.AsyncXSense()
    device = FakeXSenseDevice("SDS0A")
    device.data = {"chirpTone": "3"}
    calls = []

    async def do_thing(station_arg, page, data):
        calls.append((station_arg, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.update_shadow_volume(device, "chirpVol", 40)

    assert len(calls) == 1
    station_arg, page, data = calls[0]
    desired = data["state"]["desired"]
    assert station_arg is device.station
    assert page == "2nd_cfg_device-sn"
    assert desired == {
        "shadow": "infoDev",
        "chirpVol": "40",
        "deviceSN": "device-sn",
        "chirpTone": "3",
    }


@pytest.mark.asyncio
async def test_sbs50_child_reminder_volume_preserves_reminder_tone():
    client = async_xsense.AsyncXSense()
    device = FakeXSenseDevice("SDS0A")
    device.data = {"remindTone": "2"}
    calls = []

    async def do_thing(station_arg, page, data):
        calls.append((station_arg, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.update_shadow_volume(device, "remindVol", 30)

    assert len(calls) == 1
    station_arg, page, data = calls[0]
    desired = data["state"]["desired"]
    assert station_arg is device.station
    assert page == "2nd_cfg_device-sn"
    assert desired == {
        "shadow": "infoDev",
        "remindVol": "30",
        "deviceSN": "device-sn",
        "remindTone": "2",
    }


@pytest.mark.asyncio
async def test_light_alarm_volume_uses_light_info_payload_without_station_sn():
    client = async_xsense.AsyncXSense()
    device = FakeXSenseDevice("CB0Z-3S", entity_map.EntityType.LIGHT)
    device.data = {"alarmTone": "1"}
    calls = []

    async def do_thing(station_arg, page, data):
        calls.append((station_arg, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.update_shadow_volume(device, "alarmVol", 70)

    assert len(calls) == 1
    station_arg, page, data = calls[0]
    desired = data["state"]["desired"]
    assert station_arg is device.station
    assert page == "2nd_cfg_device-sn"
    assert desired == {
        "shadow": "infoDev",
        "alarmVol": "70",
        "deviceSN": "device-sn",
        "alarmTone": "1",
    }



@pytest.mark.asyncio
async def test_co_alarm_volume_uses_co_info_payload_without_station_sn():
    client = async_xsense.AsyncXSense()
    device = FakeXSenseDevice("XC0C-MR", entity_map.EntityType.CO)
    device.data = {"alarmTone": "3"}
    calls = []

    async def do_thing(station_arg, page, data):
        calls.append((station_arg, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.update_shadow_volume(device, "alarmVol", 80)

    assert len(calls) == 1
    station_arg, page, data = calls[0]
    desired = data["state"]["desired"]
    assert station_arg is device.station
    assert page == "2nd_cfg_device-sn"
    assert desired == {
        "shadow": "infoDev",
        "alarmVol": "80",
        "deviceSN": "device-sn",
        "alarmTone": "3",
    }


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


@pytest.mark.asyncio
async def test_temperature_alarm_volume_uses_temp_info_payload_without_station_sn():
    client = async_xsense.AsyncXSense()
    device = FakeXSenseDevice("STH0B", entity_map.EntityType.TEMPERATURE)
    device.data = {"alarmTone": "2"}
    calls = []

    async def do_thing(station_arg, page, data):
        calls.append((station_arg, page, data))
        return {"ok": True}

    client.do_thing = do_thing

    await client.update_shadow_volume(device, "alarmVol", 60)

    assert len(calls) == 1
    station_arg, page, data = calls[0]
    desired = data["state"]["desired"]
    assert station_arg is device.station
    assert page == "2nd_cfg_device-sn"
    assert desired == {
        "shadow": "infoDev",
        "alarmVol": "60",
        "deviceSN": "device-sn",
        "alarmTone": "2",
    }


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
    assert not async_xsense.is_camera_entity(camera)


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
    assert ("/device/getuserconfig", {"serialNumber": "cam-sn", "voiceReminder": False}) in calls


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("camera_data", "expected"),
    [
        ({"liveResolution": "VIDEO_SIZE_1920x1080"}, "1920x1080"),
        ({"liveResolution": "HD"}, "1920x1080"),
        ({"supportedRecordingResolutions": ["P1296", "P1080"]}, "2304x1296"),
        ({"supportedRecordingResolutions": []}, "auto"),
    ],
)
async def test_start_camera_live_uses_apk_live_resolution_fallback(
    camera_data, expected
):
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

    mac_input = "[{\"name\":\"é\",\"value\":1}]" + "{\"label\":\"中文\",\"enabled\":true}" + "x" + "secret"
    assert client._calculate_mac(data) == hashlib.md5(
        mac_input.encode("utf-8")
    ).hexdigest()


def test_calculate_mac_uses_java_scalar_text_for_bool_and_null():
    client = async_xsense.AsyncXSense()
    client.clientsecret = b"secret"

    data = {"enabled": True, "disabled": False, "missing": None}

    assert client._calculate_mac(data) == hashlib.md5(
        b"truefalsenullsecret"
    ).hexdigest()


def test_calculate_mac_skips_empty_lists_like_apk():
    client = async_xsense.AsyncXSense()
    client.clientsecret = b"secret"

    data = {"empty": [], "plain": "x"}

    assert client._calculate_mac(data) == hashlib.md5(b"xsecret").hexdigest()


def test_calculate_mac_string_led_lists_use_java_scalar_text():
    client = async_xsense.AsyncXSense()
    client.clientsecret = b"secret"

    data = {"values": ["a", True, None], "plain": "z"}

    assert client._calculate_mac(data) == hashlib.md5(
        b"atruenullzsecret"
    ).hexdigest()


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
async def test_register_ipc_uses_mqtt_region_for_node_type_like_apk():
    client = async_xsense.AsyncXSense()
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
            {"userName": "user@example.com", "nodeType": "EU", "language": "en"},
        )
    ]


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
async def test_update_camera_data_skips_addx_when_normal_device_list_has_no_camera():
    client = async_xsense.AsyncXSense()
    test_house = house.House(None, "house-id", "Home", "US", "us-east-1", "mqtt")
    test_house.set_stations({"stationSort": [], "stations": [], "cameras": []})
    client.houses = {"house-id": test_house}

    async def addx_call(endpoint, **kwargs):
        raise AssertionError("ADDX should not be queried without APK camera entries")

    client.addx_call = addx_call

    await client.update_camera_data()

    assert test_house.stations == {}


def test_camera_data_normalizes_apk_integer_support_flags():
    data = async_xsense._camera_data(
        {
            "deviceModel": {
                "canStandby": 1,
                "whiteLight": 1,
                "supportMotionTrack": 1,
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


def test_camera_user_config_payload_sends_only_changed_cloud_fields_like_apk():
    camera = device_module.Device(
        None,
        deviceId="cam-id",
        deviceName="Camera",
        deviceSn="cam-sn",
        deviceType="SSC0A",
    )
    camera.set_data(
        {
            "needMotion": True,
            "deviceCallToggleOn": True,
            "deviceSupportLanguage": ["en"],
            "supportDeviceCall": True,
        }
    )

    payload = async_xsense._camera_user_config_payload(
        camera, {"needVideo": 1, "supportDeviceCall": False}
    )

    assert payload == {"serialNumber": "cam-sn", "needVideo": 1}


def test_camera_user_config_payload_adds_apk_toggle_companions():
    camera = device_module.Device(
        None,
        deviceId="cam-id",
        deviceName="Camera",
        deviceSn="cam-sn",
        deviceType="SSC0A",
    )
    camera.set_data(
        {
            "alarmSeconds": 20,
            "motionSensitivity": None,
            "nightThresholdLevel": 3,
            "supportRocker": False,
            "videoSeconds": 0,
        }
    )

    assert async_xsense._camera_user_config_payload(camera, {"needMotion": 1}) == {
        "serialNumber": "cam-sn",
        "needMotion": 1,
        "motionSensitivity": 1,
    }
    assert async_xsense._camera_user_config_payload(camera, {"needVideo": 1}) == {
        "serialNumber": "cam-sn",
        "needVideo": 1,
        "videoSeconds": -1,
    }
    assert async_xsense._camera_user_config_payload(camera, {"needAlarm": 1}) == {
        "serialNumber": "cam-sn",
        "needAlarm": 1,
        "alarmSeconds": 20,
    }
    assert async_xsense._camera_user_config_payload(
        camera, {"needNightVision": 1}
    ) == {
        "serialNumber": "cam-sn",
        "needNightVision": 1,
        "nightThresholdLevel": 3,
    }


def test_camera_user_config_payload_uses_apk_rocker_alarm_seconds():
    camera = device_module.Device(
        None,
        deviceId="cam-id",
        deviceName="Camera",
        deviceSn="cam-sn",
        deviceType="SSC0A",
    )
    camera.set_data({"alarmSeconds": 20, "supportRocker": True})

    assert async_xsense._camera_user_config_payload(camera, {"needAlarm": 1}) == {
        "serialNumber": "cam-sn",
        "needAlarm": 1,
        "alarmSeconds": 10,
    }


def test_camera_config_write_value_uses_apk_field_types():
    assert async_xsense._camera_config_write_value("deviceCallToggleOn", True) is True
    assert async_xsense._camera_config_write_value("deviceCallToggleOn", False) is False
    assert async_xsense._camera_config_write_value("needMotion", True) == 1
    assert async_xsense._camera_config_write_value("needMotion", False) == 0
    assert async_xsense._camera_config_payload_value("needMotion", True) == 1
    assert async_xsense._camera_config_payload_value("needMotion", False) == 0
    assert async_xsense._camera_config_payload_value("deviceCallToggleOn", 1) is True

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
    assert async_xsense._camera_data({"sdCard": {"formatStatus": 0}})["supportSdCard"] is True
    assert async_xsense._camera_data({"sdCard": {"formatStatus": 1}})["supportSdCard"] is False
    assert async_xsense._camera_data({"sdCard": {"formatStatus": 23}})["supportSdCard"] is False
    assert async_xsense._camera_data({})["supportSdCard"] is False

def test_camera_data_requires_apk_sleep_support_code():
    data = async_xsense._camera_data(
        {"deviceSupport": {"deviceDormancySupport": 2}}
    )

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
