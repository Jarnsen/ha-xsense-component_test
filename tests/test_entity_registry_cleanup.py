from types import SimpleNamespace

from custom_components.xsense import (
    OBSOLETE_SENSOR_KEYS,
    _is_obsolete_sensor_entry,
    _obsolete_sensor_unique_ids,
    _sensor_unique_id,
    _clear_visible_device_metadata,
    _remove_obsolete_device_metadata,
    _remove_obsolete_sensor_entities,
    _visible_identifier_connections_removed,
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


def test_static_identifiers_are_not_exposed_in_device_info():
    from custom_components.xsense.entity import XSenseEntity

    class ProbeEntity(XSenseEntity):
        entity_description = SimpleNamespace(key="probe")

    source = SimpleNamespace(
        entity_id="station_1",
        data={
            "mac": "00:11:22:33:44:55",
            "macBT": "AA:BB:CC:DD:EE:FF",
            "sw": "v1.0",
        },
        sn="serial-number",
        type="SBS50",
        name="Base Station",
    )

    device_info = ProbeEntity(SimpleNamespace(), source).device_info

    assert device_info["identifiers"] == {("xsense", "station_1")}
    assert device_info["model"] == "SBS50"
    assert device_info["sw_version"] == "1.0"
    assert "serial_number" not in device_info
    assert "connections" not in device_info


def test_alarm_panel_device_info_does_not_expose_serial_number():
    from custom_components.xsense.alarm_control_panel import XSenseAlarmControlPanel

    station = SimpleNamespace(
        entity_id="station_1",
        name="Base Station",
        type="SBS50",
        sn="serial-number",
    )

    device_info = XSenseAlarmControlPanel(SimpleNamespace(), station).device_info

    assert device_info["identifiers"] == {("xsense", "station_1")}
    assert device_info["model"] == "SBS50"
    assert "serial_number" not in device_info


def test_visible_identifier_connections_are_removed_from_registry_metadata():
    connections = {
        ("bluetooth", "AA:BB:CC:DD:EE:FF"),
        ("mac", "00:11:22:33:44:55"),
        ("something_else", "kept"),
    }

    assert _visible_identifier_connections_removed(connections) == {
        ("something_else", "kept")
    }


def test_clear_visible_device_metadata_clears_registry_identifiers():
    device = SimpleNamespace(
        id="device-id",
        serial_number="serial-number",
        connections={
            ("bluetooth", "AA:BB:CC:DD:EE:FF"),
            ("mac", "00:11:22:33:44:55"),
            ("something_else", "kept"),
        },
    )
    calls = []

    class FakeDeviceRegistry:
        def async_update_device(self, device_id, **kwargs):
            calls.append((device_id, kwargs))

    _clear_visible_device_metadata(FakeDeviceRegistry(), device)

    assert calls == [
        (
            "device-id",
            {
                "new_connections": {("something_else", "kept")},
                "serial_number": None,
            },
        )
    ]


def test_obsolete_device_metadata_cleanup_skips_clean_registry_entries(monkeypatch):
    device = SimpleNamespace(
        id="device-id",
        serial_number=None,
        connections={("something_else", "kept")},
    )
    calls = []

    class FakeDeviceRegistry:
        def async_get_device(self, *, identifiers):
            assert identifiers == {("xsense", "station_1")}
            return device

        def async_update_device(self, device_id, **kwargs):
            calls.append((device_id, kwargs))

    import custom_components.xsense as xsense

    monkeypatch.setattr(xsense.dr, "async_get", lambda hass: FakeDeviceRegistry())

    monkeypatch.setattr(
        xsense.dr,
        "async_entries_for_config_entry",
        lambda registry, entry_id: [],
    )

    _remove_obsolete_device_metadata(
        SimpleNamespace(),
        {
            "stations": {
                "station_1": SimpleNamespace(entity_id="station_1")
            },
            "devices": {},
        },
        SimpleNamespace(entry_id="entry-id"),
    )

    assert calls == []


def test_obsolete_device_metadata_cleanup_handles_child_devices(monkeypatch):
    devices_by_identifier = {
        ("xsense", "station_1"): None,
        ("xsense", "device_1"): SimpleNamespace(
            id="child-device-id",
            serial_number="child-serial",
            connections={("mac", "00:11:22:33:44:55")},
        ),
    }
    calls = []

    class FakeDeviceRegistry:
        def async_get_device(self, *, identifiers):
            return devices_by_identifier[next(iter(identifiers))]

        def async_update_device(self, device_id, **kwargs):
            calls.append((device_id, kwargs))

    import custom_components.xsense as xsense

    monkeypatch.setattr(xsense.dr, "async_get", lambda hass: FakeDeviceRegistry())

    monkeypatch.setattr(
        xsense.dr,
        "async_entries_for_config_entry",
        lambda registry, entry_id: [],
    )

    _remove_obsolete_device_metadata(
        SimpleNamespace(),
        {
            "stations": {
                "station_1": SimpleNamespace(entity_id="station_1")
            },
            "devices": {
                "device_1": SimpleNamespace(entity_id="device_1")
            },
        },
        SimpleNamespace(entry_id="entry-id"),
    )

    assert calls == [
        (
            "child-device-id",
            {"new_connections": set(), "serial_number": None},
        )
    ]


def test_obsolete_device_metadata_cleanup_scans_config_entry_devices(monkeypatch):
    stale_device = SimpleNamespace(
        id="stale-device-id",
        serial_number="stale-serial",
        connections={("mac", "00:11:22:33:44:55")},
    )
    calls = []

    class FakeDeviceRegistry:
        def async_get_device(self, *, identifiers):
            return None

        def async_update_device(self, device_id, **kwargs):
            calls.append((device_id, kwargs))

    import custom_components.xsense as xsense

    monkeypatch.setattr(xsense.dr, "async_get", lambda hass: FakeDeviceRegistry())
    monkeypatch.setattr(
        xsense.dr,
        "async_entries_for_config_entry",
        lambda registry, entry_id: [stale_device],
    )

    _remove_obsolete_device_metadata(
        SimpleNamespace(),
        {"stations": {}, "devices": {}},
        SimpleNamespace(entry_id="entry-id"),
    )

    assert calls == [
        (
            "stale-device-id",
            {"new_connections": set(), "serial_number": None},
        )
    ]


def test_obsolete_sensor_entry_detection_is_scoped_to_xsense_sensors():
    assert _is_obsolete_sensor_entry(
        SimpleNamespace(
            domain="sensor",
            platform="xsense",
            unique_id="old-device-serial-number",
        )
    )
    assert not _is_obsolete_sensor_entry(
        SimpleNamespace(
            domain="binary_sensor",
            platform="xsense",
            unique_id="old-device-serial-number",
        )
    )
    assert not _is_obsolete_sensor_entry(
        SimpleNamespace(
            domain="sensor",
            platform="other",
            unique_id="old-device-serial-number",
        )
    )
    assert not _is_obsolete_sensor_entry(
        SimpleNamespace(
            domain="sensor",
            platform="xsense",
            unique_id="station-1-ip",
        )
    )


def test_obsolete_sensor_cleanup_removes_stale_registry_entries(monkeypatch):
    removed = []

    class FakeEntityRegistry:
        def async_get_entity_id(self, platform, domain, unique_id):
            return None

        def async_remove(self, entity_id):
            removed.append(entity_id)

    registry = FakeEntityRegistry()
    entries = [
        SimpleNamespace(
            domain="sensor",
            platform="xsense",
            unique_id="missing-device-serial-number",
            entity_id="sensor.missing_device_serial_number",
        ),
        SimpleNamespace(
            domain="sensor",
            platform="xsense",
            unique_id="station-1-ip",
            entity_id="sensor.station_1_ip",
        ),
    ]

    import custom_components.xsense as xsense

    monkeypatch.setattr(xsense.er, "async_get", lambda hass: registry)
    monkeypatch.setattr(
        xsense.er,
        "async_entries_for_config_entry",
        lambda entity_registry, entry_id: entries,
    )

    _remove_obsolete_sensor_entities(
        SimpleNamespace(),
        {
            "stations": {
                "station_1": SimpleNamespace(entity_id="station_1")
            },
            "devices": {},
        },
        SimpleNamespace(entry_id="entry-id"),
    )

    assert removed == ["sensor.missing_device_serial_number"]
