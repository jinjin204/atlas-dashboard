import pandas as pd
import sys
import os

# Add parent directory to path to import logic
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from logic.inventory import calculate_inventory, normalize_text
except ImportError:
    print("Error: Could not import logic.inventory")
    sys.exit(1)

def test_forced_deduplication():
    print("Testing forced deduplication logic...")

    # ユーザー指定の再現データ
    # 擬似データで重複とNoneを再現
    test_master_df = pd.DataFrame({
        '商品名': ['剣', '剣', None, '盾'], 
        '単価': [1000, 1200, 0, 500] # 重複時は最初(1000)が残るはず
    })
    
    # ログデータ（ダミー）
    test_log_df = pd.DataFrame({'path': ['剣.nc']})

    print(f"Input Master DF:\n{test_master_df}")

    try:
        # calculate_inventory 実行
        result_df = calculate_inventory(test_master_df, test_log_df)
        
        print("\nCalculation result:")
        print(result_df[['商品名', 'セット在庫', 'セット価格']])
        
        # 検証1: 行数が減っているか (4行 -> 2行: '剣'と'盾')
        # Noneは消え、'剣'は1つになるはず
        expected_count = 2
        if len(result_df) == expected_count:
            print(f"PASS: Row count is {len(result_df)} (Expected {expected_count})")
        else:
            print(f"FAIL: Row count is {len(result_df)} (Expected {expected_count})")
            # 詳細確認
            print(result_df)
            sys.exit(1)

        # 検証2: 重複エラーが出ないこと (ここに来ている時点でOKだが)
        print("PASS: No ValueError raised.")
        
    except Exception as e:
        print(f"FAIL: Exception raised: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_forced_deduplication()
