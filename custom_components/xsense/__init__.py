"""The X-Sense Home Security integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .coordinator import XSenseDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.ALARM_CONTROL_PANEL,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up X-Sense Home Security from a config entry."""
    coordinator = XSenseDataUpdateCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator: XSenseDataUpdateCoordinator | None = hass.data[DOMAIN].pop(
            entry.entry_id, None
        )
        if coordinator is not None:
            await coordinator.async_shutdown()

    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Allow users to remove XSense devices no longer returned by the cloud API."""
    coordinator: XSenseDataUpdateCoordinator | None = hass.data.get(DOMAIN, {}).get(
        entry.entry_id
    )
    if coordinator is None:
        return False

    data = coordinator.data
    if not data:
        return False

    current_identifiers = set()
    for station in data.get("stations", {}).values():
        current_identifiers.add(station.entity_id)
        current_identifiers.add(station.sn)

    for device in data.get("devices", {}).values():
        current_identifiers.add(device.entity_id)
        current_identifiers.add(device.sn)

    return not any(
        identifier
        for identifier in device_entry.identifiers
        if identifier[0] == DOMAIN and identifier[1] in current_identifiers
    )
