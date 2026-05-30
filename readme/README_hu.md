# ha-xsense-component_test

## Áttekintés
Ez a Home Assistant integráció elérhetővé teszi az X-Sense eszközöket az okosotthonban. Theo Snel eredeti munkáján alapul, és HACS-en keresztül telepíthető.

Javasolt egy külön X-Sense fiókot létrehozni a Home Assistant számára, majd a fő fiókból csak a támogatott eszközöket megosztani vele.

## Telepítés
A HACS-ben adja hozzá egyéni tárolóként a `https://github.com/Jarnsen/ha-xsense-component_test` címet, töltse le az integrációt, kövesse a HACS újraindítási utasítását, majd állítsa be a Home Assistant célú X-Sense fiókkal.

## Támogatott eszközök
Támogatottak a bázisállomások, füstérzékelők, CO-érzékelők, hőriasztók, vízszivárgás-érzékelők, higrométerek, ajtó- és mozgásérzékelők, lámpák, billentyűzetek, postaláda-érzékelők, figyelő eszközök és támogatott kamerák, ha az X-Sense fiók jelenti őket.

A megerősített modellcsaládok: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## Entitások és műveletek
Az integráció csak a ténylegesen jelentett mezőkhöz hoz létre entitásokat. Ilyen lehet a riasztás, némítás, akkumulátor, jelerősség, hőmérséklet, páratartalom, CO, olvasható időadatok, kamerabeállítások, LED kapcsolók, teszt, némítás és tűzriadó gomb.

Az eszközkezelés, megosztás, eltávolítás, firmware, fiókok és fizetés továbbra is az X-Sense alkalmazásban marad.

## Támogatás
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)
