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

## Entity và thao tác
Tích hợp chỉ tạo entity cho các trường có trong cloud X-Sense, MQTT shadow hoặc API camera được ứng dụng hỗ trợ. Có thể bao gồm binary sensor, sensor chẩn đoán, switch, select, number và nút cho các chức năng được hỗ trợ như test, mute, fire drill và wake camera.

Nếu thiết bị không báo cáo trường hoặc ứng dụng X-Sense đánh dấu tính năng không được hỗ trợ cho thiết bị/tài khoản đó, entity sẽ không được tạo. Liên kết, xóa, chia sẻ, tài khoản, thanh toán, firmware, định dạng thẻ SD và các thao tác quản trị khác vẫn nằm trong ứng dụng X-Sense.

____________________________________________________________

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
