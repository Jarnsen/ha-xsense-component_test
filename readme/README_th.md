# ha-xsense-component_test

<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## ภาพรวม
อินทิเกรชันนี้ช่วยให้ใช้อุปกรณ์ X-Sense กับ Home Assistant ได้ในระบบสมาร์ตโฮม พัฒนาจากโค้ดเดิมของ [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) และเผยแพร่โดยได้รับอนุญาตและความร่วมมือจากเขา

ก่อนที่อินทิเกรชันอย่างเป็นทางการของ Home Assistant จะพร้อมใช้งาน อินทิเกรชัน HACS นี้จะได้รับการอัปเดตเพื่อเพิ่มความสามารถและแก้ไขปัญหาอย่างต่อเนื่อง

## คุณสมบัติ
- รวมอุปกรณ์ X-Sense หลายประเภทเข้ากับ Home Assistant
- รองรับการทำงานอัตโนมัติจากข้อมูลเซนเซอร์ X-Sense
- รองรับสถานีฐาน เครื่องตรวจจับควัน เครื่องตรวจจับคาร์บอนมอนอกไซด์ เครื่องตรวจจับความร้อน เซนเซอร์น้ำรั่ว เครื่องวัดอุณหภูมิและความชื้น เซนเซอร์ประตู เซนเซอร์ตรวจจับการเคลื่อนไหว ไฟ คีย์แพด เซนเซอร์กล่องจดหมาย และอุปกรณ์ listener เมื่อมีข้อมูลในบัญชี X-Sense
- อัปเดตแบบเรียลไทม์ผ่าน X-Sense MQTT shadow พร้อมการดึงข้อมูลจากคลาวด์เป็นระยะเป็นแผนสำรอง
- ติดตั้งผ่าน HACS ได้ง่าย

## ข้อกำหนด
- เซิร์ฟเวอร์ Home Assistant ที่ใช้งานได้
- บัญชี X-Sense ที่มีอุปกรณ์ที่รองรับ
- ติดตั้ง HACS ใน Home Assistant แล้ว

## วิดีโอแนะนำ
สำหรับคำแนะนำแบบละเอียดเกี่ยวกับการติดตั้งและตั้งค่า integration สามารถดูวิดีโอนี้ได้:

[![X-Sense Home Assistant Integration](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## การเตรียมตัว
- **สร้างบัญชี X-Sense ที่สองสำหรับ Home Assistant**: แนะนำให้ใช้บัญชีแยก เพราะบัญชีเดียวกันอาจไม่สามารถล็อกอินในแอปและ Home Assistant ได้พร้อมกันอย่างเสถียร
- **แชร์อุปกรณ์ที่รองรับจากบัญชีหลักไปยังบัญชี Home Assistant**: ใช้บัญชีหลักสำหรับจัดการอุปกรณ์ และแชร์เฉพาะอุปกรณ์ที่ต้องการใช้งานกับ Home Assistant

## ติดตั้งผ่าน HACS
1. **เปิด HACS ใน Home Assistant**:
   HACS เป็นส่วนขยายสำคัญที่ช่วยติดตั้ง custom integration ได้ง่าย

2. **ไปที่ custom repositories**:
   ในหน้า settings ของ HACS ให้เพิ่ม repository นี้เป็น custom source

3. **เพิ่ม repository**:
   ใส่ URL: `https://github.com/Jarnsen/ha-xsense-component_test`

4. **ดาวน์โหลดและติดตั้ง integration**:
   ค้นหา integration ใน HACS ดาวน์โหลดและติดตั้ง จากนั้นตั้งค่าผ่านหน้า Home Assistant

____________________________________________________________

## การตั้งค่า
หลังติดตั้งแล้วต้องตั้งค่าพื้นฐานเพื่อให้ integration ทำงานถูกต้อง:
- **ชื่อผู้ใช้และรหัสผ่าน**: ใช้ข้อมูลบัญชี X-Sense ใหม่ที่สร้างไว้สำหรับ Home Assistant
- **ภาพรวมอุปกรณ์**: หลังตั้งค่าสำเร็จ อุปกรณ์ที่แชร์ไว้จะพร้อมใช้งานใน Home Assistant และใช้กับ automation ได้

## มุมมองใน Home Assistant
เมื่อติดตั้งและตั้งค่าสำเร็จ integration จะปรากฏใน Home Assistant อุปกรณ์จะอยู่บน dashboard และใช้กับ automation, notification และงานอื่นได้

## อุปกรณ์ที่รองรับ
อินทิเกรชันนี้รองรับอุปกรณ์ X-Sense หลายประเภท เอนทิตีที่มีขึ้นอยู่กับฟิลด์ข้อมูลที่อุปกรณ์และบัญชีรายงาน รุ่นและกลุ่มที่ยืนยันแล้วได้แก่:
- **สถานีฐาน (SBS50)**: ฮับกลางสำหรับอุปกรณ์ X-Sense.
- **สัญญาณเตือนความร้อน (XH02-M)**: ตรวจจับอุณหภูมิสูงผิดปกติ.
- **เครื่องตรวจจับคาร์บอนมอนอกไซด์ (XC01-M; XC04-WX)**: ตรวจจับระดับ CO ที่เป็นอันตราย.
- **เครื่องตรวจจับควัน (XS01-M; XS01-WX; XS03-WX; XS0B-MR และรุ่น RF/iR ที่เกี่ยวข้อง)**: ตรวจจับควันตั้งแต่เนิ่นๆ.
- **เครื่องตรวจจับ CO และควันแบบรวม (SC07-WX; XP0A-MR และรุ่น XP/SC ที่เกี่ยวข้อง)**: ตรวจจับ CO และควัน.
- **เครื่องตรวจจับน้ำรั่ว (SWS51)**: ตรวจจับน้ำในตำแหน่งที่ไม่ต้องการ.
- **ไฮโกรมิเตอร์-เทอร์โมมิเตอร์ (STH51, STH0A, STH0B, STH0C)**: ตรวจวัดอุณหภูมิและความชื้น.
- **เซ็นเซอร์ประตู (SDS0A)** และ **เซ็นเซอร์การเคลื่อนไหว (SMS0A)**: แสดงเมื่อ X-Sense รายงานสถานะ.
- **กล้อง (SSC0A, SSC0B)**: แสดงเอนทิตีกล้อง ภาพย่อ URL สตรีมสด การวินิจฉัย และการตั้งค่าตามแอป Android เมื่ออุปกรณ์และบัญชีรองรับ.
- **อุปกรณ์อื่นที่เชื่อมกับสถานี**: ไฟ แป้นกด กล่องจดหมาย listener สัญญาณทางเข้า smart drop รีโมต และข้อมูลเรดอนจะแสดงเมื่อ API รายงานฟิลด์ที่รองรับ.

### เอนทิตีและคำสั่งที่มี
Integration จะสร้าง Home Assistant entity เฉพาะ field ที่มีอยู่จริงใน X-Sense cloud, MQTT shadow payload หรือ camera API ที่สอดคล้องกับแอป Android เท่านั้น แล้วแต่รุ่นอุปกรณ์ อาจรวมถึง:

- Binary sensor สำหรับ alarm, mute, end-of-life, AC-break, water alarm, temperature alarm, charging, motion, door, armed, warning, reminder, light, PIR และสถานะ keypad
- Sensor สำหรับ battery, RF signal, Wi-Fi signal, firmware, temperature, humidity, CO level, CO peak, alarm volume, voice volume, chirp volume, reminder volume, warning threshold, mute timer, timestamp ที่อ่านได้, timezone, serial number, MAC address และข้อมูล diagnostic อื่น
- Switch สำหรับ setting ที่ X-Sense รายงานว่าสามารถเขียนค่าได้ เช่น LED light, alarm enablement, continued alarm, chirp tone, reminder, PIR, sunshine/white light, await, keypad sound, camera motion detection, recording, night vision, audio, cooldown, light และ doorbell controls
- Select และ number สำหรับ camera setting ที่รองรับ เช่น language, recording resolution, codec, anti-flicker rate, motion sensitivity, video length, volume, alarm duration, cooldown, night threshold และ doorbell ring key
- ปุ่ม test, mute, fire-drill และ wake camera สำหรับรุ่นที่แอป X-Sense มี action นั้นให้ใช้

บาง entity เป็น diagnostic หรือ configuration และจะถูกจัดกลุ่มแบบนั้นใน Home Assistant หากอุปกรณ์ไม่รายงาน field ใด หรือแอป X-Sense ระบุว่า feature นั้นไม่รองรับสำหรับอุปกรณ์/บัญชีนี้ entity ที่เกี่ยวข้องจะไม่ถูกสร้าง การผูกอุปกรณ์ ลบ แชร์ บัญชี การชำระเงิน อัปเดต firmware ฟอร์แมต SD card และงานจัดการอื่นยังอยู่ในแอป X-Sense

____________________________________________________________

## ตัวอย่าง Automation
ด้วย integration นี้สามารถสร้าง automation ได้หลายแบบ ตัวอย่างเช่น:

### ตัวอย่าง 1: แจ้งเตือนอุณหภูมิ
เมื่ออุณหภูมิจากเทอร์โมมิเตอร์ X-Sense สูงเกินไป จะส่ง notification:

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
        message: "อุณหภูมิสูงกว่า 30 องศา!"
```

### ตัวอย่าง 2: Alarm น้ำรั่ว
เมื่อตัวตรวจจับน้ำรั่วตรวจพบน้ำ จะส่งการแจ้งเตือน:

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
        message: "ตรวจพบน้ำรั่ว!"
```

## ต้องการความช่วยเหลือ
หากคุณมีอุปกรณ์ X-Sense ที่ยังไม่ได้ทดสอบ โปรดแจ้งผลการใช้งานผ่าน GitHub, Discord หรือฟอรัม Home Assistant
