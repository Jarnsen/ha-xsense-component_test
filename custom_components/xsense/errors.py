"""Translatable Home Assistant errors for X-Sense."""

from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN


def xsense_error(
    translation_key: str,
    **translation_placeholders: object,
) -> HomeAssistantError:
    """Return a translatable Home Assistant error."""
    placeholders = {
        key: str(value) for key, value in translation_placeholders.items()
    } or None
    return HomeAssistantError(
        translation_domain=DOMAIN,
        translation_key=translation_key,
        translation_placeholders=placeholders,
    )
