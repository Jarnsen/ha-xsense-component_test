## 🚀 v.1.2.5

A major APK-alignment release after the 1.2.4 cloud/API refactor. This version improves device actions, self-test reporting, camera gating, and API efficiency so Home Assistant behaves much closer to the X-Sense Android app.

### ✨ Highlights

- 📱 Matched more Wi-Fi, SBS50 child-device, smoke, CO, water, temperature, and radon actions to the APK paths.
- 🧪 Added readable self-test result and time sensors using the APK self-test update topics.
- 📷 Avoided unnecessary camera API probing unless APK-supported SSC0A/SSC0B cameras are present.
- 🕒 Stopped base station report-time updates from filling the Home Assistant activity log.

### 🛠️ Fixed

- Fixed Wi-Fi action thing names, including dashed/non-dashed models and the special XS01-WX EN/UL serial path.
- Fixed Wi-Fi fire-drill and self-test action targets to use the same shadow targets as the APK.
- Fixed camera-only entities so camera controls and diagnostics appear only for APK-supported camera models.
