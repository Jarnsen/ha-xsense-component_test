"""Shared helpers for camera-gated X-Sense recordings runtime."""

from __future__ import annotations

from contextlib import suppress

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .python_xsense.async_xsense import is_camera_entity


def has_camera_entities(data) -> bool:
    """Return whether refreshed X-Sense account data contains cameras."""
    for entity in (
        *data.get("stations", {}).values(),
        *data.get("devices", {}).values(),
    ):
        with suppress(AttributeError):
            if is_camera_entity(entity):
                return True
    return False


def has_registered_camera_entities(hass: HomeAssistant) -> bool:
    """Return whether Home Assistant has registered X-Sense camera entities."""
    with suppress(Exception):
        registry = er.async_get(hass)
        return any(
            entry.domain == "camera" and entry.platform == DOMAIN
            for entry in registry.entities.values()
        )
    return False


def has_any_camera_entities(hass: HomeAssistant) -> bool:
    """Return whether X-Sense recordings features should be available."""
    if has_registered_camera_entities(hass):
        return True
    for coordinator in getattr(hass, "data", {}).get(DOMAIN, {}).values():
        data = getattr(coordinator, "data", None)
        if isinstance(data, dict) and has_camera_entities(data):
            return True
    return False
