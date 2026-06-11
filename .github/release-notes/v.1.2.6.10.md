## 🔧 v.1.2.6.10

A focused compatibility and reliability hotfix for Home Assistant 2026.5/2026.6, SBS10 child devices, and WebRTC camera cleanup.

### 🛠️ Fixed

- 🧩 Handled both Home Assistant MQTT subscription constructor shapes so older and newer supported HA builds can load the integration.
- 📡 Parsed SBS10 child-device `mainpage` reports when X-Sense sends the APK-style device list instead of a `devs` map.
- 🧪 Matched SBS10 smoke RF self-test commands to the APK target/shadow path for `XS01-M` and `XS03-iWX` devices.
- 🚨 Limited the SBS50 alarm control panel to security-device setups instead of smoke-only stations.
- 🎥 Tightened WebRTC camera cleanup to stop tracks, transports, senders, and receivers before closing peer connections.
