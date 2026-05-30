# ha-xsense-component_test

## Pārskats
Šī Home Assistant integrācija padara X-Sense ierīces pieejamas viedajā mājā. Tā balstīta uz Theo Snel sākotnējo darbu un tiek instalēta ar HACS.

Iesakām izveidot atsevišķu X-Sense kontu Home Assistant vajadzībām un no galvenā konta kopīgot tikai atbalstītās ierīces.

## Instalēšana
HACS pievienojiet pielāgoto repozitoriju `https://github.com/Jarnsen/ha-xsense-component_test`, lejupielādējiet integrāciju, izpildiet HACS restartēšanas norādījumus un konfigurējiet to ar Home Assistant paredzēto X-Sense kontu.

## Atbalstītās ierīces
Atbalstītas ir bāzes stacijas, dūmu detektori, CO detektori, karstuma trauksmes, ūdens noplūdes detektori, higrometri, durvju un kustības sensori, gaismas, tastatūras, pastkastīšu sensori, klausīšanās ierīces un atbalstītas kameras, ja X-Sense konts tās ziņo.

Apstiprinātās modeļu saimes ietver: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## Entītijas un darbības
Integrācija izveido entītijas tikai tiem datiem, kurus ierīce patiešām ziņo. Tie var būt trauksmes, klusuma režīms, baterija, signāls, temperatūra, mitrums, CO, salasāmi laika lauki, kameras iestatījumi, LED slēdži un testa, klusuma un ugunsdrošības mācību pogas.

Ierīču pārvaldība, kopīgošana, noņemšana, firmware, konti un maksājumi paliek X-Sense lietotnē.

## Atbalsts
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)
