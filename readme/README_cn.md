# 简体中文文档

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


此页面是兼容旧链接的转向页。完整的简体中文文档请查看：

[打开简体中文 README](README_zh-CN.md)

## 兼容性和 HACS 更新
如果你仍在使用旧的 `v1.2.6.x` 版本，请先更新到 `v1.3.14` 或更新版本，再将 Home Assistant Core 升级到 2026.7 或更新版本。当前的 `v1.3.x` 版本不再需要 `aiortc`。

此集成作为 HACS 自定义仓库安装。如果更新没有立即出现，请在 HACS 中选择 X-Sense 仓库，运行 **Update information**，然后更新或重新下载集成并重启 Home Assistant。


____________________________________________________________

## 摄像机实时预览和 AI 通知
最简单的方式是使用随附的 blueprint。点击下方按钮导入，选择摄像机的 `Motion` 事件实体，或在订阅摄像机可用时选择 `AI Detection`，然后按需调整通知动作。

When a Motion event includes X-Sense playback metadata, the integration immediately tries to cache the clip. The default camera-event blueprint sends a recording notification only after cached media is ready, using `recording_url` to open the X-Sense Recordings viewer and `recording_media_url` as proof that the clip is playable. Manual automation runs use the selected event entity's latest recording data, so recording-link notifications are skipped until that entity has a ready cached clip. Recording media sync can keep recent clips ready in the background.

[![导入 blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FJarnsen%2Fha-xsense-component_test%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fxsense%2Fcamera_ai_notification.yaml)

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

