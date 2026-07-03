# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## Tổng quan
Tích hợp Home Assistant này cho phép sử dụng thiết bị X-Sense trong hệ thống nhà thông minh. Dự án dựa trên mã gốc của [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) và được phát hành với sự cho phép cùng hợp tác của ông.

Cho đến khi có tích hợp Home Assistant chính thức, tích hợp HACS này sẽ tiếp tục được cập nhật để thêm tính năng và sửa lỗi.

## Tính năng
- Tích hợp nhiều thiết bị X-Sense vào Home Assistant.
- Hỗ trợ tự động hóa dựa trên dữ liệu cảm biến X-Sense.
- Hỗ trợ trạm gốc, đầu báo khói, đầu báo CO, báo nhiệt, cảm biến rò rỉ nước, nhiệt ẩm kế, cảm biến cửa, cảm biến chuyển động, đèn, bàn phím, cảm biến hộp thư và thiết bị lắng nghe khi được tài khoản X-Sense báo cáo.
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


## Thiết lập chi tiết bằng ảnh chụp màn hình

1. Tạo một tài khoản X-Sense riêng cho Home Assistant và chỉ chia sẻ các thiết bị được hỗ trợ từ tài khoản chính.

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

2. Trong HACS, thêm `https://github.com/Jarnsen/ha-xsense-component_test` làm kho tùy chỉnh.

![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

3. Tải xuống và cài đặt integration, khởi động lại Home Assistant, rồi cấu hình bằng tài khoản X-Sense mới.

![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

4. Sau khi thiết lập thành công, các thiết bị được chia sẻ sẽ xuất hiện trên trang thiết bị của Home Assistant.

![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)

5. Ghép nối, gỡ bỏ, firmware, thanh toán, thẻ SD và quản lý tài khoản vẫn nằm trong ứng dụng X-Sense.

## Thiết bị được hỗ trợ
Tích hợp này hỗ trợ nhiều thiết bị X-Sense. Thực thể được tạo phụ thuộc vào các trường dữ liệu mà thiết bị và tài khoản báo cáo. Các dòng và mẫu đã xác nhận gồm:
- **Trạm gốc (SBS50)**: Hub trung tâm cho thiết bị X-Sense.
- **Báo nhiệt (XH02-M)**: Phát hiện nhiệt độ cao bất thường.
- **Bộ phát hiện carbon monoxide (XC01-M; XC04-WX)**: Phát hiện nồng độ CO nguy hiểm.
- **Bộ phát hiện khói (XS01-M; XS01-WX; XS03-WX; XS0B-MR và các mẫu RF/iR liên quan)**: Phát hiện khói sớm.
- **Bộ phát hiện kết hợp CO và khói (SC07-WX; XP0A-MR và các mẫu XP/SC liên quan)**: Phát hiện CO và khói.
- **Bộ phát hiện rò nước (SWS51)**: Phát hiện nước ở nơi không mong muốn.
- **Ẩm kế-nhiệt kế (STH51, STH0A, STH0B, STH0C)**: Theo dõi nhiệt độ và độ ẩm.
- **Cảm biến cửa (SDS0A)** và **cảm biến chuyển động (SMS0A)**: Hiển thị khi X-Sense cung cấp trạng thái.
- **Camera (SSC0A, SSC0B)**: Hiển thị thực thể camera, ảnh thu nhỏ, URL phát trực tiếp, chẩn đoán và cài đặt dựa trên ứng dụng Android khi thiết bị và tài khoản hỗ trợ.
- **Thiết bị khác kết nối qua trạm**: Đèn, bàn phím, hộp thư, thiết bị lắng nghe, báo động lối xe, thiết bị nhận hàng thông minh, điều khiển và dữ liệu radon hiển thị khi API báo cáo trường được hỗ trợ.

### Thực thể và thao tác có sẵn
Tích hợp chỉ tạo thực thể Home Assistant cho các trường thực sự có trong đám mây X-Sense, payload MQTT shadow hoặc API camera tương ứng với hành vi của ứng dụng Android. Tùy thiết bị, có thể bao gồm:

- Binary sensor cho alarm, mute, end-of-life, AC-break, alarm nước, alarm nhiệt độ, sạc, chuyển động, cửa, trạng thái armed, cảnh báo, nhắc nhở, đèn, PIR và trạng thái keypad.
- Sensor cho pin, tín hiệu RF, tín hiệu Wi-Fi, phần mềm thiết bị, nhiệt độ, độ ẩm, mức CO, đỉnh CO, âm lượng báo động, âm lượng giọng nói, âm lượng tiếng bíp, âm lượng nhắc nhở, ngưỡng cảnh báo, bộ hẹn giờ tắt tiếng, mốc thời gian dễ đọc, múi giờ và dữ liệu chẩn đoán khác.
- Công tắc cho các thiết lập có thể ghi mà X-Sense báo cáo hỗ trợ, như đèn LED, bật cảnh báo, cảnh báo liên tục, âm chirp, nhắc nhở, PIR, ánh sáng mặt trời/ánh sáng trắng, chế độ chờ, âm bàn phím, phát hiện chuyển động camera, ghi hình, chế độ nhìn đêm, âm thanh, thời gian nghỉ, đèn và điều khiển chuông cửa.
- Lựa chọn và số cho các thiết lập camera được hỗ trợ như ngôn ngữ, độ phân giải ghi hình, codec, chống nhấp nháy, độ nhạy chuyển động, độ dài video, âm lượng, thời lượng cảnh báo, thời gian nghỉ, ngưỡng ban đêm và phím chuông cửa.
- Nút test, mute, fire-drill và wake camera cho các model mà ứng dụng X-Sense cung cấp thao tác tương ứng.

Một số thực thể là chẩn đoán hoặc cấu hình và được nhóm như vậy trong Home Assistant. Nếu thiết bị không báo cáo trường cụ thể, hoặc ứng dụng X-Sense đánh dấu tính năng không được hỗ trợ cho thiết bị/tài khoản đó, thực thể tương ứng sẽ không được tạo. Liên kết thiết bị, xóa, chia sẻ, tài khoản, thanh toán, cập nhật phần mềm thiết bị, định dạng thẻ SD và các thao tác quản trị khác vẫn nằm trong ứng dụng X-Sense.
____________________________________________________________

## Xem trực tiếp camera và thông báo AI
Cách đơn giản nhất là nhập blueprint đi kèm bằng nút bên dưới, chọn `Motion` hoặc `AI Detection` có sẵn, rồi chỉnh hành động thông báo nếu cần.

Khi sự kiện Motion có metadata phát lại từ X-Sense, tích hợp sẽ cố gắng cache clip ngay lập tức. Khi tệp đã sẵn sàng, thông báo dùng `recording_media_url` để phát video; nếu chưa, `recording_url` mở trình xem X-Sense Recordings trong Home Assistant. Recording media sync có thể chuẩn bị các clip mới ở nền.

[![Nhập blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FJarnsen%2Fha-xsense-component_test%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fxsense%2Fcamera_ai_notification.yaml)

Motion và AI Detection là sự kiện một lần, không phải trạng thái bật/tắt. Với tự động hóa thủ công hãy dùng `event.received`; chỉ dùng `event_type` để lọc các loại như `person`, `pet`, `vehicle`, `package`, `other` hoặc `ai_detection`.

Ví dụ tự động hóa:

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

____________________________________________________________
## Ví dụ tự động hóa
Với tích hợp này, có thể tạo nhiều automation khác nhau. Một vài ví dụ:

### Ví dụ 1: Cảnh báo nhiệt độ
Khi nhiệt độ từ nhiệt kế X-Sense quá cao, một thông báo được gửi:

```yaml
automation:
  - alias: "Cảnh báo nhiệt độ X-Sense"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "Nhiệt độ vượt quá 30 độ!"
```

### Ví dụ 2: Cảnh báo rò nước
Khi bộ phát hiện rò nước phát hiện nước, cảnh báo được kích hoạt:

```yaml
automation:
  - alias: "Cảnh báo rò nước"
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

## Tài liệu tham khảo đầy đủ

### Tài khoản và cài đặt
- Dùng một tài khoản X-Sense riêng cho Home Assistant.
- Chỉ chia sẻ các thiết bị được hỗ trợ từ tài khoản chính.
- Thêm, xóa, chia sẻ, thanh toán, phần mềm thiết bị và quản lý tài khoản vẫn nằm trong ứng dụng X-Sense.
- Nếu ứng dụng và Home Assistant đăng xuất lẫn nhau, hãy kiểm tra xem có dùng cùng tài khoản không.

### Cập nhật và sử dụng API
- Thay đổi trạng thái nhanh được nhận qua thông điệp MQTT shadow.
- Yêu cầu cloud chỉ dùng cho đăng nhập, tải thiết bị và làm mới trạng thái.
- Polling định kỳ chỉ là dự phòng khi thiếu thông điệp MQTT.
- Không nên lặp lại việc dò toàn bộ thiết bị trong mỗi lần cập nhật.

### Thực thể, camera và khắc phục sự cố
- Thực thể chỉ được tạo khi X-Sense thật sự báo trường đó.
- Giá trị chẩn đoán được nhóm là chẩn đoán trong Home Assistant.
- Camera được hỗ trợ có thể cung cấp thực thể camera, ảnh xem trước, luồng trực tiếp, trạng thái và cài đặt được hỗ trợ.
- Khi báo lỗi, hãy gửi model, phiên bản tích hợp, chẩn đoán, nhật ký và việc giá trị có đổi trong app hay không.

## Danh sách thiết bị và thực thể

### Nhóm thiết bị chính
- SBS50: trạm cơ sở và trạng thái cấp trạm.
- XS01-WX: báo khói Wi-Fi, bao gồm tài khoản không có thiết bị con riêng.
- XS01-M, XS03-WX, XS0B-MR: nhóm báo khói.
- XC01-M, XC04-WX: nhóm báo CO.
- SC07-WX, XP0A-MR: nhóm kết hợp khói và CO.
- XH02-M: nhóm báo nhiệt.
- SWS51: nhóm phát hiện rò rỉ nước.
- STH51, STH0A, STH0B, STH0C: nhiệt độ và độ ẩm.
- SDS0A: cảm biến cửa.
- SMS0A: cảm biến chuyển động.
- SSC0A, SSC0B: camera được hỗ trợ.

### Trường trạng thái
- Trạng thái cảnh báo hiển thị khi X-Sense báo trường cảnh báo.
- Trạng thái tắt tiếng hiển thị khi X-Sense báo trường tắt tiếng.
- Trạng thái pin hiển thị khi thiết bị báo dữ liệu pin.
- Giá trị RF và Wi-Fi hiển thị khi thiết bị báo.
- Giá trị thời gian dạng gọn của X-Sense được chuyển thành cảm biến thời gian dễ đọc trong Home Assistant.

### Điều khiển và báo lỗi
- Công tắc chỉ được tạo cho cài đặt có thể ghi mà X-Sense báo.
- Nút chỉ được tạo cho hành động được ứng dụng hỗ trợ.
- Điều khiển camera chỉ được tạo khi API đánh dấu là có sẵn.
- Báo lỗi nên có model chính xác, phiên bản tích hợp, chẩn đoán, nhật ký và giá trị có thay đổi trong app X-Sense không.
