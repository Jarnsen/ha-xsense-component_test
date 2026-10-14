"""Prevent new English fallbacks without rejecting legitimate shared terms."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
TRANSLATIONS = ROOT / "custom_components/xsense/translations"
ENGLISH = json.loads((TRANSLATIONS / "en.json").read_text(encoding="utf-8"))
ALLOWLIST = json.loads(
    (ROOT / "tests/fixtures/translation_identical_terms.json").read_text(encoding="utf-8")
)
ALIASES = {"nb": "no", "zh-Hans": "zh-CN", "zh-Hant": "zh-TW"}
# Protocol/storage identifiers and video-quality abbreviations are not prose.
SHARED_TERMS = {"SSID", "HD", "SD"}


def _leaves(data, prefix=()):
    if isinstance(data, dict):
        return {
            path: value
            for key, child in data.items()
            for path, value in _leaves(child, (*prefix, key)).items()
        }
    assert isinstance(data, str), prefix
    return {".".join(prefix): data}


@pytest.mark.parametrize(
    "path", sorted(p for p in TRANSLATIONS.glob("*.json") if p.stem != "en"),
    ids=lambda p: p.stem,
)
def test_no_unreviewed_english_fallbacks(path):
    source = _leaves(ENGLISH)
    local = _leaves(json.loads(path.read_text(encoding="utf-8")))
    assert local.keys() == source.keys()
    exemptions = ALLOWLIST.get(ALIASES.get(path.stem, path.stem), {})
    unchanged = {
        key for key, text in local.items()
        if text == source[key] and text not in SHARED_TERMS
    }
    assert unchanged == exemptions.keys(), {
        "untranslated": sorted(unchanged - exemptions.keys()),
        "stale_exemptions": sorted(exemptions.keys() - unchanged),
    }
    for key, exemption in exemptions.items():
        assert exemption["text"] == source[key] == local[key]
        assert exemption["reason"].strip(), (path.stem, key)


def test_identical_term_exemptions_only_name_canonical_locales():
    canonical = {
        p.stem for p in TRANSLATIONS.glob("*.json")
        if p.stem != "en" and p.stem not in ALIASES
    }
    assert ALLOWLIST.keys() <= canonical


def test_reviewed_device_lifetime_and_recording_interval_terms():
    reviewed = json.loads(
        (ROOT / "tests/fixtures/translation_semantic_terms.json").read_text(
            encoding="utf-8"
        )
    )
    assert reviewed
    for locale, terms in reviewed.items():
        local = _leaves(json.loads(
            (TRANSLATIONS / f"{locale}.json").read_text(encoding="utf-8")
        ))
        for key, expected in terms.items():
            assert local[key] == expected, (locale, key)
