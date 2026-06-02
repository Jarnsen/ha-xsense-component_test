from types import SimpleNamespace

from custom_components.xsense.diagnostics import entity_diagnostics


def test_entity_diagnostics_redacts_network_and_device_identifiers():
    entity = SimpleNamespace(
        type="SBS50",
        data={
            "deviceSN": "device-sn",
            "ip": "192.0.2.10",
            "ipAddress": "192.0.2.11",
            "ipcId": "ipc-id",
            "ipcSn": "ipc-sn",
            "stationId": "station-id",
            "stationSN": "station-sn",
            "wifiRSSI": -55,
        },
    )

    data = entity_diagnostics(entity)["data"]

    assert data["deviceSN"] == "**REDACTED**"
    assert data["ip"] == "**REDACTED**"
    assert data["ipAddress"] == "**REDACTED**"
    assert data["ipcId"] == "**REDACTED**"
    assert data["ipcSn"] == "**REDACTED**"
    assert data["stationId"] == "**REDACTED**"
    assert data["stationSN"] == "**REDACTED**"
    assert data["wifiRSSI"] == -55
