# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Översikt
Den här Home Assistant-integrationen gör X-Sense-enheter tillgängliga i ditt smarta hem. Den bygger på Theo Snels ursprungliga arbete och installeras via HACS.

Vi rekommenderar att du skapar ett separat X-Sense-konto för Home Assistant och bara delar de enheter som stöds från huvudkontot.

## Installation
Lägg till `https://github.com/Jarnsen/ha-xsense-component_test` som anpassat repository i HACS, ladda ned integrationen, följ HACS anvisning för omstart och konfigurera sedan integrationen med X-Sense-kontot för Home Assistant.


## Detaljerad installation med skärmbilder

1. Skapa ett separat X-Sense-konto för Home Assistant och dela endast enheter som stöds från huvudkontot.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

2. Lägg till `https://github.com/Jarnsen/ha-xsense-component_test` som ett anpassat repository i HACS.

![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

3. Ladda ned och installera integrationen, starta om Home Assistant och konfigurera den sedan med det nya X-Sense-kontot.

![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

4. Efter lyckad installation visas de delade enheterna på enhetssidan i Home Assistant.

![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)

5. Parkoppling, borttagning, firmware, betalningar, SD-kort och kontohantering stannar i X-Sense-appen.

## Enheter som stöds
Basstationer, brandvarnare, CO-detektorer, värmelarm, vattenläckagedetektorer, hygrometrar, dörr- och rörelsesensorer, lampor, knappsatser, brevlådesensorer, lyssnarenheter och kameror stöds när de rapporteras av X-Sense-kontot.

Bekräftade modellfamiljer omfattar: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## Entiteter och åtgärder
Integrationen skapar bara entiteter för data som enheten faktiskt rapporterar. Det kan omfatta larm, tyst läge, batteri, signal, temperatur, luftfuktighet, CO, läsbara tidsfält, kamerainställningar, LED-brytare samt knappar för test, tyst läge och brandövning.

Enhetshantering, delning, borttagning, firmware, konton och betalningar ligger kvar i X-Sense-appen. Använd Discord eller Home Assistant-forumet för diskussioner.

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
## Exempel på automatiseringar
```yaml
automation:
  - alias: "X-Sense temperaturvarning"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "Temperaturen överstiger 30 grader!"
```

```yaml
automation:
  - alias: "Vattenläckagelarm"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "Vattenläckage upptäckt!"
```

## Support
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

## Fler detaljer

### Kontoinställning

Det rekommenderas att använda ett separat X-Sense-konto för Home Assistant och bara dela de enheter som stöds och som ska visas i Home Assistant. Integrationen parkopplar inte, tar inte bort och flyttar inte enheter mellan hem. Sådan enhetshantering hör fortfarande hemma i den officiella X-Sense-appen.

### Statusuppdateringar

Integrationen använder MQTT shadow-meddelanden för snabba statusändringar och försiktig periodisk molnhämtning för att uppdatera data. Status som rapporteras av en station uppdateras på stationen, medan status från en underenhet uppdateras på den aktuella enheten, så att larm och sensorer inte fastnar på gamla värden.

### Tillgängliga entiteter

Beroende på modell kan rök-, CO-, vatten-, temperatur-, rörelse- och dörrlarm visas, liksom larmtystning, slut på livslängd, laddning, påminnelsestatus, ljusstatus och andra diagnostiska binära sensorer. Sensorer kan omfatta batteri, RF- eller Wi-Fi-signal, firmware, temperatur, luftfuktighet, CO-nivå, CO-toppvärde, volym, tröskelvärden, läsbara tider, tidszon och annan diagnostik. Brytare, val och numeriska värden skapas bara när enheten faktiskt stöder dem.

### Kameror

Kameror som stöds kan ge kameraentitet, miniatyrbilder, liveström, anslutningsstatus och inställningar som följer X-Sense-appen. Om Home Assistant har en WebRTC-väg tillgänglig kan integrationen använda den för lämplig livevisning.

### Felsökning

Om en entitet saknas bör du först kontrollera i X-Sense-appen att enheten verkligen rapporterar det värdet. Om statusen förblir gammal kan du läsa om integrationen som ett tillfälligt test och bifoga diagnostik samt relevanta loggrader från Home Assistant i rapporten.

### Enhetsbeteende

- Stationer och underenheter kan rapportera olika uppsättningar värden. Integrationen antar därför inte att varje station måste ha en underenhet.
- Tidsvärden konverteras till läsbar form när enheten skickar tid i det format som X-Sense-appen använder.
- En entitet skapas inte om enheten inte rapporterar funktionen. Det undviker missvisande kontroller i Home Assistant.

### Molnbelastning

Integrationen försöker använda X-Sense-API:t sparsamt. Snabba ändringar hämtas från MQTT-meddelanden, och molnanrop används bara där de behövs för inloggning, inläsning av enheter eller uppdatering av status.

### Rapportera problem

När du rapporterar ett fel, ange enhetsmodell, integrationsversion, om rätt värde visas i X-Sense-appen och bifoga integrationsdiagnostik från Home Assistant. Det hjälper också att kort beskriva om status aldrig ändras, eller först ändras efter att integrationen lästs in på nytt.

## Fullständig referens

### Kontoinställning i detalj
- Använd ett separat X-Sense-konto för Home Assistant.
- Dela endast de enheter som stöds från huvudkontot.
- Parkoppling, borttagning, delning och flytt av enheter sker i X-Sense-appen.
- Om appen och Home Assistant loggar ut varandra använder de sannolikt samma konto.

### Uppdateringar och API-belastning
- Snabba statusändringar tas emot via MQTT shadow-meddelanden.
- Molnförfrågningar används för inloggning, enhetsladdning och statusuppdatering.
- Periodisk polling är reserv när ett MQTT-meddelande saknas.

### Entiteter och åtgärder
- Entiteter skapas endast för fält som X-Sense faktiskt rapporterar.
- Diagnostiska värden markeras som diagnostik.
- Test, tystning, brandövning och kameraväckning visas bara för modeller som stöds.

### Kamerareferens
- Kameror som stöds kan ge kameraentitet, miniatyrbild, liveström och diagnostik.
- WebRTC-vägen används bara om den är tillgänglig i Home Assistant.
- SD-kort, betalningar, firmware och kontoadministration hanteras i X-Sense-appen.

### Felsökningschecklista
- Felrapporter bör innehålla modell, integrationsversion, diagnostik och relevanta loggar.

### Omfattning
- Integrationen lägger inte till, tar bort eller flyttar enheter mellan hem.

## Checklista för enheter och entiteter

### Centrala enhetsfamiljer
- SBS50: basstation och status på stationsnivå.
- XS01-WX: Wi-Fi-brandvarnare, även konton utan separat underenhet.
- XS01-M, XS03-WX, XS0B-MR: brandvarnarfamiljer.
- XC01-M, XC04-WX: CO-larmfamiljer.
- SC07-WX, XP0A-MR: kombinerade rök- och CO-familjer.
- XH02-M: värmelarmfamilj.
- SWS51: vattenläckagedetektorfamilj.
- STH51, STH0A, STH0B, STH0C: temperatur och luftfuktighet.
- SDS0A: dörrsensor.
- SMS0A: rörelsesensor.
- SSC0A, SSC0B: kameror som stöds.

### Statusfält
- Larmstatus visas när X-Sense rapporterar ett larmfält.
- Tystningsstatus visas när X-Sense rapporterar ett tystningsfält.
- Batteristatus visas när enheten rapporterar batteridata.
- RF- och Wi-Fi-signal visas när enheten rapporterar dem.
- Kompakta tidsvärden konverteras till läsbara Home Assistant-sensorer.

### Kontroller och rapporter
- Brytare skapas endast för skrivbara inställningar rapporterade av X-Sense.
- Knappar skapas endast för åtgärder som stöds av appen.
- Kamerakontroller skapas endast när API:et markerar dem som tillgängliga.
- Felrapporter bör innehålla exakt modell, integrationsversion, diagnostik, loggar och om värdet ändras i X-Sense-appen.

### Driftanteckningar
- Efter installationen bör enhetsnamn och rum kontrolleras mot X-Sense-appen.
- Om larm, tyst läge eller LED inte ändras direkt, vänta på nästa MQTT-meddelande eller statusuppdatering.
- För SBS50-stationer bör både stationsstatus och varje underenhet kontrolleras.
- För XS01-WX kan hela statusen rapporteras direkt på enheten, även utan en separat underenhet på kontot.
- För kameror beror de entiteter som skapas på vilka funktioner X-Sense-molnet returnerar för kontot.
- Om en entitet inte skapas, jämför först värdet med X-Sense-appen och bifoga diagnostik.
- Integrationen är avsedd att visa och styra funktioner som stöds, inte ersätta parkoppling eller enhetshantering i appen.
