## 🔧 v.1.2.2

A hotfix release for setup and control issues reported after 1.2.1. This version aligns standalone Wi-Fi and base station shadow reads more closely with the Android app.

### ✨ Highlights

- 🏠 Fixed setup failures caused by missing station-level X-Sense `mainpage` shadows on some standalone Wi-Fi devices.
- 📱 Aligned standalone Wi-Fi and base station shadow reads with Android app behavior.
- 🧪 Fixed smoke detector self-test payload timestamps.
- 🚨 Fixed fire drill payloads to target the base station serial the same way the Android app does.

### 🛠️ Fixed

- Fixed the setup 404 path for affected standalone Wi-Fi devices.
- Fixed smoke control payloads that were using the wrong timestamp or target shape.
- Cleaned up the Release Drafter template so future draft notes render correctly.
