"""Home Assistant media_source platform entry point.

Home Assistant auto-discovers this filename and requires ``async_get_media_source``.
The implementation lives in ``recordings_media.py`` so runtime registration can stay
camera-gated in ``__init__.py`` without breaking platform discovery on reload.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .recordings_gate import has_any_camera_entities
from .recordings_media import XSenseRecordingsMediaSource


async def async_get_media_source(hass: HomeAssistant) -> XSenseRecordingsMediaSource:
    """Return the X-Sense recordings media source when cameras are available."""
    if not has_any_camera_entities(hass):
        raise HomeAssistantError(
            "X-Sense recordings are unavailable without a supported camera"
        )
    return XSenseRecordingsMediaSource(hass)
