import json
import re
from pathlib import Path

from custom_components.xsense.python_xsense import AsyncXSense, __version__
from custom_components.xsense.python_xsense.async_xsense import (
    camera_live_resolution,
    is_camera_entity,
)


ROOT = Path(__file__).resolve().parents[1]
RELEASE_NOTES = ROOT / ".github" / "release-notes"
MANIFEST = ROOT / "custom_components" / "xsense" / "manifest.json"
FRONTEND = ROOT / "custom_components" / "xsense" / "frontend.py"
CHANGELOG = ROOT / "CHANGELOG.md"
HACS = ROOT / "hacs.json"
ISSUE_TEMPLATE = ROOT / ".github" / "ISSUE_TEMPLATE" / "custom.md"


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def _release_note_version(path: Path) -> str:
    return path.stem.removeprefix("v.").removeprefix("v")


def _latest_release_note_version() -> str:
    release_versions = [
        _release_note_version(path) for path in RELEASE_NOTES.glob("*.md")
    ]
    return max(release_versions, key=_version_key)


def _manifest_version() -> str:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return manifest["version"]


def _hacs_homeassistant_version() -> str:
    hacs = json.loads(HACS.read_text(encoding="utf-8"))
    return hacs["homeassistant"]


def test_manifest_version_matches_latest_release_note():
    assert _manifest_version() == _latest_release_note_version()


def test_frontend_panel_asset_version_matches_manifest():
    frontend = FRONTEND.read_text(encoding="utf-8")
    match = re.search(r'^PANEL_ASSET_VERSION = "([^"]+)"$', frontend, re.MULTILINE)

    assert match is not None
    assert match.group(1) == _manifest_version()


def test_changelog_top_entry_matches_manifest_version():
    version = _manifest_version()
    changelog = CHANGELOG.read_text(encoding="utf-8").splitlines()
    entries = [line for line in changelog if line.startswith("- [")]

    assert entries[0] == f"- [{version}](.github/release-notes/{version}.md)"


def test_latest_release_note_heading_matches_manifest_version():
    version = _manifest_version()
    release_note = RELEASE_NOTES / f"{version}.md"

    assert release_note.exists()
    assert release_note.read_text(encoding="utf-8").splitlines()[0] == (
        f"## X-Sense Home Security v{version}"
    )


def test_manifest_does_not_use_direct_wheel_requirement():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert not any(
        "wheemer-python-xsense@" in requirement
        or "github.com/Wheemer/python-xsense" in requirement
        for requirement in manifest["requirements"]
    )


def test_source_vendored_python_xsense_package_is_imported():
    assert __version__ == "0.1.0"


def test_python_xsense_package_exposes_current_integration_surface():
    assert AsyncXSense
    assert is_camera_entity
    assert camera_live_resolution
    assert hasattr(AsyncXSense, "update_camera_sleep")


def test_issue_template_versions_match_release_metadata():
    template = ISSUE_TEMPLATE.read_text(encoding="utf-8")

    assert _hacs_homeassistant_version() in template
    assert _manifest_version() in template
