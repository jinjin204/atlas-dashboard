# ウォークスルー: zeus_chat.py 抜本改修

## 改修対象
[zeus_chat.py](file:///c:/Users/yjing/.gemini/atlas-hub/logic/zeus_chat.py)

---

## 変更内容

### 1. `load_history_stats()` — 起点日の動的取得

| 項目 | 旧 | 新 |
|------|-----|-----|
| 起点 | `valid[0]`（最古エントリ） | `type: "initial"` のエントリを優先検索 |
| ペース | `(最新 - 最古) / (最新日 - 最古日)` | `(最新 - initial) / (今日 - 起点日)` |
| 返却値 | pace, last_count, last_date, is_long_term | + `origin_date`, `origin_count`, `origin_details` |

### 2. `build_system_prompt()` — プロンプト構造改革

````carousel
**旧構造:**
```
本日の日付
→ ペルソナ設定
→ ガイドライン
→ [全体状況] (ハードコード期限 2026-05-05)
→ [監視イベント] (Python加工済み)
→ [商品マスタ]
→ [在庫]
→ 禁止事項
```
<!-- slide -->
**新構造 (仕様書準拠):**
```
## 日付情報 (今日/起点日/経過日数)
## Python確定サマリー (計算済み数値)
## IDベース マージ結果
→ ペルソナ設定
→ ガイドライン (再計算禁止ルール追加)
→ [商品マスタ]
→ [在庫]
## event_master.json Raw JSON
→ 禁止事項
```
````

### 3. 主な改善点

- **ハードコード日付の排除**: 期限をアクティブイベントの`date`から動的取得（フォールバック: 2026-05-05）
- **IDベースマージ**: `production_master` × `history_summary[initial]` の精密マージ結果をプロンプトに注入
- **event_master Raw注入**: Python側での加工を完全撤廃。JSON生データとしてAIに渡し、解釈はAI側に委譲
- **計算禁止ルール**: AIに対して「Python確定サマリーを信頼せよ、再計算するな」を明記

---

## テスト結果

```
Ran 2 tests in 0.193s
OK
```

- `test_merge_event_targets_and_history` → ✅ PASS
- `test_zeus_chat_logic` → ✅ PASS

---

## 次のステップ

Streamlitを起動 → 「軍師Zeus」タブ → 「進捗報告」と入力 → 以下を確認:
1. 日付ヘッダー（今日/起点日/経過日数）が正確か
2. 確定サマリーの数値が妥当か
3. event_master生データが表示されているか（コンソールログで確認）
