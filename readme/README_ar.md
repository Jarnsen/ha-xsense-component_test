
# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.

<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>
<div dir="rtl">
## نظرة عامة


تتيح لك هذه التكاملية مع Home Assistant استخدام أجهزة X-Sense داخل نظام المنزل الذكي. تم إنشاؤها استنادًا إلى الكود الأصلي لـ


  [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense)
  ونُشرت بإذنه وبالتعاون معه.


يتم الحفاظ على تكامل HACS هذا بنشاط للمستخدمين الذين يريدون دعمًا أوسع لأجهزة X-Sense في Home Assistant. يتم تحديثه بانتظام لإضافة ميزات جديدة، وتوسيع دعم الأجهزة، وإصلاح المشاكل التي يبلغ عنها المستخدمون.

<p align="center">
 <img src="https://github.com/user-attachments/assets/fbe7e69b-9204-4de4-a245-e0e2bdbd7f73" alt="Image">
</p>
## الميزات
- تكامل مختلف أجهزة X-Sense مع Home Assistant.
- دعم الأتمتة بناءً على بيانات أجهزة الاستشعار من X-Sense.
- دعم للأنواع التالية من الأجهزة: محطات القاعدة، أجهزة كشف الدخان، أجهزة كشف أول أكسيد الكربون، أجهزة الكشف الحراري، أجهزة كشف تسرب المياه ومقاييس الرطوبة.
- إعداد سهل من خلال HACS (Home Assistant Community Store).

## المتطلبات
- خادم Home Assistant فعال (يوصى بأحدث إصدار).
- حساب X-Sense مع الأجهزة المدعومة.
- يجب تثبيت HACS في Home Assistant لتمكين تثبيت التكامل.

## فيديو تعليمي
للحصول على دليل تفصيلي حول التثبيت والتكوين، يمكنك مشاهدة الفيديو التالي:

[![تطبيق تكامل X-Sense Home Assistant](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## التحضير
قبل تثبيت التكامل، من الضروري القيام ببعض التحضيرات:

- **إنشاء حساب ثاني في تطبيق X-Sense (للاستخدام مع Home Assistant)**: نظرًا لأنك لا تستطيع تسجيل الدخول في التطبيق وHome Assistant بنفس الحساب في آن واحد، ننصح باستخدام حساب منفصل لـ Home Assistant. هذا يمنعك من فصل الاتصال بشكل متكرر بين التطبيق وHome Assistant. الحساب الإضافي يتيح تكامل سلس دون انقطاعات.

- **مشاركة الأجهزة المدعومة من الحساب الرئيسي إلى حساب Home Assistant**: استخدم تطبيق X-Sense لمشاركة **فقط الأجهزة المدعومة** مع الحساب الجديد الذي أنشأته. بهذه الطريقة، يمكنك استخدام التكامل بسهولة في Home Assistant، بينما تستمر في إدارة الأجهزة من حسابك الرئيسي.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## التثبيت عبر HACS
1. **افتح HACS في Home Assistant**:
  HACS هو امتداد مهم لـ Home Assistant، يتيح لك تثبيت التكاملات المخصصة بسهولة.

  ![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **اذهب إلى المستودعات المخصصة**:
  انتقل إلى الإعدادات في لوحة HACS وأضف هذا المستودع كمصدر مخصص.

3. **أضف المستودع**:
  أدخل عنوان URL للمستودع: `https://github.com/Jarnsen/ha-xsense-component_test`

  ![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **قم بتنزيل التكامل وتثبيته**:
  ابحث عن التكامل في HACS، قم بتنزيله وتثبيته. بعد التثبيت، يمكنك إعداد التكامل من خلال واجهة Home Assistant.

  ![HACS repository selection screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)

  ![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## الإعداد
بعد التثبيت، يلزم إجراء إعداد أساسي لكي يعمل التكامل بشكل صحيح:
- **اسم المستخدم وكلمة المرور**: استخدم بيانات الاعتماد الخاصة بحساب X-Sense الجديد الذي أنشأته لتكوين الاتصال.

  ![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

- **نظرة عامة على الأجهزة**: بعد الإعداد بنجاح، ستكون الأجهزة المشتركة متاحة في Home Assistant ويمكن استخدامها للأتمتة.

  ![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)
## العرض في Home Assistant
بعد التثبيت والإعداد بنجاح، سيكون التكامل مرئيًا في Home Assistant. ستكون الأجهزة مرئية على لوحة التحكم ويمكن استخدامها للأتمتة والإشعارات وحالات الاستخدام الأخرى.


![منتدى](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/2d271b78-39d9-4bbd-837d-8593cf1933bd)


____________________________________________________________

## الأجهزة المدعومة
يدعم هذا التكامل عدة أجهزة X-Sense. تعتمد الكيانات المتاحة على الحقول التي يرسلها الجهاز والحساب. تشمل العائلات والنماذج المؤكدة:
- **المحطة الأساسية (SBS50)**: محور مركزي لأجهزة X-Sense.
- **إنذار الحرارة (XH02-M)**: يكتشف درجات الحرارة المرتفعة بشكل غير طبيعي.
- **كاشف أول أكسيد الكربون (XC01-M; XC04-WX)**: يكتشف تراكيز CO الخطرة.
- **كاشف الدخان (XS01-M; XS01-WX; XS03-WX; XS0B-MR والنماذج RF/iR المرتبطة)**: اكتشاف مبكر للدخان.
- **كاشف CO والدخان المشترك (SC07-WX; XP0A-MR والنماذج XP/SC المرتبطة)**: يكتشف CO والدخان.
- **كاشف تسرب المياه (SWS51)**: يكتشف الماء في الأماكن غير المرغوبة.
- **مقياس الرطوبة والحرارة (STH51, STH0A, STH0B, STH0C)**: يراقب الحرارة والرطوبة.
- **حساس الباب (SDS0A)** و **حساس الحركة (SMS0A)**: يظهران عندما يرسل X-Sense الحالة.
- **الكاميرا (SSC0A, SSC0B)**: تعرض كيانات الكاميرا والصور المصغرة وروابط البث المباشر والتشخيصات والإعدادات المدعومة بسلوك تطبيق Android عندما يدعمها الجهاز والحساب.
- **أجهزة أخرى متصلة بالمحطة**: الضوء ولوحة المفاتيح وصندوق البريد و جهاز الاستماع وإنذار الممر و جهاز التسليم الذكي والريموت وبيانات الرادون تظهر عندما ترسل API حقولًا مدعومة.

### الكيانات والإجراءات المتاحة
ينشئ التكامل كيانات Home Assistant فقط للحقول الموجودة فعليًا في سحابة X-Sense أو حمولات MQTT shadow أو واجهات الكاميرا المتوافقة مع سلوك تطبيق Android. حسب الجهاز، قد يشمل ذلك:

- حساسات ثنائية لحالة alarm و mute و end-of-life و AC-break و water alarm و temperature alarm و charging و motion و door و armed و warning و reminder و light و PIR وحالة keypad.
- حساسات للبطارية، إشارة RF، إشارة Wi-Fi، البرنامج الثابت، درجة الحرارة، الرطوبة، مستوى CO، ذروة CO، حجم صوت الإنذار، حجم الصوت، حجم صوت التنبيه، حجم التذكير، حدود التحذير، مؤقتات الكتم، طوابع زمنية مقروءة، المنطقة الزمنية وبيانات تشخيص أخرى.
- مفاتيح للإعدادات القابلة للكتابة التي يعلن X-Sense دعمها، مثل LED light، تفعيل alarm، continued alarm، chirp tone، reminders، PIR، sunshine/white light، await، صوت keypad، كشف حركة camera، recording، night vision، audio، cooldown، light وتحكم doorbell.
- عناصر select و number لإعدادات الكاميرا المدعومة مثل language، recording resolution، codec، anti-flicker rate، motion sensitivity، video length، volume، alarm duration، cooldown، night threshold و doorbell ring key.
- أزرار test و mute و fire-drill و camera wake للطرازات التي يعرض تطبيق X-Sense الإجراء المطابق لها.

بعض الكيانات تشخيصية أو متعلقة بالإعدادات ويتم تجميعها كذلك في Home Assistant. إذا لم يرسل الجهاز حقلًا معينًا، أو وضع تطبيق X-Sense الميزة كغير مدعومة لهذا الجهاز/الحساب، فلن يتم إنشاء الكيان المقابل. تبقى إجراءات ربط الجهاز، إزالته، مشاركته، الحساب، الدفع، تحديث البرنامج الثابت، تهيئة بطاقة SD، والإدارة الأخرى داخل تطبيق X-Sense.
____________________________________________________________

## أمثلة على الأتمتة
باستخدام هذا التكامل، يمكنك إنشاء مجموعة متنوعة من الأتمتة. فيما يلي بعض الأمثلة:

### المثال 1: تحذير درجة الحرارة
عندما تكون درجة الحرارة من مقياس حرارة X-Sense أعلى من 30 درجة مئوية، يتم إرسال إشعار:

```yaml
automation:
  - alias: "تحذير درجة الحرارة X-Sense"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "درجة الحرارة تجاوزت 30 درجة!"
```

### المثال 2: إنذار كاشف تسرب المياه
عندما يكتشف كاشف تسرب المياه وجود ماء، يتم تفعيل إشعار:

```yaml
automation:
  - alias: "إنذار تسرب المياه"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "تم اكتشاف تسرب مياه!"
```

____________________________________________________________

## نحن بحاجة إلى مساعدتك
نحن نبحث دائمًا عن دعم لتحسين وتطوير هذا التكامل. هناك العديد من الطرق التي يمكنك المساعدة بها:

1. **اختبار الأجهزة**: إذا كنت تملك جهاز X-Sense يعمل مع التكامل، أبلغنا بذلك لنضيفه إلى قائمة الأجهزة المدعومة.

2. **الإبلاغ عن الأجهزة غير المدعومة**: إذا كان هناك جهاز لا يعمل، أبلغنا بذلك لنقدم الدعم أو ندمج الجهاز في الإصدارات المستقبلية.

3. **مشاركة الأجهزة للاختبار**: أفضل طريقة لاختبار أجهزة جديدة هي مشاركة الجهاز عبر تطبيق X-Sense لضمان دعم أكبر عدد ممكن من الأجهزة.

4. **دعم المجتمع**: شارك في النقاشات في مجتمعنا. سواء كانت لديك اقتراحات للتحسين أو تقدم المساعدة للمستخدمين الآخرين في إعداداتهم، فإن كل مساعدة مرحب بها!

للنقاشات والدعم، يمكنك العثور علينا على خادمنا في Discord أو في منتدى Home Assistant:

 [Discord](https://discord.gg/5phHHgGb3V)

[منتدى](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)



</div>

## مرجع كامل

### الحساب والتثبيت
- استخدم حساب X-Sense منفصلاً لـ Home Assistant.
- شارك الأجهزة المدعومة فقط من حساب X-Sense الرئيسي.
- تبقى عمليات الاقتران والإزالة والمشاركة والبرامج الثابتة والحساب والمدفوعات وإدارة بطاقة SD داخل تطبيق X-Sense.

### التحديثات واستخدام API
- تصل تغييرات الحالة السريعة عبر رسائل MQTT shadow.
- تُستخدم طلبات السحابة لتسجيل الدخول واكتشاف الأجهزة وبيانات الكاميرا واستعادة الحالة.
- polling الدوري هو خيار احتياطي فقط عند فقدان تحديث مباشر.

### الكيانات والكاميرات واستكشاف الأخطاء
- تُنشأ الكيانات فقط للحقول التي يبلّغ عنها X-Sense فعلاً.
- تُنشأ كيانات الكاميرا وعناصر التحكم فقط عندما يعلن API المتوافق مع تطبيق Android دعم الحساب والطراز.
- إذا كانت قيمة مفقودة، فقارنها أولاً مع تطبيق X-Sense ثم أرفق التشخيصات وسجلات Home Assistant ذات الصلة.

## قائمة فحص الأجهزة والكيانات

### عائلات الأجهزة الرئيسية
- تتم معالجة محطة SBS50، إنذارات الدخان XS، إنذارات CO من XC، الإنذارات المركبة SC/XP، إنذارات الحرارة XH، حساسات المياه SWS، حساسات الحرارة/الرطوبة STH، حساسات الأبواب SDS، حساسات الحركة SMS، كاميرات SSC وغيرها من عائلات X-Sense عندما يعرض API حقولها.

### حقول الحالة
- لا تظهر حقول الإنذار والكتم والبطارية وإشارة RF/Wi-Fi والحرارة والرطوبة وCO والمياه والحركة والباب والضوء والتذكيرات والتحذيرات والطوابع الزمنية المقروءة إلا عندما يبلّغ عنها X-Sense.

### التحكم والتقارير
- تُنشأ المفاتيح والقوائم والأرقام والأزرار فقط للإعدادات والإجراءات القابلة للكتابة التي يعرضها الجهاز/الحساب.
- التقرير الجيد يتضمن الطراز الدقيق، إصدار التكامل، التشخيصات، السجلات، وما إذا كانت القيمة تتغير بشكل صحيح في تطبيق X-Sense.

____________________________________________________________

## Camera AI Notifications
Supported cameras expose AI detections as Home Assistant `event` entities. Use the camera device's `AI Detection` event entity in automations with the `event.received` trigger. Event entities are momentary notifications, so they do not stay `on` or `off` like binary sensors.

Available event types include `person`, `pet`, `vehicle`, `vehicle_enter`, `vehicle_out`, `vehicle_held_up`, `package`, `package_drop_off`, `package_pick_up`, `package_exist`, `other`, and `ai_detection`. The `ai_detection` event type is used when one camera notification contains more than one detected object.

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

For dashboards or conditions that need the most recent detection, use the `Last AI Detection` and related last-detection timestamp sensors. Those sensors are history values; the actual notification trigger is the `AI Detection` event entity.

____________________________________________________________
