import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict

import aiohttp

from .aws_signer import AWSSigner
from .base import XSenseBase
from .entity import Entity
from .entity_map import EntityType, entities
from .exceptions import SessionExpired, APIFailure, XSenseError
from .house import House
from .station import Station
from ..const import LOGGER

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

# The Android app reads these standalone Wi-Fi device categories from the
# house-level mainpage/2nd_mainpage shadows, not from station-level mainpage
# shadows. Querying a station-level mainpage for them returns 404 on accounts
# such as #160 and should not fail setup.
_HOUSE_STATE_DEVICE_TYPES = {
    "SC06-WX",
    "SC07-WX",
    "STH0C",
    "SWS0B",
    "XC04-WX",
    "XC0C-iA",
    "XC0C-iR",
    "XC0M-iR",
    "XP0A-iR",
    "XP0H-iR",
    "XP0J-iA",
    "XR0A-iR",
    "XS01-WX",
    "XS03-WX",
    "XS0B-iR",
    "XS0E-iR",
    "XS0R-iA",
}

# The APK uses 2nd_info directly for the newer standalone Wi-Fi CO,
# combined, temperature/humidity, water, and radon families. Wi-Fi smoke
# families still use the legacy info shadow in their settings screens.
_SECOND_INFO_DEVICE_TYPES = {
    "SC06-WX",
    "SC07-WX",
    "STH0C",
    "SWS0B",
    "XC04-WX",
    "XC0C-iA",
    "XC0C-iR",
    "XC0M-iR",
    "XP0A-iR",
    "XP0H-iR",
    "XP0J-iA",
    "XR0A-iR",
}


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
    return _CAMERA_RESOLUTION_ALIASES.get(normalized.upper())


def _camera_webrtc_ticket_valid(ticket: dict) -> bool:
    expiration = ticket.get("expirationTime")
    if expiration in (None, ""):
        return False
    try:
        return int(expiration) > int(datetime.now().timestamp() * 1000)
    except (TypeError, ValueError):
        return False


def camera_live_resolution(camera: Entity) -> str:
    """Return the APK start-live resolution for a camera live-view session."""
    saved_resolution = _camera_resolution(camera.data.get("liveResolution"))
    if saved_resolution:
        return saved_resolution

    return "1280x720"


class AsyncXSense(XSenseBase):
    def __init__(self, session=None, language: str | None = None):
        super().__init__()
        self.session = session
        self._owns_session = session is None
        self.language = _ipc_language(language)

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

    async def get_house(self, house: House, page: str):
        if self._aws_token_expiring():
            await self.load_aws()

        url, headers = self._house_request(house, page)

        session = await self._get_session()
        async with session.get(url, headers=headers) as response:
            self._lastres = response
            return await response.json()

    async def get_thing(self, station: Station, page: str):
        if self._aws_token_expiring():
            await self.load_aws()

        url, headers = self._thing_request(station, page)

        session = await self._get_session()
        async with session.get(url, headers=headers) as response:
            self._lastres = response
            return await response.json()

    async def do_thing(self, station: Station, page: str, data: Dict):
        if self._aws_token_expiring():
            await self.load_aws()

        body = _shadow_update_body(data)
        url, headers = self._thing_request(station, page, body)

        session = await self._get_session()
        async with session.post(url, data=body, headers=headers) as response:
            self._lastres = response
            if response.status >= 400:
                text = await response.text()
                raise APIFailure(
                    f"Unable to update thing shadow: {response.status}/{text}"
                )
            return await response.json()

    async def login(self, username, password):
        await asyncio.get_running_loop().run_in_executor(
            None, self.sync_login, username, password
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
        await self.addx_call(
            "/device/updaterecresolution",
            serialNumber=camera.sn,
            recResolution=resolution,
        )
        camera.set_data({"recResolution": resolution})

    async def update_camera_default_codec(self, camera: Entity, codec: str) -> None:
        """Write the default camera codec through the Android app endpoint."""
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
        await self.addx_call(
            "/device/updateCooldown",
            serialNumber=camera.sn,
            cooldown={"userEnable": user_enable, "value": value},
        )
        camera.set_data({"cooldownEnabled": user_enable, "cooldownValue": value})

    async def get_camera_webrtc_ticket(self, camera: Entity) -> dict | None:
        """Return an APK WebRTC ticket, reusing it until it is near expiry."""
        cached = camera.data.get("cameraWebrtcTicket")
        if isinstance(cached, dict) and _camera_webrtc_ticket_valid(cached):
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
                }
            )

    async def wake_camera(self, camera: Entity) -> None:
        """Wake a sleeping camera through the Android app endpoint."""
        await self.addx_call("/device/wakeupDevice", serialNumber=camera.sn)

    async def update_camera_doorbell_config(self, camera: Entity, **updates) -> None:
        """Write doorbell config through the Android app endpoint."""
        doorbell_config = {
            "alarmWhenRemoveToggleOn": camera.data.get("alarmWhenRemoveToggleOn")
        }
        doorbell_config.update(updates)
        await self.addx_call(
            "/device/config/updatedoorbellconfig",
            serialNumber=camera.sn,
            doorbellConfig=doorbell_config,
        )
        camera.set_data(updates)

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
                return

            text = await self._lastres.text()
            raise APIFailure(
                f"Unable to retrieve station data: {self._lastres.status}/{text}"
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
        desired.update(extra)
        action_data = definition.get("data", {})
        if callable(action_data):
            action_data = action_data(entity)
        desired.update(action_data)

        data = {"state": {"desired": desired}}

        return await self.do_thing(target, topic, data)

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
        station = getattr(entity, "station", entity)
        desired = {
            "shadow": "infoBase" if entity is station else "infoDev",
            data_key: str(value),
        }

        if data_key in {"alarmVol", "voiceVol"}:
            if _volume_includes_station_sn(entity, data_key):
                desired["stationSN"] = station.sn

            if entity is station:
                if entity.type == "SBS10":
                    if data_key != "voiceVol" and "voiceVol" in entity.data:
                        desired["voiceVol"] = str(entity.data["voiceVol"])
                    if data_key != "alarmVol" and "alarmVol" in entity.data:
                        desired["alarmVol"] = str(entity.data["alarmVol"])
            else:
                desired["deviceSN"] = entity.sn

            if data_key == "alarmVol":
                if alarm_tone := entity.data.get("alarmTone"):
                    desired["alarmTone"] = str(alarm_tone)
        else:
            desired["deviceSN"] = entity.sn
            tone_key = _volume_tone_key(data_key)
            if tone_key and (tone := entity.data.get(tone_key)):
                desired[tone_key] = str(tone)

        return await self.do_thing(
            station, _shadow_config_topic(entity), {"state": {"desired": desired}}
        )

    async def action(self, entity: Entity, action: str):
        entity_def = entities.get(entity.type)
        if not entity_def:
            raise XSenseError(
                f"Entity type {entity.type} is unknown, action {action} not possible"
            )

        action_def = next(
            (a for a in entity_def.get("actions", []) if a.get("action") == action),
            None,
        )
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
    if getattr(entity, "entity_type", None) in {
        EntityType.CO,
        EntityType.LIGHT,
        EntityType.TEMPERATURE,
    }:
        return False
    return True


def _volume_tone_key(data_key: str) -> str | None:
    """Return the companion tone field the app preserves with volume changes."""
    return {
        "alarmVol": "alarmTone",
        "chirpVol": "chirpTone",
        "remindVol": "remindTone",
    }.get(data_key)


def _shadow_update_body(data: Dict) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def _action_timestamp(definition: Dict, entity: Entity) -> str | None:
    time_format = definition.get("time_format", "datetime")
    if callable(time_format):
        time_format = time_format(entity)
    if time_format is None:
        return None
    if time_format == "epoch_ms":
        return str(int(datetime.now(timezone.utc).timestamp() * 1000))
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


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
        "isCharging": data.get("isCharging"),
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
        "supportPersonDetect": False,
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
    if "needMotion" in payload and camera.data.get("motionSensitivity") in (None, 0):
        payload["motionSensitivity"] = 1
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


def _enabled_option_values(options: Any) -> list[Any]:
    """Return enabled option values from the APK SettingOptionsResponse shape."""
    if not isinstance(options, list):
        return []
    values: list[Any] = []
    for option in options:
        if not isinstance(option, dict):
            continue
        if option.get("enabled") is False:
            continue
        value = option.get("value")
        if value is not None:
            values.append(value)
    return values


def _camera_settings_options_data(data: Dict) -> Dict:
    """Return APK camera form options from /user/getFormOptions."""
    form_options = data.get("deviceFormOptions") or {} if isinstance(data, dict) else {}
    video_seconds = _enabled_option_values(form_options.get("videoSeconds"))
    cooldown = _enabled_option_values(form_options.get("cooldown_in_s"))
    result: Dict[str, Any] = {}
    if video_seconds:
        result["videoSecondsValues"] = video_seconds
    if cooldown:
        result["cooldownOptions"] = cooldown
    return result


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
    """Return the APK default for unset camera motion sensitivity."""
    return 1 if value in (None, 0) else value


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
