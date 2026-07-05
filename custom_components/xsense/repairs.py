"""Maintenance checks for the X-Sense integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.core import HomeAssistant

from .const import LOGGER

CAMERA_BLUEPRINT_VERSION = 8
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
    "xsense_include_recording_link and xsense_recording_tap_url and xsense_recording_media_url",
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
    result = await hass.async_add_executor_job(
        _update_stale_camera_blueprints,
        blueprint_dir,
        _bundled_camera_blueprint_path(),
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
    bundled_blueprint_path: Path,
) -> dict[str, list[str]]:
    """Update stale imported X-Sense camera blueprints in place."""
    result: dict[str, list[str]] = {"updated": [], "failed": []}
    if not blueprint_dir.exists():
        return result
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

    for path in _stale_camera_blueprint_paths(blueprint_dir):
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


def _stale_camera_blueprint_paths(blueprint_dir: Path) -> list[Path]:
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
        if not _is_stale_camera_blueprint(text):
            continue
        stale_files.append(path)

    return stale_files


def _is_xsense_camera_blueprint(text: str) -> bool:
    """Return whether the YAML text looks like the X-Sense camera blueprint."""
    return any(marker in text for marker in _CAMERA_BLUEPRINT_MARKERS)


def _is_current_camera_blueprint(text: str) -> bool:
    """Return whether the imported blueprint has the current safe templates."""
    return all(marker in text for marker in _CURRENT_BLUEPRINT_MARKERS)


def _is_stale_camera_blueprint(text: str) -> bool:
    """Return whether an X-Sense camera blueprint has unsafe old templates."""
    if _is_current_camera_blueprint(text):
        return False
    if (
        "xsense_blueprint_version: 2" in text
        or "xsense_blueprint_version: 3" in text
        or "xsense_blueprint_version: 4" in text
        or "xsense_blueprint_version: 5" in text
        or "xsense_blueprint_version: 6" in text
        or "xsense_blueprint_version: 7" in text
    ):
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
