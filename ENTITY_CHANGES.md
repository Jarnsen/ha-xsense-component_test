# X-Sense Entity Changes

This file tracks user-visible entity changes that may affect dashboards, automations, or existing entity lists.

## Current Behavior

- Entities are created from fields reported by X-Sense for the account and device. If X-Sense stops reporting a writable field such as `alarmVol`, the matching Home Assistant control is not created.
- Writable controls are exposed only when the integration has both a reported field and a known write path for that field.
- `CO Level` is a raw X-Sense diagnostic level code. CO concentration values use the ppm sensors such as `CO` and `CO Peak`.

## Recent Changes

### Unreleased

- SBS50 alarm volume is exposed when X-Sense reports `alarmVol`; it uses the same settings shadow path as alarm tone.
- LED light switches are created only when the device reports `ledLight`. Older LED switches created from model guessing are cleaned up when the device does not report that field.
- `CO Level` is marked as diagnostic because it is a raw X-Sense level code, not a ppm concentration sensor.

### 1.4.x

- Device settings that were previously read-only sensors moved to writable Home Assistant controls when X-Sense reports support.
- Alarm tone is exposed separately from alarm volume when X-Sense reports `alarmTone`.
- Alarm volume is exposed only when X-Sense reports `alarmVol`.
