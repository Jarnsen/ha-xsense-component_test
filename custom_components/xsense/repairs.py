"""Repair checks for the X-Sense integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN, LOGGER

CAMERA_BLUEPRINT_VERSION = 6
CAMERA_BLUEPRINT_ISSUE_ID = "stale_camera_notification_blueprint"
CAMERA_BLUEPRINT_IMPORT_URL = (
    "https://my.home-assistant.io/redirect/blueprint_import/"
    "?blueprint_url=https%3A%2F%2Fgithub.com%2FJarnsen%2F"
    "ha-xsense-component_test%2Fblob%2Fmain%2Fblueprints%2F"
    "automation%2Fxsense%2Fcamera_ai_notification.yaml"
)
_CAMERA_BLUEPRINT_MARKERS = (
    "X-Sense Camera Event",
    "camera_ai_notification.yaml",
    "Jarnsen/ha-xsense-component_test",
)
_CURRENT_BLUEPRINT_MARKERS = (
    "xsense_event_data is mapping",
    "event_type: xsense_camera_event",
    "state_attr(xsense_event_entity, 'recording_media_url')",
    "xsense_recording_url[0:19] == '/xsense-recordings#'",
    "xsense_notification_url",
    "xsense_include_recording_link and xsense_recording_tap_url and xsense_recording_media_url",
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
    """Create a repair issue when imported X-Sense camera blueprints are stale."""
    blueprint_dir = Path(hass.config.path("blueprints", "automation"))
    stale_files = await hass.async_add_executor_job(
        _stale_camera_blueprint_files,
        blueprint_dir,
    )
    if not stale_files:
        ir.async_delete_issue(hass, DOMAIN, CAMERA_BLUEPRINT_ISSUE_ID)
        return

    file_list = ", ".join(stale_files[:5])
    if len(stale_files) > 5:
        file_list = f"{file_list}, ..."

    ir.async_create_issue(
        hass,
        DOMAIN,
        CAMERA_BLUEPRINT_ISSUE_ID,
        is_fixable=False,
        is_persistent=True,
        learn_more_url=CAMERA_BLUEPRINT_IMPORT_URL,
        severity=ir.IssueSeverity.WARNING,
        translation_key=CAMERA_BLUEPRINT_ISSUE_ID,
        translation_placeholders={
            "files": file_list,
            "import_url": CAMERA_BLUEPRINT_IMPORT_URL,
        },
    )


def _stale_camera_blueprint_files(blueprint_dir: Path) -> list[str]:
    """Return imported X-Sense camera notification blueprints that need updating."""
    if not blueprint_dir.exists():
        return []

    stale_files: list[str] = []
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
        stale_files.append(_relative_blueprint_path(blueprint_dir, path))

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
    """Return a readable blueprint path for a repair issue."""
    try:
        return path.relative_to(blueprint_dir).as_posix()
    except ValueError:
        return path.as_posix()
