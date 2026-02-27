"""
master_loader.py - マスタデータ CSV to JSON 自動変換モジュール

CSVファイル（メニュー.xlsx - 商品マスタ.csv）を読み込み、
構造化されたJSONファイル（production_master.json）を生成する。
"""

import pandas as pd
import json
import os
import glob
import logging

logger = logging.getLogger(__name__)

# --- パス設定 ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
CSV_PATH = os.path.join(DATA_DIR, 'メニュー.xlsx - 商品マスタ.csv')
JSON_PATH = os.path.join(DATA_DIR, 'production_master.json')
HISTORY_PATH = os.path.join(DATA_DIR, 'history_summary.json')


def get_val(row, col, default=0):
    """数値フィールドの安全な取得。NaN・空文字の場合はデフォルト値を返す。"""
    val = row.get(col)
    if pd.isna(val) or val == '':
        return default
    return val


def get_str(row, col, default=""):
    """文字列フィールドの安全な取得。NaN・空文字の場合はデフォルト値を返す。"""
    val = row.get(col)
    if pd.isna(val) or val == '':
        return default
    return str(val)


def find_latest_csv(directory):
    """
    指定ディレクトリ内で最新のCSVファイルを検索する。
    フォールバック用：メインのCSVパスが見つからない場合に使用。

    Returns:
        str or None: 最新CSVファイルのパス。見つからない場合はNone。
    """
    if not os.path.isdir(directory):
        return None

    csv_files = glob.glob(os.path.join(directory, '*.csv'))
    # confirmed_log.csv は除外
    csv_files = [f for f in csv_files if 'confirmed_log' not in os.path.basename(f).lower()]

    if not csv_files:
        return None

    # 更新日時が最新のものを返す
    latest = max(csv_files, key=os.path.getmtime)
    logger.info(f"フォールバック: 最新CSV検出 → {latest}")
    return latest


def convert_dataframe_to_json(df, force=False, excel_bytes=None):
    """
    DataFrameを受け取り、構造化されたJSONファイルを生成する。
    excel_bytes が渡された場合、自動的にイベントターゲットの合算も行う。

    Args:
        df (pd.DataFrame): マスタデータのDataFrame
        force (bool): True の場合、タイムスタンプチェックを無視して保存する（DFの場合は常に保存推奨）
        excel_bytes (bytes): メニュー.xlsx のバイナリデータ（イベント情報取得用）

    Returns:
        list: 変換されたマスタデータのリスト。
    """
    master_list = []
    for index, row in df.iterrows():
        if pd.isna(row.get('ID')):
            continue

        item = {
            "id": get_str(row, 'ID'),
            "category": get_str(row, 'カテゴリ'),
            "name": get_str(row, '商品名'),
            "part": get_str(row, '部位'),
            "price": int(get_val(row, '単価1')),
            "current_stock": int(get_val(row, '在庫数')),
            "requirements": {
                "yield": float(get_val(row, '取数', 1)),
                "material_type": get_str(row, '材料種別'),
                "nc_machine_type": get_str(row, 'NCマシン', 'Both')
            },
            "process": {
                "prep": {
                    "setup_min": float(get_val(row, '生地_固定')),
                    "unit_min": float(get_val(row, '生地_単体')),
                    "drying_hr": float(get_val(row, '生地乾燥h'))
                },
                "nc": {
                    "front_rough_min": float(get_val(row, 'NC表_粗分')),
                    "front_finish_min": float(get_val(row, 'NC表_仕分')),
                    "back_rough_min": float(get_val(row, 'NC裏_粗分')),
                    "back_finish_min": float(get_val(row, 'NC裏_仕分'))
                },
                "assembly": {
                    "cut_off_min": float(get_val(row, '切離分')),
                    "bonding_min": float(get_val(row, '組付接着分')),
                    "drying_hr": float(get_val(row, '組付乾燥h'))
                },
                "manual": {
                    "fitting_min": float(get_val(row, '嵌合調整分')),
                    "machine_work_min": float(get_val(row, '機械加工分')),
                    "sanding_min": float(get_val(row, '研磨手加分')),
                    "assembly_min": float(get_val(row, '組立玉入分'))
                }
            }
        }
        master_list.append(item)

    # --- Phase 3: イベントターゲット合算 (内部結合) ---
    if excel_bytes:
        logger.info("Excelバイナリが渡されたため、イベントターゲットを合算します。")
        # merge_event_targets はリストを書き換えて返す
        # NOTE: merge_event_targets 内部でのJSON保存は重複になるが、
        # ここで呼ぶことで確実に反映させる。
        # ただし、merge_event_targets からJSON保存ロジックを削除するのが綺麗だが、
        # ユーザーの「緊急命令」を確実に満たすため、ここでの呼び出しを優先する。
        # master_list は参照渡しされるため変数は更新される。
        master_list = merge_event_targets(master_list, excel_bytes)
        
    # --- 安全装置: データ量チェック ---
    # 既存のJSONがあり、かつ新しいデータが極端に少ない（例: 10件未満）場合は
    # 誤って上書きしないようにする（テストデータ等による事故防止）
    if os.path.exists(JSON_PATH) and len(master_list) < 10:
        try:
            with open(JSON_PATH, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
            if len(old_data) > 20:
                logger.warning(f"⚠️ Data Safety Guard: New data has {len(master_list)} items, but old data had {len(old_data)}. Skipping overwrite.")
                print(f"⚠️ Data Safety Guard: Skipping overwrite to protect data. (New: {len(master_list)}, Old: {len(old_data)})")
                return old_data
        except Exception:
            pass # 読み込み失敗時は無視して上書き

    # --- JSON書き出し ---
    # merge_event_targets でも保存しているかもしれないが、
    # convert関数の責務としてここでも保存する (最終的な整合性のため)
    try:
        os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(master_list, f, indent=2, ensure_ascii=False)
        msg = f"SUCCESS: production_master.json has been created at {JSON_PATH} ({len(master_list)} items)"
        logger.info(msg)
        print(msg) # コンソールにも強制出力
    except Exception as e:
        logger.error(f"JSON書き出し失敗: {e}")
        print(f"ERROR: Failed to create production_master.json: {e}")
        return master_list

    return master_list


# --- Drive連携用インポート ---
try:
    from logic import drive_utils
    from logic.drive_utils import upload_to_drive, HISTORY_SUMMARY_DRIVE_ID
except ImportError:
    try:
        import drive_utils
        from drive_utils import upload_to_drive, HISTORY_SUMMARY_DRIVE_ID
    except ImportError:
        drive_utils = None
        upload_to_drive = None
        HISTORY_SUMMARY_DRIVE_ID = None


def sync_from_drive():
    """
    Google Driveから「メニュー.xlsx」を取得し、master JSONを更新する。
    
    Returns:
        list: 更新後のマスタリスト
    """
    if not drive_utils:
        logger.error("drive_utilsが見つからないため、Drive同期できません。")
        return []

    print("--- Google Drive Sync Start ---")
    logger.info("Google Drive認証開始...")
    
    try:
        service = drive_utils.authenticate()
        if not service:
            logger.error("Google Drive認証失敗")
            return []

        # ファイル検索
        file_meta = drive_utils.find_file(service, "メニュー")
        if not file_meta:
            logger.error("Drive上に 'メニュー' を含むファイルが見つかりません。")
            return []

        file_id = file_meta['id']
        file_name = file_meta['name']
        mime_type = file_meta['mimeType']
        
        print(f"File Found: {file_name} ({file_id})")
        
        # ダウンロード
        stream = drive_utils.download_content(service, file_id, mime_type)
        if not stream:
            logger.error("ダウンロード失敗")
            return []
            
        # Excelとして読み込み
        try:
            excel_bytes = stream.getvalue()
            df = pd.read_excel(stream, sheet_name="商品マスタ")
            print(f"Excel Loaded: {len(df)} rows")
        except Exception as e:
            logger.error(f"Excel読み込みエラー: {e}")
            return []

        # JSON変換 & 保存 (イベント合算含む)
        # convert_dataframe_to_json は内部で production_master.json を保存する
        master_list = convert_dataframe_to_json(df, force=True, excel_bytes=excel_bytes)
        
        print("--- Google Drive Sync Completed ---")
        return master_list

    except Exception as e:
        logger.error(f"Drive同期予期せぬエラー: {e}")
        import traceback
        traceback.print_exc()
        return []


def convert_csv_to_json(force=False):
    """
    データソースからJSONを生成する。
    デフォルトでGoogle Driveからの同期を試みる。
    失敗した場合、ローカルCSV (フォールバック) を使用する。
    """
    # 1. Drive同期を試行
    print("Attempting Google Drive Sync...")
    master_list = sync_from_drive()
    
    if master_list:
        return master_list
    
    print("Drive Sync Failed. Falling back to local CSV...")
    
    # 2. ローカルCSVフォールバック (旧ロジック)
    # --- CSVファイルの特定 ---
    csv_path = CSV_PATH
    if not os.path.exists(csv_path):
        logger.warning(f"デフォルトCSV不在: {csv_path}")
        csv_path = find_latest_csv(DATA_DIR)
        if csv_path is None:
            logger.error(f"data/ フォルダ内にCSVファイルが見つかりません: {DATA_DIR}")
            return []

    # --- CSV読み込み ---
    try:
        df = pd.read_csv(csv_path, encoding='utf-8')
        logger.info(f"CSV読み込み成功: {csv_path} ({len(df)} 行)")
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(csv_path, encoding='cp932')
            logger.info(f"CSV読み込み成功 (cp932): {csv_path} ({len(df)} 行)")
        except Exception as e:
            logger.error(f"CSV読み込み失敗: {e}")
            return load_master_json()
    except Exception as e:
        logger.error(f"CSV読み込み失敗: {e}")
        return load_master_json()

    return convert_dataframe_to_json(df, force=True)


def load_master_json():
    """
    既存のJSONファイルを読み込んで返す。

    Returns:
        list: マスタデータのリスト。ファイル不在・エラー時は空リスト。
    """
    if not os.path.exists(JSON_PATH):
        return []
    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"JSON読み込み失敗: {e}")
        return []



def _import_initial_from_note(xls, note_text, history_path):
    """
    備考テキスト（例: "クリマ2512 AK列"）をパースし、
    指定されたシートの指定列から初期在庫データを読み取り、
    history_summary.json に type="initial" として記録する。
    
    Args:
        xls: pd.ExcelFile オブジェクト
        note_text (str): 備考テキスト（例: "クリマ2512 AK列"）
        history_path (str): history_summary.json のパス
    """
    import re
    
    if not note_text:
        return
    
    # パース: "クリマ2512 AK列" -> sheet_name="クリマ2512", col_letter="AK"
    # パターン: シート名 + 列名(アルファベット) + "列"
    match = re.match(r'(.+?)\s+([A-Za-z]+)列', note_text)
    if not match:
        logger.warning(f"備考テキストのパース失敗: '{note_text}' (期待形式: 'シート名 列名列')")
        return
    
    target_sheet = match.group(1).strip()
    col_letter = match.group(2).strip().upper()
    
    # 列文字をインデックスに変換 (A=0, B=1, ..., AK=36, AL=37)
    col_idx = 0
    for ch in col_letter:
        col_idx = col_idx * 26 + (ord(ch) - ord('A') + 1)
    col_idx -= 1  # 0-indexed
    
    logger.info(f"備考から初期在庫参照先を特定: シート='{target_sheet}', 列={col_letter}(idx={col_idx})")
    
    if target_sheet not in xls.sheet_names:
        logger.warning(f"初期在庫参照先シート '{target_sheet}' がExcel内に存在しません。")
        return
    
    # 既に initial エントリが正しく存在するか確認
    if os.path.exists(history_path):
        try:
            with open(history_path, 'r', encoding='utf-8') as f:
                hist = json.load(f)
            for h in hist:
                if h.get('type') == 'initial' and h.get('details') and len(h.get('details', {})) > 2:
                    logger.info("初期在庫は既に正しく登録済み。スキップします。")
                    return
        except Exception:
            pass
    
    try:
        df_raw = pd.read_excel(xls, sheet_name=target_sheet, header=None)
        
        # ID列を探す (通常 C列=idx 2)
        header_row_idx = -1
        id_col_idx = -1
        
        for r_idx in range(min(10, len(df_raw))):
            row_vals = [str(x).strip().upper() for x in df_raw.iloc[r_idx].values]
            if 'ID' in row_vals:
                header_row_idx = r_idx
                id_col_idx = row_vals.index('ID')
                break
        
        if header_row_idx == -1:
            logger.warning(f"シート '{target_sheet}' から 'ID' 列が見つかりません。")
            return
        
        initial_details = {}
        total_count = 0
        
        for i in range(header_row_idx + 1, len(df_raw)):
            row = df_raw.iloc[i]
            
            # ID取得
            if id_col_idx >= len(row):
                continue
            raw_id = row.iloc[id_col_idx]
            if pd.isna(raw_id):
                continue
            clean_id = str(raw_id).strip()
            if not clean_id:
                continue
            
            # 指定列からカウント取得
            count = 0
            if col_idx < len(row):
                try:
                    val = row.iloc[col_idx]
                    count = int(float(val)) if pd.notna(val) else 0
                except (ValueError, TypeError):
                    count = 0
            
            if count > 0:
                initial_details[clean_id] = {"count": count, "target": 0}
                total_count += count
        
        if not initial_details:
            logger.warning(f"初期在庫データが空です（シート '{target_sheet}' {col_letter}列）。")
            return
        
        # history_summary.json に initial エントリを更新/追加
        from datetime import datetime
        new_entry = {
            "type": "initial",
            "date": "2025-12-14",
            "timestamp": datetime(2025, 12, 14, 23, 59, 59).isoformat(),
            "total_current": total_count,
            "total_target": 0,
            "details": initial_details,
            "source_note": note_text
        }
        
        history_list = []
        if os.path.exists(history_path):
            try:
                with open(history_path, 'r', encoding='utf-8') as f:
                    history_list = json.load(f)
            except Exception:
                history_list = []
        
        # 既存の initial を削除して入れ替え
        history_list = [h for h in history_list if h.get('type') != 'initial']
        history_list.insert(0, new_entry)
        
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(history_list, f, indent=2, ensure_ascii=False)
        
        # --- Phase 1: Drive同期 ---
        if upload_to_drive and HISTORY_SUMMARY_DRIVE_ID:
            _ok, _msg = upload_to_drive(history_path, HISTORY_SUMMARY_DRIVE_ID)
            logger.info(f"[Drive同期] 初期在庫インポート後: {_msg}")
        
        logger.info(f"初期在庫インポート完了（備考参照）: {len(initial_details)} 件, 総数 {total_count}")
        print(f"初期在庫インポート完了: {len(initial_details)} 件 (from {target_sheet} {col_letter}列)")
        
    except Exception as e:
        logger.error(f"初期在庫インポート中にエラー: {e}")


def merge_event_targets(master_list, excel_bytes, _unused_sheet_name=None):
    """
    【新ロジック】イベントマスタで「アクティブ/表示」となっている全イベントの目標を合算して統合する。
    旧引数 `sheet_name` は互換性のため残すが使用しない（_unused_sheet_name）。
    
    Args:
        master_list (list): convert_dataframe_to_json の出力
        excel_bytes (bytes): メニュー.xlsx のバイナリデータ
    
    Returns:
        list: target_quantity(合算値) と event_data(詳細) が追加された master_list
    """
    import io as _io
    
    if not excel_bytes:
        return master_list
    
    try:
        xls = pd.ExcelFile(_io.BytesIO(excel_bytes))
    except Exception as e:
        logger.error(f"Excelバイナリ読み込み失敗: {e}")
        return master_list

    # 1. イベントマスタからアクティブなシートを特定
    target_sheets = []
    display_events = [] # Zeus監視用

    if 'イベントマスタ' in xls.sheet_names:
        try:
            master_sheet = pd.read_excel(xls, sheet_name='イベントマスタ')
            
            # カラム特定
            col_map = {
                'active': None,
                'display': None,
                'sheet': None,
                'name': None,
                'deadline': None,
                'date': None,
                'venue': None,
                'booth': None,
                'loadin': None,
                'note': None  # 備考列（初期在庫参照先）
            }
            
            # ヘッダー探索
            for col in master_sheet.columns:
                c_str = str(col).strip()
                if 'アクティブ' in c_str or 'Active' in c_str or '進軍' in c_str: col_map['active'] = col
                if '表示' in c_str or 'Display' in c_str or '監視' in c_str: col_map['display'] = col
                if 'シート' in c_str or '対象' in c_str: col_map['sheet'] = col
                if 'イベント名' in c_str: col_map['name'] = col
                if '締切' in c_str or 'Deadline' in c_str: col_map['deadline'] = col
                if '開催' in c_str or 'Date' in c_str: col_map['date'] = col
                if '会場' in c_str or 'Venue' in c_str: col_map['venue'] = col
                if 'ブース' in c_str or 'Booth' in c_str: col_map['booth'] = col
                if '搬入' in c_str or 'LoadIn' in c_str: col_map['loadin'] = col
                if '備考' in c_str or 'Note' in c_str or 'note' in c_str: col_map['note'] = col

            # 必須カラムチェック（シート名は必須）
            if col_map['sheet']:
                for _, row in master_sheet.iterrows():
                    # 値取得ヘルパー
                    def _get_val(c_key):
                        if not col_map[c_key]: return None
                        val = row.get(col_map[c_key])
                        return str(val).strip() if pd.notna(val) else ""
                    
                    def _is_true(c_key):
                        val = _get_val(c_key)
                        if not val:
                            return False
                        return val.upper() in ['TRUE', '1', '1.0', 'YES', 'ON']

                    sheet_name = _get_val('sheet')
                    if not sheet_name:
                        continue

                    # Active判定 (進軍指示)
                    # NOTE: アクティブなら無条件でターゲット合算対象
                    if _is_true('active'):
                        target_sheets.append(sheet_name)
                        
                        # 備考列から初期在庫を自動インポート
                        note_val = _get_val('note')
                        if note_val:
                            _import_initial_from_note(xls, note_val, HISTORY_PATH)
                    
                    # Display判定 (監視・広報)
                    # NOTE: 表示フラグONならZeusの監視リストに入れる
                    if _is_true('display'):
                        event_info = {
                            "name": _get_val('name') or sheet_name,
                            "sheet": sheet_name,
                            "deadline": _get_val('deadline'),
                            "date": _get_val('date'),
                            "venue": _get_val('venue'),
                            "booth": _get_val('booth'),
                            "loadin": _get_val('loadin'),
                            "is_active": _is_true('active')
                        }
                        display_events.append(event_info)

                logger.info(f"🎯 アクティブイベント (計算対象): {target_sheets}")
                logger.info(f"👀 表示イベント (監視対象): {[e['name'] for e in display_events]}")
                
                # --- Zeus監視用データの保存 (event_master.json) ---
                event_json_path = os.path.join(DATA_DIR, 'event_master.json')
                try:
                    with open(event_json_path, 'w', encoding='utf-8') as f:
                        json.dump(display_events, f, indent=2, ensure_ascii=False)
                    logger.info(f"監視イベントリスト保存完了: {event_json_path}")
                except Exception as e:
                    logger.error(f"監視イベントリスト保存失敗: {e}")

            else:
                logger.warning("⚠️ イベントマスタから '対象シート' 列が見つかりません。")

        except Exception as e:
            logger.error(f"イベントマスタ読み込みエラー: {e}")
    else:
        logger.warning("⚠️ 'イベントマスタ' シートが見つかりません。")

    # 2. 各シートから目標を合算
    aggregated_targets = {} # {clean_id: {'total': 0, 'details': []}}
    
    for sheet in target_sheets:
        if sheet not in xls.sheet_names:
            logger.warning(f"⚠️ 指定されたシート '{sheet}' がExcel内に存在しません。")
            continue

        try:
            df_raw = pd.read_excel(xls, sheet_name=sheet, header=None)
            
            # データ開始行を探す (ID という文字がある行)
            header_row_idx = -1
            id_col_idx = -1
            
            for r_idx in range(min(10, len(df_raw))):
                row_vals = [str(x).strip().upper() for x in df_raw.iloc[r_idx].values]
                if 'ID' in row_vals:
                    header_row_idx = r_idx
                    id_col_idx = row_vals.index('ID')
                    break
            
            if header_row_idx == -1:
                logger.warning(f"シート '{sheet}' から 'ID' 列が見つかりません。スキップします。")
                continue
                
            target_col_idx = 5  # F列
            current_col_idx = 6  # G列
            
            # データ反復
            for i in range(header_row_idx + 1, len(df_raw)):
                row = df_raw.iloc[i]
                
                if id_col_idx >= len(row): continue
                raw_id = row.iloc[id_col_idx]
                if pd.isna(raw_id): continue
                clean_id = str(raw_id).strip()
                if not clean_id: continue
                
                tgt_val = 0
                if target_col_idx < len(row):
                    try:
                        val = row.iloc[target_col_idx]
                        tgt_val = int(float(val)) if pd.notna(val) else 0
                    except:
                        tgt_val = 0
                
                cur_val = 0
                if current_col_idx < len(row):
                    try:
                        val = row.iloc[current_col_idx]
                        cur_val = int(float(val)) if pd.notna(val) else 0
                    except:
                        cur_val = 0

                if tgt_val > 0 or cur_val > 0:
                    if clean_id not in aggregated_targets:
                        aggregated_targets[clean_id] = {'target_total': 0, 'current_total': 0, 'details': []}
                    
                    aggregated_targets[clean_id]['target_total'] += tgt_val
                    aggregated_targets[clean_id]['current_total'] += cur_val
                    aggregated_targets[clean_id]['details'].append(f"{sheet}: 目標{tgt_val}/在庫{cur_val}")
                    
        except Exception as e:
            logger.error(f"シート '{sheet}' 集計エラー: {e}")

    # 3. master_list に反映
    merge_count = 0
    
    # 履歴保存用の集計データ（details を必ず含める）
    history_data = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "total_target": 0,
        "total_current": 0,
        "type": "scan",
        "details": {}  # ★ 商品IDごとの個数を必ず含める
    }

    for item in master_list:
        raw_id = item.get('id', '')
        clean_id = str(raw_id).strip()
        
        target_info = aggregated_targets.get(clean_id)
        if target_info:
            t_total = target_info['target_total']
            c_total = target_info['current_total']
            details = target_info['details']
            
            item['target_quantity'] = t_total
            item['event_sheet_stock'] = c_total 
            item['remaining'] = max(0, t_total - c_total)
            
            count_for_history = c_total
            target_for_history = t_total
            
            if 'event_data' not in item:
                item['event_data'] = {}
            
            item['event_data']['合算内訳'] = ", ".join(details)
            item['event_data']['アクティブイベント'] = ", ".join(target_sheets)
            
            merge_count += 1
        else:
            item['target_quantity'] = 0
            item['remaining'] = 0
            if 'event_data' in item:
                 item['event_data'].pop('合算内訳', None)
                 item['event_data'].pop('アクティブイベント', None)
            
            count_for_history = item.get('current_stock', 0)
            target_for_history = 0

        # --- 履歴詳細へ追加 (全アイテム対象) ---
        history_data["total_target"] += target_for_history
        history_data["total_current"] += count_for_history
        
        # ★ 商品IDごとの個数を details に必ず記録
        if clean_id:
            history_data['details'][clean_id] = {
                "count": count_for_history,
                "target": target_for_history
            }

    logger.info(f"全イベント合算完了: {merge_count} アイテムに目標を設定")
    
    # --- 履歴の保存 ---
    if not os.path.exists(HISTORY_PATH):
        history_data["type"] = "initial"
        try:
            with open(HISTORY_PATH, 'w', encoding='utf-8') as f:
                json.dump([history_data], f, indent=2, ensure_ascii=False)
            logger.info(f"履歴初期化: {HISTORY_PATH} を作成しました。")
            # --- Phase 1: Drive同期 ---
            if upload_to_drive and HISTORY_SUMMARY_DRIVE_ID:
                _ok, _msg = upload_to_drive(HISTORY_PATH, HISTORY_SUMMARY_DRIVE_ID)
                logger.info(f"[Drive同期] 履歴初期化後: {_msg}")
        except Exception as e:
            logger.error(f"履歴ファイル作成失敗: {e}")
    else:
        try:
            with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
                hist_list = json.load(f)
            
            hist_list.append(history_data)
            
            with open(HISTORY_PATH, 'w', encoding='utf-8') as f:
                json.dump(hist_list, f, indent=2, ensure_ascii=False)
            # --- Phase 1: Drive同期 ---
            if upload_to_drive and HISTORY_SUMMARY_DRIVE_ID:
                _ok, _msg = upload_to_drive(HISTORY_PATH, HISTORY_SUMMARY_DRIVE_ID)
                logger.info(f"[Drive同期] 履歴追記後: {_msg}")
        except Exception as e:
            logger.error(f"履歴追記失敗: {e}")

    # --- JSON書き出し ---
    try:
        os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(master_list, f, indent=2, ensure_ascii=False)
        msg = f"SUCCESS: Merged production_master.json saved at {JSON_PATH} ({len(master_list)} items)"
        logger.info(msg)
        print(msg)
    except Exception as e:
        logger.error(f"Merged JSON書き出し失敗: {e}")
        print(f"ERROR: Failed to save merged production_master.json: {e}")

    return master_list


def import_initial_stock(excel_path=None, sheet_name='クリマ2512'):
    """
    指定されたExcelシートから初期在庫（IDベース）をインポートし、
    history_summary.json に type="initial" として保存する。

    Args:
        excel_path (str): メニュー.xlsx のパス。Noneの場合はデフォルトパスを使用。
        sheet_name (str): 読み込むシート名。デフォルトは 'クリマ2512'。
    """
    # Excelパスの特定
    if excel_path is None:
        # デフォルトパスの構築 (メニュー.xlsx は CSVの隣にあるはず)
        # CSV_PATH = .../data/メニュー.xlsx - 商品マスタ.csv
        # よって data/メニュー.xlsx を探す
        excel_path = os.path.join(DATA_DIR, 'メニュー.xlsx')

    if not os.path.exists(excel_path):
        logger.error(f"初期在庫インポート失敗: ファイルが見つかりません {excel_path}")
        return

    logger.info(f"初期在庫インポート開始: {excel_path} (Sheet: {sheet_name})")

    try:
        # Excel読み込み
        # C列=ID (index 2), AK列=残 (index 36), AL列=金額 (index 37)
        # header=0 (1行目) をヘッダーとする
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
        
        # カラム特定 (名前で探すが、位置も考慮)
        # AK列は37番目(0-indexで36)
        
        id_col = None
        count_col = None
        value_col = None

        # 1. カラム名で探索
        for col in df.columns:
            c_str = str(col).strip()
            if c_str == 'ID': id_col = col
            if '残' in c_str: count_col = col # "残"を含むカラム
            if '金額' in c_str: value_col = col
        
        # 2. 位置で強制指定（指示優先）
        # C列=2, AK列=36, AL列=37
        # pandasのread_excel結果のcolumnsの並びがExcel通りかわからないため、ilocでアクセスする方が安全か？
        # しかしデータフレームの列アクセスは名前が基本。
        # ここでは指示通り「C列、AK列、AL列」を位置で特定する戦略を採る。
        # ただし、read_excelの挙動により無駄な列がスキップされている可能性があるため、
        # usecols で指定して読み直すのが最も確実。
        
        df = pd.read_excel(excel_path, sheet_name=sheet_name, usecols="C,AK,AL")
        # 読み込み後のカラム名は元のヘッダーになる
        # 0番目: ID, 1番目: AK列のヘッダー, 2番目: AL列のヘッダー
        
        initial_data_details = {}
        total_value = 0
        total_count = 0
        
        for index, row in df.iterrows():
            # 1行目はヘッダーとして消費されているので、データは2行目から
            
            # ID (0番目)
            raw_id = row.iloc[0]
            if pd.isna(raw_id): continue
            clean_id = str(raw_id).strip()
            if not clean_id: continue
            
            # Count (1番目: AK列)
            raw_count = row.iloc[1]
            try:
                count = int(raw_count) if pd.notna(raw_count) else 0
            except:
                count = 0
                
            # Value (2番目: AL列)
            raw_value = row.iloc[2]
            try:
                value = int(raw_value) if pd.notna(raw_value) else 0
            except:
                value = 0
            
            if count > 0 or value > 0:
                initial_data_details[clean_id] = {
                    "count": count,
                    "value": value
                }
                total_value += value
                total_count += count
        
        # JSON構造作成
        # 日付固定: 2025-12-14 (クリマ2512最終日)
        from datetime import datetime
        date_str = "2025-12-14"
        # タイムスタンプもこの日の終わりに設定
        timestamp_str = datetime(2025, 12, 14, 23, 59, 59).isoformat()
        
        new_entry = {
            "type": "initial",
            "date": date_str,
            "timestamp": timestamp_str,
            "summary": total_value, # AL列合計
            "total_current": total_count,
            "details": initial_data_details,
            "total_target": 0 # 初期在庫データの文脈ではターゲット不明
        }

        # history_summary.json 更新
        history_list = []
        if os.path.exists(HISTORY_PATH):
            try:
                with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
                    history_list = json.load(f)
            except:
                history_list = []
        
        # 既存の type: "initial" を削除して入れ替え
        history_list = [h for h in history_list if h.get('type') != 'initial']
        
        # 先頭に追加（あるいは時系列順？初期在庫なので先頭が自然）
        history_list.insert(0, new_entry)
        
        # 保存
        with open(HISTORY_PATH, 'w', encoding='utf-8') as f:
            json.dump(history_list, f, indent=2, ensure_ascii=False)
            
        msg = f"初期在庫インポート完了: {len(initial_data_details)} 件, 総数 {total_count}, 総額 {total_value}"
        logger.info(msg)
        print(msg)
        return new_entry

    except Exception as e:
        logger.error(f"初期在庫インポート中にエラー: {e}")
        print(f"ERROR: {e}")
        return None

if __name__ == "__main__":
    # 直接実行時は強制変換（Drive同期含む）
    convert_csv_to_json(force=True)
