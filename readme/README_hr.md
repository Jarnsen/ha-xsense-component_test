# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Pregled
Ova integracija za Home Assistant omogućuje korištenje X-Sense uređaja u pametnom domu. Temelji se na izvornom radu Thea Snela i namijenjena je instalaciji putem HACS-a.

Preporučujemo stvaranje drugog X-Sense računa za Home Assistant i dijeljenje samo podržanih uređaja iz glavnog računa.

## Instalacija
V HACS dodajte repozitorij po meri `https://github.com/Jarnsen/ha-xsense-component_test`, prenesite integracijo, sledite navodilom HACS za ponovni zagon in jo nato nastavite z računom X-Sense za Home Assistant.


## Detaljno postavljanje sa snimkama zaslona

1. Izradite zaseban X-Sense račun za Home Assistant i s glavnog računa podijelite samo podržane uređaje.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

2. U HACS-u dodajte `https://github.com/Jarnsen/ha-xsense-component_test` kao prilagođeni repozitorij.

![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

3. Preuzmite i instalirajte integraciju, ponovno pokrenite Home Assistant i zatim je konfigurirajte novim X-Sense računom.

![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

4. Nakon uspješnog postavljanja dijeljeni uređaji prikazat će se na stranici uređaja u Home Assistantu.

![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)

5. Uparivanje, uklanjanje, firmware, plaćanja, SD kartice i upravljanje računom ostaju u X-Sense aplikaciji.

## Podržani uređaji
Podprte so bazne postaje, detektorji dima, detektorji CO, toplotni alarmi, detektorji izliva vode, higrometri, senzorji vrat in gibanja, luči, tipkovnice, senzorji poštnega nabiralnika, poslušalne naprave in podprte kamere, kadar jih račun X-Sense poroča.

Potvrđene obitelji modela uključuju: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## Entiteti i radnje
Integracija ustvari samo entitete za podatke, ki jih naprava dejansko poroča. To lahko vključuje alarme, utišanje, baterijo, signal, temperaturo, vlago, CO, berljive čase, nastavitve kamere, stikala LED, test, utišanje in požarno vajo.

Upravljanje naprav, deljenje, odstranjevanje, firmware, računi in plačila ostanejo v aplikaciji X-Sense. Za razprave uporabite Discord ali forum Home Assistant.

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
## Primjeri automatizacija
```yaml
automation:
  - alias: "X-Sense upozorenje temperature"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "Temperatura je premašila 30 stupnjeva!"
```

```yaml
automation:
  - alias: "Alarm curenja vode"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "Otkriveno je curenje vode!"
```

## Podrška
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

## Dodatne pojedinosti

### Postavljanje računa

Preporučuje se zaseban X-Sense račun za Home Assistant i dijeljenje samo podržanih uređaja koje želite prikazati u Home Assistantu. Integracija ne uparuje, ne uklanja i ne premješta uređaje između domova. Takvo upravljanje uređajima ostaje u službenoj aplikaciji X-Sense.

### Ažuriranja stanja

Integracija koristi MQTT shadow poruke za brze promjene stanja i oprezno periodično dohvaćanje iz oblaka za osvježavanje podataka. Stanje koje prijavi stanica sprema se na stanicu, a stanje koje prijavi podređeni uređaj sprema se na taj uređaj, kako alarmi i senzori ne bi ostali na starim vrijednostima.

### Dostupni entiteti

Ovisno o modelu mogu se prikazati alarmi za dim, CO, vodu, temperaturu, pokret i vrata, utišavanje alarma, kraj životnog vijeka, punjenje, status podsjetnika, status svjetla i drugi dijagnostički binarni senzori. Senzori mogu uključivati bateriju, RF ili Wi-Fi signal, firmware, temperaturu, vlagu, razinu CO, vršnu vrijednost CO, glasnoću, pragove, čitljiva vremena, vremensku zonu i dodatnu dijagnostiku. Prekidači, odabiri i numeričke vrijednosti stvaraju se samo kada ih uređaj stvarno podržava.

### Kamere

Podržane kamere mogu pružiti entitet kamere, minijature, prijenos uživo, status veze i postavke usklađene s aplikacijom X-Sense. Ako je u Home Assistantu dostupna WebRTC putanja, integracija je može koristiti za prikladan prikaz uživo.

### Rješavanje problema

Ako neki entitet nedostaje, najprije provjerite u aplikaciji X-Sense prikazuje li uređaj doista tu vrijednost. Ako stanje ostaje zastarjelo, ponovno učitajte integraciju samo kao privremeni test i uz prijavu priložite dijagnostiku te relevantne zapise Home Assistanta.

### Ponašanje uređaja

- Stanice i podređeni uređaji mogu prijavljivati različite skupove vrijednosti. Integracija zato ne pretpostavlja da svaka stanica mora imati podređeni uređaj.
- Vremenske vrijednosti pretvaraju se u čitljiv oblik kada uređaj šalje vrijeme u formatu koji koristi aplikacija X-Sense.
- Entitet se ne stvara ako uređaj ne prijavljuje tu mogućnost. Time se izbjegavaju zavaravajuće kontrole u Home Assistantu.

### Opterećenje oblaka

Integracija nastoji štedljivo koristiti X-Sense API. Brze promjene preuzimaju se iz MQTT poruka, a pozivi prema oblaku koriste se samo kada su potrebni za prijavu, učitavanje uređaja ili osvježavanje stanja.

### Prijava problema

Pri prijavi greške navedite model uređaja, verziju integracije, prikazuje li se ispravna vrijednost u aplikaciji X-Sense i priložite dijagnostiku integracije iz Home Assistanta. Korisno je i kratko opisati mijenja li se stanje ikada ili tek nakon ponovnog učitavanja integracije.

## Potpuni referentni odjeljak

### Detaljno postavljanje računa
- Za Home Assistant koristite zaseban X-Sense račun.
- S glavnog računa podijelite samo podržane uređaje.
- Uparivanje, uklanjanje, dijeljenje i premještanje uređaja ostaju u aplikaciji X-Sense.
- Ako se aplikacija i Home Assistant međusobno odjavljuju, vjerojatno koriste isti račun.

### Ažuriranja i opterećenje API-ja
- Brze promjene stanja primaju se putem MQTT shadow poruka.
- Cloud zahtjevi koriste se za prijavu, učitavanje uređaja i osvježavanje stanja.
- Periodičko dohvaćanje služi kao rezerva ako MQTT poruka izostane.

### Entiteti i radnje
- Entiteti se stvaraju samo za polja koja X-Sense stvarno prijavljuje.
- Dijagnostičke vrijednosti označene su kao dijagnostika.
- Test, utišavanje, protupožarna vježba i buđenje kamere dostupni su samo za podržane modele.

### Referenca za kamere
- Podržane kamere mogu pružiti entitet kamere, sličicu, prijenos uživo i dijagnostiku.
- WebRTC put koristi se samo ako je dostupan u Home Assistantu.
- SD kartica, plaćanja, firmware i upravljanje računom ostaju u aplikaciji X-Sense.

### Kontrolni popis za rješavanje problema
- U prijavi problema navedite model, verziju integracije, dijagnostiku i relevantne zapise.

### Opseg
- Integracija ne dodaje, ne uklanja i ne premješta uređaje između domova.

## Popis uređaja i entiteta

### Glavne obitelji uređaja
- SBS50: bazna stanica i status na razini stanice.
- XS01-WX: Wi-Fi dimni alarm, uključujući račune bez zasebnog podređenog uređaja.
- XS01-M, XS03-WX, XS0B-MR: obitelji dimnih alarma.
- XC01-M, XC04-WX: obitelji CO alarma.
- SC07-WX, XP0A-MR: kombinirane obitelji dima i CO.
- XH02-M: obitelj toplinskih alarma.
- SWS51: obitelj detektora curenja vode.
- STH51, STH0A, STH0B, STH0C: temperatura i vlaga.
- SDS0A: senzor vrata.
- SMS0A: senzor pokreta.
- SSC0A, SSC0B: podržane kamere.

### Polja statusa
- Status alarma prikazuje se kada X-Sense prijavi polje alarma.
- Status utišavanja prikazuje se kada X-Sense prijavi polje utišavanja.
- Status baterije prikazuje se kada uređaj prijavi podatke baterije.
- RF i Wi-Fi signal prikazuju se kada ih uređaj prijavi.
- Kompaktne vremenske vrijednosti pretvaraju se u čitljive Home Assistant senzore.

### Kontrole i prijave
- Prekidači se stvaraju samo za zapisive postavke koje X-Sense prijavi.
- Gumbi se stvaraju samo za radnje koje podržava aplikacija.
- Kontrole kamere stvaraju se samo kada ih API označi dostupnima.
- Prijava greške treba sadržavati model, verziju integracije, dijagnostiku, zapise i mijenja li se vrijednost u aplikaciji X-Sense.

### Napomene za rad
- Nakon postavljanja provjerite odgovaraju li nazivi uređaja i prostorije aplikaciji X-Sense.
- Ako se alarm, utišavanje ili LED ne promijene odmah, pričekajte sljedeću MQTT poruku ili osvježavanje stanja.
- Kod SBS50 stanica provjerite i stanje stanice i pojedinačne podređene uređaje.
- Kod XS01-WX cijelo stanje može biti prijavljeno izravno na uređaju, čak i bez zasebnog podređenog uređaja na računu.
- Kod kamera stvoreni entiteti ovise o mogućnostima koje X-Sense oblak vrati za taj račun.
- Ako entitet nije stvoren, prvo usporedite vrijednost s aplikacijom X-Sense i priložite dijagnostiku.
- Integracija je namijenjena prikazu i upravljanju podržanim funkcijama, a ne zamjeni uparivanja ili upravljanja uređajima u aplikaciji.
