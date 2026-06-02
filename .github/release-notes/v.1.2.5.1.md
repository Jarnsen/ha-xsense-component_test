## v.1.2.5.1

### Summary

This hotfix addresses a Home Assistant startup warning introduced by MQTT setup work after the 1.2.5 release.

### Fixed

- Fixed MQTT TLS certificate setup so default certificate loading no longer runs on the Home Assistant event loop during integration setup.
- Moved MQTT connection preparation through the Home Assistant executor for both initial connect and reconnect paths.

### Improved

- Added regression coverage to ensure TLS setup is deferred until connection preparation.
- Added regression coverage to ensure MQTT connection preparation is routed through the Home Assistant executor.

### Validation

- git diff --check
- Full test suite passed
