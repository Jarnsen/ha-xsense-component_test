# ha-xsense-component_test

## 概览
此 Home Assistant 集成可在智能家居中使用 X-Sense 设备。它基于 Theo Snel 的原始工作，并通过 HACS 安装。

建议为 Home Assistant 创建一个单独的 X-Sense 账号，并只从主账号共享受支持的设备。

## 安装
在 HACS 中添加自定义仓库 `https://github.com/Jarnsen/ha-xsense-component_test`，下载集成，按照 HACS 的重启提示操作，然后使用专用于 Home Assistant 的 X-Sense 账号完成配置。

## 支持的设备
当 X-Sense 账号上报相关设备时，本集成支持基站、烟雾报警器、CO 探测器、热报警器、水浸探测器、温湿度计、门磁和运动传感器、灯、键盘、邮箱传感器、监听设备以及受支持的摄像机。

已确认的型号系列包括：SBS50、XH02-M、XC01-M、XC04-WX、XS01-M、XS01-WX、XS03-WX、XS0B-MR、SC07-WX、XP0A-MR、SWS51、STH51、STH0A、STH0B、STH0C、SDS0A、SMS0A、SSC0A、SSC0B。

## 实体和操作
集成只会为设备实际上报的数据创建实体。这可能包括报警、静音状态、电池、信号、温度、湿度、CO、可读时间字段、摄像机设置、LED 开关，以及测试、静音或消防演练按钮。

设备管理、共享、移除、固件、账号和付款仍保留在 X-Sense 应用中。

## 支持
[Discord](https://discord.gg/5phHHgGb3V)

[Home Assistant Forum](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)
