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
    media_url_choice = choose_action["choose"][0]
    fallback_url_choice = choose_action["choose"][1]
    direct_url_action = media_url_choice["sequence"][0]
    fallback_url_action = fallback_url_choice["sequence"][0]
    direct_message = direct_url_action["message"]
    notification_data = direct_url_action["data"]
    fallback_notification_data = fallback_url_action["data"]

    assert variables["xsense_event_entity"] == "ai_detection_event"
    assert variables["xsense_include_recording_link"] == "include_recording_link"
    assert variables["xsense_include_snapshot_link"] == "include_snapshot_link"
    assert "trigger.to_state.attributes" in variables["xsense_event_data"]
    assert "trigger.event.data" in variables["xsense_event_data"]
    assert "state_attr(xsense_event_entity, 'event_type')" in variables["xsense_event_type"]
    assert "camera_name" in variables["xsense_camera_name"]
    assert "state_attr(xsense_event_entity, 'camera_name')" in variables["xsense_camera_name"]
    assert "state_attr(xsense_event_entity, 'friendly_name')" in variables["xsense_camera_name"]
    assert "recording_url" in variables["xsense_recording_url"]
    assert "state_attr(xsense_event_entity, 'recording_url')" in variables["xsense_recording_url"]
    assert "recording_media_url" in variables["xsense_recording_media_url"]
    assert "state_attr(xsense_event_entity, 'recording_media_url')" in variables["xsense_recording_media_url"]
    assert "xsense_recording_url[0:13] != '/media/local/'" in variables[
        "xsense_recording_tap_url"
    ]
    assert "xsense_recording_media_url or xsense_recording_url" in variables[
        "xsense_recording_tap_url"
    ]
    assert "xsense_recording_target" not in variables
    assert "snapshot_url" in variables["xsense_snapshot_url"]
    assert "state_attr(xsense_event_entity, 'snapshot_url')" in variables["xsense_snapshot_url"]
    assert "xsense_notification_url" not in variables
    assert "noAction" not in str(blueprint)
    assert "app://com.xsense.security" not in str(blueprint)
    assert direct_url_action["domain"] == "mobile_app"
    assert direct_url_action["type"] == "notify"
    assert direct_url_action["device_id"] == "notify_device"
    assert direct_url_action["title"] == "{{ xsense_camera_name }}"
    assert len(blueprint["actions"]) == 1
    assert len(choose_action["choose"]) == 2
    assert "default" not in choose_action
    assert "actions" not in blueprint["blueprint"]["input"]
    assert "Companion app video playback target" in blueprint["blueprint"]["description"]
    assert "recording_media_url" in blueprint["blueprint"]["description"]
    assert "xsense_camera_name" in direct_message
    assert "xsense_recording_url" not in direct_message
    assert "xsense_snapshot_url" in direct_message
    assert "No playback URL" not in str(blueprint)
    assert "trigger." not in direct_message
    assert notification_data["url"] == "{{ xsense_recording_tap_url }}"
    assert notification_data["clickAction"] == "{{ xsense_recording_tap_url }}"
    assert notification_data["video"] == "{{ xsense_recording_media_url }}"
    assert notification_data["attachment"] == {
        "url": "{{ xsense_recording_media_url }}",
        "content-type": "video/mp4",
        "hide-thumbnail": False,
    }
    assert "xsense_recording_media_url" in str(media_url_choice["conditions"])
    assert "xsense_recording_tap_url" in str(fallback_url_choice["conditions"])
    assert fallback_notification_data == {
        "url": "{{ xsense_recording_tap_url }}",
        "clickAction": "{{ xsense_recording_tap_url }}",
    }
    assert "actions" not in notification_data
    assert "trigger." not in str(choose_action)


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
    assert panels[0]["module_url"] == "/xsense_recordings_static/recordings-panel.js"


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

    assert len(views) == 3
    assert isinstance(views[0], http.XSenseRecordingsPanelDataView)
    assert isinstance(views[1], http.XSenseRecordingsPanelPlaybackView)
    assert isinstance(views[2], http.XSenseRecordingsPanelThumbnailView)


def test_recordings_panel_data_exposes_cache_backed_clips(monkeypatch):
    from custom_components.xsense import http

    ready_paths = set()

    monkeypatch.setattr(
        http,
        "_path_ready",
        lambda path: str(path) in ready_paths,
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
        "source": "sd_playback",
        "playback_url": "/xsense-recordings#entry_id=entry-id",
        "thumbnail_url": "https://example.invalid/thumb.jpg",
        "media_root": "/media/xsense_recordings",
    }
    ready_paths.update(
        {
            str(http._clip_cache_path(clip)),
            str(http._clip_thumbnail_cache_path(clip)),
        }
    )

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
    assert camera["clips"][0]["thumbnail_url"].startswith(
        "/media/local/xsense_recordings/thumbs/"
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
                            "source": "sd_playback",
                            "playback_url": "/xsense-recordings#entry_id=entry-id",
                            "media_root": "/media/xsense_recordings",
                        }
                    ],
                }
            ],
        },
    )

    assert data["cameras"][0]["clips"][0]["thumbnail_url"] == ""


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
    clip_path.write_bytes(b"mp4")
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
