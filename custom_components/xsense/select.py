"""Support for X-Sense select settings."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.components.select import SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


SELECTS: tuple[SelectEntityDescription, ...] = ()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up X-Sense select entities."""
    async_add_entities([])
