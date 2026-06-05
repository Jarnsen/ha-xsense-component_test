## 🔧 v.1.2.6.9

A focused reliability hotfix for child-device shadow updates and WebRTC camera cleanup.

### 🛠️ Fixed

- 📡 Routed MQTT `devs` child payloads through the same APK-style state parser used by full shadow reads.
- 🧭 Matched child-device updates by the serial fields used in X-Sense shadow payloads instead of only the raw map key.
- 🎥 Fixed WebRTC camera cleanup when a live-view timeout closes the session, preventing the timeout task from cancelling itself.
- ⏱️ Added coverage to keep the old broad integration login timeout from coming back.

### 🔎 Validation

- ✅ Installed and restarted on Steve Home Assistant before release.
- ✅ X-Sense loaded and the smoke alarm entities came back online.
- ✅ Full test suite passed.
- ✅ APK-alignment pass completed for child shadow routing, camera WebRTC signaling, and active entity exposure.
