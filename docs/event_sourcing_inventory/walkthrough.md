# UX改善 & データ構造強化 ウォークスルー

## 1. UX改善: タブ状態の維持 (Navigation)
`st.tabs` のリセット問題を解決するため、**「サイドバーメニュー (`st.sidebar.radio`)」** に構造を変更しました。
- **効果**: 確定ボタンを押して `st.rerun()` しても、`session_state["current_page"]` により「Stock画面」に留まり続けます。
- **操作**: 左側のサイドバーから画面を切り替えます。

## 2. データ構造の強化 (Integrity: Hash Base)
脆弱な「行番号」への依存を排除し、**「ログ内容のSHA256ハッシュ」** をキーに採用しました。

| 旧仕様 (Row Index) | 新仕様 (SHA256 Hash) |
|---|---|
| `33,34` | `a1b2c3d4...` |
| 行の増減でズレる | 内容が変わらない限り不変 (堅牢) |
| データクレンジングに弱い | データクレンジングに強い |

## 3. テトリス予測への基盤 (Time Tracking)
`ATLAS_TIMESTAMP` (加工完了時刻) を記録することで、実績時間の分析が可能になりました。
将来的に「Product A の平均加工時間は 45分」といった **標準時間(SPT)** を算出し、残り時間と比較する「テトリス型キャパシティ管理」へ発展させられます。

## 変更ファイル

| ファイル | 変更内容 |
|---|---|
| [app.py](file:///c:/Users/yjing/.gemini/atlas-hub/app.py) | `st.tabs` → `st.sidebar.radio` 変更、HashベースのDedup実装、`st.session_state` 制御 |
| [production_logic.py](file:///c:/Users/yjing/.gemini/atlas-hub/logic/production_logic.py) | `hash_row()` 追加、`SOURCE_HASHES` 生成ロジック実装 |
| [drive_utils.py](file:///c:/Users/yjing/.gemini/atlas-hub/logic/drive_utils.py) | CSVヘッダー変更 (`SOURCE_ROWS` → `SOURCE_HASHES`) |
| [inventory.py](file:///c:/Users/yjing/.gemini/atlas-hub/logic/inventory.py) | 引数変更 (`source_rows` → `source_hashes`) |

## CSVスキーマ (最終版 v2)

```
TIMESTAMP,PROJECT,PART,ACTION,SOURCE_HASHES,ATLAS_TIMESTAMP
2026/02/10 23:55:00,勇者の剣,本体,PRODUCED,"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",2026/02/09 14:00:00
```
