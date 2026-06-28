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


def test_ai_notification_blueprint_selects_mobile_app_device():
    with open(
        "blueprints/automation/xsense/camera_ai_notification.yaml",
        encoding="utf-8",
    ) as file:
        blueprint = yaml.load(file, Loader=BlueprintLoader)

    selector = blueprint["blueprint"]["input"]["notify_device"]["selector"]

    assert selector == {"device": {"integration": "mobile_app"}}


def test_ai_notification_blueprint_has_import_source_metadata():
    with open(
        "blueprints/automation/xsense/camera_ai_notification.yaml",
        encoding="utf-8",
    ) as file:
        blueprint = yaml.load(file, Loader=BlueprintLoader)

    source_url = blueprint["blueprint"]["source_url"]

    assert source_url == (
        "https://github.com/Jarnsen/ha-xsense-component_test/blob/main/"
        "blueprints/automation/xsense/camera_ai_notification.yaml"
    )


def test_ai_notification_blueprint_docs_use_github_file_import_url():
    with open("readme/README_en.md", encoding="utf-8") as file:
        readme = file.read()

    assert "raw.githubusercontent.com" not in readme
    assert (
        "blueprint_url=https%3A%2F%2Fgithub.com%2FJarnsen%2F"
        "ha-xsense-component_test%2Fblob%2Fmain%2Fblueprints%2F"
        "automation%2Fxsense%2Fcamera_ai_notification.yaml"
    ) in readme


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


def test_ai_notification_blueprint_does_not_expose_custom_camera_actions():
    with open(
        "blueprints/automation/xsense/camera_ai_notification.yaml",
        encoding="utf-8",
    ) as file:
        blueprint = yaml.load(file, Loader=BlueprintLoader)

    assert "actions" not in blueprint["blueprint"]["input"]
    assert "camera.play_stream" not in str(blueprint)
    assert "camera.record" not in str(blueprint)


def test_ai_notification_blueprint_exposes_safe_event_variables():
    with open(
        "blueprints/automation/xsense/camera_ai_notification.yaml",
        encoding="utf-8",
    ) as file:
        blueprint = yaml.load(file, Loader=BlueprintLoader)

    variables = blueprint["variables"]
    choose_action = blueprint["actions"][0]
    direct_url_action = choose_action["choose"][0]["sequence"][0]
    fallback_action = choose_action["default"][0]
    direct_message = direct_url_action["message"]
    fallback_message = fallback_action["message"]
    notification_data = direct_url_action["data"]

    assert variables["xsense_include_recording_link"] == "include_recording_link"
    assert variables["xsense_include_snapshot_link"] == "include_snapshot_link"
    assert "trigger.event.data" in variables["xsense_event_data"]
    assert "camera_name" in variables["xsense_camera_name"]
    assert "recording_url" in variables["xsense_recording_url"]
    assert "xsense_recording_target" not in variables
    assert "snapshot_url" in variables["xsense_snapshot_url"]
    assert "xsense_notification_url" not in variables
    assert "noAction" not in str(blueprint)
    assert "app://com.xsense.security" not in str(blueprint)
    assert direct_url_action["domain"] == "mobile_app"
    assert direct_url_action["type"] == "notify"
    assert direct_url_action["device_id"] == "notify_device"
    assert fallback_action["domain"] == "mobile_app"
    assert fallback_action["type"] == "notify"
    assert fallback_action["device_id"] == "notify_device"
    assert direct_url_action["title"] == "{{ xsense_camera_name }}"
    assert fallback_action["title"] == "{{ xsense_camera_name }}"
    assert len(blueprint["actions"]) == 1
    assert "actions" not in blueprint["blueprint"]["input"]
    assert "Home Assistant playback URL" in blueprint["blueprint"]["description"]
    assert "xsense_camera_name" in direct_message
    assert "xsense_camera_name" in fallback_message
    assert "xsense_recording_url" in direct_message
    assert "xsense_snapshot_url" in direct_message
    assert "xsense_recording_url" not in fallback_message
    assert "xsense_snapshot_url" in fallback_message
    assert "No playback URL" in fallback_message
    assert "trigger." not in direct_message
    assert "trigger." not in fallback_message
    assert notification_data["url"] == "{{ xsense_recording_url }}"
    assert notification_data["clickAction"] == "{{ xsense_recording_url }}"
    assert "data" not in fallback_action
    assert "actions" not in notification_data
    assert "trigger." not in str(choose_action)
