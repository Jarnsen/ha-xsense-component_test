from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from custom_components.xsense.diagnostics import (
    api_client_diagnostics,
    async_get_config_entry_diagnostics,
    coordinator_diagnostics,
    entity_diagnostics,
    local_communication_diagnostics,
)
from custom_components.xsense.const import DOMAIN


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
    assert diagnostics["communication"] == {
        "ip_reported": True,
        "ssid_reported": False,
        "mac_reported": True,
        "local_runtime_candidate": True,
        "local_control_confirmed": False,
        "runtime_path": "aws_iot_shadow",
        "shadow_name": None,
    }
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

    assert diagnostics["communication"]["local_runtime_candidate"] is False
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


def test_local_communication_diagnostics_marks_lan_fields_as_unproven():
    entity = SimpleNamespace(
        type="XS01-WX",
        online=True,
        shadow_name="XS01-WXstation-sn",
        data={
            "ipAddress": "192.168.1.87",
            "ssid": "Reid",
            "mac": "00:11:22:33:44:55",
        },
    )

    diagnostics = local_communication_diagnostics(entity)

    assert diagnostics == {
        "ip_reported": True,
        "ssid_reported": True,
        "mac_reported": True,
        "local_runtime_candidate": True,
        "local_control_confirmed": False,
        "runtime_path": "aws_iot_shadow",
        "shadow_name": "XS01-WXstation-sn",
    }


def test_api_client_diagnostics_keeps_session_state_without_tokens():
    xsense = SimpleNamespace(
        VERSION="v1.36.0_20260130",
        APPCODE="1360",
        CLIENTYPE="2",
        IPC_VERSION="v1.36.0_20260130",
        IPC_APPCODE="1360",
        IPC_CLIENTTYPE="2",
        region="us-east-1",
        userid="user-id",
        user_id_code="user-id-code",
        signer=object(),
        access_token="secret-access-token",
        refresh_token="secret-refresh-token",
        access_token_expiry=datetime.now(timezone.utc) + timedelta(seconds=120),
        aws_access_key="secret-key",
        aws_secret_access_key="secret-secret",
        aws_session_token="secret-session",
        aws_access_expiry=datetime.now(timezone.utc) - timedelta(seconds=5),
        _addx_session={"token": "secret-addx-token", "nodeType": "US"},
        houses={"house-id": object()},
    )

    diagnostics = api_client_diagnostics(xsense)

    assert diagnostics["connected"] is True
    assert diagnostics["app_version"] == "v1.36.0_20260130"
    assert diagnostics["user_id_present"] is True
    assert diagnostics["user_id_code_present"] is True
    assert diagnostics["aws_signer_present"] is True
    assert diagnostics["access_token"]["present"] is True
    assert diagnostics["access_token"]["expired"] is False
    assert diagnostics["aws_token"]["present"] is True
    assert diagnostics["aws_token"]["expired"] is True
    assert diagnostics["addx_session_present"] is True
    assert diagnostics["addx_node_type"] == "US"
    assert diagnostics["house_count"] == 1
    assert "secret" not in str(diagnostics)


def test_api_client_diagnostics_handles_missing_client():
    assert api_client_diagnostics(None) == {"connected": False}


def test_api_client_diagnostics_handles_naive_expiry_datetimes():
    naive_utc_now = datetime.now(timezone.utc).replace(tzinfo=None)
    xsense = SimpleNamespace(
        access_token_expiry=naive_utc_now + timedelta(seconds=120),
        aws_access_expiry=naive_utc_now - timedelta(seconds=5),
    )

    diagnostics = api_client_diagnostics(xsense)

    assert diagnostics["access_token"]["present"] is True
    assert diagnostics["access_token"]["expired"] is False
    assert diagnostics["aws_token"]["present"] is True
    assert diagnostics["aws_token"]["expired"] is True


def test_coordinator_diagnostics_includes_compact_mqtt_state():
    mqtt = SimpleNamespace(
        connected=True,
        _simple_subscriptions={"topic/one": set(), "topic/two": set()},
        _wildcard_subscriptions={"topic/+/#"},
    )
    station = SimpleNamespace(
        type="XS01-WX",
        data={"ipAddress": "192.168.1.87", "ssid": "Reid"},
        shadow_name="XS01-WXstation-sn",
    )
    device = SimpleNamespace(type="SBS50", data={}, shadow_name="SBS50-sn")
    coordinator = SimpleNamespace(
        data={"stations": {"station": station}, "devices": {"device": device}},
        last_update_success=True,
        last_exception=None,
        _initialized=True,
        _camera_initialized=False,
        _last_camera_update_attempt=None,
        _camera_station_cache={},
        mqtt_servers={"mqtt.example": mqtt},
        xsense=SimpleNamespace(
            VERSION="v1",
            APPCODE="1",
            CLIENTYPE="2",
            IPC_VERSION="v1",
            IPC_APPCODE="1",
            IPC_CLIENTTYPE="2",
            houses={},
        ),
    )

    diagnostics = coordinator_diagnostics(coordinator)

    assert diagnostics["api"]["connected"] is True
    assert diagnostics["mqtt_server_count"] == 1
    assert diagnostics["mqtt_connected_count"] == 1
    assert diagnostics["mqtt_servers"] == {
        "mqtt.example": {"connected": True, "subscriptions": 3}
    }
    assert diagnostics["communication"] == {
        "local_runtime_candidates": 1,
        "local_control_confirmed": 0,
        "aws_iot_shadow": 2,
    }


async def test_config_entry_diagnostics_handles_missing_coordinator_data():
    coordinator = SimpleNamespace(
        data=None,
        last_update_success=False,
        last_exception=RuntimeError("refresh failed"),
        _initialized=False,
        _camera_initialized=False,
        _last_camera_update_attempt=None,
        _camera_station_cache={},
        mqtt_servers={},
        xsense=None,
    )
    entry = SimpleNamespace(
        entry_id="entry-id",
        as_dict=lambda: {
            "entry_id": "entry-id",
            "data": {"email": "user@example.test", "password": "secret-password"},
        },
    )
    hass = SimpleNamespace(data={DOMAIN: {"entry-id": coordinator}})

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["entry"]["data"]["email"] == "**REDACTED**"
    assert diagnostics["entry"]["data"]["password"] == "**REDACTED**"
    assert diagnostics["coordinator"]["api"] == {"connected": False}
    assert diagnostics["coordinator"]["last_exception"] == "RuntimeError"
    assert diagnostics["data"] == {"stations": [], "devices": []}
