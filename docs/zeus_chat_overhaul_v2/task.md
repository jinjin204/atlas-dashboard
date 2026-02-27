# タスクリスト: zeus_chat.py 抜本改修（最終仕様準拠）

## Phase 1: load_history_stats の改修
- [x] 起点日を `type: "initial"` から動的取得（ハードコード厳禁）
- [x] ペース計算: `(最新total_current - initial.total_current) / (今日 - 起点日)`
- [x] 起点情報 (origin_date, origin_count, origin_details) を返却

## Phase 2: build_system_prompt の構造改革
- [x] プロンプト最上段に `日付ヘッダー` (今日/起点日/経過日数)
- [x] Python確定サマリー: 目標/残数/工数/ペース/予測をAIに再計算させない
- [x] IDベースマージ結果: production_master × history_summary[initial]
- [x] event_master.json を Raw JSON として流し込み（加工禁止）
- [x] ハードコード日付の排除 → アクティブイベントから期限を動的取得

## Phase 3: 検証
- [x] 構文チェック → OK
- [x] unittest 2件全パス → OK
- [x] 直近ペース判定バグ修正 (>= 3 → >= 2)
- [ ] ユーザーによる実動作確認 (Streamlitで「進捗報告」)
