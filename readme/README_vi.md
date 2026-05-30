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

## Video hướng dẫn
Để xem hướng dẫn chi tiết về cài đặt và cấu hình tích hợp, bạn có thể xem video sau:

[![X-Sense Home Assistant Integration](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## Chuẩn bị
- **Tạo tài khoản X-Sense thứ hai cho Home Assistant**: Nên dùng tài khoản riêng vì một tài khoản có thể không đăng nhập ổn định cùng lúc trong ứng dụng và Home Assistant.
- **Chia sẻ thiết bị được hỗ trợ từ tài khoản chính sang tài khoản Home Assistant**: Tiếp tục quản lý bằng tài khoản chính và chỉ chia sẻ các thiết bị cần tích hợp.

## Cài đặt qua HACS
1. **Mở HACS trong Home Assistant**:
   HACS là tiện ích quan trọng giúp cài đặt các tích hợp tùy chỉnh dễ dàng.

2. **Vào custom repositories**:
   Trong cài đặt HACS, thêm repository này làm nguồn tùy chỉnh.

3. **Thêm repository**:
   Nhập URL repository: `https://github.com/Jarnsen/ha-xsense-component_test`

4. **Tải xuống và cài đặt tích hợp**:
   Tìm tích hợp trong HACS, tải xuống và cài đặt. Sau khi cài đặt, cấu hình được thực hiện trong giao diện Home Assistant.

____________________________________________________________

## Cấu hình
Sau khi cài đặt, cần cấu hình cơ bản để tích hợp hoạt động đúng:
- **Tên người dùng và mật khẩu**: Dùng thông tin đăng nhập của tài khoản X-Sense mới tạo cho Home Assistant.
- **Tổng quan thiết bị**: Sau khi cấu hình thành công, các thiết bị đã chia sẻ sẽ xuất hiện trong Home Assistant và có thể dùng cho automation.

## Hiển thị trong Home Assistant
Sau khi cài đặt và cấu hình thành công, tích hợp sẽ hiển thị trong Home Assistant. Các thiết bị có sẵn trên dashboard và có thể dùng cho automation, thông báo và các mục đích khác.

## Thiết bị được hỗ trợ
Tích hợp này hỗ trợ nhiều thiết bị X-Sense. Entity được tạo phụ thuộc vào các trường dữ liệu mà thiết bị và tài khoản báo cáo. Các dòng và mẫu đã xác nhận gồm:
- **Trạm gốc (SBS50)**: Hub trung tâm cho thiết bị X-Sense.
- **Báo nhiệt (XH02-M)**: Phát hiện nhiệt độ cao bất thường.
- **Bộ phát hiện carbon monoxide (XC01-M; XC04-WX)**: Phát hiện nồng độ CO nguy hiểm.
- **Bộ phát hiện khói (XS01-M; XS01-WX; XS03-WX; XS0B-MR và các mẫu RF/iR liên quan)**: Phát hiện khói sớm.
- **Bộ phát hiện kết hợp CO và khói (SC07-WX; XP0A-MR và các mẫu XP/SC liên quan)**: Phát hiện CO và khói.
- **Bộ phát hiện rò nước (SWS51)**: Phát hiện nước ở nơi không mong muốn.
- **Ẩm kế-nhiệt kế (STH51, STH0A, STH0B, STH0C)**: Theo dõi nhiệt độ và độ ẩm.
- **Cảm biến cửa (SDS0A)** và **cảm biến chuyển động (SMS0A)**: Hiển thị khi X-Sense cung cấp trạng thái.
- **Camera (SSC0A, SSC0B)**: Hiển thị entity camera, ảnh thu nhỏ, URL phát trực tiếp, chẩn đoán và cài đặt dựa trên ứng dụng Android khi thiết bị và tài khoản hỗ trợ.
- **Thiết bị khác kết nối qua trạm**: Đèn, bàn phím, hộp thư, listener, báo động lối xe, smart drop, điều khiển và dữ liệu radon hiển thị khi API báo cáo trường được hỗ trợ.

### Entity và thao tác có sẵn
Tích hợp chỉ tạo entity Home Assistant cho các trường thực sự có trong cloud X-Sense, payload MQTT shadow hoặc API camera tương ứng với hành vi của ứng dụng Android. Tùy thiết bị, có thể bao gồm:

- Binary sensor cho alarm, mute, end-of-life, AC-break, alarm nước, alarm nhiệt độ, sạc, chuyển động, cửa, trạng thái armed, cảnh báo, nhắc nhở, đèn, PIR và trạng thái keypad.
- Sensor cho pin, tín hiệu RF, tín hiệu Wi-Fi, firmware, nhiệt độ, độ ẩm, mức CO, đỉnh CO, âm lượng alarm, âm lượng voice, âm lượng chirp, âm lượng reminder, ngưỡng cảnh báo, timer mute, timestamp dễ đọc, múi giờ, số sê-ri, địa chỉ MAC và dữ liệu chẩn đoán khác.
- Switch cho các thiết lập có thể ghi mà X-Sense báo cáo hỗ trợ, như đèn LED, bật alarm, continued alarm, âm chirp, reminder, PIR, sunshine/white light, await, âm keypad, phát hiện chuyển động camera, ghi hình, night vision, audio, cooldown, đèn và điều khiển doorbell.
- Select và number cho các thiết lập camera được hỗ trợ như ngôn ngữ, độ phân giải ghi hình, codec, anti-flicker, độ nhạy chuyển động, độ dài video, volume, thời lượng alarm, cooldown, ngưỡng ban đêm và phím chuông doorbell.
- Nút test, mute, fire-drill và wake camera cho các model mà ứng dụng X-Sense cung cấp thao tác tương ứng.

Một số entity là chẩn đoán hoặc cấu hình và được nhóm như vậy trong Home Assistant. Nếu thiết bị không báo cáo trường cụ thể, hoặc ứng dụng X-Sense đánh dấu tính năng không được hỗ trợ cho thiết bị/tài khoản đó, entity tương ứng sẽ không được tạo. Liên kết thiết bị, xóa, chia sẻ, tài khoản, thanh toán, cập nhật firmware, định dạng thẻ SD và các thao tác quản trị khác vẫn nằm trong ứng dụng X-Sense.
____________________________________________________________

## Ví dụ Automation
Với tích hợp này, có thể tạo nhiều automation khác nhau. Một vài ví dụ:

### Ví dụ 1: Cảnh báo nhiệt độ
Khi nhiệt độ từ nhiệt kế X-Sense quá cao, một thông báo được gửi:

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
        message: "Nhiệt độ vượt quá 30 độ!"
```

### Ví dụ 2: Alarm rò nước
Khi bộ phát hiện rò nước phát hiện nước, cảnh báo được kích hoạt:

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
        message: "Phát hiện rò rỉ nước!"
```

## Cần sự hỗ trợ của bạn
Nếu bạn có thiết bị X-Sense chưa được kiểm thử, hãy gửi phản hồi qua GitHub, Discord hoặc diễn đàn Home Assistant.
