# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Oversikt
Denne Home Assistant-integrasjonen gjør X-Sense-enheter tilgjengelige i smarthuset. Den bygger på Theo Snels opprinnelige arbeid og installeres via HACS.

Vi anbefaler å opprette en egen X-Sense-konto for Home Assistant og bare dele støttede enheter fra hovedkontoen.

## Installasjon
Legg til `https://github.com/Jarnsen/ha-xsense-component_test` som egendefinert repository i HACS, last ned integrasjonen, følg HACS-instruksjonene for omstart og konfigurer den med X-Sense-kontoen for Home Assistant.


## Detaljert oppsett med skjermbilder

1. Opprett en separat X-Sense-konto for Home Assistant, og del bare støttede enheter fra hovedkontoen.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

2. Legg til `https://github.com/Jarnsen/ha-xsense-component_test` som et egendefinert repository i HACS.

![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

3. Last ned og installer integrasjonen, start Home Assistant på nytt, og konfigurer den deretter med den nye X-Sense-kontoen.

![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

4. Etter vellykket oppsett vises de delte enhetene på enhetssiden i Home Assistant.

![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)

5. Paring, fjerning, firmware, betalinger, SD-kort og kontoadministrasjon forblir i X-Sense-appen.

## Støttede enheter
Basestasjoner, røykvarslere, CO-detektorer, varmealarmer, vannlekkasjedetektorer, hygrometre, dør- og bevegelsessensorer, lys, tastaturer, postkassesensorer, lytteenheter og støttede kameraer støttes når X-Sense-kontoen rapporterer dem.

Bekreftede modellfamilier inkluderer: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## Entiteter og handlinger
Integrasjonen oppretter bare entiteter for data enheten faktisk rapporterer. Det kan omfatte alarmer, demping, batteri, signal, temperatur, fuktighet, CO, lesbare tidsfelt, kamerainnstillinger, LED-brytere og knapper for test, demping og brannøvelse.

Enhetsadministrasjon, deling, fjerning, firmware, kontoer og betalinger forblir i X-Sense-appen. Bruk Discord eller Home Assistant-forumet for diskusjoner.

## Camera Live View and AI Notifications
Supported cameras use native Home Assistant WebRTC for live video and audio. They also create an `AI Detection` event entity, such as `event.front_camera_ai_detection`. Use this `event.*` entity for notification automations, and replace the sample entity ID with the actual entity ID shown in your Home Assistant instance.

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
  - alias: "X-Sense temperaturvarsel"
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
  - alias: "Vannlekkasjealarm"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "Vannlekkasje oppdaget!"
```

## Støtte
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

## Flere detaljer

### Kontooppsett

Det anbefales å bruke en egen X-Sense-konto for Home Assistant og bare dele de støttede enhetene som skal vises i Home Assistant. Integrasjonen parer ikke, fjerner ikke og flytter ikke enheter mellom hjem. Slik enhetsadministrasjon hører fortsatt hjemme i den offisielle X-Sense-appen.

### Statusoppdateringer

Integrasjonen bruker MQTT shadow-meldinger for raske statusendringer og forsiktig periodisk skyhenting for å friske opp data. Status som rapporteres av en stasjon, lagres på stasjonen, mens status fra en underenhet lagres på den aktuelle enheten, slik at alarmer og sensorer ikke blir stående med gamle verdier.

### Tilgjengelige enheter

Avhengig av modell kan det vises røyk-, CO-, vann-, temperatur-, bevegelses- og døralarmer, alarmdemping, levetidsslutt, lading, påminnelsesstatus, lysstatus og andre diagnostiske binærsensorer. Sensorer kan omfatte batteri, RF- eller Wi-Fi-signal, fastvare, temperatur, fuktighet, CO-nivå, CO-toppverdi, volum, terskler, lesbare tidspunkter, tidssone og annen diagnostikk. Brytere, valg og tallfelt opprettes bare når enheten faktisk støtter dem.

### Kameraer

Støttede kameraer kan gi kameraenhet, miniatyrbilder, direktestrøm, tilkoblingsstatus og innstillinger som samsvarer med X-Sense-appen. Hvis Home Assistant har en WebRTC-sti tilgjengelig, kan integrasjonen bruke den for egnet direktevisning.

### Feilsøking

Hvis en enhet mangler, bør du først kontrollere i X-Sense-appen at den aktuelle verdien faktisk vises for enheten. Hvis statusen ikke oppdateres, kan du laste integrasjonen på nytt som en midlertidig test og legge ved diagnostikk samt relevante logglinjer fra Home Assistant i rapporten.

### Enhetsatferd

- Stasjoner og underenheter kan rapportere ulike sett med verdier. Integrasjonen antar derfor ikke at hver stasjon må ha en underenhet.
- Tidsverdier konverteres til lesbar form når enheten sender tid i formatet X-Sense-appen bruker.
- En entitet opprettes ikke hvis enheten ikke rapporterer funksjonen. Det unngår misvisende kontroller i Home Assistant.

### Skybelastning

Integrasjonen prøver å være skånsom mot X-Sense-API-et. Raske endringer hentes fra MQTT-meldinger, og skykall brukes bare der de trengs for innlogging, innlasting av enheter eller oppfrisking av status.

### Rapportering av problemer

Når du rapporterer en feil, oppgi enhetsmodell, integrasjonsversjon, om riktig verdi vises i X-Sense-appen, og legg ved integrasjonsdiagnostikk fra Home Assistant. Det hjelper også å beskrive kort om status aldri endres, eller først endres etter at integrasjonen lastes inn på nytt.

## Full referanse

### Kontooppsett i detalj
- Bruk en egen X-Sense-konto for Home Assistant.
- Del bare støttede enheter fra hovedkontoen.
- Paring, fjerning, deling og flytting av enheter blir i X-Sense-appen.
- Hvis appen og Home Assistant logger hverandre ut, bruker de trolig samme konto.

### Oppdateringer og API-belastning
- Raske statusendringer mottas via MQTT shadow-meldinger.
- Skyforespørsler brukes til innlogging, enhetslasting og statusoppdatering.
- Periodisk polling er reserve hvis en MQTT-melding mangler.

### Entiteter og handlinger
- Entiteter opprettes bare for felt som X-Sense faktisk rapporterer.
- Diagnostiske verdier merkes som diagnostikk.
- Test, demping, brannøvelse og kameravekking vises bare for støttede modeller.

### Kamerareferanse
- Støttede kameraer kan gi kameraentitet, miniatyrbilde, direktestrøm og diagnostikk.
- WebRTC-stien brukes bare hvis den er tilgjengelig i Home Assistant.
- SD-kort, betalinger, fastvare og kontoadministrasjon håndteres i X-Sense-appen.

### Sjekkliste for feilsøking
- Feilrapporter bør inneholde modell, integrasjonsversjon, diagnostikk og relevante logger.

### Omfang
- Integrasjonen legger ikke til, fjerner eller flytter enheter mellom hjem.

## Sjekkliste for enheter og entiteter

### Viktige enhetsfamilier
- SBS50: basestasjon og status på stasjonsnivå.
- XS01-WX: Wi-Fi-røykvarsler, også kontoer uten separat underenhet.
- XS01-M, XS03-WX, XS0B-MR: røykvarslerfamilier.
- XC01-M, XC04-WX: CO-varslerfamilier.
- SC07-WX, XP0A-MR: kombinerte røyk- og CO-familier.
- XH02-M: varmevarslerfamilie.
- SWS51: vannlekkasjedetektorfamilie.
- STH51, STH0A, STH0B, STH0C: temperatur og fuktighet.
- SDS0A: dørsensor.
- SMS0A: bevegelsessensor.
- SSC0A, SSC0B: støttede kameraer.

### Statusfelt
- Alarmstatus vises når X-Sense rapporterer et alarmfelt.
- Dempestatus vises når X-Sense rapporterer et dempefelt.
- Batteristatus vises når enheten rapporterer batteridata.
- RF- og Wi-Fi-signal vises når enheten rapporterer dem.
- Kompakte tidsverdier konverteres til lesbare Home Assistant-sensorer.

### Kontroller og rapporter
- Brytere opprettes bare for skrivbare innstillinger rapportert av X-Sense.
- Knapper opprettes bare for handlinger støttet av appen.
- Kamerakontroller opprettes bare når API-et markerer dem som tilgjengelige.
- Feilrapporter bør inneholde modell, integrasjonsversjon, diagnostikk, logger og om verdien endres i X-Sense-appen.

### Driftsmerknader
- Etter oppsett bør enhetsnavn og rom kontrolleres mot X-Sense-appen.
- Hvis alarm, demping eller LED ikke endres med en gang, vent på neste MQTT-melding eller statusoppdatering.
- For SBS50-stasjoner bør både stasjonsstatus og de enkelte underenhetene kontrolleres.
- For XS01-WX kan hele statusen rapporteres direkte på enheten, også uten en egen underenhet på kontoen.
- For kameraer avhenger entitetene som opprettes av hvilke funksjoner X-Sense-skyen returnerer for kontoen.
- Hvis en entitet ikke opprettes, sammenlign først verdien med X-Sense-appen og legg ved diagnostikk.
- Integrasjonen er ment å vise og styre støttede funksjoner, ikke erstatte paring eller enhetsadministrasjon i appen.
