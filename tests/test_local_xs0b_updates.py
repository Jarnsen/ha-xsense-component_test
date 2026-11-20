"""Regression coverage for the captured SBS50 XS0B-MR state format."""

import asyncio
import shutil
import socket
from types import SimpleNamespace
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.xsense.binary_sensor import (
    SENSORS,
    XSenseBinarySensorEntity,
    _local_xs0b_topic,
)
from custom_components.xsense.entity import XSenseEntity
from custom_components.xsense.python_xsense.device import Device
from custom_components.xsense.python_xsense.station import Station


def detector(station_sn="1234ABCD", child_sn="00000001", model="XS0B-MR"):
    station = Station(None, category="SBS50", stationSn=station_sn)
    return Device(station, deviceType=model, deviceSn=child_sn, deviceId="cloud-id")


@pytest.mark.parametrize(
    ("key", "suffix", "active", "clear"),
    [
        ("alarm_status", "smokealarm", "Detected", "Cleared"),
        ("is_life_end", "lifeend", "EOL", "Normal"),
    ],
)
async def test_live_packets_update_existing_entity(monkeypatch, key, suffix, active, clear):
    from homeassistant.components import mqtt

    device = detector()
    cloud = SimpleNamespace(state=False)
    entity = object.__new__(XSenseBinarySensorEntity)
    entity.hass = SimpleNamespace(config=SimpleNamespace(components={"mqtt"}))
    entity.entity_description = SimpleNamespace(key=key, value_fn=lambda _: cloud.state)
    entity._current_entity = Mock(return_value=device)
    entity._local_state = entity._local_topic = None
    entity.async_write_ha_state = Mock()
    remove = []
    entity.async_on_remove = remove.append
    monkeypatch.setattr(XSenseEntity, "async_added_to_hass", AsyncMock())
    unsubscribe = Mock()
    subscribe = AsyncMock(return_value=unsubscribe)
    connection = Mock(return_value=Mock())
    monkeypatch.setattr(mqtt, "async_subscribe", subscribe)
    monkeypatch.setattr(mqtt, "async_subscribe_connection_status", connection)
    await entity.async_added_to_hass()
    node = "SBS501234ABCD_00000001"
    topic = f"homeassistant/binary_sensor/{node}/{node}_{suffix}/state"
    subscribe.assert_awaited_once_with(entity.hass, topic, entity._local_message, qos=1)
    connection.assert_called_once_with(entity.hass, entity._local_connection)

    def send(status, *, retain=False, received_topic=topic):
        entity._local_message(
            SimpleNamespace(topic=received_topic, retain=retain, payload=status)
        )

    send(f'{{"status":"{active}"}}', retain=True)
    send(f'{{"status":"{active}"}}', received_topic=topic.replace("00000001", "00000002"))
    send(f'{{"status":"{active}"}}', received_topic=topic.replace("1234ABCD", "1234ABCE"))
    send('{"status":"unknown"}')
    send("bad JSON")
    entity.async_write_ha_state.assert_not_called()
    send(f'{{"status":"{active}"}}')
    assert entity.is_on is True
    entity.async_write_ha_state.assert_called_once()
    send(f'{{"status":"{active}"}}')
    entity.async_write_ha_state.assert_called_once()
    cloud.state = True
    send(f'{{"status":"{clear}"}}')
    assert entity.is_on is True
    cloud.state = False
    assert entity.is_on is False
    send(f'{{"status":"{active}"}}')
    entity._local_connection(False)
    assert entity.is_on is False
    remove[0]()
    unsubscribe.assert_called_once()
    send(f'{{"status":"{active}"}}')
    assert entity.is_on is False


def test_topic_does_not_guess_or_subscribe_other_models():
    assert _local_xs0b_topic(detector(model="XS01-WX"), "alarm_status") is None
    assert _local_xs0b_topic(detector(child_sn="1"), "alarm_status") is None
    assert _local_xs0b_topic(detector(station_sn="1234ABC+"), "alarm_status") is None
    assert _local_xs0b_topic(detector(), "battery_end_of_use") is None


@pytest.mark.parametrize("model", ["XS0B-MR", "XS01-M", "XH02-M"])
def test_only_newer_explicit_cloud_clear_recovers_missed_local_clear(monkeypatch, caplog, model):
    device = detector(model=model)
    entity = object.__new__(XSenseBinarySensorEntity)
    entity.entity_description = next(sensor for sensor in SENSORS if sensor.key == "alarm_status")
    entity._current_entity = Mock(return_value=device)
    entity._local_topic = _local_xs0b_topic(device, "alarm_status")
    entity._local_state = None
    entity._local_alarm_at = None
    entity.async_write_ha_state = Mock()
    monkeypatch.setattr(XSenseEntity, "_handle_coordinator_update", Mock())
    caplog.set_level("DEBUG", logger="custom_components.xsense.binary_sensor")

    def report(status):
        device.set_data(status)
        entity._handle_coordinator_update()

    def detect():
        entity._local_message(SimpleNamespace(
            topic=entity._local_topic, retain=False, payload='{"status":"Detected"}',
        ))

    now = datetime.now(UTC).replace(microsecond=0)
    fresh = (now - timedelta(seconds=5)).strftime("%Y%m%d%H%M%S")
    older = (now - timedelta(seconds=20)).strftime("%Y%m%d%H%M%S")
    device.set_data({"status": {"alarmStatus": "0", "time": older}})
    detect()
    entity._local_alarm_at = now - timedelta(seconds=10)
    report({"status": {"alarmStatus": "0", "time": older}})
    assert entity.is_on is True
    report({"status": {"time": fresh}})
    assert entity.is_on is True
    report({"status": {"alarmStatus": "0"}, "time": fresh})
    assert entity.is_on is True
    report({"status": {"alarmStatus": "0", "time": fresh}})
    assert entity.is_on is False
    assert entity._local_alarm_at is None
    detect()
    report({"status": {"alarmStatus": "0", "time": fresh}})
    assert entity.is_on is True
    assert "newer cloud alarm clear" in caplog.text
    assert device.station.sn not in caplog.text
    assert device.sn not in caplog.text


@pytest.mark.parametrize("model", ["XS0B-MR", "XS01-M", "XH02-M"])
async def test_captured_sbs50_topics_through_mosquitto(tmp_path, monkeypatch, model):
    """Use a private broker and HA's actual MQTT subscription path."""
    from homeassistant import auth, config_entries, loader
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers import device_registry, entity_registry
    from homeassistant.setup import async_setup_component

    broker = shutil.which("mosquitto")
    publisher = shutil.which("mosquitto_pub")
    if not broker or not publisher:
        pytest.skip("Mosquitto and mosquitto_pub are required")
    with socket.socket() as sock, socket.socket() as http_sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        http_sock.bind(("127.0.0.1", 0))
        http_port = http_sock.getsockname()[1]
    conf = tmp_path / "broker.conf"
    conf.write_text(f"listener {port} 127.0.0.1\nallow_anonymous true\n")
    (tmp_path / "configuration.yaml").write_text("{}\n")
    process = await asyncio.create_subprocess_exec(
        broker, "-c", str(conf), stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    hass = HomeAssistant(str(tmp_path))
    loader.async_setup(hass)
    hass.config_entries = config_entries.ConfigEntries(hass, {})
    remove = []
    try:
        async with asyncio.timeout(5):
            while True:
                try:
                    _, writer = await asyncio.open_connection("127.0.0.1", port)
                    writer.close()
                    await writer.wait_closed()
                    break
                except ConnectionRefusedError:
                    await asyncio.sleep(0.02)

        await hass.config_entries.async_initialize()
        if hasattr(device_registry, "async_setup"):
            device_registry.async_setup(hass)
        await device_registry.async_load(hass)
        await entity_registry.async_load(hass)
        hass.auth = await auth.auth_manager_from_config(hass, [], [])
        assert await async_setup_component(
            hass, "mqtt", {"http": {"server_host": "127.0.0.1", "server_port": http_port}}
        )
        entry = config_entries.ConfigEntry(
            domain="mqtt", title="Replay broker", source="user",
            version=1, minor_version=1, options={},
            discovery_keys={}, subentries_data=(), unique_id=None,
            data={"broker": "127.0.0.1", "port": port, "protocol": "5",
                  "discovery": False},
        )
        await hass.config_entries.async_add(entry)
        assert entry.state is config_entries.ConfigEntryState.LOADED
        await hass.async_start()
        monkeypatch.setattr(XSenseEntity, "async_added_to_hass", AsyncMock())
        entities = {}
        updates = asyncio.Queue()
        heat = model == "XH02-M"
        station_sn, child_sn = ("15298924", "00000009") if heat else ("163988C7", "00000001")
        alarm_suffix = "heatalarm" if heat else "smokealarm"
        for label, device, key in (
            ("alarm", detector(station_sn, child_sn, model), "alarm_status"),
            ("life", detector(station_sn, child_sn, model), "is_life_end"),
            ("other_child", detector(station_sn, "00000002", model), "alarm_status"),
            ("other_station", detector("163988C8", child_sn, model), "alarm_status"),
            ("camera", detector(station_sn, child_sn, "SSC0A"), "alarm_status"),
            ("combo", detector(station_sn, child_sn, "XP0A-MR"), "alarm_status"),
        ):
            entity = object.__new__(XSenseBinarySensorEntity)
            entity.hass = hass
            device.data["cloud"] = False
            entity.entity_description = SimpleNamespace(
                key=key, value_fn=lambda current: current.data["cloud"]
            )
            entity._current_entity = Mock(return_value=device)
            entity._local_state = entity._local_topic = None
            entity.async_on_remove = remove.append
            entity.async_write_ha_state = (
                lambda name=label, sensor=entity: updates.put_nowait((name, sensor.is_on))
            )
            await entity.async_added_to_hass()
            entities[label] = entity
        assert entities["camera"]._local_topic is None
        assert entities["combo"]._local_topic is None
        if heat:
            assert entities["life"]._local_topic is None
        await hass.async_block_till_done()
        node = f"SBS50{station_sn}_{child_sn}"

        async def publish(suffix, status):
            proc = await asyncio.create_subprocess_exec(
                publisher, "-h", "127.0.0.1", "-p", str(port), "-q", "1",
                "-t", f"homeassistant/binary_sensor/{node}/{node}_{suffix}/state",
                "-m", f'{{"status":"{status}"}}',
            )
            assert await proc.wait() == 0

        # XH02-M topic and state payloads: ioBroker.xsense b65e18d,
        # test/haTopics.test.js. Smoke models use their own alarm topic.
        async with asyncio.timeout(5):
            while updates.empty():
                await publish(alarm_suffix, "Detected")
                await asyncio.sleep(0.1)
        assert updates.get_nowait() == ("alarm", True)
        await publish(alarm_suffix, "Cleared")
        assert await asyncio.wait_for(updates.get(), 5) == ("alarm", False)
        if not heat:
            await publish("lifeend", "EOL")
            assert await asyncio.wait_for(updates.get(), 5) == ("life", True)
            await publish("lifeend", "Normal")
            assert await asyncio.wait_for(updates.get(), 5) == ("life", False)
        for label in ("other_child", "other_station", "camera", "combo"):
            assert entities[label].is_on is False
        assert all(entity._current_entity().data["cloud"] is False for entity in entities.values())
        assert updates.empty()
    finally:
        for unsubscribe in reversed(remove):
            unsubscribe()
        try:
            await hass.async_stop(force=True)
        finally:
            if process.returncode is None:
                process.terminate()
            await process.wait()
