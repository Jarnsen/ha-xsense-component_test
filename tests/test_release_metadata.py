import json
from importlib import metadata
import sys
from pathlib import Path

from xsense import AsyncXSense, House
from xsense.async_xsense import camera_live_resolution, is_camera_entity
from xsense.exceptions import APIFailure, AuthFailed, NotFoundError, SessionExpired


ROOT = Path(__file__).resolve().parents[1]
VENDOR_PATH = ROOT / "custom_components" / "xsense" / "_vendor"


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def _release_note_version(path: Path) -> str:
    return path.stem.removeprefix("v.").removeprefix("v")


def test_manifest_version_matches_latest_release_note():
    manifest = json.loads(
        (ROOT / "custom_components" / "xsense" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    release_versions = [
        _release_note_version(path)
        for path in (ROOT / ".github" / "release-notes").glob("*.md")
    ]
    latest_release_version = max(release_versions, key=_version_key)

    assert manifest["version"] == latest_release_version


def test_manifest_does_not_use_direct_wheel_requirement():
    manifest = json.loads(
        (ROOT / "custom_components" / "xsense" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert not any(
        "wheemer-python-xsense@" in requirement
        or "github.com/Wheemer/python-xsense" in requirement
        for requirement in manifest["requirements"]
    )


def test_vendored_python_xsense_package_is_imported():
    assert str(VENDOR_PATH) in sys.path
    assert str(VENDOR_PATH) in str(Path(sys.modules["xsense"].__file__).resolve())
    assert metadata.version("wheemer-python-xsense") == "0.1.0.dev2026070501"


def test_python_xsense_package_exposes_integration_imports():
    assert AsyncXSense
    assert House
    assert is_camera_entity
    assert camera_live_resolution
    assert APIFailure
    assert AuthFailed
    assert NotFoundError
    assert SessionExpired
