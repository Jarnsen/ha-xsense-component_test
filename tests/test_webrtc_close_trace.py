"""Cleanup diagnostics must identify callers without leaking frame contents."""

from custom_components.xsense.camera import _webrtc_close_callers


def test_close_trace_identifies_caller_without_paths_or_locals():
    secret = "private-token-must-not-appear"
    trace = _webrtc_close_callers()
    assert trace[0]["function"] == "test_close_trace_identifies_caller_without_paths_or_locals"
    assert 1 <= len(trace) <= 8
    assert secret not in repr(trace)
    for frame in trace:
        assert set(frame) == {"function", "file", "line"}
        assert "/" not in frame["file"]
        assert "\\" not in frame["file"]
        assert isinstance(frame["line"], int)
