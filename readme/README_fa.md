# ha-xsense-component_test

<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## نمای کلی
این یکپارچه‌سازی Home Assistant امکان استفاده از دستگاه‌های X-Sense را در خانه هوشمند فراهم می‌کند. این پروژه بر پایه کد اصلی [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) ساخته شده و با اجازه و همکاری او منتشر شده است.

تا زمانی که یکپارچه‌سازی رسمی Home Assistant آماده شود، این نسخه HACS برای افزودن قابلیت‌ها و رفع مشکلات به‌روزرسانی می‌شود.

## قابلیت‌ها
- افزودن انواع دستگاه‌های X-Sense به Home Assistant.
- پشتیبانی از اتوماسیون بر پایه داده‌های حسگرهای X-Sense.
- پشتیبانی از ایستگاه پایه، هشدار دود، هشدار مونوکسید کربن، هشدار گرما، نشت آب، دما و رطوبت، حسگر در، حسگر حرکت، چراغ، صفحه‌کلید، صندوق پستی و دستگاه listener در صورت گزارش شدن توسط حساب X-Sense.
- به‌روزرسانی بلادرنگ از طریق X-Sense MQTT shadow و polling دوره‌ای ابر به عنوان پشتیبان.
- نصب آسان از طریق HACS.

## پیش‌نیازها
- سرور Home Assistant فعال.
- حساب X-Sense با دستگاه‌های پشتیبانی‌شده.
- نصب بودن HACS در Home Assistant.

## آماده‌سازی
- **یک حساب دوم X-Sense برای Home Assistant بسازید**: استفاده از حساب جداگانه توصیه می‌شود، زیرا ورود همزمان با یک حساب در برنامه و Home Assistant ممکن است پایدار نباشد.
- **دستگاه‌های پشتیبانی‌شده را از حساب اصلی با حساب Home Assistant به اشتراک بگذارید**: مدیریت دستگاه‌ها در حساب اصلی باقی می‌ماند و Home Assistant فقط به دستگاه‌های اشتراک‌گذاری‌شده دسترسی دارد.

## نصب و پیکربندی
1. HACS را در Home Assistant باز کنید.
2. آدرس `https://github.com/Jarnsen/ha-xsense-component_test` را به عنوان custom repository اضافه کنید.
3. یکپارچه‌سازی را دانلود و نصب کنید.
4. در صفحه Integrations با نام کاربری و رمز عبور X-Sense پیکربندی را انجام دهید.

## دستگاه‌های پشتیبانی‌شده
Entityهای ایجادشده به فیلدهایی بستگی دارد که X-Sense cloud یا MQTT shadow گزارش می‌کند. دستگاه‌های رایج شامل SBS50 base station، دستگاه‌های دود و CO سری XS/SC/XP/XC، هشدار گرما XH، نشت آب SWS، دما و رطوبت STH، حسگر در SDS، حسگر حرکت SMS، چراغ، صفحه‌کلید، صندوق پستی، هشدار مسیر ورودی و سایر دستگاه‌هایی است که فیلدهای پشتیبانی‌شده را گزارش می‌کنند.

## Entityها و عملکردها
- Binary sensor برای alarm، mute، پایان عمر، AC break، هشدار آب، هشدار دما، شارژ، حرکت، در، armed، reminder، light و diagnostics.
- Sensor برای باتری، RF، Wi-Fi، firmware، دما، رطوبت، CO، volume، زمان‌های خوانا، شماره سریال، MAC و diagnostics دیگر.
- Switch برای تنظیمات قابل نوشتن مانند LED light، alarm، reminders، PIR، sunshine، await و keypad sound در صورت پشتیبانی دستگاه.
- دکمه‌های test، mute و fire drill برای مدل‌های پشتیبانی‌شده.

## نمونه Automation
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
        message: "نشت آب تشخیص داده شد!"
```

## به کمک شما نیاز داریم
اگر دستگاه X-Sense تست‌نشده‌ای دارید، لطفاً بازخورد خود را در GitHub، Discord یا انجمن Home Assistant ارسال کنید.
