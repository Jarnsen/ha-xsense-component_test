# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linkitetyt julkaisutiedot jokaiselle julkaistulle versiolle.


<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Yleiskatsaus
Tämä Home Assistant -integraatio tuo X-Sense-laitteet älykotiin. Se perustuu Theo Snelin alkuperäiseen työhön ja asennetaan HACS:n kautta.

Suosittelemme luomaan erillisen X-Sense-tilin Home Assistantia varten ja jakamaan päätililtä vain tuetut laitteet.

## Yhteensopivuus ja HACS-päivitykset
Jos käytät edelleen vanhaa `v1.2.6.x`-versiota, päivitä versioon `v1.3.14` tai uudempaan ennen Home Assistant Core 2026.7:ään tai uudempaan päivittämistä. Vanhat versiot vaativat `aiortc`-paketin, joka ei ole yhteensopiva Home Assistantin Python 3.14 -ajoympäristön kanssa. Nykyiset `v1.4.x`-versiot eivät enää vaadi `aiortc`-pakettia.

Tämä integraatio asennetaan HACS:n mukautettuna repositoriona. Jos päivitys ei näy heti, avaa HACS, valitse X-Sense-repositorio, suorita **Update information**, päivitä tai lataa integraatio uudelleen ja käynnistä Home Assistant uudelleen.


Entity changes: [X-Sense Entity Changes](../ENTITY_CHANGES.md).
## Asennus
Lisää HACS:ssa mukautettu arkisto `https://github.com/Jarnsen/ha-xsense-component_test`, lataa integraatio, noudata HACS:n uudelleenkäynnistysohjetta ja määritä integraatio Home Assistantille luodulla X-Sense-tilillä.


## Yksityiskohtainen käyttöönotto kuvakaappauksilla

1. Luo Home Assistantia varten erillinen X-Sense-tili ja jaa päätililtä vain tuetut laitteet.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

2. Lisää HACSissa mukautetuksi repositorioksi `https://github.com/Jarnsen/ha-xsense-component_test`.

![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

3. Lataa ja asenna integraatio, käynnistä Home Assistant uudelleen ja määritä integraatio uudella X-Sense-tilillä.

![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

4. Onnistuneen määrityksen jälkeen jaetut laitteet näkyvät Home Assistantin laitesivulla.

![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)

5. Paritus, poisto, laiteohjelmisto, maksut, SD-kortit ja tilinhallinta pysyvät X-Sense-sovelluksessa.

## Tuetut laitteet
Tuettuja ovat tukiasemat, palovaroittimet, CO-ilmaisimet, lämpöhälyttimet, vesivuotoilmaisimet, kosteusmittarit, ovi- ja liiketunnistimet, valot, näppäimistöt, postilaatikkoanturit, kuuntelulaitteet ja tuetut kamerat, kun X-Sense-tili raportoi ne.

Vahvistetut malliperheet sisältävät: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## Entiteetit ja toiminnot
Integraatio luo entiteettejä vain tiedoille, jotka laite todella raportoi. Näitä voivat olla hälytykset, mykistys, akku, signaali, lämpötila, kosteus, CO, luettavat aikakentät, kamera-asetukset, LED-kytkimet sekä testaus-, mykistys- ja paloharjoituspainikkeet.

Laitteiden hallinta, jakaminen, poistaminen, laiteohjelmisto, tilit ja maksut pysyvät X-Sense-sovelluksessa. Keskusteluihin voi käyttää Discordia tai Home Assistant -foorumia.

## Kameran live-näkymä ja AI-ilmoitukset
Helpoin tapa on tuoda mukana oleva blueprint alla olevalla painikkeella, valita `Motion` tai saatavilla oleva `AI Detection` ja muokata ilmoitustoimintoa.

Kun Motion-tapahtuma sisältää X-Sense-toistotietoja, integraatio voi ensin välimuistittaa leikkeen ja lähettää sen jälkeen mobiili-ilmoituksen, joka avaa vastaavan leikkeen X-Sense Recordings -näkymässä. Poista tallennuslinkit käytöstä blueprintissä, jos haluat vain yksinkertaisen liikeilmoituksen ilman videon odottamista. Tallennusmedian synkronointi voi pitää uusimmat leikkeet valmiina taustalla, ja vanhemmat tuodut X-Sense-kamerablueprintit päivittyvät automaattisesti.

[![Tuo blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FJarnsen%2Fha-xsense-component_test%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fxsense%2Fcamera_ai_notification.yaml)

Motion ja AI Detection ovat kertaluonteisia tapahtumia, eivät päälle/pois-tiloja. Käytä manuaalisissa automaatioissa `event.received`; käytä `event_type` vain suodattamaan tyyppejä kuten `person`, `pet`, `vehicle`, `package`, `other` tai `ai_detection`.

Esimerkkiautomaatio:

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
## Automaatioesimerkkejä
```yaml
automation:
  - alias: "X-Sense lämpötilahälytys"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "Lämpötila ylittää 30 astetta!"
```

```yaml
automation:
  - alias: "Vesivuotohälytys"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "Vesivuoto havaittu!"
```

## Tuki
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

## Lisätiedot

### Tilin määritys

Home Assistantia varten suositellaan erillistä X-Sense-tiliä, jolle jaetaan vain ne tuetut laitteet, jotka halutaan näkyviin Home Assistantissa. Integraatio ei parita, poista eikä siirrä laitteita kotien välillä. Laitteiden hallinta tehdään edelleen virallisessa X-Sense-sovelluksessa.

### Tilapäivitykset

Integraatio käyttää nopeisiin tilamuutoksiin MQTT shadow -viestejä ja tietojen virkistämiseen maltillista säännöllistä pilvikyselyä. Aseman ilmoittama tila tallennetaan asemalle ja alilaitteen ilmoittama tila kyseiselle laitteelle, jotta hälytykset ja anturit eivät jää vanhoihin arvoihin.

### Saatavilla olevat entiteetit

Mallista riippuen näkyviin voi tulla savu-, CO-, vesi-, lämpötila-, liike- ja ovihälytyksiä, hälytyksen vaimennus, käyttöiän päättyminen, lataus, muistutuksen tila, valon tila sekä muita diagnostisia binääriantureita. Antureihin voi kuulua akku, RF- tai Wi-Fi-signaali, laiteohjelmisto, lämpötila, kosteus, CO-pitoisuus, CO-huippuarvo, äänenvoimakkuus, raja-arvot, luettavat aikaleimat, aikavyöhyke ja muuta diagnostiikkaa. Kytkimet, valinnat ja numerokentät luodaan vain, kun laite todella tukee niitä.

### Kamerat

### Vianmääritys

Jos jokin entiteetti puuttuu, tarkista ensin X-Sense-sovelluksesta, että kyseinen arvo on oikeasti laitteen tarjoama. Jos tila jää vanhaksi, lataa integraatio uudelleen vain väliaikaisena testinä ja liitä virheilmoitukseen diagnostiikka sekä asiaankuuluvat Home Assistant -lokirivit.

### Laitteiden toiminta

- Asemat ja alilaitteet voivat ilmoittaa eri arvojoukkoja. Siksi integraatio ei oleta, että jokaisella asemalla täytyy olla alilaite.
- Aika-arvot muunnetaan luettavaan muotoon, kun laite lähettää ajan X-Sense-sovelluksen käyttämässä muodossa.
- Entiteettiä ei luoda, jos laite ei ilmoita kyseistä toimintoa. Näin Home Assistantiin ei synny harhaanjohtavia ohjaimia.

### Pilven kuormitus

Integraatio pyrkii käyttämään X-Sensen APIa säästeliäästi. Nopeat muutokset saadaan MQTT-viesteistä, ja pilvikutsuja käytetään vain kirjautumiseen, laitteiden lataamiseen tai tilan päivittämiseen tarvittaessa.

### Ongelman ilmoittaminen

Kun ilmoitat viasta, kerro laitteen malli, integraation versio, näkyykö oikea arvo X-Sense-sovelluksessa, ja liitä mukaan Home Assistantin integraatiodiagnostiikka. Kerro myös lyhyesti, muuttuuko tila lainkaan vai vasta integraation uudelleenlatauksen jälkeen.

## Täydellinen viiteosa

### Tilin määritys tarkemmin
- Käytä Home Assistantia varten erillistä X-Sense-tiliä.
- Jaa päätililtä vain tuetut laitteet.
- Paritus, poisto, jakaminen ja siirrot pysyvät X-Sense-sovelluksessa.
- Jos sovellus ja Home Assistant kirjaavat toisensa ulos, ne käyttävät todennäköisesti samaa tiliä.

### Päivitykset ja API-kuorma
- Nopeat tilamuutokset vastaanotetaan MQTT shadow -viesteistä.
- Pilvikyselyjä käytetään kirjautumiseen, laitteiden lataamiseen ja tilan päivitykseen.
- Säännöllinen kysely on varmistus, jos MQTT-viesti puuttuu.

### Entiteetit ja toiminnot
- Entiteetit luodaan vain kentille, joita X-Sense todella raportoi.
- Diagnostiikka-arvot merkitään diagnostiikaksi.
- Testi, mykistys, paloharjoitus ja kameran herätys näkyvät vain tuetuilla malleilla.

### Kameraviite
- Tuetut kamerat voivat tarjota kameraentiteetin, esikatselun, live-streamin ja diagnostiikkaa.
- SD-kortti, maksut, laiteohjelmisto ja tilinhallinta pysyvät X-Sense-sovelluksessa.

### Vianmäärityksen tarkistuslista
- Virheraporttiin tarvitaan malli, integraation versio, diagnostiikka ja relevantit lokit.

### Rajaus
- Integraatio ei lisää, poista tai siirrä laitteita kotien välillä.

## Laitteiden ja entiteettien tarkistuslista

### Keskeiset laiteperheet
- SBS50: tukiasema ja aseman tason tila.
- XS01-WX: Wi-Fi-savuhälytin, myös tilit ilman erillistä alilaitetta.
- XS01-M, XS03-WX, XS0B-MR: savuhälytinperheet.
- XC01-M, XC04-WX: CO-hälytinperheet.
- SC07-WX, XP0A-MR: yhdistetyt savu- ja CO-perheet.
- XH02-M: lämpöhälytinperhe.
- SWS51: vesivuotoanturin perhe.
- STH51, STH0A, STH0B, STH0C: lämpötila ja kosteus.
- SDS0A: ovianturi.
- SMS0A: liiketunnistin.
- SSC0A, SSC0B: tuetut kamerat.

### Tilakentät
- Hälytystila näytetään, kun X-Sense raportoi hälytyskentän.
- Mykistystila näytetään, kun X-Sense raportoi mykistyskentän.
- Akun tila näytetään, kun laite raportoi akkudataa.
- RF- ja Wi-Fi-signaali näytetään, kun laite raportoi ne.
- Kompaktit aikaleimat muunnetaan luettaviksi Home Assistant -sensoreiksi.

### Ohjaimet ja raportointi
- Kytkimet luodaan vain X-Sensen raportoimille kirjoitettaville asetuksille.
- Painikkeet luodaan vain sovelluksen tukemille toiminnoille.
- Kameraohjaimet luodaan vain, kun API merkitsee ne saataville.
- Virheraporttiin tarvitaan tarkka malli, integraation versio, diagnostiikka, lokit ja tieto muuttuuko arvo X-Sense-sovelluksessa.

### Käyttöhuomiot
- Tarkista käyttöönoton jälkeen, että laitteiden nimet ja huoneet vastaavat X-Sense-sovellusta.
- Jos hälytys, mykistys tai LED ei muutu heti, odota seuraavaa MQTT-viestiä tai tilapäivitystä.
- SBS50-asemissa kannattaa tarkistaa sekä aseman tila että yksittäiset alilaitteet.
- XS01-WX voi raportoida koko tilan suoraan laitteen kautta, vaikka tilillä ei olisi erillistä alilaitetta.
- Kameroissa luotavat entiteetit riippuvat siitä, mitä toimintoja X-Sense-pilvi palauttaa kyseiselle tilille.
- Jos entiteettiä ei luoda, vertaa arvo ensin X-Sense-sovellukseen ja liitä mukaan diagnostiikka.
- Integraation tarkoitus on näyttää ja ohjata tuettuja toimintoja, ei korvata paritusta tai laitehallintaa sovelluksessa.
