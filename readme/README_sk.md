# ha-xsense-component_test

## Prehľad
Táto integrácia pre Home Assistant sprístupňuje zariadenia X-Sense v inteligentnej domácnosti. Vychádza z pôvodnej práce Thea Snela a inštaluje sa cez HACS.

Odporúčame vytvoriť samostatný účet X-Sense pre Home Assistant a z hlavného účtu doň zdieľať iba podporované zariadenia.

## Inštalácia
V HACS pridajte vlastný repozitár `https://github.com/Jarnsen/ha-xsense-component_test`, integráciu stiahnite, postupujte podľa pokynov HACS na reštart a potom ju nastavte pomocou účtu X-Sense určeného pre Home Assistant.

## Podporované zariadenia
Podporované sú základňové stanice, detektory dymu, detektory CO, tepelné alarmy, detektory úniku vody, vlhkomery, dverové a pohybové senzory, svetlá, klávesnice, senzory poštovej schránky, posluchové zariadenia a podporované kamery, ak ich účet X-Sense poskytuje.

Potvrdené modelové rady zahŕňajú: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## Entity a akcie
Integrácia vytvára iba entity pre údaje, ktoré zariadenie skutočne hlási. Môže ísť o alarmy, stlmenie, batériu, signál, teplotu, vlhkosť, CO, čitateľné časové údaje, nastavenia kamier, LED prepínače a tlačidlá testu, stlmenia alebo požiarneho cvičenia.

Správa zariadení, zdieľanie, odstránenie, firmvér, účty a platby zostávajú v aplikácii X-Sense.

## Podpora
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)
