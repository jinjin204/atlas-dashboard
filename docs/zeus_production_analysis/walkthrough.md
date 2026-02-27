# ウォークスルー: 動作フロー仕様に基づく master_loader.py / zeus_chat.py 全面改修

## 変更概要

### Phase 1: [master_loader.py](file:///c:/Users/yjing/.gemini/atlas-hub/logic/master_loader.py) の改修

| 変更 | 内容 |
|------|------|
| `_import_initial_from_note()` 新規追加 | 備考テキスト（例: "クリマ2512 AK列"）をパースし、指定シート・列から初期在庫を自動インポート |
| `col_map` に `note`/`loadin` 追加 | イベントマスタの備考列・搬入列を自動検出 |
| Active判定の復元 | `_is_true('active')` のNoneチェック追加 |
| `details` 確実記録 | `history_data` 初期化時に `details: {}` を含め、全アイテムのIDごとの個数を必ず記録 |

### Phase 2: [zeus_chat.py](file:///c:/Users/yjing/.gemini/atlas-hub/logic/zeus_chat.py) の改修

| 変更 | 内容 |
|------|------|
| `load_history_stats()` | 全ログの通算ペースを基本とし、直近2点間が正常値なら採用する二段構え方式に改修 |
| `get_daily_achievements()` | `details` 付きエントリのみを有効とし、古い形式のエントリをスキップ。「最新 vs 直前」の比較に統一 |
| `build_system_prompt()` 予測ロジック | ペースベース残日数 vs 工数ベース残日数の保守的（遅い方）を採用。期限超過日数の具体的表示を追加 |

### Phase 3: テスト修正

[verify_zeus_logic.py](file:///c:/Users/yjing/.gemini/atlas-hub/tests/verify_zeus_logic.py) のアサーションを新しいプロンプト構造に合わせて更新。

## テスト結果

| テスト | 結果 |
|--------|------|
| 構文チェック (py_compile) | ✅ PASS |
| verify_zeus_logic (2件) | ✅ PASS |
| test_master_loader | ⏭ SKIP (pytest 未インストール) |

## 残作業

- **Drive同期 & スキャン実行**: Streamlit アプリを起動して「軍師Zeus」タブで「進捗報告」と入力し、本日の成果・平均ペース・完了予定日が正しく報告されることを確認
