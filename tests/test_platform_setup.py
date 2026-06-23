from types import SimpleNamespace

import yaml
from yaml.loader import SafeLoader

from custom_components.xsense import (
    alarm_control_panel,
    binary_sensor,
    button,
    camera,
    event,
    number,
    select,
    sensor,
    switch,
)
from custom_components.xsense.const import DOMAIN


ENTITY_PLATFORMS = (
    binary_sensor,
    button,
    camera,
    event,
    number,
    select,
    sensor,
    switch,
)


class BlueprintLoader(SafeLoader):
    """YAML loader that tolerates Home Assistant blueprint tags."""


BlueprintLoader.add_constructor(
    "!input", lambda loader, node: loader.construct_scalar(node)
)


async def _setup_platform(module, coordinator):
    entry = SimpleNamespace(entry_id="entry-id")
    hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: coordinator}})
    calls = []

    def async_add_entities(entities):
        calls.append(list(entities))

    await module.async_setup_entry(hass, entry, async_add_entities)
    return calls


async def test_entity_platform_setup_handles_empty_coordinator_data():
    coordinator = SimpleNamespace(
        data=None,
        xsense=None,
        mqtt_servers={},
    )

    for module in ENTITY_PLATFORMS:
        assert await _setup_platform(module, coordinator) == [[]]


async def test_alarm_panel_setup_handles_missing_xsense_client():
    coordinator = SimpleNamespace(data=None, xsense=None)

    assert await _setup_platform(alarm_control_panel, coordinator) == []


async def test_select_setup_includes_standalone_camera_devices():
    device_camera = SimpleNamespace(
        data={"deviceLanguage": "en", "deviceSupportLanguage": ["en"], "isAdmin": True},
        entity_id="standalone-camera",
        name="Standalone Camera",
        online=True,
        type="SSC0A",
    )

    class Coordinator:
        data = {"stations": {}, "devices": {device_camera.entity_id: device_camera}}
        last_update_success = True
        xsense = None

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    calls = await _setup_platform(select, Coordinator())

    assert [entity._dev_id for entity in calls[0]] == [device_camera.entity_id]
    assert calls[0][0]._station_id == ""


async def test_camera_controls_do_not_duplicate_station_backed_camera_devices():
    camera_data = {
        "deviceLanguage": "en",
        "deviceSupportLanguage": ["en"],
        "isAdmin": True,
        "needMotion": 1,
        "alarmVol": 50,
        "supportAlarmVolume": True,
    }
    station_camera = SimpleNamespace(
        data=camera_data,
        entity_id="camera-id",
        name="Camera",
        online=True,
        type="SSC0A",
    )

    class Coordinator:
        data = {
            "stations": {station_camera.entity_id: station_camera},
            "devices": {station_camera.entity_id: station_camera},
        }
        last_update_success = True
        xsense = None

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    for module in (switch, select, number):
        calls = await _setup_platform(module, Coordinator())
        assert len(calls[0]) == len({entity.unique_id for entity in calls[0]})


def test_ai_notification_blueprint_selector_lists_xsense_event_entities():
    with open(
        "blueprints/automation/xsense/camera_ai_notification.yaml",
        encoding="utf-8",
    ) as file:
        blueprint = yaml.load(file, Loader=BlueprintLoader)

    entity_filter = blueprint["blueprint"]["input"]["ai_detection_event"]["selector"][
        "entity"
    ]["filter"][0]

    assert entity_filter == {"integration": "xsense", "domain": "event"}


def test_ai_notification_blueprint_filters_by_selected_event_entity():
    with open(
        "blueprints/automation/xsense/camera_ai_notification.yaml",
        encoding="utf-8",
    ) as file:
        blueprint = yaml.load(file, Loader=BlueprintLoader)

    trigger = blueprint["triggers"][0]

    assert "event_types" not in blueprint["blueprint"]["input"]
    assert trigger["trigger"] == "event.received"
    assert trigger["target"]["entity_id"] == "ai_detection_event"
    assert trigger["options"]["event_type"] == [
        "motion",
        "ai_detection",
        "person",
        "pet",
        "vehicle",
        "vehicle_enter",
        "vehicle_out",
        "vehicle_held_up",
        "package",
        "package_drop_off",
        "package_pick_up",
        "package_exist",
        "other",
    ]
    assert "AI activity" not in str(blueprint)


def test_ai_notification_blueprint_default_action_does_not_template_trigger():
    with open(
        "blueprints/automation/xsense/camera_ai_notification.yaml",
        encoding="utf-8",
    ) as file:
        blueprint = yaml.load(file, Loader=BlueprintLoader)

    default_actions = blueprint["blueprint"]["input"]["actions"]["default"]

    assert "trigger." not in str(default_actions)
