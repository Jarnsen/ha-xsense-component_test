"""XsenseMQTT is a MQTT client for the XSense server."""

import asyncio
from collections.abc import Callable
import logging
from typing import Any

import paho.mqtt.client as mqtt
from xsense.mqtt_helper import MQTTHelper

from homeassistant.components.mqtt.client import (
    MQTT,
    Subscription,
    _matcher_for_topic,
    _raise_on_error,
)
from homeassistant.components.mqtt.models import (
    AsyncMessageCallbackType,
    MessageCallbackType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HassJob, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)


RECONNECT_INTERVAL_SECONDS = 300
DEFAULT_ENCODING = "utf-8"
DEFAULT_OPTIMISTIC = False
DEFAULT_QOS = 0


class XSenseMQTT(MQTT):
    """XSenseMQTT is a MQTT client for xsense, derived from the Home Assistant MQTT client."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry[Any],
        conf: dict[str, Any],
        mqtt_helper: MQTTHelper,
    ) -> None:
        """Initialize XSense MQTT client."""
        super().__init__(hass, config_entry, conf)

        self.mqtt_helper = mqtt_helper
        self._mqttc = mqtt_helper.client

        self.topics: list[str] = []
        self.on_data: Callable[[str, bytes], None] | None = None

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

    def is_subscribed(self, topic: str):
        """Check if already subscribed to topic."""
        return topic in self.topics

    async def async_connect(self, client_available: asyncio.Future[bool]) -> None:
        """Connect to the host. Does not process messages yet."""

        result: int | None = None
        self._available_future = client_available
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
        finally:
            if result is not None and result != 0:
                if result is not None:
                    _LOGGER.error(
                        "Failed to connect to MQTT server: %s",
                        mqtt.error_string(result),
                    )
                self._async_connection_result(False)

    async def _reconnect_loop(self) -> None:
        """Reconnect to the MQTT server."""
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

            await asyncio.sleep(RECONNECT_INTERVAL_SECONDS)

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

    async def _async_perform_subscriptions(self) -> None:
        if not self.subscriptions:
            return

        for topic in [(i.topic, 0) for i in self.subscriptions]:
            result, mid = self._mqttc.subscribe([topic])

            if result == 0:
                await self._async_wait_for_mid(mid)
            else:
                _raise_on_error(result)

        # XSense MQTT server doesn't like too many subscriptions at once.
        # topics = [[i.topic, 0] for i in self.subscriptions]
        # _LOGGER.error(f"subscribing to {topics}")
        # result, mid = self._mqttc.subscribe(topics)

        # if result == 0:
        #     await self._async_wait_for_mid(mid)
        # else:
        #     _raise_on_error(result)

    async def _async_perform_subscription(self, subscription: Subscription) -> None:
        self._mqttc.subscribe([(subscription.topic, 0)])

    async def async_subscribe(
        self,
        topic: str,
        msg_callback: AsyncMessageCallbackType | MessageCallbackType,
        qos: int,
        encoding: str | None = None,
    ) -> Callable[[], None]:
        """Set up a subscription to a topic with the provided qos.

        This method is a coroutine.
        """
        if not isinstance(topic, str):
            raise HomeAssistantError("Topic needs to be a string!")

        subscription = Subscription(
            topic, _matcher_for_topic(topic), HassJob(msg_callback), qos, encoding
        )

        self._async_track_subscription(subscription)
        self._matching_subscriptions.cache_clear()

        if self.connected:
            self.config_entry.async_create_background_task(
                self.hass,
                self._async_perform_subscription(subscription),
                name="xsense-mqtt subscribe",
            )

        self.topics.append(topic)

        @callback
        def async_remove() -> None:
            """Remove subscription."""
            self._async_untrack_subscription(subscription)
            self._matching_subscriptions.cache_clear()
            if subscription in self._retained_topics:
                del self._retained_topics[subscription]
            # Only unsubscribe if currently connected
            if self.connected:
                self._async_unsubscribe(topic)

        return async_remove

    @callback
    def _async_mqtt_on_message(
        self, _mqttc: mqtt.Client, _userdata: None, msg: mqtt.MQTTMessage
    ) -> None:
        if self.on_data is not None:
            self.on_data(msg.topic, msg.payload)

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
