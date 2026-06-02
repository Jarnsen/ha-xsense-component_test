## v.1.2.5

### Summary

This release tightens integration behavior to match the X-Sense Android app more closely after the 1.2.4 cloud/API refactor.

### Fixed

- Fixed camera API probing so accounts without SSC0A/SSC0B cameras do not call the IPC/ADDX camera API unnecessarily.
- Fixed camera-only entities so camera controls and diagnostics are exposed only for APK-supported camera models.
- Fixed self-test reporting to follow the APK self-test update topics and expose readable result/time sensors.
- Fixed base station report-time entities from filling the Home Assistant activity log.
- Fixed additional APK-supported mute actions for Wi-Fi, SBS50 child, smoke, CO, water, temperature, and radon devices.
- Fixed Wi-Fi action thing names to match the APK, including dashed and non-dashed models plus the special XS01-WX EN/UL serial path.
- Fixed Wi-Fi fire-drill and self-test action targets to use the same shadow targets as the APK.

### Improved

- Added regression coverage for APK thing-name rules, camera gating, action payloads, self-test updates, report-time handling, and shadow volume writes.
- Kept API usage lighter by skipping camera-specific API calls unless APK-supported cameras are present in the normal device list.

### Validation

- git diff --check
- JSON parse checks for integration strings and translations
- Python AST and duplicate-key checks for integration and test files
- Full test suite passed
