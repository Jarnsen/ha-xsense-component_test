from types import SimpleNamespace

from custom_components.xsense.diagnostics import entity_diagnostics


def test_entity_diagnostics_keeps_only_functional_state_data():
    entity = SimpleNamespace(
        type="SBS50",
        entity_type="BASESTATION",
        online=True,
        sn="entity-sn",
        data={
            "deviceSN": "device-sn",
            "ip": "192.0.2.10",
            "ipAddress": "192.0.2.11",
            "mac": "00:11:22:33:44:55",
            "macBT": "AA:BB:CC:DD:EE:FF",
            "serialNumber": "serial-number",
            "sn": "sn-value",
            "wiredMacAddress": "66:77:88:99:AA:BB",
            "ipcId": "ipc-id",
            "ipcSn": "ipc-sn",
            "stationId": "station-id",
            "stationSN": "station-sn",
            "thumbImgUrl": "https://example.test/thumb.jpg",
            "title": "Kitchen",
            "userId": "user-id",
            "wifiRSSI": -55,
            "safeMode": 1,
        },
    )

    diagnostics = entity_diagnostics(entity)

    assert diagnostics["type"] == "SBS50"
    assert diagnostics["entity_type"] == "BASESTATION"
    assert diagnostics["online"] is True
    assert "serial_number" not in diagnostics
    assert diagnostics["data"] == {
        "ip": "192.0.2.10",
        "ipAddress": "192.0.2.11",
        "wifiRSSI": -55,
        "safeMode": 1,
    }


def test_entity_diagnostics_keeps_camera_stream_urls_for_troubleshooting():
    entity = SimpleNamespace(
        type="XCO1-MR",
        entity_type="DEVICE",
        online=True,
        data={
            "cameraAudioUrl": "https://example.test/audio.m3u8",
            "cameraLiveUrl": "webrtc://camera",
            "cameraLiveId": "live-id",
            "cameraLiveProtocol": "webrtc",
            "firmwareStatus": 0,
            "liveAudioToggleOn": 1,
            "supportLiveAudio": None,
            "supportWebrtc": True,
            "thumbImgUrl": "https://example.test/thumb.jpg",
        },
    )

    diagnostics = entity_diagnostics(entity)

    assert diagnostics["data"] == {
        "cameraAudioUrl": "https://example.test/audio.m3u8",
        "cameraLiveProtocol": "webrtc",
        "cameraLiveUrl": "webrtc://camera",
        "firmwareStatus": 0,
        "liveAudioToggleOn": 1,
        "supportLiveAudio": None,
        "supportWebrtc": True,
    }


def test_entity_diagnostics_handles_missing_data():
    entity = SimpleNamespace(type="UNKNOWN")

    diagnostics = entity_diagnostics(entity)

    assert diagnostics["type"] == "UNKNOWN"
    assert diagnostics["entity_type"] == ""
    assert diagnostics["online"] is None
    assert diagnostics["data"] == {}
