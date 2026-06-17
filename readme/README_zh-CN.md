# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## 概览
此 Home Assistant 集成允许在智能家居系统中使用 X-Sense 设备。它基于 [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) 的原始代码创建，并在他的许可和合作下发布。

此 HACS 集成会持续维护，面向希望在 Home Assistant 中获得更广泛 X-Sense 设备支持的用户。它会定期更新，加入新功能、扩大设备覆盖范围，并修复用户反馈的问题。

<p align="center">
 <img src="https://github.com/user-attachments/assets/fbe7e69b-9204-4de4-a245-e0e2bdbd7f73" alt="Image">
</p>

## 功能
- 将各种 X-Sense 设备集成到 Home Assistant 中。
- 支持基于 X-Sense 传感器数据的自动化。
- 支持 X-Sense 账号中可用的基站、烟雾报警器、一氧化碳报警器、热报警器、水浸探测器、温湿度计、门磁、运动传感器、灯、键盘、邮箱传感器、监听器、摄像机以及其他受支持设备。
- 通过 HACS（Home Assistant Community Store）进行简单设置。

## 要求
- 运行良好的 Home Assistant 服务器（建议使用最新版本）。
- 拥有支持设备的 X-Sense 帐户。
- 必须在 Home Assistant 中安装 HACS 才能安装此集成。

## 教学视频
有关安装和配置集成的详细指南，您可以观看以下视频：

[![X-Sense Home Assistant Integration](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## 准备工作
在安装集成之前，需要进行一些准备工作：

- **在 X-Sense 应用程序中创建第二个帐户（供 Home Assistant 使用）**：由于无法同时使用同一个帐户在应用程序和 Home Assistant 中登录，我们建议为 Home Assistant 使用单独的帐户。这样可以避免在应用程序和 Home Assistant 之间频繁注销。额外的帐户可以实现无缝集成和连续使用，不会因频繁的登录和注销而中断。

- **将主帐户中的受支持设备共享到 Home Assistant 帐户**：使用 X-Sense 应用程序仅将**受支持的设备**共享给新创建的帐户。这样，您可以轻松在 Home Assistant 中使用集成，同时继续通过主帐户管理设备。

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## 通过 HACS 安装
1. **在 Home Assistant 中打开 HACS**：
  HACS 是 Home Assistant 的一个重要扩展，允许您轻松安装自定义集成。

  ![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **进入自定义存储库**：
  在 HACS 仪表板中导航到设置并将此存储库添加为自定义来源。

3. **添加存储库**：
  输入存储库的 URL：`https://github.com/Jarnsen/ha-xsense-component_test`

  ![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **下载并安装集成**：
  在 HACS 中查找集成，下载并安装它。安装完成后，可以通过 Home Assistant 界面进行配置。

  ![HACS repository selection screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)

  ![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## 配置
安装完成后，需要进行基本配置以正确设置集成：
- **用户名和密码**：使用新创建的 X-Sense 帐户的登录凭据建立连接。

  ![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

- **设备概览**：成功配置后，共享的设备将在 Home Assistant 中可用，并可以用于自动化。

  ![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)
## Home Assistant 中的显示
成功安装和配置后，集成将在 Home Assistant 中可见。设备将在仪表板中可见，可用于自动化、通知和其他用途。


![论坛](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/2d271b78-39d9-4bbd-837d-8593cf1933bd)

____________________________________________________________

## 支持的设备
此集成支持多种 X-Sense 设备。可用实体取决于设备和账号实际上报的数据字段。目前确认的设备系列和型号包括：
- **基站 (SBS50)**：X-Sense 设备的中央集线器。
- **热报警器 (XH02-M)**：检测异常高温。
- **一氧化碳报警器 (XC01-M; XC04-WX)**：检测危险的一氧化碳浓度。
- **烟雾报警器 (XS01-M; XS01-WX; XS03-WX; XS0B-MR 及相关 RF/iR 型号)**：用于早期烟雾检测。
- **一氧化碳和烟雾组合报警器 (SC07-WX; XP0A-MR 及相关 XP/SC 型号)**：同时检测一氧化碳和烟雾。
- **水浸探测器 (SWS51)**：检测不应出现的积水。
- **温湿度计 (STH51, STH0A, STH0B, STH0C)**：监测温度和湿度。
- **门磁传感器 (SDS0A)**：当 X-Sense 账号提供时显示门状态。
- **运动传感器 (SMS0A)**：当 X-Sense 账号提供时显示运动报警状态。
- **摄像机 (SSC0A, SSC0B)**：在设备和账号支持时，提供摄像机实体、缩略图、实时流 URL、状态诊断以及基于 Android 应用行为的设置。
- **其他连接到基站的设备**：灯、键盘、邮箱传感器、监听器、车道报警、智能投递设备、遥控器和氡数据会在 API 上报支持字段时显示。

### 可用实体和操作
集成只会为 X-Sense 云端、MQTT shadow payload 或与 Android 应用行为一致的摄像机 API 中实际存在的字段创建 Home Assistant 实体。根据设备不同，可能包括：

- 用于 alarm、mute、end-of-life、AC-break、水浸报警、温度报警、充电、运动、门、布防状态、warning、reminder、light、PIR 和 keypad 状态的二进制传感器。
- 电池、RF 信号、Wi-Fi 信号、固件、温度、湿度、CO 浓度、CO 峰值、警报音量、语音音量、提示音音量、提醒音量、警告阈值、静音计时器、可读时间戳、时区以及其他诊断传感器。
- X-Sense 报告支持的可写设置开关，例如 LED light、alarm enablement、continued alarm、chirp tone、reminders、PIR、sunshine/white light、await、keypad sound、camera motion detection、recording、night vision、audio、cooldown、light 和 doorbell 控制。
- 用于受支持摄像机设置的 select 和 number，例如 language、recording resolution、codec、anti-flicker rate、motion sensitivity、video length、volume、alarm duration、cooldown、night threshold 和 doorbell ring key。
- 当 X-Sense 应用为该型号提供相应操作时，创建 test、mute、fire-drill 和 camera wake 按钮。

部分实体属于诊断或配置类，会在 Home Assistant 中按相应类别分组。如果设备未上报某个字段，或 X-Sense 应用标记该设备/账号不支持该功能，则不会创建对应实体。设备绑定、删除、共享、账号、支付、固件更新、SD 卡格式化以及其他管理操作仍保留在 X-Sense 应用中。
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
## 自动化示例
通过此集成，可以创建各种自动化。以下是一些示例：

### 示例 1：温度警告
当 X-Sense 温度计的温度过高时，会发送通知：

```yaml
automation:
  - alias: "X-Sense 温度警告"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "温度超过 30 度！"
```

### 示例 2：水泄漏报警
当水泄漏探测器检测到水时，会触发警报：

```yaml
automation:
  - alias: "水泄漏报警"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "检测到水泄漏！"
```

____________________________________________________________

## 我们需要你的帮助
我们始终在寻求支持，以进一步开发和改进此集成。以下是一些您可以帮助的方式：

1. **测试设备**：如果您有一个与集成兼容的 X-Sense 设备，请告诉我们，以便我们将其添加到支持的设备列表中。

2. **关于不支持设备的反馈**：如果设备无法正常工作，请提供反馈，以便我们提供支持或在未来的版本中包含该设备。

3. **共享设备进行测试**：测试新设备的最佳方式是通过 X-Sense 应用共享设备。这样可以确保尽可能多的设备得到支持。

4. **社区支持**：参与社区讨论。无论是提出改进建议还是帮助其他用户进行设置，每一种帮助都是值得赞赏的！

有关讨论和支持，您可以加入我们的 Discord 服务器或访问 Home Assistant 论坛：

[Discord](https://discord.gg/5phHHgGb3V)

[论坛](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

## 完整参考

### 账号和安装
- 为 Home Assistant 使用单独的 X-Sense 账号。
- 只从主 X-Sense 账号共享受支持的设备。
- 配对、移除、共享、固件、账号、付款和 SD 卡管理仍在 X-Sense 应用中完成。

### 更新和 API 使用
- 快速状态变化通过 MQTT shadow 消息接收。
- 云端请求用于登录、设备发现、摄像头数据和状态恢复。
- 周期性轮询只是缺少实时更新时的备用方式。

### 实体、摄像头和故障排查
- 只有 X-Sense 实际上报的字段才会创建实体。
- 摄像头实体和控制项只会在与 Android 应用一致的 API 为该账号和型号报告支持时创建。
- 如果缺少某个值，请先与 X-Sense 应用对比，然后附上诊断信息和相关 Home Assistant 日志。

## 设备和实体检查清单

### 主要设备系列
- 当 API 暴露相应字段时，会处理 SBS50 基站、XS 烟雾报警器、XC 一氧化碳报警器、SC/XP 组合报警器、XH 热报警器、SWS 漏水传感器、STH 温湿度传感器、SDS 门磁、SMS 运动传感器、SSC 摄像头以及其他 X-Sense 上报的设备系列。

### 状态字段
- 报警、静音、电池、RF/Wi-Fi 信号、温度、湿度、CO、水、运动、门、灯、提醒、警告和可读时间戳只会在 X-Sense 上报时显示。

### 控制和反馈
- 开关、选择、数值和按钮只会为设备/账号暴露的可写设置和操作创建。
- 好的错误报告应包含准确型号、集成版本、诊断信息、日志，以及该值在 X-Sense 应用中是否正确变化。
