# Walkthrough: 生産管理BIダッシュボード

## 変更概要

Atlas-hubに「📊 BI Dashboard」ページを新規追加。`production_master.json`（JOIN済データ）を活用し、スマホ最適化された6つのKPIカードを表示する。

## 作成・変更ファイル

| ファイル | 操作 | 内容 |
|---|---|---|
| [bi_dashboard.py](file:///c:/Users/yjing/.gemini/atlas-hub/logic/bi_dashboard.py) | 新規 | 6つのKPI計算関数 |
| [app.py](file:///c:/Users/yjing/.gemini/atlas-hub/app.py) | 変更 | 新ページ追加、スマホCSS、import |
| [test_bi_dashboard.py](file:///c:/Users/yjing/.gemini/atlas-hub/tests/test_bi_dashboard.py) | 新規 | 14件のユニットテスト |

## 6つのKPI

| # | KPI | データソース | UI |
|---|---|---|---|
| 1 | 🗓️ イベントカウントダウン | `event_master.json` (is_active=true) | グラデーション紫カード + 残日数大文字 |
| 2 | 💰 目標売上ギャップ | `price × target_quantity` vs `price × event_sheet_stock` | プログレスバー + 金額表示 |
| 3 | ⏱️ 残り加工時間 | `remaining × (NC+手作業)` | st.metric 2列 + 効率ランキング |
| 4 | 📋 本日タスク | 時間帯判定(20時以降=夜間) | Go/No-Go カード + 推奨アイテム |
| 5 | 🪵 材料アラート | `remaining / yield` で板数算出 | 材料種別カード + ⚠️ 警告 |
| 6 | 🆕 新作開発枠 | 進捗率50%以上 & 残30日以上 | 🟢OK / 🔴NG カード |

## app.py の変更箇所

render_diffs(file:///c:/Users/yjing/.gemini/atlas-hub/app.py)

## テスト結果

- **pytest**: 全14テスト PASSED ✅
- **py_compile**: `app.py`, `bi_dashboard.py` ともに構文エラーなし ✅

## 起動方法

```bash
cd c:\Users\yjing\.gemini\atlas-hub
.\venv\Scripts\streamlit.exe run app.py
```

サイドバーの先頭に「📊 BI Dashboard」が表示されます。
