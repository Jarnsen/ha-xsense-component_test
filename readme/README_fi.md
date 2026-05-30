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

Laitteiden hallinta, jakaminen, poistaminen, laiteohjelmisto, tilit ja maksut pysyvät X-Sense-sovelluksessa.

## Tuki
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)
