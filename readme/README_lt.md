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

Įrenginių valdymas, bendrinimas, šalinimas, firmware, paskyros ir mokėjimai lieka X-Sense programėlėje. Diskusijoms naudokite Discord arba Home Assistant forumą.

## Automatizavimo pavyzdžiai
```yaml
automation:
  - alias: "X-Sense temperatūros įspėjimas"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "Temperatūra viršijo 30 laipsnių!"
```

```yaml
automation:
  - alias: "Vandens nuotėkio signalizacija"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "Aptiktas vandens nuotėkis!"
```

## Pagalba
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

## Daugiau informacijos

### Paskyros nustatymas

Rekomenduojama Home Assistant naudoti atskirą X-Sense paskyrą ir su ja bendrinti tik tuos palaikomus įrenginius, kuriuos norite matyti Home Assistant. Integracija nesusieja, nešalina ir neperkelia įrenginių tarp namų. Tokį įrenginių valdymą ir toliau reikia atlikti oficialioje X-Sense programėlėje.

### Būsenos atnaujinimai

Integracija naudoja MQTT shadow pranešimus greitiems būsenos pokyčiams ir atsargų periodinį debesies užklausimą duomenims atnaujinti. Stoties pateikta būsena atnaujinama stotyje, o antrinio įrenginio pateikta būsena atnaujinama konkrečiame įrenginyje, kad signalai ir jutikliai neužstrigtų su senomis reikšmėmis.

### Galimi objektai

Priklausomai nuo modelio gali būti rodomi dūmų, CO, vandens, temperatūros, judesio ir durų signalai, signalo nutildymas, eksploatacijos pabaiga, įkrovimas, priminimo būsena, šviesos būsena ir kiti diagnostiniai dvejetainiai jutikliai. Jutikliai gali apimti bateriją, RF arba Wi-Fi signalą, programinę aparatinę įrangą, temperatūrą, drėgmę, CO lygį, CO piką, garsumą, slenksčius, lengvai skaitomą laiką, laiko juostą, serijos numerį, MAC adresą ir kitą diagnostiką. Jungikliai, pasirinkimai ir skaitinės reikšmės kuriami tik tada, kai įrenginys juos tikrai palaiko.

### Kameros

Palaikomos kameros gali pateikti kameros objektą, miniatiūras, tiesioginį srautą, ryšio būseną ir nustatymus, suderintus su X-Sense programėle. Jei Home Assistant yra WebRTC kelias, integracija gali jį naudoti tinkamai tiesioginei peržiūrai.

### Trikčių šalinimas

Jei objektas nerodomas, pirmiausia X-Sense programėlėje patikrinkite, ar įrenginys iš tiesų pateikia tą reikšmę. Jei būsena lieka pasenusi, perkraukite integraciją tik kaip laikiną bandymą ir prie pranešimo pridėkite diagnostiką bei susijusias Home Assistant žurnalo eilutes.

### Įrenginių veikimas

- Stotys ir antriniai įrenginiai gali pranešti skirtingus reikšmių rinkinius. Todėl integracija nemano, kad kiekviena stotis būtinai turi turėti antrinį įrenginį.
- Laiko reikšmės paverčiamos į skaitomą formatą, kai įrenginys siunčia laiką X-Sense programėlės naudojamu formatu.
- Objektas nekuriamas, jei įrenginys nepraneša apie tą funkciją. Taip Home Assistant neatsiranda klaidinančių valdiklių.

### Debesies apkrova

Integracija stengiasi taupiai naudoti X-Sense API. Greiti pakeitimai gaunami iš MQTT pranešimų, o debesies užklausos naudojamos tik tada, kai jų reikia prisijungimui, įrenginių įkėlimui arba būsenos atnaujinimui.

### Problemos pranešimas

Pranešdami apie klaidą nurodykite įrenginio modelį, integracijos versiją, ar teisinga reikšmė matoma X-Sense programėlėje, ir pridėkite Home Assistant integracijos diagnostiką. Taip pat naudinga trumpai parašyti, ar būsena niekada nesikeičia, ar pasikeičia tik perkrovus integraciją.

## Išsami nuorodų dalis

### Paskyros nustatymas išsamiai
- Home Assistant naudokite atskirą X-Sense paskyrą.
- Iš pagrindinės paskyros bendrinkite tik palaikomus įrenginius.
- Susiejimas, šalinimas, bendrinimas ir perkėlimas lieka X-Sense programėlėje.
- Jei programėlė ir Home Assistant viena kitą atjungia, tikriausiai naudojama ta pati paskyra.

### Atnaujinimai ir API apkrova
- Greiti būsenos pokyčiai gaunami per MQTT shadow pranešimus.
- Debesijos užklausos naudojamos prisijungimui, įrenginių įkėlimui ir būsenai atnaujinti.
- Periodinė apklausa yra atsarga, kai MQTT pranešimas negaunamas.

### Esybės ir veiksmai
- Esybės kuriamos tik laukams, kuriuos X-Sense iš tikrųjų praneša.
- Diagnostinės reikšmės pažymimos kaip diagnostika.
- Testas, nutildymas, gaisro pratybos ir kameros pažadinimas rodomi tik palaikomiems modeliams.

### Kameros
- Palaikomos kameros gali pateikti kameros esybę, miniatiūrą, tiesioginę transliaciją ir diagnostiką.
- WebRTC kelias naudojamas tik tada, kai jis prieinamas Home Assistant.
- SD kortelės, mokėjimų, programinės aparatinės įrangos ir paskyros tvarkymas lieka X-Sense programėlėje.

### Trikčių šalinimas
- Pranešime nurodykite modelį, integracijos versiją, diagnostiką ir aktualius žurnalus.

### Apimtis
- Integracija neprideda, nepašalina ir neperkelia įrenginių tarp namų.

## Įrenginių ir esybių kontrolinis sąrašas

### Pagrindinės įrenginių šeimos
- SBS50: bazinė stotis ir stoties lygio būsena.
- XS01-WX: Wi-Fi dūmų signalizatorius, įskaitant paskyras be atskiro antrinio įrenginio.
- XS01-M, XS03-WX, XS0B-MR: dūmų signalizatorių šeimos.
- XC01-M, XC04-WX: CO signalizatorių šeimos.
- SC07-WX, XP0A-MR: kombinuotos dūmų ir CO šeimos.
- XH02-M: karščio signalizatoriaus šeima.
- SWS51: vandens nuotėkio detektoriaus šeima.
- STH51, STH0A, STH0B, STH0C: temperatūra ir drėgmė.
- SDS0A: durų jutiklis.
- SMS0A: judesio jutiklis.
- SSC0A, SSC0B: palaikomos kameros.

### Būsenos laukai
- Aliarmo būsena rodoma, kai X-Sense praneša aliarmo lauką.
- Nutildymo būsena rodoma, kai X-Sense praneša nutildymo lauką.
- Baterijos būsena rodoma, kai įrenginys praneša baterijos duomenis.
- RF ir Wi-Fi signalas rodomas, kai įrenginys jį praneša.
- Kompaktiškos laiko reikšmės paverčiamos skaitomais Home Assistant jutikliais.

### Valdikliai ir pranešimai
- Jungikliai kuriami tik X-Sense praneštiems rašomiems nustatymams.
- Mygtukai kuriami tik programėlės palaikomiems veiksmams.
- Kameros valdikliai kuriami tik kai API pažymi juos kaip prieinamus.
- Pranešime apie problemą nurodykite tikslų modelį, integracijos versiją, diagnostiką, žurnalus ir ar reikšmė keičiasi X-Sense programėlėje.

### Naudojimo pastabos
- Po sąrankos patikrinkite, ar įrenginių pavadinimai ir kambariai sutampa su X-Sense programėle.
- Jei aliarmas, nutildymas arba LED būsena nepasikeičia iš karto, palaukite kito MQTT pranešimo arba būsenos atnaujinimo.
- SBS50 stotims tikrinkite ir stoties būseną, ir atskirus antrinius įrenginius.
- XS01-WX gali pranešti visą būseną tiesiogiai įrenginyje, net jei paskyroje nėra atskiro antrinio įrenginio.
- Kameroms sukuriami subjektai priklauso nuo galimybių, kurias X-Sense debesis grąžina konkrečiai paskyrai.
- Jei subjektas nesukuriamas, pirmiausia palyginkite reikšmę su X-Sense programėle ir pridėkite diagnostiką.
- Integracija skirta palaikomoms funkcijoms rodyti ir valdyti, o ne pakeisti susiejimą ar įrenginių valdymą programėlėje.
