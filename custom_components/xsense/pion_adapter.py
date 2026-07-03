"""Pion-based SD recording capture for X-Sense cameras."""

from __future__ import annotations

import asyncio
import json
import os
import platform
from contextlib import suppress
from importlib import import_module
from pathlib import Path
from time import monotonic
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, LOGGER
from .webrtc_signal import make_start_sd_playback_command_payload

HELPER_TIMEOUT = 45
FFMPEG_TIMEOUT = 60


async def async_capture_sd_recording(
    hass: HomeAssistant,
    *,
    coordinator: Any,
    camera: Any,
    start_time: int,
    output_path: Path,
    duration_seconds: int | None = None,
) -> Path:
    """Capture one SD-card playback session to MP4 without video transcoding."""
    lock = _recording_capture_lock(hass, output_path)
    async with lock:
        if _mp4_ready(output_path):
            return output_path
        return await _async_capture_sd_recording_unlocked(
            hass,
            coordinator=coordinator,
            camera=camera,
            start_time=start_time,
            output_path=output_path,
            duration_seconds=duration_seconds,
        )


async def _async_capture_sd_recording_unlocked(
    hass: HomeAssistant,
    *,
    coordinator: Any,
    camera: Any,
    start_time: int,
    output_path: Path,
    duration_seconds: int | None = None,
) -> Path:
    """Capture one SD-card playback session while holding the recording lock."""
    helper_path = _pion_helper_path()
    if helper_path is None:
        raise RuntimeError("X-Sense Pion adapter binary is missing")
    ffmpeg_binary = _ffmpeg_binary(hass)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    h264_path = output_path.with_name(f"{output_path.name}.h264")
    temp_output_path = output_path.with_suffix(".tmp.mp4")
    h264_path.unlink(missing_ok=True)
    temp_output_path.unlink(missing_ok=True)
    output_path.unlink(missing_ok=True)
    capture_started_at = monotonic()

    ticket_data = await coordinator.xsense.get_camera_webrtc_ticket(
        camera, force_refresh=True
    )
    if not isinstance(ticket_data, dict):
        raise RuntimeError("X-Sense did not return a WebRTC ticket")

    webrtc_signal = await hass.async_add_import_executor_job(
        import_module, f"{DOMAIN}.webrtc_signal"
    )
    ticket = webrtc_signal.XSenseWebRTCTicket.from_api(camera.sn, ticket_data)

    helper_timeout = _capture_timeout(duration_seconds)
    LOGGER.debug(
        "X-Sense Pion SD recording capture starting: %s",
        {
            "camera": _short_id(getattr(camera, "sn", "")),
            "start_time": int(start_time),
            "duration": duration_seconds,
            "timeout": helper_timeout,
            "helper": helper_path.name,
        },
    )
    proc = await _start_helper(helper_path, h264_path, start_time, ticket, helper_timeout)
    candidate_tasks: set[asyncio.Task] = set()

    async def _send_helper_command(command: dict[str, Any]) -> None:
        if proc.stdin is None or proc.stdin.is_closing():
            return
        proc.stdin.write(json.dumps(command, separators=(",", ":")).encode() + b"\n")
        await proc.stdin.drain()

    def _remote_candidate_callback(candidate: dict[str, Any]) -> None:
        task = hass.async_create_task(
            _send_helper_command(
                {
                    "type": "candidate",
                    "candidate": candidate.get("candidate") or "",
                    "sdpMid": candidate.get("sdpMid") or "0",
                    "sdpMLineIndex": int(candidate.get("sdpMLineIndex") or 0),
                }
            )
        )
        candidate_tasks.add(task)
        task.add_done_callback(candidate_tasks.discard)

    signal_session = None
    try:
        offer_sdp = await _read_helper_offer(proc)
        signal_session = webrtc_signal.XSenseWebRTCSignalSession(
            session=async_get_clientsession(hass),
            ticket=ticket,
            offer_sdp=offer_sdp,
            resolution=_camera_resolution(camera),
            camera_online=bool(getattr(camera, "online", False)),
            remote_candidate_callback=_remote_candidate_callback,
        )
        answer_sdp = await signal_session.start()
        await _send_helper_command({"type": "answer", "sdp": answer_sdp})
        signal_session.start_forwarding_remote_candidates()
        result = await _wait_for_helper(proc, helper_timeout)
        helper_finished_at = monotonic()
        if int(result.get("h264Samples") or 0) <= 0 or not h264_path.exists():
            raise RuntimeError(f"X-Sense Pion adapter did not receive video: {result}")
        await _remux_h264_to_mp4(ffmpeg_binary, h264_path, output_path)
        mp4_finished_at = monotonic()
        if not _mp4_ready(output_path):
            raise RuntimeError("X-Sense Pion adapter did not create a playable MP4")
        LOGGER.debug(
            "X-Sense Pion SD recording captured: %s",
            {
                "camera": _short_id(getattr(camera, "sn", "")),
                "start_time": int(start_time),
                "packets": result.get("packets"),
                "bytes": result.get("bytes"),
                "h264_samples": result.get("h264Samples"),
                "h264_bytes": result.get("h264Bytes"),
                "output_bytes": output_path.stat().st_size,
                "helper_elapsed_ms": int(
                    (helper_finished_at - capture_started_at) * 1000
                ),
                "mp4_elapsed_ms": int(
                    (mp4_finished_at - helper_finished_at) * 1000
                ),
                "total_elapsed_ms": int((mp4_finished_at - capture_started_at) * 1000),
            },
        )
        return output_path
    finally:
        if signal_session is not None:
            await signal_session.close()
        for task in list(candidate_tasks):
            task.cancel()
        if proc.returncode is None:
            proc.terminate()
            with suppress(Exception):
                await asyncio.wait_for(proc.wait(), timeout=5)
            if proc.returncode is None:
                proc.kill()
        h264_path.unlink(missing_ok=True)
        temp_output_path.unlink(missing_ok=True)


def _recording_capture_lock(hass: HomeAssistant, output_path: Path) -> asyncio.Lock:
    """Return a per-output lock for SD recording capture."""
    locks = hass.data.setdefault(DOMAIN, {}).setdefault("_recording_capture_locks", {})
    key = str(output_path)
    lock = locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        locks[key] = lock
    return lock


async def _start_helper(
    helper_path: Path,
    h264_path: Path,
    start_time: int,
    ticket: Any | None = None,
    timeout_seconds: int = HELPER_TIMEOUT,
) -> asyncio.subprocess.Process:
    env = os.environ.copy()
    env.update(
        {
            "XSENSE_RECORDINGS_DATA_CHANNEL": "1",
            "XSENSE_RECORDINGS_DATA_CHANNEL_LABEL": "data-channel-of-",
            "XSENSE_RECORDINGS_DATA_CHANNEL_START_PAYLOAD": make_start_sd_playback_command_payload(
                int(start_time)
            ),
            "XSENSE_RECORDINGS_DISABLE_MDNS": "1",
            "XSENSE_RECORDINGS_H264_OUTPUT": str(h264_path),
            "XSENSE_RECORDINGS_REMOTE_SDP_TYPE": "answer",
            "XSENSE_RECORDINGS_CHROME_SDP": "1",
        }
    )
    if ice_servers := _ice_servers_env(ticket):
        env["XSENSE_RECORDINGS_ICE_SERVERS"] = ice_servers
    return await asyncio.create_subprocess_exec(
        str(helper_path),
        "--interactive",
        "--timeout",
        f"{int(timeout_seconds)}s",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )


def _capture_timeout(duration_seconds: int | None) -> int:
    """Return a bounded helper timeout for one recording clip."""
    if duration_seconds is None:
        return HELPER_TIMEOUT
    try:
        duration = int(duration_seconds)
    except (TypeError, ValueError):
        return HELPER_TIMEOUT
    if duration <= 0:
        return HELPER_TIMEOUT
    return max(HELPER_TIMEOUT, min(duration + 10, 180))


def _ice_servers_env(ticket: Any | None) -> str:
    """Return Pion-compatible ICE server JSON from an X-Sense ticket."""
    servers = getattr(ticket, "ice_servers", None) or []
    normalized: list[dict[str, Any]] = []
    for server in servers:
        if not isinstance(server, dict):
            continue
        urls = server.get("urls") or server.get("url")
        if not urls:
            continue
        item: dict[str, Any] = {"urls": urls}
        if username := server.get("username"):
            item["username"] = username
        if credential := server.get("credential") or server.get("password"):
            item["credential"] = credential
        normalized.append(item)
    return json.dumps(normalized, separators=(",", ":")) if normalized else ""


async def _read_helper_offer(proc: asyncio.subprocess.Process) -> str:
    assert proc.stdout is not None
    deadline = asyncio.get_running_loop().time() + 20
    while asyncio.get_running_loop().time() < deadline:
        line = await asyncio.wait_for(proc.stdout.readline(), timeout=20)
        if not line:
            break
        with suppress(json.JSONDecodeError):
            event = json.loads(line.decode(errors="ignore"))
            if event.get("type") == "offer" and str(event.get("sdp", "")).startswith(
                "v=0"
            ):
                return str(event["sdp"])
    raise RuntimeError("X-Sense Pion adapter did not return a WebRTC offer")


async def _wait_for_helper(
    proc: asyncio.subprocess.Process, timeout_seconds: int = HELPER_TIMEOUT
) -> dict[str, Any]:
    assert proc.stdout is not None
    last_event: dict[str, Any] = {}
    while True:
        line = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout_seconds + 5)
        if not line:
            break
        with suppress(json.JSONDecodeError):
            event = json.loads(line.decode(errors="ignore"))
            last_event = event
            if event.get("type") == "result":
                await proc.wait()
                return event
    stderr = ""
    if proc.stderr is not None:
        with suppress(Exception):
            stderr = (await proc.stderr.read()).decode(errors="ignore").strip()
    raise RuntimeError(
        f"X-Sense Pion adapter exited without a result: {last_event or stderr}"
    )


async def _remux_h264_to_mp4(
    ffmpeg_binary: str, h264_path: Path, output_path: Path
) -> None:
    await _run_ffmpeg(
        [
            ffmpeg_binary,
            "-hide_banner",
            "-loglevel",
            "warning",
            "-fflags",
            "+genpts",
            "-f",
            "h264",
            "-i",
            str(h264_path),
            "-an",
            "-c:v",
            "copy",
            "-movflags",
            "+faststart",
            "-y",
            str(output_path),
        ],
        "remux X-Sense SD recording",
    )


async def _run_ffmpeg(command: list[str], action: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=FFMPEG_TIMEOUT)
    except asyncio.TimeoutError as exc:
        proc.kill()
        raise RuntimeError(f"ffmpeg timed out while trying to {action}") from exc
    if proc.returncode != 0:
        detail = (stderr or stdout).decode(errors="ignore").strip()
        raise RuntimeError(f"ffmpeg failed to {action}: {detail}")


def _pion_helper_path() -> Path | None:
    base = Path(__file__).parent
    system = platform.system().lower()
    machine = _normalized_machine()
    names = [
        f"xsense_pion_adapter_{system}_{machine}",
        "xsense_pion_adapter_windows_amd64.exe" if system == "windows" else "",
        "xsense_pion_adapter.exe" if system == "windows" else "xsense_pion_adapter",
    ]
    for name in names:
        if not name:
            continue
        path = base / "bin" / name
        if path.exists():
            _ensure_executable(path)
            return path
    return None


def _ffmpeg_binary(hass: HomeAssistant) -> str:
    data_ffmpeg = "ffmpeg"
    with suppress(Exception):
        ffmpeg_component = import_module("homeassistant.components.ffmpeg")
        data_ffmpeg = getattr(ffmpeg_component, "DATA_FFMPEG", data_ffmpeg)
    ffmpeg = hass.data.get(data_ffmpeg)
    binary = getattr(ffmpeg, "binary", None)
    if binary:
        return str(binary)
    return "ffmpeg"


def _normalized_machine() -> str:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        return "amd64"
    if machine in {"aarch64", "arm64"}:
        return "arm64"
    if machine.startswith("armv7") or machine.startswith("armv6") or machine == "arm":
        return "arm"
    return machine


def _ensure_executable(path: Path) -> None:
    if platform.system().lower() == "windows":
        return
    with suppress(OSError):
        path.chmod(path.stat().st_mode | 0o111)


def _camera_resolution(camera: Any) -> str | None:
    data = getattr(camera, "data", {}) or {}
    for key in ("liveResolution", "videoResolution", "resolution"):
        value = data.get(key)
        if value:
            return str(value)
    return None


def _mp4_ready(path: Path) -> bool:
    if not path.exists() or path.stat().st_size <= 16:
        return False
    with path.open("rb") as file:
        head = file.read(32)
    return b"ftyp" in head


def _short_id(value: Any) -> str:
    text = str(value or "")
    if len(text) <= 8:
        return text
    return f"...{text[-6:]}"
