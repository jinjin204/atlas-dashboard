"""
Atlas Hub - Calendar Agent
個人GoogleカレンダーからN日分の予定を取得し、空き時間を算出する。
商品スケジュール（production_master.json）と統合し、
atlas_integrated_data.json としてGoogle Driveに出力する。

※会社アカウントへのアクセスは行わない（個人アカウントのみ）。
"""

import os
import io
import json
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


# ================================================================
# 設定
# ================================================================
CALENDAR_SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/tasks.readonly',
]
LOOK_AHEAD_DAYS = 90  # 3ヶ月分
WORK_START_HOUR = 9    # 作業可能時間帯の開始
WORK_END_HOUR = 22     # 作業可能時間帯の終了

# Drive出力先のフォルダID（atlas-hubと同じフォルダ）
OUTPUT_FOLDER_ID = "1swLvCAzeFx8N9DhG5jfeUXPvlhCmCK6i"
OUTPUT_FILENAME = "atlas_integrated_data.json"


# ================================================================
# 認証（drive_utils.pyと共通のtoken.jsonを使用）
# ================================================================
def _get_credentials():
    """
    認証情報を取得する（3段階フォールバック）:
    1. token.json が存在すれば読み込み（有効期限切れならリフレッシュ）
    2. credentials.json が存在すればブラウザ認証フロー（InstalledAppFlow）
    3. st.secrets["google_oauth"] から構築（クラウド用）
    """
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    token_file = os.path.join(base_dir, 'token.json')
    creds_file = os.path.join(base_dir, 'credentials.json')
    
    creds = None
    
    # --- Step 1: token.json から読み込み ---
    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_file(token_file, CALENDAR_SCOPES)
            print(f"[calendar_agent] token.json 読み込み成功")
        except Exception as e:
            print(f"[calendar_agent] token.json 読み込みエラー: {e}")
            creds = None
    
    # --- トークンの有効性チェック＆リフレッシュ ---
    if creds:
        if creds.valid:
            return creds
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # リフレッシュ後のtoken.jsonを更新保存
                with open(token_file, 'w') as f:
                    f.write(creds.to_json())
                print("[calendar_agent] トークンをリフレッシュしました")
                return creds
            except Exception as e:
                print(f"[calendar_agent] トークンリフレッシュ失敗: {e}")
                # スコープ変更等でリフレッシュ不可の場合は再認証へ
                creds = None
        else:
            # refresh_tokenが無い or 期限切れでない異常状態 → 再認証
            print("[calendar_agent] トークンが無効です。再認証します。")
            creds = None
    
    # --- Step 2: credentials.json でブラウザ認証（ローカル） ---
    if os.path.exists(creds_file):
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            print("[calendar_agent] ブラウザ認証を開始します...")
            flow = InstalledAppFlow.from_client_secrets_file(creds_file, CALENDAR_SCOPES)
            creds = flow.run_local_server(port=0)
            
            # token.json に保存
            with open(token_file, 'w') as f:
                f.write(creds.to_json())
            print(f"[calendar_agent] ✅ 認証完了。token.json を保存しました: {token_file}")
            
            # refresh_token を画面に表示（st.secrets設定用）
            if creds.refresh_token:
                print(f"[calendar_agent] 📋 refresh_token: {creds.refresh_token}")
                print("[calendar_agent] ↑ この値を st.secrets の google_oauth.refresh_token に設定してください")
            
            return creds
        except Exception as e:
            print(f"[calendar_agent] ブラウザ認証エラー: {e}")
            creds = None
    
    # --- Step 3: st.secrets フォールバック（クラウド） ---
    try:
        import streamlit as st
        oauth_info = st.secrets.get("google_oauth", {})
        refresh_token = oauth_info.get("refresh_token", "")
        if not refresh_token:
            print("[calendar_agent] st.secrets に refresh_token が未設定です")
            return None
        
        creds = Credentials(
            token=oauth_info.get("token", ""),
            refresh_token=refresh_token,
            token_uri=oauth_info.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=oauth_info.get("client_id", ""),
            client_secret=oauth_info.get("client_secret", ""),
            scopes=CALENDAR_SCOPES,
        )
        if not creds.valid:
            creds.refresh(Request())
        return creds
    except Exception as e:
        print(f"[calendar_agent] st.secrets 認証エラー: {e}")
        return None


# ================================================================
# カレンダーからイベントを取得
# ================================================================
def fetch_calendar_events(creds, days=LOOK_AHEAD_DAYS):
    """
    個人Googleカレンダーの予定を取得する。
    
    Returns:
        list[dict]: 各イベント {'summary', 'start', 'end', 'all_day', 'calendar'}
    """
    service = build('calendar', 'v3', credentials=creds)
    
    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days)).isoformat()
    
    events = []
    
    # カレンダーリストを取得（個人アカウントのカレンダーのみ）
    calendar_list = service.calendarList().list().execute()
    
    for cal in calendar_list.get('items', []):
        cal_id = cal['id']
        cal_summary = cal.get('summary', cal_id)
        
        # Google自動生成カレンダー（祝日・誕生日等）は除外
        if '#holiday@group.v.calendar.google.com' in cal_id:
            print(f"[calendar_agent] スキップ（祝日カレンダー）: {cal_summary}")
            continue
        if '#contacts@group.v.calendar.google.com' in cal_id:
            print(f"[calendar_agent] スキップ（誕生日カレンダー）: {cal_summary}")
            continue
        if '#weather@group.v.calendar.google.com' in cal_id:
            print(f"[calendar_agent] スキップ（天気カレンダー）: {cal_summary}")
            continue
        
        access_role = cal.get('accessRole', '')
        print(f"[calendar_agent] 取得対象: {cal_summary} (role={access_role})")
        
        try:
            events_result = service.events().list(
                calendarId=cal_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime',
                maxResults=500,
            ).execute()
            
            for event in events_result.get('items', []):
                start = event.get('start', {})
                end = event.get('end', {})
                
                # 終日イベント or 時間指定イベント
                if 'date' in start:
                    all_day = True
                    start_dt = start['date']
                    end_dt = end.get('date', start_dt)
                else:
                    all_day = False
                    start_dt = start.get('dateTime', '')
                    end_dt = end.get('dateTime', '')
                
                events.append({
                    'summary': event.get('summary', '(タイトルなし)'),
                    'start': start_dt,
                    'end': end_dt,
                    'all_day': all_day,
                    'calendar': cal_summary,
                })
        except Exception as e:
            print(f"[calendar_agent] カレンダー '{cal_summary}' の取得エラー: {e}")
            continue
    
    print(f"[calendar_agent] 取得イベント数: {len(events)}")
    return events


# ================================================================
# 空き時間を算出
# ================================================================
def calculate_free_slots(events, days=LOOK_AHEAD_DAYS):
    """
    カレンダーの予定を元に、日ごとの空き時間ブロックを算出する。
    
    Returns:
        list[dict]: 日ごとの空き時間情報
        [
            {
                'date': '2026-03-01',
                'day_of_week': '日',
                'events': [...],         # その日の予定
                'free_blocks': [...],    # 空きブロック [{'start': '09:00', 'end': '13:00', 'hours': 4}]
                'total_free_hours': 8.5, # その日の合計空き時間
                'is_blocked': False,     # 終日予定でブロックされているか
            }
        ]
    """
    JST = timezone(timedelta(hours=9))
    today = datetime.now(JST).date()
    
    day_names = ['月', '火', '水', '木', '金', '土', '日']
    
    # 日ごとにイベントを整理
    daily_data = {}
    for day_offset in range(days):
        d = today + timedelta(days=day_offset)
        date_str = d.isoformat()
        daily_data[date_str] = {
            'date': date_str,
            'day_of_week': day_names[d.weekday()],
            'events': [],
            'free_blocks': [],
            'total_free_hours': 0,
            'is_blocked': False,
        }
    
    # イベントを日付に振り分け
    for event in events:
        if event['all_day']:
            # 終日イベント: 該当日をブロック
            start_date = event['start']
            end_date = event.get('end', start_date)
            try:
                sd = datetime.strptime(start_date, '%Y-%m-%d').date()
                ed = datetime.strptime(end_date, '%Y-%m-%d').date()
                current = sd
                while current < ed:
                    key = current.isoformat()
                    if key in daily_data:
                        daily_data[key]['is_blocked'] = True
                        daily_data[key]['events'].append({
                            'summary': event['summary'],
                            'start': '終日',
                            'end': '終日',
                        })
                    current += timedelta(days=1)
            except ValueError:
                pass
        else:
            # 時間指定イベント
            try:
                start_dt = datetime.fromisoformat(event['start'])
                end_dt = datetime.fromisoformat(event['end'])
                # JSTに変換
                start_jst = start_dt.astimezone(JST)
                end_jst = end_dt.astimezone(JST)
                
                key = start_jst.date().isoformat()
                if key in daily_data:
                    daily_data[key]['events'].append({
                        'summary': event['summary'],
                        'start': start_jst.strftime('%H:%M'),
                        'end': end_jst.strftime('%H:%M'),
                    })
            except (ValueError, TypeError):
                pass
    
    # 各日の空き時間を計算
    for date_str, day_info in daily_data.items():
        if day_info['is_blocked']:
            day_info['total_free_hours'] = 0
            continue
        
        # 予定のある時間帯を集約
        busy_ranges = []
        for evt in day_info['events']:
            if evt['start'] == '終日':
                continue
            try:
                sh, sm = map(int, evt['start'].split(':'))
                eh, em = map(int, evt['end'].split(':'))
                busy_ranges.append((sh * 60 + sm, eh * 60 + em))
            except (ValueError, TypeError):
                pass
        
        # ソートしてマージ
        busy_ranges.sort()
        merged = []
        for start, end in busy_ranges:
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        
        # 空きブロック算出（WORK_START_HOUR ~ WORK_END_HOUR）
        work_start = WORK_START_HOUR * 60
        work_end = WORK_END_HOUR * 60
        free_blocks = []
        cursor = work_start
        
        for busy_start, busy_end in merged:
            if busy_start > cursor and busy_start >= work_start:
                block_start = max(cursor, work_start)
                block_end = min(busy_start, work_end)
                if block_end > block_start:
                    free_blocks.append({
                        'start': f"{block_start // 60:02d}:{block_start % 60:02d}",
                        'end': f"{block_end // 60:02d}:{block_end % 60:02d}",
                        'hours': round((block_end - block_start) / 60, 1),
                    })
            cursor = max(cursor, busy_end)
        
        # 最後の空きブロック
        if cursor < work_end:
            block_start = max(cursor, work_start)
            free_blocks.append({
                'start': f"{block_start // 60:02d}:{block_start % 60:02d}",
                'end': f"{work_end // 60:02d}:{work_end % 60:02d}",
                'hours': round((work_end - block_start) / 60, 1),
            })
        
        day_info['free_blocks'] = free_blocks
        day_info['total_free_hours'] = sum(b['hours'] for b in free_blocks)
    
    return list(daily_data.values())


# ================================================================
# 商品スケジュールと統合
# ================================================================
def integrate_with_production(free_slots, production_master_path=None):
    """
    空き時間データと商品スケジュール（production_master.json）を統合する。
    カレンダーの固定予定を isGoal: true のタスクとして追加する。
    
    Returns:
        dict: 統合データ
    """
    # production_master.jsonの読み込み
    production_data = []
    if production_master_path and os.path.exists(production_master_path):
        try:
            with open(production_master_path, 'r', encoding='utf-8') as f:
                production_data = json.load(f)
        except Exception as e:
            print(f"[calendar_agent] production_master.json 読み込みエラー: {e}")
    
    # 固定予定をタスク形式に変換
    fixed_events = []
    for slot in free_slots:
        for evt in slot.get('events', []):
            fixed_events.append({
                'title': evt['summary'],
                'date': slot['date'],
                'start_time': evt['start'],
                'end_time': evt['end'],
                'isGoal': True,  # 固定予定マーカー
                'type': 'calendar_event',
                'day_of_week': slot['day_of_week'],
            })
    
    # 日別サマリー（空き時間を含む）
    daily_summary = []
    for slot in free_slots:
        daily_summary.append({
            'date': slot['date'],
            'day_of_week': slot['day_of_week'],
            'total_free_hours': slot['total_free_hours'],
            'is_blocked': slot['is_blocked'],
            'free_blocks': slot['free_blocks'],
            'event_count': len(slot['events']),
        })
    
    # 統計情報
    total_free = sum(s['total_free_hours'] for s in free_slots)
    blocked_days = sum(1 for s in free_slots if s['is_blocked'])
    work_days = sum(1 for s in free_slots if s['total_free_hours'] > 0)
    
    integrated = {
        'generated_at': datetime.now(timezone(timedelta(hours=9))).isoformat(),
        'look_ahead_days': LOOK_AHEAD_DAYS,
        'summary': {
            'total_free_hours': round(total_free, 1),
            'blocked_days': blocked_days,
            'available_work_days': work_days,
            'avg_free_hours_per_day': round(total_free / max(work_days, 1), 1),
        },
        'fixed_events': fixed_events,
        'daily_schedule': daily_summary,
        'production_master': production_data,
    }
    
    return integrated


# ================================================================
# Google Driveへ出力
# ================================================================
def upload_to_drive(creds, data, folder_id=OUTPUT_FOLDER_ID, filename=OUTPUT_FILENAME):
    """
    統合データをJSONとしてGoogle Driveにアップロードする。
    既存ファイルがあれば上書き、なければ新規作成。
    """
    from googleapiclient.http import MediaIoBaseUpload
    
    service = build('drive', 'v3', credentials=creds)
    
    json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
    stream = io.BytesIO(json_bytes)
    media = MediaIoBaseUpload(stream, mimetype='application/json', resumable=True)
    
    # 既存ファイルを検索
    query = f"name = '{filename}' and trashed = false and '{folder_id}' in parents"
    results = service.files().list(q=query, pageSize=1, fields='files(id)').execute()
    existing = results.get('files', [])
    
    if existing:
        # 上書きアップロード
        file_id = existing[0]['id']
        updated = service.files().update(fileId=file_id, media_body=media).execute()
        print(f"[calendar_agent] ✅ Drive更新完了: {filename} (ID: {file_id})")
        return file_id
    else:
        # 新規作成
        file_metadata = {
            'name': filename,
            'parents': [folder_id],
            'mimeType': 'application/json',
        }
        created = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        file_id = created.get('id')
        print(f"[calendar_agent] ✅ Drive新規作成: {filename} (ID: {file_id})")
        return file_id


# ================================================================
# Google Tasks API 統合
# ================================================================
def fetch_google_tasks(creds):
    """
    Google Tasks API から期日付きタスクを取得する。
    
    Returns:
        list[dict]: 各タスク {'title', 'due', 'notes', 'status', 'task_list'}
    """
    try:
        service = build('tasks', 'v1', credentials=creds)
    except Exception as e:
        print(f"[calendar_agent] Tasks API 初期化エラー: {e}")
        return []
    
    tasks = []
    JST = timezone(timedelta(hours=9))
    now = datetime.now(JST)
    
    # 実行時から31日先のタイムスタンプを作成 (Google Tasks API用)
    time_max = (now + timedelta(days=31)).isoformat()
    
    try:
        # 全タスクリストを取得
        tasklists = service.tasklists().list(maxResults=100).execute()
        
        for tl in tasklists.get('items', []):
            tl_id = tl['id']
            tl_title = tl.get('title', '無題リスト')
            
            try:
                tasks_result = service.tasks().list(
                    tasklist=tl_id,
                    showCompleted=False,
                    showHidden=False,
                    maxResults=100,
                    dueMax=time_max  # 31日先まで取得
                ).execute()
                
                items = tasks_result.get('items', [])
                print(f"[calendar_agent] =========================================")
                print(f"[calendar_agent] タスクリスト '{tl_title}' から {len(items)} 件のRAWタスクを取得しました")

                for task in items:
                    title = task.get('title', '(無題)')
                    due = task.get('due', '')
                    
                    # デバッグ出力（全件表示）
                    print(f"[calendar_agent]   - タスク確認: title='{title}', due='{due}'")
                    
                    # 「確定申告」を含むタスクへの特別なログ
                    if '確定申告' in title:
                        print(f"[calendar_agent]   ★確定申告タスク発見★ title='{title}', due='{due}'")

                    if not due:
                        print(f"[calendar_agent]     -> 期日(due)が存在しないためスキップしました")
                        continue  # 期日なしタスクはスキップ
                    
                    # 期日をパース（RFC 3339形式: "2026-03-15T00:00:00.000Z"）
                    try:
                        due_dt = datetime.fromisoformat(due.replace('Z', '+00:00'))
                        due_jst = due_dt.astimezone(JST)
                        days_until = (due_jst.date() - now.date()).days
                    except (ValueError, TypeError):
                        days_until = None
                    
                    tasks.append({
                        'title': task.get('title', '(無題)'),
                        'due': due,
                        'due_date': due_jst.strftime('%Y-%m-%d') if days_until is not None else due[:10],
                        'days_until': days_until,
                        'notes': task.get('notes', ''),
                        'status': task.get('status', 'needsAction'),
                        'task_list': tl_title,
                    })
            except Exception as e:
                print(f"[calendar_agent] タスクリスト '{tl_title}' 取得エラー: {e}")
                continue
    except Exception as e:
        print(f"[calendar_agent] Tasks API エラー: {e}")
        return []
    
    # 期日が近い順にソート
    tasks.sort(key=lambda t: t.get('days_until', 9999) if t.get('days_until') is not None else 9999)
    
    print(f"[calendar_agent] 取得タスク数: {len(tasks)} (期日付きのみ)")
    return tasks


# ================================================================
# アグレッシブ提案エンジン（軍師モード）
# ================================================================
def generate_aggressive_suggestions(free_slots, production_data=None, google_tasks=None):
    """
    カレンダーの空き時間を分析し、アグレッシブな「限界突破」スケジュール提案を生成する。
    あえて無茶な提案をすることで、マスターデータの精緻化（家族の予定入力等）を促す。
    
    Args:
        free_slots: calculate_free_slots の出力
        production_data: production_master.json の内容（残数が多い商品の提案に使用）
    
    Returns:
        list[dict]: 提案リスト
        [
            {
                'type': str,          # 'early_morning' | 'weekend_extend' | 'gap_slot' | 'nc_setup'
                'message': str,       # 主提案メッセージ
                'impact': str,        # 効果の説明
                'date': str,          # 対象日
                'nudge': str,         # マスター精緻化を促すナッジメッセージ
                'priority': int,      # 1=高 3=低
            }
        ]
    """
    JST = timezone(timedelta(hours=9))
    today = datetime.now(JST).date()
    suggestions = []
    
    # 残り生産量が多い商品を特定（提案文に使用）
    top_remaining_item = None
    if production_data:
        remaining_items = [(p.get('name', '?'), p.get('remaining', 0)) for p in production_data if p.get('remaining', 0) > 0]
        remaining_items.sort(key=lambda x: x[1], reverse=True)
        if remaining_items:
            top_remaining_item = remaining_items[0][0]
    
    for slot in free_slots:
        d = slot['date']
        try:
            slot_date = datetime.strptime(d, '%Y-%m-%d').date()
        except ValueError:
            continue
        
        # 過去の日付はスキップ
        if slot_date < today:
            continue
        
        # 7日先までのみ提案（直近のアクションに集中）
        days_ahead = (slot_date - today).days
        if days_ahead > 7:
            continue
        
        day_of_week = slot['day_of_week']
        is_weekend = day_of_week in ('土', '日')
        free_blocks = slot.get('free_blocks', [])
        total_free = slot.get('total_free_hours', 0)
        events = slot.get('events', [])
        is_blocked = slot.get('is_blocked', False)
        
        if is_blocked:
            continue
        
        # ===== 提案1: 早朝隙間（6:00-9:00）の活用 =====
        # イベントが朝9時以降に開始する場合、出勤前の時間を提案
        has_morning_event = any(
            e.get('start', '99:99') < '09:00' and e.get('start', '00:00') >= '06:00'
            for e in events if e.get('start') != '終日'
        )
        if not has_morning_event and not is_weekend and events:
            # 平日で朝の予定がない場合
            item_name = top_remaining_item or '大物商品'
            suggestions.append({
                'type': 'nc_setup',
                'message': f'⏰ {d}（{day_of_week}）出勤前の45分で NCマシンのセットアップを完了させよ！'
                           f' 仕事中に{item_name}の粗削りを無人運転で完了できる。',
                'impact': f'出勤前15分の段取りで、日中3〜4時間分のNC加工を無人で進行可能',
                'date': d,
                'nudge': '📝 出勤時間をカレンダーに登録すると、この提案の精度が上がります',
                'priority': 1,
            })
        
        # ===== 提案2: 週末予定なし → 稼働時間延長 =====
        if is_weekend and total_free >= 10 and len(events) <= 1:
            suggestions.append({
                'type': 'weekend_extend',
                'message': f'🔥 {d}（{day_of_week}）は予定がほぼ空いています！'
                           f' 稼働時間を朝8時〜夜22時（14時間）にすれば、目標ペースを一気に巻き返せます。',
                'impact': f'空き時間 {total_free}h を最大活用。NC2台並行稼働 + 手作業で3〜4製品を同時進行',
                'date': d,
                'nudge': '📝 家族の予定・買い出しの時間をカレンダーに入れると、実使用可能な時間がわかります',
                'priority': 1,
            })
        
        # ===== 提案3: 会議間の隙間30分以上 → 手作業 =====
        for block in free_blocks:
            try:
                hours = block.get('hours', 0)
                block_start = block.get('start', '')
                block_end = block.get('end', '')
            except (ValueError, TypeError):
                continue
            
            if 0.5 <= hours <= 2.0 and not is_weekend:
                suggestions.append({
                    'type': 'gap_slot',
                    'message': f'⚡ {d}（{day_of_week}）{block_start}〜{block_end}に{hours}時間の隙間あり！'
                               f' ヤスリがけ・組み立て等の手作業を詰め込めます。',
                    'impact': f'{int(hours * 60)}分あれば、2〜3個の仕上げ作業が可能',
                    'date': d,
                    'nudge': '📝 移動時間・準備時間をマスタデータに追加すると、より現実的な提案になります',
                    'priority': 2,
                })
        
        # ===== 提案4: 平日夜の稼働延長 (20:00-23:00) =====
        if not is_weekend and total_free >= 3:
            has_late_event = any(
                e.get('end', '00:00') > '20:00'
                for e in events if e.get('start') != '終日'
            )
            if not has_late_event:
                suggestions.append({
                    'type': 'night_extend',
                    'message': f'🌙 {d}（{day_of_week}）夜20時以降は予定なし。'
                               f' 手作業（ヤスリ・組立）なら騒音を気にせず23時まで延長可能。',
                    'impact': '追加3時間で仕上げ系の作業を5〜6個進められる',
                    'date': d,
                    'nudge': '📝 「NC稼働可能時間」「手作業可能時間」を分けてマスタに記録すると、夜間提案の精度が上がります',
                    'priority': 3,
                })
    
    # ===== 提案5: 期日直近（3日以内）のタスク =====
    if google_tasks:
        for task in google_tasks:
            try:
                days_until = task.get('days_until')
                if days_until is not None and 0 <= days_until <= 3:
                    title = task.get('title', '無題タスク')
                    suggestions.append({
                        'type': 'urgent_task',
                        'message': f'🚨 期限間近：{title} があと{days_until}日で締め切りです。生産計画を調整し、事務作業の時間を確保せよ！',
                        'impact': f'期日超過によるペナルティや信用低下を回避',
                        'date': today.strftime("%Y-%m-%d"),
                        'nudge': '📝 事務作業や買い出しの期限（Google ToDo）を登録すると、警告の精度が上がります',
                        'priority': 1,
                    })
            except Exception:
                pass
    
    # 優先度でソート
    suggestions.sort(key=lambda s: (s['priority'], s['date']))
    
    # 最大10件に制限
    suggestions = suggestions[:10]
    
    print(f"[calendar_agent] 生成提案数: {len(suggestions)}")
    return suggestions


# ================================================================
# メインエントリーポイント
# ================================================================
def run(output_local=True, output_drive=True):
    """
    カレンダーエージェントのメイン実行関数。
    
    1. Google Calendar から予定を取得
    2. 空き時間を算出
    3. Google Tasks から期日付きタスクを取得
    4. アグレッシブ提案を生成
    5. 商品スケジュールと統合
    6. atlas_integrated_data.json を出力
    """
    print("=" * 50)
    print("[calendar_agent] Atlas Calendar Agent 起動")
    print(f"[calendar_agent] 対象期間: 本日から {LOOK_AHEAD_DAYS} 日間")
    print("=" * 50)
    
    # 1. 認証
    creds = _get_credentials()
    if not creds:
        print("[calendar_agent] ❌ 認証に失敗しました。token.json を確認してください。")
        return None
    
    # 2. カレンダーイベント取得
    print("[calendar_agent] Step 1: カレンダーイベント取得中...")
    events = fetch_calendar_events(creds)
    
    # 3. 空き時間算出
    print("[calendar_agent] Step 2: 空き時間を算出中...")
    free_slots = calculate_free_slots(events)
    
    # 4. Google Tasks 取得
    print("[calendar_agent] Step 3: Google Tasks取得中...")
    google_tasks = []
    try:
        google_tasks = fetch_google_tasks(creds)
    except Exception as e:
        print(f"[calendar_agent] ⚠️ Tasks取得スキップ（スコープ未認可の可能性）: {e}")
    
    # 5. 商品スケジュールとの統合
    print("[calendar_agent] Step 4: 商品スケジュールと統合中...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    production_path = os.path.join(base_dir, '..', 'data', 'production_master.json')
    integrated = integrate_with_production(free_slots, production_path)
    
    # 6. アグレッシブ提案生成
    print("[calendar_agent] Step 5: アグレッシブ提案を生成中...")
    production_data = integrated.get('production_master', [])
    suggestions = generate_aggressive_suggestions(free_slots, production_data, google_tasks)
    
    # 統合データに追加
    integrated['google_tasks'] = google_tasks
    integrated['aggressive_suggestions'] = suggestions
    
    # 7. ローカル出力
    if output_local:
        local_path = os.path.join(base_dir, '..', 'data', OUTPUT_FILENAME)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, 'w', encoding='utf-8') as f:
            json.dump(integrated, f, ensure_ascii=False, indent=2)
        print(f"[calendar_agent] ✅ ローカル出力: {local_path}")
    
    # 8. Drive出力
    if output_drive:
        print("[calendar_agent] Step 6: Google Driveへアップロード中...")
        try:
            upload_to_drive(creds, integrated)
        except Exception as e:
            print(f"[calendar_agent] ⚠️ Driveアップロードエラー: {e}")
    
    # サマリー表示
    s = integrated['summary']
    print("=" * 50)
    print(f"[calendar_agent] 📊 サマリー:")
    print(f"  合計空き時間: {s['total_free_hours']} 時間")
    print(f"  ブロック日数: {s['blocked_days']} 日")
    print(f"  作業可能日数: {s['available_work_days']} 日")
    print(f"  平均空き時間/日: {s['avg_free_hours_per_day']} 時間")
    print(f"  期日付きタスク: {len(google_tasks)} 件")
    print(f"  アグレッシブ提案: {len(suggestions)} 件")
    print("=" * 50)
    
    return integrated


# スタンドアロン実行用
if __name__ == '__main__':
    result = run()
    if result:
        print(json.dumps(result['summary'], ensure_ascii=False, indent=2))
    else:
        print("実行に失敗しました。")
