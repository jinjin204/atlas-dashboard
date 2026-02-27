# 動作フロー（履歴・予測）仕様に基づく master_loader.py / zeus_chat.py 全面改修

仕様書 `動作フロー_履歴・予測.md` を唯一の真実として、履歴記録・成果算出・未来予測ロジックを一撃で完遂する。

## 現状の問題点

1. **`master_loader.py`**: `merge_event_targets` の履歴記録に `details`（商品IDごとの個数）が含まれないスキャンエントリが大量に存在（4900行中、`details` 付きは最新エントリのみ）
2. **`master_loader.py`**: イベントマスタのアクティブ行から「備考」列を読み取り、持越元の初期在庫を動的に特定するロジックが未実装
3. **`zeus_chat.py`**: 本日の成果算出が「最新ログ vs 直前ログ」ではなく「最新ログ vs 昨日以前の最後のログ」で実装されており、仕様と微妙にずれ
4. **`zeus_chat.py`**: 平均ペース算出が全ログの通算ではなく直近2点間のみ。仕様では「全てのログから平均生産個数」を要求
5. **`zeus_chat.py`**: 未来予測が工程時間ベースの残工数計算を使っておらず、単純な時間割で計算中

## 修正方針

### Phase 1: `master_loader.py` の改修

---

### マスタローダー

#### [MODIFY] [master_loader.py](file:///c:/Users/yjing/.gemini/atlas-hub/logic/master_loader.py)

**変更1: イベントマスタからの動的シート特定 + 備考列の読み取り**

`merge_event_targets` 関数内で、イベントマスタのアクティブ行から「備考」列を読み取り、持越元の初期在庫参照先（例: 「クリマ2512 AK列」）を自動的に特定するロジックを追加。

```python
# col_map に 'note' (備考) を追加
col_map['note'] = None
# ヘッダー探索に備考の判定を追加
if '備考' in c_str or 'Note' in c_str: col_map['note'] = col

# アクティブ行から備考を取得して初期在庫をインポート
note_val = _get_val('note')
if note_val and _is_true('active'):
    _import_initial_from_note(xls, note_val, target_sheets)
```

**変更2: 初期在庫の自動インポート関数**

`_import_initial_from_note(xls, note_text, target_sheets)` を新規追加。備考テキスト（例: "クリマ2512 AK列"）をパースし、指定されたシートの指定列からデータを読み取り、初期在庫として `history_summary.json` に記録する。

**変更3: 履歴記録の改善**

`merge_event_targets` 内での `history_data` 記録を確実に `details`（商品IDごとの個数）を含むようにする。現状のロジックは条件によって `details` が `{}` のまま保存されるバグがある。

---

### Phase 2: `zeus_chat.py` の改修

---

### Zeusチャットロジック

#### [MODIFY] [zeus_chat.py](file:///c:/Users/yjing/.gemini/atlas-hub/logic/zeus_chat.py)

**変更1: 本日の成果算出ロジックの修正**

`get_daily_achievements()` を修正し、仕様通り「最新のログ」と「その直前のログ」を比較する方式にする。現在の「昨日以前の最終ログ」との比較から、時系列ソート後の直前エントリとの比較に変更。ただし、`details` が無いスキャンエントリはスキップする。

```python
# detailsが空でないログのみ有効とする
valid_history = [h for h in parsed_history if h.get('details')]
if len(valid_history) < 2:
    return "★本日の成果: （比較用データ不足）"
latest = valid_history[-1]
prev = valid_history[-2]
```

**変更2: 全ログベースの平均ペース算出**

`load_history_stats()` を修正し、全ログから1日あたりの平均生産個数を算出する。

```python
# 初期値と最新値から通算日平均を算出
initial = valid_history[0]
latest = valid_history[-1]
total_days = (latest['_dt'] - initial['_dt']).days
if total_days > 0:
    total_produced = latest.get('total_current', 0) - initial.get('total_current', 0)
    pace_per_day = total_produced / total_days
```

**変更3: 未来予測（完了予定日）のロジック改善**

`build_system_prompt()` 内の予測ロジックを修正:

1. 商品マスタから目標在庫と工程別加工時間（NC＋手作業）を取得
2. `(目標数 - 現在数) × 加工時間` で残り必要工数を算出
3. 平均ペース × 平均工数/個 で残日数・完了予定日を算出

---

### Phase 3: エラーハンドリング

#### [MODIFY] [zeus_chat.py](file:///c:/Users/yjing/.gemini/atlas-hub/logic/zeus_chat.py)

- `today_str` の未定義による `NameError` を根絶（現状のコードでは L536 で定義されているが、それ以前の箇所で使用していないか確認）
- `google-genai` ライブラリ不足時の警告は既にL13-18で実装済み。追加の堅牢性確認
- `history_summary.json` の `details` が無い古いエントリのフィルタリング

## 検証計画

### 自動テスト

1. **構文チェック**: 修正後の両ファイルに対して `python -c "import py_compile; py_compile.compile('logic/master_loader.py', doraise=True)"` を実行
2. **既存テスト実行**: `cd c:\Users\yjing\.gemini\atlas-hub && python -m pytest tests/test_master_loader.py tests/test_zeus_search.py -v`
3. **Drive同期 + スキャン実行**: `cd c:\Users\yjing\.gemini\atlas-hub && python -c "from logic.master_loader import sync_from_drive; sync_from_drive()"` で最新データを取得し、`history_summary.json` に `details` 付きエントリが追記されることを確認

### 手動検証

1. ユーザーに Streamlit アプリを起動してもらい、「軍師Zeus」タブで「進捗報告」と入力 → 本日の成果・平均ペース・完了予定日が日本語で正しく報告されることを目視確認
