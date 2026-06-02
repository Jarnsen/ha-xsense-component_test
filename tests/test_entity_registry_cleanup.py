import sys
from types import SimpleNamespace

for module_name in list(sys.modules):
    if module_name == "custom_components.xsense" or module_name.startswith(
        "custom_components.xsense."
    ):
        del sys.modules[module_name]
if not hasattr(sys.modules.get("custom_components"), "__path__"):
    sys.modules.pop("custom_components", None)

from custom_components.xsense import (
    OBSOLETE_SENSOR_KEYS,
    _is_obsolete_sensor_entry,
    _migrate_legacy_none_entity_ids,
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


def test_obsolete_sensor_cleanup_keeps_current_device_entities(monkeypatch):
    removed = []

    class FakeEntityRegistry:
        def async_get_entity_id(self, platform, domain, unique_id):
            return None

        def async_remove(self, entity_id):
            removed.append(entity_id)

    current_unique_ids = [
        "xs01-wx-alarm-status",
        "xs01-wx-battery",
        "xs01-wx-connected",
        "xs01-wx-ip-address",
        "xs01-wx-last-self-test",
        "xs01-wx-last-self-test-time",
        "xs01-wx-led-light",
        "xs01-wx-mute-status",
        "xs01-wx-report-time",
        "xs01-wx-signal-strength",
        "xs01-wx-software-version",
        "xs01-wx-ssid",
    ]
    entries = [
        SimpleNamespace(
            domain="sensor",
            platform="xsense",
            unique_id=unique_id,
            entity_id="sensor." + unique_id.replace("-", "_"),
        )
        for unique_id in current_unique_ids
    ]
    entries.extend(
        [
            SimpleNamespace(
                domain="sensor",
                platform="xsense",
                unique_id="xs01-wx-online-time",
                entity_id="sensor.xs01_wx_online_time",
            ),
            SimpleNamespace(
                domain="sensor",
                platform="xsense",
                unique_id="xs01-wx-serial-number",
                entity_id="sensor.xs01_wx_serial_number",
            ),
        ]
    )

    import custom_components.xsense as xsense

    monkeypatch.setattr(xsense.er, "async_get", lambda hass: FakeEntityRegistry())
    monkeypatch.setattr(
        xsense.er,
        "async_entries_for_config_entry",
        lambda entity_registry, entry_id: entries,
    )

    _remove_obsolete_sensor_entities(
        SimpleNamespace(),
        {"stations": {}, "devices": {"xs01_wx": SimpleNamespace(entity_id="xs01_wx")}},
        SimpleNamespace(entry_id="entry-id"),
    )

    assert removed == ["sensor.xs01_wx_online_time", "sensor.xs01_wx_serial_number"]


def test_obsolete_sensor_cleanup_scans_all_xsense_sensor_entries(monkeypatch):
    removed = []

    class FakeEntityRegistry:
        entities = {
            "sensor.orphan_serial_number": SimpleNamespace(
                domain="sensor",
                platform="xsense",
                unique_id="orphan-serial-number",
                entity_id="sensor.orphan_serial_number",
            ),
            "sensor.orphan_ip": SimpleNamespace(
                domain="sensor",
                platform="xsense",
                unique_id="orphan-ip",
                entity_id="sensor.orphan_ip",
            ),
        }

        def async_get_entity_id(self, platform, domain, unique_id):
            return None

        def async_remove(self, entity_id):
            removed.append(entity_id)

    import custom_components.xsense as xsense

    monkeypatch.setattr(xsense.er, "async_get", lambda hass: FakeEntityRegistry())
    monkeypatch.setattr(
        xsense.er,
        "async_entries_for_config_entry",
        lambda entity_registry, entry_id: [],
    )

    _remove_obsolete_sensor_entities(
        SimpleNamespace(),
        {"stations": {}, "devices": {}},
        SimpleNamespace(entry_id="entry-id"),
    )

    assert removed == ["sensor.orphan_serial_number"]


def test_legacy_none_entity_id_migration_renames_safe_entries(monkeypatch):
    renamed = []
    entries = [
        SimpleNamespace(
            domain="binary_sensor",
            platform="xsense",
            entity_id="binary_sensor.smoke_alarm_none",
            unique_id="device-connected",
            device_id="device-id",
            object_id_base="Connected",
            original_name=None,
            translation_key="connected",
        ),
        SimpleNamespace(
            domain="button",
            platform="xsense",
            entity_id="button.smoke_alarm_none",
            unique_id="device-test",
            device_id="device-id",
            object_id_base="Test",
            original_name=None,
            translation_key="test",
        ),
        SimpleNamespace(
            domain="sensor",
            platform="other",
            entity_id="sensor.other_none",
            unique_id="other-test",
            device_id="device-id",
            object_id_base="Test",
            original_name=None,
            translation_key="test",
        ),
    ]

    class FakeEntityRegistry:
        def async_get(self, entity_id):
            return None

        def async_update_entity(self, entity_id, **kwargs):
            renamed.append((entity_id, kwargs))

    class FakeDeviceRegistry:
        def async_get(self, device_id):
            assert device_id == "device-id"
            return SimpleNamespace(name_by_user=None, name="Smoke Alarm")

    import custom_components.xsense as xsense

    monkeypatch.setattr(xsense.er, "async_get", lambda hass: FakeEntityRegistry())
    monkeypatch.setattr(xsense.dr, "async_get", lambda hass: FakeDeviceRegistry())
    monkeypatch.setattr(
        xsense.er,
        "async_entries_for_config_entry",
        lambda entity_registry, entry_id: entries,
    )

    _migrate_legacy_none_entity_ids(
        SimpleNamespace(), SimpleNamespace(entry_id="entry-id")
    )

    assert renamed == [
        (
            "binary_sensor.smoke_alarm_none",
            {"new_entity_id": "binary_sensor.smoke_alarm_connected"},
        ),
        ("button.smoke_alarm_none", {"new_entity_id": "button.smoke_alarm_test"}),
    ]


def test_legacy_none_entity_id_migration_applies_to_other_xsense_devices(monkeypatch):
    renamed = []
    entries = [
        SimpleNamespace(
            domain="binary_sensor",
            platform="xsense",
            entity_id="binary_sensor.water_leak_sensor_none",
            unique_id="leak-device-connected",
            device_id="leak-device-id",
            object_id_base="Connected",
            original_name="Connected",
            translation_key="connected",
        ),
        SimpleNamespace(
            domain="button",
            platform="xsense",
            entity_id="button.base_station_none",
            unique_id="base-device-test",
            device_id="base-device-id",
            object_id_base="Test",
            original_name="Test",
            translation_key="test",
        ),
    ]

    class FakeEntityRegistry:
        entities = {}

        def async_get(self, entity_id):
            return None

        def async_update_entity(self, entity_id, **kwargs):
            renamed.append((entity_id, kwargs))

    class FakeDeviceRegistry:
        def async_get(self, device_id):
            devices = {
                "leak-device-id": SimpleNamespace(
                    name_by_user=None, name="Water Leak Sensor"
                ),
                "base-device-id": SimpleNamespace(
                    name_by_user=None, name="Base Station"
                ),
            }
            return devices[device_id]

    import custom_components.xsense as xsense

    monkeypatch.setattr(xsense.er, "async_get", lambda hass: FakeEntityRegistry())
    monkeypatch.setattr(xsense.dr, "async_get", lambda hass: FakeDeviceRegistry())
    monkeypatch.setattr(
        xsense.er,
        "async_entries_for_config_entry",
        lambda entity_registry, entry_id: entries,
    )

    _migrate_legacy_none_entity_ids(
        SimpleNamespace(), SimpleNamespace(entry_id="entry-id")
    )

    assert renamed == [
        (
            "binary_sensor.water_leak_sensor_none",
            {"new_entity_id": "binary_sensor.water_leak_sensor_connected"},
        ),
        ("button.base_station_none", {"new_entity_id": "button.base_station_test"}),
    ]


def test_legacy_none_entity_id_migration_uses_entity_id_base_without_device(monkeypatch):
    renamed = []
    entries = [
        SimpleNamespace(
            domain="button",
            platform="xsense",
            entity_id="button.smoke_alarm_none",
            unique_id="device-test",
            device_id=None,
            object_id_base="Test",
            original_name=None,
            translation_key="test",
        )
    ]

    class FakeEntityRegistry:
        entities = {}

        def async_get(self, entity_id):
            return None

        def async_update_entity(self, entity_id, **kwargs):
            renamed.append((entity_id, kwargs))

    class FakeDeviceRegistry:
        def async_get(self, device_id):
            return None

    import custom_components.xsense as xsense

    monkeypatch.setattr(xsense.er, "async_get", lambda hass: FakeEntityRegistry())
    monkeypatch.setattr(xsense.dr, "async_get", lambda hass: FakeDeviceRegistry())
    monkeypatch.setattr(
        xsense.er,
        "async_entries_for_config_entry",
        lambda entity_registry, entry_id: entries,
    )

    _migrate_legacy_none_entity_ids(
        SimpleNamespace(), SimpleNamespace(entry_id="entry-id")
    )

    assert renamed == [
        ("button.smoke_alarm_none", {"new_entity_id": "button.smoke_alarm_test"})
    ]


def test_legacy_none_entity_id_migration_skips_existing_target(monkeypatch):
    renamed = []
    entries = [
        SimpleNamespace(
            domain="button",
            platform="xsense",
            entity_id="button.smoke_alarm_none",
            unique_id="device-test",
            device_id="device-id",
            object_id_base="Test",
            original_name=None,
            translation_key="test",
        )
    ]

    class FakeEntityRegistry:
        def async_get(self, entity_id):
            assert entity_id == "button.smoke_alarm_test"
            return SimpleNamespace(entity_id="button.smoke_alarm_test")

        def async_update_entity(self, entity_id, **kwargs):
            renamed.append((entity_id, kwargs))

    class FakeDeviceRegistry:
        def async_get(self, device_id):
            return SimpleNamespace(name_by_user=None, name="Smoke Alarm")

    import custom_components.xsense as xsense

    monkeypatch.setattr(xsense.er, "async_get", lambda hass: FakeEntityRegistry())
    monkeypatch.setattr(xsense.dr, "async_get", lambda hass: FakeDeviceRegistry())
    monkeypatch.setattr(
        xsense.er,
        "async_entries_for_config_entry",
        lambda entity_registry, entry_id: entries,
    )

    _migrate_legacy_none_entity_ids(
        SimpleNamespace(), SimpleNamespace(entry_id="entry-id")
    )

    assert renamed == []
