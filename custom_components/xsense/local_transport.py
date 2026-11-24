"""Verified SBS50 MQTT topics and persisted per-detector transport choices."""

import re
from types import SimpleNamespace
from typing import Any

from .python_xsense.device import Device
from .python_xsense.station import Station

CONF_LOCAL_MQTT_ONLY = "local_mqtt_only"
_SMOKE_MODELS = frozenset({"XS0B-MR", "XS01-M"})
_SERIAL = re.compile(r"[0-9A-Fa-f]{8}")


def local_state_mapping(model: str, key: str) -> tuple[str, str, str] | None:
    """Return only the topics and payloads verified against captured packets."""
    if model == "XH02-M" and key == "alarm_status":
        return "heatalarm", "Detected", "Cleared"
    if model in _SMOKE_MODELS:
        if key == "alarm_status":
            return "smokealarm", "Detected", "Cleared"
        if key == "is_life_end":
            return "lifeend", "EOL", "Normal"
    return None


def local_availability_topic(device: Any) -> str | None:
    """Use only the detector connectivity topics verified for these models."""
    if local_device_key(device) is None:
        return None
    node = f"SBS50{device.station.sn}_{device.sn}"
    return f"homeassistant/binary_sensor/{node}/{node}_online/state"


def local_device_key(device: Any) -> str | None:
    """Identify an eligible detector and its station, not a cloud object ID."""
    if not isinstance(device, Device) or getattr(device.station, "type", None) != "SBS50":
        return None
    station_sn, child_sn = device.station.sn, device.sn
    if (
        local_state_mapping(device.type, "alarm_status") is None
        or not isinstance(station_sn, str) or not _SERIAL.fullmatch(station_sn)
        or not isinstance(child_sn, str) or not _SERIAL.fullmatch(child_sn)
    ):
        return None
    return f"{station_sn.casefold()}:{child_sn.casefold()}"


def local_state_topic(device: Any, key: str) -> str | None:
    if local_device_key(device) is None or (mapping := local_state_mapping(device.type, key)) is None:
        return None
    node = f"SBS50{device.station.sn}_{device.sn}"
    return f"homeassistant/binary_sensor/{node}/{node}_{mapping[0]}/state"


def local_device_record(device: Device) -> dict[str, str | None]:
    """Persist identity only. Do not save cloud state, broker settings or secrets."""
    return {
        "station_sn": device.station.sn,
        "station_id": str(device.station.entity_id or device.station.sn),
        "station_name": device.station.name or "SBS50",
        "device_sn": device.sn,
        "device_id": str(device.entity_id or device.sn),
        "device_name": device.name or device.type,
        "model": device.type,
        "house_id": getattr(device.station.house, "house_id", None),
    }


def restore_local_devices(options) -> dict[str, Device]:
    """Rebuild local-only inventory without making an X-Sense API request."""
    stored = options.get(CONF_LOCAL_MQTT_ONLY, {})
    if not isinstance(stored, dict):
        return {}
    devices = {}
    fields = ("station_sn", "station_id", "station_name", "device_sn",
              "device_id", "device_name", "model")
    for key, record in stored.items():
        if not isinstance(record, dict) or any(
            not isinstance(record.get(field), str) or not record[field] for field in fields
        ):
            continue
        house = SimpleNamespace(house_id=record.get("house_id"))
        station = Station(house, stationSn=record["station_sn"], stationId=record["station_id"],
                          stationName=record["station_name"], category="SBS50")
        device = Device(station, deviceSn=record["device_sn"], deviceId=record["device_id"],
                        deviceName=record["device_name"], deviceType=record["model"])
        if local_device_key(device) != key:
            continue
        device.local_mqtt_only = True
        lookup_id = device.entity_id if device.entity_id not in devices else f"local-mqtt:{key}"
        devices[lookup_id] = device
    return devices
