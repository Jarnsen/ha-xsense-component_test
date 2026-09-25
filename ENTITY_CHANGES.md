# X-Sense Entity Changes

This file tracks user-visible entity changes that may affect dashboards, automations, or existing entity lists.

## Current Behavior

- Entities are created from fields reported by X-Sense for the account and device. If X-Sense stops reporting a writable field such as `alarmVol`, the matching Home Assistant control is not created.
- Writable controls are exposed only when the integration has both a reported field and a known write path for that field.
- `CO Level` is a raw X-Sense diagnostic level code. CO concentration values use the ppm sensors such as `CO` and `CO Peak`.

## Recent Changes

### 1.4.25.1

- XR0A-iR Wi-Fi radon stations expose the app home-card radon reading (`longTermValue`, Bq/m³), 1/7/30/90-day averages, long-term day count, and peak radon. Battery, Wi-Fi, alarm, and end-of-life entities are created for that station.
- STH0C Wi-Fi temperature/humidity stations create temperature, humidity, and alarm entities before late mainpage values arrive. SWS0B Wi-Fi water stations create the water alarm entity. Wi-Fi combo climate models XC04-WX, XC0C-iA, XC0C-iR, and XC0M-iR create temperature and humidity entities the same way.

### 1.4.18

- Combo smoke/CO detectors such as XP0A-MR are treated as CO-capable devices so CO and CO Level entities are created before late CO payload values arrive.
- Older `co_event_id` registry entries are cleaned up because they are no longer provided as Home Assistant entities.
- SBS50 alarm volume is exposed when X-Sense reports `alarmVol`; it uses the same settings shadow path as alarm tone.
- LED light switches are created only when the device reports `ledLight`. Older LED switches created from model guessing are cleaned up when the device does not report that field.
- `CO Level` is marked as diagnostic because it is a raw X-Sense level code, not a ppm concentration sensor.

### 1.4.x

- Device settings that were previously read-only sensors moved to writable Home Assistant controls when X-Sense reports support.
- Alarm tone is exposed separately from alarm volume when X-Sense reports `alarmTone`.
- Alarm volume is exposed only when X-Sense reports `alarmVol`.
