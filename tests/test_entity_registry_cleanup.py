from types import SimpleNamespace

from custom_components.xsense import (
    OBSOLETE_SENSOR_KEYS,
    _obsolete_sensor_unique_ids,
    _sensor_unique_id,
)


def test_obsolete_sensor_unique_ids_match_old_sensor_format():
    assert _sensor_unique_id("base_SN", "serial_number") == "base-sn-serial-number"


def test_obsolete_sensor_cleanup_targets_static_identifier_entities_only():
    station = SimpleNamespace(entity_id="station_1")
    device = SimpleNamespace(entity_id="device_1")

    unique_ids = _obsolete_sensor_unique_ids(
        {"stations": {"station_1": station}, "devices": {"device_1": device}}
    )

    assert len(unique_ids) == len(OBSOLETE_SENSOR_KEYS) * 2
    assert "station-1-serial-number" in unique_ids
    assert "station-1-station-sn" in unique_ids
    assert "station-1-device-mac" in unique_ids
    assert "device-1-bluetooth-mac" in unique_ids
    assert "station-1-ip" not in unique_ids
    assert "device-1-wifi-rssi" not in unique_ids
