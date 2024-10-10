# ha-xsense-component_test

## Overview
This integration for Home Assistant allows the use of X-Sense devices within a smart home system. It was created based on the original code by [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) and is published with his permission and collaboration.

Until an official Home Assistant integration from Theo becomes available, this HACS integration will be used and regularly updated to add new functionalities and resolve existing issues. This integration allows users to easily integrate their X-Sense devices into Home Assistant and use them for various automations and monitoring.

![images](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/c49a97f2-5e10-4129-82bc-1d647adc0895)

## Features
- Integration of various X-Sense devices into Home Assistant.
- Support for automations based on X-Sense sensor data.
- Support for the following device types: base stations, smoke detectors, carbon monoxide detectors, heat alarms, water leak detectors, and hygrometers.
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

![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## Installation via HACS
1. **Open HACS in Home Assistant**:
   HACS is an important extension for Home Assistant that allows you to easily install custom integrations.

   ![Download (1)](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **Go to custom repositories**:
   Navigate to settings in the HACS dashboard and add the repository as a custom source.

3. **Add the repository**:
   Enter the repository URL: `https://github.com/Jarnsen/ha-xsense-component_test`

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **Download and install the integration**:
   Find the integration in HACS, download it, and install it. After installation, configuration can be done through the Home Assistant interface.

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)
   
   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## Configuration
After installation, basic configuration is required to properly set up the integration:
- **Username and password**: Use the credentials of the newly created X-Sense account to establish the connection.

    ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)
  
- **Device overview**: After successful configuration, the shared devices will be available in Home Assistant and can be used for automations.

    ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)
## View in Home Assistant
After successful installation and configuration, the integration will be visible in Home Assistant. The devices will be available on the dashboard and can be used for automations, notifications, and other applications.


![Forum](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/2d271b78-39d9-4bbd-837d-8593cf1933bd)

____________________________________________________________

## Supported Devices
This integration supports a variety of X-Sense devices. Here is a list of the currently confirmed and tested devices:
- **Base station (SBS50)**: Central hub for X-Sense devices.
- **Heat alarm (XH02-M)**: Detects unusually high temperatures.
- **Carbon monoxide detector (XC01-M; XC04-WX)**: Detects dangerous concentrations of carbon monoxide.
- **Smoke detector (XS01-M, WX; XS03-WX; XS0B-MR)**: Early detection of smoke.
- **Carbon monoxide and smoke combination detector (SC07-WX; XP0A-MR (partially supported))**: Combined devices for detecting carbon monoxide and smoke.
- **Water leak detector (SWS51)**: Detects the presence of water in unwanted areas.
- **Hygrometer-thermometer (STH51)**: Monitors temperature and humidity.

These devices can be used to create automations and alerts after being integrated into Home Assistant.

____________________________________________________________

## Automation Examples
With this integration, various automations can be created. Here are some examples:

### Example 1: Temperature Alert
When the temperature from an X-Sense thermometer is too high, a notification is sent:

```yaml
automation:
  - alias: "Xsense Temperature Alert"
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
