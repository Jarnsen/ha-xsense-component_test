"""Frontend panel registration for X-Sense recordings."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components import panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

FRONTEND_URL_PATH = "xsense-recordings"
STATIC_URL_PATH = f"/{DOMAIN}_recordings_static"
PANEL_ELEMENT_NAME = "xsense-recordings-panel"
PANEL_TITLE = "X-Sense Recordings"
PANEL_ASSET_VERSION = "1.4.10.4"


def _recordings_panel_module_url() -> str:
    """Return the recordings panel module URL with a release cache-buster."""
    return f"{STATIC_URL_PATH}/recordings-panel.js?v={PANEL_ASSET_VERSION}"


async def async_register_recordings_panel(hass: HomeAssistant) -> None:
    """Register the X-Sense recordings sidebar panel once."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get("_recordings_panel_registered"):
        return

    frontend_path = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                STATIC_URL_PATH,
                str(frontend_path),
                cache_headers=False,
            )
        ]
    )
    await panel_custom.async_register_panel(
        hass=hass,
        frontend_url_path=FRONTEND_URL_PATH,
        webcomponent_name=PANEL_ELEMENT_NAME,
        sidebar_title=PANEL_TITLE,
        sidebar_icon="mdi:video-box",
        module_url=_recordings_panel_module_url(),
        embed_iframe=False,
    )
    domain_data["_recordings_panel_registered"] = True


def async_unregister_recordings_panel(hass: HomeAssistant) -> None:
    """Remove the X-Sense recordings sidebar panel if it was registered."""
    frontend.async_remove_panel(hass, FRONTEND_URL_PATH, warn_if_unknown=False)
    hass.data.setdefault(DOMAIN, {}).pop("_recordings_panel_registered", None)


def recordings_panel_url(
    entry_id: str,
    serial: str,
    start_time: int,
    *,
    base_url: str | None = None,
    end_time: int | None = None,
) -> str:
    """Return a deep link into the X-Sense recordings sidebar panel."""
    from urllib.parse import quote, urlencode

    params = {
        "entry_id": str(entry_id),
        "serial": str(serial),
        "start": str(int(start_time)),
    }
    if end_time is not None:
        params["end"] = str(int(end_time))
    path = f"/{FRONTEND_URL_PATH}#{urlencode(params, quote_via=quote)}"
    if not base_url:
        return path
    return f"{base_url.rstrip('/')}{path}"
