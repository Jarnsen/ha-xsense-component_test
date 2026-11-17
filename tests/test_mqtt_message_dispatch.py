"""Keep MQTT packet bursts from monopolizing a single event-loop callback."""

import asyncio
import json
import socket
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, Mock

import paho.mqtt.client as paho
import pytest
from test_audit_repairs import make_coordinator, make_station
from test_mqtt_callback_pipeline import publish_packet

from custom_components.xsense import mqtt as mqtt_module
from custom_components.xsense.coordinator import DataUpdateCoordinator
from custom_components.xsense.mqtt import XSenseMQTT


def make_client():
    loop = asyncio.get_running_loop()
    client = paho.Client(paho.CallbackAPIVersion.VERSION2)
    mqtt = XSenseMQTT(NS(loop=loop), NS(title="Offline test"), NS(client=client))
    mqtt.init_client()
    return mqtt


@pytest.mark.asyncio
async def test_real_packet_burst_yields_between_application_messages():
    mqtt = make_client()
    left, right = socket.socketpair()
    left.setblocking(False)
    mqtt._mqttc._sock = left
    for mid in range(1, 21):
        message = paho.MQTTMessage(mid)
        message.qos = 1
        message.state = paho.mqtt_ms_wait_for_puback
        mqtt._mqttc._out_messages[mid] = message
    delivered, heartbeats = [], []
    mqtt.on_data = lambda topic, payload: delivered.append(payload)
    try:
        right.sendall(b"".join(publish_packet("test", {"sequence": i}) for i in range(20)))
        mqtt._async_reader_callback(mqtt._mqttc)
        assert delivered == []
        assert mqtt.callback_diagnostics["max_messages_per_read"] == 20
        assert mqtt.callback_diagnostics["max_queued_messages"] == 20
        asyncio.get_running_loop().call_soon(lambda: heartbeats.append(len(delivered)))
        await asyncio.sleep(0)
        assert heartbeats == [1]
        assert len(delivered) == 1
        for _ in range(19):
            await asyncio.sleep(0)
        assert delivered == [f'{{"sequence": {i}}}'.encode() for i in range(20)]
    finally:
        mqtt._mqttc._sock = None
        left.close()
        right.close()


@pytest.mark.asyncio
async def test_failed_message_does_not_stop_following_alarm(caplog):
    mqtt = make_client()
    delivered = []

    def receive(topic, payload):
        if payload == b"first":
            raise ValueError("sensitive-payload-must-not-be-logged")
        delivered.append(payload)

    mqtt.on_data = receive
    for payload in (b"first", b"second"):
        mqtt._async_mqtt_on_message(None, None, NS(topic="secret-topic", payload=payload))
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert delivered == [b"second"]
    assert "sensitive-payload" not in caplog.text
    assert "secret-topic" not in caplog.text


@pytest.mark.asyncio
async def test_explicit_stop_delivers_received_messages_before_cleanup_awaits():
    mqtt = make_client()
    delivered = []
    mqtt.on_data = lambda topic, payload: delivered.append(payload)
    mqtt._async_mqtt_on_message(None, None, NS(topic="test", payload=b"pending"))
    mqtt._subscribe_debouncer.async_cleanup = AsyncMock()
    mqtt._unsubscribe_debouncer.async_cleanup = AsyncMock()
    mqtt._async_perform_unsubscribes = AsyncMock()
    await mqtt.async_disconnect()
    await asyncio.sleep(0)
    assert delivered == [b"pending"]
    mqtt._async_mqtt_on_message(None, None, NS(topic="test", payload=b"late"))
    await asyncio.sleep(0)
    assert delivered == [b"pending"]


@pytest.mark.asyncio
async def test_sustained_reads_cannot_grow_a_pending_application_batch():
    mqtt = make_client()
    delivered = []
    mqtt.on_data = lambda topic, payload: delivered.append(payload)

    def read(_limit):
        for i in range(5):
            mqtt._async_mqtt_on_message(None, None, NS(topic="test", payload=str(i).encode()))
        return 0

    mqtt._mqttc.loop_read = Mock(side_effect=read)
    mqtt._async_reader_callback(mqtt._mqttc)
    for _ in range(50):
        mqtt._async_reader_callback(mqtt._mqttc)
    assert mqtt._mqttc.loop_read.call_count == 1
    assert len(mqtt._message_queue) == 5
    # A deferred read must be kicked even without a fresh fd-ready notification.
    mqtt._mqttc.loop_read.side_effect = lambda _: 0
    for _ in range(6):
        await asyncio.sleep(0)
    assert mqtt._mqttc.loop_read.call_count == 2
    assert delivered == [b"0", b"1", b"2", b"3", b"4"]
    assert not mqtt._message_queue


@pytest.mark.asyncio
async def test_real_sustained_batches_preserve_all_messages_and_protocol_ack():
    mqtt = make_client()
    left, right = socket.socketpair()
    left.setblocking(False)
    mqtt._mqttc._sock = left
    for mid in range(1, 21):
        message = paho.MQTTMessage(mid)
        message.qos = 1
        message.state = paho.mqtt_ms_wait_for_puback
        mqtt._mqttc._out_messages[mid] = message
    completed = asyncio.get_running_loop().create_future()
    mqtt._pending_operations[7] = completed
    delivered = []
    mqtt.on_data = lambda topic, payload: delivered.append(json.loads(payload)["sequence"])
    packets = [publish_packet("test", {"sequence": i}) for i in range(60)]
    packets.insert(20, b"\x40\x02\x00\x07")
    try:
        right.sendall(b"".join(packets))
        for _ in range(90):
            mqtt._async_reader_callback(mqtt._mqttc)
            await asyncio.sleep(0)
        assert delivered == list(range(60))
        assert completed.done()
        assert mqtt.callback_diagnostics["max_queued_messages"] <= 20
        assert not mqtt._message_queue
        assert mqtt._message_dispatch_handle is None
        assert mqtt._reader_resume_handle is None
    finally:
        mqtt._mqttc._sock = None
        left.close()
        right.close()


@pytest.mark.asyncio
async def test_non_stopping_flush_keeps_failed_unload_runtime_usable():
    mqtt = make_client()
    delivered = []
    mqtt.on_data = lambda topic, payload: delivered.append(payload)
    for payload in (b"first", b"second"):
        mqtt._async_mqtt_on_message(None, None, NS(topic="test", payload=payload))
    mqtt.async_flush_messages()
    assert delivered == [b"first", b"second"]
    mqtt._async_mqtt_on_message(None, None, NS(topic="test", payload=b"third"))
    await asyncio.sleep(0)
    assert delivered == [b"first", b"second", b"third"]
    assert mqtt._message_dispatch_handle is None


@pytest.mark.asyncio
async def test_eager_disconnect_cannot_dispatch_second_alarm_inside_first_handler():
    mqtt = make_client()
    mqtt._subscribe_debouncer.async_cleanup = AsyncMock()
    mqtt._unsubscribe_debouncer.async_cleanup = AsyncMock()
    mqtt._async_perform_unsubscribes = AsyncMock()
    order, tasks = [], []

    def receive(topic, payload):
        if payload == b"first":
            order.append("first-start")
            # HA can eagerly start an async service from a synchronous event listener.
            tasks.append(asyncio.Task(mqtt.async_disconnect(), loop=asyncio.get_running_loop(), eager_start=True))
            order.append("first-end")
        else:
            order.append("second")

    mqtt.on_data = receive
    for payload in (b"first", b"second"):
        mqtt._async_mqtt_on_message(None, None, NS(topic="test", payload=payload))
    await asyncio.sleep(0)
    await asyncio.gather(*tasks)
    assert order == ["first-start", "first-end", "second"]
    assert not mqtt._message_queue
    assert mqtt._message_dispatch_handle is None


@pytest.mark.asyncio
async def test_two_eager_shutdowns_join_delivery_but_retire_coordinator_once(monkeypatch):
    mqtt = make_client()
    coordinator = make_coordinator(make_station())
    coordinator.mqtt_servers = {"broker": mqtt}
    coordinator.xsense = NS(close=AsyncMock())
    close = coordinator.xsense.close
    coordinator._async_disconnect_mqtt = AsyncMock()
    parent_shutdown = AsyncMock()
    monkeypatch.setattr(DataUpdateCoordinator, "async_shutdown", parent_shutdown)
    tasks, delivered = [], []

    def receive(topic, payload):
        assert not coordinator._shutting_down
        delivered.append(payload)
        if payload == b"first":
            for _ in range(2):
                tasks.append(asyncio.Task(coordinator.async_shutdown(), loop=asyncio.get_running_loop(), eager_start=True))

    mqtt.on_data = receive
    for payload in (b"first", b"second"):
        mqtt._async_mqtt_on_message(None, None, NS(topic="test", payload=payload))
    await asyncio.sleep(0)
    await asyncio.gather(*tasks)
    assert delivered == [b"first", b"second"]
    parent_shutdown.assert_awaited_once()
    coordinator._async_disconnect_mqtt.assert_awaited_once()
    close.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancelled_drain_waiter_does_not_cancel_active_delivery():
    mqtt = make_client()
    tasks, order = [], []

    def receive(topic, payload):
        if payload == b"first":
            task = asyncio.Task(mqtt.async_drain_messages(stop_receiving=True), loop=asyncio.get_running_loop(), eager_start=True)
            tasks.append(task)
            task.cancel()
            assert not mqtt._message_dispatch_idle.cancelled()
        order.append(payload)

    mqtt.on_data = receive
    for payload in (b"first", b"second"):
        mqtt._async_mqtt_on_message(None, None, NS(topic="test", payload=payload))
    await asyncio.sleep(0)
    with pytest.raises(asyncio.CancelledError):
        await tasks[0]
    await asyncio.sleep(0)
    assert order == [b"first", b"second"]
    assert mqtt._message_dispatch_idle is None
    assert not mqtt._message_dispatch_stopped


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel_count", [1, 2])
async def test_cancelled_shutdown_caller_does_not_leave_teardown_permanently_incomplete(monkeypatch, cancel_count):
    coordinator = make_coordinator(make_station())
    coordinator.xsense = NS(close=AsyncMock())
    close = coordinator.xsense.close
    coordinator._async_disconnect_mqtt = AsyncMock()
    entered, release = asyncio.Event(), asyncio.Event()

    async def parent_shutdown(_self):
        entered.set()
        await release.wait()

    monkeypatch.setattr(DataUpdateCoordinator, "async_shutdown", parent_shutdown)
    pending = asyncio.create_task(coordinator.async_shutdown())
    await asyncio.wait_for(entered.wait(), 5)
    for _ in range(cancel_count):
        pending.cancel()
        await asyncio.sleep(0)
    was_joining = not pending.done()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await pending
    await coordinator.async_shutdown()
    assert was_joining
    coordinator._async_disconnect_mqtt.assert_awaited_once()
    close.assert_awaited_once()
    assert coordinator.xsense is None


@pytest.mark.asyncio
async def test_shutdown_from_tracked_operation_does_not_cancel_its_own_waiter(monkeypatch):
    coordinator = make_coordinator(make_station())
    coordinator.xsense = NS(close=AsyncMock())
    close = coordinator.xsense.close
    coordinator._async_disconnect_mqtt = AsyncMock()
    monkeypatch.setattr(DataUpdateCoordinator, "async_shutdown", AsyncMock())

    async def operation():
        async with coordinator._async_operation():
            await coordinator.async_shutdown()

    await asyncio.wait_for(operation(), 5)
    assert coordinator._operation_tasks == {}
    close.assert_awaited_once()
    assert coordinator._shutdown_requesters == set()


@pytest.mark.asyncio
async def test_second_shutdown_waits_for_existing_cleanup(monkeypatch):
    coordinator = make_coordinator(make_station())
    coordinator.xsense = NS(close=AsyncMock())
    coordinator._async_disconnect_mqtt = AsyncMock()
    entered, release = asyncio.Event(), asyncio.Event()

    async def parent_shutdown(_self):
        entered.set()
        await release.wait()

    monkeypatch.setattr(DataUpdateCoordinator, "async_shutdown", parent_shutdown)
    first = asyncio.create_task(coordinator.async_shutdown())
    await asyncio.wait_for(entered.wait(), 5)
    second = asyncio.create_task(coordinator.async_shutdown())
    await asyncio.sleep(0)
    was_pending = not second.done()
    release.set()
    await asyncio.gather(first, second)
    assert was_pending
    coordinator._async_disconnect_mqtt.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop_cancels_deferred_buffered_read():
    mqtt = make_client()
    mqtt.on_data = lambda topic, payload: None
    mqtt._mqttc.loop_read = Mock(return_value=0)
    mqtt._async_mqtt_on_message(None, None, NS(topic="test", payload=b"alarm"))
    mqtt._async_reader_callback(mqtt._mqttc)
    await asyncio.sleep(0)
    assert mqtt._reader_resume_handle is not None
    mqtt._subscribe_debouncer.async_cleanup = AsyncMock()
    mqtt._unsubscribe_debouncer.async_cleanup = AsyncMock()
    mqtt._async_perform_unsubscribes = AsyncMock()
    await mqtt.async_disconnect()
    await asyncio.sleep(0)
    mqtt._mqttc.loop_read.assert_not_called()
    assert mqtt._reader_resume_handle is None
    assert mqtt._message_dispatch_handle is None


@pytest.mark.asyncio
async def test_protocol_ack_remains_readable_during_disconnect_cleanup():
    mqtt = make_client()
    left, right = socket.socketpair()
    left.setblocking(False)
    mqtt._mqttc._sock = left
    message = paho.MQTTMessage(7)
    message.qos = 1
    message.state = paho.mqtt_ms_wait_for_puback
    mqtt._mqttc._out_messages[7] = message
    completed = asyncio.get_running_loop().create_future()
    mqtt._pending_operations[7] = completed
    mqtt._subscribe_debouncer.async_cleanup = AsyncMock()
    mqtt._unsubscribe_debouncer.async_cleanup = AsyncMock()

    async def cleanup():
        assert mqtt._message_dispatch_stopped
        right.sendall(b"\x40\x02\x00\x07")
        mqtt._async_reader_callback(mqtt._mqttc)
        assert completed.done()

    mqtt._async_perform_unsubscribes = cleanup
    try:
        await mqtt.async_disconnect()
    finally:
        mqtt._mqttc._sock = None
        left.close()
        right.close()


@pytest.mark.asyncio
async def test_deferred_read_uses_current_client_not_retired_socket():
    mqtt = make_client()
    old = mqtt._mqttc
    old.loop_read = Mock(return_value=0)
    mqtt.on_data = lambda topic, payload: None
    mqtt._async_mqtt_on_message(None, None, NS(topic="test", payload=b"alarm"))
    mqtt._async_reader_callback(old)
    current = paho.Client(paho.CallbackAPIVersion.VERSION2)
    current.loop_read = Mock(return_value=0)
    mqtt._mqttc = current
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    current.loop_read.assert_called_once()
    mqtt._async_reader_callback(old)
    old.loop_read.assert_not_called()


@pytest.mark.asyncio
async def test_coordinator_retirement_applies_received_alarm_before_detaching_callback():
    mqtt = make_client()
    station = make_station()
    coordinator = make_coordinator(station)
    coordinator.mqtt_servers = {"broker": mqtt}
    received = []

    def receive(topic, payload):
        assert mqtt.on_data is receive
        assert coordinator.xsense is not None
        assert not coordinator._shutting_down
        received.append(payload)

    mqtt.on_data = receive
    mqtt._async_mqtt_on_message(None, None, NS(topic="test", payload=b"alarm"))
    mqtt.async_disconnect = AsyncMock()
    await coordinator._async_disconnect_mqtt()
    assert received == [b"alarm"]
    assert mqtt.on_data is None
    assert not mqtt._message_queue
    assert mqtt._message_dispatch_handle is None


@pytest.mark.asyncio
async def test_cancelled_multi_client_retirement_still_closes_partially_drained_clients():
    coordinator = make_coordinator(make_station())
    entered, release = asyncio.Event(), asyncio.Event()

    async def delayed_drain(**_kwargs):
        entered.set()
        await release.wait()

    first = NS(on_data=Mock(), async_drain_messages=AsyncMock(), async_disconnect=AsyncMock())
    second = NS(on_data=Mock(), async_drain_messages=AsyncMock(side_effect=delayed_drain), async_disconnect=AsyncMock())
    coordinator.mqtt_servers = {"first": first, "second": second}
    retiring = asyncio.create_task(coordinator._async_disconnect_mqtt())
    await asyncio.wait_for(entered.wait(), 5)
    retiring.cancel()
    with pytest.raises(asyncio.CancelledError):
        await retiring
    release.set()
    await asyncio.gather(*coordinator._mqtt_retirement_tasks.values())
    first.async_disconnect.assert_awaited_once_with(disconnect_paho_client=True)
    second.async_disconnect.assert_awaited_once_with(disconnect_paho_client=True)
    assert coordinator.mqtt_servers == {}


@pytest.mark.asyncio
async def test_reentrant_arrival_retains_fifo_and_schedules_only_one_runner():
    mqtt = make_client()
    delivered = []

    def receive(topic, payload):
        delivered.append(payload)
        if payload == b"first":
            mqtt._async_mqtt_on_message(None, None, NS(topic="test", payload=b"third"))

    mqtt.on_data = receive
    for payload in (b"first", b"second"):
        mqtt._async_mqtt_on_message(None, None, NS(topic="test", payload=payload))
    for _ in range(3):
        await asyncio.sleep(0)
    assert delivered == [b"first", b"second", b"third"]
    assert mqtt._message_dispatch_handle is None
    assert not mqtt._message_queue


@pytest.mark.asyncio
async def test_received_intrusion_survives_transient_disconnect_and_clears_in_order():
    mqtt = make_client()
    station = make_station()
    station.set_devices({"devices": [{
        "deviceId": "sensor", "deviceSn": "SN", "deviceType": "SDS0A",
        "deviceName": "Door", "roomName": "Entry",
    }]})
    coordinator = make_coordinator(station)
    coordinator.hass = NS(bus=Mock())
    mqtt.on_data = coordinator.async_event_received
    for value in ("1", "0"):
        report = {"stationSn": station.sn, "deviceSn": "SN", "deviceType": "SDS0A", "isAlarm": value}
        mqtt._async_mqtt_on_message(None, None, NS(
            topic="@xsense/events/safealarm/house", payload=json.dumps({"eventData": report}).encode()
        ))
    mqtt.connected = True
    mqtt._async_connection_result = Mock()
    mqtt._async_on_disconnect(7)
    await asyncio.sleep(0)
    assert coordinator.active_intrusion_sensors == {station.sn: {"SN"}}
    coordinator.hass.bus.async_fire.assert_called_once()
    await asyncio.sleep(0)
    assert coordinator.active_intrusion_sensors == {}


@pytest.mark.asyncio
@pytest.mark.parametrize("old_count", [1, 4, 16])
async def test_real_connack_on_replacement_socket_cannot_overtake_received_messages(old_count):
    mqtt = make_client()
    old_left, old_right = socket.socketpair()
    new_left, new_right = socket.socketpair()
    old_left.setblocking(False)
    new_left.setblocking(False)
    mqtt._mqttc._sock = old_left
    jobs, delivered = [], []

    def background(_hass, coro, name):
        task = asyncio.create_task(coro, name=name)
        jobs.append(task)
        return task

    mqtt.config_entry.async_create_background_task = background
    mqtt._async_open_connection = AsyncMock(return_value=0)
    mqtt.on_data = lambda topic, payload: delivered.append(json.loads(payload)["sequence"])
    for mid in range(1, 21):
        message = paho.MQTTMessage(mid)
        message.qos = 1
        message.state = paho.mqtt_ms_wait_for_puback
        mqtt._mqttc._out_messages[mid] = message
    try:
        old_right.sendall(b"".join(publish_packet("test", {"sequence": i}) for i in range(old_count)))
        mqtt.connected = True
        mqtt._async_reader_callback(mqtt._mqttc)
        assert len(mqtt._message_queue) == old_count
        mqtt._async_on_disconnect(128)
        mqtt._mqttc._sock = new_left
        old_left.close()
        new_right.sendall(b"\x20\x02\x00\x00" + b"".join(
            publish_packet("test", {"sequence": i}) for i in range(old_count, old_count + 2)
        ))
        for _ in range(old_count * 2 + 30):
            mqtt._async_reader_callback(mqtt._mqttc)
            await asyncio.sleep(0)
        assert delivered == list(range(old_count + 2))
        assert mqtt.connected
        assert mqtt._reconnect_task is None
        assert mqtt._connection_generation == 2
        assert not mqtt._message_queue
        assert mqtt._message_dispatch_idle is None
        assert mqtt._message_dispatch_handle is None
        assert mqtt._reader_resume_handle is None
    finally:
        await mqtt.async_disconnect()
        mqtt._mqttc._sock = None
        old_left.close()
        old_right.close()
        new_left.close()
        new_right.close()
        await asyncio.gather(*jobs, return_exceptions=True)


@pytest.mark.asyncio
async def test_callback_metrics_separate_reader_from_application_and_hide_payloads(monkeypatch):
    mqtt = make_client()
    ticks = iter(range(20))
    monkeypatch.setattr(mqtt_module, "perf_counter", lambda: next(ticks))
    mqtt._mqttc.loop_read = lambda _: 0
    mqtt._async_reader_callback(mqtt._mqttc)
    mqtt.on_data = lambda topic, payload: None
    mqtt._async_mqtt_on_message(None, None, NS(topic="private-topic", payload=b"secret-token"))
    await asyncio.sleep(0)
    metrics = mqtt.callback_diagnostics
    assert metrics["reader_callbacks"] == 1
    assert metrics["application_messages"] == 1
    assert metrics["max_reader_seconds"] == 1
    assert metrics["max_dispatch_seconds"] == 1
    assert metrics["queued_messages"] == 0
    assert "private" not in json.dumps(metrics)
    assert "secret" not in json.dumps(metrics)
