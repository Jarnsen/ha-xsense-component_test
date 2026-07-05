# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Áttekintés
Ez a Home Assistant integráció elérhetővé teszi az X-Sense eszközöket az okosotthonban. Theo Snel eredeti munkáján alapul, és HACS-en keresztül telepíthető.

Javasolt egy külön X-Sense fiókot létrehozni a Home Assistant számára, majd a fő fiókból csak a támogatott eszközöket megosztani vele.

## Kompatibilitás és HACS-frissítések
Ha még régi `v1.2.6.x` verziót használ, frissítsen `v1.3.14` vagy újabb verzióra, mielőtt a Home Assistant Core-t 2026.7 vagy újabb verzióra frissíti. A régi verziók `aiortc`-t igényeltek, amely nem kompatibilis a Home Assistant Python 3.14 futtatókörnyezetével. A jelenlegi `v1.3.x` verziók már nem igénylik az `aiortc`-t.

Ez az integráció egyéni HACS-tárolóként települ. Ha a frissítés nem jelenik meg azonnal, nyissa meg a HACS-t, válassza az X-Sense tárolót, futtassa az **Update information** műveletet, majd frissítse vagy töltse le újra az integrációt, és indítsa újra a Home Assistantot.

## Telepítés
A HACS-ben adja hozzá egyéni tárolóként a `https://github.com/Jarnsen/ha-xsense-component_test` címet, töltse le az integrációt, kövesse a HACS újraindítási utasítását, majd állítsa be a Home Assistant célú X-Sense fiókkal.


## Részletes beállítás képernyőképekkel

1. Hozz létre külön X-Sense-fiókot a Home Assistant számára, és a fő fiókból csak a támogatott eszközöket oszd meg vele.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

2. A HACS-ban add hozzá egyéni tárolóként: `https://github.com/Jarnsen/ha-xsense-component_test`.

![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

3. Töltsd le és telepítsd az integrációt, indítsd újra a Home Assistantot, majd állítsd be az új X-Sense-fiókkal.

![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

4. Sikeres beállítás után a megosztott eszközök megjelennek a Home Assistant eszközoldalán.

![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)

5. A párosítás, eltávolítás, firmware, fizetések, SD-kártyák és fiókkezelés az X-Sense alkalmazásban marad.

## Támogatott eszközök
Támogatottak a bázisállomások, füstérzékelők, CO-érzékelők, hőriasztók, vízszivárgás-érzékelők, higrométerek, ajtó- és mozgásérzékelők, lámpák, billentyűzetek, postaláda-érzékelők, figyelő eszközök és támogatott kamerák, ha az X-Sense fiók jelenti őket.

A megerősített modellcsaládok: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## Entitások és műveletek
Az integráció csak a ténylegesen jelentett mezőkhöz hoz létre entitásokat. Ilyen lehet a riasztás, némítás, akkumulátor, jelerősség, hőmérséklet, páratartalom, CO, olvasható időadatok, kamerabeállítások, LED kapcsolók, teszt, némítás és tűzriadó gomb.

Az eszközkezelés, megosztás, eltávolítás, firmware, fiók és fizetés továbbra is az X-Sense alkalmazásban marad. Kérdésekhez használja a Discordot vagy a Home Assistant fórumot.

## Kamera élőkép és AI értesítések
A legegyszerűbb a mellékelt blueprint importálása az alábbi gombbal, majd a `Motion` vagy elérhető `AI Detection` kiválasztása és az értesítési művelet módosítása, ha szükséges.

When a Motion event includes X-Sense playback metadata, the integration immediately tries to cache the clip. With recording links enabled, the default camera-event blueprint waits until cached media is ready, then sends a mobile notification that opens the matching X-Sense Recordings clip. Turn recording links off if you want a plain motion notification without waiting for video. Manual automation runs use the selected event entity's latest recording data. Recording media sync can keep recent clips ready in the background. The integration updates older imported X-Sense camera-event blueprints automatically when Home Assistant starts or during the periodic blueprint maintenance check.

[![Blueprint importálása](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FJarnsen%2Fha-xsense-component_test%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fxsense%2Fcamera_ai_notification.yaml)

A Motion és AI Detection egyszeri események, nem be/ki állapotok. Kézi automatizációkhoz használd az `event.received` triggert; `event_type` csak típusok szűréséhez kell, például `person`, `pet`, `vehicle`, `package`, `other` vagy `ai_detection`.

Példa automatizáció:

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
## Automatizálási példák
```yaml
automation:
  - alias: "X-Sense hőmérséklet-riasztás"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "A hőmérséklet meghaladta a 30 fokot!"
```

```yaml
automation:
  - alias: "Vízszivárgás-riasztás"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "Vízszivárgás észlelve!"
```

## Támogatás
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

## További részletek

### Fiókbeállítás

Ajánlott külön X-Sense-fiókot használni a Home Assistanthoz, és csak azokat a támogatott eszközöket megosztani vele, amelyeket a Home Assistantban szeretne látni. Az integráció nem párosít, nem távolít el és nem helyez át eszközöket otthonok között. Az ilyen eszközkezelés továbbra is a hivatalos X-Sense alkalmazásban történik.

### Állapotfrissítések

Az integráció MQTT shadow üzeneteket használ a gyors állapotváltozásokhoz, és óvatos, időszakos felhőlekérdezést az adatok frissítéséhez. Az állomás által jelentett állapot az állomáson, az aleszköz által jelentett állapot pedig az adott eszközön frissül, hogy a riasztások és érzékelők ne ragadjanak régi értéken.

### Elérhető entitások

Modelltől függően megjelenhet füst-, CO-, víz-, hőmérséklet-, mozgás- és ajtóriasztás, riasztásnémítás, élettartam vége, töltés, emlékeztető állapota, fényállapot és további diagnosztikai bináris érzékelők. Az érzékelők között lehet akkumulátor, RF- vagy Wi-Fi-jel, firmware, hőmérséklet, páratartalom, CO-szint, CO-csúcsérték, hangerő, küszöbértékek, olvasható időpontok, időzóna és egyéb diagnosztika. Kapcsolók, választók és számmezők csak akkor jönnek létre, ha az eszköz valóban támogatja őket.

### Kamera-referencia

### Hibaelhárítási ellenőrzőlista

Ha egy entitás hiányzik, először ellenőrizze az X-Sense alkalmazásban, hogy az adott érték valóban megjelenik-e az eszköznél. Ha az állapot elavult marad, csak ideiglenes tesztként töltse újra az integrációt, és a hibajelentéshez csatolja a diagnosztikát, valamint a releváns Home Assistant naplósorokat.

### Eszközviselkedés

- Az állomások és az aleszközök eltérő értékkészleteket jelenthetnek. Az integráció ezért nem feltételezi, hogy minden állomáshoz tartoznia kell aleszköznek.
- Az időértékek olvasható formára alakulnak, ha az eszköz az X-Sense alkalmazás által használt formátumban küldi őket.
- Entitás nem jön létre, ha az eszköz nem jelenti az adott funkciót. Ez megakadályozza a félrevezető vezérlők megjelenését a Home Assistantban.

### Felhőterhelés

Az integráció igyekszik kíméletesen használni az X-Sense API-t. A gyors változások MQTT üzenetekből érkeznek, a felhőhívások pedig csak bejelentkezéshez, eszközbetöltéshez vagy állapotfrissítéshez szükséges esetekben történnek.

### Hibajelentés

Hiba jelentésekor adja meg az eszköz modelljét, az integráció verzióját, hogy a helyes érték látható-e az X-Sense alkalmazásban, és csatolja a Home Assistant integrációdiagnosztikáját. Az is hasznos, ha röviden leírja, hogy az állapot soha nem változik-e, vagy csak az integráció újratöltése után frissül.

## Teljes referencia

### Fiókbeállítás részletesen
- A Home Assistant számára használj külön X-Sense-fiókot.
- A fő fiókból csak a támogatott eszközöket oszd meg.
- A párosítás, eltávolítás, megosztás és eszközáthelyezés az X-Sense alkalmazásban marad.
- Ha az alkalmazás és a Home Assistant kijelentkezteti egymást, valószínűleg ugyanazt a fiókot használják.

### Frissítések és API-terhelés
- A gyors állapotváltozások MQTT shadow üzeneteken keresztül érkeznek.
- A felhőkérések bejelentkezésre, eszközbetöltésre és állapotfrissítésre szolgálnak.
- Az időszakos lekérdezés tartalék, ha egy MQTT üzenet kimarad.

### Entitások és műveletek
- Entitás csak olyan mezőhöz jön létre, amelyet az X-Sense ténylegesen jelent.
- A diagnosztikai értékek diagnosztikaként jelennek meg.
- Teszt, némítás, tűzriadó-próba és kameraébresztés csak támogatott modelleknél érhető el.

### Kamerák
- A támogatott kamerák kameraentitást, bélyegképet, élő streamet és diagnosztikát adhatnak.
- Az SD-kártya, fizetések, firmware és fiókkezelés az X-Sense alkalmazásban marad.

### Hibaelhárítás
- Hibajelentéshez add meg a modellt, integrációs verziót, diagnosztikát és naplókat.

### Hatókör
- Az integráció nem ad hozzá, nem távolít el és nem helyez át eszközöket otthonok között.

## Eszköz- és entitás-ellenőrzőlista

### Fő eszközcsaládok
- SBS50: bázisállomás és állomásszintű állapot.
- XS01-WX: Wi-Fi füstjelző, külön alárendelt eszköz nélküli fiókokkal is.
- XS01-M, XS03-WX, XS0B-MR: füstjelző családok.
- XC01-M, XC04-WX: CO-jelző családok.
- SC07-WX, XP0A-MR: kombinált füst és CO családok.
- XH02-M: hőjelző család.
- SWS51: vízszivárgás-érzékelő család.
- STH51, STH0A, STH0B, STH0C: hőmérséklet és páratartalom.
- SDS0A: ajtóérzékelő.
- SMS0A: mozgásérzékelő.
- SSC0A, SSC0B: támogatott kamerák.

### Állapotmezők
- A riasztási állapot akkor jelenik meg, ha az X-Sense riasztási mezőt jelent.
- A némítási állapot akkor jelenik meg, ha az X-Sense némítási mezőt jelent.
- Az akkumulátor állapota akkor jelenik meg, ha az eszköz akkumulátoradatot jelent.
- Az RF és Wi-Fi jel akkor jelenik meg, ha az eszköz jelenti.
- A kompakt időértékek olvasható Home Assistant szenzorokká alakulnak.

### Vezérlők és jelentés
- Kapcsolók csak X-Sense által jelentett írható beállításokhoz jönnek létre.
- Gombok csak alkalmazás által támogatott műveletekhez jönnek létre.
- Kamera-vezérlők csak akkor jönnek létre, ha az API elérhetőnek jelöli őket.
- Hibajelentésben szerepeljen a pontos modell, integrációs verzió, diagnosztika, naplók és hogy az érték változik-e az X-Sense alkalmazásban.

### Üzemeltetési megjegyzések
- Beállítás után ellenőrizze, hogy az eszköznevek és helyiségek megegyeznek-e az X-Sense alkalmazásban láthatókkal.
- Ha a riasztás, a némítás vagy a LED állapota nem változik azonnal, várja meg a következő MQTT üzenetet vagy állapotfrissítést.
- SBS50 állomásoknál az állomás állapotát és az egyes alárendelt eszközöket is ellenőrizni kell.
- XS01-WX esetén a teljes állapot közvetlenül az eszközön jelenhet meg, külön alárendelt eszköz nélkül is.
- Kameráknál a létrehozott entitások attól függenek, milyen képességeket ad vissza az X-Sense felhő az adott fiókhoz.
- Ha egy entitás nem jön létre, először hasonlítsa össze az értéket az X-Sense alkalmazással, és mellékeljen diagnosztikát.
- Az integráció célja a támogatott funkciók megjelenítése és vezérlése, nem pedig a párosítás vagy az eszközkezelés kiváltása az alkalmazásban.
