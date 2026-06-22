"""X-Sense ADDX WebRTC signaling helpers."""

from __future__ import annotations

import asyncio
import base64
import json
import time
from collections import Counter
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse, urlunparse

import aiohttp

from .const import LOGGER

SIGNAL_MODE = "vicoo"
SIGNAL_VIEWER_TYPE = "a4x_sdk"
_SIGNAL_NAME = "test-123"
_DEFAULT_RESOLUTION = "1280x720"
_ANSWER_TIMEOUT = 40
_SIGNAL_RECONNECT_DELAY = 5
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


class XSenseWebRTCSignalSession:
    """Relay Home Assistant WebRTC SDP through the X-Sense signal server."""

    def __init__(
        self,
        *,
        session: aiohttp.ClientSession,
        ticket: XSenseWebRTCTicket,
        offer_sdp: str,
        resolution: str | None,
        camera_online: bool,
        remote_candidate_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self._session = session
        self._ticket = ticket
        self._offer_sdp = offer_sdp
        self._resolution = resolution or _DEFAULT_RESOLUTION
        self._camera_online = camera_online
        self._session_id = ticket.session_id
        self._recipient_client_id = ticket.serial_number
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._answer: asyncio.Future[str] = asyncio.get_running_loop().create_future()
        self._closed = False
        self._offer_sent = False
        self._camera_peer_ready = False
        self._signal_event_counts: Counter[str] = Counter()
        self._local_candidate_count = 0
        self._sent_candidate_count = 0
        self._offer_attempt_count = 0
        self._signal_reconnect_count = 0
        self._pending_remote_candidates: list[Any] = []
        self._ha_candidate_history: list[dict[str, Any]] = []
        self._pending_client_candidates: list[dict[str, Any]] = []
        self._remote_candidate_callback = remote_candidate_callback
        self._forward_client_candidates = False
        self._last_signal_event: str | None = None
        self._read_task: asyncio.Task | None = None
        self._reconnect_task: asyncio.Task | None = None

    def _debug_context(self, **extra: Any) -> dict[str, Any]:
        context = _ticket_debug_context(self._ticket)
        context.update(
            {
                "session": _short_id(self._session_id),
                "recipient": _short_id(self._recipient_client_id),
                "resolution": self._resolution,
                "camera_online": self._camera_online,
                "camera_peer_ready": self._camera_peer_ready,
                "offer_sent": self._offer_sent,
                "sdp_answer_received": _future_has_result(self._answer),
                "last_signal_event": self._last_signal_event,
                "signal_events": dict(self._signal_event_counts),
                "offer_attempt_count": self._offer_attempt_count,
                "signal_reconnect_count": self._signal_reconnect_count,
                "local_candidate_count": self._local_candidate_count,
                "sent_candidate_count": self._sent_candidate_count,
                "pending_remote_candidates": len(self._pending_remote_candidates),
                "pending_client_candidates": len(self._pending_client_candidates),
            }
        )
        context.update(extra)
        return context

    async def start(self) -> str:
        """Return the X-Sense SDP answer for a Home Assistant WebRTC offer."""
        LOGGER.debug("X-Sense WebRTC signal relay starting: %s", self._debug_context())
        await self._connect_signal()
        LOGGER.debug(
            "X-Sense WebRTC waiting for PEER_IN before relay offer: %s",
            self._debug_context(answer_timeout_s=_ANSWER_TIMEOUT),
        )
        try:
            return await asyncio.wait_for(self._answer, timeout=_ANSWER_TIMEOUT)
        except Exception as err:
            LOGGER.debug(
                "X-Sense WebRTC signal relay failed: %s",
                self._debug_context(error=_exception_debug(err)),
            )
            raise

    async def close(self) -> None:
        """Close the X-Sense signal connection."""
        self._closed = True
        ws = self._ws
        self._ws = None
        if ws is not None and not ws.closed:
            with suppress(Exception):
                await ws.close()
        if self._read_task is not None:
            self._read_task.cancel()
            self._read_task = None
        if self._reconnect_task is not None:
            self._reconnect_task.cancel()
            self._reconnect_task = None

    def start_forwarding_remote_candidates(self) -> None:
        """Forward queued X-Sense ICE candidates to Home Assistant."""
        self._forward_client_candidates = True
        LOGGER.debug(
            "X-Sense WebRTC signal relay forwarding queued remote candidates to HA: %s",
            self._debug_context(
                queued_remote_candidate_count=len(self._pending_client_candidates)
            ),
        )
        while self._pending_client_candidates:
            self._forward_remote_candidate(self._pending_client_candidates.pop(0))

    async def add_candidate(self, candidate: Any) -> None:
        """Forward a trickled Home Assistant WebRTC candidate to X-Sense."""
        if self._closed:
            return
        payload = _candidate_init_payload(candidate)
        if payload is None:
            LOGGER.debug(
                "X-Sense WebRTC signal relay ignored invalid HA ICE candidate: %s",
                self._debug_context(candidate_type=type(candidate).__name__),
            )
            return
        if payload not in self._ha_candidate_history:
            self._ha_candidate_history.append(payload)
        if self._ws is None or self._ws.closed or not self._offer_sent:
            self._pending_remote_candidates.append(payload)
            queued_count = len(self._pending_remote_candidates)
            if _should_log_candidate_count(queued_count):
                LOGGER.debug(
                    "X-Sense WebRTC signal relay queued HA ICE candidate: %s",
                    self._debug_context(
                        queue_reason=_candidate_queue_reason(self),
                        queued_candidate_count=queued_count,
                        **_single_candidate_debug(payload),
                    ),
                )
            return
        await self._send_candidate(payload)

    async def _connect_signal(self) -> None:
        options = self._ticket.signal_connect_options()
        url = options.pop("url", self._ticket.signal_url())
        self._ws = await self._session.ws_connect(url, **options)
        LOGGER.debug(
            "X-Sense WebRTC signal relay connected: %s",
            self._debug_context(connect_host=_safe_host(url)),
        )
        self._read_task = asyncio.create_task(self._read_loop())

    async def _read_loop(self) -> None:
        close_code: int | None = None
        try:
            ws = self._ws
            assert ws is not None
            async for message in ws:
                if message.type not in (
                    aiohttp.WSMsgType.TEXT,
                    aiohttp.WSMsgType.BINARY,
                ):
                    continue
                raw = message.data
                event, payload = parse_signal_message(raw)
                if event:
                    self._last_signal_event = event
                    self._signal_event_counts[event] += 1
                if self._should_log_signal_event(event):
                    LOGGER.debug(
                        "X-Sense WebRTC signal relay event received: %s",
                        self._debug_context(
                            event=event, payload=_payload_debug(payload)
                        ),
                    )
                await self._handle_signal_event(event, payload)
            close_code = ws.close_code
        except Exception as err:
            if not self._answer.done():
                self._answer.set_exception(err)
            LOGGER.debug(
                "X-Sense WebRTC signal relay read failed: %s",
                self._debug_context(error=_exception_debug(err)),
            )
        finally:
            LOGGER.debug(
                "X-Sense WebRTC signal relay websocket closed: %s",
                self._debug_context(signal_close_code=close_code),
            )
            self._schedule_signal_reconnect(close_code)

    def _schedule_signal_reconnect(
        self, close_code: int | None, reason: str = "signal_closed_before_answer"
    ) -> None:
        if self._closed or self._answer.done():
            return
        if close_code in _SIGNAL_TERMINAL_CLOSE_CODES:
            return
        if self._reconnect_task is not None and not self._reconnect_task.done():
            return
        LOGGER.debug(
            "X-Sense WebRTC signal relay scheduling reconnect: %s",
            self._debug_context(
                signal_close_code=close_code,
                reconnect_delay_s=_SIGNAL_RECONNECT_DELAY,
                reconnect_reason=reason,
            ),
        )
        self._reconnect_task = asyncio.create_task(self._reconnect_signal(reason))

    async def _reconnect_signal(self, reason: str) -> None:
        await asyncio.sleep(_SIGNAL_RECONNECT_DELAY)
        if self._closed or self._answer.done():
            return
        self._reset_offer_attempt("signal_reconnect")
        self._camera_peer_ready = False
        with suppress(Exception):
            await self.close_signal_only()
        self._signal_reconnect_count += 1
        LOGGER.debug(
            "X-Sense WebRTC signal relay reconnecting signal socket: %s",
            self._debug_context(reconnect_reason=reason),
        )
        try:
            await self._connect_signal()
        except Exception as err:
            LOGGER.debug(
                "X-Sense WebRTC signal relay reconnect failed: %s",
                self._debug_context(error=_exception_debug(err)),
            )
            if not self._answer.done():
                self._answer.set_exception(err)

    async def close_signal_only(self) -> None:
        """Close only the current signal websocket before reconnecting."""
        ws = self._ws
        self._ws = None
        if ws is not None and not ws.closed:
            await ws.close()

    async def _handle_signal_event(self, event: str | None, payload: Any) -> None:
        if self._closed:
            return
        if event == "PEER_IN":
            if _is_owned_peer_message(payload, self._ticket.serial_number):
                self._recipient_client_id = (
                    _matching_peer_id(payload, self._ticket.serial_number)
                    or self._ticket.serial_number
                )
                should_log_peer = (
                    not self._camera_peer_ready
                    or not self._offer_sent
                    or self._should_log_signal_event(event)
                )
                self._camera_peer_ready = True
                if should_log_peer:
                    LOGGER.debug(
                        "X-Sense WebRTC signal relay matched camera peer: %s",
                        self._debug_context(
                            event=event,
                            **_peer_event_debug(payload, self._ticket.serial_number),
                        ),
                    )
                await self._send_offer()
            else:
                LOGGER.debug(
                    "X-Sense WebRTC signal relay ignored peer in for other client: %s",
                    self._debug_context(
                        event=event,
                        **_peer_event_debug(payload, self._ticket.serial_number),
                    ),
                )
            return
        if event == "PEER_OUT":
            if _is_owned_peer_message(payload, self._ticket.serial_number):
                self._camera_peer_ready = False
                if not _future_has_result(self._answer):
                    self._reset_offer_attempt("peer_out_before_answer")
                    self._schedule_signal_reconnect(
                        None, reason="peer_out_before_answer"
                    )
                    LOGGER.debug(
                        "X-Sense WebRTC signal relay reset offer after peer out before answer: %s",
                        self._debug_context(
                            event=event,
                            **_peer_event_debug(payload, self._ticket.serial_number),
                        ),
                    )
            else:
                LOGGER.debug(
                    "X-Sense WebRTC signal relay ignored peer out for other client: %s",
                    self._debug_context(
                        event=event,
                        **_peer_event_debug(payload, self._ticket.serial_number),
                    ),
                )
            return
        if event == "SDP_ANSWER":
            answer = _owned_answer_sdp(payload, self._ticket)
            if answer:
                answer, normalize_context = _normalize_answer_sdp(
                    answer, self._offer_sdp
                )
                LOGGER.debug(
                    "X-Sense WebRTC signal relay received SDP answer: %s",
                    self._debug_context(
                        answer_sdp=_sdp_debug(answer),
                        answer_normalization=normalize_context,
                    ),
                )
                if not self._answer.done():
                    self._answer.set_result(answer)
            else:
                LOGGER.debug(
                    "X-Sense WebRTC signal relay ignored SDP answer: %s",
                    self._debug_context(
                        payload=_payload_debug(payload),
                        reason=_answer_reject_reason(payload, self._ticket),
                    ),
                )
            return
        if event == "ICE_CANDIDATE":
            candidate = _remote_candidate_init_payload(payload)
            if candidate is None:
                LOGGER.debug(
                    "X-Sense WebRTC signal relay ignored invalid remote ICE candidate: %s",
                    self._debug_context(payload=_payload_debug(payload)),
                )
                return
            if self._forward_client_candidates:
                self._forward_remote_candidate(candidate)
            else:
                self._pending_client_candidates.append(candidate)
                LOGGER.debug(
                    "X-Sense WebRTC signal relay queued remote ICE candidate for HA: %s",
                    self._debug_context(),
                )

    def _forward_remote_candidate(self, candidate: dict[str, Any]) -> None:
        if self._remote_candidate_callback is None:
            LOGGER.debug(
                "X-Sense WebRTC signal relay dropped remote ICE candidate without HA callback: %s",
                self._debug_context(**_single_candidate_debug(candidate)),
            )
            return
        LOGGER.debug(
            "X-Sense WebRTC signal relay forwarding remote ICE candidate to HA: %s",
            self._debug_context(**_single_candidate_debug(candidate)),
        )
        self._remote_candidate_callback(candidate)

    async def _send_offer(self) -> None:
        if self._closed or self._offer_sent or self._ws is None or self._ws.closed:
            LOGGER.debug(
                "X-Sense WebRTC signal relay skipped SDP offer send: %s",
                self._debug_context(skip_reason=_offer_skip_reason(self)),
            )
            return
        self._offer_attempt_count += 1
        offer = make_sdp_offer_payload(
            offer_sdp=self._offer_sdp,
            ticket=self._ticket,
            recipient_client_id=self._recipient_client_id,
            session_id=self._session_id,
            resolution=self._resolution,
        )
        relay_offer_sdp, relay_offer_context = _relay_offer_sdp(self._offer_sdp)
        LOGGER.debug(
            "X-Sense WebRTC signal relay sending SDP offer: %s",
            self._debug_context(
                offer_sdp=_sdp_debug(self._offer_sdp),
                relay_offer_sdp=_sdp_debug(relay_offer_sdp),
                relay_offer_normalization=relay_offer_context,
                offer_envelope=_signal_envelope_debug(offer),
            ),
        )
        await self._ws.send_str(offer)
        self._offer_sent = True

        candidates = _local_sdp_candidates(self._offer_sdp)
        self._local_candidate_count = len(candidates)
        LOGGER.debug(
            "X-Sense WebRTC signal relay sending local ICE candidates: %s",
            self._debug_context(**_candidate_debug_summary(candidates)),
        )
        for candidate in candidates:
            await self._send_candidate(candidate)
        if self._offer_attempt_count > 1 and self._ha_candidate_history:
            LOGGER.debug(
                "X-Sense WebRTC signal relay replaying HA ICE candidates after offer retry: %s",
                self._debug_context(
                    replay_candidate_count=len(self._ha_candidate_history)
                ),
            )
            self._pending_remote_candidates.clear()
            for candidate in self._ha_candidate_history:
                await self._send_candidate(candidate)
        await self._flush_pending_remote_candidates()

    async def _flush_pending_remote_candidates(self) -> None:
        """Send any HA candidates that arrived before the X-Sense offer was sent."""
        if self._pending_remote_candidates:
            LOGGER.debug(
                "X-Sense WebRTC signal relay flushing queued HA ICE candidates: %s",
                self._debug_context(
                    **_candidate_debug_summary(self._pending_remote_candidates)
                ),
            )
        while self._pending_remote_candidates and not self._closed:
            await self._send_candidate(self._pending_remote_candidates.pop(0))

    async def _send_candidate(self, candidate: dict[str, Any]) -> None:
        if self._ws is None or self._ws.closed:
            return
        await self._ws.send_str(
            make_ice_candidate_payload(
                candidate=candidate["candidate"],
                sdp_mid=candidate.get("sdpMid"),
                sdp_m_line_index=candidate["sdpMLineIndex"],
                ticket=self._ticket,
                recipient_client_id=self._recipient_client_id,
                session_id=self._session_id,
            )
        )
        self._sent_candidate_count += 1
        if _should_log_candidate_count(self._sent_candidate_count):
            LOGGER.debug(
                "X-Sense WebRTC signal relay sent HA ICE candidate to X-Sense: %s",
                self._debug_context(**_single_candidate_debug(candidate)),
            )

    def _reset_offer_attempt(self, reason: str) -> None:
        self._offer_sent = False
        self._local_candidate_count = 0
        self._sent_candidate_count = 0
        LOGGER.debug(
            "X-Sense WebRTC signal relay offer attempt reset: %s",
            self._debug_context(reset_reason=reason),
        )

    def _should_log_signal_event(self, event: str | None) -> bool:
        """Return whether this signal event should emit a debug line."""
        if event in {"SDP_ANSWER", "ICE_CANDIDATE"}:
            return True
        if event not in {"PEER_IN", "PEER_OUT"}:
            return True
        count = self._signal_event_counts.get(event, 0)
        return count <= 3 or count in {5, 10, 25, 50, 100}


def make_sdp_offer_payload(
    *,
    offer_sdp: str,
    ticket: XSenseWebRTCTicket,
    recipient_client_id: str,
    session_id: str,
    resolution: str | None,
) -> str:
    """Return the APK-compatible SDP offer envelope."""
    relay_sdp = _relay_offer_sdp(offer_sdp)[0]
    payload = _b64_json({"type": "offer", "sdp": relay_sdp})
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
                payload = json.loads(_base64_decode_required_text(payload))
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
    return payload


def _decode_signal_peer_payload(payload: str) -> Any:
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


def _answer_sdp(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    encoded = payload.get("messagePayload")
    if not isinstance(encoded, str):
        return None
    with suppress(Exception):
        decoded = json.loads(_base64_decode_required_text(encoded))
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
    if sender != ticket.serial_number:
        return None
    if recipient != ticket.client_id:
        return None
    return _answer_sdp(payload)


def _answer_reject_reason(payload: Any, ticket: XSenseWebRTCTicket) -> str:
    if not isinstance(payload, dict):
        return "payload_not_dict"
    sender = payload.get("senderClientId")
    recipient = payload.get("recipientClientId")
    if sender != ticket.serial_number:
        return "sender_mismatch"
    if recipient != ticket.client_id:
        return "recipient_mismatch"
    encoded = payload.get("messagePayload")
    if not isinstance(encoded, str):
        return "missing_message_payload"
    with suppress(Exception):
        decoded = json.loads(_base64_decode_required_text(encoded))
        if isinstance(decoded.get("sdp"), str):
            return "accepted"
    return "invalid_sdp_payload"


def _is_owned_peer_message(payload: Any, serial_number: str) -> bool:
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


def _candidate_init_payload(candidate: Any) -> dict[str, Any] | None:
    value = getattr(candidate, "candidate", None)
    if not isinstance(value, str) or not value:
        return None
    return {
        "sdpMid": getattr(candidate, "sdp_mid", None),
        "sdpMLineIndex": int(getattr(candidate, "sdp_m_line_index", 0) or 0),
        "candidate": value,
    }


def _remote_candidate_init_payload(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get("candidate")
    if not isinstance(value, str) or not value:
        return None
    sdp_m_line_index = payload.get("sdpMLineIndex")
    if sdp_m_line_index is None:
        sdp_m_line_index = payload.get("sdp_m_line_index")
    return {
        "sdpMid": payload.get("sdpMid") or payload.get("sdp_mid"),
        "sdpMLineIndex": int(sdp_m_line_index or 0),
        "candidate": value,
    }


def _is_apk_supported_local_candidate(candidate: str) -> bool:
    parts = candidate.split()
    protocol = parts[2].lower() if len(parts) > 2 else ""
    return protocol != "tcp" and "127.0.0.1" not in candidate and "::1" not in candidate


def _sdp_without_local_candidates(sdp: str) -> str:
    lines = [
        line
        for line in sdp.splitlines()
        if not line.startswith("a=candidate:")
        and not line.startswith("a=end-of-candidates")
    ]
    ending = "\r\n" if "\r\n" in sdp else "\n"
    return ending.join(lines) + (ending if sdp.endswith(("\r\n", "\n")) else "")


def _relay_offer_sdp(sdp: str) -> tuple[str, dict[str, Any]]:
    """Return an X-Sense camera friendly SDP offer without changing media transport."""
    sdp = _sdp_without_local_candidates(sdp)
    sections = _sdp_sections(sdp)
    if not sections:
        return sdp, {"sections": 0}

    normalized_sections: list[list[str]] = [sections[0]]
    context: dict[str, Any] = {
        "sections": len(sections),
        "audio_removed_payloads": 0,
        "video_removed_payloads": 0,
        "audio_kept_payloads": 0,
        "video_kept_payloads": 0,
    }
    for section in sections[1:]:
        normalized, section_context = _normalize_offer_media_section(section)
        normalized_sections.append(normalized)
        kind = section_context.get("kind")
        if kind in {"audio", "video"}:
            context[f"{kind}_removed_payloads"] += section_context[
                "removed_payloads"
            ]
            context[f"{kind}_kept_payloads"] += section_context["kept_payloads"]
    return "".join(line for section in normalized_sections for line in section), context


def _sdp_sections(sdp: str) -> list[list[str]]:
    sections: list[list[str]] = [[]]
    for line in sdp.splitlines(keepends=True):
        if line.startswith("m="):
            sections.append([line])
        else:
            sections[-1].append(line)
    return [section for section in sections if section]


def _normalize_offer_media_section(
    section: list[str],
) -> tuple[list[str], dict[str, Any]]:
    if not section or not section[0].startswith("m="):
        return section, {"kind": None, "removed_payloads": 0, "kept_payloads": 0}
    media_line = section[0].rstrip("\r\n")
    parts = media_line.split()
    if len(parts) < 4:
        return section, {"kind": None, "removed_payloads": 0, "kept_payloads": 0}
    kind = parts[0].removeprefix("m=")
    payloads = parts[3:]
    if kind == "application":
        return section, {"kind": kind, "removed_payloads": 0, "kept_payloads": 0}
    if kind not in {"audio", "video"}:
        return section, {
            "kind": kind,
            "removed_payloads": 0,
            "kept_payloads": len(payloads),
        }

    codec_by_payload = _payload_codecs(section)
    allowed_payloads = [
        payload
        for payload in payloads
        if _offer_payload_allowed(kind, payload, codec_by_payload)
    ]
    if not allowed_payloads:
        return section, {
            "kind": kind,
            "removed_payloads": 0,
            "kept_payloads": len(payloads),
        }

    allowed = set(allowed_payloads)
    normalized = [_replace_media_payloads(section[0], allowed_payloads)]
    for line in section[1:]:
        attribute_payload = _offer_attribute_payload(line)
        if attribute_payload in (None, "*") or attribute_payload in allowed:
            normalized.append(line)
    return normalized, {
        "kind": kind,
        "removed_payloads": len(payloads) - len(allowed_payloads),
        "kept_payloads": len(allowed_payloads),
    }


def _media_section_kind(section: list[str]) -> str | None:
    if not section or not section[0].startswith("m="):
        return None
    return section[0].split(maxsplit=1)[0].removeprefix("m=")


def _payload_codecs(section: list[str]) -> dict[str, str]:
    codecs: dict[str, str] = {}
    for line in section:
        if not line.startswith("a=rtpmap:"):
            continue
        value = line.removeprefix("a=rtpmap:").strip()
        payload, _, codec = value.partition(" ")
        codec_name = codec.split("/", 1)[0].upper()
        if payload and codec_name:
            codecs[payload] = codec_name
    return codecs


def _offer_payload_allowed(
    kind: str, payload: str, codec_by_payload: dict[str, str]
) -> bool:
    codec = codec_by_payload.get(payload)
    if kind == "audio":
        return payload == "0" or codec == "PCMU"
    if kind == "video":
        return codec == "H264"
    return True


def _replace_media_payloads(line: str, payloads: list[str]) -> str:
    ending = _line_ending(line)
    parts = line.rstrip("\r\n").split()
    return " ".join([*parts[:3], *payloads]) + ending


def _line_ending(line: str) -> str:
    return "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""


def _offer_attribute_payload(line: str) -> str | None:
    for prefix in ("a=rtpmap:", "a=fmtp:", "a=rtcp-fb:"):
        if not line.startswith(prefix):
            continue
        value = line.removeprefix(prefix).strip()
        payload = value.split(maxsplit=1)[0]
        return payload.split(":", 1)[0]
    return None


def _sdp_debug(sdp: str | None) -> dict[str, Any]:
    if not isinstance(sdp, str):
        return {"type": type(sdp).__name__}
    lines = sdp.splitlines()
    return {
        "sdp_len": len(sdp),
        "media": [
            line.removeprefix("m=")
            for line in lines
            if line.startswith("m=")
        ],
        "mids": [
            line.removeprefix("a=mid:")
            for line in lines
            if line.startswith("a=mid:")
        ],
        "groups": [
            line.removeprefix("a=group:")
            for line in lines
            if line.startswith("a=group:")
        ],
        "setup": [
            line.removeprefix("a=setup:")
            for line in lines
            if line.startswith("a=setup:")
        ],
        "directions": [
            line.removeprefix("a=")
            for line in lines
            if line in {"a=sendrecv", "a=sendonly", "a=recvonly", "a=inactive"}
        ],
        "ice_ufrag_count": sum(1 for line in lines if line.startswith("a=ice-ufrag:")),
        "ice_pwd_count": sum(1 for line in lines if line.startswith("a=ice-pwd:")),
        "fingerprint_count": sum(
            1 for line in lines if line.startswith("a=fingerprint:")
        ),
        "rtcp_mux_count": sum(1 for line in lines if line == "a=rtcp-mux"),
        "candidate_lines": sum(
            1 for line in lines if line.startswith("a=candidate:")
        ),
    }


def _normalize_answer_sdp(
    sdp: str, offer_sdp: str | None = None
) -> tuple[str, dict[str, Any]]:
    """Normalize browser-rejected SDP answer attributes without changing media."""
    setup_actpass_replaced = 0
    sendrecv_replaced = 0
    recvonly_offer_mids = _offer_recvonly_media_mids(offer_sdp)
    normalized_sections: list[list[str]] = []
    for section in _sdp_sections(sdp):
        normalized_section: list[str] = []
        media_kind = _media_section_kind(section)
        mid = _media_section_mid(section)
        for line in section:
            stripped = line.rstrip("\r\n")
            ending = _line_ending(line)
            if stripped == "a=setup:actpass":
                normalized_section.append(f"a=setup:passive{ending}")
                setup_actpass_replaced += 1
            elif (
                media_kind in {"audio", "video"}
                and stripped == "a=sendrecv"
                and (
                    (recvonly_offer_mids is None)
                    or (mid is not None and mid in recvonly_offer_mids)
                )
            ):
                normalized_section.append(f"a=sendonly{ending}")
                sendrecv_replaced += 1
            else:
                normalized_section.append(line)
        normalized_sections.append(normalized_section)
    return "".join(line for section in normalized_sections for line in section), {
        "setup_actpass_replaced": setup_actpass_replaced,
        "sendrecv_replaced": sendrecv_replaced,
    }


def _offer_recvonly_media_mids(sdp: str | None) -> set[str] | None:
    if sdp is None:
        return None
    mids: set[str] = set()
    for section in _sdp_sections(sdp):
        if _media_section_kind(section) not in {"audio", "video"}:
            continue
        if _media_section_direction(section) != "recvonly":
            continue
        mid = _media_section_mid(section)
        if mid is not None:
            mids.add(mid)
    return mids


def _media_section_mid(section: list[str]) -> str | None:
    for line in section:
        if line.startswith("a=mid:"):
            return line.removeprefix("a=mid:").strip()
    return None


def _media_section_direction(section: list[str]) -> str | None:
    for line in section:
        stripped = line.rstrip("\r\n")
        if stripped in {"a=sendrecv", "a=sendonly", "a=recvonly", "a=inactive"}:
            return stripped.removeprefix("a=")
    return None


def _candidate_debug_summary(candidates: list[dict[str, Any]]) -> dict[str, Any]:
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


def _single_candidate_debug(candidate: dict[str, Any]) -> dict[str, Any]:
    return _candidate_debug_summary([candidate])


def _should_log_candidate_count(count: int) -> bool:
    """Return whether this candidate count should get an individual debug line."""
    return count <= 1 or count in {5, 10, 25, 50, 100}


def _candidate_queue_reason(session: XSenseWebRTCSignalSession) -> str:
    if session._ws is None:
        return "signal_not_connected"
    if session._ws.closed:
        return "signal_closed"
    if not session._offer_sent:
        return "waiting_for_peer_offer"
    return "unknown"


def _offer_skip_reason(session: XSenseWebRTCSignalSession) -> str:
    if session._closed:
        return "session_closed"
    if session._offer_sent:
        return "offer_already_sent"
    if session._ws is None:
        return "signal_not_connected"
    if session._ws.closed:
        return "signal_closed"
    return "unknown"


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
    if not isinstance(payload, dict):
        return {}
    return {
        key: _short_id(payload.get(key))
        for key in ("group", "role", "id", "name", "clientId", "serialNumber")
        if payload.get(key) not in (None, "")
    }


def _signal_envelope_debug(payload: str) -> dict[str, Any]:
    with suppress(Exception):
        data = json.loads(payload)
        if isinstance(data, dict):
            return {
                "keys": sorted(str(key) for key in data.keys()),
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


def _ticket_debug_context(ticket: XSenseWebRTCTicket) -> dict[str, Any]:
    return {
        "camera": _short_id(ticket.serial_number),
        "client": _short_id(ticket.client_id),
        "role": ticket.role,
        "signal_host": _safe_host(ticket.signal_server),
        "signal_ip_override": bool(ticket.signal_server_ip_address),
        "ice_servers": len(ticket.ice_servers or []),
        "signal_ping_interval": ticket.signal_ping_interval,
        "ticket_expires_in_s": (
            round((ticket.expiration_time - int(time.time() * 1000)) / 1000)
            if ticket.expiration_time is not None
            else None
        ),
    }


def _future_has_result(future: asyncio.Future[Any]) -> bool:
    if not future.done() or future.cancelled():
        return False
    with suppress(asyncio.CancelledError, Exception):
        return future.exception() is None
    return False


def _exception_debug(err: BaseException) -> dict[str, Any]:
    text = str(err)
    return {
        "type": type(err).__name__,
        "message_len": len(text),
        "has_message": bool(text),
    }


def _payload_debug(payload: Any) -> str:
    if isinstance(payload, dict):
        keys = sorted(str(key) for key in payload.keys())
        return f"dict_keys={keys}"
    if isinstance(payload, str):
        return f"str:{_short_id(payload)}"
    return type(payload).__name__


def _base64_decode_required_text(value: str) -> str:
    missing_padding = (-len(value)) % 4
    return base64.b64decode(value + ("=" * missing_padding), validate=False).decode()


def _base64_decode_text(value: str) -> str | None:
    with suppress(Exception):
        decoded = _base64_decode_required_text(value)
        if decoded:
            return decoded
    return None


def _b64_json(data: dict[str, Any]) -> str:
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.b64encode(raw).decode()


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
