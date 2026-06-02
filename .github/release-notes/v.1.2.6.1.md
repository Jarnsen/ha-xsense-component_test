## v.1.2.6.1

### Fixed

- Remove obsolete serial number and MAC address sensor entities left behind by older releases.
- Harden obsolete sensor cleanup so stale identifier entries are removed without touching current device entities.
- Rename legacy X-Sense entities that were left with none-suffixed IDs when a clean device-based entity ID is available.
- Keep control entities unavailable until X-Sense reports the device online, while still showing sensor data when it exists.
- Match the APK online-time offline thresholds so stale reports do not make devices look controllable.
- Keep static identifiers out of normal sensors and visible device metadata while leaving them available in Home Assistant diagnostics.
