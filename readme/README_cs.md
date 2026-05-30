# ha-xsense-component_test

## Přehled
Tato integrace pro Home Assistant zpřístupňuje zařízení X-Sense v chytré domácnosti. Vychází z původní práce Theo Snela a instaluje se přes HACS.

Doporučujeme vytvořit samostatný účet X-Sense pro Home Assistant a z hlavního účtu do něj sdílet pouze podporovaná zařízení.

## Instalace
V HACS přidejte vlastní repozitář `https://github.com/Jarnsen/ha-xsense-component_test`, integraci stáhněte, postupujte podle pokynů HACS pro restart a poté ji nastavte pomocí účtu X-Sense určeného pro Home Assistant.

## Podporovaná zařízení
Podporovány jsou základnové stanice, kouřové hlásiče, detektory CO, tepelné hlásiče, detektory úniku vody, hygrometry, dveřní a pohybové senzory, světla, klávesnice, poštovní senzory, naslouchací zařízení a podporované kamery, pokud je účet X-Sense poskytuje.

Potvrzené modelové řady zahrnují: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## Entity a akce
Integrace vytváří pouze entity pro data, která zařízení skutečně hlásí. Může jít o alarmy, ztlumení, baterii, signál, teplotu, vlhkost, CO, čitelné časové údaje, nastavení kamer, přepínače LED a tlačítka testu, ztlumení nebo požárního cvičení.

Správa zařízení, sdílení, odebrání, firmware, účty a platby zůstávají v aplikaci X-Sense.

## Podpora
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)
