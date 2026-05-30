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
此整合支援多種 X-Sense 裝置。可用實體取決於裝置與帳號實際回報的資料欄位。目前確認的裝置系列與型號包括：
- **基地台 (SBS50)**：X-Sense 裝置的中央 Hub。
- **熱警報器 (XH02-M)**：偵測異常高溫。
- **一氧化碳警報器 (XC01-M; XC04-WX)**：偵測危險的一氧化碳濃度。
- **煙霧警報器 (XS01-M; XS01-WX; XS03-WX; XS0B-MR 與相關 RF/iR 型號)**：早期偵測煙霧。
- **一氧化碳與煙霧複合警報器 (SC07-WX; XP0A-MR 與相關 XP/SC 型號)**：同時偵測一氧化碳與煙霧。
- **漏水偵測器 (SWS51)**：偵測不應出現的積水。
- **溫溼度計 (STH51, STH0A, STH0B, STH0C)**：監測溫度與濕度。
- **門磁感測器 (SDS0A)**：當 X-Sense 帳號提供時顯示門狀態。
- **動作感測器 (SMS0A)**：當 X-Sense 帳號提供時顯示動作警報狀態。
- **攝影機 (SSC0A, SSC0B)**：在裝置與帳號支援時，提供攝影機實體、縮圖、即時串流 URL、狀態診斷與 Android App 行為支援的設定。
- **其他連接至基地台的裝置**：燈、鍵盤、信箱感測器、listener、車道警報、smart drop、遙控器與氡資料會在 API 回報支援欄位時顯示。

### 可用實體與動作
整合只會為 X-Sense 雲端、MQTT shadow 或 App 支援的攝影機 API 中存在的欄位建立實體。依裝置不同，可能包含二元感測器、診斷感測器、開關、選擇項、數值與按鈕，例如測試、靜音、消防演練與喚醒攝影機。

如果裝置未回報某個欄位，或 X-Sense App 標示該裝置/帳號不支援該功能，就不會建立對應實體。裝置綁定、移除、分享、帳號、付款、韌體更新、SD 卡格式化與其他管理操作仍保留在 X-Sense App 中。

____________________________________________________________

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
