"""
bi_dashboard.py - 生産管理BIダッシュボード ロジックモジュール

production_master.json（商品マスタ×イベントシートJOIN済）を活用し、
6つのKPI指標を算出する。

KPI:
  1. イベントカウントダウン
  2. 目標売上ギャップ
  3. 残り総加工時間 & 最適生産ルート
  4. 本日の最適タスク (Go/No-Go)
  5. 材料発注アラート
  6. 新作開発枠判定
"""

import io
import json
import os
import math
import pandas as pd
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')


# =============================================================
# 共通ヘルパー
# =============================================================

def _load_event_master():
    """event_master.json を読み込む"""
    path = os.path.join(DATA_DIR, 'event_master.json')
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def _get_active_event(event_master=None):
    """アクティブイベントを取得 (最初のis_active=True)"""
    events = event_master or _load_event_master()
    for evt in events:
        if evt.get('is_active', False):
            return evt
    return None


def _calc_item_times(item):
    """アイテムの1個あたりNC/手作業/合計時間(分)を算出"""
    proc = item.get('process', {})
    nc = proc.get('nc', {})
    prep = proc.get('prep', {})
    assembly = proc.get('assembly', {})
    manual = proc.get('manual', {})

    nc_min = (
        nc.get('front_rough_min', 0)
        + nc.get('front_finish_min', 0)
        + nc.get('back_rough_min', 0)
        + nc.get('back_finish_min', 0)
    )
    manual_min = (
        prep.get('unit_min', 0)
        + assembly.get('cut_off_min', 0)
        + assembly.get('bonding_min', 0)
        + manual.get('fitting_min', 0)
        + manual.get('machine_work_min', 0)
        + manual.get('sanding_min', 0)
        + manual.get('assembly_min', 0)
    )
    return nc_min, manual_min, nc_min + manual_min


# =============================================================
# KPI 1: イベントカウントダウン
# =============================================================

def calc_countdown(now=None, event_master=None):
    """
    アクティブイベントまでの残り日数を算出。

    Returns:
        dict: {
            "event_name": str,
            "event_date": str (YYYY-MM-DD),
            "days_remaining": int,
            "venue": str,
        } or None
    """
    now = now or datetime.now()
    evt = _get_active_event(event_master)
    if not evt:
        return None

    date_str = str(evt.get('date', '')).split(' ')[0]
    try:
        event_date = datetime.strptime(date_str, '%Y-%m-%d')
    except (ValueError, TypeError):
        return None

    days = (event_date - now).days
    return {
        "event_name": evt.get('name', '不明'),
        "event_date": date_str,
        "days_remaining": max(0, days),
        "venue": evt.get('venue', ''),
    }


# =============================================================
# KPI 2: 目標売上ギャップ
# =============================================================

def calc_sales_gap(master_data):
    """
    目標売上と現在完成額のギャップを算出。
    price > 0 のアイテムのみ対象（鞘は price=0 で自動除外）。

    Returns:
        dict: {
            "target_revenue": int,
            "current_revenue": int,
            "gap": int,
            "progress_ratio": float (0.0 ~ 1.0),
        }
    """
    target_rev = 0
    current_rev = 0

    for item in (master_data or []):
        price = item.get('price', 0)
        if price <= 0:
            continue
        target_rev += item.get('target_quantity', 0) * price
        current_rev += item.get('event_sheet_stock', 0) * price

    progress = current_rev / target_rev if target_rev > 0 else 0.0
    return {
        "target_revenue": target_rev,
        "current_revenue": current_rev,
        "gap": target_rev - current_rev,
        "progress_ratio": min(progress, 1.0),
    }


# =============================================================
# KPI 3: 残り総加工時間 & 最適生産ルート
# =============================================================

def calc_remaining_hours(master_data):
    """
    残り数量 × 工程時間で総残り加工時間を算出。
    さらに「1分あたりの売上貢献額」で効率ランキングを作成。

    Returns:
        dict: {
            "total_nc_hours": float,
            "total_manual_hours": float,
            "total_hours": float,
            "efficiency_ranking": [
                {"name": str, "part": str, "remaining": int,
                 "yen_per_min": float, "total_min": float, "price": int}
            ],  # 上位5件
        }
    """
    total_nc = 0
    total_manual = 0
    efficiency_items = []

    for item in (master_data or []):
        remaining = item.get('remaining', 0)
        if remaining <= 0:
            continue

        nc_min, manual_min, total_min = _calc_item_times(item)
        total_nc += remaining * nc_min
        total_manual += remaining * manual_min

        price = item.get('price', 0)
        # 効率 = 1個あたり売上 / 1個あたり所要時間
        yen_per_min = price / total_min if total_min > 0 else 0

        efficiency_items.append({
            "name": item.get('name', '?'),
            "part": item.get('part', '?'),
            "id": item.get('id', ''),
            "remaining": remaining,
            "yen_per_min": round(yen_per_min, 1),
            "total_min_per_unit": round(total_min, 1),
            "nc_min_per_unit": round(nc_min, 1),
            "manual_min_per_unit": round(manual_min, 1),
            "price": price,
        })

    # 効率順でソート (高い方が優先)
    efficiency_items.sort(key=lambda x: x['yen_per_min'], reverse=True)

    return {
        "total_nc_hours": round(total_nc / 60, 1),
        "total_manual_hours": round(total_manual / 60, 1),
        "total_hours": round((total_nc + total_manual) / 60, 1),
        "efficiency_ranking": efficiency_items[:5],
    }


# =============================================================
# KPI 4: 本日の最適タスク (Go/No-Go)
# =============================================================

def calc_today_tasks(master_data, current_hour=None):
    """
    今から着手すべき作業指示を提示。
    - 20時以降: NCは騒音NG。手作業のみ推奨。
    - 20時前: NC + 手作業 それぞれ推奨。

    Returns:
        dict: {
            "is_night_mode": bool,
            "nc_available": bool,
            "recommended_nc": dict or None,  # NC推奨アイテム
            "recommended_manual": dict or None,  # 手作業推奨アイテム
            "all_done": bool,
            "message": str,
        }
    """
    if current_hour is None:
        current_hour = datetime.now().hour

    is_night = current_hour >= 20 or current_hour < 6
    nc_available = not is_night

    # 残りがあるアイテムを抽出
    remaining_items = []
    for item in (master_data or []):
        rem = item.get('remaining', 0)
        if rem <= 0:
            continue
        nc_min, manual_min, total_min = _calc_item_times(item)
        remaining_items.append({
            "name": item.get('name', '?'),
            "part": item.get('part', '?'),
            "id": item.get('id', ''),
            "remaining": rem,
            "nc_min": nc_min,
            "manual_min": manual_min,
            "total_min": total_min,
            "price": item.get('price', 0),
            "nc_machine_type": item.get('requirements', {}).get('nc_machine_type', 'Both'),
        })

    if not remaining_items:
        return {
            "is_night_mode": is_night,
            "nc_available": nc_available,
            "recommended_nc": None,
            "recommended_manual": None,
            "all_done": True,
            "message": "🎉 全品目の目標を達成済み！",
        }

    # NC推奨: NC時間があるアイテムで、残数が多い順
    nc_candidates = [i for i in remaining_items if i['nc_min'] > 0]
    nc_candidates.sort(key=lambda x: x['remaining'], reverse=True)

    # 手作業推奨: 手作業時間があるアイテムで、残数が多い順
    manual_candidates = [i for i in remaining_items if i['manual_min'] > 0]
    manual_candidates.sort(key=lambda x: x['remaining'], reverse=True)

    recommended_nc = nc_candidates[0] if nc_candidates and nc_available else None
    recommended_manual = manual_candidates[0] if manual_candidates else None

    # メッセージ構築
    if is_night:
        msg = "🌙 夜間モード（20時以降）: NC稼働NG。手作業に集中せよ。"
        if recommended_manual:
            msg += f"\n→ 推奨: {recommended_manual['name']}（{recommended_manual['part']}）の手作業 約{recommended_manual['manual_min']}分/個"
    else:
        msg = "☀️ 日中モード: NC+手作業の並行稼働が可能。"
        parts = []
        if recommended_nc:
            parts.append(f"NC → {recommended_nc['name']}（{recommended_nc['part']}）残{recommended_nc['remaining']}個")
        if recommended_manual:
            parts.append(f"手作業 → {recommended_manual['name']}（{recommended_manual['part']}）残{recommended_manual['remaining']}個")
        if parts:
            msg += "\n→ " + " / ".join(parts)

    return {
        "is_night_mode": is_night,
        "nc_available": nc_available,
        "recommended_nc": recommended_nc,
        "recommended_manual": recommended_manual,
        "all_done": False,
        "message": msg,
    }


# =============================================================
# KPI 5: 材料発注アラート
# =============================================================

def calc_material_alerts(master_data, days_remaining=None, event_master=None):
    """
    材料種別ごとに必要量を算出し、不足予測を提示。

    Returns:
        dict: {
            "materials": {
                "SPF": {"remaining_items": int, "boards_needed": float, "alert": bool},
                ...
            },
            "alerts": [str],  # アラートメッセージ一覧
        }
    """
    if days_remaining is None:
        countdown = calc_countdown(event_master=event_master)
        days_remaining = countdown['days_remaining'] if countdown else 30

    # 材料種別ごとに集計
    material_map = {}  # {material: {"remaining": int, "boards": float, "items": [...]}}

    for item in (master_data or []):
        remaining = item.get('remaining', 0)
        if remaining <= 0:
            continue

        material = item.get('requirements', {}).get('material_type', '不明')
        yield_per_board = item.get('requirements', {}).get('yield', 1) or 1

        if material not in material_map:
            material_map[material] = {"remaining_count": 0, "boards_needed": 0, "items": []}

        material_map[material]["remaining_count"] += remaining
        material_map[material]["boards_needed"] += remaining / yield_per_board
        material_map[material]["items"].append(
            f"{item.get('name', '?')}({item.get('part', '?')}) ×{remaining}"
        )

    # アラート判定
    alerts = []
    materials_out = {}

    for mat, info in material_map.items():
        boards = math.ceil(info['boards_needed'])
        # アラート条件: 必要板数が5枚以上（大量消費材料）
        is_alert = boards >= 5
        materials_out[mat] = {
            "remaining_count": info['remaining_count'],
            "boards_needed": boards,
            "alert": is_alert,
            "items": info['items'],
        }
        if is_alert:
            alerts.append(f"⚠️ {mat}: {boards}枚必要 ({info['remaining_count']}個分)")

    return {
        "materials": materials_out,
        "alerts": alerts,
    }


# =============================================================
# KPI 6: 新作開発枠
# =============================================================

def calc_dev_slot(master_data, event_master=None, now=None):
    """
    進捗に余裕がある場合のみ、新規開発OKサインを表示。

    判定基準:
    - 進捗率 50% 以上 かつ 残り日数 30日以上 → OK
    - それ以外 → NG

    Returns:
        dict: {
            "is_ok": bool,
            "progress_ratio": float,
            "days_remaining": int,
            "message": str,
        }
    """
    gap = calc_sales_gap(master_data)
    progress_ratio = gap['progress_ratio']

    countdown = calc_countdown(now=now, event_master=event_master)
    days_remaining = countdown['days_remaining'] if countdown else 0

    is_ok = progress_ratio >= 0.5 and days_remaining >= 30

    if is_ok:
        msg = f"🟢 新作開発OK！ 進捗{progress_ratio:.0%} / 残{days_remaining}日 → 余裕あり"
    elif progress_ratio >= 0.5:
        msg = f"🟡 進捗は十分({progress_ratio:.0%})だが、残り{days_remaining}日は余裕不足。既存品に集中を推奨。"
    else:
        msg = f"🔴 進捗{progress_ratio:.0%}。既存品の生産に集中せよ。"

    return {
        "is_ok": is_ok,
        "progress_ratio": progress_ratio,
        "days_remaining": days_remaining,
        "message": msg,
    }


# =============================================================
# KPI 7: バーンアップチャート（目標 vs 実績）
# =============================================================

def _load_history_summary():
    """
    history_summary.json を読み込む。
    ローカルファイルが存在しない場合は、Google DriveからHISTORY_SUMMARY_DRIVE_IDを
    使って最新データをダウンロードし、ローカルにキャッシュする。
    """
    path = os.path.join(DATA_DIR, 'history_summary.json')

    # クラウド環境（Streamlit Cloud）かどうかを判定し、クラウドなら常にDriveから最新を取得
    try:
        from logic.drive_utils import _is_cloud
        is_cloud = _is_cloud()
    except Exception:
        is_cloud = False

    # 1. ローカル環境時のみ、ローカルファイルがあればそれを使用
    if not is_cloud and os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass

    # 2. ローカルに無い場合、DriveからHISTORY_SUMMARY_DRIVE_IDでダウンロード
    try:
        from logic.drive_utils import authenticate, download_content, HISTORY_SUMMARY_DRIVE_ID
        if not HISTORY_SUMMARY_DRIVE_ID:
            return []

        service = authenticate()
        if not service:
            return []

        stream = download_content(service, HISTORY_SUMMARY_DRIVE_ID, 'application/json')
        if not stream:
            return []

        data = json.loads(stream.read().decode('utf-8'))

        # ローカルにキャッシュ保存
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass  # キャッシュ失敗は無視

        return data
    except ImportError:
        return []
    except Exception:
        return []


def _calc_burnup_start_date(excel_bytes=None):
    """
    バーンアップチャートの起点日を動的に算出する。

    メニュー.xlsx の「イベントマスタ」シートを読み込み、
    アクティブイベント（H列=True）の直前にある終了済みイベントの
    「開催日(C列) + 日数(D列) - 1」を起点日として返す。

    Args:
        excel_bytes: メニュー.xlsxのバイナリデータ

    Returns:
        str: 起点日 (YYYY-MM-DD) or None
    """
    if not excel_bytes:
        return None

    try:
        # イベントマスタシートを読み込む（1行目=ヘッダー）
        df = pd.read_excel(
            io.BytesIO(excel_bytes if isinstance(excel_bytes, bytes) else excel_bytes),
            sheet_name='イベントマスタ',
            header=0,
        )
        print(f"[_calc_burnup_start_date] イベントマスタ読込: {len(df)}行")

        # アクティブイベント行のインデックスを特定
        # H列「アクティブフラグ」が True のイベントを探す
        active_idx = None
        for idx, row in df.iterrows():
            flag = row.get('アクティブフラグ', '')
            if flag is True or str(flag).strip().lower() == 'true':
                active_idx = idx
                break

        if active_idx is None:
            print("[_calc_burnup_start_date] アクティブイベントが見つかりません")
            return None

        if active_idx == 0:
            print("[_calc_burnup_start_date] アクティブイベントが先頭行のため前イベントなし")
            return None

        # アクティブイベントの1つ前の行（直前の終了済みイベント）
        prev_row = df.iloc[active_idx - 1]
        prev_date = prev_row.get('開催日')
        prev_days = prev_row.get('日数', 1)

        if pd.isna(prev_date):
            print("[_calc_burnup_start_date] 前イベントの開催日が空です")
            return None

        # pandas Timestamp → datetime
        if hasattr(prev_date, 'to_pydatetime'):
            prev_date = prev_date.to_pydatetime()
        elif isinstance(prev_date, str):
            prev_date = datetime.strptime(str(prev_date)[:10], '%Y-%m-%d')

        # 日数のパース（NaN対策）
        try:
            days = int(prev_days) if not pd.isna(prev_days) else 1
        except (ValueError, TypeError):
            days = 1

        # 起点日 = 前イベント開催日 + 日数 - 1 (最終日)
        start_date = prev_date + timedelta(days=days - 1)
        result = start_date.strftime('%Y-%m-%d')
        print(f"[_calc_burnup_start_date] 算出: {prev_row.get('イベント名')} "
              f"開催日={prev_date.strftime('%Y-%m-%d')} + {days}日 - 1 → 起点日={result}")
        return result

    except Exception as e:
        print(f"[_calc_burnup_start_date] エラー: {e}")
        return None


def calc_burnup_data(master_data, event_master=None, excel_bytes=None):
    """
    バーンアップチャート用データを生成。

    1. history_summary.json の details 付きエントリから各時点の完成金額を算出
    2. アクティブイベント日付までの3本の目標ペースラインを生成
    3. 同日に複数スキャンがある場合は最新のみ採用
    4. 起点日はメニュー.xlsxのイベントマスタシートから動的算出

    Args:
        master_data: 商品マスタデータ
        event_master: イベントマスタJSON（オプション）
        excel_bytes: メニュー.xlsxのバイナリデータ（起点日算出用）

    Returns:
        dict: {
            "actual": [{"date": str, "revenue": int}, ...],
            "targets": [
                {"label": "80万目標", "value": 800000},
                {"label": "70万目標", "value": 700000},
                {"label": "60万目標", "value": 600000},
            ],
            "start_date": str,
            "event_date": str,
            "event_name": str,
        } or None
    """
    history = _load_history_summary()
    if not history or not master_data:
        return None

    # master_data から ID→price のマップと目標総売上を作成
    price_map = {}
    valid_target_revenue = 0
    for item in master_data:
        item_id = item.get('id', '')
        price = item.get('price', 0)
        target = item.get('target_quantity', 0)
        if item_id and price > 0:
            price_map[item_id] = price
            valid_target_revenue += target * price

    # 履歴エントリからの完成金額算出（推測計算を廃止、事実行のみ計算）
    daily_data = {}  # {date_str: valid_revenue}
    has_details_flag = set()

    for entry in history:
        # 日付パース
        ts = entry.get('timestamp') or entry.get('date', '')
        if not ts:
            continue

        try:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            try:
                dt = datetime.strptime(str(ts)[:10], '%Y-%m-%d')
            except Exception:
                continue

        date_str = dt.strftime('%Y-%m-%d')

        details = entry.get('details')
        if details:
            # detailsがある場合は、各アイテムの「個数×単価」を合算
            valid_revenue = sum(item_data.get('count', 0) * price_map.get(item_id, 0)
                                for item_id, item_data in details.items() if item_id in price_map)
            daily_data[date_str] = valid_revenue
            has_details_flag.add(date_str)
        # detailsがない推測値の利用（旧合計個数ベース等の推定計算）は行わず無視する（グラフを点のみにする）

    if not daily_data:
        return None

    # 日付順にソート
    sorted_dates = sorted(daily_data.keys())
    
    # start_date: メニュー.xlsxのイベントマスタシートから動的算出
    start_date = _calc_burnup_start_date(excel_bytes)
    # フォールバック: Excel読込失敗時は実績データの最古日付または決め打ち
    if not start_date:
        start_date = "2025-12-14"
        print(f"[calc_burnup_data] フォールバック: 起点日 {start_date} を使用")

    # 起点日の初期資産額を計算（クリマ2512シートの「残数」から）
    initial_revenue = 0
    if excel_bytes:
        try:
            import io
            # C列(ID) と AK列(残数) を取得
            df_cur = pd.read_excel(io.BytesIO(excel_bytes), sheet_name='クリマ2512', usecols="C,AK")
            for _, row in df_cur.iterrows():
                raw_id = row.iloc[0]
                raw_count = row.iloc[1]
                if pd.isna(raw_id): continue
                clean_id = str(raw_id).strip()
                if not clean_id or clean_id not in price_map: continue
                try:
                    count = int(float(raw_count)) if pd.notna(raw_count) else 0
                    if count > 0:
                        initial_revenue += count * price_map[clean_id]
                except:
                    pass
            print(f"[calc_burnup_data] クリマ2512初期資産計算: ¥{initial_revenue:,}")
        except Exception as e:
            print(f"[calc_burnup_data] 初期資産計算エラー: {e}")

    # 起点日データとして確実な値を割り当てる
    daily_data[start_date] = initial_revenue
    
    # ソートし直してactualリストを作成
    sorted_dates = sorted(daily_data.keys())
    actual = [{"date": d, "revenue": daily_data[d]} for d in sorted_dates]

    # イベント情報取得
    countdown = calc_countdown(event_master=event_master)
    if countdown:
        event_date = countdown['event_date']
        event_name = countdown['event_name']
    else:
        event_date = sorted_dates[-1] if sorted_dates else start_date
        event_name = '不明'

    return {
        "actual": actual,
        "targets": [
            {"label": "100% 目標", "value": valid_target_revenue},
            {"label": "80% 目標", "value": int(valid_target_revenue * 0.8)},
            {"label": "60% 目標", "value": int(valid_target_revenue * 0.6)},
        ],
        "start_date": start_date,
        "event_date": event_date,
        "event_name": event_name,
    }


# =============================================================
# KPI 8: バーンダウンチャート（残り総作業時間の推移）
# =============================================================

def calc_burndown_hours(master_data, event_master=None, calendar_data=None):
    """
    残り総作業時間（NC＋手作業）のバーンダウンチャート用データを生成。

    1. master_data から ID→(NC分+手作業分)/個 のマップを構築
    2. history_summary.json の details 付きエントリから、
       各時点の「残り総作業時間」を算出
    3. 理想線: カレンダーの日別空き時間に基づいて減少する曲線
       （カレンダーデータ未連携時は1日8時間のフォールバック）

    Args:
        master_data: 商品マスタデータ
        event_master: イベントマスタJSON（オプション）
        calendar_data: カレンダー統合データ（calendar_agent出力、オプション）
            calendar_data['daily_schedule'] に日別空き時間が含まれる

    Returns:
        dict: {
            "actual": [{"date": str, "remaining_hours": float}, ...],
            "ideal":  [{"date": str, "remaining_hours": float}, ...],
            "daily_capacity": [{"date": str, "capacity_hours": float}, ...],
            "current_remaining_hours": float,
            "ideal_finish_date": str,
            "event_date": str,
            "event_name": str,
            "capacity_source": str,  # "calendar" or "fixed"
        } or None
    """
    if not master_data:
        return None

    # --- 1. ID → 1個あたりの工程時間（分）マップ（NC/手作業分離） ---
    time_map = {}       # {item_id: total_min_per_unit}
    nc_time_map = {}    # {item_id: nc_min_per_unit}
    manual_time_map = {}  # {item_id: manual_min_per_unit}
    for item in master_data:
        item_id = item.get('id', '')
        if not item_id:
            continue
        nc_min, manual_min, total_min = _calc_item_times(item)
        time_map[item_id] = total_min
        nc_time_map[item_id] = nc_min
        manual_time_map[item_id] = manual_min

    # --- 2. 履歴から各時点の残り総作業時間を算出 ---
    history = _load_history_summary()
    if not history:
        # 履歴がなくても現在値だけで理想線は描画可能
        hours_info = calc_remaining_hours(master_data)
        current_hours = hours_info['total_hours']
        if current_hours <= 0:
            return None

        today_str = datetime.now().strftime('%Y-%m-%d')
        actual = [{
            "date": today_str,
            "remaining_hours": current_hours,
            "remaining_nc_hours": hours_info['total_nc_hours'],
            "remaining_manual_hours": hours_info['total_manual_hours'],
        }]
    else:
        # details 付きエントリのみ処理
        daily_hours = {}  # {date_str: {total, nc, manual}}
        for entry in history:
            details = entry.get('details')
            if not details:
                continue

            ts = entry.get('timestamp') or entry.get('date', '')
            if not ts:
                continue
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                try:
                    dt = datetime.strptime(str(ts)[:10], '%Y-%m-%d')
                except Exception:
                    continue

            date_str = dt.strftime('%Y-%m-%d')

            # 残り作業時間 = Σ(max(0, target - count) × 1個あたり時間)
            total_remaining_min = 0
            nc_remaining_min = 0
            manual_remaining_min = 0
            for item_id, item_data in details.items():
                target = item_data.get('target', 0)
                count = item_data.get('count', 0)
                remaining = max(0, target - count)
                total_remaining_min += remaining * time_map.get(item_id, 0)
                nc_remaining_min += remaining * nc_time_map.get(item_id, 0)
                manual_remaining_min += remaining * manual_time_map.get(item_id, 0)

            remaining_hours = round(total_remaining_min / 60, 1)
            nc_hours = round(nc_remaining_min / 60, 1)
            manual_hours = round(manual_remaining_min / 60, 1)
            # 同一日は最新値で上書き（後のエントリが最新）
            daily_hours[date_str] = {
                'total': remaining_hours,
                'nc': nc_hours,
                'manual': manual_hours,
            }

        if not daily_hours:
            # detailsのある履歴がなくても現在値で表示
            hours_info = calc_remaining_hours(master_data)
            current_hours = hours_info['total_hours']
            if current_hours <= 0:
                return None
            today_str = datetime.now().strftime('%Y-%m-%d')
            actual = [{
                "date": today_str,
                "remaining_hours": current_hours,
                "remaining_nc_hours": hours_info['total_nc_hours'],
                "remaining_manual_hours": hours_info['total_manual_hours'],
            }]
        else:
            sorted_dates = sorted(daily_hours.keys())
            actual = [{
                "date": d,
                "remaining_hours": daily_hours[d]['total'],
                "remaining_nc_hours": daily_hours[d]['nc'],
                "remaining_manual_hours": daily_hours[d]['manual'],
            } for d in sorted_dates]

    # --- 3. 現在の残り総作業時間（最新の actual ポイント） ---
    current_hours = actual[-1]['remaining_hours']
    start_date_str = actual[-1]['date']

    # --- 4. 理想線: カレンダー連動 or 固定8h/日 ---
    HOURS_PER_DAY_FALLBACK = 8

    # カレンダーデータから日別キャパシティマップを構築
    calendar_capacity_map = {}  # {date_str: total_free_hours}
    capacity_source = "fixed"
    if calendar_data and isinstance(calendar_data, dict):
        daily_schedule = calendar_data.get('daily_schedule', [])
        if daily_schedule:
            capacity_source = "calendar"
            for day_info in daily_schedule:
                date_key = day_info.get('date', '')
                if date_key:
                    calendar_capacity_map[date_key] = day_info.get('total_free_hours', 0)

    try:
        start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
    except (ValueError, TypeError):
        start_dt = datetime.now()

    # 理想線 & 日別キャパシティを同時に構築
    ideal = []
    daily_capacity = []
    remaining = current_hours
    d = 0
    MAX_DAYS = 365  # 無限ループ防止

    # 初期ポイント（現在の残り時間）
    ideal.append({
        "date": start_dt.strftime('%Y-%m-%d'),
        "remaining_hours": round(remaining, 1),
    })

    while remaining > 0 and d < MAX_DAYS:
        d += 1
        day_dt = start_dt + timedelta(days=d)
        date_str = day_dt.strftime('%Y-%m-%d')

        # その日のキャパシティを取得（カレンダー優先、なければフォールバック）
        if date_str in calendar_capacity_map:
            day_capacity = calendar_capacity_map[date_str]
        else:
            day_capacity = HOURS_PER_DAY_FALLBACK

        daily_capacity.append({
            "date": date_str,
            "capacity_hours": round(day_capacity, 1),
        })

        remaining = max(0, remaining - day_capacity)
        ideal.append({
            "date": date_str,
            "remaining_hours": round(remaining, 1),
        })

    days_to_finish = d
    finish_dt = start_dt + timedelta(days=days_to_finish)
    ideal_finish_date = finish_dt.strftime('%Y-%m-%d')

    # --- 5. イベント情報 ---
    countdown = calc_countdown(event_master=event_master)
    if countdown:
        event_date = countdown['event_date']
        event_name = countdown['event_name']
    else:
        event_date = ideal_finish_date
        event_name = '不明'

    # --- 6. 売上マイルストーン（Y軸上の目安ライン） ---
    # 全目標達成時の「初期総作業時間」と「総売上」を算出
    initial_total_min = 0
    total_target_revenue = 0
    for item in master_data:
        target_qty = item.get('target_quantity', 0)
        if target_qty <= 0:
            continue
        item_id = item.get('id', '')
        per_unit_min = time_map.get(item_id, 0)
        initial_total_min += target_qty * per_unit_min
        price = item.get('price', 0)
        if price > 0:
            total_target_revenue += target_qty * price

    initial_total_hours = round(initial_total_min / 60, 1)

    # 売上M円に達した時の残り作業時間（目安）
    # 線形近似: 残り時間 = 初期総時間 × (1 - M / 総売上)
    milestones = []
    MILESTONE_TARGETS = [
        {"revenue": 600000, "label": "🥉 60万円突破", "color": "#cd7f32"},  # 銅
        {"revenue": 700000, "label": "🥈 70万円突破", "color": "#c0c0c0"},  # 銀
        {"revenue": 800000, "label": "🥇 80万円突破", "color": "#ffd700"},  # 金
    ]
    if total_target_revenue > 0 and initial_total_hours > 0:
        for m in MILESTONE_TARGETS:
            rev = m['revenue']
            if rev > total_target_revenue:
                continue  # 目標総売上を超えるマイルストーンはスキップ
            remaining_h = round(initial_total_hours * (1 - rev / total_target_revenue), 1)
            if remaining_h >= 0:
                milestones.append({
                    "revenue": rev,
                    "remaining_hours": remaining_h,
                    "label": m['label'],
                    "color": m['color'],
                })

    return {
        "actual": actual,
        "ideal": ideal,
        "daily_capacity": daily_capacity,
        "current_remaining_hours": current_hours,
        "current_nc_hours": actual[-1].get('remaining_nc_hours', 0),
        "current_manual_hours": actual[-1].get('remaining_manual_hours', 0),
        "initial_total_hours": initial_total_hours,
        "total_target_revenue": total_target_revenue,
        "milestones": milestones,
        "ideal_finish_date": ideal_finish_date,
        "event_date": event_date,
        "event_name": event_name,
        "capacity_source": capacity_source,
    }
