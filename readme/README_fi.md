# ha-xsense-component_test

## Yleiskatsaus
Tämä Home Assistant -integraatio tuo X-Sense-laitteet älykotiin. Se perustuu Theo Snelin alkuperäiseen työhön ja asennetaan HACS:n kautta.

Suosittelemme luomaan erillisen X-Sense-tilin Home Assistantia varten ja jakamaan päätililtä vain tuetut laitteet.

## Asennus
Lisää HACS:ssa mukautettu arkisto `https://github.com/Jarnsen/ha-xsense-component_test`, lataa integraatio, noudata HACS:n uudelleenkäynnistysohjetta ja määritä integraatio Home Assistantille luodulla X-Sense-tilillä.

## Tuetut laitteet
Tuettuja ovat tukiasemat, palovaroittimet, CO-ilmaisimet, lämpöhälyttimet, vesivuotoilmaisimet, kosteusmittarit, ovi- ja liiketunnistimet, valot, näppäimistöt, postilaatikkoanturit, kuuntelulaitteet ja tuetut kamerat, kun X-Sense-tili raportoi ne.

Vahvistetut malliperheet sisältävät: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## Entiteetit ja toiminnot
Integraatio luo entiteettejä vain tiedoille, jotka laite todella raportoi. Näitä voivat olla hälytykset, mykistys, akku, signaali, lämpötila, kosteus, CO, luettavat aikakentät, kamera-asetukset, LED-kytkimet sekä testaus-, mykistys- ja paloharjoituspainikkeet.

Laitteiden hallinta, jakaminen, poistaminen, laiteohjelmisto, tilit ja maksut pysyvät X-Sense-sovelluksessa. Keskusteluihin voi käyttää Discordia tai Home Assistant -foorumia.

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

Mallista riippuen näkyviin voi tulla savu-, CO-, vesi-, lämpötila-, liike- ja ovihälytyksiä, hälytyksen vaimennus, käyttöiän päättyminen, lataus, muistutuksen tila, valon tila sekä muita diagnostisia binääriantureita. Antureihin voi kuulua akku, RF- tai Wi-Fi-signaali, laiteohjelmisto, lämpötila, kosteus, CO-pitoisuus, CO-huippuarvo, äänenvoimakkuus, raja-arvot, luettavat aikaleimat, aikavyöhyke, sarjanumero, MAC-osoite ja muuta diagnostiikkaa. Kytkimet, valinnat ja numerokentät luodaan vain, kun laite todella tukee niitä.

### Kamerat

Tuetut kamerat voivat tarjota kameraentiteetin, pikkukuvat, live-lähetyksen, yhteyden tilan ja X-Sense-sovelluksen mukaiset asetukset. Jos Home Assistantissa on käytettävissä WebRTC-polku, integraatio voi käyttää sitä sopivaan live-katseluun.

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

### Kamerat
- Tuetut kamerat voivat tarjota kameraentiteetin, esikatselun, live-streamin ja diagnostiikkaa.
- WebRTC-polku käytetään vain, jos se on Home Assistantissa saatavilla.
- SD-kortti, maksut, laiteohjelmisto ja tilinhallinta pysyvät X-Sense-sovelluksessa.

### Vianmääritys
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
