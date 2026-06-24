# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


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

## 教學影片
如需安裝與設定整合的詳細指南，可以觀看以下影片：

[![X-Sense Home Assistant Integration](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## 準備
- **建立第二個 X-Sense 帳戶供 Home Assistant 使用**：同一帳戶通常無法同時穩定登入 X-Sense App 與 Home Assistant，因此建議使用獨立帳戶。
- **從主要帳戶分享受支援裝置給 Home Assistant 帳戶**：用主要帳戶管理裝置，並將要整合的裝置分享給 Home Assistant 帳戶。

## 透過 HACS 安裝
1. **在 Home Assistant 中開啟 HACS**：
  HACS 是 Home Assistant 的重要擴充，可讓你輕鬆安裝自訂整合。

2. **前往自訂儲存庫**：
  在 HACS 儀表板設定中，將此儲存庫新增為自訂來源。

3. **新增儲存庫**：
  輸入儲存庫 URL：`https://github.com/Jarnsen/ha-xsense-component_test`

4. **下載並安裝整合**：
  在 HACS 中找到此整合、下載並安裝。安裝後即可透過 Home Assistant 介面設定。

____________________________________________________________

## 設定
安裝後需要基本設定才能正常使用整合：
- **使用者名稱與密碼**：使用新建立的 X-Sense 帳號登入資訊建立連線。
- **裝置概覽**：設定成功後，共享的裝置會出現在 Home Assistant 中，並可用於自動化。

## 在 Home Assistant 中檢視
成功安裝與設定後，整合會顯示在 Home Assistant 中。裝置可在儀表板使用，並可用於自動化、通知與其他用途。


## 詳細設定與截圖

1. 為 Home Assistant 建立獨立的 X-Sense 帳號，並只從主要帳號分享支援的裝置。

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

2. 在 HACS 中將 `https://github.com/Jarnsen/ha-xsense-component_test` 新增為自訂儲存庫。

![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

3. 下載並安裝整合、重新啟動 Home Assistant，然後使用新的 X-Sense 帳號完成設定。

![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

4. 設定成功後，共享的裝置會顯示在 Home Assistant 的裝置頁面。

![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)

5. 配對、移除、韌體、付款、SD 卡與帳號管理仍保留在 X-Sense App 中。

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
- **其他連接至基地台的裝置**：燈、鍵盤、信箱感測器、監聽裝置、車道警報、智慧投遞裝置、遙控器與氡資料會在 API 回報支援欄位時顯示。

### 可用實體與動作
整合只會針對 X-Sense 雲端、MQTT shadow 負載或與 Android App 行為一致的攝影機 API 中實際存在的欄位建立 Home Assistant 實體。依裝置不同，可能包含：

- 警報、靜音、壽命結束、AC 斷電、漏水警報、溫度警報、充電、動作、門、設防狀態、警告、提醒、燈光、PIR 與鍵盤狀態等二元感測器。
- 電池、RF 訊號、Wi-Fi 訊號、韌體、溫度、濕度、CO 濃度、CO 峰值、警報音量、語音音量、啁啾音量、提醒音量、警告門檻、靜音計時、可讀時間戳記、時區與其他診斷感測器。
- X-Sense 回報支援且可寫入的設定開關，例如 LED 燈、警報啟用、持續警報、啁啾音、提醒、PIR、日光/白光、等待狀態、鍵盤聲音、攝影機動作偵測、錄影、夜視、音訊、冷卻時間、燈光與門鈴控制。
- 支援的攝影機設定用選擇項與數值，例如語言、錄影解析度、編碼器、防閃爍頻率、動作靈敏度、影片長度、音量、警報持續時間、冷卻時間、夜間門檻與門鈴按鍵。
- 當 X-Sense App 對該型號提供對應動作時，建立測試、靜音、消防演練與喚醒攝影機按鈕。

部分實體屬於診斷或設定類別，Home Assistant 會依此分組。如果裝置沒有回報特定欄位，或 X-Sense App 標示該裝置/帳號不支援該功能，就不會建立對應實體。裝置綁定、移除、分享、帳號、付款、韌體更新、SD 卡格式化與其他管理操作仍保留在 X-Sense App 中。
____________________________________________________________

## 攝影機即時預覽與 AI 通知
最簡單的方式是使用隨附的 blueprint。使用下方按鈕匯入，選擇攝影機的 `Motion` 事件實體，或在訂閱攝影機可用時選擇 `AI Detection`，然後依需要調整通知動作。

[![匯入 blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2FJarnsen%2Fha-xsense-component_test%2Fmain%2Fblueprints%2Fautomation%2Fxsense%2Fcamera_ai_notification.yaml)

Motion 和 AI Detection 是一次性事件，不是開/關狀態。手動自動化請使用 Home Assistant 的 `event.received` 觸發器並選擇攝影機 `Motion` 或 `AI Detection` 實體；只有在需要把訂閱 AI Detection 限制為 `person`、`pet`、`vehicle`、`package`、`other` 或 `ai_detection` 等物件類型時，才使用 `event_type`。

自動化範例:

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
## 自動化範例
透過此整合可以建立多種自動化。以下是一些範例：

### 範例 1：溫度警示
當 X-Sense 溫度計的溫度過高時傳送通知：

```yaml
automation:
  - alias: "X-Sense 溫度警示"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_temperature
      above: 30
    action:
      service: notify.notify
      data:
        message: "溫度超過 30 度！"
```

### 範例 2：漏水警報
當漏水偵測器偵測到水時觸發警報：

```yaml
automation:
  - alias: "漏水警報"
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

## 完整參考

### 帳號與安裝
- 請為 Home Assistant 使用獨立的 X-Sense 帳號。
- 只從主帳號分享支援的裝置。
- 新增、移除、分享、付款、韌體與帳號管理仍保留在 X-Sense App。
- 如果 App 與 Home Assistant 互相登出，請確認是否使用同一個帳號。

### 更新與 API 使用
- 快速狀態變更會透過 MQTT shadow 訊息接收。
- 雲端請求只用於登入、載入裝置與刷新狀態。
- 定期輪詢只在 MQTT 訊息缺失時作為備援。
- 不應在每次更新時重複完整裝置探索。

### 實體、相機與疑難排解
- 只有 X-Sense 實際回報的欄位才會建立實體。
- 診斷值會在 Home Assistant 中歸類為診斷資訊。
- 支援的相機可提供相機實體、縮圖、即時串流、狀態與支援的設定。
- 回報問題時，請提供型號、整合版本、診斷資訊、記錄，以及 App 中數值是否會變化。

## 裝置與實體檢查清單

### 主要裝置系列
- SBS50：基站與基站層級狀態。
- XS01-WX：Wi-Fi 煙霧警報器，也包含沒有獨立子裝置的帳號。
- XS01-M、XS03-WX、XS0B-MR：煙霧警報器系列。
- XC01-M、XC04-WX：CO 警報器系列。
- SC07-WX、XP0A-MR：煙霧與 CO 複合系列。
- XH02-M：熱警報器系列。
- SWS51：漏水偵測器系列。
- STH51、STH0A、STH0B、STH0C：溫度與濕度。
- SDS0A：門窗感測器。
- SMS0A：動作感測器。
- SSC0A、SSC0B：支援的相機。

### 狀態欄位
- 當 X-Sense 回報 alarm 欄位時會顯示警報狀態。
- 當 X-Sense 回報 mute 欄位時會顯示靜音狀態。
- 當裝置回報電池資料時會顯示電池狀態。
- RF 與 Wi-Fi 訊號會在裝置回報時顯示。
- X-Sense 的精簡時間值會轉成 Home Assistant 可讀的時間感測器。

### 控制與回報
- 開關只會針對 X-Sense 回報的可寫設定建立。
- 按鈕只會針對 App 支援的動作建立。
- 相機控制只會在 API 標示可用時建立。
- 回報問題時，請提供精確型號、整合版本、診斷資訊、記錄，以及 X-Sense App 中數值是否會變化。
