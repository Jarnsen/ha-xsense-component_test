# ha-xsense-component_test

## Oversigt
Denne Home Assistant-integration gør X-Sense-enheder tilgængelige i dit smart home. Den bygger på Theo Snels oprindelige arbejde og installeres via HACS.

Vi anbefaler at oprette en separat X-Sense-konto til Home Assistant og kun dele de understøttede enheder fra hovedkontoen.

## Installation
Tilføj `https://github.com/Jarnsen/ha-xsense-component_test` som brugerdefineret repository i HACS, download integrationen, følg HACS' genstartsvejledning, og konfigurer derefter integrationen med X-Sense-kontoen til Home Assistant.

## Understøttede enheder
Understøttet er basestationer, røgalarmer, CO-detektorer, varmealarmer, vandlækagedetektorer, hygrometre, dør- og bevægelsessensorer, lys, tastaturer, postkassesensorer, lytteenheder og understøttede kameraer, når X-Sense-kontoen rapporterer dem.

Bekræftede modelfamilier omfatter: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## Entiteter og handlinger
Integrationen opretter kun entiteter for data, som enheden faktisk rapporterer. Det kan være alarmer, lydløs status, batteri, signal, temperatur, fugtighed, CO, læsbare tidsfelter, kameraindstillinger, LED-kontakter samt knapper til test, lydløs og brandøvelse.

Enhedsadministration, deling, fjernelse, firmware, konti og betalinger forbliver i X-Sense-appen.

## Support
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)
