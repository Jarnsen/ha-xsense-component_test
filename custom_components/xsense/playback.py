"""Home Assistant playback page for X-Sense camera recordings."""

from __future__ import annotations

from urllib.parse import quote

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import DOMAIN, LOGGER
from .webrtc_signal import (
    make_start_sd_playback_command_payload,
    make_stop_sd_playback_command_payload,
)

PLAYBACK_VIEW_NAME = "api:xsense:playback"
PLAYBACK_VIEW_URL = "/xsense/playback/{entry_id}/{serial}/{start_time}"


def async_register_playback_view(hass: HomeAssistant) -> None:
    """Register the X-Sense playback view once."""
    if hass.data.setdefault(DOMAIN, {}).get("_playback_view_registered"):
        return
    hass.http.register_view(XSensePlaybackView())
    hass.data[DOMAIN]["_playback_view_registered"] = True


def playback_url(
    entry_id: str,
    serial: str,
    start_time: int,
    camera_entity_id: str,
    base_url: str | None = None,
) -> str:
    """Return a Home Assistant URL for an X-Sense SD playback event."""
    path = (
        f"/xsense/playback/{quote(str(entry_id), safe='')}/"
        f"{quote(str(serial), safe='')}/{int(start_time)}"
        f"?camera_entity_id={quote(camera_entity_id, safe='')}"
    )
    if not base_url:
        return path
    return f"{base_url.rstrip('/')}{path}"


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
