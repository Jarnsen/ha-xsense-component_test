import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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
