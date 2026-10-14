from datetime import datetime

import requests

from .aws_signer import AWSSigner
from .base import XSenseBase
from .entity import Entity
from .entity_map import entities
from .exceptions import APIFailure, SessionExpired, XSenseError
from .house import House
from .station import Station


class XSense(XSenseBase):
    def __init__(self, session=None):
        super().__init__()
        self.session = session or requests.Session()
        self._owns_session = session is None

    def close(self):
        if self._owns_session:
            self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()

    def api_call(self, code, unauth=False, **kwargs):
        data = {
            **kwargs
        }

        if unauth:
            headers = None
            mac = 'abcdefg'
        else:
            if self._access_token_expiring():
                self.refresh()
            headers = {'Authorization': self.access_token}
            mac = self._calculate_mac(data)

        res = self.session.post(
            f'{self.API}/app',
            json={
                **data,
                "clientType": self.CLIENTYPE,
                "mac": mac,
                "appVersion": self.VERSION,
                "bizCode": code,
                "appCode": self.APPCODE,
            },
            headers=headers
        )
        self._lastres = res

        data = res.json()
        if res.status_code >= 400:
            message = data.get('message') or 'unknown error'
            raise APIFailure(f'API failure: {res.status_code}/{message}')

        if 'reCode' not in data:
            raise APIFailure('API failure: Cannot understand response')

        if data['reCode'] != 200:
            errCode = data.get('errCode', 0)
            if errCode in ('10000008', '10000020'):
                raise SessionExpired(data.get('reMsg'))
            raise APIFailure(f"Request for code {code} failed with error {errCode}/{data['reCode']} {data.get('reMsg')}")

        return data['reData']

    def get_house(self, house: House, page: str):
        if self._aws_token_expiring():
            self.load_aws()

        url, headers = self._house_request(house, page)
        res = self.session.get(url, headers=headers)
        self._lastres = res
        return res.json()

    def get_thing(self, station: Station, page: str):
        if self._aws_token_expiring():
            self.load_aws()

        url, headers = self._thing_request(station, page)
        res = self.session.get(url, headers=headers)
        self._lastres = res
        return res.json()

    def do_thing(self, station: Station, page: str, data: dict):
        if self._aws_token_expiring():
            self.load_aws()

        url, headers = self._thing_request(station, page, data)
        res = self.session.post(url, headers=headers, json=data)
        self._lastres = res
        return res.json()

    def login(self, username, password):
        self.sync_login(username, password)
        self.load_aws()

    def refresh(self):
        url, data, headers = self._refresh_request()

        res = self.session.post(
            url,
            json=data,
            headers=headers
        )
        self._lastres = res
        data = res.json()

        if res.status_code == 400:
            raise SessionExpired(data.get('message', 'token refresh failed'))

        self._parse_refresh_result(data.get('AuthenticationResult', {}))

    def init(self):
        self.get_client_info()

    def load_aws(self):
        self.get_aws_tokens()
        if self.signer:
            self.signer.update(self.aws_access_key, self.aws_secret_access_key, self.aws_session_token)
        else:
            self.signer = AWSSigner(self.aws_access_key, self.aws_secret_access_key, self.aws_session_token)

    def load_all(self):
        result = {}
        for i in self.get_houses():
            h = House(
                self.signer,
                i['houseId'],
                i['houseName'],
                i['houseRegion'],
                i['mqttRegion'],
                i['mqttServer']
            )
            result[i['houseId']] = h

            if rooms := self.get_rooms(h.house_id):
                h.set_rooms(rooms)

            if station := self.get_stations(h.house_id):
                h.set_stations(station)
        self.houses = result

    def get_client_info(self):
        data = self.api_call("101001", unauth=True)
        self.clientid = data['clientId']
        self.clientsecret = self._decode_secret(data['clientSecret'])
        self.region = data['cgtRegion']
        self.userpool = data['userPoolId']

    def get_aws_tokens(self):
        data = self.api_call("101003", userName=self.username)
        self.aws_access_key = data['accessKeyId']
        self.aws_secret_access_key = data['secretAccessKey']
        self.aws_session_token = data['sessionToken']
        self.aws_access_expiry = datetime.strptime(data['expiration'], "%Y-%m-%d %H:%M:%S%z")

    def get_houses(self):
        params = {
            'utctimestamp': "0"
        }
        return self.api_call("102007", **params)

    def get_rooms(self, houseId: str):
        params = {
            'houseId': houseId,
            'utctimestamp': "0"
        }
        return self.api_call("102008", **params)

    def get_stations(self, houseId: str):
        params = {
            'houseId': houseId,
            'utctimestamp': "0"
        }
        return self.api_call("103007", **params)

    def get_history(self, houseId: str, dayTime: str, timeZone: str, nextToken: str | None = None):
        params = {
            'houseId': houseId,
            'dayTime': dayTime,
            'timeZone': timeZone,
        }
        if nextToken:
            params['nextToken'] = nextToken
        return self.api_call("104001", **params)

    def get_history_month(self, houseId: str, hisMonth: str, timeZone: str):
        params = {
            'houseId': houseId,
            'hisMonth': hisMonth,
            'timeZone': timeZone,
        }
        return self.api_call("104006", **params)

    def get_station_history(
        self,
        houseId: str,
        stationId: str,
        dayTime: str,
        timeZone: str,
        deviceId: str | None = None,
        nextToken: str | None = None,
    ):
        params = {
            'houseId': houseId,
            'dayTime': dayTime,
            'timeZone': timeZone,
            'stationId': stationId,
        }
        if deviceId:
            params['deviceId'] = deviceId
        if nextToken:
            params['nextToken'] = nextToken
        return self.api_call("104007", **params)

    def get_station_history_month(
        self,
        houseId: str,
        stationId: str,
        deviceId: str,
        hisMonth: str,
        timeZone: str,
    ):
        params = {
            'houseId': houseId,
            'hisMonth': hisMonth,
            'timeZone': timeZone,
            'stationId': stationId,
            'deviceId': deviceId,
        }
        return self.api_call("104008", **params)

    def get_security_history(self, serverId: str, nextToken: str | None = None):
        params = {
            'serverId': serverId,
        }
        if nextToken:
            params['nextToken'] = nextToken
        return self.api_call("505001", **params)

    def get_sth_history(
        self,
        houseId: str,
        stationId: str,
        lastTime: str = "",
        nextToken: str | None = None,
    ):
        params = {
            'houseId': houseId,
            'stationId': stationId,
            'lastTime': lastTime,
        }
        if nextToken:
            params['nextToken'] = nextToken
        return self.api_call("104020", **params)

    def get_co_ppm_history(self, stationId: str, timeZone: str, deviceId: str | None = None):
        params = {
            'stationId': stationId,
            'timeZone': timeZone,
        }
        if deviceId:
            params['deviceId'] = deviceId
            return self.api_call("104009", **params)
        return self.api_call("104014", **params)

    def get_co_ppm_history_details(
        self,
        houseId: str,
        stationId: str,
        dayTime: str,
        timeZone: str,
        deviceId: str | None = None,
    ):
        params = {
            'houseId': houseId,
            'stationId': stationId,
            'dayTime': dayTime,
            'timeZone': timeZone,
        }
        if deviceId:
            params['deviceId'] = deviceId
            return self.api_call("104010", **params)
        return self.api_call("104015", **params)

    def get_house_state(self, house: House):
        for page in ('mainpage', '2nd_mainpage'):
            res = self.get_house(house, page)

            if self._lastres.status_code == 404:
                continue

            if 'reported' in res.get('state', {}):
                self._parse_get_house_state(house, res['state']['reported'])
            # else:
            #     raise APIFailure(f'Unable to retrieve station data: {self._lastres.status_code}/{self._lastres.text}')

    def get_alarm_state(self, station: Station):
        res = self.get_thing(station, '2nd_safemode')

        if self._lastres.status_code == 404:
            return

        if 'reported' in res.get('state', {}):
            station.set_alarm_data(res['state']['reported'])

    def get_station_state(self, station: Station):
        res = None
        if station.type not in ('SBS50', 'SC07-WX', 'XC04-WX'):
            res = self.get_thing(station, f'info_{station.sn}')

        if res is None or self._lastres.status_code == 404:
            res = self.get_thing(station, f'2nd_info_{station.sn}')

        if self._lastres.status_code == 404:
            return

        if 'reported' in res.get('state', {}):
            station.set_data(res['state']['reported'])
        else:
            raise APIFailure(f'Unable to retrieve station data: {self._lastres.status_code}/{self._lastres.text}')

    def get_state(self, station: Station):
        if not station.devices:
            return

        res = None
        if station.type not in ('SBS10',):
            res = self.get_thing(station, '2nd_mainpage')

        if res is None or self._lastres.status_code == 404:
            res = self.get_thing(station, 'mainpage')

        if 'reported' in res.get('state', {}):
            self.parse_get_state(station, res['state']['reported'])
        else:
            raise APIFailure(f'Unable to retrieve station data: {self._lastres.status_code}/{self._lastres.text}')

    def set_state(self, entity: Entity, shadow: str, topic: str, definition: dict):
        station = entity.station
        t = datetime.now()
        timestamp = t.strftime('%Y%m%d%H%M%S')

        desired = {
            "deviceSN": entity.sn,
            "shadow": shadow,
            "stationSN": station.sn,
            "time": timestamp,
            "userId": self.userid
        }
        desired.update(definition.get('extra', {}))

        data = {"state": {"desired": desired}}

        self.do_thing(station, topic, data)

    def action(self, entity: Entity, action: str):
        entity_def = entities.get(entity.type)
        if not entity_def:
            raise XSenseError(f'Entity type {entity.type} is unkown, action {action} not possible')

        action_def = next((a for a in entity_def.get('actions', []) if a.get('action') == action), None)
        if not action_def:
            raise XSenseError(f'Action {action} is not supported for entity type {entity.type}')

        topic = action_def.get('topic')
        if callable(topic):
            topic = topic(entity)
        self.set_state(entity, action_def['shadow'], topic, action_def)
