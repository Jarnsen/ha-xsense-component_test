# ha-xsense-component_test

<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## সামগ্ৰিক বিৱৰণ
এই Home Assistant integration-এ X-Sense device সমূহক smart home system-ত ব্যৱহাৰ কৰিবলৈ সহায় কৰে। ই [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense)-ৰ মূল code-ৰ ওপৰত আধাৰিত আৰু তেওঁৰ অনুমতি আৰু সহযোগিতাৰে প্ৰকাশ কৰা হৈছে।

Home Assistant-ৰ official integration উপলব্ধ নোহোৱা পৰ্যন্ত, এই HACS integration-টো নতুন feature যোগ কৰা আৰু সমস্যা সমাধানৰ বাবে update হৈ থাকিব।

## বৈশিষ্ট্য
- বিভিন্ন X-Sense device Home Assistant-ত integrate কৰে।
- X-Sense sensor data-ৰ ওপৰত automation সমৰ্থন কৰে।
- X-Sense account-ত উপলব্ধ থাকিলে base station, smoke detector, carbon monoxide detector, heat alarm, water leak detector, thermo-hygrometer, door sensor, motion sensor, light, keypad, mailbox sensor, listener device, camera আৰু অন্য supported device সমৰ্থন কৰে।
- X-Sense MQTT shadow-ৰ জৰিয়তে real-time update, আৰু backup হিচাপে periodic cloud polling।
- HACS-ৰ জৰিয়তে সহজ installation।

## প্ৰয়োজনীয়তা
- চলি থকা Home Assistant server।
- supported device থকা X-Sense account।
- Home Assistant-ত HACS install কৰা থাকিব লাগিব।

## কেনেকৈ কৰিব ভিডিঅ'
Integration install আৰু configure কৰাৰ বিস্তারিত guide-ৰ বাবে এই video চাব পাৰে:

[![X-Sense Home Assistant Integration](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## প্ৰস্তুতি
- **Home Assistant-ৰ বাবে দ্বিতীয় X-Sense account সৃষ্টি কৰক**: একে account app আৰু Home Assistant-ত একেলগে স্থিৰভাৱে login হৈ নাথাকিব পাৰে, সেয়ে পৃথক account ব্যৱহাৰ কৰাটো ভাল।
- **মূল account-ৰ পৰা Home Assistant account-লৈ supported device share কৰক**: device administration মূল account-ত ৰাখক আৰু Home Assistant-লৈ কেৱল প্ৰয়োজনীয় device share কৰক।

## HACS-ৰ জৰিয়তে installation
1. **Home Assistant-ত HACS খোলক**:
   HACS হৈছে Home Assistant-ৰ এটা extension, যাৰ সহায়ত custom integration সহজে install কৰিব পাৰি।

2. **Custom repositories-লৈ যাওক**:
   HACS dashboard-ৰ settings-ত repository-টো custom source হিচাপে add কৰক।

3. **Repository add কৰক**:
   Repository URL লিখক: `https://github.com/Jarnsen/ha-xsense-component_test`

4. **Integration download আৰু install কৰক**:
   HACS-ত integration বিচাৰি download/install কৰক। Installation-ৰ পিছত Home Assistant interface-ৰ পৰা configure কৰিব পাৰি।

____________________________________________________________

## Configuration
Installation-ৰ পিছত integration সঠিকভাৱে setup কৰিবলৈ basic configuration লাগে:
- **Username আৰু password**: নতুনকৈ create কৰা X-Sense account-ৰ credential ব্যৱহাৰ কৰক।
- **Device overview**: Configuration সফল হলে shared devices Home Assistant-ত উপলব্ধ হ'ব আৰু automation-ত ব্যৱহাৰ কৰিব পাৰিব।

## Home Assistant-ত view
Installation আৰু configuration সফল হলে integration Home Assistant-ত দেখা যাব। Devices dashboard-ত উপলব্ধ হ'ব আৰু automation, notification, আৰু অন্য use case-ত ব্যৱহাৰ কৰিব পাৰিব।

## Supported devices
এই integration-এ বিভিন্ন X-Sense device support কৰে। কোন entity সৃষ্টি হ'ব সেয়া device আৰু account-এ report কৰা data field-ৰ ওপৰত নিৰ্ভৰ কৰে। নিশ্চিত device family আৰু model:
- **Base station (SBS50)**: X-Sense device-ৰ central hub।
- **Heat alarm (XH02-M)**: অস্বাভাৱিক উচ্চ temperature detect কৰে।
- **Carbon monoxide detector (XC01-M; XC04-WX)**: বিপজ্জনক CO concentration detect কৰে।
- **Smoke detector (XS01-M; XS01-WX; XS03-WX; XS0B-MR আৰু related RF/iR models)**: smoke early detection।
- **CO আৰু smoke combination detector (SC07-WX; XP0A-MR আৰু related XP/SC models)**: CO আৰু smoke detect কৰে।
- **Water leak detector (SWS51)**: অনাকাংক্ষিত স্থানত পানী detect কৰে।
- **Hygrometer-thermometer (STH51, STH0A, STH0B, STH0C)**: temperature আৰু humidity monitor কৰে।
- **Door sensor (SDS0A)** আৰু **motion sensor (SMS0A)**: X-Sense-এ status দিলে দেখুওৱা হয়।
- **Camera (SSC0A, SSC0B)**: device আৰু account support কৰিলে camera entity, thumbnail, live stream URL, diagnostic, আৰু Android app-backed setting দেখুওৱা হয়।
- **অন্য station-connected devices**: light, keypad, mailbox, listener, driveway alarm, smart drop, remote, আৰু radon data API-এ supported field report কৰিলে দেখুওৱা হয়।

### উপলব্ধ entity আৰু action
Integration-এ কেৱল X-Sense cloud, MQTT shadow payload, বা Android app-aligned camera API-ত সঁচাকৈ থকা field-ৰ বাবে Home Assistant entity সৃষ্টি কৰে। Device অনুসৰি ইয়াত থাকিব পাৰে:

- Alarm, mute, end-of-life, AC-break, water alarm, temperature alarm, charging, motion, door, armed, warning, reminder, light, PIR, আৰু keypad status-ৰ binary sensor।
- Battery, RF signal, Wi-Fi signal, firmware, temperature, humidity, CO level, CO peak, alarm volume, voice volume, chirp volume, reminder volume, warning threshold, mute timer, readable timestamp, timezone, serial number, MAC address, আৰু অন্য diagnostic sensor।
- X-Sense-এ report কৰা writable setting-ৰ switch, যেনে LED light, alarm enablement, continued alarm, chirp tone, reminder, PIR, sunshine/white light, await, keypad sound, camera motion detection, recording, night vision, audio, cooldown, light, আৰু doorbell control।
- Supported camera setting-ৰ select আৰু number, যেনে language, recording resolution, codec, anti-flicker rate, motion sensitivity, video length, volume, alarm duration, cooldown, night threshold, আৰু doorbell ring key।
- যি model-ত X-Sense app-এ matching action দিয়ে, সেইবোৰৰ বাবে test, mute, fire-drill, আৰু camera wake button।

কিছুমান entity diagnostic বা configuration-related আৰু Home Assistant-ত তেনেকৈ group কৰা হয়। Device-এ কোনো field report নকৰিলে, বা X-Sense app-এ সেই device/account-ৰ বাবে feature unsupported বুলি দেখুৱালে, সংশ্লিষ্ট entity সৃষ্টি নহয়। Device binding, remove, sharing, account, payment, firmware update, SD-card format, আৰু অন্য management action X-Sense app-তেই থাকে।
____________________________________________________________

## Automation উদাহৰণ
এই integration-ৰ সহায়ত বিভিন্ন automation সৃষ্টি কৰিব পাৰি। কেইটামান উদাহৰণ:

### উদাহৰণ 1: Temperature alert
X-Sense thermometer-ৰ temperature বেছি হলে notification পঠিওৱা হয়:

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
        message: "Temperature 30 degrees-তকৈ বেছি!"
```

### উদাহৰণ 2: Water leak alarm
Water leak detector-এ water detect কৰিলে alert trigger হয়:

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

## আপোনাৰ সহায় প্ৰয়োজন
আপোনাৰ ওচৰত যদি এতিয়াও test নোহোৱা X-Sense device আছে, GitHub, Discord বা Home Assistant forum-ত feedback দিয়ক।
