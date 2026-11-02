"""Regressions for source-audit findings, without live cloud access."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.xsense import binary_sensor, number, select, switch
from custom_components.xsense.python_xsense.async_xsense import (
    AsyncXSense,
    _station_info_shadow_names,
)
from custom_components.xsense.python_xsense.event_parser import mqtt_reported_data
from custom_components.xsense.python_xsense.exceptions import APIFailure, SessionExpired
from custom_components.xsense.python_xsense.mapping import (
    safe_float,
    safe_float_list,
    safe_int,
)
from custom_components.xsense.python_xsense.station import Station
from custom_components.xsense.python_xsense.xsense import XSense


class Response:
    def __init__(self, status, data):
        self.status = status
        self.data = data

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def text(self):
        return json.dumps(self.data)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,data,error",
    [
        (500, {"message": "temporary outage"}, APIFailure),
        (429, {"__type": "TooManyRequestsException"}, APIFailure),
        (400, {"__type": "TooManyRequestsException"}, APIFailure),
        (400, {"__type": "NotAuthorizedException"}, SessionExpired),
        (200, {}, APIFailure),
        (200, [], APIFailure),
        (200, {"AuthenticationResult": {"IdToken": "id"}}, APIFailure),
        (
            200,
            {
                "AuthenticationResult": {
                    "IdToken": "id",
                    "AccessToken": "access",
                    "ExpiresIn": "invalid",
                }
            },
            APIFailure,
        ),
    ],
)
async def test_failed_refresh_preserves_existing_credentials(status, data, error):
    client = AsyncXSense()
    client.aws_access_key = "existing-aws-key"
    client.access_token = "existing-access"
    client.id_token = "existing-id"
    client.refresh_token = "existing-refresh"
    client._refresh_request = lambda: ("https://unused.invalid", {}, {})
    client._get_session = AsyncMock(
        return_value=SimpleNamespace(post=lambda *a, **k: Response(status, data))
    )
    with pytest.raises(error):
        await client.refresh()
    assert client.aws_access_key == "existing-aws-key"
    assert client.access_token == "existing-access"
    assert client.id_token == "existing-id"
    assert client.refresh_token == "existing-refresh"


@pytest.mark.parametrize("state", [None, [], "invalid", 42])
def test_malformed_shadow_envelope_is_ignored(state):
    assert mqtt_reported_data({"state": state}) == {}
    assert mqtt_reported_data({"state": {"reported": {"alarmStatus": False}}}) == {
        "alarmStatus": False
    }


@pytest.mark.parametrize(
    "value", ["NaN", "Infinity", "-Infinity", float("inf"), float("nan")]
)
def test_nonfinite_measurements_are_unknown(value):
    assert safe_float(value) is None
    assert safe_int(value) is None


@pytest.mark.parametrize("value", [[10, 30], "10,30", "[10,30]", "[10, 30]"])
def test_apk_range_shapes(value):
    assert safe_float_list(value) == [10.0, 30.0]


def test_nonfinite_range_is_rejected():
    assert safe_float_list("[10, NaN]") is None


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 403, 429, 500])
async def test_house_shadow_failure_is_not_silently_successful(status):
    client = AsyncXSense()
    client._lastres = SimpleNamespace(status=status)
    client.get_house = AsyncMock(return_value={"message": "failure"})
    with pytest.raises(APIFailure):
        await client.get_house_state(SimpleNamespace())


@pytest.mark.parametrize("status", [403, 429, 500])
def test_sync_shadow_write_rejects_http_failure(status):
    response = SimpleNamespace(status_code=status, json=lambda: {"message": "failure"})
    client = XSense(session=SimpleNamespace(post=lambda *a, **k: response))
    client._aws_token_expiring = lambda: False
    client._thing_request = lambda *args: ("https://unused.invalid", {})
    with pytest.raises(APIFailure):
        client.do_thing(SimpleNamespace(), "page", {})


@pytest.mark.parametrize("client_type", [AsyncXSense, XSense])
def test_valid_refresh_retains_refresh_token_and_invalidates_old_identity(client_type):
    client = client_type()
    client.refresh_token = "original-refresh"
    client.aws_access_key = "old-aws"
    client._accept_refresh_response(
        200,
        {
            "AuthenticationResult": {
                "AccessToken": "new-access",
                "IdToken": "new-id",
                "ExpiresIn": 3600,
            }
        },
    )
    assert client.refresh_token == "original-refresh"
    assert client.access_token == "new-access"
    assert client.id_token == "new-id"
    assert client.aws_access_key is None
    if isinstance(client, XSense):
        client.close()


@pytest.mark.parametrize(
    "model", ["CB0T-3B", "LP/R-SCA(VL)-0G", "CB0T-4B", "W/R-SCA(VL)-0G"]
)
def test_regional_combos_keep_canonical_alarm_and_silence_semantics(model):
    entity = SimpleNamespace(type=model, data={})
    assert binary_sensor.has_alarm_status(entity)
    assert binary_sensor.has_life_end_status(entity)
    for active in (False, True):
        for code in range(5):
            entity.data = {"alarmStatus": active, "muteStatus": code}
            assert binary_sensor.mute_status(entity) is (active and 1 <= code <= 3)


@pytest.mark.parametrize("model", ["CB0T-4B", "W/R-SCA(VL)-0G"])
def test_regional_wifi_combo_thing_and_info_page(model):
    station = Station(
        SimpleNamespace(), category=model, stationId="station", stationSn="SERIAL"
    )
    assert station.shadow_name == f"{model}-SERIAL"
    assert _station_info_shadow_names(station) == ("2nd_info_SERIAL",)


@pytest.mark.parametrize(
    "model,count", [("SDA51", 7), ("SMA51", 7), ("SMA0A", 7), ("SWS51", 3)]
)
def test_alarm_tone_choices_follow_the_model_dialog(model, count):
    description = next(item for item in select.SELECTS if item.key == "alarm_tone")
    assert select.shadow_select_options(
        SimpleNamespace(type=model, data={}), description
    ) == [str(i) for i in range(1, count + 1)]


def test_nonfinite_number_pair_is_unknown():
    assert number._number_pair([float("inf"), 30]) is None
    assert number._number_pair([10, float("nan")]) is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code,expected",
    [("account-code", "account-code"), (None, "legacy-user"), ("", "legacy-user")],
)
async def test_command_user_id_prefers_apk_account_claim_with_legacy_fallback(
    code, expected
):
    station = SimpleNamespace(sn="BASE")
    entity = SimpleNamespace(sn="DEVICE", type="SWS51", data={}, station=station)
    client = AsyncXSense()
    client.userid = "legacy-user"
    client.user_id_code = code
    client.do_thing = AsyncMock()
    await client.set_state(entity, "waterSelfTest", "page", {})
    assert client.do_thing.call_args.args[2]["state"]["desired"]["userId"] == expected
    _, payload = client.build_command_state(entity, "appMode", {})
    assert payload["state"]["desired"]["userId"] == expected
    sync = XSense()
    sync.userid, sync.user_id_code = "legacy-user", code
    sync.do_thing = Mock()
    try:
        sync.set_state(entity, "waterSelfTest", "page", {})
        assert sync.do_thing.call_args.args[2]["state"]["desired"]["userId"] == expected
    finally:
        sync.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled,volume", [("0", "0"), ("1", "50")])
@pytest.mark.parametrize("model", ["STH0B", "STH0A", "STH51", "SWS51"])
async def test_sth0b_alarm_enable_pairs_volume_without_changing_other_models(
    enabled, volume, model
):
    client = AsyncXSense()
    client.do_thing = AsyncMock()
    parent = SimpleNamespace(sn="BASE", type="SBS50")
    entity = SimpleNamespace(
        sn="DEVICE", type=model, station=parent, data={"alarmVol": 0}
    )
    await client.update_shadow_setting(entity, "alarmEnable", enabled)
    desired = client.do_thing.call_args.args[2]["state"]["desired"]
    assert desired["alarmEnable"] == enabled
    if model in {"STH0B", "STH0A", "STH51"}:
        assert desired["alarmVol"] == volume
    else:
        assert "alarmVol" not in desired


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bounds", [[float("nan"), 30], [10, float("inf")], [30, 10], [10]]
)
async def test_invalid_range_write_never_reaches_the_cloud(bounds):
    client = AsyncXSense()
    client.do_thing = AsyncMock()
    entity = SimpleNamespace(
        sn="DEVICE", type="STH51", station=SimpleNamespace(sn="BASE", type="SBS50")
    )
    with pytest.raises(ValueError):
        await client.update_shadow_array_setting(entity, "tRange", bounds)
    client.do_thing.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("minimum,maximum", [(float("nan"), 150), (75, float("inf"))])
async def test_nonfinite_radon_threshold_never_reaches_the_cloud(minimum, maximum):
    client = AsyncXSense()
    client.api_call = AsyncMock()
    entity = SimpleNamespace(sn="RADON", entity_id="radon")
    with pytest.raises(ValueError):
        await client.update_radon_thresholds(
            entity, min_radon=minimum, max_radon=maximum
        )
    client.api_call.assert_not_awaited()


@pytest.mark.parametrize("payload", [None, [], 7, {"reCode": 200}])
def test_sync_api_rejects_malformed_envelopes(payload):
    response = SimpleNamespace(status_code=200, json=lambda: payload)
    client = XSense(session=SimpleNamespace(post=lambda *a, **k: response))
    with pytest.raises(APIFailure):
        client.api_call("unused", unauth=True)


def test_sync_api_invalid_json_becomes_api_failure():
    response = SimpleNamespace(
        status_code=502, json=Mock(side_effect=ValueError("invalid JSON"))
    )
    client = XSense(session=SimpleNamespace(post=lambda *a, **k: response))
    with pytest.raises(APIFailure):
        client.api_call("unused", unauth=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
async def test_number_entity_rejects_nonfinite_service_values(value):
    client = SimpleNamespace(update_shadow_volume=AsyncMock())
    instance = SimpleNamespace(
        _current_entity=lambda: SimpleNamespace(),
        entity_description=SimpleNamespace(exists_fn=lambda _: True),
        coordinator=SimpleNamespace(xsense=client),
    )
    with pytest.raises(HomeAssistantError):
        await number.XSenseNumberEntity.async_set_native_value(instance, value)
    client.update_shadow_volume.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("fails", [False, True])
@pytest.mark.parametrize("model", ["STH0B", "STH0A", "STH51"])
async def test_sth0b_switch_updates_paired_cache_only_after_success(fails, model):
    parent = SimpleNamespace(sn="BASE", type="SBS50", shadow_name="SBS50BASE")
    entity = SimpleNamespace(
        sn="DEVICE",
        type=model,
        station=parent,
        data={"alarmEnabled": False, "alarmVol": 0},
    )
    client = AsyncXSense()
    client.do_thing = AsyncMock(side_effect=APIFailure("offline") if fails else None)
    coordinator = SimpleNamespace(xsense=client, async_update_listeners=Mock())
    instance = SimpleNamespace(
        _current_entity=lambda: entity,
        entity_description=next(
            item for item in switch.SWITCHES if item.key == "alarm_enabled"
        ),
        coordinator=coordinator,
    )
    if fails:
        with pytest.raises(APIFailure):
            await switch.XSenseSwitchEntity._async_set_state(instance, True)
        assert entity.data == {"alarmEnabled": False, "alarmVol": 0}
        coordinator.async_update_listeners.assert_not_called()
    else:
        await switch.XSenseSwitchEntity._async_set_state(instance, True)
        assert entity.data == {"alarmEnabled": True, "alarmVol": 50}
        coordinator.async_update_listeners.assert_called_once()
