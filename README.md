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
- X-Sense camera support now includes native Home Assistant WebRTC live video and audio, camera entities, thumbnails, readable status fields, and regular motion event reporting when reported by the camera.
- Supported cameras expose Motion and AI Detection updates through Home Assistant event entities, with a simple automation blueprint available in the language documentation. Supported camera setup and tuning controls are exposed in Home Assistant when the X-Sense app reports that the feature and account support it.
- More X-Sense-reported entities are exposed, including additional smoke, CO, water, temperature, humidity, light, keypad, mailbox, motion, door, reminder, warning, and diagnostic fields when devices report them.
- Device actions such as test, mute, and fire drill are available for supported models, and supported settings such as LED light, reminders, alarm, PIR, related toggles, and alarm, voice, chirp, and reminder volume levels are exposed as Home Assistant controls.
- X-Sense timestamp fields are shown as readable Home Assistant date/time sensors instead of raw compact values.

### Available Languages / Verfügbare Sprachen:

| | | |
|---|---|---|
| <img src="https://flagcdn.com/16x12/gb.png" width="16" height="12" alt=""> [English](readme/README_en.md) | <img src="https://flagcdn.com/16x12/de.png" width="16" height="12" alt=""> [Deutsch](readme/README_de.md) | <img src="https://flagcdn.com/16x12/fr.png" width="16" height="12" alt=""> [Français](readme/README_fr.md) |
| <img src="https://flagcdn.com/16x12/es.png" width="16" height="12" alt=""> [Español](readme/README_es.md) | <img src="https://flagcdn.com/16x12/it.png" width="16" height="12" alt=""> [Italiano](readme/README_it.md) | <img src="https://flagcdn.com/16x12/pl.png" width="16" height="12" alt=""> [Polski](readme/README_pl.md) |
| <img src="https://flagcdn.com/16x12/nl.png" width="16" height="12" alt=""> [Nederlands](readme/README_nl.md) | <img src="https://flagcdn.com/16x12/pt.png" width="16" height="12" alt=""> [Português](readme/README_pt.md) | <img src="https://flagcdn.com/16x12/br.png" width="16" height="12" alt=""> [Português (Brasil)](readme/README_pt-BR.md) |
| <img src="https://flagcdn.com/16x12/cz.png" width="16" height="12" alt=""> [Čeština](readme/README_cs.md) | <img src="https://flagcdn.com/16x12/sk.png" width="16" height="12" alt=""> [Slovenčina](readme/README_sk.md) | <img src="https://flagcdn.com/16x12/hu.png" width="16" height="12" alt=""> [Magyar](readme/README_hu.md) |
| <img src="https://flagcdn.com/16x12/ro.png" width="16" height="12" alt=""> [Română](readme/README_ro.md) | <img src="https://flagcdn.com/16x12/si.png" width="16" height="12" alt=""> [Slovenščina](readme/README_sl.md) | <img src="https://flagcdn.com/16x12/hr.png" width="16" height="12" alt=""> [Hrvatski](readme/README_hr.md) |
| <img src="https://flagcdn.com/16x12/dk.png" width="16" height="12" alt=""> [Dansk](readme/README_da.md) | <img src="https://flagcdn.com/16x12/se.png" width="16" height="12" alt=""> [Svenska](readme/README_sv.md) | <img src="https://flagcdn.com/16x12/no.png" width="16" height="12" alt=""> [Norsk](readme/README_no.md) |
| <img src="https://flagcdn.com/16x12/fi.png" width="16" height="12" alt=""> [Suomi](readme/README_fi.md) | <img src="https://flagcdn.com/16x12/ee.png" width="16" height="12" alt=""> [Eesti](readme/README_et.md) | <img src="https://flagcdn.com/16x12/lv.png" width="16" height="12" alt=""> [Latviešu](readme/README_lv.md) |
| <img src="https://flagcdn.com/16x12/lt.png" width="16" height="12" alt=""> [Lietuvių](readme/README_lt.md) | <img src="https://flagcdn.com/16x12/tr.png" width="16" height="12" alt=""> [Türkçe](readme/README_tr.md) | <img src="https://flagcdn.com/16x12/gr.png" width="16" height="12" alt=""> [Ελληνικά](readme/README_el.md) |
| <img src="https://flagcdn.com/16x12/ru.png" width="16" height="12" alt=""> [Русский](readme/README_ru.md) | <img src="https://flagcdn.com/16x12/ua.png" width="16" height="12" alt=""> [Українська](readme/README_uk.md) | <img src="https://flagcdn.com/16x12/il.png" width="16" height="12" alt=""> [עברית](readme/README_he.md) |
| <img src="https://flagcdn.com/16x12/sa.png" width="16" height="12" alt=""> [العربية](readme/README_ar.md) | <img src="https://flagcdn.com/16x12/in.png" width="16" height="12" alt=""> [हिन्दी](readme/README_hi.md) | <img src="https://flagcdn.com/16x12/cn.png" width="16" height="12" alt=""> [简体中文](readme/README_zh-CN.md) |
| <img src="https://flagcdn.com/16x12/tw.png" width="16" height="12" alt=""> [繁體中文](readme/README_zh-TW.md) | <img src="https://flagcdn.com/16x12/jp.png" width="16" height="12" alt=""> [日本語](readme/README_ja.md) | <img src="https://flagcdn.com/16x12/kr.png" width="16" height="12" alt=""> [한국어](readme/README_ko.md) |
| <img src="https://flagcdn.com/16x12/th.png" width="16" height="12" alt=""> [ไทย](readme/README_th.md) | <img src="https://flagcdn.com/16x12/vn.png" width="16" height="12" alt=""> [Tiếng Việt](readme/README_vi.md) | <img src="https://flagcdn.com/16x12/id.png" width="16" height="12" alt=""> [Bahasa Indonesia](readme/README_id.md) |
| <img src="https://flagcdn.com/16x12/ir.png" width="16" height="12" alt=""> [فارسی](readme/README_fa.md) | <img src="https://flagcdn.com/16x12/in.png" width="16" height="12" alt=""> [অসমীয়া](readme/README_as.md) | |

If a language is missing, please let us know, and we will do our best to add it.

Falls eine Sprache fehlt, lassen Sie es uns wissen, und wir bemühen uns, diese hinzuzufügen.

### Release Notes / Versionshinweise

[Changelog](CHANGELOG.md) - linked release notes for every published version.
