# X-Sense APK Evidence

X-Sense APK reverse-engineering evidence for this integration belongs in:

`references/xsense_apk/`

Use that folder for recovered APK/XAPK files, jadx output, and short evidence notes. Do not rely on `.tmp`, OS temp folders, or disposable Codex work folders for APK evidence.

The local checkout currently excludes `references/` because that folder can contain large research material. If APK evidence notes need to ship in the repo, add the small note files explicitly or mirror the decision in this tracked file.

Before changing APK-sensitive behavior, recover or refresh the APK evidence and compare the implementation against it. APK-sensitive behavior includes camera events, recording playback, AI notifications, WebRTC signaling, and alarm-topic mappings.

Current local APK evidence:

- X-Sense APK `v1.40.0_20260612`, app code `1400`, package `com.xsense.security`, is stored locally as `references/xsense_apk/original/xsense-1400.apk`.
- Decompiled JADX output for app code `1400` is stored locally under `references/xsense_apk/decompiled/1400/`.
- `resources/AndroidManifest.xml` confirms `android:versionCode="1400"` and `android:versionName="v1.40.0_20260612"`.
- `sources/j2/C3839E.java` confirms signed API payload metadata: `appCode=1400`, `appVersion=v1.40.0_20260612`, `clientType=2`.
- `sources/A3/C1233g.java` confirms the decoded Cognito client secret strips the app-code prefix using `String.valueOf(1400).length()`.
- `sources/Q/v.java` confirms the ADDX/VicoHome camera metadata remains `VicoHome`, `com.ai.vicoo`, version code `200700500`, version name `2.7.5`.
- `sources/V1/f.java` is the primary APK device-type helper. At review time, a mechanical comparison of its model strings against `custom_components/xsense/python_xsense/entity_map.py` reported no missing APK helper models. Re-run that comparison whenever the APK is refreshed.
- `sources/com/claybox/iot/ams/thing/V.java` is the main APK shadow parser. The
  similarly named `T.java` is a query wrapper and must not be used as parser
  evidence.

## APK 1400 parity recheck (2026-07-19)

- The integration model map exactly matches every model routed by `V1/f.java`, plus the APK light-group pseudo-model `group-L`. Tests now lock both the exact model set and every model's entity family.
- Action auditing distinguishes APK command code, an actual APK UI route to that
  command, the integration's exposed action, and real-hardware confirmation.
  These are not interchangeable forms of evidence.
- For alarm detectors, `self-test` is the individual detector alarm/test command:
  it must sound that detector and produce the corresponding test result. `Fire
  drill` is the separate broader alarm command. Notification preferences and
  physical self-test reports do not prove that a remote self-test command exists.
- `XS01-WX` has a real active-alarm mute route in `F3/C2270O.java`: `appMute`
  on `appmute` or `2nd_appmute`, using the model-specific Wi-Fi thing name and
  `muteType=0`. The reachable alarm UI calls `smokeMute()` and the handler writes
  that shadow, so this is a command rather than a notification preference; the
  integration exposes Mute. APK settings expose a self-test notification
  preference but no reachable remote self-test command, so Test is not exposed.
  Physical self-test and mute reports remain supported.
- `SC06-WX` and `XS0B-iR` retain their APK alarm-mute route but do not expose a remote self-test route in APK 1400. Stale `test` buttons are removed while their physical self-test report sensors remain model-backed.
- `@claybox/events/keyboard/{requestId}` is a temporary PIN-creation confirmation subscription, not a live keypad-code event stream. Runtime SKP0A code events remain sourced from the APK `2nd_safenotice` path.
- Camera ticket fields, signal URL construction, peer/offer/answer ordering, direct `liveUrl`/`url` handling, recording endpoints, and ADDX metadata were rechecked against APK 1400 with no new camera protocol delta found.
- APK 1400 parses both `peak.coPpmPeak` and `peak.radonPeak`, assigning the same
  nested `peak.time` to the matching peak-time field. The integration now
  preserves `radonPeak` and `radonPeakTime` instead of discarding them when it
  flattens the nested object. The raw radon value is Bq/m³; the app only converts
  it for display when the account preference selects pCi/L.
- APK operation `104115` writes the XR0A-iR display preferences with
  `stationId`, `stationSn`, `tempUnit`, and `radonUnit`. Operation `104118`
  writes the paired `minRadon` and `maxRadon` thresholds. The integration now
  exposes those settings only when the required station identity is available.
- The APK obtains `day1Value`, `day7Value`, `day30Value`, `day90Value`,
  `longTermValue`, and `longTermDay` from the separate `104026` chart request.
  They are not ordinary device-list or shadow fields and are therefore not
  represented as static Home Assistant sensors without implementing that chart
  query and aggregation path.
- Station and child records returned by account/device APIs must be copied into
  each entity's data store. Preserving only identity fields loses server-backed
  settings such as XR0A-iR units and thresholds before any shadow update.
- `Sma0aSettingActivity` exposes `reportInterval` as an 11-value mailbox picker
  (2, 5, 10, 15, 30, 60, 120, 240, 360, 480, or 720 minutes) and writes it as
  `infoDev` through `2nd_cfg_{deviceSn}`. The mailbox main-page path also reports
  `scheduleStatus`; both entities remain payload-gated.
- `Sma0aSettingActivity` and `SBS50MailboxSettingActivity` both toggle
  `mailNotice` through `MailboxDesiredBean`; Home Assistant exposes this as a
  mailbox-only writable switch and removes the former read-only binary sensor.
- `WifiCoSmokePeakDesiredBean` and `TempHumidityClearLogDesiredBean` remain
  unused transport classes in APK 1400: no current activity or presenter calls
  them, so they are not exposed as invented reset/delete buttons.
- The APK SOS path is model-specific: SBS10 sends `sosStatus` to `sosdown`,
  while SBS50 sends `sosType` through its second-generation path. The existing
  client helper only implements the latter shape, so no generic SOS entity is
  exposed until both model routes are represented and guarded independently.

## APK 1400 entity naming policy

Entity IDs and unique IDs remain stable. Display names follow this order:

1. Use the exact APK English UI string when APK 1400 provides one.
2. Use Home Assistant's standard device-class name for standard measurements
   such as temperature, humidity, battery, and carbon monoxide concentration.
3. For payload-backed diagnostic fields that APK 1400 parses but never labels
   on a screen, use a readable form of the APK transport field and keep the
   entity diagnostic. Do not describe that wording as an APK UI label.

Verified APK resource labels used by the integration include:

| Integration concept | APK resource | APK 1400 text |
| --- | --- | --- |
| End-of-life state | `text_end_life` | `End-of-Life` |
| Normal aggregate state | `text_normal` | `Normal` |
| Silenced state | `item_smoke_silencing` | `Device Silenced` |
| Alarm drill | `text_alarm_drill` | `Alarm Drill` |
| Device test | `item_check_self` / `item_smoke_check_self` | `Device Test` |
| CO reading | `text_co_value` | `CO Reading` |
| CO level | `text_co_level` | `CO Level` |
| Peak CO level | `text_co_peak` | `Peak CO Level` |
| Wi-Fi firmware | `item_wifi_firmware_version` | `Wi-Fi Module Firmware Version` |
| IP address | `item_ip_address` | `IP Address` |
| LED control | `item_led_light` | `LED Indicator` |
| LED level | `item_led_settings` | `LED Brightness` |
| Mounting state | `history_title_mounting_bracket_removed` | `Mounting Bracket Removed` |
| Water alarm | `title_leak_water_alarm` | `Water Leak Alarm` |
| Temperature alarm | `text_temp_alarm` | `Temperature Alarm` |
| Device time zone | `tips_bs_timezone` | `Device Time Zone` |
| Data interval | `text_reporting_frequency` | `Data Reporting Interval` |
| Sensor sensitivity | `item_sensitivity` | `Sensor Sensitivity` |
| Detection sensitivity | `detection_sensitivity` | `Detection Sensitivity` |
| Automatic light duration | `text_light_on_time` | `Automatic Light Duration` |
| Temperature range | `text_temp_range` | `Temperature Range` |
| Relative humidity range | `text_humidity_range` | `Relative Humidity Range` |
| Comfort settings | `text_customized_comfort` | `Customize Comfort Levels` |
| Temperature calibration | `text_settings_temp_calibration` | `Temperature calibration settings...` |
| Humidity calibration | `text_settings_humidity_calibration` | `Relative humidity calibration settings...` |
| Radon lower threshold | `title_radon_threshold_min` | `Green Line Threshold` |
| Radon upper threshold | `title_radon_threshold_max` | `Red Line Threshold` |
| Camera wake action | `camera_wake_up` | `Wake up` |
| Camera sleep setting | `sleep_plan` | `Sleep mode` |
| Camera motion detection | `motion_detection` | `Motion Detection` |
| Camera person detection | `detection_pedestrian` | `Person Detection` |
| Camera recording resolution | `video_resolution` | `Recording Resolution` |
| Camera image rotation | `rotate_image` | `Rotate image` |
| Camera anti-flicker setting | `anti_flicker` | `Anti-Flicker` |
| Camera flicker frequency | `flicker_rate` | `Flicker Frequency` |
| Camera motion tracking | `motion_tracking` | `Motion Tracking` |
| Camera mechanical chime | `mechanical_chime_switch` | `Mechanical Chime` |
| Camera alarm duration | `title_alarm_duration` | `Alarm Duration` |

The remaining transport-only diagnostic labels include camera status codes,
firmware status, thumbnail/dormancy timestamps, `smokeEdition`, `checkType`,
`alarmOccur`, `alarmSource`, `reAlarm`, raw report times, and reported device
type/category fields. APK 1400 parses these values but does not provide a
corresponding user-facing label, so they remain clearly diagnostic rather than
being presented as official APK controls.
