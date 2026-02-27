def get_part_type(path: str) -> str:
    """
    パスから部位（本体または鞘）を判定する。
    """
    if not path:
        return "本体"
    lower_path = path.lower()
    if "saya" in lower_path or "鞘" in lower_path:
        return "鞘"
    return "本体"

def get_process_type(path: str) -> str:
    """
    パスから工程（粗削り/仕上げ）を判定する。
    """
    if not path:
        return "不明"
    
    lower_path = path.lower()
    
    # 判定ロジック (英単語または日本語)
    # 粗削り: rough, 荒, ara
    # 仕上げ: finish, shiage, fin
    
    if "rough" in lower_path or "荒" in lower_path or "ara" in lower_path:
        return "粗削り"
    
    if "finish" in lower_path or "仕" in lower_path or "fin" in lower_path:
        return "仕上げ"
        
    return "不明"
