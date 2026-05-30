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
Integrasi ini mendukung berbagai perangkat X-Sense. Entity yang tersedia bergantung pada field data yang dilaporkan perangkat dan akun. Keluarga dan model yang dikonfirmasi meliputi:
- **Base station (SBS50)**: Hub pusat untuk perangkat X-Sense.
- **Alarm panas (XH02-M)**: Mendeteksi suhu yang sangat tinggi.
- **Detektor karbon monoksida (XC01-M; XC04-WX)**: Mendeteksi konsentrasi CO berbahaya.
- **Detektor asap (XS01-M; XS01-WX; XS03-WX; XS0B-MR dan model RF/iR terkait)**: Deteksi asap dini.
- **Detektor gabungan CO dan asap (SC07-WX; XP0A-MR dan model XP/SC terkait)**: Mendeteksi CO dan asap.
- **Detektor kebocoran air (SWS51)**: Mendeteksi air di tempat yang tidak diinginkan.
- **Higrometer-termometer (STH51, STH0A, STH0B, STH0C)**: Memantau suhu dan kelembapan.
- **Sensor pintu (SDS0A)** dan **sensor gerak (SMS0A)**: Ditampilkan saat X-Sense menyediakan status.
- **Kamera (SSC0A, SSC0B)**: Menampilkan entity kamera, thumbnail, URL live stream, diagnostik, dan pengaturan berbasis aplikasi Android saat didukung perangkat dan akun.
- **Perangkat lain yang terhubung ke station**: Lampu, keypad, mailbox, listener, alarm driveway, smart drop, remote, dan data radon ditampilkan saat API melaporkan field yang didukung.

## Entity dan aksi
Integrasi hanya membuat entity untuk field yang ada di cloud X-Sense, MQTT shadow, atau API kamera yang didukung aplikasi. Ini dapat mencakup binary sensor, sensor diagnostik, switch, select, number, dan tombol seperti test, mute, fire drill, serta wake camera.

Jika field tidak dilaporkan atau aplikasi X-Sense menandai fitur tidak didukung untuk perangkat/akun tersebut, entity tidak dibuat. Bind, hapus, bagikan, akun, pembayaran, firmware, format SD card, dan tindakan manajemen lain tetap berada di aplikasi X-Sense.

____________________________________________________________

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
