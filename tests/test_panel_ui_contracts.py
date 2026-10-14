"""Panel data and browser-controller regressions using only isolated fixtures."""

import importlib
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


def test_panel_controller_contracts():
    node = shutil.which("node")
    assert node is not None
    result = subprocess.run(
        [node, "--test", str(Path(__file__).with_suffix(".mjs"))],
        check=False, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.asyncio
@pytest.mark.parametrize("sync,retained,suppressed,expected", [
    (True, True, False, 1), (False, True, False, 1), (False, False, False, 0),
    (True, True, True, 1), (False, True, True, 1),
])
async def test_pending_includes_sync_hidden_clips(tmp_path, monkeypatch, sync, retained, suppressed, expected):
    http = importlib.import_module("custom_components.xsense.http")
    media = importlib.import_module("custom_components.xsense.recordings_media")
    hass = SimpleNamespace(data={}, config_entries=SimpleNamespace(
        async_get_entry=lambda _: SimpleNamespace(options={}, data={})
    ))
    clip = {"entry_id": "entry", "serial": "CAM", "start": 100, "end": 110,
            "date": "1970-01-01", "source": "video_url", "playback_url": "https://example.invalid/clip.m3u8",
            "media_root": str(tmp_path)}
    index = {"warning": "Cloud history is stale", "cameras": [
        {"entry_id": "entry", "serial": "CAM", "online": True, "clips": [clip]}
    ]}
    monkeypatch.setattr(http, "_recording_media_root", lambda *_: tmp_path)
    monkeypatch.setattr(media, "_recording_media_root_from_value", lambda *_: tmp_path)
    monkeypatch.setattr(http, "_recording_media_sync_enabled", lambda *_: sync)
    monkeypatch.setattr(http, "_recording_cache_retained", lambda *_: retained)
    monkeypatch.setattr(http, "async_recording_cache_suppressed", AsyncMock(return_value=suppressed))
    monkeypatch.setattr(http, "_hls_playback_fields_for_clip", lambda *_: {})
    source = SimpleNamespace(_async_mp4_ready=AsyncMock(return_value=False),
                             _async_hls_cache_playback_ready=AsyncMock(return_value=False),
                             _async_path_ready=AsyncMock(return_value=False))
    result = await http._async_build_panel_data_from_index(hass, source, index)
    assert result["stats"]["indexed_clips"] == 1
    assert result["stats"]["pending_clips"] == expected
    assert result["stats"]["visible_clips"] == (0 if sync and not suppressed else 1)
    if suppressed:
        assert result["cameras"][0]["clips"][0]["manual_cache_deleted"] is True
    assert result["warning"] == index["warning"]
    assert result["cameras"][0]["days_descending"] is True
