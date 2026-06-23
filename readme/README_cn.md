# 简体中文文档

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


此页面是兼容旧链接的转向页。完整的简体中文文档请查看：

[打开简体中文 README](README_zh-CN.md)

____________________________________________________________

## 摄像机实时预览和 AI 通知
受支持的摄像机默认使用稳定的 X-Sense stream source 路径，在摄像机/账号提供时为 Home Assistant 实时预览提供视频和音频。实验性的 X-Sense WebRTC 桥接可在集成选项中开启用于测试，并会自动启用 debug 日志。摄像机还会创建 `Motion` 和 `AI Detection` 事件实体，例如 `event.front_camera_motion` 和 `event.front_camera_ai_detection`。

最简单的方式是使用随附的 blueprint。点击下方按钮导入，选择摄像机的 `Motion` 事件实体，或在订阅摄像机可用时选择 `AI Detection`，然后按需调整通知动作。

[![导入 blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2FJarnsen%2Fha-xsense-component_test%2Fmain%2Fblueprints%2Fautomation%2Fxsense%2Fcamera_ai_notification.yaml)

Motion 和 AI Detection 是一次性事件，不是开/关状态。手动自动化请使用 Home Assistant 的 `event.received` 触发器并选择摄像机 `Motion` 或 `AI Detection` 实体；只有在需要把订阅 AI Detection 限制为 `person`、`pet`、`vehicle`、`package`、`other` 或 `ai_detection` 等对象类型时，才使用 `event_type`。

自动化示例:

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
