# 生産管理BIダッシュボード実装計画

Atlas-hubに新しいページ「📊 BI Dashboard」を追加し、スマホ最適化された生産管理BIダッシュボードを構築する。`production_master.json`（=商品マスタ×イベントシートのJOIN済データ）を活用し、6つのKPI項目をStreamlit UIで表示する。

## 設計方針

### データソース

既存の `production_master.json` は、`merge_event_targets` 関数内で **商品マスタ** と **アクティブイベントシート**（クリマ2605）が `ID` を基準にJOIN済みであり、各アイテムに以下が含まれている：
- `target_quantity`（目標数）、`event_sheet_stock`（イベントシート在庫）、`remaining`（残数）
- `process.nc.*`（NC加工時間4工程）、`process.manual.*`（手作業時間4工程）
- `process.prep.*`（生地準備）、`process.assembly.*`（組付工程）
- `price`（単価）、`requirements.yield`（取数）

→ **新たなJOIN処理は不要**。既存パイプラインが起動時に自動実行するため、`st.session_state['master_data']` をそのまま利用する。

### `event_master.json` からのイベント情報

アクティブイベント：`クリエーターズマーケット54`（2026-05-05開催）

---

## 提案する変更内容

### ロジックモジュール

#### [NEW] [bi_dashboard.py](file:///c:/Users/yjing/.gemini/atlas-hub/logic/bi_dashboard.py)

ダッシュボード専用の計算ロジックを集約。以下の関数を作成：

1. **`calc_countdown(event_master)`** → 残り日数、イベント名
2. **`calc_sales_gap(master_data)`** → 目標売上, 現在完成額, 進捗率
3. **`calc_remaining_hours(master_data)`** → 残り総時間(NC/手作業別), アイテム別効率ランキング
4. **`calc_today_tasks(master_data, current_hour)`** → 本日推奨タスクリスト（20時以降の深夜モード判定含む）
5. **`calc_material_alerts(master_data, daily_pace, days_remaining)`** → 材料消費予測アラート
6. **`calc_dev_slot(progress_ratio, days_remaining)`** → 新作開発余裕判定

### アプリケーション本体

#### [MODIFY] [app.py](file:///c:/Users/yjing/.gemini/atlas-hub/app.py)

- `PAGES` リストに `"📊 BI Dashboard"` を追加（L210付近）
- 新しい `elif selection == "📊 BI Dashboard":` ブロックを追加
- スマホ最適化CSS（`max-width`, 大きめフォント、カード型レイアウト）を追記

---

## 6つのKPI項目の実装詳細

### 1. イベントカウントダウン 🗓️
- `event_master.json` のアクティブイベント日付から `(event_date - now).days` を算出
- `st.metric(label="イベントまで", value=f"{days}日")` で大文字表示

### 2. 目標売上ギャップ 💰
- 目標額 = `Σ(target_quantity × price)`（本体のみ、鞘は price=0 のため自動除外）
- 現在完成額 = `Σ(event_sheet_stock × price)`
- `st.progress(完成額/目標額)` + `st.metric` で金額差を表示

### 3. 残り総加工時間＆最適生産ルート ⏱️
- 各アイテムのNC合計 = `front_rough + front_finish + back_rough + back_finish`
- 各アイテムの手作業合計 = `prep.unit + assembly.cut_off + assembly.bonding + manual.fitting + manual.machine_work + manual.sanding + manual.assembly`
- 残時間 = `Σ(remaining × (nc_total + manual_total))` を分単位で集計
- **効率ランキング**: `price / total_process_min` で「1分あたりの売上貢献額」を算出、上位3品を推奨
- NC時間と手作業時間を別指標で表示

### 4. 本日の最適タスク（Go/No-Go） 📋
- 現在時刻が20時以降 → **NCは騒音NG、手作業のみ推奨**
- 20時前 → NC稼働可能。残数の多い上位アイテムからNC1件＋手作業1件を抽出
- 全アイテム完了済み → `st.success("全目標達成！")` 表示

### 5. 材料発注アラート ⚠️
- 材料種別（SPF/ヒノキ/マツ/毛糸）ごとに remaining を集計
- `remaining / yield` で必要板数を算出
- 残り日数に対して1日あたり消費量を計算し「不足予測日」を提示
- しきい値を超えたらアラート表示

### 6. 新作開発枠 🆕
- 進捗率50%以上 かつ 残り日数30日以上 → `st.success("🟢 新作開発OK")`
- それ以外 → `st.warning("🔴 既存品に集中せよ")`

---

## 検証計画

### 自動テスト

#### [NEW] [test_bi_dashboard.py](file:///c:/Users/yjing/.gemini/atlas-hub/tests/test_bi_dashboard.py)

`bi_dashboard.py` の各計算関数に対するユニットテスト：
- カウントダウン計算の正確性
- 売上ギャップ計算（鞘のprice=0が除外されること）
- 残時間計算の合計値
- Go/No-Go判定の時間帯別分岐
- 材料アラート閾値

```
cd c:\Users\yjing\.gemini\atlas-hub
python -m pytest tests/test_bi_dashboard.py -v
```

### 手動検証

1. `streamlit run app.py` でアプリ起動
2. サイドバーから「📊 BI Dashboard」を選択
3. 6つのKPIが正常表示されることを確認
4. ブラウザのDevToolsでモバイルビュー（375px）に切り替え、レイアウト崩れがないことを確認
