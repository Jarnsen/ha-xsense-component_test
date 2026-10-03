import asyncio
from pathlib import Path
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import OptionsFlowManager
from homeassistant.helpers import entity_registry as er
import pytest
import voluptuous as vol
import voluptuous_serialize

from custom_components.xsense import config_flow

from custom_components.xsense.config_flow import (
    XSenseOptionsFlow,
    _recording_media_path_allowed,
    options_schema,
    recording_media_storage_path,
    recording_media_storage_path_changed,
)


def _serialize_options_schema(schema):
    """Use the serializer provided by the active Home Assistant schema backend."""
    if type(schema).__module__.startswith("probatio."):
        from probatio.codecs import to_field_list

        return to_field_list(schema, custom_serializer=cv.custom_serializer)
    return voluptuous_serialize.convert(schema, custom_serializer=cv.custom_serializer)


@pytest.mark.parametrize("path", [
    "/media/../config/clips", "/media/clips/../../config", "/media-other/clips",
    "media/clips", "//media/clips", "/media/\x00clips",
])
def test_recording_path_rejects_escape(path):
    assert not _recording_media_path_allowed(path)


@pytest.mark.parametrize("path", ["/media", "/media/xsense_recordings", "/media/camera/clips"])
def test_recording_path_accepts_media_subdirectories(path):
    assert _recording_media_path_allowed(path)


def test_recording_path_rejects_resolved_symlink_escape(monkeypatch, tmp_path):
    from pathlib import Path

    original_resolve = Path.resolve
    def resolve(path, *args, **kwargs):
        if str(path) == "/media/linked":
            return tmp_path / "outside"
        return original_resolve(path, *args, **kwargs)
    monkeypatch.setattr(Path, "resolve", resolve)
    assert not _recording_media_path_allowed("/media/linked")
from custom_components.xsense.const import (
    CONF_RECORDING_CACHE_MAX_SIZE_MB,
    CONF_RECORDING_CACHE_MODE,
    CONF_RECORDING_CACHE_RETENTION_DAYS,
    CONF_RECORDING_MEDIA_CLIPS_ORDER,
    CONF_RECORDING_MEDIA_DAYS_ORDER,
    CONF_RECORDING_MEDIA_STORAGE_PATH,
    CONF_RECORDING_MEDIA_SYNC_ENABLED,
    CONF_RECORDING_MEDIA_SYNC_HOURS,
    CONF_RECORDING_NOTIFICATION_QUALITY,
    DEFAULT_RECORDING_CACHE_MAX_SIZE_MB,
    DEFAULT_RECORDING_CACHE_MODE,
    DEFAULT_RECORDING_CACHE_RETENTION_DAYS,
    DEFAULT_RECORDING_MEDIA_CLIPS_ORDER,
    DEFAULT_RECORDING_MEDIA_DAYS_ORDER,
    DEFAULT_RECORDING_MEDIA_STORAGE_PATH,
    DEFAULT_RECORDING_MEDIA_SYNC_HOURS,
    DEFAULT_RECORDING_NOTIFICATION_QUALITY,
)


@pytest.mark.parametrize("value", [float("inf"), float("-inf")])
@pytest.mark.parametrize("option,default", [
    (CONF_RECORDING_MEDIA_SYNC_HOURS, DEFAULT_RECORDING_MEDIA_SYNC_HOURS),
    (CONF_RECORDING_CACHE_RETENTION_DAYS, DEFAULT_RECORDING_CACHE_RETENTION_DAYS),
    (CONF_RECORDING_CACHE_MAX_SIZE_MB, DEFAULT_RECORDING_CACHE_MAX_SIZE_MB),
])
def test_options_flow_normalizes_infinite_stale_numeric_options(option, default, value):
    flow = XSenseOptionsFlow(SimpleNamespace(options={
        option: value,
    }))

    form = asyncio.run(flow.async_step_init())
    values = form["data_schema"]({})

    assert values[option] == default
    result = asyncio.run(flow.async_step_init(values))
    assert result["type"] == "create_entry"
    assert result["data"][option] == default


def test_options_schema_has_recording_sync_defaults_without_camera_path_option():
    schema = options_schema({})

    assert schema({}) == {
        CONF_RECORDING_CACHE_MODE: DEFAULT_RECORDING_CACHE_MODE,
        CONF_RECORDING_MEDIA_SYNC_ENABLED: False,
        CONF_RECORDING_MEDIA_SYNC_HOURS: DEFAULT_RECORDING_MEDIA_SYNC_HOURS,
        CONF_RECORDING_MEDIA_STORAGE_PATH: DEFAULT_RECORDING_MEDIA_STORAGE_PATH,
        CONF_RECORDING_CACHE_RETENTION_DAYS: DEFAULT_RECORDING_CACHE_RETENTION_DAYS,
        CONF_RECORDING_CACHE_MAX_SIZE_MB: DEFAULT_RECORDING_CACHE_MAX_SIZE_MB,
        CONF_RECORDING_NOTIFICATION_QUALITY: DEFAULT_RECORDING_NOTIFICATION_QUALITY,
        CONF_RECORDING_MEDIA_DAYS_ORDER: DEFAULT_RECORDING_MEDIA_DAYS_ORDER,
        CONF_RECORDING_MEDIA_CLIPS_ORDER: DEFAULT_RECORDING_MEDIA_CLIPS_ORDER,
    }


def test_options_schema_orders_recording_options_for_the_ui():
    schema = options_schema({})

    assert [field.schema for field in schema.schema] == [
        CONF_RECORDING_CACHE_MODE,
        CONF_RECORDING_MEDIA_SYNC_ENABLED,
        CONF_RECORDING_MEDIA_SYNC_HOURS,
        CONF_RECORDING_MEDIA_STORAGE_PATH,
        CONF_RECORDING_CACHE_RETENTION_DAYS,
        CONF_RECORDING_CACHE_MAX_SIZE_MB,
        CONF_RECORDING_NOTIFICATION_QUALITY,
        CONF_RECORDING_MEDIA_DAYS_ORDER,
        CONF_RECORDING_MEDIA_CLIPS_ORDER,
    ]


def test_options_schema_can_hide_camera_recording_options():
    schema = options_schema({}, include_recording_options=False)

    assert schema.schema == {}
    assert schema({}) == {}


def test_options_schema_rejects_removed_camera_path_option():
    schema = options_schema({})

    with pytest.raises(vol.Invalid):
        schema({"camera_live_view_mode": "webrtc_signal"})


def test_options_schema_accepts_recording_sync_options():
    schema = options_schema({})

    assert schema(
        {
            CONF_RECORDING_CACHE_MODE: "retained",
            CONF_RECORDING_MEDIA_SYNC_ENABLED: True,
            CONF_RECORDING_MEDIA_SYNC_HOURS: "6",
            CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/xsense_alt",
            CONF_RECORDING_CACHE_RETENTION_DAYS: 14,
            CONF_RECORDING_CACHE_MAX_SIZE_MB: 4096,
            CONF_RECORDING_NOTIFICATION_QUALITY: "sd",
            CONF_RECORDING_MEDIA_DAYS_ORDER: "ascending",
            CONF_RECORDING_MEDIA_CLIPS_ORDER: "ascending",
        }
    ) == {
        CONF_RECORDING_CACHE_MODE: "retained",
        CONF_RECORDING_MEDIA_DAYS_ORDER: "ascending",
        CONF_RECORDING_MEDIA_CLIPS_ORDER: "ascending",
        CONF_RECORDING_MEDIA_SYNC_ENABLED: True,
        CONF_RECORDING_MEDIA_SYNC_HOURS: 6,
        CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/xsense_alt",
        CONF_RECORDING_CACHE_RETENTION_DAYS: 14,
        CONF_RECORDING_CACHE_MAX_SIZE_MB: 4096,
        CONF_RECORDING_NOTIFICATION_QUALITY: "sd",
    }


def test_options_schema_can_be_serialized_for_home_assistant_options_ui():
    converted = _serialize_options_schema(options_schema({}))
    storage_path_field = next(
        item
        for item in converted
        if item["name"] == CONF_RECORDING_MEDIA_STORAGE_PATH
    )
    quality_field = next(
        item for item in converted if item["name"] == CONF_RECORDING_NOTIFICATION_QUALITY
    )
    days_order_field = next(
        item for item in converted if item["name"] == CONF_RECORDING_MEDIA_DAYS_ORDER
    )

    assert storage_path_field["type"] == "string"
    assert storage_path_field["default"] == "/media/xsense_recordings"
    assert quality_field["selector"]["select"]["translation_key"] == (
        CONF_RECORDING_NOTIFICATION_QUALITY
    )
    assert quality_field["selector"]["select"]["options"] == ["hd", "sd"]
    assert days_order_field["selector"]["select"]["translation_key"] == (
        CONF_RECORDING_MEDIA_DAYS_ORDER
    )
    assert days_order_field["selector"]["select"]["options"] == [
        "ascending",
        "descending",
    ]


def test_options_schema_normalizes_stale_prerelease_options():
    schema = options_schema(
        {
            CONF_RECORDING_CACHE_MODE: "invalid",
            CONF_RECORDING_MEDIA_SYNC_ENABLED: "yes",
            CONF_RECORDING_MEDIA_SYNC_HOURS: "999",
            CONF_RECORDING_MEDIA_STORAGE_PATH: "/tmp/xsense",
            CONF_RECORDING_NOTIFICATION_QUALITY: "bad",
            CONF_RECORDING_MEDIA_DAYS_ORDER: "newest_first",
            CONF_RECORDING_MEDIA_CLIPS_ORDER: "oldest-first",
        }
    )

    assert schema({}) == {
        CONF_RECORDING_CACHE_MODE: DEFAULT_RECORDING_CACHE_MODE,
        CONF_RECORDING_MEDIA_SYNC_ENABLED: False,
        CONF_RECORDING_MEDIA_SYNC_HOURS: DEFAULT_RECORDING_MEDIA_SYNC_HOURS,
        CONF_RECORDING_MEDIA_STORAGE_PATH: DEFAULT_RECORDING_MEDIA_STORAGE_PATH,
        CONF_RECORDING_CACHE_RETENTION_DAYS: DEFAULT_RECORDING_CACHE_RETENTION_DAYS,
        CONF_RECORDING_CACHE_MAX_SIZE_MB: DEFAULT_RECORDING_CACHE_MAX_SIZE_MB,
        CONF_RECORDING_NOTIFICATION_QUALITY: DEFAULT_RECORDING_NOTIFICATION_QUALITY,
        CONF_RECORDING_MEDIA_DAYS_ORDER: "descending",
        CONF_RECORDING_MEDIA_CLIPS_ORDER: "ascending",
    }


def test_options_schema_accepts_storage_path_text_for_ui_validation():
    schema = options_schema({})

    assert (
        schema({CONF_RECORDING_MEDIA_STORAGE_PATH: "/tmp/xsense"})[
            CONF_RECORDING_MEDIA_STORAGE_PATH
        ]
        == "/tmp/xsense"
    )


def test_options_flow_rejects_storage_path_outside_media_without_schema_crash():
    flow = XSenseOptionsFlow(SimpleNamespace(options={}))
    user_input = {
        CONF_RECORDING_MEDIA_STORAGE_PATH: "/tmp/xsense",
        CONF_RECORDING_MEDIA_SYNC_ENABLED: False,
        CONF_RECORDING_MEDIA_SYNC_HOURS: 6,
        CONF_RECORDING_NOTIFICATION_QUALITY: "hd",
        CONF_RECORDING_MEDIA_DAYS_ORDER: "ascending",
        CONF_RECORDING_MEDIA_CLIPS_ORDER: "ascending",
    }

    result = asyncio.run(flow.async_step_init(user_input))

    assert result["type"] == "form"
    assert result["step_id"] == "init"
    assert result["errors"] == {
        CONF_RECORDING_MEDIA_STORAGE_PATH: "invalid_recording_media_path"
    }


def test_options_flow_aborts_without_cameras():
    flow = XSenseOptionsFlow(
        SimpleNamespace(
            entry_id="entry-no-camera",
            options={
                CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/xsense_recordings",
            },
        )
    )
    flow.hass = SimpleNamespace(
        data={
            "xsense": {
                "entry-no-camera": SimpleNamespace(
                    data={
                        "stations": {"station": SimpleNamespace(type="SBS50")},
                        "devices": {"detector": SimpleNamespace(type="XS01-M")},
                    }
                )
            }
        }
    )

    result = asyncio.run(flow.async_step_init())

    assert result["type"] == "abort"
    assert result["reason"] == "no_options"


def test_options_flow_keeps_recording_options_with_cameras():
    flow = XSenseOptionsFlow(
        SimpleNamespace(
            entry_id="entry-camera",
            options={
                CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/xsense_recordings",
            },
        )
    )
    flow.hass = SimpleNamespace(
        data={
            "xsense": {
                "entry-camera": SimpleNamespace(
                    data={
                        "stations": {},
                        "devices": {"camera": SimpleNamespace(type="SSC0A")},
                    }
                )
            }
        }
    )

    result = asyncio.run(flow.async_step_init())

    assert result["type"] == "form"
    assert result["step_id"] == "init"
    assert [field.schema for field in result["data_schema"].schema] == [
        CONF_RECORDING_CACHE_MODE,
        CONF_RECORDING_MEDIA_SYNC_ENABLED,
        CONF_RECORDING_MEDIA_SYNC_HOURS,
        CONF_RECORDING_MEDIA_STORAGE_PATH,
        CONF_RECORDING_CACHE_RETENTION_DAYS,
        CONF_RECORDING_CACHE_MAX_SIZE_MB,
        CONF_RECORDING_NOTIFICATION_QUALITY,
        CONF_RECORDING_MEDIA_DAYS_ORDER,
        CONF_RECORDING_MEDIA_CLIPS_ORDER,
    ]


def test_recording_media_storage_path_change_detection():
    assert recording_media_storage_path({}) == DEFAULT_RECORDING_MEDIA_STORAGE_PATH
    assert not recording_media_storage_path_changed(
        {},
        {CONF_RECORDING_MEDIA_STORAGE_PATH: DEFAULT_RECORDING_MEDIA_STORAGE_PATH},
    )
    assert recording_media_storage_path_changed(
        {CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/old"},
        {CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/new"},
    )


def test_options_flow_confirms_recording_storage_path_changes():
    flow = XSenseOptionsFlow(
        SimpleNamespace(
            options={
                CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/xsense_recordings",
                CONF_RECORDING_MEDIA_SYNC_ENABLED: False,
                CONF_RECORDING_MEDIA_SYNC_HOURS: 24,
                CONF_RECORDING_NOTIFICATION_QUALITY: "hd",
                CONF_RECORDING_MEDIA_DAYS_ORDER: "descending",
                CONF_RECORDING_MEDIA_CLIPS_ORDER: "descending",
            }
        )
    )
    user_input = {
        CONF_RECORDING_CACHE_MODE: DEFAULT_RECORDING_CACHE_MODE,
        CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/xsense_alt",
        CONF_RECORDING_MEDIA_SYNC_ENABLED: False,
        CONF_RECORDING_MEDIA_SYNC_HOURS: 6,
        CONF_RECORDING_CACHE_RETENTION_DAYS: DEFAULT_RECORDING_CACHE_RETENTION_DAYS,
        CONF_RECORDING_CACHE_MAX_SIZE_MB: DEFAULT_RECORDING_CACHE_MAX_SIZE_MB,
        CONF_RECORDING_NOTIFICATION_QUALITY: "sd",
        CONF_RECORDING_MEDIA_DAYS_ORDER: "ascending",
        CONF_RECORDING_MEDIA_CLIPS_ORDER: "ascending",
    }

    warning = asyncio.run(flow.async_step_init(user_input))

    assert warning["type"] == "form"
    assert warning["step_id"] == "confirm_recording_media_storage_path"
    assert warning["description_placeholders"] == {
        "old_path": "/media/xsense_recordings",
        "new_path": "/media/xsense_alt",
    }

    result = asyncio.run(flow.async_step_confirm_recording_media_storage_path({}))

    assert result["type"] == "create_entry"
    assert result["data"] == user_input


def test_options_flow_preserves_effective_legacy_values_without_credentials():
    legacy = {
        CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/legacy",
        CONF_RECORDING_MEDIA_DAYS_ORDER: "ascending",
        CONF_RECORDING_MEDIA_CLIPS_ORDER: "ascending",
    }
    flow = XSenseOptionsFlow(SimpleNamespace(
        options={},
        data={**legacy, "email": "test@example.invalid", "password": "secret",
              CONF_RECORDING_CACHE_MODE: "retained"},
    ))

    form = asyncio.run(flow.async_step_init())
    values = form["data_schema"]({})
    assert all(values[key] == value for key, value in legacy.items())
    assert values[CONF_RECORDING_CACHE_MODE] == DEFAULT_RECORDING_CACHE_MODE
    result = asyncio.run(flow.async_step_init(values))

    assert result["type"] == "create_entry"
    assert result["data"] == values
    assert "email" not in result["data"]
    assert "password" not in result["data"]


def test_options_flow_confirms_change_from_effective_legacy_path():
    flow = XSenseOptionsFlow(SimpleNamespace(
        options={}, data={CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/legacy"},
    ))
    form = asyncio.run(flow.async_step_init())
    values = form["data_schema"]({
        CONF_RECORDING_MEDIA_STORAGE_PATH: DEFAULT_RECORDING_MEDIA_STORAGE_PATH,
    })

    warning = asyncio.run(flow.async_step_init(values))

    assert warning["step_id"] == "confirm_recording_media_storage_path"
    assert warning["description_placeholders"] == {
        "old_path": "/media/legacy",
        "new_path": DEFAULT_RECORDING_MEDIA_STORAGE_PATH,
    }
    result = asyncio.run(flow.async_step_confirm_recording_media_storage_path({}))
    assert result["data"] == values


def test_options_flow_prefers_options_over_legacy_data():
    legacy = {
        CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/legacy",
        CONF_RECORDING_MEDIA_DAYS_ORDER: "ascending",
        CONF_RECORDING_MEDIA_CLIPS_ORDER: "ascending",
    }
    current = {
        CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/current",
        CONF_RECORDING_MEDIA_DAYS_ORDER: "descending",
        CONF_RECORDING_MEDIA_CLIPS_ORDER: "descending",
    }
    flow = XSenseOptionsFlow(SimpleNamespace(options=current, data=legacy))

    form = asyncio.run(flow.async_step_init())
    values = form["data_schema"]({})

    assert all(values[key] == value for key, value in current.items())
    assert asyncio.run(flow.async_step_init(values))["type"] == "create_entry"


@pytest.mark.parametrize("loaded_data", [None, {}, {"stations": {}, "devices": {}}])
@pytest.mark.parametrize("owner,domain,platform,disabled", [
    ("entry-camera", "camera", "xsense", None),
    ("entry-camera", "camera", "xsense", "user"),
    ("other-entry", "camera", "xsense", None),
    ("entry-camera", "sensor", "xsense", None),
    ("entry-camera", "camera", "other", None),
])
def test_options_flow_registry_fallback_is_entry_scoped_and_unloaded_only(
    monkeypatch, loaded_data, owner, domain, platform, disabled,
):
    record = SimpleNamespace(
        config_entry_id=owner, domain=domain, platform=platform, disabled_by=disabled,
    )
    registry = SimpleNamespace(entities=SimpleNamespace(
        get_entries_for_config_entry_id=lambda entry_id: (
            [record] if record.config_entry_id == entry_id else []
        ),
    ))
    monkeypatch.setattr(er, "async_get", lambda hass: registry)
    flow = XSenseOptionsFlow(SimpleNamespace(entry_id="entry-camera", options={}))
    flow.hass = SimpleNamespace(data={"xsense": {
        "entry-camera": SimpleNamespace(data=loaded_data),
    }})

    result = asyncio.run(flow.async_step_init())

    eligible = (loaded_data is None and owner == "entry-camera"
                and domain == "camera" and platform == "xsense")
    assert result["type"] == ("form" if eligible else "abort")
    if not eligible:
        assert result["reason"] == "no_options"


def test_unloaded_camera_entry_can_save_storage_options(monkeypatch):
    record = SimpleNamespace(domain="camera", platform="xsense")
    registry = SimpleNamespace(entities=SimpleNamespace(
        get_entries_for_config_entry_id=lambda entry_id: (
            [record] if entry_id == "entry-camera" else []
        ),
    ))
    monkeypatch.setattr(er, "async_get", lambda hass: registry)
    flow = XSenseOptionsFlow(SimpleNamespace(entry_id="entry-camera", options={}))
    flow.hass = SimpleNamespace(data={})

    form = asyncio.run(flow.async_step_init())
    values = form["data_schema"]({CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/repaired"})
    warning = asyncio.run(flow.async_step_init(values))
    assert warning["step_id"] == "confirm_recording_media_storage_path"
    result = asyncio.run(flow.async_step_confirm_recording_media_storage_path({}))
    assert result["data"] == values


@pytest.fixture
def options_manager():
    entry = SimpleNamespace(entry_id="audit", options={}, data={})

    def update(current, options):
        current.options = options
        return True

    hass = SimpleNamespace(
        data={"xsense": {"audit": SimpleNamespace(data={
            "stations": {"cam": SimpleNamespace(type="SSC0A")}, "devices": {},
        })}},
        config_entries=SimpleNamespace(
            async_get_entry=lambda _: entry, async_get_known_entry=lambda _: entry,
            async_update_entry=update,
        ),
    )

    class Manager(OptionsFlowManager):
        async def async_create_flow(self, *args, **kwargs):
            return XSenseOptionsFlow(entry)

        async def _async_setup_preview(self, *args, **kwargs):
            pass

    return SimpleNamespace(entry=entry, manager=Manager(hass), hass=hass)


def test_stale_options_form_confirms_against_current_persisted_path(options_manager):
    state = options_manager

    async def run():
        old = await state.manager.async_init("audit", context={"source": "init"})
        newer = await state.manager.async_init("audit", context={"source": "init"})
        await state.manager.async_configure(newer["flow_id"], {
            CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/newer",
        })
        await state.manager.async_configure(newer["flow_id"], {})
        warning = await state.manager.async_configure(old["flow_id"], {
            CONF_RECORDING_NOTIFICATION_QUALITY: "sd",
        })
        assert warning["step_id"] == "confirm_recording_media_storage_path"
        assert warning["description_placeholders"] == {
            "old_path": "/media/newer", "new_path": DEFAULT_RECORDING_MEDIA_STORAGE_PATH,
        }
        assert state.entry.options[CONF_RECORDING_MEDIA_STORAGE_PATH] == "/media/newer"
        await state.manager.async_configure(old["flow_id"], {})
        assert state.entry.options[CONF_RECORDING_MEDIA_STORAGE_PATH] == DEFAULT_RECORDING_MEDIA_STORAGE_PATH
        assert state.entry.options[CONF_RECORDING_NOTIFICATION_QUALITY] == "sd"

    asyncio.run(run())


@pytest.mark.parametrize("replace_entry", [False, True])
def test_confirmation_rechecks_current_legacy_path(options_manager, replace_entry):
    state = options_manager

    async def run():
        form = await state.manager.async_init("audit", context={"source": "init"})
        await state.manager.async_configure(form["flow_id"], {
            CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/requested",
        })
        if replace_entry:
            state.entry = SimpleNamespace(entry_id="audit", options={}, data={})
            state.hass.config_entries.async_get_entry = lambda _: state.entry
            state.hass.config_entries.async_get_known_entry = lambda _: state.entry
        state.entry.data[CONF_RECORDING_MEDIA_STORAGE_PATH] = "/media/concurrent"
        warning = await state.manager.async_configure(form["flow_id"], {})
        assert warning["type"] == "form"
        assert warning["description_placeholders"] == {
            "old_path": "/media/concurrent", "new_path": "/media/requested",
        }
        assert state.entry.options == {}
        await state.manager.async_configure(form["flow_id"], {})
        assert state.entry.options[CONF_RECORDING_MEDIA_STORAGE_PATH] == "/media/requested"

    asyncio.run(run())


@pytest.mark.parametrize("suffix", ["", "/child/grandchild"])
def test_storage_path_rejects_existing_file_and_file_ancestor(monkeypatch, suffix):
    original_stat = Path.stat

    def stat(path, *args, **kwargs):
        if str(path) == "/media/file":
            return SimpleNamespace(st_mode=0o100644)
        if str(path).startswith("/media/file/"):
            raise NotADirectoryError(str(path))
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", stat)
    flow = XSenseOptionsFlow(SimpleNamespace(options={}))
    values = options_schema()({
        CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/file" + suffix,
        CONF_RECORDING_NOTIFICATION_QUALITY: "sd",
    })
    result = asyncio.run(flow.async_step_init(values))
    assert result["errors"] == {
        CONF_RECORDING_MEDIA_STORAGE_PATH: "invalid_recording_media_path",
    }
    hints = {field.schema: field.description["suggested_value"] for field in result["data_schema"].schema}
    assert hints[CONF_RECORDING_MEDIA_STORAGE_PATH] == values[CONF_RECORDING_MEDIA_STORAGE_PATH]
    assert hints[CONF_RECORDING_NOTIFICATION_QUALITY] == "sd"


def test_confirmation_revalidates_destination_before_save(monkeypatch, options_manager):
    state = options_manager

    async def run():
        form = await state.manager.async_init("audit", context={"source": "init"})
        await state.manager.async_configure(form["flow_id"], {
            CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/requested",
            CONF_RECORDING_NOTIFICATION_QUALITY: "sd",
        })
        original_stat = Path.stat

        def stat(path, *args, **kwargs):
            if str(path) == "/media/requested":
                return SimpleNamespace(st_mode=0o100644)
            return original_stat(path, *args, **kwargs)

        monkeypatch.setattr(Path, "stat", stat)
        error = await state.manager.async_configure(form["flow_id"], {})
        assert error["step_id"] == "init"
        assert error["errors"][CONF_RECORDING_MEDIA_STORAGE_PATH] == "invalid_recording_media_path"
        assert state.entry.options == {}

    asyncio.run(run())


def test_options_filesystem_checks_run_off_event_loop(monkeypatch, options_manager):
    state = options_manager
    thread_ids = []
    original_resolve, original_stat = Path.resolve, Path.stat

    def resolve(path, *args, **kwargs):
        thread_ids.append(threading.get_ident())
        return original_resolve(path, *args, **kwargs)

    def stat(path, *args, **kwargs):
        thread_ids.append(threading.get_ident())
        return original_stat(path, *args, **kwargs)

    async def run():
        event_loop_thread = threading.get_ident()
        state.hass.async_add_executor_job = Mock(side_effect=asyncio.to_thread)
        monkeypatch.setattr(Path, "resolve", resolve)
        monkeypatch.setattr(Path, "stat", stat)
        form = await state.manager.async_init("audit", context={"source": "init"})
        await state.manager.async_configure(form["flow_id"], {
            CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/new/nested",
        })
        result = await state.manager.async_configure(form["flow_id"], {})
        assert result["type"] == "create_entry"
        assert thread_ids and event_loop_thread not in thread_ids
        assert state.hass.async_add_executor_job.call_count > 0

    asyncio.run(run())


def test_options_flow_saves_without_warning_when_storage_path_unchanged():
    flow = XSenseOptionsFlow(
        SimpleNamespace(
            options={
                CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/xsense_recordings",
            }
        )
    )
    user_input = {
        CONF_RECORDING_CACHE_MODE: DEFAULT_RECORDING_CACHE_MODE,
        CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/xsense_recordings",
        CONF_RECORDING_MEDIA_SYNC_ENABLED: False,
        CONF_RECORDING_MEDIA_SYNC_HOURS: 6,
        CONF_RECORDING_CACHE_RETENTION_DAYS: DEFAULT_RECORDING_CACHE_RETENTION_DAYS,
        CONF_RECORDING_CACHE_MAX_SIZE_MB: DEFAULT_RECORDING_CACHE_MAX_SIZE_MB,
        CONF_RECORDING_NOTIFICATION_QUALITY: "hd",
        CONF_RECORDING_MEDIA_DAYS_ORDER: "ascending",
        CONF_RECORDING_MEDIA_CLIPS_ORDER: "ascending",
    }

    result = asyncio.run(flow.async_step_init(user_input))

    assert result["type"] == "create_entry"
    assert result["data"] == user_input
