# ha-xsense-component_test

## Apžvalga
Ši Home Assistant integracija leidžia naudoti X-Sense įrenginius išmaniajame name. Ji paremta pradiniu Theo Snel darbu ir diegiama per HACS.

Rekomenduojame sukurti atskirą X-Sense paskyrą Home Assistant ir iš pagrindinės paskyros bendrinti tik palaikomus įrenginius.

## Diegimas
HACS pridėkite pasirinktinę saugyklą `https://github.com/Jarnsen/ha-xsense-component_test`, atsisiųskite integraciją, vykdykite HACS paleidimo iš naujo nurodymus ir sukonfigūruokite ją su Home Assistant skirta X-Sense paskyra.

## Palaikomi įrenginiai
Palaikomos bazinės stotys, dūmų detektoriai, CO detektoriai, šilumos signalizacijos, vandens nuotėkio detektoriai, higrometrai, durų ir judesio jutikliai, šviesos, klaviatūros, pašto dėžutės jutikliai, klausymo įrenginiai ir palaikomos kameros, kai jas pateikia X-Sense paskyra.

Patvirtintos modelių šeimos apima: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## Esybės ir veiksmai
Integracija kuria esybes tik tiems duomenims, kuriuos įrenginys iš tikrųjų pateikia. Tai gali būti signalizacijos, nutildymas, baterija, signalas, temperatūra, drėgmė, CO, skaitomi laiko laukai, kameros nustatymai, LED jungikliai ir testavimo, nutildymo bei gaisro pratybų mygtukai.

Įrenginių valdymas, bendrinimas, šalinimas, firmware, paskyros ir mokėjimai lieka X-Sense programėlėje.

## Pagalba
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)
