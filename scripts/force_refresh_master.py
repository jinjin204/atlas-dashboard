
import sys
import os
import pandas as pd
from unittest.mock import MagicMock

# Mock streamlit to allow drive_utils to run without streamlit server
# access to st.empty(), st.error(), etc. will be ignored or printed
mock_st = MagicMock()
mock_st.empty.return_value = MagicMock()
# Mock cache_data as a pass-through decorator
def mock_cache_data(*args, **kwargs):
    def decorator(func):
        return func
    return decorator
mock_st.cache_data = mock_cache_data

sys.modules["streamlit"] = mock_st

# Add path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logic import drive_utils
from logic import master_loader

def main():
    print("--- 1. Authenticating & Fetching from Drive ---")
    try:
        # load_data_from_drive returns: master_df, log_df, event_sheet_names, excel_bytes
        # BUT if it fails early, it might return (None, None) or similar.
        result = drive_utils.load_data_from_drive()
        
        if result is None:
             print("ERROR: load_data_from_drive returned None")
             return
             
        if len(result) == 2:
            master_df, log_df = result
            sheet_names = []
            excel_bytes = None
            print("WARNING: drive_utils returned only 2 values. Event merging might be skipped.")
        elif len(result) == 4:
            master_df, log_df, sheet_names, excel_bytes = result
        else:
             print(f"ERROR: Unexpected return length: {len(result)}")
             return

    except Exception as e:
        print(f"CRITICAL ERROR during Drive fetch: {e}")
        import traceback
        traceback.print_exc()
        return

    if master_df is None:
        print("ERROR: Failed to fetch master_df (None returned). Check credentials or Drive connection.")
        return

    print(f"--- 2. Converting & Merging (Rows: {len(master_df)}) ---")
    
    # Check if excel_bytes is valid
    if excel_bytes:
        print(f"Excel Bytes Size: {len(excel_bytes)} bytes")
    else:
        print("WARNING: SQL bytes are None. Event merging will be skipped.")

    # This function now saves to JSON automatically and merges events if bytes provided
    master_loader.convert_dataframe_to_json(master_df, force=True, excel_bytes=excel_bytes)
    
    # Load and verify
    print("--- 3. Verifying Output ---")
    json_path = master_loader.JSON_PATH
    if os.path.exists(json_path):
        import json
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"Total Items in JSON: {len(data)}")
            if data:
                print("First 3 items:")
                for item in data[:3]:
                    print(f"- ID: {item.get('id')}, Name: {item.get('name')}, Target: {item.get('target_quantity')}")
                
                # Check for fabricated data remnants
                fake = next((i for i in data if 'Excalibur' in i.get('name', '') or 'Dragon Plate' in i.get('name', '')), None)
                if fake:
                    print(f"❌ WARNING: Fabricated data found! {fake['name']}")
                else:
                    print("✅ No fabricated sample data found.")
    else:
        print("❌ Error: production_master.json was NOT created.")

if __name__ == "__main__":
    main()
