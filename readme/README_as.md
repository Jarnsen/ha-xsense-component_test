# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## সামগ্ৰিক বিৱৰণ
এই Home Assistant একীকৰণ-এ X-Sense ডিভাইচ সমূহক স্মাৰ্ট-হোম ব্যৱস্থা-ত ব্যৱহাৰ কৰিবলৈ সহায় কৰে। ই [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense)-ৰ মূল code-ৰ ওপৰত আধাৰিত আৰু তেওঁৰ অনুমতি আৰু সহযোগিতাৰে প্ৰকাশ কৰা হৈছে।

Home Assistant-ৰ আনুষ্ঠানিক একীকৰণ উপলব্ধ নোহোৱা পৰ্যন্ত, এই HACS integration-টো নতুন সুবিধা যোগ কৰা আৰু সমস্যা সমাধানৰ বাবে আপডেট হৈ থাকিব।

## বৈশিষ্ট্য
- বিভিন্ন X-Sense ডিভাইচ Home Assistant-ত যোগ কৰে।
- X-Sense চেন্সৰৰ তথ্য-ৰ ওপৰত automation সমৰ্থন কৰে।
- X-Sense একাউণ্ট-ত উপলব্ধ থাকিলে বেছ ষ্টেচন, ধোঁৱা সতৰ্কক, carbon monoxide detector, তাপ সতৰ্কক, পানী লিক সতৰ্কক, তাপ-আৰ্দ্ৰতা মাপক, দুৱাৰৰ চেন্সৰ, গতি চেন্সৰ, light, keypad, ডাকবাকচ চেন্সৰ, শ্ৰোতা ডিভাইচ, camera আৰু অন্য সমৰ্থিত ডিভাইচ সমৰ্থন কৰে।
- X-Sense MQTT shadow-ৰ জৰিয়তে তাৎক্ষণিক আপডেট, আৰু বিকল্প হিচাপে সীমিত সময়মাফিক ক্লাউড পলিং।
- HACS-ৰ জৰিয়তে সহজ সংস্থাপন।

## প্ৰয়োজনীয়তা
- চলি থকা Home Assistant server।
- সমৰ্থিত ডিভাইচ থকা X-Sense একাউণ্ট।
- Home Assistant-ত HACS সংস্থাপন কৰা থাকিব লাগিব।

## কেনেকৈ কৰিব ভিডিঅ'
একীকৰণ সংস্থাপন আৰু কনফিগাৰ কৰাৰ বিস্তারিত guide-ৰ বাবে এই ভিডিঅ চাব পাৰে:

[![X-Sense Home Assistant Integration](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## প্ৰস্তুতি
- **Home Assistant-ৰ বাবে দ্বিতীয় X-Sense একাউণ্ট সৃষ্টি কৰক**: একে একাউণ্ট app আৰু Home Assistant-ত একেলগে স্থিৰভাৱে লগইন হৈ নাথাকিব পাৰে, সেয়ে পৃথক একাউণ্ট ব্যৱহাৰ কৰাটো ভাল।
- **মূল একাউণ্ট-ৰ পৰা Home Assistant একাউণ্ট-লৈ সমৰ্থিত ডিভাইচ share কৰক**: ডিভাইচ পৰিচালনা মূল একাউণ্ট-ত ৰাখক আৰু Home Assistant-লৈ কেৱল প্ৰয়োজনীয় device share কৰক।

## HACS-ৰ জৰিয়তে সংস্থাপন
1. **Home Assistant-ত HACS খোলক**:
  HACS হৈছে Home Assistant-ৰ এটা extension, যাৰ সহায়ত custom integration সহজে install কৰিব পাৰি।

2. **কাষ্টম repository-লৈ যাওক**:
  HACS dashboard-ৰ ছেটিংছ-ত repository-টো কাষ্টম উৎস হিচাপে add কৰক।

3. **Repository যোগ কৰক**:
  Repository URL লিখক: `https://github.com/Jarnsen/ha-xsense-component_test`

4. **একীকৰণ ডাউনলোড আৰু সংস্থাপন কৰক**:
  HACS-ত integration বিচাৰি download/install কৰক। Installation-ৰ পিছত Home Assistant interface-ৰ পৰা configure কৰিব পাৰি।

____________________________________________________________

## কনফিগাৰেচন
Installation-ৰ পিছত integration সঠিকভাৱে setup কৰিবলৈ মৌলিক কনফিগাৰেচন লাগে:
- **ব্যৱহাৰকাৰীৰ নাম আৰু password**: নতুনকৈ create কৰা X-Sense একাউণ্ট-ৰ লগইন তথ্য ব্যৱহাৰ কৰক।
- **ডিভাইচৰ সামগ্ৰিক দৃশ্য**: কনফিগাৰেচন সফল হলে ভাগ কৰা ডিভাইচসমূহ Home Assistant-ত উপলব্ধ হ'ব আৰু automation-ত ব্যৱহাৰ কৰিব পাৰিব।

## Home Assistant-ত দৃশ্য
Installation আৰু configuration সফল হলে integration Home Assistant-ত দেখা যাব। ডিভাইচসমূহ dashboard-ত উপলব্ধ হ'ব আৰু automation, জাননী, আৰু অন্য ব্যৱহাৰ-ত ব্যৱহাৰ কৰিব পাৰিব।


## বিতং setup screenshot

1. Home Assistant-ৰ বাবে পৃথক X-Sense একাউণ্ট সৃষ্টি কৰক আৰু মূল একাউণ্টৰ পৰা কেৱল সমৰ্থিত ডিভাইচ share কৰক।

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

2. HACS-ত custom repository হিচাপে `https://github.com/Jarnsen/ha-xsense-component_test` যোগ কৰক।

![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

3. Integration download/install কৰাৰ পিছত Home Assistant restart কৰক, তাৰ পিছত নতুন X-Sense একাউণ্টৰ username/password দিয়ে configure কৰক।

![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

4. Configuration সফল হলে shared devices Home Assistant device page-ত দেখা যাব।

![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)

5. ডিভাইচ pairing, removal, firmware, payment, SD card, আৰু account management X-Sense app-তেই ৰাখক।

## সমৰ্থিত ডিভাইচ
এই integration-এ বিভিন্ন X-Sense ডিভাইচ সমৰ্থন কৰে। কোন এণ্টিটি সৃষ্টি হ'ব সেয়া device আৰু একাউণ্ট-এ report কৰা তথ্য ক্ষেত্ৰ-ৰ ওপৰত নিৰ্ভৰ কৰে। নিশ্চিত device family আৰু model:
- **Base station (SBS50)**: X-Sense ডিভাইচ-ৰ কেন্দ্ৰীয় hub।
- **Heat alarm (XH02-M)**: অস্বাভাৱিক উচ্চ তাপমাত্ৰা ধৰা পেলায়।
- **Carbon monoxide detector (XC01-M; XC04-WX)**: বিপজ্জনক CO ঘনত্ব ধৰা পেলায়।
- **Smoke detector (XS01-M; XS01-WX; XS03-WX; XS0B-MR আৰু related RF/iR models)**: smoke early detection।
- **CO আৰু smoke combination detector (SC07-WX; XP0A-MR আৰু related XP/SC models)**: CO আৰু smoke ধৰা পেলায়।
- **Water leak detector (SWS51)**: অনাকাংক্ষিত স্থানত পানী ধৰা পেলায়।
- **Hygrometer-thermometer (STH51, STH0A, STH0B, STH0C)**: তাপমাত্ৰা আৰু আৰ্দ্ৰতা নিৰীক্ষণ কৰে।
- **Door sensor (SDS0A)** আৰু **গতি চেন্সৰ (SMS0A)**: X-Sense-এ স্থিতি দিলে দেখুওৱা হয়।
- **কেমেৰা (SSC0A, SSC0B)**: ডিভাইচ আৰু একাউণ্টে সমৰ্থন কৰিলে কেমেৰা এণ্টিটি, সৰু পূৰ্বদৃশ্য, live stream URL, নিৰ্ণায়ক তথ্য, আৰু Android app-ৰ সৈতে মিল থকা ছেটিং দেখুওৱা হয়।
- **ষ্টেচনৰ সৈতে সংযুক্ত অন্য ডিভাইচ**: লাইট, কীপেড, ডাকবাকচ, শ্ৰোতা ডিভাইচ, ড্ৰাইভৱে এলাৰ্ম, স্মাৰ্ট ড্ৰপ, ৰিম’ট, আৰু ৰেডন তথ্য API-এ সমৰ্থিত ক্ষেত্ৰ report কৰিলে দেখুওৱা হয়।

### উপলব্ধ এণ্টিটি আৰু কাৰ্য
একীকৰণে কেৱল X-Sense cloud, MQTT shadow payload, বা Android app-aligned camera API-ত সঁচাকৈ থকা ক্ষেত্ৰৰ বাবে Home Assistant এণ্টিটি সৃষ্টি কৰে। ডিভাইচ অনুসৰি ইয়াত থাকিব পাৰে:

- এলাৰ্ম, mute, end-of-life, AC-break, water alarm, তাপমাত্ৰা এলাৰ্ম, charging, motion, door, armed, warning, reminder, light, PIR, আৰু keypad status-ৰ binary sensor।
- বেটাৰী, RF সংকেত, Wi-Fi সংকেত, ফাৰ্মৱেৰ, তাপমাত্ৰা, আৰ্দ্ৰতা, CO স্তৰ, CO সৰ্বোচ্চ মান, এলাৰ্মৰ volume, কণ্ঠস্বৰৰ ভলিউম, চাৰ্প ভলিউম, সোঁৱৰাই দিয়াৰ ভলিউম, সতৰ্কতাৰ সীমা, নীৰৱ কৰাৰ টাইমাৰ, পঢ়িব পৰা সময়চিহ্ন, সময় মণ্ডল, আৰু অন্য diagnostic চেন্সৰ।
- Supported camera setup and tuning controls are exposed in Home Assistant when the X-Sense app reports that the feature and account support it.
- যি মডেলত X-Sense app-এ মিল থকা কাৰ্য দিয়ে, সেইবোৰৰ বাবে test, mute, fire-drill, আৰু camera wake button।

কিছুমান এণ্টিটি diagnostic বা configuration-সম্পৰ্কীয় আৰু Home Assistant-ত তেনেকৈ group কৰা হয়। ডিভাইচে কোনো ক্ষেত্ৰ report নকৰিলে, বা X-Sense app-এ সেই ডিভাইচ/একাউণ্টৰ বাবে সুবিধা সমৰ্থিত নহয় বুলি দেখুৱালে, সংশ্লিষ্ট এণ্টিটি সৃষ্টি নহয়। ডিভাইচ জোৰা লগোৱা, আঁতৰোৱা, ভাগ-বতৰা কৰা, একাউণ্ট, payment, ফাৰ্মৱেৰ আপডেট, SD-card format, আৰু অন্য পৰিচালনামূলক কাৰ্য X-Sense app-তেই থাকে।
____________________________________________________________

## অটোমেশনৰ উদাহৰণ
এই integration-ৰ সহায়ত বিভিন্ন automation সৃষ্টি কৰিব পাৰি। কেইটামান উদাহৰণ:

### উদাহৰণ 1: তাপমাত্ৰাৰ সতৰ্কবাণী
X-Sense thermometer-ৰ তাপমাত্ৰা বেছি হলে জাননী পঠিওৱা হয়:

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
        message: "তাপমাত্ৰা ৩০ ডিগ্ৰীতকৈ বেছি!"
```

### উদাহৰণ 2: পানী লিক হোৱাৰ এলাৰ্ম
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
        message: "পানী লিক হোৱা ধৰা পৰিছে!"
```

## আপোনাৰ সহায় প্ৰয়োজন
আপোনাৰ ওচৰত যদি এতিয়াও পৰীক্ষা নোহোৱা X-Sense ডিভাইচ আছে, GitHub, Discord বা Home Assistant forum-ত মতামত দিয়ক।

## সম্পূৰ্ণ ৰেফাৰেন্স

### একাউণ্ট আৰু সংস্থাপন
- Home Assistant-ৰ বাবে পৃথক X-Sense একাউণ্ট ব্যৱহাৰ কৰক।
- মূল একাউণ্টৰ পৰা কেৱল সমৰ্থিত ডিভাইচ ভাগ কৰক।
- ডিভাইচ যোগ, আঁতৰোৱা, ভাগ কৰা, firmware আৰু payment X-Sense app-তেই থাকে।
- App আৰু Home Assistant-এ ইজনে সিজনক logout কৰিলে একেটা একাউণ্ট ব্যৱহাৰ কৰা হৈছে নেকি চাওক।

### আপডেট আৰু API ব্যৱহাৰ
- দ্ৰুত state change MQTT shadow message-ৰ পৰা আহে।
- Cloud request login, device load, আৰু state refresh-ৰ বাবে সীমিতভাৱে ব্যৱহাৰ কৰা হয়।
- MQTT message নাহিলে periodic polling backup হিচাপে থাকে।
- Full device discovery প্ৰতিটো update-ত কৰা উচিত নহয়।

### এণ্টিটি, কেমেৰা, আৰু সমস্যা সমাধান
- X-Sense-এ সঁচাকৈ জনোৱা ক্ষেত্ৰ থাকিলেহে এণ্টিটি সৃষ্টি হয়।
- নিৰ্ণায়ক মানসমূহ Home Assistant-ত নিৰ্ণায়ক হিচাপে গোট কৰা হয়।
- কেমেৰা সমৰ্থিত হ’লে কেমেৰা এণ্টিটি, সৰু পূৰ্বদৃশ্য, live stream, স্থিতি, আৰু সমৰ্থিত ছেটিং দেখুওৱা হয়।
- সমস্যা জনাওঁতে মডেল, একীকৰণৰ সংস্কৰণ, নিৰ্ণায়ক তথ্য, লগ, আৰু app-ত মান সলনি হয় নে নহয় উল্লেখ কৰক।

## ডিভাইচ আৰু এণ্টিটি পৰীক্ষা-তালিকা

### মূল ডিভাইচ পৰিয়াল
- SBS50: বেছ ষ্টেচন আৰু ষ্টেচন-স্তৰৰ স্থিতি।
- XS01-WX: Wi-Fi ধোঁৱা সতৰ্কক, কেৱল-ষ্টেচন থকা একাউণ্টসহ।
- XS01-M, XS03-WX, XS0B-MR: ধোঁৱা সতৰ্কক পৰিয়াল।
- XC01-M, XC04-WX: CO alarm পৰিয়াল.
- SC07-WX, XP0A-MR: smoke আৰু CO combination পৰিয়াল.
- XH02-M: তাপ সতৰ্কক পৰিয়াল।
- SWS51: পানী লিক ধৰা পেলোৱা ডিভাইচৰ পৰিয়াল।
- STH51, STH0A, STH0B, STH0C: temperature আৰু humidity পৰিয়াল.
- SDS0A: দুৱাৰৰ চেন্সৰ পৰিয়াল।
- SMS0A: গতি চেন্সৰ পৰিয়াল।
- SSC0A, SSC0B: সমৰ্থিত কেমেৰা পৰিয়াল।

### স্থিতিৰ ক্ষেত্ৰ
- X-Sense-এ এলাৰ্ম ক্ষেত্ৰ দিলে এলাৰ্মৰ স্থিতি দেখুওৱা হয়।
- মিউট ক্ষেত্ৰ দিলে মিউটৰ স্থিতি দেখুওৱা হয়।
- বেটাৰীৰ তথ্য দিলে বেটাৰীৰ স্থিতি দেখুওৱা হয়।
- RF আৰু Wi-Fi সংকেত device-এ report কৰিলে দেখুওৱা হয়.
- সংক্ষিপ্ত সময়চিহ্ন Home Assistant-ত পঢ়িব পৰা সময় চেন্সৰ হিচাপে দেখুওৱা হয়।

### নিয়ন্ত্ৰণ আৰু প্ৰতিবেদন
- X-Sense-এ লিখিব পৰা ছেটিং জনালে switch সৃষ্টি হয়।
- app-এ সমৰ্থন কৰা কাৰ্য থাকিলেহে button সৃষ্টি হয়।
- Android-ৰ সৈতে মিল থকা API-এ উপলব্ধ বুলি দিলে কেমেৰা নিয়ন্ত্ৰণ সৃষ্টি হয়।
- সমস্যা জনাওঁতে সঠিক মডেল, একীকৰণৰ সংস্কৰণ, নিৰ্ণায়ক তথ্য, লগ, আৰু app-ত মান সলনি হয় নে নহয় লিখক।

____________________________________________________________

## কেমেৰা লাইভ ভিউ আৰু AI জাননী
সৰ্বাধিক সহজ পদ্ধতি হ’ল তলৰ বুটামেৰে অন্তর্ভুক্ত blueprint import কৰা, `Motion` বা উপলব্ধ `AI Detection` বাছনি কৰা, আৰু প্ৰয়োজন হলে notification action সলনি কৰা।

[![Blueprint import কৰক](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2FJarnsen%2Fha-xsense-component_test%2Fmain%2Fblueprints%2Fautomation%2Fxsense%2Fcamera_ai_notification.yaml)

Motion আৰু AI Detection এককালীন events, on/off states নহয়। Manual automations ৰ বাবে `event.received` ব্যৱহাৰ কৰক; `event_type` কেৱল `person`, `pet`, `vehicle`, `package`, `other` বা `ai_detection` ধৰণৰ type filter কৰিবলৈ লাগে।

Automation উদাহৰণ:

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

____________________________________________________________
