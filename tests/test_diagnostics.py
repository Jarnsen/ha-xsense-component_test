from types import SimpleNamespace

from custom_components.xsense.diagnostics import entity_diagnostics


def test_entity_diagnostics_keeps_static_identifiers_visible():
    entity = SimpleNamespace(
        type="SBS50",
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
            "wifiRSSI": -55,
        },
    )

    diagnostics = entity_diagnostics(entity)
    data = diagnostics["data"]

    assert diagnostics["serial_number"] == "entity-sn"

    assert data["deviceSN"] == "device-sn"
    assert data["ip"] == "192.0.2.10"
    assert data["ipAddress"] == "192.0.2.11"
    assert data["mac"] == "00:11:22:33:44:55"
    assert data["macBT"] == "AA:BB:CC:DD:EE:FF"
    assert data["serialNumber"] == "serial-number"
    assert data["sn"] == "sn-value"
    assert data["ipcId"] == "**REDACTED**"
    assert data["ipcSn"] == "**REDACTED**"
    assert data["stationId"] == "**REDACTED**"
    assert data["stationSN"] == "station-sn"
    assert data["wiredMacAddress"] == "66:77:88:99:AA:BB"
    assert data["wifiRSSI"] == -55


def test_entity_diagnostics_handles_missing_serial_number():
    entity = SimpleNamespace(type="UNKNOWN", data={})

    diagnostics = entity_diagnostics(entity)

    assert diagnostics["serial_number"] is None
    assert diagnostics["data"] == {}
