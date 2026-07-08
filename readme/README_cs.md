# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - propojené poznámky k vydání pro každou publikovanou verzi.


<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Přehled
Tato integrace pro Home Assistant zpřístupňuje zařízení X-Sense v chytré domácnosti. Vychází z původní práce Theo Snela a je určena pro instalaci přes HACS.

Doporučujeme vytvořit druhý účet X-Sense určený pro Home Assistant a z hlavního účtu do něj sdílet pouze podporovaná zařízení.

## Kompatibilita a aktualizace HACS
Pokud stále používáte staré sestavení `v1.2.6.x`, aktualizujte na `v1.3.14` nebo novější před aktualizací Home Assistant Core na 2026.7 nebo novější. Staré verze vyžadovaly `aiortc`, které není kompatibilní s Pythonem 3.14 v Home Assistant. Aktuální verze `v1.3.x` už `aiortc` nevyžadují.

Tato integrace se instaluje jako vlastní repozitář HACS. Pokud se aktualizace nezobrazí hned, otevřete HACS, vyberte repozitář X-Sense, spusťte **Update information**, poté integraci aktualizujte nebo znovu stáhněte a restartujte Home Assistant.


Entity changes: [X-Sense Entity Changes](../ENTITY_CHANGES.md).
## Instalace
V HACS přidejte vlastní repozitář `https://github.com/Jarnsen/ha-xsense-component_test`, integraci stáhněte, restartujte Home Assistant podle pokynů HACS a potom integraci nastavte pomocí účtu X-Sense určeného pro Home Assistant.


## Podrobné nastavení se snímky obrazovky

1. Vytvořte samostatný účet X-Sense pro Home Assistant a z hlavního účtu sdílejte pouze podporovaná zařízení.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

2. V HACS přidejte vlastní repozitář `https://github.com/Jarnsen/ha-xsense-component_test`.

![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

3. Integraci stáhněte, nainstalujte, restartujte Home Assistant a potom ji nastavte pomocí nového účtu X-Sense.

![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

4. Po úspěšném nastavení se sdílená zařízení zobrazí na stránce zařízení v Home Assistantu.

![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)

5. Párování, odebrání, firmware, platby, SD karty a správa účtu zůstávají v aplikaci X-Sense.

## Podporovaná zařízení
Podporovány jsou základnové stanice, kouřové hlásiče, detektory CO, tepelné hlásiče, detektory úniku vody, hygrometry, dveřní a pohybové senzory, světla, klávesnice, poštovní senzory, naslouchací zařízení a podporované kamery, pokud je účet X-Sense poskytuje.

Potvrzené modelové řady zahrnují: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## Entity a akce
Integrace vytváří pouze entity pro data, která zařízení skutečně hlásí. Může jít o alarmy, ztlumení, baterii, signál, teplotu, vlhkost, CO, čitelné časové údaje, nastavení kamer, přepínače LED, tlačítka testu, ztlumení a požárního cvičení.

Správa zařízení, sdílení, odebrání, firmware, účty a platby zůstávají v aplikaci X-Sense. Pro diskuse použijte Discord nebo fórum Home Assistant.

## Živý náhled kamery a oznámení AI
Nejjednodušší je importovat přiložený blueprint tlačítkem níže, vybrat `Motion` nebo dostupné `AI Detection` a upravit akci oznámení.

Když událost Motion obsahuje data přehrávání X-Sense, integrace může nejprve uložit klip do cache a potom odeslat mobilní oznámení, které otevře odpovídající klip v X-Sense Recordings. Vypněte odkazy na nahrávky v blueprintu, pokud chcete jen jednoduché oznámení o pohybu bez čekání na video. Synchronizace médií nahrávek může udržovat nejnovější klipy připravené na pozadí a starší importované blueprinty kamer X-Sense se aktualizují automaticky.

[![Importovat blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FJarnsen%2Fha-xsense-component_test%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fxsense%2Fcamera_ai_notification.yaml)

Motion a AI Detection jsou jednorázové události, ne stavy zapnuto/vypnuto. Pro ruční automatizace použijte `event.received`; `event_type` používejte jen pro filtrování typů jako `person`, `pet`, `vehicle`, `package`, `other` nebo `ai_detection`.

Příklad automatizace:

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
## Příklady automatizací
```yaml
automation:
  - alias: "Upozornění X-Sense na teplotu"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "Teplota překročila 30 stupňů!"
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
        message: "Zjištěn únik vody!"
```

## Podpora
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

## Další podrobnosti

### Nastavení účtu

Doporučujeme používat pro Home Assistant samostatný účet X-Sense a v aplikaci X-Sense s ním sdílet pouze zařízení, která chcete v Home Assistantu zobrazit. Integrace nepáruje, neodebírá ani nepřesouvá zařízení mezi domácnostmi. Správa zařízení zůstává v oficiální aplikaci X-Sense.

### Aktualizace stavů

Integrace používá zprávy MQTT shadow pro rychlé změny stavu a opatrné periodické dotazování cloudu pro obnovení dat. Stav nahlášený stanicí se ukládá ke stanici a stav nahlášený podřízeným zařízením se ukládá k danému zařízení, aby se alarmy a čidla neblokovaly na starých hodnotách.

### Dostupné entity

Podle možností konkrétního modelu se zobrazují alarm kouře, CO, vody, teploty, pohybu a dveří, ztlumení alarmu, konec životnosti, nabíjení, stav připomenutí, stav světla a další diagnostické binární senzory. Senzory mohou zahrnovat baterii, signál RF nebo Wi-Fi, firmware, teplotu, vlhkost, koncentraci CO, špičku CO, hlasitost, prahové hodnoty, čitelné časové údaje, časové pásmo a další diagnostiku. Přepínače, výběry a číselné entity se vytvoří jen tehdy, když je zařízení opravdu podporuje.

### Kamery

### Řešení potíží

Pokud se některá entita nezobrazí, ověřte nejdříve v aplikaci X-Sense, že dané zařízení tuto hodnotu skutečně nabízí. Pokud stav zůstává zastaralý, zkuste integraci znovu načíst jen jako dočasný test a k hlášení přiložte diagnostiku a relevantní protokoly Home Assistantu.

### Chování zařízení

- Stanice a podřízená zařízení mohou hlásit různé sady hodnot. Integrace proto nepředpokládá, že každá stanice musí mít podřízené zařízení.
- Hodnoty časů se převádějí do čitelné podoby, pokud zařízení posílá čas ve formátu používaném aplikací X-Sense.
- Entita se nezobrazí, pokud zařízení danou funkci nehlásí. Tím se v Home Assistantu nevytváří zavádějící ovládání.

### Zátěž cloudu

Integrace se snaží být šetrná k API X-Sense. Rychlé změny se přebírají z MQTT zpráv a cloudové požadavky se používají jen tam, kde jsou potřeba pro přihlášení, načtení zařízení nebo obnovení stavu.

### Hlášení problému

Při hlášení chyby uveďte model zařízení, verzi integrace, zda se správná hodnota zobrazuje v aplikaci X-Sense, a přiložte diagnostiku integrace z Home Assistantu. Pomůže také krátký popis, zda se stav nikdy nezmění, nebo se změní až po opětovném načtení integrace.

## Kompletní referenční část

### Nastavení účtu podrobně
- Pro Home Assistant používejte samostatný účet X-Sense.
- Z hlavního účtu sdílejte pouze podporovaná zařízení.
- Párování, odebrání, sdílení a přesun zařízení zůstávají v aplikaci X-Sense.
- Pokud se aplikace a Home Assistant odhlašují, zkontrolujte, že nepoužívají stejný účet.

### Aktualizace a zatížení API
- Rychlé změny stavu přicházejí přes MQTT shadow zprávy.
- Cloudové dotazy slouží pro přihlášení, načtení zařízení a obnovení stavu.
- Periodické dotazování je pouze záloha, pokud MQTT zpráva chybí.

### Entity a akce
- Entity vznikají jen pro pole, která X-Sense opravdu hlásí.
- Diagnostické hodnoty jsou označeny jako diagnostika.
- Test, ztlumení, požární cvičení a probuzení kamery jsou dostupné jen pro podporované modely.

### Referenční část ke kamerám
- Podporované kamery mohou zobrazit entitu kamery, náhled, živý stream a diagnostiku.
- SD karta, platby, firmware a správa účtu zůstávají v aplikaci X-Sense.

### Kontrolní seznam pro řešení potíží
- Při hlášení chyby uveďte model, verzi integrace, diagnostiku a relevantní protokoly.

### Rozsah
- Integrace nepřidává, nemaže ani nepřesouvá zařízení mezi domácnostmi.

## Kontrolní seznam zařízení a entit

### Hlavní rodiny zařízení
- SBS50: základnová stanice a stav na úrovni stanice.
- XS01-WX: Wi-Fi kouřový hlásič včetně účtů bez podřízeného zařízení.
- XS01-M, XS03-WX, XS0B-MR: rodiny kouřových hlásičů.
- XC01-M, XC04-WX: rodiny detektorů CO.
- SC07-WX, XP0A-MR: kombinované rodiny kouře a CO.
- XH02-M: rodina tepelných hlásičů.
- SWS51: rodina detektorů úniku vody.
- STH51, STH0A, STH0B, STH0C: teplota a vlhkost.
- SDS0A: dveřní senzor.
- SMS0A: pohybový senzor.
- SSC0A, SSC0B: podporované kamery.

### Stavová pole
- Stav alarmu se zobrazí, když X-Sense hlásí pole alarmu.
- Stav ztlumení se zobrazí, když X-Sense hlásí pole ztlumení.
- Stav baterie se zobrazí, když zařízení hlásí baterii.
- Signál RF a Wi-Fi se zobrazí, když jej zařízení poskytne.
- Kompaktní časové hodnoty se převádějí na čitelné senzory Home Assistant.

### Ovládání a hlášení
- Přepínače se vytvářejí jen pro zapisovatelná nastavení hlášená X-Sense.
- Tlačítka se vytvářejí jen pro akce podporované aplikací.
- Ovládání kamer se vytváří jen tehdy, když jej API označí jako dostupné.
- Hlášení chyby má obsahovat přesný model, verzi integrace, diagnostiku, protokoly a informaci, zda se hodnota mění v aplikaci X-Sense.

### Provozní poznámky
- Po spuštění integrace ověřte, že jsou zařízení pojmenována stejně jako v aplikaci X-Sense.
- Pokud se alarm, ztlumení nebo LED nezmění okamžitě, počkejte na další MQTT zprávu nebo obnovu stavu.
- U stanic SBS50 kontrolujte stav stanice i jednotlivých podřízených zařízení.
- U modelu XS01-WX může být celý stav hlášen přímo na zařízení, i když účet nemá samostatné podřízené zařízení.
- U kamer závisí dostupné entity na tom, co cloud X-Sense vrátí pro konkrétní účet.
- Pokud se entita nevytvoří, nejprve porovnejte hodnoty s aplikací X-Sense a přiložte diagnostiku.
- Integrace má sledovat a ovládat podporované funkce, ne nahrazovat párování nebo správu zařízení v aplikaci.
