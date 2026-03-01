"""
zeus_chat.py - 軍師Zeus チャットロジック

マスタデータと在庫状況をコンテキストとしてGemini APIに渡し、
「アトラス工房の軍師Zeus」としてユーザーの質問に回答する。

Uses: google-genai (新SDK)
"""

import json
import logging
import os
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None
    logging.warning("google-genai library not found. Chat features will be disabled, but search logic is available.")
import pandas as pd

OUTPUT_VERSION = "2026-02-15 v2 (Detailed Process Times)"

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
HISTORY_PATH = os.path.join(DATA_DIR, 'history_summary.json')

def load_event_master():
    """Zeus監視用のイベントマスタを読み込む"""
    event_path = os.path.join(DATA_DIR, 'event_master.json')
    if not os.path.exists(event_path):
        return []
    try:
        with open(event_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Event master load error: {e}")
        return []


def load_history_stats():
    """
    【最終仕様】起点日を type:"initial" から動的取得し、全ログ通算のペースを算出。
    
    仕様:
      起点 = history_summary.json 内の type:"initial" レコードの date
      ペース = (最新total_current - initial.total_current) / (今日 - 起点日)
    
    Returns:
        dict: {pace, last_count, last_date, is_long_term,
               origin_date, origin_count, origin_details} or None
    """
    if not os.path.exists(HISTORY_PATH):
        return None
    
    try:
        with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
            history = json.load(f)
            
        if not history:
            return None

        from datetime import datetime

        # ★ 仕様: type="initial" から起点データを動的取得（ハードコード厳禁）
        initial_entry = None
        for h in history:
            if h.get('type') == 'initial':
                initial_entry = h
                break
        
        if not initial_entry:
            # initial が無い場合、最古のエントリをフォールバックとする
            logger.warning("type='initial' が見つかりません。最古のエントリを起点とします。")
            initial_entry = history[0]

        # 起点日のパース
        origin_ts = initial_entry.get('timestamp') or initial_entry.get('date')
        if not origin_ts:
            return None
        try:
            origin_dt = datetime.fromisoformat(origin_ts.replace('Z', '+00:00'))
        except Exception:
            return None
        
        origin_count = initial_entry.get('total_current', 0)
        origin_details = initial_entry.get('details', {})

        # 全エントリに _dt を付与
        for h in history:
            ts = h.get('timestamp') or h.get('date')
            if not ts:
                continue
            try:
                h['_dt'] = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except Exception:
                continue

        valid = [h for h in history if '_dt' in h]
        if len(valid) < 2:
            return None
            
        valid.sort(key=lambda x: x['_dt'])
        current = valid[-1]

        # ★ 仕様: (最新total_current - initial.total_current) / (今日 - 起点日)
        now = datetime.now(origin_dt.tzinfo)  # タイムゾーン一致
        total_days = (now - origin_dt).days
        if total_days <= 0:
            total_days = 1
        
        total_produced = current.get('total_current', 0) - origin_count
        pace_per_day = total_produced / total_days
        
        # 直近2点間のペース（参考値）
        is_long_term = False
        if len(valid) >= 2:
            prev = valid[-2]
            recent_days = (current['_dt'] - prev['_dt']).days
            if recent_days <= 0:
                recent_days = 1
            recent_diff = current.get('total_current', 0) - prev.get('total_current', 0)
            recent_pace = recent_diff / recent_days
            
            if 0 < recent_pace <= 10:
                pace_per_day = recent_pace
            else:
                is_long_term = True

        return {
            "pace": round(pace_per_day, 2),
            "last_count": current.get('total_current', 0),
            "last_date": current['_dt'].strftime('%Y-%m-%d'),
            "is_long_term": is_long_term,
            # ★ 起点情報も返す（build_system_prompt で使用）
            "origin_date": origin_dt.strftime('%Y-%m-%d'),
            "origin_count": origin_count,
            "origin_details": origin_details,
        }

    except Exception as e:
        logger.error(f"履歴統計の計算失敗: {e}")
        return None


def get_daily_achievements():
    """本日の成果（在庫増分）を計算して文字列で返す"""
    try:
        import json
        import os
        from datetime import datetime, timedelta

        # history_path check (uses global constant)
        if not os.path.exists(HISTORY_PATH):
            return "★本日の成果: （履歴データなし）"

        with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
            history = json.load(f)

        if not history:
            return "★本日の成果: （履歴データなし）"

        # 日付順にソート
        parsed_history = []
        for h in history:
            ts_str = h.get('timestamp') or h.get('date', '')
            if not ts_str: continue
            try:
                # ISOフォーマット対応 (Z除去)
                dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                h['_dt'] = dt
                parsed_history.append(h)
            except:
                continue
        
        parsed_history.sort(key=lambda x: x['_dt'])

        if not parsed_history:
            return "★本日の成果: （有効な履歴なし）"

        # ★ details が空でないログのみ有効とする（古い形式のエントリをスキップ）
        valid_history = [h for h in parsed_history if h.get('details') and len(h.get('details', {})) > 0]
        
        if len(valid_history) < 2:
            return "★本日の成果: （比較用の詳細データ不足 - details付きエントリが2件以上必要）"

        # ★ 仕様: 最新のログを「現在の状態」とする
        latest = valid_history[-1]
        latest_date = latest['_dt'].date()
        
        # 比較対象（昨日以前の最後のログ）を探す
        base_entry = None
        for h in reversed(valid_history[:-1]):
            if h['_dt'].date() < latest_date:
                base_entry = h
                break
        
        # もし昨日以前のログがなければ、記録上の最初のログを基準にする
        if not base_entry:
            base_entry = valid_history[0]
            
        latest_details = latest.get('details', {})
        base_details = base_entry.get('details', {})

        # 差分計算
        achievements = []
        
        # マスタデータをロードして名前解決
        master_map = {}
        try:
            master_path = os.path.join(DATA_DIR, 'production_master.json')
            if os.path.exists(master_path):
                with open(master_path, 'r', encoding='utf-8') as f:
                    m_data = json.load(f)
                    for m in m_data:
                        mid = str(m.get('id', '')).strip()
                        if mid:
                            master_map[mid] = {
                                'name': m.get('name', mid),
                                'part': m.get('part', '')
                            }
        except:
            pass
        
        # 最新にあるIDを走査
        for item_id, info in latest_details.items():
            # infoは {"count": 10, ...} 形式または数値
            current_count = 0
            if isinstance(info, dict):
                current_count = info.get('count', 0)
            elif isinstance(info, (int, float, str)):
                 try: current_count = int(info)
                 except: pass

            # 比較対象
            base_info = base_details.get(item_id, {})
            base_count = 0
            if isinstance(base_info, dict):
                base_count = base_info.get('count', 0)
            elif isinstance(base_info, (int, float, str)):
                 try: base_count = int(base_info)
                 except: pass
            
            diff = current_count - base_count
            
            # 増加分のみ報告
            if diff > 0:
                item_info = master_map.get(item_id, {})
                if isinstance(item_info, dict):
                    name = item_info.get('name', item_id)
                    part = item_info.get('part', '')
                    display_name = f"{name} ({part})" if part else name
                else:
                    display_name = str(item_info)
                achievements.append(f"{display_name} +{diff}")
        
        if not achievements:
            return "★本日の成果: なし（今のところ在庫の増加はありません）"
            
        return "★本日の成果: " + " / ".join(achievements) + "！！"

    except Exception as e:
        logger.error(f"成果計算エラー: {e}")
        return f"★本日の成果: (計算エラー: {e})"


def build_system_prompt(master_data: list, inventory_df: pd.DataFrame = None, current_event_name: str = None, all_event_names: list = None, user_message: str = None) -> str:
    """
    マスタデータと在庫状況からシステムプロンプトを構築する。

    Args:
        master_data: load_master_json() の出力（商品リスト）
        inventory_df: calculate_inventory() の出力（在庫DataFrame）
        current_event_name: 現在選択中のイベントシート名（例: "クリマ2605"）
        all_event_names: 全イベントシート名のリスト（例: ["クリマ2605", "デザフェス58"]）

    Returns:
        str: システムプロンプト文字列
    """
    
    # --- 商品マスタの要約テキスト & 残作業時間の計算 ---
    product_lines = []
    
    total_remaining_count = 0
    total_target_count = 0
    
    # 時間計算用
    total_nc_min = 0
    total_manual_min = 0
    
    if master_data:
        for item in master_data:
            nc = item.get("process", {}).get("nc", {})
            nc_unit = (
                nc.get("front_rough_min", 0)
                + nc.get("front_finish_min", 0)
                + nc.get("back_rough_min", 0)
                + nc.get("back_finish_min", 0)
            )
            prep = item.get("process", {}).get("prep", {})
            assembly = item.get("process", {}).get("assembly", {})
            manual = item.get("process", {}).get("manual", {})

            manual_unit = (
                prep.get("unit_min", 0) # setupは無視
                + assembly.get("cut_off_min", 0)
                + assembly.get("bonding_min", 0)
                + manual.get("fitting_min", 0)
                + manual.get("machine_work_min", 0)
                + manual.get("sanding_min", 0)
                + manual.get("assembly_min", 0)
            )
            all_unit = nc_unit + manual_unit # 乾燥除く

            reqs = item.get("requirements", {})
            
            # --- 残数集計 ---
            tgt = item.get('target_quantity', 0)
            rem = item.get('remaining', 0)
            total_target_count += tgt
            total_remaining_count += rem
            
            # --- 残時間集計 ---
            # 不足数 * 単価時間
            if rem > 0:
                total_nc_min += rem * nc_unit
                total_manual_min += rem * manual_unit

            # --- イベント情報の動的注入 ---
            event_data = item.get('event_data', {})
            event_info_str = ""
            
            if event_data:
                details = []
                for k, v in event_data.items():
                    details.append(f"{k}: {v}")
                
                if rem > 0:
                     details.append(f"残数: {rem}")

                if details:
                    event_info_str = f"   ★イベント情報: [{', '.join(details)}]"

            line = (
                f"- **{item.get('name', '?')}** ({item.get('part', '?')}) "
                f"[カテゴリ: {item.get('category', '?')}]\n"
                f"  ID: {item.get('id', '?')} / 単価: ¥{item.get('price', 0):,} / "
                f"マスタ在庫: {item.get('current_stock', 0)} {event_info_str}\n"
                f"  材料: {reqs.get('material_type', '?')} / "
                f"NCマシン: {reqs.get('nc_machine_type', '?')} / "
                f"取数: {reqs.get('yield', 1)}\n"
                f"  【工程時間(分)】\n"
                f"    生地単体{prep.get('unit_min', 0)} / "
                f"    NC合計: {nc_unit}分 (表粗:{nc.get('front_rough_min', 0)} / 表仕:{nc.get('front_finish_min', 0)} / 裏粗:{nc.get('back_rough_min', 0)} / 裏仕:{nc.get('back_finish_min', 0)})\n"
                f"    組付合計: {assembly.get('cut_off_min', 0)+assembly.get('bonding_min', 0)} "
                f"(切断:{assembly.get('cut_off_min', 0)} / 接着:{assembly.get('bonding_min', 0)}) / "
                f"    手加工合計: {manual_unit - (prep.get('unit_min',0)+assembly.get('cut_off_min',0)+assembly.get('bonding_min',0))} "
                f"(準備:{prep.get('unit_min', 0)} / 嵌合:{manual.get('fitting_min', 0)} / 機械:{manual.get('machine_work_min', 0)} / 研磨:{manual.get('sanding_min', 0)} / 組立:{manual.get('assembly_min', 0)}) \n"
                f"  ⏱ 全工程合計(乾燥除く): {all_unit}分"
            )
            product_lines.append(line)

    product_context = "\n".join(product_lines) if product_lines else "（マスタデータなし）"
    
    # 合計時間 (時間単位)
    total_remaining_hours = (total_nc_min + total_manual_min) / 60
    
    # プリフォーマット（SyntaxError回避のため）
    nc_str = f"{total_nc_min / 60:.1f}"
    manual_str = f"{total_manual_min / 60:.1f}"
    
    # 複雑なF-stringを回避するために外で定義
    time_info_line = f"- **残り総作業時間: {total_remaining_hours:.1f} 時間** (NC: {nc_str}h / 手: {manual_str}h)"

    # --- マスタ検索用マップ作成 (ID -> Item) ---
    master_map = {str(item.get('id', '')): item for item in master_data if item.get('id')}

    # --- 在庫状況の要約テキスト ---
    inventory_context = "（在庫データなし）"
    if inventory_df is not None and not inventory_df.empty:
        inv_lines = []
        for _, row in inventory_df.iterrows():
            name = row.get("商品名", "?")
            part_val = row.get("部位", "?") # Using '部位' for consistency check if needed, or row key
            # inventory_df is from calculate_inventory, which likely has 'ID' or 'id'.
            # Let's check inventory.py -> It preserves ID if master has it.
            # Assuming row has an identifier or we match by Name/Part.
            # Actually, `inventory_df` usually has the same index or columns as master DF if merged.
            # But let's look at `calculate_inventory` return. It returns a DF with "商品名", "部位", "ID" etc.
            
            # Try to find matching master item to get process times
            # Prefer ID match
            row_id = str(row.get('ID', '')).strip()
            master_item = master_map.get(row_id)
            
            # Fallback: Name match (less reliable but okay for now)
            if not master_item:
                # simple name search
                pass 

            nc_ts = 0
            man_ts = 0
            
            if master_item:
                # Calculate times
                proc = master_item.get('process', {})
                n = proc.get('nc', {})
                nc_ts = (n.get('front_rough_min', 0) + n.get('front_finish_min', 0) + 
                         n.get('back_rough_min', 0) + n.get('back_finish_min', 0))
                
                p = proc.get('prep', {})
                a = proc.get('assembly', {})
                m = proc.get('manual', {})
                man_ts = (p.get('unit_min', 0) + a.get('cut_off_min', 0) + a.get('bonding_min', 0) +
                          m.get('fitting_min', 0) + m.get('machine_work_min', 0) + m.get('sanding_min', 0) + m.get('assembly_min', 0))

            body = row.get("本体", 0)
            sheath = row.get("鞘", 0)
            status = row.get("status_text", "?")
            confirmed = row.get("確定数", 0)
            sales = row.get("販売数", 0)
            
            inv_lines.append(
                f"- {name}: 本体={body}, 鞘={sheath}, "
                f"確定数={confirmed}, 販売数={sales}, ステータス={status} "
                f"[NC: {nc_ts}分 / 手: {man_ts}分]"
            )
        inventory_context = "\n".join(inv_lines)
    # ================================================================
    # ★ 仕様書準拠: Python側で全計算を確定し、プロンプトに注入
    # ================================================================
    from datetime import datetime, timedelta
    now = datetime.now()
    today_str = now.strftime('%Y/%m/%d')
    
    # --- A. 起点日の動的取得 (ハードコード厳禁) ---
    stats = load_history_stats()
    daily_pace = stats['pace'] if stats else 0
    is_long_term = stats.get('is_long_term', False) if stats else False
    origin_date_str = stats.get('origin_date', '不明') if stats else '不明'
    origin_count = stats.get('origin_count', 0) if stats else 0
    
    # --- B. IDによる精密マージ (production_master × history initial) ---
    # load_history_stats() が返す origin_details を利用
    origin_details = stats.get('origin_details', {}) if stats else {}
    
    merge_lines = []
    for item in (master_data or []):
        item_id = str(item.get('id', '')).strip()
        if not item_id:
            continue
        target = item.get('target_quantity', 0)
        current = item.get('current_stock', 0)
        
        # 起点在庫 (IDベースでマージ)
        init_info = origin_details.get(item_id, {})
        init_count = init_info.get('count', 0) if isinstance(init_info, dict) else 0
        
        produced = current - init_count  # 起点からの生産数
        remaining = max(0, target - current)
        
        merge_lines.append(
            f"  {item.get('name', '?')} ({item.get('part', '?')}): "
            f"ID={item_id}, 起点在庫={init_count}, 現在={current}, "
            f"目標={target}, 生産数={produced}, 残={remaining}"
        )
    
    merge_context = "\n".join(merge_lines) if merge_lines else "（マージデータなし）"
    
    # --- C. 不足工数の精密算出 (Pythonが完遂) ---
    # total_nc_min, total_manual_min, total_remaining_count は既にL230-L310で計算済み
    
    # --- D. 未来予測 (工程時間ベース) ---
    prediction_msg = "データ不足のため予測不能"
    reality_check_msg = ""
    DAILY_WORK_HOURS = 8.0
    
    if daily_pace > 0 and total_remaining_count > 0:
        avg_hours_per_item = total_remaining_hours / total_remaining_count if total_remaining_count > 0 else 0
        
        days_needed_by_pace = total_remaining_count / daily_pace
        days_needed_by_hours = total_remaining_hours / DAILY_WORK_HOURS if DAILY_WORK_HOURS > 0 else float('inf')
        
        days_needed = max(days_needed_by_pace, days_needed_by_hours)
        finish_date = now + timedelta(days=days_needed)
        
        estimated_daily_hours = daily_pace * avg_hours_per_item
        
        pace_type_str = "長期平均" if is_long_term else "直近実績"
        prefix_msg = f"（{pace_type_str}ベース）" if is_long_term else ""
        
        # ★ 期限も動的に（イベントマスタのアクティブ最遠期限を取得可能だが、ここでは保守的に固定）
        # 将来的にはイベントマスタから動的に取得すべき
        # 暫定: イベントマスタにアクティブイベントがあればその開催日を期限にする
        event_master = load_event_master()
        deadline = None
        deadline_event_name = ""
        if event_master:
            for evt in event_master:
                if evt.get('is_active', False):
                    date_str = evt.get('date', '')
                    if date_str:
                        try:
                            d_str = str(date_str).replace('/', '-').split(' ')[0]
                            deadline = datetime.strptime(d_str, '%Y-%m-%d')
                            deadline_event_name = evt.get('name', '?')
                            break
                        except ValueError:
                            pass
        
        if not deadline:
            deadline = datetime(2026, 5, 5)  # フォールバック
            deadline_event_name = "最終期限"

        remaining_days_to_deadline = (deadline - now).days

        if finish_date <= deadline:
            prediction_msg = f"{prefix_msg}現在のペース({daily_pace:.1f}個/日)なら {finish_date.strftime('%Y-%m-%d')} に完了予定。{deadline_event_name}({deadline.strftime('%Y-%m-%d')})まで{remaining_days_to_deadline}日あり、間に合う見込み。"
        else:
            overshoot_days = (finish_date - deadline).days
            prediction_msg = f"{prefix_msg}現在のペース({daily_pace:.1f}個/日)だと {finish_date.strftime('%Y-%m-%d')} 完了予定で、{deadline_event_name}({deadline.strftime('%Y-%m-%d')})より{overshoot_days}日超過..."
        
        if estimated_daily_hours > 12.0:
            reality_check_msg = f"⚠️ 警告: 現在の日産ペース({daily_pace:.1f}個)を維持するには、1日約{estimated_daily_hours:.1f}時間の作業が必要。無理は禁物です。"

    elif total_remaining_count <= 0:
        prediction_msg = "全目標達成済み！勝利だ！"
    elif daily_pace <= 0:
        prediction_msg = "生産ペースが計測できないため予測不能（まずは作業を開始し、データを蓄積せよ）"

    # --- ユーザーの関心事項（検索・合算ロジック） ---
    search_context = ""
    if user_message:
        found_items = search_products_by_query(master_data, user_message)
        if found_items:
            search_context = build_search_context(found_items)
            print(f"--- [Zeus Search] Found {len(found_items)} items for query ---")

    # --- 本日の成果 ---
    achievements_str = get_daily_achievements()

    # --- ★ カレンダー空き時間 & Google Tasks の読み込み ---
    calendar_context = ""
    tasks_context = ""
    cal_data_path = os.path.join(DATA_DIR, 'atlas_integrated_data.json')
    if os.path.exists(cal_data_path):
        try:
            with open(cal_data_path, 'r', encoding='utf-8') as f:
                cal_data = json.load(f)
            
            # 直近1週間の日別空き時間を抽出
            daily_schedule = cal_data.get('daily_schedule', [])
            if daily_schedule:
                today_date = now.strftime('%Y-%m-%d')
                week_slots = []
                for slot in daily_schedule[:7]:  # 直近7日分
                    d = slot.get('date', '')
                    if d < today_date:
                        continue
                    dow = slot.get('day_of_week', '?')
                    free_h = slot.get('total_free_hours', 0)
                    blocked = slot.get('is_blocked', False)
                    blocks = slot.get('free_blocks', [])
                    
                    if blocked:
                        week_slots.append(f"  {d}({dow}): ■終日ブロック（予定あり）")
                    else:
                        block_str = ', '.join([f"{b['start']}-{b['end']}({b['hours']}h)" for b in blocks[:4]])
                        week_slots.append(f"  {d}({dow}): 空き{free_h}h [{block_str}]")
                
                if week_slots:
                    calendar_context = "\n".join(week_slots)
            
            # Google Tasks（期日付き）
            google_tasks = cal_data.get('google_tasks', [])
            if google_tasks:
                task_lines = []
                for t in google_tasks[:10]:
                    days_until = t.get('days_until')
                    urgency = '🚨' if days_until is not None and days_until <= 3 else '📋'
                    days_label = f"あと{days_until}日" if days_until is not None else '期日不明'
                    task_lines.append(f"  {urgency} {t['title']} — 期日: {t.get('due_date', '?')} ({days_label})")
                tasks_context = "\n".join(task_lines)
        except Exception as e:
            logger.error(f"カレンダーデータ読み込みエラー: {e}")

    # --- ★ event_master.json を Raw JSON として流し込み（加工禁止） ---
    if not event_master:
        event_master = load_event_master()
    
    event_raw_json = "（event_master.json が見つかりません）"
    if event_master:
        try:
            event_raw_json = json.dumps(event_master, ensure_ascii=False, indent=2)
        except Exception:
            event_raw_json = str(event_master)

    # ================================================================
    # ★ System Prompt Construction (仕様書: 日付→確定サマリー→Raw生データ)
    # ================================================================
    system_prompt = f"""
## 最重要: 日付情報
- 本日の日付: {today_str}
- プロジェクト起点日: {origin_date_str}
- 起点からの経過日数: {(now - datetime.strptime(origin_date_str, '%Y-%m-%d')).days if origin_date_str != '不明' else '不明'}日

## Python計算済み確定サマリー（AIはこの数値を信頼せよ。自力で再計算するな）
- 目標総数: {total_target_count} 個
- 現在の総在庫: {stats['last_count'] if stats else '不明'} 個
- 現在の残数: {total_remaining_count} 個
{time_info_line}
- 起点時の総在庫: {origin_count} 個
- 起点からの総生産数: {(stats['last_count'] - origin_count) if stats else '不明'} 個
- 平均生産ペース: {daily_pace:.1f} 個/日 ({'長期平均' if is_long_term else '直近実績'})
- 完了予測: {prediction_msg}
{f'- {reality_check_msg}' if reality_check_msg else ''}

{achievements_str}

## IDベース マージ結果 (production_master × history_summary[initial])
{merge_context}

あなたはアトラス工房の主、yjing（イジン）を支える「熟練の軍師Zeus」です。
以下のガイドラインに従って、職人の相棒として振る舞ってください。

1. 性格と口調:
   - 事務的な【現状】【予測】といった見出しは極力使わず、自然な対話形式で報告せよ。
   - yjingの実力と情熱を尊重しつつ、データに基づいた冷静な助言を行え。
   - 語尾は「〜ですな」「〜でしょう」「〜だ」など、落ち着いた軍師風にせよ。

2. 検索と集計（重要！）:
   - ユーザーが商品名の一部（例：「伝説剣」）を言及した場合、以下の【ユーザーの関心事項】セクションにあるデータを最優先で参照せよ。
   - 該当データが複数ある場合（例：長・短、本体・鞘）、個別の数値を羅列するだけでなく、「合計」の数値をまず答えよ。
   - その後、必要に応じて内訳（「長が〇個、短が〇個」など）を補足せよ。

3. 計算の禁止:
   - 上記「Python計算済み確定サマリー」の数値を絶対正とせよ。自力で再計算するな。
   - 工数、ペース、予測はPython側で確定済み。AIはこれを信頼して報告するだけでよい。

4. 労働基準:
   - 人間の1日は24時間だが、稼働時間は「1日8時間」を基準として納期を考えよ。
   - 物理的に不可能なスケジュール（1日20時間労働など）は警告せよ。

5. 呼称: ユーザーを必ず「yjing」と呼べ。「アトラス」はアプリ名である。

6. カレンダー連携スケジュール提案（重要！）:
   - 下記「カレンダー空き時間」セクションのデータと、各商品の加工時間マスタを照らし合わせよ。
   - その日の空き枠にジャストフィットする具体的な作業（NC放置と手作業の組み合わせ）を提案せよ。
   - 例: 「明日は9:00-13:00に4時間の空きがある。NCにロト剣本体の粗削り(110分)をセットし、その間に伝説剣の鞘ヤスリがけ(40分×2個)を進めれば、4時間枠を最大活用できる。」
   - NCは無人運転可能であることを考慮し、NC加工中に手作業を並行する提案を優先せよ。


【ユーザーの関心事項（検索結果）】
{search_context if search_context else "（特になし。全体を見て回答せよ）"}

[イベント商品マスタ（目標・進捗含む）]
{product_context}

[現在の在庫詳細]
{inventory_context}

## イベントマスタ 生データ (event_master.json) ※未加工
以下はevent_master.jsonの生データである。応募締切やイベント日程は、この生データから自力で読み取れ。
```json
{event_raw_json}
```

## カレンダー空き時間（直近1週間の日別実質空き）
{calendar_context if calendar_context else '（カレンダーデータ未取得。scripts/calendar_sync.py を実行せよ）'}

## Google Tasks（期日付きタスク）
{tasks_context if tasks_context else '（期日付きタスクなし）'}

## 禁止事項
- 冗長な挨拶や前置きは省略せよ。「お疲れ様です」不要。いきなり本題に入れ。
- 聞かれていないマスタの詳細スペックをダラダラ列挙するな。
- 感情論ではなく数字で語れ。ただし「現実チェック」の警告がある場合は必ず伝えよ。
"""

    # --- 視界の確保: 生成されたプロンプトをログに出力 ---
    print("--- [Zeus Logic] System Prompt Context Dump ---")
    try:
        print(system_prompt)
    except UnicodeEncodeError:
        import sys
        encoding = sys.stdout.encoding or 'utf-8'
        print(system_prompt.encode(encoding, errors='replace').decode(encoding))
    print("-----------------------------------------------")
    
    return system_prompt

def search_products_by_query(master_data, query):
    """
    クエリ（ユーザーメッセージ）に含まれる単語に基づいてマスタデータを検索する。
    """
    if not query or not master_data:
        return []
    
    # クエリの前処理 (スペース除去、全角半角統一)
    normalized_query = query.lower().replace("　", " ").replace(" ", "")
    
    hits = []
    
    # 除外ワード（これらだけで検索しないように）
    STOP_WORDS = ["進捗", "状況", "どう", "教えて", "在庫", "は", "が", "の", "？", "?", "合計", "全部", "工数", "時間", "何分", "どれくらい"]
    
    if normalized_query in STOP_WORDS:
        return []
    
    for item in master_data:
        # マスタ側のデータも正規化
        raw_name = item.get('name', '')
        raw_part = item.get('part', '')
        raw_cat = item.get('category', '')
        
        norm_name = raw_name.lower().replace("　", "").replace(" ", "")
        norm_part = raw_part.lower().replace("　", "").replace(" ", "")
        norm_cat = raw_cat.lower().replace("　", "").replace(" ", "")
        
        is_hit = False
        
        # 1. 完全一致・包含 (双方向)
        # "伝説剣" (query) -> "伝説剣長" (product): query in name
        if len(normalized_query) >= 1 and normalized_query in norm_name:
            is_hit = True
        
        # "伝説剣長" (product) -> "伝説剣　長の..." (query): name in query
        if len(norm_name) >= 1 and norm_name in normalized_query:
            is_hit = True

        # 2. カテゴリ・部位の部分一致
        if len(normalized_query) >= 1 and normalized_query in norm_cat: is_hit = True
        if len(normalized_query) >= 1 and normalized_query in norm_part: is_hit = True 
        
        # 3. 逆に、カテゴリ等がクエリに含まれているか
        if len(norm_cat) >= 1 and norm_cat in normalized_query: is_hit = True
        
        if is_hit:
            # 重複チェックしないと複数回ヒットする可能性あるので
            if item not in hits:
                hits.append(item)

    return hits

def build_search_context(items):
    """
    検索ヒット商品群から、Zeus用のコンテキストテキストを生成する。
    合算値と内訳を見やすく整形する。
    また、各商品の加工時間（NC、手作業）も計算して付与する。
    """
    if not items:
        return ""
    
    total_target = sum(i.get('target_quantity', 0) for i in items)
    total_current = sum(i.get('current_stock', 0) for i in items)
    total_remaining = sum(i.get('remaining', 0) for i in items)
    
    # カテゴリや名前の傾向を見る
    names = sorted(list(set([i.get('name') for i in items])))
    name_str = "/".join(names[:3])
    if len(names) > 3: name_str += "..."
    
    context = f"★検索ヒット: 計{len(items)}件 (代表: {name_str})\n"
    context += f"  - 合計目標: {total_target} / 合計在庫: {total_current} / 合計残数: {total_remaining}\n"
    context += "  - 内訳(詳細スペック含む):\n"
    
    for item in items:
        # 工数計算
        proc = item.get('process', {})
        nc = proc.get('nc', {})
        prep = proc.get('prep', {})
        assembly = proc.get('assembly', {})
        manual = proc.get('manual', {})

        nc_total = (
            nc.get('front_rough_min', 0) + 
            nc.get('front_finish_min', 0) + 
            nc.get('back_rough_min', 0) + 
            nc.get('back_finish_min', 0)
        )
        
        manual_total = (
            prep.get('unit_min', 0) + 
            assembly.get('cut_off_min', 0) + 
            assembly.get('bonding_min', 0) + 
            manual.get('fitting_min', 0) + 
            manual.get('machine_work_min', 0) + 
            manual.get('sanding_min', 0) + 
            manual.get('assembly_min', 0)
        )

        context += (
            f"    ・{item.get('name')} ({item.get('part')}): "
            f"目標{item.get('target_quantity')} / 在庫{item.get('current_stock')} / 残{item.get('remaining')} "
            f"| 工数[NC: {nc_total}分, 手: {manual_total}分]\n"
        )
        
    return context


from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_message

# ... (既存コード) ...

def is_rate_limit_error(exception):
    """レート制限エラー判定"""
    return "RESOURCE_EXHAUSTED" in str(exception) or "429" in str(exception)

@retry(
    retry=retry_if_exception_message(match=r".*(RESOURCE_EXHAUSTED|429).*"),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    reraise=True
)
def _send_message_with_retry(chat, message):
    """リトライ付きメッセージ送信"""
    return chat.send_message(message)

def get_chat_response(api_key: str, system_prompt: str, message_history: list, user_message: str) -> str:
    """
    都度Clientを生成してメッセージを送信し、応答を取得する（Stateless）。
    "Client has been closed" エラー回避のため、オブジェクトを維持しない。

    Args:
        api_key: Gemini API キー
        system_prompt: システムプロンプト
        message_history: [{"role": "user"|"assistant", "content": "text"}, ...] 形式の履歴
        user_message: 今回のユーザー入力

    Returns:
        str: AIの応答テキスト
    """
    try:
        client = genai.Client(api_key=api_key)

        # 履歴の変換 (app.py形式 -> SDK形式)
        # app.py: role="assistant" -> SDK: role="model"
        sdk_history = []
        for msg in message_history:
            role = "model" if msg["role"] == "assistant" else "user"
            sdk_history.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["content"])]
                )
            )

        chat = client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
            ),
            history=sdk_history
        )

        # リトライ付き送信
        try:
            response = _send_message_with_retry(chat, user_message)
            return response.text
        except Exception:
            # リトライ失敗時は例外が再送出されるのでここでキャッチ
             raise

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Gemini API error: {error_msg}")

        if "API_KEY" in error_msg.upper() or "PERMISSION" in error_msg.upper():
            return "⚠️ APIキーが無効です。`.streamlit/secrets.toml` の `GEMINI_API_KEY` を確認してください。"
        elif "RESOURCE_EXHAUSTED" in error_msg.upper() or "429" in error_msg or "QUOTA" in error_msg.upper():
            return f"⚠️ アクセス集中により応答できませんでした（レート制限）。1分ほど待ってから再度お試しください。(詳細: {error_msg})"
        else:
            return f"⚠️ エラーが発生しました: {error_msg}"


class InitialStockAnalyzer:
    """
    初期在庫データを分析し、戦略的工数計算を行うクラス。
    """
    def __init__(self):
        self.history_path = HISTORY_PATH
        # master_loader.py と同じパス構成を想定
        self.master_path = os.path.join(DATA_DIR, 'production_master.json')
        self.initial_data = None
        self.master_data = None
        self.analysis_results = []
        self.summary = {}

    def load_data(self):
        """データ読み込み"""
        # 1. Master Data
        if os.path.exists(self.master_path):
            with open(self.master_path, 'r', encoding='utf-8') as f:
                self.master_data = json.load(f)
        else:
            logger.error("Master data not found.")
            return False

        # 2. Initial History
        if os.path.exists(self.history_path):
            with open(self.history_path, 'r', encoding='utf-8') as f:
                history = json.load(f)
                # type="initial" を探す
                for h in history:
                    if h.get('type') == 'initial':
                        self.initial_data = h
                        break
        
        if not self.initial_data:
            logger.error("Initial stock data not found in history.")
            return False
            
        return True

    def analyze(self):
        """
        IDベースでマスタと結合し、不足数・工数を計算する。
        """
        if not self.master_data or not self.initial_data:
            return

        initial_details = self.initial_data.get('details', {})
        results = []
        
        total_shortage_count = 0
        total_nc_min = 0
        total_manual_min = 0

        for item in self.master_data:
            item_id = str(item.get('id', '')).strip()
            if not item_id: continue
            
            # マスタの目標数 (target_quantity)
            # ※ イベント合算ロジックで付与された target_quantity を使用
            target = item.get('target_quantity', 0)
            
            # 初期在庫数
            initial_info = initial_details.get(item_id, {})
            initial_count = initial_info.get('count', 0)
            
            # 不足数
            shortage = max(0, target - initial_count)
            
            # 工数計算 (不足分に対して)
            nc_time = 0
            manual_time = 0
            
            # 工数パラメータの取得 (不足数に関わらず取得しておく)
            proc_nc = item.get('process', {}).get('nc', {})
            proc_prep = item.get('process', {}).get('prep', {})
            proc_assembly = item.get('process', {}).get('assembly', {})
            proc_manual = item.get('process', {}).get('manual', {})

            if shortage > 0:
                # NC時間 (粗+仕上 * 表裏)
                nc_unit = (
                    proc_nc.get('front_rough_min', 0) + 
                    proc_nc.get('front_finish_min', 0) + 
                    proc_nc.get('back_rough_min', 0) + 
                    proc_nc.get('back_finish_min', 0)
                )
                nc_time = shortage * nc_unit
                
                # 手作業時間 (準備+組付+手加工)
                # ※乾燥時間は除く
                
                # Setupはロット単位だが、ここでは簡易的に個数比例とするか、無視するか。
                # 「NC時間と手作業時間の合計」なので、直感的には個数比例部分を積算。
                # unit_min (単体) + ...
                manual_unit = (
                    proc_prep.get('unit_min', 0) +
                    proc_assembly.get('cut_off_min', 0) +
                    proc_assembly.get('bonding_min', 0) +
                    proc_manual.get('fitting_min', 0) +
                    proc_manual.get('machine_work_min', 0) +
                    proc_manual.get('sanding_min', 0) +
                    proc_manual.get('assembly_min', 0)
                )
                manual_time = shortage * manual_unit

            results.append({
                "id": item_id,
                "name": item.get('name'),
                "target": target,
                "initial": initial_count,
                "shortage": shortage,
                "nc_details": {
                    "表_粗削": proc_nc.get('front_rough_min', 0),
                    "表_仕上": proc_nc.get('front_finish_min', 0),
                    "裏_粗削": proc_nc.get('back_rough_min', 0),
                    "裏_仕上": proc_nc.get('back_finish_min', 0)
                },
                "manual_details": {
                    "準備": proc_prep.get('unit_min', 0), 
                    "切断": proc_assembly.get('cut_off_min', 0),
                    "接着": proc_assembly.get('bonding_min', 0),
                    "合わせ": proc_manual.get('fitting_min', 0),
                    "機械加工": proc_manual.get('machine_work_min', 0),
                    "研磨": proc_manual.get('sanding_min', 0),
                    "組立": proc_manual.get('assembly_min', 0)
                },
                "nc_min": nc_time,
                "manual_min": manual_time
            })
            
            total_shortage_count += shortage
            total_nc_min += nc_time
            total_manual_min += manual_time

        self.analysis_results = results
        self.summary = {
            "total_items": len(results),
            "total_shortage": total_shortage_count,
            "total_nc_hours": total_nc_min / 60,
            "total_manual_hours": total_manual_min / 60
        }

    def generate_strategist_report(self):
        s = self.summary
        # 1日8時間稼働とした場合の残り日数
        working_days_needed = s['total_nc_hours'] / 8 
        
        return (
            f"yjing殿、現在の戦況を報告しますぞ。\n"
            f"目標まで残り{s['total_shortage']}個。工数に換算すると、NC加工だけで約{s['total_nc_hours']:.1f}時間ほど積み上げる必要がありますな。\n"
            f"1日8時間集中したとしても、あと{working_days_needed:.1f}日分。5月5日の決戦まで残り80日ですから、今のペースを維持すれば勝利は目前です。\n"
            f"今日は、NCの負荷が高い「盗賊の剣」あたりを回しておくと、後々の研磨が楽になりますぞ。無理は禁物ですが、一歩ずつ進んでまいりましょう。"
        )

    def get_plot_data_frame(self):
        """グラフ描画用のDataFrameを返す"""
        if not self.analysis_results:
            return pd.DataFrame()
        return pd.DataFrame(self.analysis_results)
