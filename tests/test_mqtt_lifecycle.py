"""Exercise the broker-facing MQTT subscription lifecycle."""

import asyncio
from threading import Event
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError

from custom_components.xsense import mqtt


@callback
def receive_message(_message):
    """Receive a test subscription message."""


class BrokerClient:
    """Return Paho results and deliver SUBACKs on the event loop."""

    def __init__(self, loop):
        self.loop = loop
        self.calls = []
        self.result = 0
        self.reasons = [1]
        self.mid = 0

    def subscribe(self, topics):
        self.calls.append(topics)
        self.mid += 1
        if self.result:
            return self.result, None
        if self.reasons is not None:
            self.loop.call_soon(
                self.on_subscribe, self, None, self.mid, self.reasons, None
            )
        return 0, self.mid

    def publish(self, *_args):
        self.mid += 1
        self.on_publish(self, None, self.mid)
        return SimpleNamespace(mid=self.mid, rc=0)


def client():
    loop = asyncio.get_running_loop()
    broker = BrokerClient(loop)
    result = mqtt.XSenseMQTT(
        SimpleNamespace(loop=loop),
        SimpleNamespace(title="Test account"),
        SimpleNamespace(client=broker),
    )
    result.init_client()
    return result, broker


@pytest.mark.asyncio
async def test_finished_reconnect_task_does_not_block_replacement():
    connection, _broker = client()
    old_task = asyncio.create_task(asyncio.sleep(0))
    await old_task
    connection._reconnect_task = old_task
    connection._reconnect_loop = AsyncMock()
    connection.config_entry.async_create_background_task = (
        lambda hass, coro, name: asyncio.create_task(coro, name=name)
    )

    connection._async_connection_result(False)
    replacement = connection._reconnect_task
    assert replacement is not old_task
    connection._async_connection_result(False)
    assert connection._reconnect_task is replacement
    await replacement
    connection._reconnect_loop.assert_awaited_once()
    connection._should_reconnect = False
    connection.async_ensure_reconnect()
    assert connection._reconnect_task is replacement


@pytest.mark.asyncio
async def test_connack_cancellation_cannot_release_running_paho_worker():
    connection, broker = client()
    loop = asyncio.get_running_loop()
    entered = asyncio.Event()
    release, finished = Event(), Event()
    broker.socket = Mock(return_value=None)
    broker.disconnect = Mock()
    connection.mqtt_helper.house = SimpleNamespace(mqtt_server="mqtt.example")
    connection._async_prepare_connection = AsyncMock()
    def connect(*args):
        loop.call_soon_threadsafe(entered.set)
        assert release.wait(5)
        finished.set()
        return 0

    broker.connect = connect

    async def executor(func, *args):
        return await loop.run_in_executor(None, func, *args)

    connection.hass.async_add_executor_job = executor
    opening = asyncio.create_task(connection._async_open_connection())
    connection._reconnect_task = opening
    await asyncio.wait_for(entered.wait(), 2)
    try:
        connection.connected = True
        connection._async_connection_result(True)
        retiring = asyncio.create_task(connection.async_disconnect(True))
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        opening.cancel()
        await asyncio.sleep(0)
        assert not finished.is_set()
        assert connection._connection_lock.locked()
        assert broker.on_socket_open == connection._on_socket_open
        broker.disconnect.assert_not_called()
    finally:
        release.set()
        await asyncio.gather(opening, retiring, return_exceptions=True)

    assert opening.cancelled()
    assert finished.is_set()
    assert broker.on_socket_open == connection._async_on_socket_open
    broker.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_retirement_during_credential_preparation_prevents_dial():
    connection, broker = client()
    preparing, resume = asyncio.Event(), asyncio.Event()
    broker.socket = Mock(return_value=None)
    broker.connect = Mock(return_value=0)
    broker.disconnect = Mock()
    connection.mqtt_helper.house = SimpleNamespace(mqtt_server="mqtt.example")

    async def executor(func, *args):
        return func(*args)

    async def prepare():
        preparing.set()
        await resume.wait()

    connection.hass.async_add_executor_job = executor
    connection._async_prepare_connection = prepare
    attempt = asyncio.create_task(connection.async_connect())
    await preparing.wait()
    retirement = asyncio.create_task(connection.async_disconnect(True))
    await asyncio.sleep(0)
    assert not connection._should_reconnect
    resume.set()
    await asyncio.gather(attempt, retirement)
    broker.connect.assert_not_called()
    broker.disconnect.assert_called_once()


@pytest.mark.parametrize("identifier,should_retry", [(134, False), (135, False), (137, True)])
@pytest.mark.asyncio
async def test_paho_v2_connack_refusal_policy(identifier, should_retry):
    connection, broker = client()
    connection._async_connection_result = Mock()
    connection.hass.create_task = Mock(side_effect=lambda coro: coro.close())
    reason = mqtt.mqtt.ReasonCode(mqtt.mqtt.PacketTypes.CONNACK, identifier=identifier)

    broker.on_connect(broker, None, None, reason, None)

    assert not connection.connected
    assert connection._should_reconnect is should_retry
    assert connection.hass.create_task.call_count == int(not should_retry)


@pytest.mark.asyncio
async def test_old_suback_timeout_cannot_untrack_new_connection(monkeypatch):
    connection, broker = client()
    await connection.async_subscribe("home/events", receive_message, 1)
    connection.connected = True
    broker.reasons = None
    monkeypatch.setattr(mqtt, "TIMEOUT_ACK", 0.02)
    old_batch = asyncio.create_task(connection._async_perform_subscriptions())
    await asyncio.sleep(0)
    assert connection._pending_operations

    connection._async_connection_result = Mock()
    connection._async_on_disconnect(128)
    connection.connected = True
    broker.reasons = [1]
    await connection._async_perform_subscriptions()
    await old_batch

    assert broker.calls == [[("home/events", 1)], [("home/events", 1)]]
    assert connection.is_subscribed("home/events")
    assert connection._pending_operations == {}


@pytest.mark.asyncio
@pytest.mark.parametrize("restored", [True, False])
async def test_direct_subscribe_old_timeout_respects_replacement_suback(restored):
    connection, broker = client()
    connection.connected = True
    broker.reasons = None
    pending = asyncio.create_task(
        connection.async_subscribe("home/events", receive_message, 1)
    )
    await asyncio.sleep(0)
    old_ack = connection._pending_operations[broker.mid]

    connection._async_connection_result = Mock()
    connection._async_on_disconnect(128)
    connection.connected = True
    connection._connection_generation += 1
    broker.reasons = [1 if restored else 128]
    await connection._async_perform_subscriptions()
    assert list(connection._pending_operations.values()) == [old_ack]
    assert broker.calls == [[("home/events", 1)], [("home/events", 1)]]

    connection._async_timeout_mid(old_ack)
    if restored:
        remove = await pending
        assert connection.is_subscribed("home/events")
        connection._unsubscribe_debouncer.async_schedule = Mock()
        remove()
    else:
        with pytest.raises(TimeoutError):
            await pending
    assert not connection._pending_operations
    assert not connection.is_subscribed("home/events")


@pytest.mark.asyncio
@pytest.mark.parametrize("restored", [True, False])
async def test_direct_subscribe_waits_when_old_timeout_arrives_first(restored):
    connection, broker = client()
    connection.connected = True
    broker.reasons = None
    pending = asyncio.create_task(
        connection.async_subscribe("home/events", receive_message, 1)
    )
    await asyncio.sleep(0)
    old_ack = connection._pending_operations[broker.mid]
    connection._async_connection_result = Mock()
    connection._async_on_disconnect(128)
    connection.connected = True
    connection._connection_generation += 1
    batch = asyncio.create_task(connection._async_perform_subscriptions())
    await asyncio.sleep(0)

    connection._async_timeout_mid(old_ack)
    await asyncio.sleep(0)
    assert not pending.done()
    broker.on_subscribe(broker, None, broker.mid, [1 if restored else 128], None)
    await batch
    if restored:
        assert callable(await pending)
    else:
        with pytest.raises(TimeoutError):
            await pending
    assert connection.is_subscribed("home/events") is restored
    assert not connection._direct_subscribe_results
    assert not connection._pending_operations


@pytest.mark.asyncio
async def test_direct_subscribe_first_reconnect_ack_cannot_mask_second_rejection():
    connection, broker = client()
    connection.connected = True
    broker.reasons = None
    pending = asyncio.create_task(
        connection.async_subscribe("home/events", receive_message, 1)
    )
    await asyncio.sleep(0)
    old_ack = connection._pending_operations[broker.mid]
    connection._async_connection_result = Mock()

    for reason in (1, 128):
        connection._async_on_disconnect(128)
        connection.connected = True
        connection._connection_generation += 1
        broker.reasons = [reason]
        await connection._async_perform_subscriptions()
        assert connection.is_subscribed("home/events") is (reason == 1)

    connection._async_timeout_mid(old_ack)
    with pytest.raises(TimeoutError):
        await pending
    assert len(broker.calls) == 3
    assert not connection._direct_subscribe_results
    assert not connection._pending_operations


@pytest.mark.asyncio
async def test_cancelled_direct_subscribe_unsubscribes_restored_topic():
    connection, broker = client()
    connection.connected = True
    broker.reasons = None
    pending = asyncio.create_task(
        connection.async_subscribe("home/events", receive_message, 1)
    )
    await asyncio.sleep(0)
    connection._async_connection_result = Mock()
    connection._async_on_disconnect(128)
    connection.connected = True
    connection._connection_generation += 1
    broker.reasons = [1]
    await connection._async_perform_subscriptions()
    connection._unsubscribe_debouncer.async_schedule = Mock()

    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending

    assert not connection.is_subscribed("home/events")
    assert connection._pending_unsubscribes == {"home/events"}
    assert not connection._direct_subscribe_results
    assert not connection._pending_operations


@pytest.mark.asyncio
@pytest.mark.parametrize("remove_in_flight", [True, False])
async def test_removal_during_resubscribe_does_not_abort_or_restore_topic(remove_in_flight):
    connection, broker = client()
    remove_first = await connection.async_subscribe("home/first", receive_message, 1)
    remove_queued = await connection.async_subscribe("home/queued/+", receive_message, 1)
    await connection.async_subscribe("home/remaining", receive_message, 1)
    connection.connected = True
    broker.reasons = None
    batch = asyncio.create_task(connection._async_perform_subscriptions())
    await asyncio.sleep(0)
    first_mid = broker.mid
    assert broker.calls == [[("home/first", 1)]]
    connection._unsubscribe_debouncer.async_schedule = Mock()
    broker.reasons = [1]

    if remove_in_flight:
        remove_first()
        connection._async_timeout_mid(connection._pending_operations[first_mid])
        removed = "home/first"
    else:
        remove_queued()
        broker.on_subscribe(broker, None, first_mid, [1], None)
        removed = "home/queued/+"
    await batch

    assert broker.calls == [
        [("home/first", 1)],
        [("home/remaining", 1)],
        *([[("home/queued/+", 1)]] if remove_in_flight else []),
    ]
    assert not connection.is_subscribed(removed)
    assert connection.is_subscribed("home/remaining")
    assert connection._pending_operations == {}


@pytest.mark.asyncio
async def test_unsubscribe_failure_still_retires_connection():
    connection, broker = client()
    connection._async_perform_unsubscribes = AsyncMock(side_effect=OSError("socket lost"))
    connection._async_cancel_reconnect = Mock()
    broker.disconnect = Mock()
    await connection.async_disconnect(disconnect_paho_client=True)

    assert not connection._should_reconnect
    connection._async_cancel_reconnect.assert_called_once()
    broker.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_queued_unsubscribe_does_not_remove_readded_topic():
    connection, broker = client()
    connection.connected = True
    remove = await connection.async_subscribe("home/events", receive_message, 1)
    connection._unsubscribe_debouncer.async_schedule = Mock()
    remove()
    await connection.async_subscribe("home/events", receive_message, 1)
    broker.unsubscribe = Mock(return_value=(0, 3))
    connection._async_wait_for_mid_or_raise = AsyncMock()

    await connection._async_perform_unsubscribes()

    broker.unsubscribe.assert_not_called()
    assert connection.is_subscribed("home/events")
    assert not connection._pending_unsubscribes


@pytest.mark.asyncio
async def test_connected_subscription_uses_qos_and_consumes_suback():
    connection, broker = client()
    connection.connected = True

    await connection.async_subscribe("home/events", receive_message, 1)

    assert broker.calls == [[("home/events", 1)]]
    assert connection.is_subscribed("home/events")
    assert connection._pending_operations == {}
    broker.on_subscribe(broker, None, broker.mid, [1], None)
    assert connection._pending_operations == {}


@pytest.mark.asyncio
async def test_reconnect_subscriptions_preserve_each_requested_qos():
    connection, broker = client()
    await connection.async_subscribe("home/events", receive_message, 1)
    await connection.async_subscribe("home/state", receive_message, 0)
    assert broker.calls == []

    connection.connected = True
    await connection._async_perform_subscriptions()

    assert broker.calls == [[("home/events", 1)], [("home/state", 0)]]
    assert connection._pending_operations == {}


@pytest.mark.asyncio
async def test_send_failure_untracks_subscription_and_allows_retry():
    connection, broker = client()
    connection.connected = True
    broker.result = mqtt.mqtt.MQTT_ERR_NO_CONN

    with pytest.raises(HomeAssistantError):
        await connection.async_subscribe("home/events", receive_message, 1)

    assert not connection.is_subscribed("home/events")
    assert connection._pending_operations == {}
    broker.result = 0
    await connection.async_subscribe("home/events", receive_message, 1)
    assert connection.is_subscribed("home/events")
    assert len(connection.subscriptions) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", [128, SimpleNamespace(value=135)])
async def test_rejected_suback_untracks_subscription(reason):
    connection, broker = client()
    connection.connected = True
    broker.reasons = [reason]

    with pytest.raises(HomeAssistantError):
        await connection.async_subscribe("home/events", receive_message, 1)

    assert not connection.is_subscribed("home/events")
    assert connection._pending_operations == {}


@pytest.mark.asyncio
async def test_suback_timeout_untracks_and_ignores_late_ack(monkeypatch):
    connection, broker = client()
    connection.connected = True
    broker.reasons = None
    monkeypatch.setattr(mqtt, "TIMEOUT_ACK", 0.001)

    with pytest.raises(TimeoutError):
        await connection.async_subscribe("home/events", receive_message, 1)

    assert not connection.is_subscribed("home/events")
    assert connection._pending_operations == {}
    broker.on_subscribe(broker, None, broker.mid, [1], None)
    assert connection._pending_operations == {}


@pytest.mark.asyncio
async def test_cancelled_subscription_removes_waiter_and_tracking():
    connection, broker = client()
    connection.connected = True
    broker.reasons = None
    task = asyncio.create_task(
        connection.async_subscribe("home/events", receive_message, 1)
    )
    await asyncio.sleep(0)
    assert connection._pending_operations
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert connection._pending_operations == {}
    assert not connection.is_subscribed("home/events")
    broker.on_subscribe(broker, None, broker.mid, [1], None)
    assert connection._pending_operations == {}


@pytest.mark.asyncio
async def test_reconnect_rejection_is_not_kept_as_subscribed():
    connection, broker = client()
    await connection.async_subscribe("home/events", receive_message, 1)
    broker.reasons = [128]

    connection.connected = True
    await connection._async_perform_subscriptions()

    assert not connection.is_subscribed("home/events")
    assert connection._pending_operations == {}


@pytest.mark.asyncio
async def test_publish_callback_before_wait_is_still_consumed():
    connection, _broker = client()

    await connection.async_publish("home/request", "{}", 0, False)

    assert connection._pending_operations == {}


@pytest.mark.asyncio
async def test_cancelled_reconnect_batch_retains_intent_and_retries():
    connection, broker = client()
    await connection.async_subscribe("home/events", receive_message, 1)
    await connection.async_subscribe("home/state", receive_message, 0)
    assert broker.calls == []
    assert connection.is_subscribed("home/events")
    assert connection.is_subscribed("home/state")
    broker.reasons = None
    connection.connected = True

    task = asyncio.create_task(connection._async_perform_subscriptions())
    await asyncio.sleep(0)
    assert connection._pending_operations
    cancelled_mid = broker.mid
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert connection._pending_operations == {}
    assert connection.is_subscribed("home/events")
    assert connection.is_subscribed("home/state")
    broker.on_subscribe(broker, None, cancelled_mid, [1], None)
    assert connection._pending_operations == {}

    broker.reasons = [1]
    await connection._async_perform_subscriptions()

    assert broker.calls == [
        [("home/events", 1)],
        [("home/events", 1)],
        [("home/state", 0)],
    ]
    assert connection._pending_operations == {}
    assert len(connection.subscriptions) == 2
