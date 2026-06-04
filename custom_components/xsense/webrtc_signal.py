"""X-Sense ADDX WebRTC signaling helpers."""

from __future__ import annotations

import asyncio
import base64
import json
import time
from contextlib import suppress
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse, urlunparse

import aiohttp
from aiortc import (
    RTCBundlePolicy as AiortcRTCBundlePolicy,
    RTCConfiguration as AiortcRTCConfiguration,
    RTCIceCandidate,
    RTCIceServer as AiortcRTCIceServer,
    RTCPeerConnection,
    RTCSessionDescription,
)
from aiortc.mediastreams import MediaStreamError, MediaStreamTrack
from aiortc.sdp import candidate_from_sdp, candidate_to_sdp
from homeassistant.components.camera.webrtc import (
    WebRTCAnswer,
    WebRTCError,
    WebRTCSendMessage,
)
from webrtc_models import RTCIceCandidateInit

from .const import LOGGER

SIGNAL_MODE = "vicoo"
SIGNAL_VIEWER_TYPE = "a4x_sdk"
SIGNAL_DATA_CHANNEL = "data-channel-of-"
_SIGNAL_NAME = "test-123"
_DEFAULT_RESOLUTION = "auto"


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
            return True
        return self.expiration_time > int(time.time() * 1000) + 60_000

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
    """Media track that forwards frames from the X-Sense camera peer."""

    def __init__(self, kind: str) -> None:
        super().__init__()
        self.kind = kind
        self._source: asyncio.Future[MediaStreamTrack] = asyncio.get_running_loop().create_future()

    def set_source(self, track: MediaStreamTrack) -> None:
        """Set the source track once the camera peer receives it."""
        if not self._source.done():
            self._source.set_result(track)

    async def recv(self):
        """Return the next frame from the camera peer."""
        if self.readyState != "live":
            raise MediaStreamError
        source = await self._source
        return await source.recv()


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def make_sdp_offer_payload(
    *,
    offer_sdp: str,
    ticket: XSenseWebRTCTicket,
    recipient_client_id: str,
    session_id: str,
    resolution: str | None,
) -> str:
    """Return the APK-compatible SDP offer envelope."""
    payload = _b64_json({"type": "offer", "sdp": offer_sdp})
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
    candidate: RTCIceCandidate | RTCIceCandidateInit,
    ticket: XSenseWebRTCTicket,
    recipient_client_id: str,
    session_id: str,
) -> str:
    """Return the APK-compatible ICE candidate envelope."""
    candidate_sdp = _candidate_to_sdp(candidate)
    sdp_mid = getattr(candidate, "sdpMid", None) or getattr(candidate, "sdp_mid", None)
    sdp_m_line_index = getattr(candidate, "sdpMLineIndex", None)
    if sdp_m_line_index is None:
        sdp_m_line_index = getattr(candidate, "sdp_m_line_index", None)
    payload = _b64_json(
        {
            "sdpMid": sdp_mid,
            "sdpMLineIndex": sdp_m_line_index,
            "candidate": candidate_sdp,
        }
    )
    envelope = {
        "messageType": "ICE_CANDIDATE",
        "messagePayload": payload,
        "recipientClientId": recipient_client_id,
        "senderClientId": ticket.client_id,
        "sessionId": session_id,
    }
    return json.dumps(envelope, separators=(",", ":"))


def make_start_live_data_channel_message(resolution: str) -> dict[str, Any]:
    """Return the APK-compatible data-channel startLive command."""
    timestamp = int(time.time())
    return {
        "requestID": f"cmd_{timestamp}",
        "connectionID": "7893feb",
        "timeStamp": timestamp,
        "action": "startLive",
        "size": _map_video_size(resolution),
        "resolution": resolution,
    }


def parse_signal_message(raw: str | bytes) -> tuple[str | None, Any]:
    """Parse a signal-server message into the APK event callback shape."""
    if isinstance(raw, bytes):
        raw = raw.decode(errors="ignore")
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None, raw

    event = data.get("messageType") or data.get("event") or data.get("type")
    payload: Any = _signal_payload(data)
    if isinstance(payload, str) and event in {"SDP_ANSWER", "ICE_CANDIDATE"}:
        with suppress(Exception):
            payload = json.loads(base64.b64decode(payload).decode())
    if event in {"PEER_IN", "PEER_OUT"}:
        payload = _signal_peer_payload(payload)
    return event, payload


def _signal_payload(data: dict[str, Any]) -> Any:
    for key in ("messagePayload", "payload", "data", "message", "body"):
        if key in data:
            return data[key]
    return data


def _signal_peer_payload(payload: Any) -> Any:
    if isinstance(payload, str):
        with suppress(Exception):
            payload = json.loads(payload)
    if isinstance(payload, dict):
        for key in ("clientId", "serialNumber", "deviceSn", "deviceSN", "sn"):
            value = payload.get(key)
            if value:
                return str(value)
    return payload


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
    ) -> None:
        self._session = session
        self._ticket = ticket
        self._offer_sdp = offer_sdp
        self._resolution = resolution or _DEFAULT_RESOLUTION
        self._send_message = send_message
        self._session_id = session_id or ticket.session_id
        self._recipient_client_id = ticket.serial_number
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._ha_pc = RTCPeerConnection()
        self._camera_pc = RTCPeerConnection(_camera_rtc_configuration(ticket))
        self._video = _ProxyTrack("video")
        self._audio = _ProxyTrack("audio")
        self._data_channel = None

    async def start(self) -> None:
        """Connect both WebRTC peers and start the X-Sense camera stream."""
        try:
            self._setup_camera_peer()
            self._ha_pc.addTrack(self._video)
            self._ha_pc.addTrack(self._audio)
            await self._ha_pc.setRemoteDescription(
                RTCSessionDescription(sdp=self._offer_sdp, type="offer")
            )
            answer = await self._ha_pc.createAnswer()
            await self._ha_pc.setLocalDescription(answer)
            self._send_message(WebRTCAnswer(self._ha_pc.localDescription.sdp))

            connect_options = self._ticket.signal_connect_options()
            connect_url = connect_options.pop("url", self._ticket.signal_url())
            self._ws = await self._session.ws_connect(
                connect_url, heartbeat=30, **connect_options
            )
            self._reader_task = asyncio.create_task(self._read_loop())
            await self._start_camera_peer()
        except Exception as err:  # noqa: BLE001 - surface cleanly to HA frontend
            LOGGER.debug("Unable to start X-Sense WebRTC bridge", exc_info=err)
            self._send_message(WebRTCError("xsense_webrtc_start_failed", str(err)))
            await self.close()

    async def add_candidate(self, candidate: RTCIceCandidateInit) -> None:
        """Forward a browser ICE candidate to the HA-facing peer."""
        await self._ha_pc.addIceCandidate(_candidate_init_to_aiortc(candidate))

    async def close(self) -> None:
        """Close the X-Sense signaling and WebRTC sessions."""
        if self._reader_task:
            self._reader_task.cancel()
        if self._ws and not self._ws.closed:
            await self._ws.close()
        await self._camera_pc.close()
        await self._ha_pc.close()

    def _setup_camera_peer(self) -> None:
        @self._camera_pc.on("icecandidate")
        async def on_icecandidate(candidate):
            if candidate is not None and self._ws is not None and not self._ws.closed:
                await self._ws.send_str(
                    make_ice_candidate_payload(
                        candidate=candidate,
                        ticket=self._ticket,
                        recipient_client_id=self._recipient_client_id,
                        session_id=self._session_id,
                    )
                )

        @self._camera_pc.on("track")
        def on_track(track):
            if track.kind == "video":
                self._video.set_source(track)
            elif track.kind == "audio":
                self._audio.set_source(track)

        self._data_channel = self._camera_pc.createDataChannel(SIGNAL_DATA_CHANNEL)

        @self._data_channel.on("open")
        def on_open():
            self._data_channel.send(
                json.dumps(
                    make_start_live_data_channel_message(self._resolution),
                    separators=(",", ":"),
                )
            )

    async def _start_camera_peer(self) -> None:
        self._camera_pc.addTransceiver("video", direction="recvonly")
        self._camera_pc.addTransceiver("audio", direction="recvonly")
        offer = await self._camera_pc.createOffer()
        await self._camera_pc.setLocalDescription(offer)
        await self._send_offer()

    async def _send_offer(self) -> None:
        if self._ws is None or self._camera_pc.localDescription is None:
            return
        await self._ws.send_str(
            make_sdp_offer_payload(
                offer_sdp=self._camera_pc.localDescription.sdp,
                ticket=self._ticket,
                recipient_client_id=self._recipient_client_id,
                session_id=self._session_id,
                resolution=self._resolution,
            )
        )

    async def _read_loop(self) -> None:
        if self._ws is None:
            return
        async for message in self._ws:
            if message.type not in (aiohttp.WSMsgType.TEXT, aiohttp.WSMsgType.BINARY):
                continue
            event, payload = parse_signal_message(message.data)
            if event == "PEER_IN":
                if isinstance(payload, str) and payload:
                    self._recipient_client_id = payload
                await self._send_offer()
            elif event == "SDP_ANSWER":
                answer = _answer_sdp(payload)
                if answer:
                    await self._camera_pc.setRemoteDescription(
                        RTCSessionDescription(sdp=answer, type="answer")
                    )
            elif event == "ICE_CANDIDATE":
                candidate = _candidate_payload_to_aiortc(payload)
                if candidate:
                    await self._camera_pc.addIceCandidate(candidate)
            elif event == "PEER_OUT":
                self._send_message(
                    WebRTCError(
                        "xsense_webrtc_peer_offline", "Camera peer went offline"
                    )
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
    if isinstance(payload, dict):
        nested = payload.get("sdp")
        if isinstance(nested, str):
            return nested
        encoded = payload.get("messagePayload")
        if isinstance(encoded, str):
            with suppress(Exception):
                decoded = json.loads(base64.b64decode(encoded).decode())
                return decoded.get("sdp")
    return None


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


def _candidate_to_sdp(candidate: RTCIceCandidate | RTCIceCandidateInit) -> str:
    if isinstance(candidate, RTCIceCandidateInit):
        return candidate.candidate
    return candidate_to_sdp(candidate)


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
