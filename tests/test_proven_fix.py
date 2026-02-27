import pandas as pd
import sys
import os
import traceback

# Add parent directory to path to import logic
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from logic.inventory import calculate_inventory
except ImportError:
    print("Error: Could not import logic.inventory")
    sys.exit(1)

def test_proven_fix():
    print("=== Testing Proven Fix for Duplicate Labels ===")

    # Case 1: Master data with duplicate index
    # Creating a dataframe where index is not unique
    print("Scenario 1: Master DataFrame with duplicate indices...")
    df_dup_index = pd.DataFrame({
        '商品名': ['Item A', 'Item B', 'Item C'],
        '単価': [1000, 2000, 3000]
    })
    # Force duplicate index
    df_dup_index.index = [0, 0, 1] 
    
    # Check if our logic fixes this via reset_index
    log_df = pd.DataFrame({'path': ['Item A.nc']})

    try:
        result = calculate_inventory(df_dup_index, log_df)
        print("Scenario 1 PASS: Handled duplicate index without error.")
        if not result.index.is_unique:
             print("WARNING: Result index is not unique.")
        else:
             print("PASS: Result index is unique.")
    except Exception as e:
        print(f"Scenario 1 FAIL: {e}")
        traceback.print_exc()

    # Case 2: Master data with duplicate columns AND rows
    print("\nScenario 2: Master DataFrame with duplicate columns and rows...")
    # This creates a DF with two '商品名' columns
    df_dup_cols = pd.DataFrame([
        ['Item A', 'Item A', 1000],
        ['Item A', 'Item A', 1000], # Duplicate row
        ['Item B', 'Item B', 2000]
    ], columns=['商品名', '商品名', '単価'])
    
    try:
        result = calculate_inventory(df_dup_cols, log_df)
        print("Scenario 2 PASS: Handled duplicate columns and rows.")
        # Verify deduplication happened
        if len(result) == 2: # Item A and Item B
             print("PASS: Row count is correct (2).")
        else:
             print(f"FAIL: Row count is {len(result)} (Expected 2).")
    except Exception as e:
        print(f"Scenario 2 FAIL: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_proven_fix()
