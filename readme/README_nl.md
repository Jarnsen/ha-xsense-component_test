# ha-xsense-component_test

## Overzicht
Deze integratie voor Home Assistant maakt het mogelijk om Xsense-apparaten binnen het smart home-systeem te gebruiken. De integratie is gebaseerd op de originele code van [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) en is met zijn toestemming en in samenwerking met hem uitgebracht.

Totdat er een officiële Home Assistant-integratie van Theo beschikbaar is, wordt deze HACS-integratie gebruikt en regelmatig bijgewerkt om nieuwe functies toe te voegen en bestaande problemen op te lossen. Deze integratie stelt gebruikers in staat om hun Xsense-apparaten eenvoudig in Home Assistant te integreren en te gebruiken voor verschillende automatiseringen en monitoring.

![images](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/c49a97f2-5e10-4129-82bc-1d647adc0895)

## Functies
- Integratie van verschillende Xsense-apparaten in Home Assistant.
- Ondersteuning voor automatiseringen op basis van Xsense-sensorgegevens.
- Ondersteuning voor de volgende apparaattypen: basistations, rookmelders, koolmonoxidemelders, hittesensoren, watermelders en hygrometers.
- Eenvoudige installatie via HACS (Home Assistant Community Store).

## Vereisten
- Een werkende Home Assistant-server (de nieuwste versie wordt aanbevolen).
- Een Xsense-account met ondersteunde apparaten.
- HACS moet in Home Assistant zijn geïnstalleerd om de installatie van de integratie mogelijk te maken.

## How-to-Video
Voor een gedetailleerde handleiding over de installatie en configuratie van de integratie kun je de volgende video bekijken:

[![X-Sense Home Assistant Integration](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## Voorbereiding
Voordat je de integratie installeert, zijn er enkele voorbereidingen nodig:

- **Maak een tweede account aan in de X-Sense-app (voor gebruik met Home Assistant)**: Omdat het niet mogelijk is om tegelijkertijd in de app en in Home Assistant met hetzelfde account aangemeld te zijn, raden we aan om een apart account voor Home Assistant te gebruiken. Dit voorkomt dat je steeds afgemeld wordt tussen de app en Home Assistant. Het extra account zorgt voor een naadloze integratie en gebruik zonder onderbrekingen door herhaald in- en uitloggen.

- **Deel de ondersteunde apparaten van het hoofdaccount met het Home Assistant-account**: Gebruik de X-Sense-app om **alleen de ondersteunde apparaten** te delen met het nieuw aangemaakte account. Op deze manier kun je de integratie eenvoudig in Home Assistant gebruiken, terwijl het beheer via je hoofdaccount plaatsvindt.

![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## Installatie via HACS
1. **Open HACS in Home Assistant**:
   HACS is een belangrijke uitbreiding voor Home Assistant, waarmee je eenvoudig aangepaste integraties kunt installeren.

   ![Download (1)](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **Ga naar de aangepaste repositories**:
   Navigeer in het HACS-dashboard naar de instellingen en voeg de repository toe als aangepaste bron.

3. **Voeg de repository toe**:
   Voer de URL van de repository in: `https://github.com/Jarnsen/ha-xsense-component_test`

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **Download en installeer de integratie**:
   Zoek de integratie in HACS, download deze en installeer deze. Na de installatie kan de configuratie via de Home Assistant-interface worden uitgevoerd.

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)
   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## Configuratie
Na de installatie is een basisconfiguratie nodig om de integratie correct in te stellen:
- **Gebruikersnaam en wachtwoord**: Gebruik de inloggegevens van het nieuw aangemaakte X-Sense-account om de verbinding tot stand te brengen.
- **Apparaatoverzicht**: Na succesvolle configuratie worden de gedeelde apparaten beschikbaar in Home Assistant en kunnen deze worden gebruikt voor automatiseringen.

## Weergave in Home Assistant
Na een succesvolle installatie en configuratie is de integratie zichtbaar in Home Assistant. De apparaten zijn dan zichtbaar op het dashboard en kunnen worden gebruikt voor automatiseringen, meldingen en andere toepassingen.

![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/50bbafde-c94b-445e-9aa3-9c33d5f151d6)

____________________________________________________________

## Ondersteunde apparaten
Deze integratie ondersteunt verschillende Xsense-apparaten. Hieronder vind je een lijst van de momenteel bevestigde en geteste apparaten:
- **Basisstation (SBS50)**: Centrale hub voor de Xsense-apparaten.
- **Hittesensor (XH02-M)**: Detectie van ongebruikelijk hoge temperaturen.
- **Koolmonoxidemelder (XC01-M; XC04-WX)**: Meldt gevaarlijke concentraties koolmonoxide.
- **Rookmelder (XS01-M, WX; XS03-WX; XS0B-MR)**: Vroege detectie van rookontwikkeling.
- **Koolmonoxide- en rookcombinatiemelder (SC07-WX; XP0A-MR (gedeeltelijk ondersteund))**: Gecombineerde apparaten voor de detectie van koolmonoxide en rook.
- **Watermelder (SWS51)**: Meldt de aanwezigheid van water op ongewenste plekken.
- **Hygrometer-thermometer (STH51)**: Bewaking van temperatuur en luchtvochtigheid.

Deze apparaten kunnen, na integratie in Home Assistant, worden gebruikt voor automatiseringen en waarschuwingsmeldingen.

____________________________________________________________

## Voorbeelden van automatiseringen
Met deze integratie kunnen verschillende automatiseringen worden gemaakt. Hier zijn enkele voorbeelden:

### Voorbeeld 1: Temperatuurwaarschuwing
Wanneer de temperatuur van een Xsense-thermometer te hoog is, wordt er een melding verstuurd:
```yaml
automation:
  - alias: "Xsense Temperatuurwaarschuwing"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "De temperatuur overschrijdt 30 graden!"
```

### Voorbeeld 2: Watermelder-alarm
Wanneer de watermelder water detecteert, wordt er een waarschuwingsmelding geactiveerd:
```yaml
automation:
  - alias: "Watermelder Alarm"
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

## We hebben hulp nodig
We zijn altijd op zoek naar ondersteuning om deze integratie verder te ontwikkelen en te verbeteren. Hier zijn enkele manieren waarop je kunt helpen:

1. **Testen van apparaten**: Als je een Xsense-apparaat hebt dat werkt met de integratie, laat het ons weten zodat we het kunnen toevoegen aan de lijst met ondersteunde apparaten.

2. **Ondersteuning voor niet-werkende apparaten**: Als een apparaat niet werkt, meld dit dan, zodat we ondersteuning kunnen bieden of het kunnen integreren in toekomstige versies.

3. **Delen van apparaten**: De beste manier om nieuwe apparaten te testen is door het apparaat te delen via de X-Sense-app.

Voor discussies en ondersteuning kun je ons bereiken op onze Discord-server of in het Home Assistant-forum:

[Discord](https://discord.gg/5phHHgGb3V)

[Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

