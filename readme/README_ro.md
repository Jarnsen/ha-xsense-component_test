# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Prezentare generală
Această integrare pentru Home Assistant expune dispozitivele X-Sense în casa inteligentă. Se bazează pe lucrarea originală a lui Theo Snel și se instalează prin HACS.

Recomandăm crearea unui al doilea cont X-Sense pentru Home Assistant și partajarea din contul principal doar a dispozitivelor acceptate.

## Instalare
În HACS adăugați depozitul personalizat `https://github.com/Jarnsen/ha-xsense-component_test`, descărcați integrarea, urmați instrucțiunile HACS pentru repornire, apoi configurați integrarea cu acel cont X-Sense.


## Configurare detaliată cu capturi de ecran

1. Creați un cont X-Sense separat pentru Home Assistant și partajați din contul principal doar dispozitivele acceptate.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

2. În HACS, adăugați `https://github.com/Jarnsen/ha-xsense-component_test` ca depozit personalizat.

![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

3. Descărcați și instalați integrarea, reporniți Home Assistant, apoi configurați integrarea cu noul cont X-Sense.

![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

4. După configurarea reușită, dispozitivele partajate apar în pagina de dispozitive din Home Assistant.

![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)

5. Asocierea, eliminarea, firmware-ul, plățile, cardurile SD și administrarea contului rămân în aplicația X-Sense.

## Dispozitive acceptate
Sunt acceptate stații de bază, detectoare de fum, detectoare CO, alarme de căldură, detectoare de scurgeri de apă, higrometre, senzori de ușă și mișcare, lumini, tastaturi, senzori de cutie poștală, dispozitive de ascultare și camere acceptate, atunci când contul X-Sense le raportează.

Familiile de modele confirmate includ: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## Entități și acțiuni
Integrarea creează entități numai pentru câmpurile raportate efectiv de dispozitiv. Acestea pot include alarme, muting, baterie, semnal, temperatură, umiditate, CO, marcaje de timp lizibile, setări de cameră, comutatoare LED, test, muting și exerciții de alarmă.

Administrarea dispozitivelor, partajarea, eliminarea, firmware-ul, conturile și plățile rămân în aplicația X-Sense. Pentru discuții folosiți Discord sau forumul Home Assistant.

## Vizualizare live cameră și notificări AI
Cel mai simplu este să importați blueprint-ul inclus cu butonul de mai jos, să alegeți `Motion` sau `AI Detection` disponibil și să ajustați acțiunea de notificare.

[![Importă blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FJarnsen%2Fha-xsense-component_test%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fxsense%2Fcamera_ai_notification.yaml)

Motion și AI Detection sunt evenimente unice, nu stări pornit/oprit. Pentru automatizări manuale folosiți `event.received`; `event_type` este necesar doar pentru filtrarea tipurilor ca `person`, `pet`, `vehicle`, `package`, `other` sau `ai_detection`.

Exemplu de automatizare:

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
## Exemple de automatizări
```yaml
automation:
  - alias: "Alertă temperatură X-Sense"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "Temperatura a depășit 30 de grade!"
```

```yaml
automation:
  - alias: "Alarmă scurgere de apă"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "Scurgere de apă detectată!"
```

## Suport
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

## Detalii suplimentare

### Configurarea contului

Este recomandat să folosiți un cont X-Sense separat pentru Home Assistant și să partajați cu el doar dispozitivele acceptate pe care doriți să le vedeți în Home Assistant. Integrarea nu asociază, nu elimină și nu mută dispozitive între locuințe. Acest tip de administrare rămâne în aplicația oficială X-Sense.

### Actualizări de stare

Integrarea folosește mesaje MQTT shadow pentru schimbări rapide de stare și interogări periodice prudente ale cloudului pentru reîmprospătarea datelor. Starea raportată de o stație este actualizată pe stație, iar starea raportată de un dispozitiv copil este actualizată pe dispozitivul respectiv, astfel încât alarmele și senzorii să nu rămână blocați pe valori vechi.

### Entități disponibile

În funcție de model, pot apărea alarme pentru fum, CO, apă, temperatură, mișcare și ușă, oprirea sonorului alarmei, sfârșitul duratei de viață, încărcare, stare memento, stare lumină și alți senzori binari de diagnostic. Senzorii pot include baterie, semnal RF sau Wi-Fi, firmware, temperatură, umiditate, nivel CO, vârf CO, volum, praguri, ore lizibile, fus orar și alte informații de diagnostic. Comutatoarele, selecțiile și valorile numerice sunt create doar când dispozitivul le acceptă cu adevărat.

### Camere

### Depanare

Dacă lipsește o entitate, verificați mai întâi în aplicația X-Sense că dispozitivul raportează într-adevăr acea valoare. Dacă starea rămâne învechită, reîncărcați integrarea doar ca test temporar și atașați diagnosticul, împreună cu liniile relevante din jurnalul Home Assistant.

### Comportamentul dispozitivelor

- Stațiile și dispozitivele copil pot raporta seturi diferite de valori. De aceea, integrarea nu presupune că fiecare stație trebuie să aibă un dispozitiv copil.
- Valorile de timp sunt convertite într-o formă lizibilă atunci când dispozitivul trimite timpul în formatul folosit de aplicația X-Sense.
- O entitate nu este creată dacă dispozitivul nu raportează acea funcție. Astfel se evită controale înșelătoare în Home Assistant.

### Încărcarea cloudului

Integrarea încearcă să folosească prudent API-ul X-Sense. Schimbările rapide sunt preluate din mesajele MQTT, iar apelurile către cloud sunt folosite doar unde sunt necesare pentru autentificare, încărcarea dispozitivelor sau reîmprospătarea stării.

### Raportarea unei probleme

Când raportați o eroare, includeți modelul dispozitivului, versiunea integrării, dacă valoarea corectă apare în aplicația X-Sense și diagnosticul integrării din Home Assistant. Ajută și o descriere scurtă: starea nu se schimbă niciodată sau se schimbă doar după reîncărcarea integrării.

## Secțiune completă de referință

### Configurarea contului în detaliu
- Folosiți un cont X-Sense separat pentru Home Assistant.
- Partajați din contul principal doar dispozitivele acceptate.
- Asocierea, eliminarea, partajarea și mutarea dispozitivelor rămân în aplicația X-Sense.
- Dacă aplicația și Home Assistant se deconectează reciproc, probabil folosesc același cont.

### Actualizări și încărcarea API
- Schimbările rapide de stare sunt primite prin mesaje MQTT shadow.
- Cererile către cloud sunt folosite pentru autentificare, încărcarea dispozitivelor și reîmprospătarea stării.
- Interogarea periodică este rezervă când un mesaj MQTT lipsește.

### Entități și acțiuni
- Entitățile sunt create doar pentru câmpurile raportate efectiv de X-Sense.
- Valorile de diagnostic sunt marcate ca diagnostic.
- Testul, amuțirea, exercițiul de incendiu și trezirea camerei apar doar pentru modelele acceptate.

### Referință pentru camere
- Camerele acceptate pot oferi entitate cameră, miniatură, flux live și diagnostic.
- Cardul SD, plățile, firmware-ul și administrarea contului rămân în aplicația X-Sense.

### Listă de verificare pentru depanare
- Raportul trebuie să includă modelul, versiunea integrării, diagnostice și jurnale relevante.

### Domeniu
- Integrarea nu adaugă, nu elimină și nu mută dispozitive între locuințe.

## Listă de verificare pentru dispozitive și entități

### Familii principale de dispozitive
- SBS50: stație de bază și stare la nivel de stație.
- XS01-WX: alarmă de fum Wi-Fi, inclusiv conturi fără dispozitiv copil separat.
- XS01-M, XS03-WX, XS0B-MR: familii de alarme de fum.
- XC01-M, XC04-WX: familii de alarme CO.
- SC07-WX, XP0A-MR: familii combinate fum și CO.
- XH02-M: familie de alarme de căldură.
- SWS51: familie de detectoare de scurgeri de apă.
- STH51, STH0A, STH0B, STH0C: temperatură și umiditate.
- SDS0A: senzor de ușă.
- SMS0A: senzor de mișcare.
- SSC0A, SSC0B: camere acceptate.

### Câmpuri de stare
- Starea alarmei apare când X-Sense raportează un câmp de alarmă.
- Starea de amuțire apare când X-Sense raportează un câmp de amuțire.
- Starea bateriei apare când dispozitivul raportează date despre baterie.
- Semnalul RF și Wi-Fi apare când dispozitivul îl raportează.
- Valorile compacte de timp sunt convertite în senzori Home Assistant ușor de citit.

### Comenzi și raportări
- Switch-urile sunt create doar pentru setări inscriptibile raportate de X-Sense.
- Butoanele sunt create doar pentru acțiuni acceptate de aplicație.
- Comenzile camerei sunt create doar când API-ul le marchează disponibile.
- Raportul de problemă trebuie să includă modelul exact, versiunea integrării, diagnostice, jurnale și dacă valoarea se schimbă în aplicația X-Sense.

### Note de funcționare
- După configurare, verificați dacă numele dispozitivelor și camerele corespund cu aplicația X-Sense.
- Dacă alarma, modul silențios sau LED-ul nu se schimbă imediat, așteptați următorul mesaj MQTT sau următoarea actualizare de stare.
- Pentru stațiile SBS50, verificați atât starea stației, cât și fiecare dispozitiv subordonat.
- Pentru XS01-WX, întreaga stare poate fi raportată direct pe dispozitiv, chiar fără un dispozitiv subordonat separat în cont.
- Pentru camere, entitățile create depind de capabilitățile pe care cloudul X-Sense le returnează pentru acel cont.
- Dacă o entitate nu este creată, comparați mai întâi valoarea cu aplicația X-Sense și atașați diagnosticul.
- Integrarea este destinată afișării și controlului funcțiilor acceptate, nu înlocuirii împerecherii sau administrării dispozitivelor în aplicație.
