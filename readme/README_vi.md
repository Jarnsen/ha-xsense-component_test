# ha-xsense-component_test

<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Tổng quan
Tích hợp Home Assistant này cho phép sử dụng thiết bị X-Sense trong hệ thống nhà thông minh. Dự án dựa trên mã gốc của [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) và được phát hành với sự cho phép cùng hợp tác của ông.

Cho đến khi có tích hợp Home Assistant chính thức, tích hợp HACS này sẽ tiếp tục được cập nhật để thêm tính năng và sửa lỗi.

## Tính năng
- Tích hợp nhiều thiết bị X-Sense vào Home Assistant.
- Hỗ trợ tự động hóa dựa trên dữ liệu cảm biến X-Sense.
- Hỗ trợ trạm gốc, đầu báo khói, đầu báo CO, báo nhiệt, cảm biến rò rỉ nước, nhiệt ẩm kế, cảm biến cửa, cảm biến chuyển động, đèn, bàn phím, cảm biến hộp thư và thiết bị listener khi được tài khoản X-Sense báo cáo.
- Cập nhật thời gian thực qua X-Sense MQTT shadow, với polling đám mây định kỳ làm dự phòng.
- Cài đặt dễ dàng qua HACS.

## Yêu cầu
- Máy chủ Home Assistant đang hoạt động.
- Tài khoản X-Sense có thiết bị được hỗ trợ.
- HACS đã được cài đặt trong Home Assistant.

## Chuẩn bị
- **Tạo tài khoản X-Sense thứ hai cho Home Assistant**: Nên dùng tài khoản riêng vì một tài khoản có thể không đăng nhập ổn định cùng lúc trong ứng dụng và Home Assistant.
- **Chia sẻ thiết bị được hỗ trợ từ tài khoản chính sang tài khoản Home Assistant**: Tiếp tục quản lý bằng tài khoản chính và chỉ chia sẻ các thiết bị cần tích hợp.

## Cài đặt và cấu hình
1. Mở HACS trong Home Assistant.
2. Thêm `https://github.com/Jarnsen/ha-xsense-component_test` làm custom repository.
3. Tải xuống và cài đặt tích hợp.
4. Cấu hình bằng tên người dùng và mật khẩu X-Sense trong trang Integrations của Home Assistant.

## Thiết bị được hỗ trợ
Các entity được tạo phụ thuộc vào trường dữ liệu mà X-Sense cloud hoặc MQTT shadow báo cáo. Các thiết bị phổ biến gồm SBS50 base station, thiết bị khói và CO dòng XS/SC/XP/XC, báo nhiệt XH, cảm biến nước SWS, nhiệt ẩm kế STH, cảm biến cửa SDS, cảm biến chuyển động SMS, đèn, bàn phím, hộp thư, driveway alarm và các thiết bị khác báo cáo trường được hỗ trợ.

## Entity và thao tác
- Binary sensor cho alarm, mute, end-of-life, AC break, water alarm, temperature alarm, charging, motion, door, armed, reminder, light và diagnostics.
- Sensor cho battery, RF signal, Wi-Fi signal, firmware, temperature, humidity, CO, volume, timestamp dễ đọc, serial number, MAC address và diagnostics khác.
- Switch cho các cài đặt có thể ghi như LED light, alarm, reminders, PIR, sunshine, await và keypad sound khi thiết bị hỗ trợ.
- Nút test, mute và fire drill cho các mẫu được hỗ trợ.

## Ví dụ Automation
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
        message: "Phát hiện rò rỉ nước!"
```

## Cần sự hỗ trợ của bạn
Nếu bạn có thiết bị X-Sense chưa được kiểm thử, hãy gửi phản hồi qua GitHub, Discord hoặc diễn đàn Home Assistant.
