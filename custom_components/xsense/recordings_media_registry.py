"""Home Assistant version compatibility for camera-gated media sources."""

from __future__ import annotations

from contextlib import suppress

from homeassistant.core import HomeAssistant

from .const import DOMAIN


def async_hide_recordings_media_source(hass: HomeAssistant) -> None:
    """Remove X-Sense recordings from the Media Browser across HA versions."""
    _domain_data(hass).pop("_recordings_media_source_registered", None)

    with suppress(Exception):
        from homeassistant.components.media_source.const import (
            DATA_MEDIA_SOURCE_PLATFORMS,
        )

        if (platforms := hass.data.get(DATA_MEDIA_SOURCE_PLATFORMS)) is not None:
            platforms._processed[DOMAIN] = None
            return

    with suppress(ImportError):
        from homeassistant.components.media_source.const import MEDIA_SOURCE_DATA

        hass.data.get(MEDIA_SOURCE_DATA, {}).pop(DOMAIN, None)
        return

    with suppress(AttributeError, TypeError):
        hass.data.get("media_source", {}).pop(DOMAIN, None)


def async_show_recordings_media_source(hass: HomeAssistant) -> None:
    """Expose X-Sense recordings in the Media Browser across HA versions."""
    domain_data = _domain_data(hass)
    if domain_data.get("_recordings_media_source_registered"):
        return

    with suppress(Exception):
        from homeassistant.components.media_source.const import (
            DATA_MEDIA_SOURCE_PLATFORMS,
        )

        if (platforms := hass.data.get(DATA_MEDIA_SOURCE_PLATFORMS)) is not None:
            platforms._processed.pop(DOMAIN, None)
            domain_data["_recordings_media_source_registered"] = True
            return

    registry = _explicit_media_source_registry(hass)
    if registry is None:
        return

    from .recordings_media import XSenseRecordingsMediaSource

    registry[DOMAIN] = XSenseRecordingsMediaSource(hass)
    domain_data["_recordings_media_source_registered"] = True


def _explicit_media_source_registry(hass: HomeAssistant) -> dict | None:
    with suppress(ImportError):
        from homeassistant.components.media_source.const import MEDIA_SOURCE_DATA

        return hass.data.setdefault(MEDIA_SOURCE_DATA, {})
    with suppress(AttributeError, TypeError):
        registry = hass.data.setdefault("media_source", {})
        if isinstance(registry, dict):
            return registry
    return None


def _domain_data(hass: HomeAssistant) -> dict:
    with suppress(AttributeError, TypeError):
        return hass.data.setdefault(DOMAIN, {})
    return {}
