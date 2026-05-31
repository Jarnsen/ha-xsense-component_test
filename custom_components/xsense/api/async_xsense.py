import asyncio
from datetime import datetime, timezone
import json
from typing import Dict

import aiohttp

from .aws_signer import AWSSigner
from .base import XSenseBase
from .entity import Entity
from .entity_map import entities
from .exceptions import SessionExpired, APIFailure, XSenseError
from .house import House
from .station import Station

CAMERA_TYPES = {"SSC0A", "SSC0B"}
CAMERA_LIVE_URL_MAX_AGE_SECONDS = 240


class AsyncXSense(XSenseBase):
    def __init__(self, session=None):
        super().__init__()
        self.session = session
        self._owns_session = session is None

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
                message = data.get("message") or "unknown error"
                raise APIFailure(f"API failure: {response.status}/{message}")

            if "reCode" not in data:
                raise APIFailure("API failure: Cannot understand response")

            if data["reCode"] != 200:
                errCode = data.get("errCode", 0)
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
                message = data.get("message") or data.get("reMsg") or "unknown error"
                raise APIFailure(f"IPC API failure: {response.status}/{message}")

            if str(data.get("reCode")) != "200":
                err_code = data.get("errCode", 0)
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
        node = addx_session.get("nodeType", "US")
        base_url = self.ADDX_API_BY_NODE.get(node, self.ADDX_API_BY_NODE["US"])
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
                if response.status in (401, 403) and _retry:
                    self._addx_session = await self.register_ipc()
                    return await self.addx_call(endpoint, _retry=False, **kwargs)
                message = result.get("msg") or result.get("message") or "unknown error"
                raise APIFailure(f"ADDX API failure: {response.status}/{message}")

            if result.get("result") not in (0, None):
                raise APIFailure(
                    f"ADDX request for {endpoint} failed with error {result.get('result')}/{result.get('msg')}"
                )
            return result.get("data")

    def _addx_body(self, addx_session: dict, data: Dict | None = None) -> Dict:
        """Return the ADDX request body shape used by the Android SDK."""
        result = dict(data or {})
        country = addx_session.get("countryNo") or "US"
        language = addx_session.get("language") or "en"
        tenant = addx_session.get("tenantId")
        result["countryNo"] = country
        result["language"] = language
        result["app"] = {
            "appName": "X-Sense Home Security",
            "appType": "Android",
            "bundle": "com.xsense.security",
            "channelId": 0,
            "tenantId": tenant,
            "version": int(self.IPC_APPCODE),
            "versionName": self.IPC_VERSION,
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

        url, headers = self._thing_request(station, page, data)

        session = await self._get_session()
        async with session.post(url, json=data, headers=headers) as response:
            self._lastres = response
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
        node_type = "US"
        for house in self.houses.values():
            region = (house.region or "")[:2].upper()
            if region:
                node_type = region
                break
        return await self.ipc_call(
            "C10101",
            userName=self.username,
            nodeType=node_type,
            language="en",
        )

    async def update_camera_data(self):
        """Merge camera metadata and config from the Android app ADDX API."""
        cameras = [
            station
            for house in self.houses.values()
            for station in house.stations.values()
            if station.type in CAMERA_TYPES
        ]
        if not cameras:
            return

        data = await self.addx_call("/device/listuserdevices")
        devices = (data or {}).get("list") or []
        by_sn = {device.get("serialNumber"): device for device in devices}

        for camera in cameras:
            addx_device = by_sn.get(camera.sn)
            if not addx_device:
                continue

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

            if any(
                camera.data.get(key)
                for key in (
                    "supportLiveAudio",
                    "supportLiveSpeakerVolume",
                    "supportRecordingAudio",
                    "supportMechanicalDingDong",
                )
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

    async def update_camera_config(self, camera: Entity, **updates):
        """Write camera user config through the Android app endpoint."""
        payload = {"serialNumber": camera.sn, **updates}
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
            liveResolution=str(camera.data.get("recResolution") or ""),
        )
        if isinstance(data, dict):
            camera.set_data(
                {
                    "cameraAudioUrl": data.get("audioUrl"),
                    "cameraLiveId": data.get("liveId"),
                    "cameraLiveStartedAt": datetime.now(),
                    "cameraLiveUrl": data.get("liveUrl") or data.get("url"),
                }
            )
            return data.get("liveUrl") or data.get("url")
        return None

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
        res = None

        if station.type not in ("SBS50", "SC07-WX", "XC04-WX"):
            res = await self.get_thing(station, f"info_{station.sn}")

        if res is None or self._lastres.status == 404:
            res = await self.get_thing(station, f"2nd_info_{station.sn}")

        if self._lastres.status == 404:
            return

        if "reported" in res.get("state", {}):
            station.set_data(res["state"]["reported"])
        else:
            text = await self._lastres.text()
            raise APIFailure(
                f"Unable to retrieve station data: {self._lastres.status}/{text}"
            )

    async def get_state(self, station: Station):
        res = None
        if station.type not in ("SBS10",):
            res = await self.get_thing(station, "2nd_mainpage")

        if res is None or self._lastres.status == 404:
            res = await self.get_thing(station, "mainpage")

        if "reported" in res.get("state", {}):
            self.parse_get_state(station, res["state"]["reported"])
        else:
            text = await self._lastres.text()
            raise APIFailure(
                f"Unable to retrieve station data: {self._lastres.status}/{text}"
            )

    async def set_state(
        self, entity: Entity, shadow: str, topic: str, definition: Dict
    ):
        station = entity.station
        t = datetime.now(timezone.utc)
        timestamp = t.strftime("%Y%m%d%H%M%S")

        desired = {
            "deviceSN": entity.sn,
            "shadow": shadow,
            "stationSN": station.sn,
            "time": timestamp,
            "userId": self.userid,
        }
        desired.update(definition.get("extra", {}))
        action_data = definition.get("data", {})
        if callable(action_data):
            action_data = action_data(entity)
        desired.update(action_data)

        data = {"state": {"desired": desired}}

        return await self.do_thing(station, topic, data)

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
        "supportAntiFlicker": data.get("antiflickerSupport"),
        "supportAlarm": device_support.get("deviceSupportAlarm"),
        "supportAlarmVolume": device_support.get("supportAlarmVolume"),
        "supportBattery": device_model.get("canStandby"),
        "supportChargeAutoPowerOn": device_support.get("supportChargeAutoPowerOn"),
        "supportCryDetect": device_support.get("supportCryDetect"),
        "supportDeviceCall": device_support.get("supportDeviceCall"),
        "supportDoorBellAlarm": device_support.get("supportAlarmWhenRemoveToggle"),
        "supportLiveAudio": device_support.get("supportLiveAudioToggle"),
        "supportLight": device_model.get("whiteLight"),
        "supportMechanicalDingDong": device_support.get("supportMechanicalDingDong"),
        "supportMirrorFlip": device_support.get("deviceSupportMirrorFlip"),
        "supportMotionTrack": device_model.get("supportMotionTrack"),
        "supportPersonDetect": False,
        "supportPirCooldown": device_support.get("supportPirCooldown"),
        "supportRecLamp": device_support.get("supportRecLamp"),
        "supportRecordingAudio": device_support.get("supportRecordingAudioToggle"),
        "supportRocker": device_model.get("canRotate"),
        "supportSdCard": sd_card.get("formatStatus") not in (None, 23),
        "supportSleep": device_support.get("deviceDormancySupport"),
        "supportLiveSpeakerVolume": device_support.get("supportLiveSpeakerVolume"),
        "supportedRecordingResolutions": device_support.get("deviceSupportResolution"),
        "supportVoiceVolume": device_support.get("supportVoiceVolume"),
        "supportWebrtc": device_support.get("supportWebrtc"),
        "thumbImgTime": data.get("thumbImgTime"),
        "thumbImgUrl": data.get("thumbImgUrl"),
        "timeZone": data.get("timeZone"),
        "timeZoneArea": data.get("timeZoneArea"),
        "wifiChannel": data.get("wifiChannel"),
        "wiredMacAddress": data.get("wiredMacAddress"),
    }


def _camera_config_data(data: Dict) -> Dict:
    cooldown = data.get("cooldown") or {}
    return {
        "alarmSeconds": data.get("alarmSeconds"),
        "alarmVol": data.get("alarmVolume"),
        "antiflicker": data.get("antiflicker"),
        "antiflickerSwitch": data.get("antiflickerSwitch"),
        "chargeAutoPowerOnCapacity": data.get("chargeAutoPowerOnCapacity"),
        "chargeAutoPowerOnCapacityOptions": data.get(
            "chargeAutoPowerOnCapacityOptions"
        ),
        "chargeAutoPowerOnSwitch": data.get("chargeAutoPowerOnSwitch"),
        "cooldownSupported": cooldown.get("deviceSupport"),
        "cooldownEnabled": cooldown.get("userEnable"),
        "cooldownOptions": cooldown.get("notCloseValues") or data.get("coolDownValues"),
        "cooldownValue": cooldown.get("value"),
        "cryDetect": data.get("cryDetect"),
        "cryDetectLevel": data.get("cryDetectLevel"),
        "deviceCallToggleOn": data.get("deviceCallToggleOn"),
        "deviceLanguage": data.get("deviceLanguage"),
        "devicePersonDetect": data.get("devicePersonDetect"),
        "deviceSupportLanguage": data.get("deviceSupportLanguage"),
        "mechanicalDingDongDuration": data.get("mechanicalDingDongDuration"),
        "mechanicalDingDongSwitch": data.get("mechanicalDingDongSwitch"),
        "mirrorFlip": data.get("mirrorFlip"),
        "motionSensitivity": data.get("motionSensitivity"),
        "motionSensitivityOptionList": data.get("motionSensitivityOptionList"),
        "motionTrack": data.get("motionTrack"),
        "motionTrackMode": data.get("motionTrackMode"),
        "needAlarm": data.get("needAlarm"),
        "needMotion": data.get("needMotion"),
        "needNightVision": data.get("needNightVision"),
        "needVideo": data.get("needVideo"),
        "nightThresholdLevel": data.get("nightThresholdLevel"),
        "nightVisionMode": data.get("nightVisionMode"),
        "recLamp": data.get("recLamp"),
        "timeZone": data.get("timeZone"),
        "timeZoneArea": data.get("timeZoneArea"),
        "videoSeconds": data.get("videoSeconds"),
        "videoSecondsValues": data.get("videoSecondsValues"),
        "voiceVol": data.get("voiceVolume"),
        "voiceVolumeSwitch": data.get("voiceVolumeSwitch"),
        "whiteLightScintillation": data.get("whiteLightScintillation"),
    }


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
        "liveAudioToggleOn": audio.get("liveAudioToggleOn"),
        "liveSpeakerVolume": audio.get("liveSpeakerVolume"),
        "recordingAudioToggleOn": audio.get("recordingAudioToggleOn"),
    }


def _camera_doorbell_data(data: Dict) -> Dict:
    doorbell_config = data.get("doorbellConfig") or data
    return {
        "alarmWhenRemoveToggleOn": doorbell_config.get("alarmWhenRemoveToggleOn"),
    }
