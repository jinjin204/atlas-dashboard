# タスクリスト

- [x] `production_logic.py` の NameError 修正
- [x] Drive 連携バグ修正（mimeType 判定 + bare except）
- [x] `production_master.json` の物理的生成（31件, 25921 bytes）
- [x] イベントシート `target_quantity` 統合
    - [x] メニュー.xlsx のシート構成確認（26シート）
    - [x] `master_loader.py` に `merge_event_targets` 関数追加
    - [x] `drive_utils.py` の戻り値を4つ組に拡張
    - [x] `app.py` にドロップダウンUI + マージ処理追加
    - [x] 動作確認（クリマ2605: 27件マージ、26商品にtarget_quantity付与）
