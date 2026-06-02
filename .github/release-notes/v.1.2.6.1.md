## v.1.2.6.1

### Summary

This hotfix cleans up stale entities and improves availability handling after the 1.2.6 release.

### Fixed

- Removed obsolete serial number and MAC address sensor entities left behind by older releases.
- Hardened obsolete sensor cleanup so stale identifier entries are removed without touching current device entities.
- Renamed legacy X-Sense entities that were left with none-suffixed IDs when a clean device-based entity ID is available.
- Kept control entities unavailable until X-Sense reports the device online, while still showing sensor data when it exists.
- Matched the APK online-time offline thresholds so stale reports do not make devices look controllable.
- Kept static identifiers out of normal sensors and visible device metadata while leaving them available in Home Assistant diagnostics.

### Validation

- Home Assistant install check completed before release
- Full test suite passed
