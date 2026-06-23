# X-Sense WebRTC Bridge

This is an experimental local bridge for testing X-Sense camera WebRTC sessions.
The normal Home Assistant camera path does not require this bridge.

The bridge speaks the APK-style X-Sense signaling flow to the camera and exposes
a go2rtc-compatible WebRTC source on `127.0.0.1:39091`. It is intended for
development and troubleshooting while the integration's default camera live view
continues to use the stable X-Sense stream source path.

## Build

```bash
go test ./...
go build -o xsense-webrtc-bridge .
```

## Run

```bash
./xsense-webrtc-bridge
```

Then open the X-Sense integration options in Home Assistant and select
`Experimental X-Sense WebRTC bridge`. That option also enables integration debug
logging while it is selected.
