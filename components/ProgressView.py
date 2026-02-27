import streamlit as st

def render_progress_view(label, actual_time, standard_time):
    """
    進捗バーを表示するコンポーネント
    
    Args:
        label (str): ラベル（例: "本体 粗削り"）
        actual_time (float): 実績時間
        standard_time (float): 標準時間（目標）
    """
    if standard_time <= 0:
        return # 標準時間がなければ表示しない
        
    progress = actual_time / standard_time
    # 進捗が1.0を超えるとエラーになるのでキャップする（表示上）
    display_progress = min(progress, 1.0)
    percentage = int(progress * 100)
    
    st.write(f"**{label}**")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.progress(display_progress)
    with col2:
        st.caption(f"{int(actual_time)}分 / {int(standard_time)}分 ({percentage}%)")
        
    if percentage > 100:
        st.caption(f":warning: {percentage - 100}% 超過")
