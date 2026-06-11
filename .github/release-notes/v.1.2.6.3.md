## 📷 v.1.2.6.3

A focused camera and MQTT polish release. This version improves APK-aligned camera discovery for accounts where the Android app reports cameras only through the ADDX camera device list, and quiets clean MQTT disconnect noise.

### ✨ Highlights

- 📷 Uses the APK/ADDX camera device list as the camera authority for SSC0A and SSC0B cameras.
- 🔁 Creates camera entities even when the normal home device list has no camera stub.
- 🧭 Reconciles stale camera stubs against the camera serials returned by the Android app API path.
- 📡 Treats clean MQTT disconnect code 0 as a normal debug event instead of a warning.
- 🎥 Starts live view with the APK default empty liveResolution when no camera-specific live ratio is saved.
- 🧩 Derives WebRTC support from the APK streamProtocol rule instead of relying on optional metadata.

### 🛠️ Fixed

- Fixed missing cameras for accounts where the ADDX camera list returns the camera but the normal home device list does not.
- Fixed camera replacement when an old home-list camera stub does not match the current ADDX camera serial.
- Fixed unnecessary Home Assistant log warnings for clean MQTT disconnects.
- Fixed live-stream startup payloads to match the APK when no saved live ratio exists.
- Fixed WebRTC support reporting for RTSP/RTMP cameras using the APK DeviceBean.isWebRTC() rule.
