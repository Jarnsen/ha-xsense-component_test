# 简体中文文档

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


此页面是兼容旧链接的转向页。完整的简体中文文档请查看：

[打开简体中文 README](README_zh-CN.md)

____________________________________________________________

## Camera Live View and AI Notifications
Supported cameras use native Home Assistant WebRTC for live video and audio. They also create `Motion` and `AI Detection` event entities, such as `event.front_camera_motion` and `event.front_camera_ai_detection`. Use these `event.*` entities for notification automations, and replace sample entity IDs with the actual entity IDs shown in your Home Assistant instance.

The easiest UI path is the included blueprint. Use the button below to import it, select the camera `Motion` or `AI Detection` event entity, leave Event types selected to notify for every camera event, then keep or replace the default notification action. If a mobile notification action fails because a phone is not connected to local push notifications, edit the blueprint automation action and choose a working notification target.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2FJarnsen%2Fha-xsense-component_test%2Fmain%2Fblueprints%2Fautomation%2Fxsense%2Fcamera_ai_notification.yaml)

Camera Motion and AI Detection updates are one-time events, not on/off states. Trigger on them with Home Assistant's `event.received` trigger and filter by `event_type`. Supported event types include `motion`, `person`, `pet`, `vehicle`, `vehicle_enter`, `vehicle_out`, `vehicle_held_up`, `package`, `package_drop_off`, `package_pick_up`, `package_exist`, `other`, and `ai_detection`. The `ai_detection` event type is used when one camera notification contains more than one detected object.

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

____________________________________________________________
