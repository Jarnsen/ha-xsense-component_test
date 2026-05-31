# ha-xsense-component_test

<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## 概要
この Home Assistant 統合により、X-Sense デバイスをスマートホームシステムに統合することができます。この統合は [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) のオリジナルコードに基づいて作成され、彼の許可と協力のもとで公開されました。

Theo による公式な Home Assistant 統合が提供されるまで、この HACS 統合を使用します。この統合は、新機能の追加や既存の問題の解決を目的として定期的に更新されます。この統合により、ユーザーは簡単に X-Sense デバイスを Home Assistant に統合し、さまざまな自動化や監視に利用することができます。

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

![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/9cc18693-5f37-49c5-a67d-22602fa7eef5)

____________________________________________________________

## HACS からのインストール
1. **Home Assistant で HACS を開く**：
   HACS は Home Assistant の重要な拡張機能で、カスタム統合のインストールを簡単に行うことができます。

   ![Download (1)](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/3220c686-f53f-4766-9523-e3272a6ff104)

2. **カスタムリポジトリに移動**：
   HACS ダッシュボードの設定に移動し、このリポジトリをカスタムソースとして追加します。

3. **リポジトリを追加**：
   リポジトリの URL を入力します：`https://github.com/Jarnsen/ha-xsense-component_test`

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c23cf0-a212-4889-8d08-f995ff2fd5d7)

4. **統合をダウンロードしてインストール**：
   HACS で統合を検索し、ダウンロードしてインストールします。インストール後、Home Assistant インターフェースを介して設定が行えます。

   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/5bd2d567-6568-47c5-a45e-6af7228ff30e)
   
   ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/33cd7bfa-eec2-44f5-af30-4f21269f0081)

____________________________________________________________

## 設定
インストール後、統合を正しく設定するために基本的な設定が必要です：
- **ユーザー名とパスワード**：新しく作成した X-Sense アカウントの認証情報を使用して接続を確立します。

    ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)
  
- **デバイス概要**：設定が成功すると、共有されたデバイスが Home Assistant で利用可能になり、自動化に使用できます。

    ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)
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
- **その他のステーション接続デバイス**: ライト、キーパッド、メールボックス、listener、 driveway alarm、smart drop、リモコン、ラドンデータは、API が対応フィールドを報告する場合に表示されます。

### 利用可能なエンティティと操作
この統合は、X-Sense クラウド、MQTT shadow payload、または Android アプリの挙動に合わせたカメラ API に実際に存在するフィールドに対してのみ Home Assistant エンティティを作成します。デバイスによって、次のようなものが含まれます。

- alarm、mute、end-of-life、AC-break、水漏れアラーム、温度アラーム、充電、モーション、ドア、armed 状態、warning、reminder、light、PIR、keypad 状態のバイナリセンサー。
- battery、RF signal、Wi-Fi signal、firmware、temperature、humidity、CO level、CO peak、alarm volume、voice volume、chirp volume、reminder volume、warning thresholds、mute timers、読みやすい timestamps、timezone、serial number、MAC address、その他の診断センサー。
- X-Sense が対応を報告する書き込み可能な設定用スイッチ。例: LED light、alarm enablement、continued alarm、chirp tone、reminders、PIR、sunshine/white light、await、keypad sound、camera motion detection、recording、night vision、audio、cooldown、light、doorbell controls。
- language、recording resolution、codec、anti-flicker rate、motion sensitivity、video length、volume、alarm duration、cooldown、night threshold、doorbell ring key など、対応するカメラ設定用の select と number エンティティ。
- X-Sense アプリが該当モデルで対応操作を提供している場合の test、mute、fire-drill、camera wake ボタン。

一部のエンティティは診断または設定関連であり、Home Assistant でもそのように分類されます。デバイスが特定のフィールドを報告しない場合、または X-Sense アプリがそのデバイス/アカウントで機能非対応と示す場合、対応するエンティティは作成されません。デバイスの追加、削除、共有、アカウント、支払い、firmware 更新、SD カード初期化、その他の管理操作は X-Sense アプリ側に残ります。
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
      entity_id: sensor.xsense_temperature
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
