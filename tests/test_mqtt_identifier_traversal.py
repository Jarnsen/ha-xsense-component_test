"""Bound repeated traversal without changing MQTT identifier precedence."""

import json
from unittest.mock import Mock

import pytest
from test_audit_repairs import make_coordinator, make_station

from custom_components.xsense.python_xsense import event_parser


def test_report_and_envelope_visit_shared_report_once(monkeypatch):
    report = {"stationSN": "station", "devs": {"child": {"deviceSN": "child"}}}
    envelope = {"state": {"reported": report}, "deviceSN": "envelope-device"}
    keys = []
    normalize = event_parser.mqtt_identifier_key_name

    def observe(key):
        keys.append(key)
        return normalize(key)

    monkeypatch.setattr(event_parser, "mqtt_identifier_key_name", observe)
    assert event_parser.mqtt_identifier_candidates(report, envelope) == [
        "station", "child", "envelope-device",
    ]
    assert keys.count("stationSN") == 1
    assert keys.count("devs") == 1


def test_equal_but_distinct_encoded_reports_keep_all_identifiers():
    assert event_parser.mqtt_identifier_candidates(
        '{"deviceSN":"first"}', '{"deviceSN":"second"}',
        {"eventData": '{"stationSN":"station"}'},
    ) == ["first", "second", "station"]


def test_shared_sequence_keeps_first_seen_identifier_order():
    shared = [{"deviceSN": "child"}]
    assert event_parser.mqtt_identifier_candidates(
        {"devs": shared, "stationSN": "station"},
        {"devs": shared, "deviceSN": "other"},
    ) == ["child", "station", "other"]


@pytest.mark.parametrize("debug, expected_walks", [(False, 0), (True, 1)])
def test_resolved_station_does_not_walk_payload_for_disabled_debug(monkeypatch, debug, expected_walks):
    station = make_station()
    coordinator = make_coordinator(station)
    coordinator.async_update_listeners = Mock()
    namespace = coordinator._async_process_mqtt_event.__func__.__globals__
    walk = Mock(wraps=namespace["_mqtt_identifier_candidates"])
    monkeypatch.setitem(namespace, "_mqtt_identifier_candidates", walk)
    monkeypatch.setattr(namespace["LOGGER"], "isEnabledFor", lambda _: debug)
    coordinator.async_event_received(
        f"$aws/things/{station.shadow_name}/shadow/name/2nd_mainpage/update",
        json.dumps({"state": {"reported": {"stationSN": station.sn, "safeMode": "Away"}}}).encode(),
    )
    assert station.safe_mode == "Away"
    assert walk.call_count == expected_walks
    coordinator.async_update_listeners.assert_called_once()


def test_unresolved_station_keeps_nested_identifier_fallback(monkeypatch):
    station = make_station()
    coordinator = make_coordinator(station)
    coordinator.async_update_listeners = Mock()
    namespace = coordinator._async_process_mqtt_event.__func__.__globals__
    walk = Mock(wraps=namespace["_mqtt_identifier_candidates"])
    monkeypatch.setitem(namespace, "_mqtt_identifier_candidates", walk)
    monkeypatch.setattr(namespace["LOGGER"], "isEnabledFor", lambda _: False)
    coordinator.async_event_received(
        "$aws/things/unknown/shadow/name/2nd_mainpage/update",
        json.dumps({"state": {"reported": {"nested": {"stationSN": station.sn}, "safeMode": "Away"}}}).encode(),
    )
    assert station.safe_mode == "Away"
    walk.assert_called_once()
    coordinator.async_update_listeners.assert_called_once()
