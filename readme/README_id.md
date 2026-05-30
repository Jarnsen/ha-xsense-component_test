# ha-xsense-component_test

<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Ringkasan
Integrasi Home Assistant ini memungkinkan perangkat X-Sense digunakan di sistem rumah pintar. Integrasi ini dibuat berdasarkan kode asli dari [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) dan diterbitkan dengan izin serta kerja samanya.

Sampai integrasi resmi Home Assistant tersedia, integrasi HACS ini akan terus diperbarui untuk menambah fitur dan memperbaiki masalah.

## Fitur
- Mengintegrasikan berbagai perangkat X-Sense ke Home Assistant.
- Mendukung otomatisasi berdasarkan data sensor X-Sense.
- Mendukung base station, detektor asap, detektor karbon monoksida, alarm panas, detektor kebocoran air, termohigrometer, sensor pintu, sensor gerak, lampu, keypad, sensor kotak surat, dan perangkat listener saat tersedia di akun X-Sense.
- Pembaruan real-time melalui X-Sense MQTT shadow, dengan polling cloud berkala sebagai cadangan.
- Instalasi mudah melalui HACS.

## Persyaratan
- Server Home Assistant yang berfungsi.
- Akun X-Sense dengan perangkat yang didukung.
- HACS harus terpasang di Home Assistant.

## Persiapan
- **Buat akun X-Sense kedua untuk Home Assistant**: Akun terpisah disarankan karena satu akun mungkin tidak stabil jika digunakan bersamaan di aplikasi dan Home Assistant.
- **Bagikan perangkat yang didukung dari akun utama ke akun Home Assistant**: Pengelolaan tetap dilakukan di akun utama, sementara Home Assistant memakai perangkat yang dibagikan.

## Instalasi dan konfigurasi
1. Buka HACS di Home Assistant.
2. Tambahkan `https://github.com/Jarnsen/ha-xsense-component_test` sebagai custom repository.
3. Unduh dan pasang integrasi.
4. Konfigurasikan dengan nama pengguna dan kata sandi X-Sense di halaman Integrations Home Assistant.

## Perangkat yang didukung
Entity yang dibuat bergantung pada field yang dilaporkan oleh X-Sense cloud atau MQTT shadow. Perangkat umum mencakup SBS50 base station, perangkat asap dan CO seri XS/SC/XP/XC, alarm panas XH, detektor air SWS, termohigrometer STH, sensor pintu SDS, sensor gerak SMS, lampu, keypad, kotak surat, driveway alarm, dan perangkat lain yang melaporkan field yang didukung.

## Entity dan aksi
- Binary sensor untuk alarm, mute, end-of-life, AC break, water alarm, temperature alarm, charging, motion, door, armed, reminder, light, dan diagnostics.
- Sensor untuk battery, RF signal, Wi-Fi signal, firmware, temperature, humidity, CO, volume, timestamp yang mudah dibaca, serial number, MAC address, dan diagnostics lain.
- Switch untuk pengaturan yang dapat ditulis seperti LED light, alarm, reminders, PIR, sunshine, await, dan keypad sound jika didukung perangkat.
- Tombol test, mute, dan fire drill untuk model yang didukung.

## Contoh Automation
```yaml
automation:
  - alias: "X-Sense Water Leak Alarm"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "Kebocoran air terdeteksi!"
```

## Kami membutuhkan bantuan
Jika Anda memiliki perangkat X-Sense yang belum diuji, silakan kirim masukan melalui GitHub, Discord, atau forum Home Assistant.
