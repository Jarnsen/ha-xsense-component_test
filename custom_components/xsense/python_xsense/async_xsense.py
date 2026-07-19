import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

import aiohttp

from .aws_signer import AWSSigner
from .base import XSenseBase, shadow_update_body
from .entity import Entity
from .entity_map import EntityType
from .exceptions import SessionExpired, APIFailure, XSenseError
from .house import House
from .mapping import bool_state
from .station import Station

LOGGER = logging.getLogger(__name__)

CAMERA_TYPES = {"SSC0A", "SSC0B"}
CAMERA_LIVE_URL_MAX_AGE_SECONDS = 240
_CAMERA_VIDEO_RESOLUTIONS = {
    "auto",
    "640x360",
    "640x480",
    "960x720",
    "1280x720",
    "1280x960",
    "1920x1080",
    "2048x1440",
    "2048x1536",
    "2304x1296",
    "2560x1440",
    "3840x2160",
    "7680x4320",
}
_CAMERA_RESOLUTION_ALIASES = {
    "AUTO": "auto",
    "SD": "1280x720",
    "HD": "1920x1080",
    "2K": "2560x1440",
    "360P": "640x360",
    "P360": "640x360",
    "480P": "640x480",
    "P480": "640x480",
    "720P": "1280x720",
    "P720": "1280x720",
    "1080P": "1920x1080",
    "P1080": "1920x1080",
    "1296P": "2304x1296",
    "P1296": "2304x1296",
    "1440P": "2560x1440",
    "P1440": "2560x1440",
    "1536P": "2048x1536",
    "P1536": "2048x1536",
}

CAMERA_AI_NOTIFICATION_TYPES = (
    "person",
    "pet",
    "vehicle_enter",
    "vehicle_out",
    "vehicle_held_up",
    "package_exist",
    "package_drop_off",
    "package_pick_up",
    "other",
)
CAMERA_AI_ASSISTANT_TYPES = ("person", "pet", "vehicle", "package")
_CAMERA_AI_NOTIFICATION_GROUPS = {
    "person": ("person",),
    "pet": ("pet",),
    "vehicle": ("vehicle_enter", "vehicle_out", "vehicle_held_up"),
    "package": ("package_exist", "package_drop_off", "package_pick_up"),
    "other": ("other",),
}
_CAMERA_AI_NOTIFICATION_PAYLOAD_KEYS = {
    "package": "package",
    "person": "person",
    "pet": "pet",
    "vehicle": "vehicle",
    "other": "other",
}
# The Android app reads these standalone Wi-Fi device categories from the
# house-level mainpage/2nd_mainpage shadows, not from station-level mainpage
# shadows. Querying a station-level mainpage for them returns 404 on accounts
# such as #160 and should not fail setup.
_HOUSE_STATE_DEVICE_TYPES = {
    "SC06-WX",
    "SC07-WX",
    "SC07-iA",
    "STH0C",
    "SWS0B",
    "XC04-WX",
    "XC0C-iA",
    "XC0C-iR",
    "XC0M-iR",
    "XP0A-iR",
    "XP0H-iR",
    "XP0J-iA",
    "XP0S-iA",
    "XP0T-iA",
    "XP0V-iA",
    "XP0W-iA",
    "XR0A-iR",
    "XS01-WX",
    "XS03-WX",
    "XS0B-iR",
    "XS0AA-iA",
    "XS0AB-iA",
    "XS0E-iR",
    "XS0R-iA",
}

# The APK uses 2nd_info directly for the newer standalone Wi-Fi CO,
# combined, temperature/humidity, water, and radon families. Wi-Fi smoke
# families still use the legacy info shadow in their settings screens.
_SECOND_INFO_DEVICE_TYPES = {
    "SC06-WX",
    "SC07-WX",
    "SC07-iA",
    "STH0C",
    "SWS0B",
    "XC04-WX",
    "XC0C-iA",
    "XC0C-iR",
    "XC0M-iR",
    "XP0A-iR",
    "XP0H-iR",
    "XP0J-iA",
    "XP0S-iA",
    "XP0T-iA",
    "XP0V-iA",
    "XP0W-iA",
    "XR0A-iR",
}


def _shadow_update_body(data: Dict) -> str:
    """Return compact AWS shadow JSON body kept for integration parity."""
    return shadow_update_body(data)


def _debug_keys(value: Any) -> list[str]:
    """Return sorted mapping keys for debug logs without dumping values."""
    if not isinstance(value, dict):
        return []
    return sorted(str(key) for key in value)


def _debug_data_shape(value: Any) -> dict[str, Any]:
    """Return compact response shape details for debug logs."""
    if isinstance(value, dict):
        shape: dict[str, Any] = {"keys": _debug_keys(value)}
        if isinstance(value.get("list"), list):
            shape["list_count"] = len(value["list"])
        return shape
    if isinstance(value, list):
        return {"list_count": len(value)}
    return {"type": type(value).__name__}


def _station_state_shadow_names(station: Station) -> tuple[str, ...]:
    if station.type in _HOUSE_STATE_DEVICE_TYPES:
        return ()
    if station.type == "SBS10":
        return ("mainpage",)
    if station.type == "SBS50":
        return ("2nd_mainpage",)
    return ()


def _station_info_shadow_names(station: Station) -> tuple[str, ...]:
    if station.type == "SBS10":
        return (f"info_{station.sn}",)
    if station.type == "SBS50" or station.type in _SECOND_INFO_DEVICE_TYPES:
        return (f"2nd_info_{station.sn}",)
    return (f"info_{station.sn}",)


class _ThingShadowTarget:
    def __init__(self, station: Station, shadow_name: str) -> None:
        self.house = station.house
        self.shadow_name = shadow_name


def is_camera_entity(entity: Entity) -> bool:
    """Return if an entity came from the APK camera sources."""
    return (
        getattr(entity, "entity_type", None) == EntityType.CAMERA
        or entity.type in CAMERA_TYPES
    )


def _normalized_camera_serial(value) -> str | None:
    """Return a camera serial in the comparison form used for ADDX matching."""
    if value is None:
        return None
    serial = "".join(char for char in str(value).upper() if char.isalnum())
    return serial or None


def _camera_resolution(value) -> str | None:
    """Return an APK-style camera video resolution value."""
    if value is None:
        return None
    resolution = str(value).strip().replace("VIDEO_SIZE_", "")
    if not resolution:
        return None
    normalized = resolution.replace("×", "x")
    if normalized in _CAMERA_VIDEO_RESOLUTIONS:
        return normalized
    if alias := _CAMERA_RESOLUTION_ALIASES.get(normalized.upper()):
        return alias
    return None


def _camera_webrtc_ticket_valid(ticket: dict) -> bool:
    expiration = ticket.get("expirationTime")
    if expiration in (None, ""):
        return False
    try:
        return int(expiration) > int(datetime.now().timestamp() * 1000)
    except (TypeError, ValueError):
        return False


def _camera_supported_resolutions(camera: Entity) -> list[str]:
    """Return APK-supported camera live resolutions in device order."""
    supported = (
        camera.data.get("supportedRecordingResolutions")
        or camera.data.get("deviceSupportResolution")
        or []
    )
    if isinstance(supported, str):
        supported = [supported]
    elif not isinstance(supported, (list, tuple)):
        return []
    resolutions: list[str] = []
    for value in supported:
        resolution = _camera_resolution(value)
        if resolution and resolution not in resolutions:
            resolutions.append(resolution)
    return resolutions


def camera_live_resolution(camera: Entity) -> str:
    """Return the APK start-live resolution for a camera live-view session."""
    supported_resolutions = _camera_supported_resolutions(camera)
    saved_resolution = _camera_resolution(camera.data.get("liveResolution"))
    if saved_resolution and (
        not supported_resolutions or saved_resolution in supported_resolutions
    ):
        return saved_resolution
    if supported_resolutions:
        return supported_resolutions[0]

    return "auto"


def camera_online(camera: Entity) -> bool:
    """Return whether ADDX currently reports the camera online."""
    online = getattr(camera, "online", None)
    if online is not None:
        return online is True
    return camera.data.get("online") == 1


def camera_stream_protocol(camera: Entity) -> str | None:
    """Return the ADDX stream protocol from the camera device model."""
    protocol = camera.data.get("streamProtocol")
    if protocol is None:
        return None
    return str(protocol).lower()


def stream_source_protocol(source: str | None) -> str | None:
    """Return a stream source URL protocol without exposing the full source URL."""
    if not isinstance(source, str) or "://" not in source:
        return None
    return source.split("://", 1)[0].lower()


def schedule_time(value: str) -> str:
    """Return an APK schedule time in HHMM form."""
    text = str(value).strip()
    if ":" in text:
        hour, minute = text.split(":", 1)
        text = f"{hour.zfill(2)}{minute.zfill(2)}"
    if len(text) != 4 or not text.isdigit():
        raise ValueError("X-Sense schedule time must be HH:MM or HHMM")
    hour = int(text[:2])
    minute = int(text[2:])
    if hour > 23 or minute > 59:
        raise ValueError("X-Sense schedule time is out of range")
    return text


def schedule_week_days(values: list[str]) -> list[str]:
    """Return APK weekday values, where 1 is Sunday and 7 is Saturday."""
    result = [str(value).strip() for value in values]
    if not result:
        raise ValueError("X-Sense schedule must include at least one weekday")
    invalid = [
        value for value in result if value not in {"1", "2", "3", "4", "5", "6", "7"}
    ]
    if invalid:
        raise ValueError("X-Sense schedule weekdays must be 1 through 7")
    return result


def light_schedule_list(value) -> list:
    """Return a normalized schedule list from the APK query response."""
    if isinstance(value, dict):
        data = value.get("schedList") or value.get("schedule") or value.get("list")
        return data if isinstance(data, list) else []
    return value if isinstance(value, list) else []


def light_group_list(value) -> list:
    """Return a normalized group list from the APK query response."""
    if isinstance(value, dict):
        data = value.get("groupList") or value.get("groups") or value.get("list")
        if data is None and isinstance(value.get("reData"), dict):
            data = value["reData"].get("groupList")
        return data if isinstance(data, list) else []
    return value if isinstance(value, list) else []


def non_empty_strings(values: list[str], field_name: str) -> list[str]:
    """Return stripped non-empty strings for API list fields."""
    result = [str(value).strip() for value in values if str(value).strip()]
    if not result:
        raise ValueError(f"X-Sense {field_name} must include at least one ID")
    return result


def typed_option(option: str) -> int | str:
    """Return option as int when the API supplied numeric options."""
    try:
        return int(option)
    except ValueError:
        return option


def comfort_pair(value, default: list[float]) -> list[float]:
    """Return a comfort range pair for APK comfort mode writes."""
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        try:
            return [float(value[0]), float(value[1])]
        except (TypeError, ValueError):
            pass
    return list(default)


def is_native_stream_camera(camera: Entity) -> bool:
    """Return whether the camera advertises a native stream protocol."""
    protocol = camera_stream_protocol(camera)
    if protocol is None:
        return False
    return "rtsp" in protocol or "rtmp" in protocol


def is_webrtc_camera(camera: Entity) -> bool:
    """Return whether the camera should use ADDX WebRTC signaling."""
    protocol = camera_stream_protocol(camera)
    if protocol is None:
        return True
    return "rtsp" not in protocol and "rtmp" not in protocol


class AsyncXSense(XSenseBase):
    def __init__(self, session=None, language: str | None = None):
        super().__init__()
        self.session = session
        self._owns_session = session is None
        self.language = _ipc_language(language)
        self._sbs50_child_info_loaded: set[tuple[str, str]] = set()

    async def _get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
            self._owns_session = True
        return self.session

    async def close(self):
        if self._owns_session and self.session and not self.session.closed:
            await self.session.close()

    async def __aenter__(self):
        await self._get_session()
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        await self.close()

    async def api_call(self, code, unauth=False, **kwargs):
        data = {**kwargs}

        if unauth:
            headers = None
            mac = "abcdefg"
        else:
            if self._access_token_expiring():
                await self.refresh()
            headers = {"Authorization": self.access_token}
            mac = self._calculate_mac(data)

        session = await self._get_session()
        async with session.post(
            f"{self.API}/app",
            json={
                **data,
                "clientType": self.CLIENTYPE,
                "mac": mac,
                "appVersion": self.VERSION,
                "bizCode": code,
                "appCode": self.APPCODE,
            },
            headers=headers,
        ) as response:
            self._lastres = response

            data = await response.json()

            if response.status >= 400:
                LOGGER.debug(
                    "X-Sense API failure context: code=%s status=%s keys=%s",
                    code,
                    response.status,
                    _debug_keys(data),
                )
                message = data.get("message") or "unknown error"
                raise APIFailure(f"API failure: {response.status}/{message}")

            if "reCode" not in data:
                LOGGER.debug(
                    "X-Sense API unexpected response context: code=%s status=%s keys=%s",
                    code,
                    response.status,
                    _debug_keys(data),
                )
                raise APIFailure("API failure: Cannot understand response")

            if data["reCode"] != 200:
                errCode = data.get("errCode", 0)
                LOGGER.debug(
                    "X-Sense API error context: code=%s reCode=%s errCode=%s keys=%s",
                    code,
                    data["reCode"],
                    errCode,
                    _debug_keys(data),
                )
                if errCode in ("10000008", "10000020"):
                    raise SessionExpired(data.get("reMsg"))
                raise APIFailure(
                    f"Request for code {code} failed with error {errCode}/{data['reCode']} {data.get('reMsg')}"
                )
            return data["reData"]

    async def ai_service_call(self, code: str, **kwargs):
        """Call the APK AI-notification service endpoint."""
        if self._access_token_expiring():
            await self.refresh()

        session = await self._get_session()
        async with session.post(
            f"{self.API}/app",
            json=self._signed_body(kwargs, code),
            headers={"Authorization": self.access_token},
        ) as response:
            self._lastres = response
            data = await response.json()

            if response.status >= 400:
                LOGGER.debug(
                    "X-Sense AI service failure context: code=%s status=%s keys=%s",
                    code,
                    response.status,
                    _debug_keys(data),
                )
                message = data.get("message") or data.get("reMsg") or "unknown error"
                raise APIFailure(f"AI service failure: {response.status}/{message}")

            if str(data.get("reCode")) != "200":
                err_code = data.get("errCode", 0)
                LOGGER.debug(
                    "X-Sense AI service error context: code=%s reCode=%s errCode=%s keys=%s",
                    code,
                    data.get("reCode"),
                    err_code,
                    _debug_keys(data),
                )
                if err_code in ("10000008", "10000020"):
                    raise SessionExpired(data.get("reMsg"))
                raise APIFailure(
                    f"AI service request for code {code} failed with error {err_code}/{data.get('reCode')} {data.get('reMsg')}"
                )
            return data.get("reData")

    async def get_ai_service_list(self) -> list[dict]:
        """Return APK AI-notification services for the account."""
        user_id = self.user_id_code or self.userid
        if not user_id:
            return []
        data = await self.ai_service_call("701001", userId=user_id)
        LOGGER.debug(
            "X-Sense AI service list response: %s",
            _debug_data_shape(data),
        )
        return data if isinstance(data, list) else []

    async def get_ai_service_history(
        self, server_id: str, next_token: str | None = None
    ) -> dict:
        """Return APK AI-notification history for a service."""
        payload: dict[str, Any] = {"serverId": server_id}
        if next_token:
            payload["nextToken"] = next_token
        data = await self.ai_service_call("701008", **payload)
        return data if isinstance(data, dict) else {}

    async def get_camera_event_history(
        self,
        serial_numbers: list[str],
        start_timestamp: int,
        end_timestamp: int,
        *,
        start: int = 0,
        limit: int = 20,
    ) -> dict:
        """Return ADDX camera library records using the APK playback path."""
        serials = [str(serial) for serial in serial_numbers if serial]
        if not serials:
            return {}
        data = await self.addx_call(
            "/library/newselectlibrary",
            startTimestamp=start_timestamp,
            endTimestamp=end_timestamp,
            to=limit,
            serialNumber=serials,
            tags=[],
            marked=0,
            **{"from": start},
        )
        LOGGER.debug(
            "X-Sense camera record history response: %s",
            _debug_data_shape(data),
        )
        return data if isinstance(data, dict) else {}

    async def get_camera_event_record_history(
        self,
        serial_numbers: list[str],
        start_timestamp: int,
        end_timestamp: int,
        *,
        start: int = 0,
        limit: int = 20,
        tags: list[str] | None = None,
        video_event: str | None = None,
        doorbell_tags: list[str] | None = None,
        device_call_event_tag: str | None = None,
        serial_number_to_activity_zone: dict[str, list[int]] | None = None,
        missing: int | None = None,
        marked: int | None = 0,
    ) -> dict:
        """Return APK camera event-library records using the event filter path."""
        serials = [str(serial) for serial in serial_numbers if serial]
        if not serials:
            return {}
        payload: dict[str, Any] = {
            "startTimestamp": start_timestamp,
            "endTimestamp": end_timestamp,
            "to": limit,
            "serialNumber": serials,
            "tags": tags or [],
            "from": start,
        }
        if marked is not None:
            payload["marked"] = marked
        if missing is not None:
            payload["missing"] = missing
        if video_event:
            payload["videoEvent"] = video_event
        if doorbell_tags is not None:
            payload["doorbellTags"] = doorbell_tags
        if device_call_event_tag:
            payload["deviceCallEventTag"] = device_call_event_tag
        if serial_number_to_activity_zone:
            payload["serialNumberToActivityZone"] = serial_number_to_activity_zone

        data = await self.addx_call("/library/newselectlibrary/event", **payload)
        LOGGER.debug(
            "X-Sense camera event record history response: %s",
            _debug_data_shape(data),
        )
        return data if isinstance(data, dict) else {}

    async def get_camera_library_by_trace_id(self, trace_id: str) -> dict:
        """Return one APK camera library record by trace id."""
        if not trace_id:
            return {}
        data = await self.addx_call("/library/getLibraryByTraceId", traceId=trace_id)
        LOGGER.debug(
            "X-Sense camera trace record response: %s",
            _debug_data_shape(data),
        )
        return data if isinstance(data, dict) else {}

    async def get_camera_library_by_library_id(self, library_id: str) -> dict:
        """Return one APK camera library record by library id."""
        if not library_id:
            return {}
        data = await self.addx_call("/library/newselectsinglelibrary", traceId=library_id)
        LOGGER.debug(
            "X-Sense camera library record response: %s",
            _debug_data_shape(data),
        )
        return data if isinstance(data, dict) else {}

    async def retrieve_camera_local_videos(
        self, camera: Entity, start_time: int, end_time: int
    ) -> dict:
        """Return APK SD-card video slices for a camera and time window."""
        data = await self.addx_call(
            "/device/retrieveLocalVideos",
            serialNumber=camera.sn,
            startTime=start_time,
            endTime=end_time,
        )
        LOGGER.debug(
            "X-Sense camera local video slices response: %s",
            _debug_data_shape(data),
        )
        return data if isinstance(data, dict) else {}

    async def play_camera_local_video(
        self, camera: Entity, start_time: int, end_time: int
    ) -> str | None:
        """Return the APK local-video playback URL/string for a camera window."""
        data = await self.addx_call(
            "/device/playLocalVideo",
            serialNumber=camera.sn,
            startTime=start_time,
            endTime=end_time,
        )
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            value = data.get("data") or data.get("url") or data.get("videoUrl")
            return str(value) if value else None
        return None

    async def stop_camera_local_video(self, camera: Entity) -> None:
        """Stop APK local-video playback for a camera."""
        await self.addx_call("/device/stopPlayLocalVideo", serialNumber=camera.sn)

    async def query_camera_sd_card_format(self, camera: Entity) -> dict:
        """Return the APK SD-card format status response for a camera."""
        data = await self.addx_call(
            "/device/querySdCardFormat",
            serialNumber=camera.sn,
            queueId=str(camera.sn or ""),
        )
        LOGGER.debug(
            "X-Sense camera SD card format response: %s",
            _debug_data_shape(data),
        )
        return data if isinstance(data, dict) else {}

    async def get_camera_activity_zones(self, camera: Entity) -> dict:
        """Return APK activity zones configured for one camera."""
        data = await self.addx_call("/device/getactivityzone", serialNumber=camera.sn)
        LOGGER.debug(
            "X-Sense camera activity zone response: %s",
            _debug_data_shape(data),
        )
        return data if isinstance(data, dict) else {}

    async def query_user_camera_activity_zones(self) -> dict | list:
        """Return APK account-level camera activity-zone data."""
        data = await self.addx_call("/device/queryUserActivityZone")
        LOGGER.debug(
            "X-Sense camera user activity zone response: %s",
            _debug_data_shape(data),
        )
        return data if isinstance(data, (dict, list)) else {}

    async def get_daily_history(
        self,
        house: House | str,
        day_time: str,
        time_zone: str,
        next_token: str | None = None,
    ) -> dict:
        """Return account daily history using the documented APK endpoint."""
        house_id = house.house_id if hasattr(house, "house_id") else str(house)
        payload: dict[str, Any] = {
            "houseId": house_id,
            "dayTime": day_time,
            "timeZone": time_zone,
        }
        if next_token:
            payload["nextToken"] = next_token
        data = await self.api_call("104001", **payload)
        return data if isinstance(data, dict) else {}

    async def get_monthly_history(
        self,
        house: House | str,
        month: str,
        time_zone: str,
    ) -> dict:
        """Return account monthly history counts using the APK endpoint."""
        house_id = house.house_id if hasattr(house, "house_id") else str(house)
        data = await self.api_call(
            "104006", houseId=house_id, hisMonth=month, timeZone=time_zone
        )
        return data if isinstance(data, dict) else {}

    async def get_station_history(
        self,
        station: Station,
        day_time: str,
        time_zone: str,
        *,
        device: Entity | str | None = None,
        next_token: str | None = None,
    ) -> dict:
        """Return station or device daily history through the APK endpoint."""
        payload: dict[str, Any] = {
            "houseId": station.house.house_id,
            "stationId": station.entity_id,
            "dayTime": day_time,
            "timeZone": time_zone,
        }
        if device is not None:
            payload["deviceId"] = (
                device.entity_id if hasattr(device, "entity_id") else str(device)
            )
        if next_token:
            payload["nextToken"] = next_token
        data = await self.api_call("104007", **payload)
        return data if isinstance(data, dict) else {}

    async def get_station_monthly_history(
        self,
        station: Station,
        month: str,
        time_zone: str,
        *,
        device: Entity | str | None = None,
    ) -> dict:
        """Return station or device monthly history counts through the APK endpoint."""
        payload: dict[str, Any] = {
            "houseId": station.house.house_id,
            "stationId": station.entity_id,
            "hisMonth": month,
            "timeZone": time_zone,
        }
        if device is not None:
            payload["deviceId"] = (
                device.entity_id if hasattr(device, "entity_id") else str(device)
            )
        data = await self.api_call("104008", **payload)
        return data if isinstance(data, dict) else {}

    async def get_co_history_days(
        self,
        station: Station,
        time_zone: str,
        *,
        device: Entity | str | None = None,
    ) -> dict:
        """Return CO history days for a station or child device."""
        payload: dict[str, Any] = {
            "stationId": station.entity_id,
            "timeZone": time_zone,
        }
        code = "104014"
        if device is not None:
            code = "104009"
            payload["deviceId"] = (
                device.entity_id if hasattr(device, "entity_id") else str(device)
            )
        data = await self.api_call(code, **payload)
        return data if isinstance(data, dict) else {}

    async def get_co_history_details(
        self,
        station: Station,
        day_time: str,
        time_zone: str,
        *,
        device: Entity | str | None = None,
    ) -> dict:
        """Return CO PPM readings for a station or child device."""
        payload: dict[str, Any] = {
            "houseId": station.house.house_id,
            "stationId": station.entity_id,
            "dayTime": day_time,
            "timeZone": time_zone,
        }
        code = "104015"
        if device is not None:
            code = "104010"
            payload["deviceId"] = (
                device.entity_id if hasattr(device, "entity_id") else str(device)
            )
        data = await self.api_call(code, **payload)
        return data if isinstance(data, dict) else {}

    async def get_temperature_history(
        self,
        station: Station,
        last_time: str,
        *,
        next_token: str | None = None,
    ) -> dict:
        """Return temperature/humidity chart history through the APK endpoint."""
        payload: dict[str, Any] = {
            "houseId": station.house.house_id,
            "stationId": station.entity_id,
            "lastTime": last_time,
        }
        if next_token:
            payload["nextToken"] = next_token
        data = await self.api_call("104020", **payload)
        return data if isinstance(data, dict) else {}

    async def get_dispatch_history(
        self, server_id: str, next_token: str | None = None
    ) -> dict:
        """Return security dispatch history through the APK endpoint."""
        payload: dict[str, Any] = {"serverId": server_id}
        if next_token:
            payload["nextToken"] = next_token
        data = await self.api_call("505001", **payload)
        return data if isinstance(data, dict) else {}

    async def ipc_call(self, code: str, **kwargs):
        """Call the X-Sense IPC endpoint used by the Android app."""
        if self._access_token_expiring():
            await self.refresh()

        session = await self._get_session()
        async with session.post(
            f"{self.IPC_API}/ipc",
            json=self._signed_body(kwargs, code, ipc=True),
            headers={"Authorization": self.access_token},
        ) as response:
            self._lastres = response
            data = await response.json()

            if response.status >= 400:
                LOGGER.debug(
                    "X-Sense IPC failure context: code=%s status=%s keys=%s",
                    code,
                    response.status,
                    _debug_keys(data),
                )
                message = data.get("message") or data.get("reMsg") or "unknown error"
                raise APIFailure(f"IPC API failure: {response.status}/{message}")

            if str(data.get("reCode")) != "200":
                err_code = data.get("errCode", 0)
                LOGGER.debug(
                    "X-Sense IPC error context: code=%s reCode=%s errCode=%s keys=%s",
                    code,
                    data.get("reCode"),
                    err_code,
                    _debug_keys(data),
                )
                if err_code in ("10000008", "10000020"):
                    raise SessionExpired(data.get("reMsg"))
                raise APIFailure(
                    f"Request for IPC code {code} failed with error {err_code}/{data.get('reCode')} {data.get('reMsg')}"
                )
            return data.get("reData")

    async def addx_call(self, endpoint: str, *, _retry: bool = True, **kwargs):
        """Call the ADDX camera API after the IPC endpoint has issued a token."""
        if self._addx_session is None:
            self._addx_session = await self.register_ipc()

        addx_session = self._addx_session
        node = addx_session.get("nodeType")
        base_url = self.ADDX_API_BY_NODE.get(node)
        if base_url is None:
            raise APIFailure(f"Unknown ADDX nodeType: {node}")
        data = self._addx_body(addx_session, kwargs)

        session = await self._get_session()
        async with session.post(
            f"{base_url}{endpoint}",
            json=data,
            headers={
                "Authorization": addx_session["token"],
                "Content-Type": "application/json",
            },
        ) as response:
            self._lastres = response
            result = await response.json()

            if response.status >= 400:
                LOGGER.debug(
                    "X-Sense ADDX failure context: endpoint=%s status=%s node=%s keys=%s data_shape=%s",
                    endpoint,
                    response.status,
                    node,
                    _debug_keys(result),
                    _debug_data_shape(result.get("data")),
                )
                if response.status in (401, 403) and _retry:
                    self._addx_session = None
                    self._addx_session = await self.register_ipc()
                    return await self.addx_call(endpoint, _retry=False, **kwargs)
                message = result.get("msg") or result.get("message") or "unknown error"
                raise APIFailure(f"ADDX API failure: {response.status}/{message}")

            if result.get("result") not in (0, None):
                LOGGER.debug(
                    "X-Sense ADDX error context: endpoint=%s result=%s node=%s keys=%s data_shape=%s",
                    endpoint,
                    result.get("result"),
                    node,
                    _debug_keys(result),
                    _debug_data_shape(result.get("data")),
                )
                if result.get("result") == -1024 and _retry:
                    self._addx_session = None
                    self._addx_session = await self.register_ipc()
                    return await self.addx_call(endpoint, _retry=False, **kwargs)
                raise APIFailure(
                    f"ADDX request for {endpoint} failed with error {result.get('result')}/{result.get('msg')}"
                )
            return result.get("data")

    def _addx_body(self, addx_session: dict, data: Dict | None = None) -> Dict:
        """Return the ADDX request body shape used by the Android SDK."""
        result = dict(data or {})
        country = addx_session.get("countryNo")
        if not country:
            raise APIFailure("Missing ADDX countryNo from IPC registration")
        language = addx_session.get("language")
        if not language:
            raise APIFailure("Missing ADDX language from IPC registration")
        result["countryNo"] = country
        result["language"] = language
        result["app"] = {
            "appName": self.ADDX_APP_NAME,
            "appType": "Android",
            "bundle": self.ADDX_APP_BUNDLE,
            "channelId": self.ADDX_APP_CHANNEL_ID,
            "countlyId": self.ADDX_APP_COUNTLY_ID,
            "tenantId": self.ADDX_APP_TENANT_ID,
            "version": self.ADDX_APP_VERSION,
            "versionName": self.ADDX_APP_VERSION_NAME,
        }
        return result

    async def get_house(self, house: House, page: str, *, _retry: bool = True):
        if self._aws_token_expiring():
            await self.load_aws()

        url, headers = self._house_request(house, page)

        session = await self._get_session()
        async with session.get(url, headers=headers) as response:
            self._lastres = response
            if response.status in (401, 403) and _retry:
                await self.load_aws()
                return await self.get_house(house, page, _retry=False)
            return await response.json()

    async def get_thing(self, station: Station, page: str, *, _retry: bool = True):
        if self._aws_token_expiring():
            await self.load_aws()

        url, headers = self._thing_request(station, page)

        session = await self._get_session()
        async with session.get(url, headers=headers) as response:
            self._lastres = response
            if response.status in (401, 403) and _retry:
                await self.load_aws()
                return await self.get_thing(station, page, _retry=False)
            return await response.json()

    async def do_thing(
        self, station: Station, page: str, data: Dict, *, _retry: bool = True
    ):
        if self._aws_token_expiring():
            await self.load_aws()

        body = shadow_update_body(data)
        url, headers = self._thing_request(station, page, body)

        session = await self._get_session()
        async with session.post(url, data=body, headers=headers) as response:
            self._lastres = response
            if (
                response.status in (401, 403)
                and _retry
                and self.signer is not None
                and self.aws_access_expiry is not None
            ):
                await self.load_aws()
                return await self.do_thing(station, page, data, _retry=False)
            if response.status >= 400:
                text = await response.text()
                raise APIFailure(
                    f"Unable to update thing shadow: {response.status}/{text}"
                )
            return await response.json()

    async def login(self, username, password):
        await asyncio.get_running_loop().run_in_executor(
            None, self._cognito_login, username, password
        )
        await self.load_aws()

    async def refresh(self):
        url, data, headers = self._refresh_request()
        session = await self._get_session()
        async with session.post(url, json=data, headers=headers) as response:
            self._lastres = response
            text = await response.text()
            data = json.loads(text)

            if response.status == 400:
                raise SessionExpired(data.get("message", "token refresh failed"))

            self._parse_refresh_result(data.get("AuthenticationResult", {}))

    async def init(self):
        await self.get_client_info()

    async def load_aws(self):
        await self.get_aws_tokens()
        if self.signer:
            self.signer.update(
                self.aws_access_key, self.aws_secret_access_key, self.aws_session_token
            )
        else:
            self.signer = AWSSigner(
                self.aws_access_key, self.aws_secret_access_key, self.aws_session_token
            )

    async def load_all(self):
        result = {}
        for i in await self.get_houses():
            h = House(
                self.signer,
                i["houseId"],
                i["houseName"],
                i["houseRegion"],
                i["mqttRegion"],
                i["mqttServer"],
            )
            result[i["houseId"]] = h

            if rooms := await self.get_rooms(h.house_id):
                h.set_rooms(rooms)

            if stations := await self.get_stations(h.house_id):
                h.set_stations(stations)

        self.houses = result

    async def register_ipc(self):
        """Register with X-Sense IPC and receive the ADDX camera token."""
        if not self.houses:
            raise APIFailure("Cannot register IPC without an X-Sense house")
        house = next(iter(self.houses.values()))
        node_type = _ipc_node_type(house.mqtt_region)
        return await self.ipc_call(
            "C10101",
            userName=self.username,
            nodeType=node_type,
            language=self.language,
        )

    async def update_camera_data(self):
        """Merge camera metadata and config from the Android app ADDX API."""
        data = await self.addx_call("/device/listuserdevices")
        devices = [
            device
            for device in (data or {}).get("list") or []
            if _normalized_camera_serial(device.get("serialNumber"))
        ]
        if not devices:
            return

        cameras = []
        for device in devices:
            camera = self._camera_from_addx_device(device)
            if camera is not None:
                cameras.append((camera, device))
        if not cameras:
            return

        for camera, addx_device in cameras:
            camera.set_data(_camera_data(addx_device))
            try:
                config = await self.addx_call(
                    "/device/getuserconfig",
                    serialNumber=camera.sn,
                    voiceReminder=False,
                )
            except APIFailure:
                config = None
            if config:
                camera.set_data(_camera_config_data(config))

            try:
                setting_options = await self.addx_call(
                    "/user/getFormOptions",
                    serialNumber=camera.sn,
                )
            except APIFailure:
                setting_options = None
            if setting_options:
                camera.set_data(_camera_settings_options_data(setting_options))
                LOGGER.debug(
                    "X-Sense camera form options loaded: %s",
                    _camera_options_debug_context(camera),
                )

            if (
                any(
                    camera.data.get(key) is not False
                    for key in (
                        "supportLiveAudio",
                        "supportLiveSpeakerVolume",
                        "supportRecordingAudio",
                    )
                )
                or camera.data.get("supportMechanicalDingDong") is True
            ):
                try:
                    audio = await self.addx_call(
                        "/device/config/querydeviceaudio",
                        serialNumber=camera.sn,
                    )
                except APIFailure:
                    audio = None
                if audio:
                    camera.set_data(_camera_audio_data(audio))

            if camera.data.get("supportDoorBellAlarm"):
                try:
                    doorbell = await self.addx_call(
                        "/device/config/querydoorbellconfig",
                        serialNumber=camera.sn,
                    )
                except APIFailure:
                    doorbell = None
                if doorbell:
                    camera.set_data(_camera_doorbell_data(doorbell))

            if camera.data.get("supportPersonDetect") is not False:
                try:
                    notification_settings = await self.addx_call(
                        "/device/queryMessageNotification/v1",
                        serialNumber=camera.sn,
                        userId=self.userid,
                    )
                except APIFailure:
                    notification_settings = None
                if notification_settings:
                    camera.set_data(
                        _camera_ai_notification_data(notification_settings)
                    )

                try:
                    ai_event_settings = await self.addx_call(
                        "/aiAssist/queryEventObjectSwitch",
                        isAll=False,
                        serialNumbers=[camera.sn],
                    )
                except APIFailure:
                    ai_event_settings = None
                if ai_event_settings:
                    camera.set_data(
                        _camera_ai_assistant_data(ai_event_settings, camera.sn)
                    )

    async def get_camera_thumbnail(self, camera: Entity) -> bytes | None:
        """Return the latest camera thumbnail bytes from the APK thumbnail URL."""
        thumbnail_url = camera.data.get("thumbImgUrl")
        if not thumbnail_url:
            return None

        session = await self._get_session()
        async with session.get(thumbnail_url) as response:
            self._lastres = response
            if response.status >= 400:
                return None
            return await response.read()

    def _camera_from_addx_device(self, data: Dict) -> Station | None:
        """Return the X-Sense camera entity backed by an ADDX DeviceBean."""
        serial = data.get("serialNumber")
        normalized_serial = _normalized_camera_serial(serial)
        if normalized_serial is None:
            return None

        for house in self.houses.values():
            for station in house.stations.values():
                if (
                    is_camera_entity(station)
                    and _normalized_camera_serial(station.sn) == normalized_serial
                ):
                    camera_type = _camera_type(data)
                    if camera_type:
                        station.type = camera_type
                    if data.get("deviceName"):
                        station.name = data["deviceName"]
                    return station

        device_house_id = data.get("houseId")
        if device_house_id in (None, ""):
            target_houses = list(self.houses.values())
        else:
            target_houses = [
                house
                for house in self.houses.values()
                if str(device_house_id) == str(house.house_id)
            ]
            if not target_houses and len(self.houses) == 1:
                target_houses = list(self.houses.values())

        if len(target_houses) != 1:
            return None

        house = target_houses[0]
        station_id = str(serial)
        camera_type = _camera_type(data)
        station = Station(
            house,
            stationId=station_id,
            stationSn=serial,
            stationName=data.get("deviceName")
            or data.get("displayModelNo")
            or station_id,
            category=camera_type,
            deviceType=camera_type,
            onLine=data.get("online"),
            devices=[],
        )
        station.entity_type = EntityType.CAMERA
        station.set_devices({"devices": []})
        house.stations[station.entity_id] = station
        return station

    async def update_camera_config(self, camera: Entity, **updates):
        """Write camera user config through the Android app endpoint."""
        payload = _camera_user_config_payload(camera, updates)
        LOGGER.debug(
            "X-Sense camera config update: %s",
            _camera_write_debug_context(camera, "/device/updateuserconfig", updates),
        )
        await self.addx_call("/device/updateuserconfig", **payload)
        camera.set_data(updates)

    async def update_camera_audio(self, camera: Entity, **updates):
        """Write camera audio config through the Android app endpoint."""
        device_audio = {
            key: camera.data.get(key)
            for key in (
                "doorBellRingKey",
                "liveAudioToggleOn",
                "liveSpeakerVolume",
                "recordingAudioToggleOn",
            )
            if camera.data.get(key) is not None
        }
        device_audio.update(
            {key: value for key, value in updates.items() if value is not None}
        )
        LOGGER.debug(
            "X-Sense camera config update: %s",
            _camera_write_debug_context(
                camera, "/device/config/updatedeviceaudio", updates
            ),
        )
        await self.addx_call(
            "/device/config/updatedeviceaudio",
            serialNumber=camera.sn,
            deviceAudio=device_audio,
        )
        camera.set_data(updates)

    async def update_camera_recording_resolution(
        self, camera: Entity, resolution: str
    ) -> None:
        """Write camera recording resolution through the Android app endpoint."""
        LOGGER.debug(
            "X-Sense camera config update: %s",
            _camera_write_debug_context(
                camera, "/device/updaterecresolution", {"recResolution": resolution}
            ),
        )
        await self.addx_call(
            "/device/updaterecresolution",
            serialNumber=camera.sn,
            recResolution=resolution,
        )
        camera.set_data({"recResolution": resolution})

    async def update_camera_default_codec(self, camera: Entity, codec: str) -> None:
        """Write the default camera codec through the Android app endpoint."""
        LOGGER.debug(
            "X-Sense camera config update: %s",
            _camera_write_debug_context(
                camera, "/device/config/updatedefaultcodec", {"defaultCodec": codec}
            ),
        )
        await self.addx_call(
            "/device/config/updatedefaultcodec",
            serialNumber=camera.sn,
            defaultCodec=codec,
        )
        camera.set_data({"defaultCodec": codec})

    async def update_camera_cooldown(
        self, camera: Entity, *, user_enable: bool, value: int
    ) -> None:
        """Write camera cooldown through the Android app cooldown endpoint."""
        LOGGER.debug(
            "X-Sense camera config update: %s",
            _camera_write_debug_context(
                camera,
                "/device/updateCooldown",
                {"cooldown.userEnable": user_enable, "cooldown.value": value},
            ),
        )
        await self.addx_call(
            "/device/updateCooldown",
            serialNumber=camera.sn,
            cooldown={"userEnable": user_enable, "value": value},
        )
        camera.set_data({"cooldownEnabled": user_enable, "cooldownValue": value})

    async def get_camera_webrtc_ticket(
        self, camera: Entity, *, force_refresh: bool = False
    ) -> dict | None:
        """Return an APK WebRTC ticket, reusing it until it is near expiry."""
        cached = camera.data.get("cameraWebrtcTicket")
        if (
            not force_refresh
            and isinstance(cached, dict)
            and _camera_webrtc_ticket_valid(cached)
        ):
            return cached

        data = await self.addx_call(
            "/device/getWebrtcTicket",
            serialNumber=camera.sn,
            verifyDormancyStatus=True,
        )
        if isinstance(data, dict):
            camera.set_data({"cameraWebrtcTicket": data})
            return data
        return None

    async def start_camera_live(self, camera: Entity) -> str | None:
        """Return the direct live URL from the ADDX start-live endpoint."""
        live_started_at = camera.data.get("cameraLiveStartedAt")
        if (
            (camera_live_url := camera.data.get("cameraLiveUrl"))
            and isinstance(live_started_at, datetime)
            and (datetime.now() - live_started_at).total_seconds()
            < CAMERA_LIVE_URL_MAX_AGE_SECONDS
        ):
            return camera_live_url

        data = await self.addx_call(
            "/device/newstartlive",
            serialNumber=camera.sn,
            liveResolution=camera_live_resolution(camera),
        )
        if isinstance(data, dict):
            live_url = _camera_live_url(data)
            camera.set_data(
                {
                    "cameraAudioUrl": data.get("audioUrl"),
                    "cameraLiveId": data.get("liveId"),
                    "cameraLiveStartedAt": datetime.now(),
                    "cameraLiveUrl": live_url,
                    "cameraLiveProtocol": _url_scheme(live_url),
                }
            )
            return live_url
        return None

    async def keep_camera_live_alive(self, camera: Entity) -> None:
        """Send the APK camera live-view keepalive request."""
        await self.addx_call(
            "/device/keepalive", serialNumber=camera.sn, seconds=30
        )

    async def stop_camera_live(self, camera: Entity) -> None:
        """Stop camera live view through the Android app endpoint."""
        try:
            await self.addx_call("/device/stoplive", serialNumber=camera.sn)
        finally:
            camera.set_data(
                {
                    "cameraAudioUrl": None,
                    "cameraLiveId": None,
                    "cameraLiveStartedAt": None,
                    "cameraLiveUrl": None,
                    "cameraLiveProtocol": None,
                    "cameraWebrtcTicket": None,
                }
            )

    async def wake_camera(self, camera: Entity) -> None:
        """Wake a sleeping camera through the Android app endpoint."""
        await self.addx_call("/device/wakeupDevice", serialNumber=camera.sn)

    async def update_camera_sleep(self, camera: Entity, enabled: bool) -> None:
        """Write camera dormancy through the Android app endpoint."""
        LOGGER.debug(
            "X-Sense camera config update: %s",
            _camera_write_debug_context(
                camera, "/device/dormancy/switch", {"dormancySwitch": enabled}
            ),
        )
        await self.addx_call(
            "/device/dormancy/switch",
            serialNumber=camera.sn,
            dormancySwitch=1 if enabled else 0,
        )

    async def update_camera_doorbell_config(self, camera: Entity, **updates) -> None:
        """Write doorbell config through the Android app endpoint."""
        doorbell_config = {
            "alarmWhenRemoveToggleOn": camera.data.get("alarmWhenRemoveToggleOn")
        }
        doorbell_config.update(updates)
        LOGGER.debug(
            "X-Sense camera config update: %s",
            _camera_write_debug_context(
                camera, "/device/config/updatedoorbellconfig", updates
            ),
        )
        await self.addx_call(
            "/device/config/updatedoorbellconfig",
            serialNumber=camera.sn,
            doorbellConfig=doorbell_config,
        )
        camera.set_data(updates)

    async def update_camera_ai_notification(
        self, camera: Entity, event_object: str, enabled: bool
    ) -> None:
        """Write camera AI notification category settings through the app endpoint."""
        current = _camera_ai_notification_enabled(camera.data)
        if enabled:
            current.add(event_object)
        else:
            current.discard(event_object)
        payload = _camera_ai_notification_payload(current)
        LOGGER.debug(
            "X-Sense camera config update: %s",
            _camera_write_debug_context(
                camera,
                "/device/updateMessageNotification/v1",
                {f"aiNotification.{event_object}": enabled},
            ),
        )
        await self.addx_call(
            "/device/updateMessageNotification/v1",
            serialNumber=camera.sn,
            eventObjectType=payload,
        )
        camera.set_data(_camera_ai_notification_state_data(current))

    async def update_camera_ai_assistant(
        self, camera: Entity, event_object: str, enabled: bool
    ) -> None:
        """Write camera AI assistant object switch through the app endpoint."""
        LOGGER.debug(
            "X-Sense camera config update: %s",
            _camera_write_debug_context(
                camera,
                "/aiAssist/updateEventObjectSwitch",
                {f"aiAssistant.{event_object}": enabled},
            ),
        )
        await self.addx_call(
            "/aiAssist/updateEventObjectSwitch",
            serialNumber=camera.sn,
            list=[{"checked": enabled, "eventObject": event_object}],
        )
        camera.set_data({_camera_ai_assistant_key(event_object): enabled})

    async def get_client_info(self):
        data = await self.api_call("101001", unauth=True)
        self.clientid = data["clientId"]
        self.clientsecret = self._decode_secret(data["clientSecret"])
        self.region = data["cgtRegion"]
        self.userpool = data["userPoolId"]

    async def get_aws_tokens(self):
        data = await self.api_call("101003", userName=self.username)
        self.aws_access_key = data["accessKeyId"]
        self.aws_secret_access_key = data["secretAccessKey"]
        self.aws_session_token = data["sessionToken"]
        self.aws_access_expiry = datetime.strptime(
            data["expiration"], "%Y-%m-%d %H:%M:%S%z"
        )

    async def get_houses(self):
        params = {"utctimestamp": "0"}
        return await self.api_call("102007", **params)

    async def get_rooms(self, houseId: str):
        params = {"houseId": houseId, "utctimestamp": "0"}
        return await self.api_call("102008", **params)

    async def get_stations(self, houseId: str):
        params = {"houseId": houseId, "utctimestamp": "0"}
        return await self.api_call("103007", **params)

    async def get_house_state(self, house: House):
        for page in ("mainpage", "2nd_mainpage"):
            res = await self.get_house(house, page)

            if self._lastres.status == 404:
                continue

            if "reported" in res.get("state", {}):
                self._parse_get_house_state(house, res["state"]["reported"])
            # else:
            #     text = await self._lastres.text()
            #     raise APIFailure(f'Unable to retrieve house data: {self._lastres.status}/{text}')

    async def get_alarm_state(self, station: Station):
        res = await self.get_thing(station, "2nd_safemode")
        if self._lastres.status == 404:
            return

        if "reported" in res.get("state", {}):
            station.set_alarm_data(res["state"]["reported"])

    async def get_station_state(self, station: Station):
        for page in _station_info_shadow_names(station):
            res = await self.get_thing(station, page)

            if self._lastres.status == 404:
                continue

            if "reported" in res.get("state", {}):
                station.set_data(res["state"]["reported"])
                return

            text = await self._lastres.text()
            raise APIFailure(
                f"Unable to retrieve station data: {self._lastres.status}/{text}"
            )

    async def get_state(self, station: Station):
        for page in _station_state_shadow_names(station):
            res = await self.get_thing(station, page)

            if self._lastres.status == 404:
                return

            if "reported" in res.get("state", {}):
                self.parse_get_state(station, res["state"]["reported"])
                await self._get_sbs50_child_info_state(station)
                return

            text = await self._lastres.text()
            raise APIFailure(
                f"Unable to retrieve station data: {self._lastres.status}/{text}"
            )

    async def _get_sbs50_child_info_state(self, station: Station) -> None:
        """Merge optional APK per-device info shadows for SBS50 children."""
        if station.type != "SBS50":
            return
        for device in getattr(station, "devices", {}).values():
            if not getattr(device, "sn", None):
                continue
            info_key = (station.sn, device.sn)
            if info_key in self._sbs50_child_info_loaded:
                continue
            target = _ThingShadowTarget(station, f"SBS50{station.sn}")
            page = f"2nd_info_{device.sn}"
            try:
                res = await self.get_thing(target, page)
                if self._lastres.status == 404:
                    self._sbs50_child_info_loaded.add(info_key)
                    continue
                if "reported" in res.get("state", {}):
                    device.set_data(res["state"]["reported"])
                    self._sbs50_child_info_loaded.add(info_key)
                    continue
                text = await self._lastres.text()
                LOGGER.debug(
                    "X-Sense SBS50 child info shadow ignored: %s",
                    {
                        "station": station.type,
                        "device": device.type,
                        "page": page,
                        "status": self._lastres.status,
                        "response": text,
                    },
                )
            except Exception as ex:  # noqa: BLE001
                LOGGER.debug(
                    "X-Sense SBS50 child info shadow failed: %s",
                    {
                        "station": station.type,
                        "device": device.type,
                        "page": page,
                        "error": str(ex),
                    },
                )

    async def set_state(
        self, entity: Entity, shadow: str, topic: str, definition: Dict
    ):
        station = getattr(entity, "station", entity)
        target = definition.get("target")
        if callable(target):
            target = target(entity)
        if target is None:
            target = station

        desired = {
            "deviceSN": entity.sn,
            "shadow": shadow,
            "stationSN": station.sn,
            "userId": self.userid,
        }
        if timestamp := _action_timestamp(definition, entity):
            desired["time"] = timestamp
        extra = definition.get("extra", {})
        if callable(extra):
            extra = extra(entity)
        extra = {
            key: value(entity) if callable(value) else value
            for key, value in extra.items()
        }
        desired.update(extra)
        action_data = definition.get("data", {})
        if callable(action_data):
            action_data = action_data(entity)
        desired.update(action_data)

        data = {"state": {"desired": desired}}
        LOGGER.debug(
            "X-Sense action shadow update: %s",
            _action_debug_context(
                entity, definition.get("action"), target, topic, desired
            ),
        )

        return await self.do_thing(target, topic, data)

    def _station_for_entity(self, entity: Entity) -> Station:
        station = getattr(entity, "station", entity)
        if not getattr(station, "sn", None):
            raise XSenseError("Entity is not associated with a station")
        return station

    def _validate_volume(self, volume: int) -> None:
        if not isinstance(volume, int):
            raise XSenseError("Volume must be an integer")
        if volume < 0 or volume > 100:
            raise XSenseError("Volume must be between 0 and 100")

    def _bool_value(self, value) -> str:
        if isinstance(value, bool):
            return "1" if value else "0"
        if value in (0, 1, "0", "1"):
            return str(value)
        raise XSenseError("Value must be a boolean or 0/1")

    def _utc_timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    def build_command_state(
        self,
        entity: Entity,
        shadow: str,
        values: Dict,
        include_device: bool | None = None,
        include_time: bool = True,
        include_user: bool = True,
    ):
        """Return the app-style desired shadow payload for command helpers."""
        station = self._station_for_entity(entity)
        if include_device is None:
            include_device = entity is not station

        desired = {
            "shadow": shadow,
            "stationSN": station.sn,
        }
        if include_device:
            desired["deviceSN"] = entity.sn
        if include_time:
            desired["time"] = self._utc_timestamp()
        if include_user:
            desired["userId"] = self.userid
        desired.update({key: value for key, value in values.items() if value is not None})
        return station, {"state": {"desired": desired}}

    def build_config_state(self, entity: Entity, shadow: str, values: Dict):
        """Return an app-style config shadow payload without time/user fields."""
        return self.build_command_state(
            entity, shadow, values, include_time=False, include_user=False
        )

    def build_desired_state(self, entity: Entity, shadow: str, definition: Dict):
        """Return an app-style action payload for a mapped action definition."""
        extra = definition.get("extra", {})
        if callable(extra):
            extra = extra(entity)
        data = definition.get("data", {})
        if callable(data):
            data = data(entity)
        values = {**extra, **data}
        return self.build_command_state(entity, shadow, values)

    async def set_device_config(self, entity: Entity, **values):
        """Write raw device config values through the APK config shadow."""
        shadow = "infoBase" if isinstance(entity, Station) else "infoDev"
        station, data = self.build_config_state(entity, shadow, values)
        return await self.do_thing(station, f"2nd_cfg_{entity.sn}", data)

    async def set_alarm_volume(
        self,
        entity: Entity,
        volume: int,
        alarm_tone: str | None = None,
        mute: str | None = None,
    ):
        """Write alarm volume/tone values through the APK config shadow."""
        self._validate_volume(volume)
        values = {"alarmVol": str(volume)}
        if alarm_tone is not None:
            values["alarmTone"] = alarm_tone
        if mute is not None:
            values["mute"] = mute
        shadow = "infoBase" if isinstance(entity, Station) else "infoDev"
        station, data = self.build_config_state(entity, shadow, values)
        return await self.do_thing(station, f"2nd_cfg_{entity.sn}", data)

    async def set_voice_volume(self, station: Station, volume: int):
        """Write station voice volume through the APK config shadow."""
        self._validate_volume(volume)
        station, data = self.build_config_state(
            station, "infoBase", {"voiceVol": str(volume)}
        )
        return await self.do_thing(station, f"2nd_cfg_{station.sn}", data)

    async def set_station_mode(
        self, station: Station, safe_mode: str, force_arm: str | None = None
    ):
        """Write station arm/disarm safe mode through the APK app-mode shadow."""
        values = {
            "userParam": "source=1",
            "source": "1",
            "safeMode": safe_mode,
        }
        if force_arm is not None:
            values["forceArm"] = force_arm
        station, data = self.build_command_state(
            station,
            "appMode",
            values,
            include_device=False,
            include_time=False,
        )
        return await self.do_thing(station, "2nd_appmode", data)

    async def trigger_sos(self, station: Station, sos_type: str = "1"):
        """Trigger station SOS through the APK shadow command."""
        station, data = self.build_command_state(
            station,
            "sosDown",
            {"userParam": "source=1", "sosType": sos_type},
            include_device=False,
        )
        return await self.do_thing(station, "2nd_sosdown", data)

    async def cancel_sos(self, station: Station):
        """Cancel station SOS through the APK shadow command."""
        station, data = self.build_command_state(
            station, "sosDown", {"sosStatus": "0"}, include_device=False
        )
        return await self.do_thing(station, "sosdown", data)

    async def cancel_alarm(self, station: Station):
        """Cancel an active station alarm through the APK shadow command."""
        station, data = self.build_command_state(
            station,
            "alarmCancel",
            {"cancelTime": self._utc_timestamp()},
            include_device=False,
            include_time=False,
        )
        return await self.do_thing(station, "alarmcancel", data)

    async def set_fire_drill(
        self,
        entity: Entity,
        drill: bool | str = True,
        drill_time: str | None = None,
        alarm_type: str | None = None,
        alarm_vol: str | None = None,
        alarm_tone: str | None = None,
        location: str | None = None,
        stop_reason: str | None = None,
    ):
        """Write fire-drill command values through the APK shadow."""
        values = {
            "drill": self._bool_value(drill),
            "drillTime": drill_time,
            "alarmType": alarm_type,
            "alarmVol": alarm_vol,
            "alarmTone": alarm_tone,
            "location": location,
            "stopReason": stop_reason,
        }
        if not isinstance(entity, Station):
            values["deviceType"] = entity.type
        station, data = self.build_command_state(
            entity,
            "appFireDrill",
            values,
            include_device=not isinstance(entity, Station),
        )
        return await self.do_thing(station, "2nd_firedrill", data)

    async def set_sos_sound(self, station: Station, sos_sound: str):
        """Write station SOS sound through the APK shadow command."""
        station, data = self.build_command_state(
            station,
            "sosParam",
            {"userParam": "source=1", "sosSound": sos_sound},
            include_device=False,
        )
        return await self.do_thing(station, "2nd_sosparam", data)

    async def activate_device(self, entity: Entity):
        """Activate a device through the APK activation shadow."""
        station, data = self.build_command_state(
            entity, "app2ndActivate", {"activate": "1"}, include_device=True
        )
        return await self.do_thing(station, "2nd_appactivate", data)

    async def set_install_guide_test(
        self,
        entity: Entity,
        active: bool | str = True,
        dev_type: str | None = None,
        test_time: str = "180",
        detc_sens: str | None = None,
    ):
        """Write install-guide test values through the APK shadow."""
        values = {
            "devType": dev_type or entity.type,
            "test": self._bool_value(active),
            "testTime": test_time,
            "detcSens": detc_sens,
        }
        station, data = self.build_command_state(
            entity, "appInstallGuide", values, include_device=True
        )
        return await self.do_thing(station, "2nd_appinstallguide", data)

    async def signal_test(
        self,
        entity: Entity,
        dev_type: str | None = None,
        test: bool | str = True,
        test_time: str = "5",
    ):
        """Write RF signal-test values through the APK shadow."""
        station, data = self.build_command_state(
            entity,
            "signalTest",
            {
                "devType": dev_type or entity.type,
                "test": self._bool_value(test),
                "testTime": test_time,
            },
            include_device=True,
        )
        return await self.do_thing(station, f"2nd_signaltest_{entity.sn}", data)

    async def set_motion_test(
        self, entity: Entity, active: bool | str = True, dev_type: str = "SMS01"
    ):
        """Write motion-test values through the APK shadow."""
        station, data = self.build_command_state(
            entity,
            "testIR",
            {"devType": dev_type, "testIR": self._bool_value(active)},
            include_device=True,
            include_time=False,
            include_user=False,
        )
        return await self.do_thing(station, "testir", data)

    async def set_light_power(self, entity: Entity, on: bool | str):
        """Compatibility wrapper for the APK light power command."""
        return await self.update_light_power(entity, self._bool_value(on) == "1")

    async def set_light_group_power(
        self,
        station: Station,
        group_id: str,
        device_sns: list[str],
        on: bool | str,
        timeout: str = "180",
    ):
        """Write light group power through the APK group shadow."""
        station, data = self.build_command_state(
            station,
            "groupLampPower",
            {
                "userParam": "source=1",
                "timeOut": timeout,
                "groupId": group_id,
                "devs": device_sns,
                "isOn": self._bool_value(on),
            },
            include_device=False,
        )
        return await self.do_thing(station, "2nd_grouppower", data)

    async def mute_water(
        self,
        entity: Entity,
        set_type: str = "0",
        silence_time: str = "",
        trigger_source: str | None = None,
    ):
        """Write water-alarm mute values through the APK shadow."""
        values = {
            "setType": set_type,
            "silenceTime": silence_time,
            "triggerSource": trigger_source,
        }
        station, data = self.build_command_state(
            entity, "appWater", values, include_device=True
        )
        return await self.do_thing(station, "2nd_appwater", data)

    async def mute_temperature_humidity(
        self, entity: Entity, mute_type: str = "1", sensor_type: str | None = None
    ):
        """Write temperature/humidity mute values through the APK shadow."""
        station, data = self.build_command_state(
            entity,
            "extendMute",
            {"muteType": mute_type, "type": sensor_type or entity.type},
            include_device=True,
        )
        return await self.do_thing(station, "2nd_appmute", data)

    async def mute_driveway(
        self, entity: Entity, mute: bool | str = True, topic: str = "2nd_driveway"
    ):
        """Write driveway alarm mute values through the APK shadow."""
        station, data = self.build_command_state(
            entity,
            "appDriveway",
            {"mute": self._bool_value(mute)},
            include_device=True,
        )
        return await self.do_thing(station, topic, data)

    async def update_light_power(self, entity: Entity, enabled: bool):
        """Write an SBS50 light power change through the app light shadows."""
        station = getattr(entity, "station", entity)
        desired = {
            "isOn": "1" if enabled else "0",
            "time": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
            "userId": self.userid,
            "userParam": "source=1",
        }
        if entity.type == "group-L":
            desired.update(
                {
                    "devs": entity.data.get("devs") or [],
                    "groupId": entity.data.get("groupId"),
                    "shadow": "groupLampPower",
                    "stationSN": station.sn,
                    "timeOut": "180",
                }
            )
            return await self.do_thing(
                station, "2nd_grouppower", {"state": {"desired": desired}}
            )

        desired.update(
            {
                "dev": entity.sn,
                "shadow": "lampPower",
                "stationSN": station.sn,
            }
        )
        return await self.do_thing(
            station, "2nd_lamppower", {"state": {"desired": desired}}
        )

    async def update_shadow_volume(self, entity: Entity, data_key: str, value: int):
        """Write a volume value through the same settings shadow as the app."""
        return await self.update_shadow_setting(entity, data_key, value)

    async def update_radon_unit(self, entity: Entity, radon_unit: str):
        """Write the XR0A-iR display units through the APK REST operation."""
        station = getattr(entity, "station", entity)
        if not getattr(station, "entity_id", None) or not getattr(station, "sn", None):
            raise APIFailure("X-Sense radon unit update requires station identity")
        return await self.api_call(
            "104115",
            stationId=station.entity_id,
            stationSn=station.sn,
            tempUnit=str(entity.data.get("tempUnit", "1")),
            radonUnit=str(radon_unit),
        )

    async def update_radon_thresholds(
        self, entity: Entity, *, min_radon: int, max_radon: int
    ):
        """Write the paired XR0A-iR thresholds through the APK REST operation."""
        station = getattr(entity, "station", entity)
        if not getattr(station, "entity_id", None) or not getattr(station, "sn", None):
            raise APIFailure("X-Sense radon threshold update requires station identity")
        if min_radon < 1 or max_radon > 9999 or min_radon >= max_radon:
            raise ValueError(
                "X-Sense radon thresholds require "
                "1 <= minimum < maximum <= 9999"
            )
        return await self.api_call(
            "104118",
            stationId=station.entity_id,
            stationSn=station.sn,
            minRadon=str(min_radon),
            maxRadon=str(max_radon),
        )

    async def update_shadow_setting(self, entity: Entity, data_key: str, value):
        """Write a non-camera setting through the same settings shadow as the app."""
        station = getattr(entity, "station", entity)
        desired = {
            "shadow": "infoBase" if entity is station else "infoDev",
            data_key: str(value),
        }

        if data_key in {"alarmVol", "voiceVol", "alarmTone"}:
            if _volume_includes_station_sn(entity, data_key):
                desired["stationSN"] = station.sn

            if entity is station:
                if entity.type == "SBS10":
                    if data_key != "voiceVol" and "voiceVol" in entity.data:
                        desired["voiceVol"] = str(entity.data["voiceVol"])
                    if data_key != "alarmVol" and "alarmVol" in entity.data:
                        desired["alarmVol"] = str(entity.data["alarmVol"])
                    if data_key != "alarmTone" and "alarmTone" in entity.data:
                        desired["alarmTone"] = str(entity.data["alarmTone"])
            else:
                desired["deviceSN"] = entity.sn

            if data_key == "alarmVol":
                if alarm_tone := entity.data.get("alarmTone"):
                    desired["alarmTone"] = str(alarm_tone)
            if data_key == "alarmTone":
                if alarm_vol := entity.data.get("alarmVol"):
                    desired["alarmVol"] = str(alarm_vol)
        else:
            if entity is station:
                desired["stationSN"] = station.sn
            else:
                desired["deviceSN"] = entity.sn
                if _shadow_setting_includes_station_sn(entity, data_key):
                    desired["stationSN"] = station.sn
            if data_key == "tempUnit":
                desired["changeUnit"] = "1"
            companion_key = _shadow_setting_companion_key(data_key)
            if companion_key and (companion := entity.data.get(companion_key)):
                desired[companion_key] = str(companion)

        return await self.do_thing(
            station, _shadow_config_topic(entity), {"state": {"desired": desired}}
        )

    async def update_light_setting(
        self,
        entity: Entity,
        data_key: str,
        value,
        *,
        on_event: str,
    ):
        """Write an SBS50 light setting through the APK light shadow path."""
        station = getattr(entity, "station", entity)
        desired = {
            "shadow": "infoDev",
            "deviceSN": entity.sn,
            data_key: str(value),
            "onEvent": on_event,
        }

        return await self.do_thing(
            station, f"2nd_cfg_{entity.sn}", {"state": {"desired": desired}}
        )

    async def update_light_scene(self, entity: Entity, scene: str):
        """Write the SBS50 light scene payload used by the APK."""
        station = getattr(entity, "station", entity)
        desired = {
            "shadow": "infoDev",
            "deviceSN": entity.sn,
            "lightScene": str(scene),
            "onEvent": "1",
        }
        if str(scene) == "1":
            desired["pirEnable"] = "1"
            desired["awaitEnable"] = "0"
        elif str(scene) == "2":
            desired["pirEnable"] = "0"
            desired["awaitEnable"] = "1"
        else:
            desired["pirEnable"] = "1"
            desired["awaitEnable"] = "1"

        return await self.do_thing(
            station, f"2nd_cfg_{entity.sn}", {"state": {"desired": desired}}
        )

    async def query_light_schedules(self, entity: Entity):
        """Query SBS50 light schedules through the same REST API as the APK."""
        station = getattr(entity, "station", entity)
        data = await self.api_call(
            "405105",
            stationId=station.entity_id,
            deviceId=entity.entity_id,
        )
        return light_schedule_list(data)

    async def create_light_schedule(
        self,
        entity: Entity,
        *,
        name: str,
        start_time: str,
        end_time: str,
        week_days: list[str],
        enabled: bool,
        time_zone: str,
    ):
        """Create an SBS50 light schedule through the APK schedule API."""
        station = getattr(entity, "station", entity)
        return await self.api_call(
            "405101",
            stationId=station.entity_id,
            schedName=name,
            deviceIds=[entity.entity_id],
            timeZone=time_zone,
            startTime=schedule_time(start_time),
            endTime=schedule_time(end_time),
            isEnable="1" if enabled else "0",
            weekDays=schedule_week_days(week_days),
            newTimeZoneMode="1",
        )

    async def update_light_schedule(
        self,
        entity: Entity,
        *,
        schedule_id: str,
        start_time: str,
        end_time: str,
        week_days: list[str],
        enabled: bool,
        time_zone: str,
    ):
        """Update an SBS50 light schedule through the APK schedule API."""
        station = getattr(entity, "station", entity)
        return await self.api_call(
            "405103",
            stationId=station.entity_id,
            schedId=schedule_id,
            deviceId=entity.entity_id,
            timeZone=time_zone,
            startTime=schedule_time(start_time),
            endTime=schedule_time(end_time),
            isEnable="1" if enabled else "0",
            weekDays=schedule_week_days(week_days),
            newTimeZoneMode="1",
        )

    async def rename_light_schedule(
        self,
        entity: Entity,
        *,
        schedule_id: str,
        name: str,
    ):
        """Rename an SBS50 light schedule through the APK schedule API."""
        station = getattr(entity, "station", entity)
        return await self.api_call(
            "405102",
            stationId=station.entity_id,
            schedId=schedule_id,
            schedName=name,
        )

    async def delete_light_schedule(self, entity: Entity, *, schedule_id: str):
        """Delete an SBS50 light schedule through the APK schedule API."""
        station = getattr(entity, "station", entity)
        return await self.api_call(
            "405104",
            stationId=station.entity_id,
            schedId=schedule_id,
            deviceId=entity.entity_id,
        )

    async def query_light_groups(self, entity: Entity):
        """Query SBS50 light groups through the same REST API as the APK."""
        station = getattr(entity, "station", entity)
        data = await self.api_call("405001", stationId=station.entity_id)
        return light_group_list(data)

    async def create_light_group(
        self,
        entity: Entity,
        *,
        name: str,
    ):
        """Create an SBS50 light group through the APK group API."""
        station = getattr(entity, "station", entity)
        return await self.api_call(
            "405002",
            stationId=station.entity_id,
            groupName=name,
        )

    async def rename_light_group(
        self,
        entity: Entity,
        *,
        group_id: str,
        name: str,
    ):
        """Rename an SBS50 light group through the APK group API."""
        station = getattr(entity, "station", entity)
        return await self.api_call(
            "405003",
            stationId=station.entity_id,
            groupId=group_id,
            groupName=name,
        )

    async def update_light_group_timer(
        self,
        entity: Entity,
        *,
        group_id: str,
        data_key: str,
        value: str,
    ):
        """Update an SBS50 light group timer through the APK group API."""
        station = getattr(entity, "station", entity)
        payload = {
            "stationId": station.entity_id,
            "groupId": group_id,
            data_key: value,
            "onEvent": "1" if data_key == "pirTime" else "2",
        }
        return await self.api_call("405004", **payload)

    async def bind_light_group(
        self,
        entity: Entity,
        *,
        name: str,
        device_ids: list[str],
    ):
        """Add SBS50 lights to a group through the APK group API."""
        station = getattr(entity, "station", entity)
        return await self.api_call(
            "405005",
            stationId=station.entity_id,
            groupName=name,
            deviceIds=non_empty_strings(device_ids, "group device list"),
        )

    async def delete_light_group(self, entity: Entity, *, group_id: str):
        """Delete an SBS50 light group through the APK group API."""
        station = getattr(entity, "station", entity)
        return await self.api_call(
            "405006",
            stationId=station.entity_id,
            groupId=group_id,
        )

    async def remove_light_group_devices(
        self,
        entity: Entity,
        *,
        device_ids: list[str],
    ):
        """Remove SBS50 lights from their group through the APK group API."""
        station = getattr(entity, "station", entity)
        return await self.api_call(
            "405007",
            stationId=station.entity_id,
            deviceIds=non_empty_strings(device_ids, "group device list"),
        )

    async def update_co_pre_alarm(
        self,
        entity: Entity,
        *,
        enabled: bool | None = None,
        period: int | str | None = None,
    ):
        """Write CO low pre-alarm settings through the APK warn-period shadow."""
        station = getattr(entity, "station", entity)
        desired = {
            "shadow": "appWarnPerion",
            "deviceSN": entity.sn,
            "stationSN": station.sn,
            "time": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
            "userId": self.userid,
        }
        if enabled is not None:
            desired["warnIsOpen"] = "1" if enabled else "0"
        if period is not None:
            desired["warnPeriod"] = str(period)

        return await self.do_thing(
            station, "2nd_warnperiod", {"state": {"desired": desired}}
        )

    async def update_shadow_array_setting(
        self,
        entity: Entity,
        data_key: str,
        values: list[float],
        *,
        comfort_type: str | None = None,
    ):
        """Write paired range settings through the same array payload as the app."""
        updates = {data_key: values}
        return await self.update_shadow_settings(
            entity, updates, comfort_type=comfort_type
        )

    async def update_shadow_settings(
        self,
        entity: Entity,
        updates: Dict,
        *,
        comfort_type: str | None = None,
    ):
        """Write multiple non-camera settings in one APK-style shadow payload."""
        station = getattr(entity, "station", entity)
        desired = {
            "shadow": "infoDev",
            "deviceSN": entity.sn,
            "stationSN": station.sn,
        }
        desired.update(updates)
        if comfort_type is not None:
            desired["comfortType"] = comfort_type

        return await self.do_thing(
            station, _shadow_config_topic(entity), {"state": {"desired": desired}}
        )

    async def action(self, entity: Entity, action: str):
        action_def = self.action_definition(entity, action)
        if not action_def:
            raise XSenseError(
                f"Action {action} is not supported for entity type {entity.type}"
            )

        topic = action_def.get("topic")
        if callable(topic):
            topic = topic(entity)
        shadow = action_def["shadow"]
        if callable(shadow):
            shadow = shadow(entity)
        return await self.set_state(entity, shadow, topic, action_def)


def _url_scheme(url: str | None) -> str | None:
    """Return the URL scheme without logging or exposing the full URL."""
    if not isinstance(url, str) or "://" not in url:
        return None
    return url.split("://", 1)[0].lower()


def _camera_live_url(data: Dict) -> str | None:
    """Return the live URL from the APK LiveResponse data model."""
    live_url = data.get("liveUrl") or data.get("url")
    if not isinstance(live_url, str) or not live_url:
        return None
    return live_url


def _shadow_config_topic(entity: Entity) -> str:
    """Return the settings shadow topic used by the X-Sense app."""
    station = getattr(entity, "station", None)
    if entity.type == "SBS50":
        return f"2nd_cfg_{entity.sn}"
    if station and station.type == "SBS50":
        return f"2nd_cfg_{entity.sn}"
    return f"info_{entity.sn}"


def _volume_includes_station_sn(entity: Entity, data_key: str) -> bool:
    """Return if the APK volume payload includes stationSN for this entity."""
    if data_key == "voiceVol":
        return True
    if data_key == "alarmTone":
        if entity is getattr(entity, "station", entity):
            return True
        data_key = "alarmVol"
    if getattr(entity, "entity_type", None) in {
        EntityType.CO,
        EntityType.LIGHT,
        EntityType.TEMPERATURE,
    }:
        return False
    return True


def _shadow_setting_companion_key(data_key: str) -> str | None:
    """Return the companion setting the app preserves with paired updates."""
    return {
        "alarmVol": "alarmTone",
        "alarmTone": "alarmVol",
        "chirpVol": "chirpTone",
        "chirpTone": "chirpVol",
        "remindVol": "remindTone",
        "remindTone": "remindVol",
    }.get(data_key)


def _shadow_setting_includes_station_sn(entity: Entity, data_key: str) -> bool:
    """Return if an APK settings payload includes stationSN for this field."""
    return (
        data_key in {"tempUnit", "tAdjust", "hAdjust"}
        and getattr(entity, "entity_type", None) == EntityType.TEMPERATURE
    )


def _action_timestamp(definition: Dict, entity: Entity) -> str | None:
    time_format = definition.get("time_format", "datetime")
    if callable(time_format):
        time_format = time_format(entity)
    if time_format is None:
        return None
    if time_format == "epoch_ms":
        return str(int(datetime.now(timezone.utc).timestamp() * 1000))
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def _short_id(value):
    """Return a short diagnostic id without logging full serial-like values."""
    if value in (None, ""):
        return None
    text = str(value)
    return text if len(text) <= 6 else f"...{text[-6:]}"


def _action_debug_context(entity: Entity, action: str, target, topic, desired: Dict):
    """Return safe action metadata without full serials or payload values."""
    station = getattr(entity, "station", entity)
    context = {
        "action": action,
        "device": _short_id(getattr(entity, "sn", None)),
        "device_type": getattr(entity, "type", None),
        "station": _short_id(getattr(station, "sn", None)),
        "station_type": getattr(station, "type", None),
        "target": _short_id(getattr(target, "shadow_name", None)),
        "topic": topic,
        "shadow": desired.get("shadow"),
        "has_time": "time" in desired,
        "has_user_param": "userParam" in desired,
    }
    if getattr(entity, "type", None) == "XS01-WX":
        smoke_edition = _action_smoke_edition(entity)
        context.update(
            {
                "smoke_edition_present": smoke_edition is not None,
                "smoke_edition_ge9": _action_smoke_edition_ge9(smoke_edition),
                "xs01_wx_serial_v9": _action_xs01_wx_serial_v9(entity),
            }
        )
    return context


def _action_smoke_edition(entity: Entity):
    for source in (entity, getattr(entity, "station", None)):
        data = getattr(source, "data", None) or {}
        value = data.get("smokeEdition")
        if value not in (None, ""):
            return value
    return None


def _action_smoke_edition_ge9(smoke_edition) -> bool:
    try:
        return int(smoke_edition or 0) >= 9
    except (TypeError, ValueError):
        return False


def _action_xs01_wx_serial_v9(entity: Entity) -> bool:
    station = getattr(entity, "station", entity)
    station_sn = str(getattr(station, "sn", "") or "")
    return "EN" in station_sn.upper() or "UL" in station_sn.upper()


def _camera_write_debug_context(camera: Entity, endpoint: str, updates: Dict):
    """Return safe camera write metadata without full serials or payload values."""
    return {
        "endpoint": endpoint,
        "device": _short_id(getattr(camera, "sn", None)),
        "device_type": getattr(camera, "type", None),
        "fields": sorted(str(key) for key in updates),
    }


def _ipc_node_type(mqtt_region: str | None) -> str:
    """Return the IPC node type from the APK current-house MQTT region."""
    if not mqtt_region or len(mqtt_region) <= 2:
        return "US"
    node_type = mqtt_region[:2].upper()
    return node_type if node_type in {"CN", "EU", "US"} else "US"


def _ipc_language(language: str | None) -> str:
    """Return the simple app language code the APK sends to IPC registration."""
    if not language:
        return "en"
    normalized = str(language).strip().replace("_", "-")
    if not normalized:
        return "en"
    return normalized.split("-", 1)[0].lower()


def _camera_type(data: Dict) -> str | None:
    device_model = data.get("deviceModel") or {}
    for value in (
        data.get("modelNo"),
        data.get("displayModelNo"),
        device_model.get("modelName"),
    ):
        model = str(value or "").strip().upper()
        if model:
            return model
    return None


def _camera_data(data: Dict) -> Dict:
    device_model = data.get("deviceModel") or {}
    device_support = data.get("deviceSupport") or {}
    sd_card = data.get("sdCard") or {}
    person_detect_support = _first_present(
        device_model.get("devicePersonDetect"),
        device_support.get("devicePersonDetect"),
        device_support.get("supportPersonDetect"),
        data.get("devicePersonDetect"),
        data.get("supportPersonDetect"),
        data.get("personDetectSupport"),
    )

    return {
        "activatedTime": data.get("activatedTime"),
        "antiflickerSupport": data.get("antiflickerSupport"),
        "awake": data.get("awake"),
        "batteryLevel": data.get("batteryLevel"),
        "cameraModel": data.get("displayModelNo") or device_model.get("modelName"),
        "cameraStatusCode": data.get("statusCode"),
        "codec": data.get("codec"),
        "defaultCodec": data.get("defaultCodec"),
        "deviceDormancyMessage": data.get("deviceDormancyMessage"),
        "deviceDormancyWakeTime": data.get("deviceDormancyWakeTime"),
        "deviceStatus": data.get("deviceStatus"),
        "firmwareStatus": data.get("firmwareStatus"),
        "firmwareVersion": data.get("firmwareId"),
        "ip": data.get("ip"),
        "isAdmin": (
            data.get("userId") == data.get("adminId")
            if data.get("userId") is not None and data.get("adminId") is not None
            else data.get("isAdmin")
        ),
        "isCharging": bool_state(data.get("isCharging")),
        "isMoved": data.get("isMoved"),
        "liveAudioToggleOn": data.get("liveAudioToggleOn"),
        "modelNo": data.get("modelNo"),
        "networkName": data.get("networkName"),
        "offlineTime": data.get("offlineTime"),
        "online": data.get("online"),
        "recResolution": data.get("recResolution"),
        "sdCardFormatStatus": sd_card.get("formatStatus"),
        "sdCardTotal": sd_card.get("total"),
        "sdCardUsed": sd_card.get("used"),
        "signalStrength": data.get("signalStrength"),
        "showCodecChange": data.get("showCodecChange"),
        "streamProtocol": device_model.get("streamProtocol"),
        "supportAntiFlicker": _addx_bool(data.get("antiflickerSupport")),
        "supportAlarm": _addx_bool(device_support.get("deviceSupportAlarm")),
        "supportAlarmVolume": _addx_bool(device_support.get("supportAlarmVolume")),
        "supportBattery": _addx_bool(device_model.get("canStandby")),
        "supportChargeAutoPowerOn": _addx_bool(
            device_support.get("supportChargeAutoPowerOn")
        ),
        "supportCryDetect": _addx_bool(device_support.get("supportCryDetect")),
        "supportDeviceCall": _addx_bool(device_support.get("supportDeviceCall")),
        "supportDoorBellAlarm": _addx_bool(
            device_support.get("supportAlarmWhenRemoveToggle")
        ),
        "supportLiveAudio": _addx_bool(device_support.get("supportLiveAudioToggle")),
        "supportLight": _addx_bool(device_model.get("whiteLight")),
        "supportMechanicalDingDong": _addx_bool(
            device_support.get("supportMechanicalDingDong")
        ),
        "supportMirrorFlip": _addx_bool(device_support.get("deviceSupportMirrorFlip")),
        "supportMotionTrack": _addx_bool(device_model.get("supportMotionTrack")),
        "supportPersonDetect": _addx_bool(person_detect_support),
        "supportPirCooldown": _addx_bool(device_support.get("supportPirCooldown")),
        "supportRecLamp": _addx_bool(device_support.get("supportRecLamp")),
        "supportRecordingAudio": _addx_bool(
            device_support.get("supportRecordingAudioToggle")
        ),
        "supportRocker": _addx_bool(device_model.get("canRotate")),
        "supportSdCard": bool(sd_card) and sd_card.get("formatStatus") != 23,
        "supportSleep": device_support.get("deviceDormancySupport") == 1,
        "supportLiveSpeakerVolume": _addx_bool(
            device_support.get("supportLiveSpeakerVolume")
        ),
        "supportedRecordingResolutions": device_support.get("deviceSupportResolution"),
        "supportVoiceVolume": _addx_bool(device_support.get("supportVoiceVolume")),
        "supportWebrtc": _addx_bool(device_support.get("supportWebrtc")),
        "thumbImgTime": data.get("thumbImgTime"),
        "thumbImgUrl": data.get("thumbImgUrl"),
        "timeZone": data.get("timeZone"),
        "timeZoneArea": data.get("timeZoneArea"),
        "wifiChannel": data.get("wifiChannel"),
        "wiredMacAddress": data.get("wiredMacAddress"),
    }


_CAMERA_USER_CONFIG_KEYS = (
    "alarmSeconds",
    "alarmVolume",
    "antiflicker",
    "antiflickerSwitch",
    "chargeAutoPowerOnCapacity",
    "chargeAutoPowerOnSwitch",
    "cryDetect",
    "cryDetectLevel",
    "deviceCallToggleOn",
    "deviceLanguage",
    "devicePersonDetect",
    "mechanicalDingDongDuration",
    "mechanicalDingDongSwitch",
    "mirrorFlip",
    "motionSensitivity",
    "motionTrack",
    "motionTrackMode",
    "needAlarm",
    "needMotion",
    "needNightVision",
    "needVideo",
    "nightThresholdLevel",
    "nightVisionMode",
    "recLamp",
    "timeZone",
    "timeZoneArea",
    "videoSeconds",
    "voiceVolume",
    "voiceVolumeSwitch",
    "whiteLightScintillation",
)

_CAMERA_BOOLEAN_USER_CONFIG_KEYS = {"deviceCallToggleOn"}


def _camera_user_config_payload(camera: Entity, updates: Dict) -> Dict:
    """Return the APK UserConfigBean-style camera config payload."""
    payload = {"serialNumber": camera.sn}
    payload.update(
        {
            key: _camera_config_payload_value(key, value)
            for key, value in updates.items()
            if key in _CAMERA_USER_CONFIG_KEYS and value is not None
        }
    )
    _add_camera_config_companions(camera, payload)
    return payload


def _add_camera_config_companions(camera: Entity, payload: Dict) -> None:
    """Add companion config fields the APK sends with selected toggles."""
    if "needMotion" in payload and camera.data.get("motionSensitivity") is not None:
        payload["motionSensitivity"] = camera.data["motionSensitivity"]
    if "needVideo" in payload and camera.data.get("videoSeconds") == 0:
        payload["videoSeconds"] = -1
    if "needAlarm" in payload:
        if camera.data.get("supportRocker") is True:
            payload["alarmSeconds"] = 10
        elif camera.data.get("alarmSeconds") in (None, 0):
            payload["alarmSeconds"] = 5
        else:
            payload["alarmSeconds"] = camera.data["alarmSeconds"]
    if (
        "needNightVision" in payload
        and camera.data.get("nightThresholdLevel") is not None
    ):
        payload["nightThresholdLevel"] = camera.data["nightThresholdLevel"]


def _camera_config_payload_value(key: str, value):
    """Return the value type used by the APK UserConfigBean field."""
    if key in _CAMERA_BOOLEAN_USER_CONFIG_KEYS:
        return value if isinstance(value, bool) else _addx_bool(value)
    if isinstance(value, bool):
        return 1 if value else 0
    return value


def _camera_config_write_value(key: str, enabled: bool):
    """Return the value type used by the APK UserConfigBean field."""
    return _camera_config_payload_value(key, enabled)


def _addx_bool(value) -> bool | None:
    """Return the APK-style Boolean/int support flag value."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value == 1
    return None


def _first_present(*values):
    """Return the first value that is explicitly present."""
    for value in values:
        if value is not None:
            return value
    return None


def _enabled_option_values(options: Any) -> list[Any]:
    """Return enabled option values from the APK SettingOptionsResponse shape."""
    if not isinstance(options, list):
        return []
    values: list[Any] = []
    for option in options:
        if not isinstance(option, dict):
            continue
        if _addx_bool(option.get("enabled")) is not True:
            continue
        value = option.get("value")
        if value is not None:
            values.append(value)
    return values


def _option_debug_values(options: Any) -> list[dict[str, Any]]:
    """Return safe APK option metadata for debug/diagnostics."""
    if not isinstance(options, list):
        return []
    values: list[dict[str, Any]] = []
    for option in options:
        if not isinstance(option, dict):
            continue
        value = option.get("value")
        if value is None:
            continue
        values.append(
            {
                "value": value,
                "enabled": _addx_bool(option.get("enabled")),
            }
        )
    return values


def _camera_settings_options_data(data: Dict) -> Dict:
    """Return APK camera form options from /user/getFormOptions."""
    form_options = data.get("deviceFormOptions") or {} if isinstance(data, dict) else {}
    video_seconds_options = form_options.get("videoSeconds")
    cooldown_options = form_options.get("cooldown_in_s")
    video_seconds = _enabled_option_values(video_seconds_options)
    cooldown = _enabled_option_values(cooldown_options)
    result: Dict[str, Any] = {}
    video_seconds_debug = _option_debug_values(video_seconds_options)
    cooldown_debug = _option_debug_values(cooldown_options)
    if video_seconds_debug:
        result["videoSecondsOptions"] = video_seconds_debug
    if cooldown_debug:
        result["cooldownOptionDetails"] = cooldown_debug
    if video_seconds:
        result["videoSecondsValues"] = video_seconds
    if cooldown:
        result["cooldownOptions"] = cooldown
    return result


def _camera_options_debug_context(camera: Entity) -> Dict:
    """Return safe camera option-list diagnostics."""
    return {
        "camera": _short_id(getattr(camera, "sn", None)),
        "model": camera.data.get("modelNo") or getattr(camera, "type", None),
        "video_seconds": camera.data.get("videoSeconds"),
        "video_seconds_values": camera.data.get("videoSecondsValues"),
        "video_seconds_options": camera.data.get("videoSecondsOptions"),
        "cooldown": camera.data.get("cooldownValue"),
        "cooldown_options": camera.data.get("cooldownOptions"),
        "cooldown_option_details": camera.data.get("cooldownOptionDetails"),
        "recording_resolution": camera.data.get("recResolution"),
        "recording_resolutions": camera.data.get("supportedRecordingResolutions"),
    }


def _camera_config_data(data: Dict) -> Dict:
    cooldown = data.get("cooldown") or {}
    return {
        "alarmSeconds": data.get("alarmSeconds"),
        "alarmVol": data.get("alarmVolume"),
        "antiflicker": data.get("antiflicker"),
        "antiflickerSwitch": _addx_bool(data.get("antiflickerSwitch")),
        "chargeAutoPowerOnCapacity": data.get("chargeAutoPowerOnCapacity"),
        "chargeAutoPowerOnCapacityOptions": data.get(
            "chargeAutoPowerOnCapacityOptions"
        ),
        "chargeAutoPowerOnSwitch": _addx_bool(data.get("chargeAutoPowerOnSwitch")),
        "cooldownSupported": _addx_bool(cooldown.get("deviceSupport")),
        "cooldownEnabled": _addx_bool(cooldown.get("userEnable")),
        "cooldownOptions": cooldown.get("notCloseValues") or data.get("coolDownValues"),
        "cooldownValue": cooldown.get("value"),
        "cryDetect": _addx_bool(data.get("cryDetect")),
        "cryDetectLevel": data.get("cryDetectLevel"),
        "deviceCallToggleOn": _addx_bool(data.get("deviceCallToggleOn")),
        "deviceLanguage": data.get("deviceLanguage"),
        "devicePersonDetect": _addx_bool(data.get("devicePersonDetect")),
        "deviceSupportLanguage": data.get("deviceSupportLanguage"),
        "mechanicalDingDongDuration": data.get("mechanicalDingDongDuration"),
        "mechanicalDingDongSwitch": _addx_bool(data.get("mechanicalDingDongSwitch")),
        "mirrorFlip": _addx_bool(data.get("mirrorFlip")),
        "motionSensitivity": _camera_motion_sensitivity_value(
            data.get("motionSensitivity")
        ),
        "motionSensitivityOptionList": data.get("motionSensitivityOptionList"),
        "motionTrack": _addx_bool(data.get("motionTrack")),
        "motionTrackMode": data.get("motionTrackMode"),
        "needAlarm": _addx_bool(data.get("needAlarm")),
        "needMotion": _addx_bool(data.get("needMotion")),
        "needNightVision": _addx_bool(data.get("needNightVision")),
        "needVideo": _addx_bool(data.get("needVideo")),
        "nightThresholdLevel": data.get("nightThresholdLevel"),
        "nightVisionMode": data.get("nightVisionMode"),
        "recLamp": _addx_bool(data.get("recLamp")),
        "timeZone": data.get("timeZone"),
        "timeZoneArea": data.get("timeZoneArea"),
        "videoSeconds": _camera_video_seconds_value(data.get("videoSeconds")),
        "videoSecondsValues": data.get("videoSecondsValues"),
        "voiceVol": data.get("voiceVolume"),
        "voiceVolumeSwitch": _addx_bool(data.get("voiceVolumeSwitch")),
        "whiteLightScintillation": _addx_bool(data.get("whiteLightScintillation")),
    }


def _camera_motion_sensitivity_value(value):
    """Return the APK camera motion sensitivity value."""
    return value


def _camera_video_seconds_value(value):
    """Return the APK default for unset camera recording duration."""
    return -1 if value in (None, 0) else value


def _camera_audio_data(data: Dict) -> Dict:
    audio = data.get("deviceAudio") or data
    ring_keys = audio.get("supportDoorBellRingKey") or []
    return {
        "doorBellRingKey": audio.get("doorBellRingKey"),
        "doorBellRingKeyOptions": [
            ring_key.get("id")
            for ring_key in ring_keys
            if isinstance(ring_key, dict) and ring_key.get("id") is not None
        ],
        "liveAudioToggleOn": _addx_bool(audio.get("liveAudioToggleOn")),
        "liveSpeakerVolume": audio.get("liveSpeakerVolume"),
        "recordingAudioToggleOn": _addx_bool(audio.get("recordingAudioToggleOn")),
    }


def _camera_doorbell_data(data: Dict) -> Dict:
    doorbell_config = data.get("doorbellConfig") or data
    return {
        "alarmWhenRemoveToggleOn": _addx_bool(
            doorbell_config.get("alarmWhenRemoveToggleOn")
        ),
    }


def _camera_ai_notification_data(data: Dict) -> Dict:
    """Return AI notification category settings from the APK response."""
    raw_items = data.get("list")
    if isinstance(data.get("data"), dict):
        raw_items = data["data"].get("list", raw_items)
    if not isinstance(raw_items, list):
        return {}

    enabled: set[str] = set()
    supported: set[str] = set()
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        group_types = _CAMERA_AI_NOTIFICATION_GROUPS.get(name)
        if group_types is None:
            continue

        sub_events = item.get("subEvent")
        if isinstance(sub_events, list) and sub_events:
            item_types = []
            for sub_event in sub_events:
                if not isinstance(sub_event, dict):
                    continue
                sub_name = str(sub_event.get("name") or "").strip()
                if sub_name in group_types:
                    item_types.append(sub_name)
                    supported.add(sub_name)
                    if sub_event.get("choice") is True:
                        enabled.add(sub_name)
        else:
            item_types = list(group_types)
            supported.update(item_types)
            if item.get("choice") is True:
                enabled.update(item_types)

    result = _camera_ai_notification_state_data(enabled)
    result["aiNotificationSupportedTypes"] = sorted(supported)
    return result


def _camera_ai_notification_enabled(data: Dict) -> set[str]:
    """Return currently enabled AI notification categories from entity data."""
    return {
        event_type
        for event_type in CAMERA_AI_NOTIFICATION_TYPES
        if data.get(_camera_ai_notification_key(event_type)) is True
    }


def _camera_ai_notification_payload(enabled: set[str]) -> Dict:
    """Return the APK updateMessageNotification eventObjectType payload."""
    payload: dict[str, list[str]] = {"vehicle": [], "package": []}
    for group, group_types in _CAMERA_AI_NOTIFICATION_GROUPS.items():
        selected = [event_type for event_type in group_types if event_type in enabled]
        payload_key = _CAMERA_AI_NOTIFICATION_PAYLOAD_KEYS[group]
        if group in {"vehicle", "package"}:
            payload[payload_key] = selected
        elif selected:
            payload[payload_key] = []
    return payload


def _camera_ai_notification_state_data(enabled: set[str]) -> Dict:
    """Return flat entity data for AI notification category settings."""
    return {
        _camera_ai_notification_key(event_type): event_type in enabled
        for event_type in CAMERA_AI_NOTIFICATION_TYPES
    }


def _camera_ai_notification_key(event_type: str) -> str:
    """Return the entity data key for an AI notification category."""
    return f"aiNotification{_camel_suffix(event_type)}"


def _camera_ai_assistant_data(data: Dict, serial_number: str | None = None) -> Dict:
    """Return AI assistant object switches from the APK response."""
    raw_items = data.get("data", data)
    if isinstance(raw_items, dict):
        raw_items = raw_items.get("data") or raw_items.get("list") or [raw_items]
    if not isinstance(raw_items, list):
        return {}

    selected_device = None
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        if serial_number is None or str(item.get("serialNumber")) == str(serial_number):
            selected_device = item
            break
    if selected_device is None:
        return {}

    object_list = selected_device.get("list")
    if not isinstance(object_list, list):
        return {}

    result: Dict[str, bool] = {}
    supported: list[str] = []
    for item in object_list:
        if not isinstance(item, dict):
            continue
        event_object = str(item.get("eventObject") or "").strip()
        if event_object not in CAMERA_AI_ASSISTANT_TYPES:
            continue
        supported.append(event_object)
        result[_camera_ai_assistant_key(event_object)] = item.get("checked") is True
    if supported:
        result["aiAssistantSupportedTypes"] = supported
    return result


def _camera_ai_assistant_key(event_object: str) -> str:
    """Return the entity data key for an AI assistant object switch."""
    return f"aiAssistant{_camel_suffix(event_object)}"


def _camel_suffix(value: str) -> str:
    """Return PascalCase for snake-style APK object names."""
    return "".join(part.capitalize() for part in value.split("_") if part)
