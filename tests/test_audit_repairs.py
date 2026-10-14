"""Regression replays for the APK, camera event, and lifecycle audit."""

import asyncio
import json
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

import pytest
from botocore.exceptions import ClientError

from custom_components.xsense import alarm_control_panel as alarm
from custom_components.xsense import coordinator as module
from custom_components.xsense import event
from custom_components.xsense.python_xsense.base import XSenseBase
from custom_components.xsense.python_xsense.exceptions import APIFailure, AuthFailed
from custom_components.xsense.python_xsense.house import House
from custom_components.xsense.python_xsense.station import Station


def make_coordinator(*cameras):
    house = House.__new__(House)
    house.house_id = "house"
    house.stations = {camera.entity_id: camera for camera in cameras}
    c = module.XSenseDataUpdateCoordinator.__new__(module.XSenseDataUpdateCoordinator)
    c.xsense = NS(
        houses={"house": house},
        parse_get_state=XSenseBase.__new__(XSenseBase).parse_get_state,
    )
    c.data = {"stations": dict(house.stations), "devices": {}}
    c._listeners = {}
    c._shutting_down = False
    c._operation_tasks = {}
    c._connect_lock = asyncio.Lock()
    c._camera_ai_history_initialized = set()
    c._camera_ai_history_seen = set()
    c._camera_event_history_seen = set()
    c._camera_event_history_initialized = False
    c._camera_ai_service_houses = {}
    c._camera_event_snapshots = {}
    c._camera_event_snapshot_tasks = {}
    c._camera_event_delivery_locks = {}
    c._camera_ai_history_unsub = None
    c._deferred_refresh_unsub = None
    c.mqtt_servers = {}
    c.entry = NS(entry_id="audit", data={"email": "test", "password": "test"})
    c.last_update_success = True
    return c


def make_station(serial="station", category="SBS50"):
    return Station(
        NS(mqtt_server="test"),
        stationId=serial,
        stationSn=serial,
        stationName=serial,
        category=category,
        safeMode="Disarmed",
    )


def make_panel(monkeypatch):
    station = make_station()
    c = make_coordinator(station)
    panel = alarm.XSenseAlarmControlPanel(c, station)
    panel.hass = object()
    panel.async_write_ha_state = lambda: None
    panel._active_normal_arm_mode = "Home"
    panel._cancel_arm_request_timeout = lambda: None
    notices = []
    panel._async_create_force_arm_notification = lambda s, mode: notices.append(mode)
    panel._async_clear_force_arm_notification = lambda: None
    c._listeners[0] = (panel._handle_coordinator_update, None)
    return c, station, panel, notices


def receive(c, station, shadow, **payload):
    c.async_event_received(
        f"$aws/things/{station.sn}/shadow/name/{shadow}/update",
        json.dumps(
            {"state": {"reported": {"stationSN": station.sn, **payload}}}
        ).encode(),
    )


@pytest.mark.parametrize("reported", ["Home", "Away", "Disarmed"])
def test_confirmation_never_changes_actual_mode_or_uses_result_target(
    monkeypatch, reported
):
    c, s, p, notices = make_panel(monkeypatch)
    receive(c, s, "2nd_modeconfirm", safeMode=reported, forceReason=[{"door": "1"}])
    assert s.safe_mode == "Disarmed"
    assert str(p.alarm_state) == "disarmed"
    assert p._pending_force_arm_mode == "Home"
    assert notices == ["Home"]
    assert not hasattr(s, "_xsense_mode_result")


@pytest.mark.parametrize("reported", ["Home", "Away", "Disarmed"])
def test_actual_mode_completes_any_request_and_ignores_later_confirmation(
    monkeypatch, reported
):
    c, s, p, notices = make_panel(monkeypatch)
    receive(c, s, "2nd_safemode", safeMode=reported, forceReason=[{"door": "1"}])
    assert p._active_normal_arm_mode is None
    assert s.safe_mode == reported
    receive(c, s, "2nd_modeconfirm", safeMode="Home", forceReason=[{"door": "1"}])
    assert notices == []
    assert p._pending_force_arm_mode is None


def test_confirmation_first_persists_and_empty_confirmation_keeps_waiting(monkeypatch):
    c, s, p, notices = make_panel(monkeypatch)
    receive(c, s, "2nd_modeconfirm", safeMode="Home", forceReason=[])
    assert p._active_normal_arm_mode == "Home"
    receive(c, s, "2nd_modeconfirm", forceReason=[{"door": "1"}])
    receive(c, s, "2nd_safemode", safeMode="Away")
    assert p._pending_force_arm_mode == "Home"
    assert notices == ["Home"]


def test_refresh_and_unrelated_topics_do_not_impersonate_mode_results(monkeypatch):
    c, s, p, notices = make_panel(monkeypatch)
    receive(c, s, "2nd_info_station", safeMode="Home", forceReason=[{"door": "1"}])
    assert p._active_normal_arm_mode == "Home"
    assert notices == []
    replacement = make_station()
    replacement.set_data({"safeMode": "Home"})
    c.data["stations"][s.entity_id] = replacement
    p._handle_coordinator_update()
    assert p._active_normal_arm_mode == "Home"


def test_ambiguous_camera_labels_never_route_but_strong_identifier_does():
    a, b = (make_station(name, "SSC0A") for name in ("A", "B"))
    a.sn = b.sn = "shared-label"
    c = make_coordinator(a, b)
    assert c._get_station_by_id("shared-label") is None
    assert module._camera_station_for_identifiers(c, ["shared-label"]) is None
    c.async_event_received(
        "@xsense/events/aiplan/user",
        json.dumps(
            {
                "eventData": {
                    "stationSN": "shared-label",
                    "eventItems": [
                        {"eventType": "person", "eventTime": "20260908120000"}
                    ],
                }
            }
        ).encode(),
    )
    assert "lastAiDetection" not in a.data
    assert "lastAiDetection" not in b.data
    assert module._camera_station_for_identifiers(c, ["shared-label", "B"]) is b


def event_entity(c, camera, *, ai=False):
    cls = event.XSenseEventEntity if ai else event.XSenseMotionEventEntity
    e = cls.__new__(cls)
    e.coordinator = c
    e.hass = getattr(c, "hass", None)
    e._dev_id = camera.entity_id
    e._camera_identity = camera.entity_id
    e._device_entity = False
    e._station_id = None
    e._motion_initialized = e._ai_detection_initialized = True
    e._last_motion_fingerprint = e._last_ai_detection_fingerprint = None
    e._add_camera_event_context = lambda *args: None
    e._add_motion_playback_url = e._add_recording_playback_url = lambda *args: None
    e._write_state_if_added = lambda: None
    fired = []
    e._trigger_event = lambda kind, data: fired.append(dict(data))
    c._listeners[len(c._listeners)] = (e._handle_coordinator_update, None)
    return e, fired


async def test_empty_ai_baseline_is_initialized_per_service():
    s = make_station("camera", "SSC0A")
    c = make_coordinator(s)
    _e, fired = event_entity(c, s, ai=True)
    c.xsense.get_ai_service_history = AsyncMock(return_value={"alarmItems": []})
    assert not await c._update_camera_ai_service_history(["service"])
    c.xsense.get_ai_service_history.return_value = {
        "alarmItems": [
            {
                "eventId": "new",
                "createTime": "20260908120000",
                "eventData": {
                    "serialNumber": "camera",
                    "eventItems": [
                        {"eventType": "person", "eventTime": "20260908120000"}
                    ],
                },
            }
        ]
    }
    assert await c._update_camera_ai_service_history(["service"])
    assert len(fired) == 1
    assert not await c._update_camera_ai_service_history(["service"])
    assert not await c._update_camera_ai_service_history(["new-service"])
    assert len(fired) == 1


@pytest.mark.parametrize("ai", [False, True])
async def test_each_history_record_delivered_once_even_during_station_refresh(ai):
    old = make_station("camera", "SSC0A")
    c = make_coordinator(old)
    e, fired = event_entity(c, old, ai=ai)
    old.set_data(
        {
            "eventTime": "20260908115900",
            "lastAiDetection": "person",
            "lastPersonDetectionTime": "20260908115900",
        }
    )
    e._handle_coordinator_update()
    fired.clear()
    current = make_station("camera", "SSC0A")
    c.xsense.houses["house"].stations["camera"] = current
    if ai:
        c._camera_ai_history_initialized.add("service")
        c.xsense.get_ai_service_history = AsyncMock(
            return_value={
                "alarmItems": [
                    {
                        "eventId": str(i),
                        "createTime": t,
                        "eventData": {
                            "serialNumber": "camera",
                            "eventItems": [{"eventType": "person", "eventTime": t}],
                        },
                    }
                    for i, t in enumerate(["20260908120000", "20260908120100"])
                ]
            }
        )
        run = lambda: c._update_camera_ai_service_history(["service"])
    else:
        c._camera_event_history_initialized = True
        c.xsense.get_camera_event_record_history_for_cameras = AsyncMock(
            return_value={
                "list": [
                    {"serialNumber": "camera", "timestamp": t, "traceId": str(t)}
                    for t in [1788868800, 1788868860]
                ]
            }
        )
        e._trigger_event_after_recording_cache = lambda *args: False
        run = lambda: c._update_camera_event_history([current])
    assert await run()
    assert [f["time"] for f in fired] == ["20260908120000", "20260908120100"]
    await run()
    c.async_update_listeners()
    assert len(fired) == 2


@pytest.mark.parametrize("ai", [False, True])
def test_history_delivery_does_not_match_another_cameras_secondary_alias(ai):
    a, b = (make_station(name, "SSC0A") for name in ("A", "B"))
    b.sn = "A"
    c = make_coordinator(a, b)
    _ea, fired_a = event_entity(c, a, ai=ai)
    _eb, fired_b = event_entity(c, b, ai=ai)
    b.set_data(
        {
            "eventTime": "20260908120000",
            "lastAiDetection": "person",
            "lastPersonDetectionTime": "20260908120000",
        }
    )
    c._async_publish_camera_event(b)
    assert fired_a == []
    assert len(fired_b) == 1


@pytest.mark.parametrize("shadow", ["2nd_safemode", "2nd_modeconfirm"])
def test_mqtt_mode_result_reaches_panel_during_discovery_replacement(
    monkeypatch, shadow
):
    c, _old, p, notices = make_panel(monkeypatch)
    new = make_station()
    c.xsense.houses["house"].stations[new.entity_id] = new
    receive(c, new, shadow, safeMode="Home", forceReason=[{"door": "1"}])
    c.data["stations"][new.entity_id] = new
    c.async_update_listeners()
    assert p._active_normal_arm_mode is None
    if shadow == "2nd_modeconfirm":
        assert p._pending_force_arm_mode == "Home"
        assert notices == ["Home"]
        assert str(p.alarm_state) == "disarmed"
    else:
        assert p._pending_force_arm_mode is None
        assert notices == []
        assert str(p.alarm_state) == "armed_home"


async def test_delayed_preparation_is_fifo_and_uses_captured_media(monkeypatch):
    from custom_components.xsense import recordings_media

    s = make_station("camera", "SSC0A")
    c = make_coordinator(s)
    tasks = []
    c.hass = NS(
        data={}, async_create_task=lambda coro: tasks.append(asyncio.create_task(coro))
    )
    e, fired = event_entity(c, s)
    started = asyncio.Event()
    release = asyncio.Event()
    prepared = []
    snapshots = []

    async def cache(hass, *, entity, playback, **kwargs):
        prepared.append((entity.data["eventTime"], playback["video_url"]))
        if len(prepared) == 1:
            started.set()
            await release.wait()
        return "/media/local/ready.mp4"

    async def snapshot(hass, playback):
        snapshots.append(playback["video_url"])
        return playback["video_url"].encode()

    monkeypatch.setattr(recordings_media, "async_cache_recording_playback", cache)
    monkeypatch.setattr(
        recordings_media, "async_extract_camera_event_snapshot", snapshot
    )
    s.set_data(
        {
            "eventTime": "20260908120000",
            "playback": {"video_url": "A", "image_url": "A.jpg"},
        }
    )
    e._handle_coordinator_update()
    await asyncio.wait_for(started.wait(), 2)
    s.data["playback"]["video_url"] = "MUTATED"
    s.set_data({"eventTime": "20260908120100", "playback": {"video_url": "B"}})
    e._handle_coordinator_update()
    await asyncio.sleep(0)
    assert len(prepared) == 1
    release.set()
    await asyncio.gather(*tasks)
    assert prepared == [("20260908120000", "A"), ("20260908120100", "B")]
    assert snapshots == ["A", "B"]
    assert [f["time"] for f in fired] == ["20260908120000", "20260908120100"]
    assert fired[0]["snapshot_url"] == "A.jpg"
    assert c.camera_event_snapshot(s) == b"B"


@pytest.mark.parametrize("ai", [False, True])
async def test_failed_preparation_retries_same_event_after_enrichment(monkeypatch, ai):
    from custom_components.xsense import recordings_media

    s = make_station("camera", "SSC0A")
    c = make_coordinator(s)
    tasks = []
    c.hass = NS(
        data={}, async_create_task=lambda coro: tasks.append(asyncio.create_task(coro))
    )
    e, fired = event_entity(c, s, ai=ai)
    cache = AsyncMock(side_effect=["", "/media/local/ready.mp4"])
    monkeypatch.setattr(recordings_media, "async_cache_recording_playback", cache)
    monkeypatch.setattr(
        recordings_media,
        "async_extract_camera_event_snapshot",
        AsyncMock(return_value=None),
    )
    s.set_data(
        {
            "eventTime": "20260908120000",
            "lastAiDetection": "person",
            "lastPersonDetectionTime": "20260908120000",
            "playback": {"video_url": "old"},
        }
    )
    e._handle_coordinator_update()
    e._handle_coordinator_update()
    assert len(tasks) == 1
    await tasks[0]
    assert fired == []
    s.set_data({"playback": {"video_url": "ready"}})
    e._handle_coordinator_update()
    await tasks[1]
    e._handle_coordinator_update()
    assert cache.await_count == 2
    assert len(fired) == 1


@pytest.mark.parametrize(
    "code, exception",
    [
        ("TooManyRequestsException", APIFailure),
        ("InternalErrorException", APIFailure),
        ("NotAuthorizedException", AuthFailed),
        ("UserNotFoundException", AuthFailed),
    ],
)
def test_cognito_transient_errors_do_not_request_reauth(code, exception):
    error = ClientError({"Error": {"Code": code, "Message": "test"}}, "InitiateAuth")
    with pytest.raises(exception):
        XSenseBase.__new__(XSenseBase)._raise_cognito_error(error)


@pytest.mark.parametrize("ai", [False, True])
async def test_history_poller_retries_current_failed_preparation_without_replaying(
    monkeypatch, ai
):
    from custom_components.xsense import recordings_media

    s = make_station("camera", "SSC0A")
    c = make_coordinator(s)
    tasks = []
    c.hass = NS(
        data={}, async_create_task=lambda coro: tasks.append(asyncio.create_task(coro))
    )
    _e, fired = event_entity(c, s, ai=ai)
    cache = AsyncMock(side_effect=["", "/media/local/ready.mp4"])
    monkeypatch.setattr(recordings_media, "async_cache_recording_playback", cache)
    monkeypatch.setattr(
        recordings_media,
        "async_extract_camera_event_snapshot",
        AsyncMock(return_value=None),
    )
    if ai:
        c._camera_ai_history_initialized.add("service")
        row = {
            "eventId": "id",
            "createTime": "20260908120000",
            "eventData": {
                "serialNumber": "camera",
                "playback": {"video_url": "old"},
                "eventItems": [{"eventType": "person", "eventTime": "20260908120000"}],
            },
        }
        c.xsense.get_ai_service_history = AsyncMock(return_value={"alarmItems": [row]})
        run = lambda: c._update_camera_ai_service_history(["service"])
    else:
        c._camera_event_history_initialized = True
        row = {
            "serialNumber": "camera",
            "timestamp": 1788868800,
            "traceId": "id",
            "videoUrl": "old",
        }
        c.xsense.get_camera_event_record_history_for_cameras = AsyncMock(
            return_value={"list": [row]}
        )
        run = lambda: c._update_camera_event_history([s])
    await run()
    await tasks[0]
    assert fired == []
    if ai:
        row["eventData"]["playback"]["video_url"] = "ready"
    else:
        row["videoUrl"] = "ready"
    await run()
    await tasks[1]
    await run()
    assert len(tasks) == 2
    assert len(fired) == 1
    assert cache.await_args.kwargs["playback"]["video_url"] == "ready"


def test_raw_event_is_not_replayed_when_same_event_gains_playback():
    s = make_station("camera", "SSC0A")
    c = make_coordinator(s)
    e, fired = event_entity(c, s)
    s.set_data({"eventTime": "20260908120000"})
    e._handle_coordinator_update()
    s.set_data({"playback": {"video_url": "ready"}})
    e._handle_coordinator_update()
    e._handle_coordinator_update()
    assert len(fired) == 1


async def test_connect_retires_mqtt_clients_with_old_signer(monkeypatch):
    c = make_coordinator()
    c.hass = NS(config=NS(language="en"))
    old = c.xsense
    old.close = AsyncMock()
    mqtt = NS(on_data=c.async_event_received, async_disconnect=AsyncMock())
    c.mqtt_servers = {"server": mqtt}
    new = NS(close=AsyncMock())
    monkeypatch.setattr(module, "AsyncXSense", lambda *args, **kwargs: new)
    monkeypatch.setattr(module, "async_get_clientsession", lambda hass: object())
    monkeypatch.setattr(module, "_async_init_and_login", AsyncMock())
    await c._connect()
    mqtt.async_disconnect.assert_awaited_once_with(disconnect_paho_client=True)
    old.close.assert_awaited_once()
    assert mqtt.on_data is None
    assert not c.mqtt_servers
    assert c.xsense is new


async def test_shutdown_cancels_inflight_login_and_calls_parent(monkeypatch):
    c = make_coordinator()
    c.hass = NS(config=NS(language="en"))
    c.xsense.close = AsyncMock()
    new = NS(close=AsyncMock())
    started = asyncio.Event()

    async def login(*args):
        started.set()
        await asyncio.Event().wait()

    parent = AsyncMock()
    monkeypatch.setattr(module.DataUpdateCoordinator, "async_shutdown", parent)
    monkeypatch.setattr(module, "AsyncXSense", lambda *args, **kwargs: new)
    monkeypatch.setattr(module, "async_get_clientsession", lambda hass: object())
    monkeypatch.setattr(module, "_async_init_and_login", login)
    pending = asyncio.create_task(c._connect())
    await asyncio.wait_for(started.wait(), 2)
    await c.async_shutdown()
    assert pending.cancelled()
    parent.assert_awaited_once()
    new.close.assert_awaited_once()
    assert c.xsense is None
    assert c._operation_tasks == {}
    with pytest.raises(asyncio.CancelledError):
        await c._connect()
    c.async_event_received("ignored", b"invalid")


async def test_shutdown_joins_all_retirees_when_connect_is_cancelled(monkeypatch):
    c = make_coordinator()
    c.xsense.close = AsyncMock()
    started = asyncio.Event()
    release = asyncio.Event()

    async def disconnect_first(**kwargs):
        started.set()
        await release.wait()

    first = NS(
        on_data=c.async_event_received,
        async_disconnect=AsyncMock(side_effect=disconnect_first),
    )
    second = NS(on_data=c.async_event_received, async_disconnect=AsyncMock())
    c.mqtt_servers = {"first": first, "second": second}
    parent = AsyncMock()
    monkeypatch.setattr(module.DataUpdateCoordinator, "async_shutdown", parent)
    connect = asyncio.create_task(c._connect())
    await asyncio.wait_for(started.wait(), 2)
    shutdown = asyncio.create_task(c.async_shutdown())
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert first.on_data is second.on_data is None
    assert not shutdown.done()
    release.set()
    await asyncio.wait_for(shutdown, 2)
    assert connect.cancelled()
    first.async_disconnect.assert_awaited_once()
    second.async_disconnect.assert_awaited_once()
    assert c._mqtt_retirement_tasks == {}
    assert c.mqtt_servers == {}


async def test_old_snapshot_never_links_current_proxy_after_discovery(monkeypatch):
    from custom_components.xsense import recordings_media

    old = make_station("camera", "SSC0A")
    old.set_data({"eventTime": "20260908120000"})
    c = make_coordinator(old)
    new = make_station("camera", "SSC0A")
    new.set_data({"eventTime": "20260908120100"})
    c.xsense.houses["house"].stations["camera"] = new
    tasks = []
    c.hass = NS(
        data={}, async_create_task=lambda coro: tasks.append(asyncio.create_task(coro))
    )
    e, fired = event_entity(c, old)
    monkeypatch.setattr(
        recordings_media,
        "async_cache_recording_playback",
        AsyncMock(return_value="/media/local/old.mp4"),
    )
    monkeypatch.setattr(
        recordings_media,
        "async_extract_camera_event_snapshot",
        AsyncMock(return_value=b"old-frame"),
    )
    assert event._trigger_event_after_recording_cache(
        e,
        "motion",
        old,
        {
            "time": "20260908120000",
            "camera_entity_id": "camera.test",
            "snapshot_url": "old.jpg",
            "playback": {"video_url": "old"},
        },
    )
    await tasks[0]
    assert fired[0]["snapshot_url"] == "old.jpg"
    assert c._camera_event_snapshots == {}
