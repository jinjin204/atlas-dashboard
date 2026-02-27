import streamlit as st
from .ProgressView import render_progress_view

def render_catalog_card(row):
    """
    カタログカードを描画するコンポーネント
    """
    product_name = row.get('商品名', '不明')
    price = row.get('セット価格', 0)
    status_text = row.get('status_text', 'ステータス不明')
    
    # 在庫数
    try: body_count = int(row.get('本体', 0))
    except: body_count = 0
    try: sheath_count = int(row.get('鞘', 0))
    except: sheath_count = 0
    
    # 鞘がある商品かどうか (inventory.py で判定済み)
    has_sheath = row.get('has_sheath', False)

    # 値取得用ヘルパー
    def get_val(key, default=0):
        val = row.get(key, default)
        return val if pd.notna(val) else default

    import pandas as pd # pandas use

    with st.container():
        st.markdown(f"### {product_name}")
        st.write(f"**価格:** ¥{price:,.0f}")
        
        # 表面に在庫数を表示
        if has_sheath:
            st.caption(f"在庫: 本体 {body_count} / 鞘 {sheath_count}")
        else:
            st.caption(f"在庫: {body_count}")
        
        if "在庫あり" in status_text:
            st.success(status_text)
        elif "製作中" in status_text:
            st.warning(status_text)
        else:
            st.error(status_text)
            
        with st.expander("詳細在庫・進捗情報"):
            if has_sheath:
                col_b, col_s = st.columns(2)
                with col_b:
                    st.write(f"#### 本体 (在庫: {body_count})")
                    render_progress_view("NC粗削り", get_val('本体_粗削り_実績'), get_val('本体NC粗削時間'))
                    render_progress_view("NC仕上げ", get_val('本体_仕上げ_実績'), get_val('本体NC仕上時間'))
                with col_s:
                    st.write(f"#### 鞘 (在庫: {sheath_count})")
                    render_progress_view("NC粗削り", get_val('鞘_粗削り_実績'), get_val('鞘NC粗削時間'))
                    render_progress_view("NC仕上げ", get_val('鞘_仕上げ_実績'), get_val('鞘NC仕上時間'))
            else:
                # 本体のみ表示
                st.write(f"#### 本体 (在庫: {body_count})")
                render_progress_view("NC粗削り", get_val('本体_粗削り_実績'), get_val('本体NC粗削時間'))
                render_progress_view("NC仕上げ", get_val('本体_仕上げ_実績'), get_val('本体NC仕上時間'))
        
        st.markdown("---")
