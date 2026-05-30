# ha-xsense-component_test

## Pregled
Ta integracija za Home Assistant omogoča uporabo naprav X-Sense v pametnem domu. Temelji na izvirnem delu Thea Snela in se namesti prek HACS.

Priporočamo, da ustvarite ločen račun X-Sense za Home Assistant in iz glavnega računa delite samo podprte naprave.

## Namestitev
V HACS dodajte repozitorij po meri `https://github.com/Jarnsen/ha-xsense-component_test`, prenesite integracijo, sledite navodilom HACS za ponovni zagon in jo nato nastavite z računom X-Sense za Home Assistant.

## Podprte naprave
Podprte so bazne postaje, detektorji dima, detektorji CO, toplotni alarmi, detektorji izliva vode, higrometri, senzorji vrat in gibanja, luči, tipkovnice, senzorji poštnega nabiralnika, poslušalne naprave in podprte kamere, kadar jih račun X-Sense poroča.

Potrjene družine modelov vključujejo: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## Entitete in dejanja
Integracija ustvari samo entitete za podatke, ki jih naprava dejansko poroča. To lahko vključuje alarme, utišanje, baterijo, signal, temperaturo, vlago, CO, berljive čase, nastavitve kamere, stikala LED ter gumbe za test, utišanje in požarno vajo.

Upravljanje naprav, deljenje, odstranjevanje, firmware, računi in plačila ostanejo v aplikaciji X-Sense.

## Podpora
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)
