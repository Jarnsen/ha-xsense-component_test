"""Diagnostics support for XSense."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import XSenseDataUpdateCoordinator

TO_REDACT = {
    CONF_EMAIL,
    CONF_PASSWORD,
    "adminId",
    "cameraAudioUrl",
    "cameraLiveId",
    "cameraLiveUrl",
    "deviceId",
    "ipcId",
    "ipcSn",
    "networkName",
    "stationId",
    "thumbImgUrl",
    "title",
    "unique_id",
    "userId",
}


def entity_diagnostics(entity) -> dict[str, Any]:
    """Return diagnostic data for an X-Sense entity."""
    return {
        "type": entity.type,
        "serial_number": getattr(entity, "sn", None),
        "data": async_redact_data(entity.data, TO_REDACT),
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    coordinator: XSenseDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "data": {
            "stations": [
                entity_diagnostics(station)
                for station in coordinator.data["stations"].values()
            ],
            "devices": [
                entity_diagnostics(device)
                for device in coordinator.data["devices"].values()
            ],
        },
    }
