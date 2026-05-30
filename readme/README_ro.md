# ha-xsense-component_test

## Prezentare generală
Această integrare Home Assistant face dispozitivele X-Sense disponibile în casa inteligentă. Se bazează pe lucrarea originală a lui Theo Snel și se instalează prin HACS.

Recomandăm crearea unui cont X-Sense separat pentru Home Assistant și partajarea din contul principal doar a dispozitivelor acceptate.

## Instalare
În HACS, adăugați depozitul personalizat `https://github.com/Jarnsen/ha-xsense-component_test`, descărcați integrarea, urmați instrucțiunile HACS pentru repornire și configurați-o cu contul X-Sense dedicat Home Assistant.

## Dispozitive acceptate
Sunt acceptate stații de bază, detectoare de fum, detectoare CO, alarme de căldură, detectoare de scurgeri de apă, higrometre, senzori de ușă și mișcare, lumini, tastaturi, senzori de cutie poștală, dispozitive de ascultare și camere acceptate atunci când contul X-Sense le raportează.

Familiile de modele confirmate includ: SBS50, XH02-M, XC01-M, XC04-WX, XS01-M, XS01-WX, XS03-WX, XS0B-MR, SC07-WX, XP0A-MR, SWS51, STH51, STH0A, STH0B, STH0C, SDS0A, SMS0A, SSC0A, SSC0B.

## Entități și acțiuni
Integrarea creează entități doar pentru datele raportate efectiv de dispozitiv. Acestea pot include alarme, silențiere, baterie, semnal, temperatură, umiditate, CO, câmpuri de timp lizibile, setări ale camerei, comutatoare LED și butoane pentru test, silențiere și exercițiu de incendiu.

Administrarea dispozitivelor, partajarea, eliminarea, firmware-ul, conturile și plățile rămân în aplicația X-Sense.

## Suport
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)
