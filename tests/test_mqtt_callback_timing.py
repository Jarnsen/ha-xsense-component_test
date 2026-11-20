"""Explain slow dispatches without changing delivery or retaining payloads."""

import json
import logging
from unittest.mock import Mock

import pytest
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from test_audit_repairs import make_coordinator, make_station

from custom_components.xsense import entity, sensor
from custom_components.xsense.callback_timing import CallbackTiming


def test_slow_dispatch_breakdown_and_log_cooldown(monkeypatch, caplog):
    coordinator = make_coordinator(make_station())
    namespace = coordinator.async_event_received.__func__.__globals__
    clock = iter((0.0, 0.85, 0.85, 1.0, 1.9, 1.9))
    monkeypatch.setitem(namespace, "perf_counter", lambda: next(clock))
    delivered = []

    def receive(topic, payload):
        delivered.append((topic, payload))
        timing = coordinator._mqtt_callback_timing
        timing.discovery_seconds = 0.2
        timing.discovery_calls = 7
        timing.entity_write_seconds = 0.6
        timing.entity_write_calls = 100

    monkeypatch.setattr(coordinator, "_async_process_mqtt_event", receive)
    with caplog.at_level(logging.DEBUG, logger=namespace["LOGGER"].name):
        coordinator.async_event_received("private-topic", b"private-payload")
        first = coordinator._mqtt_slowest_dispatch_work
        coordinator.async_event_received("private-topic", b"private-payload")
    assert first == {
        "total_seconds": 0.85, "discovery_seconds": 0.2,
        "reported_child_count": None,
        "slowest_entity_write_seconds": 0.0, "slowest_entity_write_class": None,
        "discovery_calls": 7, "entity_write_seconds": 0.6,
        "entity_write_calls": 100, "other_seconds": 0.05,
    }
    assert coordinator._mqtt_slowest_dispatch_work["total_seconds"] == pytest.approx(0.9)
    assert len(delivered) == 2
    assert caplog.text.count("slow MQTT dispatch work") == 1
    assert "private-topic" not in caplog.text
    assert "private-payload" not in caplog.text
    assert coordinator._mqtt_callback_timing is None


def test_failed_delivery_restores_timing_context_and_preserves_error(monkeypatch):
    coordinator = make_coordinator(make_station())
    namespace = coordinator.async_event_received.__func__.__globals__
    clock = iter((0.0, 0.02))
    monkeypatch.setitem(namespace, "perf_counter", lambda: next(clock))
    previous = object()
    coordinator._mqtt_callback_timing = previous
    receive = Mock(side_effect=ValueError("handler failed"))
    monkeypatch.setattr(coordinator, "_async_process_mqtt_event", receive)
    with pytest.raises(ValueError, match="handler failed"):
        coordinator.async_event_received("topic", b"payload")
    assert coordinator._mqtt_callback_timing is previous
    assert coordinator._mqtt_slowest_dispatch_work["total_seconds"] == 0.02
    receive.assert_called_once_with("topic", b"payload")


def test_rssi_child_dispatch_keeps_fast_and_slow_counts(monkeypatch):
    station = make_station()
    coordinator = make_coordinator(station)
    coordinator.async_update_listeners = Mock()
    namespace = coordinator.async_event_received.__func__.__globals__
    monkeypatch.setattr(namespace["LOGGER"], "isEnabledFor", lambda _: False)
    clock = iter((0.0, 0.12, 1.0, 1.9, 2.0, 2.4, 3.0, 3.1200001, 4.0, 4.8999999))
    monkeypatch.setitem(namespace, "perf_counter", lambda: next(clock))
    topic = f"$aws/things/{station.shadow_name}/shadow/name/2nd_mainpage/update"
    for count in (1, 22, 5, 9, 12):
        report = {
            "stationSN": station.sn, "wifiRSSI": -45,
            "devs": {f"private-{i}": {} for i in range(count)},
        }
        coordinator.async_event_received(
            topic, json.dumps({"state": {"reported": report}}).encode(),
        )

    samples = coordinator._mqtt_rssi_child_dispatch_work
    assert samples["fastest"]["total_seconds"] == 0.12
    assert samples["fastest"]["reported_child_count"] == 1
    assert samples["slowest"]["total_seconds"] == pytest.approx(0.9)
    assert samples["slowest"]["reported_child_count"] == 22
    assert "private-" not in json.dumps(samples)


def test_slowest_sensor_phases_and_type_are_from_the_same_write(monkeypatch):
    station = make_station()
    coordinator = make_coordinator(station)
    timing = coordinator._mqtt_callback_timing = CallbackTiming()
    now = 0.0

    def advance(seconds):
        nonlocal now
        now += seconds

    monkeypatch.setattr(entity, "perf_counter", lambda: now)
    monkeypatch.setattr(sensor, "perf_counter", lambda: now)

    def lookup(self):
        advance(self.lookup_delay)
        return station

    def is_available(self):
        advance(self.availability_delay)
        return True

    def write(self):
        if isinstance(self, sensor.XSenseSensorEntity):
            assert self.available
            assert self.native_value == "private-reading"
        advance(self.other_delay)

    monkeypatch.setattr(entity.XSenseEntity, "_current_entity", lookup)
    monkeypatch.setattr(CoordinatorEntity, "available", property(is_available))
    monkeypatch.setattr(CoordinatorEntity, "_handle_coordinator_update", write)

    def make_sensor(key, lookup_delay, availability_delay, value_delay, other_delay):
        def read_value(_):
            advance(value_delay)
            return "private-reading"

        item = sensor.XSenseSensorEntity(
            coordinator, station,
            sensor.XSenseSensorEntityDescription(key=key, value_fn=read_value),
        )
        item.entity_id = f"sensor.private_{key}"
        item.lookup_delay = lookup_delay
        item.availability_delay = availability_delay
        item.other_delay = other_delay
        return item

    slow = make_sensor("battery", 0.02, 0.03, 0.04, 0.835)
    fast = make_sensor("wifi_rssi", 0.06, 0.07, 0.08, 0.0)
    slow._handle_coordinator_update()
    fast._handle_coordinator_update()
    work = timing.snapshot(now)
    assert work["entity_write_calls"] == 2
    assert work["slowest_entity_write_seconds"] == pytest.approx(0.945)
    assert work["slowest_entity_write_class"] == "XSenseSensorEntity"
    assert work["slowest_sensor_type"] == "battery"
    assert work["slowest_sensor_lookup_seconds"] == pytest.approx(0.04)
    assert work["slowest_sensor_availability_seconds"] == pytest.approx(0.03)
    assert work["slowest_sensor_value_seconds"] == pytest.approx(0.04)
    assert "private" not in json.dumps(work)
    assert slow._mqtt_sensor_write_timing is fast._mqtt_sensor_write_timing is None

    # A longer non-sensor write replaces the entire winner, not only the duration.
    control = object.__new__(entity.XSenseEntity)
    control.coordinator = coordinator
    control.other_delay = 1.0
    control._handle_coordinator_update()
    work = timing.snapshot(now)
    assert work["slowest_entity_write_class"] == "XSenseEntity"
    assert not any(key.startswith("slowest_sensor_") for key in work)
