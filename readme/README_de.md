# ha-xsense-component_test 
<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>



## Überblick
Diese Integration für Home Assistant ermöglicht die Verwendung von X-Sense-Geräten innerhalb des Smart-Home-Systems. Sie wurde basierend auf dem Originalcode von [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) erstellt und mit seiner Erlaubnis und in Zusammenarbeit mit ihm veröffentlicht.

Bis es eine offizielle Home Assistant-Integration von Theo gibt, wird diese HACS-Integration verwendet und regelmäßig aktualisiert, um neue Funktionen hinzuzufügen und bestehende Probleme zu beheben. Diese Integration ermöglicht es Nutzern, ihre X-Sense-Geräte einfach in Home Assistant zu integrieren und für verschiedene Automationen und Überwachungen zu nutzen.

<p align="center">
  <img src="https://github.com/user-attachments/assets/fbe7e69b-9204-4de4-a245-e0e2bdbd7f73" alt="Image">
</p>

## Funktionen
- Integration verschiedener X-Sense-Geräte in Home Assistant.
- Unterstützung für Automationen auf Basis der X-Sense-Sensordaten.
- Unterstützung für Basisstationen, Rauchmelder, Kohlenmonoxidmelder, Hitzemelder, Wassermelder, Hygrometer, Türsensoren, Bewegungssensoren, Licht, Tastatur, Briefkastensensoren, Listener, Kameras und weitere unterstützte Geräte, wenn sie im X-Sense-Konto verfügbar sind.
- Einfache Einrichtung über HACS (Home Assistant Community Store).

## Voraussetzungen
- Ein funktionierender Home Assistant-Server (empfohlen ist die neueste Version).
- Ein X-Sense-Konto mit unterstützten Geräten.
- HACS muss in Home Assistant installiert sein, um die Installation der Integration zu ermöglichen.

## How-to-Video
Für eine detaillierte Anleitung zur Installation und Konfiguration der Integration kannst du dir folgendes Video ansehen:

[![X-Sense Home Assistant Integration](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## Vorbereitung
Bevor du die Integration installierst, sind einige Vorbereitungen notwendig:

- **Erstelle einen zweiten Account in der X-Sense-App (für die Verwendung mit Home Assistant)**: Da es bei X-Sense nicht möglich ist, gleichzeitig in der App und in Home Assistant mit demselben Konto angemeldet zu sein, empfehlen wir die Nutzung eines separaten Kontos für Home Assistant. Dadurch wird verhindert, dass du immer wieder zwischen der App und Home Assistant abgemeldet wirst. Der zusätzliche Account ermöglicht eine nahtlose Integration und Nutzung, ohne dass es zu Störungen durch wiederholtes An- und Abmelden kommt.

- **Teile die unterstützten Geräte vom Hauptkonto mit dem Home Assistant-Konto**: Verwende die X-Sense-App, um **nur die unterstützten Geräte** mit dem neu erstellten Account zu teilen. Auf diese Weise kannst du die Integration unkompliziert in Home Assistant nutzen, während die Verwaltung weiterhin über dein Hauptkonto erfolgt.

![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## Installation über HACS
1. **Öffne HACS in Home Assistant**:
   HACS ist eine wichtige Erweiterung für Home Assistant, die es dir ermöglicht, benutzerdefinierte Integrationen einfach zu installieren.

   ![Download (1)](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **Gehe zu den benutzerdefinierten Repositories**:
   Navigiere im HACS-Dashboard zu den Einstellungen und füge das Repository als benutzerdefinierte Quelle hinzu.

3. **Füge das Repository hinzu**:
   Gib die URL des Repositories ein: `https://github.com/Jarnsen/ha-xsense-component_test`

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **Lade die Integration herunter und installiere sie**:
   Suche die Integration in HACS, lade sie herunter und installiere sie. Nach der Installation kann die Konfiguration über die Home Assistant-Benutzeroberfläche vorgenommen werden.

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)
   
   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## Konfiguration
Nach der Installation ist eine grundlegende Konfiguration notwendig, um die Integration korrekt einzurichten:
- **Benutzername und Passwort**: Verwende die Zugangsdaten des neu erstellten X-Sense-Kontos, um die Verbindung herzustellen.

    ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)
  
- **Geräteübersicht**: Nach erfolgreicher Einrichtung werden die geteilten Geräte in Home Assistant verfügbar und können dort für Automationen genutzt werden.

    ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)
## Ansicht in Home Assistant
Nach erfolgreicher Installation und Konfiguration wird die Integration in Home Assistant sichtbar sein. Die Geräte sind dann im Dashboard sichtbar und können für Automationen, Benachrichtigungen und andere Anwendungsfälle verwendet werden.


![Forum](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/2d271b78-39d9-4bbd-837d-8593cf1933bd)

____________________________________________________________

## Unterstützte Geräte
Diese Integration unterstützt verschiedene X-Sense-Geräte. Die verfügbaren Entitäten hängen davon ab, welche Datenfelder das jeweilige Gerät und Konto meldet. Zu den derzeit unterstützten Gerätefamilien und bestätigten Modellen gehören:
- **Basisstation (SBS50)**: Zentraler Hub für X-Sense-Geräte.
- **Hitzemelder (XH02-M)**: Erkennt ungewöhnlich hohe Temperaturen.
- **Kohlenmonoxidmelder (XC01-M; XC04-WX)**: Erkennt gefährliche Kohlenmonoxidkonzentrationen.
- **Rauchmelder (XS01-M; XS01-WX; XS03-WX; XS0B-MR und verwandte RF/iR-Modelle)**: Früherkennung von Rauch.
- **Kombinierte Kohlenmonoxid- und Rauchmelder (SC07-WX; XP0A-MR und verwandte XP/SC-Modelle)**: Kombigeräte zur Erkennung von Kohlenmonoxid und Rauch.
- **Wassermelder (SWS51)**: Erkennt Wasser an unerwünschten Stellen.
- **Hygrometer-Thermometer (STH51, STH0A, STH0B, STH0C)**: Überwacht Temperatur und Luftfeuchtigkeit.
- **Türsensor (SDS0A)**: Stellt den Türstatus bereit, wenn er vom X-Sense-Konto gemeldet wird.
- **Bewegungsmelder (SMS0A)**: Stellt den Bewegungsalarmstatus bereit, wenn er vom X-Sense-Konto gemeldet wird.
- **Kamera (SSC0A, SSC0B)**: Stellt Kameraentitäten, Vorschaubilder, Livestream-URLs, Statusdiagnosen und appgestützte Einstellungen bereit, wenn Gerät und Konto dies unterstützen.
- **Weitere über Stationen verbundene Geräte**: Licht, Tastatur, Briefkastensensor, Listener, Einfahrtsalarm, Smart Drop, Fernbedienung und Radondaten werden angezeigt, wenn die X-Sense-API unterstützte Felder meldet.

Nach der Einbindung in Home Assistant können diese Geräte für Automationen und Warnungen genutzt werden.

### Verfügbare Entitäten und Aktionen
Die Integration erstellt Home-Assistant-Entitäten nur für Felder, die in der X-Sense-Cloud, in MQTT-Shadow-Daten oder über die appgestützten Kamera-APIs vorhanden sind. Je nach Gerät kann dies Folgendes umfassen:

- Binärsensoren für Alarm, Stummschaltung, Lebensdauerende, AC-Unterbrechung, Wasseralarm, Temperaturalarm, Laden, Bewegung, Tür, Scharfstatus, Warnungen, Erinnerungen, Licht, PIR und Tastaturstatus.
- Sensoren für Batterie, RF-Signal, WLAN-Signal, Firmware, Temperatur, Luftfeuchtigkeit, CO-Wert, CO-Spitzenwert, Alarm-, Sprach-, Chirp- und Erinnerungslautstärke, Warnschwellen, Stummschaltzeiten, lesbare Zeitstempel, Zeitzone, Seriennummer, MAC-Adresse und weitere Diagnosedaten.
- Schalter für unterstützte beschreibbare Einstellungen wie LED-Licht, Alarmaktivierung, fortgesetzten Alarm, Chirp-Ton, Erinnerungen, PIR, Sonnenschein, Wartezustand, Tastenton, Kamera-Bewegungserkennung, Aufnahme, Nachtsicht, Audio, Cooldown, Licht und Türklingelsteuerung.
- Auswahlfelder und Zahlenwerte für unterstützte Kameraeinstellungen wie Sprache, Aufnahmeauflösung, Codec, Anti-Flicker-Rate, Bewegungsempfindlichkeit, Videolänge, Lautstärke, Alarmdauer, Cooldown, Nachtschwelle und Türklingelton.
- Test-, Stumm-, Feueralarm- und Kamera-Weckschaltflächen für Modelle, bei denen die X-Sense-App die passende Aktion anbietet.

Einige Entitäten sind Diagnose- oder Konfigurationseinheiten und werden in Home Assistant entsprechend gruppiert. Wenn ein Gerät ein Feld nicht meldet oder die X-Sense-App die Funktion für dieses Gerät/Konto als nicht unterstützt markiert, wird keine passende Entität erstellt. Gerätebindung, Entfernen, Teilen, Konto-, Zahlungs-, Firmware-Update-, SD-Kartenformatierungs- und andere Verwaltungsaktionen bleiben in der X-Sense-App.

____________________________________________________________

## Beispiele für Automationen
Mit dieser Integration lassen sich verschiedene Automationen erstellen. Hier sind einige Beispiele:

### Beispiel 1: Temperaturwarnung
Wenn die Temperatur von einem X-Sense-Thermometer zu hoch ist, wird eine Benachrichtigung gesendet:

```yaml
automation:
  - alias: "X-Sense Temperaturwarnung"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "Die Temperatur überschreitet 30 Grad!"
```

### Beispiel 2: Wassermelder-Alarm
Wenn der Wassermelder Wasser erkennt, wird eine Warnmeldung ausgelöst:

```yaml
automation:
  - alias: "Wassermelder Alarm"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "Wasseraustritt erkannt!"
```

____________________________________________________________

## Wir brauchen Hilfe
Wir sind immer auf der Suche nach Unterstützung, um diese Integration weiterzuentwickeln und zu verbessern. Hier sind einige Möglichkeiten, wie du helfen kannst:

1. **Testen von Geräten**: Wenn du ein X-Sense-Gerät besitzt, das mit der Integration funktioniert, lass es uns wissen, damit wir es zur Liste der unterstützten Geräte hinzufügen können.

2. **Feedback zu nicht unterstützten Geräten**: Falls ein Gerät nicht funktioniert, gib uns bitte Rückmeldung, damit wir Unterstützung bieten oder das Gerät in zukünftigen Versionen der Integration einbinden können.

3. **Teilen von Geräten zum Testen**: Die beste Möglichkeit, neue Geräte zu testen, besteht darin, das Gerät über die X-Sense-App zu teilen. So können wir sicherstellen, dass möglichst viele Geräte unterstützt werden.

4. **Community-Unterstützung**: Beteilige dich an Diskussionen in unserer Community. Ob du Vorschläge für Verbesserungen hast oder anderen Nutzern mit ihrer Einrichtung hilfst – jede Hilfe ist willkommen!

Für Diskussionen und Unterstützung kannst du uns auf unserem Discord-Server oder im Home Assistant Forum erreichen:

[Discord](https://discord.gg/5phHHgGb3V)

[Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)
