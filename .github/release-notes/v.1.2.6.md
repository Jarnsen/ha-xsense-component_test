## v.1.2.6

### Summary

This release expands APK-aligned device support, improves camera setup, and refreshes diagnostics and documentation.

### Fixed

- Fixed additional APK-aligned device update paths so station, child-device, and alternate/internal device payloads update the correct Home Assistant entities more reliably.
- Improved camera discovery and camera entity setup for devices reported through the X-Sense Android app API paths.
- Cleaned up diagnostics so user-facing diagnostic sections avoid unnecessary serial/MAC-style identifiers while keeping useful troubleshooting data.

### Improved

- Expanded and polished the translated README files, including setup screenshots, supported-device/entity guidance, and a canonical Simplified Chinese README with a legacy redirect.
- Added and updated regression coverage for the X-Sense API client, coordinator behavior, sensors, camera guards, and diagnostics.

### Validation

- Full test suite passed
- Documentation structure, link coverage, Markdown code fences, YAML examples, and stale wording checks passed
