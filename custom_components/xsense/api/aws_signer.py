import hashlib
import datetime
import hmac
import json
import urllib
from typing import Dict
from urllib.parse import parse_qsl, quote, urlencode, urlsplit


class AWSSigner:
    algorithm = "AWS4-HMAC-SHA256"
    service = "iotdata"

    def __init__(self, client_id: str, client_secret: str, token: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = token

    def _sign(self, key, msg):
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    def get_signing_key(self, date_stamp, region):
        k_date = self._sign((f"AWS4{self.client_secret}").encode("utf-8"), date_stamp)
        # print(f'date   : {string_to_hex(k_date)}')
        k_region = self._sign(key=k_date, msg=region)
        # print(f'region : {string_to_hex(k_region)}')
        k_service = self._sign(key=k_region, msg=self.service)
        # print(f'service: {string_to_hex(k_service)}')
        k_signing = self._sign(key=k_service, msg="aws4_request")
        # print(f'result: {string_to_hex(k_signing)}')
        return k_signing

    def get_canonical_request(self, method, url, headers, content_hash):
        query = parse_qsl(url.query, keep_blank_values=True)
        canonical_query = urlencode(sorted(query), quote_via=quote)

        return "\n".join(
            [
                method,
                url.path,
                canonical_query,
                "\n".join(f"{key}:{value}" for key, value in headers),
                "",
                ";".join(k for k, v in headers),
                content_hash,
            ]
        )

    def get_string_to_sign(self, scope, amz_date, canonical_request):
        return "\n".join(
            [
                self.algorithm,
                amz_date,
                scope,
                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
            ]
        )

    def compute_signature(
        self, scope, method, url, headers, content_hash, date_stamp, amz_date, region
    ):
        canonical_request = self.get_canonical_request(
            method, url, headers, content_hash
        )
        string_to_sign = self.get_string_to_sign(scope, amz_date, canonical_request)

        signing_key = self.get_signing_key(date_stamp, region)

        return hmac.new(
            signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def combine_sort_headers(self, **kwargs):
        return sorted({k.lower(): v for k, v in kwargs.items()}.items())

    def sign_headers(
        self, method: str, url: str, region: str, headers: Dict, content: str
    ):
        parsed_url = urlsplit(url)

        result = {"host": parsed_url.netloc}
        t = datetime.datetime.now(datetime.timezone.utc)
        amz_date = t.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = t.strftime("%Y%m%d")

        scope = f"{date_stamp}/{region}/{self.service}/aws4_request"

        # calculate content hash
        if content:
            if isinstance(content, Dict):
                content = json.dumps(content, sort_keys=True)

            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        else:
            content_hash = hashlib.sha256(b"").hexdigest()

        result["X-Amz-Date"] = amz_date

        canonical_headers = self.combine_sort_headers(**headers, **result)

        signature = self.compute_signature(
            scope,
            method,
            parsed_url,
            canonical_headers,
            content_hash,
            date_stamp,
            amz_date,
            region,
        )

        signed_headers = ";".join(k for k, v in canonical_headers)
        credential = f"{self.client_id}/{scope}"

        result["Authorization"] = (
            f"{self.algorithm} "
            f"Credential={credential}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )

        return result

    def presign_url(self, url, region):
        t = datetime.datetime.now(datetime.timezone.utc)
        date_time = t.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = t.strftime("%Y%m%d")
        credential_scope = f"{date_stamp}/{region}/{self.service}/aws4_request"
        credential = f"{self.client_id}/{credential_scope}"
        parsed_url = urlsplit(url)

        canonical_querystring = "&".join(
            f"{k}={v}"
            for k, v in (
                ("X-Amz-Algorithm", self.algorithm),
                ("X-Amz-Credential", urllib.parse.quote_plus(credential)),
                ("X-Amz-Date", date_time),
                ("X-Amz-SignedHeaders", "host"),
            )
        )

        content_hash = hashlib.sha256(b"").hexdigest()
        # content_hash = 'UNSIGNED-PAYLOAD'

        canonical_headers = f"host:{parsed_url.netloc}\n"

        canonical_request = (
            "GET"
            + "\n"
            + parsed_url.path
            + "\n"
            + canonical_querystring
            + "\n"
            + canonical_headers
            + "\nhost\n"
            + content_hash
        )
        string_to_sign = (
            self.algorithm
            + "\n"
            + date_time
            + "\n"
            + credential_scope
            + "\n"
            + hashlib.sha256(canonical_request.encode()).hexdigest()
        )
        signing_key = self.get_signing_key(date_stamp, region)

        signature = hmac.new(
            signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        canonical_querystring += (
            f"&X-Amz-Security-Token={urllib.parse.quote(self.token)}"
        )
        canonical_querystring += f"&X-Amz-Signature={signature}"

        return (
            parsed_url.scheme
            + "://"
            + parsed_url.netloc
            + parsed_url.path
            + "?"
            + canonical_querystring
        )

    def update(self, client_id: str, client_secret: str, token: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = token
