import streamlit as st
import pandas as pd
import json
import streamlit.components.v1 as components
from datetime import datetime
import os
import shutil
import io
import socket
import plotly.graph_objects as go
import qrcode

# --- Imports (Logic) ---
try:
    from logic.drive_utils import load_data_from_drive, read_confirmed_sheet
    from logic.production_logic import calculate_production_events
    from logic.inventory import calculate_inventory, confirm_production, cancel_confirmation
    from logic.master_loader import convert_csv_to_json, convert_dataframe_to_json, load_master_json, merge_event_targets
    from components.CatalogCard import render_catalog_card
    from logic import zeus_chat
    import logic.master_loader
    import logic.bi_dashboard
    import importlib
    importlib.reload(zeus_chat)
    importlib.reload(logic.master_loader)
    importlib.reload(logic.bi_dashboard)
    from logic.bi_dashboard import calc_countdown, calc_sales_gap, calc_remaining_hours, calc_today_tasks, calc_material_alerts, calc_dev_slot, calc_burnup_data
    from logic.zeus_chat import build_system_prompt, get_chat_response
except ImportError as e:
    st.error(f"Modules not found: {e}")
    st.stop()

# --- Page Config ---
st.set_page_config(
    page_title="Atlas Hub | Production Manager",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "Atlas Hub Production Manager v2.4 (Zeus Enhanced Logic)"
    }
)

# --- Hybrid Mode Detection ---
SRC_DIR = 'PM_Strategic Mind & Pipeline'
IS_LOCAL = os.path.exists(os.path.join(os.path.expanduser('~'), '.gemini', SRC_DIR)) or os.path.exists(SRC_DIR)

# --- Sidebar Controls ---
with st.sidebar:
    st.header("⚙️ System")
    if IS_LOCAL:
        st.success("🏠 ローカル統合モードで稼働中")
    else:
        st.info("☁️ クラウド分析モードで稼働中")

# --- CSS Styling ---
st.markdown("""
<style>
    .reportview-container {
        background: #f0f2f6;
    }
    .main-header {
        font-family: "Helvetica Neue", Arial, sans-serif;
        color: #333;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    /* --- BI Dashboard: スマホ最適化 --- */
    .bi-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 16px;
        padding: 1.2rem;
        margin-bottom: 0.8rem;
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .bi-card h3 {
        color: #e0e0e0;
        font-size: 0.85rem;
        margin: 0 0 0.5rem 0;
        font-weight: 400;
        letter-spacing: 0.05em;
    }
    .bi-card .bi-value {
        color: #ffffff;
        font-size: 2rem;
        font-weight: 700;
        line-height: 1.1;
    }
    .bi-card .bi-sub {
        color: #8892b0;
        font-size: 0.8rem;
        margin-top: 0.3rem;
    }
    .bi-countdown {
        background: linear-gradient(135deg, #0f3460 0%, #533483 100%) !important;
    }
    .bi-revenue {
        background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%) !important;
    }
    .bi-alert {
        background: linear-gradient(135deg, #2d1b00 0%, #4a1e00 100%) !important;
        border: 1px solid rgba(255,152,0,0.3) !important;
    }
    .bi-ok {
        background: linear-gradient(135deg, #0d2818 0%, #1a4731 100%) !important;
        border: 1px solid rgba(76,175,80,0.3) !important;
    }
    .bi-ng {
        background: linear-gradient(135deg, #2d0a0a 0%, #4a1010 100%) !important;
        border: 1px solid rgba(244,67,54,0.3) !important;
    }
    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        .bi-card .bi-value {
            font-size: 1.6rem;
        }
    }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ Atlas Hub Production Manager")

# --- GUARDRAIL: Auto-Recovery for Static Files ---
def check_and_deploy_static_files():
    """
    Checks if static files exist. If not, attempts to copy from the known source.
    This prevents 'Static files not found' errors after environment resets.
    """
    # 1. Define Paths (Absolute)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    static_dir = os.path.join(base_dir, "static")
    
    # 2. Source Path (Hardcoded fallback - Robust Pattern)
    user_home = os.path.expanduser("~")
    # Search for source directory in standard locations
    possible_sources = [
        os.path.join(user_home, ".gemini", "PM‗Strategic Mind & Pipeline", "20260119_V5.1"),
        os.path.join(user_home, ".gemini", "PM_Strategic Mind & Pipeline", "20260119_V5.1")
    ]
    
    required_files = ["index.html", "style.css", "logic.js"]
    
    # 3. Check & Recovery
    if not os.path.exists(static_dir):
        try:
            os.makedirs(static_dir)
            st.toast(f"📁 Created static directory: {static_dir}")
        except OSError as e:
            st.error(f"Failed to create static directory: {e}")
            return False

    missing_files = [f for f in required_files if not os.path.exists(os.path.join(static_dir, f))]
    
    if missing_files:
        st.warning(f"⚠️ Missing static files: {missing_files}. Attempting auto-recovery...")
        
        # Find valid source
        valid_source = None
        for src in possible_sources:
            if os.path.exists(src):
                valid_source = src
                break
        
        if not valid_source:
             # Fallback: Try to find using os.walk in .gemini if exact path fails (Heavy but safe)
            st.error("❌ Auto-recovery failed: Source directory 'PM_Strategic Mind & Pipeline' not found on this machine.")
            return False
            
        # Copy
        success_count = 0
        for f in missing_files:
            src_path = os.path.join(valid_source, f)
            dst_path = os.path.join(static_dir, f)
            try:
                if os.path.exists(src_path):
                    shutil.copy2(src_path, dst_path)
                    success_count += 1
                else:
                    st.error(f"❌ Source file not found: {src_path}")
            except Exception as e:
                st.error(f"❌ Failed to copy {f}: {e}")
        
        if success_count == len(missing_files):
            st.success("✅ Auto-recovery successful! Reloading...")
            st.rerun()
        else:
            st.error("❌ Partial recovery only. Please check file system.")
            return False
            
    return True

# Run Guardrail (ローカル時のみ — クラウドではstatic不要)
if IS_LOCAL:
    if not check_and_deploy_static_files():
        st.stop()
else:
    st.markdown("※クラウド環境のため、日程の直接編集は別画面（GAS）から行ってください。")

# --- Data Loading ---
master_df, log_df, event_sheet_names, excel_bytes = load_data_from_drive()

# イベントシート情報をsession_stateに保存
if event_sheet_names:
    st.session_state['event_sheet_names'] = event_sheet_names
if excel_bytes:
    st.session_state['excel_bytes'] = excel_bytes

# --- Master Data (Drive連携: DF → JSON 自動変換) ---
if master_df is not None:
    # Driveから取得できた場合、JSONを自動更新・保存
    # convert_dataframe_to_json 内部で merge_event_targets も呼ばれるように excel_bytes を渡す
    master_list = convert_dataframe_to_json(master_df, force=True, excel_bytes=excel_bytes)
    st.session_state['master_data'] = master_list
    if master_list:
        st.toast(f"📦 マスタデータ更新: {len(master_list)} 件 (from Drive)")
else:
    # Drive取得失敗時は既存JSONまたはローカルCSVフォールバック
    master_list = convert_csv_to_json()
    st.session_state['master_data'] = master_list

# --- DEBUG: Verify Loaded Data ---
with st.sidebar.expander("🛠️ Debug Information"):
    try:
        from logic.zeus_chat import OUTPUT_VERSION
        st.write(f"Logic Version: {OUTPUT_VERSION}")
    except ImportError as e:
        st.error(f"Logic Version: Unknown (Error: {e})")
        # Try to reload explicitly if not found
        if st.button("Reload Module"):
            import importlib
            import logic.zeus_chat
            importlib.reload(logic.zeus_chat)
            st.rerun()

    if 'master_data' in st.session_state and st.session_state['master_data']:
        first_item = st.session_state['master_data'][0]
        st.write(f"Item: {first_item.get('name')}")
        st.json(first_item.get('process', {}).get('nc', {}))
    else:
        st.write("Master Data: Empty")

# --- イベント目標のマージ (自動合算) は convert_dataframe_to_json 内で実行済み ---
# (以前の明示的な呼び出しコードは削除されました)

# --- Calendar & Tasks Data Loading (Zeus Aggressive Suggestions) ---
@st.cache_data(ttl=3600)
def fetch_and_cache_calendar_data():
    try:
        from logic.calendar_agent import run as run_calendar_agent
        # Drive同期は不要、ローカル（エフェメラル）へのJSON出力を有効にして既存ロジックと互換性を保つ
        return run_calendar_agent(output_local=True, output_drive=False)
    except Exception as e:
        print(f"Error executing calendar agent: {e}")
        return {}

calendar_data_cache = fetch_and_cache_calendar_data() or {}

# --- Logic Execution ---
production_events = []
inventory_df = pd.DataFrame()

# 1. Production Events (Strict Column Logic - 14 cols)
if log_df is not None and not log_df.empty:
    with st.spinner("Processing Production Logs..."):
        production_events = calculate_production_events(log_df)

# 2. Inventory (導出方式: H列 + CONFIRMED - 販売)
confirmed_df = pd.DataFrame()
try:
    confirmed_df = read_confirmed_sheet()
except Exception:
    confirmed_df = pd.DataFrame()

if master_df is not None and log_df is not None:
    inventory_df = calculate_inventory(master_df, log_df, confirmed_df)

# --- Navigation ---
if IS_LOCAL:
    PAGES = ["📊 BI Dashboard", "📅 Strategic Mind", "📋 Inspector", "📦 Catalog", "🏭 Input", "📦 Stock", "⚔️ 軍師Zeus"]
    default_page = "📅 Strategic Mind"
else:
    # クラウドモード: ローカル依存ページを除外
    PAGES = ["📊 BI Dashboard", "📋 Inspector", "📦 Catalog", "📦 Stock", "⚔️ 軍師Zeus"]
    default_page = "📊 BI Dashboard"

if 'current_page' not in st.session_state:
    st.session_state.current_page = default_page

with st.sidebar:
    st.title("Navigation")
    selection = st.radio("Go to", PAGES, key="current_page")

    st.divider()

    # --- イベント情報 (自動合算) ---
    st.info("ℹ️ イベントマスタ設定に基づき、アクティブな全イベントの目標を合算しています")

    # --- イベント応募ステータス管理 ---
    event_master_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'event_master.json')
    
    # クラウド環境でローカルにファイルがない場合、Driveから復元
    if not os.path.exists(event_master_path):
        try:
            from logic.drive_utils import authenticate as _auth, download_content, EVENT_MASTER_DRIVE_ID
            if EVENT_MASTER_DRIVE_ID:
                _svc = _auth()
                if _svc:
                    _stream = download_content(_svc, EVENT_MASTER_DRIVE_ID, 'application/json')
                    if _stream:
                        os.makedirs(os.path.dirname(event_master_path), exist_ok=True)
                        with open(event_master_path, 'wb') as f:
                            f.write(_stream.read())
                        print("[app] ✅ Driveからevent_master.jsonを復元")
        except Exception as e:
            print(f"[app] event_master復元スキップ: {e}")
    
    if os.path.exists(event_master_path):
        try:
            with open(event_master_path, 'r', encoding='utf-8') as f:
                event_list = json.load(f)
            
            if event_list:
                st.markdown("### 📝 イベント応募状況")
                changed = False
                for i, evt in enumerate(event_list):
                    evt_name = evt.get('name', '不明')
                    deadline = evt.get('deadline', '')
                    is_applied = evt.get('is_applied', False)
                    
                    # 締切情報のラベル
                    deadline_label = ""
                    if deadline:
                        try:
                            from datetime import datetime as dt_cls
                            dl = dt_cls.strptime(str(deadline).split(' ')[0], '%Y-%m-%d')
                            days_left = (dl - datetime.now()).days
                            if days_left < 0:
                                deadline_label = f" 🚨 締切超過{abs(days_left)}日"
                            elif days_left == 0:
                                deadline_label = " 🔴 本日締切！"
                            elif days_left <= 3:
                                deadline_label = f" 🟠 締切まで{days_left}日"
                            else:
                                deadline_label = f" 📅 締切: {deadline.split(' ')[0]}"
                        except Exception:
                            deadline_label = f" 📅 {deadline}"
                    
                    label = f"✅ {evt_name}" if is_applied else f"⬜ {evt_name}{deadline_label}"
                    new_val = st.checkbox(
                        label,
                        value=is_applied,
                        key=f"applied_{i}_{evt_name}",
                    )
                    if new_val != is_applied:
                        event_list[i]['is_applied'] = new_val
                        changed = True
                
                if changed:
                    try:
                        with open(event_master_path, 'w', encoding='utf-8') as f:
                            json.dump(event_list, f, ensure_ascii=False, indent=2)
                        
                        # Drive同期（ローカル環境のみ実行。クラウドは_is_cloud()ガードで自動スキップ）
                        try:
                            from logic.drive_utils import upload_to_drive, EVENT_MASTER_DRIVE_ID
                            if upload_to_drive and EVENT_MASTER_DRIVE_ID:
                                _ok, _msg = upload_to_drive(event_master_path, EVENT_MASTER_DRIVE_ID)
                                if _ok:
                                    st.success("✅ 応募ステータスを保存 & Drive同期しました")
                                else:
                                    st.warning(f"⚠️ ローカル保存OK、Drive同期失敗: {_msg}")
                            else:
                                st.success("✅ 応募ステータスを保存しました")
                        except ImportError:
                            st.success("✅ 応募ステータスを保存しました（Drive同期なし）")
                        
                        st.rerun()
                    except Exception as e:
                        st.error(f"保存エラー: {e}")
        except Exception:
            pass

    st.divider()
    if st.button("🔄 最新データに更新", use_container_width=True, help="Driveから最新のメニュー.xlsxを再取得します"):
        try:
            with st.spinner("Google Driveから最新マスタを取得中..."):
                # キャッシュを破棄してDriveから強制再取得
                st.cache_data.clear()
                new_master_df, _, new_sheets, new_bytes = load_data_from_drive()
                if new_master_df is not None:
                    master_list = convert_dataframe_to_json(new_master_df, force=True)
                    
                    # 更新後即座に合算を実行
                    master_list = merge_event_targets(master_list, new_bytes, None)
                    
                    st.session_state['master_data'] = master_list
                    if new_sheets:
                        st.session_state['event_sheet_names'] = new_sheets
                    if new_bytes:
                        st.session_state['excel_bytes'] = new_bytes
                    st.success(f"✅ マスタデータ更新完了（{len(master_list)} 件）")
                else:
                    st.warning("⚠️ Driveからのデータ取得に失敗しました。認証情報を確認してください。")
        except Exception as e:
            st.error(f"❌ データ更新中にエラーが発生しました: {e}")
        st.rerun()

    st.divider()
    # QRコード表示はローカル時のみ（クラウドではローカルIP不要）
    if IS_LOCAL:
        st.markdown("### 📱 スマホ・ iPad で見る")
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = '127.0.0.1'
        app_url = f"http://{local_ip}:8501"
        qr_img = qrcode.make(app_url)
        buf = io.BytesIO()
        qr_img.save(buf, format='PNG')
        buf.seek(0)
        st.image(buf, caption="カメラで読み取ってアクセス", width=200)
        st.code(app_url, language=None)

# ---------------------------------------------------------
# TAB 1: STRATEGIC MIND UI (Integrated)
# ---------------------------------------------------------
if selection == "📅 Strategic Mind":
    if not IS_LOCAL:
        # クラウド環境ではStrategic Mind（iframe）は利用不可
        st.warning("☁️ この機能はローカル環境専用です。")
        st.markdown("日程の編集は [GAS画面](https://script.google.com) から直接行ってください。")
    else:
        # 1. Read Static Assets (Absolute Paths)
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            static_dir = os.path.join(base_dir, "static")
            
            with open(os.path.join(static_dir, "index.html"), "r", encoding="utf-8") as f:
                html_template = f.read()
            with open(os.path.join(static_dir, "style.css"), "r", encoding="utf-8") as f:
                css_content = f.read()
            with open(os.path.join(static_dir, "logic.js"), "r", encoding="utf-8") as f:
                js_content = f.read()
        except FileNotFoundError:
            st.error("Static files not found. Auto-recovery failed.")
            st.stop()

        # 2. Data Injection Strategy (Robust)
        # production_events -> JSON string
        events_json = json.dumps(production_events, ensure_ascii=False)
        
        # --- GUARDRAIL: Python-side Data Validation ---
        if production_events:
            st.toast(f"📊 Production Events: {len(production_events)} 件読み込み済み")
            # Validate each event has required fields
            bad_events = [i for i, e in enumerate(production_events) 
                          if not all(k in e for k in ('title', 'start', 'extendedProps'))]
            if bad_events:
                st.warning(f"⚠️ {len(bad_events)} 件の不正なイベントデータを検出。インデックス: {bad_events[:5]}")
                # Filter out bad events
                production_events = [e for e in production_events 
                                     if all(k in e for k in ('title', 'start', 'extendedProps'))]
                events_json = json.dumps(production_events, ensure_ascii=False)
        else:
            st.info("ℹ️ 生産イベントデータなし（ログが空か、90日以内のデータがありません）")
        
        try:
            json.loads(events_json)
        except json.JSONDecodeError as e:
            st.error(f"❌ JSON生成エラー: {e}")
            events_json = "[]"

        js_injected = js_content.replace('productionEvents: [],', f'productionEvents: {events_json},')
        
        if 'productionEvents: [],' not in js_content:
             split_marker = '(function () {'
             if split_marker in js_injected:
                 parts = js_injected.split(split_marker)
                 js_injected = parts[0] + f'\nPM.productionEvents = {events_json};\n' + split_marker + parts[1]
             else:
                 js_injected += f'\nPM.productionEvents = {events_json};\nPM.renderCalendar();\n'

        # 3. Construct Final HTML
        final_html = html_template.replace('/* INJECTED CSS WILL GO HERE */', css_content)
        final_html = final_html.replace('/* INJECTED LOGIC WILL GO HERE */', js_injected)

        # 4. Render Component
        components.html(final_html, height=850, scrolling=False)


# ---------------------------------------------------------
# TAB 2: INSPECTOR (DEBUG)
# ---------------------------------------------------------
elif selection == "📋 Inspector":
    st.header("🔍 Data Inspector")
    
    if log_df is not None:
        st.markdown("### Raw Log Data (Latest 20)")
        st.write("Checking for columns: **TIMESTAMP**, **PROJECT**, **PATH**, **PART**")
        
        cols = log_df.columns.tolist()
        required = ['TIMESTAMP', 'PROJECT', 'PATH']
        missing = [c for c in required if c not in cols]
        
        if missing:
            st.error(f"❌ Misisng Columns: {missing}")
            st.warning("Please verify CSV header row exists and matches strict naming.")
            st.code(f"Current columns: {cols}")
        else:
            try:
                disp_cols = required + (['PART'] if 'PART' in cols else [])
                display_df = log_df[disp_cols].copy()
                display_df['TIMESTAMP_PARSED'] = pd.to_datetime(display_df['TIMESTAMP'], errors='coerce')
                st.dataframe(display_df.tail(20), use_container_width=True)
            except Exception as e:
                st.error(f"Error displaying table: {e}")
                st.dataframe(log_df.tail(20))
    else:
        st.info("No log data loaded.")


# ---------------------------------------------------------
# TAB 3: CATALOG
# ---------------------------------------------------------
elif selection == "📦 Catalog":
    st.header("📦 Inventory Catalog")
    if not inventory_df.empty:
        cols = st.columns(3)
        for i, row in inventory_df.iterrows():
            with cols[i % 3]:
                render_catalog_card(row)
    else:
        st.info("No inventory data calculated.")


# ---------------------------------------------------------
# TAB 4: INPUT (Atlas CNC Log Entry)
# ---------------------------------------------------------
elif selection == "🏭 Input":
    st.header("🏭 加工実績入力 (Atlas)")
    if not IS_LOCAL:
        # クラウド環境ではInput（ローカルHTML）は利用不可
        st.warning("☁️ この機能はローカル環境専用です。")
        st.markdown("加工実績の入力は、ローカルPC上の Atlas Hub または GAS画面から行ってください。")
    else:
        st.caption("CNC加工ログをスプレッドシートに記録します。入力完了後、📅カレンダータブで反映を確認してください。")
        
        atlas_html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "atlas", "index.html")
        
        if os.path.exists(atlas_html_path):
            with open(atlas_html_path, "r", encoding="utf-8") as f:
                atlas_html = f.read()
            components.html(atlas_html, height=750, scrolling=True)
        else:
            st.warning(f"⚠️ Atlas入力画面が見つかりません: {atlas_html_path}")
            st.info("atlas/index.html をプロジェクトの隣に配置してください。")


# ---------------------------------------------------------
# TAB 5: STOCK (Inventory Confirmation & Management)
# ---------------------------------------------------------
elif selection == "📦 Stock":
    st.header("📦 在庫管理 & 生産確定")
    
    # --- 在庫確定キュー ---
    st.subheader("🔄 生産確定 (CONFIRMEDシートへ記録)")
    st.caption("確定ボタンを押すと、アトラスのスプレッドシートに確定記録が追記されます。マスタファイルは変更しません。")
    
    # 済みの Source Hashes を収集 (Dedup用: Hash Base)
    confirmed_hashes = set()
    if not confirmed_df.empty and 'SOURCE_HASHES' in confirmed_df.columns:
        for val in confirmed_df['SOURCE_HASHES'].dropna().astype(str):
            for h in val.split(','):
                if h.strip():
                    confirmed_hashes.add(h.strip())
    
    # 未確定イベントのみフィルタリング
    valid_events = []
    for evt in production_events:
        props = evt.get('extendedProps', {})
        src_hashes = props.get('source_hashes', '')
        
        # イベントに含まれるハッシュが一つでも確定済みなら「確定済み」とみなす
        is_confirmed = False
        if src_hashes:
            for h in src_hashes.split(','):
                if h.strip() in confirmed_hashes:
                    is_confirmed = True
                    break
        
        if not is_confirmed:
            valid_events.append(evt)
            
    if valid_events:
        high_conf = [e for e in valid_events if e.get('extendedProps', {}).get('confidence') == 'high']
        low_conf = [e for e in valid_events if e.get('extendedProps', {}).get('confidence') == 'low']
        
        if high_conf:
            st.markdown(f"### ⚔️ 確定可能な実績 ({len(high_conf)} 件)")
            
            for i, evt in enumerate(high_conf):
                props = evt.get('extendedProps', {})
                project = props.get('project', '不明')
                date = evt.get('start', '')
                source_hashes = props.get('source_hashes', '')
                atlas_ts = props.get('atlas_timestamp', '')
                
                col1, col2, col3 = st.columns([3, 4, 3])
                with col1:
                    st.markdown(f"**⚔️ {project}**")
                    st.caption(f"日付: {date}")
                with col2:
                    st.caption(f"加工時間: {atlas_ts}")
                with col3:
                    btn_key = f"confirm_{i}_{project}_{date}"
                    if st.button("✅ 確定", key=btn_key):
                        with st.spinner(f"{project} を確定記録中..."):
                            s1, m1 = confirm_production(project, "本体", source_hashes, atlas_ts)
                            s2, m2 = confirm_production(project, "鞘", source_hashes, atlas_ts)
                        if s1 and s2:
                            st.success(f"✅ {project} (本体+鞘) を確定しました")
                            st.balloons()
                            st.rerun() # リロード (Session StateでStockタブ維持)
                        elif s1:
                            st.warning(f"{m1}\n鞘の記録: {m2}")
                        else:
                            st.error(f"エラー: {m1}")
                st.divider()
        else:
            st.info("確定可能な高信頼度イベントはありません。")
        
        if low_conf:
            with st.expander(f"❓ 低信頼度イベント ({len(low_conf)} 件)"):
                st.caption("片面のみの加工記録です。")
                for i, evt in enumerate(low_conf):
                    props = evt.get('extendedProps', {})
                    project = props.get('project', '不明')
                    date = evt.get('start', '')
                    source_hashes = props.get('source_hashes', '')
                    atlas_ts = props.get('atlas_timestamp', '')
                    
                    col1, col2 = st.columns([4, 2])
                    with col1:
                        st.markdown(f"❓ **{project}** ({date})")
                    with col2:
                        btn_key = f"confirm_low_{i}_{project}_{date}"
                        if st.button("⚠️ 強制確定", key=btn_key, type="secondary"):
                            success, msg = confirm_production(project, "本体", source_hashes, atlas_ts)
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
    else:
        st.info("全ての生産イベントは確定済みです。")
    
    st.divider()
    
    # --- 現在の在庫一覧 (導出表示) ---
    st.subheader("📊 在庫状況 (マスタ初期値 + 確定数 - 販売数)")
    if not inventory_df.empty:
        display_cols = ['商品名', '本体', '鞘', '確定数', '販売数', 'status_text']
        available_cols = [c for c in display_cols if c in inventory_df.columns]
        st.dataframe(
            inventory_df[available_cols].rename(columns={'status_text': 'ステータス'}),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("在庫データなし。")
    
    # --- 確定履歴 ---
    if not confirmed_df.empty:
        with st.expander(f"📋 確定履歴 ({len(confirmed_df)} 件)"):
            st.dataframe(confirmed_df, use_container_width=True, hide_index=True)


# ---------------------------------------------------------
# TAB 6: 軍師Zeus (AI Chat with Gemini)
# ---------------------------------------------------------
elif selection == "⚔️ 軍師Zeus":
    st.header("⚔️ 軍師Zeus — アトラス工房AI軍師")
    st.caption("マスタデータと在庫状況を熟知したAI軍師に、生産計画や加工時間について相談できます。")

    # --- APIキーチェック ---
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        st.error(
            "⚠️ Gemini APIキーが設定されていません。\n\n"
            "`.streamlit/secrets.toml` を開いて `GEMINI_API_KEY` に有効なキーを設定してください。\n\n"
            "APIキーは [Google AI Studio](https://aistudio.google.com/apikey) で無料で取得できます。"
        )
        st.stop()

    # --- チャットセッション初期化（履歴のみ管理） ---
    if "zeus_messages" not in st.session_state:
        st.session_state.zeus_messages = []

    # --- コントロールバー ---
    col1, col2 = st.columns([6, 1])
    with col1:
        master_count = len(st.session_state.get("master_data", []))
        inv_count = len(inventory_df) if not inventory_df.empty else 0
        st.caption(f"📦 コンテキスト: マスタ {master_count} 件 / 在庫 {inv_count} 件")
    with col2:
        if st.button("🔄 リセット", use_container_width=True):
            st.session_state.zeus_messages = []
            st.rerun()

    st.divider()

    # --- チャット履歴表示 ---
    for msg in st.session_state.zeus_messages:
        with st.chat_message(msg["role"], avatar="⚔️" if msg["role"] == "assistant" else None):
            st.markdown(msg["content"])

    # --- ウェルカムメッセージ ---
    if not st.session_state.zeus_messages:
        with st.chat_message("assistant", avatar="⚔️"):
            welcome = (
                "我はアトラス工房の軍師、**Zeus**。\n\n"
                "工房の生産データを全て把握しておる。何でも聞いてくれ。\n\n"
                "例えば…\n"
                "- 「大斧のNC加工にどのくらい時間かかる？」\n"
                "- 「在庫が少ない商品は？」\n"
                "- 「ロト剣と伝説剣、どっちが加工時間長い？」\n"
                "- 「イベントに向けて何を優先的に作るべき？」"
            )
            st.markdown(welcome)

    # --- チャット入力 ---
    if user_input := st.chat_input("軍師Zeusに質問する..."):
        # ユーザーメッセージ表示
        st.session_state.zeus_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # AI応答取得
        with st.chat_message("assistant", avatar="⚔️"):
            with st.spinner("軍師Zeus 思考中..."):
                # 最新のマスタ＆在庫情報でプロンプト再構築（常に最新情報）
                # 最新のマスタ＆在庫情報でプロンプト再構築（常に最新情報）
                master_data = st.session_state.get("master_data", [])
                
                # イベント情報の取得（Zeusへのコンテキスト注入）
                # 新ロジック: マスタデータからアクティブイベント名を取得
                current_event = "（イベントマスタ設定による複数イベント合算）"
                if master_data and 'event_data' in master_data[0]:
                    current_event = master_data[0]['event_data'].get('アクティブイベント', current_event)
                all_events = st.session_state.get('event_sheet_names', [])
                # System Prompt構築（ユーザー入力を渡して検索させる）
                system_prompt = build_system_prompt(
                    st.session_state['master_data'],
                    inventory_df, 
                    current_event_name=current_event,
                    all_event_names=all_events,
                    user_message=user_input # Assuming 'prompt' is not defined, keeping 'user_input' as per original logic for the actual message. If 'prompt' was meant to be a new variable, it needs to be defined. Sticking to the instruction's literal change for the argument name.
                )
                
                # 直前のメッセージを除いた履歴を渡す（今回の入力は引数で渡すため）
                history_for_api = st.session_state.zeus_messages[:-1]
                
                # --- Debug: Show System Prompt ---
                with st.expander("🔍 Debug: System Prompt (Context)", expanded=False):
                    st.code(system_prompt, language="text")

                response = get_chat_response(
                    api_key, 
                    system_prompt, 
                    history_for_api, 
                    user_input
                )
            st.markdown(response)

        st.session_state.zeus_messages.append({"role": "assistant", "content": response})


# ---------------------------------------------------------
# TAB 7: BI DASHBOARD (Production BI)
# ---------------------------------------------------------
elif selection == "📊 BI Dashboard":
    st.header("📊 生産管理BIダッシュボード")
    st.caption("スマホで一目把握。イベント準備の全体像をリアルタイム表示。")

    master_data = st.session_state.get('master_data', [])

    if not master_data:
        st.warning("⚠️ マスタデータが読み込まれていません。サイドバーの『マスタ更新』を実行してください。")
        st.stop()

    # ==========================
    # カレンダー統合データ読み込み（キャッシュから取得）
    # ==========================
    calendar_data = calendar_data_cache

    # ==========================
    # 🚨 Google Tasks アラート（期日付きタスク）
    # ==========================
    google_tasks = calendar_data.get('google_tasks', [])
    if google_tasks:
        # 期日が30日以内のタスクを取得
        display_tasks = [t for t in google_tasks if t.get('days_until') is not None and t['days_until'] <= 30]
        
        # 期日が近い順にソート（3日以内などの緊急タスクが上に来るように）
        display_tasks.sort(key=lambda x: x['days_until'])

        if display_tasks:
            for t in display_tasks:
                days = t['days_until']
                
                # 3日以内または期限切れは警告色（赤）、それ以外は通常色
                if days < 0:
                    emoji = "🚨"
                    label = f"期限超過 {abs(days)}日"
                    card_cls = "bi-ng"  # 赤背景
                    text_color = "#ff8a80"
                elif days == 0:
                    emoji = "🔴"
                    label = "本日期限"
                    card_cls = "bi-ng"
                    text_color = "#ff8a80"
                elif days <= 3:
                    emoji = "🟠"
                    label = f"あと{days}日"
                    card_cls = "bi-ng"  # 警告色維持
                    text_color = "#ff8a80"
                else:
                    emoji = "📅"
                    label = f"あと{days}日"
                    card_cls = ""  # デフォルト（青系）
                    text_color = "#a0d2db"

                st.markdown(f"""
                <div class="bi-card {card_cls}" style="padding: 0.8rem 1.2rem; margin-bottom: 0.5rem;">
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span style="font-size: 1.5rem;">{emoji}</span>
                        <div>
                            <div style="color: #fff; font-weight: 700; font-size: 1rem;">{t['title']}</div>
                            <div style="color: {text_color}; font-size: 0.8rem;">{label} | 期日: {t['due_date']} | {t.get('task_list', '')}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.divider()

    # ==========================
    # ⚔️ 軍師の提案（アグレッシブスケジュール）
    # ==========================
    suggestions = calendar_data.get('aggressive_suggestions', [])
    if suggestions:
        st.markdown("#### ⚔️ 軍師の限界突破スケジュール提案")
        st.caption("カレンダーの隙間を突いた攻めの生産計画。あえて無茶な提案をし、マスターデータの精緻化を促します。")

        for sg in suggestions:
            sg_type = sg.get('type', '')
            priority = sg.get('priority', 3)

            # 優先度に応じたカードスタイル
            if priority == 1:
                card_cls = "bi-alert"
            elif priority == 2:
                card_cls = "bi-countdown"
            else:
                card_cls = "bi-card"

            st.markdown(f"""
            <div class="bi-card {card_cls}" style="padding: 0.8rem 1.2rem;">
                <div style="color: #fff; font-weight: 700; font-size: 0.95rem; margin-bottom: 0.4rem;">
                    {sg['message']}
                </div>
                <div style="color: #a0d2db; font-size: 0.8rem; margin-bottom: 0.3rem;">
                    💪 効果: {sg['impact']}
                </div>
                <div style="color: #ffd93d; font-size: 0.75rem; font-style: italic;">
                    {sg['nudge']}
                </div>
            </div>
            """, unsafe_allow_html=True)

        # ナッジメッセージ（マスターデータ精緻化の促進）
        st.info(
            "💡 **軍師からの助言:** 上記の提案は「カレンダーの予定」と「ToDoリストの期限」を基に算出しています。\n\n"
            "以下の情報を入力すると精度がさらに向上します:\n"
            "- 🏠 家族の予定（子供の送迎、習い事、通院など）\n"
            "- 🛒 買い出し・用事の時間\n"
            "- 🚗 移動時間\n"
            "- 🍽️ 食事・休憩時間\n"
            "- ✅ 事務作業や買い出しの期限（Google ToDo）\n\n"
            "**カレンダーやToDoが精緻であるほど、軍師の提案は現実的になります。**"
        )
        st.divider()

    # ==========================
    # KPI 1: カウントダウン
    # ==========================
    countdown = calc_countdown()
    if countdown:
        days = countdown['days_remaining']
        # 緊急度による色分け
        if days <= 14:
            urgency_emoji = "🔴"
        elif days <= 30:
            urgency_emoji = "🟡"
        else:
            urgency_emoji = "🟢"

        st.markdown(f"""
        <div class="bi-card bi-countdown">
            <h3>🗓️ イベントカウントダウン</h3>
            <div class="bi-value">{urgency_emoji} あと {days} 日</div>
            <div class="bi-sub">{countdown['event_name']} ({countdown['event_date']}) @ {countdown['venue']}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("アクティブなイベントが設定されていません。")

    # ==========================
    # KPI 2: 目標売上ギャップ
    # ==========================
    gap = calc_sales_gap(master_data)
    st.markdown(f"""
    <div class="bi-card bi-revenue">
        <h3>💰 目標売上 vs 現在完成額</h3>
        <div class="bi-value">¥{gap['current_revenue']:,} / ¥{gap['target_revenue']:,}</div>
        <div class="bi-sub">ギャップ: ¥{gap['gap']:,} | 進捗率: {gap['progress_ratio']:.0%}</div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(gap['progress_ratio'])

    # ==========================
    # バーンアップチャート
    # ==========================
    burnup = calc_burnup_data(master_data, excel_bytes=st.session_state.get('excel_bytes'))
    if burnup and burnup['actual']:
        st.markdown("#### 📈 目標 vs 実績 フィーバーチャート")

        fig = go.Figure()

        # 実績ライン
        actual_dates = [a['date'] for a in burnup['actual']]
        # キャッシュ残存時の安全対策として get を使用
        actual_values = [a.get('revenue', a.get('count', 0)) for a in burnup['actual']]
        fig.add_trace(go.Scatter(
            x=actual_dates,
            y=actual_values,
            mode='lines+markers',
            name='実績',
            line=dict(color='#00d4ff', width=3, shape='spline'),
            marker=dict(size=7, color='#00d4ff', line=dict(width=1, color='white')),
            hovertemplate='%{x}<br><b>¥%{y:,.0f}</b><extra>実績</extra>',
        ))

        # 目標ペースライン（3本）
        target_colors = ['#ff6b6b', '#ffd93d', '#6bcb77']
        target_dashes = ['dash', 'dot', 'dashdot']
        for i, tgt in enumerate(burnup['targets']):
            fig.add_trace(go.Scatter(
                x=[burnup['start_date'], burnup['event_date']],
                y=[0, tgt['value']],
                mode='lines',
                name=tgt['label'],
                line=dict(color=target_colors[i], width=2, dash=target_dashes[i]),
                hovertemplate=f"{tgt['label']}<br>"+"%{x}<br>¥%{y:,.0f}<extra></extra>",
            ))

        # レイアウト（ダークテーマ、スマホ対応）
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='rgba(26,26,46,0.9)',
            plot_bgcolor='rgba(15,52,96,0.4)',
            height=380,
            margin=dict(l=50, r=20, t=30, b=50),
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='center',
                x=0.5,
                font=dict(size=11),
            ),
            xaxis=dict(
                title='',
                gridcolor='rgba(255,255,255,0.1)',
                showgrid=True,
            ),
            yaxis=dict(
                title='資産額 (円)',
                gridcolor='rgba(255,255,255,0.1)',
                showgrid=True,
                tickformat=',d',
            ),
            hovermode='x unified',
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📈 履歴データが不足しています。スキャンを蓄積するとチャートが表示されます。")

    st.divider()

    # ==========================
    # KPI 3: 残り加工時間 & 効率ルート
    # ==========================
    hours = calc_remaining_hours(master_data)
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("🔧 NC残時間", f"{hours['total_nc_hours']}h")
    with col_b:
        st.metric("✋ 手作業残時間", f"{hours['total_manual_hours']}h")

    st.markdown(f"""
    <div class="bi-card">
        <h3>⏱️ 残り総加工時間</h3>
        <div class="bi-value">{hours['total_hours']} 時間</div>
        <div class="bi-sub">NC: {hours['total_nc_hours']}h / 手作業: {hours['total_manual_hours']}h</div>
    </div>
    """, unsafe_allow_html=True)

    if hours['efficiency_ranking']:
        st.markdown("#### 🏆 最適生産ルート（売上効率順）")
        for rank, item in enumerate(hours['efficiency_ranking'], 1):
            medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][rank - 1]
            st.markdown(
                f"{medal} **{item['name']}** ({item['part']}) "
                f"— ¥{item['yen_per_min']}/分 | "
                f"残{item['remaining']}個 | "
                f"NC:{item['nc_min_per_unit']}分 + 手:{item['manual_min_per_unit']}分"
            )

    st.divider()

    # ==========================
    # KPI 4: 本日の最適タスク
    # ==========================
    tasks = calc_today_tasks(master_data)

    if tasks['all_done']:
        st.markdown(f"""
        <div class="bi-card bi-ok">
            <h3>📋 本日のタスク</h3>
            <div class="bi-value">🎉 全目標達成！</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        card_class = "bi-alert" if tasks['is_night_mode'] else "bi-card"
        mode_label = "🌙 夜間モード" if tasks['is_night_mode'] else "☀️ 日中モード"

        nc_html = ""
        if tasks['recommended_nc']:
            nc = tasks['recommended_nc']
            nc_html = f"<div class='bi-sub'>🔧 NC推奨: {nc['name']}（{nc['part']}）残{nc['remaining']}個 — {nc['nc_machine_type']}で{nc['nc_min']}分/個</div>"
        elif tasks['nc_available']:
            nc_html = "<div class='bi-sub'>🔧 NC: 対象なし</div>"
        else:
            nc_html = "<div class='bi-sub'>🔇 NC: 夜間のため停止推奨</div>"

        manual_html = ""
        if tasks['recommended_manual']:
            m = tasks['recommended_manual']
            manual_html = f"<div class='bi-sub'>✋ 手作業推奨: {m['name']}（{m['part']}）残{m['remaining']}個 — {m['manual_min']}分/個</div>"

        st.markdown(f"""
        <div class="bi-card {card_class}">
            <h3>📋 本日の最適タスク</h3>
            <div class="bi-value">{mode_label}</div>
            {nc_html}
            {manual_html}
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ==========================
    # KPI 5: 材料発注アラート
    # ==========================
    mat_info = calc_material_alerts(master_data)

    if mat_info['alerts']:
        for alert_msg in mat_info['alerts']:
            st.warning(alert_msg)

    st.markdown("#### 🪵 材料消費予測")
    for mat_name, mat_data in mat_info['materials'].items():
        card_cls = "bi-alert" if mat_data['alert'] else "bi-card"
        st.markdown(f"""
        <div class="bi-card {card_cls}">
            <h3>🪵 {mat_name}</h3>
            <div class="bi-value">{mat_data['boards_needed']} 枚必要</div>
            <div class="bi-sub">{mat_data['remaining_count']}個分 | 内訳: {', '.join(mat_data['items'][:3])}</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ==========================
    # KPI 6: 新作開発枠
    # ==========================
    dev = calc_dev_slot(master_data)
    if dev['is_ok']:
        card_cls = "bi-ok"
    elif dev['progress_ratio'] >= 0.5:
        card_cls = "bi-alert"
    else:
        card_cls = "bi-ng"

    st.markdown(f"""
    <div class="bi-card {card_cls}">
        <h3>🆕 新作開発枠</h3>
        <div class="bi-value">{dev['message']}</div>
        <div class="bi-sub">進捗: {dev['progress_ratio']:.0%} | 残日数: {dev['days_remaining']}日</div>
    </div>
    """, unsafe_allow_html=True)
