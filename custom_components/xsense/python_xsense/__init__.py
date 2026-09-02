"""Async X-Sense cloud, MQTT, and camera client library."""

from .device import Device
from .async_xsense import (
    AsyncXSense,
    camera_addx_serial,
    camera_for_identifier,
    camera_identifiers,
    camera_matches_identifier,
    camera_primary_identifiers,
    cameras_share_identity,
)
from .house import House
from .mqtt_helper import MQTTHelper
from .station import Station

__version__ = "0.1.0"

__all__ = [
    "AsyncXSense",
    "camera_addx_serial",
    "camera_for_identifier",
    "camera_identifiers",
    "camera_matches_identifier",
    "camera_primary_identifiers",
    "cameras_share_identity",
    "Device",
    "House",
    "MQTTHelper",
    "Station",
    "__version__",
]
