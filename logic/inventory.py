
import pandas as pd
import re
import io
# drive_utils imports will be handled within function to avoid circular imports or context issues if necessary,
# but usually it's better to pass the service or use the module. 
# Here we will import drive_utils inside the function or at top level if safe.
from logic import drive_utils
import streamlit as st

def normalize_text(text):
    if pd.isna(text): return ""
    # 全角半角・空白・大文字小文字を統一して「比較専用のキー」を作る
    return re.sub(r'\s+', '', str(text)).lower().translate(str.maketrans(
        '０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ',
        '0123456789abcdefghijklmnopqrstuvwxyz'
    ))

def calculate_inventory(master_df, log_df, confirmed_df=None):
    # === 【最終運用仕様】販売ログ減算・部位表示制御 ===
    
    # 1. カラム特定 (柔軟検索)
    def find_col(df, keywords):
        for col in df.columns:
            if any(k in str(col) for k in keywords):
                return col
        return None

    name_col = find_col(master_df, ['商品名', 'Project', 'Name', '品名'])
    part_col = find_col(master_df, ['部位', 'Part', 'Category', 'Type'])
    stock_col = find_col(master_df, ['在庫数', '在庫', 'Stock', 'Qty', '数量'])
    price_col = find_col(master_df, ['単価', '価格', 'Price', '金額'])

    if not name_col:
        return pd.DataFrame(columns=['商品名', 'セット価格', '本体', '鞘', 'status_text', 'has_sheath'])

    # 2. 販売ログの集計 (Sales Count)
    sales_map = {}
    if log_df is not None and not log_df.empty:
        # 製品名と工程のカラムを探す
        l_name_col = find_col(log_df, ['project', 'Project', '商品名', 'Job'])
        l_proc_col = find_col(log_df, ['path', 'Path', '工程', 'Process', 'Status']) # 工程情報
        
        if l_name_col and l_proc_col:
            # 正規化キー作成
            log_df['join_key'] = log_df[l_name_col].fillna("").astype(str).apply(normalize_text)
            
            # 販売行を抽出 (キーワード: 販売, 売上, 売れた)
            def is_sales(val):
                s = str(val)
                return any(k in s for k in ['販売', '売上', '売れた'])
                
            sales_logs = log_df[log_df[l_proc_col].apply(is_sales)]
            
            # 商品ごとの販売数をカウント
            sales_map = sales_logs['join_key'].value_counts().to_dict()

    # 3. マスタデータのグルーピング設定
    master_df['join_key'] = master_df[name_col].astype(str).apply(normalize_text)
    
    # 除外フィルタ: 空行, "合計"
    df_clean = master_df[
        (master_df['join_key'] != "") & 
        (master_df[name_col] != "合計")
    ].copy()
    
    result_rows = []
    
    for key, group in df_clean.groupby('join_key'):
        first_row = group.iloc[0]
        product_name = first_row[name_col]
        
        # 価格
        try: price = int(float(group[price_col].max())) if price_col else 0
        except: price = 0
            
        # マスタ在庫集計 & 鞘フラグ判定
        body_stock_master = 0
        sheath_stock_master = 0
        has_sheath = False
        
        for _, row in group.iterrows():
            try: qty = int(float(row.get(stock_col, 0)))
            except: qty = 0
            
            part_val = str(row.get(part_col, ""))
            # 鞘判定
            if "鞘" in part_val or "saya" in part_val.lower() or "sheath" in part_val.lower():
                sheath_stock_master += qty
                has_sheath = True
            else:
                body_stock_master += qty
        
        # 販売分を減算 (Sales count)
        sales_count = sales_map.get(key, 0)
        
        # --- CONFIRMED (導出方式): 確定記録から生産数を加算 ---
        confirmed_produced = 0
        confirmed_cancelled = 0
        if confirmed_df is not None and not confirmed_df.empty:
            proj_col = 'PROJECT' if 'PROJECT' in confirmed_df.columns else None
            act_col = 'ACTION' if 'ACTION' in confirmed_df.columns else None
            if proj_col and act_col:
                # 正規化して比較
                matched = confirmed_df[
                    confirmed_df[proj_col].fillna('').apply(normalize_text) == key
                ]
                confirmed_produced = len(matched[matched[act_col] == 'PRODUCED'])
                confirmed_cancelled = len(matched[matched[act_col] == 'CANCEL'])
        
        net_confirmed = confirmed_produced - confirmed_cancelled
        
        # 在庫 = マスタ初期値(H列) + 確定生産数 - 販売数
        remaining_body = max(0, body_stock_master + net_confirmed - sales_count)
        if has_sheath:
            remaining_sheath = max(0, sheath_stock_master + net_confirmed - sales_count)
        else:
            remaining_sheath = 0
            
        # ステータス判定
        status = "在庫なし"
        if remaining_body >= 1:
            status = "在庫あり"
        
        result_rows.append({
            '商品名': product_name,
            'セット価格': price,
            '本体': remaining_body,
            '鞘': remaining_sheath,
            'status_text': status,
            'join_key': key,
            'has_sheath': has_sheath,
            '確定数': net_confirmed,
            '販売数': sales_count
        })
        
    result_df = pd.DataFrame(result_rows)
    if result_df.empty:
        result_df = pd.DataFrame(columns=['商品名', 'セット価格', '本体', '鞘', 'status_text', 'has_sheath', '確定数', '販売数'])

    return result_df

def confirm_production(project, part="本体", source_hashes="", atlas_timestamp=""):
    """
    生産確定: CONFIRMEDシートに記録を追記する。
    マスタファイル(H列)は一切変更しない。
    
    project: 商品名
    part: 部位 (本体/鞘)
    source_hashes: 元ログのハッシュ値 (SHA256)
    atlas_timestamp: 加工日時
    return: (success: bool, message: str)
    """
    return drive_utils.append_to_confirmed_sheet(
        project=project,
        part=part,
        action="PRODUCED",
        source_hashes=source_hashes,
        atlas_timestamp=atlas_timestamp
    )


def cancel_confirmation(project, part="本体"):
    """
    確定取消し: CONFIRMEDシートにCANCEL記録を追記する。
    データは削除せず、CANCEL行を追加して打ち消す。
    
    return: (success: bool, message: str)
    """
    return drive_utils.append_to_confirmed_sheet(
        project=project,
        part=part,
        action="CANCEL",
        source_rows="manual_cancel"
    )
