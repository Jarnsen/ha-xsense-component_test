"""Wire sequence captured from #182's repeated-switching baseline, 65984b9."""
import base64
import json
from pathlib import Path
from types import SimpleNamespace

from custom_components.xsense.python_xsense import webrtc_signal


async def relay_trace(module, serial):
    class Socket:
        closed = False

        def __init__(self):
            self.messages = []

        async def send_str(self, message):
            self.messages.append(json.loads(message))

        async def close(self):
            self.closed = True

    ws = Socket()
    ticket = module.XSenseWebRTCTicket.from_api(serial, {
        "signalServer": "https://signal.example", "groupId": serial,
        "role": "viewer", "id": "viewer123", "traceId": "trace123",
        "sign": "test-sign", "time": 123456, "expirationTime": 9999999999999,
        "signalServerIpAddress": "192.0.2.10",
    })
    sdp = (
        "v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 0\r\na=mid:0\r\n"
        "a=candidate:1 1 udp 1 192.0.2.1 4000 typ host\r\n"
        "m=video 9 UDP/TLS/RTP/SAVPF 96\r\na=mid:1\r\n"
        "a=rtpmap:96 H264/90000\r\n"
    )
    session = module.XSenseWebRTCSignalSession(
        session=object(), ticket=ticket, offer_sdp=sdp,
        resolution="1920x1080", camera_online=True,
    )
    session._session_id = "baseline-session"
    session._ws = ws
    trace = [{"step": "connect", "url": ticket.signal_url(),
              "options": ticket.signal_connect_options()}]
    offset = 0

    def checkpoint(step):
        nonlocal offset
        trace.append({"step": step, "messages": ws.messages[offset:]})
        offset = len(ws.messages)

    async def event(kind, payload):
        parsed = module.parse_signal_message(json.dumps({
            "messageType": kind, "messagePayload": payload,
        }))
        await session._handle_signal_event(*parsed)

    try:
        await session.add_candidate(SimpleNamespace(
            candidate="candidate:2 1 udp 1 192.0.2.2 4001 typ host",
            sdp_mid="0", sdp_m_line_index=0,
        ))
        checkpoint("early_trickle")
        await event("PEER_IN", "OTHER_CAMERA")
        checkpoint("unrelated_peer")
        await event("PEER_IN", serial)
        checkpoint("owned_peer_offer_and_embedded_ice")
        await session.add_candidate(SimpleNamespace(
            candidate="candidate:3 1 udp 1 192.0.2.3 4002 typ host",
            sdp_mid="1", sdp_m_line_index=1,
        ))
        checkpoint("trickle_while_waiting_for_answer")
        await event("PEER_OUT", serial)
        await event("PEER_IN", serial)
        checkpoint("rejoined_peer")
        answer_sdp = "v=0\r\n"
        await session._handle_signal_event("SDP_ANSWER", {
            "senderClientId": serial, "recipientClientId": "viewer123",
            "messagePayload": base64.b64encode(json.dumps({
                "type": "answer", "sdp": answer_sdp,
            }).encode()).decode(),
        })
        checkpoint("answer_flushes_trickled_ice")
        assert session._answer.result() == answer_sdp
    finally:
        await session.close()
        if not session._answer.done():
            session._answer.cancel()
    trace.append({"step": "closed", "socket_closed": ws.closed})
    return trace


async def test_ten_camera_switches_match_65984b9_wire_sequence():
    fixture = json.loads((Path(__file__).parent / "fixtures" / "webrtc_65984b9.json").read_text())
    assert fixture["commit"] == "65984b9126deb0646f8fd1b4f756f5430e4718e8"
    for index in range(10):
        serial = "CAMERA_A" if index % 2 == 0 else "CAMERA_B"
        assert await relay_trace(webrtc_signal, serial) == fixture["traces"][serial]
