# アトラス戦略機能拡張 - 実装計画書

## ゴール
`master_loader.py` を拡張し、イベントマスタの「二重フラグ（Double Flag）」システム（アクティブ/表示）に対応させる。

- **アクティブフラグ (Active Flag)**: 生産目標の合算対象となるイベントを決定する（進軍指示）。
- **表示フラグ (Display Flag)**: Zeusが監視し、締め切り（応募期限など）やステータスを報告する対象となるイベントを決定する（監視・広報）。

`zeus_chat.py` を更新し、この情報を活用して、Zeusが「作業の集中」と「締め切りの監視」を両立できるようにする。

## ユーザー確認事項
- **カラム名**: マスタデータのカラム名を以下と仮定して実装します。実際のExcelと異なる場合は修正が必要です。
    - アクティブフラグ: `アクティブ`, `Active`
    - 表示フラグ: `表示`, `Display`
    - 締め切り: `応募締切`, `Deadline`
    - 開催日: `開催日`, `Date`
    - 会場: `会場`, `Venue`
    - ブース: `ブース`, `Booth`
    - 搬入: `搬入`, `LoadIn`
- **新規JSONファイル**: Zeus用のイベントメタデータを格納するために `data/event_master.json` を新規作成します。既存の `production_master.json` の構造を大きく変えずに済むため、フロントエンドへの影響を最小限に抑えられます。

## 変更内容

### ロジックコンポーネント

#### [MODIFY] [master_loader.py](file:///c:/Users/yjing/.gemini/atlas-hub/logic/master_loader.py)
- `merge_event_targets` 関数を更新:
    - 「アクティブ」および「表示」カラムをスキャンするように変更。
    - メタデータカラム（応募締切、開催日、会場など）も取得。
    - **アクティブフラグ** が立っているイベントのみを生産目標の合算対象（`target_sheets`）とする。
    - **表示フラグ** が立っているイベントをすべて収集し、`event_list` としてまとめる。
    - `event_list` を `data/event_master.json` に保存する処理を追加。

#### [MODIFY] [zeus_chat.py](file:///c:/Users/yjing/.gemini/atlas-hub/logic/zeus_chat.py)
- `load_event_master()` 関数を追加し、`data/event_master.json` を読み込む。
- `build_system_prompt` 関数を更新:
    - コンテキストに「監視対象イベントリスト（表示フラグONのイベント）」を注入。
    - Zeusへの指示を追加:
        - アクティブなイベントについては、生産進捗・残作業時間を報告する。
        - 表示フラグが立っているイベントについては、特に「応募締切」などの期限を監視し、必要に応じてユーザーに注意喚起を行う。

## 検証計画

### 自動テスト
- `master_loader.py` を実行（`check_env.py` または直接実行）し、以下を確認:
    - `production_master.json`: アクティブなイベントの目標のみが合算されていること。
    - `data/event_master.json`: 表示対象イベントのリスト（締め切り情報含む）が正しく生成されていること。
- スクリプトで `zeus_chat.build_system_prompt` を呼び出し、生成されたプロンプトに新しいコンテキスト（監視イベント情報）が含まれているか確認。

### 手動検証
- 修正後のコードを実行。
- 生成されたJSONファイルを目視確認。
- Zeusの応答（シミュレーション）を確認し、期限に関する言及が含まれるかチェック。
