
import pandas as pd
import json
import os
import sys
import io

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logic import master_loader

def create_mock_data():
    # 1. Product Master DataFrame
    master_data = {
        'ID': ['DP-001', 'ITEM-002'],
        'カテゴリ': ['Plate', 'Weapon'],
        '商品名': ['Dragon Plate', 'Excalibur'],
        '部位': ['Body', 'Blade'],
        '単価1': [1000, 5000],
        '在庫数': [10, 5],
        '取数': [1, 1],
        '材料種別': ['Iron', 'Steel'],
        'NCマシン': ['Both', 'Both'],
        '生地_固定': [10, 20],
        '生地_単体': [5, 10],
        '生地乾燥h': [1, 2],
        'NC表_粗分': [30, 60],
        'NC表_仕分': [15, 30],
        'NC裏_粗分': [30, 60],
        'NC裏_仕分': [15, 30],
        '切離分': [5, 5],
        '組付接着分': [10, 10],
        '組付乾燥h': [0.5, 0.5],
        '嵌合調整分': [5, 5],
        '機械加工分': [10, 10],
        '研磨手加分': [20, 20],
        '組立玉入分': [5, 5]
    }
    master_df = pd.DataFrame(master_data)

    # 2. Excel Bytes (Event Master & Event Sheet)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # Event Master
        event_master_data = {
            'フラグ': ['TRUE', 'FALSE'],
            '種別': ['Event', 'Event'],
            'イベント名': ['Test Event 1', 'Test Event 2'],
            '対象シート': ['EventSheet1', 'EventSheet2']
        }
        pd.DataFrame(event_master_data).to_excel(writer, sheet_name='イベントマスタ', index=False)
        
        # Event Sheet 1 (Active)
        # ID is usually in col A or B. master_loader searches for "ID" header row.
        # Targets are in F (index 5) and G (index 6).
        # Let's create a DataFrame that aligns with this.
        # Row 0: Header with "ID"
        # Row 1+: Data
        
        # Create a dataframe with enough columns to place Target at F(5) and Current at G(6)
        # Columns: A, B, C, D, E, F, G
        # Indexes: 0, 1, 2, 3, 4, 5, 6
        
        data = [
            ['DP-001', '', '', '', '', 2, 0],  # Target=2, Current=0
            ['ITEM-002', '', '', '', '', 5, 1] # Target=5, Current=1
        ]
        columns = ['ID', 'ColB', 'ColC', 'ColD', 'ColE', 'Target', 'Current']
        event_df = pd.DataFrame(data, columns=columns)
        event_df.to_excel(writer, sheet_name='EventSheet1', index=False)
        
    buffer.seek(0)
    return master_df, buffer.read()

def test_phase3_logic():
    print("--- Starting Phase 3 Logic Test ---")
    master_df, excel_bytes = create_mock_data()
    
    # Clean up previous JSON
    json_path = master_loader.JSON_PATH
    if os.path.exists(json_path):
        os.remove(json_path)
    
    # 1. Convert DataFrame to JSON (With Event Merge)
    print("1. Converting DataFrame to JSON with Excel Bytes...")
    # NOTE: merge_event_targets is now called INSIDE convert_dataframe_to_json
    master_list = master_loader.convert_dataframe_to_json(master_df, force=True, excel_bytes=excel_bytes)
    
    # Verify initial JSON in memory
    dp_updated = next((item for item in master_list if item['id'] == 'DP-001'), None)
    if dp_updated and dp_updated.get('target_quantity') == 2:
        print("PASS: Master list has target quantity 2 for Dragon Plate.")
    else:
        print(f"FAIL: Master list has target quantity {dp_updated.get('target_quantity') if dp_updated else 'None'}.")

    # Verify JSON on disk
    if not os.path.exists(json_path):
        print("FAIL: production_master.json not created.")
        return
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data_disk = json.load(f)
        dp_disk = next((item for item in data_disk if item['id'] == 'DP-001'), None)
        if dp_disk and dp_disk.get('target_quantity') == 2:
            print("PASS: JSON on disk has target quantity 2.")
        else:
            print(f"FAIL: JSON on disk has target quantity {dp_disk.get('target_quantity', 0) if dp_disk else 'None'} (Expected 2).")

    # 2. (Skipped manual merge step as it is integrated)
    print("2. (Skipped manual merge step)")

if __name__ == "__main__":
    test_phase3_logic()
