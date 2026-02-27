import hashlib
import pandas as pd
from datetime import datetime, timedelta

def hash_row(row):
    """
    行データのユニークなハッシュ値を生成 (SHA256)
    TimeStamp + Project + Path + Message
    """
    path_val = str(row.get('PATH', '')).strip()
    proj_val = str(row.get('PROJECT', '')).strip()
    ts_val = str(row.get('TIMESTAMP', '')).strip()
    msg_val = str(row.get('MESSAGE', '')).strip()
    
    raw_str = f"{ts_val}|{proj_val}|{path_val}|{msg_val}"
    return hashlib.sha256(raw_str.encode('utf-8')).hexdigest()

def determine_side(path):
    """
    ファイルパスから加工面(表/裏)を判定する
    """
    path_lower = str(path).lower()
    if any(kw in path_lower for kw in ['face', 'front', 'omote', '表']):
        return '表'
    if any(kw in path_lower for kw in ['back', 'rear', 'ura', '裏', 'base']):
        return '裏'
    return '不明'

def calculate_production_events(log_df):
    """
    ログデータから生産カレンダー用イベントを作成する (共通仕様書 v1.0 準拠)
    """
    events = []
    
    if log_df is None or log_df.empty:
        return events

    df = log_df.copy()
    
    # 必須列の存在確認と補完
    if 'TIMESTAMP' not in df.columns:
        return events
    if 'PROJECT' not in df.columns:
        df['PROJECT'] = 'Unknown'
    if 'PART' not in df.columns:
        df['PART'] = ''
    if 'PATH' not in df.columns:
        df['PATH'] = ''

    # TIMESTAMP のパースと90日フィルタリング
    df['dt_parsed'] = pd.to_datetime(df['TIMESTAMP'], errors='coerce')
    df = df.dropna(subset=['dt_parsed'])
    
    cutoff_date = datetime.now() - timedelta(days=90)
    df = df[df['dt_parsed'] >= cutoff_date]
    
    if df.empty:
        return events

    # 日付文字列 (YYYY-MM-DD) の作成
    df['LOG_DATE'] = df['dt_parsed'].dt.strftime('%Y-%m-%d')
    
    # グループ化: 日付 + プロジェクト + パーツ
    grouped = df.groupby(['LOG_DATE', 'PROJECT', 'PART'])

    for (d_str, proj_name, part_name), group in grouped:
        # 面判定
        sides = set()
        hashes = []
        
        for idx, row in group.iterrows():
            s = determine_side(row['PATH'])
            sides.add(s)
            hashes.append(hash_row(row))
        
        has_front = '表' in sides
        has_back = '裏' in sides
        
        # タイトルとステータスの決定
        disp_title = proj_name
        if part_name:
            disp_title = f"{proj_name} ({part_name})"
            
        status_details = f"Sides: {list(sides)}"
        color = "#28a745" if (has_front and has_back) else "#ffc107" # 緑(高信頼) or 黄(低信頼)

        # FullCalendar用イベント形式
        source_hashes = ",".join(hashes)
        max_ts = group['dt_parsed'].max()
        atlas_timestamp = max_ts.strftime('%Y-%m-%d %H:%M:%S')

        events.append({
            "title": disp_title,
            "start": d_str,
            "color": color,
            "extendedProps": {
                "details": status_details,
                "project": proj_name,
                "part": part_name,
                "confidence": "high" if (has_front and has_back) else "low",
                "source_hashes": source_hashes,
                "atlas_timestamp": atlas_timestamp
            }
        })

    return events
