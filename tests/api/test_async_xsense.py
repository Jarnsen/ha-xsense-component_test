import importlib
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
entity_map = load_api_module("entity_map")
exceptions = load_api_module("exceptions")
house = load_api_module("house")
station = load_api_module("station")


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
        ("XC0M-iR", "extendMute", "2nd_appmute", "XC0M-iR-station-sn"),
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

    payload = {"state": {"desired": {"b": 2, "a": 1}}}
    result = await client.do_thing(
        FakeXSenseStation(), "2nd_selftest_device-sn", payload
    )

    assert result == {"ok": True}
    assert len(signed_payloads) == 1
    assert len(session.calls) == 1
    assert session.calls[0]["json"] is None
    assert session.calls[0]["data"] == signed_payloads[0]
    assert session.calls[0]["data"] == async_xsense._shadow_update_body(payload)
    assert session.calls[0]["data"] == '{"state":{"desired":{"b":2,"a":1}}}'


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


@pytest.mark.asyncio
async def test_update_camera_data_creates_cameras_from_addx_device_list():
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
    calls = []

    async def addx_call(endpoint, **kwargs):
        calls.append((endpoint, kwargs))
        if endpoint == "/device/listuserdevices":
            return {
                "list": [
                    {
                        "serialNumber": "cam-sn",
                        "deviceName": "Front Camera",
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

    assert "cam-id" in test_house.stations
    camera = test_house.stations["cam-id"]
    assert async_xsense.is_camera_entity(camera)
    assert camera.name == "Front Camera"
    assert camera.type == "SSC0A"
    assert camera.sn == "cam-sn"
    assert camera.data["batteryLevel"] == 3
    assert camera.data["streamProtocol"] == "webrtc"
    assert ("/device/getuserconfig", {"serialNumber": "cam-sn", "voiceReminder": False}) in calls


@pytest.mark.asyncio
async def test_update_camera_data_skips_ipc_api_when_normal_device_list_has_no_camera():
    client = async_xsense.AsyncXSense()
    test_house = house.House(None, "house-id", "Home", "US", "us-east-1", "mqtt")
    test_house.stations = {}
    test_house.station_order = []
    client.houses = {"house-id": test_house}
    calls = []

    async def addx_call(endpoint, **kwargs):
        calls.append((endpoint, kwargs))
        return {"list": []}

    client.addx_call = addx_call

    await client.update_camera_data()

    assert calls == []
    assert test_house.stations == {}


@pytest.mark.asyncio
async def test_update_camera_data_ignores_accounts_without_camera_ipc_client():
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

    calls = []

    async def addx_call(endpoint, **kwargs):
        calls.append((endpoint, kwargs))
        raise exceptions.APIFailure(
            "Request for IPC code C10101 failed with error "
            "10000023/500 clientId is incorrect !"
        )

    client.addx_call = addx_call

    await client.update_camera_data()

    assert calls == [("/device/listuserdevices", {})]
    assert test_house.stations == {"cam-id": camera_station}


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


class FakeJsonResponse:
    def __init__(self, body, status=200):
        self._body = body
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self):
        return self._body


class FakeApiSession:
    def __init__(self, body):
        self.body = body
        self.calls = []

    def post(self, url, data=None, json=None, headers=None):
        self.calls.append({"url": url, "data": data, "json": json, "headers": headers})
        return FakeJsonResponse(self.body)


@pytest.mark.asyncio
async def test_get_client_info_uses_apk_ipc_client_header():
    client = async_xsense.AsyncXSense()
    session = FakeApiSession(
        {
            "reCode": 200,
            "reData": {
                "clientId": "ipc-client",
                "clientSecret": "MTM2MHNlY3JldHg=",
                "cgtRegion": "us-east-1",
                "userPoolId": "pool",
            },
        }
    )

    async def get_session():
        return session

    client._get_session = get_session

    await client.get_client_info()

    assert client.clientid == "ipc-client"
    assert client.clientsecret == b"secret"
    body = session.calls[0]["json"]
    assert body["bizCode"] == "101001"
    assert body["appCode"] == client.IPC_APPCODE
    assert body["appVersion"] == client.IPC_VERSION
    assert body["clientType"] == client.IPC_CLIENTTYPE
    assert body["mac"] == "d41d8cd98f00b204e9800998ecf8427e"


@pytest.mark.asyncio
async def test_legacy_unauth_api_call_keeps_app_client_header():
    client = async_xsense.AsyncXSense()
    session = FakeApiSession({"reCode": 200, "reData": {"ok": True}})

    async def get_session():
        return session

    client._get_session = get_session

    assert await client.api_call("101001", unauth=True) == {"ok": True}
    body = session.calls[0]["json"]
    assert body["appCode"] == client.APPCODE
    assert body["appVersion"] == client.VERSION
    assert body["clientType"] == client.CLIENTYPE
    assert body["mac"] == "abcdefg"
