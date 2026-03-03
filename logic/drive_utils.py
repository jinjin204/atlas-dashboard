import os
import io
import mimetypes
import pandas as pd
import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/tasks.readonly'
]
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'
TARGET_FOLDER_ID = "1swLvCAzeFx8N9DhG5jfeUXPvlhCmCK6i"

# --- ファイルID直接指定（検索不要・クラウドでも確実） ---
MASTER_FILE_ID = "127mB52AEe-c9RziCiyfFyzRgCK6dYoi9"          # メニュー.xlsx
MASTER_FILE_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
LOG_FILE_ID = "1N9Rmg3z_Iohvrpd5QPtVSvstozuOYp0117PSVjUKq-U"  # アトラス (Google Spreadsheet)
LOG_FILE_MIME = "application/vnd.google-apps.spreadsheet"

# --- Phase 1: クラウド同期対象ファイルのDrive ID ---
HISTORY_SUMMARY_DRIVE_ID = "1LTM58WGFT27DpEZ_1TPBeQiJcSr6-uRT"
ATLAS_LOG_DRIVE_ID = "1N9Rmg3z_Iohvrpd5QPtVSvstozuOYp0117PSVjUKq-U"
EVENT_MASTER_DRIVE_ID = "1VrxYt_HpJflPNmp-UU39wXtbDXSsQ5Dk"

def _is_cloud():
    """ローカル環境かクラウド環境かを判定する"""
    if os.path.exists(TOKEN_FILE) or os.path.exists(CREDENTIALS_FILE):
        return False
    
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "google_oauth" in st.secrets:
            return True
    except Exception:
        pass
    return False

def _authenticate_cloud():
    """
    Streamlit Cloud用: st.secrets["google_oauth"] からOAuth2認証を復元する。
    リフレッシュトークンを使って自動的にアクセストークンを再取得する。
    """
    try:
        # st.secrets に google_oauth キーが存在するか安全にチェック
        if not hasattr(st, 'secrets'):
            print("[authenticate_cloud] st.secrets が利用不可")
            return None

        oauth_info = st.secrets.get("google_oauth", None)
        if not oauth_info:
            print("[authenticate_cloud] st.secrets に google_oauth キーが存在しません")
            return None

        refresh_token = oauth_info.get("refresh_token", "")
        if not refresh_token:
            print("[authenticate_cloud] refresh_token が設定されていません")
            return None

        creds = Credentials(
            token=oauth_info.get("token", ""),
            refresh_token=refresh_token,
            token_uri=oauth_info.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=oauth_info.get("client_id", ""),
            client_secret=oauth_info.get("client_secret", ""),
            scopes=SCOPES,
        )
        # トークンが期限切れの場合は自動リフレッシュ
        if not creds.valid:
            creds.refresh(Request())
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"☁️ クラウド認証エラー: {e}")
        print(f"[authenticate_cloud] ERROR: {e}")
        return None


def _authenticate_local():
    """ローカル用: token.json / credentials.json ファイルから認証する。"""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except:
                return None
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                st.error("Credential file missing.")
                return None
            try:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            except:
                return None
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            
    return build('drive', 'v3', credentials=creds)


def authenticate():
    """
    環境に応じて適切な認証方法を選択する。
    ローカルの token.json を最優先で試行し、失敗時のみクラウド認証にフォールバック。
    """
    # 1. ローカルの token.json が存在すれば最優先で使用
    if os.path.exists(TOKEN_FILE):
        print("[authenticate] token.json が存在 → ローカル認証を優先")
        result = _authenticate_local()
        if result:
            return result
        print("[authenticate] ローカル認証失敗 → クラウド認証にフォールバック")

    # 2. token.json が無い場合、環境判定してクラウドまたはローカル認証
    if _is_cloud():
        return _authenticate_cloud()
    else:
        return _authenticate_local()


def find_file(service, keyword):
    try:
        query = f"name contains '{keyword}' and trashed = false and '{TARGET_FOLDER_ID}' in parents"
        results = service.files().list(q=query, pageSize=10, fields="files(id, name, mimeType)", orderBy="modifiedTime desc").execute()
        items = results.get('files', [])
        if not items:
            print(f"[find_file] No files found for keyword '{keyword}'")
            return None
        # ~$ で始まるExcel一時ファイルを除外
        for item in items:
            if not item['name'].startswith('~$'):
                print(f"[find_file] Found: {item['name']} (ID: {item['id']})")
                return item
        print(f"[find_file] All results were temp files (~$) for keyword '{keyword}'")
        return None
    except Exception as e:
        print(f"[find_file] Error searching for '{keyword}': {e}")
        return None

def download_content(service, file_id, mime_type):
    """
    Driveファイルをダウンロードする。
    - Google Workspaceファイル (Sheets等): export API でエクスポート
    - 通常ファイル (xlsx, pdf等): get_media で直接ダウンロード
    """
    try:
        print(f"[download] file_id={file_id}, mime_type={mime_type}")
        
        if 'google-apps' in mime_type:
            # Google Workspaceファイルのエクスポート
            if 'spreadsheet' in mime_type:
                export_mime = 'text/csv'
            elif 'document' in mime_type:
                export_mime = 'text/plain'
            else:
                export_mime = 'application/pdf'
            
            print(f"[download] Exporting as {export_mime}")
            request = service.files().export_media(fileId=file_id, mimeType=export_mime)
        else:
            # 通常ファイルの直接ダウンロード
            print(f"[download] Direct download (get_media)")
            request = service.files().get_media(fileId=file_id)
        
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        fh.seek(0)
        size = fh.getbuffer().nbytes
        print(f"[download] OK - {size} bytes")
        
        if size == 0:
            print("[download] WARNING: Downloaded 0 bytes")
            return None
        
        return fh
    except Exception as e:
        print(f"[download] FAIL: {type(e).__name__}: {e}")
        # エラーを再伝播して呼び出し元でキャッチできるようにする
        raise

# --- 在庫書き戻し用関数 (inventory.py から呼び出される) ---

def find_file_by_partial_name(service, keyword, folder_id=None):
    """
    ファイル名の部分一致でDriveファイルを検索。
    Returns: (file_id, mime_type, file_name) or None
    """
    try:
        fid = folder_id or TARGET_FOLDER_ID
        query = f"name contains '{keyword}' and trashed = false and '{fid}' in parents"
        results = service.files().list(
            q=query, pageSize=1,
            fields="files(id, name, mimeType)",
            orderBy="modifiedTime desc"
        ).execute()
        items = results.get('files', [])
        if not items:
            return None
        f = items[0]
        return (f['id'], f['mimeType'], f['name'])
    except Exception as e:
        st.error(f"Drive検索エラー: {e}")
        return None


def download_file_content(service, file_id, mime_type):
    """
    ファイルをバイナリストリームとしてダウンロード。
    Google Spreadsheet形式の場合はCSVエクスポート、
    それ以外(xlsx等)はバイナリダウンロード。
    Returns: io.BytesIO or None
    """
    try:
        if mime_type == 'application/vnd.google-apps.spreadsheet':
            request = service.files().export_media(fileId=file_id, mimeType='text/csv')
        else:
            request = service.files().get_media(fileId=file_id)

        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)
        return fh
    except Exception as e:
        st.error(f"ダウンロードエラー: {e}")
        return None


def update_file_content(service, file_id, stream, mime_type):
    """
    Driveファイルの内容を上書きアップロードする。
    stream: io.BytesIO (書き込むバイナリデータ)
    mime_type: アップロードするファイルのMIMEタイプ
    Returns: updated file metadata dict or None
    """
    try:
        media = MediaIoBaseUpload(stream, mimetype=mime_type, resumable=True)
        updated_file = service.files().update(
            fileId=file_id,
            media_body=media
        ).execute()
        return updated_file
    except Exception as e:
        st.error(f"アップロードエラー: {e}")
        return None


def get_file_modified_time(service, file_id):
    """
    楽観的ロック用: ファイルの最終更新日時を取得。
    Returns: modifiedTime string or None
    """
    try:
        file_meta = service.files().get(
            fileId=file_id,
            fields='modifiedTime'
        ).execute()
        return file_meta.get('modifiedTime')
    except Exception as e:
        st.error(f"メタデータ取得エラー: {e}")
        return None


# --- CONFIRMED ログ管理 (ローカルCSV方式) ---
# Sheets API不要。ローカルCSVファイルに追記する。
# 単一マシンの工房向け。将来的にCloud同期を追加可能。

import csv
from datetime import datetime

CONFIRMED_HEADERS = ["TIMESTAMP", "PROJECT", "PART", "ACTION", "SOURCE_HASHES", "ATLAS_TIMESTAMP"]


def _get_confirmed_path():
    """CONFIRMEDログファイルのパスを返す。data/ ディレクトリがなければ作成。"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(base_dir), "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "confirmed_log.csv")


def append_to_confirmed_sheet(project, part, action="PRODUCED", source_hashes="", atlas_timestamp=""):
    """
    CONFIRMEDログに1行追記する（ローカルCSV）。
    Append-Only: 既存データは一切変更しない。
    
    Returns: (success: bool, message: str)
    """
    try:
        filepath = _get_confirmed_path()
        file_exists = os.path.exists(filepath)
        
        timestamp = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        row = [timestamp, project, part, action, source_hashes, atlas_timestamp]
        
        with open(filepath, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(CONFIRMED_HEADERS)
            writer.writerow(row)
        
        return True, f"✅ {project}({part}) を確定記録しました [{action}]"
        
    except Exception as e:
        return False, f"確定記録エラー: {e}"


def read_confirmed_sheet():
    """
    CONFIRMEDログの全データをDataFrameとして取得。
    ファイルが存在しない場合は空のDataFrameを返す。
    
    Returns: pd.DataFrame
    """
    try:
        filepath = _get_confirmed_path()
        
        if not os.path.exists(filepath):
            return pd.DataFrame(columns=CONFIRMED_HEADERS)
        
        df = pd.read_csv(filepath, encoding='utf-8')
        return df
        
    except Exception as e:
        return pd.DataFrame(columns=CONFIRMED_HEADERS)


@st.cache_data(show_spinner=False, ttl=600)
def load_data_from_drive():
    """
    Load Master and Log data with UI feedback.
    Applies st.empty() to clear status after loading.
    """
    status_area = st.empty()
    status_area.info("🔵 Connecting to Google Drive...")
    print("[load_data] Step 1: Authenticating...")
    
    try:
        service = authenticate()
    except Exception as e:
        status_area.error(f"❌ 認証エラー: {e}")
        return None, None, [], None

    if not service:
        status_area.error("❌ 認証失敗")
        return None, None, [], None
    print("[load_data] Step 1: OK")
        
    status_area.info("🔵 Downloading files...")
    print("[load_data] Step 2: Downloading by direct file ID...")

    # ファイルID直接指定でダウンロード（検索不要）
    try:
        master_stream = download_content(service, MASTER_FILE_ID, MASTER_FILE_MIME)
    except Exception as e:
        master_stream = None
        st.warning(f"⚠️ Masterダウンロードエラー: {e}")

    try:
        log_stream = download_content(service, LOG_FILE_ID, LOG_FILE_MIME)
    except Exception as e:
        log_stream = None
        st.warning(f"⚠️ Logダウンロードエラー: {e}")
    
    if not master_stream:
        print("[load_data] FAIL: master_stream is None")
    if not log_stream:
        print("[load_data] FAIL: log_stream is None")
    
    status_area.success("✅ Download Complete!")
    
    # Parse Master (xlsx)
    master_df = None
    if master_stream:
        try:
            master_df = pd.read_excel(master_stream, sheet_name="商品マスタ")
            print(f"[load_data] Step 5: Master parsed OK ({len(master_df)} rows)")
        except Exception as e:
            print(f"[load_data] FAIL: pd.read_excel error: {e}")
            st.warning(f"⚠️ Masterパースエラー: {e}")
            master_df = None
    
    # イベントシート名一覧を取得
    event_sheet_names = []
    excel_bytes = None
    EXCLUDE_SHEETS = {'商品マスタ', 'データ構造', 'Sheet2'}
    if master_stream:
        try:
            master_stream.seek(0)
            excel_bytes = master_stream.read()
            xls = pd.ExcelFile(io.BytesIO(excel_bytes))
            event_sheet_names = [s for s in xls.sheet_names if s not in EXCLUDE_SHEETS]
            print(f"[load_data] Event sheets: {event_sheet_names}")
        except Exception as e:
            print(f"[load_data] WARNING: Could not read sheet names: {e}")
    
    # Parse Log (CSV)
    log_df = None
    if log_stream:
        try:
            log_df = pd.read_csv(log_stream)
            print(f"[load_data] Step 6: Log parsed OK ({len(log_df)} rows)")
        except Exception as e:
            print(f"[load_data] FAIL: pd.read_csv error: {e}")
            log_df = None
    
    # Clear Status
    status_area.empty()
    
    return master_df, log_df, event_sheet_names, excel_bytes


def upload_to_drive(local_path, drive_file_id):
    """
    ローカルファイルをGoogleドライブ上の既存ファイルに上書きアップロードする。
    
    Phase 1 用: スキャンやログ追記の直後に呼び出し、
    Googleドライブ上の同名ファイルを自動更新する。

    Args:
        local_path (str): アップロードするローカルファイルのパス。
        drive_file_id (str): 上書き先のGoogleドライブ上のファイルID。

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # WEB環境（Streamlit Cloud）ではデータの破壊を防ぐためアップロードを完全禁止する
        if _is_cloud():
            msg = "WEB環境のためDriveへのアップロード処理をスキップしました (Read-Only)"
            print(f"[upload_to_drive] {msg}")
            return True, msg

        if not os.path.exists(local_path):
            return False, f"❌ ファイルが見つかりません: {local_path}"

        # 認証
        service = authenticate()
        if not service:
            return False, "❌ Google Drive認証に失敗しました"

        # MIMEタイプを自動判定
        mime_type, _ = mimetypes.guess_type(local_path)
        if mime_type is None:
            mime_type = "application/octet-stream"

        # ローカルファイルをバイナリストリームとして読み込み
        with open(local_path, "rb") as f:
            stream = io.BytesIO(f.read())

        # Driveへ上書きアップロード
        result = update_file_content(service, drive_file_id, stream, mime_type)

        if result:
            file_name = result.get("name", drive_file_id)
            print(f"[upload_to_drive] ✅ '{local_path}' → Drive '{file_name}' アップロード完了")
            return True, f"✅ '{os.path.basename(local_path)}' をドライブへアップロードしました"
        else:
            return False, "❌ アップロードに失敗しました（update_file_content が None を返しました）"

    except Exception as e:
        print(f"[upload_to_drive] ERROR: {e}")
        return False, f"❌ アップロードエラー: {e}"

