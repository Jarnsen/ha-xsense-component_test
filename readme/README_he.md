<div dir="rtl">

# ha-xsense-component_test

## סקירה כללית
האינטגרציה הזו של Home Assistant מאפשרת להשתמש במכשירי X-Sense בבית החכם. היא מבוססת על העבודה המקורית של Theo Snel ומותקנת דרך HACS.

מומלץ ליצור חשבון X-Sense נפרד עבור Home Assistant ולשתף אליו מהחשבון הראשי רק את המכשירים הנתמכים.

## התקנה
ב-HACS הוסיפו מאגר מותאם אישית `https://github.com/Jarnsen/ha-xsense-component_test`, הורידו את האינטגרציה, פעלו לפי הוראות ההפעלה מחדש של HACS והגדירו אותה עם חשבון X-Sense הייעודי ל-Home Assistant.

## מכשירים נתמכים
נתמכים תחנות בסיס, גלאי עשן, גלאי CO, אזעקות חום, גלאי נזילת מים, היגרומטרים, חיישני דלת ותנועה, אורות, לוחות מקשים, חיישני תיבת דואר, התקני האזנה ומצלמות נתמכות כאשר חשבון X-Sense מדווח עליהם.

משפחות הדגמים שאושרו כוללות: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## ישויות ופעולות
האינטגרציה יוצרת ישויות רק לשדות שהמכשיר באמת מדווח עליהם. זה עשוי לכלול אזעקות, השתקה, סוללה, אות, טמפרטורה, לחות, CO, זמנים קריאים, הגדרות מצלמה, מתגי LED, בדיקה, השתקה ותרגול אש.

ניהול מכשירים, שיתוף, הסרה, קושחה, חשבונות ותשלומים נשארים באפליקציית X-Sense.

## תמיכה
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

</div>
