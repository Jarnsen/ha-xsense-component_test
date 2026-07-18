from types import SimpleNamespace
from pathlib import Path

import asyncio
import inspect
import json
import logging

import yaml
from jinja2 import Template
import pytest
from yaml.loader import SafeLoader

import custom_components.xsense as xsense_module
from custom_components.xsense import (
    alarm_control_panel,
    binary_sensor,
    button,
    camera,
    event,
    number,
    repairs,
    select,
    sensor,
    switch,
)
from custom_components.xsense.const import CONF_RECORDING_MEDIA_SYNC_ENABLED, DOMAIN


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


async def test_supported_smoke_status_loads_before_payload_keys():
    smoke = SimpleNamespace(
        data={},
        entity_id="kitchen-smoke",
        name="Smoke Alarm",
        online=True,
        shadow_name="XS0B-iR-station-sn",
        sn="station-sn",
        type="XS0B-iR",
    )

    class Coordinator:
        data = {"stations": {smoke.entity_id: smoke}, "devices": {}}
        last_update_success = True
        xsense = None

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    binary_calls = await _setup_platform(binary_sensor, Coordinator())

    assert any(entity.entity_description.key == "mute_status" for entity in binary_calls[0])


async def test_supported_co_status_loads_before_payload_keys():
    co_detector = SimpleNamespace(
        data={},
        entity_id="co-detector",
        name="CO Detector",
        online=True,
        shadow_name="XC04-WX-station-sn",
        sn="station-sn",
        type="XC04-WX",
    )

    class Coordinator:
        data = {"stations": {co_detector.entity_id: co_detector}, "devices": {}}
        last_update_success = True
        xsense = None

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    binary_calls = await _setup_platform(binary_sensor, Coordinator())
    sensor_calls = await _setup_platform(sensor, Coordinator())

    binary_keys = {entity.entity_description.key for entity in binary_calls[0]}
    sensor_keys = {entity.entity_description.key for entity in sensor_calls[0]}

    assert {"alarm_status", "is_life_end", "mute_status"} <= binary_keys
    assert {"co", "co_level"} <= sensor_keys


async def test_supported_combo_co_status_loads_before_payload_keys():
    combo_detector = SimpleNamespace(
        data={},
        entity_id="combo-detector",
        name="Smoke CO Detector",
        online=True,
        shadow_name="XP0A-MR-station-sn",
        sn="station-sn",
        type="XP0A-MR",
    )

    class Coordinator:
        data = {"stations": {}, "devices": {combo_detector.entity_id: combo_detector}}
        last_update_success = True
        xsense = None

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    sensor_calls = await _setup_platform(sensor, Coordinator())
    sensor_keys = {entity.entity_description.key for entity in sensor_calls[0]}

    assert {"co", "co_level"} <= sensor_keys


def test_supported_co_late_values_are_unknown_until_reported():
    co_detector = SimpleNamespace(data={}, type="XC04-WX")
    sensor_descriptions = {item.key: item for item in sensor.SENSORS}
    binary_descriptions = {item.key: item for item in binary_sensor.SENSORS}

    assert sensor_descriptions["co"].value_fn(co_detector) is None
    assert sensor_descriptions["co_level"].value_fn(co_detector) is None
    assert binary_descriptions["is_life_end"].value_fn(co_detector) is None
    assert binary_descriptions["mute_status"].value_fn(co_detector) is None


async def test_water_does_not_create_life_end_before_payload_key():
    water = SimpleNamespace(
        data={},
        entity_id="water",
        name="Water Sensor",
        online=True,
        shadow_name="SBS50station-sn",
        sn="water-sn",
        type="SWS51",
    )

    class Coordinator:
        data = {"stations": {}, "devices": {water.entity_id: water}}
        last_update_success = True
        xsense = None

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    binary_calls = await _setup_platform(binary_sensor, Coordinator())
    binary_keys = {entity.entity_description.key for entity in binary_calls[0]}

    assert "is_life_end" not in binary_keys
    assert "alarm_status" in binary_keys


async def test_sbs50_station_entities_load_before_late_shadow_keys():
    station = SimpleNamespace(
        data={},
        entity_id="base-station",
        name="Stacja bazowa",
        online=True,
        shadow_name="SBS5015A96B8A",
        sn="15A96B8A",
        type="SBS50",
    )

    class Coordinator:
        data = {"stations": {station.entity_id: station}, "devices": {}}
        last_update_success = True
        xsense = None

        def async_add_listener(self, *args, **kwargs):
            return lambda: None

    binary_calls = await _setup_platform(binary_sensor, Coordinator())
    sensor_calls = await _setup_platform(sensor, Coordinator())
    select_calls = await _setup_platform(select, Coordinator())

    assert any(
        entity.entity_description.key == "alarm_status" for entity in binary_calls[0]
    )
    sensor_keys = {entity.entity_description.key for entity in sensor_calls[0]}
    assert {"ip", "safe_mode", "wifi_rssi", "wifi_ssid", "zone_name"} <= sensor_keys
    assert {
        entity.entity_description.key for entity in select_calls[0]
    } >= {"alarm_tone", "led_brightness"}


def test_co_level_keeps_long_term_statistics_state_class():
    description = next(item for item in sensor.SENSORS if item.key == "co_level")

    assert description.state_class == sensor.SensorStateClass.MEASUREMENT


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


def test_packaged_ai_notification_blueprint_matches_import_blueprint():
    package_path = repairs._bundled_camera_blueprint_path()
    assert package_path.as_posix().endswith(
        "custom_components/xsense/blueprints/camera_ai_notification.yaml"
    )
    with open(
        "blueprints/automation/xsense/camera_ai_notification.yaml",
        encoding="utf-8",
    ) as file:
        import_blueprint = file.read()

    assert package_path.read_text(encoding="utf-8") == import_blueprint


def test_ai_notification_blueprint_docs_use_github_file_import_url():
    with open("readme/README_en.md", encoding="utf-8") as file:
        readme = file.read()

    assert "raw.githubusercontent.com" not in readme
    assert (
        "blueprint_url=https%3A%2F%2Fgithub.com%2FJarnsen%2F"
        "ha-xsense-component_test%2Fblob%2Fmain%2Fblueprints%2F"
        "automation%2Fxsense%2Fcamera_ai_notification.yaml"
    ) in readme


def test_blueprint_maintenance_interval_callback_stays_event_loop_safe():
    setup_source = inspect.getsource(xsense_module.async_setup_entry)
    maintenance_source = inspect.getsource(xsense_module._schedule_startup_maintenance)

    assert "@callback" in setup_source
    assert "def _schedule_blueprint_maintenance_check" in setup_source
    assert "hass.create_task(async_check_stale_camera_blueprints(hass))" in setup_source
    assert "hass.async_create_task(async_check_stale_camera_blueprints(hass))" not in setup_source
    assert "hass.create_task(_async_run_startup_maintenance" in maintenance_source
    assert "lambda _now: hass.async_create_task" not in maintenance_source
    assert "hass.async_create_task(_async_run_startup_maintenance" not in maintenance_source


def test_startup_maintenance_waits_until_home_assistant_started(monkeypatch):
    calls = []

    def async_call_later(hass, delay, callback):
        calls.append(("timer", delay, callback))
        return lambda: calls.append(("cancel_timer",))

    class Bus:
        def async_listen_once(self, event, callback):
            calls.append(("listen", event, callback))
            return lambda: calls.append(("cancel_listen",))

    class Hass:
        is_running = False
        bus = Bus()
        data = {DOMAIN: {"entry-id": object()}}

        def create_task(self, coro):
            calls.append(("task", coro.cr_code.co_name))
            coro.close()

    class Entry:
        entry_id = "entry-id"

        def async_on_unload(self, unsub):
            calls.append(("unload", unsub))

    monkeypatch.setattr(xsense_module, "async_call_later", async_call_later)

    coordinator = Hass.data[DOMAIN]["entry-id"]
    xsense_module._schedule_startup_maintenance(Hass(), Entry(), coordinator)

    assert calls[0][0:2] == ("listen", "homeassistant_started")
    calls[0][2](None)
    assert calls[1][0:2] == ("timer", xsense_module.STARTUP_MAINTENANCE_DELAY)
    assert calls[2][0] == "unload"
    calls[1][2](None)
    assert calls[3] == ("task", "_async_run_startup_maintenance")


def test_ai_notification_blueprint_filters_by_selected_event_entity():
    with open(
        "blueprints/automation/xsense/camera_ai_notification.yaml",
        encoding="utf-8",
    ) as file:
        blueprint = yaml.load(file, Loader=BlueprintLoader)

    trigger = blueprint["triggers"][0]

    assert "event_types" not in blueprint["blueprint"]["input"]
    assert trigger == {"trigger": "event", "event_type": "xsense_camera_event"}
    assert blueprint["actions"][0]["condition"] == "template"
    assert "xsense_event_entity_id == xsense_event_entity" in blueprint["actions"][0][
        "value_template"
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
    entity_guard = blueprint["actions"][0]
    choose_action = blueprint["actions"][1]
    notification_choice = choose_action["choose"][0]
    plain_notification_choice = choose_action["choose"][3]
    direct_url_action = notification_choice["sequence"][0]
    plain_notification_action = plain_notification_choice["sequence"][0]
    direct_message = direct_url_action["message"]
    notification_data = direct_url_action["data"]

    assert variables["xsense_event_entity"] == "ai_detection_event"
    assert variables["xsense_blueprint_version"] == 10
    assert variables["xsense_include_recording_link"] == "include_recording_link"
    assert variables["xsense_include_snapshot_link"] == "include_snapshot_link"
    assert "trigger.event.data" in variables["xsense_event_data"]
    assert "trigger.to_state" not in variables["xsense_event_data"]
    assert "trigger.event.data is mapping" in variables["xsense_has_trigger_data"]
    assert "xsense_event_data is mapping" in variables["xsense_event_type"]
    assert "state_attr(xsense_event_entity, 'event_type')" in variables["xsense_event_type"]
    assert "camera_name" in variables["xsense_camera_name"]
    assert "xsense_event_data is mapping" in variables["xsense_camera_name"]
    assert "state_attr(xsense_event_entity, 'camera_name')" in variables["xsense_camera_name"]
    assert "state_attr(xsense_event_entity, 'friendly_name')" in variables["xsense_camera_name"]
    assert "event_entity_id" in variables["xsense_event_entity_id"]
    assert "recording_url" in variables["xsense_recording_url"]
    assert "trigger.event.data is mapping" in variables["xsense_recording_url"]
    assert "state_attr(xsense_event_entity, 'recording_url')" in variables["xsense_recording_url"]
    assert "recording_media_url" in variables["xsense_recording_media_url"]
    assert "trigger.event.data is mapping" in variables["xsense_recording_media_url"]
    assert "state_attr(xsense_event_entity, 'recording_media_url')" in variables["xsense_recording_media_url"]
    assert "recording_cache_ready" in variables["xsense_recording_cache_ready"]
    assert "xsense_event_data is mapping" in variables["xsense_recording_cache_ready"]
    assert "xsense_recording_url[0:19] == '/xsense-recordings#'" in variables[
        "xsense_recording_tap_url"
    ]
    assert "/media/local" not in variables["xsense_recording_tap_url"]
    assert variables["xsense_notification_url"] == (
        "{{ xsense_recording_tap_url or '/xsense-recordings' }}"
    )
    assert "xsense_recording_target" not in variables
    assert "snapshot_url" in variables["xsense_snapshot_url"]
    assert "trigger.event.data is mapping" in variables["xsense_snapshot_url"]
    assert "state_attr(xsense_event_entity, 'snapshot_url')" in variables["xsense_snapshot_url"]
    assert "noAction" not in str(blueprint)
    assert "app://com.xsense.security" not in str(blueprint)
    assert direct_url_action["domain"] == "mobile_app"
    assert direct_url_action["type"] == "notify"
    assert direct_url_action["device_id"] == "notify_device"
    assert direct_url_action["title"] == "{{ xsense_camera_name }}"
    assert plain_notification_action["domain"] == "mobile_app"
    assert plain_notification_action["type"] == "notify"
    assert plain_notification_action["device_id"] == "notify_device"
    assert plain_notification_action["title"] == "{{ xsense_camera_name }}"
    assert "data" not in plain_notification_action
    assert len(blueprint["actions"]) == 2
    assert "xsense_event_entity_id" in entity_guard["value_template"]
    assert len(choose_action["choose"]) == 4
    assert "default" not in choose_action
    assert "actions" not in blueprint["blueprint"]["input"]
    assert "keeps mobile push delivery reliable" in blueprint["blueprint"]["description"]
    assert "recording_media_url" in blueprint["blueprint"]["description"]
    assert "xsense_camera_name" in direct_message
    assert "xsense_recording_url" not in direct_message
    assert "Recording ready" in direct_message
    assert "xsense_snapshot_url" not in direct_message
    assert "Snapshot:" not in str(blueprint)
    assert "No playback URL" not in str(blueprint)
    assert "trigger." not in direct_message
    assert notification_data["url"] == "{{ xsense_notification_url }}"
    assert notification_data["clickAction"] == "{{ xsense_notification_url }}"
    assert notification_data["image"] == "{{ xsense_snapshot_url }}"
    assert "video" not in notification_data
    assert "attachment" not in notification_data
    assert "xsense_include_recording_link" in str(notification_choice["conditions"])
    assert "xsense_recording_tap_url" in str(notification_choice["conditions"])
    assert "xsense_recording_cache_ready" in str(notification_choice["conditions"])
    assert "xsense_recording_media_url" not in str(notification_choice["conditions"])
    assert plain_notification_choice["conditions"] == [
        {
            "condition": "template",
            "value_template": "{{ not xsense_include_recording_link and (xsense_event_data.get('recording_cache_ready') if xsense_event_data is mapping else false) != true }}",
        }
    ]
    assert "actions" not in notification_data
    assert "trigger." not in str(choose_action)
    recording_without_snapshot = choose_action["choose"][1]["sequence"][0]
    plain_with_snapshot = choose_action["choose"][2]["sequence"][0]
    assert recording_without_snapshot["data"] == {
        "url": "{{ xsense_notification_url }}",
        "clickAction": "{{ xsense_notification_url }}",
    }
    assert plain_with_snapshot["data"] == {"image": "{{ xsense_snapshot_url }}"}


def test_ai_notification_tap_url_never_uses_raw_media_or_external_urls():
    with open(
        "blueprints/automation/xsense/camera_ai_notification.yaml",
        encoding="utf-8",
    ) as file:
        blueprint = yaml.load(file, Loader=BlueprintLoader)

    tap_template = Template(blueprint["variables"]["xsense_recording_tap_url"])
    notification_template = Template(blueprint["variables"]["xsense_notification_url"])

    def rendered_notification_url(recording_url):
        tap_url = tap_template.render(xsense_recording_url=recording_url)
        return notification_template.render(xsense_recording_tap_url=tap_url)

    assert rendered_notification_url(
        "/xsense-recordings#entry_id=entry-id&serial=CAMERA-SN&start=1&end=2"
    ) == "/xsense-recordings#entry_id=entry-id&serial=CAMERA-SN&start=1&end=2"
    assert rendered_notification_url("/xsense-recordings") == "/xsense-recordings"
    assert rendered_notification_url("/xsense-recordings-bad#entry_id=entry-id") == (
        "/xsense-recordings"
    )
    assert rendered_notification_url(
        "/media/local/xsense_recordings/videos/clip.mp4"
    ) == "/xsense-recordings"
    assert rendered_notification_url("https://example.invalid/clip.mp4") == (
        "/xsense-recordings"
    )
    assert rendered_notification_url("") == "/xsense-recordings"


def test_stale_camera_blueprint_detection(tmp_path):
    blueprint_dir = tmp_path / "blueprints" / "automation"
    xsense_dir = blueprint_dir / "xsense"
    xsense_dir.mkdir(parents=True)
    stale = xsense_dir / "old.yaml"
    stale.write_text(
        """
blueprint:
  name: X-Sense Camera Event
  source_url: https://github.com/Jarnsen/ha-xsense-component_test/blob/main/blueprints/automation/xsense/camera_ai_notification.yaml
variables:
  xsense_event_data: "{{ trigger.event.data }}"
  xsense_event_type: "{{ xsense_event_data.get('event_type') }}"
""",
        encoding="utf-8",
    )
    current = xsense_dir / "current.yaml"
    current.write_text(
        f"""
blueprint:
  name: X-Sense Camera Event
triggers:
  - trigger: event
    event_type: xsense_camera_event
variables:
  xsense_blueprint_version: {repairs.CAMERA_BLUEPRINT_VERSION}
  xsense_has_trigger_data: "{{{{ trigger is defined and trigger.event is defined and trigger.event.data is mapping }}}}"
  xsense_event_data: "{{{{ trigger.event.data }}}}"
  xsense_event_type: "{{{{ (xsense_event_data.get('event_type') if xsense_event_data is mapping else '') }}}}"
  xsense_recording_media_url: "{{{{ state_attr(xsense_event_entity, 'recording_media_url') }}}}"
  xsense_recording_cache_ready: "{{{{ (xsense_event_data.get('recording_cache_ready') if xsense_event_data is mapping else false) or false }}}}"
  xsense_recording_tap_url: "{{{{ xsense_recording_url if xsense_recording_url == '/xsense-recordings' or xsense_recording_url[0:19] == '/xsense-recordings#' else '' }}}}"
  xsense_notification_url: "{{{{ xsense_recording_tap_url or '/xsense-recordings' }}}}"
  xsense_snapshot_url: "{{{{ state_attr(xsense_event_entity, 'snapshot_url') }}}}"
actions:
  - choose:
      - conditions:
          - condition: template
            value_template: "{{{{ xsense_include_recording_link and xsense_recording_tap_url and xsense_recording_cache_ready }}}}"
        sequence:
          - data:
              image: "{{{{ xsense_snapshot_url }}}}"
      - conditions:
          - condition: template
            value_template: "{{{{ not xsense_include_recording_link and (xsense_event_data.get('recording_cache_ready') if xsense_event_data is mapping else false) != true }}}}"
""",
        encoding="utf-8",
    )
    safe_without_version = xsense_dir / "safe_without_version.yaml"
    safe_without_version.write_text(
        """
blueprint:
  name: X-Sense Camera Event
triggers:
  - trigger: event
    event_type: xsense_camera_event
variables:
  xsense_has_trigger_data: "{{ trigger is defined and trigger.event is defined and trigger.event.data is mapping }}"
  xsense_event_type: "{{ (xsense_event_data.get('event_type') if xsense_event_data is mapping else '') }}"
  xsense_recording_media_url: "{{ state_attr(xsense_event_entity, 'recording_media_url') }}"
  xsense_recording_cache_ready: "{{ (xsense_event_data.get('recording_cache_ready') if xsense_event_data is mapping else false) or false }}"
  xsense_recording_tap_url: "{{ xsense_recording_url if xsense_recording_url == '/xsense-recordings' or xsense_recording_url[0:19] == '/xsense-recordings#' else '' }}"
  xsense_notification_url: "{{ xsense_recording_tap_url or '/xsense-recordings' }}"
  xsense_snapshot_url: "{{ state_attr(xsense_event_entity, 'snapshot_url') }}"
actions:
  - choose:
      - conditions:
          - condition: template
            value_template: "{{ xsense_include_recording_link and xsense_recording_tap_url and xsense_recording_cache_ready }}"
        sequence:
          - data:
              image: "{{ xsense_snapshot_url }}"
      - conditions:
          - condition: template
            value_template: "{{ not xsense_include_recording_link and (xsense_event_data.get('recording_cache_ready') if xsense_event_data is mapping else false) != true }}"
""",
        encoding="utf-8",
    )
    stale_v7 = xsense_dir / "v7.yaml"
    stale_v7.write_text(
        """
blueprint:
  name: X-Sense Camera Event
triggers:
  - trigger: event
    event_type: xsense_camera_event
variables:
  xsense_blueprint_version: 7
  xsense_event_type: "{{ (xsense_event_data.get('event_type') if xsense_event_data is mapping else '') }}"
  xsense_recording_media_url: "{{ state_attr(xsense_event_entity, 'recording_media_url') }}"
  xsense_recording_tap_url: "{{ xsense_recording_url if xsense_recording_url == '/xsense-recordings' or xsense_recording_url[0:19] == '/xsense-recordings#' else '' }}"
  xsense_notification_url: "{{ xsense_recording_tap_url or '/xsense-recordings' }}"
actions:
  - choose:
      - conditions:
          - condition: template
            value_template: "{{ xsense_include_recording_link and xsense_recording_tap_url and xsense_recording_media_url }}"
      - conditions:
          - condition: template
            value_template: "{{ not xsense_include_recording_link }}"
""",
        encoding="utf-8",
    )
    stale_v8 = xsense_dir / "v8.yaml"
    stale_v8.write_text(
        """
blueprint:
  name: X-Sense Camera Event
triggers:
  - trigger: event
    event_type: xsense_camera_event
variables:
  xsense_blueprint_version: 8
  xsense_recording_media_url: "{{ state_attr(xsense_event_entity, 'recording_media_url') }}"
  xsense_recording_cache_ready: "{{ (xsense_event_data.get('recording_cache_ready') if xsense_event_data is mapping else false) or false }}"
  xsense_recording_tap_url: "{{ xsense_recording_url if xsense_recording_url == '/xsense-recordings' or xsense_recording_url[0:19] == '/xsense-recordings#' else '' }}"
  xsense_notification_url: "{{ xsense_recording_tap_url or '/xsense-recordings' }}"
actions:
  - choose:
      - conditions:
          - condition: template
            value_template: "{{ xsense_include_recording_link and xsense_recording_tap_url and xsense_recording_media_url }}"
""",
        encoding="utf-8",
    )
    stale_v9 = xsense_dir / "v9.yaml"
    stale_v9.write_text(
        """
blueprint:
  name: X-Sense Camera Event
triggers:
  - trigger: event
    event_type: xsense_camera_event
variables:
  xsense_blueprint_version: 9
  xsense_recording_media_url: "{{ state_attr(xsense_event_entity, 'recording_media_url') }}"
  xsense_recording_cache_ready: "{{ (xsense_event_data.get('recording_cache_ready') if xsense_event_data is mapping else false) or false }}"
  xsense_recording_tap_url: "{{ xsense_recording_url if xsense_recording_url == '/xsense-recordings' or xsense_recording_url[0:19] == '/xsense-recordings#' else '' }}"
  xsense_notification_url: "{{ xsense_recording_tap_url or '/xsense-recordings' }}"
message: >-
  Motion detected. Snapshot: {{ xsense_snapshot_url }}
""",
        encoding="utf-8",
    )
    stale_v6 = xsense_dir / "v6.yaml"
    stale_v6.write_text(
        """
blueprint:
  name: X-Sense Camera Event
triggers:
  - trigger: event
    event_type: xsense_camera_event
variables:
  xsense_blueprint_version: 6
  xsense_event_type: "{{ (xsense_event_data.get('event_type') if xsense_event_data is mapping else '') }}"
  xsense_recording_media_url: "{{ state_attr(xsense_event_entity, 'recording_media_url') }}"
  xsense_recording_tap_url: "{{ xsense_recording_url if xsense_recording_url == '/xsense-recordings' or xsense_recording_url[0:19] == '/xsense-recordings#' else '' }}"
  xsense_notification_url: "{{ xsense_recording_tap_url or '/xsense-recordings' }}"
actions:
  - choose:
      - conditions:
          - condition: template
            value_template: "{{ xsense_include_recording_link and xsense_recording_tap_url and xsense_recording_media_url }}"
""",
        encoding="utf-8",
    )
    stale_v5 = xsense_dir / "v5.yaml"
    stale_v5.write_text(
        """
blueprint:
  name: X-Sense Camera Event
triggers:
  - trigger: event
    event_type: xsense_camera_event
variables:
  xsense_blueprint_version: 5
  xsense_event_type: "{{ (xsense_event_data.get('event_type') if xsense_event_data is mapping else '') }}"
  xsense_recording_media_url: "{{ state_attr(xsense_event_entity, 'recording_media_url') }}"
  xsense_recording_tap_url: "{{ xsense_recording_url if xsense_recording_url == '/xsense-recordings' or xsense_recording_url[0:19] == '/xsense-recordings#' else '' }}"
  xsense_notification_url: "{{ xsense_recording_tap_url or '/xsense-recordings' }}"
message: Open X-Sense Recordings to view recent clips.
""",
        encoding="utf-8",
    )
    stale_v2 = xsense_dir / "v2.yaml"
    stale_v2.write_text(
        """
blueprint:
  name: X-Sense Camera Event
triggers:
  - trigger: event.received
variables:
  xsense_blueprint_version: 2
  xsense_event_type: "{{ (xsense_event_data.get('event_type') if xsense_event_data is mapping else '') }}"
  xsense_recording_media_url: "{{ state_attr(xsense_event_entity, 'recording_media_url') }}"
""",
        encoding="utf-8",
    )
    stale_v4 = xsense_dir / "v4.yaml"
    stale_v4.write_text(
        """
blueprint:
  name: X-Sense Camera Event
triggers:
  - trigger: event
    event_type: xsense_camera_event
variables:
  xsense_blueprint_version: 4
  xsense_recording_tap_url: "{{ xsense_recording_url if xsense_recording_url and xsense_recording_url[0:13] != '/media/local/' else xsense_recording_media_url or xsense_recording_url }}"
  xsense_notification_url: "{{ xsense_recording_tap_url or '/xsense-recordings' }}"
""",
        encoding="utf-8",
    )
    (blueprint_dir / "other.yaml").write_text(
        "blueprint:\n  name: Other Blueprint\n",
        encoding="utf-8",
    )

    assert repairs._stale_camera_blueprint_files(blueprint_dir) == [
        "xsense/old.yaml",
        "xsense/v2.yaml",
        "xsense/v4.yaml",
        "xsense/v5.yaml",
        "xsense/v6.yaml",
        "xsense/v7.yaml",
        "xsense/v8.yaml",
        "xsense/v9.yaml",
    ]


def test_stale_camera_blueprint_auto_updates_and_reloads_automations(
    tmp_path, monkeypatch
):
    blueprint_dir = tmp_path / "blueprints" / "automation"
    blueprint_dir.mkdir(parents=True)
    blueprint_path = blueprint_dir / "old.yaml"
    blueprint_path.write_text(
        """
blueprint:
  name: X-Sense Camera Event
variables:
  xsense_event_type: "{{ xsense_event_data.get('event_type') }}"
""",
        encoding="utf-8",
    )
    async def async_add_executor_job(func, *args):
        return func(*args)

    reload_calls = []

    class Services:
        def has_service(self, domain, service):
            return (domain, service) == ("automation", "reload")

        async def async_call(self, domain, service, **kwargs):
            reload_calls.append((domain, service, kwargs))

    hass = SimpleNamespace(
        config=SimpleNamespace(path=lambda *parts: str(tmp_path.joinpath(*parts))),
        async_add_executor_job=async_add_executor_job,
        services=Services(),
    )
    asyncio.run(repairs.async_check_stale_camera_blueprints(hass))

    updated_text = blueprint_path.read_text(encoding="utf-8")
    assert f"xsense_blueprint_version: {repairs.CAMERA_BLUEPRINT_VERSION}" in updated_text
    assert "xsense_recording_cache_ready" in updated_text
    assert reload_calls == [
        ("automation", "reload", {"blocking": False}),
    ]

    reload_calls.clear()

    asyncio.run(repairs.async_check_stale_camera_blueprints(hass))

    assert reload_calls == []


def test_camera_blueprint_remote_version_updates_current_import(tmp_path, monkeypatch):
    blueprint_dir = tmp_path / "blueprints" / "automation" / "xsense"
    blueprint_dir.mkdir(parents=True)
    blueprint_path = blueprint_dir / "camera_ai_notification.yaml"
    blueprint_path.write_text(
        """
blueprint:
  name: X-Sense Camera Event
triggers:
  - trigger: event
    event_type: xsense_camera_event
variables:
  xsense_blueprint_version: 10
  xsense_has_trigger_data: "{{ trigger is defined and trigger.event is defined and trigger.event.data is mapping }}"
  xsense_event_type: "{{ (xsense_event_data.get('event_type') if xsense_event_data is mapping else '') }}"
  xsense_recording_media_url: "{{ state_attr(xsense_event_entity, 'recording_media_url') }}"
  xsense_recording_cache_ready: "{{ (xsense_event_data.get('recording_cache_ready') if xsense_event_data is mapping else false) or false }}"
  xsense_recording_tap_url: "{{ xsense_recording_url if xsense_recording_url == '/xsense-recordings' or xsense_recording_url[0:19] == '/xsense-recordings#' else '' }}"
  xsense_notification_url: "{{ xsense_recording_tap_url or '/xsense-recordings' }}"
  xsense_snapshot_url: "{{ state_attr(xsense_event_entity, 'snapshot_url') }}"
actions:
  - choose:
      - conditions:
          - condition: template
            value_template: "{{ xsense_include_recording_link and xsense_recording_tap_url and xsense_recording_cache_ready }}"
        sequence:
          - data:
              image: "{{ xsense_snapshot_url }}"
      - conditions:
          - condition: template
            value_template: "{{ not xsense_include_recording_link and (xsense_event_data.get('recording_cache_ready') if xsense_event_data is mapping else false) != true }}"
""",
        encoding="utf-8",
    )
    remote_blueprint = (
        Path("blueprints/automation/xsense/camera_ai_notification.yaml")
        .read_text(encoding="utf-8")
        .replace("xsense_blueprint_version: 10", "xsense_blueprint_version: 11")
        + "\n# remote-only blueprint change\n"
    )

    async def async_add_executor_job(func, *args):
        return func(*args)

    reload_calls = []

    class Response:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def text(self):
            return remote_blueprint

    class Session:
        def get(self, *args, **kwargs):
            return Response()

    class Services:
        def has_service(self, domain, service):
            return (domain, service) == ("automation", "reload")

        async def async_call(self, domain, service, **kwargs):
            reload_calls.append((domain, service, kwargs))

    hass = SimpleNamespace(
        config=SimpleNamespace(path=lambda *parts: str(tmp_path.joinpath(*parts))),
        async_add_executor_job=async_add_executor_job,
        data={},
        services=Services(),
    )
    monkeypatch.setattr(repairs, "async_get_clientsession", lambda hass: Session())

    asyncio.run(repairs.async_check_stale_camera_blueprints(hass))

    updated_text = blueprint_path.read_text(encoding="utf-8")
    assert "xsense_blueprint_version: 11" in updated_text
    assert "# remote-only blueprint change" in updated_text
    assert reload_calls == [("automation", "reload", {"blocking": False})]


def test_stale_camera_blueprint_update_failure_is_logged_only(tmp_path, monkeypatch):
    blueprint_dir = tmp_path / "blueprints" / "automation"
    blueprint_dir.mkdir(parents=True)
    (blueprint_dir / "old.yaml").write_text(
        """
blueprint:
  name: X-Sense Camera Event
variables:
  xsense_event_type: "{{ xsense_event_data.get('event_type') }}"
""",
        encoding="utf-8",
    )
    missing_blueprint = tmp_path / "missing.yaml"

    async def async_add_executor_job(func, *args):
        return func(*args)

    hass = SimpleNamespace(
        config=SimpleNamespace(path=lambda *parts: str(tmp_path.joinpath(*parts))),
        async_add_executor_job=async_add_executor_job,
    )
    monkeypatch.setattr(repairs, "_bundled_camera_blueprint_path", lambda: missing_blueprint)
    asyncio.run(repairs.async_check_stale_camera_blueprints(hass))

    assert "xsense_blueprint_version" not in (blueprint_dir / "old.yaml").read_text(
        encoding="utf-8"
    )


def test_recordings_panel_registration_adds_sidebar_panel(monkeypatch):
    from custom_components.xsense import frontend

    static_paths = []
    panels = []

    class Http:
        async def async_register_static_paths(self, paths):
            static_paths.extend(paths)

    async def register_panel(**kwargs):
        panels.append(kwargs)

    monkeypatch.setattr(frontend.panel_custom, "async_register_panel", register_panel)
    hass = SimpleNamespace(data={}, http=Http())

    import asyncio

    asyncio.run(frontend.async_register_recordings_panel(hass))
    asyncio.run(frontend.async_register_recordings_panel(hass))

    assert len(static_paths) == 1
    assert static_paths[0].url_path == "/xsense_recordings_static"
    assert len(panels) == 1
    assert panels[0]["frontend_url_path"] == "xsense-recordings"
    assert panels[0]["webcomponent_name"] == "xsense-recordings-panel"
    assert panels[0]["sidebar_title"] == "X-Sense Recordings"
    assert panels[0]["sidebar_icon"] == "mdi:video-box"
    with open("custom_components/xsense/manifest.json", encoding="utf-8") as file:
        version = json.load(file)["version"]
    assert panels[0]["module_url"] == (
        f"/xsense_recordings_static/recordings-panel.js?v={version}"
    )


def test_recordings_panel_unregister_removes_sidebar_panel(monkeypatch):
    from custom_components.xsense import frontend

    removed = []

    def remove_panel(hass, frontend_url_path, *, warn_if_unknown=True):
        removed.append((frontend_url_path, warn_if_unknown))

    monkeypatch.setattr(frontend.frontend, "async_remove_panel", remove_panel)
    hass = SimpleNamespace(data={DOMAIN: {"_recordings_panel_registered": True}})

    frontend.async_unregister_recordings_panel(hass)

    assert removed == [("xsense-recordings", False)]
    assert "_recordings_panel_registered" not in hass.data[DOMAIN]


def test_recordings_runtime_setup_is_camera_gated():
    assert not xsense_module._has_camera_entities(
        {
            "stations": {"station": SimpleNamespace(type="SBS50")},
            "devices": {"device": SimpleNamespace(type="XS01-M")},
        }
    )
    assert not xsense_module._has_camera_entities(
        {
            "stations": {},
            "devices": {"xcom-ir": SimpleNamespace(type="XC0M-iR")},
        }
    )
    assert xsense_module._has_camera_entities(
        {
            "stations": {"camera": SimpleNamespace(type="SSC0A")},
            "devices": {},
        }
    )


def test_recordings_runtime_gate_checks_all_loaded_entries():
    hass = SimpleNamespace(
        data={
            DOMAIN: {
                "entry-one": SimpleNamespace(
                    data={
                        "stations": {"station": SimpleNamespace(type="SBS50")},
                        "devices": {},
                    }
                ),
                "entry-two": SimpleNamespace(
                    data={
                        "stations": {},
                        "devices": {"camera": SimpleNamespace(type="SSC0A")},
                    }
                ),
            }
        }
    )

    assert xsense_module._has_any_camera_entities(hass)


def test_recordings_runtime_cleanup_removes_stale_non_camera_runtime(monkeypatch):
    calls = []

    monkeypatch.setattr(
        xsense_module,
        "async_remove_recording_index",
        lambda hass, entry_id: calls.append(("remove_index", entry_id)),
    )
    monkeypatch.setattr(
        xsense_module,
        "async_unregister_recordings_panel",
        lambda hass: calls.append("recordings_panel"),
    )
    monkeypatch.setattr(
        xsense_module,
        "async_unregister_recording_services",
        lambda hass: calls.append("recording_services"),
    )

    xsense_module._cleanup_recordings_runtime(SimpleNamespace(), "xcom-entry")

    assert calls == [
        ("remove_index", "xcom-entry"),
        "recordings_panel",

        "recording_services",
    ]


def test_setup_entry_removes_recordings_runtime_without_cameras(monkeypatch):
    calls = []

    def async_track_time_interval(hass, action, interval):
        calls.append(("interval", interval))
        return lambda: None

    async def async_register_recordings_panel(hass):
        calls.append("recordings_panel")

    async def async_register_recordings_http_views(hass):
        calls.append("recordings_http_views")


    async def async_register_recording_services(hass):
        calls.append("recording_services")

    class Coordinator:
        data = {
            "stations": {"station": SimpleNamespace(type="SBS50")},
            "devices": {"detector": SimpleNamespace(type="XS01-M")},
        }

        async def async_config_entry_first_refresh(self):
            calls.append("first_refresh")

        def async_start_camera_ai_history_polling(self, *, immediate=True):
            calls.append(("camera_history_polling", immediate))

        def async_schedule_deferred_refresh(self):
            calls.append("deferred_refresh")

    class ConfigEntries:
        async def async_forward_entry_setups(self, entry, platforms):
            calls.append(("forward_platforms", tuple(platforms)))

    class Bus:
        def async_listen_once(self, event, callback):
            calls.append(("listen_once", event))
            return lambda: None

    class Entry:
        entry_id = "entry-no-camera"

        def add_update_listener(self, listener):
            calls.append(("add_update_listener", listener.__name__))
            return lambda: None

        def async_on_unload(self, unload):
            calls.append(("on_unload", callable(unload)))

    monkeypatch.setattr(
        xsense_module,
        "XSenseDataUpdateCoordinator",
        lambda hass, entry: Coordinator(),
    )
    monkeypatch.setattr(xsense_module, "async_track_time_interval", async_track_time_interval)
    monkeypatch.setattr(
        xsense_module,
        "_cleanup_recordings_runtime",
        lambda hass, entry_id=None: calls.append(("cleanup", entry_id)),
    )
    monkeypatch.setattr(
        xsense_module,
        "async_register_recordings_panel",
        async_register_recordings_panel,
    )
    monkeypatch.setattr(
        xsense_module,
        "async_register_recordings_http_views",
        async_register_recordings_http_views,
    )

    monkeypatch.setattr(
        xsense_module,
        "async_register_recording_services",
        async_register_recording_services,
    )
    monkeypatch.setattr(
        xsense_module,
        "async_start_recording_media_sync",
        lambda hass, entry: calls.append("recording_media_sync"),
    )
    monkeypatch.setattr(
        xsense_module,
        "_schedule_startup_maintenance",
        lambda hass, entry, coordinator: calls.append("startup_maintenance"),
    )

    hass = SimpleNamespace(
        data={},
        config_entries=ConfigEntries(),
        bus=Bus(),
        is_running=True,
    )

    assert asyncio.run(xsense_module.async_setup_entry(hass, Entry()))

    assert ("cleanup", "entry-no-camera") in calls
    assert "recordings_panel" not in calls
    assert "recordings_http_views" not in calls

    assert "recording_services" not in calls
    assert "recording_media_sync" not in calls


def test_setup_entry_registers_recordings_runtime_with_cameras(monkeypatch):
    calls = []

    def async_track_time_interval(hass, action, interval):
        calls.append(("interval", interval))
        return lambda: None

    async def async_register_recordings_panel(hass):
        calls.append("recordings_panel")

    async def async_register_recordings_http_views(hass):
        calls.append("recordings_http_views")


    async def async_register_recording_services(hass):
        calls.append("recording_services")

    class Coordinator:
        data = {
            "stations": {},
            "devices": {"camera": SimpleNamespace(type="SSC0A")},
        }

        async def async_config_entry_first_refresh(self):
            calls.append("first_refresh")

        def async_start_camera_ai_history_polling(self, *, immediate=True):
            calls.append(("camera_history_polling", immediate))

        def async_schedule_deferred_refresh(self):
            calls.append("deferred_refresh")

    class ConfigEntries:
        async def async_forward_entry_setups(self, entry, platforms):
            calls.append(("forward_platforms", tuple(platforms)))

    class Bus:
        def async_listen_once(self, event, callback):
            calls.append(("listen_once", event))
            return lambda: None

    class Entry:
        entry_id = "entry-camera"
        options = {CONF_RECORDING_MEDIA_SYNC_ENABLED: True}

        def add_update_listener(self, listener):
            calls.append(("add_update_listener", listener.__name__))
            return lambda: None

        def async_on_unload(self, unload):
            calls.append(("on_unload", callable(unload)))

    monkeypatch.setattr(
        xsense_module,
        "XSenseDataUpdateCoordinator",
        lambda hass, entry: Coordinator(),
    )
    monkeypatch.setattr(xsense_module, "async_track_time_interval", async_track_time_interval)
    monkeypatch.setattr(
        xsense_module,
        "_cleanup_recordings_runtime",
        lambda hass, entry_id=None: calls.append(("cleanup", entry_id)),
    )
    monkeypatch.setattr(
        xsense_module,
        "async_register_recordings_panel",
        async_register_recordings_panel,
    )
    monkeypatch.setattr(
        xsense_module,
        "async_register_recordings_http_views",
        async_register_recordings_http_views,
    )

    monkeypatch.setattr(
        xsense_module,
        "async_register_recording_services",
        async_register_recording_services,
    )
    monkeypatch.setattr(
        xsense_module,
        "async_start_recording_media_sync",
        lambda hass, entry: calls.append("recording_media_sync"),
    )
    monkeypatch.setattr(
        xsense_module,
        "_schedule_startup_maintenance",
        lambda hass, entry, coordinator: calls.append("startup_maintenance"),
    )

    hass = SimpleNamespace(
        data={},
        config_entries=ConfigEntries(),
        bus=Bus(),
        is_running=True,
    )

    assert asyncio.run(xsense_module.async_setup_entry(hass, Entry()))

    assert ("cleanup", "entry-camera") not in calls
    assert "recordings_panel" in calls
    assert "recordings_http_views" in calls

    assert "recording_services" in calls
    assert "recording_media_sync" in calls


def test_setup_entry_registers_recordings_runtime_when_camera_appears_later(
    monkeypatch,
):
    calls = []
    listeners = []
    pending_tasks = []

    def async_track_time_interval(hass, action, interval):
        calls.append(("interval", interval))
        return lambda: None

    async def async_register_recordings_panel(hass):
        calls.append("recordings_panel")

    async def async_register_recordings_http_views(hass):
        calls.append("recordings_http_views")


    async def async_register_recording_services(hass):
        calls.append("recording_services")

    class Coordinator:
        def __init__(self):
            self.data = {"stations": {}, "devices": {}}

        async def async_config_entry_first_refresh(self):
            calls.append("first_refresh")

        def async_add_listener(self, listener):
            listeners.append(listener)
            return lambda: None

        def async_start_camera_ai_history_polling(self, *, immediate=True):
            calls.append(("camera_history_polling", immediate))

        def async_schedule_deferred_refresh(self):
            calls.append("deferred_refresh")

    coordinator = Coordinator()

    class ConfigEntries:
        async def async_forward_entry_setups(self, entry, platforms):
            calls.append(("forward_platforms", tuple(platforms)))

    class Entry:
        entry_id = "entry-delayed-camera"
        options = {CONF_RECORDING_MEDIA_SYNC_ENABLED: True}

        def add_update_listener(self, listener):
            calls.append(("add_update_listener", listener.__name__))
            return lambda: None

        def async_on_unload(self, unload):
            calls.append(("on_unload", callable(unload)))

    class Hass:
        is_running = True
        data = {}
        config_entries = ConfigEntries()

        def create_task(self, coro):
            task = asyncio.create_task(coro)
            pending_tasks.append(task)
            return task

    monkeypatch.setattr(
        xsense_module,
        "XSenseDataUpdateCoordinator",
        lambda hass, entry: coordinator,
    )
    monkeypatch.setattr(xsense_module, "async_track_time_interval", async_track_time_interval)
    monkeypatch.setattr(
        xsense_module,
        "_cleanup_recordings_runtime",
        lambda hass, entry_id=None: calls.append(("cleanup", entry_id)),
    )
    monkeypatch.setattr(
        xsense_module,
        "async_register_recordings_panel",
        async_register_recordings_panel,
    )
    monkeypatch.setattr(
        xsense_module,
        "async_register_recordings_http_views",
        async_register_recordings_http_views,
    )

    monkeypatch.setattr(
        xsense_module,
        "async_register_recording_services",
        async_register_recording_services,
    )
    monkeypatch.setattr(
        xsense_module,
        "async_start_recording_media_sync",
        lambda hass, entry: calls.append("recording_media_sync"),
    )
    monkeypatch.setattr(
        xsense_module,
        "_schedule_startup_maintenance",
        lambda hass, entry, coordinator: calls.append("startup_maintenance"),
    )

    async def run_test():
        hass = Hass()

        assert await xsense_module.async_setup_entry(hass, Entry())
        assert ("cleanup", "entry-delayed-camera") in calls
        assert "recordings_panel" not in calls

        coordinator.data["stations"]["camera"] = SimpleNamespace(type="SSC0A")
        listeners[0]()
        await asyncio.gather(*pending_tasks)

    asyncio.run(run_test())

    assert "recordings_panel" in calls
    assert "recordings_http_views" in calls

    assert "recording_services" in calls
    assert "recording_media_sync" in calls


def test_recordings_runtime_unload_unregisters_after_last_camera(monkeypatch):
    calls = []

    class ConfigEntries:
        async def async_unload_platforms(self, entry, platforms):
            return True

    async def async_shutdown():
        calls.append("shutdown")

    monkeypatch.setattr(
        xsense_module,
        "async_remove_recording_index",
        lambda hass, entry_id: calls.append(("remove_index", entry_id)),
    )
    monkeypatch.setattr(
        xsense_module,
        "async_unregister_recordings_panel",
        lambda hass: calls.append("recordings_panel"),
    )
    monkeypatch.setattr(
        xsense_module,
        "async_unregister_recording_services",
        lambda hass: calls.append("recording_services"),
    )

    entry = SimpleNamespace(entry_id="camera-entry")
    coordinator = SimpleNamespace(
        data={
            "stations": {"camera": SimpleNamespace(type="SSC0A")},
            "devices": {},
        },
        async_shutdown=async_shutdown,
    )
    hass = SimpleNamespace(
        config_entries=ConfigEntries(),
        data={DOMAIN: {entry.entry_id: coordinator}},
    )

    assert asyncio.run(xsense_module.async_unload_entry(hass, entry))
    assert calls == [
        ("remove_index", "camera-entry"),
        "shutdown",
        "recordings_panel",
        "recording_services",
    ]


def test_recordings_runtime_unregister_helpers(monkeypatch):
    from custom_components.xsense import media_source

    removed_services = []

    class Services:
        def has_service(self, domain, service):
            return True

        def async_remove(self, domain, service):
            removed_services.append((domain, service))

    hass = SimpleNamespace(
        data={
            DOMAIN: {
                "_recording_services_registered": True,
            }
        },
        services=Services(),
    )

    media_source.async_unregister_recording_services(hass)

    assert removed_services == [
        (DOMAIN, "refresh_recordings"),
        (DOMAIN, "cache_recordings"),
        (DOMAIN, "clear_recordings_cache"),
    ]
    assert "_recording_services_registered" not in hass.data[DOMAIN]


def test_recordings_panel_url_deep_links_to_clip():
    from custom_components.xsense.frontend import recordings_panel_url

    assert recordings_panel_url(
        "entry-id",
        "CAMERA/SN",
        1782049304,
        end_time=1782049334,
    ) == (
        "/xsense-recordings#entry_id=entry-id&serial=CAMERA%2FSN"
        "&start=1782049304&end=1782049334"
    )


def test_recordings_panel_video_uses_authenticated_blob_playback():
    with open(
        "custom_components/xsense/frontend/recordings-panel.js",
        encoding="utf-8",
    ) as file:
        panel = file.read()

    assert 'type: "auth/sign_path"' in panel
    assert "const signedPath = await this.signPath(playbackPath)" in panel
    assert "const response = await fetch(signedPath" in panel
    assert "URL.createObjectURL(blob)" in panel
    assert "playbackFallbackKeys" not in panel
    assert "fallback_playback_url" not in panel
    assert "retryClipPlaybackWithFallback" not in panel
    assert 'this.logPanelEvent("playback_fallback_start"' not in panel
    assert "route_clip_missing" in panel
    assert "routeClipFromParams" not in panel
    assert 'this.logPanelEvent("clip_open"' in panel
    assert 'this.logPanelEvent("playback_fetch_start"' in panel
    assert 'this.logPanelEvent("playback_fetch_response"' in panel
    assert 'this.logPanelEvent("playback_blob_ready"' in panel
    assert 'this.logPanelEvent("playback_error"' in panel
    assert 'this.logPanelEvent("video_autoplay_error"' in panel
    assert 'const events = ["loadedmetadata", "canplay", "playing", "waiting", "stalled", "error"]' in panel
    assert "video_${eventName}" in panel
    assert 'this._hass.callApi("POST", "xsense/recordings/panel/debug"' in panel
    assert 'src="${this.escape(playbackUrl)}"' in panel
    assert 'data-hls-url="${this.escape(playbackUrl)}"' in panel
    assert 'playbackType === "hls"' in panel
    assert 'const HLS_JS_URL = "/xsense_recordings_static/vendor/hls.light.min.js"' in panel
    assert "async loadHlsLibrary()" in panel
    assert "new Hls({" in panel
    assert "enableWorker: false" in panel
    assert "setPlaybackUrl(key, url, type)" in panel
    assert "clearPlaybackUrl(key)" in panel
    assert "disposePlaybackResources()" in panel
    assert 'this.logPanelEvent("playback_hls_js_attached"' in panel
    assert 'this.logPanelEvent("playback_hls_js_error"' in panel
    assert 'this.logPanelEvent("playback_hls_native_attached"' in panel
    assert 'this.logPanelEvent("playback_hls_ready"' in panel
    assert "isHlsResponse(contentType, response.url || signedPath)" in panel
    assert "Preparing recording..." in panel
    assert "clip.signed_playback_url" not in panel
    assert 'src="${this.escape(clip.playback_url)}"' not in panel
    assert 'src="${clip.playback_url}"' not in panel


def test_recordings_http_registration_adds_panel_views():
    from custom_components.xsense import http

    views = []
    hass = SimpleNamespace(
        data={},
        http=SimpleNamespace(register_view=views.append),
    )

    import asyncio

    asyncio.run(http.async_register_recordings_http_views(hass))
    asyncio.run(http.async_register_recordings_http_views(hass))

    assert len(views) == 5
    assert isinstance(views[0], http.XSenseRecordingsPanelDataView)
    assert isinstance(views[1], http.XSenseRecordingsPanelDebugView)
    assert isinstance(views[2], http.XSenseRecordingsPanelPlaybackView)
    assert isinstance(views[3], http.XSenseRecordingsPanelThumbnailView)
    assert isinstance(views[4], http.XSenseRecordingsHlsSegmentView)


def test_recordings_hls_playlist_rewrites_segments_to_token_route(tmp_path):
    from custom_components.xsense import http

    playlist = tmp_path / "index.m3u8"
    playlist.write_text(
        "#EXTM3U\n"
        "#EXT-X-TARGETDURATION:4\n"
        "segment_0001.ts\n"
        "nested/index.m3u8\n"
        "#EXT-X-ENDLIST\n",
        encoding="utf-8",
    )

    assert http._hls_playlist_for_response(
        playlist,
        "/api/xsense/recordings/hls/token",
    ) == (
        "#EXTM3U\n"
        "#EXT-X-TARGETDURATION:4\n"
        "/api/xsense/recordings/hls/token/segment_0001.ts\n"
        "/api/xsense/recordings/hls/token/nested/index.m3u8\n"
        "#EXT-X-ENDLIST\n"
    )


def test_recordings_panel_debug_view_logs_sanitized_payload(caplog):
    from custom_components.xsense import http

    class Request:
        async def json(self):
            return {
                "event": "playback_fetch_response",
                "entry_id": "01KT8FZM5BZWF5R3Y4VWY3PMZ1",
                "serial": "CAMERA-SERIAL-123456",
                "start": "1782049304",
                "end": "1782049334",
                "cached": False,
                "playback_url": "/api/xsense/recordings/play/entry-id/1/2",
                "status": 404,
                "ok": False,
                "bytes": 0,
                "elapsed_ms": 1234,
                "duration": 30000,
                "ready_state": 0,
                "network_state": 3,
                "error_code": 4,
                "message": "Recording is not ready (404)",
                "type": "mediaError",
                "details": "bufferStalledError",
                "fatal": True,
            }

    caplog.set_level(logging.DEBUG, logger="custom_components.xsense")

    response = asyncio.run(http.XSenseRecordingsPanelDebugView(None).post(Request()))

    assert response.status == 200
    assert "X-Sense recordings panel frontend event" in caplog.text
    assert "playback_fetch_response" in caplog.text
    assert "'playback_url_kind': 'api'" in caplog.text
    assert "'duration_ms': 30000" in caplog.text
    assert "'ready_state': 0" in caplog.text
    assert "'network_state': 3" in caplog.text
    assert "'error_code': 4" in caplog.text
    assert "'hls_type': 'mediaError'" in caplog.text
    assert "'hls_details': 'bufferStalledError'" in caplog.text
    assert "'hls_fatal': True" in caplog.text
    assert "CAMERA-SERIAL-123456" not in caplog.text


def test_recordings_panel_data_exposes_cache_backed_clips(monkeypatch):
    from custom_components.xsense import http

    ready_paths = set()
    mp4_ready_paths = set()

    monkeypatch.setattr(
        http,
        "_path_ready",
        lambda path: str(path) in ready_paths,
    )
    monkeypatch.setattr(
        http,
        "_mp4_ready",
        lambda path: str(path) in mp4_ready_paths,
    )
    monkeypatch.setattr(
        http,
        "_file_size",
        lambda path: 123 if str(path).endswith(".mp4") else 45,
    )
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_entry=lambda entry_id: SimpleNamespace(data={}, options={})
        )
    )
    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "date": "2026-06-30",
        "start": 1782049304,
        "end": 1782049334,
        "title": "Motion",
        "source": "video_url",
        "playback_url": "https://example.invalid/clip.mp4",
        "thumbnail_url": "https://example.invalid/thumb.jpg",
        "media_root": "/media/xsense_recordings",
    }
    ready_paths.update(
        {
            str(http._clip_thumbnail_cache_path(clip)),
        }
    )
    mp4_ready_paths.add(str(http._clip_cache_path(clip)))

    data = http.build_panel_data(
        hass,
        {
            "generated_at": "2026-06-30T00:00:00+00:00",
            "cameras": [
                {
                    "entry_id": "entry-id",
                    "serial": "CAMERA-SN",
                    "name": "Garden",
                    "online": True,
                    "clips": [clip],
                }
            ],
        },
    )

    assert data["title"] == "X-Sense Recordings"
    assert data["stats"]["ready_clips"] == 1
    assert data["stats"]["visible_clips"] == 1
    assert data["stats"]["latest_clip"]["camera_name"] == "Garden"
    assert data["stats"]["media_roots"] == ["/media/xsense_recordings"]
    camera = data["cameras"][0]
    assert camera["dates"] == ["2026-06-30"]
    assert camera["clips"][0]["playback_url"].startswith(
        "/media/local/xsense_recordings/videos/"
    )
    assert "fallback_playback_url" not in camera["clips"][0]
    assert camera["clips"][0]["thumbnail_url"].startswith(
        "/media/local/xsense_recordings/thumbs/"
    )


def test_recordings_panel_data_prefers_hls_over_legacy_mp4(monkeypatch):
    from custom_components.xsense import http

    monkeypatch.setattr(http, "_path_ready", lambda path: False)
    monkeypatch.setattr(http, "_mp4_ready", lambda path: True)
    monkeypatch.setattr(http, "_hls_ready", lambda clip: True)
    monkeypatch.setattr(http, "_file_size", lambda path: 123)
    monkeypatch.setattr(http, "_directory_size", lambda path: 777)
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_entry=lambda entry_id: SimpleNamespace(data={}, options={})
        )
    )
    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "date": "2026-06-30",
        "start": 1782049304,
        "end": 1782049334,
        "title": "Motion",
        "source": "video_url",
        "playback_url": "https://example.invalid/index.m3u8",
        "media_root": "/media/xsense_recordings",
    }

    data = http.build_panel_data(
        hass,
        {
            "generated_at": "2026-06-30T00:00:00+00:00",
            "cameras": [
                {
                    "entry_id": "entry-id",
                    "serial": "CAMERA-SN",
                    "name": "Garden",
                    "online": True,
                    "clips": [clip],
                }
            ],
        },
    )

    camera = data["cameras"][0]
    assert data["stats"]["ready_clips"] == 1
    assert data["stats"]["video_bytes"] == 777
    assert camera["clips"][0]["playback_url"].startswith(
        "/api/xsense/recordings/play/entry-id/1782049304/1782049334"
    )


def test_recordings_panel_data_omits_missing_thumbnail_url(monkeypatch):
    from custom_components.xsense import http

    monkeypatch.setattr(http, "_path_ready", lambda path: False)
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_entry=lambda entry_id: SimpleNamespace(data={}, options={})
        )
    )

    data = http.build_panel_data(
        hass,
        {
            "cameras": [
                {
                    "entry_id": "entry-id",
                    "serial": "CAMERA-SN",
                    "name": "Garden",
                    "clips": [
                        {
                            "entry_id": "entry-id",
                            "serial": "CAMERA-SN",
                            "date": "2026-06-30",
                            "start": 1782049304,
                            "end": 1782049334,
                            "source": "video_url",
                            "playback_url": "https://example.invalid/clip.mp4",
                            "media_root": "/media/xsense_recordings",
                        }
                    ],
                }
            ],
        },
    )

    assert data["cameras"][0]["clips"][0]["thumbnail_url"] == ""


def test_recordings_panel_data_counts_video_ready_without_thumbnail(monkeypatch):
    from custom_components.xsense import http

    monkeypatch.setattr(http, "_path_ready", lambda path: False)
    monkeypatch.setattr(http, "_mp4_ready", lambda path: str(path).endswith(".mp4"))
    monkeypatch.setattr(http, "_file_size", lambda path: 123)
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_entry=lambda entry_id: SimpleNamespace(data={}, options={})
        )
    )

    data = http.build_panel_data(
        hass,
        {
            "cameras": [
                {
                    "entry_id": "entry-id",
                    "serial": "CAMERA-SN",
                    "name": "Garden",
                    "clips": [
                        {
                            "entry_id": "entry-id",
                            "serial": "CAMERA-SN",
                            "date": "2026-06-30",
                            "start": 1782049304,
                            "end": 1782049334,
                            "source": "video_url",
                            "playback_url": "https://example.invalid/clip.mp4",
                            "thumbnail_url": "https://example.invalid/thumb.jpg",
                            "media_root": "/media/xsense_recordings",
                        }
                    ],
                }
            ],
        },
    )

    assert data["stats"]["ready_clips"] == 1
    assert data["stats"]["pending_clips"] == 0
    clip = data["cameras"][0]["clips"][0]
    assert clip["cached"]
    assert not clip["thumbnail_cached"]


def test_recordings_panel_data_hides_invalid_test_fixture_clips(monkeypatch):
    from custom_components.xsense import http

    monkeypatch.setattr(http, "_path_ready", lambda path: False)
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_entry=lambda entry_id: SimpleNamespace(data={}, options={})
        )
    )

    data = http.build_panel_data(
        hass,
        {
            "cameras": [
                {
                    "entry_id": "entry-id",
                    "serial": "CAMERA-SN",
                    "name": "Garden",
                    "clips": [
                        {
                            "entry_id": "entry-id",
                            "serial": "CAMERA-SN",
                            "date": "2026-06-30",
                            "start": 1782049304,
                            "end": 1782049334,
                            "media_root": "/media/xsense_recordings",
                        }
                    ],
                }
            ],
        },
    )

    assert data["stats"]["indexed_clips"] == 1
    assert data["stats"]["visible_clips"] == 0
    assert data["stats"]["pending_clips"] == 0
    assert data["cameras"][0]["clips"] == []


def test_recordings_panel_playback_serves_cached_file(monkeypatch, tmp_path):
    from aiohttp import web

    from custom_components.xsense import http
    from custom_components.xsense.media_source import XSenseRecordingsMediaSource

    clip_path = tmp_path / "clip.mp4"
    clip_path.write_bytes(b"\x00\x00\x00\x10ftypmp42\x00\x00\x00\x00cached")
    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "start": 1782049304,
        "end": 1782049334,
    }

    async def load_index(self):
        return {
            "cameras": [
                {
                    "entry_id": "entry-id",
                    "serial": "CAMERA-SN",
                    "clips": [clip],
                }
            ]
        }

    async def cached_url(self, current_clip):
        return "/media/local/xsense_recordings/videos/clip.mp4"

    monkeypatch.setattr(XSenseRecordingsMediaSource, "_async_load_index", load_index)
    monkeypatch.setattr(
        XSenseRecordingsMediaSource,
        "_async_cached_playback_url",
        cached_url,
    )
    monkeypatch.setattr(http, "_clip_cache_path", lambda current_clip: clip_path)
    monkeypatch.setattr(http, "_path_ready", lambda path: path == clip_path)
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_entry=lambda entry_id: SimpleNamespace(data={}, options={})
        )
    )

    import asyncio

    response = asyncio.run(
        http.XSenseRecordingsPanelPlaybackView(hass).get(
            SimpleNamespace(query={"serial": "CAMERA-SN"}),
            "entry-id",
            "1782049304",
            "1782049334",
        )
    )

    assert isinstance(response, web.FileResponse)


def test_recordings_panel_playback_serves_hls_before_legacy_mp4(
    monkeypatch,
    tmp_path,
):
    from aiohttp import web

    from custom_components.xsense import http, media_source
    from custom_components.xsense.media_source import XSenseRecordingsMediaSource

    clip_path = tmp_path / "clip.mp4"
    clip_path.write_bytes(b"\x00\x00\x00\x10ftypmp42\x00\x00\x00\x00legacy")
    playlist = tmp_path / "hls" / "index.m3u8"
    playlist.parent.mkdir(parents=True)
    playlist.write_text("#EXTM3U\n#EXT-X-TARGETDURATION:4\nsegment_0001.ts\n")
    (playlist.parent / "segment_0001.ts").write_bytes(b"segment")
    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "start": 1782049304,
        "end": 1782049334,
    }

    async def load_index(self):
        return {
            "cameras": [
                {
                    "entry_id": "entry-id",
                    "serial": "CAMERA-SN",
                    "clips": [clip],
                }
            ]
        }

    async def cached_url(self, current_clip):
        return "/media/local/xsense_recordings/hls/index.m3u8"

    monkeypatch.setattr(XSenseRecordingsMediaSource, "_async_load_index", load_index)
    monkeypatch.setattr(
        XSenseRecordingsMediaSource,
        "_async_cached_playback_url",
        cached_url,
    )
    monkeypatch.setattr(http, "_clip_cache_path", lambda current_clip: clip_path)
    monkeypatch.setattr(media_source, "_clip_cache_path", lambda current_clip: clip_path)
    monkeypatch.setattr(
        http,
        "_hls_playlist_cache_path",
        lambda current_clip: playlist,
    )
    monkeypatch.setattr(
        media_source,
        "_hls_playlist_cache_path",
        lambda current_clip: playlist,
    )
    hass = SimpleNamespace(
        data={},
        config_entries=SimpleNamespace(
            async_get_entry=lambda entry_id: SimpleNamespace(data={}, options={})
        ),
    )

    import asyncio

    response = asyncio.run(
        http.XSenseRecordingsPanelPlaybackView(hass).get(
            SimpleNamespace(query={"serial": "CAMERA-SN"}),
            "entry-id",
            "1782049304",
            "1782049334",
        )
    )

    assert isinstance(response, web.Response)
    assert not isinstance(response, web.FileResponse)
    assert response.content_type == http.HLS_MIME_TYPE
    assert b"/api/xsense/recordings/hls/" in response.body


def test_recordings_panel_playback_ignores_capture_query_and_uses_direct_media(
    monkeypatch,
    tmp_path,
):
    from aiohttp import web

    from custom_components.xsense import http
    from custom_components.xsense.media_source import XSenseRecordingsMediaSource

    clip_path = tmp_path / "clip.mp4"
    clip_path.write_bytes(b"direct")
    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "start": 1782049304,
        "end": 1782049334,
        "source": "video_url",
        "quality": "HD",
        "playback_url": "https://example.invalid/clip.m3u8",
    }
    seen = {}

    async def load_index(self):
        return {
            "cameras": [
                {
                    "entry_id": "entry-id",
                    "serial": "CAMERA-SN",
                    "clips": [clip],
                }
            ]
        }

    async def cached_url(self, current_clip):
        seen.update(current_clip)
        clip_path.write_bytes(b"\x00\x00\x00\x10ftypmp42\x00\x00\x00\x00sd")
        return "/media/local/xsense_recordings/videos/clip.mp4"

    monkeypatch.setattr(XSenseRecordingsMediaSource, "_async_load_index", load_index)
    monkeypatch.setattr(
        XSenseRecordingsMediaSource,
        "_async_cached_playback_url",
        cached_url,
    )
    monkeypatch.setattr(http, "_clip_cache_path", lambda current_clip: clip_path)
    monkeypatch.setattr(http, "_path_ready", lambda path: path == clip_path and path.exists())
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_entry=lambda entry_id: SimpleNamespace(data={}, options={})
        )
    )

    import asyncio

    response = asyncio.run(
        http.XSenseRecordingsPanelPlaybackView(hass).get(
            SimpleNamespace(query={"serial": "CAMERA-SN", "capture": "1"}),
            "entry-id",
            "1782049304",
            "1782049334",
        )
    )

    assert isinstance(response, web.FileResponse)
    assert seen["source"] == "video_url"
    assert seen["quality"] == "HD"
    assert seen["playback_url"] == "https://example.invalid/clip.m3u8"
    assert clip_path.read_bytes() == b"\x00\x00\x00\x10ftypmp42\x00\x00\x00\x00sd"


def test_recordings_panel_playback_waits_for_sync_when_sync_enabled(
    monkeypatch,
    tmp_path,
):
    from aiohttp import web

    from custom_components.xsense import http
    from custom_components.xsense.const import CONF_RECORDING_MEDIA_SYNC_ENABLED
    from custom_components.xsense.media_source import XSenseRecordingsMediaSource

    clip_path = tmp_path / "clip.mp4"
    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "start": 1782049304,
        "end": 1782049334,
        "source": "sd_playback",
    }

    async def load_index(self):
        return {
            "cameras": [
                {
                    "entry_id": "entry-id",
                    "serial": "CAMERA-SN",
                    "clips": [clip],
                }
            ]
        }

    async def cached_url(self, current_clip):
        raise AssertionError("sync mode should not lazy-cache panel playback")

    monkeypatch.setattr(XSenseRecordingsMediaSource, "_async_load_index", load_index)
    monkeypatch.setattr(
        XSenseRecordingsMediaSource,
        "_async_cached_playback_url",
        cached_url,
    )
    monkeypatch.setattr(http, "_clip_cache_path", lambda current_clip: clip_path)
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_entry=lambda entry_id: SimpleNamespace(
                data={},
                options={CONF_RECORDING_MEDIA_SYNC_ENABLED: True},
            )
        )
    )

    import asyncio

    with pytest.raises(web.HTTPNotFound):
        asyncio.run(
            http.XSenseRecordingsPanelPlaybackView(hass).get(
                SimpleNamespace(query={"serial": "CAMERA-SN"}),
                "entry-id",
                "1782049304",
                "1782049334",
            )
        )


def test_recordings_panel_playback_rejects_missing_clip(
    monkeypatch,
):
    from aiohttp import web

    from custom_components.xsense import http
    from custom_components.xsense.media_source import XSenseRecordingsMediaSource

    async def load_index(self):
        return {
            "cameras": [
                {
                    "entry_id": "entry-id",
                    "serial": "CAMERA-SN",
                    "name": "Garden",
                    "clips": [],
                }
            ]
        }

    monkeypatch.setattr(XSenseRecordingsMediaSource, "_async_load_index", load_index)
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_entry=lambda entry_id: SimpleNamespace(data={}, options={})
        )
    )

    with pytest.raises(web.HTTPNotFound):
        asyncio.run(
            http.XSenseRecordingsPanelPlaybackView(hass).get(
                SimpleNamespace(query={"serial": "CAMERA-SN"}),
                "entry-id",
                "1782049304",
                "1782049334",
            )
        )


def test_recordings_panel_playback_does_not_redirect_to_external_media(
    monkeypatch,
    tmp_path,
):
    from aiohttp import web

    from custom_components.xsense import http
    from custom_components.xsense.media_source import XSenseRecordingsMediaSource

    clip_path = tmp_path / "clip.mp4"
    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "start": 1782049304,
        "end": 1782049334,
    }

    async def load_index(self):
        return {
            "cameras": [
                {
                    "entry_id": "entry-id",
                    "serial": "CAMERA-SN",
                    "clips": [clip],
                }
            ]
        }

    async def cached_url(self, current_clip):
        return "https://example.invalid/clip.mp4"

    monkeypatch.setattr(XSenseRecordingsMediaSource, "_async_load_index", load_index)
    monkeypatch.setattr(
        XSenseRecordingsMediaSource,
        "_async_cached_playback_url",
        cached_url,
    )
    monkeypatch.setattr(http, "_clip_cache_path", lambda current_clip: clip_path)
    monkeypatch.setattr(http, "_path_ready", lambda path: False)
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_entry=lambda entry_id: SimpleNamespace(data={}, options={})
        )
    )

    import asyncio

    with pytest.raises(web.HTTPNotFound):
        asyncio.run(
            http.XSenseRecordingsPanelPlaybackView(hass).get(
                SimpleNamespace(query={"serial": "CAMERA-SN"}),
                "entry-id",
                "1782049304",
                "1782049334",
            )
        )


def test_recordings_panel_thumbnail_does_not_redirect_to_external_media(
    monkeypatch,
    tmp_path,
):
    from aiohttp import web

    from custom_components.xsense import http
    from custom_components.xsense.media_source import XSenseRecordingsMediaSource

    thumb_path = tmp_path / "thumb.jpg"
    clip = {
        "entry_id": "entry-id",
        "serial": "CAMERA-SN",
        "start": 1782049304,
        "end": 1782049334,
        "thumbnail_url": "https://example.invalid/thumb.jpg",
    }

    async def load_index(self):
        return {
            "cameras": [
                {
                    "entry_id": "entry-id",
                    "serial": "CAMERA-SN",
                    "clips": [clip],
                }
            ]
        }

    async def cache_thumbnail(self, current_clip):
        return False

    monkeypatch.setattr(XSenseRecordingsMediaSource, "_async_load_index", load_index)
    monkeypatch.setattr(
        XSenseRecordingsMediaSource,
        "_async_cache_thumbnail",
        cache_thumbnail,
    )
    monkeypatch.setattr(http, "_clip_thumbnail_cache_path", lambda current_clip: thumb_path)
    monkeypatch.setattr(http, "_path_ready", lambda path: False)
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_entry=lambda entry_id: SimpleNamespace(data={}, options={})
        )
    )

    import asyncio

    with pytest.raises(web.HTTPNotFound):
        asyncio.run(
            http.XSenseRecordingsPanelThumbnailView(hass).get(
                SimpleNamespace(query={"serial": "CAMERA-SN"}),
                "entry-id",
                "1782049304",
                "1782049334",
            )
        )


def test_recordings_panel_api_urls_keep_serial_in_query():
    from custom_components.xsense import http

    assert http._playback_api_url(
        "entry-id",
        "CAMERA/SN",
        1782049304,
        1782049334,
    ) == (
        "/api/xsense/recordings/play/entry-id/1782049304/1782049334"
        "?serial=CAMERA%2FSN"
    )
    assert http._thumbnail_api_url(
        "entry-id",
        "CAMERA/SN",
        1782049304,
        1782049334,
    ) == (
        "/api/xsense/recordings/thumb/entry-id/1782049304/1782049334"
        "?serial=CAMERA%2FSN"
    )
