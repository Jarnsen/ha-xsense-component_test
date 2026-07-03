import asyncio
from types import SimpleNamespace

import pytest
import voluptuous as vol
import voluptuous_serialize

from custom_components.xsense.config_flow import (
    XSenseOptionsFlow,
    options_schema,
    recording_media_storage_path,
    recording_media_storage_path_changed,
)
from custom_components.xsense.const import (
    CONF_RECORDING_MEDIA_CLIPS_ORDER,
    CONF_RECORDING_MEDIA_DAYS_ORDER,
    CONF_RECORDING_MEDIA_STORAGE_PATH,
    CONF_RECORDING_MEDIA_SYNC_ENABLED,
    CONF_RECORDING_MEDIA_SYNC_HOURS,
    DEFAULT_RECORDING_MEDIA_CLIPS_ORDER,
    DEFAULT_RECORDING_MEDIA_DAYS_ORDER,
    DEFAULT_RECORDING_MEDIA_STORAGE_PATH,
    DEFAULT_RECORDING_MEDIA_SYNC_HOURS,
)


def test_options_schema_has_recording_sync_defaults_without_camera_path_option():
    schema = options_schema({})

    assert schema({}) == {
        CONF_RECORDING_MEDIA_SYNC_ENABLED: False,
        CONF_RECORDING_MEDIA_SYNC_HOURS: DEFAULT_RECORDING_MEDIA_SYNC_HOURS,
        CONF_RECORDING_MEDIA_STORAGE_PATH: DEFAULT_RECORDING_MEDIA_STORAGE_PATH,
        CONF_RECORDING_MEDIA_DAYS_ORDER: DEFAULT_RECORDING_MEDIA_DAYS_ORDER,
        CONF_RECORDING_MEDIA_CLIPS_ORDER: DEFAULT_RECORDING_MEDIA_CLIPS_ORDER,
    }


def test_options_schema_orders_recording_options_for_the_ui():
    schema = options_schema({})

    assert [field.schema for field in schema.schema] == [
        CONF_RECORDING_MEDIA_SYNC_ENABLED,
        CONF_RECORDING_MEDIA_SYNC_HOURS,
        CONF_RECORDING_MEDIA_STORAGE_PATH,
        CONF_RECORDING_MEDIA_DAYS_ORDER,
        CONF_RECORDING_MEDIA_CLIPS_ORDER,
    ]


def test_options_schema_rejects_removed_camera_path_option():
    schema = options_schema({})

    with pytest.raises(vol.Invalid):
        schema({"camera_live_view_mode": "webrtc_signal"})


def test_options_schema_accepts_recording_sync_options():
    schema = options_schema({})

    assert schema(
        {
            CONF_RECORDING_MEDIA_SYNC_ENABLED: True,
            CONF_RECORDING_MEDIA_SYNC_HOURS: "6",
            CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/xsense_alt",
            CONF_RECORDING_MEDIA_DAYS_ORDER: "Ascending",
            CONF_RECORDING_MEDIA_CLIPS_ORDER: "Ascending",
        }
    ) == {
        CONF_RECORDING_MEDIA_DAYS_ORDER: "Ascending",
        CONF_RECORDING_MEDIA_CLIPS_ORDER: "Ascending",
        CONF_RECORDING_MEDIA_SYNC_ENABLED: True,
        CONF_RECORDING_MEDIA_SYNC_HOURS: 6,
        CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/xsense_alt",
    }


def test_options_schema_can_be_serialized_for_home_assistant_options_ui():
    converted = voluptuous_serialize.convert(options_schema({}))
    storage_path_field = next(
        item
        for item in converted
        if item["name"] == CONF_RECORDING_MEDIA_STORAGE_PATH
    )

    assert storage_path_field["type"] == "string"
    assert storage_path_field["default"] == "/media/xsense_recordings"


def test_options_schema_normalizes_stale_prerelease_options():
    schema = options_schema(
        {
            CONF_RECORDING_MEDIA_SYNC_ENABLED: "yes",
            CONF_RECORDING_MEDIA_SYNC_HOURS: "999",
            CONF_RECORDING_MEDIA_STORAGE_PATH: "/tmp/xsense",
            CONF_RECORDING_MEDIA_DAYS_ORDER: "newest_first",
            CONF_RECORDING_MEDIA_CLIPS_ORDER: "oldest-first",
        }
    )

    assert schema({}) == {
        CONF_RECORDING_MEDIA_SYNC_ENABLED: True,
        CONF_RECORDING_MEDIA_SYNC_HOURS: DEFAULT_RECORDING_MEDIA_SYNC_HOURS,
        CONF_RECORDING_MEDIA_STORAGE_PATH: DEFAULT_RECORDING_MEDIA_STORAGE_PATH,
        CONF_RECORDING_MEDIA_DAYS_ORDER: "Descending",
        CONF_RECORDING_MEDIA_CLIPS_ORDER: "Ascending",
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
        CONF_RECORDING_MEDIA_SYNC_ENABLED: True,
        CONF_RECORDING_MEDIA_SYNC_HOURS: 6,
        CONF_RECORDING_MEDIA_DAYS_ORDER: "Ascending",
        CONF_RECORDING_MEDIA_CLIPS_ORDER: "Ascending",
    }

    result = asyncio.run(flow.async_step_init(user_input))

    assert result["type"] == "form"
    assert result["step_id"] == "init"
    assert result["errors"] == {
        CONF_RECORDING_MEDIA_STORAGE_PATH: "invalid_recording_media_path"
    }


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
                CONF_RECORDING_MEDIA_DAYS_ORDER: "Descending",
                CONF_RECORDING_MEDIA_CLIPS_ORDER: "Descending",
            }
        )
    )
    user_input = {
        CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/xsense_alt",
        CONF_RECORDING_MEDIA_SYNC_ENABLED: True,
        CONF_RECORDING_MEDIA_SYNC_HOURS: 6,
        CONF_RECORDING_MEDIA_DAYS_ORDER: "Ascending",
        CONF_RECORDING_MEDIA_CLIPS_ORDER: "Ascending",
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


def test_options_flow_saves_without_warning_when_storage_path_unchanged():
    flow = XSenseOptionsFlow(
        SimpleNamespace(
            options={
                CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/xsense_recordings",
            }
        )
    )
    user_input = {
        CONF_RECORDING_MEDIA_STORAGE_PATH: "/media/xsense_recordings",
        CONF_RECORDING_MEDIA_SYNC_ENABLED: True,
        CONF_RECORDING_MEDIA_SYNC_HOURS: 6,
        CONF_RECORDING_MEDIA_DAYS_ORDER: "Ascending",
        CONF_RECORDING_MEDIA_CLIPS_ORDER: "Ascending",
    }

    result = asyncio.run(flow.async_step_init(user_input))

    assert result["type"] == "create_entry"
    assert result["data"] == user_input
