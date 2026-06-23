import logging
from types import SimpleNamespace

import pytest
import voluptuous as vol

from custom_components.xsense import _sync_experimental_debug_logging
from custom_components.xsense.config_flow import options_schema
from custom_components.xsense.const import (
    CAMERA_LIVE_VIEW_MODE_STREAM_SOURCE,
    CAMERA_LIVE_VIEW_MODE_WEBRTC_SIGNAL,
    CONF_CAMERA_LIVE_VIEW_MODE,
    DOMAIN,
    LOGGER,
)


def test_options_schema_defaults_to_stable_stream_source_path():
    schema = options_schema({})

    assert schema({}) == {CONF_CAMERA_LIVE_VIEW_MODE: CAMERA_LIVE_VIEW_MODE_STREAM_SOURCE}


def test_options_schema_accepts_experimental_webrtc_bridge_mode():
    schema = options_schema(
        {CONF_CAMERA_LIVE_VIEW_MODE: CAMERA_LIVE_VIEW_MODE_WEBRTC_SIGNAL}
    )

    assert schema(
        {CONF_CAMERA_LIVE_VIEW_MODE: CAMERA_LIVE_VIEW_MODE_WEBRTC_SIGNAL}
    ) == {CONF_CAMERA_LIVE_VIEW_MODE: CAMERA_LIVE_VIEW_MODE_WEBRTC_SIGNAL}


def test_options_schema_rejects_unknown_camera_live_mode():
    schema = options_schema({})

    with pytest.raises(vol.Invalid):
        schema({CONF_CAMERA_LIVE_VIEW_MODE: "unknown"})


def test_experimental_webrtc_bridge_option_enables_debug_logging():
    previous_level = LOGGER.level
    hass = SimpleNamespace(data={})

    try:
        LOGGER.setLevel(logging.WARNING)
        _sync_experimental_debug_logging(
            hass,
            SimpleNamespace(
                entry_id="entry-1",
                options={CONF_CAMERA_LIVE_VIEW_MODE: CAMERA_LIVE_VIEW_MODE_WEBRTC_SIGNAL}
            ),
        )

        assert LOGGER.level == logging.DEBUG
        assert hass.data[DOMAIN]["_auto_debug_previous_level"] == logging.WARNING
        assert hass.data[DOMAIN]["_auto_debug_entry_ids"] == {"entry-1"}

        _sync_experimental_debug_logging(
            hass,
            SimpleNamespace(
                entry_id="entry-1",
                options={CONF_CAMERA_LIVE_VIEW_MODE: CAMERA_LIVE_VIEW_MODE_STREAM_SOURCE}
            ),
        )

        assert LOGGER.level == logging.WARNING
        assert "_auto_debug_previous_level" not in hass.data[DOMAIN]
        assert hass.data[DOMAIN]["_auto_debug_entry_ids"] == set()
    finally:
        LOGGER.setLevel(previous_level)
