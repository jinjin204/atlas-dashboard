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
    """token.json または st.secrets から認証情報を取得する"""
    token_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'token.json')
    
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, CALENDAR_SCOPES)
        if not creds.valid and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return creds
    
    # Streamlit Cloud 用フォールバック
    try:
        import streamlit as st
        oauth_info = st.secrets["google_oauth"]
        creds = Credentials(
            token=oauth_info.get("token", ""),
            refresh_token=oauth_info["refresh_token"],
            token_uri=oauth_info.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=oauth_info["client_id"],
            client_secret=oauth_info["client_secret"],
            scopes=CALENDAR_SCOPES,
        )
        if not creds.valid:
            creds.refresh(Request())
        return creds
    except Exception as e:
        print(f"[calendar_agent] 認証エラー: {e}")
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
        
        # プライマリカレンダーと自分が所有するカレンダーのみ
        access_role = cal.get('accessRole', '')
        if access_role not in ('owner', 'writer'):
            continue
        
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
# メインエントリーポイント
# ================================================================
def run(output_local=True, output_drive=True):
    """
    カレンダーエージェントのメイン実行関数。
    
    1. Google Calendar から予定を取得
    2. 空き時間を算出
    3. 商品スケジュールと統合
    4. atlas_integrated_data.json を出力
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
    
    # 4. 商品スケジュールとの統合
    print("[calendar_agent] Step 3: 商品スケジュールと統合中...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    production_path = os.path.join(base_dir, '..', 'data', 'production_master.json')
    integrated = integrate_with_production(free_slots, production_path)
    
    # 5. ローカル出力
    if output_local:
        local_path = os.path.join(base_dir, '..', 'data', OUTPUT_FILENAME)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, 'w', encoding='utf-8') as f:
            json.dump(integrated, f, ensure_ascii=False, indent=2)
        print(f"[calendar_agent] ✅ ローカル出力: {local_path}")
    
    # 6. Drive出力
    if output_drive:
        print("[calendar_agent] Step 4: Google Driveへアップロード中...")
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
    print("=" * 50)
    
    return integrated


# スタンドアロン実行用
if __name__ == '__main__':
    result = run()
    if result:
        print(json.dumps(result['summary'], ensure_ascii=False, indent=2))
    else:
        print("実行に失敗しました。")
