# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Pregled
Ta integracija za Home Assistant omogoča uporabo naprav X-Sense v pametnem domu. Temelji na izvirnem delu Thea Snela in je namenjena namestitvi prek HACS.

Priporočamo, da ustvarite drugi račun X-Sense za Home Assistant in iz glavnega računa delite samo podprte naprave.

## Namestitev
V HACS dodajte repozitorij po meri `https://github.com/Jarnsen/ha-xsense-component_test`, prenesite integracijo, sledite navodilom HACS za ponovni zagon in jo nato nastavite z računom X-Sense za Home Assistant.


## Podrobna nastavitev s posnetki zaslona

1. Ustvarite ločen račun X-Sense za Home Assistant in iz glavnega računa delite samo podprte naprave.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

2. V HACS dodajte `https://github.com/Jarnsen/ha-xsense-component_test` kot repozitorij po meri.

![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

3. Prenesite in namestite integracijo, znova zaženite Home Assistant in jo nato nastavite z novim računom X-Sense.

![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

4. Po uspešni nastavitvi se deljene naprave prikažejo na strani naprav v Home Assistantu.

![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)

5. Seznanjanje, odstranjevanje, firmware, plačila, kartice SD in upravljanje računa ostanejo v aplikaciji X-Sense.

## Podprte naprave
Podprte so bazne postaje, detektorji dima, detektorji CO, toplotni alarmi, detektorji izliva vode, higrometri, senzorji vrat in gibanja, luči, tipkovnice, senzorji poštnega nabiralnika, poslušalne naprave in podprte kamere, kadar jih račun X-Sense poroča.

Potrjene družine modelov vključujejo: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## Entitete in dejanja
Integracija ustvari samo entitete za podatke, ki jih naprava dejansko poroča. To lahko vključuje alarme, utišanje, baterijo, signal, temperaturo, vlago, CO, berljive čase, nastavitve kamere, stikala LED, test, utišanje in požarno vajo.

Upravljanje naprav, deljenje, odstranjevanje, firmware, računi in plačila ostanejo v aplikaciji X-Sense. Za razprave uporabite Discord ali forum Home Assistant.

## Primeri avtomatizacij
```yaml
automation:
  - alias: "Opozorilo temperature X-Sense"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "Temperatura je presegla 30 stopinj!"
```

```yaml
automation:
  - alias: "Alarm izliva vode"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "Zaznan je izliv vode!"
```

## Podpora
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

## Dodatne podrobnosti

### Nastavitev računa

Priporočljivo je uporabiti ločen račun X-Sense za Home Assistant in z njim deliti samo podprte naprave, ki jih želite videti v Home Assistantu. Integracija ne seznanja, odstranjuje ali premika naprav med domovi. Takšno upravljanje naprav ostaja v uradni aplikaciji X-Sense.

### Posodobitve stanja

Integracija uporablja sporočila MQTT shadow za hitre spremembe stanja in previdno občasno poizvedovanje v oblaku za osveževanje podatkov. Stanje, ki ga sporoči postaja, se posodobi na postaji, stanje, ki ga sporoči podrejena naprava, pa na tej napravi, da alarmi in senzorji ne ostanejo pri starih vrednostih.

### Razpoložljive entitete

Glede na model se lahko prikažejo alarmi za dim, CO, vodo, temperaturo, gibanje in vrata, utišanje alarma, konec življenjske dobe, polnjenje, stanje opomnika, stanje luči in drugi diagnostični binarni senzorji. Senzorji lahko vključujejo baterijo, RF ali Wi-Fi signal, vdelano programsko opremo, temperaturo, vlago, raven CO, najvišjo vrednost CO, glasnost, pragove, berljive čase, časovni pas in drugo diagnostiko. Stikala, izbire in številčne vrednosti se ustvarijo samo, kadar jih naprava dejansko podpira.

### Kamere

Podprte kamere lahko zagotovijo entiteto kamere, sličice, prenos v živo, stanje povezave in nastavitve, usklajene z aplikacijo X-Sense. Če je v Home Assistantu na voljo pot WebRTC, jo lahko integracija uporabi za ustrezen prikaz v živo.

### Odpravljanje težav

Če entiteta manjka, najprej v aplikaciji X-Sense preverite, ali naprava res prikazuje to vrednost. Če stanje ostane zastarelo, ponovno naložite integracijo samo kot začasen preizkus in poročilu priložite diagnostiko ter ustrezne vrstice dnevnika Home Assistanta.

### Vedenje naprav

- Postaje in podrejene naprave lahko sporočajo različne nabore vrednosti. Integracija zato ne predpostavlja, da mora imeti vsaka postaja podrejeno napravo.
- Časovne vrednosti se pretvorijo v berljivo obliko, kadar naprava pošilja čas v formatu, ki ga uporablja aplikacija X-Sense.
- Entiteta se ne ustvari, če naprava te zmožnosti ne sporoča. Tako se v Home Assistantu ne pojavijo zavajajoči kontrolniki.

### Obremenitev oblaka

Integracija poskuša API X-Sense uporabljati varčno. Hitre spremembe prejme iz sporočil MQTT, klice v oblak pa uporablja samo tam, kjer so potrebni za prijavo, nalaganje naprav ali osvežitev stanja.

### Prijava težave

Pri prijavi napake navedite model naprave, različico integracije, ali je pravilna vrednost vidna v aplikaciji X-Sense, in priložite diagnostiko integracije iz Home Assistanta. Pomaga tudi kratek opis, ali se stanje nikoli ne spremeni ali se spremeni šele po ponovnem nalaganju integracije.

## Celoten referenčni del

### Nastavitev računa podrobno
- Za Home Assistant uporabite ločen račun X-Sense.
- Iz glavnega računa delite samo podprte naprave.
- Seznanjanje, odstranjevanje, deljenje in premikanje naprav ostanejo v aplikaciji X-Sense.
- Če se aplikacija in Home Assistant odjavljata med seboj, verjetno uporabljata isti račun.

### Posodobitve in obremenitev API-ja
- Hitre spremembe stanja se prejemajo prek sporočil MQTT shadow.
- Zahteve v oblak se uporabljajo za prijavo, nalaganje naprav in osvežitev stanja.
- Periodično preverjanje je rezerva, kadar sporočilo MQTT manjka.

### Entitete in dejanja
- Entitete se ustvarijo samo za polja, ki jih X-Sense dejansko sporoči.
- Diagnostične vrednosti so označene kot diagnostika.
- Test, utišanje, požarna vaja in prebujanje kamere so na voljo samo za podprte modele.

### Referenca za kamere
- Podprte kamere lahko zagotovijo entiteto kamere, sličico, prenos v živo in diagnostiko.
- WebRTC pot se uporabi samo, če je na voljo v Home Assistant.
- Kartica SD, plačila, vdelana programska oprema in upravljanje računa ostanejo v aplikaciji X-Sense.

### Kontrolni seznam za odpravljanje težav
- Prijava težave naj vsebuje model, različico integracije, diagnostiko in ustrezne dnevnike.

### Obseg
- Integracija ne dodaja, odstranjuje ali premika naprav med domovi.

## Kontrolni seznam naprav in entitet

### Glavne družine naprav
- SBS50: bazna postaja in stanje na ravni postaje.
- XS01-WX: Wi-Fi dimni alarm, tudi računi brez ločene podrejene naprave.
- XS01-M, XS03-WX, XS0B-MR: družine dimnih alarmov.
- XC01-M, XC04-WX: družine CO alarmov.
- SC07-WX, XP0A-MR: kombinirane družine dima in CO.
- XH02-M: družina toplotnih alarmov.
- SWS51: družina detektorjev puščanja vode.
- STH51, STH0A, STH0B, STH0C: temperatura in vlaga.
- SDS0A: senzor vrat.
- SMS0A: senzor gibanja.
- SSC0A, SSC0B: podprte kamere.

### Polja stanja
- Stanje alarma se prikaže, ko X-Sense sporoči polje alarma.
- Stanje utišanja se prikaže, ko X-Sense sporoči polje utišanja.
- Stanje baterije se prikaže, ko naprava sporoči podatke baterije.
- RF in Wi-Fi signal se prikažeta, ko ju naprava sporoči.
- Kompaktne časovne vrednosti se pretvorijo v berljive senzorje Home Assistant.

### Kontrole in poročila
- Stikala se ustvarijo samo za zapisljive nastavitve, ki jih sporoči X-Sense.
- Gumbi se ustvarijo samo za dejanja, ki jih podpira aplikacija.
- Kontrole kamere se ustvarijo samo, ko jih API označi kot razpoložljive.
- Prijava težave naj vsebuje natančen model, različico integracije, diagnostiko, dnevnike in ali se vrednost spreminja v aplikaciji X-Sense.

### Opombe za delovanje
- Po nastavitvi preverite, ali se imena naprav in prostori ujemajo z aplikacijo X-Sense.
- Če se alarm, utišanje ali LED ne spremeni takoj, počakajte na naslednje sporočilo MQTT ali osvežitev stanja.
- Pri postajah SBS50 preverite stanje postaje in posamezne podrejene naprave.
- Pri XS01-WX je lahko celotno stanje sporočeno neposredno na napravi, tudi brez ločene podrejene naprave v računu.
- Pri kamerah so ustvarjene entitete odvisne od zmožnosti, ki jih oblak X-Sense vrne za ta račun.
- Če entiteta ni ustvarjena, najprej primerjajte vrednost z aplikacijo X-Sense in priložite diagnostiko.
- Integracija je namenjena prikazu in upravljanju podprtih funkcij, ne pa zamenjavi seznanjanja ali upravljanja naprav v aplikaciji.
