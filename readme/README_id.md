# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Ringkasan
Integrasi Home Assistant ini memungkinkan perangkat X-Sense digunakan di sistem rumah pintar. Integrasi ini dibuat berdasarkan kode asli dari [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) dan diterbitkan dengan izin serta kerja samanya.

Sampai integrasi resmi Home Assistant tersedia, integrasi HACS ini akan terus diperbarui untuk menambah fitur dan memperbaiki masalah.

## Fitur
- Mengintegrasikan berbagai perangkat X-Sense ke Home Assistant.
- Mendukung otomatisasi berdasarkan data sensor X-Sense.
- Mendukung base stasiun, detektor asap, detektor karbon monoksida, alarm panas, detektor kebocoran air, termohigrometer, sensor pintu, sensor gerak, lampu, keypad, sensor kotak surat, dan perangkat perangkat pendengar saat tersedia di akun X-Sense.
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


## Penyiapan rinci dengan tangkapan layar

1. Buat akun X-Sense terpisah untuk Home Assistant dan bagikan hanya perangkat yang didukung dari akun utama.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

2. Tambahkan `https://github.com/Jarnsen/ha-xsense-component_test` sebagai repositori khusus di HACS.

![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

3. Unduh dan pasang integrasi, mulai ulang Home Assistant, lalu konfigurasikan dengan akun X-Sense baru.

![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

4. Setelah penyiapan berhasil, perangkat yang dibagikan akan muncul di halaman perangkat Home Assistant.

![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)

5. Pemasangan, penghapusan, firmware, pembayaran, kartu SD, dan manajemen akun tetap berada di aplikasi X-Sense.

## Perangkat yang didukung
Integrasi ini mendukung berbagai perangkat X-Sense. Entitas yang tersedia bergantung pada kolom data yang dilaporkan perangkat dan akun. Keluarga dan model yang dikonfirmasi meliputi:
- **Base stasiun (SBS50)**: Hub pusat untuk perangkat X-Sense.
- **Alarm panas (XH02-M)**: Mendeteksi suhu yang sangat tinggi.
- **Detektor karbon monoksida (XC01-M; XC04-WX)**: Mendeteksi konsentrasi CO berbahaya.
- **Detektor asap (XS01-M; XS01-WX; XS03-WX; XS0B-MR dan model RF/iR terkait)**: Deteksi asap dini.
- **Detektor gabungan CO dan asap (SC07-WX; XP0A-MR dan model XP/SC terkait)**: Mendeteksi CO dan asap.
- **Detektor kebocoran air (SWS51)**: Mendeteksi air di tempat yang tidak diinginkan.
- **Higrometer-termometer (STH51, STH0A, STH0B, STH0C)**: Memantau suhu dan kelembapan.
- **Sensor pintu (SDS0A)** dan **sensor gerak (SMS0A)**: Ditampilkan saat X-Sense menyediakan status.
- **Kamera (SSC0A, SSC0B)**: Menampilkan entitas kamera, gambar pratinjau, URL siaran langsung, diagnostik, dan pengaturan berbasis aplikasi Android saat didukung perangkat dan akun.
- **Perangkat lain yang terhubung ke stasiun**: Lampu, keypad, mailbox, perangkat pendengar, alarm driveway, perangkat penerima paket pintar, remote, dan data radon ditampilkan saat API melaporkan kolom yang didukung.

### Entitas dan aksi yang tersedia
Integrasi hanya membuat entitas Home Assistant untuk kolom yang benar-benar ada di cloud X-Sense, muatan MQTT shadow, atau API kamera yang selaras dengan aplikasi Android. Bergantung pada perangkat, ini dapat mencakup:

- Binary sensor untuk alarm, mute, end-of-life, AC-break, alarm air, alarm suhu, pengisian daya, gerakan, pintu, status armed, peringatan, pengingat, lampu, PIR, dan status keypad.
- Sensor baterai, sinyal RF, sinyal Wi-Fi, firmware, suhu, kelembapan, level CO, puncak CO, volume alarm, volume suara, volume chirp, volume pengingat, ambang peringatan, timer senyap, cap waktu yang mudah dibaca, zona waktu, dan data diagnostik lain.
- Sakelar untuk pengaturan yang dapat ditulis yang didukung X-Sense, seperti lampu LED, pengaktifan alarm, alarm berkelanjutan, nada kicau, pengingat, PIR, cahaya matahari/cahaya putih, mode tunggu, suara papan tombol, deteksi gerakan kamera, perekaman, penglihatan malam, audio, jeda pendinginan, lampu, dan kontrol bel pintu.
- Pilihan dan angka untuk pengaturan kamera yang didukung seperti bahasa, resolusi rekaman, codec, anti-flicker, sensitivitas gerakan, durasi video, volume, durasi alarm, jeda pendinginan, ambang malam, dan tombol dering bel pintu.
- Tombol test, mute, fire-drill, dan wake kamera untuk model perangkat yang menyediakan aksi tersebut di aplikasi X-Sense.

Beberapa entitas bersifat diagnostik atau konfigurasi dan dikelompokkan seperti itu di Home Assistant. Jika perangkat tidak melaporkan kolom tertentu, atau aplikasi X-Sense menandai fitur tidak didukung untuk perangkat/akun tersebut, entitas terkait tidak dibuat. Pengaitan perangkat, penghapusan, berbagi, akun, pembayaran, pembaruan firmware, format kartu SD, dan tindakan manajemen lain tetap dilakukan di aplikasi X-Sense.
____________________________________________________________

## Contoh Otomasi
Dengan integrasi ini, berbagai otomasi dapat dibuat. Berikut beberapa contoh:

### Contoh 1: Peringatan suhu
Ketika suhu dari termometer X-Sense terlalu tinggi, notifikasi dikirim:

```yaml
automation:
  - alias: "Peringatan Suhu X-Sense"
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
  - alias: "Alarm Kebocoran Air"
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

## Referensi lengkap

### Akun dan pemasangan
- Gunakan akun X-Sense terpisah untuk Home Assistant.
- Bagikan hanya perangkat yang didukung dari akun utama.
- Penambahan, penghapusan, berbagi, pembayaran, firmware, dan manajemen akun tetap di aplikasi X-Sense.
- Jika aplikasi dan Home Assistant saling keluar, kemungkinan keduanya memakai akun yang sama.

### Pembaruan dan penggunaan API
- Perubahan status cepat diterima melalui pesan MQTT shadow.
- Permintaan cloud digunakan untuk login, memuat perangkat, dan menyegarkan status.
- Polling berkala hanya menjadi cadangan jika pesan MQTT tidak diterima.
- Penemuan perangkat penuh tidak boleh diulang pada setiap pembaruan.

### Entitas, kamera, dan pemecahan masalah
- Entitas hanya dibuat jika X-Sense benar-benar melaporkan kolom tersebut.
- Nilai diagnostik dikelompokkan sebagai diagnostik di Home Assistant.
- Kamera yang didukung dapat menyediakan entitas kamera, gambar pratinjau, siaran langsung, status, dan pengaturan yang didukung.
- Jika jalur WebRTC tersedia di Home Assistant, integrasi dapat memakainya untuk tampilan langsung.
- Saat melaporkan masalah, sertakan model, versi integrasi, diagnostik, log, dan apakah nilai berubah di aplikasi.

## Daftar perangkat dan entitas

### Keluarga perangkat utama
- SBS50: stasiun dasar dan status tingkat stasiun.
- XS01-WX: alarm asap Wi-Fi, termasuk akun tanpa perangkat anak terpisah.
- XS01-M, XS03-WX, XS0B-MR: keluarga alarm asap.
- XC01-M, XC04-WX: keluarga alarm CO.
- SC07-WX, XP0A-MR: keluarga kombinasi asap dan CO.
- XH02-M: keluarga alarm panas.
- SWS51: keluarga detektor kebocoran air.
- STH51, STH0A, STH0B, STH0C: suhu dan kelembapan.
- SDS0A: sensor pintu.
- SMS0A: sensor gerak.
- SSC0A, SSC0B: kamera yang didukung.

### Kolom status
- Status alarm ditampilkan jika X-Sense melaporkan kolom alarm.
- Status mute ditampilkan jika X-Sense melaporkan kolom mute.
- Status baterai ditampilkan jika perangkat melaporkan data baterai.
- Nilai RF dan Wi-Fi ditampilkan jika dilaporkan perangkat.
- Stempel waktu ringkas X-Sense diubah menjadi sensor waktu yang mudah dibaca.

### Kontrol dan laporan
- Sakelar hanya dibuat untuk pengaturan tulis yang dilaporkan X-Sense.
- Tombol hanya dibuat untuk aksi yang didukung aplikasi.
- Kontrol kamera hanya dibuat ketika API menandainya tersedia.
- Laporan masalah perlu menyertakan model tepat, versi integrasi, diagnostik, log, dan apakah nilai berubah di aplikasi X-Sense.

____________________________________________________________

## Camera AI Notifications
Supported cameras expose AI detections as Home Assistant `event` entities. Use the camera device's `AI Detection` event entity in automations with the `event.received` trigger. Event entities are momentary notifications, so they do not stay `on` or `off` like binary sensors.

Available event types include `person`, `pet`, `vehicle`, `vehicle_enter`, `vehicle_out`, `vehicle_held_up`, `package`, `package_drop_off`, `package_pick_up`, `package_exist`, `other`, and `ai_detection`. The `ai_detection` event type is used when one camera notification contains more than one detected object.

Example automation:

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

For dashboards or conditions that need the most recent detection, use the `Last AI Detection` and related last-detection timestamp sensors. Those sensors are history values; the actual notification trigger is the `AI Detection` event entity.

____________________________________________________________
