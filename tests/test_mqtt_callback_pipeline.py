"""Replay real Paho packets through routing, discovery and native HA states."""

import asyncio
import json
import logging
import socket
import ssl
import struct
import subprocess
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, Mock, PropertyMock, patch

import paho.mqtt.client as paho
import pytest
from homeassistant import loader
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry, entity_registry
from homeassistant.helpers.entity import Entity as HAEntity
from homeassistant.helpers.entity_component import EntityComponent
from test_audit_repairs import make_coordinator, make_station

from custom_components.xsense import (
    binary_sensor,
    button,
    number,
    select,
    sensor,
    switch,
)
from custom_components.xsense.entity import XSenseEntity, _serial_identity
from custom_components.xsense.mqtt import XSenseMQTT
from custom_components.xsense.python_xsense.async_xsense import AsyncXSense


def publish_packet(topic, report):
    payload = struct.pack("!H", len(topic)) + topic.encode() + json.dumps(report).encode()
    size = len(payload)
    header = bytearray([0x30])
    while size:
        digit = size % 128
        size //= 128
        header.append(digit | (128 if size else 0))
    return bytes(header) + payload


@pytest.mark.asyncio
@pytest.mark.parametrize("websocket", [False, True, "tls"])
@pytest.mark.parametrize("rollover", [False, True])
@pytest.mark.parametrize("report_shape", ["wrapped", "direct", "top_level", "nested_list", "reported_list"])
@pytest.mark.parametrize("inventory", ["leak_sensors", "issue_447"])
async def test_socket_callback_preserves_alarm_transitions_without_reconstruction(
    tmp_path, monkeypatch, websocket, rollover, report_shape, inventory
):
    hass = HomeAssistant(str(tmp_path))
    loader.async_setup(hass)
    hass.config_entries = NS(async_wait_initialized=AsyncMock())
    # Newer HA initializes the device registry explicitly; older HA creates it lazily.
    if hasattr(device_registry, "async_setup"):
        device_registry.async_setup(hass)
    await device_registry.async_load(hass)
    await entity_registry.async_load(hass)
    station = make_station()
    models = (
        ["XP0A-MR", *(["STH51"] * 6), *(["SMS0A"] * 5), *(["SDS0A"] * 9), "SKP0A"]
        if inventory == "issue_447" else ["SWS51"] * 40
    )
    station.set_devices({"devices": [
        {"deviceId": str(i), "deviceSn": str(i), "deviceType": model,
         "deviceName": f"Leak {i}", "roomName": "Room"}
        for i, model in enumerate(models)
    ]})
    station._set_online(True)
    for device in station.devices.values():
        device._set_online(True)
        device.set_data({"batInfo": 3, "rfLevel": 3, "alarmStatus": "0", "muteStatus": "0", "alarmVol": 75, "alarmTone": 1, "ledLight": 1, "alarmEnabled": "1"})
    coordinator = make_coordinator(station)
    coordinator.xsense.has_action = AsyncXSense().has_action
    coordinator.hass = hass
    coordinator.data["devices"] = dict(station.devices)
    callbacks = []

    def listen(callback, *_args):
        callbacks.append(callback)
        return lambda: callbacks.remove(callback)

    coordinator.async_add_listener = listen
    coordinator.async_update_listeners = lambda: [callback() for callback in tuple(callbacks)]
    hass.data["xsense"] = {"audit": coordinator}
    pending, entities = [], []
    entry = NS(entry_id="audit", async_on_unload=lambda _: None)

    def add(component, batch):
        entities.extend(batch)
        pending.append(component.async_add_entities(batch))

    for domain, platform in (("binary_sensor", binary_sensor), ("sensor", sensor), ("button", button), ("number", number), ("select", select), ("switch", switch)):
        component = EntityComponent(logging.getLogger(domain), domain, hass)
        await platform.async_setup_entry(
            hass, entry, lambda batch, component=component: add(component, batch)
        )
    # Registry attachment is a setup concern, not part of MQTT state serialization.
    with patch.object(XSenseEntity, "device_info", new_callable=PropertyMock, return_value=None):
        await asyncio.gather(*pending)
    assert len(hass.states.async_all()) == len(entities)
    if rollover:
        station.set_devices({"devices": [
            {"deviceId": f"new-{i}", "deviceSn": str(i), "deviceType": model,
             "deviceName": f"Leak {i}", "roomName": "Room"}
            for i, model in enumerate(models)
        ]})
        for device in station.devices.values():
            device._set_online(True)
            device.set_data({"batInfo": 3, "rfLevel": 3, "alarmStatus": "0", "muteStatus": "0"})
        coordinator.data["devices"] = dict(station.devices)
    spies = []
    for platform, name in (
        (binary_sensor, "XSenseBinarySensorEntity"),
        (binary_sensor, "XSenseMQTTConnectedEntity"),
        (sensor, "XSenseSensorEntity"),
        (button, "XSenseButtonEntity"),
        (number, "XSenseNumberEntity"),
        (select, "XSenseSelectEntity"),
        (switch, "XSenseSwitchEntity"),
    ):
        spy = Mock(wraps=getattr(platform, name))
        monkeypatch.setattr(platform, name, spy)
        spies.append(spy)
    alarm = next(item for item in entities if item.unique_id == "0-alarm-status")
    sibling = next(item for item in entities if item.unique_id == "1-alarm-status")
    writes = []
    original_write = HAEntity.async_write_ha_state

    def record_write(item):
        writes.append(item.entity_id)
        original_write(item)

    monkeypatch.setattr(HAEntity, "async_write_ha_state", record_write)
    coordinator._mqtt_child_write_scope = frozenset({_serial_identity(station.devices["new-1" if rollover else "1"])})
    alarm.async_write_ha_state()
    assert alarm.entity_id in writes
    coordinator._mqtt_child_write_scope = None
    mqtt = XSenseMQTT(hass, NS(title="Offline test"), NS(client=paho.Client(paho.CallbackAPIVersion.VERSION2)))
    mqtt.init_client()
    mqtt.on_data = coordinator.async_event_received
    left, right = socket.socketpair()
    if websocket == "tls":
        cert = tmp_path / "loopback.pem"
        key = tmp_path / "loopback.key"
        await asyncio.to_thread(
            subprocess.run,
            ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
             "-subj", "/CN=localhost", "-keyout", str(key), "-out", str(cert)],
            check=True, capture_output=True, timeout=10,
        )
        server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server_context.load_cert_chain(cert, key)
        client_context = ssl.create_default_context(cafile=str(cert))
        left.settimeout(5)
        right.settimeout(5)
        left, right = await asyncio.gather(
            asyncio.to_thread(client_context.wrap_socket, left, server_hostname="localhost"),
            asyncio.to_thread(server_context.wrap_socket, right, server_side=True),
        )
    left.setblocking(False)
    mqtt._mqttc._sock = left
    if websocket:
        # Exercise the actual frame decoder without a remote HTTP handshake.
        with patch.object(paho._WebsocketWrapper, "_do_handshake"):
            mqtt._mqttc._sock = paho._WebsocketWrapper(left, "offline", 443, websocket == "tls", "/mqtt", None)
    topic = f"$aws/things/{station.shadow_name}/shadow/name/2nd_mainpage/update"

    def packet_for(value, extra=None):
        fields = {
            "stationSN": station.sn, "devs": {"0": {"alarmStatus": value}}, **(extra or {})
        }
        if extra is None:
            rows = [{"_deviceSN": "0", "alarmStatus": value}]
            fields = {
                "wrapped": {**fields, "wifiRSSI": -47 if value == "1" else -52},
                "direct": {"stationSN": station.sn, "_deviceSN": "0", "alarmStatus": value},
                "top_level": {"stationSN": station.sn, "0": {"alarmStatus": value}},
                "nested_list": {"stationSN": station.sn, "devs": rows},
                "reported_list": rows,
            }[report_shape]
        packet = publish_packet(topic, {"state": {"reported": fields}})
        if websocket:
            length = len(packet)
            frame_header = bytes([0x82, length]) if length < 126 else b"\x82\x7e" + struct.pack("!H", length)
            packet = frame_header + packet
        return packet

    try:
        for value, expected in (("1", "on"), ("0", "off"), ("1", "on")):
            packet = packet_for(value)
            # A fragmented MQTT packet must not deliver a partial state update.
            before = hass.states.get(alarm.entity_id).state
            right.sendall(packet[:4])
            mqtt._async_reader_callback(mqtt._mqttc)
            assert hass.states.get(alarm.entity_id).state == before
            right.sendall(packet[4:])
            writes.clear()
            mqtt._async_reader_callback(mqtt._mqttc)
            await asyncio.sleep(0)
            assert hass.states.get(alarm.entity_id).state == expected
            assert alarm.entity_id in writes
            assert sibling.entity_id not in writes
            if report_shape == "wrapped":
                rssi = next(item for item in entities if item.unique_id == "station-wifi-rssi")
                assert rssi.entity_id in writes
                assert hass.states.get(rssi.entity_id).state == ("-47" if value == "1" else "-52")
            work = coordinator._mqtt_slowest_dispatch_work
            assert work["entity_write_calls"] > 0
            assert work["discovery_calls"] == 6
            sibling_controls = [item for item in entities if item.unique_id.startswith("1-") and item.entity_id.split(".")[0] in {"button", "number", "select", "switch"}]
            assert sibling_controls
            assert all(item.entity_id not in writes for item in sibling_controls)
            for item in sibling_controls:
                item.async_write_ha_state()
                assert item.entity_id in writes
        if websocket == "tls" and report_shape == "wrapped":
            rssi_values = []

            def receive_rssi(topic, payload):
                coordinator.async_event_received(topic, payload)
                rssi_values.append(hass.states.get(rssi.entity_id).state)

            mqtt.on_data = receive_rssi
            right.sendall(packet_for("0") + packet_for("1"))
            mqtt._async_reader_callback(mqtt._mqttc)
            assert left.pending() > 0
            for _ in range(4):
                await asyncio.sleep(0)
            assert rssi_values == ["-52", "-47"]
            assert left.pending() == 0
            ignored = publish_packet(f"{topic}/accepted", {})
            assert len(ignored) < 126
            ignored_frame = bytes([0x82, len(ignored)]) + ignored
            right.sendall(ignored_frame + packet_for("0"))
            mqtt._async_reader_callback(mqtt._mqttc)
            assert left.pending() > 0
            for _ in range(4):
                await asyncio.sleep(0)
            assert rssi_values == ["-52", "-47", "-52"]
            assert left.pending() == 0
        delivered = []

        def receive(topic, payload):
            coordinator.async_event_received(topic, payload)
            delivered.append(hass.states.get(alarm.entity_id).state)

        mqtt.on_data = receive
        right.sendall(b"".join(packet_for(value) for value in ("0", "1", "0")))
        for _ in range(8):
            mqtt._async_reader_callback(mqtt._mqttc)
            await asyncio.sleep(0)
        assert delivered == ["off", "on", "off"]
        # A missing sibling still needs its unavailable state written.
        sibling_key = "new-1" if rollover else "1"
        missing = coordinator.data["devices"].pop(sibling_key)
        writes.clear()
        right.sendall(packet_for("1"))
        mqtt._async_reader_callback(mqtt._mqttc)
        await asyncio.sleep(0)
        assert sibling.entity_id in writes
        assert hass.states.get(sibling.entity_id).state == "unavailable"
        coordinator.data["devices"][sibling_key] = missing
        for extra in ({"onLine": "1"}, {"devs": {"unknown-child": {"alarmStatus": "1"}}}):
            writes.clear()
            right.sendall(packet_for("0", extra))
            mqtt._async_reader_callback(mqtt._mqttc)
            await asyncio.sleep(0)
            assert sibling.entity_id in writes
        # HTTP/global refreshes must still serialize all entities.
        writes.clear()
        coordinator.async_update_listeners()
        assert sibling.entity_id in writes
        assert all(spy.call_count == 0 for spy in spies)
        assert len(hass.states.async_all()) == len(entities)
    finally:
        mqtt._mqttc._sock = None
        left.close()
        right.close()
        await hass.async_stop()
