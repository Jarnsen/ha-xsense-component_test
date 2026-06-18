# ha-xsense-component_test

[Changelog](../CHANGELOG.md) - linked release notes for every published version.


<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## 概要
この Home Assistant 統合により、X-Sense デバイスをスマートホームシステムに統合することができます。この統合は [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) のオリジナルコードに基づいて作成され、彼の許可と協力のもとで公開されました。

この HACS 統合は、Home Assistant でより幅広い X-Sense デバイス対応を求めるユーザー向けに積極的に保守されています。新機能、対応デバイスの拡充、報告された問題の修正を含めて定期的に更新されます。

<p align="center">
 <img src="https://github.com/user-attachments/assets/fbe7e69b-9204-4de4-a245-e0e2bdbd7f73" alt="Image">
</p>

## 機能
- X-Sense デバイスを Home Assistant に統合します。
- X-Sense センサーのデータを使用した自動化をサポートします。
- 次のデバイスタイプをサポートします：ベースステーション、煙検知器、一酸化炭素検知器、熱アラーム、水漏れ検知器、湿度計。
- HACS（Home Assistant Community Store）を通じて簡単に設定できます。

## 必要条件
- 正常に動作する Home Assistant サーバー（最新バージョン推奨）。
- サポートされているデバイスを持つ X-Sense アカウント。
- この統合をインストールするには、Home Assistant に HACS がインストールされている必要があります。

## チュートリアル動画
インストールと統合の設定に関する詳細なガイドについては、以下のビデオをご覧ください：

[![X-Sense Home Assistant Integration](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## 準備
統合をインストールする前に、いくつかの準備が必要です：

- **X-Sense アプリで 2 番目のアカウントを作成（Home Assistant 用）**：同じアカウントでアプリと Home Assistant に同時にログインすることはできないため、Home Assistant 用に別のアカウントを使用することをお勧めします。これにより、アプリと Home Assistant との間で頻繁にログアウトすることを防ぎます。追加のアカウントにより、シームレスな統合と継続的な使用が可能になり、頻繁なログインとログアウトによる中断がなくなります。

- **メインアカウントから Home Assistant アカウントにサポートされているデバイスを共有**：X-Sense アプリを使用して、新しく作成したアカウントと **サポートされているデバイスのみ** を共有します。これにより、メインアカウントを通じてデバイスを管理しながら、Home Assistant で簡単に統合を使用できます。

![X-Sense device sharing screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## HACS からのインストール
1. **Home Assistant で HACS を開く**：
  HACS は Home Assistant の重要な拡張機能で、カスタム統合のインストールを簡単に行うことができます。

  ![HACS download screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **カスタムリポジトリに移動**：
  HACS ダッシュボードの設定に移動し、このリポジトリをカスタムソースとして追加します。

3. **リポジトリを追加**：
  リポジトリの URL を入力します：`https://github.com/Jarnsen/ha-xsense-component_test`

  ![HACS custom repository screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **統合をダウンロードしてインストール**：
  HACS で統合を検索し、ダウンロードしてインストールします。インストール後、Home Assistant インターフェースを介して設定が行えます。

  ![HACS repository selection screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)

  ![HACS installation screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## 設定
インストール後、統合を正しく設定するために基本的な設定が必要です：
- **ユーザー名とパスワード**：新しく作成した X-Sense アカウントの認証情報を使用して接続を確立します。

  ![X-Sense configuration screen](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)

- **デバイス概要**：設定が成功すると、共有されたデバイスが Home Assistant で利用可能になり、自動化に使用できます。

  ![Home Assistant device overview](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)
## Home Assistant での表示
インストールと設定が成功すると、Home Assistant で統合が表示されます。デバイスはダッシュボードに表示され、自動化、通知、その他の用途に使用できます。

![フォーラム](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/2d271b78-39d9-4bbd-837d-8593cf1933bd)

____________________________________________________________

## サポートされているデバイス
この統合は複数の X-Sense デバイスをサポートします。作成されるエンティティは、デバイスとアカウントが報告するデータ項目によって変わります。確認済みの主なデバイスは次のとおりです。
- **ベースステーション (SBS50)**: X-Sense デバイスの中央ハブ。
- **熱警報器 (XH02-M)**: 異常な高温を検出します。
- **一酸化炭素検知器 (XC01-M; XC04-WX)**: 危険な CO 濃度を検出します。
- **煙検知器 (XS01-M; XS01-WX; XS03-WX; XS0B-MR および関連 RF/iR モデル)**: 煙を早期検知します。
- **CO/煙複合検知器 (SC07-WX; XP0A-MR および関連 XP/SC モデル)**: CO と煙を検知します。
- **水漏れ検知器 (SWS51)**: 不要な場所の水を検知します。
- **温湿度計 (STH51, STH0A, STH0B, STH0C)**: 温度と湿度を監視します。
- **ドアセンサー (SDS0A)** と **モーションセンサー (SMS0A)**: X-Sense が状態を提供する場合に表示されます。
- **カメラ (SSC0A, SSC0B)**: デバイスとアカウントが対応している場合、カメラエンティティ、サムネイル、ライブストリーム URL、診断、Android アプリに基づく設定を提供します。
- **その他のステーション接続デバイス**: ライト、キーパッド、メールボックス、リスナー端末、 車道アラーム、スマートドロップ、リモコン、ラドンデータは、API が対応フィールドを報告する場合に表示されます。

### 利用可能なエンティティと操作
この統合は、X-Sense クラウド、MQTT shadow payload、または Android アプリの挙動に合わせたカメラ API に実際に存在するフィールドに対してのみ Home Assistant エンティティを作成します。デバイスによって、次のようなものが含まれます。

- alarm、mute、end-of-life、AC-break、水漏れアラーム、温度アラーム、充電、モーション、ドア、armed 状態、warning、reminder、light、PIR、keypad 状態のバイナリセンサー。
- バッテリー、RF信号、Wi-Fi信号、ファームウェア、温度、湿度、CO濃度、COピーク、アラーム音量、音声音量、チャープ音量、リマインダー音量、警告しきい値、ミュートタイマー、読みやすい タイムスタンプ、タイムゾーン、その他の診断センサー。
- X-Sense が対応を報告する書き込み可能な設定用スイッチ。例: LED light、alarm enablement、continued alarm、chirp tone、reminders、PIR、sunshine/white light、await、keypad sound、camera motion detection、recording、night vision、audio、cooldown、light、doorbell controls。
- language、recording resolution、codec、anti-flicker rate、motion sensitivity、video length、volume、alarm duration、cooldown、night threshold、doorbell ring key など、対応するカメラ設定用の select と number エンティティ。
- X-Sense アプリが該当モデルで対応操作を提供している場合の test、mute、fire-drill、camera wake ボタン。

一部のエンティティは診断または設定関連であり、Home Assistant でもそのように分類されます。デバイスが特定のフィールドを報告しない場合、または X-Sense アプリがそのデバイス/アカウントで機能非対応と示す場合、対応するエンティティは作成されません。デバイスの追加、削除、共有、アカウント、支払い、ファームウェア 更新、SD カード初期化、その他の管理操作は X-Sense アプリ側に残ります。
____________________________________________________________

## Camera AI Notifications
Supported cameras create an `AI Detection` event entity, such as `event.front_camera_ai_detection`. Use this `event.*` entity for notification automations, and replace the sample entity ID with the actual entity ID shown in your Home Assistant instance.

The easiest UI path is the included blueprint. Use the button below to import it, select the camera `AI Detection` event entity, leave Detection types selected to notify for every AI event, then keep or replace the default notification action.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2FJarnsen%2Fha-xsense-component_test%2Fmain%2Fblueprints%2Fautomation%2Fxsense%2Fcamera_ai_notification.yaml)

AI detections are one-time events, not on/off states. Trigger on them with Home Assistant's `event.received` trigger and filter by `event_type`. Supported event types include `person`, `pet`, `vehicle`, `vehicle_enter`, `vehicle_out`, `vehicle_held_up`, `package`, `package_drop_off`, `package_pick_up`, `package_exist`, `other`, and `ai_detection`. The `ai_detection` event type is used when one camera notification contains more than one detected object.

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

Use the `Last AI Detection` sensor and related last-detection timestamp sensors only for last-known history, dashboards, or conditions. These sensors can be unknown until the first notification arrives and are not the main notification trigger.
____________________________________________________________
## 自動化の例
この統合を使用すると、さまざまな自動化を作成できます。以下はいくつかの例です：

### 例 1：温度警告
X-Sense 温度計の温度が高すぎる場合、通知が送信されます：

```yaml
automation:
  - alias: "X-Sense 温度警告"
    trigger:
      platform: numeric_state
      entity_id: sensor.xsense_温度
      above: 30
    action:
      service: notify.notify
      data:
        message: "温度が 30 度を超えました！"
```

### 例 2：水漏れアラーム
水漏れ検知器が水を検出した場合、警報が発生します：

```yaml
automation:
  - alias: "水漏れアラーム"
    trigger:
      platform: state
      entity_id: binary_sensor.xsense_waterleak
      to: "on"
    action:
      service: notify.notify
      data:
        message: "水漏れが検出されました！"
```

____________________________________________________________

## ご協力ください
この統合をさらに開発し、改善するためのサポートを常に求めています。以下はあなたが支援できる方法のいくつかです：

1. **デバイステスト**：X-Sense デバイスを持っていて、この統合と互換性がある場合は、それをお知らせください。サポートされているデバイスのリストに追加します。

2. **サポートされていないデバイスに関するフィードバック**：デバイスが正常に動作しない場合は、フィードバックを提供してください。サポートを提供するか、今後のバージョンにそのデバイスを含めるようにします。

3. **テスト用デバイスの共有**：新しいデバイスをテストする最良の方法は、X-Sense アプリを介してデバイスを共有することです。これにより、できるだけ多くのデバイスがサポートされるようになります。

4. **コミュニティサポート**：コミュニティでの議論に参加してください。改善の提案でも、他のユーザーを支援することでも、すべてのサポートは大歓迎です！

ディスカッションとサポートに関しては、私たちの Discord サーバーに参加するか、Home Assistant フォーラムにアクセスしてください：

[Discord](https://discord.gg/5phHHgGb3V)

[フォーラム](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)

## 完全なリファレンス

### アカウントとインストール
- Home Assistant 用に別の X-Sense アカウントを使用してください。
- メインの X-Sense アカウントからは対応デバイスのみを共有してください。
- ペアリング、削除、共有、ファームウェア、アカウント、支払い、SD カード管理は X-Sense アプリに残します。

### 更新と API 使用
- すばやい状態変化は MQTT shadow メッセージで受信します。
- クラウド要求はログイン、デバイス検出、カメラデータ、状態復旧に使用します。
- 定期ポーリングはライブ更新を逃した場合のバックアップです。

### エンティティ、カメラ、トラブルシューティング
- エンティティは X-Sense が実際に報告するフィールドに対してのみ作成されます。
- カメラのエンティティと操作は、Android アプリ準拠の API がそのアカウントとモデルで対応を報告した場合のみ作成されます。
- 値がない場合は、まず X-Sense アプリと比較し、その後 Home Assistant の診断情報と関連ログを添付してください。

## デバイスとエンティティのチェックリスト

### 主なデバイスファミリー
- SBS50 ベースステーション、XS 煙感知器、XC CO 検知器、SC/XP 複合検知器、XH 熱感知器、SWS 水漏れセンサー、STH 温湿度センサー、SDS ドアセンサー、SMS モーションセンサー、SSC カメラ、その他 API がフィールドを公開する X-Sense ファミリーを処理します。

### 状態フィールド
- アラーム、ミュート、バッテリー、RF/Wi-Fi 信号、温度、湿度、CO、水、動き、ドア、ライト、リマインダー、警告、読みやすい時刻は X-Sense が報告した場合のみ表示されます。

### 操作と報告
- スイッチ、セレクト、数値、ボタンはデバイス/アカウントが公開する書き込み可能な設定と操作に対してのみ作成されます。
- 良いバグ報告には、正確なモデル、統合バージョン、診断情報、ログ、X-Sense アプリで値が正しく変化するかを含めてください。
