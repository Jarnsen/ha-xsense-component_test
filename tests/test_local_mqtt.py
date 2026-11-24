"""APK 1420 local MQTT provisioning contract."""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import aiohttp
import pytest
from homeassistant.exceptions import HomeAssistantError
from test_audit_repairs import make_coordinator, make_station

from custom_components.xsense import coordinator as coordinator_module
from custom_components.xsense.config_flow import XSenseOptionsFlow
from custom_components.xsense.mqtt import XSenseMQTT
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
    client = SimpleNamespace(configure_local_mqtt=AsyncMock())
    station = SimpleNamespace(type="SBS50", sn="s", name="Base")
    coordinator = SimpleNamespace(async_configure_local_mqtt=client.configure_local_mqtt,
                                  data={"stations": {"s": station}, "devices": {}})
    flow = XSenseOptionsFlow(entry)
    flow.hass = SimpleNamespace(data={"xsense": {"local": coordinator}})
    return flow, entry, client, coordinator


@pytest.mark.asyncio
async def test_local_mqtt_form_and_success_do_not_store_credentials():
    flow, entry, client, _ = make_flow()
    form = await flow.async_step_local_mqtt()
    values = form["data_schema"]({"station": "s",
        "host": "192.168.1.2", "port": 1883, "username": "user", "password": "secret"})
    result = await flow.async_step_local_mqtt(values)
    assert result["step_id"] == "local_mqtt_done"
    assert "secret" not in repr(result)
    assert entry.options == {"existing": "kept"}
    assert client.configure_local_mqtt.await_args.kwargs["enabled"] is True
    assert (await flow.async_step_local_mqtt_done({}))["type"] == "abort"


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [XSenseError("secret"), TimeoutError("secret"), aiohttp.ClientError("secret"), HomeAssistantError("secret")])
async def test_local_mqtt_failed_write_stays_in_form_without_secrets(failure):
    flow, entry, client, _ = make_flow()
    client.configure_local_mqtt.side_effect = failure
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
    flow, _, client, _ = make_flow()
    original = flow._local_mqtt_stations()
    flow._local_mqtt_stations = lambda: original
    flow.hass.data["xsense"].clear()
    result = await flow.async_step_local_mqtt({"station": "s", "enabled": True,
        "host": "192.168.1.2", "port": 1883, "username": "user", "password": "secret"})
    assert result["errors"] == {"base": "local_mqtt_failed"}
    client.configure_local_mqtt.assert_not_called()


def make_provisioning_coordinator():
    station = make_station("1234ABCD")
    coordinator = make_coordinator(station)
    coordinator.mqtt_servers[station.house.mqtt_server] = SimpleNamespace(
        connected=True, async_subscribe=AsyncMock(return_value=Mock()),
    )
    coordinator._pending_local_mqtt_reports = {}
    coordinator._async_notify_mqtt_station = Mock()
    return coordinator, station


_BROKER_SETTINGS = {
    "enabled": True, "host": "192.168.1.2", "port": 1883,
    "username": "broker", "password": "test-secret",
}


async def test_local_mqtt_waits_for_matching_station_receipt_and_isolates_reports():
    coordinator, station = make_provisioning_coordinator()
    posted = asyncio.Event()
    async def send(*_args, **_kwargs):
        posted.set()
        return {}
    coordinator.xsense.configure_local_mqtt = AsyncMock(side_effect=send)
    transport = XSenseMQTT(
        SimpleNamespace(loop=asyncio.get_running_loop()),
        SimpleNamespace(title="Local MQTT test"), SimpleNamespace(client=Mock()),
    )
    transport.on_data = coordinator.async_event_received
    pending = asyncio.create_task(coordinator.async_configure_local_mqtt(station, **_BROKER_SETTINGS))
    station.set_data({"alarmStatus": "1"})
    station.has_alarm = True
    initial = station.data.copy()
    topic = f"$aws/things/{station.shadow_name}/shadow/name"
    def report(shadow, *, retain=False, **values):
        transport._async_mqtt_on_message(
            None, None, SimpleNamespace(
                topic=f"{topic}/{shadow}/update",
                payload=json.dumps({"state": {"reported": values}}).encode(), retain=retain,
            ),
        )

    try:
        await asyncio.wait_for(posted.wait(), 1)
        report("2nd_haparamup", retain=True, stationSN=station.sn, haEnable="1")
        await asyncio.sleep(0)
        assert not pending.done()
        for shadow, values in (
            ("2nd_halinkup", {"stationSN": station.sn, "linkStatus": "0"}),
            ("2nd_haparamup", {"stationSN": "other"}),
            ("2nd_haparamup", {"stationSN": station.sn}),
            ("2nd_haparamup", {"stationSN": station.sn, "time": "20200101000000"}),
            ("2nd_haparamup", {"stationSN": station.sn, "haEnable": "0"}),
        ):
            report(shadow, **values)
            await asyncio.sleep(0)
            assert not pending.done()
        report("2nd_haparamup", stationSN=station.sn, haEnable="1",
               time=coordinator.xsense.configure_local_mqtt.await_args.kwargs["request_time"],
               haPassword=_BROKER_SETTINGS["password"])
        await asyncio.wait_for(pending, 1)
        assert station.data == initial
        assert station.has_alarm is True
        coordinator._async_notify_mqtt_station.assert_not_called()
    finally:
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
    assert not coordinator._pending_local_mqtt_reports


@pytest.mark.parametrize("code", [None, 403])
async def test_local_mqtt_cleans_up_timeout_or_rejected_write(monkeypatch, code):
    coordinator, station = make_provisioning_coordinator()
    monkeypatch.setattr(coordinator_module, "_LOCAL_MQTT_CONFIRM_TIMEOUT", 0.02)
    coordinator.xsense.configure_local_mqtt = AsyncMock(return_value={"code": code})
    with pytest.raises(HomeAssistantError, match="did not confirm|rejected"):
        await coordinator.async_configure_local_mqtt(station, **_BROKER_SETTINGS)
    assert not coordinator._pending_local_mqtt_reports


async def test_local_mqtt_offline_does_not_send_unconfirmable_write():
    coordinator, station = make_provisioning_coordinator()
    coordinator.xsense.configure_local_mqtt = AsyncMock()
    coordinator.mqtt_servers.clear()
    with pytest.raises(HomeAssistantError, match="connected X-Sense cloud session"):
        await coordinator.async_configure_local_mqtt(station, **_BROKER_SETTINGS)
    coordinator.xsense.configure_local_mqtt.assert_not_awaited()


async def test_local_mqtt_does_not_write_before_report_subscription_is_ready():
    coordinator, station = make_provisioning_coordinator()
    mqtt = coordinator.mqtt_servers[station.house.mqtt_server]
    mqtt.async_subscribe.side_effect = HomeAssistantError("MQTT SUBACK rejected")
    coordinator.xsense.configure_local_mqtt = AsyncMock()
    with pytest.raises(HomeAssistantError, match="SUBACK rejected"):
        await coordinator.async_configure_local_mqtt(station, **_BROKER_SETTINGS)
    coordinator.xsense.configure_local_mqtt.assert_not_awaited()
    assert not coordinator._pending_local_mqtt_reports
