## 📷 v.1.2.5.2

A camera discovery hotfix for accounts where X-Sense cameras are returned through the APK/ADDX camera device list instead of the normal station list.

### ✨ Highlights

- 📷 Improved SSC0A and SSC0B camera discovery from the ADDX `/device/listuserdevices` response.
- 🔍 Kept IPC/ADDX camera discovery errors visible so future camera API issues are easier to diagnose.

### 🛠️ Fixed

- Fixed camera creation before camera metadata is fully loaded.
- Fixed accounts where APK-visible cameras were missing from Home Assistant.

### 🔎 Validation

- ✅ Full test suite passed.
- ✅ Added regression coverage for APK-aligned camera discovery.
