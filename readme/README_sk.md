# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Prehľad
Táto integrácia pre Home Assistant sprístupňuje zariadenia X-Sense v inteligentnej domácnosti. Vychádza z pôvodnej práce Thea Snela a je určená na inštaláciu cez HACS.

Odporúčame vytvoriť druhý účet X-Sense pre Home Assistant a z hlavného účtu doň zdieľať iba podporované zariadenia.

## Kompatibilita a aktualizácie HACS
Ak stále používate starú verziu `v1.2.6.x`, aktualizujte na `v1.3.14` alebo novšiu pred aktualizáciou Home Assistant Core na 2026.7 alebo novšiu. Staré verzie vyžadovali `aiortc`, ktoré nie je kompatibilné s Python 3.14 runtime v Home Assistant. Aktuálne verzie `v1.3.x` už `aiortc` nevyžadujú.

Táto integrácia sa inštaluje ako vlastný HACS repozitár. Ak sa aktualizácia nezobrazí okamžite, otvorte HACS, vyberte repozitár X-Sense, spustite **Update information**, potom integráciu aktualizujte alebo znova stiahnite a reštartujte Home Assistant.

## Inštalácia
V HACS pridajte vlastný repozitár `https://github.com/Jarnsen/ha-xsense-component_test`, integráciu stiahnite, reštartujte Home Assistant podľa pokynov HACS a potom ju nastavte pomocou účtu X-Sense určeného pre Home Assistant.


## Podrobné nastavenie so snímkami obrazovky

1. Vytvorte samostatný účet X-Sense pre Home Assistant a z hlavného účtu zdieľajte iba podporované zariadenia.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

2. V HACS pridajte `https://github.com/Jarnsen/ha-xsense-component_test` ako vlastný repozitár.

![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

3. Stiahnite a nainštalujte integráciu, reštartujte Home Assistant a potom ju nastavte pomocou nového účtu X-Sense.

![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

4. Po úspešnom nastavení sa zdieľané zariadenia zobrazia na stránke zariadení v Home Assistante.

![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)

5. Párovanie, odstránenie, firmware, platby, SD karty a správa účtu zostávajú v aplikácii X-Sense.

## Podporované zariadenia
Podporované sú základňové stanice, detektory dymu, detektory CO, tepelné alarmy, detektory úniku vody, vlhkomery, dverové a pohybové senzory, svetlá, klávesnice, senzory poštovej schránky, posluchové zariadenia a podporované kamery, ak ich účet X-Sense poskytuje.

Potvrdené modelové rady zahŕňajú: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## Entity a akcie
Integrácia vytvára iba entity pre údaje, ktoré zariadenie skutočne hlási. Môže ísť o alarmy, stlmenie, batériu, signál, teplotu, vlhkosť, CO, čitateľné časové údaje, nastavenia kamier, LED prepínače, test, stlmenie a požiarne cvičenie.

Správa zariadení, zdieľanie, odstránenie, firmvér, účty a platby zostávajú v aplikácii X-Sense. Na diskusiu použite Discord alebo fórum Home Assistant.

## Živý náhľad kamery a oznámenia AI
Najjednoduchšie je importovať priložený blueprint tlačidlom nižšie, vybrať `Motion` alebo dostupné `AI Detection` a upraviť akciu oznámenia.

When a Motion event includes X-Sense playback metadata, the integration immediately tries to cache the clip. With recording links enabled, the default camera-event blueprint waits until cached media is ready, then sends a mobile notification that opens the matching X-Sense Recordings clip. Turn recording links off if you want a plain motion notification without waiting for video. Manual automation runs use the selected event entity's latest recording data. Recording media sync can keep recent clips ready in the background.

[![Importovať blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FJarnsen%2Fha-xsense-component_test%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fxsense%2Fcamera_ai_notification.yaml)

Motion a AI Detection sú jednorazové udalosti, nie stavy zapnuté/vypnuté. Pre manuálne automatizácie použite `event.received`; `event_type` používajte len na filtrovanie typov ako `person`, `pet`, `vehicle`, `package`, `other` alebo `ai_detection`.

Príklad automatizácie:

```yaml
alias: "Notify when X-Sense detects a person"
triggers:
  - trigger: event.received
    target:
      entity_id: event.front_camera_ai_detection
    options:
      event_type:
        - person
actions:
  - action: notify.mobile_app_phone
    data:
      message: "X-Sense camera detected a person."
```

____________________________________________________________
## Príklady automatizácií
```yaml
automation:
  - alias: "Upozornenie X-Sense na teplotu"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "Teplota prekročila 30 stupňov!"
```

```yaml
automation:
  - alias: "Alarm úniku vody"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "Zistený únik vody!"
```

## Podpora
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

## Ďalšie podrobnosti

### Nastavenie účtu

Odporúča sa používať pre Home Assistant samostatný účet X-Sense a zdieľať s ním iba podporované zariadenia, ktoré chcete v Home Assistante zobrazovať. Integrácia nepáruje, neodstraňuje ani nepresúva zariadenia medzi domácnosťami. Takáto správa zariadení zostáva v oficiálnej aplikácii X-Sense.

### Aktualizácie stavu

Integrácia používa správy MQTT shadow na rýchle zmeny stavu a opatrné periodické cloudové dopytovanie na obnovenie údajov. Stav nahlásený stanicou sa aktualizuje na stanici a stav nahlásený podriadeným zariadením sa aktualizuje na konkrétnom zariadení, aby alarmy a senzory nezostali na starých hodnotách.

### Dostupné entity

V závislosti od modelu sa môžu zobraziť alarmy dymu, CO, vody, teploty, pohybu a dverí, stlmenie alarmu, koniec životnosti, nabíjanie, stav pripomienky, stav svetla a ďalšie diagnostické binárne senzory. Senzory môžu zahŕňať batériu, RF alebo Wi-Fi signál, firmvér, teplotu, vlhkosť, úroveň CO, špičku CO, hlasitosť, prahové hodnoty, čitateľné časy, časové pásmo a ďalšiu diagnostiku. Prepínače, výbery a číselné hodnoty sa vytvoria iba vtedy, keď ich zariadenie skutočne podporuje.

### Kamery

### Riešenie problémov

Ak niektorá entita chýba, najprv v aplikácii X-Sense overte, že zariadenie túto hodnotu naozaj zobrazuje. Ak stav zostáva zastaraný, znova načítajte integráciu iba ako dočasný test a k hláseniu priložte diagnostiku aj príslušné riadky denníka Home Assistantu.

### Správanie zariadení

- Stanice a podriadené zariadenia môžu hlásiť rôzne sady hodnôt. Integrácia preto nepredpokladá, že každá stanica musí mať podriadené zariadenie.
- Časové hodnoty sa prevádzajú do čitateľnej podoby, keď zariadenie posiela čas vo formáte používanom aplikáciou X-Sense.
- Entita sa nevytvorí, ak zariadenie danú funkciu nehlási. Tým sa v Home Assistante nevytvárajú zavádzajúce ovládacie prvky.

### Zaťaženie cloudu

Integrácia sa snaží používať API X-Sense šetrne. Rýchle zmeny sa preberajú zo správ MQTT a cloudové volania sa používajú iba tam, kde sú potrebné na prihlásenie, načítanie zariadení alebo obnovenie stavu.

### Hlásenie problému

Pri hlásení chyby uveďte model zariadenia, verziu integrácie, či sa správna hodnota zobrazuje v aplikácii X-Sense, a priložte diagnostiku integrácie z Home Assistantu. Pomôže aj krátky opis, či sa stav nikdy nezmení alebo sa zmení až po opätovnom načítaní integrácie.

## Úplná referenčná časť

### Nastavenie účtu podrobne
- Pre Home Assistant používajte samostatný účet X-Sense.
- Z hlavného účtu zdieľajte iba podporované zariadenia.
- Párovanie, odstránenie, zdieľanie a presun zariadení zostávajú v aplikácii X-Sense.
- Ak sa aplikácia a Home Assistant navzájom odhlasujú, pravdepodobne používajú rovnaký účet.

### Aktualizácie a zaťaženie API
- Rýchle zmeny stavu sa prijímajú cez MQTT shadow správy.
- Cloudové požiadavky slúžia na prihlásenie, načítanie zariadení a obnovenie stavu.
- Periodické dotazovanie je záloha, keď MQTT správa chýba.

### Entity a akcie
- Entity sa vytvárajú iba pre polia, ktoré X-Sense skutočne hlási.
- Diagnostické hodnoty sú označené ako diagnostika.
- Test, stlmenie, požiarne cvičenie a prebudenie kamery sú dostupné iba pre podporované modely.

### Referencia pre kamery
- Podporované kamery môžu poskytovať entitu kamery, náhľad, živý stream a diagnostiku.
- SD karta, platby, firmvér a správa účtu zostávajú v aplikácii X-Sense.

### Kontrolný zoznam riešenia problémov
- Hlásenie problému má obsahovať model, verziu integrácie, diagnostiku a relevantné denníky.

### Rozsah
- Integrácia nepridáva, neodstraňuje ani nepresúva zariadenia medzi domácnosťami.

## Kontrolný zoznam zariadení a entít

### Hlavné rodiny zariadení
- SBS50: základňová stanica a stav na úrovni stanice.
- XS01-WX: Wi-Fi dymový hlásič vrátane účtov bez samostatného podriadeného zariadenia.
- XS01-M, XS03-WX, XS0B-MR: rodiny dymových hlásičov.
- XC01-M, XC04-WX: rodiny CO hlásičov.
- SC07-WX, XP0A-MR: kombinované rodiny dymu a CO.
- XH02-M: rodina tepelných hlásičov.
- SWS51: rodina detektorov úniku vody.
- STH51, STH0A, STH0B, STH0C: teplota a vlhkosť.
- SDS0A: dverový senzor.
- SMS0A: pohybový senzor.
- SSC0A, SSC0B: podporované kamery.

### Stavové polia
- Stav alarmu sa zobrazí, keď X-Sense hlási pole alarmu.
- Stav stlmenia sa zobrazí, keď X-Sense hlási pole stlmenia.
- Stav batérie sa zobrazí, keď zariadenie hlási údaje batérie.
- RF a Wi-Fi signál sa zobrazí, keď ho zariadenie hlási.
- Kompaktné časové hodnoty sa konvertujú na čitateľné senzory Home Assistant.

### Ovládanie a hlásenia
- Prepínače sa vytvárajú iba pre zapisovateľné nastavenia hlásené X-Sense.
- Tlačidlá sa vytvárajú iba pre akcie podporované aplikáciou.
- Ovládanie kamery sa vytvorí iba vtedy, keď ho API označí ako dostupné.
- Hlásenie problému má obsahovať presný model, verziu integrácie, diagnostiku, denníky a či sa hodnota mení v aplikácii X-Sense.

### Prevádzkové poznámky
- Po nastavení skontrolujte, či názvy zariadení a miestnosti zodpovedajú aplikácii X-Sense.
- Ak sa alarm, stlmenie alebo LED nezmení okamžite, počkajte na ďalšiu MQTT správu alebo obnovenie stavu.
- Pri staniciach SBS50 kontrolujte stav stanice aj jednotlivé podriadené zariadenia.
- Pri XS01-WX môže byť celý stav hlásený priamo na zariadení, aj bez samostatného podriadeného zariadenia v účte.
- Pri kamerách závisia vytvorené entity od schopností, ktoré cloud X-Sense vráti pre daný účet.
- Ak sa entita nevytvorí, najprv porovnajte hodnotu s aplikáciou X-Sense a priložte diagnostiku.
- Integrácia má zobrazovať a ovládať podporované funkcie, nie nahrádzať párovanie alebo správu zariadení v aplikácii.
