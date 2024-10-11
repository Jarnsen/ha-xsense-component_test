# ha-xsense-component_test

<p align="center">
<img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

## 概要
この Home Assistant 統合により、Xsense デバイスをスマートホームシステムに統合することができます。この統合は [Theo Snel](https://github.com/theosnel/homeassistant-core/tree/xsense/homeassistant/components/xsense) のオリジナルコードに基づいて作成され、彼の許可と協力のもとで公開されました。

Theo による公式な Home Assistant 統合が提供されるまで、この HACS 統合を使用します。この統合は、新機能の追加や既存の問題の解決を目的として定期的に更新されます。この統合により、ユーザーは簡単に Xsense デバイスを Home Assistant に統合し、さまざまな自動化や監視に利用することができます。

![images](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/c49a97f2-5e10-4129-82bc-1d647adc0895)

## 機能
- Xsense デバイスを Home Assistant に統合します。
- Xsense センサーのデータを使用した自動化をサポートします。
- 次のデバイスタイプをサポートします：ベースステーション、煙検知器、一酸化炭素検知器、熱アラーム、水漏れ検知器、湿度計。
- HACS（Home Assistant Community Store）を通じて簡単に設定できます。

## 必要条件
- 正常に動作する Home Assistant サーバー（最新バージョン推奨）。
- サポートされているデバイスを持つ Xsense アカウント。
- この統合をインストールするには、Home Assistant に HACS がインストールされている必要があります。

## チュートリアル動画
インストールと統合の設定に関する詳細なガイドについては、以下のビデオをご覧ください：

[![X-Sense Home Assistant Integration](https://img.youtube.com/vi/3CCKK-qX-YA/0.jpg)](https://www.youtube.com/watch?v=3CCKK-qX-YA)

____________________________________________________________

## 準備
統合をインストールする前に、いくつかの準備が必要です：

- **Xsense アプリで 2 番目のアカウントを作成（Home Assistant 用）**：同じアカウントでアプリと Home Assistant に同時にログインすることはできないため、Home Assistant 用に別のアカウントを使用することをお勧めします。これにより、アプリと Home Assistant との間で頻繁にログアウトすることを防ぎます。追加のアカウントにより、シームレスな統合と継続的な使用が可能になり、頻繁なログインとログアウトによる中断がなくなります。

- **メインアカウントから Home Assistant アカウントにサポートされているデバイスを共有**：Xsense アプリを使用して、新しく作成したアカウントと **サポートされているデバイスのみ** を共有します。これにより、メインアカウントを通じてデバイスを管理しながら、Home Assistant で簡単に統合を使用できます。

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
- **ユーザー名とパスワード**：新しく作成した Xsense アカウントの認証情報を使用して接続を確立します。

    ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/48c5e923-a6a0-4a47-8f26-8ef3954ea34b)
  
- **デバイス概要**：設定が成功すると、共有されたデバイスが Home Assistant で利用可能になり、自動化に使用できます。

    ![image](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/42b33b6b-ecd9-45f6-99fc-314a0abd9bbe)
## Home Assistant での表示
インストールと設定が成功すると、Home Assistant で統合が表示されます。デバイスはダッシュボードに表示され、自動化、通知、その他の用途に使用できます。

![フォーラム](https://github.com/Elwinmage/ha-xsense-component/assets/15807572/2d271b78-39d9-4bbd-837d-8593cf1933bd)

____________________________________________________________

## サポートされているデバイス
この統合は、さまざまな Xsense デバイスをサポートしています。以下は現在確認されているテスト済みのデバイスのリストです：
- **ベースステーション (SBS50)**：Xsense デバイスの中央ハブ。
- **熱アラーム (XH02-M)**：異常に高い温度を検出します。
- **一酸化炭素アラーム (XC01-M; XC04-WX)**：危険な一酸化炭素濃度を検出します。
- **煙検知器 (XS01-M, WX; XS03-WX; XS0B-MR)**：早期に煙を検出します。
- **一酸化炭素と煙のコンボアラーム (SC07-WX; XP0A-MR (部分的にサポート))**：一酸化炭素と煙の両方を検出するためのコンボデバイス。
- **水漏れ検知器 (SWS51)**：不要な場所に水があることを検出します。
- **湿度計-温度計 (STH51)**：温度と湿度を監視します。

これらのデバイスは、Home Assistant に統合された後、自動化と警報の作成に使用できます。

____________________________________________________________

## 自動化の例
この統合を使用すると、さまざまな自動化を作成できます。以下はいくつかの例です：

### 例 1：温度警告
Xsense 温度計の温度が高すぎる場合、通知が送信されます：

```yaml
automation:
  - alias: "Xsense 温度警告"
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

1. **デバイステスト**：Xsense デバイスを持っていて、この統合と互換性がある場合は、それをお知らせください。サポートされているデバイスのリストに追加します。

2. **サポートされていないデバイスに関するフィードバック**：デバイスが正常に動作しない場合は、フィードバックを提供してください。サポートを提供するか、今後のバージョンにそのデバイスを含めるようにします。

3. **テスト用デバイスの共有**：新しいデバイスをテストする最良の方法は、Xsense アプリを介してデバイスを共有することです。これにより、できるだけ多くのデバイスがサポートされるようになります。

4. **コミュニティサポート**：コミュニティでの議論に参加してください。改善の提案でも、他のユーザーを支援することでも、すべてのサポートは大歓迎です！

ディスカッションとサポートに関しては、私たちの Discord サーバーに参加するか、Home Assistant フォーラムにアクセスしてください：

[Discord](https://discord.gg/5phHHgGb3V)

[フォーラム](https://community.home-assistant.io/t/x-sense-security-is-it-possible-to-create-an-integration/534119/110)
