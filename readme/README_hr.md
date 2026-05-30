# ha-xsense-component_test

## Pregled
Ova integracija za Home Assistant omogućuje korištenje X-Sense uređaja u pametnom domu. Temelji se na izvornom radu Thea Snela i instalira se putem HACS-a.

Preporučujemo stvaranje zasebnog X-Sense računa za Home Assistant i dijeljenje samo podržanih uređaja s glavnog računa.

## Instalacija
U HACS-u dodajte prilagođeni repozitorij `https://github.com/Jarnsen/ha-xsense-component_test`, preuzmite integraciju, slijedite HACS upute za ponovno pokretanje i zatim je konfigurirajte s X-Sense računom namijenjenim Home Assistantu.

## Podržani uređaji
Podržane su bazne stanice, detektori dima, detektori CO, toplinski alarmi, detektori curenja vode, higrometri, senzori vrata i pokreta, svjetla, tipkovnice, senzori poštanskog sandučića, uređaji za osluškivanje i podržane kamere kada ih X-Sense račun prijavljuje.

Potvrđene obitelji modela uključuju: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## Entiteti i radnje
Integracija stvara entitete samo za podatke koje uređaj stvarno prijavljuje. To može uključivati alarme, utišavanje, bateriju, signal, temperaturu, vlagu, CO, čitljiva vremenska polja, postavke kamera, LED prekidače te gumbe za test, utišavanje i protupožarnu vježbu.

Upravljanje uređajima, dijeljenje, uklanjanje, firmware, računi i plaćanja ostaju u aplikaciji X-Sense.

## Podrška
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)
