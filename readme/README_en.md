# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Overview
This integration for Home Assistant allows the use of X-Sense devices within a smart home system. It was created based on the original code by [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) and is published with his permission and collaboration.

This HACS integration is actively maintained for users who want broader X-Sense device support in Home Assistant. It is regularly updated with new functionality, device coverage, and fixes for reported issues.

<p align="center">
 <img src="https://github.com/user-attachments/assets/fbe7e69b-9204-4de4-a245-e0e2bdbd7f73" alt="Image">
</p>

## Features
- Integration of various X-Sense devices into Home Assistant.
- Support for automations based on X-Sense sensor data.
- Support for the following device types: base stations, smoke detectors, carbon monoxide detectors, heat alarms, water leak detectors, hygrometers, door sensors, motion sensors, lights, keypads, mailbox sensors, audio monitoring devices, and supported cameras when they are available in the X-Sense account.
- Real-time updates through X-Sense MQTT shadows, with periodic cloud polling as a fallback.
- Supported cameras expose AI notification detections as Home Assistant event entities, and keep last-detection sensors for recent person, pet, vehicle, package, and other detection history when those events are reported.
- Easy setup through HACS (Home Assistant Community Store).

## Requirements
- A functional Home Assistant server (latest version recommended).
- An X-Sense account with supported devices.
- HACS must be installed in Home Assistant to enable integration installation.

## How-to Video
For a detailed guide on installation and configuration of the integration, you can watch the following video:

[![X-Sense Home Assistant Integration](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## Preparation
Before installing the integration, some preparations are necessary:

- **Create a second account in the X-Sense app (for use with Home Assistant)**: Since it is not possible to be logged into the app and Home Assistant with the same account simultaneously, we recommend using a separate account for Home Assistant. This prevents you from constantly being logged out of either the app or Home Assistant. The additional account allows for seamless integration and usage without disruptions caused by repeated logins.

- **Share the supported devices from the main account with the Home Assistant account**: Use the X-Sense app to share **only the supported devices** with the newly created account. This way, the integration can be used easily in Home Assistant while administration continues through the main account.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## Installation via HACS
1. **Open HACS in Home Assistant**:
  HACS is an important extension for Home Assistant that allows you to easily install custom integrations.

  ![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **Go to custom repositories**:
  Navigate to settings in the HACS dashboard and add the repository as a custom source.

3. **Add the repository**:
  Enter the repository URL: `https://github.com/Jarnsen/ha-xsense-component_test`

  ![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **Download and install the integration**:
  Find the integration in HACS, download it, and install it. After installation, configuration can be done through the Home Assistant interface.

  ![HACS repository selection screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)

  ![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## Configuration
After installation, basic configuration is required to properly set up the integration:
- **Username and password**: Use the credentials of the newly created X-Sense account to establish the connection.

  ![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

- **Device overview**: After successful configuration, the shared devices will be available in Home Assistant and can be used for automations.

  ![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)
## View in Home Assistant
After successful installation and configuration, the integration will be visible in Home Assistant. The devices will be available on the dashboard and can be used for automations, notifications, and other applications.


![Forum](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/2d271b78-39d9-4bbd-837d-8593cf1933bd)

____________________________________________________________

## Supported Devices
This integration supports a variety of X-Sense devices. Supported entities depend on the data fields reported by each device and account. Here is a list of currently supported device families and confirmed models:
- **Base station (SBS50)**: Central hub for X-Sense devices.
- **Heat alarm (XH02-M)**: Detects unusually high temperatures.
- **Carbon monoxide detector (XC01-M; XC04-WX)**: Detects dangerous concentrations of carbon monoxide.
- **Smoke detector (XS01-M; XS01-WX; XS03-WX; XS0B-MR and related RF/iR models)**: Early detection of smoke.
- **Carbon monoxide and smoke combination detector (SC07-WX; XP0A-MR and related XP/SC models)**: Combined devices for detecting carbon monoxide and smoke.
- **Water leak detector (SWS51)**: Detects the presence of water in unwanted areas.
- **Hygrometer-thermometer (STH51, STH0A, STH0B, STH0C)**: Monitors temperature and humidity.
- **Door sensor (SDS0A)**: Exposes door state when provided by the X-Sense account.
- **Motion detector (SMS0A)**: Exposes motion alarm state when provided by the X-Sense account.
- **Camera (SSC0A, SSC0B)**: Exposes camera entities, thumbnails, live stream URLs, status diagnostics, and Android-app-backed settings when supported by the device and account.
- **Other station-connected devices**: Light, keypad, mailbox, audio monitoring device, driveway alarm, smart delivery device, remote, and radon device data is exposed when the X-Sense API reports supported fields.

These devices can be used to create automations and alerts after being integrated into Home Assistant.

### Available Entities and Actions
The integration creates Home Assistant entities only for fields that are present in the X-Sense cloud, MQTT shadow payloads, or Android-app-aligned camera APIs. Depending on the device, this can include:

- Alarm, mute, end-of-life, AC-break, water-alarm, temperature-alarm, charging, motion, door, armed, warning, reminder, light, PIR, and keypad status binary sensors.
- Battery, RF signal, Wi-Fi signal, firmware, temperature, humidity, CO level, CO peak, alarm volume, voice volume, chirp volume, reminder volume, warning thresholds, mute timers, readable timestamp fields, timezone, and other diagnostic sensors.
- Switches for supported writable settings reported by X-Sense, such as LED light, alarm enablement, continued alarm, chirp tone, reminders, PIR, sunshine, await, keypad sound, camera motion detection, recording, night vision, audio, cooldown, light, and doorbell controls.
- Selects and numbers for supported camera settings such as language, recording resolution, codec, anti-flicker rate, motion sensitivity, video length, volume, alarm duration, cooldown, night threshold, and doorbell ring key.
- Test, mute, fire-drill, and camera wake buttons for device models where the X-Sense app exposes the matching action.

Some entities are diagnostic or configuration-related and are grouped that way in Home Assistant. If a device does not report a specific field, or the X-Sense app marks the feature unsupported for that device/account, the matching entity is not created. Device binding, removal, sharing, account, payment, firmware update, SD-card format, and other management actions remain in the X-Sense app.

____________________________________________________________

## Camera AI Notifications
Supported cameras create an `AI Detection` event entity, such as `event.front_camera_ai_detection`. Use this `event.*` entity for notification automations, and replace the sample entity ID with the actual entity ID shown in your Home Assistant instance.

AI detections are one-time events, not on/off states. Trigger on them with Home Assistant's `event.received` trigger and filter by `event_type`. Supported event types include `person`, `pet`, `vehicle`, `vehicle_enter`, `vehicle_out`, `vehicle_held_up`, `package`, `package_drop_off`, `package_pick_up`, `package_exist`, `other`, and `ai_detection`. The `ai_detection` event type is used when one camera notification contains more than one detected object.

Example automation:

```yaml
alias: "Notify when X-Sense detects a person"
triggers:
  - trigger: event.received
    target:
      entity_id: event.front_camera_ai_detection
    options:
      event_type:
        - person
actions:
  - action: notify.mobile_app_phone
    data:
      message: "X-Sense camera detected a person."
```

Use the `Last AI Detection` sensor and related last-detection timestamp sensors only for last-known history, dashboards, or conditions. These sensors can be unknown until the first notification arrives and are not the main notification trigger.
____________________________________________________________
## Automation Examples
With this integration, various automations can be created. Here are some examples:

### Example 1: Temperature Alert
When the temperature from an X-Sense thermometer is too high, a notification is sent:

```yaml
automation:
  - alias: "X-Sense Temperature Alert"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "The temperature exceeds 30 degrees!"
```

### Example 2: Water Leak Alarm
When the water leak detector detects water, an alert is triggered:

```yaml
automation:
  - alias: "Water Leak Alarm"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "Water leak detected!"
```

____________________________________________________________

## We Need Your Help
We are always looking for support to continue developing and improving this integration. Here are some ways you can help:

1. **Testing devices**: If you own an X-Sense device that works with the integration, let us know so we can add it to the list of supported devices.

2. **Feedback on unsupported devices**: If a device does not work, provide us with feedback so we can offer support or include the device in future versions of the integration.

3. **Sharing devices for testing**: The best way to test new devices is to share them via the X-Sense app. This way, we can ensure that as many devices as possible are supported.

4. **Community support**: Participate in discussions in our community. Whether you have suggestions for improvements or help other users with their setup – every bit of help is welcome!

For discussions and support, you can join our Discord server or visit the Home Assistant forum:

[Discord](https://discord.gg/5phHHgGb3V)

[Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

## Complete Reference

### Account and installation
- Use a separate X-Sense account for Home Assistant.
- Share only supported devices from the main X-Sense account.
- Pairing, removal, sharing, firmware, account, payment, and SD-card management remain in the X-Sense app.

### Updates and API usage
- Fast state changes are received through MQTT shadow messages.
- Cloud requests are used for login, device discovery, camera data, and state recovery.
- Periodic polling is only a fallback when a live update is missed.

### Entities, cameras, and troubleshooting
- Entities are created only for fields that X-Sense actually reports.
- Camera entities and controls are created only when the Android-app-aligned API reports support for that account and model.
- If a value is missing, first compare it with the X-Sense app, then include diagnostics and relevant Home Assistant logs in a report.

## Device and Entity Checklist

### Main device families
- SBS50 base station, XS smoke alarms, XC carbon monoxide alarms, SC/XP combination alarms, XH heat alarms, SWS water leak sensors, STH temperature/humidity sensors, SDS door sensors, SMS motion sensors, SSC cameras, and other reported X-Sense families are handled when the API exposes their fields.

### Status fields
- Alarm, mute, battery, RF/Wi-Fi signal, temperature, humidity, CO, water, motion, door, light, reminder, warning, and readable timestamp fields appear only when reported by X-Sense.

### Controls and reporting
- Switches, selects, numbers, and buttons are created only for writable settings and actions that the device/account exposes.
- Good bug reports include the exact model, integration version, diagnostics, logs, and whether the value changes correctly in the X-Sense app.
