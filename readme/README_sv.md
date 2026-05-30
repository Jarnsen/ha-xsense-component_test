# ha-xsense-component_test

## Översikt
Den här Home Assistant-integrationen gör X-Sense-enheter tillgängliga i ditt smarta hem. Den bygger på Theo Snels ursprungliga arbete och installeras via HACS.

Vi rekommenderar att du skapar ett separat X-Sense-konto för Home Assistant och bara delar de enheter som stöds från huvudkontot.

## Installation
Lägg till `https://github.com/Jarnsen/ha-xsense-component_test` som anpassat repository i HACS, ladda ned integrationen, följ HACS anvisning för omstart och konfigurera sedan integrationen med X-Sense-kontot för Home Assistant.

## Enheter som stöds
Basstationer, brandvarnare, CO-detektorer, värmelarm, vattenläckagedetektorer, hygrometrar, dörr- och rörelsesensorer, lampor, knappsatser, brevlådesensorer, lyssnarenheter och kameror stöds när de rapporteras av X-Sense-kontot.

Bekräftade modellfamiljer omfattar: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## Entiteter och åtgärder
Integrationen skapar bara entiteter för data som enheten faktiskt rapporterar. Det kan omfatta larm, tyst läge, batteri, signal, temperatur, luftfuktighet, CO, läsbara tidsfält, kamerainställningar, LED-brytare samt knappar för test, tyst läge och brandövning.

Enhetshantering, delning, borttagning, firmware, konton och betalningar ligger kvar i X-Sense-appen.

## Support
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)
