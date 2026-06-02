## v.1.2.6.2

### Summary

This hotfix aligns app metadata, signing, MQTT/shadow payloads, presence updates, and camera handling with the current Android APK.

### Fixed

- Updated X-Sense app request metadata to match the current Android app.
- Matched the Android app compact JSON format for AWS shadow and MQTT command payloads.
- Fixed request signing for Unicode payloads, empty lists, booleans, null values, and mixed list values.
- Added AWS IoT presence-event handling so online/offline state updates like it does in the app.
- Tightened camera support to the APK-supported camera models and improved live-stream resolution fallback.
- Allowed camera data loading to retry after a failed update instead of suppressing future attempts.

### Validation

- Installed and checked on Steve Home Assistant before release
- Home Assistant config check passed
- Home Assistant restarted successfully after install
- XS01-WX live API readback confirmed online with current data
- Full test suite passed
