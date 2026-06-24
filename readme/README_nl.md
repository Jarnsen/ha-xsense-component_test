# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Overzicht
Deze integratie voor Home Assistant maakt het gebruik van X-Sense-apparaten binnen het slimme huis mogelijk. Het is gebaseerd op de originele code van [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) en is gepubliceerd met zijn toestemming en in samenwerking met hem.

Deze HACS-integratie wordt actief onderhouden voor gebruikers die bredere ondersteuning voor X-Sense-apparaten in Home Assistant willen. Ze wordt regelmatig bijgewerkt met nieuwe functies, extra apparaatondersteuning en oplossingen voor gemelde problemen.

<p align="center">
 <img src="https://github.com/user-attachments/assets/fbe7e69b-9204-4de4-a245-e0e2bdbd7f73" alt="Image">
</p>

## Functies
- Integratie van verschillende X-Sense-apparaten in Home Assistant.
- Ondersteuning voor automatiseringen op basis van X-Sense-sensorgegevens.
- Ondersteuning voor basisstations, rookmelders, koolmonoxidemelders, hittemelders, waterleksensoren, hygrometers, deursensoren, bewegingssensoren, lampen, keypads, brievenbussensoren, luisterapparaten, camera's en andere ondersteunde apparaten wanneer ze beschikbaar zijn in het X-Sense-account.
- Eenvoudige installatie via HACS (Home Assistant Community Store).

## Vereisten
- Een werkende Home Assistant-server (de nieuwste versie wordt aanbevolen).
- Een X-Sense-account met ondersteunde apparaten.
- HACS moet geïnstalleerd zijn in Home Assistant om de installatie van de integratie mogelijk te maken.

## Uitlegvideo
Voor een gedetailleerde handleiding voor het installeren en configureren van de integratie, kun je de volgende video bekijken:

[![X-Sense Home Assistant Integration](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## Voorbereiding
Voordat je de integratie installeert, moeten enkele voorbereidingen worden getroffen:

- **Maak een tweede account aan in de X-Sense-app (voor gebruik met Home Assistant)**: Aangezien het niet mogelijk is om met dezelfde account tegelijk aangemeld te zijn in de app en Home Assistant, raden we aan om een apart account te gebruiken voor Home Assistant. Hierdoor voorkom je dat je voortdurend wordt uitgelogd uit de app of Home Assistant. Het extra account zorgt voor een naadloze integratie en continu gebruik zonder onderbrekingen.

- **Deel de ondersteunde apparaten van het hoofdaccount met het Home Assistant-account**: Gebruik de X-Sense-app om **alleen de ondersteunde apparaten** met het nieuw aangemaakte account te delen. Zo kun je de integratie gemakkelijk gebruiken in Home Assistant, terwijl je de apparaten blijft beheren via je hoofdaccount.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## Installatie via HACS
1. **Open HACS in Home Assistant**:
  HACS is een belangrijke uitbreiding voor Home Assistant waarmee je eenvoudig aangepaste integraties kunt installeren.

  ![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **Ga naar de aangepaste repositories**:
  Navigeer in het HACS-dashboard naar de instellingen en voeg de repository toe als een aangepaste bron.

3. **Voeg de repository toe**:
  Voer de URL van de repository in: `https://github.com/Jarnsen/ha-xsense-component_test`

  ![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **Download en installeer de integratie**:
  Zoek de integratie in HACS, download en installeer deze. Na de installatie kan de configuratie worden uitgevoerd via de Home Assistant-interface.

  ![HACS repository selection screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)

  ![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## Configuratie
Na de installatie is een basisconfiguratie nodig om de integratie correct in te stellen:
- **Gebruikersnaam en wachtwoord**: Gebruik de inloggegevens van het nieuw aangemaakte X-Sense-account om de verbinding tot stand te brengen.

  ![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

- **Overzicht van apparaten**: Na succesvolle configuratie zijn de gedeelde apparaten beschikbaar in Home Assistant en kunnen ze worden gebruikt voor automatiseringen.

  ![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)
## Weergave in Home Assistant
Na een succesvolle installatie en configuratie is de integratie zichtbaar in Home Assistant. De apparaten zijn dan zichtbaar op het dashboard en kunnen worden gebruikt voor automatiseringen, meldingen en andere toepassingen.

![X-Sense integration screenshot](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/50bbafde-c94b-445e-9aa3-9c33d5f151d6)

____________________________________________________________

## Ondersteunde apparaten
Deze integratie ondersteunt meerdere X-Sense-apparaten. Beschikbare entiteiten hangen af van de velden die het apparaat en account melden. Bevestigde families en modellen zijn onder andere:
- **Basisstation (SBS50)**: Centrale hub voor X-Sense-apparaten.
- **Hittemelder (XH02-M)**: Detecteert ongewoon hoge temperaturen.
- **Koolmonoxidemelder (XC01-M; XC04-WX)**: Detecteert gevaarlijke CO-concentraties.
- **Rookmelder (XS01-M; XS01-WX; XS03-WX; XS0B-MR en verwante RF/iR-modellen)**: Vroege rookdetectie.
- **Combinatiemelder voor CO en rook (SC07-WX; XP0A-MR en verwante XP/SC-modellen)**: Detecteert CO en rook.
- **Waterleksensor (SWS51)**: Detecteert water op ongewenste plaatsen.
- **Hygrometer-thermometer (STH51, STH0A, STH0B, STH0C)**: Meet temperatuur en luchtvochtigheid.
- **Deursensor (SDS0A)** en **bewegingssensor (SMS0A)**: Worden getoond wanneer X-Sense deze status meldt.
- **Camera (SSC0A, SSC0B)**: Toont camera-entiteiten, miniaturen, livestream-URL's, statusdiagnose en app-ondersteunde instellingen wanneer apparaat en account dit ondersteunen.
- **Andere station-apparaten**: Licht, toetsenpaneel, brievenbus, luisterapparaat, oprit-alarm, slimme afleverbox, afstandsbediening en radongegevens worden getoond wanneer ondersteunde velden worden gemeld.

### Beschikbare entiteiten en acties
De integratie maakt Home Assistant-entiteiten alleen voor velden die echt aanwezig zijn in de X-Sense-cloud, MQTT-shadowberichten of camera-API's die aansluiten op het gedrag van de Android-app. Afhankelijk van het apparaat kan dit omvatten:

- Binaire sensoren voor alarm, mute, end-of-life, AC-break, wateralarm, temperatuuralarm, laden, beweging, deur, armed status, warning, reminder, light, PIR en keypad-status.
- Sensoren voor batterij, RF-signaal, Wi-Fi-signaal, firmware, temperatuur, luchtvochtigheid, CO-niveau, CO-piek, alarmvolume, spraakvolume, pieptoonvolume, herinneringsvolume, waarschuwingsdrempels, stilte-timers, leesbare tijdstempels, tijdzone en andere diagnostische gegevens.
- Supported camera setup and tuning controls are exposed in Home Assistant when the X-Sense app reports that the feature and account support it.
- Test-, mute-, fire-drill- en camera wake-knoppen voor modellen waarbij de X-Sense-app de bijbehorende actie aanbiedt.

Sommige entiteiten zijn diagnostisch of configuratiegerelateerd en worden zo gegroepeerd in Home Assistant. Als een apparaat een bepaald veld niet rapporteert, of als de X-Sense-app de functie als niet ondersteund markeert voor dat apparaat/account, wordt de bijbehorende entiteit niet aangemaakt. Apparaat koppelen, verwijderen, delen, account, betaling, firmware-update, SD-kaart formatteren en andere beheeracties blijven in de X-Sense-app.
____________________________________________________________

## Camera-livebeeld en AI-meldingen
De eenvoudigste manier is de meegeleverde blueprint. Importeer die met de knop hieronder, kies de camera-evententiteit `Motion` of `AI Detection` voor een camera met abonnement, en pas de meldingsactie zo nodig aan.

[![Blueprint importeren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2FJarnsen%2Fha-xsense-component_test%2Fmain%2Fblueprints%2Fautomation%2Fxsense%2Fcamera_ai_notification.yaml)

Motion en AI Detection zijn eenmalige events, geen aan/uit-statussen. Gebruik voor handmatige automatiseringen de Home Assistant-trigger `event.received` met de camera-entiteit `Motion` of `AI Detection`; `event_type` is alleen nodig om AI Detection met abonnement te beperken tot typen zoals `person`, `pet`, `vehicle`, `package`, `other` of `ai_detection`.

Voorbeeldautomatisering:

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
## Voorbeelden van automatiseringen
Met deze integratie kun je verschillende automatiseringen maken. Hier zijn enkele voorbeelden:

### Voorbeeld 1: Temperatuuralarm
Wanneer de temperatuur van een X-Sense-thermometer te hoog is, wordt een melding verstuurd:

```yaml
automation:
  - alias: "X-Sense Temperatuuralarm"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "De temperatuur overschrijdt 30 graden!"
```

### Voorbeeld 2: Waterleksensor-alarm
Wanneer de waterleksensor water detecteert, wordt een waarschuwing geactiveerd:

```yaml
automation:
  - alias: "Waterleksensor Alarm"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "Waterlekkage gedetecteerd!"
```

____________________________________________________________

## Wij hebben jouw hulp nodig
We zijn altijd op zoek naar ondersteuning om deze integratie verder te ontwikkelen en te verbeteren. Hier zijn een paar manieren waarop je kunt helpen:

1. **Testen van apparaten**: Als je een X-Sense-apparaat hebt dat werkt met de integratie, laat het ons weten, zodat we het aan de lijst met ondersteunde apparaten kunnen toevoegen.

2. **Feedback over niet-ondersteunde apparaten**: Als een apparaat niet werkt, geef ons dan feedback, zodat we ondersteuning kunnen bieden of het apparaat in toekomstige versies van de integratie kunnen opnemen.

3. **Delen van apparaten voor tests**: De beste manier om nieuwe apparaten te testen, is door het apparaat te delen via de X-Sense-app. Zo kunnen we ervoor zorgen dat zoveel mogelijk apparaten worden ondersteund.

4. **Gemeenschapssteun**: Neem deel aan discussies in onze gemeenschap. Of je nu suggesties hebt voor verbeteringen of andere gebruikers helpt met hun installatie - alle hulp is welkom!

Voor discussies en ondersteuning kun je ons bereiken op onze Discord-server of in het Home Assistant-forum:

[Discord](https://discord.gg/5phHHgGb3V)

[Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

## Volledige referentie

### Account en installatie
- Gebruik een apart X-Sense-account voor Home Assistant.
- Deel alleen ondersteunde apparaten vanuit het hoofdaccount.
- Koppelen, verwijderen, delen, firmware, account, betalingen en SD-kaartbeheer blijven in de X-Sense-app.

### Updates en API-gebruik
- Snelle statuswijzigingen komen via MQTT-shadowberichten binnen.
- Cloudverzoeken worden gebruikt voor aanmelden, apparaatdetectie, cameragegevens en statusherstel.
- Periodiek pollen is alleen een fallback wanneer een live-update ontbreekt.

### Entiteiten, camera's en probleemoplossing
- Entiteiten worden alleen gemaakt voor velden die X-Sense echt rapporteert.
- Camera-entiteiten en bediening worden alleen gemaakt wanneer de Android-app-uitgelijnde API ondersteuning meldt voor dat account en model.
- Ontbreekt een waarde, vergelijk dan eerst met de X-Sense-app en voeg daarna diagnostiek en relevante Home Assistant-logboeken toe.

## Checklist voor apparaten en entiteiten

### Belangrijkste apparaatfamilies
- SBS50-basisstation, XS-rookmelders, XC-CO-melders, SC/XP-combinatiemelders, XH-hittealarmen, SWS-waterleksensoren, STH-temperatuur/vochtigheidssensoren, SDS-deursensoren, SMS-bewegingssensoren, SSC-camera's en andere gemelde X-Sense-families worden verwerkt wanneer de API hun velden aanbiedt.

### Statusvelden
- Alarm, dempen, batterij, RF/Wi-Fi-signaal, temperatuur, luchtvochtigheid, CO, water, beweging, deur, licht, herinneringen, waarschuwingen en leesbare tijdstempels verschijnen alleen wanneer X-Sense ze rapporteert.

### Bediening en rapportage
- Schakelaars, keuzelijsten, nummers en knoppen worden alleen gemaakt voor schrijfbare instellingen en acties die apparaat/account aanbieden.
- Een goede bugmelding bevat exact model, integratieversie, diagnostiek, logs en of de waarde correct verandert in de X-Sense-app.
