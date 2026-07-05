# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.

<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>



## Überblick
Diese Integration für Home Assistant ermöglicht die Verwendung von X-Sense-Geräten innerhalb des Smart-Home-Systems. Sie wurde basierend auf dem Originalcode von [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) erstellt und mit seiner Erlaubnis und in Zusammenarbeit mit ihm veröffentlicht.

Diese HACS-Integration wird aktiv gepflegt, damit Nutzer eine breitere X-Sense-Geräteunterstützung in Home Assistant erhalten. Sie wird regelmäßig mit neuen Funktionen, zusätzlicher Geräteabdeckung und Korrekturen für gemeldete Probleme aktualisiert.

## Kompatibilität und HACS-Updates
Wenn Sie noch eine alte `v1.2.6.x`-Version verwenden, aktualisieren Sie auf `v1.3.14` oder neuer, bevor Sie Home Assistant Core auf 2026.7 oder neuer aktualisieren. Die alten `v1.2.6.x`-Versionen benötigten `aiortc`, das nicht mit der Python-3.14-Laufzeit von Home Assistant kompatibel ist. Aktuelle `v1.3.x`-Versionen benötigen `aiortc` nicht mehr.

Diese Integration wird als benutzerdefiniertes HACS-Repository installiert. Wenn Home Assistant das Update nicht sofort anzeigt, öffnen Sie HACS, wählen Sie das X-Sense-Repository, führen Sie im Drei-Punkte-Menü **Update information** / **Informationen aktualisieren** aus, aktualisieren oder laden Sie die Integration erneut herunter und starten Sie Home Assistant neu.

<p align="center">
 <img src="https://github.com/user-attachments/assets/fbe7e69b-9204-4de4-a245-e0e2bdbd7f73" alt="Image">
</p>

## Funktionen
- Integration verschiedener X-Sense-Geräte in Home Assistant.
- Unterstützung für Automationen auf Basis der X-Sense-Sensordaten.
- Unterstützung für Basisstationen, Rauchmelder, Kohlenmonoxidmelder, Hitzemelder, Wassermelder, Hygrometer, Türsensoren, Bewegungssensoren, Licht, Tastatur, Briefkastensensoren, Lauschgerät, Kameras und weitere unterstützte Geräte, wenn sie im X-Sense-Konto verfügbar sind.
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

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## Installation über HACS
1. **Öffne HACS in Home Assistant**:
  HACS ist eine wichtige Erweiterung für Home Assistant, die es dir ermöglicht, benutzerdefinierte Integrationen einfach zu installieren.

  ![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **Gehe zu den benutzerdefinierten Repositories**:
  Navigiere im HACS-Dashboard zu den Einstellungen und füge das Repository als benutzerdefinierte Quelle hinzu.

3. **Füge das Repository hinzu**:
  Gib die URL des Repositories ein: `https://github.com/Jarnsen/ha-xsense-component_test`

  ![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **Lade die Integration herunter und installiere sie**:
  Suche die Integration in HACS, lade sie herunter und installiere sie. Nach der Installation kann die Konfiguration über die Home Assistant-Benutzeroberfläche vorgenommen werden.

  ![HACS repository selection screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)

  ![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## Konfiguration
Nach der Installation ist eine grundlegende Konfiguration notwendig, um die Integration korrekt einzurichten:
- **Benutzername und Passwort**: Verwende die Zugangsdaten des neu erstellten X-Sense-Kontos, um die Verbindung herzustellen.

  ![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

- **Geräteübersicht**: Nach erfolgreicher Einrichtung werden die geteilten Geräte in Home Assistant verfügbar und können dort für Automationen genutzt werden.

  ![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)
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
- **Weitere über Stationen verbundene Geräte**: Licht, Tastatur, Briefkastensensor, Lauschgerät, Einfahrtsalarm, Smart-Drop-Gerät, Fernbedienung und Radondaten werden angezeigt, wenn die X-Sense-API unterstützte Felder meldet.

Nach der Einbindung in Home Assistant können diese Geräte für Automationen und Warnungen genutzt werden.

### Verfügbare Entitäten und Aktionen
Die Integration erstellt Home-Assistant-Entitäten nur für Felder, die in der X-Sense-Cloud, in MQTT-Shadow-Daten oder über die appgestützten Kamera-APIs vorhanden sind. Je nach Gerät kann dies Folgendes umfassen:

- Binärsensoren für Alarm, Stummschaltung, Lebensdauerende, AC-Unterbrechung, Wasseralarm, Temperaturalarm, Laden, Bewegung, Tür, Scharfstatus, Warnungen, Erinnerungen, Licht, PIR und Tastaturstatus.
- Sensoren für Batterie, RF-Signal, WLAN-Signal, Firmware, Temperatur, Luftfeuchtigkeit, CO-Wert, CO-Spitzenwert, Alarm-, Sprach-, Chirp- und Erinnerungslautstärke, Warnschwellen, Stummschaltzeiten, lesbare Zeitstempel, Zeitzone und weitere Diagnosedaten.
- Schalter für unterstützte beschreibbare Einstellungen wie LED-Licht, Alarmaktivierung, fortgesetzten Alarm, Chirp-Ton, Erinnerungen, PIR, Sonnenschein, Wartezustand, Tastenton, Kamera-Bewegungserkennung, Aufnahme, Nachtsicht, Audio, Cooldown, Licht und Türklingelsteuerung.
- Auswahlfelder und Zahlenwerte für unterstützte Kameraeinstellungen wie Sprache, Aufnahmeauflösung, Codec, Anti-Flicker-Rate, Bewegungsempfindlichkeit, Videolänge, Lautstärke, Alarmdauer, Cooldown, Nachtschwelle und Türklingelton.
- Test-, Stumm-, Feueralarm- und Kamera-Weckschaltflächen für Modelle, bei denen die X-Sense-App die passende Aktion anbietet.

Einige Entitäten sind Diagnose- oder Konfigurationseinheiten und werden in Home Assistant entsprechend gruppiert. Wenn ein Gerät ein Feld nicht meldet oder die X-Sense-App die Funktion für dieses Gerät/Konto als nicht unterstützt markiert, wird keine passende Entität erstellt. Gerätebindung, Entfernen, Teilen, Konto-, Zahlungs-, Firmware-Update-, SD-Kartenformatierungs- und andere Verwaltungsaktionen bleiben in der X-Sense-App.

____________________________________________________________

## Kamera-Liveansicht und KI-Benachrichtigungen
Der einfachste Weg ist der enthaltene Blueprint. Importiere ihn mit der Schaltfläche unten, wähle die Kamera-Event-Entität `Motion` oder bei abonnierter Kamera `AI Detection`, und passe die Benachrichtigungsaktion bei Bedarf an.

When a Motion event includes X-Sense playback metadata, the integration immediately tries to cache the clip. With recording links enabled, the default camera-event blueprint waits until cached media is ready, then sends a mobile notification that opens the matching X-Sense Recordings clip. Turn recording links off if you want a plain motion notification without waiting for video. Manual automation runs use the selected event entity's latest recording data. Recording media sync can keep recent clips ready in the background. The integration updates older imported X-Sense camera-event blueprints automatically when Home Assistant starts or during the periodic blueprint maintenance check.

[![Blueprint importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FJarnsen%2Fha-xsense-component_test%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fxsense%2Fcamera_ai_notification.yaml)

Motion und AI Detection sind einmalige Events, keine Ein/Aus-Zustände. Für eigene Automationen nutze den Home-Assistant-Trigger `event.received` mit der Kamera-Entität `Motion` oder `AI Detection`; `event_type` ist nur zum Eingrenzen abonnierter AI-Detection-Objekttypen wie `person`, `pet`, `vehicle`, `package`, `other` oder `ai_detection` nötig.

Beispielautomation:

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

## Vollständige Referenz

### Konto und Installation
- Verwende für Home Assistant ein separates X-Sense-Konto.
- Teile vom Hauptkonto nur unterstützte Geräte mit diesem Konto.
- Koppeln, Entfernen, Teilen, Firmware, Konto, Zahlungen und SD-Kartenverwaltung bleiben in der X-Sense-App.

### Updates und API-Nutzung
- Schnelle Statusänderungen kommen über MQTT-Shadow-Nachrichten.
- Cloud-Anfragen werden für Anmeldung, Gerätesuche, Kameradaten und Statuswiederherstellung genutzt.
- Periodisches Polling dient nur als Fallback, wenn ein Live-Update fehlt.

### Entitäten, Kameras und Fehlersuche
- Entitäten werden nur für Felder erstellt, die X-Sense tatsächlich meldet.
- Kamera-Entitäten und Steuerungen werden nur erstellt, wenn die an der Android-App ausgerichtete API Unterstützung für dieses Konto und Modell meldet.
- Wenn ein Wert fehlt, vergleiche ihn zuerst mit der X-Sense-App und füge dann Diagnosen sowie relevante Home-Assistant-Logs bei.

## Geräte- und Entitäten-Checkliste

### Wichtige Gerätefamilien
- SBS50-Basisstation, XS-Rauchmelder, XC-CO-Melder, SC/XP-Kombimelder, XH-Hitzemelder, SWS-Wassermelder, STH-Temperatur-/Feuchtesensoren, SDS-Türsensoren, SMS-Bewegungssensoren, SSC-Kameras und weitere gemeldete X-Sense-Familien werden unterstützt, wenn die API ihre Felder bereitstellt.

### Statusfelder
- Alarm, Stummschaltung, Batterie, RF-/WLAN-Signal, Temperatur, Luftfeuchte, CO, Wasser, Bewegung, Tür, Licht, Erinnerungen, Warnungen und lesbare Zeitstempel erscheinen nur, wenn X-Sense sie meldet.

### Steuerungen und Meldungen
- Schalter, Auswahlen, Zahlen und Tasten werden nur für beschreibbare Einstellungen und Aktionen erstellt, die Gerät und Konto bereitstellen.
- Gute Fehlermeldungen enthalten das genaue Modell, die Integrationsversion, Diagnosen, Logs und ob sich der Wert in der X-Sense-App korrekt ändert.
