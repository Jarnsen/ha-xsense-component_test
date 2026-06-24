<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

<div dir="rtl">

# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


## סקירה כללית
האינטגרציה הזו של Home Assistant מאפשרת להשתמש במכשירי X-Sense בבית החכם. היא מבוססת על העבודה המקורית של Theo Snel ומותקנת דרך HACS.

מומלץ ליצור חשבון X-Sense נפרד עבור Home Assistant ולשתף אליו מהחשבון הראשי רק את המכשירים הנתמכים.

## התקנה
ב-HACS הוסיפו מאגר מותאם אישית `https://github.com/Jarnsen/ha-xsense-component_test`, הורידו את האינטגרציה, פעלו לפי הוראות ההפעלה מחדש של HACS והגדירו אותה עם חשבון X-Sense הייעודי ל-Home Assistant.


## הגדרה מפורטת עם צילומי מסך

1. צרו חשבון X-Sense נפרד עבור Home Assistant ושתפו אליו מהחשבון הראשי רק מכשירים נתמכים.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

2. הוסיפו ב-HACS את `https://github.com/Jarnsen/ha-xsense-component_test` כמאגר מותאם אישית.

![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

3. הורידו והתקינו את האינטגרציה, הפעילו מחדש את Home Assistant, ואז הגדירו אותה עם חשבון X-Sense החדש.

![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

4. לאחר הגדרה מוצלחת, המכשירים המשותפים יופיעו בעמוד המכשירים של Home Assistant.

![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)

5. צימוד, הסרה, קושחה, תשלומים, כרטיסי SD וניהול חשבון נשארים באפליקציית X-Sense.

## מכשירים נתמכים
נתמכים תחנות בסיס, גלאי עשן, גלאי CO, אזעקות חום, גלאי נזילת מים, היגרומטרים, חיישני דלת ותנועה, אורות, לוחות מקשים, חיישני תיבת דואר, התקני האזנה ומצלמות נתמכות כאשר חשבון X-Sense מדווח עליהם.

משפחות הדגמים שאושרו כוללות: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## ישויות ופעולות
האינטגרציה יוצרת ישויות רק לשדות שהמכשיר באמת מדווח עליהם. זה עשוי לכלול אזעקות, השתקה, סוללה, אות, טמפרטורה, לחות, CO, זמנים קריאים, הגדרות מצלמה, מתגי LED, בדיקה, השתקה ותרגול אש.

ניהול מכשירים, שיתוף, הסרה, קושחה, חשבונות ותשלומים נשארים באפליקציית X-Sense. לדיונים השתמשו ב-Discord או בפורום Home Assistant.

## דוגמאות אוטומציה
```yaml
automation:
  - alias: "התראת טמפרטורה X-Sense"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "הטמפרטורה עלתה מעל 30 מעלות!"
```

```yaml
automation:
  - alias: "אזעקת נזילת מים"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "זוהתה נזילת מים!"
```

## תמיכה
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)


## פרטים נוספים

### הגדרת חשבון

מומלץ להשתמש בחשבון X-Sense נפרד עבור Home Assistant ולשתף אליו רק את המכשירים הנתמכים שברצונך להציג ב-Home Assistant. האינטגרציה אינה מצמדת, מסירה או מעבירה מכשירים בין בתים. ניהול כזה נשאר באפליקציית X-Sense הרשמית.

### עדכוני מצב

האינטגרציה משתמשת בהודעות MQTT shadow לשינויי מצב מהירים ובשאילתות ענן תקופתיות וזהירות לרענון נתונים. מצב שמגיע מתחנה נשמר על התחנה, ומצב שמגיע ממכשיר משנה נשמר על אותו מכשיר, כדי שהתרעות וחיישנים לא יישארו תקועים על ערכים ישנים.

### ישויות זמינות

בהתאם לדגם, עשויים להופיע חיישנים בינאריים עבור עשן, CO, מים, טמפרטורה, תנועה ודלת, השתקת התרעה, סוף חיי מכשיר, טעינה, מצב תזכורת, מצב תאורה ואבחון נוסף. חיישנים יכולים לכלול סוללה, אות RF או Wi-Fi, קושחה, טמפרטורה, לחות, רמת CO, שיא CO, עוצמת קול, ספי התרעה, זמני קריאה נוחים, אזור זמן ונתוני אבחון נוספים. מתגים, בחירות ושדות מספריים נוצרים רק כאשר המכשיר באמת תומך בהם.

### מצלמות

### פתרון תקלות

אם ישות מסוימת חסרה, יש לבדוק קודם באפליקציית X-Sense שהמכשיר באמת מציג את הערך הזה. אם מצב נשאר מיושן, אפשר לטעון מחדש את האינטגרציה כבדיקה זמנית בלבד ולצרף לדיווח אבחון ושורות יומן רלוונטיות מ-Home Assistant.

### התנהגות מכשירים

- תחנות ומכשירי משנה עשויים לדווח על קבוצות ערכים שונות. לכן האינטגרציה אינה מניחה שלכל תחנה חייב להיות מכשיר משנה.
- ערכי זמן מומרים לתצוגה קריאה כאשר המכשיר שולח זמן בפורמט שבו משתמשת אפליקציית X-Sense.
- ישות לא תיווצר אם המכשיר אינו מדווח על אותה יכולת. כך נמנעים פקדים מטעים ב-Home Assistant.

### עומס על הענן

האינטגרציה מנסה להשתמש ב-API של X-Sense בצורה מתונה. שינויים מהירים מתקבלים מהודעות MQTT, וקריאות ענן משמשות רק כאשר הן נחוצות להתחברות, טעינת מכשירים או רענון מצב.

### דיווח על בעיה

בעת דיווח על תקלה, יש לציין את דגם המכשיר, גרסת האינטגרציה, האם הערך הנכון מופיע באפליקציית X-Sense, ולצרף אבחון של האינטגרציה מ-Home Assistant. כדאי גם לתאר בקצרה אם המצב אינו משתנה כלל או משתנה רק לאחר טעינה מחדש של האינטגרציה.

</div>

## מדריך מלא נוסף

### משפחות מכשירים מרכזיות
- SBS50: תחנת בסיס וסטטוס ברמת התחנה.
- XS01-WX: גלאי עשן Wi-Fi, כולל חשבונות שבהם אין התקן משנה נפרד.
- XS01-M, XS03-WX, XS0B-MR: משפחות גלאי עשן.
- XC01-M, XC04-WX: משפחות גלאי פחמן חד-חמצני.
- SC07-WX, XP0A-MR: מכשירים משולבים לעשן ולפחמן חד-חמצני.
- XH02-M: משפחת גלאי חום.
- SWS51: משפחת חיישני נזילת מים.
- STH51, STH0A, STH0B, STH0C: טמפרטורה ולחות.
- SDS0A: חיישן דלת.
- SMS0A: חיישן תנועה.
- SSC0A, SSC0B: מצלמות נתמכות.

### שדות מצב
- מצב אזעקה מוצג רק כאשר X-Sense מדווחת שדה אזעקה.
- מצב השתקה מוצג רק כאשר X-Sense מדווחת שדה השתקה.
- מצב סוללה מוצג כאשר המכשיר מדווח נתוני סוללה.
- ערכי RF ו-Wi-Fi מוצגים כאשר הם מדווחים על ידי המכשיר.
- שדות זמן קומפקטיים מומרים לערכים קריאים ב-Home Assistant.
- זמני online ו-report מוצגים בצורה ידידותית יותר.

### פקדים
- מתגים נוצרים רק עבור הגדרות כתיבה ש-X-Sense מדווחת עליהן.
- כפתורים נוצרים רק עבור פעולות שהאפליקציה תומכת בהן.
- פקדי מצלמה נוצרים רק כאשר ה-API התואם לאפליקציית Android מסמן אותם כזמינים.
- פעולות חשבון, תשלום, קישור, הסרה ו-firmware נשארות באפליקציית X-Sense.

### דיווח בעיות טוב
- ציינו את דגם המכשיר המדויק.
- ציינו את גרסת האינטגרציה.
- ציינו האם הערך משתנה באפליקציית X-Sense.
- צרפו לוגים של Home Assistant ודיאגנוסטיקה של האינטגרציה.
- ציינו האם טעינה מחדש של האינטגרציה משנה את הערך.

## פרטי שימוש נוספים

### עדכוני MQTT ו-polling
- MQTT shadow משמש לעדכוני מצב מהירים.
- polling תקופתי משמש רק כגיבוי כאשר חסר עדכון חי.
- טעינת רשימת המכשירים המלאה אינה אמורה לחזור בכל מחזור עדכון.
- כך האינטגרציה שומרת על עומס נמוך יותר מול שירותי X-Sense.

### מצלמות ו-WebRTC
- מצלמות נתמכות יכולות לחשוף תמונה ממוזערת וכתובת stream.
- זמינות ה-stream תלויה במכשיר, בחשבון ובתגובת שירות X-Sense.
- הגדרות שאינן זמינות בחשבון לא יוצגו כפקדים.

### פעולות שנשארות באפליקציה
- הוספת מכשיר חדש.
- מחיקת מכשיר.
- העברת מכשיר בין בתים.
- ניהול משתמשים ושיתוף מתקדם.
- תשלום, מנוי ושירותי ענן חיצוניים.
- עדכוני firmware ותחזוקת SD card.

### בדיקה אחרי התקנה
- ודאו שהמכשירים משותפים לחשבון Home Assistant.
- ודאו שהאינטגרציה נטענת ללא שגיאות ביומנים.
- בדקו אם הערכים משתנים גם באפליקציית X-Sense.
- בדקו שה-entities שנוצרו תואמים לשדות שהמכשיר באמת מדווח.

____________________________________________________________

## תצוגת מצלמה חיה והתראות AI
הדרך הפשוטה ביותר היא לייבא את ה-blueprint המצורף בעזרת הכפתור למטה, לבחור `Motion` או `AI Detection` זמין, ולשנות את פעולת ההתראה לפי הצורך.

[![ייבוא blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2FJarnsen%2Fha-xsense-component_test%2Fmain%2Fblueprints%2Fautomation%2Fxsense%2Fcamera_ai_notification.yaml)

Motion ו-AI Detection הם אירועים חד-פעמיים, לא מצבי פועל/כבוי. לאוטומציות ידניות השתמשו ב-`event.received`; `event_type` נחוץ רק לסינון סוגים כמו `person`, `pet`, `vehicle`, `package`, `other` או `ai_detection`.

דוגמת אוטומציה:

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
