from types import SimpleNamespace

from custom_components.xsense.python_xsense import AsyncXSense, XSense
from custom_components.xsense.python_xsense.entity_map import SATestAction


def test_vendored_python_xsense_keeps_shared_library_compatibility_surface():
    assert XSense
    assert {
        "api_call",
        "get_history",
        "get_history_month",
        "get_station_history",
        "get_station_history_month",
        "get_security_history",
        "get_sth_history",
        "get_co_ppm_history",
        "get_co_ppm_history_details",
    } <= set(dir(XSense))
    assert {
        "get_history",
        "get_history_month",
        "get_security_history",
        "get_sth_history",
        "get_co_ppm_history",
        "get_co_ppm_history_details",
        "get_station_history_month",
        "query_mailbox_schedules",
        "create_mailbox_schedule",
        "update_mailbox_schedule",
        "rename_mailbox_schedule",
        "delete_mailbox_schedule",
    } <= set(dir(AsyncXSense))

    action = SATestAction()
    assert action["action"] == "test"
    assert action["shadow"] == "appSelfTest"
    assert action["topic"](SimpleNamespace(sn="device-id")) == "appselftest_device-id"
