import pytest
import voluptuous as vol

from custom_components.xsense.config_flow import options_schema


def test_options_schema_has_no_camera_path_option():
    schema = options_schema({})

    assert schema({}) == {}


def test_options_schema_rejects_removed_camera_path_option():
    schema = options_schema({})

    with pytest.raises(vol.Invalid):
        schema({"camera_live_view_mode": "webrtc_signal"})
