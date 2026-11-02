"""APK 1420 local MQTT provisioning contract."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import aiohttp
import pytest

from custom_components.xsense.config_flow import XSenseOptionsFlow
from custom_components.xsense.python_xsense import AsyncXSense
from custom_components.xsense.python_xsense.exceptions import XSenseError


@pytest.mark.asyncio
async def test_local_mqtt_apk_payload():
    client = AsyncXSense.__new__(AsyncXSense)
    client.user_id_code = "account-code"
    client.do_thing = AsyncMock()
    station = SimpleNamespace(type="SBS50", sn="station")
    await client.configure_local_mqtt(
        station, enabled=True, host="192.168.1.10", port=1883,
        username="broker-user", password="secret",
    )
    target, topic, body = client.do_thing.call_args.args
    assert target is station
    assert topic == "2nd_haparam"
    desired = body["state"]["desired"]
    assert desired == {
        "shadow": "appHaParam", "stationSN": "station", "deviceSN": "station",
        "userId": "account-code", "userParam": "source=1", "haEnable": "1",
        "haIp": "192.168.1.10", "haMqttPort": "1883",
        "haUserName": "broker-user", "haPassword": "secret", "time": desired["time"],
    }
    assert len(desired["time"]) == 14


@pytest.mark.asyncio
async def test_local_mqtt_distinct_readback_shadows():
    client = AsyncXSense.__new__(AsyncXSense)
    client.get_thing = AsyncMock()
    station = SimpleNamespace(type="SBS50")
    await client.get_local_mqtt_settings(station)
    client.get_thing.assert_awaited_with(station, "2nd_haparamup")
    await client.get_local_mqtt_status(station)
    client.get_thing.assert_awaited_with(station, "2nd_halinkup")


@pytest.mark.asyncio
@pytest.mark.parametrize("changes", [
    {"enabled": "1"}, {"host": "broker.local"}, {"host": "::1"}, {"host": 123},
    {"port": 0}, {"port": 65536}, {"port": True},
    {"username": None}, {"password": None},
])
async def test_local_mqtt_invalid_input_never_writes(changes):
    client = AsyncXSense.__new__(AsyncXSense)
    client.user_id_code = "account-code"
    client.do_thing = AsyncMock()
    values = {"enabled": True, "host": "192.168.1.10", "port": 1883,
              "username": "user", "password": "secret"}
    values.update(changes)
    with pytest.raises(XSenseError):
        await client.configure_local_mqtt(SimpleNamespace(type="SBS50", sn="s"), **values)
    client.do_thing.assert_not_called()


@pytest.mark.asyncio
async def test_local_mqtt_other_models_rejected():
    client = AsyncXSense.__new__(AsyncXSense)
    client.get_thing = AsyncMock()
    client.do_thing = AsyncMock()
    station = SimpleNamespace(type="SSC0A", sn="camera")
    with pytest.raises(XSenseError):
        await client.get_local_mqtt_settings(station)
    with pytest.raises(XSenseError):
        await client.get_local_mqtt_status(station)
    with pytest.raises(XSenseError):
        await client.configure_local_mqtt(station, enabled=True, host="192.168.1.2",
                                         port=1883, username="u", password="p")
    client.get_thing.assert_not_called()
    client.do_thing.assert_not_called()


def make_flow():
    entry = SimpleNamespace(entry_id="local", options={"existing": "kept"})
    client = SimpleNamespace(configure_local_mqtt=AsyncMock(return_value={}))
    station = SimpleNamespace(type="SBS50", sn="s", name="Base")
    coordinator = SimpleNamespace(xsense=client, data={"stations": {"s": station}, "devices": {}})
    flow = XSenseOptionsFlow(entry)
    flow.hass = SimpleNamespace(data={"xsense": {"local": coordinator}})
    return flow, entry, client, coordinator


@pytest.mark.asyncio
async def test_local_mqtt_form_and_success_do_not_store_credentials():
    flow, entry, client, _ = make_flow()
    form = await flow.async_step_local_mqtt()
    values = form["data_schema"]({"station": "s", "enabled": False,
        "host": "192.168.1.2", "port": 1883, "username": "user", "password": "secret"})
    result = await flow.async_step_local_mqtt(values)
    assert result["step_id"] == "local_mqtt_done"
    assert "secret" not in repr(result)
    assert entry.options == {"existing": "kept"}
    assert client.configure_local_mqtt.await_args.kwargs["enabled"] is False
    assert (await flow.async_step_local_mqtt_done({}))["type"] == "abort"


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [XSenseError("secret"), TimeoutError("secret"), aiohttp.ClientError("secret"), {"code": 403}])
async def test_local_mqtt_failed_write_stays_in_form_without_secrets(failure):
    flow, entry, client, _ = make_flow()
    if isinstance(failure, Exception):
        client.configure_local_mqtt.side_effect = failure
    else:
        client.configure_local_mqtt.return_value = failure
    result = await flow.async_step_local_mqtt({"station": "s", "enabled": True,
        "host": "192.168.1.2", "port": 1883, "username": "user", "password": "secret"})
    assert result["errors"] == {"base": "local_mqtt_failed"}
    assert "secret" not in repr(result)
    assert entry.options == {"existing": "kept"}


@pytest.mark.asyncio
async def test_local_mqtt_removed_station_does_not_write():
    flow, _, client, _ = make_flow()
    result = await flow.async_step_local_mqtt({"station": "removed"})
    assert result["errors"] == {"station": "local_mqtt_failed"}
    client.configure_local_mqtt.assert_not_called()


@pytest.mark.asyncio
async def test_local_mqtt_menu_preserves_recording_options():
    flow, _, _, coordinator = make_flow()
    coordinator.data["devices"]["camera"] = SimpleNamespace(type="SSC0A")
    menu = await flow.async_step_init()
    assert menu["menu_options"] == ["recordings", "local_mqtt"]
    assert (await flow.async_step_recordings())["step_id"] == "init"


@pytest.mark.asyncio
async def test_local_mqtt_missing_inventory_aborts():
    flow, _, _, coordinator = make_flow()
    coordinator.data["stations"].clear()
    assert (await flow.async_step_local_mqtt())["reason"] == "no_options"


@pytest.mark.asyncio
async def test_local_mqtt_old_firmware_never_writes():
    client = AsyncXSense.__new__(AsyncXSense)
    client.do_thing = AsyncMock()
    with pytest.raises(XSenseError, match="firmware"):
        await client.configure_local_mqtt(
            SimpleNamespace(type="SBS50", data={"sw": "v1.6.9"}),
            enabled=True, host="192.168.1.2", port=1883, username="u", password="p",
        )
    client.do_thing.assert_not_called()


@pytest.mark.asyncio
async def test_local_mqtt_requires_account_identity():
    client = AsyncXSense.__new__(AsyncXSense)
    client.user_id_code = None
    client.do_thing = AsyncMock()
    with pytest.raises(XSenseError, match="user ID"):
        await client.configure_local_mqtt(
            SimpleNamespace(type="SBS50", sn="s"), enabled=True,
            host="192.168.1.2", port=1883, username="u", password="p",
        )
    client.do_thing.assert_not_called()


@pytest.mark.asyncio
async def test_local_mqtt_reload_during_configuration_returns_form():
    flow, _, client, coordinator = make_flow()
    coordinator.xsense = None
    result = await flow.async_step_local_mqtt({"station": "s", "enabled": True,
        "host": "192.168.1.2", "port": 1883, "username": "user", "password": "secret"})
    assert result["errors"] == {"base": "local_mqtt_failed"}
    client.configure_local_mqtt.assert_not_called()
