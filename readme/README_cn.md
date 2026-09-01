# 简体中文文档

[Changelog](../CHANGELOG.md) - 每个已发布版本的链接发行说明。


此页面是兼容旧链接的转向页。完整的简体中文文档请查看：

[打开简体中文 README](README_zh-CN.md)

## 兼容性和 HACS 更新
如果你仍在使用旧的 `v1.2.6.x` 版本，请先更新到 `v1.3.14` 或更新版本，再将 Home Assistant Core 升级到 2026.7 或更新版本。当前的 `v1.4.x` 版本不再需要 `aiortc`。

此集成作为 HACS 自定义仓库安装。如果更新没有立即出现，请在 HACS 中选择 X-Sense 仓库，运行 **Update information**，然后更新或重新下载集成并重启 Home Assistant。


Entity changes: [X-Sense Entity Changes](../ENTITY_CHANGES.md).

____________________________________________________________

## 摄像机实时预览和 AI 通知
最简单的方式是使用随附的 blueprint。点击下方按钮导入，选择摄像机的 `Motion` 事件实体，或在订阅摄像机可用时选择 `AI Detection`，然后按需调整通知动作。

当 Motion 事件包含 X-Sense 播放元数据时，集成会在发送打开 X-Sense Recordings 中匹配剪辑的通知之前准备私有 Home Assistant 播放 URL。在蓝图中关闭录制链接，以获得不带视频的普通动作通知。较早导入的 X-Sense 相机蓝图会自动更新。

<!-- xsense-recording-storage-modes -->
摄像机 SD 卡记录显示在 X-Sense Recordings 中。仅播放是默认存储模式：Home Assistant 将签名的 X-Sense URL 保持私有，重写 HLS 播放列表，并仅在播放器请求时代理片段，而不保留完整的剪辑。保留本地录音将完整的剪辑存储在 /media/xsense_recordings 下，并启用可配置的保留、最大大小、手动删除和可选的后台同步。本地清理永远不会删除 X-Sense SD 卡或云存储中的录音。

[![导入 blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FJarnsen%2Fha-xsense-component_test%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fxsense%2Fcamera_ai_notification.yaml)

摄像机 Motion 同时提供显示当前已检测/已清除状态的二进制传感器，以及每次新检测触发一次的 Motion 事件。AI Detection 是一次性事件。手动自动化请使用 Home Assistant 的 `event.received` 触发器并选择摄像机 `Motion` 或 `AI Detection` 实体；只有在需要把订阅 AI Detection 限制为 `person`、`pet`、`vehicle`、`package`、`other` 或 `ai_detection` 等对象类型时，才使用 `event_type`。

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

## SKP0A 键盘代码自动化
SKP0A 键盘不会发布每个单独的按键。在使用 Home、Away 或 Disarmed 提交有效的 X-Sense 应用程序创建的代码后，它会发布键盘事件。集成将提交的代码事件公开为 `xsense_keypad_code`。

使用随附的单代码蓝图为选定的代码运行 Home Assistant 操作。您可以选择要求使用 Home、Away 或 Disarmed 模式按钮来提交代码，也可以选择将自动化限制为一个键盘序列号。

[![导入蓝图](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FJarnsen%2Fha-xsense-component_test%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fxsense%2Fkeypad_code_action.yaml)

当您希望通过自动化将多个键盘代码映射到不同的 Home Assistant 操作时，请使用路由器蓝图。

[![导入路由器蓝图](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FJarnsen%2Fha-xsense-component_test%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fxsense%2Fkeypad_code_router.yaml)

键盘模式按钮充当提交按钮。如果所选模式已处于活动状态，X-Sense 可能不会发布新事件，因此在提交代码时选择当前非活动模式按钮之一。

____________________________________________________________
