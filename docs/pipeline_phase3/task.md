# Task List

- [x] 現状の確認と設計
    - [x] `master_loader.py`, `drive_utils.py`, `PIPELINE.md` のコード解析
    - [x] `app.py` の確認
    - [x] Phase 3 の要件に基づいたデータフローの設計
- [x] 実装 (Execution)
    - [x] `tests/test_phase3.py`: 再現/検証用スクリプトの作成 & 実行
    - [x] `master_loader.py`: `convert_dataframe_to_json` に `excel_bytes` 引数を追加し、内部で `merge_event_targets` を呼ぶ (再修正: TypeError対応)
        - [x] 引数 `excel_bytes` の追加確認
    - [x] `app.py`: `convert_dataframe_to_json` 呼び出し時に `excel_bytes` を渡す
    - [x] `app.py`: 重複していた `merge_event_targets` 呼び出しを削除
    - [x] `app.py`: `logic.master_loader` のリロード処理を追加 (キャッシュ対策)
- [x] 検証 (Verification)
    - [x] `tests/test_phase3.py` の修正と実行 (TypeError解消確認)
    - [x] `production_master.json` の内容確認（実在する31商品: 再取得による復元）
    - [x] アプリ起動確認 (コード上の不整合なし)
