"""Guard codec filtering independently of signaling lifecycle tests."""
import pytest

from custom_components.xsense.python_xsense.webrtc_signal import _relay_offer_sdp


@pytest.mark.parametrize("payloads", [(96, 98), (102, 108)])
def test_h264_selection_uses_codec_names_and_preserves_parameters(payloads):
    first, second = payloads
    parameters = {
        first: "level-asymmetry-allowed=1;packetization-mode=1;profile-level-id=42001f",
        second: "level-asymmetry-allowed=1;packetization-mode=0;profile-level-id=42e01f",
    }
    lines = [
        "v=0", "a=group:BUNDLE 0 1 2",
        "m=audio 9 UDP/TLS/RTP/SAVPF 111 0", "a=mid:0",
        "a=rtpmap:111 opus/48000/2", "a=fmtp:111 minptime=10",
        "a=rtpmap:0 PCMU/8000",
        f"m=video 9 UDP/TLS/RTP/SAVPF 120 {first} 121 {second}",
        "a=mid:1", "a=recvonly", "a=rtcp-mux", "a=rtcp-fb:* transport-cc",
        "a=rtpmap:120 VP8/90000", "a=rtcp-fb:120 nack",
        "a=rtpmap:121 rtx/90000", f"a=fmtp:121 apt={first}",
    ]
    for payload, fmtp in parameters.items():
        lines.extend([f"a=rtpmap:{payload} H264/90000", f"a=fmtp:{payload} {fmtp}", f"a=rtcp-fb:{payload} nack pli"])
    data = "m=application 9 UDP/DTLS/SCTP webrtc-datachannel\r\na=mid:2\r\na=sctp-port:5000\r\n"
    result, context = _relay_offer_sdp("\r\n".join(lines) + "\r\n" + data)
    assert "m=audio 9 UDP/TLS/RTP/SAVPF 0\r\n" in result
    assert f"m=video 9 UDP/TLS/RTP/SAVPF {first} {second}\r\n" in result
    for payload, fmtp in parameters.items():
        assert f"a=fmtp:{payload} {fmtp}\r\n" in result
        assert f"a=rtcp-fb:{payload} nack pli\r\n" in result
    assert "a=rtcp-fb:* transport-cc\r\n" in result
    assert result.endswith(data)
    for removed in ("opus/", "VP8/", "rtx/", "a=fmtp:121", "a=rtcp-fb:120"):
        assert removed not in result
    assert context["video_kept_payloads"] == 2


def test_absent_h264_preserves_existing_baseline_fallback():
    offer = "v=0\r\nm=video 9 UDP/TLS/RTP/SAVPF 96\r\na=rtpmap:96 VP8/90000\r\n"
    result, context = _relay_offer_sdp(offer)
    assert result == offer
    assert context["video_removed_payloads"] == 0


def test_additional_h264_profile_is_not_silently_rewritten():
    offer = "v=0\r\nm=video 9 UDP/TLS/RTP/SAVPF 41\r\na=rtpmap:41 H264/90000\r\na=fmtp:41 packetization-mode=1;profile-level-id=f4001f\r\n"
    assert _relay_offer_sdp(offer)[0] == offer
