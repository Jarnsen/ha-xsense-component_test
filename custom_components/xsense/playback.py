"""Home Assistant playback page for X-Sense camera recordings."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from aiohttp import web
from homeassistant.components import frontend
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import (
    CONF_RECORDING_MEDIA_STORAGE_PATH,
    DEFAULT_RECORDING_MEDIA_STORAGE_PATH,
    DOMAIN,
    LOGGER,
)
from .api.async_xsense import is_camera_entity
from .pion_adapter import async_capture_sd_recording
from .webrtc_signal import (
    make_start_sd_playback_command_payload,
    make_stop_sd_playback_command_payload,
)

PLAYBACK_VIEW_NAME = "api:xsense:playback"
PLAYBACK_VIEW_URL = "/xsense/playback/{entry_id}/{serial}/{start_time}"
RECORDING_MEDIA_VIEW_NAME = "api:xsense:recording"
RECORDING_MEDIA_VIEW_URL = "/xsense/recording/{entry_id}/{start_time}"
PLAYBACK_PANEL_PATH = "xsense-playback"
PLAYBACK_STATIC_PATH = "/xsense_static"
PLAYBACK_PANEL_MODULE = f"{PLAYBACK_STATIC_PATH}/xsense-playback-panel.js"


async def async_register_playback_view(hass: HomeAssistant) -> None:
    """Register the X-Sense playback routes once."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if not domain_data.get("_playback_static_registered"):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    PLAYBACK_STATIC_PATH,
                    str(Path(__file__).parent / "frontend"),
                    cache_headers=False,
                )
            ]
        )
        domain_data["_playback_static_registered"] = True

    if not domain_data.get("_playback_panel_registered"):
        frontend.async_register_built_in_panel(
            hass,
            component_name="custom",
            frontend_url_path=PLAYBACK_PANEL_PATH,
            config={
                "_panel_custom": {
                    "name": "xsense-playback-panel",
                    "embed_iframe": False,
                    "trust_external": False,
                    "module_url": PLAYBACK_PANEL_MODULE,
                }
            },
            require_admin=False,
            show_in_sidebar=False,
        )
        domain_data["_playback_panel_registered"] = True

    if not (
        domain_data.get("_playback_legacy_view_registered")
        or domain_data.get("_playback_view_registered")
    ):
        hass.http.register_view(XSensePlaybackView())
        domain_data["_playback_legacy_view_registered"] = True
    if not domain_data.get("_recording_media_view_registered"):
        hass.http.register_view(XSenseRecordingMediaView())
        domain_data["_recording_media_view_registered"] = True


def playback_url(
    entry_id: str,
    serial: str,
    start_time: int,
    camera_entity_id: str,
    base_url: str | None = None,
    end_time: int | None = None,
) -> str:
    """Return a Home Assistant URL for an X-Sense SD playback event."""
    return playback_panel_url(
        entry_id,
        serial,
        start_time,
        camera_entity_id,
        base_url=base_url,
        mode="recording",
        end_time=end_time,
    )


def recording_media_url(
    entry_id: str,
    serial: str,
    start_time: int,
    base_url: str | None = None,
    end_time: int | None = None,
) -> str:
    """Return the backend media route for one X-Sense SD recording."""
    path = (
        f"/xsense/recording"
        f"/{quote(str(entry_id), safe='')}"
        f"/{int(start_time)}"
        f"?serial={quote(str(serial), safe='')}"
    )
    if end_time is not None:
        path = f"{path}&end_time={int(end_time)}"
    if not base_url:
        return path
    return f"{base_url.rstrip('/')}{path}"


def playback_panel_url(
    entry_id: str,
    serial: str,
    start_time: int,
    camera_entity_id: str,
    base_url: str | None = None,
    mode: str = "webrtc",
    end_time: int | None = None,
) -> str:
    """Return the legacy HA-hosted WebRTC playback panel URL."""
    path = (
        f"/{PLAYBACK_PANEL_PATH}"
        f"?mode={quote(str(mode), safe='')}"
        f"&entry_id={quote(str(entry_id), safe='')}"
        f"&serial={quote(str(serial), safe='')}"
        f"&start_time={int(start_time)}"
        f"&camera_entity_id={quote(camera_entity_id, safe='')}"
    )
    if end_time is not None:
        path = f"{path}&end_time={int(end_time)}"
    if not base_url:
        return path
    return f"{base_url.rstrip('/')}{path}"


class XSenseRecordingMediaView(HomeAssistantView):
    """Cache and redirect one X-Sense SD recording to local HA media."""

    url = RECORDING_MEDIA_VIEW_URL
    name = RECORDING_MEDIA_VIEW_NAME
    requires_auth = True

    async def get(
        self, request: web.Request, entry_id: str, start_time: str
    ) -> web.Response:
        """Return a cached MP4 recording."""
        hass: HomeAssistant = request.app["hass"]
        coordinator = hass.data.get(DOMAIN, {}).get(entry_id)
        if coordinator is None or not hasattr(coordinator, "xsense"):
            raise web.HTTPNotFound(text="X-Sense account is not loaded")

        serial = request.query.get("serial", "")
        if not serial:
            raise web.HTTPBadRequest(text="Missing X-Sense camera serial")
        camera = _coordinator_camera_entity(coordinator, serial)
        if camera is None:
            raise web.HTTPNotFound(text="X-Sense camera is not loaded")
        try:
            sd_start_time = int(start_time)
        except ValueError as err:
            raise web.HTTPBadRequest(text="Invalid playback start time") from err

        try:
            end_time = int(request.query.get("end_time") or sd_start_time)
        except ValueError:
            end_time = sd_start_time

        output_path = _recording_cache_path(
            hass, entry_id, serial, sd_start_time, end_time
        )
        if not _path_ready(output_path):
            LOGGER.debug(
                "X-Sense recording media route caching SD clip: %s",
                {
                    "entry_id": entry_id,
                    "camera": _short_id(serial),
                    "start_time": sd_start_time,
                },
            )
            try:
                await async_capture_sd_recording(
                    hass,
                    coordinator=coordinator,
                    camera=camera,
                    start_time=sd_start_time,
                    output_path=output_path,
                    duration_seconds=_recording_duration(sd_start_time, end_time),
                )
            except Exception as exc:  # noqa: BLE001
                LOGGER.debug(
                    "X-Sense recording media route failed to cache SD clip: %s",
                    {
                        "entry_id": entry_id,
                        "camera": _short_id(serial),
                        "start_time": sd_start_time,
                        "error": str(exc),
                    },
                )
                raise web.HTTPInternalServerError(
                    text="Unable to prepare X-Sense recording"
                ) from exc

        local_url = _local_media_url(output_path)
        if not local_url:
            raise web.HTTPInternalServerError(text="Unable to serve X-Sense recording")
        raise web.HTTPFound(local_url)


class XSensePlaybackView(HomeAssistantView):
    """Render a simple HA-hosted WebRTC playback page for one X-Sense recording."""

    url = PLAYBACK_VIEW_URL
    name = PLAYBACK_VIEW_NAME
    requires_auth = True

    async def get(
        self, request: web.Request, entry_id: str, serial: str, start_time: str
    ) -> web.Response:
        """Return the playback page."""
        hass: HomeAssistant = request.app["hass"]
        if entry_id not in hass.data.get(DOMAIN, {}):
            raise web.HTTPNotFound()

        camera_entity_id = request.query.get("camera_entity_id", "")
        if not camera_entity_id.startswith("camera."):
            raise web.HTTPBadRequest(text="Missing camera entity id")
        try:
            sd_start_time = int(start_time)
        except ValueError as err:
            raise web.HTTPBadRequest(text="Invalid playback start time") from err

        LOGGER.debug(
            "X-Sense playback page opened: %s",
            {
                "camera_entity_id": camera_entity_id,
                "serial_present": bool(serial),
                "start_time": sd_start_time,
            },
        )
        start_payload = make_start_sd_playback_command_payload(sd_start_time)
        stop_payload = make_stop_sd_playback_command_payload()
        return web.Response(
            text=_playback_html(camera_entity_id, start_payload, stop_payload),
            content_type="text/html",
        )


def _playback_html(camera_entity_id: str, start_payload: str, stop_payload: str) -> str:
    """Return the browser player page."""
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>X-Sense recording</title>
  <style>
    html, body {{ margin: 0; height: 100%; background: #111; color: #eee; font-family: sans-serif; }}
    main {{ min-height: 100%; display: grid; grid-template-rows: 1fr auto; }}
    video {{ width: 100%; height: 100%; object-fit: contain; background: #000; }}
    #status {{ padding: 12px 14px; font-size: 14px; background: #1f1f1f; }}
  </style>
</head>
<body>
<main>
  <video id="video" autoplay controls playsinline></video>
  <div id="status">Starting X-Sense recording...</div>
</main>
<script>
const cameraEntityId = {camera_entity_id!r};
const startPayload = {start_payload!r};
const stopPayload = {stop_payload!r};
const statusEl = document.getElementById("status");
const videoEl = document.getElementById("video");
let ws;
let pc;
let msgId = 1;
let sessionId;
let dataChannel;
let pendingCandidates = [];

function setStatus(message) {{
  statusEl.textContent = message;
}}

function hassToken() {{
  const raw = localStorage.getItem("hassTokens");
  if (!raw) throw new Error("Home Assistant auth token not found");
  const parsed = JSON.parse(raw);
  return parsed.access_token || parsed.token;
}}

function sendMessage(message) {{
  message.id = msgId++;
  ws.send(JSON.stringify(message));
  return message.id;
}}

function waitForResult(id) {{
  return new Promise((resolve, reject) => {{
    const handler = (event) => {{
      const data = JSON.parse(event.data);
      if (data.id !== id || data.type === "event") return;
      ws.removeEventListener("message", handler);
      if (data.type === "result" && data.success !== false) resolve(data.result);
      else reject(new Error((data.error && data.error.message) || "Home Assistant command failed"));
    }};
    ws.addEventListener("message", handler);
  }});
}}

async function connectWebSocket() {{
  const url = `${{location.protocol === "https:" ? "wss" : "ws"}}://${{location.host}}/api/websocket`;
  ws = new WebSocket(url);
  await new Promise((resolve, reject) => {{
    ws.onmessage = (event) => {{
      const data = JSON.parse(event.data);
      if (data.type === "auth_required") ws.send(JSON.stringify({{type: "auth", access_token: hassToken()}}));
      if (data.type === "auth_ok") resolve();
      if (data.type === "auth_invalid") reject(new Error("Home Assistant auth failed"));
    }};
    ws.onerror = () => reject(new Error("Home Assistant websocket failed"));
  }});
}}

async function startPlayback() {{
  await connectWebSocket();
  const configId = sendMessage({{type: "camera/webrtc/get_client_config", entity_id: cameraEntityId}});
  const clientConfig = await waitForResult(configId);
  pc = new RTCPeerConnection(clientConfig.configuration || {{}});
  pc.ontrack = (event) => {{
    videoEl.srcObject = event.streams[0];
    setStatus("Playing X-Sense recording");
  }};
  pc.onicecandidate = (event) => {{
    if (!event.candidate) return;
    const candidate = event.candidate.toJSON();
    if (!sessionId) {{
      pendingCandidates.push(candidate);
      return;
    }}
    sendMessage({{type: "camera/webrtc/candidate", entity_id: cameraEntityId, session_id: sessionId, candidate}});
  }};
  if (clientConfig.dataChannel) {{
    dataChannel = pc.createDataChannel(clientConfig.dataChannel);
    dataChannel.onopen = () => dataChannel.send(startPayload);
  }}
  pc.addTransceiver("audio", {{direction: "recvonly"}});
  pc.addTransceiver("video", {{direction: "recvonly"}});
  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);
  const offerId = sendMessage({{type: "camera/webrtc/offer", entity_id: cameraEntityId, offer: offer.sdp}});
  ws.addEventListener("message", async (event) => {{
    const data = JSON.parse(event.data);
    if (data.id !== offerId || data.type !== "event") return;
    const payload = data.event;
    if (payload.type === "session") {{
      sessionId = payload.session_id;
      while (pendingCandidates.length) {{
        sendMessage({{type: "camera/webrtc/candidate", entity_id: cameraEntityId, session_id: sessionId, candidate: pendingCandidates.shift()}});
      }}
    }}
    if (payload.type === "answer") await pc.setRemoteDescription({{type: "answer", sdp: payload.answer}});
    if (payload.type === "candidate" && payload.candidate) await pc.addIceCandidate(payload.candidate);
    if (payload.type === "error") setStatus(payload.message || "Unable to start X-Sense recording");
  }});
}}

window.addEventListener("beforeunload", () => {{
  try {{ if (dataChannel && dataChannel.readyState === "open") dataChannel.send(stopPayload); }} catch (err) {{}}
  try {{ if (pc) pc.close(); }} catch (err) {{}}
  try {{ if (ws) ws.close(); }} catch (err) {{}}
}});

startPlayback().catch((err) => setStatus(err.message));
</script>
</body>
</html>"""


def _coordinator_camera_entity(coordinator, serial: str):
    """Return the loaded camera entity for a serial number."""
    data = getattr(coordinator, "data", None)
    if not isinstance(data, dict):
        return None
    for entity in (
        *(data.get("stations") or {}).values(),
        *(data.get("devices") or {}).values(),
    ):
        if str(getattr(entity, "sn", "") or "") == serial and is_camera_entity(entity):
            return entity
    return None


def _recording_cache_path(
    hass: HomeAssistant, entry_id: str, serial: str, start_time: int, end_time: int
) -> Path:
    """Return the recording route cache path for one SD recording."""
    root = _recording_media_root(hass, entry_id)
    return root / "videos" / f"{_safe_segment(serial)}_{int(start_time)}_{int(end_time)}.mp4"


def _recording_media_root(hass: HomeAssistant, entry_id: str) -> Path:
    """Return configured recording media root under /media."""
    entry = hass.config_entries.async_get_entry(entry_id)
    value = None
    if entry is not None:
        value = entry.options.get(
            CONF_RECORDING_MEDIA_STORAGE_PATH,
            entry.data.get(
                CONF_RECORDING_MEDIA_STORAGE_PATH,
                DEFAULT_RECORDING_MEDIA_STORAGE_PATH,
            ),
        )
    root = str(value or DEFAULT_RECORDING_MEDIA_STORAGE_PATH).strip()
    if root != "/media" and not root.startswith("/media/"):
        root = DEFAULT_RECORDING_MEDIA_STORAGE_PATH
    return Path(root)


def _local_media_url(path: Path) -> str:
    """Return the Home Assistant local media URL for a cached recording."""
    try:
        relative = path.resolve().relative_to(Path("/media").resolve())
    except ValueError:
        return ""
    return f"/media/local/{quote(relative.as_posix())}"


def _path_ready(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def _recording_duration(start_time: int, end_time: int) -> int | None:
    duration = int(end_time) - int(start_time)
    return duration if duration > 0 else None


def _safe_segment(value: str) -> str:
    return "".join(
        character if character.isalnum() or character in {"-", "_"} else "_"
        for character in str(value)
    )


def _short_id(value: str) -> str:
    text = str(value or "")
    if len(text) <= 8:
        return text
    return f"...{text[-6:]}"
