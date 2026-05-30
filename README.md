<div align="right">
  <details>
    <summary>🌐 Language</summary>

| | | |
|---|---|---|
| [🇬🇧 English](readme/README_en.md) | [🇩🇪 Deutsch](readme/README_de.md) | [🇫🇷 Français](readme/README_fr.md) |
| [🇪🇸 Español](readme/README_es.md) | [🇮🇹 Italiano](readme/README_it.md) | [🇵🇱 Polski](readme/README_pl.md) |
| [🇳🇱 Nederlands](readme/README_nl.md) | [🇵🇹 Português](readme/README_pt.md) | [🇧🇷 Português (Brasil)](readme/README_pt-BR.md) |
| [🇨🇿 Čeština](readme/README_cs.md) | [🇸🇰 Slovenčina](readme/README_sk.md) | [🇭🇺 Magyar](readme/README_hu.md) |
| [🇷🇴 Română](readme/README_ro.md) | [🇸🇮 Slovenščina](readme/README_sl.md) | [🇭🇷 Hrvatski](readme/README_hr.md) |
| [🇩🇰 Dansk](readme/README_da.md) | [🇸🇪 Svenska](readme/README_sv.md) | [🇳🇴 Norsk](readme/README_no.md) |
| [🇫🇮 Suomi](readme/README_fi.md) | [🇪🇪 Eesti](readme/README_et.md) | [🇱🇻 Latviešu](readme/README_lv.md) |
| [🇱🇹 Lietuvių](readme/README_lt.md) | [🇹🇷 Türkçe](readme/README_tr.md) | [🇬🇷 Ελληνικά](readme/README_el.md) |
| [🇷🇺 Русский](readme/README_ru.md) | [🇺🇦 Українська](readme/README_uk.md) | [🇮🇱 עברית](readme/README_he.md) |
| [🇸🇦 العربية](readme/README_ar.md) | [🇮🇳 हिन्दी](readme/README_hi.md) | [🇨🇳 中文 (简体)](readme/README_zh-CN.md) |
| [🇹🇼 中文 (繁體)](readme/README_zh-TW.md) | [🇯🇵 日本語](readme/README_ja.md) | [🇰🇷 한국어](readme/README_ko.md) |
| [🇹🇭 ไทย](readme/README_th.md) | [🇻🇳 Tiếng Việt](readme/README_vi.md) | [🇮🇩 Bahasa Indonesia](readme/README_id.md) |
| [🇮🇷 فارسی](readme/README_fa.md) | [🇮🇳 অসমীয়া](readme/README_as.md) | |
  </details>
</div>

# ha-xsense-component_test 
 ![GitHub Release](https://img.shields.io/github/release/Jarnsen/ha-xsense-component_test.svg?style=plastic) ![GitHub issues](https://img.shields.io/github/issues/Jarnsen/ha-xsense-component_test.svg?style=plastic) ![GitHub Stars](https://img.shields.io/github/stars/Jarnsen/ha-xsense-component_test.svg?style=plastic) ![GitHub Last Commit](https://img.shields.io/github/last-commit/Jarnsen/ha-xsense-component_test.svg?style=plastic) ![Documentation](https://img.shields.io/badge/docs-excellent-brightgreen.svg?style=plastic) ![HACS Status](https://img.shields.io/badge/HACS-Default-blue.svg?style=plastic) ![Home Assistant](https://img.shields.io/badge/Home%20Assistant-%3E%3D%202025.3.0-brightgreen.svg?style=plastic) [![Discord](https://img.shields.io/discord/1118894710027731025.svg?style=plastic&logo=discord&label=Discord)](https://discord.com/invite/5phHHgGb3V) [![YouTube Channel](https://img.shields.io/youtube/channel/subscribers/UCXao3LZhkhYyGybSl3yCxwQ.svg?style=plastic&logo=youtube&label=Subscribers)](https://www.youtube.com/channel/UCXao3LZhkhYyGybSl3yCxwQ) [![YouTube Video](https://img.shields.io/badge/Watch%20on-YouTube-red.svg?style=plastic&logo=youtube)](https://www.youtube.com/watch?v=3CCKK-qX-YA)
---

<p align="center">
  <img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>


<p align="center">
  <img src="https://github.com/user-attachments/assets/fbe7e69b-9204-4de4-a245-e0e2bdbd7f73" alt="Image">
</p>


## Overview (English) / Überblick (Deutsch)

This repository contains the Home Assistant integration for X-Sense devices. This repository is available in multiple languages to help users worldwide understand and use the integration easily.

Dieses Repository enthält die Home Assistant-Integration für X-Sense-Geräte. Dieses Repository ist in mehreren Sprachen verfügbar, damit Nutzer weltweit die Integration einfach verstehen und nutzen können.

### Recent Improvements / Aktuelle Verbesserungen

- The integration now includes its X-Sense API client directly, removing the external `python-xsense` dependency.
- MQTT shadow updates and polling have been improved to reduce unnecessary cloud requests while keeping device state current.
- X-Sense camera support has been expanded using the Android app API behavior as a guide, including camera entities, thumbnails/live streams, readable status fields, and supported camera settings such as motion detection, recording, night vision, audio, cooldown, light, doorbell, wake, and codec controls.
- More X-Sense-reported entities are exposed, including additional smoke, CO, water, temperature, humidity, light, keypad, mailbox, motion, door, reminder, warning, and diagnostic fields when devices report them.
- Device actions such as test, mute, and fire drill are available for supported models, and supported device settings such as LED light, reminders, alarm, PIR, and related toggles are exposed as switches.
- X-Sense timestamp fields are shown as readable Home Assistant date/time sensors instead of raw compact values.

### Available Languages / Verfügbare Sprachen:

- [🇬🇧 English (en)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_en.md)
- [🇩🇪 German (Deutsch) (de)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_de.md)
- [🇫🇷 French (Français) (fr)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_fr.md)
- [🇪🇸 Spanish (Español) (es)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_es.md)
- [🇮🇹 Italian (Italiano) (it)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_it.md)
- [🇵🇱 Polish (Polski) (pl)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_pl.md)
- [🇳🇱 Dutch (Nederlands) (nl)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_nl.md)
- [🇵🇹 Portuguese (Português) (pt)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_pt.md)
- [🇧🇷 Brazilian Portuguese (Português Brasil) (pt-BR)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_pt-BR.md)
- [🇨🇿 Czech (Čeština) (cs)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_cs.md)
- [🇸🇰 Slovak (Slovenčina) (sk)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_sk.md)
- [🇭🇺 Hungarian (Magyar) (hu)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_hu.md)
- [🇷🇴 Romanian (Română) (ro)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_ro.md)
- [🇸🇮 Slovenian (Slovenščina) (sl)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_sl.md)
- [🇭🇷 Croatian (Hrvatski) (hr)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_hr.md)
- [🇩🇰 Danish (Dansk) (da)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_da.md)
- [🇸🇪 Swedish (Svenska) (sv)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_sv.md)
- [🇳🇴 Norwegian (Norsk) (no)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_no.md)
- [🇫🇮 Finnish (Suomi) (fi)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_fi.md)
- [🇪🇪 Estonian (Eesti) (et)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_et.md)
- [🇱🇻 Latvian (Latviešu) (lv)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_lv.md)
- [🇱🇹 Lithuanian (Lietuvių) (lt)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_lt.md)
- [🇹🇷 Turkish (Türkçe) (tr)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_tr.md)
- [🇬🇷 Greek (Ελληνικά) (el)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_el.md)
- [🇷🇺 Russian (Русский) (ru)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_ru.md)
- [🇺🇦 Ukrainian (Українська) (uk)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_uk.md)
- [🇮🇱 Hebrew (עברית) (he)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_he.md)
- [🇸🇦 Arabic (العربية) (ar)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_ar.md)
- [🇮🇳 Hindi (हिन्दी) (hi)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_hi.md)
- [🇨🇳 Simplified Chinese (中文 简体) (zh-CN)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_zh-CN.md)
- [🇹🇼 Traditional Chinese (中文 繁體) (zh-TW)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_zh-TW.md)
- [🇯🇵 Japanese (日本語) (ja)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_ja.md)
- [🇰🇷 Korean (한국어) (ko)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_ko.md)
- [🇹🇭 Thai (ไทย) (th)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_th.md)
- [🇻🇳 Vietnamese (Tiếng Việt) (vi)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_vi.md)
- [🇮🇩 Indonesian (Bahasa Indonesia) (id)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_id.md)
- [🇮🇷 Persian (فارسی) (fa)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_fa.md)
- [🇮🇳 Assamese (অসমীয়া) (as)](https://github.com/Jarnsen/ha-xsense-component_test/blob/main/readme/README_as.md)

If a language is missing, please let us know, and we will do our best to add it.

Falls eine Sprache fehlt, lassen Sie es uns wissen, und wir bemühen uns, diese hinzuzufügen.
