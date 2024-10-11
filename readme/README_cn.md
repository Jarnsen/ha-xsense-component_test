# ha-xsense-component_test

<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## 概览
此 Home Assistant 集成允许在智能家居系统中使用 Xsense 设备。它基于 [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) 的原始代码创建，并在他的许可和合作下发布。

在 Theo 的官方 Home Assistant 集成发布之前，将使用此 HACS 集成，并定期更新以添加新功能和解决现有问题。此集成使用户可以轻松地将 Xsense 设备集成到 Home Assistant 中，并用于各种自动化和监控。

![images](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/c49a97f2-5e10-4129-82bc-1d647adc0895)

## 功能
- 将各种 Xsense 设备集成到 Home Assistant 中。
- 支持基于 Xsense 传感器数据的自动化。
- 支持以下设备类型：基站、烟雾探测器、一氧化碳探测器、热报警器、水泄漏探测器和湿度计。
- 通过 HACS（Home Assistant Community Store）进行简单设置。

## 要求
- 运行良好的 Home Assistant 服务器（建议使用最新版本）。
- 拥有支持设备的 Xsense 帐户。
- 必须在 Home Assistant 中安装 HACS 才能安装此集成。

## 教学视频
有关安装和配置集成的详细指南，您可以观看以下视频：

[![X-Sense Home Assistant Integration](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## 准备工作
在安装集成之前，需要进行一些准备工作：

- **在 X-Sense 应用程序中创建第二个帐户（供 Home Assistant 使用）**：由于无法同时使用同一个帐户在应用程序和 Home Assistant 中登录，我们建议为 Home Assistant 使用单独的帐户。这样可以避免在应用程序和 Home Assistant 之间频繁注销。额外的帐户可以实现无缝集成和连续使用，不会因频繁的登录和注销而中断。

- **将主帐户中的受支持设备共享到 Home Assistant 帐户**：使用 X-Sense 应用程序将**仅支持的设备**与新创建的帐户共享。这样，您可以轻松在 Home Assistant 中使用集成，同时继续通过主帐户管理设备。

![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## 通过 HACS 安装
1. **在 Home Assistant 中打开 HACS**：
   HACS 是 Home Assistant 的一个重要扩展，允许您轻松安装自定义集成。

   ![Download (1)](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **进入自定义存储库**：
   在 HACS 仪表板中导航到设置并将此存储库添加为自定义来源。

3. **添加存储库**：
   输入存储库的 URL：`https://github.com/Jarnsen/ha-xsense-component_test`

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **下载并安装集成**：
   在 HACS 中查找集成，下载并安装它。安装完成后，可以通过 Home Assistant 界面进行配置。

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)
   
   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## 配置
安装完成后，需要进行基本配置以正确设置集成：
- **用户名和密码**：使用新创建的 X-Sense 帐户的登录凭据建立连接。

    ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)
  
- **设备概览**：成功配置后，共享的设备将在 Home Assistant 中可用，并可以用于自动化。

    ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)
## Home Assistant 中的显示
成功安装和配置后，集成将在 Home Assistant 中可见。设备将在仪表板中可见，可用于自动化、通知和其他用途。


![论坛](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/2d271b78-39d9-4bbd-837d-8593cf1933bd)

____________________________________________________________

## 支持的设备
此集成支持多种 Xsense 设备。以下是当前已确认和测试的设备列表：
- **基站 (SBS50)**：Xsense 设备的中央集线器。
- **热报警器 (XH02-M)**：检测异常高温。
- **一氧化碳报警器 (XC01-M; XC04-WX)**：检测危险的一氧化碳浓度。
- **烟雾报警器 (XS01-M, WX; XS03-WX; XS0B-MR)**：早期检测烟雾。
- **一氧化碳和烟雾组合报警器 (SC07-WX; XP0A-MR (部分支持))**：组合设备，用于检测一氧化碳和烟雾。
- **水泄漏探测器 (SWS51)**：检测不希望存在的水。
- **湿度计-温度计 (STH51)**：监测温度和湿度。

这些设备可以在集成到 Home Assistant 后用于创建自动化和警报。

____________________________________________________________

## 自动化示例
通过此集成，可以创建各种自动化。以下是一些示例：

### 示例 1：温度警告
当 Xsense 温度计的温度过高时，会发送通知：

```yaml
automation:
  - alias: "Xsense 温度警告"
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

1. **测试设备**：如果您有一个与集成兼容的 Xsense 设备，请告诉我们，以便我们将其添加到支持的设备列表中。

2. **关于不支持设备的反馈**：如果设备无法正常工作，请提供反馈，以便我们提供支持或在未来的版本中包含该设备。

3. **共享设备进行测试**：测试新设备的最佳方式是通过 X-Sense 应用共享设备。这样可以确保尽可能多的设备得到支持。

4. **社区支持**：参与社区讨论。无论是提出改进建议还是帮助其他用户进行设置，每一种帮助都是值得赞赏的！

有关讨论和支持，您可以加入我们的 Discord 服务器或访问 Home Assistant 论坛：

[Discord](https://discord.gg/5phHHgGb3V)

[论坛](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)
