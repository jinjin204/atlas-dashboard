# カレンダー・Tasks統合 & 提案型AIスケジューラ実装計画

ダッシュボードを「可視化ツール」から「マスターデータ精緻化を促す提案型AI（軍師）」へ進化させる。3つの機能を追加する。

## 変更概要

| # | 機能 | 対象ファイル |
|---|------|------------|
| 1 | 会社カレンダー取得制限解除 | `calendar_agent.py` |
| 2 | Google Tasks API統合 | `calendar_agent.py` (新規関数追加) |
| 3 | アグレッシブ提案エンジン | `calendar_agent.py` (新規関数追加), `app.py` (UI追加) |

---

## 提案変更

### 1. カレンダーフィルタ修正

#### [MODIFY] [calendar_agent.py](file:///c:/Users/yjing/.gemini/atlas-hub/logic/calendar_agent.py)

- L155-157の `access_role` フィルタを削除し、全カレンダー（reader, freeBusyReader含む）を対象にする
- ただし不要なカレンダー（祝日、誕生日等のGoogle自動生成カレンダー）を除外するフィルタを追加

```diff
-        access_role = cal.get('accessRole', '')
-        if access_role not in ('owner', 'writer'):
-            continue
+        # Google自動生成カレンダー（祝日・誕生日等）は除外
+        cal_id = cal['id']
+        if cal_id.endswith('#holiday@group.v.calendar.google.com'):
+            continue
+        if 'contacts' in cal_id and '@group.v.calendar.google.com' in cal_id:
+            continue
```

---

### 2. Google Tasks API統合

#### [MODIFY] [calendar_agent.py](file:///c:/Users/yjing/.gemini/atlas-hub/logic/calendar_agent.py)

- `CALENDAR_SCOPES` に `https://www.googleapis.com/auth/tasks.readonly` を追加
- `fetch_google_tasks()` 関数を新規追加: Google Tasks API (`tasks`, `v1`) から期日付きタスクを取得
- `run()` 関数を拡張し、タスク取得結果を統合データに含める

> [!IMPORTANT]
> `token.json` のスコープに `tasks.readonly` が含まれていないため、初回実行時にブラウザ再認証が必要になります。既存の `token.json` を削除して再認証してください。

#### [MODIFY] [requirements.txt](file:///c:/Users/yjing/.gemini/atlas-hub/requirements.txt)

- 依存ライブラリの変更なし（`google-api-python-client` で Tasks API もカバー済み）

---

### 3. アグレッシブ提案エンジン + ダッシュボードUI

#### [MODIFY] [calendar_agent.py](file:///c:/Users/yjing/.gemini/atlas-hub/logic/calendar_agent.py)

`generate_aggressive_suggestions()` 関数を新規追加:
- 入力: 空き時間データ (`free_slots`)、`production_master.json`
- 出力: 「提案」リスト（各提案に `message`, `type`, `impact`, `nudge_message` を含む）
- アルゴリズム:
  - **早朝隙間検出**: 出勤前（6:00-9:00）の短い空き時間を検出し、NCセットアップを提案
  - **休日延長提案**: 週末に予定がない場合、稼働時間延長を提案
  - **隙間時間活用**: 平日の会議間の30分以上の隙間に手作業を提案
  - **ナッジメッセージ**: 各提案に「家族の予定をカレンダーに入力すれば精度が上がります」等のマスター精緻化を促すメッセージを付与

#### [MODIFY] [app.py](file:///c:/Users/yjing/.gemini/atlas-hub/app.py)

BI Dashboardセクション（L695以降）に以下を追加:
1. **タスクアラート**: Google Tasksから取得した期日付きタスクをダッシュボード上部に警告表示
2. **軍師の提案カード**: アグレッシブ提案をカード形式で表示（既存のbi-cardスタイルを活用）
3. **ナッジUI**: 提案の下に「📝 カレンダーに家族の予定を入力すると、さらに精緻な提案ができます」等のメッセージ表示

---

## 検証計画

### 自動テスト

既存テスト `tests/test_bi_dashboard.py` の実行:
```
cd c:\Users\yjing\.gemini\atlas-hub && python -m pytest tests/test_bi_dashboard.py -v
```

新規テスト追加は不要（既存のBI Dashboard KPIロジックに影響なし。追加するのはcalendar_agent内の新規関数のみで、外部APIに依存するため手動検証が適切）。

### 手動検証

1. **ローカルでStreamlitを起動**:
   ```
   cd c:\Users\yjing\.gemini\atlas-hub && streamlit run app.py
   ```
2. **BI Dashboardページを開き、以下を確認**:
   - タスクアラートが表示されるか（Google Tasksに期日付きタスクがある場合）
   - アグレッシブ提案カードが表示されるか
   - ナッジメッセージが表示されるか
3. **calendar_sync.py をスタンドアロンで実行**して、会社カレンダーのイベントが取得されるか確認:
   ```
   cd c:\Users\yjing\.gemini\atlas-hub && python scripts/calendar_sync.py --no-drive
   ```

### GitHubプッシュ
動作確認後、変更をコミット＆プッシュ。
