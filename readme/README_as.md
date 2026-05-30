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
- X-Sense account-ত উপলব্ধ থাকিলে base station, smoke detector, carbon monoxide detector, heat alarm, water leak detector, thermo-hygrometer, door sensor, motion sensor, light, keypad, mailbox sensor আৰু listener device সমৰ্থন কৰে।
- X-Sense MQTT shadow-ৰ জৰিয়তে real-time update, আৰু backup হিচাপে periodic cloud polling।
- HACS-ৰ জৰিয়তে সহজ installation।

## প্ৰয়োজনীয়তা
- চলি থকা Home Assistant server।
- supported device থকা X-Sense account।
- Home Assistant-ত HACS install কৰা থাকিব লাগিব।

## প্ৰস্তুতি
- **Home Assistant-ৰ বাবে দ্বিতীয় X-Sense account সৃষ্টি কৰক**: একে account app আৰু Home Assistant-ত একেলগে স্থিৰভাৱে login হৈ নাথাকিব পাৰে, সেয়ে পৃথক account ব্যৱহাৰ কৰাটো ভাল।
- **মূল account-ৰ পৰা Home Assistant account-লৈ supported device share কৰক**: device administration মূল account-ত ৰাখক আৰু Home Assistant-লৈ কেৱল প্ৰয়োজনীয় device share কৰক।

## Installation আৰু configuration
1. Home Assistant-ত HACS খুলক।
2. `https://github.com/Jarnsen/ha-xsense-component_test` custom repository হিচাপে যোগ কৰক।
3. integration download আৰু install কৰক।
4. Home Assistant Integrations পৃষ্ঠাত X-Sense username আৰু password দি setup সম্পূৰ্ণ কৰক।

## Supported devices
কোন entity সৃষ্টি হ'ব সেয়া X-Sense cloud বা MQTT shadow-এ report কৰা field-ৰ ওপৰত নিৰ্ভৰ কৰে। সাধাৰণ device-ৰ ভিতৰত SBS50 base station, XS/SC/XP/XC smoke আৰু CO device, XH heat alarm, SWS water detector, STH thermo-hygrometer, SDS door sensor, SMS motion sensor, light, keypad, mailbox, driveway alarm আৰু supported field report কৰা অন্য device থাকে।

## Entity আৰু action
- alarm, mute, end-of-life, AC break, water alarm, temperature alarm, charging, motion, door, armed, reminder, light আৰু diagnostic binary sensor।
- battery, RF signal, Wi-Fi signal, firmware, temperature, humidity, CO, volume, readable timestamp, serial number, MAC address আৰু অন্য diagnostic sensor।
- device-এ support কৰিলে LED light, alarm, reminders, PIR, sunshine, await আৰু keypad sound control-ৰ switch।
- supported model-ৰ বাবে test, mute আৰু fire drill button।

## Automation উদাহৰণ
```yaml
automation:
  - alias: "X-Sense Water Leak Alarm"
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
