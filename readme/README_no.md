# ha-xsense-component_test

## Oversikt
Denne Home Assistant-integrasjonen gjør X-Sense-enheter tilgjengelige i smarthjemmet. Den bygger på Theo Snels opprinnelige arbeid og installeres via HACS.

Vi anbefaler å opprette en separat X-Sense-konto for Home Assistant og bare dele de støttede enhetene fra hovedkontoen.

## Installasjon
Legg til `https://github.com/Jarnsen/ha-xsense-component_test` som egendefinert repository i HACS, last ned integrasjonen, følg HACS' veiledning for omstart, og konfigurer deretter integrasjonen med X-Sense-kontoen for Home Assistant.

## Støttede enheter
Basestasjoner, røykvarslere, CO-detektorer, varmealarmer, vannlekkasjedetektorer, hygrometre, dør- og bevegelsessensorer, lys, tastaturer, postkassesensorer, lytteenheter og støttede kameraer støttes når X-Sense-kontoen rapporterer dem.

Bekreftede modellfamilier omfatter: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## Entiteter og handlinger
Integrasjonen oppretter bare entiteter for data enheten faktisk rapporterer. Det kan omfatte alarmer, demping, batteri, signal, temperatur, fuktighet, CO, lesbare tidsfelt, kamerainnstillinger, LED-brytere og knapper for test, demping og brannøvelse.

Enhetsadministrasjon, deling, fjerning, firmware, kontoer og betalinger forblir i X-Sense-appen.

## Støtte
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)
