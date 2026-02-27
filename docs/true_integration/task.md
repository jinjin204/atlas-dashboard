# Atlas Hub「真の統合」タスクリスト

## Phase 0: デバッグ修復 ✅
- [x] `logic.js` 構造破損修復
- [x] `index.html` onerror修復 + データガードレール
- [x] `app.py` Python側バリデーション
- [x] `skill.md` / `仕様書.md` 更新

## Phase 1: 在庫書き戻しパイプラインの接続 ✅
- [x] `drive_utils.py` に `find_file_by_partial_name()` 実装
- [x] `drive_utils.py` に `update_file_content()` 実装
- [x] `drive_utils.py` に `download_file_content()` 実装
- [x] `drive_utils.py` に `get_file_modified_time()` 実装
- [x] `inventory.py` の `update_master_inventory()` に楽観的ロック追加

## Phase 2: 在庫確定 UI (カレンダー連動) ✅
- [x] `app.py` にStockタブ追加（高/低信頼度の確認キュー）
- [x] `st.button("在庫確定")` → `update_master_inventory()` 接続
- [x] 操作ログ表示 (変更前→変更後)
- [x] キャッシュクリア & balloons

## Phase 3: Atlas 入力タブの統合 ✅
- [x] `app.py` に Input タブ追加
- [x] `atlas/index.html` を iframe で埋め込み
- [x] 不在時のフォールバックメッセージ

## Phase 4: Stock (在庫照会) タブ ✅
- [x] 在庫一覧テーブル表示
- [x] 高/低信頼度の分離表示

## Phase 5: ドキュメント最終更新 ✅
- [x] `仕様書.md` にパイプライン仕様・在庫連動プロトコル追記
- [x] `skill.md` にパイプライン完全性規律追記
- [x] `rules.md` にデータパイプライン・ルール & No White Screen ルール追記

## 未完了: ブラウザ動作確認
- [ ] `streamlit run app.py` → 5タブ表示確認
- [ ] Stockタブ → 在庫確定ボタン動作確認
