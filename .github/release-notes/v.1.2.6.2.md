## v.1.2.6.2

### Fixed

- Update X-Sense app request metadata to match the current Android app.
- Match the Android app compact-style JSON payloads for AWS shadow and MQTT commands.
- Fix X-Sense request signing for Unicode payloads, empty lists, booleans, and null values.
- Handle AWS IoT presence events so device online status updates like the app.
- Tighten camera handling to the APK-supported camera models and live-stream resolution fallback.
- Retry camera data loading after a failed camera update instead of suppressing future retries.
