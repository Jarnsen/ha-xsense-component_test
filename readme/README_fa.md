# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## نمای کلی
این یکپارچه‌سازی Home Assistant امکان استفاده از دستگاه‌های X-Sense را در خانه هوشمند فراهم می‌کند. این پروژه بر پایه کد اصلی [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) ساخته شده و با اجازه و همکاری او منتشر شده است.

تا زمانی که یکپارچه‌سازی رسمی Home Assistant آماده شود، این نسخه HACS برای افزودن قابلیت‌ها و رفع مشکلات به‌روزرسانی می‌شود.

## قابلیت‌ها
- افزودن انواع دستگاه‌های X-Sense به Home Assistant.
- پشتیبانی از اتوماسیون بر پایه داده‌های حسگرهای X-Sense.
- پشتیبانی از ایستگاه پایه، هشدار دود، هشدار مونوکسید کربن، هشدار گرما، نشت آب، دما و رطوبت، حسگر در، حسگر حرکت، چراغ، صفحه‌کلید، صندوق پستی و دستگاه شنونده در صورت گزارش شدن توسط حساب X-Sense.
- به‌روزرسانی بلادرنگ از طریق X-Sense MQTT shadow و پرس‌وجوی دوره‌ای ابر به عنوان پشتیبان.
- نصب آسان از طریق HACS.

## پیش‌نیازها
- سرور Home Assistant فعال.
- حساب X-Sense با دستگاه‌های پشتیبانی‌شده.
- نصب بودن HACS در Home Assistant.

## ویدیوی راهنما
برای راهنمای دقیق نصب و پیکربندی این یکپارچه‌سازی می‌توانید ویدیوی زیر را ببینید:

[![X-Sense Home Assistant Integration](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## آماده‌سازی
- **یک حساب دوم X-Sense برای Home Assistant بسازید**: استفاده از حساب جداگانه توصیه می‌شود، زیرا ورود همزمان با یک حساب در برنامه و Home Assistant ممکن است پایدار نباشد.
- **دستگاه‌های پشتیبانی‌شده را از حساب اصلی با حساب Home Assistant به اشتراک بگذارید**: مدیریت دستگاه‌ها در حساب اصلی باقی می‌ماند و Home Assistant فقط به دستگاه‌های اشتراک‌گذاری‌شده دسترسی دارد.

## نصب از طریق HACS
1. **HACS را در Home Assistant باز کنید**:
  HACS افزونه‌ای مهم برای Home Assistant است که نصب یکپارچه‌سازی‌های سفارشی را ساده می‌کند.

2. **به custom repositories بروید**:
  در تنظیمات HACS، این مخزن را به‌عنوان منبع سفارشی اضافه کنید.

3. **مخزن را اضافه کنید**:
  URL مخزن را وارد کنید: `https://github.com/Jarnsen/ha-xsense-component_test`

4. **یکپارچه‌سازی را دانلود و نصب کنید**:
  یکپارچه‌سازی را در HACS پیدا کرده، دانلود و نصب کنید. پس از نصب، پیکربندی از رابط Home Assistant انجام می‌شود.

____________________________________________________________

## پیکربندی
پس از نصب، برای راه‌اندازی درست یکپارچه‌سازی به پیکربندی پایه نیاز است:
- **نام کاربری و رمز عبور**: از اطلاعات ورود حساب X-Sense جدیدی که برای Home Assistant ساخته‌اید استفاده کنید.
- **نمای کلی دستگاه‌ها**: پس از پیکربندی موفق، دستگاه‌های به‌اشتراک‌گذاشته‌شده در Home Assistant در دسترس خواهند بود و می‌توان از آن‌ها در اتوماسیون‌ها استفاده کرد.

## نمایش در Home Assistant
پس از نصب و پیکربندی موفق، یکپارچه‌سازی در Home Assistant دیده می‌شود. دستگاه‌ها در داشبورد در دسترس هستند و می‌توان از آن‌ها برای اتوماسیون، اعلان‌ها و کاربردهای دیگر استفاده کرد.


## راه‌اندازی گام‌به‌گام با تصویر

1. برای Home Assistant یک حساب جداگانه X-Sense بسازید و فقط دستگاه‌های پشتیبانی‌شده را از حساب اصلی به آن اشتراک بگذارید.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

2. در HACS مخزن `https://github.com/Jarnsen/ha-xsense-component_test` را به‌عنوان مخزن سفارشی اضافه کنید.

![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

3. integration را دانلود و نصب کنید، Home Assistant را restart کنید و سپس با حساب X-Sense جدید پیکربندی کنید.

![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

4. پس از راه‌اندازی موفق، دستگاه‌های اشتراک‌گذاری‌شده در صفحه دستگاه‌های Home Assistant دیده می‌شوند.

![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)

5. جفت‌سازی، حذف، firmware، پرداخت‌ها، کارت SD و مدیریت حساب در برنامه X-Sense باقی می‌ماند.

## دستگاه‌های پشتیبانی‌شده
این یکپارچه‌سازی از چندین دستگاه X-Sense پشتیبانی می‌کند. موجودیت‌های موجود به فیلدهایی بستگی دارند که دستگاه و حساب گزارش می‌کنند. خانواده‌ها و مدل‌های تأییدشده شامل موارد زیر هستند:
- **ایستگاه پایه (SBS50)**: هاب مرکزی برای دستگاه‌های X-Sense.
- **هشدار حرارت (XH02-M)**: دماهای غیرعادی بالا را تشخیص می‌دهد.
- **آشکارساز مونوکسید کربن (XC01-M; XC04-WX)**: غلظت خطرناک CO را تشخیص می‌دهد.
- **آشکارساز دود (XS01-M; XS01-WX; XS03-WX; XS0B-MR و مدل‌های RF/iR مرتبط)**: تشخیص زودهنگام دود.
- **آشکارساز ترکیبی CO و دود (SC07-WX; XP0A-MR و مدل‌های XP/SC مرتبط)**: CO و دود را تشخیص می‌دهد.
- **آشکارساز نشت آب (SWS51)**: آب را در محل‌های ناخواسته تشخیص می‌دهد.
- **رطوبت‌سنج-دماسنج (STH51, STH0A, STH0B, STH0C)**: دما و رطوبت را پایش می‌کند.
- **سنسور در (SDS0A)** و **سنسور حرکت (SMS0A)**: وقتی X-Sense وضعیت را ارائه کند نمایش داده می‌شوند.
- **دوربین (SSC0A, SSC0B)**: در صورت پشتیبانی دستگاه و حساب، موجودیت‌های دوربین، تصویر بندانگشتی، URL پخش زنده، تشخیص‌ها و تنظیمات مبتنی بر رفتار اپ Android را ارائه می‌کند.
- **سایر دستگاه‌های متصل به ایستگاه**: چراغ، کی‌پد، صندوق پستی، دستگاه شنونده، هشدار مسیر، دستگاه دریافت هوشمند، ریموت و داده‌های رادون وقتی API فیلدهای پشتیبانی‌شده را گزارش کند نمایش داده می‌شوند.

### موجودیت‌ها و عملکردهای موجود
این یکپارچه‌سازی فقط برای فیلدهایی موجودیت‌های Home Assistant می‌سازد که واقعاً در ابر X-Sense، payloadهای MQTT shadow یا APIهای دوربین همسو با اپ Android وجود داشته باشند. بسته به دستگاه، این موارد می‌تواند شامل شود:

- سنسورهای دودویی برای هشدار، بی‌صدا، پایان عمر، قطع برق AC، هشدار آب، هشدار دما، شارژ، حرکت، در، حالت مسلح، هشدار، یادآور، چراغ، PIR و وضعیت کی‌پد.
- سنسورهای باتری، سیگنال RF، سیگنال Wi-Fi، فریمور، دما، رطوبت، سطح CO، اوج CO، حجم صدای هشدار، حجم صدا، حجم چرپ، حجم یادآور، آستانه‌های هشدار، تایمرهای بی‌صدا، زمان‌های خوانا، منطقه زمانی و داده‌های تشخیصی دیگر.
- سوییچ‌ها برای تنظیمات قابل‌نوشتن که X-Sense گزارش می‌کند، مانند چراغ LED، فعال‌سازی هشدار، هشدار پیوسته، صدای chirp، یادآورها، PIR، sunshine/white light، await، صدای کی‌پد، تشخیص حرکت دوربین، ضبط، دید در شب، صدا، cooldown، چراغ و کنترل‌های زنگ در.
- select و number برای تنظیمات پشتیبانی‌شده دوربین مانند زبان، وضوح ضبط، codec، نرخ anti-flicker، حساسیت حرکت، طول ویدیو، volume، مدت هشدار، cooldown، آستانه شب و کلید زنگ زنگ در.
- دکمه‌های تست، بی‌صدا کردن، تمرین آتش‌سوزی و بیدار کردن دوربین برای مدل‌هایی که اپ X-Sense همان عملکرد را ارائه می‌کند.

برخی موجودیت‌ها تشخیصی یا مربوط به پیکربندی هستند و در Home Assistant به همین شکل گروه‌بندی می‌شوند. اگر دستگاه فیلد خاصی را گزارش نکند، یا اپ X-Sense آن قابلیت را برای دستگاه/حساب پشتیبانی‌نشده بداند، موجودیت مربوط ساخته نمی‌شود. اتصال، حذف، اشتراک‌گذاری، حساب، پرداخت، به‌روزرسانی فریمور، فرمت کارت SD و سایر کارهای مدیریتی در اپ X-Sense باقی می‌مانند.
____________________________________________________________

## نمونه‌های خودکارسازی
با این یکپارچه‌سازی می‌توان اتوماسیون‌های مختلفی ساخت. چند نمونه:

### نمونه ۱: هشدار دما
وقتی دمای دماسنج X-Sense بیش از حد بالا باشد، اعلان ارسال می‌شود:

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
        message: "دما از ۳۰ درجه بیشتر شده است!"
```

### نمونه ۲: هشدار نشت آب
وقتی آشکارساز نشت آب وجود آب را تشخیص دهد، هشدار فعال می‌شود:

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
        message: "نشت آب تشخیص داده شد!"
```

## به کمک شما نیاز داریم
اگر دستگاه X-Sense تست‌نشده‌ای دارید، لطفاً بازخورد خود را در GitHub، Discord یا انجمن Home Assistant ارسال کنید.

## مرجع کامل

### حساب و نصب
- برای Home Assistant از یک حساب جداگانه X-Sense استفاده کنید.
- از حساب اصلی فقط دستگاه‌های پشتیبانی‌شده را به اشتراک بگذارید.
- افزودن، حذف، اشتراک‌گذاری، پرداخت، firmware و مدیریت حساب در برنامه X-Sense باقی می‌ماند.
- اگر برنامه و Home Assistant یکدیگر را از حساب خارج می‌کنند، احتمالاً از یک حساب مشترک استفاده می‌کنند.

### به‌روزرسانی و استفاده از API
- تغییرات سریع وضعیت از پیام‌های MQTT shadow دریافت می‌شوند.
- درخواست‌های ابری فقط برای ورود، بارگذاری دستگاه و تازه‌سازی وضعیت استفاده می‌شوند.
- polling دوره‌ای فقط زمانی نقش پشتیبان دارد که پیام MQTT نرسد.
- کشف کامل دستگاه‌ها نباید در هر چرخه به‌روزرسانی تکرار شود.

### موجودیت‌ها، دوربین و عیب‌یابی
- موجودیت فقط زمانی ساخته می‌شود که X-Sense آن فیلد را گزارش کند.
- مقدارهای diagnostic در Home Assistant به عنوان diagnostic گروه‌بندی می‌شوند.
- دوربین‌های پشتیبانی‌شده می‌توانند موجودیت دوربین، تصویر بندانگشتی، پخش زنده، وضعیت و تنظیمات پشتیبانی‌شده داشته باشند.
- اگر مسیر WebRTC در Home Assistant موجود باشد، می‌تواند برای live view استفاده شود.
- هنگام گزارش مشکل، مدل، نسخه یکپارچه‌سازی، داده‌های عیب‌یابی، گزارش‌ها و تغییر کردن یا نکردن مقدار در برنامه را ذکر کنید.

## فهرست دستگاه‌ها و موجودیت‌ها

### خانواده‌های اصلی دستگاه
- SBS50: ایستگاه پایه و وضعیت سطح ایستگاه.
- XS01-WX: هشدار دود Wi-Fi، از جمله حساب‌هایی که دستگاه فرعی جداگانه ندارند.
- XS01-M، XS03-WX، XS0B-MR: خانواده‌های هشدار دود.
- XC01-M، XC04-WX: خانواده‌های هشدار CO.
- SC07-WX، XP0A-MR: خانواده‌های ترکیبی دود و CO.
- XH02-M: خانواده هشدار حرارت.
- SWS51: خانواده آشکارساز نشت آب.
- STH51، STH0A، STH0B، STH0C: دما و رطوبت.
- SDS0A: حسگر در.
- SMS0A: حسگر حرکت.
- SSC0A، SSC0B: دوربین‌های پشتیبانی‌شده.

### فیلدهای وضعیت
- وضعیت هشدار زمانی نمایش داده می‌شود که X-Sense فیلد هشدار را گزارش کند.
- وضعیت بی‌صدا زمانی نمایش داده می‌شود که X-Sense فیلد mute را گزارش کند.
- وضعیت باتری زمانی نمایش داده می‌شود که دستگاه داده باتری گزارش کند.
- سیگنال RF و Wi-Fi زمانی نمایش داده می‌شود که دستگاه آن را گزارش کند.
- زمان‌های فشرده X-Sense به حسگرهای خوانای Home Assistant تبدیل می‌شوند.

### کنترل‌ها و گزارش خطا
- کلیدها فقط برای تنظیمات قابل‌نوشتن گزارش‌شده توسط X-Sense ساخته می‌شوند.
- دکمه‌ها فقط برای عملکردهای پشتیبانی‌شده در برنامه ساخته می‌شوند.
- کنترل‌های دوربین فقط وقتی ساخته می‌شوند که API آن‌ها را موجود بداند.
- گزارش خطا باید شامل مدل دقیق، نسخه یکپارچه‌سازی، داده‌های عیب‌یابی، گزارش‌ها و تغییر کردن یا نکردن مقدار در برنامه X-Sense باشد.

____________________________________________________________

## Camera AI Notifications
Supported cameras create an `AI Detection` event entity, such as `event.front_camera_ai_detection`. Use this `event.*` entity for notification automations, and replace the sample entity ID with the actual entity ID shown in your Home Assistant instance.

The easiest UI path is the included blueprint. Use the button below to import it, select the camera `AI Detection` event entity, leave Detection types selected to notify for every AI event, then keep or replace the default notification action.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2FJarnsen%2Fha-xsense-component_test%2Fmain%2Fblueprints%2Fautomation%2Fxsense%2Fcamera_ai_notification.yaml)

If the button does not open Home Assistant, import this raw blueprint URL manually: `https://raw.githubusercontent.com/Jarnsen/ha-xsense-component_test/main/blueprints/automation/xsense/camera_ai_notification.yaml`.

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
