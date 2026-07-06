"""Helpers for connecting to and using the X-Sense MQTT broker."""

from __future__ import annotations

import json
import uuid
import ssl
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Optional

from paho.mqtt import client as mqtt_client

from .aws_signer import AWSSigner

if TYPE_CHECKING:
    from .house import House
    from .station import Station


URL_MAX_AGE = 5
USERNAME = "?SDK=iOS&Version=2.26.5"
FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_COUNT = 12
MAX_RECONNECT_DELAY = 60
DEFAULT_QOS = 0
DEFAULT_SUBSCRIBE_QOS = 1
DEFAULT_RETAIN = False
TEMP_DATA_TYPES = ("STH51", "STH0A", "STH0B")


def shadow_update_topic(thing_name: str, shadow: str) -> str:
    return f"$aws/things/{thing_name}/shadow/name/{shadow}/update"


def shadow_wildcard_topic(thing_name: str) -> str:
    return f"$aws/things/{thing_name}/shadow/name/+/update"


def presence_topic(thing_name: str) -> str:
    return f"$aws/events/presence/+/{thing_name}"


def house_event_topic(house_id: str) -> str:
    return f"@xsense/events/+/{house_id}"


def parse_message_payload(payload: Any) -> Dict:
    if isinstance(payload, bytes):
        payload = payload.decode()
    if isinstance(payload, str):
        return json.loads(payload)
    if payload is None:
        return {}
    return payload


def should_ignore_shadow_topic(topic: str) -> bool:
    ignored_suffixes = ("/update/accepted", "/update/documents", "/update/rejected")
    return topic.endswith(ignored_suffixes)


class MQTTHelper:
    def _get_path(self):
        if (
            not self._mqtt_path
            or not self._sig_age
            or datetime.now() - self._sig_age > timedelta(minutes=URL_MAX_AGE)
        ):
            signed = self.signer.presign_url(
                f"wss://{self.house.mqtt_server}/mqtt", self.house.mqtt_region
            )
            url_parts = signed.split("/")
            self._mqtt_path = "/" + "/".join(url_parts[3:])
            self._sig_age = datetime.now()

        return self._mqtt_path

    def __init__(self, signer: AWSSigner, house: House):
        self.signer = signer
        self.house = house
        self.active = False
        self._last_update = None
        self._update_callback = None
        self._mqtt_path = None
        self._sig_age = None

        self.client = mqtt_client.Client(
            callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2,
            client_id=str(uuid.uuid4()),
            reconnect_on_failure=False,
            transport="websockets",
        )

        self._tls_context_configured = False
        self.client.username_pw_set(USERNAME, "")

    def ensure_tls_context(self):
        """Configure TLS after certificate loading has moved off the event loop."""
        if self._tls_context_configured:
            return
        ssl_context = ssl.create_default_context()
        self.client.tls_set_context(ssl_context)
        self._tls_context_configured = True

    def prepare_connect(self):
        self.client.ws_set_options(path=self._get_path())

    def prepare_connection(self):
        self.prepare_connect()
        self.ensure_tls_context()

    def connect(self, port: int = 443, keepalive: int = 60):
        self.prepare_connection()
        result = self.client.connect(self.house.mqtt_server, port, keepalive)
        self.active = result == 0
        return result

    def loop_start(self):
        self.client.loop_start()

    def loop_stop(self):
        self.client.loop_stop()

    def disconnect(self):
        result = self.client.disconnect()
        self.active = False
        return result

    def publish(
        self,
        topic: str,
        payload: Any,
        qos: int = DEFAULT_QOS,
        retain: bool = DEFAULT_RETAIN,
    ):
        if not isinstance(payload, str):
            payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        return self.client.publish(topic, payload, qos=qos, retain=retain)

    def subscribe(self, topic: str, qos: int = DEFAULT_SUBSCRIBE_QOS):
        return self.client.subscribe(topic, qos=qos)

    def subscribe_live_updates(self, qos: int = DEFAULT_SUBSCRIBE_QOS) -> List:
        results = []
        for topic in self.live_update_topics():
            results.append(self.subscribe(topic, qos=qos))
        return results

    def set_message_callback(
        self, callback: Callable[[str, Dict], None], ignore_shadow_ack: bool = True
    ):
        def on_message(_client, _userdata, msg):
            if ignore_shadow_ack and should_ignore_shadow_topic(msg.topic):
                return
            payload = parse_message_payload(msg.payload)
            self._last_update = (msg.topic, payload)
            callback(msg.topic, payload)

        self.client.on_message = on_message

    def live_update_topics(self) -> List[str]:
        topics = [
            house_event_topic(self.house.house_id),
            shadow_wildcard_topic(self.house.house_id),
        ]

        for station in getattr(self.house, "stations", {}).values():
            topics.append(shadow_wildcard_topic(station.shadow_name))
            topics.append(presence_topic(station.shadow_name))

        return topics

    def temp_data_devices(
        self, station: Station, device_types: Iterable[str] = TEMP_DATA_TYPES
    ) -> List[str]:
        device_types = set(device_types)
        return [
            device.sn
            for device in getattr(station, "devices", {}).values()
            if device.type in device_types
        ]

    def build_temp_data_request(
        self,
        station: Station,
        device_sns: Optional[Iterable[str]] = None,
        timeout_minutes: int = 5,
        user_id: Optional[str] = None,
    ) -> Dict:
        if device_sns is None:
            device_sns = self.temp_data_devices(station)
        device_sns = list(device_sns)
        if not device_sns:
            raise ValueError("At least one device serial number is required")
        if user_id is None:
            raise ValueError("user_id is required to request temperature data")

        return {
            "state": {
                "desired": {
                    "shadow": "appTempData",
                    "deviceSN": device_sns,
                    "source": "1",
                    "report": "1",
                    "reportDst": "1",
                    "timeoutM": str(timeout_minutes),
                    "userId": user_id,
                    "time": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
                    "stationSN": station.sn,
                }
            }
        }

    def temp_data_topic(self, station: Station) -> str:
        return shadow_update_topic(station.shadow_name, "2nd_apptempdata")

    def request_temp_data(
        self,
        station: Station,
        device_sns: Optional[Iterable[str]] = None,
        timeout_minutes: int = 5,
        user_id: Optional[str] = None,
    ):
        payload = self.build_temp_data_request(
            station, device_sns, timeout_minutes, user_id
        )
        return self.publish(self.temp_data_topic(station), payload)
