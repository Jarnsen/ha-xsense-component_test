# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Pārskats
Šī Home Assistant integrācija padara X-Sense ierīces pieejamas viedajā mājā. Tā balstīta uz Theo Snel sākotnējo darbu un tiek instalēta ar HACS.

Iesakām izveidot atsevišķu X-Sense kontu Home Assistant vajadzībām un no galvenā konta kopīgot tikai atbalstītās ierīces.

## Instalēšana
HACS pievienojiet pielāgoto repozitoriju `https://github.com/Jarnsen/ha-xsense-component_test`, lejupielādējiet integrāciju, izpildiet HACS restartēšanas norādījumus un konfigurējiet to ar Home Assistant paredzēto X-Sense kontu.


## Detalizēta iestatīšana ar ekrānuzņēmumiem

1. Izveidojiet atsevišķu X-Sense kontu Home Assistant vajadzībām un no galvenā konta kopīgojiet tikai atbalstītās ierīces.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

2. HACS pievienojiet `https://github.com/Jarnsen/ha-xsense-component_test` kā pielāgotu repozitoriju.

![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

3. Lejupielādējiet un instalējiet integrāciju, pārstartējiet Home Assistant un konfigurējiet to ar jauno X-Sense kontu.

![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

4. Pēc veiksmīgas iestatīšanas kopīgotās ierīces parādīsies Home Assistant ierīču lapā.

![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)

5. Savienošana pārī, noņemšana, firmware, maksājumi, SD kartes un konta pārvaldība paliek X-Sense lietotnē.

## Atbalstītās ierīces
Atbalstītas ir bāzes stacijas, dūmu detektori, CO detektori, karstuma trauksmes, ūdens noplūdes detektori, higrometri, durvju un kustības sensori, gaismas, tastatūras, pastkastīšu sensori, klausīšanās ierīces un atbalstītas kameras, ja X-Sense konts tās ziņo.

Apstiprinātās modeļu saimes ietver: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## Entītijas un darbības
Integrācija izveido entītijas tikai tiem datiem, kurus ierīce patiešām ziņo. Tie var būt trauksmes, klusuma režīms, baterija, signāls, temperatūra, mitrums, CO, salasāmi laika lauki, kameras iestatījumi, LED slēdži un testa, klusuma un ugunsdrošības mācību pogas.

Ierīču pārvaldība, kopīgošana, noņemšana, firmware, konti un maksājumi paliek X-Sense lietotnē. Diskusijām izmantojiet Discord vai Home Assistant forumu.

## Camera AI Notifications
Supported cameras create an `AI Detection` event entity, such as `event.front_camera_ai_detection`. Use this `event.*` entity for notification automations, and replace the sample entity ID with the actual entity ID shown in your Home Assistant instance.

The easiest UI path is the included blueprint: `blueprints/automation/xsense/camera_ai_notification.yaml`. Import it, select the camera `AI Detection` event entity, leave Detection types selected to notify for every AI event, then keep or replace the default notification action.

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
## Automatizācijas piemēri
```yaml
automation:
  - alias: "X-Sense temperatūras brīdinājums"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "Temperatūra pārsniedz 30 grādus!"
```

```yaml
automation:
  - alias: "Ūdens noplūdes trauksme"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "Konstatēta ūdens noplūde!"
```

## Atbalsts
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

## Papildu informācija

### Konta iestatīšana

Home Assistant vajadzībām ieteicams izmantot atsevišķu X-Sense kontu un kopīgot ar to tikai tās atbalstītās ierīces, kuras vēlaties redzēt Home Assistant. Integrācija nesavieno pārī, nenoņem un nepārvieto ierīces starp mājām. Šāda ierīču pārvaldība joprojām jāveic oficiālajā X-Sense lietotnē.

### Statusa atjauninājumi

Integrācija izmanto MQTT shadow ziņojumus ātrām statusa izmaiņām un saudzīgu periodisku mākoņa vaicāšanu datu atsvaidzināšanai. Stacijas ziņotais statuss tiek saglabāts stacijai, bet apakšierīces ziņotais statuss tiek saglabāts konkrētajai ierīcei, lai trauksmes un sensori nepaliktu pie vecām vērtībām.

### Pieejamās entītijas

Atkarībā no modeļa var tikt rādītas dūmu, CO, ūdens, temperatūras, kustības un durvju trauksmes, trauksmes apklusināšana, kalpošanas laika beigas, uzlāde, atgādinājuma statuss, gaismas statuss un citi diagnostikas binārie sensori. Sensori var ietvert akumulatoru, RF vai Wi-Fi signālu, aparātprogrammatūru, temperatūru, mitrumu, CO līmeni, CO maksimumu, skaļumu, sliekšņus, salasāmus laikus, laika joslu un citu diagnostiku. Slēdži, izvēles un skaitliskās vērtības tiek izveidotas tikai tad, ja ierīce tās patiešām atbalsta.

### Kameras

Atbalstītās kameras var nodrošināt kameras entītiju, sīktēlus, tiešraides straumi, savienojuma statusu un iestatījumus, kas atbilst X-Sense lietotnei. Ja Home Assistant ir pieejams WebRTC ceļš, integrācija to var izmantot piemērotai tiešraides skatīšanai.

### Problēmu novēršana

Ja kāda entītija trūkst, vispirms X-Sense lietotnē pārbaudiet, vai ierīce tiešām rāda šo vērtību. Ja statuss paliek novecojis, pārlādējiet integrāciju tikai kā pagaidu pārbaudi un pievienojiet diagnostiku, kā arī atbilstošās Home Assistant žurnāla rindas.

### Ierīču darbība

- Stacijas un apakšierīces var ziņot atšķirīgas vērtību kopas. Tāpēc integrācija nepieņem, ka katrai stacijai obligāti jābūt apakšierīcei.
- Laika vērtības tiek pārveidotas salasāmā formā, ja ierīce sūta laiku X-Sense lietotnē izmantotajā formātā.
- Entītija netiek izveidota, ja ierīce par šo iespēju neziņo. Tas novērš maldinošas vadīklas Home Assistant vidē.

### Mākoņa noslodze

Integrācija cenšas saudzīgi izmantot X-Sense API. Ātras izmaiņas tiek saņemtas no MQTT ziņojumiem, bet mākoņa pieprasījumi tiek izmantoti tikai tad, kad tie vajadzīgi pieteikšanās, ierīču ielādes vai statusa atsvaidzināšanas nolūkiem.

### Problēmas ziņošana

Ziņojot par kļūdu, norādiet ierīces modeli, integrācijas versiju, vai pareizā vērtība ir redzama X-Sense lietotnē, un pievienojiet Home Assistant integrācijas diagnostiku. Noder arī īss apraksts, vai statuss nekad nemainās vai mainās tikai pēc integrācijas pārlādēšanas.

## Pilna atsauces sadaļa

### Konta iestatīšana detalizēti
- Home Assistant vajadzībām izmantojiet atsevišķu X-Sense kontu.
- No galvenā konta kopīgojiet tikai atbalstītās ierīces.
- Savienošana pārī, noņemšana, kopīgošana un pārvietošana paliek X-Sense lietotnē.
- Ja lietotne un Home Assistant izraksta viens otru, tie, iespējams, izmanto to pašu kontu.

### Atjauninājumi un API slodze
- Ātras stāvokļa izmaiņas tiek saņemtas ar MQTT shadow ziņām.
- Mākoņa pieprasījumi tiek izmantoti pieteikšanai, ierīču ielādei un stāvokļa atjaunošanai.
- Periodiska aptauja ir rezerve, ja MQTT ziņa nav saņemta.

### Entītijas un darbības
- Entītijas tiek izveidotas tikai laukiem, kurus X-Sense patiešām ziņo.
- Diagnostikas vērtības tiek atzīmētas kā diagnostika.
- Tests, klusēšana, ugunsdrošības treniņš un kameras pamodināšana ir tikai atbalstītiem modeļiem.

### Kameru atsauce
- Atbalstītās kameras var nodrošināt kameras entītiju, sīktēlu, tiešraidi un diagnostiku.
- WebRTC ceļš tiek izmantots tikai tad, ja tas ir pieejams Home Assistant.
- SD karte, maksājumi, programmaparatūra un konta pārvaldība paliek X-Sense lietotnē.

### Problēmu novēršanas kontrolsaraksts
- Ziņojumā norādiet modeli, integrācijas versiju, diagnostiku un attiecīgos žurnālus.

### Tvērums
- Integrācija nepievieno, nenoņem un nepārvieto ierīces starp mājām.

## Ierīču un entītiju kontrolsaraksts

### Galvenās ierīču saimes
- SBS50: bāzes stacija un stacijas līmeņa statuss.
- XS01-WX: Wi-Fi dūmu trauksme, arī kontiem bez atsevišķas apakšierīces.
- XS01-M, XS03-WX, XS0B-MR: dūmu trauksmju saimes.
- XC01-M, XC04-WX: CO trauksmju saimes.
- SC07-WX, XP0A-MR: kombinētās dūmu un CO saimes.
- XH02-M: karstuma trauksmes saime.
- SWS51: ūdens noplūdes detektora saime.
- STH51, STH0A, STH0B, STH0C: temperatūra un mitrums.
- SDS0A: durvju sensors.
- SMS0A: kustības sensors.
- SSC0A, SSC0B: atbalstītās kameras.

### Statusa lauki
- Trauksmes statuss tiek rādīts, ja X-Sense ziņo trauksmes lauku.
- Klusēšanas statuss tiek rādīts, ja X-Sense ziņo klusēšanas lauku.
- Baterijas statuss tiek rādīts, ja ierīce ziņo baterijas datus.
- RF un Wi-Fi signāls tiek rādīts, ja ierīce to ziņo.
- Kompaktās laika vērtības tiek pārvērstas lasāmos Home Assistant sensoros.

### Vadīklas un ziņojumi
- Slēdži tiek izveidoti tikai X-Sense ziņotajiem rakstāmajiem iestatījumiem.
- Pogas tiek izveidotas tikai lietotnes atbalstītām darbībām.
- Kameras vadīklas tiek izveidotas tikai tad, ja API tās atzīmē kā pieejamas.
- Problēmas ziņojumā norādiet precīzu modeli, integrācijas versiju, diagnostiku, žurnālus un vai vērtība mainās X-Sense lietotnē.

### Lietošanas piezīmes
- Pēc iestatīšanas pārbaudiet, vai ierīču nosaukumi un telpas sakrīt ar X-Sense lietotni.
- Ja trauksme, klusuma režīms vai LED statuss nemainās uzreiz, pagaidiet nākamo MQTT ziņojumu vai stāvokļa atjaunošanu.
- SBS50 stacijām pārbaudiet gan stacijas stāvokli, gan atsevišķās pakārtotās ierīces.
- XS01-WX var ziņot visu stāvokli tieši ierīcē, pat ja kontā nav atsevišķas pakārtotās ierīces.
- Kamerām izveidotās entītijas ir atkarīgas no iespējām, ko X-Sense mākonis atgriež konkrētajam kontam.
- Ja entītija netiek izveidota, vispirms salīdziniet vērtību ar X-Sense lietotni un pievienojiet diagnostiku.
- Integrācija ir paredzēta atbalstīto funkciju rādīšanai un vadībai, nevis savienošanas pārī vai ierīču pārvaldības aizstāšanai lietotnē.
