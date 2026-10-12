"""Localization contracts for X-Sense services and force-arm notifications."""

import json
import re
import string
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
import voluptuous as vol
import yaml

from custom_components.xsense import alarm_control_panel as alarm

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components/xsense"
LOCALES = sorted((INTEGRATION / "translations").glob("*.json"))
SOURCE = json.loads((INTEGRATION / "strings.json").read_text(encoding="utf-8"))
SERVICES = yaml.safe_load((INTEGRATION / "services.yaml").read_text(encoding="utf-8"))


def leaves(data, prefix=()):
    if isinstance(data, dict):
        return {
            path: value
            for key, child in data.items()
            for path, value in leaves(child, (*prefix, key)).items()
        }
    return {".".join(prefix): data}


def placeholders(value):
    return Counter(
        field for _, field, _, _ in string.Formatter().parse(value)
        if field is not None
    )


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, f"Duplicate JSON key: {key}"
        result[key] = value
    return result


@pytest.mark.parametrize("path", LOCALES, ids=lambda path: path.stem)
def test_all_locale_leaf_and_placeholder_contracts(path):
    localized = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_keys)
    expected = leaves(SOURCE)
    actual = leaves(localized)
    assert actual.keys() == expected.keys()
    for key, value in actual.items():
        assert isinstance(value, str) and value.strip(), key
        assert placeholders(value) == placeholders(expected[key]), key
        assert "[%key:" not in value, key
    assert set(localized["selector"]["force_arm_mode"]["options"]) == {"home", "away"}


@pytest.mark.parametrize("path", LOCALES, ids=lambda path: path.stem)
def test_service_names_descriptions_and_all_fields_are_localized(path):
    localized = json.loads(path.read_text(encoding="utf-8"))
    assert set(SERVICES) == set(SOURCE["services"])
    assert set(localized["services"]) == set(SERVICES)
    for key, schema in SERVICES.items():
        text = localized["services"][key]
        assert text["name"].strip()
        assert text["description"].strip()
        assert set(text.get("fields", {})) == set(schema.get("fields", {}))
        for field in text.get("fields", {}).values():
            assert field["name"].strip()
        if path.stem != "en":
            assert text["name"] != SOURCE["services"][key]["name"], (path.stem, key)
            assert text["description"] != SOURCE["services"][key]["description"], (path.stem, key)
    for key in ("refresh_recordings", "cache_recordings", "clear_recordings_cache"):
        assert localized["services"][key]["fields"]["entry_id"]["description"].strip()


@pytest.mark.parametrize("path", LOCALES, ids=lambda path: path.stem)
def test_required_abort_and_cache_failure_messages(path):
    localized = json.loads(path.read_text(encoding="utf-8"))
    mismatch = localized["config"]["abort"]["unique_id_mismatch"]
    assert mismatch.strip()
    error = localized["exceptions"]["recording_cache_failed"]["message"]
    assert placeholders(error) == Counter({"failed": 1, "downloaded": 1})
    assert "{failed}" not in error.format(failed=3, downloaded=2)
    if path.stem != "en":
        assert mismatch != SOURCE["config"]["abort"]["unique_id_mismatch"]
        assert error != SOURCE["exceptions"]["recording_cache_failed"]["message"]


def test_yaml_metadata_and_force_arm_wire_values():
    for service in SERVICES.values():
        assert service["name"].strip()
        assert service["description"].strip()
    for name in ("force_arm", "force_arm_now"):
        selector = SERVICES[name]["fields"]["mode"]["selector"]["select"]
        assert selector["options"] == ["home", "away"]
        assert selector["translation_key"] == "force_arm_mode"
    for mode in ("home", "away", "Home", "Away"):
        assert vol.Schema(alarm.FORCE_ARM_SCHEMA)({"mode": mode}) == {
            "mode": mode.capitalize()
        }
    with pytest.raises(vol.Invalid):
        vol.Schema(alarm.FORCE_ARM_SCHEMA)({"mode": "Disarmed"})


def test_storage_path_and_partial_english_regressions():
    for path in LOCALES:
        localized = json.loads(path.read_text(encoding="utf-8"))
        help_text = localized["options"]["step"]["init"]["data_description"]
        assert "/media" in help_text["recording_media_storage_path"]
        assert "/media" in localized["options"]["error"]["invalid_recording_media_path"]
        if path.stem != "en":
            for key, text in help_text.items():
                english = SOURCE["options"]["step"]["init"]["data_description"][key]
                for sentence in re.split(r"(?<=[.!?]) +", english):
                    if len(sentence.split()) >= 6:
                        assert sentence not in text, (path.stem, key, sentence)


def test_reviewed_wake_and_eviction_corrections():
    expected = {
    "hi": {
        "recording_media_storage_path": "/media के अंतर्गत एक फ़ोल्डर का उपयोग करें। नए कैश किए गए वीडियो और थंबनेल यहाँ संग्रहीत होते हैं।",
        "invalid_recording_media_path": "/media के अंतर्गत एक फ़ोल्डर का उपयोग करें।"
    },
    "ja": {
        "recording_media_sync_enabled": "最近の録画を自動的にキャッシュします。ストレージ容量を使用し、カメラをスリープから復帰させる頻度が高くなる可能性があります。"
    },
    "de": {
        "recording_cache_max_size_mb": "Maximale lokale Cachegröße in MB. Wenn das Limit erreicht ist, werden zuerst die Aufnahmen entfernt, deren letzter Aufruf am längsten zurückliegt."
    },
    "da": {
        "recording_cache_max_size_mb": "Maksimal lokal cachestørrelse i MB. Når grænsen er nået, fjernes først de optagelser, der ikke er blevet set i længst tid."
    },
    "fi": {
        "recording_cache_max_size_mb": "Paikallisen välimuistin enimmäiskoko megatavuina. Kun raja saavutetaan, ensin poistetaan tallenteet, joiden viimeisestä katselusta on kulunut eniten aikaa."
    },
    "ko": {
        "recording_cache_max_size_mb": "로컬 캐시의 최대 크기(MB)입니다. 한도에 도달하면 마지막으로 본 시점이 가장 오래된 녹화부터 삭제됩니다."
    },
    "sl": {
        "recording_media_storage_path": "Uporabite mapo pod /media. Tukaj se shranjujejo novi predpomnjeni videoposnetki in sličice.",
        "recording_media_sync_enabled": "Samodejno shranjujte nedavne posnetke v predpomnilnik. To porablja prostor za shranjevanje in lahko pogosteje prebudi kamere.",
        "recording_media_sync_hours": "Kako pogosto naj se izvaja redna dopolnilna sinhronizacija v ozadju. Ko je sinhronizacija omogočena, se nedavni posnetki preverjajo vsakih nekaj minut."
    }
}
    for locale, values in expected.items():
        localized = json.loads(
            (INTEGRATION / "translations" / f"{locale}.json").read_text(encoding="utf-8")
        )
        for key, text in values.items():
            section = (
                localized["options"]["error"]
                if key == "invalid_recording_media_path"
                else localized["options"]["step"]["init"]["data_description"]
            )
            assert section[key] == text


def panel_fixture():
    station = SimpleNamespace(entity_id="station", sn="serial", name="Base", type="SBS50")
    coordinator = SimpleNamespace(
        data={"stations": {"station": station}, "devices": {}},
        entry=SimpleNamespace(entry_id="entry"),
    )
    panel = alarm.XSenseAlarmControlPanel(coordinator, station)
    panel.entity_id = "alarm_control_panel.base"
    panel.hass = SimpleNamespace(config=SimpleNamespace(language="de"))
    panel._handle_coordinator_update = Mock()
    return panel, station


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["complete", "selector_only", "partial_service", "failure"])
async def test_notification_translations_do_not_block_entity_setup(monkeypatch, case):
    panel, station = panel_fixture()
    created = Mock()
    base_added = AsyncMock()
    monkeypatch.setattr(alarm.CoordinatorEntity, "async_added_to_hass", base_added)
    monkeypatch.setattr(alarm.persistent_notification, "async_create", created)

    async def translations(_hass, language, category, integrations):
        assert language == "de" and integrations == {"xsense"}
        if case == "failure":
            raise OSError("translation loading unavailable")
        if category == "selector":
            return {"component.xsense.selector.force_arm_mode.options.away": "Abwesend"}
        if case == "selector_only":
            return {}
        if case == "partial_service":
            return {"component.xsense.services.force_arm.name": "Scharfschalten"}
        return {
            "component.xsense.services.force_arm.name": "Scharfschalten",
            "component.xsense.services.force_arm.description": "Offene Sensoren blockieren die Anfrage.",
        }

    monkeypatch.setattr(alarm, "async_get_translations", translations)
    await panel.async_added_to_hass()
    base_added.assert_awaited_once()
    panel._handle_coordinator_update.assert_called_once()
    panel._async_create_force_arm_notification(station, "Away")
    args, kwargs = created.call_args
    assert "/xsense-force-arm#entity_id=alarm_control_panel.base&mode=Away" in args[1]
    assert kwargs["notification_id"] == "xsense_force_arm_station"
    if case == "complete":
        assert "Offene Sensoren blockieren" in args[1]
        assert "Abwesend" in args[1]
    else:
        assert "One or more sensors are open." in args[1]

@pytest.mark.asyncio
@pytest.mark.parametrize("raw_mode", ["Home", "Away", "home", "away"])
@pytest.mark.parametrize("action", ["async_force_arm", "async_force_arm_now"])
async def test_legacy_and_ui_modes_reach_identical_canonical_commands(raw_mode, action):
    panel, station = panel_fixture()
    station.set_alarm_data = Mock()
    api = SimpleNamespace(set_station_mode=AsyncMock())
    panel.coordinator.xsense = api
    panel._pending_force_arm_mode = raw_mode.capitalize()
    panel._async_clear_force_arm_notification = Mock()
    panel.async_write_ha_state = Mock()
    validated = vol.Schema(alarm.FORCE_ARM_SCHEMA)({"mode": raw_mode})
    await getattr(panel, action)(**validated)
    api.set_station_mode.assert_awaited_once_with(
        station, raw_mode.capitalize(), force_arm="1"
    )
    assert panel._pending_force_arm_mode is None
