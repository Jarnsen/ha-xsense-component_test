"""X-Sense ADDX WebRTC signaling helpers."""

from __future__ import annotations

import asyncio
import base64
import json
import random
import time
import warnings
from contextlib import suppress
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
_DEFAULT_RESOLUTION = "auto"
_PEER_IN_TIMEOUT = 20
_PLAY_TIMEOUT = 40
_FIRST_FRAME_TIMEOUT = 10


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
    """Media track that forwards frames from the X-Sense camera peer."""

    def __init__(self, kind: str, on_frame: Callable[[], None] | None = None) -> None:
        super().__init__()
        self.kind = kind
        self._on_frame = on_frame
        self._source: asyncio.Future[MediaStreamTrack] = (
            asyncio.get_running_loop().create_future()
        )

    def set_source(self, track: MediaStreamTrack) -> None:
        """Set the source track once the camera peer receives it."""
        if not self._source.done():
            self._source.set_result(track)

    async def recv(self):
        """Return the next frame from the camera peer."""
        if self.readyState != "live":
            raise MediaStreamError
        source = await self._source
        frame = await source.recv()
        if self._on_frame:
            self._on_frame()
        return frame


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
    message = make_data_channel_command("startLive")
    message.update(
        {
            "size": _map_video_size(resolution),
            "resolution": resolution,
        }
    )
    return message


def make_data_channel_command(action: str) -> dict[str, Any]:
    """Return the APK-compatible base data-channel command."""
    return {
        "requestID": f"{int(time.time() * 1000)}-{random.randint(0, 999)}",
        "connectionID": "7893feb",
        "timeStamp": int(time.time()),
        "action": action,
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
    if isinstance(payload, str) and event == "SDP_ANSWER":
        payload = data
    elif isinstance(payload, str) and event == "ICE_CANDIDATE":
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
        self._video = _ProxyTrack("video", self._mark_first_frame_received)
        self._audio = _ProxyTrack("audio")
        self._data_channel = None
        self._pending_ha_candidates: list[RTCIceCandidate] = []
        self._pending_camera_candidates: list[RTCIceCandidate] = []
        self._camera_peer_ready = False
        self._camera_offer_sent = False
        self._camera_offer_sdp: str | None = None
        self._camera_local_description_task: asyncio.Task[None] | None = None
        self._peer_in_timeout_task: asyncio.Task[None] | None = None
        self._play_timeout_task: asyncio.Task[None] | None = None
        self._first_frame_timeout_task: asyncio.Task[None] | None = None
        self._start_live_sent = False
        self._first_frame_received = False
        self._closed = False
        self._close_lock = asyncio.Lock()

    async def start(self) -> bool:
        """Connect both WebRTC peers and start the X-Sense camera stream."""
        try:
            self._setup_camera_peer()
            self._ha_pc.addTrack(self._video)
            self._ha_pc.addTrack(self._audio)
            await self._ha_pc.setRemoteDescription(
                RTCSessionDescription(sdp=self._offer_sdp, type="offer")
            )
            await self._flush_pending_ha_candidates()
            answer = await self._ha_pc.createAnswer()
            await self._ha_pc.setLocalDescription(answer)
            self._send_message(WebRTCAnswer(self._ha_pc.localDescription.sdp))

            connect_options = self._ticket.signal_connect_options()
            connect_url = connect_options.pop("url", self._ticket.signal_url())
            self._ws = await self._session.ws_connect(
                connect_url, heartbeat=30, **connect_options
            )
            self._reader_task = asyncio.create_task(self._read_loop())
            self._peer_in_timeout_task = asyncio.create_task(
                self._fail_after_timeout(
                    _PEER_IN_TIMEOUT,
                    "xsense_webrtc_peer_in_timeout",
                    "Camera did not join the WebRTC session",
                )
            )
            self._play_timeout_task = asyncio.create_task(
                self._fail_after_timeout(
                    _PLAY_TIMEOUT,
                    "xsense_webrtc_play_timeout",
                    "Camera live view did not start",
                )
            )
            await self._start_camera_peer()
            return True
        except Exception as err:  # noqa: BLE001 - surface cleanly to HA frontend
            LOGGER.debug("Unable to start X-Sense WebRTC bridge", exc_info=err)
            self._send_message(WebRTCError("xsense_webrtc_start_failed", str(err)))
            await self.close()
            return False

    async def add_candidate(self, candidate: RTCIceCandidateInit) -> None:
        """Forward a browser ICE candidate after the HA offer has been applied."""
        if self._closed:
            return
        parsed = _candidate_init_to_aiortc(candidate)
        if self._ha_pc.remoteDescription is None:
            self._pending_ha_candidates.append(parsed)
            return
        await self._ha_pc.addIceCandidate(parsed)

    async def close(self) -> None:
        """Close the X-Sense signaling and WebRTC sessions."""
        async with self._close_lock:
            if self._closed:
                return
            self._closed = True
            self._send_stop_live()
            if self._reader_task:
                self._reader_task.cancel()
                with suppress(asyncio.CancelledError, Exception):
                    await self._reader_task
            await self._cancel_task(getattr(self, "_peer_in_timeout_task", None))
            await self._cancel_task(getattr(self, "_play_timeout_task", None))
            await self._cancel_task(getattr(self, "_first_frame_timeout_task", None))
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
                await self._camera_pc.close()
            with suppress(Exception):
                await self._ha_pc.close()
            self._pending_ha_candidates.clear()
            self._pending_camera_candidates.clear()

    def _create_task(
        self, coro: Coroutine[Any, Any, Any]
    ) -> asyncio.Task[Any] | None:
        try:
            return asyncio.create_task(coro)
        except Exception:
            coro.close()
            return None

    async def _cancel_task(self, task: asyncio.Task[Any] | None) -> None:
        if task and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await task

    async def _fail_after_timeout(self, delay: int, code: str, message: str) -> None:
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            raise
        if self._closed:
            return
        self._send_message(WebRTCError(code, message))
        await self.close()

    def _mark_first_frame_received(self) -> None:
        if self._first_frame_received:
            return
        self._first_frame_received = True
        first_frame_task = getattr(self, "_first_frame_timeout_task", None)
        if first_frame_task:
            first_frame_task.cancel()
        play_task = getattr(self, "_play_timeout_task", None)
        if play_task:
            play_task.cancel()

    def _send_stop_live(self) -> None:
        """Send the APK stopLive data-channel command before closing."""
        if getattr(self._data_channel, "readyState", None) != "open":
            return
        with suppress(Exception):
            self._data_channel.send(
                json.dumps(
                    make_data_channel_command("stopLive"),
                    separators=(",", ":"),
                )
            )

    def _setup_camera_peer(self) -> None:
        @self._camera_pc.on("track")
        def on_track(track):
            if track.kind == "video":
                self._video.set_source(track)
            elif track.kind == "audio":
                self._audio.set_source(track)

        self._data_channel = self._camera_pc.createDataChannel(SIGNAL_DATA_CHANNEL)

        @self._data_channel.on("open")
        def on_open():
            self._send_start_live_if_ready()

        @self._camera_pc.on("connectionstatechange")
        def on_connectionstatechange():
            state = self._camera_pc.connectionState
            if state in {"failed", "closed"} and not self._closed:
                self._send_message(
                    WebRTCError(
                        "xsense_webrtc_peer_failed",
                        f"Camera peer connection {state}",
                    )
                )
                self._create_task(self.close())

    def _send_start_live_if_ready(self) -> None:
        """Send startLive when the APK would: after the data channel opens."""
        if self._start_live_sent or getattr(
            self._data_channel, "readyState", None
        ) != "open":
            return
        try:
            self._data_channel.send(
                json.dumps(
                    make_start_live_data_channel_message(self._resolution),
                    separators=(",", ":"),
                )
            )
        except Exception as err:
            LOGGER.debug("Unable to send X-Sense startLive command", exc_info=err)
            return
        self._start_live_sent = True
        self._first_frame_timeout_task = self._create_task(
            self._fail_after_timeout(
                _FIRST_FRAME_TIMEOUT,
                "xsense_webrtc_first_frame_timeout",
                "Camera did not send a video frame",
            )
        )

    async def _start_camera_peer(self) -> None:
        self._camera_pc.addTransceiver("video", direction="recvonly")
        self._camera_pc.addTransceiver("audio", direction="recvonly")
        offer = await self._camera_pc.createOffer()
        self._camera_offer_sdp = offer.sdp
        self._camera_local_description_task = asyncio.create_task(
            self._camera_pc.setLocalDescription(offer)
        )
        await self._send_offer()

    async def _send_offer(self) -> None:
        if (
            self._closed
            or self._ws is None
            or getattr(self._ws, "closed", False)
            or self._camera_offer_sdp is None
            or not self._camera_peer_ready
            or self._camera_offer_sent
        ):
            return
        await self._ws.send_str(
            make_sdp_offer_payload(
                offer_sdp=self._camera_offer_sdp,
                ticket=self._ticket,
                recipient_client_id=self._recipient_client_id,
                session_id=self._session_id,
                resolution=self._resolution,
            )
        )
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
        for candidate in _local_sdp_candidates(self._camera_pc.localDescription.sdp):
            if self._closed or self._ws is None or getattr(self._ws, "closed", False):
                return
            await self._ws.send_str(
                make_ice_candidate_payload(
                    candidate=candidate["candidate"],
                    sdp_mid=candidate["sdpMid"],
                    sdp_m_line_index=candidate["sdpMLineIndex"],
                    ticket=self._ticket,
                    recipient_client_id=self._recipient_client_id,
                    session_id=self._session_id,
                )
            )

    async def _read_loop(self) -> None:
        if self._ws is None:
            return
        try:
            async for message in self._ws:
                if self._closed:
                    return
                if message.type not in (aiohttp.WSMsgType.TEXT, aiohttp.WSMsgType.BINARY):
                    continue
                event, payload = parse_signal_message(message.data)
                await self._handle_signal_event(event, payload)
        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001 - signal server can close mid-session
            if not self._closed:
                LOGGER.debug("X-Sense WebRTC signal reader stopped", exc_info=err)

    async def _handle_signal_event(self, event: str | None, payload: Any) -> None:
        if self._closed:
            return
        if event == "PEER_IN":
            if _is_owned_peer_message(payload, self._ticket.serial_number):
                self._recipient_client_id = str(payload)
                self._camera_peer_ready = True
                task = getattr(self, "_peer_in_timeout_task", None)
                if task:
                    task.cancel()
                await self._send_offer()
        elif event == "SDP_ANSWER":
            answer = _owned_answer_sdp(payload, self._ticket)
            if answer:
                await self._camera_pc.setRemoteDescription(
                    RTCSessionDescription(sdp=answer, type="answer")
                )
                await self._flush_pending_camera_candidates()
        elif event == "ICE_CANDIDATE":
            candidate = _candidate_payload_to_aiortc(payload)
            if candidate:
                if self._camera_pc.remoteDescription is None:
                    self._pending_camera_candidates.append(candidate)
                else:
                    await self._camera_pc.addIceCandidate(candidate)
        elif event == "PEER_OUT":
            if _is_owned_peer_message(payload, self._ticket.serial_number):
                self._send_message(
                    WebRTCError(
                        "xsense_webrtc_peer_offline", "Camera peer went offline"
                    )
                )

    async def _flush_pending_ha_candidates(self) -> None:
        """Apply queued browser ICE candidates after the HA offer is set."""
        while self._pending_ha_candidates and not self._closed:
            await self._ha_pc.addIceCandidate(self._pending_ha_candidates.pop(0))

    async def _flush_pending_camera_candidates(self) -> None:
        """Apply queued camera ICE candidates after the APK-style SDP answer gate."""
        while self._pending_camera_candidates and not self._closed:
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


def _owned_answer_sdp(payload: Any, ticket: XSenseWebRTCTicket) -> str | None:
    """Return the SDP answer only when it belongs to this APK-style session."""
    if isinstance(payload, dict):
        sender = payload.get("senderClientId")
        recipient = payload.get("recipientClientId")
        if sender and sender != ticket.serial_number:
            return None
        if recipient and recipient != ticket.client_id:
            return None
    return _answer_sdp(payload)


def _is_owned_peer_message(payload: Any, serial_number: str) -> bool:
    """Return whether a PEER_IN/PEER_OUT payload belongs to this camera."""
    return isinstance(payload, str) and payload == serial_number


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
    if len(parts) < 3 or parts[2].lower() != "udp":
        return False
    return "127.0.0.1" not in candidate and "::1" not in candidate


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
