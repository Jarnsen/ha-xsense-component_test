## X-Sense Home Security v.1.2.6.11

### 🔧 Fixes
- Fixed the camera WebRTC start path so online cameras send the SDP offer when the X-Sense signal socket opens, while offline/unknown cameras still wait for PEER_IN like the Android app.
- Kept `PEER_IN` handling as the offline camera resume path instead of blocking cameras already reported online.
- Matched the APK startLive timing by waiting for both the data channel and camera peer connection before sending the live command.
- Tightened WebRTC close cleanup after failed stream attempts to reduce leftover aioice retry/session errors.
- Normalized camera motion sensitivity and recording duration defaults the same way the Android app does, avoiding unknown `0` values for those controls.
