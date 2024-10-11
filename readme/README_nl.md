# ha-xsense-component_test

<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Overzicht
Deze integratie voor Home Assistant maakt het gebruik van Xsense-apparaten binnen het slimme huis mogelijk. Het is gebaseerd op de originele code van [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) en is gepubliceerd met zijn toestemming en in samenwerking met hem.

Totdat een officiële Home Assistant-integratie van Theo beschikbaar is, zal deze HACS-integratie worden gebruikt en regelmatig worden bijgewerkt om nieuwe functies toe te voegen en bestaande problemen op te lossen. Deze integratie stelt gebruikers in staat om hun Xsense-apparaten eenvoudig in Home Assistant te integreren en te gebruiken voor verschillende automatiseringen en bewaking.

![images](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/c49a97f2-5e10-4129-82bc-1d647adc0895)

## Functies
- Integratie van verschillende Xsense-apparaten in Home Assistant.
- Ondersteuning voor automatiseringen op basis van Xsense-sensorgegevens.
- Ondersteuning voor de volgende apparaattype: basisstations, rookmelders, koolmonoxidemelders, hittealarmen, waterlekdetectoren en hygrometers.
- Eenvoudige installatie via HACS (Home Assistant Community Store).

## Vereisten
- Een werkende Home Assistant-server (de nieuwste versie wordt aanbevolen).
- Een Xsense-account met ondersteunde apparaten.
- HACS moet geïnstalleerd zijn in Home Assistant om de installatie van de integratie mogelijk te maken.

## Uitlegvideo
Voor een gedetailleerde handleiding voor het installeren en configureren van de integratie, kun je de volgende video bekijken:

[![X-Sense Home Assistant Integration](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## Voorbereiding
Voordat je de integratie installeert, moeten enkele voorbereidingen worden getroffen:

- **Maak een tweede account aan in de X-Sense-app (voor gebruik met Home Assistant)**: Aangezien het niet mogelijk is om met dezelfde account tegelijk aangemeld te zijn in de app en Home Assistant, raden we aan om een apart account te gebruiken voor Home Assistant. Hierdoor voorkom je dat je voortdurend wordt uitgelogd uit de app of Home Assistant. Het extra account zorgt voor een naadloze integratie en continu gebruik zonder onderbrekingen.

- **Deel de ondersteunde apparaten van het hoofdaccount met het Home Assistant-account**: Gebruik de X-Sense-app om **alleen de ondersteunde apparaten** met het nieuw aangemaakte account te delen. Zo kun je de integratie gemakkelijk gebruiken in Home Assistant, terwijl je de apparaten blijft beheren via je hoofdaccount.

![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## Installatie via HACS
1. **Open HACS in Home Assistant**:
   HACS is een belangrijke uitbreiding voor Home Assistant waarmee je eenvoudig aangepaste integraties kunt installeren.

   ![Download (1)](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **Ga naar de aangepaste repositories**:
   Navigeer in het HACS-dashboard naar de instellingen en voeg de repository toe als een aangepaste bron.

3. **Voeg de repository toe**:
   Voer de URL van de repository in: `https://github.com/Jarnsen/ha-xsense-component_test`

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **Download en installeer de integratie**:
   Zoek de integratie in HACS, download en installeer deze. Na de installatie kan de configuratie worden uitgevoerd via de Home Assistant-interface.

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)
   
   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## Configuratie
Na de installatie is een basisconfiguratie nodig om de integratie correct in te stellen:
- **Gebruikersnaam en wachtwoord**: Gebruik de inloggegevens van het nieuw aangemaakte X-Sense-account om de verbinding tot stand te brengen.

    ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)
  
- **Overzicht van apparaten**: Na succesvolle configuratie zijn de gedeelde apparaten beschikbaar in Home Assistant en kunnen ze worden gebruikt voor automatiseringen.

    ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)
## Weergave in Home Assistant
Na een succesvolle installatie en configuratie is de integratie zichtbaar in Home Assistant. De apparaten zijn dan zichtbaar op het dashboard en kunnen worden gebruikt voor automatiseringen, meldingen en andere toepassingen.

![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/50bbafde-c94b-445e-9aa3-9c33d5f151d6)

____________________________________________________________

## Ondersteunde apparaten
Deze integratie ondersteunt verschillende Xsense-apparaten. Hieronder staat een lijst met de momenteel bevestigde en geteste apparaten:
- **Basisstation (SBS50)**: Centraal knooppunt voor de Xsense-apparaten.
- **Hittealarm (XH02-M)**: Detectie van ongewoon hoge temperaturen.
- **Koolmonoxidemelder (XC01-M; XC04-WX)**: Meldt gevaarlijke concentraties koolmonoxide.
- **Rookmelder (XS01-M, WX; XS03-WX; XS0B-MR)**: Vroege detectie van rookontwikkeling.
- **Combi-melder voor koolmonoxide en rook (SC07-WX; XP0A-MR (gedeeltelijk ondersteund))**: Gecombineerde apparaten voor de detectie van koolmonoxide en rook.
- **Waterlekdetector (SWS51)**: Meldt de aanwezigheid van water op ongewenste plaatsen.
- **Hygrometer-thermometer (STH51)**: Monitoring van temperatuur en luchtvochtigheid.

Deze apparaten kunnen na integratie in Home Assistant worden gebruikt voor het maken van automatiseringen en waarschuwingen.

____________________________________________________________

## Voorbeelden van automatiseringen
Met deze integratie kun je verschillende automatiseringen maken. Hier zijn enkele voorbeelden:

### Voorbeeld 1: Temperatuuralarm
Wanneer de temperatuur van een Xsense-thermometer te hoog is, wordt een melding verstuurd:

```yaml
automation:
  - alias: "Xsense Temperatuuralarm"
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

1. **Testen van apparaten**: Als je een Xsense-apparaat hebt dat werkt met de integratie, laat het ons weten, zodat we het aan de lijst met ondersteunde apparaten kunnen toevoegen.

2. **Feedback over niet-ondersteunde apparaten**: Als een apparaat niet werkt, geef ons dan feedback, zodat we ondersteuning kunnen bieden of het apparaat in toekomstige versies van de integratie kunnen opnemen.

3. **Delen van apparaten voor tests**: De beste manier om nieuwe apparaten te testen, is door het apparaat te delen via de X-Sense-app. Zo kunnen we ervoor zorgen dat zoveel mogelijk apparaten worden ondersteund.

4. **Gemeenschapssteun**: Neem deel aan discussies in onze gemeenschap. Of je nu suggesties hebt voor verbeteringen of andere gebruikers helpt met hun installatie - alle hulp is welkom!

Voor discussies en ondersteuning kun je ons bereiken op onze Discord-server of in het Home Assistant-forum:

[Discord](https://discord.gg/5phHHgGb3V)

[Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)
