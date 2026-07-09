import base64
import binascii
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Dict

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from pycognito import AWSSRP

from .entity import Entity
from .entity_map import entities
from .exceptions import APIFailure, AuthFailed
from .station import Station
from .house import House


def _mac_json(value) -> str:
    """Return compact Gson-style JSON for X-Sense MAC input."""
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def _mac_scalar(value) -> str:
    """Return the Java StringBuilder text used by the app MAC input."""
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value)


def _jwt_claim(token: str | None, claim: str):
    if not token:
        return None
    try:
        payload = token.split('.')[1]
        padding = '=' * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload + padding)
        claims = json.loads(decoded)
    except (
        IndexError,
        TypeError,
        ValueError,
        UnicodeDecodeError,
        binascii.Error,
        json.JSONDecodeError,
    ):
        return None
    value = claims.get(claim)
    return str(value) if value is not None else None


def shadow_update_body(data: Dict) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(',', ':'))


_COGNITO_CLIENT_CONFIG = Config(
    connect_timeout=15,
    read_timeout=15,
    retries={'total_max_attempts': 4, 'mode': 'standard'},
)


class XSenseBase:
    API = 'https://api.x-sense-iot.com'
    VERSION = "v1.36.0_20260130"
    APPCODE = "1360"
    CLIENTYPE = "2"
    IPC_API = 'https://ipc.x-sense-iot.com'
    ADDX_API_BY_NODE = {
        'CN': 'https://api.addx.live',
        'EU': 'https://api-eu.vicohome.io',
        'US': 'https://api-us.vicohome.io',
    }
    IPC_VERSION = VERSION
    IPC_APPCODE = APPCODE
    IPC_CLIENTTYPE = CLIENTYPE

    ADDX_APP_NAME = 'VicoHome'
    ADDX_APP_BUNDLE = 'com.ai.vicoo'
    ADDX_APP_CHANNEL_ID = 1000
    ADDX_APP_COUNTLY_ID = 'b940908f19b8e858'
    ADDX_APP_TENANT_ID = 'guard'
    ADDX_APP_VERSION = 200700500
    ADDX_APP_VERSION_NAME = '2.7.5'

    userid = None
    user_id_code = None
    username = None
    clientid = None
    clientsecret = None
    userpool = None
    region = None

    access_token = None
    id_token = None
    refresh_token = None
    access_token_expiry = None

    aws_access_key = None
    aws_secret_access_key = None
    aws_session_token = None
    aws_access_expiry = None

    signer = None

    _lastres = None

    def __init__(self):
        self.houses: Dict[str, House] = {}
        self._addx_session = None

    def _parse_client_error(self, e: ClientError):
        return e.response.get('Error', {}).get('Message') or str(e)

    def sync_login(self, username, password):
        self.username = username
        session = boto3.Session()
        cognito = session.client(
            'cognito-idp', region_name=self.region, config=_COGNITO_CLIENT_CONFIG
        )

        aws_srp = AWSSRP(
            username=username,
            password=password,
            pool_id=self.userpool,
            client_id=self.clientid,
            client=cognito
        )

        auth_params = aws_srp.get_auth_params()
        if self.clientsecret:
            auth_params['SECRET_HASH'] = self.generate_hash(username + self.clientid)

        try:
            response = cognito.initiate_auth(
                ClientId=self.clientid,
                AuthFlow='USER_SRP_AUTH',
                AuthParameters=auth_params
            )
        except ClientError as e:
            raise AuthFailed(self._parse_client_error(e)) from e
        except BotoCoreError as e:
            raise APIFailure(f'Cognito connection failed: {e}') from e

        self.userid = response['ChallengeParameters']['USERNAME']

        challenge_response = aws_srp.process_challenge(response["ChallengeParameters"], auth_params)

        if self.clientsecret:
            challenge_response['SECRET_HASH'] = self.generate_hash(self.userid + self.clientid)

        try:
            response = cognito.respond_to_auth_challenge(
                ClientId=self.clientid,
                ChallengeName='PASSWORD_VERIFIER',
                ChallengeResponses=challenge_response
            )

            auth_result = response['AuthenticationResult']
            self.access_token = auth_result['AccessToken']
            self.id_token = auth_result['IdToken']
            self.refresh_token = auth_result['RefreshToken']
            self._set_user_id_code_from_tokens()
            self.access_token_expiry = datetime.now(timezone.utc) + timedelta(seconds=auth_result['ExpiresIn'])

        except ClientError as e:
            raise AuthFailed(self._parse_client_error(e)) from e
        except BotoCoreError as e:
            raise APIFailure(f'Cognito connection failed: {e}') from e

    _cognito_login = sync_login

    def restore_session(self, username, access_token, refresh_token, id_token):
        self.username = username
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.id_token = id_token
        self._set_user_id_code_from_tokens()
        self.access_token_expiry = datetime.now(timezone.utc)
        self.aws_access_expiry = datetime.now(timezone.utc)

    def _set_user_id_code_from_tokens(self):
        self.user_id_code = None
        for token in (self.id_token, self.access_token):
            if user_id_code := _jwt_claim(token, 'user_id_code'):
                self.user_id_code = user_id_code
                return

    def _access_token_expiring(self):
        return datetime.now(timezone.utc) > self.access_token_expiry - timedelta(seconds=60)

    def _aws_token_expiring(self):
        return datetime.now(timezone.utc) > self.aws_access_expiry - timedelta(seconds=60)

    def _decode_secret(self, encoded):
        value = base64.b64decode(encoded)
        return value[4:-1]

    def _calculate_mac(self, data):
        values = []
        if data:
            for key in data:
                value = data[key]
                if isinstance(value, list):
                    if not value:
                        continue
                    if isinstance(value[0], str):
                        values.extend(_mac_scalar(item) for item in value)
                    else:
                        values.append(_mac_json(value))
                elif isinstance(value, dict):
                    values.append(_mac_json(value))
                else:
                    values.append(_mac_scalar(value))

        concatenated_string = ''.join(values)
        mac_data = concatenated_string.encode('utf-8') + self.clientsecret
        return hashlib.md5(mac_data).hexdigest()

    def _signed_body(self, data: Dict | None, code: str, *, ipc: bool = False) -> Dict:
        data = dict(data or {})
        data['mac'] = self._calculate_mac(data)
        data['bizCode'] = code
        data['appCode'] = self.IPC_APPCODE if ipc else self.APPCODE
        data['appVersion'] = self.IPC_VERSION if ipc else self.VERSION
        data['clientType'] = self.IPC_CLIENTTYPE if ipc else self.CLIENTYPE
        return data

    def generate_hash(self, data):
        return base64.b64encode(
            hmac.new(
                self.clientsecret,
                bytes(data, 'utf-8'),
                digestmod=hashlib.sha256
            ).digest()
        ).decode()

    def _refresh_request(self):
        url = f'https://cognito-idp.{self.region}.amazonaws.com'
        data = {
            "AuthFlow": "REFRESH_TOKEN_AUTH",
            "AuthParameters": {
                "REFRESH_TOKEN": self.refresh_token,
                "SECRET_HASH": self.clientsecret.decode()
            },
            "ClientId": self.clientid,
            "UserContextData": {}
        }
        t = datetime.now(timezone.utc)
        amz_date = t.strftime('%Y%m%dT%H%M%SZ')
        headers = {
            'x-amz-date': amz_date,
            'x-amz-target': 'AWSCognitoIdentityProviderService.InitiateAuth',
            'content-type': 'application/x-amz-json-1.1'
        }
        return url, data, headers

    def _house_request(self, house: House, page: str):
        headers = {
            'Content-Type': 'application/x-amz-json-1.0',
            'User-Agent': 'aws-sdk-iOS/2.26.5 iOS/17.3 nl_NL',
            'X-Amz-Security-Token': self.aws_session_token
        }

        host = f'{house.mqtt_region}.x-sense-iot.com'
        uri = f'/things/{house.house_id}/shadow?name={page}'

        url = f'https://{host}{uri}'

        signed = self.signer.sign_headers('GET', url, house.mqtt_region, headers, None)
        headers |= signed

        return url, headers

    def _thing_request(self, station: Station, page: str, data=None):
        headers = {
            'Content-Type': 'application/x-amz-json-1.0',
            'User-Agent': 'aws-sdk-iOS/2.26.5 iOS/17.3 nl_NL',
            'X-Amz-Security-Token': self.aws_session_token
        }

        thing_name = _thing_name(station)

        host = f'{station.house.mqtt_region}.x-sense-iot.com'
        uri = f'/things/{thing_name}/shadow?name={page}'

        url = f'https://{host}{uri}'

        method = 'POST' if data else 'GET'
        signed = self.signer.sign_headers(method, url, station.house.mqtt_region, headers, data)
        headers |= signed

        return url, headers

    def _parse_refresh_result(self, data: Dict):
        if 'RefreshToken' in data:
            self.refresh_token = data['RefreshToken']
        if 'AccessToken' in data:
            self.access_token = data['AccessToken']
        if 'IdToken' in data:
            self.id_token = data['IdToken']
        self._set_user_id_code_from_tokens()
        if 'ExpiresIn' in data:
            self.access_token_expiry = datetime.now(timezone.utc) + timedelta(seconds=data['ExpiresIn'])

    def parse_get_state(self, station: Station, data: Dict):
        if isinstance(data, list):
            station_data = {}
            children = data
        else:
            station_data = data.copy()
            children = station_data.pop('devs', {}) or {}

        children = _merge_top_level_child_state(station, station_data, children)

        if _apply_group_light_state(station, station_data, children):
            return

        _normalize_apk_alarm_status(station_data)
        has_alarm_status = 'alarmStatus' in station_data or 'a' in station_data
        if station_data:
            station.set_data(station_data)
        if 'safeMode' in station_data:
            station.safe_mode = station_data['safeMode']

        station.has_alarm = _is_active_state(station_data.get('activate')) or (
            has_alarm_status and _is_active_state(station.data.get('alarmStatus'))
        )

        for child_key, child_state in _child_state_items(children):
            if dev := _state_child_device(station, child_key, child_state):
                _apply_apk_child_context(station_data, dev, child_state)
                _normalize_apk_alarm_status(child_state)
                dev.set_data(child_state)

    def _parse_get_house_state(self, house: House, data: Dict):
        for sn, i in data.items():
            if station := house.get_station_by_sn(sn):
                self.parse_get_state(station, i)

    def station_by_sn(self, serial_number: str | None):
        """Return the station with this station serial number."""
        if not serial_number:
            return None
        for house in self.houses.values():
            if station := house.get_station_by_sn(serial_number):
                return station
        return None

    def station_by_shadow_name(self, shadow_name: str | None):
        """Return the station matching an AWS IoT shadow thing name."""
        if not shadow_name:
            return None
        for house in self.houses.values():
            for station in house.stations.values():
                if station.shadow_name == shadow_name:
                    return station
        return None

    def station_by_device_sn(self, serial_number: str | None):
        """Return the station containing this station or child device serial."""
        if not serial_number:
            return None
        for house in self.houses.values():
            for station in house.stations.values():
                if station.sn == serial_number or station.get_device_by_sn(serial_number):
                    return station
        return None

    def apply_safe_mode(self, station: Station, safe_mode) -> None:
        """Store safeMode consistently for HTTP polling and MQTT updates."""
        station.safe_mode = safe_mode
        station.set_data({"safeMode": safe_mode})

    def action_definition(self, entity: Entity, action: str) -> Dict | None:
        """Return the supported action definition for an entity, if resolvable."""
        entity_def = entities.get(entity.type)
        if not entity_def:
            return None
        action_def = next(
            (a for a in entity_def.get('actions', []) if a.get('action') == action),
            None,
        )
        if action_def is None or not _action_route_resolves(entity, action_def):
            return None
        return action_def

    def has_action(self, entity: Entity, action: str):
        return self.action_definition(entity, action) is not None


def _action_route_resolves(entity: Entity, action_def: Dict) -> bool:
    """Return whether an app shadow action can resolve for this entity context."""
    if not getattr(entity, 'sn', None):
        return False
    try:
        topic = _resolve_action_value(action_def.get('topic'), entity)
        shadow = _resolve_action_value(action_def.get('shadow'), entity)
        target = _resolve_action_value(action_def.get('target'), entity)
        extra = _resolve_action_value(action_def.get('extra', {}), entity)
        data = _resolve_action_value(action_def.get('data', {}), entity)
    except (AttributeError, TypeError, KeyError, ValueError):
        return False

    if not topic or not shadow:
        return False
    if not isinstance(extra, dict) or not isinstance(data, dict):
        return False

    target = target if target is not None else getattr(entity, 'station', entity)
    return bool(getattr(target, 'shadow_name', None) or getattr(target, 'sn', None))


def _resolve_action_value(value, entity: Entity):
    """Return an action value, resolving callables against the entity."""
    if callable(value):
        return value(entity)
    return value


def _state_child_device(station: Station, child_key, child_state):
    """Return the child device targeted by an app shadow payload."""
    for value in _child_state_identifiers(child_key, child_state):
        getter = getattr(station, "get_device_by_identifier", None)
        if getter is not None:
            if dev := getter(value):
                return dev
        if dev := station.get_device_by_sn(value):
            return dev
    return None


def _merge_top_level_child_state(station: Station, station_data: Dict, children):
    """Move APK child-id keyed shadow records into the child update collection."""
    if isinstance(children, dict):
        child_updates = children.copy()
    elif isinstance(children, list):
        child_updates = list(children)
    else:
        child_updates = children
    for key in list(station_data):
        value = station_data[key]
        if not isinstance(value, dict):
            continue
        getter = getattr(station, "get_device_by_identifier", None)
        device = getter(key) if getter is not None else None
        if device is None and station.get_device_by_sn(key):
            device = station.get_device_by_sn(key)
        if device is None:
            continue
        if isinstance(child_updates, list):
            child_state = value.copy()
            child_state.setdefault("_deviceSN", key)
            child_updates.append(child_state)
            station_data.pop(key)
            continue
        if not isinstance(child_updates, dict):
            child_updates = {}
        child_updates[key] = station_data.pop(key)
    return child_updates


def _child_state_items(children):
    """Yield child device shadow records in the list/dict forms used by the app."""
    if isinstance(children, dict):
        yield from children.items()
    elif isinstance(children, list):
        for child_state in children:
            if isinstance(child_state, dict):
                yield None, child_state


def _child_state_identifiers(child_key, child_state) -> tuple[str, ...]:
    """Return device serial identifiers used by X-Sense child shadows."""
    values = [child_key]
    if isinstance(child_state, dict):
        values.extend(
            child_state.get(key)
            for key in (
                "deviceSN",
                "deviceSn",
                "_deviceSN",
                "_deviceSn",
                "devSerialNumber",
                "serialNumber",
                "sn",
            )
        )
    seen = set()
    result = []
    for value in values:
        if value is None:
            continue
        text = str(value)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return tuple(result)


def _apply_group_light_state(station: Station, station_data: Dict, children) -> bool:
    group_id = station_data.get('groupId')
    if group_id is None:
        return False

    group = station.get_group_device(group_id)
    if group is None:
        return False

    group_data = station_data.copy()
    if 'isOn' in group_data:
        group_data['on'] = group_data['isOn']
    if isinstance(children, list):
        group_data['devs'] = children
    group.set_data(group_data)
    return True


def _is_active_state(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value == 1
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'on', 'active', 'alarm'}
    return False


def _normalize_apk_alarm_status(data: Dict) -> None:
    """Mirror APK alarm topic state into the canonical alarmStatus key."""
    if "alarmStatus" in data or "a" in data:
        return
    if "isAlarm" in data:
        data["alarmStatus"] = data["isAlarm"]


def _apply_apk_child_context(station_data: Dict, child: Entity, child_state: Dict) -> None:
    """Apply APK parent shadow fields that belong to specific child devices."""
    if "coLevel" not in station_data or "coLevel" in child_state:
        return
    entity_def = entities.get(child.type, {})
    if getattr(entity_def.get("type"), "value", None) == "co":
        child_state["coLevel"] = station_data["coLevel"]


def _thing_name(station: Station) -> str:
    """Return the AWS IoT thing name used by the X-Sense app."""
    return station.shadow_name
