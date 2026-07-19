from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from custom_components.xsense.python_xsense.entity_map import EntityType
from custom_components.xsense.sensor import (
    SENSORS,
    battery_percentage,
    has_report_time,
    has_self_test_report,
    optional_data_timestamp,
    self_test_result,
)


def _sensor_description(key):
    return next(description for description in SENSORS if description.key == key)


def test_battery_percentage_returns_unknown_for_non_numeric_value():
    entity = SimpleNamespace(data={"batInfo": "unknown"})

    assert battery_percentage(entity) is None


def test_base_station_report_time_is_internal_metadata():
    entity = SimpleNamespace(
        data={"time": "20260531150149"},
        entity_type=EntityType.BASESTATION,
    )

    assert not has_report_time(entity)


def test_device_report_time_remains_available():
    entity = SimpleNamespace(
        data={"time": "20260531150149"},
        entity_type=EntityType.TEMPERATURE,
    )

    assert has_report_time(entity)


def test_self_test_result_success_code_matches_apk():
    entity = SimpleNamespace(data={"lastSelfTest": "0"})

    assert self_test_result(entity) == "success"


def test_self_test_result_accepts_success_text():
    entity = SimpleNamespace(data={"lastSelfTest": "successful"})

    assert self_test_result(entity) == "success"


def test_self_test_result_preserves_failure_code():
    entity = SimpleNamespace(data={"lastSelfTest": "3"})

    assert self_test_result(entity) == "failed"


@pytest.mark.parametrize("device_type", ["XS01-M", "XS01-WX", "SC06-WX", "XS0B-iR"])
def test_self_test_report_sensor_exists_for_report_capable_device_before_first_report(
    device_type,
):
    entity = SimpleNamespace(data={}, type=device_type)

    assert has_self_test_report(entity)


@pytest.mark.parametrize("device_type", ["XS01-WX", "SC06-WX", "XS0B-iR"])
def test_self_test_report_does_not_require_remote_test_action(device_type):
    entity = SimpleNamespace(data={}, type=device_type)

    assert has_self_test_report(entity)


def test_self_test_report_sensor_exists_after_report_even_without_action_map():
    entity = SimpleNamespace(data={"lastSelfTest": "0"}, type="UNKNOWN")

    assert has_self_test_report(entity)


def test_self_test_result_not_run_before_first_report():
    entity = SimpleNamespace(data={})

    assert self_test_result(entity) == "not_run"


def test_optional_timestamp_is_none_before_first_report():
    entity = SimpleNamespace(data={})

    assert optional_data_timestamp("lastSelfTestTime")(entity) is None


def test_radon_peak_entities_are_model_backed_before_first_report():
    entity = SimpleNamespace(data={}, type="XR0A-iR")

    assert _sensor_description("radon_peak").exists_fn(entity)
    assert _sensor_description("radon_peak").value_fn(entity) is None
    assert _sensor_description("radon_peak_time").exists_fn(entity)
    assert _sensor_description("radon_peak_time").value_fn(entity) is None


def test_radon_peak_entities_use_apk_values():
    entity = SimpleNamespace(
        data={"radonPeak": 148.5, "radonPeakTime": "20260719101011"},
        type="XR0A-iR",
    )

    assert _sensor_description("radon_peak").value_fn(entity) == 148.5
    assert _sensor_description("radon_peak_time").value_fn(entity) == datetime(
        2026, 7, 19, 10, 10, 11, tzinfo=timezone.utc
    )
