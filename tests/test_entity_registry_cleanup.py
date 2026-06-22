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
    OBSOLETE_ACTION_KEYS_BY_DEVICE_TYPE,
    OBSOLETE_BINARY_SENSOR_KEYS,
    OBSOLETE_NUMBER_KEYS,
    OBSOLETE_SELECT_KEYS,
    OBSOLETE_SENSOR_KEYS,
    OBSOLETE_SWITCH_KEYS,
    _is_obsolete_binary_sensor_entry,
    _is_obsolete_sensor_entry,
    _migrate_legacy_none_entity_ids,
    _obsolete_action_unique_ids,
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


def test_obsolete_action_unique_ids_target_removed_model_actions_only():
    xs03_iwx = SimpleNamespace(entity_id="hall_smoke", type="XS03-iWX")
    xs01_wx = SimpleNamespace(entity_id="kitchen_smoke", type="XS01-WX")

    unique_ids = _obsolete_action_unique_ids(
        {"stations": {}, "devices": {"hall": xs03_iwx, "kitchen": xs01_wx}}
    )

    assert OBSOLETE_ACTION_KEYS_BY_DEVICE_TYPE["XS03-iWX"] == ("mute",)
    assert unique_ids == {"hall-smoke-mute"}


def test_software_version_is_device_info_not_sensor():
    from custom_components.xsense.sensor import SENSORS

    sensor_keys = {description.key for description in SENSORS}

    assert "sw_version" not in sensor_keys
    assert "sbs50_sw" not in sensor_keys


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


def test_obsolete_binary_sensor_entry_detection_is_scoped_to_xsense_led_binary_sensor():
    assert _is_obsolete_binary_sensor_entry(
        SimpleNamespace(
            entity_id='binary_sensor.old_device_led_light',
            platform='xsense',
            unique_id='old-device-led-light',
        )
    )
    assert not _is_obsolete_binary_sensor_entry(
        SimpleNamespace(
            domain='sensor',
            platform='xsense',
            unique_id='old-device-led-light',
        )
    )
    assert not _is_obsolete_binary_sensor_entry(
        SimpleNamespace(
            domain='binary_sensor',
            platform='other',
            unique_id='old-device-led-light',
        )
    )
    assert not _is_obsolete_binary_sensor_entry(
        SimpleNamespace(
            domain='binary_sensor',
            platform='xsense',
            unique_id='old-device-connected',
        )
    )


def test_obsolete_binary_sensor_keys_only_remove_removed_binary_sensors():
    assert OBSOLETE_BINARY_SENSOR_KEYS == (
        'led_light',
        'motion_required',
        'video_recording_enabled',
        'night_vision_enabled',
        'recording_light_enabled',
        'camera_alarm_enabled',
        'camera_mirror_flip',
        'camera_antiflicker',
        'camera_live_audio',
        'camera_voice_volume',
        'camera_cooldown_enabled',
        "camera_awake",
        "camera_webrtc_supported",
        "person_detected",
        "pet_detected",
        "vehicle_detected",
        "package_detected",
        "other_detected",
        "vehicle_enter_detected",
        "vehicle_out_detected",
        "vehicle_held_up_detected",
        "package_drop_off_detected",
        "package_pick_up_detected",
        "package_exist_detected",
        "alarm_enabled",
        "continued_alarm",
        "on",
        "await_enabled",
        "pir_enabled",
        "sunshine_enabled",
        "key_sound_enabled",
        "warning_enabled",
        "chirp_tone_enabled",
        "reminder_enabled",
        "reminder_tone_enabled",
    )


def test_camera_setup_controls_are_not_obsolete_registry_entries():
    assert OBSOLETE_SWITCH_KEYS == ()
    assert OBSOLETE_SELECT_KEYS == ()
    assert OBSOLETE_NUMBER_KEYS == ()


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
            domain='sensor',
            platform='xsense',
            unique_id='missing-device-serial-number',
            entity_id='sensor.missing_device_serial_number',
        ),
        SimpleNamespace(
            domain='sensor',
            platform='xsense',
            unique_id='station-1-ip',
            entity_id='sensor.station_1_ip',
        ),
        SimpleNamespace(
            domain='binary_sensor',
            platform='xsense',
            unique_id='kitchen-smoke-alarm-led-light',
            entity_id='binary_sensor.kitchen_smoke_alarm_led_light',
        ),
        SimpleNamespace(
            domain='binary_sensor',
            platform='xsense',
            unique_id='garden-camera-moved',
            entity_id='binary_sensor.garden_camera_motion',
        ),
        SimpleNamespace(
            domain='binary_sensor',
            platform='xsense',
            unique_id='hall-motion-moved',
            entity_id='binary_sensor.hall_motion_motion',
        ),
        SimpleNamespace(
            domain='switch',
            platform='xsense',
            unique_id='camera-1-camera-motion-detection',
            entity_id='switch.camera_1_camera_motion_detection',
        ),
        SimpleNamespace(
            domain='select',
            platform='xsense',
            unique_id='camera-1-camera-default-codec',
            entity_id='select.camera_1_camera_default_codec',
        ),
        SimpleNamespace(
            domain='number',
            platform='xsense',
            unique_id='camera-1-camera-live-speaker-volume',
            entity_id='number.camera_1_camera_live_speaker_volume',
        ),
        SimpleNamespace(
            domain='binary_sensor',
            platform='xsense',
            unique_id='kitchen-smoke-alarm-connected',
            entity_id='binary_sensor.kitchen_smoke_alarm_connected',
        ),
        SimpleNamespace(
            domain='button',
            platform='xsense',
            unique_id='hall-smoke-mute',
            entity_id='button.hall_smoke_mute',
        ),
        SimpleNamespace(
            domain='button',
            platform='xsense',
            unique_id='kitchen-smoke-mute',
            entity_id='button.kitchen_smoke_mute',
        ),
    ]

    import custom_components.xsense as xsense

    monkeypatch.setattr(xsense.er, 'async_get', lambda hass: registry)
    monkeypatch.setattr(
        xsense.er,
        'async_entries_for_config_entry',
        lambda entity_registry, entry_id: entries,
    )

    _remove_obsolete_sensor_entities(
        SimpleNamespace(),
        {
            'stations': {
                'station_1': SimpleNamespace(entity_id='station_1')
            },
            'devices': {
                'camera': SimpleNamespace(entity_id='garden_camera', type='SSC0A'),
                'motion': SimpleNamespace(entity_id='hall_motion', type='SMS'),
                'hall': SimpleNamespace(entity_id='hall_smoke', type='XS03-iWX'),
                'kitchen': SimpleNamespace(entity_id='kitchen_smoke', type='XS01-WX'),
            },
        },
        SimpleNamespace(entry_id='entry-id'),
    )

    assert removed == [
        'sensor.missing_device_serial_number',
        'binary_sensor.kitchen_smoke_alarm_led_light',
        'button.hall_smoke_mute',
    ]



def test_obsolete_sensor_cleanup_keeps_current_device_entities(monkeypatch):
    removed = []

    class FakeEntityRegistry:
        def async_get_entity_id(self, platform, domain, unique_id):
            return None

        def async_remove(self, entity_id):
            removed.append(entity_id)

    current_sensor_unique_ids = [
        'xs01-wx-alarm-status',
        'xs01-wx-battery',
        'xs01-wx-ip-address',
        'xs01-wx-last-self-test',
        'xs01-wx-last-self-test-time',
        'xs01-wx-mute-status',
        'xs01-wx-report-time',
        'xs01-wx-signal-strength',
        'xs01-wx-ssid',
    ]
    entries = [
        SimpleNamespace(
            domain='sensor',
            platform='xsense',
            unique_id=unique_id,
            entity_id='sensor.' + unique_id.replace('-', '_'),
        )
        for unique_id in current_sensor_unique_ids
    ]
    entries.extend(
        [
            SimpleNamespace(
                domain='binary_sensor',
                platform='xsense',
                unique_id='xs01-wx-connected',
                entity_id='binary_sensor.xs01_wx_connected',
            ),
            SimpleNamespace(
                domain='sensor',
                platform='xsense',
                unique_id='xs01-wx-online-time',
                entity_id='sensor.xs01_wx_online_time',
            ),
            SimpleNamespace(
                domain='sensor',
                platform='xsense',
                unique_id='xs01-wx-serial-number',
                entity_id='sensor.xs01_wx_serial_number',
            ),
            SimpleNamespace(
                domain='sensor',
                platform='xsense',
                unique_id='xs01-wx-software-version',
                entity_id='sensor.xs01_wx_software_version',
            ),
            SimpleNamespace(
                domain='sensor',
                platform='xsense',
                unique_id='xs01-wx-sw-version',
                entity_id='sensor.xs01_wx_sw_version',
            ),
            SimpleNamespace(
                domain='sensor',
                platform='xsense',
                unique_id='xs01-wx-alarm-vol',
                entity_id='sensor.xs01_wx_alarm_vol',
            ),
            SimpleNamespace(
                domain='sensor',
                platform='xsense',
                unique_id='xs01-wx-voice-vol',
                entity_id='sensor.xs01_wx_voice_vol',
            ),
            SimpleNamespace(
                domain='sensor',
                platform='xsense',
                unique_id='xs01-wx-chirp-vol',
                entity_id='sensor.xs01_wx_chirp_vol',
            ),
            SimpleNamespace(
                domain='sensor',
                platform='xsense',
                unique_id='xs01-wx-reminder-vol',
                entity_id='sensor.xs01_wx_reminder_vol',
            ),
            SimpleNamespace(
                domain='binary_sensor',
                platform='xsense',
                unique_id='xs01-wx-led-light',
                entity_id='binary_sensor.xs01_wx_led_light',
            ),
        ]
    )

    import custom_components.xsense as xsense

    monkeypatch.setattr(xsense.er, 'async_get', lambda hass: FakeEntityRegistry())
    monkeypatch.setattr(
        xsense.er,
        'async_entries_for_config_entry',
        lambda entity_registry, entry_id: entries,
    )

    _remove_obsolete_sensor_entities(
        SimpleNamespace(),
        {'stations': {}, 'devices': {'xs01_wx': SimpleNamespace(entity_id='xs01_wx')}},
        SimpleNamespace(entry_id='entry-id'),
    )

    assert removed == [
        'sensor.xs01_wx_online_time',
        'sensor.xs01_wx_serial_number',
        'sensor.xs01_wx_software_version',
        'sensor.xs01_wx_sw_version',
        'sensor.xs01_wx_alarm_vol',
        'sensor.xs01_wx_voice_vol',
        'sensor.xs01_wx_chirp_vol',
        'sensor.xs01_wx_reminder_vol',
        'binary_sensor.xs01_wx_led_light',
    ]



def test_obsolete_sensor_cleanup_scans_all_xsense_sensor_entries(monkeypatch):
    removed = []

    class FakeEntityRegistry:
        entities = {
            'sensor.orphan_serial_number': SimpleNamespace(
                domain='sensor',
                platform='xsense',
                unique_id='orphan-serial-number',
                entity_id='sensor.orphan_serial_number',
            ),
            'sensor.orphan_ip': SimpleNamespace(
                domain='sensor',
                platform='xsense',
                unique_id='orphan-ip',
                entity_id='sensor.orphan_ip',
            ),
            'binary_sensor.orphan_led_light': SimpleNamespace(
                domain='binary_sensor',
                platform='xsense',
                unique_id='orphan-led-light',
                entity_id='binary_sensor.orphan_led_light',
            ),
            'binary_sensor.orphan_connected': SimpleNamespace(
                domain='binary_sensor',
                platform='xsense',
                unique_id='orphan-connected',
                entity_id='binary_sensor.orphan_connected',
            ),
        }

        def async_get_entity_id(self, platform, domain, unique_id):
            return None

        def async_remove(self, entity_id):
            removed.append(entity_id)

    import custom_components.xsense as xsense

    monkeypatch.setattr(xsense.er, 'async_get', lambda hass: FakeEntityRegistry())
    monkeypatch.setattr(
        xsense.er,
        'async_entries_for_config_entry',
        lambda entity_registry, entry_id: [],
    )

    _remove_obsolete_sensor_entities(
        SimpleNamespace(),
        {'stations': {}, 'devices': {}},
        SimpleNamespace(entry_id='entry-id'),
    )

    assert removed == ['sensor.orphan_serial_number', 'binary_sensor.orphan_led_light']



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


def test_camera_metadata_entities_are_obsolete_registry_entries():
    sensor_keys = {
        "camera_model",
        "camera_device_status",
        "camera_sleep_message",
        "camera_wake_time",
        "camera_stream_protocol",
        "camera_codec",
        "camera_time_zone",
        "last_motion_time",
    }
    binary_sensor_keys = {"camera_awake", "camera_webrtc_supported"}

    assert sensor_keys.issubset(set(OBSOLETE_SENSOR_KEYS))
    assert binary_sensor_keys.issubset(set(OBSOLETE_BINARY_SENSOR_KEYS))


def test_writable_config_values_are_not_exposed_as_read_only_entities():
    from custom_components.xsense.binary_sensor import SENSORS as BINARY_SENSORS
    from custom_components.xsense.sensor import SENSORS

    removed_sensor_keys = {
        "led_brightness",
        "await_brightness",
        "trigger_brightness",
        "temperature_min",
        "temperature_max",
        "humidity_min",
        "humidity_max",
        "temperature_unit",
        "temperature_adjustment",
        "humidity_adjustment",
        "temperature_comfort",
        "humidity_comfort",
        "temperature_range",
        "humidity_range",
        "comfort_type",
        "alarm_tone",
        "chirp_tone",
        "reminder_tone",
        "alarm_interval",
        "reminder_time",
        "detection_sensitivity",
        "sensitivity",
        "pir_time",
        "warning_period",
        "app_time",
        "light_scene",
    }
    removed_binary_keys = {
        "alarm_enabled",
        "continued_alarm",
        "on",
        "await_enabled",
        "pir_enabled",
        "sunshine_enabled",
        "key_sound_enabled",
        "warning_enabled",
        "chirp_tone_enabled",
        "reminder_enabled",
        "reminder_tone_enabled",
    }

    assert removed_sensor_keys.isdisjoint({description.key for description in SENSORS})
    assert removed_binary_keys.isdisjoint(
        {description.key for description in BINARY_SENSORS}
    )
    assert removed_sensor_keys.issubset(set(OBSOLETE_SENSOR_KEYS))
    assert removed_binary_keys.issubset(set(OBSOLETE_BINARY_SENSOR_KEYS))
