"""Regression coverage for settings and recordings UI recovery."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.exceptions import HomeAssistantError

import custom_components.xsense as integration
from custom_components.xsense import frontend as panel_ui
from custom_components.xsense import recordings_media as media
from custom_components.xsense.const import (
    CONF_RECORDING_CACHE_MODE,
    CONF_RECORDING_MEDIA_SYNC_ENABLED,
    CONF_RECORDING_MEDIA_SYNC_HOURS,
    DEFAULT_RECORDING_CACHE_MAX_SIZE_MB,
    DEFAULT_RECORDING_CACHE_RETENTION_DAYS,
    DEFAULT_RECORDING_MEDIA_SYNC_HOURS,
    DOMAIN,
)


def test_late_registration_retries_failure_without_duplicate_tasks(monkeypatch):
    async def run():
        listeners, tasks, cleanups = [], [], []
        coordinator = SimpleNamespace(
            data={"stations": {}, "devices": {}},
            async_config_entry_first_refresh=AsyncMock(),
            async_add_listener=lambda cb: listeners.append(cb) or (lambda: None),
            async_start_camera_ai_history_polling=Mock(),
            async_schedule_deferred_refresh=Mock(),
        )
        entry = SimpleNamespace(
            entry_id="audit-camera",
            options={},
            async_on_unload=Mock(),
            add_update_listener=lambda cb: (lambda: None),
        )

        def create_task(coro):
            task = asyncio.create_task(coro)
            tasks.append(task)
            return task

        hass = SimpleNamespace(
            data={},
            config_entries=SimpleNamespace(async_forward_entry_setups=AsyncMock()),
            create_task=create_task,
        )
        register = AsyncMock(side_effect=[RuntimeError("test registration failure"), None])
        monkeypatch.setattr(integration, "async_load_identity_store", AsyncMock())
        monkeypatch.setattr(integration, "_async_register_recordings_runtime", register)
        monkeypatch.setattr(integration, "_cleanup_recordings_runtime", lambda *a: cleanups.append(a))
        monkeypatch.setattr(integration, "async_stop_recording_media_sync", Mock())
        monkeypatch.setattr(integration, "async_track_time_interval", lambda *a: lambda: None)
        monkeypatch.setattr(integration, "_schedule_startup_maintenance", Mock())
        assert await integration._async_setup_entry_runtime(hass, entry, coordinator)
        assert register.await_count == 0
        coordinator.data["stations"]["cam"] = SimpleNamespace(type="SSC0A")
        listeners[0]()
        listeners[0]()
        assert len(tasks) == 1
        await asyncio.gather(*tasks)
        assert register.await_count == 1
        listeners[0]()
        await asyncio.gather(*tasks)
        assert register.await_count == 2
        listeners[0]()
        assert len(tasks) == 2

    asyncio.run(run())


@pytest.fixture
def late_registration(monkeypatch):
    real_cleanup = integration._cleanup_recordings_runtime
    listeners, tasks = [], []
    coordinator = SimpleNamespace(
        data={"stations": {}, "devices": {}},
        async_config_entry_first_refresh=AsyncMock(),
        async_add_listener=lambda cb: listeners.append(cb) or (lambda: None),
        async_start_camera_ai_history_polling=Mock(),
        async_schedule_deferred_refresh=Mock(),
    )
    entry = SimpleNamespace(
        entry_id="audit-camera", options={}, async_on_unload=Mock(),
        add_update_listener=lambda cb: (lambda: None),
    )

    def create_task(coro):
        task = asyncio.create_task(coro)
        tasks.append(task)
        return task

    hass = SimpleNamespace(
        data={}, create_task=create_task,
        config_entries=SimpleNamespace(async_forward_entry_setups=AsyncMock()),
    )
    cleanup, stop = Mock(), Mock()
    monkeypatch.setattr(integration, "async_load_identity_store", AsyncMock())
    monkeypatch.setattr(integration, "_cleanup_recordings_runtime", cleanup)
    monkeypatch.setattr(integration, "async_stop_recording_media_sync", stop)
    monkeypatch.setattr(integration, "async_track_time_interval", lambda *a: lambda: None)
    monkeypatch.setattr(integration, "_schedule_startup_maintenance", Mock())

    async def start():
        assert await integration._async_setup_entry_runtime(hass, entry, coordinator)
        cleanup.reset_mock()
        coordinator.data["stations"]["cam"] = SimpleNamespace(type="SSC0A")
        listeners[0]()

    return SimpleNamespace(
        hass=hass, entry=entry, coordinator=coordinator, tasks=tasks,
        listeners=listeners, cleanup=cleanup, stop=stop, start=start,
        real_cleanup=real_cleanup,
    )


def test_late_registration_cancellation_propagates_and_allows_retry(monkeypatch, late_registration):
    state = late_registration

    async def run():
        started, release = asyncio.Event(), asyncio.Event()

        async def register(*args):
            started.set()
            await release.wait()

        registration = AsyncMock(side_effect=register)
        monkeypatch.setattr(integration, "_async_register_recordings_runtime", registration)
        await state.start()
        await started.wait()
        state.tasks[0].cancel()
        with pytest.raises(asyncio.CancelledError):
            await state.tasks[0]
        state.stop.assert_not_called()
        release.set()
        state.listeners[0]()
        await state.tasks[-1]
        assert registration.await_count == 2
        state.listeners[0]()
        assert len(state.tasks) == 2

    asyncio.run(run())


def test_late_registration_cleans_up_when_cameras_disappear(monkeypatch, late_registration):
    state = late_registration

    async def run():
        started, release = asyncio.Event(), asyncio.Event()

        async def register(*args):
            started.set()
            await release.wait()

        registration = AsyncMock(side_effect=register)
        monkeypatch.setattr(integration, "_async_register_recordings_runtime", registration)
        await state.start()
        await started.wait()
        state.coordinator.data["stations"].clear()
        state.listeners[0]()
        release.set()
        await state.tasks[0]
        state.cleanup.assert_called_once_with(state.hass, state.entry.entry_id)
        state.coordinator.data["stations"]["cam"] = SimpleNamespace(type="SSC0A")
        state.listeners[0]()
        await state.tasks[-1]
        assert registration.await_count == 2

    asyncio.run(run())


@pytest.mark.parametrize("fails", [False, True])
def test_late_registration_does_not_clean_up_replacement(monkeypatch, late_registration, fails):
    state = late_registration

    async def run():
        started, release = asyncio.Event(), asyncio.Event()

        async def register(*args):
            started.set()
            await release.wait()
            if fails:
                raise RuntimeError("registration failed after replacement")

        monkeypatch.setattr(integration, "_async_register_recordings_runtime", register)
        await state.start()
        await started.wait()
        replacement = SimpleNamespace(data=state.coordinator.data)
        state.hass.data[DOMAIN][state.entry.entry_id] = replacement
        release.set()
        await state.tasks[0]
        state.cleanup.assert_not_called()
        state.stop.assert_not_called()
        assert state.hass.data[DOMAIN][state.entry.entry_id] is replacement

    asyncio.run(run())


def test_late_registration_skips_replaced_coordinator_before_start(monkeypatch, late_registration):
    state = late_registration

    async def run():
        registration = AsyncMock()
        monkeypatch.setattr(integration, "_async_register_recordings_runtime", registration)
        await state.start()
        state.hass.data[DOMAIN][state.entry.entry_id] = SimpleNamespace()
        await state.tasks[0]
        registration.assert_not_awaited()
        state.cleanup.assert_not_called()
        state.stop.assert_not_called()

    asyncio.run(run())


def test_real_late_registration_does_not_start_sync_after_replacement(monkeypatch, late_registration):
    state = late_registration

    async def run():
        started, release = asyncio.Event(), asyncio.Event()

        async def panel(hass):
            started.set()
            await release.wait()

        start_sync = Mock()
        monkeypatch.setattr(integration, "async_register_recordings_panel", panel)
        monkeypatch.setattr(integration, "async_register_recording_services", AsyncMock())
        monkeypatch.setattr(integration, "async_register_recordings_media_source", Mock())
        monkeypatch.setattr(integration, "async_start_recording_media_sync", start_sync)
        monkeypatch.setattr(integration, "async_schedule_hls_playback_profile_migration", Mock())
        await state.start()
        await started.wait()
        state.hass.data[DOMAIN][state.entry.entry_id] = SimpleNamespace(data=state.coordinator.data)
        release.set()
        await state.tasks[0]
        start_sync.assert_not_called()

    asyncio.run(run())


def test_failed_late_registration_cleans_partial_runtime_on_camera_removal(monkeypatch, late_registration):
    state = late_registration

    async def run():
        monkeypatch.setattr(integration, "async_register_recordings_panel", AsyncMock())
        monkeypatch.setattr(integration, "async_register_recording_services", AsyncMock(
            side_effect=RuntimeError("service registration failed after panel creation"),
        ))
        await state.start()
        await state.tasks[0]
        state.coordinator.data["stations"].clear()
        state.listeners[0]()
        state.cleanup.assert_called_with(state.hass, state.entry.entry_id)

    asyncio.run(run())


@pytest.mark.parametrize("successor", [None, "other-camera", "replacement", "other-no-camera"])
def test_pending_panel_registration_cleanup_preserves_current_camera_owners(
    monkeypatch, late_registration, successor,
):
    state = late_registration

    async def run():
        started, release = asyncio.Event(), asyncio.Event()
        panels = {}

        async def register_panel(**kwargs):
            started.set()
            await release.wait()
            panels[kwargs["frontend_url_path"]] = kwargs

        def remove_panel(hass, path, **kwargs):
            panels.pop(path, None)

        monkeypatch.setattr(panel_ui, "async_register_recordings_static_paths", AsyncMock())
        monkeypatch.setattr(panel_ui.panel_custom, "async_register_panel", register_panel)
        monkeypatch.setattr(panel_ui.frontend, "async_remove_panel", remove_panel)
        monkeypatch.setattr(integration, "async_register_recordings_panel", panel_ui.async_register_recordings_panel)
        monkeypatch.setattr(integration, "async_stop_hls_playback_profile_migration", Mock())
        monkeypatch.setattr(integration, "async_unregister_recording_services", Mock())
        monkeypatch.setattr(integration, "async_unregister_recordings_media_source", Mock())
        monkeypatch.setattr(integration, "async_clear_recording_event_clips", Mock())
        start_sync = Mock()
        monkeypatch.setattr(integration, "async_start_recording_media_sync", start_sync)
        await state.start()
        monkeypatch.setattr(integration, "_cleanup_recordings_runtime", state.real_cleanup)
        await started.wait()
        state.hass.data[panel_ui.frontend.DATA_PANELS] = panels
        lock = state.hass.data[DOMAIN]["_recordings_panel_lock"]
        del state.hass.data[DOMAIN][state.entry.entry_id]
        if successor is not None:
            successor_id = state.entry.entry_id if successor == "replacement" else successor
            state.hass.data[DOMAIN][successor_id] = SimpleNamespace(data={
                "stations": {} if successor == "other-no-camera" else {
                    "cam": SimpleNamespace(type="SSC0A"),
                }, "devices": {},
            })
        state.real_cleanup(state.hass)
        if successor is None:
            integration._prune_domain_data_after_unload(state.hass)
            assert state.hass.data[DOMAIN]["_recordings_panel_lock"] is lock
        release.set()
        await state.tasks[0]
        retained = successor in ("other-camera", "replacement")
        assert (panel_ui.FRONTEND_URL_PATH in panels) is retained
        assert bool(state.hass.data[DOMAIN].get("_recordings_panel_registered")) is retained
        start_sync.assert_not_called()

    asyncio.run(run())


def test_pending_registration_failure_cleans_removed_cameras_immediately(monkeypatch, late_registration):
    state = late_registration

    async def run():
        started, release = asyncio.Event(), asyncio.Event()

        async def register(*args):
            started.set()
            await release.wait()
            raise RuntimeError("registration failed after cameras disappeared")

        monkeypatch.setattr(integration, "_async_register_recordings_runtime", register)
        await state.start()
        await started.wait()
        state.coordinator.data["stations"].clear()
        state.listeners[0]()
        state.cleanup.assert_not_called()
        release.set()
        await state.tasks[0]
        state.cleanup.assert_called_once_with(state.hass, state.entry.entry_id)

        # The attempted flag must be cleared so later updates do not clean twice.
        state.listeners[0]()
        state.cleanup.assert_called_once_with(state.hass, state.entry.entry_id)

    asyncio.run(run())


@pytest.mark.parametrize("value", [float("inf"), float("-inf")])
@pytest.mark.parametrize("default,minimum,maximum", [
    (DEFAULT_RECORDING_CACHE_RETENTION_DAYS, 1, 365),
    (DEFAULT_RECORDING_CACHE_MAX_SIZE_MB, 128, 102400),
])
def test_runtime_bounded_integer_options_normalize_infinity(value, default, minimum, maximum):
    assert media._bounded_int_option(value, default, minimum, maximum) == default
    assert media._bounded_int_option(minimum, default, minimum, maximum) == minimum
    assert media._bounded_int_option(maximum, default, minimum, maximum) == maximum


@pytest.mark.parametrize("value", ["bad", None, 0, -1, 169, float("inf")])
@pytest.mark.parametrize("sync_enabled", [True, False])
def test_sync_interval_uses_safe_default(monkeypatch, value, sync_enabled):
    intervals = []
    monkeypatch.setattr(media, "async_call_later", lambda *a: lambda: None)
    monkeypatch.setattr(media, "async_track_time_interval", lambda h, cb, interval: intervals.append(interval) or (lambda: None))
    entry = SimpleNamespace(
        entry_id="audit-camera",
        options={
            CONF_RECORDING_CACHE_MODE: "retained",
            CONF_RECORDING_MEDIA_SYNC_ENABLED: sync_enabled,
            CONF_RECORDING_MEDIA_SYNC_HOURS: value,
        },
        async_on_unload=Mock(),
    )
    hass = SimpleNamespace(
        data={DOMAIN: {}},
        config_entries=SimpleNamespace(async_get_entry=lambda _: entry),
    )
    media.async_start_recording_media_sync(hass, entry)
    if sync_enabled:
        assert any(i.total_seconds() == DEFAULT_RECORDING_MEDIA_SYNC_HOURS * 3600 for i in intervals)
    else:
        assert intervals == [media.RECORDING_CACHE_MAINTENANCE_INTERVAL]
    media.async_stop_recording_media_sync(hass, entry.entry_id)


@pytest.mark.parametrize("failed,downloaded", [(5, 0), (2, 3), (0, 3)])
def test_cache_action_reports_failed_downloads(monkeypatch, failed, downloaded):
    callbacks = {}
    hass = SimpleNamespace(
        data={},
        services=SimpleNamespace(async_register=lambda domain, name, cb, **kw: callbacks.update({name: cb})),
    )
    monkeypatch.setattr(media, "async_cache_recording_media", AsyncMock(return_value={"failed": failed, "downloaded": downloaded}))

    async def run():
        await media.async_register_recording_services(hass)
        action = callbacks[media.SERVICE_CACHE_RECORDINGS]
        if failed:
            with pytest.raises(HomeAssistantError) as exc:
                await action(SimpleNamespace(data={}))
            assert exc.value.translation_key == "recording_cache_failed"
            assert exc.value.translation_placeholders == {"failed": str(failed), "downloaded": str(downloaded)}
        else:
            await action(SimpleNamespace(data={}))

    asyncio.run(run())
