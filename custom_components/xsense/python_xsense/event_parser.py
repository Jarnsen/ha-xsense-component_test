"""Pure parsers for X-Sense MQTT and camera-history event payloads."""

from __future__ import annotations

from contextlib import suppress
from datetime import datetime, timezone
import json
from typing import Any


APK_AI_DETECTION_OBJECTS = {
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
}

APK_AI_DETECTION_GROUPS = {
    "person": {"person"},
    "pet": {"pet"},
    "vehicle": {"vehicle", "vehicle_enter", "vehicle_out", "vehicle_held_up"},
    "package": {"package", "package_drop_off", "package_pick_up", "package_exist"},
    "other": {"other"},
}

APK_AI_DETECTION_DATA_KEYS = {
    "person": "person",
    "pet": "pet",
    "vehicle_enter": "vehicleEnter",
    "vehicle_out": "vehicleOut",
    "vehicle_held_up": "vehicleHeldUp",
    "package_drop_off": "packageDropOff",
    "package_pick_up": "packagePickUp",
    "package_exist": "packageExist",
    "other": "other",
}

MQTT_IDENTIFIER_KEYS = {
    "camerasn",
    "cxserialnumber",
    "deviceid",
    "devicesn",
    "devserialnumber",
    "realcxserialnumber",
    "serial",
    "serialnumber",
    "sn",
    "stationsn",
    "stationserialnumber",
}

SELF_TEST_RESULT_KEYS = (
    "lastSelfTest",
    "selfTest",
    "selfTestResult",
    "selfTestStatus",
    "testResult",
    "testStatus",
    "result",
)

SELF_TEST_TIME_KEYS = (
    "lastSelfTestTime",
    "selfTestTime",
    "testTime",
    "eventTime",
    "timestamp",
    "time",
)

SELF_TEST_FAULT_KEYS = (
    "selfTestCoFault",
    "selfTestLifeEnd",
    "selfTestLowPower",
    "selfTestSmokeFault",
)

__all__ = [
    "APK_AI_DETECTION_DATA_KEYS",
    "APK_AI_DETECTION_GROUPS",
    "APK_AI_DETECTION_OBJECTS",
    "MQTT_IDENTIFIER_KEYS",
    "apk_ai_detection_name_times",
    "apk_ai_detection_names",
    "apk_ai_detection_object_times",
    "apply_apk_ai_detection_aliases",
    "apply_apk_dispatch_aliases",
    "apply_apk_event_aliases",
    "camera_ai_history_event_key",
    "camera_event_history_event_key",
    "camera_event_history_playback_data",
    "camera_event_history_playback_source",
    "camera_event_history_records",
    "camera_event_history_station_data",
    "camera_event_history_time",
    "camera_playback_epoch_seconds",
    "latest_apk_detection_time",
    "is_self_test_topic",
    "is_presence_topic",
    "mqtt_identifier_candidates",
    "mqtt_identifier_key_name",
    "mqtt_reported_data",
    "mqtt_topic_kind",
    "normalize_self_test_report",
    "normalize_self_test_result",
    "self_test_report_payload",
    "SELF_TEST_RESULT_KEYS",
    "SELF_TEST_TIME_KEYS",
]


def mqtt_reported_data(data: dict[str, Any]) -> dict[str, Any] | list[Any]:
    """Return device data from either shadow reports or X-Sense event payloads."""
    reported = data.get("state", {}).get("reported")
    if isinstance(reported, dict):
        return reported.copy()
    if isinstance(reported, list):
        return list(reported)

    event_data = data.get("eventData")
    if isinstance(event_data, str):
        try:
            event_data = json.loads(event_data)
        except json.JSONDecodeError:
            event_data = None
    if isinstance(event_data, dict):
        result = event_data.copy()
        if event_time := data.get("eventTime"):
            result.setdefault("time", event_time)
            result.setdefault("eventTime", event_time)
        if event_type := data.get("eventType") or result.get("eventType"):
            result.setdefault("eventType", event_type)
        apply_apk_dispatch_aliases(result)
        apply_apk_event_aliases(result)
        return result

    if any(
        key in data
        for key in (
            "dispatchDevs",
            "eventItems",
            "eventObjectType",
            "eventType",
            "lastType",
            "serialNumber",
        )
    ):
        result = data.copy()
        if event_time := data.get("eventTime"):
            result.setdefault("time", event_time)
            result.setdefault("eventTime", event_time)
        apply_apk_dispatch_aliases(result)
        apply_apk_event_aliases(result)
        return result

    return {}


def mqtt_identifier_candidates(*values: Any) -> list[str]:
    """Return possible station/device identifiers from nested MQTT payloads."""
    candidates: list[str] = []
    seen: set[str] = set()

    def add(value: Any) -> None:
        if value in (None, ""):
            return
        text = str(value).strip()
        if not text or text in seen:
            return
        seen.add(text)
        candidates.append(text)

    def walk(value: Any) -> None:
        if isinstance(value, str):
            text = value.strip()
            if text.startswith(("{", "[")):
                with suppress(json.JSONDecodeError):
                    walk(json.loads(text))
            return
        if isinstance(value, dict):
            for key, nested_value in value.items():
                key_name = mqtt_identifier_key_name(key)
                if key_name in MQTT_IDENTIFIER_KEYS and not isinstance(
                    nested_value, (dict, list, tuple, set)
                ):
                    add(nested_value)
                walk(nested_value)
            return
        if isinstance(value, (list, tuple, set)):
            for item in value:
                walk(item)

    for value in values:
        walk(value)
    return candidates


def mqtt_identifier_key_name(value: Any) -> str:
    """Return a normalized MQTT identifier key name."""
    return "".join(char for char in str(value).strip().lower() if char.isalnum())


def mqtt_topic_kind(topic: str) -> str:
    """Return a non-sensitive MQTT topic category."""
    if is_presence_topic(topic):
        return "presence"
    if topic.startswith("@xsense/events/aiplan/"):
        return "ai_plan"
    if topic.startswith("@xsense/events/"):
        return "house_event"
    if "/shadow/name/" in topic:
        return "shadow"
    return "other"


def is_presence_topic(topic: str) -> bool:
    """Return if an MQTT topic is an AWS IoT presence update."""
    return "/events/presence/" in topic


def is_self_test_topic(topic: str) -> bool:
    """Return if an MQTT update is an X-Sense self-test report topic."""
    return any(
        marker in topic
        for marker in (
            "_testup/update",
            "alarmtestup/update",
            "selftestup/update",
            "selftestup_v2/update",
        )
    )


def normalize_self_test_report(data: dict[str, Any]) -> None:
    """Normalize APK self-test report fields into reusable state keys."""
    report = self_test_report_payload(data)
    target = report if report is not data else data
    for key in SELF_TEST_RESULT_KEYS:
        value = report.get(key)
        if value not in (None, ""):
            target["lastSelfTest"] = normalize_self_test_result(value)
            break
    else:
        fault_values = [report.get(key) for key in SELF_TEST_FAULT_KEYS]
        if any(value not in (None, "") for value in fault_values):
            target["lastSelfTest"] = (
                "1"
                if any(is_truthy_self_test_fault(value) for value in fault_values)
                else "0"
            )

    for key in SELF_TEST_TIME_KEYS:
        value = report.get(key)
        if value not in (None, ""):
            target["lastSelfTestTime"] = value
            break

    for key in ("stationSN", "deviceSN", "userId"):
        value = report.get(key)
        if value not in (None, ""):
            target.setdefault(key, value)


def self_test_report_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Return the APK SmokeCheckSelfUpShadowBean-style payload."""
    if any(key in data for key in SELF_TEST_RESULT_KEYS):
        return data
    for value in data.values():
        if isinstance(value, dict) and any(
            key in value for key in (*SELF_TEST_RESULT_KEYS, *SELF_TEST_FAULT_KEYS)
        ):
            return value
    return data


def normalize_self_test_result(value: Any) -> Any:
    """Return the app-style success code when the report uses readable text."""
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"success", "successful", "ok", "pass", "passed"}:
            return "0"
        if normalized in {"fail", "failed", "failure", "error"}:
            return "1"
    return value


def is_truthy_self_test_fault(value: Any) -> bool:
    """Return whether an APK DeviceTestV2 fault flag is set."""
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "fault", "failed"}
    return value is True or value == 1


def camera_ai_history_event_key(server_id: str, alarm_item: dict[str, Any]) -> str:
    """Return a stable key for one APK AI-history alarm item."""
    if event_id := alarm_item.get("eventId"):
        return f"{server_id}:{event_id}"
    payload = json.dumps(
        alarm_item,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return f"{server_id}:{payload}"


def camera_event_history_records(history: dict[str, Any]) -> list[dict[str, Any]]:
    """Return ADDX camera event records from the APK event-history response."""
    data = history.get("data") if isinstance(history.get("data"), dict) else history
    records = data.get("list") if isinstance(data, dict) else None
    if not isinstance(records, list):
        return []
    return [record for record in records if isinstance(record, dict)]


def camera_event_history_event_key(record: dict[str, Any]) -> str:
    """Return a stable key for one APK ADDX camera event record."""
    serial = record.get("serialNumber") or record.get("deviceSn") or record.get("sn")
    trace = record.get("traceId") or record.get("traceIds")
    timestamp = record.get("timestamp") or record.get("startTime") or record.get("date")
    if serial and (trace or timestamp):
        return f"camera-event:{serial}:{trace or timestamp}"
    payload = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return f"camera-event:{payload}"


def camera_event_history_station_data(record: dict[str, Any]) -> dict[str, Any]:
    """Return normal camera state keys from an APK ADDX event-history record."""
    serial = record.get("serialNumber") or record.get("deviceSn") or record.get("sn")
    if not serial:
        return {}

    timestamp = record.get("timestamp") or record.get("startTime")
    event_time = camera_event_history_time(timestamp)
    data: dict[str, Any] = {
        "serialNumber": serial,
        "deviceSN": serial,
        "eventType": record.get("videoEvent") or record.get("tags") or "motion",
        "eventItems": record.get("eventInfoList"),
        "eventObjectType": record.get("eventInfoList") or record.get("tags"),
        "lastType": record.get("videoEvent") or record.get("tags"),
    }
    if event_time:
        data["time"] = event_time
        data["eventTime"] = event_time

    if playback := camera_event_history_playback_data(record):
        data["playback"] = playback

    apply_apk_event_aliases(data)
    return data


def camera_event_history_playback_data(record: dict[str, Any]) -> dict[str, Any]:
    """Return APK recording playback metadata from an ADDX history record."""
    playback: dict[str, Any] = {}
    for source_key, target_key in (
        ("traceId", "trace_id"),
        ("traceIds", "trace_ids"),
        ("videoUrl", "video_url"),
        ("imageUrl", "image_url"),
        ("packageImageUrl", "package_image_url"),
        ("multiResolutionVideos", "multi_resolution_videos"),
        ("subVideos", "sub_videos"),
        ("resolution", "resolution"),
        ("resolutionInfo", "resolution_info"),
        ("highFramerate", "high_framerate"),
        ("startTime", "start_time"),
        ("endTime", "end_time"),
        ("timestamp", "timestamp"),
        ("period", "period"),
        ("fileSize", "file_size"),
        ("videoEvent", "video_event"),
        ("tags", "tags"),
    ):
        value = record.get(source_key)
        if value not in (None, ""):
            playback[target_key] = value

    for raw_key, seconds_key in (
        ("start_time", "start_time_s"),
        ("end_time", "end_time_s"),
        ("timestamp", "timestamp_s"),
    ):
        seconds = camera_playback_epoch_seconds(playback.get(raw_key))
        if seconds is not None:
            playback[seconds_key] = seconds

    playback_source = camera_event_history_playback_source(record)
    if playback_source:
        playback["source"] = playback_source
    return playback


def camera_playback_epoch_seconds(value: Any) -> int | None:
    """Return epoch seconds for APK playback values that may be ms or seconds."""
    if value in (None, ""):
        return None
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return None
    if timestamp > 10_000_000_000:
        timestamp //= 1000
    return timestamp


def camera_event_history_playback_source(record: dict[str, Any]) -> str | None:
    """Return how the APK can play a camera history record."""
    if record.get("videoUrl"):
        return "video_url"
    if record.get("startTime") not in (None, "") or record.get("timestamp") not in (
        None,
        "",
    ):
        return "sd_playback"
    return None


def camera_event_history_time(value: Any) -> str | None:
    """Return an X-Sense compact timestamp from an ADDX epoch timestamp."""
    if value in (None, ""):
        return None
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return str(value)
    if timestamp > 10_000_000_000:
        timestamp //= 1000
    return datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y%m%d%H%M%S")


def apply_apk_dispatch_aliases(data: dict[str, Any]) -> None:
    """Apply APK dispatch device identifiers to normal MQTT lookup keys."""
    dispatch_devs = data.get("dispatchDevs")
    if not isinstance(dispatch_devs, list):
        return

    dispatch_dev = next((item for item in dispatch_devs if isinstance(item, dict)), None)
    if dispatch_dev is None:
        return

    if station_sn := _first_alias(
        dispatch_dev,
        (
            "stationSn",
            "stationSN",
            "_stationSN",
            "_stationSn",
            "stationSerialNumber",
            "serialNumber",
            "sn",
        ),
    ):
        data.setdefault("stationSN", station_sn)
    if device_sn := _first_alias(
        dispatch_dev,
        (
            "deviceSn",
            "deviceSN",
            "_deviceSN",
            "_deviceSn",
            "devSerialNumber",
            "serialNumber",
            "sn",
        ),
    ):
        data.setdefault("deviceSN", device_sn)
        data.setdefault("serialNumber", device_sn)
    if event_time := dispatch_dev.get("eventTime"):
        data.setdefault("time", event_time)


def _first_alias(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None


def apply_apk_event_aliases(data: dict[str, Any]) -> None:
    """Apply APK event aliases that are not reported as shadow keys."""
    apply_apk_ai_detection_aliases(data)


def apply_apk_ai_detection_aliases(data: dict[str, Any]) -> None:
    """Apply APK AI detection object names from camera event payloads."""
    fallback_time = data.get("time") or data.get("eventTime")
    object_times = apk_ai_detection_object_times(data, fallback_time)
    objects = set(object_times)
    if not objects:
        return

    data["lastAiDetection"] = ",".join(sorted(objects))
    for group, object_names in APK_AI_DETECTION_GROUPS.items():
        detected_objects = objects & object_names
        detected = bool(detected_objects)
        data[f"{group}Detected"] = detected
        if detected:
            time_value = latest_apk_detection_time(
                object_times.get(name) for name in detected_objects
            )
            if time_value:
                data[f"last{group.title()}DetectionTime"] = time_value
    for object_name, data_key in APK_AI_DETECTION_DATA_KEYS.items():
        detected = object_name in objects
        data[f"{data_key}Detected"] = detected
        if detected and object_times.get(object_name):
            data[f"last{data_key[0].upper()}{data_key[1:]}DetectionTime"] = object_times[
                object_name
            ]


def apk_ai_detection_object_times(
    data: dict[str, Any], fallback_time: Any = None
) -> dict[str, Any]:
    """Return APK AI detection object names and their best event timestamp."""
    raw_values: list[Any] = [
        data.get("eventObjectType"),
        data.get("eventItems"),
        data.get("lastType"),
        data.get("lastAiDetection"),
    ]
    objects: dict[str, Any] = {}
    for raw_value in raw_values:
        for name, time_value in apk_ai_detection_name_times(
            raw_value, fallback_time
        ).items():
            objects[name] = latest_apk_detection_time((objects.get(name), time_value))
    return objects


def apk_ai_detection_name_times(value: Any, fallback_time: Any = None) -> dict[str, Any]:
    """Return APK AI detection object names with timestamps from nested payloads."""
    if value is None:
        return {}
    if isinstance(value, str):
        text = value.strip()
        if text.startswith(("{", "[")):
            with suppress(json.JSONDecodeError):
                return apk_ai_detection_name_times(json.loads(text), fallback_time)
        return {name: fallback_time for name in apk_ai_detection_names(text)}
    if isinstance(value, dict):
        item_time = value.get("eventTime") or value.get("time") or fallback_time
        objects: dict[str, Any] = {}
        for key in ("eventType", "eventObjectType", "eventItems", "lastType"):
            for name, time_value in apk_ai_detection_name_times(
                value.get(key), item_time
            ).items():
                objects[name] = latest_apk_detection_time(
                    (objects.get(name), time_value)
                )
        for key, nested_value in value.items():
            key_name = str(key).strip().lower()
            if key_name in APK_AI_DETECTION_GROUPS:
                nested = apk_ai_detection_name_times(nested_value, item_time)
                if nested:
                    for name, time_value in nested.items():
                        objects[name] = latest_apk_detection_time(
                            (objects.get(name), time_value)
                        )
                elif nested_value not in (None, False):
                    for name in APK_AI_DETECTION_GROUPS[key_name]:
                        objects[name] = latest_apk_detection_time(
                            (objects.get(name), item_time)
                        )
                continue
            if key_name in APK_AI_DETECTION_OBJECTS and nested_value not in (
                None,
                False,
            ):
                objects[key_name] = latest_apk_detection_time(
                    (objects.get(key_name), item_time)
                )
                continue
            if key in {"eventType", "eventObjectType", "eventItems", "lastType"}:
                continue
            for name, time_value in apk_ai_detection_name_times(
                nested_value, item_time
            ).items():
                objects[name] = latest_apk_detection_time(
                    (objects.get(name), time_value)
                )
        return objects
    if isinstance(value, (list, tuple, set)):
        objects: dict[str, Any] = {}
        for item in value:
            for name, time_value in apk_ai_detection_name_times(
                item, fallback_time
            ).items():
                objects[name] = latest_apk_detection_time(
                    (objects.get(name), time_value)
                )
        return objects
    return {}


def latest_apk_detection_time(values) -> Any:
    """Return the newest compact X-Sense time value from an iterable."""
    candidates = [value for value in values if value not in (None, "")]
    if not candidates:
        return None
    return max(candidates, key=str)


def apk_ai_detection_names(value: Any) -> set[str]:
    """Return APK AI detection object names from a scalar/list/dict value."""
    if value is None:
        return set()
    if isinstance(value, str):
        text = value.strip()
        if text.startswith(("{", "[")):
            with suppress(json.JSONDecodeError):
                return apk_ai_detection_names(json.loads(text))
        candidates = [
            part.strip().lower()
            for part in text.replace(";", ",").replace("|", ",").split(",")
        ]
        return {name for name in candidates if name in APK_AI_DETECTION_OBJECTS}
    if isinstance(value, dict):
        names: set[str] = set()
        for key, nested_value in value.items():
            key_name = str(key).strip().lower()
            if key_name in APK_AI_DETECTION_GROUPS:
                nested_names = apk_ai_detection_names(nested_value)
                if nested_names:
                    names.update(nested_names)
                elif nested_value not in (None, False):
                    names.update(APK_AI_DETECTION_GROUPS[key_name])
                continue
            if key_name in APK_AI_DETECTION_OBJECTS and nested_value not in (
                None,
                False,
            ):
                names.add(key_name)
            names.update(apk_ai_detection_names(nested_value))
        return names
    if isinstance(value, (list, tuple, set)):
        names: set[str] = set()
        for item in value:
            names.update(apk_ai_detection_names(item))
        return names
    return set()
