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
exceptions = load_api_module("exceptions")


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


@pytest.mark.asyncio
async def test_get_state_skips_house_level_wifi_device_shadows():
    client = async_xsense.AsyncXSense()
    station = FakeStation("STH0C")
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
    def __init__(self) -> None:
        self.type = "SBS50"
        self.sn = "station-sn"
        self.shadow_name = "SBS50station-sn"


class FakeXSenseDevice:
    def __init__(self, device_type: str = "XS0B-MR") -> None:
        self.type = device_type
        self.sn = "device-sn"
        self.station = FakeXSenseStation()
        self.data = {}


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
