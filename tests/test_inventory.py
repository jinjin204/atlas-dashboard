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

def test_duplicates_and_types():
    print("Testing with dirty data (duplicates, bad types)...")

    # Mock Master Data with duplicates and various column names
    master_data = {
        '品名': ['Item A', 'Item A', 'Item B', 'Item C'], # Duplicate Item A
        '本体単価': [1000, 1200, 2000, 3000],          # Different prices for duplicate
        '鞘単価': [500, 500, 1000, 1500]
    }
    master_df = pd.DataFrame(master_data)

    # Mock Log Data
    log_data = {
        'path': [
            'Project/Item A/part.nc', 
            'Project/Item A/part.nc', # Duplicate log
            'Project/Item B/part.nc'
        ],
        'Time': ['100', '200', 'nan'] # Mixed types, strings
    }
    log_df = pd.DataFrame(log_data)

    try:
        result_df = calculate_inventory(master_df, log_df)
        print("Calculation successful!")
        
        # Validation
        print("Columns:", result_df.columns.tolist())
        print(result_df[['商品名', 'セット在庫', 'セット価格', 'status_text']])
        
        # Check deduplication
        if len(result_df) == 3: # Item A (deduped), Item B, Item C
            print("Row count correct (deduplicated).")
        else:
            print(f"Row count unexpected: {len(result_df)} (Expected 3)")

        # Check normalize_text with Series
        try:
            print("Testing normalize_text with Series...")
            series_input = pd.Series(["  Test  "])
            norm = normalize_text(series_input)
            print(f"normalize_text(Series) result: '{norm}'")
            if norm != "test":
                print("FAILED: normalize_text did not handle Series correctly.")
        except Exception as e:
            print(f"FAILED: normalize_text raised exception with Series: {e}")

    except Exception as e:
        print(f"FAILED: calculate_inventory raised exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_duplicates_and_types()
