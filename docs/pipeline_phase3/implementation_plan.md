# Implementation Plan - Phase 3: In-Memory Master Data Processing

## Goal
`PIPELINE.md` Phase 3 に従い、マスターデータの処理フローを改善する。
現在は `drive_utils.py` がExcelをダウンロードし、中間CSVファイルを経由（あるいは意図せず経由）して `master_loader.py` がJSONを作成している可能性がある。
これを、メモリ上のデータ(`DataFrame`, `bytes`)を直接受け渡して `production_master.json` を生成するフローに変更し、ディスクI/Oを削減すると同時に、情報の欠落（詳細工数など）を防ぐ。

## User Review Required
- 特になし（内部ロジックの変更）

## Proposed Changes

### 1. `logic/master_loader.py`
- 新しいエントリーポイント関数 `process_master_data_from_memory(master_df, excel_bytes)` を追加 (または既存を改修)。
    - `convert_dataframe_to_json` で `master_df` を `master_list` に変換。
    - `merge_event_targets` で `excel_bytes` (個別イベントシート含む) から目標数をマージ。
    - 最終的なリストを `production_master.json` に保存。
- 既存の `convert_csv_to_json` はバックワード互換性のため残すが、メインフローからは外す。

### 2. `app.py` (Main Application)
- `load_data_from_drive` の戻り値を受け取った後、`master_loader.process_master_data_from_memory` を呼び出すように変更。
- 既存のCSV読み込み依存コードを削除/無効化。

### 3. `logic/drive_utils.py`
- 変更なし (既に `master_df` と `excel_bytes` を返しているため)。
- 必要であれば、データ型や戻り値の確認を行う。

## Verification Plan

### Automated Tests
- 再現スクリプト `reproduce_phase3.py` を作成。
    - モック(または実際のファイル)の `excel_bytes` と `master_df` を作成。
    - `master_loader` の新関数に渡す。
    - 生成された `production_master.json` を読み込み、以下の点を検証する。
        - "Dragon Plate" (ID: 存在するID) の `target_quantity` が 2 になっているか。
        - `process` (詳細工数) が正しく含まれているか。
        - 処理がエラーなく完了するか。

### Manual Verification
- `app.py` を起動し、"Reload Data" (もしあれば) または起動時のロードでエラーが出ないことを確認。
- アプリ上の表示で目標数や工数が反映されているか確認。
