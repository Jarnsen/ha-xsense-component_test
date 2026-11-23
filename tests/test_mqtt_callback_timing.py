"""Explain slow dispatches without changing delivery or retaining payloads."""

import json
import logging
from threading import Event
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
    coordinator._mqtt_state_write_probe.close()


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


def test_sensor_writes_keep_aggregate_metrics_without_sensor_detail(monkeypatch):
    station = make_station()
    coordinator = make_coordinator(station)
    timing = coordinator._mqtt_callback_timing = CallbackTiming()
    now = 0.0

    def advance(seconds):
        nonlocal now
        now += seconds

    monkeypatch.setattr(entity, "perf_counter", lambda: now)

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
        item._coordinator_state_initialized = True
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
    assert work["entity_write_seconds"] == pytest.approx(now)
    assert not any(key.startswith("slowest_sensor_") for key in work)
    assert "private" not in json.dumps(work)

    # A longer non-sensor write replaces the aggregate winner.
    control = object.__new__(entity.XSenseEntity)
    control.coordinator = coordinator
    control.other_delay = 1.0
    control._handle_coordinator_update()
    work = timing.snapshot(now)
    assert work["slowest_entity_write_class"] == "XSenseEntity"
    assert work["slowest_entity_write_seconds"] == pytest.approx(1.0)
    assert work["entity_write_calls"] == 3
    assert not any(key.startswith("slowest_sensor_") for key in work)


@pytest.mark.asyncio
async def test_slow_ha_write_keeps_cpu_and_same_write_stack(monkeypatch, caplog, tmp_path):
    from homeassistant.const import EVENT_STATE_CHANGED, EVENT_STATE_REPORTED
    from homeassistant.core import HomeAssistant, callback

    station = make_station()
    coordinator = make_coordinator(station)
    hass = HomeAssistant(str(tmp_path))
    item = sensor.XSenseSensorEntity(
        coordinator, station,
        sensor.XSenseSensorEntityDescription(key="battery", value_fn=lambda _: 100),
    )
    item.entity_id = "sensor.private_entity_id"
    item.hass = hass
    item._no_platform_reported = True
    monkeypatch.setattr(sensor.XSenseSensorEntity, "unit_of_measurement", None)
    monkeypatch.setattr(coordinator, "_async_process_mqtt_event", lambda *_: item.async_write_ha_state())
    monkeypatch.setattr(coordinator, "_mqtt_next_work_log", float("inf"), raising=False)
    logger = coordinator.async_event_received.__func__.__globals__["LOGGER"]

    @callback
    def slow_state_listener(event):
        assert event.data["entity_id"] == "sensor.private_entity_id"
        Event().wait(0.24)

    @callback
    def is_test_sensor(data):
        return data["entity_id"] == item.entity_id

    unsub_change = hass.bus.async_listen(EVENT_STATE_CHANGED, slow_state_listener, is_test_sensor)
    unsub_report = hass.bus.async_listen(EVENT_STATE_REPORTED, slow_state_listener, is_test_sensor)
    try:
        with caplog.at_level(logging.DEBUG, logger=logger.name):
            coordinator.async_event_received("private-topic", b"private-payload")
            sample = coordinator._mqtt_slowest_sensor_state_write
            assert sample["write_result"] == "state_changed"
            assert "X-Sense slow MQTT sensor state write" in caplog.text
            assert "X-Sense slow MQTT dispatch work" not in caplog.text

            # A forced next log makes the unchanged write independently inspectable.
            coordinator._mqtt_logged_sensor_write = None
            coordinator.async_event_received("private-topic", b"private-payload")
            assert "'write_result': 'state_reported'" in caplog.text

        assert sample["sensor_type"] == "battery"
        assert sample["wall_seconds"] >= 0.2
        assert sample["non_cpu_seconds"] >= 0.1
        assert sample["thread_cpu_seconds"] < sample["wall_seconds"]
        assert sample["dispatch_seconds"] >= sample["wall_seconds"]
        assert sample["stack_capture"] == "captured"
        assert any(
            ".slow_state_listener:" in frame
            for stack in sample["stack_samples"] for frame in stack["frames"]
        )
        assert "private_entity_id" not in caplog.text
        assert "private-topic" not in caplog.text
        assert "private-payload" not in caplog.text
    finally:
        unsub_change()
        unsub_report()
        coordinator._mqtt_state_write_probe.close()


def test_diagnostics_retain_slow_sensor_independently_of_slowest_dispatch(monkeypatch):
    coordinator = make_coordinator(make_station())
    monkeypatch.setattr(coordinator, "_mqtt_slowest_dispatch_work", {"total_seconds": 5}, raising=False)
    traced = {"sensor_type": "battery", "wall_seconds": 1.5, "stack_samples": [{}]}
    untraced = {"sensor_type": "battery", "wall_seconds": 2.46, "stack_samples": []}

    def process(topic, payload):
        timing = coordinator._mqtt_callback_timing
        assert timing.state_write_probe is None
        timing.record_sensor_state_write(traced)
        timing.record_sensor_state_write(untraced)

    monkeypatch.setattr(coordinator, "_async_process_mqtt_event", process)
    coordinator.async_event_received("private-topic", b"private-payload")
    assert coordinator._mqtt_slowest_dispatch_work == {"total_seconds": 5}
    assert coordinator._mqtt_slowest_sensor_state_write is untraced
    assert coordinator._mqtt_slowest_traced_sensor_state_write is traced


def test_state_write_sampler_stops_when_debug_logging_is_disabled(monkeypatch, caplog):
    coordinator = make_coordinator(make_station())
    monkeypatch.setattr(coordinator, "_async_process_mqtt_event", Mock())
    logger = coordinator.async_event_received.__func__.__globals__["LOGGER"]
    with caplog.at_level(logging.DEBUG, logger=logger.name):
        coordinator.async_event_received("topic", b"payload")
        probe = coordinator._mqtt_state_write_probe
        assert probe.is_running()
        coordinator.async_event_received("topic", b"payload")
        assert coordinator._mqtt_state_write_probe is probe
    coordinator.async_event_received("topic", b"payload")
    assert coordinator._mqtt_state_write_probe is None
    assert not probe.is_running()


def test_sensor_log_preserves_first_stack_and_later_severe_write(caplog):
    coordinator = make_coordinator(make_station())
    logger = coordinator.async_event_received.__func__.__globals__["LOGGER"]

    def record(now, *samples):
        timing = CallbackTiming(state_write_probe=Mock())
        for wall, stack in samples:
            timing.record_sensor_state_write({"wall_seconds": wall, "stack_samples": stack})
        coordinator._record_mqtt_sensor_write_details(timing, 3, now)

    stack = [{"frames": ["test.listener:1"]}]
    with caplog.at_level(logging.DEBUG, logger=logger.name):
        record(1, (0.2, []))
        record(2, (0.21, []))
        record(3, (0.22, stack))
        record(4, (2.46, []), (0.5, stack))
    messages = [item.getMessage() for item in caplog.records if "slow MQTT sensor state write" in item.getMessage()]
    assert len(messages) == 4
    assert "0.21" not in caplog.text
    assert "0.22" in messages[1] and "test.listener:1" in messages[1]
    assert "2.46" in messages[2] and "test.listener:1" in messages[3]
    assert coordinator._mqtt_slowest_sensor_state_write["wall_seconds"] == 2.46
    assert coordinator._mqtt_slowest_traced_sensor_state_write["wall_seconds"] == 0.5
