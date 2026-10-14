"""Regression coverage for failed setup and persistent-registry unload."""

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components import xsense
from custom_components.xsense import recordings_gate
from custom_components.xsense.const import DOMAIN


def coordinator(*, camera=True):
    return SimpleNamespace(
        xsense=object(),
        data={
            "stations": {"device": SimpleNamespace(type="SSC0A" if camera else "SBS50")},
            "devices": {},
        },
        async_config_entry_first_refresh=AsyncMock(),
        async_shutdown=AsyncMock(),
        async_add_listener=Mock(return_value=lambda: None),
        async_start_camera_ai_history_polling=Mock(),
        async_schedule_deferred_refresh=Mock(),
    )


@pytest.fixture
def runtime(monkeypatch):
    callbacks = []
    entry = SimpleNamespace(
        entry_id="camera-entry",
        async_on_unload=callbacks.append,
        add_update_listener=Mock(return_value=lambda: None),
    )
    hass = SimpleNamespace(
        data={DOMAIN: {"_recordings_static_paths_registered": True}},
        config_entries=SimpleNamespace(
            async_forward_entry_setups=AsyncMock(),
            async_unload_platforms=AsyncMock(return_value=True),
        ),
    )
    registry = SimpleNamespace(
        entities={
            "camera.persisted": SimpleNamespace(domain="camera", platform=DOMAIN)
        }
    )
    monkeypatch.setattr(recordings_gate.er, "async_get", lambda _hass: registry)
    current = coordinator()
    monkeypatch.setattr(xsense, "XSenseDataUpdateCoordinator", lambda *_args: current)
    monkeypatch.setattr(xsense, "async_load_identity_store", AsyncMock())
    registered = set()

    async def register(_hass, _entry):
        registered.update({"panel", "services", "source"})
        hass.data[DOMAIN]["_recording_services_registered"] = True

    monkeypatch.setattr(xsense, "_async_register_recordings_runtime", register)
    for kind, name in (
        ("panel", "async_unregister_recordings_panel"),
        ("services", "async_unregister_recording_services"),
        ("source", "async_unregister_recordings_media_source"),
    ):
        monkeypatch.setattr(xsense, name, lambda _hass, kind=kind: registered.discard(kind))
    for name in (
        "async_stop_hls_playback_profile_migration",
        "async_stop_recording_media_sync",
        "async_remove_recording_index",
        "async_clear_recording_event_clips",
        "async_cancel_recording_cache_tasks",
    ):
        monkeypatch.setattr(xsense, name, Mock())
    monkeypatch.setattr(xsense, "async_track_time_interval", Mock(return_value=lambda: None))
    monkeypatch.setattr(xsense, "_schedule_startup_maintenance", Mock())
    return SimpleNamespace(
        hass=hass, entry=entry, coordinator=current, registry=registry,
        registered=registered, callbacks=callbacks,
    )


def test_registry_visibility_does_not_imply_loaded_runtime_ownership(runtime):
    assert recordings_gate.has_any_camera_entities(runtime.hass)
    assert not recordings_gate.has_loaded_camera_entities(runtime.hass)
    assert not xsense._has_any_camera_entities(runtime.hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [False, True])
async def test_identity_load_precedes_platforms_and_flushes_on_exit(runtime, monkeypatch, failure):
    manager = SimpleNamespace(async_close=AsyncMock())

    async def load(_hass, _entry, coordinator):
        coordinator._xsense_identity_store = manager

    async def forward(*_args):
        assert runtime.coordinator._xsense_identity_store is manager
        if failure:
            raise RuntimeError("partial setup")

    monkeypatch.setattr(xsense, "async_load_identity_store", load)
    runtime.hass.config_entries.async_forward_entry_setups.side_effect = forward
    if failure:
        with pytest.raises(RuntimeError, match="partial setup"):
            await xsense.async_setup_entry(runtime.hass, runtime.entry)
    else:
        await xsense.async_setup_entry(runtime.hass, runtime.entry)
        manager.async_close.assert_not_awaited()
        await xsense.async_unload_entry(runtime.hass, runtime.entry)
    manager.async_close.assert_awaited_once()


@pytest.mark.asyncio
async def test_last_camera_unload_removes_global_runtime_with_persisted_registry(runtime):
    assert await xsense.async_setup_entry(runtime.hass, runtime.entry)
    assert runtime.registered == {"panel", "services", "source"}

    assert await xsense.async_unload_entry(runtime.hass, runtime.entry)

    assert runtime.registered == set()
    runtime.coordinator.async_shutdown.assert_awaited_once()
    assert runtime.hass.data[DOMAIN] == {"_recordings_static_paths_registered": True}
    assert recordings_gate.has_registered_camera_entities(runtime.hass)


@pytest.mark.asyncio
async def test_last_unload_reload_preserves_in_use_recording_root_lock(runtime):
    from custom_components.xsense.recordings_media import _recording_maintenance_lock

    await xsense.async_setup_entry(runtime.hass, runtime.entry)
    root = Path("/media/xsense-test-lock-lifetime")
    lock = _recording_maintenance_lock(runtime.hass, root)
    await lock.acquire()
    waiter = asyncio.create_task(lock.acquire())
    await asyncio.sleep(0)
    try:
        await xsense.async_unload_entry(runtime.hass, runtime.entry)
        assert runtime.entry.entry_id not in runtime.hass.data[DOMAIN]
        assert _recording_maintenance_lock(runtime.hass, root) is lock
        assert not waiter.done()
        await xsense.async_setup_entry(runtime.hass, runtime.entry)
        assert _recording_maintenance_lock(runtime.hass, root) is lock
        assert not waiter.done()
    finally:
        lock.release()
        await waiter
        lock.release()
    await xsense.async_unload_entry(runtime.hass, runtime.entry)


@pytest.mark.asyncio
async def test_unloading_one_of_two_camera_entries_preserves_shared_runtime(runtime):
    other = coordinator()
    runtime.hass.data[DOMAIN]["other-entry"] = other
    await xsense.async_setup_entry(runtime.hass, runtime.entry)

    await xsense.async_unload_entry(runtime.hass, runtime.entry)

    assert runtime.registered == {"panel", "services", "source"}
    assert runtime.hass.data[DOMAIN]["other-entry"] is other
    other.async_shutdown.assert_not_awaited()


@pytest.mark.asyncio
async def test_remaining_sensor_entry_does_not_keep_camera_runtime(runtime):
    other = coordinator(camera=False)
    runtime.hass.data[DOMAIN]["sensor-entry"] = other
    await xsense.async_setup_entry(runtime.hass, runtime.entry)

    await xsense.async_unload_entry(runtime.hass, runtime.entry)

    assert runtime.registered == set()
    assert runtime.hass.data[DOMAIN]["sensor-entry"] is other


@pytest.mark.asyncio
async def test_failed_platform_unload_preserves_entry_and_runtime(runtime):
    await xsense.async_setup_entry(runtime.hass, runtime.entry)
    runtime.hass.config_entries.async_unload_platforms.return_value = False

    assert not await xsense.async_unload_entry(runtime.hass, runtime.entry)

    assert runtime.registered == {"panel", "services", "source"}
    assert runtime.hass.data[DOMAIN][runtime.entry.entry_id] is runtime.coordinator
    runtime.coordinator.async_shutdown.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [RuntimeError("refresh failed"), asyncio.CancelledError()])
async def test_first_refresh_failure_closes_coordinator_without_publishing(runtime, failure):
    runtime.coordinator.async_config_entry_first_refresh.side_effect = failure

    with pytest.raises(type(failure)) as raised:
        await xsense.async_setup_entry(runtime.hass, runtime.entry)

    assert raised.value is failure
    runtime.coordinator.async_shutdown.assert_awaited_once()
    assert runtime.entry.entry_id not in runtime.hass.data[DOMAIN]
    assert runtime.registered == set()
    runtime.hass.config_entries.async_unload_platforms.assert_not_awaited()


@pytest.mark.asyncio
async def test_partial_recordings_registration_failure_rolls_back(runtime, monkeypatch):
    failure = RuntimeError("services registration failed")

    async def fail(_hass, _entry):
        runtime.registered.add("panel")
        raise failure

    monkeypatch.setattr(xsense, "_async_register_recordings_runtime", fail)
    with pytest.raises(RuntimeError) as raised:
        await xsense.async_setup_entry(runtime.hass, runtime.entry)

    assert raised.value is failure
    assert runtime.registered == set()
    assert runtime.entry.entry_id not in runtime.hass.data[DOMAIN]
    runtime.coordinator.async_shutdown.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel", [False, True])
async def test_platform_setup_failure_unloads_partial_platforms_and_runtime(runtime, cancel):
    failure = asyncio.CancelledError() if cancel else RuntimeError("platform failed")
    runtime.hass.config_entries.async_forward_entry_setups.side_effect = failure

    with pytest.raises(type(failure)) as raised:
        await xsense.async_setup_entry(runtime.hass, runtime.entry)

    assert raised.value is failure
    runtime.hass.config_entries.async_unload_platforms.assert_awaited_once_with(
        runtime.entry, xsense.PLATFORMS
    )
    assert runtime.registered == set()
    assert runtime.entry.entry_id not in runtime.hass.data[DOMAIN]
    runtime.coordinator.async_shutdown.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel", [False, True])
async def test_failed_setup_preserves_other_camera_entry(runtime, cancel):
    other = coordinator()
    runtime.hass.data[DOMAIN]["other-entry"] = other
    runtime.registered.update({"panel", "services", "source"})
    failure = asyncio.CancelledError() if cancel else RuntimeError("failed")
    runtime.hass.config_entries.async_forward_entry_setups.side_effect = failure

    with pytest.raises(type(failure)):
        await xsense.async_setup_entry(runtime.hass, runtime.entry)

    assert runtime.hass.data[DOMAIN]["other-entry"] is other
    assert runtime.entry.entry_id not in runtime.hass.data[DOMAIN]
    assert runtime.registered == {"panel", "services", "source"}
    other.async_shutdown.assert_not_awaited()
    runtime.hass.config_entries.async_unload_platforms.assert_awaited_once_with(
        runtime.entry, xsense.PLATFORMS
    )
    runtime.coordinator.async_shutdown.assert_awaited_once()


@pytest.mark.asyncio
async def test_reload_recreates_runtime_despite_persistent_registry(runtime):
    await xsense.async_setup_entry(runtime.hass, runtime.entry)
    await xsense.async_unload_entry(runtime.hass, runtime.entry)
    assert not runtime.registered

    assert await xsense.async_setup_entry(runtime.hass, runtime.entry)

    assert runtime.registered == {"panel", "services", "source"}
    assert runtime.hass.data[DOMAIN]["_recordings_static_paths_registered"] is True
    assert runtime.hass.data[DOMAIN][runtime.entry.entry_id] is runtime.coordinator


@pytest.mark.asyncio
async def test_post_forward_setup_failure_unloads_platforms(runtime):
    runtime.coordinator.async_schedule_deferred_refresh.side_effect = RuntimeError("failed")

    with pytest.raises(RuntimeError):
        await xsense.async_setup_entry(runtime.hass, runtime.entry)

    runtime.hass.config_entries.async_forward_entry_setups.assert_awaited_once()
    runtime.hass.config_entries.async_unload_platforms.assert_awaited_once()
    assert not runtime.registered
    assert runtime.entry.entry_id not in runtime.hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_shutdown_error_does_not_replace_original_setup_failure(runtime, caplog):
    failure = RuntimeError("original setup failure")
    runtime.coordinator.async_config_entry_first_refresh.side_effect = failure
    runtime.coordinator.async_shutdown.side_effect = OSError("cleanup failure")

    with pytest.raises(RuntimeError) as raised:
        await xsense.async_setup_entry(runtime.hass, runtime.entry)

    assert raised.value is failure
    assert "Could not shut down X-Sense after failed setup" in caplog.text
