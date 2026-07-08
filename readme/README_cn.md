# 简体中文文档

[Changelog](../CHANGELOG.md) - 每个已发布版本的链接发行说明。


此页面是兼容旧链接的转向页。完整的简体中文文档请查看：

[打开简体中文 README](README_zh-CN.md)

## 兼容性和 HACS 更新
如果你仍在使用旧的 `v1.2.6.x` 版本，请先更新到 `v1.3.14` 或更新版本，再将 Home Assistant Core 升级到 2026.7 或更新版本。当前的 `v1.3.x` 版本不再需要 `aiortc`。

此集成作为 HACS 自定义仓库安装。如果更新没有立即出现，请在 HACS 中选择 X-Sense 仓库，运行 **Update information**，然后更新或重新下载集成并重启 Home Assistant。


Entity changes: [X-Sense Entity Changes](../ENTITY_CHANGES.md).

____________________________________________________________

## 摄像机实时预览和 AI 通知
最简单的方式是使用随附的 blueprint。点击下方按钮导入，选择摄像机的 `Motion` 事件实体，或在订阅摄像机可用时选择 `AI Detection`，然后按需调整通知动作。

当 Motion 事件包含 X-Sense 播放数据时，集成可以先缓存该片段，然后发送移动通知，点击后会在 X-Sense Recordings 中打开对应片段。如果只想收到普通移动通知而不等待视频，请在 blueprint 中关闭录像链接。录像媒体同步可以在后台提前准备最新片段，旧的已导入 X-Sense 摄像机 blueprint 会自动更新。

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

