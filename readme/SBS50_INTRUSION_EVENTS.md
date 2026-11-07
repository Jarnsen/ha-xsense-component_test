# SBS50 Intrusion Events

Use the Home Assistant event `xsense_intrusion_triggered` to log security
alarm notices from an SBS50 with SDS0A door or SMS0A motion sensors:

```yaml
triggers:
  - trigger: event
    event_type: xsense_intrusion_triggered
```

The event includes `station_id`, `station_serial`, `device_id`,
`device_serial`, `device_name`, `device_type`, and the reported
`alarm_time` and `event_id` when available. `alarm_time` preserves the
cloud's original timestamp; Home Assistant also records when it received
the event.

This uses the live cloud alarm notice, not a sensor state or a history
query. Opening a door, detecting motion, starting entry delay, or clearing
an alarm does not itself emit this event. The event follows the app's
SDS0A/SMS0A alarm handler, not its alarm popup logic. A supplied
`event_id` is passed through as metadata, without assuming it groups
multiple sensors.

The SBS50 alarm panel shows `triggered` while at least one sensor's live
intrusion notice remains active. Each clear notice removes only that sensor.
If a clear notice is missed, a fresh main-page shadow reporting that sensor
inactive also clears it. A confirmed station disarm clears the station's
active intrusion state; a bypass prompt or unconfirmed request does not.
After the last sensor clears, the panel shows the latest reported armed mode.
This state is tracked from live notices and is not reconstructed from history
after a Home Assistant restart.
