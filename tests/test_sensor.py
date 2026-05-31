from types import SimpleNamespace

from custom_components.xsense.api.entity_map import EntityType
from custom_components.xsense.sensor import has_report_time


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
