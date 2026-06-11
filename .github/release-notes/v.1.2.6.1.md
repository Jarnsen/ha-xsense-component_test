## 🧹 v.1.2.6.1

A cleanup and availability hotfix after 1.2.6. This release removes stale identifier entities, improves device availability behavior, and keeps diagnostics useful without cluttering normal device views.

### ✨ Highlights

- 🧹 Removed obsolete serial number and MAC address sensor entities left behind by older releases.
- 🟢 Kept control entities unavailable until X-Sense reports the device online, while still showing sensor data when available.
- 🧭 Matched APK online-time offline thresholds so stale reports do not make devices look controllable.

### 🛠️ Fixed

- Hardened obsolete sensor cleanup so stale identifier entries are removed without touching current device entities.
- Renamed legacy X-Sense entities that were left with old none-suffixed IDs when a clean device-based entity ID is available.
- Kept static identifiers out of normal sensors and visible device metadata while leaving them available in Home Assistant diagnostics.
