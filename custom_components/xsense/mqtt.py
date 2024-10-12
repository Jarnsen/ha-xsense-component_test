"""XsenseMQTT is a MQTT client for the XSense server."""

import asyncio
from collections import defaultdict
from collections.abc import AsyncGenerator, Callable, Coroutine, Iterable
import contextlib
from functools import lru_cache, partial
from itertools import chain
import logging
from typing import Any

import paho.mqtt.client as mqtt
from xsense.mqtt_helper import MQTTHelper

from homeassistant.components.mqtt.client import Subscription, _matcher_for_topic
from homeassistant.components.mqtt.models import ReceiveMessage
from homeassistant.components.mqtt.util import EnsureJobAfterCooldown
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import (
    HassJob,
    HassJobType,
    HomeAssistant,
    callback,
    get_hassjob_callable_job_type,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util.collection import chunked_or_all
from homeassistant.util.logging import catch_log_exception

_LOGGER = logging.getLogger(__name__)

INITIAL_SUBSCRIBE_COOLDOWN = 0.5
UNSUBSCRIBE_COOLDOWN = 0.1
TIMEOUT_ACK = 10
RECONNECT_INTERVAL_SECONDS = 300
DEFAULT_ENCODING = "utf-8"
DEFAULT_OPTIMISTIC = False
DEFAULT_QOS = 0

MAX_SUBSCRIBES_PER_CALL = 500
MAX_UNSUBSCRIBES_PER_CALL = 500

MAX_PACKETS_TO_READ = 500

type SocketType = mqtt.WebsocketWrapper | Any
type PublishPayloadType = str | bytes | int | float | None


class XSenseMQTT:
    """XSenseMQTT is a MQTT client for xsense, copied from the Home Assistant MQTT client."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry[Any],
        mqtt_helper: MQTTHelper,
    ) -> None:
        """Initialize XSense MQTT client."""
        self.hass = hass
        self.loop = hass.loop
        self.mqtt_helper = mqtt_helper
        self._mqttc = mqtt_helper.client
        self.config_entry = config_entry

        self._simple_subscriptions: defaultdict[str, set[Subscription]] = defaultdict(
            set
        )
        self._wildcard_subscriptions: set[Subscription] = set()
        self._retained_topics: defaultdict[Subscription, set[str]] = defaultdict(set)

        self._subscribe_debouncer = EnsureJobAfterCooldown(
            INITIAL_SUBSCRIBE_COOLDOWN, self._async_perform_subscriptions
        )
        self._max_qos: defaultdict[str, int] = defaultdict(int)  # topic, max qos
        self._pending_subscriptions: dict[str, int] = {}  # topic, qos
        self._unsubscribe_debouncer = EnsureJobAfterCooldown(
            UNSUBSCRIBE_COOLDOWN, self._async_perform_unsubscribes
        )
        self._pending_unsubscribes: set[str] = set()  # topic

        # self.topics: list[str] = []
        self.on_data: Callable[[str, bytes], None] | None = None

        self.connected = False
        self._connection_lock = asyncio.Lock()
        self._pending_operations: dict[int, asyncio.Future[None]] = {}

        self._misc_timer: asyncio.TimerHandle | None = None
        self._reconnect_task: asyncio.Task | None = None
        self._should_reconnect: bool = True

    # def _async_ha_started
    # async def _async_ha_stop(self, _event: Event) -> None:
    #    await self.async_disconnect()

    # def async_start

    @property
    def subscriptions(self) -> list[Subscription]:
        """Return the tracked subscriptions."""
        return [
            *chain.from_iterable(self._simple_subscriptions.values()),
            *self._wildcard_subscriptions,
        ]

    # cleanup

    @contextlib.asynccontextmanager
    async def _async_connect_in_executor(self) -> AsyncGenerator[None]:
        # While we are connecting in the executor we need to
        # handle on_socket_open and on_socket_register_write
        # in the executor as well.
        mqttc = self._mqttc
        try:
            mqttc.on_socket_open = self._on_socket_open
            mqttc.on_socket_register_write = self._on_socket_register_write
            yield
        finally:
            # Once the executor job is done, we can switch back to
            # handling these in the event loop.
            mqttc.on_socket_open = self._async_on_socket_open
            mqttc.on_socket_register_write = self._async_on_socket_register_write

    # def async_init_client -> made sync

    def init_client(self) -> None:
        """Initialize paho client."""
        ##
        # on_socket_unregister_write and _async_on_socket_close
        # are only ever called in the event loop
        self._mqttc.on_socket_close = self._async_on_socket_close
        self._mqttc.on_socket_unregister_write = self._async_on_socket_unregister_write

        # These will be called in the event loop
        self._mqttc.on_connect = self._async_mqtt_on_connect
        self._mqttc.on_disconnect = self._async_mqtt_on_disconnect
        self._mqttc.on_message = self._async_mqtt_on_message
        self._mqttc.on_publish = self._async_mqtt_on_callback
        self._mqttc.on_subscribe = self._async_mqtt_on_callback
        self._mqttc.on_unsubscribe = self._async_mqtt_on_callback

        # suppress exceptions at callback
        self._mqttc.suppress_exceptions = True

    # unchanged
    @callback
    def _async_reader_callback(self, client: mqtt.Client) -> None:
        """Handle reading data from the socket."""
        if (status := client.loop_read(MAX_PACKETS_TO_READ)) != 0:
            self._async_on_disconnect(status)

    # unchanged / removed import
    @callback
    def _async_start_misc_periodic(self) -> None:
        """Start the misc periodic."""
        assert self._misc_timer is None, "Misc periodic already started"
        _LOGGER.debug("%s: Starting client misc loop", self.config_entry.title)
        # pylint: disable=import-outside-toplevel
        # import paho.mqtt.client as mqtt

        # Inner function to avoid having to check late import
        # each time the function is called.
        @callback
        def _async_misc() -> None:
            """Start the MQTT client misc loop."""
            if self._mqttc.loop_misc() == mqtt.MQTT_ERR_SUCCESS:
                self._misc_timer = self.loop.call_at(self.loop.time() + 1, _async_misc)

        self._misc_timer = self.loop.call_at(self.loop.time() + 1, _async_misc)

    # _async_increase_socket_buffer_size

    # unchanged
    def _on_socket_open(
        self, client: mqtt.Client, userdata: Any, sock: SocketType
    ) -> None:
        """Handle socket open."""
        self.loop.call_soon_threadsafe(
            self._async_on_socket_open, client, userdata, sock
        )

    # removed increase socket buffer size
    @callback
    def _async_on_socket_open(
        self, client: mqtt.Client, userdata: Any, sock: SocketType
    ) -> None:
        """Handle socket open."""
        fileno = sock.fileno()
        _LOGGER.debug("%s: connection opened %s", self.config_entry.title, fileno)
        if fileno > -1:
            self.loop.add_reader(sock, partial(self._async_reader_callback, client))
        if not self._misc_timer:
            self._async_start_misc_periodic()
        # Try to consume the buffer right away so it doesn't fill up
        # since add_reader will wait for the next loop iteration
        self._async_reader_callback(client)

    # unchanged
    @callback
    def _async_on_socket_close(
        self, client: mqtt.Client, userdata: Any, sock: SocketType
    ) -> None:
        """Handle socket close."""
        fileno = sock.fileno()
        _LOGGER.debug("%s: connection closed %s", self.config_entry.title, fileno)
        # If socket close is called before the connect
        # result is set make sure the first connection result is set
        self._async_connection_result(False)
        if fileno > -1:
            self.loop.remove_reader(sock)
        if self._misc_timer:
            self._misc_timer.cancel()
            self._misc_timer = None

    # unchanged
    @callback
    def _async_writer_callback(self, client: mqtt.Client) -> None:
        """Handle writing data to the socket."""
        if (status := client.loop_write()) != 0:
            self._async_on_disconnect(status)

    # unchanged
    def _on_socket_register_write(
        self, client: mqtt.Client, userdata: Any, sock: SocketType
    ) -> None:
        """Register the socket for writing."""
        self.loop.call_soon_threadsafe(
            self._async_on_socket_register_write, client, None, sock
        )

    # Uunchanged
    @callback
    def _async_on_socket_register_write(
        self, client: mqtt.Client, userdata: Any, sock: SocketType
    ) -> None:
        """Register the socket for writing."""
        fileno = sock.fileno()
        _LOGGER.debug("%s: register write %s", self.config_entry.title, fileno)
        if fileno > -1:
            self.loop.add_writer(sock, partial(self._async_writer_callback, client))

    # unchanged
    @callback
    def _async_on_socket_unregister_write(
        self, client: mqtt.Client, userdata: Any, sock: SocketType
    ) -> None:
        """Unregister the socket for writing."""
        fileno = sock.fileno()
        _LOGGER.debug("%s: unregister write %s", self.config_entry.title, fileno)
        if fileno > -1:
            self.loop.remove_writer(sock)

    # unchanged
    def _is_active_subscription(self, topic: str) -> bool:
        """Check if a topic has an active subscription."""
        return topic in self._simple_subscriptions or any(
            other.topic == topic for other in self._wildcard_subscriptions
        )

    # unchanged
    async def async_publish(
        self, topic: str, payload: PublishPayloadType, qos: int, retain: bool
    ) -> None:
        """Publish a MQTT message."""
        msg_info = self._mqttc.publish(topic, payload, qos, retain)
        _LOGGER.debug(
            "Transmitting%s message on %s: '%s', mid: %s, qos: %s",
            " retained" if retain else "",
            topic,
            payload,
            msg_info.mid,
            qos,
        )
        await self._async_wait_for_mid_or_raise(msg_info.mid, msg_info.rc)

    # updated call, added exception handler
    async def async_connect(self) -> None:
        """Connect to the host. Does not process messages yet."""

        result: int | None = None
        # self._available_future = client_available
        self._should_reconnect = True
        try:
            async with self._connection_lock, self._async_connect_in_executor():
                self.mqtt_helper.prepare_connect()
                result = await self.hass.async_add_executor_job(
                    self._mqttc.connect, self.mqtt_helper.house.mqtt_server, 443
                )
        except OSError as err:
            _LOGGER.error("Failed to connect to MQTT server due to exception: %s", err)
            self._async_connection_result(False)
        except mqtt.WebsocketConnectionError as err:
            _LOGGER.error("Error while connecting to XSense MQTT: %s", err)
            self._async_connection_result(False)
        finally:
            if result is not None and result != 0:
                if result is not None:
                    _LOGGER.error(
                        "Failed to connect to MQTT server: %s",
                        mqtt.error_string(result),
                    )
                self._async_connection_result(False)

    # removed available_future
    @callback
    def _async_connection_result(self, connected: bool) -> None:
        """Handle a connection result."""
        # if self._available_future and not self._available_future.done():
        #    self._available_future.set_result(connected)

        if connected:
            self._async_cancel_reconnect()
        elif self._should_reconnect and not self._reconnect_task:
            self._reconnect_task = self.config_entry.async_create_background_task(
                self.hass, self._reconnect_loop(), "mqtt reconnect loop"
            )

    # unchanged
    @callback
    def _async_cancel_reconnect(self) -> None:
        """Cancel the reconnect task."""
        if self._reconnect_task:
            self._reconnect_task.cancel()
            self._reconnect_task = None

    # Added Websocket Exception handler
    async def _reconnect_loop(self) -> None:
        """Reconnect to the MQTT server."""
        await asyncio.sleep(1)

        while True:
            if not self.connected:
                try:
                    async with self._connection_lock, self._async_connect_in_executor():
                        self.mqtt_helper.prepare_connect()
                        await self.hass.async_add_executor_job(self._mqttc.reconnect)
                except OSError as err:
                    _LOGGER.debug(
                        "Error re-connecting to MQTT server due to exception: %s", err
                    )
                except mqtt.WebsocketConnectionError as err:
                    _LOGGER.error("Error while re-connecting to XSense MQTT: %s", err)

            await asyncio.sleep(RECONNECT_INTERVAL_SECONDS)

    async def async_disconnect(self, disconnect_paho_client: bool = False) -> None:
        """Stop the MQTT client.

        We only disconnect grafully if disconnect_paho_client is set, but not
        when Home Assistant is shut down.
        """

        # stop waiting for any pending subscriptions
        await self._subscribe_debouncer.async_cleanup()
        # reset timeout to initial subscribe cooldown
        self._subscribe_debouncer.set_timeout(INITIAL_SUBSCRIBE_COOLDOWN)
        # stop the unsubscribe debouncer
        await self._unsubscribe_debouncer.async_cleanup()
        # make sure the unsubscribes are processed
        await self._async_perform_unsubscribes()

        # wait for ACKs to be processed
        if pending := self._pending_operations.values():
            await asyncio.wait(pending)

        # stop the MQTT loop
        async with self._connection_lock:
            self._should_reconnect = False
            self._async_cancel_reconnect()
            # We do not gracefully disconnect to ensure
            # the broker publishes the will message unless the entry is reloaded
            if disconnect_paho_client:
                self._mqttc.disconnect()

    # unchanged
    @callback
    def async_restore_tracked_subscriptions(
        self, subscriptions: list[Subscription]
    ) -> None:
        """Restore tracked subscriptions after reload."""
        for subscription in subscriptions:
            self._async_track_subscription(subscription)
        self._matching_subscriptions.cache_clear()

    # unchanged
    @callback
    def _async_track_subscription(self, subscription: Subscription) -> None:
        """Track a subscription.

        This method does not send a SUBSCRIBE message to the broker.

        The caller is responsible clearing the cache of _matching_subscriptions.
        """
        if subscription.is_simple_match:
            self._simple_subscriptions[subscription.topic].add(subscription)
        else:
            self._wildcard_subscriptions.add(subscription)

    # unchanged
    @callback
    def _async_untrack_subscription(self, subscription: Subscription) -> None:
        """Untrack a subscription.

        This method does not send an UNSUBSCRIBE message to the broker.

        The caller is responsible clearing the cache of _matching_subscriptions.
        """
        topic = subscription.topic
        try:
            if subscription.is_simple_match:
                simple_subscriptions = self._simple_subscriptions
                simple_subscriptions[topic].remove(subscription)
                if not simple_subscriptions[topic]:
                    del simple_subscriptions[topic]
            else:
                self._wildcard_subscriptions.remove(subscription)
        except (KeyError, ValueError) as exc:
            raise HomeAssistantError("Can't remove subscription twice") from exc

    # unchanged
    @callback
    def _async_queue_subscriptions(
        self, subscriptions: Iterable[tuple[str, int]], queue_only: bool = False
    ) -> None:
        """Queue requested subscriptions."""
        for subscription in subscriptions:
            topic, qos = subscription
            if (max_qos := self._max_qos[topic]) < qos:
                self._max_qos[topic] = (max_qos := qos)
            self._pending_subscriptions[topic] = max_qos
            # Cancel any pending unsubscribe since we are subscribing now
            if topic in self._pending_unsubscribes:
                self._pending_unsubscribes.remove(topic)
        if queue_only:
            return
        self._subscribe_debouncer.async_schedule()

    # unchanged
    def _exception_message(
        self,
        msg_callback: Callable[[ReceiveMessage], Coroutine[Any, Any, None] | None],
        msg: ReceiveMessage,
    ) -> str:
        """Return a string with the exception message."""
        # if msg_callback is a partial we return the name of the first argument
        if isinstance(msg_callback, partial):
            call_back_name = getattr(msg_callback.args[0], "__name__")
        else:
            call_back_name = getattr(msg_callback, "__name__")
        return (
            f"Exception in {call_back_name} when handling msg on "
            f"'{msg.topic}': '{msg.payload}'"  # type: ignore[str-bytes-safe]
        )

    @callback
    async def async_subscribe(
        self,
        topic: str,
        msg_callback: Callable[[ReceiveMessage], Coroutine[Any, Any, None] | None],
        qos: int,
        encoding: str | None = None,
        job_type: HassJobType | None = None,
    ) -> Callable[[], None]:
        """Set up a subscription to a topic with the provided qos.

        This method is a coroutine.
        """
        if not isinstance(topic, str):
            raise HomeAssistantError("Topic needs to be a string!")

        if job_type is None:
            job_type = get_hassjob_callable_job_type(msg_callback)
        if job_type is not HassJobType.Callback:
            # Only wrap the callback with catch_log_exception
            # if it is not a simple callback since we catch
            # exceptions for simple callbacks inline for
            # performance reasons.
            msg_callback = catch_log_exception(
                msg_callback, partial(self._exception_message, msg_callback)
            )

        job = HassJob(msg_callback, job_type=job_type)
        is_simple_match = not ("+" in topic or "#" in topic)
        matcher = None if is_simple_match else _matcher_for_topic(topic)

        subscription = Subscription(topic, is_simple_match, matcher, job, qos, encoding)

        self._async_track_subscription(subscription)
        self._matching_subscriptions.cache_clear()

        if self.connected:
            self.config_entry.async_create_background_task(
                self.hass,
                self._async_perform_subscription(subscription),
                name="xsense-mqtt subscribe",
            )

        # self.topics.append(topic)
        return partial(self._async_remove, subscription)

    @callback
    def _async_remove(self, subscription: Subscription) -> None:
        """Remove subscription."""
        self._async_untrack_subscription(subscription)
        self._matching_subscriptions.cache_clear()
        if subscription in self._retained_topics:
            del self._retained_topics[subscription]
        # Only unsubscribe if currently connected
        if self.connected:
            self._async_unsubscribe(subscription.topic)

    @callback
    def _async_unsubscribe(self, topic: str) -> None:
        """Unsubscribe from a topic."""
        if self._is_active_subscription(topic):
            if self._max_qos[topic] == 0:
                return
            subs = self._matching_subscriptions(topic)
            self._max_qos[topic] = max(sub.qos for sub in subs)
            # Other subscriptions on topic remaining - don't unsubscribe.
            return
        if topic in self._max_qos:
            del self._max_qos[topic]
        if topic in self._pending_subscriptions:
            # Avoid any pending subscription to be executed
            del self._pending_subscriptions[topic]

        self._pending_unsubscribes.add(topic)
        self._unsubscribe_debouncer.async_schedule()

    async def _async_perform_subscriptions(self) -> None:
        if not self.subscriptions:
            return

        for topic in [(i.topic, 0) for i in self.subscriptions]:
            result, mid = self._mqttc.subscribe([topic])

            await self._async_wait_for_mid_or_raise(mid, result)

        # XSense MQTT server doesn't like too many subscriptions at once.
        # topics = [[i.topic, 0] for i in self.subscriptions]
        # _LOGGER.error(f"subscribing to {topics}")
        # result, mid = self._mqttc.subscribe(topics)

        # if result == 0:
        #     await self._async_wait_for_mid(mid)
        # else:
        #     _raise_on_error(result)

    # unchanged
    async def _async_perform_unsubscribes(self) -> None:
        """Perform pending MQTT client unsubscribes."""
        if not self._pending_unsubscribes:
            return

        topics = list(self._pending_unsubscribes)
        self._pending_unsubscribes = set()
        debug_enabled = _LOGGER.isEnabledFor(logging.DEBUG)

        for chunk in chunked_or_all(topics, MAX_UNSUBSCRIBES_PER_CALL):
            chunk_list = list(chunk)

            result, mid = self._mqttc.unsubscribe(chunk_list)
            if debug_enabled:
                _LOGGER.debug(
                    "Unsubscribing with mid: %s to topics: %s", mid, chunk_list
                )

            await self._async_wait_for_mid_or_raise(mid, result)

    # def _async_resubscribe_and_publish_birth_message

    # removed import
    # remove async_start_reauth
    # remove hass mqtt connection state
    # remove birth message
    # add perform subscriptions
    @callback
    def _async_mqtt_on_connect(
        self,
        _mqttc: mqtt.Client,
        _userdata: None,
        _flags: dict[str, int],
        result_code: int,
        properties: mqtt.Properties | None = None,
    ) -> None:
        """On connect callback.

        Resubscribe to all topics we were subscribed to and publish birth
        message.
        """

        if result_code != mqtt.CONNACK_ACCEPTED:
            if result_code in (
                mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD,
                mqtt.CONNACK_REFUSED_NOT_AUTHORIZED,
            ):
                self._should_reconnect = False
                self.hass.async_create_task(self.async_disconnect())
            _LOGGER.error(
                "Unable to connect to the MQTT broker: %s",
                mqtt.connack_string(result_code),
            )
            self._async_connection_result(False)
            return

        self.connected = True

        self.config_entry.async_create_background_task(
            self.hass,
            self._async_perform_subscriptions(),
            name="xsense-mqtt re-subscribe",
        )

        self._async_connection_result(True)

    # def _async_queue_resubscribe
    @lru_cache(None)  # pylint: disable=method-cache-max-size-none
    def _matching_subscriptions(self, topic: str) -> list[Subscription]:
        subscriptions: list[Subscription] = []
        if topic in self._simple_subscriptions:
            subscriptions.extend(self._simple_subscriptions[topic])
        subscriptions.extend(
            subscription
            for subscription in self._wildcard_subscriptions
            # mypy doesn't know that complex_matcher is always set when
            # is_simple_match is False
            if subscription.complex_matcher(topic)  # type: ignore[misc]
        )
        return subscriptions

    # updated
    @callback
    def _async_mqtt_on_message(
        self, _mqttc: mqtt.Client, _userdata: None, msg: mqtt.MQTTMessage
    ) -> None:
        if self.on_data is not None:
            self.on_data(msg.topic, msg.payload)

    # unchanged
    @callback
    def _async_mqtt_on_callback(
        self,
        _mqttc: mqtt.Client,
        _userdata: None,
        mid: int,
        _granted_qos_reason: tuple[int, ...] | mqtt.ReasonCodes | None = None,
        _properties_reason: mqtt.ReasonCodes | None = None,
    ) -> None:
        """Publish / Subscribe / Unsubscribe callback."""
        # The callback signature for on_unsubscribe is different from on_subscribe
        # see https://github.com/eclipse/paho.mqtt.python/issues/687
        # properties and reason codes are not used in Home Assistant
        future = self._async_get_mid_future(mid)
        if future.done() and (future.cancelled() or future.exception()):
            # Timed out or cancelled
            return
        future.set_result(None)

    # unchanged
    @callback
    def _async_get_mid_future(self, mid: int) -> asyncio.Future[None]:
        """Get the future for a mid."""
        if future := self._pending_operations.get(mid):
            return future
        future = self.hass.loop.create_future()
        self._pending_operations[mid] = future
        return future

    # unchanged
    @callback
    def _async_mqtt_on_disconnect(
        self,
        _mqttc: mqtt.Client,
        _userdata: None,
        result_code: int,
        properties: mqtt.Properties | None = None,
    ) -> None:
        """Disconnected callback."""
        self._async_on_disconnect(result_code)

    # remove mqtt status dispatching
    @callback
    def _async_on_disconnect(self, result_code: int) -> None:
        if not self.connected:
            # This function is re-entrant and may be called multiple times
            # when there is a broken pipe error.
            return
        # If disconnect is called before the connect
        # result is set make sure the first connection result is set
        self._async_connection_result(False)
        self.connected = False
        _LOGGER.warning(
            "Disconnected from MQTT server (%s)",
            result_code,
        )

    # unchanged
    @callback
    def _async_timeout_mid(self, future: asyncio.Future[None]) -> None:
        """Timeout waiting for a mid."""
        if not future.done():
            future.set_exception(asyncio.TimeoutError)

    # def _async_wait_for_mid_or_raise

    # unchanged
    async def _async_wait_for_mid_or_raise(self, mid: int, result_code: int) -> None:
        """Wait for ACK from broker or raise on error."""
        if result_code != 0:
            raise HomeAssistantError(
                f"Error talking to MQTT: {mqtt.error_string(result_code)}"
            )

        # Create the mid event if not created, either _mqtt_handle_mid or
        # _async_wait_for_mid_or_raise may be executed first.
        future = self._async_get_mid_future(mid)
        loop = self.hass.loop
        timer_handle = loop.call_later(TIMEOUT_ACK, self._async_timeout_mid, future)
        try:
            await future
        except TimeoutError:
            _LOGGER.warning(
                "No ACK from MQTT server in %s seconds (mid: %s)", TIMEOUT_ACK, mid
            )
        finally:
            timer_handle.cancel()
            del self._pending_operations[mid]

    # def _discovery_cooldown

    # Custom functions
    async def _async_perform_subscription(self, subscription: Subscription) -> None:
        self._mqttc.subscribe([(subscription.topic, 0)])

    def is_subscribed(self, topic: str):
        """Check if already subscribed to topic."""
        # return topic in self.topics
        # for topic in [(i.topic, 0) for i in self.subscriptions]:
        # return any(i.topic == topic for i in self.subscriptions)
        return self._is_active_subscription(topic)
