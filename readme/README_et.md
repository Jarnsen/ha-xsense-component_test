# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Ülevaade
See Home Assistanti integratsioon teeb X-Sense seadmed nutikodus kasutatavaks. See põhineb Theo Sneli algsel tööl ja paigaldatakse HACS-i kaudu.

Soovitame luua Home Assistanti jaoks eraldi X-Sense konto ning jagada põhikontolt ainult toetatud seadmeid.

## Paigaldamine
Lisage HACS-is kohandatud repositoorium `https://github.com/Jarnsen/ha-xsense-component_test`, laadige integratsioon alla, järgige HACS-i taaskäivituse juhiseid ja seadistage integratsioon Home Assistanti jaoks loodud X-Sense kontoga.


## Üksikasjalik seadistus ekraanipiltidega

1. Loo Home Assistanti jaoks eraldi X-Sense'i konto ja jaga põhikontolt ainult toetatud seadmed.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

2. Lisa HACS-is kohandatud hoidlaks `https://github.com/Jarnsen/ha-xsense-component_test`.

![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

3. Laadi integratsioon alla, paigalda see, taaskäivita Home Assistant ja seadista see uue X-Sense'i kontoga.

![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

4. Pärast edukat seadistamist ilmuvad jagatud seadmed Home Assistanti seadmete lehele.

![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)

5. Sidumine, eemaldamine, püsivara, maksed, SD-kaardid ja konto haldus jäävad X-Sense'i rakendusse.

## Toetatud seadmed
Toetatud on tugijaamad, suitsuandurid, CO-andurid, kuumahäired, veelekkeandurid, hügromeetrid, ukse- ja liikumisandurid, valgustid, klaviatuurid, postkastiandurid, kuulamisseadmed ja toetatud kaamerad, kui X-Sense konto neid raporteerib.

Kinnitatud mudelipered hõlmavad: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## Olemid ja toimingud
Integratsioon loob olemid ainult nende andmete jaoks, mida seade tegelikult raporteerib. See võib hõlmata häireid, vaigistust, akut, signaali, temperatuuri, õhuniiskust, CO-d, loetavaid ajavälju, kaamera seadeid, LED-lüliteid ning testi-, vaigistus- ja tuleõppuse nuppe.

Seadmehaldus, jagamine, eemaldamine, püsivara, kontod ja maksed jäävad X-Sense rakendusse. Aruteludeks kasutage Discordi või Home Assistanti foorumit.

## Camera Live View and AI Notifications
Supported cameras use native Home Assistant WebRTC for live video and audio. They also create `Motion` and `AI Detection` event entities, such as `event.front_camera_motion` and `event.front_camera_ai_detection`. Use these `event.*` entities for notification automations, and replace sample entity IDs with the actual entity IDs shown in your Home Assistant instance.

The easiest UI path is the included blueprint. Use the button below to import it, select the camera `Motion` or `AI Detection` event entity, leave Event types selected to notify for every camera event, then keep or replace the default notification action. If a mobile notification action fails because a phone is not connected to local push notifications, edit the blueprint automation action and choose a working notification target.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2FJarnsen%2Fha-xsense-component_test%2Fmain%2Fblueprints%2Fautomation%2Fxsense%2Fcamera_ai_notification.yaml)

Camera Motion and AI Detection updates are one-time events, not on/off states. Trigger on them with Home Assistant's `event.received` trigger and filter by `event_type`. Supported event types include `motion`, `person`, `pet`, `vehicle`, `vehicle_enter`, `vehicle_out`, `vehicle_held_up`, `package`, `package_drop_off`, `package_pick_up`, `package_exist`, `other`, and `ai_detection`. The `ai_detection` event type is used when one camera notification contains more than one detected object.

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

____________________________________________________________
## Automatiseerimise näited
```yaml
automation:
  - alias: "X-Sense temperatuurihoiatus"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "Temperatuur ületab 30 kraadi!"
```

```yaml
automation:
  - alias: "Veelekke häire"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "Tuvastati veeleke!"
```

## Tugi
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

## Lisateave

### Konto seadistamine

Soovitatav on kasutada Home Assistanti jaoks eraldi X-Sense'i kontot ja jagada sinna ainult need toetatud seadmed, mida soovite Home Assistantis näha. Integratsioon ei seo, eemalda ega liiguta seadmeid kodude vahel. Selline seadmehaldus jääb ametlikku X-Sense'i rakendusse.

### Olekuvärskendused

Integratsioon kasutab kiirete olekumuudatuste jaoks MQTT shadow-teateid ja andmete värskendamiseks säästlikku perioodilist pilvepäringut. Jaama saadetud olek salvestatakse jaamale ning alamseadme saadetud olek konkreetsele seadmele, et alarmid ja andurid ei jääks vanadele väärtustele kinni.

### Saadaolevad olemid

Olenevalt mudelist võivad ilmuda suitsu-, CO-, vee-, temperatuuri-, liikumis- ja uksealarmid, alarmi vaigistamine, kasutusea lõpp, laadimine, meeldetuletuse olek, valguse olek ja muud diagnostilised binaarandurid. Andurid võivad sisaldada akut, RF- või Wi-Fi-signaali, püsivara, temperatuuri, niiskust, CO taset, CO tippväärtust, helitugevust, läviväärtusi, loetavaid ajatempleid, ajavööndit ja muud diagnostikat. Lülitid, valikud ja arvväärtused luuakse ainult siis, kui seade neid tegelikult toetab.

### Kaamerad

Toetatud kaamerad võivad pakkuda kaamera olemit, pisipilte, otsevoogu, ühenduse olekut ja X-Sense'i rakendusega kooskõlas olevaid seadeid. Kui Home Assistantis on WebRTC tee olemas, saab integratsioon seda sobiva otsevaate jaoks kasutada.

### Tõrkeotsing

Kui mõni olem puudub, kontrollige esmalt X-Sense'i rakenduses, kas seade seda väärtust tõesti kuvab. Kui olek jääb vanaks, laadige integratsioon ajutise testina uuesti ja lisage veateatele diagnostika ning asjakohased Home Assistanti logiread.

### Seadmete käitumine

- Jaamad ja alamseadmed võivad edastada erinevaid väärtuste komplekte. Seetõttu ei eelda integratsioon, et igal jaamal peab olema alamseade.
- Aja väärtused teisendatakse loetavaks, kui seade saadab aja X-Sense'i rakenduses kasutatavas vormingus.
- Olem jäetakse loomata, kui seade vastavat funktsiooni ei teavita. Nii välditakse Home Assistantis eksitavaid juhtelemente.

### Pilvekoormus

Integratsioon püüab X-Sense'i API-t säästlikult kasutada. Kiired muudatused võetakse MQTT-teadetest ning pilvepäringuid kasutatakse ainult seal, kus neid on vaja sisselogimiseks, seadmete laadimiseks või oleku värskendamiseks.

### Probleemist teatamine

Veateates lisage seadme mudel, integratsiooni versioon, kas õige väärtus on X-Sense'i rakenduses nähtav, ning Home Assistanti integratsiooni diagnostika. Kasulik on ka lühidalt kirjeldada, kas olek ei muutu kunagi või muutub alles pärast integratsiooni uuesti laadimist.

## Täielik viiteosa

### Konto seadistamine üksikasjalikult
- Kasuta Home Assistanti jaoks eraldi X-Sense kontot.
- Jaga põhikontolt ainult toetatud seadmed.
- Sidumine, eemaldamine, jagamine ja kodude vahel liigutamine jäävad X-Sense rakendusse.
- Kui rakendus ja Home Assistant logivad teineteist välja, kasutavad nad tõenäoliselt sama kontot.

### Uuendused ja API koormus
- Kiired olekumuutused tulevad MQTT shadow sõnumite kaudu.
- Pilvepäringuid kasutatakse sisselogimiseks, seadmete laadimiseks ja oleku värskendamiseks.
- Perioodiline päring on varu, kui MQTT sõnum puudub.

### Olemid ja toimingud
- Olemid luuakse ainult väljade jaoks, mida X-Sense tegelikult raporteerib.
- Diagnostilised väärtused märgitakse diagnostikaks.
- Test, vaigistamine, tulekahjuõppus ja kaamera äratamine on ainult toetatud mudelitel.

### Kaamerate ülevaade
- Toetatud kaamerad võivad pakkuda kaamera olemit, eelvaadet, otsevoogu ja diagnostikat.
- WebRTC teed kasutatakse ainult siis, kui Home Assistant seda pakub.
- SD-kaardi, maksete, püsivara ja konto haldus jääb X-Sense rakendusse.

### Tõrkeotsingu kontrollnimekiri
- Veateates lisa mudel, integratsiooni versioon, diagnostika ja asjakohased logid.

### Ulatus
- Integratsioon ei lisa, eemalda ega liiguta seadmeid kodude vahel.

## Seadmete ja olemite kontrollnimekiri

### Peamised seadmepered
- SBS50: baasjaam ja jaamataseme olek.
- XS01-WX: Wi-Fi suitsuandur, ka ilma alamseadmeta kontodel.
- XS01-M, XS03-WX, XS0B-MR: suitsuandurite pered.
- XC01-M, XC04-WX: CO-andurite pered.
- SC07-WX, XP0A-MR: suitsu ja CO kombineeritud pered.
- XH02-M: kuumaanduri pere.
- SWS51: veelekke anduri pere.
- STH51, STH0A, STH0B, STH0C: temperatuur ja niiskus.
- SDS0A: ukseandur.
- SMS0A: liikumisandur.
- SSC0A, SSC0B: toetatud kaamerad.

### Olekuk väljad
- Alarmiolek kuvatakse, kui X-Sense raporteerib alarmivälja.
- Vaigistuse olek kuvatakse, kui X-Sense raporteerib vaigistuse välja.
- Aku olek kuvatakse, kui seade raporteerib akuandmeid.
- RF ja Wi-Fi signaal kuvatakse, kui seade neid raporteerib.
- Kompaktsed ajaväärtused teisendatakse loetavateks Home Assistant sensoriteks.

### Juhtimine ja aruanded
- Lülitid luuakse ainult X-Sense raporteeritud kirjutatavatele seadetele.
- Nupud luuakse ainult rakenduse toetatud toimingutele.
- Kaamerajuhtimine luuakse ainult siis, kui API märgib selle saadaval olevaks.
- Veateates lisa täpne mudel, integratsiooni versioon, diagnostika, logid ja kas väärtus muutub X-Sense rakenduses.

### Kasutusmärkused
- Pärast seadistamist kontrolli, et seadmete nimed ja ruumid vastaksid X-Sense'i rakendusele.
- Kui alarm, vaigistus või LED ei muutu kohe, oota järgmist MQTT sõnumit või olekuvärskendust.
- SBS50 jaamade puhul kontrolli nii jaama olekut kui ka iga alamseadet.
- XS01-WX puhul võib kogu olek olla teatatud otse seadme kaudu, isegi ilma eraldi alamseadmeta kontol.
- Kaamerate puhul sõltuvad loodavad olemid sellest, millised võimalused X-Sense'i pilv selle konto jaoks tagastab.
- Kui olem ei teki, võrdle väärtust esmalt X-Sense'i rakendusega ja lisa diagnostika.
- Integratsioon on mõeldud toetatud funktsioonide kuvamiseks ja juhtimiseks, mitte seadmete sidumise või halduse asendamiseks rakenduses.
