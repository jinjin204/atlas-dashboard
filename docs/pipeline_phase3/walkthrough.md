# Walkthrough - Phase 3 & Real Data Restoration

Intermediate CSV廃止と、メモリ上でのデータ結合による `production_master.json` 生成フローの実装、および実データへの復元が完了しました。
ご指摘いただいた `TypeError` (unexpected keyword argument 'excel_bytes') についても、関数のシグネチャ修正とモジュールリロード処理の追加により解消しています。

## Changes

### 1. `logic/master_loader.py` (Backend)

- **[FIX]** `convert_dataframe_to_json` 関数
    - `excel_bytes=None` 引数を明示的に定義に追加。
    - `INTEGRATION.md` の通り、内部で `merge_event_targets` を呼び出し、イベント目標数を合算します。

### 2. `app.py` (Frontend/Controller)

- **[FIX]** 不要なマージ呼び出しの削除
    - `convert_dataframe_to_json` 一本化に伴い、古い `merge_event_targets` 呼び出しブロックを削除。
- **[NEW]** モジュールリロードの強化
    - `importlib.reload(logic.master_loader)` を追加し、修正が確実に反映されるようにしました。

## Verification Results

### Real Data Restoration (production_master.json)

テスト用ダミーデータを破棄し、実データ（メニュー.xlsx）から再構築しました。

- **Status**: ✅ 復元完了
- **Item Count**: 31 items
- **Sample**:
    - `AX_AXE_L_BDY`: Target 5 (クリマ2605)
    - `SW_LOTO_SCB`: Target 11 (クリマ2605)

### Error Resolution

- **Test Script**: `tests/test_phase3.py`
    - `convert_dataframe_to_json(..., excel_bytes=...)` の呼び出しが成功することを確認済み。
- **INTEGRATION.md**: 実装が最新の設計図と一致しています。
