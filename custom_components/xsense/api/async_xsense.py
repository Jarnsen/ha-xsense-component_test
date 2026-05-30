import asyncio
from datetime import datetime
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
        if not station.devices:
            return

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
        t = datetime.now()
        timestamp = t.strftime("%Y%m%d%H%M%S")

        desired = {
            "deviceSN": entity.sn,
            "shadow": shadow,
            "stationSN": station.sn,
            "time": timestamp,
            "userId": self.userid,
        }
        desired.update(definition.get("extra", {}))

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
        return await self.set_state(entity, action_def["shadow"], topic, action_def)
