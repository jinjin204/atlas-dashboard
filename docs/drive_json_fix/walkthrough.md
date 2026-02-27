# Walkthrough: Drive連携修正 & イベントシート target_quantity 統合

## Phase 1: Drive連携バグ修正

### 発見した根本原因

`data/production_master.json` が生成されない原因は **2つのバグの複合** でした：

| # | バグ | 影響 |
|---|---|---|
| 1 | `download_content` で `'spreadsheet' in mime_type` が xlsx にもマッチ | xlsx → `export_media` → **403 fileNotExportable** |
| 2 | `bare except` でエラー握り潰し | 403 が `None` を返し、原因不明のまま失敗 |

### 修正内容 ([drive_utils.py](file:///c:/Users/yjing/.gemini/atlas-hub/logic/drive_utils.py))

```diff
- if 'spreadsheet' in mime_type:   # xlsx にもマッチしてしまう
+ if mime_type == 'application/vnd.google-apps.spreadsheet':  # Google Sheets 限定

- except:           # エラー握り潰し
+ except Exception as e:   # エラーを明示出力
```

追加修正: `find_file` で `~$メニュー.xlsx` (Excel一時ファイル) を除外

### 検証結果
- `production_master.json`: ✅ 25,921 bytes / 31件の正規データ

---

## Phase 2: イベントシート target_quantity 統合

### 設計方針
- **デフォルト**: シートリストの先頭（最新イベント）を自動選択
- **UIドロップダウン**: サイドバーでイベント切り替え可能
- **除外**: `商品マスタ`, `データ構造`, `Sheet2` はイベント候補から除外

### 修正ファイル

| ファイル | 変更内容 |
|---|---|
| [drive_utils.py](file:///c:/Users/yjing/.gemini/atlas-hub/logic/drive_utils.py) | `load_data_from_drive` を4つ組 `(master_df, log_df, event_sheets, excel_bytes)` に拡張 |
| [master_loader.py](file:///c:/Users/yjing/.gemini/atlas-hub/logic/master_loader.py) | `merge_event_targets` 関数追加（ID→目標個数マッピング→master_listにマージ） |
| [app.py](file:///c:/Users/yjing/.gemini/atlas-hub/app.py) | ドロップダウンUI + マージ処理追加 |

### 検証結果（クリマ2605）
```
[merge_event] Merged 27 targets from 'クリマ2605'
  斧　大: target=5, stock=1, remaining=4
  ロト剣: target=11, stock=2, remaining=9
  伝説剣　長: target=11, stock=6, remaining=5
  伝説剣　短: target=10, stock=2, remaining=8
```
