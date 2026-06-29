package main

import (
	"os"
	"reflect"
	"testing"

	"github.com/pion/webrtc/v4"
)

func TestIceURLsSupportsStringAndList(t *testing.T) {
	if got := iceURLs("stun:example.invalid"); !reflect.DeepEqual(got, []string{"stun:example.invalid"}) {
		t.Fatalf("string URLs mismatch: %#v", got)
	}

	raw := []any{"turn:one.invalid", "turn:two.invalid", 7}
	if got := iceURLs(raw); !reflect.DeepEqual(got, []string{"turn:one.invalid", "turn:two.invalid"}) {
		t.Fatalf("list URLs mismatch: %#v", got)
	}
}

func TestIceServersFromEnv(t *testing.T) {
	t.Setenv("XSENSE_RECORDINGS_ICE_SERVERS", `[{"urls":"stun:example.invalid"},{"urls":["turn:one.invalid","turn:two.invalid"],"username":"user","credential":"pass"}]`)

	servers := iceServersFromEnv()
	if len(servers) != 2 {
		t.Fatalf("expected 2 servers, got %d", len(servers))
	}
	if !reflect.DeepEqual(servers[0].URLs, []string{"stun:example.invalid"}) {
		t.Fatalf("first server URLs mismatch: %#v", servers[0].URLs)
	}
	if !reflect.DeepEqual(servers[1].URLs, []string{"turn:one.invalid", "turn:two.invalid"}) {
		t.Fatalf("second server URLs mismatch: %#v", servers[1].URLs)
	}
	if servers[1].Username != "user" || servers[1].Credential != "pass" {
		t.Fatalf("second server credentials mismatch: %#v", servers[1])
	}
}

func TestIceTransportPolicyFromEnv(t *testing.T) {
	t.Setenv("XSENSE_RECORDINGS_ICE_TRANSPORT_POLICY", "relay")
	if got := iceTransportPolicyFromEnv(); got != webrtc.ICETransportPolicyRelay {
		t.Fatalf("relay policy mismatch: %s", got.String())
	}

	if err := os.Unsetenv("XSENSE_RECORDINGS_ICE_TRANSPORT_POLICY"); err != nil {
		t.Fatal(err)
	}
	if got := iceTransportPolicyFromEnv(); got != webrtc.ICETransportPolicyAll {
		t.Fatalf("default policy mismatch: %s", got.String())
	}
}
