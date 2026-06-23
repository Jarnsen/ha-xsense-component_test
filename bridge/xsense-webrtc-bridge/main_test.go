package main

import "testing"

func TestMapVideoSizeMatchesAPKResolutionBuckets(t *testing.T) {
	tests := map[string]string{
		"640x360":    "1280x720",
		"640x480":    "1280x720",
		"960x720":    "1280x720",
		"1280x720":   "1280x720",
		"1280x960":   "1280x720",
		"1920x1080":  "1920x1080",
		"2048x1440":  "1920x1080",
		"2048x1536":  "1920x1080",
		"2304x1296":  "1920x1080",
		"2560x1440":  "1920x1080",
		"3840x2160":  "1920x1080",
		"7680x4320":  "1920x1080",
		"unexpected": "1280x720",
	}

	for resolution, expected := range tests {
		if got := mapVideoSize(resolution); got != expected {
			t.Fatalf("mapVideoSize(%q) = %q, want %q", resolution, got, expected)
		}
	}
}
