"""X-Sense cloud, MQTT, and camera client library."""

from .async_xsense import (
    AsyncXSense,
    camera_addx_serial,
    camera_for_identifier,
    camera_identifiers,
    camera_matches_identifier,
    camera_primary_identifiers,
    cameras_share_identity,
)
from .device import Device
from .house import House
from .mqtt_helper import MQTTHelper
from .station import Station
from .xsense import XSense

__version__ = "0.1.0"

__all__ = [
    "AsyncXSense",
    "Device",
    "House",
    "MQTTHelper",
    "Station",
    "XSense",
    "__version__",
    "camera_addx_serial",
    "camera_for_identifier",
    "camera_identifiers",
    "camera_matches_identifier",
    "camera_primary_identifiers",
    "cameras_share_identity",
]
