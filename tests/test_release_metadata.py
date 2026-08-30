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
RUNTIME_REQUIREMENTS = ROOT / "requirements-runtime.txt"
INTEGRATION = MANIFEST.parent
FRONTEND = ROOT / "custom_components" / "xsense" / "frontend.py"
RECORDINGS_PANEL = INTEGRATION / "frontend" / "recordings-panel.js"
HLS_JS = INTEGRATION / "frontend" / "vendor" / "hls.light.min.js"
PACKAGE_JSON = ROOT / "package.json"
CHANGELOG = ROOT / "CHANGELOG.md"
HACS = ROOT / "hacs.json"
ISSUE_TEMPLATE = ROOT / ".github" / "ISSUE_TEMPLATE" / "custom.md"
README_LOCALES = {
    "ar",
    "as",
    "cs",
    "da",
    "de",
    "el",
    "es",
    "et",
    "fa",
    "fi",
    "fr",
    "he",
    "hi",
    "hr",
    "hu",
    "id",
    "it",
    "ja",
    "ko",
    "lt",
    "lv",
    "nl",
    "no",
    "pl",
    "pt",
    "pt-BR",
    "ro",
    "ru",
    "sk",
    "sl",
    "sv",
    "th",
    "tr",
    "uk",
    "vi",
    "zh-CN",
    "zh-TW",
}
HA_ALIAS_LOCALES = {
    "nb",
    "zh-Hans",
    "zh-Hant",
}


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


def test_vendored_hls_js_version_is_current():
    source = HLS_JS.read_text(encoding="utf-8")
    package = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    version = package["devDependencies"]["hls.js"]

    assert source.count(f'"{version}"') == 1
    assert "sourceMappingURL=" not in source


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


def test_runtime_requirements_match_manifest():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    requirements = [
        line.strip()
        for line in RUNTIME_REQUIREMENTS.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    assert requirements == manifest["requirements"]


def test_manifest_does_not_reinstall_home_assistant_core_requirements():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    requirement_names = {
        re.split(r"[<>=!~]", requirement, maxsplit=1)[0].lower()
        for requirement in manifest["requirements"]
    }

    assert requirement_names.isdisjoint({"boto3", "botocore", "paho-mqtt"})


def test_legacy_pion_adapter_binaries_are_not_packaged():
    assert not list((INTEGRATION / "bin").glob("xsense_pion_adapter*"))


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


def _translation_leaf_paths(value: object, prefix: tuple[str, ...] = ()) -> set[tuple[str, ...]]:
    if isinstance(value, dict):
        paths: set[tuple[str, ...]] = set()
        for key, child in value.items():
            paths.update(_translation_leaf_paths(child, prefix + (key,)))
        return paths
    return {prefix}


def test_non_english_translations_match_english_shape():
    translations = INTEGRATION / "translations"
    english = json.loads((translations / "en.json").read_text(encoding="utf-8"))
    english_paths = _translation_leaf_paths(english)
    localized_files = sorted(
        path for path in translations.glob("*.json") if path.name != "en.json"
    )

    assert {path.stem for path in localized_files} == README_LOCALES | HA_ALIAS_LOCALES
    for path in localized_files:
        localized = json.loads(path.read_text(encoding="utf-8"))
        assert _translation_leaf_paths(localized) == english_paths


def _translation_placeholders(value: object) -> dict[tuple[str, ...], set[str]]:
    placeholders: dict[tuple[str, ...], set[str]] = {}
    for path in _translation_leaf_paths(value):
        cursor = value
        for key in path:
            cursor = cursor[key]
        found = set(re.findall(r"\{[a-z_]+\}", str(cursor)))
        if found:
            placeholders[path] = found
    return placeholders


def test_non_english_translations_preserve_placeholders():
    translations = INTEGRATION / "translations"
    english = json.loads((translations / "en.json").read_text(encoding="utf-8"))
    expected = _translation_placeholders(english)

    for path in translations.glob("*.json"):
        localized = json.loads(path.read_text(encoding="utf-8"))
        assert _translation_placeholders(localized) == expected


def test_translation_surfaces_do_not_contain_generator_tokens():
    translations = INTEGRATION / "translations"
    paths = [*translations.glob("*.json"), RECORDINGS_PANEL]

    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "placeholder" not in text.lower()
        assert "place holder" not in text.lower()
        assert "占位符" not in text
        assert "佔位符" not in text


def test_home_assistant_alias_translations_match_canonical_files():
    translations = INTEGRATION / "translations"
    alias_pairs = {
        "nb.json": "no.json",
        "zh-Hans.json": "zh-CN.json",
        "zh-Hant.json": "zh-TW.json",
    }

    for alias, canonical in alias_pairs.items():
        assert (translations / alias).read_text(encoding="utf-8") == (
            translations / canonical
        ).read_text(encoding="utf-8")


def test_recordings_panel_frontend_translations_stay_in_sync():
    panel = RECORDINGS_PANEL.read_text(encoding="utf-8")
    dictionaries = re.findall(
        r'^\s{2}"([^"]+)": \{(.*?)^\s{2}\}',
        panel,
        re.DOTALL | re.MULTILINE,
    )

    assert dictionaries
    keys_by_language = {
        language: set(re.findall(r"^\s{4}([a-zA-Z0-9]+):", body, re.MULTILINE))
        for language, body in dictionaries
    }
    assert set(keys_by_language) == {"en", *README_LOCALES}
    for language in README_LOCALES:
        assert keys_by_language[language] == keys_by_language["en"]
    assert "t(key, params = {})" in panel


def test_recordings_panel_language_resolution_handles_home_assistant_aliases():
    panel = RECORDINGS_PANEL.read_text(encoding="utf-8")

    assert '"pt-br": "pt-BR"' in panel
    assert '"zh-hans": "zh-CN"' in panel
    assert '"zh-hant": "zh-TW"' in panel
    assert '"nb": "no"' in panel
    assert "const exact = Object.keys(TRANSLATIONS).find" in panel


def test_recording_storage_modes_are_documented_in_every_locale():
    """Keep localized camera docs aligned with the current playback architecture."""
    readme_paths = sorted((ROOT / "readme").glob("README_*.md"))

    assert {path.stem.removeprefix("README_") for path in readme_paths} == {
        "en",
        "cn",
        *README_LOCALES,
    }
    for path in readme_paths:
        text = path.read_text(encoding="utf-8")
        assert text.count("<!-- xsense-recording-storage-modes -->") == 1, path.name
        assert "HLS" in text, path.name
        assert "/media/xsense_recordings" in text, path.name
