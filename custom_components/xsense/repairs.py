"""Maintenance checks for the X-Sense integration."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, UTC
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, LOGGER

CAMERA_BLUEPRINT_VERSION = 10
CAMERA_BLUEPRINT_REMOTE_URL = (
    "https://raw.githubusercontent.com/Jarnsen/ha-xsense-component_test/main/"
    "blueprints/automation/xsense/camera_ai_notification.yaml"
)
CAMERA_BLUEPRINT_REMOTE_CHECK_INTERVAL = timedelta(hours=1)
CAMERA_BLUEPRINT_REMOTE_TIMEOUT = 10
_REMOTE_BLUEPRINT_CACHE_KEY = "_camera_blueprint_remote"
_REMOTE_BLUEPRINT_CHECKED_KEY = "_camera_blueprint_remote_checked"
_BLUEPRINT_VERSION_RE = re.compile(r"^\s*xsense_blueprint_version:\s*(\d+)\s*$", re.MULTILINE)
_CAMERA_BLUEPRINT_MARKERS = (
    "X-Sense Camera Event",
    "camera_ai_notification.yaml",
    "Jarnsen/ha-xsense-component_test",
)
_CURRENT_BLUEPRINT_MARKERS = (
    "xsense_event_data is mapping",
    "event_type: xsense_camera_event",
    "xsense_has_trigger_data",
    "state_attr(xsense_event_entity, 'recording_media_url')",
    "xsense_recording_cache_ready",
    "xsense_recording_url[0:19] == '/xsense-recordings#'",
    "xsense_notification_url",
    "image: \"{{ xsense_snapshot_url }}\"",
    "xsense_include_recording_link and xsense_recording_tap_url and xsense_recording_cache_ready",
    "not xsense_include_recording_link and (xsense_event_data.get('recording_cache_ready') if xsense_event_data is mapping else false) != true",
)
_UNSAFE_EVENT_DATA_GET_MARKERS = (
    "xsense_event_data.get('event_type')",
    'xsense_event_data.get("event_type")',
    "xsense_event_data.get('recording_url')",
    'xsense_event_data.get("recording_url")',
    "xsense_event_data.get('recording_media_url')",
    'xsense_event_data.get("recording_media_url")',
)


async def async_check_stale_camera_blueprints(hass: HomeAssistant) -> None:
    """Update imported X-Sense camera blueprints."""
    blueprint_dir = Path(hass.config.path("blueprints", "automation"))
    replacement = await _async_camera_blueprint_replacement(hass)
    result = await hass.async_add_executor_job(
        _update_stale_camera_blueprints,
        blueprint_dir,
        replacement,
    )
    if result["updated"]:
        LOGGER.debug(
            "Updated imported X-Sense camera notification blueprints: %s",
            ", ".join(result["updated"]),
        )
        await _async_reload_automations(hass)
    if result["failed"]:
        LOGGER.debug(
            "Could not update imported X-Sense camera notification blueprints: %s",
            ", ".join(result["failed"]),
        )


async def _async_camera_blueprint_replacement(hass: HomeAssistant) -> str | None:
    """Return the newest known camera blueprint text."""
    remote = await _async_fetch_remote_camera_blueprint(hass)
    if remote is not None:
        return remote
    return None


async def _async_fetch_remote_camera_blueprint(hass: HomeAssistant) -> str | None:
    """Fetch the published camera blueprint when the remote check is due."""
    hass_data = getattr(hass, "data", None)
    if hass_data is None:
        return None
    domain_data = hass_data.setdefault(DOMAIN, {})
    now = datetime.now(UTC)
    checked_at = domain_data.get(_REMOTE_BLUEPRINT_CHECKED_KEY)
    if isinstance(checked_at, datetime) and (
        now - checked_at < CAMERA_BLUEPRINT_REMOTE_CHECK_INTERVAL
    ):
        return domain_data.get(_REMOTE_BLUEPRINT_CACHE_KEY)

    domain_data[_REMOTE_BLUEPRINT_CHECKED_KEY] = now
    session = async_get_clientsession(hass)
    try:
        async with session.get(
            CAMERA_BLUEPRINT_REMOTE_URL,
            timeout=CAMERA_BLUEPRINT_REMOTE_TIMEOUT,
        ) as response:
            if response.status != 200:
                LOGGER.debug(
                    "X-Sense camera blueprint remote check skipped: %s",
                    response.status,
                )
                return domain_data.get(_REMOTE_BLUEPRINT_CACHE_KEY)
            text = await response.text()
    except Exception as err:  # noqa: BLE001 - remote update should never break setup.
        LOGGER.debug("X-Sense camera blueprint remote check failed: %s", err)
        return domain_data.get(_REMOTE_BLUEPRINT_CACHE_KEY)

    if not _is_xsense_camera_blueprint(text):
        LOGGER.debug("X-Sense camera blueprint remote check ignored unexpected content")
        return domain_data.get(_REMOTE_BLUEPRINT_CACHE_KEY)

    remote_version = _camera_blueprint_version(text)
    if remote_version is None:
        LOGGER.debug("X-Sense camera blueprint remote check ignored missing version")
        return domain_data.get(_REMOTE_BLUEPRINT_CACHE_KEY)

    domain_data[_REMOTE_BLUEPRINT_CACHE_KEY] = text
    LOGGER.debug(
        "X-Sense camera blueprint remote check found version %s",
        remote_version,
    )
    return text


async def _async_reload_automations(hass: HomeAssistant) -> None:
    """Reload automations after a blueprint file update when supported."""
    services = getattr(hass, "services", None)
    if services is None or not hasattr(services, "has_service"):
        return
    if not services.has_service("automation", "reload"):
        return
    await services.async_call("automation", "reload", blocking=False)


def _bundled_camera_blueprint_path() -> Path:
    """Return the bundled X-Sense camera notification blueprint path."""
    paths = (
        Path(__file__).parent / "blueprints" / "camera_ai_notification.yaml",
        Path(__file__).parents[2]
        / "blueprints"
        / "automation"
        / "xsense"
        / "camera_ai_notification.yaml",
    )
    for path in paths:
        if path.exists():
            return path
    return paths[0]


def _update_stale_camera_blueprints(
    blueprint_dir: Path,
    replacement: str | None = None,
) -> dict[str, list[str]]:
    """Update stale imported X-Sense camera blueprints in place."""
    result: dict[str, list[str]] = {"updated": [], "failed": []}
    if not blueprint_dir.exists():
        return result
    replacement_version = (
        _camera_blueprint_version(replacement) if replacement is not None else None
    )
    if replacement_version is not None and replacement_version < CAMERA_BLUEPRINT_VERSION:
        replacement = None
        replacement_version = None
    if replacement is None:
        bundled_blueprint_path = _bundled_camera_blueprint_path()
        try:
            replacement = bundled_blueprint_path.read_text(encoding="utf-8")
        except OSError as err:
            LOGGER.debug(
                "Unable to read bundled X-Sense camera blueprint %s: %s",
                bundled_blueprint_path,
                err,
            )
            result["failed"] = _stale_camera_blueprint_files(blueprint_dir)
            return result
    replacement_version = replacement_version or _camera_blueprint_version(replacement)
    replacement_version = replacement_version or CAMERA_BLUEPRINT_VERSION

    for path in _stale_camera_blueprint_paths(blueprint_dir, replacement_version):
        relative = _relative_blueprint_path(blueprint_dir, path)
        try:
            path.write_text(replacement, encoding="utf-8")
        except OSError as err:
            LOGGER.debug("Unable to update X-Sense blueprint %s: %s", path, err)
            result["failed"].append(relative)
            continue
        result["updated"].append(relative)
    return result


def _stale_camera_blueprint_files(blueprint_dir: Path) -> list[str]:
    """Return imported X-Sense camera notification blueprints that need updating."""
    return [
        _relative_blueprint_path(blueprint_dir, path)
        for path in _stale_camera_blueprint_paths(blueprint_dir)
    ]


def _stale_camera_blueprint_paths(
    blueprint_dir: Path,
    current_version: int = CAMERA_BLUEPRINT_VERSION,
) -> list[Path]:
    """Return imported X-Sense camera notification blueprint paths to update."""
    if not blueprint_dir.exists():
        return []

    stale_files: list[Path] = []
    for path in sorted(blueprint_dir.rglob("*.yaml")):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as err:
            LOGGER.debug("Unable to read X-Sense blueprint candidate %s: %s", path, err)
            continue

        if not _is_xsense_camera_blueprint(text):
            continue
        if not _is_stale_camera_blueprint(text, current_version):
            continue
        stale_files.append(path)

    return stale_files


def _is_xsense_camera_blueprint(text: str) -> bool:
    """Return whether the YAML text looks like the X-Sense camera blueprint."""
    return any(marker in text for marker in _CAMERA_BLUEPRINT_MARKERS)


def _is_current_camera_blueprint(text: str) -> bool:
    """Return whether the imported blueprint has the current safe templates."""
    return all(marker in text for marker in _CURRENT_BLUEPRINT_MARKERS)


def _camera_blueprint_version(text: str) -> int | None:
    """Return the X-Sense camera blueprint marker version."""
    match = _BLUEPRINT_VERSION_RE.search(text)
    if match is None:
        return None
    return int(match.group(1))


def _is_stale_camera_blueprint(
    text: str,
    current_version: int = CAMERA_BLUEPRINT_VERSION,
) -> bool:
    """Return whether an X-Sense camera blueprint has unsafe old templates."""
    version = _camera_blueprint_version(text)
    if version is not None and version < current_version:
        return True
    if _is_current_camera_blueprint(text):
        return False
    if (
        "xsense_blueprint_version: 2" in text
        or "xsense_blueprint_version: 3" in text
        or "xsense_blueprint_version: 4" in text
        or "xsense_blueprint_version: 5" in text
        or "xsense_blueprint_version: 6" in text
        or "xsense_blueprint_version: 7" in text
        or "xsense_blueprint_version: 8" in text
        or "xsense_blueprint_version: 9" in text
    ):
        return True
    if "Snapshot: {{ xsense_snapshot_url }}" in text:
        return True
    if "trigger: event.received" in text:
        return True
    if "/media/local" in text and "xsense_recording_tap_url" in text:
        return True
    if "xsense_recording_tap_url" in text and "xsense_notification_url" not in text:
        return True
    if "Open X-Sense Recordings to view recent clips" in text:
        return True
    return any(marker in text for marker in _UNSAFE_EVENT_DATA_GET_MARKERS)


def _relative_blueprint_path(blueprint_dir: Path, path: Path) -> str:
    """Return a readable blueprint path."""
    try:
        return path.relative_to(blueprint_dir).as_posix()
    except ValueError:
        return path.as_posix()
