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

## Video Panduan
Untuk panduan rinci tentang instalasi dan konfigurasi integrasi, Anda dapat menonton video berikut:

[![X-Sense Home Assistant Integration](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## Persiapan
- **Buat akun X-Sense kedua untuk Home Assistant**: Akun terpisah disarankan karena satu akun mungkin tidak stabil jika digunakan bersamaan di aplikasi dan Home Assistant.
- **Bagikan perangkat yang didukung dari akun utama ke akun Home Assistant**: Pengelolaan tetap dilakukan di akun utama, sementara Home Assistant memakai perangkat yang dibagikan.

## Instalasi melalui HACS
1. **Buka HACS di Home Assistant**:
   HACS adalah ekstensi penting untuk Home Assistant yang memudahkan pemasangan integrasi kustom.

2. **Buka custom repositories**:
   Masuk ke pengaturan HACS dan tambahkan repositori sebagai sumber kustom.

3. **Tambahkan repositori**:
   Masukkan URL repositori: `https://github.com/Jarnsen/ha-xsense-component_test`

4. **Unduh dan pasang integrasi**:
   Cari integrasi di HACS, unduh, lalu pasang. Setelah itu konfigurasi dilakukan dari antarmuka Home Assistant.

____________________________________________________________

## Konfigurasi
Setelah pemasangan, konfigurasi dasar diperlukan agar integrasi dapat digunakan:
- **Nama pengguna dan kata sandi**: Gunakan kredensial akun X-Sense baru yang dibuat untuk Home Assistant.
- **Ikhtisar perangkat**: Setelah konfigurasi berhasil, perangkat yang dibagikan akan tersedia di Home Assistant dan dapat digunakan untuk otomasi.

## Tampilan di Home Assistant
Setelah instalasi dan konfigurasi berhasil, integrasi akan terlihat di Home Assistant. Perangkat tersedia di dashboard dan dapat digunakan untuk otomasi, notifikasi, dan kebutuhan lain.

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

### Entity dan aksi yang tersedia
Integrasi hanya membuat entity Home Assistant untuk field yang benar-benar ada di cloud X-Sense, payload MQTT shadow, atau API kamera yang selaras dengan aplikasi Android. Bergantung pada perangkat, ini dapat mencakup:

- Binary sensor untuk alarm, mute, end-of-life, AC-break, alarm air, alarm suhu, pengisian daya, gerakan, pintu, status armed, peringatan, pengingat, lampu, PIR, dan status keypad.
- Sensor baterai, sinyal RF, sinyal Wi-Fi, firmware, suhu, kelembapan, level CO, puncak CO, volume alarm, volume suara, volume chirp, volume pengingat, ambang peringatan, timer mute, timestamp yang mudah dibaca, zona waktu, nomor seri, alamat MAC, dan data diagnostik lain.
- Switch untuk pengaturan tulis yang didukung X-Sense, seperti lampu LED, pengaktifan alarm, continued alarm, nada chirp, pengingat, PIR, sunshine/white light, await, suara keypad, deteksi gerakan kamera, perekaman, night vision, audio, cooldown, lampu, dan kontrol doorbell.
- Select dan number untuk pengaturan kamera yang didukung seperti bahasa, resolusi rekaman, codec, anti-flicker, sensitivitas gerakan, durasi video, volume, durasi alarm, cooldown, ambang malam, dan tombol dering doorbell.
- Tombol test, mute, fire-drill, dan wake camera untuk model perangkat yang menyediakan aksi tersebut di aplikasi X-Sense.

Beberapa entity bersifat diagnostik atau konfigurasi dan dikelompokkan seperti itu di Home Assistant. Jika perangkat tidak melaporkan field tertentu, atau aplikasi X-Sense menandai fitur tidak didukung untuk perangkat/akun tersebut, entity terkait tidak dibuat. Binding perangkat, penghapusan, berbagi, akun, pembayaran, pembaruan firmware, format kartu SD, dan tindakan manajemen lain tetap dilakukan di aplikasi X-Sense.
____________________________________________________________

## Contoh Otomasi
Dengan integrasi ini, berbagai otomasi dapat dibuat. Berikut beberapa contoh:

### Contoh 1: Peringatan suhu
Ketika suhu dari termometer X-Sense terlalu tinggi, notifikasi dikirim:

```yaml
automation:
  - alias: "Xsense Temperature Alert"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "Suhu melebihi 30 derajat!"
```

### Contoh 2: Alarm kebocoran air
Ketika detektor kebocoran air mendeteksi air, peringatan dipicu:

```yaml
automation:
  - alias: "Water Leak Alarm"
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
