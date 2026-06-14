"""X-Sense ADDX WebRTC signaling helpers."""

from __future__ import annotations

import asyncio
import base64
import json
import random
import time
import warnings
from contextlib import suppress
from collections import Counter
from dataclasses import dataclass
from collections.abc import Coroutine
from typing import Any, Callable
from urllib.parse import urlparse, urlunparse

import aiohttp
import dns.rdata

with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore",
        message="As the c extension couldn't be imported, `google-crc32c` is using a pure python implementation.*",
        category=RuntimeWarning,
        module="google_crc32c",
    )
    from aiortc import (
        RTCBundlePolicy as AiortcRTCBundlePolicy,
        RTCConfiguration as AiortcRTCConfiguration,
        RTCIceCandidate,
        RTCIceServer as AiortcRTCIceServer,
        RTCPeerConnection,
        RTCSessionDescription,
    )
    from aiortc.mediastreams import MediaStreamError, MediaStreamTrack
    from aiortc.sdp import candidate_from_sdp
from homeassistant.components.camera.webrtc import (
    WebRTCAnswer,
    WebRTCError,
    WebRTCSendMessage,
)
from webrtc_models import RTCIceCandidateInit

from .const import LOGGER


def _preload_dns_rdata_classes() -> None:
    """Warm dnspython lazy imports used by aioice mDNS outside the event loop."""
    mdns_classes = (1, 255, 512, 1232, 1280, 1400, 1440, 1500, 4096, 32769)
    mdns_types = (1, 12, 16, 28, 33, 41, 47)
    for rdclass in mdns_classes:
        for rdtype in mdns_types:
            with suppress(Exception):
                dns.rdata.get_rdata_class(rdclass, rdtype)


_preload_dns_rdata_classes()


SIGNAL_MODE = "vicoo"
SIGNAL_VIEWER_TYPE = "a4x_sdk"
SIGNAL_DATA_CHANNEL = "data-channel-of-"
_SIGNAL_NAME = "test-123"
_DEFAULT_RESOLUTION = "1280x720"
_PEER_IN_TIMEOUT = 20
_PLAY_TIMEOUT = 40
_FIRST_FRAME_TIMEOUT = 10
_DEFAULT_SIGNAL_HEARTBEAT = 30
_SIGNAL_RECONNECT_DELAY = 3
_SIGNAL_TERMINAL_CLOSE_CODES = {3002, 3004}


@dataclass(slots=True)
class XSenseWebRTCTicket:
    """ADDX WebRTC ticket data returned by the X-Sense camera API."""

    serial_number: str
    signal_server: str
    group_id: str
    role: str
    client_id: str
    trace_id: str
    sign: str
    time: int
    expiration_time: int | None = None
    signal_ping_interval: int | None = None
    app_stop_live_timeout: int | None = None
    signal_server_ip_address: str | None = None
    ice_servers: list[dict[str, Any]] | None = None

    @classmethod
    def from_api(cls, serial_number: str, data: dict[str, Any]) -> "XSenseWebRTCTicket":
        """Build a ticket from the Android app getWebrtcTicket response."""
        return cls(
            serial_number=serial_number,
            signal_server=str(data["signalServer"]),
            group_id=str(data["groupId"]),
            role=str(data["role"]),
            client_id=str(data["id"]),
            trace_id=str(data["traceId"]),
            sign=str(data["sign"]),
            time=int(data["time"]),
            expiration_time=_optional_int(data.get("expirationTime")),
            signal_ping_interval=_optional_int(data.get("signalPingInterval")),
            app_stop_live_timeout=_optional_int(data.get("appStopLiveTimeout")),
            signal_server_ip_address=data.get("signalServerIpAddress"),
            ice_servers=list(data.get("iceServer") or []),
        )

    @property
    def is_valid(self) -> bool:
        """Return whether the ticket has enough lifetime left to start playback."""
        if self.expiration_time is None:
            return False
        return self.expiration_time > int(time.time() * 1000)

    @property
    def session_id(self) -> str:
        """Return the SDK-style peer connection session id."""
        return f"Android-{self.client_id}-{int(time.time() * 1000)}"

    def signal_url(self) -> str:
        """Return the APK-compatible WebRTC signal URL."""
        parsed = self._parsed_signal_server()
        path = f"/{self.group_id}/{self.role}/{self.client_id}"
        query = (
            f"traceId={self.trace_id}&time={self.time}"
            f"&sign={self.sign}&name={_SIGNAL_NAME}"
        )
        return urlunparse((parsed.scheme, parsed.netloc, path, "", query, ""))

    def signal_connect_options(self) -> dict[str, Any]:
        """Return APK-style WebSocket connect overrides for signal IP tickets."""
        if not self.signal_server_ip_address:
            return {}
        parsed = urlparse(self.signal_url())
        host = parsed.hostname
        if not host:
            return {}
        netloc = self.signal_server_ip_address
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        url = urlunparse((parsed.scheme, netloc, parsed.path, "", parsed.query, ""))
        return {
            "url": url,
            "headers": {"Host": parsed.netloc},
            "server_hostname": host,
        }

    def _parsed_signal_server(self):
        parsed = urlparse(self.signal_server)
        if not parsed.scheme:
            parsed = urlparse(f"wss://{self.signal_server}")
        scheme = "wss" if parsed.scheme in {"http", "https"} else parsed.scheme
        return parsed._replace(scheme=scheme)


class _ProxyTrack(MediaStreamTrack):
    """Media track that forwards frames from the current X-Sense camera peer."""

    def __init__(self, kind: str, on_frame: Callable[[], None] | None = None) -> None:
        super().__init__()
        self.kind = kind
        self._on_frame = on_frame
        self._source: MediaStreamTrack | None = None
        self._source_ready = asyncio.Event()

    def set_source(self, track: MediaStreamTrack) -> None:
        """Set or replace the source track from the active camera peer."""
        self._source = track
        self._source_ready.set()

    async def recv(self):
        """Return the next frame from the active camera peer."""
        while self.readyState == "live":
            await self._source_ready.wait()
            source = self._source
            if source is None:
                self._source_ready.clear()
                continue
            try:
                frame = await source.recv()
            except MediaStreamError:
                if self._source is source:
                    self._source = None
                    self._source_ready.clear()
                continue
            if self._on_frame:
                self._on_frame()
            return frame
        raise MediaStreamError

    def stop(self) -> None:
        """Stop the proxy and wake any receiver waiting for the camera track."""
        self._source = None
        self._source_ready.set()
        super().stop()


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _short_id(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value)
    return text if len(text) <= 6 else f"...{text[-6:]}"


def _safe_host(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value if "://" in value else f"//{value}")
    return parsed.hostname or parsed.path or None


def _ticket_debug_context(ticket: XSenseWebRTCTicket) -> dict[str, Any]:
    return {
        "camera": _short_id(ticket.serial_number),
        "client": _short_id(ticket.client_id),
        "role": ticket.role,
        "signal_host": _safe_host(ticket.signal_server),
        "signal_ip_override": bool(ticket.signal_server_ip_address),
        "ice_servers": len(ticket.ice_servers or []),
        "signal_ping_interval": ticket.signal_ping_interval,
        "signal_heartbeat_s": _signal_heartbeat(ticket),
        "ticket_expires_in_s": (
            round((ticket.expiration_time - int(time.time() * 1000)) / 1000)
            if ticket.expiration_time is not None
            else None
        ),
    }


def _signal_heartbeat(ticket: XSenseWebRTCTicket) -> float:
    """Return the integration WebSocket heartbeat for the signal socket."""
    # The APK stores signalPingInterval in the ticket, but the Java wrapper does
    # not pass it into A4xSignal.init. Keep our client heartbeat stable instead
    # of interpreting that ticket field as WebSocket ping timing.
    return _DEFAULT_SIGNAL_HEARTBEAT


def _payload_debug(payload: Any) -> str:
    if isinstance(payload, dict):
        return f"dict_keys={sorted(payload.keys())}"
    if isinstance(payload, str):
        return f"str:{_short_id(payload)}"
    return type(payload).__name__


def _sdp_debug(sdp: str | None) -> dict[str, Any]:
    """Return compact SDP shape details useful for camera debugging."""
    if not isinstance(sdp, str):
        return {"sdp_len": 0, "media": []}
    media = [line[2:] for line in sdp.splitlines() if line.startswith("m=")]
    mids = [
        line.removeprefix("a=mid:")
        for line in sdp.splitlines()
        if line.startswith("a=mid:")
    ]
    return {
        "sdp_len": len(sdp),
        "media": media,
        "mids": mids,
        "directions": _sdp_media_directions(sdp),
        "video_codecs": _sdp_media_codecs(sdp, "video"),
        "fingerprints": _sdp_fingerprints(sdp),
        "candidate_lines": sum(
            1 for line in sdp.splitlines() if line.startswith("a=candidate:")
        ),
    }


def _sdp_media_directions(sdp: str) -> dict[str, str]:
    """Return media-section directions from SDP for compact debug logs."""
    directions: dict[str, str] = {}
    current_mid: str | None = None
    current_media: str | None = None
    for line in sdp.splitlines():
        if line.startswith("m="):
            current_media = line[2:].split(" ", 1)[0]
            current_mid = current_media
            directions[current_mid] = "unspecified"
        elif line.startswith("a=mid:") and current_media is not None:
            previous_mid = current_mid
            current_mid = line.removeprefix("a=mid:")
            directions[current_mid] = directions.pop(previous_mid, "unspecified")
        elif line in {"a=sendrecv", "a=sendonly", "a=recvonly", "a=inactive"}:
            if current_mid is not None:
                directions[current_mid] = line.removeprefix("a=")
    return directions


def _sdp_media_codecs(sdp: str, media_kind: str) -> list[str]:
    """Return compact codec names for one SDP media section."""
    codecs: list[str] = []
    in_section = False
    for line in sdp.splitlines():
        if line.startswith("m="):
            in_section = line.startswith(f"m={media_kind} ")
            continue
        if in_section and line.startswith("a=rtpmap:"):
            _, codec = line.removeprefix("a=rtpmap:").split(None, 1)
            codec_name = codec.split("/", 1)[0].upper()
            if codec_name not in codecs:
                codecs.append(codec_name)
    return codecs


def _sdp_fingerprints(sdp: str) -> list[str]:
    """Return compact DTLS fingerprint algorithms from SDP."""
    algorithms: list[str] = []
    for line in sdp.splitlines():
        if not line.startswith("a=fingerprint:"):
            continue
        algorithm = line.removeprefix("a=fingerprint:").split(None, 1)[0].lower()
        if algorithm not in algorithms:
            algorithms.append(algorithm)
    return algorithms


def _candidate_debug_summary(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Return compact ICE candidate shape details without logging raw IPs."""
    protocols: Counter[str] = Counter()
    candidate_types: Counter[str] = Counter()
    mids: Counter[str] = Counter()
    for candidate in candidates:
        parts = str(candidate.get("candidate", "")).split()
        if len(parts) >= 3:
            protocols[parts[2].lower()] += 1
        if "typ" in parts:
            index = parts.index("typ")
            if index + 1 < len(parts):
                candidate_types[parts[index + 1]] += 1
        mids[str(candidate.get("sdpMid"))] += 1
    return {
        "candidate_count": len(candidates),
        "candidate_protocols": dict(protocols),
        "candidate_types": dict(candidate_types),
        "candidate_mids": dict(mids),
    }


def _peer_event_debug(payload: Any, serial_number: str) -> dict[str, Any]:
    match = _matching_peer_id(payload, serial_number)
    return {
        "payload": _payload_debug(payload),
        "payload_fields": _debug_payload_fields(payload),
        "payload_matches_camera": match is not None,
        "camera": _short_id(serial_number),
        "peer": _short_id(match),
        "peer_candidates": [
            _short_id(value) for value in _peer_payload_candidates(payload)
        ],
    }


def _debug_payload_fields(payload: Any) -> dict[str, str | None]:
    """Return compact non-secret peer payload fields for signal debugging."""
    if not isinstance(payload, dict):
        return {}
    return {
        key: _short_id(payload.get(key))
        for key in ("group", "role", "id", "name", "clientId", "serialNumber")
        if payload.get(key) not in (None, "")
    }


def _signal_envelope_debug(payload: str) -> dict[str, Any]:
    """Return compact non-secret signal envelope details."""
    with suppress(Exception):
        data = json.loads(payload)
        if isinstance(data, dict):
            return {
                "keys": sorted(data.keys()),
                "message_type": data.get("messageType"),
                "sender": _short_id(data.get("senderClientId")),
                "recipient": _short_id(data.get("recipientClientId")),
                "session": _short_id(data.get("sessionId")),
                "mode": data.get("mode"),
                "viewer_type": data.get("viewerType"),
                "has_resolution": "resolution" in data,
                "payload_len": len(str(data.get("messagePayload", ""))),
            }
    return {"raw_len": len(payload)}

def _answer_reject_reason(payload: Any, ticket: XSenseWebRTCTicket) -> str:
    if not isinstance(payload, dict):
        return "payload_not_dict"
    sender = payload.get("senderClientId")
    recipient = payload.get("recipientClientId")
    if sender and sender != ticket.serial_number:
        return "sender_mismatch"
    if recipient and recipient != ticket.client_id:
        return "recipient_mismatch"
    encoded = payload.get("messagePayload")
    if not isinstance(encoded, str):
        return "missing_message_payload"
    with suppress(Exception):
        decoded = json.loads(base64.b64decode(encoded).decode())
        if isinstance(decoded.get("sdp"), str):
            return "accepted"
    return "invalid_sdp_payload"


def make_sdp_offer_payload(
    *,
    offer_sdp: str,
    ticket: XSenseWebRTCTicket,
    recipient_client_id: str,
    session_id: str,
    resolution: str | None,
) -> str:
    """Return the APK-compatible SDP offer envelope."""
    payload = _b64_json(
        {"type": "offer", "sdp": _sdp_without_local_candidates(offer_sdp)}
    )
    envelope: dict[str, Any] = {
        "messageType": "SDP_OFFER",
        "messagePayload": payload,
        "mode": SIGNAL_MODE,
        "recipientClientId": recipient_client_id,
        "senderClientId": ticket.client_id,
        "sessionId": session_id,
        "viewerType": SIGNAL_VIEWER_TYPE,
    }
    if resolution:
        envelope["resolution"] = resolution
    return json.dumps(envelope, separators=(",", ":"))


def make_ice_candidate_payload(
    *,
    candidate: str,
    sdp_mid: str | None,
    sdp_m_line_index: int,
    ticket: XSenseWebRTCTicket,
    recipient_client_id: str,
    session_id: str,
) -> str:
    """Return the APK-compatible ICE_CANDIDATE signal envelope."""
    payload = _b64_json(
        {
            "sdpMid": sdp_mid,
            "sdpMLineIndex": sdp_m_line_index,
            "candidate": candidate,
        }
    )
    envelope: dict[str, Any] = {
        "messageType": "ICE_CANDIDATE",
        "messagePayload": payload,
        "recipientClientId": recipient_client_id,
        "senderClientId": ticket.client_id,
        "sessionId": session_id,
    }
    return json.dumps(envelope, separators=(",", ":"))


def make_start_live_data_channel_message(resolution: str) -> dict[str, Any]:
    """Return the APK-compatible data-channel startLive command."""
    return make_data_channel_command(
        "startLive",
        top_level_parameters={
            "size": _map_video_size(resolution),
            "resolution": resolution,
        },
    )


def make_data_channel_command(
    action: str,
    *,
    request_id: str | None = None,
    parameters: dict[str, Any] | None = None,
    top_level_parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the APK-compatible base data-channel command."""
    message: dict[str, Any] = {
        "requestID": request_id
        or f"{int(time.time() * 1000)}-{random.randint(0, 999)}",
        "connectionID": "7893feb",
        "timeStamp": int(time.time()),
        "action": action,
    }
    if top_level_parameters:
        message.update(top_level_parameters)
    elif parameters:
        message["parameters"] = parameters
    return message


def make_change_transceiver_offer_command(offer_sdp: str) -> dict[str, Any]:
    """Return the APK-compatible changeTransceiverOffer command."""
    encoded_offer = _b64_json({"type": "offer", "sdp": offer_sdp})
    return make_data_channel_command(
        "changeTransceiverOffer", parameters={"offer": encoded_offer}
    )


def make_data_channel_answer_command(request_id: str, action: str) -> dict[str, Any]:
    """Return the APK-compatible data-channel command acknowledgement."""
    return make_data_channel_command(
        action, request_id=request_id, parameters={"returnValue": "0"}
    )


def parse_signal_message(raw: str | bytes) -> tuple[str | None, Any]:
    """Parse a signal-server message into the APK event callback shape."""
    if isinstance(raw, bytes):
        raw = raw.decode(errors="ignore")
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None, raw

    event = (
        data.get("messageType")
        or data.get("event")
        or data.get("type")
        or data.get("method")
    )
    payload: Any = _signal_payload(data)
    if isinstance(payload, str) and event == "SDP_ANSWER":
        with suppress(Exception):
            decoded = json.loads(payload)
            if isinstance(decoded, dict):
                payload = decoded
        if isinstance(payload, str):
            payload = data
    elif isinstance(payload, str) and event == "ICE_CANDIDATE":
        with suppress(Exception):
            payload = json.loads(payload)
        if isinstance(payload, str):
            with suppress(Exception):
                payload = json.loads(base64.b64decode(payload).decode())
    if event in {"PEER_IN", "PEER_OUT"}:
        payload = _signal_peer_payload(payload)
    return event, payload


def _signal_payload(data: dict[str, Any]) -> Any:
    for key in ("messagePayload", "payload", "data", "message", "body", "value"):
        if key in data:
            return data[key]
    return data


def _signal_peer_payload(payload: Any) -> Any:
    if isinstance(payload, str):
        payload = _decode_signal_peer_payload(payload)
    if isinstance(payload, dict):
        for key in ("clientId", "serialNumber", "deviceSn", "deviceSN", "sn"):
            value = payload.get(key)
            if value:
                return str(value)
    return payload


def _decode_signal_peer_payload(payload: str) -> Any:
    """Return the APK-style PEER_IN/PEER_OUT payload from signal JSON."""
    with suppress(Exception):
        return json.loads(payload)
    if not _looks_like_encoded_peer_payload(payload):
        return payload
    decoded = _base64_decode_text(payload)
    if decoded:
        with suppress(Exception):
            return json.loads(decoded)
        return decoded
    return payload


def _looks_like_encoded_peer_payload(value: str) -> bool:
    return any(char in value for char in "=+/") or value.startswith("eyJ")


def _base64_decode_text(value: str) -> str | None:
    with suppress(Exception):
        decoded = base64.b64decode(value, validate=True).decode()
        if decoded:
            return decoded
    return None


class XSenseWebRTCSession:
    """One Home Assistant WebRTC session bridged to X-Sense ADDX WebRTC."""

    def __init__(
        self,
        *,
        session: aiohttp.ClientSession,
        ticket: XSenseWebRTCTicket,
        offer_sdp: str,
        resolution: str | None,
        send_message: WebRTCSendMessage,
        session_id: str | None = None,
        on_close: Callable[[], None] | None = None,
        camera_online: bool = False,
        refresh_ticket: Callable[
            [], Coroutine[Any, Any, XSenseWebRTCTicket | None]
        ] | None = None,
    ) -> None:
        self._session = session
        self._ticket = ticket
        self._offer_sdp = offer_sdp
        self._resolution = resolution or _DEFAULT_RESOLUTION
        self._send_message = send_message
        self._on_close = on_close
        self._session_id = session_id or ticket.session_id
        self._recipient_client_id = ticket.serial_number
        self._camera_online = camera_online
        self._refresh_ticket = refresh_ticket
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._signal_reconnect_task: asyncio.Task[None] | None = None
        self._peer_reconnect_task: asyncio.Task[None] | None = None
        self._ha_pc = RTCPeerConnection()
        self._camera_pc: RTCPeerConnection | None = None
        self._video = _ProxyTrack("video", self._mark_first_frame_received)
        self._audio = _ProxyTrack("audio")
        self._data_channel = None
        self._pending_ha_candidates: list[RTCIceCandidate] = []
        self._pending_camera_candidates: list[RTCIceCandidate] = []
        self._camera_peer_ready = False
        self._data_channel_connected = False
        self._camera_offer_sent = False
        self._camera_offer_sdp: str | None = None
        self._sdp_answer_received = False
        self._camera_local_candidate_count = 0
        self._camera_remote_candidate_count = 0
        self._last_signal_event: str | None = None
        self._signal_event_counts: Counter[str] = Counter()
        self._camera_local_description_task: asyncio.Task[None] | None = None
        self._peer_in_timeout_task: asyncio.Task[None] | None = None
        self._play_timeout_task: asyncio.Task[None] | None = None
        self._first_frame_timeout_task: asyncio.Task[None] | None = None
        self._keep_alive_task: asyncio.Task[None] | None = None
        self._start_live_sent = False
        self._first_frame_received = False
        self._closed = False
        self._close_lock = asyncio.Lock()

    def _debug_context(self, **extra: Any) -> dict[str, Any]:
        ticket = getattr(self, "_ticket", None)
        context = _ticket_debug_context(ticket) if ticket is not None else {}
        camera_pc = getattr(self, "_camera_pc", None)
        ha_pc = getattr(self, "_ha_pc", None)
        data_channel = getattr(self, "_data_channel", None)
        context.update(
            {
                "session": _short_id(getattr(self, "_session_id", None)),
                "recipient": _short_id(getattr(self, "_recipient_client_id", None)),
                "resolution": getattr(self, "_resolution", None),
                "camera_online": getattr(self, "_camera_online", None),
                "camera_pc": getattr(camera_pc, "connectionState", None),
                "ha_pc": getattr(ha_pc, "connectionState", None),
                "data_channel": getattr(data_channel, "readyState", None),
                "camera_peer_ready": getattr(self, "_camera_peer_ready", None),
                "offer_sent": getattr(self, "_camera_offer_sent", None),
                "sdp_answer_received": getattr(self, "_sdp_answer_received", None),
                "first_frame_received": getattr(self, "_first_frame_received", None),
                "start_live_sent": getattr(self, "_start_live_sent", None),
                "last_signal_event": getattr(self, "_last_signal_event", None),
                "signal_events": dict(getattr(self, "_signal_event_counts", {})),
                "local_candidate_count": getattr(
                    self, "_camera_local_candidate_count", None
                ),
                "remote_candidate_count": getattr(
                    self, "_camera_remote_candidate_count", None
                ),
                "pending_ha_candidates": len(
                    getattr(self, "_pending_ha_candidates", [])
                ),
                "pending_camera_candidates": len(
                    getattr(self, "_pending_camera_candidates", [])
                ),
            }
        )
        context.update(extra)
        return context

    async def start(self) -> bool:
        """Connect both WebRTC peers and start the X-Sense camera stream."""
        try:
            LOGGER.debug("X-Sense WebRTC session starting: %s", self._debug_context())
            self._ha_pc.addTrack(self._video)
            self._ha_pc.addTrack(self._audio)
            await self._ha_pc.setRemoteDescription(
                RTCSessionDescription(sdp=self._offer_sdp, type="offer")
            )
            await self._flush_pending_ha_candidates()
            answer = await self._ha_pc.createAnswer()
            await self._ha_pc.setLocalDescription(answer)
            if not self._send_ha_message(
                WebRTCAnswer(self._ha_pc.localDescription.sdp)
            ):
                await self.close()
                return False

            LOGGER.debug("X-Sense WebRTC HA answer ready: %s", self._debug_context())
            await self._connect_signal()
            self._play_timeout_task = asyncio.create_task(
                self._fail_after_timeout(
                    _PLAY_TIMEOUT,
                    "xsense_webrtc_play_timeout",
                    "Camera did not start the WebRTC stream",
                )
            )
            if self._camera_online:
                LOGGER.debug(
                    "X-Sense WebRTC camera already online, starting peer without PEER_IN: %s",
                    self._debug_context(),
                )
                await self._start_camera_peer()
            else:
                LOGGER.debug(
                    "X-Sense WebRTC waiting for PEER_IN: %s",
                    self._debug_context(),
                )
                self._peer_in_timeout_task = asyncio.create_task(
                    self._handle_peer_in_timeout()
                )
            return True
        except Exception as err:  # noqa: BLE001 - surface cleanly to HA frontend
            LOGGER.debug(
                "X-Sense WebRTC start failed context: %s",
                self._debug_context(error=type(err).__name__, message=str(err)),
            )
            LOGGER.debug("Unable to start X-Sense WebRTC bridge", exc_info=err)
            self._send_ha_message(WebRTCError("xsense_webrtc_start_failed", str(err)))
            await self.close()
            return False

    async def add_candidate(self, candidate: RTCIceCandidateInit) -> None:
        """Forward a browser ICE candidate after the HA offer has been applied."""
        if self._closed:
            return
        parsed = _candidate_init_to_aiortc(candidate)
        if self._ha_pc.remoteDescription is None:
            self._pending_ha_candidates.append(parsed)
            LOGGER.debug(
                "X-Sense WebRTC queued HA ICE candidate: %s",
                self._debug_context(
                    pending_ha_candidates=len(self._pending_ha_candidates)
                ),
            )
            return
        await self._ha_pc.addIceCandidate(parsed)
        LOGGER.debug("X-Sense WebRTC applied HA ICE candidate: %s", self._debug_context())

    async def close(self) -> None:
        """Close the X-Sense signaling and WebRTC sessions."""
        async with self._close_lock:
            if self._closed:
                return
            LOGGER.debug("X-Sense WebRTC session closing: %s", self._debug_context())
            self._closed = True
            self._send_stop_live()
            if self._reader_task:
                self._reader_task.cancel()
                with suppress(asyncio.CancelledError, Exception):
                    await self._reader_task
            await self._cancel_task(getattr(self, "_peer_in_timeout_task", None))
            await self._cancel_task(getattr(self, "_signal_reconnect_task", None))
            await self._cancel_task(getattr(self, "_peer_reconnect_task", None))
            await self._cancel_task(getattr(self, "_play_timeout_task", None))
            await self._cancel_task(getattr(self, "_first_frame_timeout_task", None))
            await self._cancel_task(getattr(self, "_keep_alive_task", None))
            if self._camera_local_description_task:
                self._camera_local_description_task.cancel()
                with suppress(asyncio.CancelledError, Exception):
                    await self._camera_local_description_task
            if self._ws and not self._ws.closed:
                with suppress(Exception):
                    await self._ws.close()
            if getattr(self._data_channel, "readyState", None) == "open":
                with suppress(Exception):
                    self._data_channel.close()
            with suppress(Exception):
                self._video.stop()
            with suppress(Exception):
                self._audio.stop()
            if self._camera_pc is not None:
                await self._stop_peer_connection(self._camera_pc)
            await self._stop_peer_connection(self._ha_pc)
            self._pending_ha_candidates.clear()
            self._pending_camera_candidates.clear()
            on_close = getattr(self, "_on_close", None)
            if on_close:
                with suppress(Exception):
                    on_close()

    async def _stop_peer_connection(self, peer_connection: RTCPeerConnection) -> None:
        """Stop media transports before closing, matching the APK stop path."""
        get_transceivers = getattr(peer_connection, "getTransceivers", lambda: [])
        get_senders = getattr(peer_connection, "getSenders", lambda: [])
        get_receivers = getattr(peer_connection, "getReceivers", lambda: [])
        for transceiver in list(get_transceivers()):
            with suppress(Exception):
                await transceiver.stop()
            sender = getattr(transceiver, "sender", None)
            if sender is not None:
                with suppress(Exception):
                    await sender.stop()
            receiver = getattr(transceiver, "receiver", None)
            if receiver is not None:
                with suppress(Exception):
                    await receiver.stop()
        for sender in list(get_senders()):
            with suppress(Exception):
                await sender.stop()
        for receiver in list(get_receivers()):
            with suppress(Exception):
                await receiver.stop()
        with suppress(Exception):
            await peer_connection.close()
        await asyncio.sleep(0)

    def _create_task(self, coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any] | None:
        try:
            return asyncio.create_task(coro)
        except Exception:
            coro.close()
            return None

    async def _cancel_task(self, task: asyncio.Task[Any] | None) -> None:
        if task is None or task.done() or task is asyncio.current_task():
            return
        task.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await task

    def _send_ha_message(self, message: WebRTCAnswer | WebRTCError) -> bool:
        """Send a Home Assistant WebRTC message if the browser socket is open."""
        if self._closed:
            return False
        try:
            self._send_message(message)
        except (ConnectionError, RuntimeError, aiohttp.ClientConnectionError) as err:
            LOGGER.debug(
                "Home Assistant WebRTC client closed while sending X-Sense reply",
                exc_info=err,
            )
            return False
        return True

    async def _fail_after_timeout(self, delay: int, code: str, message: str) -> None:
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            raise
        if self._closed:
            return
        LOGGER.debug(
            "X-Sense WebRTC timeout: %s",
            self._debug_context(code=code, timeout_s=delay),
        )
        self._send_ha_message(WebRTCError(code, message))
        await self.close()

    async def _connect_signal(self) -> None:
        """Open the X-Sense signal websocket using the current ticket."""
        connect_options = self._ticket.signal_connect_options()
        connect_url = connect_options.pop("url", self._ticket.signal_url())
        LOGGER.debug(
            "X-Sense WebRTC signal connecting: %s",
            self._debug_context(connect_host=_safe_host(connect_url)),
        )
        signal_heartbeat = _signal_heartbeat(self._ticket)
        self._ws = await self._session.ws_connect(
            connect_url, heartbeat=signal_heartbeat, **connect_options
        )
        LOGGER.debug("X-Sense WebRTC signal connected: %s", self._debug_context())
        self._reader_task = asyncio.create_task(self._read_loop())

    async def _handle_peer_in_timeout(self) -> None:
        """Refresh the WebRTC ticket after PEER_IN timeout like the APK."""
        try:
            await asyncio.sleep(_PEER_IN_TIMEOUT)
        except asyncio.CancelledError:
            raise
        if self._closed:
            return
        LOGGER.debug(
            "X-Sense WebRTC PEER_IN timeout, refreshing ticket: %s",
            self._debug_context(timeout_s=_PEER_IN_TIMEOUT),
        )
        refresh_ticket = getattr(self, "_refresh_ticket", None)
        if refresh_ticket is None:
            LOGGER.debug(
                "X-Sense WebRTC PEER_IN timeout has no ticket refresh callback: %s",
                self._debug_context(),
            )
            return
        try:
            new_ticket = await refresh_ticket()
        except Exception as err:  # noqa: BLE001 - ticket refresh failures are non-fatal here
            LOGGER.debug(
                "X-Sense WebRTC ticket refresh after PEER_IN timeout failed: %s",
                self._debug_context(error=type(err).__name__, message=str(err)),
            )
            return
        if new_ticket is None or not new_ticket.is_valid:
            LOGGER.debug(
                "X-Sense WebRTC ticket refresh after PEER_IN timeout returned no valid ticket: %s",
                self._debug_context(),
            )
            return
        old_signal_url = self._ticket.signal_url()
        old_connect_options = self._ticket.signal_connect_options()
        new_signal_url = new_ticket.signal_url()
        new_connect_options = new_ticket.signal_connect_options()
        self._ticket = new_ticket
        if self._camera_offer_sdp is None:
            self._session_id = new_ticket.session_id
            self._recipient_client_id = new_ticket.serial_number
        LOGGER.debug(
            "X-Sense WebRTC refreshed ticket after PEER_IN timeout: %s",
            self._debug_context(
                signal_changed=(
                    old_signal_url != new_signal_url
                    or old_connect_options != new_connect_options
                )
            ),
        )
        if (
            old_signal_url == new_signal_url
            and old_connect_options == new_connect_options
        ):
            return
        await self._reconnect_signal()

    async def _reconnect_signal(self) -> None:
        """Reconnect the signal websocket after the APK would reinit it."""
        old_ws = self._ws
        old_reader = self._reader_task
        self._ws = None
        self._reader_task = None
        if old_reader and old_reader is not asyncio.current_task():
            old_reader.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await old_reader
        if old_ws and not old_ws.closed:
            with suppress(Exception):
                await old_ws.close()
        if not self._closed:
            await self._connect_signal()

    def _schedule_signal_reconnect(self, close_code: int | None) -> None:
        """Schedule APK-style signal reinit after a non-terminal close."""
        if self._closed or close_code in _SIGNAL_TERMINAL_CLOSE_CODES:
            LOGGER.debug(
                "X-Sense WebRTC signal reconnect skipped: %s",
                self._debug_context(signal_close_code=close_code),
            )
            return
        task = getattr(self, "_signal_reconnect_task", None)
        if task and not task.done():
            return
        self._signal_reconnect_task = asyncio.create_task(
            self._signal_reconnect_after_delay(close_code)
        )

    async def _signal_reconnect_after_delay(self, close_code: int | None) -> None:
        """Reinitialize signal connection after the APK's delayed close handler."""
        try:
            await asyncio.sleep(_SIGNAL_RECONNECT_DELAY)
        except asyncio.CancelledError:
            raise
        if self._closed:
            return
        LOGGER.debug(
            "X-Sense WebRTC signal reconnecting after close: %s",
            self._debug_context(
                signal_close_code=close_code,
                reconnect_delay_s=_SIGNAL_RECONNECT_DELAY,
            ),
        )
        try:
            await self._reconnect_signal()
        except Exception as err:  # noqa: BLE001 - play timeout owns user-facing failure
            LOGGER.debug(
                "X-Sense WebRTC signal reconnect failed: %s",
                self._debug_context(error=type(err).__name__, message=str(err)),
                exc_info=err,
            )

    def _schedule_peer_reconnect(self, state: str) -> None:
        """Schedule the APK live-view P2P reconnect path after peer failure."""
        task = getattr(self, "_peer_reconnect_task", None)
        if self._closed or (task and not task.done()):
            return
        self._peer_reconnect_task = asyncio.create_task(self._reconnect_camera_peer(state))

    async def _reconnect_camera_peer(self, state: str) -> None:
        """Recreate the camera peer and restart the APK live-view send path."""
        LOGGER.debug(
            "X-Sense WebRTC reconnecting camera peer after state change: %s",
            self._debug_context(peer_state=state),
        )
        self._reset_camera_peer_state()
        await self._start_camera_peer()
        self._send_start_live_if_ready()

    def _reset_camera_peer_state(self) -> None:
        """Reset camera peer state before recreating it like the APK startInternal path."""
        old_pc = self._camera_pc
        self._camera_pc = None
        self._data_channel = None
        self._data_channel_connected = False
        self._camera_offer_sent = False
        self._camera_offer_sdp = None
        self._sdp_answer_received = False
        self._camera_local_description_task = None
        self._pending_camera_candidates.clear()
        self._camera_local_candidate_count = 0
        self._camera_remote_candidate_count = 0
        self._start_live_sent = False
        self._first_frame_received = False
        first_frame_task = getattr(self, "_first_frame_timeout_task", None)
        if first_frame_task:
            first_frame_task.cancel()
            self._first_frame_timeout_task = None
        if old_pc is not None:
            self._create_task(old_pc.close())

    def _mark_first_frame_received(self) -> None:
        if self._first_frame_received:
            return
        self._first_frame_received = True
        LOGGER.debug("X-Sense WebRTC first frame received: %s", self._debug_context())
        play_task = getattr(self, "_play_timeout_task", None)
        if play_task:
            play_task.cancel()
        first_frame_task = getattr(self, "_first_frame_timeout_task", None)
        if first_frame_task:
            first_frame_task.cancel()

    def _send_stop_live(self) -> None:
        """Send the APK stopLive data-channel command before closing."""
        if getattr(self._data_channel, "readyState", None) != "open":
            return
        self._send_data_channel_json(make_data_channel_command("stopLive"))

    def _setup_camera_peer(self) -> None:
        if self._camera_pc is not None:
            return
        self._session_id = self._session_id or self._ticket.session_id
        self._camera_pc = RTCPeerConnection(_camera_rtc_configuration(self._ticket))
        camera_pc = self._camera_pc

        @camera_pc.on("track")
        def on_track(track):
            if track.kind == "video":
                self._video.set_source(track)
            elif track.kind == "audio":
                self._audio.set_source(track)

        # APK creates the audio transceiver during peer setup using the
        # WebRTC default direction, before the data channel and createOffer.
        # Video is requested at offer time.
        camera_pc.addTransceiver("audio")
        self._data_channel = camera_pc.createDataChannel(SIGNAL_DATA_CHANNEL)

        @self._data_channel.on("open")
        def on_open():
            LOGGER.debug(
                "X-Sense WebRTC data channel opened: %s",
                self._debug_context(),
            )

        @self._data_channel.on("close")
        def on_close():
            LOGGER.debug(
                "X-Sense WebRTC data channel closed: %s",
                self._debug_context(),
            )

        @self._data_channel.on("message")
        def on_message(message):
            self._handle_data_channel_message(message)

        @camera_pc.on("connectionstatechange")
        def on_connectionstatechange():
            state = camera_pc.connectionState
            if camera_pc is not self._camera_pc:
                LOGGER.debug(
                    "X-Sense WebRTC ignored stale camera peer state change: %s",
                    self._debug_context(new_state=state),
                )
                return
            LOGGER.debug(
                "X-Sense WebRTC camera peer state changed: %s",
                self._debug_context(new_state=state),
            )
            if state == "connected":
                return
            if state == "failed" and not self._closed:
                self._schedule_peer_reconnect(state)
            elif state == "closed" and not self._closed:
                LOGGER.debug(
                    "X-Sense WebRTC camera peer closed before session close: %s",
                    self._debug_context(),
                )

    def _handle_data_channel_message(self, message: str | bytes) -> None:
        """Handle camera data-channel messages in the APK callback shape."""
        if isinstance(message, bytes):
            message = message.decode(errors="ignore")
        try:
            payload = json.loads(message)
            LOGGER.debug(
                "X-Sense WebRTC data-channel message: %s",
                self._debug_context(action=payload.get("action")),
            )
        except (TypeError, json.JSONDecodeError):
            return
        action = payload.get("action")
        if action == "dataChannelConnected":
            self._data_channel_connected = True
            self._send_start_live_if_ready()
        elif action == "requestChangeTransceiverOffer":
            request_id = payload.get("requestID")
            if isinstance(request_id, str):
                self._send_data_channel_json(
                    make_data_channel_answer_command(
                        request_id, "requestChangeTransceiverOffer"
                    )
                )
            self._create_task(self._send_change_transceiver_offer())
        elif action == "changeTransceiverOffer":
            self._create_task(self._apply_change_transceiver_answer(payload))

    def _send_data_channel_json(self, payload: dict[str, Any]) -> bool:
        if getattr(self._data_channel, "readyState", None) != "open":
            return False
        try:
            self._data_channel.send(json.dumps(payload, separators=(",", ":")))
        except Exception as err:
            LOGGER.debug("Unable to send X-Sense data-channel command", exc_info=err)
            return False
        return True

    async def _send_change_transceiver_offer(self) -> None:
        """Respond to requestChangeTransceiverOffer like the Android app."""
        if self._closed or getattr(self._data_channel, "readyState", None) != "open":
            return
        if self._camera_pc is None:
            return
        offer = await self._camera_pc.createOffer()
        await self._camera_pc.setLocalDescription(offer)
        if self._send_data_channel_json(
            make_change_transceiver_offer_command(offer.sdp)
        ):
            LOGGER.debug(
                "X-Sense WebRTC sent changeTransceiverOffer: %s",
                self._debug_context(offer_sdp_len=len(offer.sdp)),
            )

    async def _apply_change_transceiver_answer(self, payload: dict[str, Any]) -> None:
        """Apply the APK changeTransceiverOffer answer from the data channel."""
        answer = _data_channel_answer_sdp(payload)
        if not answer:
            LOGGER.debug(
                "X-Sense WebRTC ignored invalid changeTransceiverOffer answer: %s",
                self._debug_context(payload=_payload_debug(payload)),
            )
            return
        await self._camera_pc.setRemoteDescription(
            RTCSessionDescription(sdp=answer, type="answer")
        )
        LOGGER.debug(
            "X-Sense WebRTC applied changeTransceiverOffer answer: %s",
            self._debug_context(),
        )

    def _send_start_live_if_ready(self) -> None:
        """Send startLive when the APK would: after dataChannelConnected."""
        if not self._data_channel_connected:
            return
        if (
            self._start_live_sent
            or getattr(self._data_channel, "readyState", None) != "open"
        ):
            return
        if not self._send_data_channel_json(
            make_start_live_data_channel_message(self._resolution)
        ):
            return
        self._start_live_sent = True
        if not self._first_frame_received and not self._first_frame_timeout_task:
            self._first_frame_timeout_task = asyncio.create_task(
                self._fail_after_timeout(
                    _FIRST_FRAME_TIMEOUT,
                    "xsense_webrtc_first_frame_timeout",
                    "Camera connected but did not send a video frame",
                )
            )
        LOGGER.debug(
            "X-Sense WebRTC sent startLive: %s",
            self._debug_context(size=_map_video_size(self._resolution)),
        )

    async def _start_camera_peer(self) -> None:
        LOGGER.debug("X-Sense WebRTC creating camera offer: %s", self._debug_context())
        if self._camera_pc is None:
            self._setup_camera_peer()
        if self._camera_pc is None:
            raise RuntimeError("Camera peer connection was not created")
        # APK createOffer asks to receive video; audio is already present from
        # peer setup, matching the SDK transceiver timing.
        self._camera_pc.addTransceiver("video", direction="recvonly")
        offer = await self._camera_pc.createOffer()
        camera_offer = RTCSessionDescription(
            sdp=_apk_camera_offer_sdp(offer.sdp), type=offer.type
        )
        self._camera_offer_sdp = camera_offer.sdp
        self._camera_local_description_task = asyncio.create_task(
            self._camera_pc.setLocalDescription(camera_offer)
        )
        await self._send_offer()

    async def _send_offer(self) -> None:
        if (
            self._closed
            or self._ws is None
            or getattr(self._ws, "closed", False)
            or self._camera_offer_sdp is None
            or self._camera_offer_sent
        ):
            return
        offer_payload = make_sdp_offer_payload(
            offer_sdp=self._camera_offer_sdp,
            ticket=self._ticket,
            recipient_client_id=self._recipient_client_id,
            session_id=self._session_id,
            resolution=self._resolution,
        )
        LOGGER.debug(
            "X-Sense WebRTC sending SDP offer: %s",
            self._debug_context(
                recipient=_short_id(self._recipient_client_id),
                offer_sdp=_sdp_debug(self._camera_offer_sdp),
                offer_envelope=_signal_envelope_debug(offer_payload),
                offer_resolution=bool(self._resolution),
            ),
        )
        await self._ws.send_str(offer_payload)
        self._camera_offer_sent = True
        if self._camera_local_description_task:
            await self._camera_local_description_task
        await self._send_local_ice_candidates()

    async def _send_local_ice_candidates(self) -> None:
        """Send gathered local ICE candidates over the X-Sense signal server."""
        if (
            self._closed
            or self._ws is None
            or getattr(self._ws, "closed", False)
            or self._camera_pc.localDescription is None
        ):
            return
        candidates = _local_sdp_candidates(self._camera_pc.localDescription.sdp)
        self._camera_local_candidate_count = len(candidates)
        LOGGER.debug(
            "X-Sense WebRTC sending local ICE candidates: %s",
            self._debug_context(**_candidate_debug_summary(candidates)),
        )
        for candidate in candidates:
            if self._closed or self._ws is None or getattr(self._ws, "closed", False):
                return
            candidate_payload = make_ice_candidate_payload(
                candidate=candidate["candidate"],
                sdp_mid=candidate["sdpMid"],
                sdp_m_line_index=candidate["sdpMLineIndex"],
                ticket=self._ticket,
                recipient_client_id=self._recipient_client_id,
                session_id=self._session_id,
            )
            with suppress(
                aiohttp.ClientConnectionError,
                aiohttp.ClientConnectionResetError,
                ConnectionError,
                RuntimeError,
            ):
                await self._ws.send_str(candidate_payload)
                continue
            LOGGER.debug(
                "X-Sense WebRTC stopped sending ICE candidates because signal closed: %s",
                self._debug_context(candidate_count=len(candidates)),
            )
            return

    async def _read_loop(self) -> None:
        if self._ws is None:
            return
        try:
            async for message in self._ws:
                if self._closed:
                    return
                if message.type not in (
                    aiohttp.WSMsgType.TEXT,
                    aiohttp.WSMsgType.BINARY,
                ):
                    continue
                event, payload = parse_signal_message(message.data)
                if event:
                    self._last_signal_event = event
                    self._signal_event_counts[event] += 1
                LOGGER.debug(
                    "X-Sense WebRTC signal event received: %s",
                    self._debug_context(event=event, payload=_payload_debug(payload)),
                )
                await self._handle_signal_event(event, payload)
        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001 - signal server can close mid-session
            if not self._closed:
                LOGGER.debug(
                    "X-Sense WebRTC signal reader stopped: %s",
                    self._debug_context(
                        error=type(err).__name__,
                        message=str(err),
                        signal_close_code=getattr(self._ws, "close_code", None),
                    ),
                    exc_info=err,
                )
        finally:
            if (
                not self._closed
                and self._ws is not None
                and getattr(self._ws, "closed", False)
            ):
                close_code = getattr(self._ws, "close_code", None)
                LOGGER.debug(
                    "X-Sense WebRTC signal websocket closed: %s",
                    self._debug_context(
                        signal_close_code=close_code,
                        signal_exception=repr(
                            getattr(self._ws, "exception", lambda: None)()
                        ),
                    ),
                )
                self._schedule_signal_reconnect(close_code)

    async def _handle_signal_event(self, event: str | None, payload: Any) -> None:
        if self._closed:
            return
        if event == "PEER_IN":
            if _is_owned_peer_message(payload, self._ticket.serial_number):
                LOGGER.debug(
                    "X-Sense WebRTC peer event matched camera: %s",
                    self._debug_context(
                        event=event,
                        **_peer_event_debug(payload, self._ticket.serial_number),
                    ),
                )
                self._recipient_client_id = (
                    _matching_peer_id(payload, self._ticket.serial_number)
                    or self._ticket.serial_number
                )
                self._camera_peer_ready = True
                task = getattr(self, "_peer_in_timeout_task", None)
                if task:
                    task.cancel()
                if self._camera_offer_sdp is None:
                    await self._start_camera_peer()
                else:
                    await self._send_offer()
            else:
                LOGGER.debug(
                    "X-Sense WebRTC ignored foreign peer event: %s",
                    self._debug_context(
                        event=event,
                        **_peer_event_debug(payload, self._ticket.serial_number),
                    ),
                )
        elif event == "SDP_ANSWER":
            answer = _owned_answer_sdp(payload, self._ticket)
            if answer:
                LOGGER.debug(
                    "X-Sense WebRTC applying SDP answer: %s",
                    self._debug_context(answer_sdp=_sdp_debug(answer)),
                )
                if self._camera_pc is None:
                    return
                await self._camera_pc.setRemoteDescription(
                    RTCSessionDescription(sdp=answer, type="answer")
                )
                self._sdp_answer_received = True
                await self._flush_pending_camera_candidates()
            else:
                LOGGER.debug(
                    "X-Sense WebRTC ignored invalid or foreign SDP answer: %s",
                    self._debug_context(
                        payload=_payload_debug(payload),
                        reason=_answer_reject_reason(payload, self._ticket),
                    ),
                )
        elif event == "ICE_CANDIDATE":
            candidate = _candidate_payload_to_aiortc(payload)
            if candidate:
                self._camera_remote_candidate_count += 1
                if self._camera_pc is None or self._camera_pc.remoteDescription is None:
                    self._pending_camera_candidates.append(candidate)
                    LOGGER.debug(
                        "X-Sense WebRTC queued camera ICE candidate: %s",
                        self._debug_context(
                            pending_camera_candidates=len(
                                self._pending_camera_candidates
                            )
                        ),
                    )
                else:
                    if self._camera_pc is not None:
                        await self._camera_pc.addIceCandidate(candidate)
                    LOGGER.debug(
                        "X-Sense WebRTC applied camera ICE candidate: %s",
                        self._debug_context(),
                    )
        elif event == "PEER_OUT":
            if _is_owned_peer_message(payload, self._ticket.serial_number):
                LOGGER.debug(
                    "X-Sense WebRTC peer went offline before stream: %s",
                    self._debug_context(
                        event=event,
                        signal_events=dict(self._signal_event_counts),
                        local_candidate_count=self._camera_local_candidate_count,
                        remote_candidate_count=self._camera_remote_candidate_count,
                        pending_ha_candidates=len(self._pending_ha_candidates),
                        pending_camera_candidates=len(
                            self._pending_camera_candidates
                        ),
                        **_peer_event_debug(payload, self._ticket.serial_number),
                    ),
                )
                # The APK marks the camera offline on PEER_OUT and lets the
                # broader play/first-frame timeouts own user-facing failure.
            else:
                LOGGER.debug(
                    "X-Sense WebRTC ignored foreign peer event: %s",
                    self._debug_context(
                        event=event,
                        **_peer_event_debug(payload, self._ticket.serial_number),
                    ),
                )

    async def _flush_pending_ha_candidates(self) -> None:
        """Apply queued browser ICE candidates after the HA offer is set."""
        while self._pending_ha_candidates and not self._closed:
            await self._ha_pc.addIceCandidate(self._pending_ha_candidates.pop(0))

    async def _flush_pending_camera_candidates(self) -> None:
        """Apply queued camera ICE candidates after the APK-style SDP answer gate."""
        while self._pending_camera_candidates and not self._closed:
            if self._camera_pc is None:
                return
            await self._camera_pc.addIceCandidate(
                self._pending_camera_candidates.pop(0)
            )


def _camera_rtc_configuration(ticket: XSenseWebRTCTicket) -> AiortcRTCConfiguration:
    servers = []
    for server in ticket.ice_servers or []:
        url = server.get("url") if isinstance(server, dict) else None
        if not url:
            continue
        servers.append(
            AiortcRTCIceServer(
                urls=url,
                username=server.get("username"),
                credential=server.get("credential"),
            )
        )
    return AiortcRTCConfiguration(
        iceServers=servers, bundlePolicy=AiortcRTCBundlePolicy.MAX_BUNDLE
    )


def _answer_sdp(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    encoded = payload.get("messagePayload")
    if not isinstance(encoded, str):
        return None
    with suppress(Exception):
        decoded = json.loads(base64.b64decode(encoded).decode())
        sdp = decoded.get("sdp")
        if isinstance(sdp, str):
            return sdp
    return None


def _owned_answer_sdp(payload: Any, ticket: XSenseWebRTCTicket) -> str | None:
    """Return the SDP answer only when it belongs to this APK-style session."""
    if not isinstance(payload, dict):
        return None
    sender = payload.get("senderClientId")
    recipient = payload.get("recipientClientId")
    if sender and sender != ticket.serial_number:
        return None
    if recipient and recipient != ticket.client_id:
        return None
    return _answer_sdp(payload)


def _data_channel_answer_sdp(payload: Any) -> str | None:
    """Return the APK changeTransceiverOffer answer SDP from data-channel JSON."""
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if not isinstance(data, dict):
        return None
    encoded = data.get("answer")
    if not isinstance(encoded, str):
        return None
    with suppress(Exception):
        decoded = json.loads(base64.b64decode(encoded).decode())
        sdp = decoded.get("sdp")
        if isinstance(sdp, str):
            return sdp
    return None


def _is_owned_peer_message(payload: Any, serial_number: str) -> bool:
    """Return whether a PEER_IN/PEER_OUT payload belongs to this camera."""
    return _matching_peer_id(payload, serial_number) is not None


def _matching_peer_id(payload: Any, serial_number: str) -> str | None:
    for value in _peer_payload_candidates(payload):
        if value == serial_number:
            return value
    return None


def _peer_payload_candidates(payload: Any) -> list[str]:
    if isinstance(payload, str):
        return [payload.strip()]
    if not isinstance(payload, dict):
        return []
    candidates: list[str] = []
    for key in (
        "clientId",
        "serialNumber",
        "deviceSn",
        "deviceSN",
        "sn",
        "id",
        "name",
    ):
        value = payload.get(key)
        if value in (None, ""):
            continue
        text = str(value).strip()
        if text and text not in candidates:
            candidates.append(text)
    return candidates


def _sdp_without_local_candidates(sdp: str) -> str:
    """Return the createOffer-style SDP before local ICE candidates are appended."""
    lines = [
        line
        for line in sdp.splitlines()
        if not line.startswith("a=candidate:")
        and not line.startswith("a=end-of-candidates")
    ]
    ending = "\r\n" if "\r\n" in sdp else "\n"
    return ending.join(lines) + (ending if sdp.endswith(("\r\n", "\n")) else "")


def _apk_camera_offer_sdp(sdp: str) -> str:
    """Return the camera offer SDP in the APK createOffer callback shape."""
    # The APK forwards SessionDescription.description from createOffer before
    # trickled ICE candidates are appended. It does not rewrite codecs or DTLS
    # fingerprints, so only strip local candidates gathered by aiortc.
    return _sdp_without_local_candidates(sdp)


def _local_sdp_candidates(sdp: str) -> list[dict[str, Any]]:
    """Return APK-style candidate payloads from a gathered local SDP."""
    candidates: list[dict[str, Any]] = []
    current_mid: str | None = None
    current_index = -1
    for raw_line in sdp.splitlines():
        line = raw_line.strip()
        if line.startswith("m="):
            current_index += 1
            current_mid = None
        elif line.startswith("a=mid:"):
            current_mid = line.removeprefix("a=mid:")
        elif line.startswith("a=candidate:"):
            candidate = line.removeprefix("a=")
            if not _is_apk_supported_local_candidate(candidate):
                continue
            candidates.append(
                {
                    "sdpMid": current_mid,
                    "sdpMLineIndex": current_index,
                    "candidate": candidate,
                }
            )
    return candidates


def _is_apk_supported_local_candidate(candidate: str) -> bool:
    """Return whether the APK would signal this local ICE candidate."""
    parts = candidate.split()
    protocol = parts[2].lower() if len(parts) > 2 else ""
    return (
        protocol != "tcp"
        and "127.0.0.1" not in candidate
        and "::1" not in candidate
    )


def _candidate_payload_to_aiortc(payload: Any) -> RTCIceCandidate | None:
    if not isinstance(payload, dict):
        return None
    candidate = payload.get("candidate")
    if not isinstance(candidate, str):
        return None
    parsed = candidate_from_sdp(candidate)
    parsed.sdpMid = payload.get("sdpMid")
    parsed.sdpMLineIndex = payload.get("sdpMLineIndex")
    return parsed


def _candidate_init_to_aiortc(candidate: RTCIceCandidateInit) -> RTCIceCandidate:
    parsed = candidate_from_sdp(candidate.candidate)
    parsed.sdpMid = candidate.sdp_mid
    parsed.sdpMLineIndex = candidate.sdp_m_line_index
    return parsed


def _b64_json(data: dict[str, Any]) -> str:
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.b64encode(raw).decode()


def _map_video_size(resolution: str) -> str:
    if resolution in {"640x360", "640x480", "960x720"}:
        return "1280x720"
    if resolution in {"1280x720", "1280x960"}:
        return "1280x720"
    if resolution in {
        "1920x1080",
        "2048x1440",
        "2048x1536",
        "2304x1296",
        "2560x1440",
        "3840x2160",
        "7680x4320",
    }:
        return "1920x1080"
    return "1280x720"
