"""Guard operational documentation against stale implementation details."""

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "xsense"


def test_storage_migration_help_lists_actual_cache_directories():
    for path in [COMPONENT / "strings.json", *sorted((COMPONENT / "translations").glob("*.json"))]:
        data = json.loads(path.read_text(encoding="utf-8"))
        description = data["options"]["step"]["confirm_recording_media_storage_path"]["description"]
        for directory in ("hls", "videos", "thumbs"):
            assert f"`{directory}`" in description, (path.name, directory)


def test_all_readmes_describe_required_event_type_and_blueprint_bus():
    for path in sorted((ROOT / "readme").glob("README_*.md")):
        text = path.read_text(encoding="utf-8")
        paragraphs = [line for line in text.splitlines() if "`event.received`" in line]
        assert paragraphs, path.name
        assert all("`options.event_type`" in line for line in paragraphs), path.name
        assert "`xsense_camera_event`" in text, path.name
        for block in re.findall(r"```yaml\s*\n(.*?)```", text, re.DOTALL):
            if "trigger: event.received" not in block:
                continue
            automation = yaml.safe_load(block)
            for trigger in automation["triggers"]:
                if trigger["trigger"] == "event.received":
                    assert trigger["options"]["event_type"], path.name
                    assert trigger["target"]["entity_id"], path.name


def test_notification_quality_help_does_not_describe_removed_capture():
    data = json.loads((COMPONENT / "strings.json").read_text(encoding="utf-8"))
    description = data["options"]["step"]["init"]["data_description"]["recording_notification_quality"]
    assert "capture" not in description
    assert "URLs" in description


def test_every_readme_keeps_entry_cleanup_note_with_storage_modes():
    marker = "<!-- xsense-cache-entry-ownership -->"
    for path in sorted((ROOT / "readme").glob("README_*.md")):
        text = path.read_text(encoding="utf-8")
        assert text.count(marker) == 1, path.name
        assert text.index("<!-- xsense-recording-storage-modes -->") < text.index(marker)
        paragraph = text.split(marker, 1)[1].strip().split("\n\n", 1)[0]
        assert paragraph and not paragraph.startswith(("#", "[", "<!--")), path.name
