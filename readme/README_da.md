# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Oversigt
Denne Home Assistant-integration gør X-Sense-enheder tilgængelige i dit smart home. Den bygger på Theo Snels oprindelige arbejde og installeres via HACS.

Vi anbefaler at oprette en separat X-Sense-konto til Home Assistant og kun dele de understøttede enheder fra hovedkontoen.

## Installation
Tilføj `https://github.com/Jarnsen/ha-xsense-component_test` som brugerdefineret repository i HACS, download integrationen, følg HACS' genstartsvejledning, og konfigurer derefter integrationen med X-Sense-kontoen til Home Assistant.


## Detaljeret opsætning med skærmbilleder

1. Opret en separat X-Sense-konto til Home Assistant, og del kun understøttede enheder fra hovedkontoen.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

2. Tilføj `https://github.com/Jarnsen/ha-xsense-component_test` som et brugerdefineret repository i HACS.

![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

3. Download og installer integrationen, genstart Home Assistant, og konfigurer den derefter med den nye X-Sense-konto.

![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

4. Efter en vellykket opsætning vises de delte enheder på enhedssiden i Home Assistant.

![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)

5. Parring, fjernelse, firmware, betalinger, SD-kort og kontostyring forbliver i X-Sense-appen.

## Understøttede enheder
Understøttet er basestationer, røgalarmer, CO-detektorer, varmealarmer, vandlækagedetektorer, hygrometre, dør- og bevægelsessensorer, lys, tastaturer, postkassesensorer, lytteenheder og understøttede kameraer, når X-Sense-kontoen rapporterer dem.

Bekræftede modelfamilier omfatter: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## Entiteter og handlinger
Integrationen opretter kun entiteter for data, som enheden faktisk rapporterer. Det kan være alarmer, lydløs status, batteri, signal, temperatur, fugtighed, CO, læsbare tidsfelter, kameraindstillinger, LED-kontakter samt knapper til test, lydløs og brandøvelse.

Enhedsadministration, deling, fjernelse, firmware, konti og betalinger forbliver i X-Sense-appen. Brug Discord eller Home Assistant-forummet til diskussioner.

## Camera AI Notifications
Supported cameras create an `AI Detection` event entity, such as `event.front_camera_ai_detection`. Use this `event.*` entity for notification automations, and replace the sample entity ID with the actual entity ID shown in your Home Assistant instance.

The easiest UI path is the included blueprint. Use the button below to import it, select the camera `AI Detection` event entity, leave Detection types selected to notify for every AI event, then keep or replace the default notification action.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2FJarnsen%2Fha-xsense-component_test%2Fmain%2Fblueprints%2Fautomation%2Fxsense%2Fcamera_ai_notification.yaml)

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
## Eksempler på automatiseringer
```yaml
automation:
  - alias: "X-Sense temperaturadvarsel"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "Temperaturen er over 30 grader!"
```

```yaml
automation:
  - alias: "Vandlækagealarm"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "Vandlækage registreret!"
```

## Support
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

## Flere detaljer

### Kontoopsætning

Det anbefales at bruge en separat X-Sense-konto til Home Assistant og kun dele de understøttede enheder, der skal vises i Home Assistant. Integrationen parrer, fjerner eller flytter ikke enheder mellem hjem. Den slags enhedsstyring hører fortsat hjemme i den officielle X-Sense-app.

### Statusopdateringer

Integrationen bruger MQTT shadow-meddelelser til hurtige statusændringer og forsigtig periodisk cloud-hentning til at opfriske data. Status fra en station gemmes på stationen, mens status fra en underenhed gemmes på den konkrete enhed, så alarmer og sensorer ikke bliver hængende på gamle værdier.

### Tilgængelige enheder

Afhængigt af modellen kan der vises røg-, CO-, vand-, temperatur-, bevægelses- og døralarmer, alarmdæmpning, levetidsudløb, opladning, påmindelsesstatus, lysstatus og andre diagnostiske binære sensorer. Sensorer kan omfatte batteri, RF- eller Wi-Fi-signal, firmware, temperatur, fugtighed, CO-niveau, CO-topværdi, lydstyrke, tærskler, læsbare tidspunkter, tidszone og anden diagnostik. Kontakter, valg og talfelter oprettes kun, når enheden faktisk understøtter dem.

### Kameraer

Understøttede kameraer kan levere kameraenhed, miniaturebilleder, livestream, forbindelsesstatus og indstillinger, der svarer til dem i X-Sense-appen. Hvis Home Assistant har en WebRTC-sti til rådighed, kan integrationen bruge den til egnet livevisning.

### Fejlfinding

Hvis en enhed mangler, skal du først kontrollere i X-Sense-appen, at den pågældende værdi findes for enheden. Hvis status ikke opdateres, kan du genindlæse integrationen som en midlertidig test og vedhæfte diagnostik samt relevante Home Assistant-loglinjer til fejlrapporten.

### Enhedsadfærd

- Stationer og underenheder kan rapportere forskellige sæt værdier. Integrationen antager derfor ikke, at hver station skal have en underenhed.
- Tidsværdier konverteres til læsbare værdier, når enheden sender tid i det format, X-Sense-appen bruger.
- En entitet vises ikke, hvis enheden ikke rapporterer funktionen. Det undgår vildledende kontroller i Home Assistant.

### Cloudbelastning

Integrationen forsøger at være skånsom mod X-Sense-API'et. Hurtige ændringer hentes fra MQTT-meddelelser, og cloudkald bruges kun, hvor de er nødvendige til login, indlæsning af enheder eller statusopdatering.

### Rapportering af problemer

Når du rapporterer en fejl, så angiv enhedsmodellen, integrationsversionen, om den korrekte værdi vises i X-Sense-appen, og vedhæft integrationsdiagnostik fra Home Assistant. Det hjælper også at beskrive, om status aldrig ændrer sig, eller først ændrer sig efter genindlæsning af integrationen.

## Komplet reference

### Kontoopsætning i detaljer
- Brug en separat X-Sense-konto til Home Assistant.
- Del kun understøttede enheder fra hovedkontoen.
- Parring, fjernelse, deling og flytning af enheder bliver i X-Sense-appen.
- Hvis appen og Home Assistant logger hinanden ud, bruger de sandsynligvis samme konto.

### Opdateringer og API-belastning
- Hurtige statusændringer modtages via MQTT shadow-beskeder.
- Cloudforespørgsler bruges til login, enhedsindlæsning og statusopdatering.
- Periodisk polling er kun fallback, når en MQTT-besked mangler.

### Entiteter og handlinger
- Entiteter oprettes kun for felter, som X-Sense faktisk rapporterer.
- Diagnostiske værdier markeres som diagnostik.
- Test, mute, brandøvelse og kameravækning vises kun for understøttede modeller.

### Kamerareference
- Understøttede kameraer kan vise kameraentitet, miniaturebillede, live stream og diagnostik.
- WebRTC bruges kun, når stien er tilgængelig i Home Assistant.
- SD-kort, betalinger, firmware og kontoadministration bliver i X-Sense-appen.

### Tjekliste til fejlfinding
- Ved fejlrapporter skal model, integrationsversion, diagnostik og relevante logge medtages.

### Afgrænsning
- Integrationen tilføjer, sletter eller flytter ikke enheder mellem hjem.

## Tjekliste for enheder og entiteter

### Centrale enhedsfamilier
- SBS50: base station og status på stationsniveau.
- XS01-WX: Wi-Fi-røgalarm, også konti uden separat underenhed.
- XS01-M, XS03-WX, XS0B-MR: røgalarmfamilier.
- XC01-M, XC04-WX: CO-alarmfamilier.
- SC07-WX, XP0A-MR: kombinerede røg- og CO-familier.
- XH02-M: varmealarmfamilie.
- SWS51: vandlækagefamilie.
- STH51, STH0A, STH0B, STH0C: temperatur og fugtighed.
- SDS0A: dørsensor.
- SMS0A: bevægelsessensor.
- SSC0A, SSC0B: understøttede kameraer.

### Statusfelter
- Alarmstatus vises, når X-Sense rapporterer et alarmfelt.
- Mute-status vises, når X-Sense rapporterer et mute-felt.
- Batteristatus vises, når enheden rapporterer batteridata.
- RF- og Wi-Fi-signal vises, når enheden rapporterer dem.
- Kompakte tidsværdier konverteres til læsbare Home Assistant-sensorer.

### Kontroller og rapporter
- Switches oprettes kun for skrivbare indstillinger rapporteret af X-Sense.
- Knapper oprettes kun for app-understøttede handlinger.
- Kamerakontroller oprettes kun, når API'et markerer dem som tilgængelige.
- Fejlrapporter bør indeholde model, integrationsversion, diagnostik, logge og om værdien ændres i X-Sense-appen.

### Driftsnoter
- Efter opsætning bør enhederne kontrolleres mod navnene og rummene i X-Sense-appen.
- Hvis alarm, lydløs tilstand eller LED ikke ændres med det samme, skal du vente på den næste MQTT-besked eller statusopdatering.
- For SBS50-stationer skal både stationsstatus og de enkelte underenheder kontrolleres.
- For XS01-WX kan hele status være rapporteret direkte på enheden, selv uden en separat underenhed på kontoen.
- For kameraer afhænger de oprettede enheder af de funktioner, X-Sense-cloud returnerer for kontoen.
- Hvis en enhed ikke oprettes, skal værdien først sammenlignes med X-Sense-appen, og diagnostik bør vedlægges.
- Integrationen er beregnet til at vise og styre understøttede funktioner, ikke til at erstatte parring eller enhedsadministration i appen.
