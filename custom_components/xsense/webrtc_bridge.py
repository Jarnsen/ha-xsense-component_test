"""X-Sense WebRTC bridge client.

This module is the Home Assistant side of the experimental Pion bridge path.
The bridge terminates the X-Sense APK-style WebRTC session and exposes a normal
stream URL for go2rtc/Alex to consume without transcoding.
"""

from __future__ import annotations

from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api.async_xsense import camera_live_resolution
from .const import LOGGER

DEFAULT_BRIDGE_URL = "http://127.0.0.1:39091"
_START_TIMEOUT = aiohttp.ClientTimeout(total=15)


async def async_get_xsense_bridge_stream_source(
    hass: HomeAssistant,
    coordinator,
    entity,
    *,
    bridge_url: str = DEFAULT_BRIDGE_URL,
) -> str | None:
    """Return a go2rtc-compatible stream URL from the X-Sense WebRTC bridge."""
    ticket_data = await coordinator.xsense.get_camera_webrtc_ticket(
        entity, force_refresh=True
    )
    LOGGER.debug(
        "X-Sense WebRTC bridge ticket received: %s",
        _ticket_data_debug_context(ticket_data),
    )
    if not isinstance(ticket_data, dict):
        return None

    payload = {
        "camera": {
            "serialNumber": getattr(entity, "sn", None),
            "resolution": camera_live_resolution(entity),
            "model": entity.data.get("cameraModel") or entity.data.get("modelNo"),
        },
        "ticket": ticket_data,
        "debug": True,
    }
    LOGGER.debug(
        "X-Sense WebRTC bridge session requested: %s",
        _bridge_debug_context(
            bridge_url,
            entity,
            ticket=_ticket_data_debug_context(ticket_data),
        ),
    )
    session = async_get_clientsession(hass)
    try:
        async with session.post(
            f"{bridge_url.rstrip('/')}/api/xsense/sessions",
            json=payload,
            timeout=_START_TIMEOUT,
        ) as response:
            if response.status >= 400:
                LOGGER.debug(
                    "X-Sense WebRTC bridge session rejected: %s",
                    _bridge_debug_context(
                        bridge_url,
                        entity,
                        status=response.status,
                    ),
                )
                return None
            data = await response.json()
    except (aiohttp.ClientError, TimeoutError) as err:
        LOGGER.debug(
            "X-Sense WebRTC bridge request failed: %s",
            _bridge_debug_context(
                bridge_url,
                entity,
                error=type(err).__name__,
            ),
        )
        return None

    stream_url = data.get("streamUrl") if isinstance(data, dict) else None
    if not isinstance(stream_url, str) or not stream_url:
        LOGGER.debug(
            "X-Sense WebRTC bridge returned no stream URL: %s",
            _bridge_debug_context(
                bridge_url,
                entity,
                response_type=type(data).__name__,
                response_keys=sorted(data) if isinstance(data, dict) else None,
            ),
        )
        return None

    LOGGER.debug(
        "X-Sense WebRTC bridge stream source ready: %s",
        _bridge_debug_context(
            bridge_url,
            entity,
            source_protocol=_stream_source_protocol(stream_url),
        ),
    )
    return stream_url


def _ticket_data_debug_context(ticket_data: Any) -> dict[str, Any]:
    """Return safe ticket metadata for debug logs."""
    if not isinstance(ticket_data, dict):
        return {"type": type(ticket_data).__name__}
    return {
        "keys": sorted(key for key in ticket_data if key not in {"sign"}),
        "has_sign": bool(ticket_data.get("sign")),
        "has_signal_ip": bool(ticket_data.get("signalServerIpAddress")),
        "ice_servers": len(ticket_data.get("iceServer") or []),
        "has_expiration": ticket_data.get("expirationTime") not in (None, ""),
        "ticket_id": _short_id(ticket_data.get("id")),
    }


def _bridge_debug_context(
    bridge_url: str, entity, **extra: Any
) -> dict[str, Any]:
    """Return bridge debug context without tokens or full serials."""
    context = {
        "bridge_host": _safe_bridge_host(bridge_url),
        "camera": _short_id(getattr(entity, "sn", None)),
        "model": entity.data.get("cameraModel") or entity.data.get("modelNo"),
        "resolution": camera_live_resolution(entity),
    }
    context.update(extra)
    return context


def _safe_bridge_host(bridge_url: str) -> str:
    """Return a log-safe bridge endpoint label."""
    return bridge_url.removeprefix("http://").removeprefix("https://").split("/", 1)[
        0
    ]


def _short_id(value):
    """Return a short diagnostic id without logging full serial-like values."""
    if value in (None, ""):
        return None
    text = str(value)
    return text if len(text) <= 6 else f"...{text[-6:]}"


def _stream_source_protocol(source: str | None) -> str | None:
    """Return a stream source protocol without exposing the source URL."""
    if not isinstance(source, str) or "://" not in source:
        return None
    return source.split("://", 1)[0].lower()
