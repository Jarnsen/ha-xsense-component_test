import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Dict

import boto3
from botocore.exceptions import ClientError
from pycognito import AWSSRP

from .entity import Entity
from .entity_map import entities
from .exceptions import AuthFailed
from .station import Station
from .house import House


class XSenseBase:
    API = "https://api.x-sense-iot.com"
    IPC_API = "https://ipc.x-sense-iot.com"
    ADDX_API_BY_NODE = {
        "CN": "https://api.addx.live",
        "EU": "https://api-eu.vicohome.io",
        "US": "https://api-us.vicohome.io",
    }
    VERSION = "v1.22.0_20240914.1"
    APPCODE = "1220"
    CLIENTYPE = "1"
    IPC_VERSION = "v1.36.0_20260130"
    IPC_APPCODE = "1360"
    IPC_CLIENTTYPE = "2"

    userid = None
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
        return e.response.get("Error", {}).get("Message") or str(e)

    def sync_login(self, username, password):
        self.username = username
        session = boto3.Session()
        cognito = session.client("cognito-idp", region_name=self.region)

        aws_srp = AWSSRP(
            username=username,
            password=password,
            pool_id=self.userpool,
            client_id=self.clientid,
            client=cognito,
        )

        auth_params = aws_srp.get_auth_params()
        if self.clientsecret:
            auth_params["SECRET_HASH"] = self.generate_hash(username + self.clientid)

        try:
            response = cognito.initiate_auth(
                ClientId=self.clientid,
                AuthFlow="USER_SRP_AUTH",
                AuthParameters=auth_params,
            )
        except ClientError as e:
            raise AuthFailed(self._parse_client_error(e)) from e

        self.userid = response["ChallengeParameters"]["USERNAME"]

        challenge_response = aws_srp.process_challenge(
            response["ChallengeParameters"], auth_params
        )

        if self.clientsecret:
            challenge_response["SECRET_HASH"] = self.generate_hash(
                self.userid + self.clientid
            )

        try:
            response = cognito.respond_to_auth_challenge(
                ClientId=self.clientid,
                ChallengeName="PASSWORD_VERIFIER",
                ChallengeResponses=challenge_response,
            )

            auth_result = response["AuthenticationResult"]
            self.access_token = auth_result["AccessToken"]
            self.id_token = auth_result["IdToken"]
            self.refresh_token = auth_result["RefreshToken"]
            self.access_token_expiry = datetime.now(timezone.utc) + timedelta(
                seconds=auth_result["ExpiresIn"]
            )

        except ClientError as e:
            raise AuthFailed(self._parse_client_error(e)) from e

    def restore_session(self, username, access_token, refresh_token, id_token):
        self.username = username
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.id_token = id_token
        self.access_token_expiry = datetime.now(timezone.utc)
        self.aws_access_expiry = datetime.now(timezone.utc)

    def _access_token_expiring(self):
        return datetime.now(timezone.utc) > self.access_token_expiry - timedelta(
            seconds=60
        )

    def _aws_token_expiring(self):
        return datetime.now(timezone.utc) > self.aws_access_expiry - timedelta(
            seconds=60
        )

    def _decode_secret(self, encoded):
        value = base64.b64decode(encoded)
        return value[4:-1]

    def _calculate_mac(self, data):
        values = []
        if data:
            for key in data:
                value = data[key]
                if isinstance(value, list):
                    if value and isinstance(value[0], str):
                        values.extend(value)
                    else:
                        values.append(json.dumps(value))
                elif isinstance(value, dict):
                    values.append(json.dumps(value, separators=(",", ":")))
                else:
                    values.append(str(value))

        concatenated_string = "".join(values)
        mac_data = concatenated_string.encode("utf-8") + self.clientsecret
        return hashlib.md5(mac_data).hexdigest()

    def _signed_body(self, data: Dict | None, code: str, *, ipc: bool = False) -> Dict:
        data = dict(data or {})
        data["mac"] = self._calculate_mac(data)
        data["bizCode"] = code
        data["appCode"] = self.IPC_APPCODE if ipc else self.APPCODE
        data["appVersion"] = self.IPC_VERSION if ipc else self.VERSION
        data["clientType"] = self.IPC_CLIENTTYPE if ipc else self.CLIENTYPE
        return data

    def generate_hash(self, data):
        return base64.b64encode(
            hmac.new(
                self.clientsecret, bytes(data, "utf-8"), digestmod=hashlib.sha256
            ).digest()
        ).decode()

    def _refresh_request(self):
        url = f"https://cognito-idp.{self.region}.amazonaws.com"
        data = {
            "AuthFlow": "REFRESH_TOKEN_AUTH",
            "AuthParameters": {
                "REFRESH_TOKEN": self.refresh_token,
                "SECRET_HASH": self.clientsecret.decode(),
            },
            "ClientId": self.clientid,
            "UserContextData": {},
        }
        t = datetime.now(timezone.utc)
        amz_date = t.strftime("%Y%m%dT%H%M%SZ")
        headers = {
            "x-amz-date": amz_date,
            "x-amz-target": "AWSCognitoIdentityProviderService.InitiateAuth",
            "content-type": "application/x-amz-json-1.1",
        }
        return url, data, headers

    def _house_request(self, house: House, page: str):
        headers = {
            "Content-Type": "application/x-amz-json-1.0",
            "User-Agent": "aws-sdk-iOS/2.26.5 iOS/17.3 nl_NL",
            "X-Amz-Security-Token": self.aws_session_token,
        }

        host = f"{house.mqtt_region}.x-sense-iot.com"
        uri = f"/things/{house.house_id}/shadow?name={page}"

        url = f"https://{host}{uri}"

        signed = self.signer.sign_headers("GET", url, house.mqtt_region, headers, None)
        headers |= signed

        return url, headers

    def _thing_request(self, station: Station, page: str, data=None):
        headers = {
            "Content-Type": "application/x-amz-json-1.0",
            "User-Agent": "aws-sdk-iOS/2.26.5 iOS/17.3 nl_NL",
            "X-Amz-Security-Token": self.aws_session_token,
        }

        thing_name = _thing_name(station)

        host = f"{station.house.mqtt_region}.x-sense-iot.com"
        uri = f"/things/{thing_name}/shadow?name={page}"

        url = f"https://{host}{uri}"

        method = "POST" if data else "GET"
        signed = self.signer.sign_headers(
            method, url, station.house.mqtt_region, headers, data
        )
        headers |= signed

        return url, headers

    def _parse_refresh_result(self, data: Dict):
        if "RefreshToken" in data:
            self.refresh_token = data["RefreshToken"]
        if "AccessToken" in data:
            self.access_token = data["AccessToken"]
        if "IdToken" in data:
            self.id_token = data["IdToken"]
        if "ExpiresIn" in data:
            self.access_token_expiry = datetime.now(timezone.utc) + timedelta(
                seconds=data["ExpiresIn"]
            )

    def parse_get_state(self, station: Station, data: Dict):
        station_data = data.copy()
        children = station_data.pop("devs", {}) or {}

        if station_data:
            station.set_data(station_data)

        station.has_alarm = _is_active_state(data.get("activate")) or _is_active_state(
            station.data.get("alarmStatus")
        )

        for sn, i in children.items():
            if dev := station.get_device_by_sn(sn):
                dev.set_data(i)

    def _parse_get_house_state(self, house: House, data: Dict):
        for sn, i in data.items():
            if station := house.get_station_by_sn(sn):
                self.parse_get_state(station, i)

    def has_action(self, entity: Entity, action: str):
        if entity_def := entities.get(entity.type):
            return any(
                a for a in entity_def.get("actions", []) if a.get("action") == action
            )
        return False


def _is_active_state(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value == 1
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "on", "active", "alarm"}
    return False


def _thing_name(station: Station) -> str:
    """Return the AWS IoT thing name used by the X-Sense app."""
    return station.shadow_name
