# ha-xsense-component_test

<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## 概覽
這個 Home Assistant 整合可讓 X-Sense 裝置加入智慧家庭系統。它以 [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) 的原始程式碼為基礎，並在他的同意與合作下發布。

在官方 Home Assistant 整合可用之前，這個 HACS 整合會持續更新，以加入新功能並修正問題。

## 功能
- 將多種 X-Sense 裝置整合到 Home Assistant。
- 支援以 X-Sense 感測資料建立自動化。
- 支援基地台、煙霧警報器、一氧化碳警報器、熱警報器、漏水偵測器、溫溼度計、門窗感測器、動作感測器、燈具、鍵盤、信箱感測器與監聽器等裝置，前提是 X-Sense 帳戶有回報這些裝置。
- 透過 X-Sense MQTT shadow 取得即時更新，並以週期性雲端輪詢作為備援。
- 可透過 HACS 安裝。

## 需求
- 可正常運作的 Home Assistant 伺服器。
- 具有受支援裝置的 X-Sense 帳戶。
- 已安裝 HACS。

## 準備
- **建立第二個 X-Sense 帳戶供 Home Assistant 使用**：同一帳戶通常無法同時穩定登入 X-Sense App 與 Home Assistant，因此建議使用獨立帳戶。
- **從主要帳戶分享受支援裝置給 Home Assistant 帳戶**：用主要帳戶管理裝置，並將要整合的裝置分享給 Home Assistant 帳戶。

## 安裝與設定
1. 在 Home Assistant 中開啟 HACS。
2. 將 `https://github.com/Jarnsen/ha-xsense-component_test` 加入 HACS 自訂存放庫。
3. 下載並安裝整合。
4. 在 Home Assistant 的整合頁面中使用 X-Sense 帳號密碼完成設定。

## 支援的裝置
支援的實體取決於 X-Sense 雲端或 MQTT shadow 回報的欄位。常見裝置包含 SBS50 基地台、XS/SC/XP/XC 系列煙霧與一氧化碳裝置、XH 熱警報器、SWS 漏水偵測器、STH 溫溼度計、SDS 門窗感測器、SMS 動作感測器，以及燈具、鍵盤、信箱、車道警報與其他回報支援欄位的裝置。

## 可用實體與動作
- 警報、靜音、壽命結束、AC 中斷、漏水、溫度警報、充電、動作、門窗、佈防、提醒、燈光與診斷二元感測器。
- 電量、RF 訊號、Wi-Fi 訊號、韌體、溫度、濕度、CO 數值、音量、可讀時間戳記、序號、MAC 位址與其他診斷感測器。
- 裝置回報支援時，會提供 LED 燈、警報、提醒、PIR、日照、等待與鍵盤聲音等開關。
- 支援型號會提供測試、靜音與消防演練按鈕。

## 自動化範例
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
        message: "偵測到漏水！"
```

## 需要協助
如果你有尚未測試的 X-Sense 裝置，請在 GitHub、Discord 或 Home Assistant 論壇提供回饋。
