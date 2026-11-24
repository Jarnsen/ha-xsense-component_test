"""Prevent cloud access from leaking back into opted-in SBS50 detectors."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from test_audit_repairs import make_coordinator

from custom_components.xsense import (
    _async_setup_entry_runtime,
    async_remove_config_entry_device,
)
from custom_components.xsense.binary_sensor import (
    async_setup_entry as setup_binary_sensors,
)
from custom_components.xsense.config_flow import XSenseOptionsFlow
from custom_components.xsense.coordinator import _mqtt_child_write_scope
from custom_components.xsense.entity import (
    XSenseEntity,
    _entity_by_id_or_serial,
    _serial_identity,
    _stable_device_id,
)
from custom_components.xsense.identity_store import validate_current_identities
from custom_components.xsense.local_transport import (
    CONF_LOCAL_MQTT_ONLY,
    local_device_key,
    local_device_record,
    restore_local_devices,
)
from custom_components.xsense.python_xsense.async_xsense import AsyncXSense
from custom_components.xsense.python_xsense.house import House


def make_house(*, local_only=False):
    house = House(None, "house-one", "House", "EU", "eu-central-1", "cloud.example")
    if local_only:
        house.cloud_excluded_children = {"163988c7": {"00000001": "cloud-selected"}}
    house.set_stations({"stations": [{
        "stationId": "cloud-station", "stationSn": "163988C7",
        "stationName": "Hall", "category": "SBS50",
        "devices": [
            {"deviceId": "cloud-selected", "deviceSn": "00000001", "deviceType": "XS0B-MR",
             "deviceName": "Smoke"},
            {"deviceId": "cloud-sibling", "deviceSn": "00000002", "deviceType": "XS01-M",
             "deviceName": "Other"},
        ],
    }]})
    return house, house.stations["cloud-station"]


def test_mixed_shadow_can_scope_writes_to_the_nonlocal_child():
    _, station = make_house(local_only=True)
    sibling = station.devices["cloud-sibling"]
    assert _mqtt_child_write_scope(station, {"stationSN": station.sn, "wifiRSSI": -60, "devs": {
        "00000001": {"alarmStatus": 0}, "00000002": {"alarmStatus": 1},
    }}) == frozenset({_serial_identity(sibling)})
    assert _mqtt_child_write_scope(station, {"devs": {"deadbeef": {"alarmStatus": 1}}}) is None


async def test_incomplete_cloud_inventory_cannot_authorize_registry_removal():
    entry = SimpleNamespace(entry_id="test")
    coordinator = SimpleNamespace(_local_only_devices={"saved": object()}, _startup_refresh_complete=False,
                                  last_update_success=False, data={"stations": {}, "devices": {}})
    hass = SimpleNamespace(data={"xsense": {entry.entry_id: coordinator}})
    device = SimpleNamespace(identifiers={("xsense", "cloud-station")})
    assert not await async_remove_config_entry_device(hass, entry, device)
    coordinator._startup_refresh_complete = True
    assert not await async_remove_config_entry_device(hass, entry, device)
    coordinator.last_update_success = True
    assert await async_remove_config_entry_device(hass, entry, device)


async def test_reused_cloud_id_keeps_both_detectors_and_separate_registry_ids():
    _, before = make_house()
    opted = before.devices["cloud-selected"]
    cached = restore_local_devices({CONF_LOCAL_MQTT_ONLY: {
        local_device_key(opted): local_device_record(opted),
    }})
    _, station = make_house(local_only=True)
    sibling = station.devices.pop("cloud-sibling")
    sibling.entity_id = opted.entity_id
    station.devices[sibling.entity_id] = sibling
    coordinator = make_coordinator(station)
    coordinator._local_only_devices = cached
    coordinator._initialized = True
    coordinator._camera_initialized = False
    coordinator._camera_station_cache = {}
    coordinator._xsense_stable_device_ids = {_serial_identity(opted): opted.entity_id}
    coordinator.data = await coordinator.get_devices(
        include_camera_history=False, include_camera_update=False, include_state_update=False,
    )
    devices = coordinator.data["devices"]
    assert devices[opted.entity_id] is sibling
    assert _entity_by_id_or_serial(devices, opted.entity_id, opted.sn, _serial_identity(opted)) is cached[opted.entity_id]
    assert _stable_device_id(coordinator, cached[opted.entity_id], _serial_identity(opted)) == opted.entity_id
    assert _stable_device_id(coordinator, sibling, _serial_identity(sibling)) != opted.entity_id
    validate_current_identities(coordinator)
    both_local = restore_local_devices({CONF_LOCAL_MQTT_ONLY: {
        local_device_key(device): local_device_record(device) for device in (opted, sibling)
    }})
    assert {_serial_identity(device) for device in both_local.values()} == {
        _serial_identity(opted), _serial_identity(sibling),
    }
    coordinator._local_only_devices = both_local
    coordinator.data["devices"] = both_local
    validate_current_identities(coordinator)
    coordinator.data["devices"] = devices
    coordinator._local_only_devices.clear()
    validate_current_identities(coordinator)


async def test_one_checkbox_round_trips_without_changing_sibling_or_recording_options():
    _, station = make_house()
    device = station.devices["cloud-selected"]
    key = local_device_key(device)
    entry = SimpleNamespace(entry_id="test", options={"recordings-test-option": 123})
    coordinator = SimpleNamespace(data={"stations": {"station": station}, "devices": station.devices})
    flow = XSenseOptionsFlow(entry)
    flow.hass = SimpleNamespace(data={"xsense": {"test": coordinator}})
    form = await flow.async_step_local_mqtt_device({"device": key})
    assert form["data_schema"]({}) == {"local_only": False}
    result = await flow.async_step_local_mqtt_transport({"local_only": True})
    options = result["data"]
    assert list(options[CONF_LOCAL_MQTT_ONLY]) == [key]
    assert options["recordings-test-option"] == 123
    restored = restore_local_devices(options)["cloud-selected"]
    assert restored.local_mqtt_only
    assert _serial_identity(restored) == _serial_identity(device)
    assert restored.data == {}
    entry.options = options
    form = await flow.async_step_local_mqtt_device({"device": key})
    assert form["data_schema"]({}) == {"local_only": True}
    result = await flow.async_step_local_mqtt_transport({"local_only": False})
    assert result["data"] == {"recordings-test-option": 123, CONF_LOCAL_MQTT_ONLY: {}}


async def test_cloud_inventory_and_shadow_updates_exclude_only_the_selected_detector():
    _, original = make_house()
    opted = original.devices["cloud-selected"]
    saved = {CONF_LOCAL_MQTT_ONLY: {local_device_key(opted): local_device_record(opted)}}
    restored = restore_local_devices(saved)
    _, station = make_house(local_only=True)
    sibling = station.devices["cloud-sibling"]
    assert station.get_device_by_sn(opted.sn) is None
    assert station.get_device_by_identifier(opted.entity_id) is None

    coordinator = make_coordinator(station)
    coordinator._local_only_devices = restored
    coordinator.xsense.load_all = AsyncMock()
    coordinator._initialized = False
    coordinator._camera_initialized = False
    coordinator._camera_station_cache = {}
    cloud = await coordinator.get_devices(
        include_camera_history=False, include_camera_update=False, include_state_update=False,
    )
    assert cloud["devices"] == {"cloud-selected": restored["cloud-selected"], "cloud-sibling": sibling}
    coordinator.data = cloud
    coordinator._async_notify_mqtt_station = Mock()
    topic = f"$aws/things/{station.shadow_name}/shadow/name/2nd_mainpage/update"
    coordinator.async_event_received(topic, json.dumps({"state": {"reported": {
        "stationSN": station.sn, "deviceSN": opted.sn, "alarmStatus": "1",
    }}}).encode())
    coordinator._async_notify_mqtt_station.assert_not_called()
    assert "alarmStatus" not in station.data
    coordinator.async_event_received(
        f"$aws/things/{station.shadow_name}/shadow/name/2nd_info_{opted.sn}/update",
        b'{"state":{"reported":{"batInfo":2}}}',
    )
    coordinator._async_notify_mqtt_station.assert_not_called()
    assert "batInfo" not in station.data

    coordinator.async_event_received(topic, json.dumps({"state": {"reported": {
        "stationSN": station.sn,
        "devs": {opted.sn: {"alarmStatus": "1"}, sibling.sn: {"alarmStatus": "1"}},
        opted.entity_id: {"alarmStatus": "1"},
    }}}).encode())
    assert sibling.data["alarmStatus"] is True
    assert opted.entity_id not in station.data
    assert restored["cloud-selected"].data == {}
    coordinator._async_notify_mqtt_station.assert_called_once()

    # Existing cloud control entities cannot resolve the cached detector.
    control = object.__new__(XSenseEntity)
    control.coordinator = coordinator
    control._station_id = station.entity_id
    control._dev_id = opted.entity_id
    control._entity_serial = opted.sn
    control._physical_identity = _serial_identity(opted)
    control._camera_identity = None
    assert control._current_entity() is None

    client = AsyncXSense()
    client.get_thing = AsyncMock(return_value={"state": {"reported": {"batInfo": 2}}})
    client._lastres = SimpleNamespace(status=200)
    await client._get_sbs50_child_info_state(station)
    assert [call.args[1] for call in client.get_thing.await_args_list] == ["2nd_info_00000002"]


@pytest.mark.asyncio
async def test_local_platforms_load_before_first_cloud_refresh(monkeypatch):
    import custom_components.xsense as integration

    _, original = make_house()
    device = original.devices["cloud-selected"]
    restored = restore_local_devices({
        CONF_LOCAL_MQTT_ONLY: {local_device_key(device): local_device_record(device)},
    })
    coordinator = SimpleNamespace(
        _local_only_devices=restored, async_config_entry_first_refresh=AsyncMock(),
        async_refresh=AsyncMock(), async_start_camera_ai_history_polling=Mock(),
        async_schedule_deferred_refresh=Mock(),
    )
    entry = SimpleNamespace(entry_id="local-entry", async_on_unload=Mock(), add_update_listener=Mock())
    hass = SimpleNamespace(data={}, config_entries=SimpleNamespace())
    calls = []
    async def setup_platforms(*_args):
        assert coordinator.data == {"stations": {}, "devices": restored}
        assert coordinator.last_update_success is False
        calls.append("local platforms")
    def start_cloud(_hass, coroutine, _name):
        calls.append("background cloud")
        coroutine.close()
    hass.config_entries.async_forward_entry_setups = setup_platforms
    monkeypatch.setattr(integration, "async_load_identity_store", AsyncMock())
    monkeypatch.setattr(integration, "_cleanup_recordings_runtime", Mock())
    monkeypatch.setattr(integration, "_schedule_startup_maintenance", Mock())
    monkeypatch.setattr(integration, "async_track_time_interval", Mock())
    entry.async_create_background_task = start_cloud
    assert await _async_setup_entry_runtime(hass, entry, coordinator)
    assert calls == ["local platforms", "background cloud"]
    coordinator.async_config_entry_first_refresh.assert_not_called()
    entities = []
    await setup_binary_sensors(hass, entry, entities.extend)
    assert {entity.entity_description.key for entity in entities} == {"alarm_status", "is_life_end"}
    assert all(not entity.available and entity.is_on is None for entity in entities)
