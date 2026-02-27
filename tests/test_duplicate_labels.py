import pandas as pd
import sys
import os

# Add parent directory to path to import logic
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from logic.inventory import calculate_inventory
except ImportError:
    print("Error: Could not import logic.inventory")
    sys.exit(1)

def test_duplicate_labels():
    print("Testing for 'duplicate labels' error...")

    # Scenario: Master Data has duplicate columns (e.g. two '商品名' columns or renaming causes collision)
    # And duplicate rows.
    master_data = {
        '商品名': ['Item A', 'Item A', 'Item B', float('nan')], 
        'Price': [1000, 1000, 2000, 0],
        'Category': ['A', 'A', 'B', 'C']
    }
    master_df = pd.DataFrame(master_data)
    
    # Force duplicate columns validation
    # Pandas dataframe with duplicate columns
    master_df_dup_col = pd.DataFrame([
        ['Item A', 100],
        ['Item B', 200]
    ], columns=['商品名', '商品名']) # Duplicate column names!
    
    print("Testing with duplicate columns in Master Data...")
    log_df = pd.DataFrame({'path': ['Item A.nc']})
    
    try:
        # This might fail with "duplicate labels" if not handled
        calculate_inventory(master_df_dup_col, log_df)
        print("PASS: Handled duplicate columns.")
    except Exception as e:
        print(f"FAIL: Duplicate columns caused error: {e}")

    print("Testing with duplicate rows in Master Data...")
    try:
        result = calculate_inventory(master_df, log_df)
        if len(result) > 0 and result['商品名'].duplicated().any():
             print("FAIL: Result has duplicates.")
        else:
             print("PASS: Handled duplicate rows.")
    except Exception as e:
        print(f"FAIL: Duplicate rows caused error: {e}")

if __name__ == "__main__":
    test_duplicate_labels()
