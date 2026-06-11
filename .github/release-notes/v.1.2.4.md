## 🚀 v.1.2.4

A larger APK-alignment release for camera discovery, supported device actions, device settings, and reported timestamps. This release moves more behavior onto the same paths used by the Android app.

### ✨ Highlights

- 📷 Fixed SSC0A/SSC0B camera discovery when cameras are returned by the app IPC/ADDX device list but not the normal station list.
- 🏠 Fixed standalone Wi-Fi setup for devices such as SC07-WX when there is no station-level `mainpage` shadow.
- 🕒 Stopped exposing base-station report time as a normal changing sensor, avoiding repeated Home Assistant activity-log entries.
- 🧪 Adjusted self-test actions for supported smoke, listener, water, keypad, motion, door, and Wi-Fi devices to match Android app shadow names, targets, and timestamp shapes.

### 🛠️ Improved

- 💡 Added supported light power control for SBS50 light devices.
- 🔊 Added alarm, voice, chirp, and reminder volume controls where devices report writable settings.
- 📷 Kept camera support scoped to the IPC models explicitly supported by the APK: SSC0A and SSC0B.
- 🔁 Improved initialization defaults for accounts where camera devices are discovered through the camera API path.
