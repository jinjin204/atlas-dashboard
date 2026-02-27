# Atlas Hub「真の統合」タスクリスト

## Phase 0: デバッグ修復 ✅
- [x] `logic.js` 構造破損修復
- [x] `index.html` onerror修復 + データガードレール
- [x] `app.py` Python側バリデーション

## Phase 1: 在庫書き戻しパイプラインの接続 ✅
- [x] `drive_utils.py` に `find_file_by_partial_name` 等の実装
- [x] `inventory.py` の `update_master_inventory` 実装(旧)

## Phase 2: 在庫確定 UI (カレンダー連動) ✅
- [x] `app.py` にStockタブ追加
- [x] `st.button` 接続

## Phase 3: Atlas 入力タブの統合 ✅
- [x] `app.py` に Input タブ追加
- [x] `atlas/index.html` iframe埋め込み

## Phase 4: Stock (在庫照会) タブ ✅
- [x] 在庫一覧テーブル表示

## Phase 5: イベントソーシング移行 ✅
- [x] `drive_utils.py` に `append_to_confirmed_log` (CSV版) 実装
- [x] `inventory.py` を `confirm_production` (Append-Only) に書き換え
- [x] `app.py` Stockタブを新方式に接続
- [x] Sheets APIエラー(403)回避のためローカルCSVにフォールバック

## Phase 6: トレーサビリティ & 二重確定防止 ✅
- [x] `production_logic.py`: `SOURCE_ROWS` (行番号) と `ATLAS_TIMESTAMP` を抽出
- [x] `drive_utils.py`: CSVヘッダーに `ATLAS_TIMESTAMP` 追加
- [x] `app.py`: 確定済み行の除外フィルタ実装

## Phase 7: データ構造強化 & UX改善 (New!) ✅
- [x] `production_logic.py`: `SOURCE_HASHES` (SHA256) 生成ロジック実装
- [x] `drive_utils.py`: CSVヘッダーを `SOURCE_ROWS` から `SOURCE_HASHES` に変更
- [x] `app.py`: `st.tabs` を廃止し `st.sidebar.radio` + `session_state` に変更 (タブ維持)
- [x] `app.py`: HashベースのDedupロジック実装

## Phase 8: ドキュメント更新 ✅
- [x] `仕様書.md` にパイプライン仕様追記
- [x] `rules.md`, `skill.md` 更新
