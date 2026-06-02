from custom_components.xsense.coordinator import _is_self_test_topic


def test_self_test_topic_detection_matches_apk_markers():
    assert _is_self_test_topic(
        "$aws/things/SBS50sn/shadow/name/selftestup/update"
    )
    assert _is_self_test_topic(
        "$aws/things/SBS50sn/shadow/name/2nd_selftestup/update"
    )
    assert _is_self_test_topic(
        "$aws/things/SBS50sn/shadow/name/selftestup_v2/update"
    )
    assert _is_self_test_topic(
        "$aws/things/SBS50sn/shadow/name/2nd_listener_testup/update"
    )
    assert not _is_self_test_topic(
        "$aws/things/SBS50sn/shadow/name/2nd_safemode/update"
    )
