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

## การเตรียมตัว
- **สร้างบัญชี X-Sense ที่สองสำหรับ Home Assistant**: แนะนำให้ใช้บัญชีแยก เพราะบัญชีเดียวกันอาจไม่สามารถล็อกอินในแอปและ Home Assistant ได้พร้อมกันอย่างเสถียร
- **แชร์อุปกรณ์ที่รองรับจากบัญชีหลักไปยังบัญชี Home Assistant**: ใช้บัญชีหลักสำหรับจัดการอุปกรณ์ และแชร์เฉพาะอุปกรณ์ที่ต้องการใช้งานกับ Home Assistant

## การติดตั้งและตั้งค่า
1. เปิด HACS ใน Home Assistant
2. เพิ่ม `https://github.com/Jarnsen/ha-xsense-component_test` เป็น custom repository
3. ดาวน์โหลดและติดตั้งอินทิเกรชัน
4. ตั้งค่าด้วยชื่อผู้ใช้และรหัสผ่าน X-Sense ในหน้า Integrations ของ Home Assistant

## อุปกรณ์ที่รองรับ
เอนทิตีที่สร้างขึ้นขึ้นอยู่กับฟิลด์ที่ X-Sense cloud หรือ MQTT shadow รายงาน อุปกรณ์ที่พบได้บ่อยได้แก่ SBS50 base station, อุปกรณ์ควันและคาร์บอนมอนอกไซด์ตระกูล XS/SC/XP/XC, XH heat alarm, SWS water leak detector, STH thermo-hygrometer, SDS door sensor, SMS motion sensor, ไฟ, คีย์แพด, กล่องจดหมาย, driveway alarm และอุปกรณ์อื่นที่รายงานฟิลด์ที่รองรับ

## เอนทิตีและคำสั่ง
- Binary sensor สำหรับ alarm, mute, end-of-life, AC break, water alarm, temperature alarm, charging, motion, door, armed, reminder, light และ diagnostics
- Sensor สำหรับ battery, RF signal, Wi-Fi signal, firmware, temperature, humidity, CO, volume, timestamp ที่อ่านง่าย, serial number, MAC address และ diagnostics อื่น ๆ
- Switch สำหรับการตั้งค่าที่อุปกรณ์รองรับ เช่น LED light, alarm, reminders, PIR, sunshine, await และ keypad sound
- ปุ่ม test, mute และ fire drill สำหรับรุ่นที่รองรับ

## ตัวอย่าง Automation
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
        message: "ตรวจพบน้ำรั่ว!"
```

## ต้องการความช่วยเหลือ
หากคุณมีอุปกรณ์ X-Sense ที่ยังไม่ได้ทดสอบ โปรดแจ้งผลการใช้งานผ่าน GitHub, Discord หรือฟอรัม Home Assistant
