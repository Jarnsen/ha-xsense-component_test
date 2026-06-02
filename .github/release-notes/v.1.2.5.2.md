## v.1.2.5.2

### Summary

This hotfix improves camera discovery for accounts where cameras are returned through the APK/ADDX camera device list.

### Fixed

- Fixed camera discovery for accounts where X-Sense cameras are returned through the same APK/ADDX camera device list used by the mobile app, but are not present in the normal X-Sense station list.
- Created SSC0A and SSC0B camera entities from the ADDX /device/listuserdevices response before camera metadata is loaded.
- Kept IPC/ADDX camera discovery errors visible instead of silently treating them as no camera support.

### Improved

- Added regression coverage for APK-aligned camera discovery from the ADDX device list.

### Validation

- Full test suite passed
