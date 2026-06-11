## 🚀 v.1.2.6.2

A focused stability release for X-Sense cloud/API communication. This version brings the integration closer to the current Android app behavior, especially around request signing, MQTT/shadow payloads, online status, and camera handling.

### ✨ Highlights

- 📱 Updated X-Sense app request metadata to match the current Android app.
- 🔐 Fixed request signing for Unicode payloads, empty lists, booleans, null values, and mixed list values.
- 📡 Matched AWS shadow and MQTT command payloads to the Android app compact JSON format.
- 🟢 Added AWS IoT presence handling so online/offline state updates more like the app.
- 📷 Tightened camera handling for APK-supported camera models and live-stream resolution fallback.

### 🛠️ Reliability

- 🔁 Camera data loading now retries after a failed update instead of suppressing later attempts.
- ✅ XS01-WX live readback was verified before release.
- 🏠 Home Assistant config check passed before publishing.
