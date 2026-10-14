"""Replay barriers for bounded event-time history retention (not live MQTT)."""

import asyncio
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

import pytest
from test_audit_repairs import event_entity, make_coordinator, make_station, module

BASE = datetime(2026, 9, 1, 12, tzinfo=UTC)


def compact(value):
    return value.strftime("%Y%m%d%H%M%S")


@pytest.fixture(autouse=True)
def trusted_clock(monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2030, 1, 1, tzinfo=UTC).astimezone(tz)

    monkeypatch.setattr(module, "datetime", Clock)


def row(ai, key, when, camera="camera", kind="person", url=None):
    if ai:
        data = {"serialNumber": camera, "eventItems": [{"eventType": kind}]}
        if when is not None:
            data["eventItems"][0]["eventTime"] = compact(when)
        if url:
            data["playback"] = {"video_url": url}
        result = {"eventId": key, "eventData": data}
        if when is not None:
            result["createTime"] = compact(when)
        return result
    result = {"serialNumber": camera, "traceId": key}
    if when is not None:
        result["timestamp"] = int(when.timestamp())
    if url:
        result["videoUrl"] = url
    return result


def history(ai, *cameras):
    c = make_coordinator(*(cameras or [make_station("camera", "SSC0A")]))
    c._camera_ai_history_initialized.add("service")
    c._camera_event_history_initialized = True
    getter = AsyncMock()
    if ai:
        c.xsense.get_ai_service_history = getter
    else:
        c.xsense.get_camera_event_record_history_for_cameras = getter
    deliveries = []
    c._listeners[0] = (
        lambda: deliveries.append(deepcopy(c._camera_event_entity.data)),
        None,
    )

    async def poll(rows):
        getter.return_value = {"alarmItems" if ai else "list": rows}
        if ai:
            return await c._update_camera_ai_service_history(["service"])
        return await c._update_camera_event_history(
            list(c.xsense.houses["house"].stations.values())
        )

    return c, poll, getter, deliveries


def window_for(c, ai):
    return getattr(
        c, "_camera_ai_history_window" if ai else "_camera_event_history_window"
    )


@pytest.mark.parametrize("ai", [False, True])
async def test_expired_keys_cannot_replay_after_station_replacement(ai):
    c, poll, _, delivered = history(ai)
    old = row(ai, "old", BASE)
    await poll([old])
    window = window_for(c, ai)
    old_keys = set(window.seen)
    await poll([row(ai, "new", BASE + timedelta(days=2))])
    assert window.seen.isdisjoint(old_keys)
    assert len(window.seen) == len(window.times) == 1
    watermarks = dict(window.watermarks)
    replacement = make_station("camera", "SSC0A")
    c.xsense.houses["house"].stations["camera"] = replacement
    c.data["stations"]["camera"] = replacement
    delivered.clear()
    # No station/event-entity timestamp guard remains to hide a coordinator replay.
    assert not await poll([old])
    assert delivered == []
    assert "eventTime" not in replacement.data
    assert window.watermarks == watermarks
    assert window.seen.isdisjoint(old_keys)


@pytest.mark.parametrize("ai", [False, True])
async def test_batch_cutoff_precedes_delivery_and_is_per_camera(ai):
    cameras = [make_station(name, "SSC0A") for name in ("A", "B")]
    c, poll, _, delivered = history(ai, *cameras)
    await poll(
        [
            row(ai, "obsolete", BASE, "A"),
            row(ai, "latest", BASE + timedelta(days=2), "A"),
            row(ai, "quiet-camera", BASE, "B"),
        ]
    )
    assert [d["eventTime"] for d in delivered] == [
        compact(BASE),
        compact(BASE + timedelta(days=2)),
    ]
    assert len(window_for(c, ai).seen) == 2
    # A later arrival inside B's window remains eligible despite A's watermark.
    await poll([row(ai, "late-B", BASE + timedelta(minutes=1), "B")])
    assert delivered[-1]["eventTime"] == compact(BASE + timedelta(minutes=1))


@pytest.mark.parametrize("ai", [False, True])
async def test_baseline_and_empty_or_failed_polls_preserve_replay_barrier(ai):
    c, poll, getter, delivered = history(ai)
    c._camera_ai_history_initialized.clear()
    c._camera_event_history_initialized = False
    await poll([row(ai, "old", BASE), row(ai, "new", BASE + timedelta(days=2))])
    assert delivered == []
    window = window_for(c, ai)
    before = (set(window.seen), dict(window.times), dict(window.watermarks))
    await poll([])
    getter.side_effect = module.APIFailure("unavailable")
    assert not await poll([])
    assert (window.seen, window.times, window.watermarks) == before
    getter.side_effect = None
    await poll([row(ai, "old", BASE)])
    assert delivered == []


def test_window_boundary_out_of_order_clock_rollback_and_future_poison(monkeypatch):
    seen = set()
    window = module._HistoryDedupWindow(seen)
    source = ("service", "camera")
    window.advance([(source, compact(BASE))])
    window.remember("old", source, compact(BASE))
    window.advance([(source, compact(BASE + timedelta(days=1)))])
    assert "old" in seen  # The lower boundary is inclusive.
    assert not window.expired(source, compact(BASE))
    window.advance([(source, compact(BASE + timedelta(days=1, seconds=1)))])
    assert "old" not in seen
    assert window.expired(source, compact(BASE))
    assert not window.expired(source, compact(BASE + timedelta(seconds=1)))
    watermark = dict(window.watermarks)
    window.advance([(source, compact(BASE - timedelta(days=10)))])
    window.advance([(source, "20990101000000")])
    assert window.watermarks == watermark

    class EarlierClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2020, 1, 1, tzinfo=UTC).astimezone(tz)

    monkeypatch.setattr(module, "datetime", EarlierClock)
    window.advance([(source, compact(BASE))])
    assert window.watermarks == watermark
    assert window.expired(source, compact(BASE))


def test_unknown_malformed_future_and_whole_json_keys_remain_pinned():
    seen = set()
    window = module._HistoryDedupWindow(seen)
    source = ("service", "camera")
    for key, value in [
        ("unknown", None),
        ('{"signedUrl":"long"}', "bad"),
        ("future", "20990101000000"),
    ]:
        window.remember(key, source, value)
    window.advance([(source, compact(BASE + timedelta(days=100)))])
    assert seen == {"unknown", '{"signedUrl":"long"}', "future"}
    assert not window.times
    # A later enriched timestamp cannot turn a pinned unknown into an evictable key.
    window.remember("unknown", source, compact(BASE))
    window.advance([(source, compact(BASE + timedelta(days=101)))])
    assert "unknown" in seen


async def test_untimestamped_ai_identity_is_not_replayed_by_retention():
    c, poll, _, delivered = history(True)
    unknown = row(True, "unknown", None)
    unknown["eventData"]["playback"] = {"video_url": "signed-url"}
    unknown.pop("eventId")  # Exercise the full-JSON fallback key.
    await poll([unknown])
    assert len(delivered) == 1
    keys = set(window_for(c, True).seen)
    for day in range(4):
        await poll([row(True, str(day), BASE + timedelta(days=day)), unknown])
    assert keys <= window_for(c, True).seen
    assert len(delivered) == 5


@pytest.mark.parametrize("bad_time", ["20269901000000", "zzzz", "20990101000000"])
@pytest.mark.parametrize("delivery", ["separate", "same_batch", "preexisting"])
async def test_bad_ai_timestamp_never_poisons_or_swallows_valid_following_event(
    bad_time, delivery
):
    c, poll, _, delivered = history(True)
    camera = c.data["stations"]["camera"]
    _, fired = event_entity(c, camera, ai=True)
    bad = row(True, "bad", BASE)
    bad["createTime"] = bad_time
    bad["eventData"]["eventItems"][0]["eventTime"] = bad_time
    good_time = BASE + timedelta(minutes=1)
    good = row(True, "good", good_time)
    if delivery == "preexisting":
        camera.set_data({"eventTime": bad_time})
    elif delivery == "separate":
        assert not await poll([bad])
        assert delivered == fired == []
        assert "eventTime" not in camera.data
        assert "service:bad" in window_for(c, True).seen
        assert "service:bad" not in window_for(c, True).times
    assert await poll([bad, good] if delivery == "same_batch" else [good])
    assert camera.data["eventTime"] == compact(good_time)
    assert [d["eventTime"] for d in delivered] == [compact(good_time)]
    assert len(fired) == 1
    await poll([bad, good])
    assert camera.data["eventTime"] == compact(good_time)
    assert len(fired) == 1


async def test_ai_older_unseen_does_not_rewind_but_equal_time_ids_each_deliver_once():
    c, poll, _, delivered = history(True)
    camera = c.data["stations"]["camera"]
    _, fired = event_entity(c, camera, ai=True)
    person = row(True, "person", BASE, kind="person")
    vehicle = row(True, "vehicle", BASE, kind="vehicle")
    assert await poll([person, vehicle])
    assert len(fired) == len(delivered) == 2
    await poll([person, vehicle])
    assert len(fired) == 2
    assert camera.data["lastAiDetection"] == "vehicle"
    before = len(delivered)
    assert not await poll([row(True, "late", BASE - timedelta(minutes=1))])
    assert len(delivered) == before
    assert camera.data["eventTime"] == compact(BASE)
    assert not await poll([row(True, "late", BASE - timedelta(minutes=1))])


@pytest.mark.parametrize("has_time", [False, True])
async def test_malformed_reported_list_with_resolved_service_does_not_abort_poll(
    monkeypatch, has_time
):
    c, poll, _, delivered = history(True)
    camera = c.data["stations"]["camera"]
    monkeypatch.setattr(module, "_camera_station_for_ai_server", lambda *args: camera)
    malformed = {"eventId": "broken", "state": {"reported": [{"bad": True}]}}
    if has_time:
        malformed["createTime"] = compact(BASE)
    await poll(
        [
            malformed,
            row(True, "good", BASE),
        ]
    )
    assert len(delivered) == 1
    assert camera.data["eventTime"] == compact(BASE)


async def test_latest_same_time_ai_identity_retries_enrichment_not_earlier_identity(
    monkeypatch,
):
    from custom_components.xsense import recordings_media

    c, poll, _, _ = history(True)
    camera = c.data["stations"]["camera"]
    tasks = []
    c.hass = NS(
        data={}, async_create_task=lambda coro: tasks.append(asyncio.create_task(coro))
    )
    _e, fired = event_entity(c, camera, ai=True)
    cache = AsyncMock(side_effect=["", "/media/local/ready.mp4"])
    monkeypatch.setattr(recordings_media, "async_cache_recording_playback", cache)
    monkeypatch.setattr(
        recordings_media,
        "async_extract_camera_event_snapshot",
        AsyncMock(return_value=None),
    )
    person = row(True, "person", BASE, kind="person")
    vehicle = row(True, "vehicle", BASE, kind="vehicle", url="broken")
    await poll([person, vehicle])
    await tasks[0]
    assert len(fired) == 1  # Immediate raw person event only.
    vehicle["eventData"]["playback"]["video_url"] = "ready"
    await poll([person, vehicle])
    await tasks[1]
    await poll([person, vehicle])
    assert len(tasks) == 2
    assert len(fired) == 2  # Exactly one ready vehicle event, no replayed person.
    assert cache.await_args.kwargs["playback"]["video_url"] == "ready"
