"""Allowlisted live-view diagnostics; never log raw signal payloads."""
import base64
import json
from urllib.parse import urlsplit


def trace_id(value):
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        return None
    text = str(value)
    if not text:
        return None
    return "..." + text[-min(6, max(0, len(text) - 1)):] if len(text) > 1 else "..."


def trace_host(value):
    if not isinstance(value, str):
        return None
    try:
        return urlsplit(value if "://" in value else "//" + value).hostname
    except ValueError:
        return None


def frame_context(raw):
    result = {"length": len(raw), "messageType": "unrecognized"}
    if len(raw) > 65536:
        result["inspection"] = "size_limit"
        return result
    try:
        envelope = json.loads(raw)
    except (ValueError, UnicodeError, TypeError):
        result["inspection"] = "non_json"
        return result
    if not isinstance(envelope, dict):
        result["inspection"] = "non_object"
        return result
    event = next((envelope.get(key) for key in (
        "messageType", "event", "type", "method"
    ) if envelope.get(key)), None)
    if event in ("PEER_IN", "PEER_OUT", "SDP_ANSWER", "SDP_OFFER", "ICE_CANDIDATE"):
        result["messageType"] = event
    result["envelope"] = _identities(envelope)
    if event not in ("PEER_IN", "PEER_OUT"):
        return result
    payload = next((envelope[key] for key in (
        "messagePayload", "payload", "data", "message", "body", "value"
    ) if key in envelope), None)
    if isinstance(payload, str):
        try:
            decoded = json.loads(payload)
            if isinstance(decoded, (dict, str)):
                payload = decoded
        except ValueError:
            if any(char in payload for char in "=+/") or payload.startswith("eyJ"):
                try:
                    decoded = base64.b64decode(payload + "=" * (-len(payload) % 4)).decode()
                    try:
                        payload = json.loads(decoded)
                    except ValueError:
                        payload = decoded
                except (ValueError, UnicodeError):
                    pass
    result["peer"] = _identities(payload) if isinstance(payload, dict) else {"id": trace_id(payload)}
    return result


def _identities(data):
    result = {key: trace_id(data[key]) for key in (
        "id", "name", "group", "clientId", "serialNumber",
        "senderClientId", "recipientClientId"
    ) if key in data}
    if "role" in data:
        role = data["role"]
        result["role"] = role if role in ("viewer", "device", "camera") else "other"
    return result
