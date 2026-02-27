
import json
from datetime import datetime, timedelta
import sys

# File path
HISTORY_FILE = r'c:\Users\yjing\.gemini\atlas-hub\data\history_summary.json'
TARGET_DATE = '2026-02-17'

def parse_timestamp(ts):
    if not ts:
        return None
    if isinstance(ts, str):
        try:
            if 'T' in ts:
                return datetime.fromisoformat(ts)
            else:
                return datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return None
    return None

def main():
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at {HISTORY_FILE}")
        return

    print(f"Loaded {len(data)} records.")

    valid_records = []
    # Sort data by timestamp just in case
    # Assume data is sorted or sort it
    
    # Pre-parse timestamps
    parsed_data = []
    for entry in data:
        ts = parse_timestamp(entry.get('timestamp') or entry.get('date'))
        if ts:
            parsed_data.append({'ts': ts, 'entry': entry})
            
    parsed_data.sort(key=lambda x: x['ts'])

    # Strict bounds for 2026-02-17
    # But user says "Yesterday's result" exists.
    # We will check increments between "Last record of 2/16" and "Last record of 2/17"
    # Or "Last record of 2/16" and "Early morning record of 2/18" (e.g. < 5AM) if strict 2/17 is missing.
    
    start_2_17 = datetime(2026, 2, 17, 0, 0, 0)
    end_2_17 = datetime(2026, 2, 17, 23, 59, 59)
    end_2_17_extended = datetime(2026, 2, 18, 5, 0, 0) # 5 AM extension rule

    prev_record = None
    target_record = None

    # Find the baseline: last record before 2/17 starts
    for item in parsed_data:
        if item['ts'] < start_2_17:
            # Check if this record has details
            if 'details' in item['entry']:
                prev_record = item

    # Find the target: last record of 2/17 (possibly extended to early 2/18)
    for item in parsed_data:
        if item['ts'] <= end_2_17_extended:
             if 'details' in item['entry']:
                target_record = item
    
    # If target_record is actually before 2/17 started, then no data for 2/17.
    if target_record and target_record['ts'] < start_2_17:
        print("Latest record is before 2/17. No new data.")
        target_record = None # Invalid for our purpose

    print("\n--- Analysis ---")
    if prev_record:
        print(f"Baseline (Prev Day): {prev_record['ts']}")
    else:
        print("Baseline: None (Using empty state)")

    if target_record:
        print(f"Target (Yesterday): {target_record['ts']}")
    else:
        print("Target: None found for 2/17 (even with 5AM extension)")
        
        # Fallback: Print what IS available around that time
        print("\n--- Surrounding Data Points ---")
        for item in parsed_data:
             if start_2_17 - timedelta(days=2) <= item['ts'] <= end_2_17 + timedelta(days=2):
                  has_details = 'details' in item['entry']
                  print(f"{item['ts']} - Has Details: {has_details}")
        return

    # Calculate Increments
    increments = {}
    
    prev_details = prev_record['entry'].get('details', {}) if prev_record else {}
    target_details = target_record['entry'].get('details', {})
    
    all_keys = set(prev_details.keys()) | set(target_details.keys())
    
    for key in all_keys:
        p_val = prev_details.get(key, {'count': 0})
        if isinstance(p_val, int): p_val = {'count': p_val} # Handle if structure is simpler
        
        t_val = target_details.get(key, {'count': 0})
        if isinstance(t_val, int): t_val = {'count': t_val}

        p_count = p_val.get('count', 0)
        t_count = t_val.get('count', 0)
        
        diff = t_count - p_count
        if diff > 0:
            increments[key] = diff

    print("\n--- Results ---")
    if not increments:
        print("No increments found (counts matches baseline).")
    else:
        for k, v in increments.items():
            print(f"ID: {k}, Increment: {v}")

if __name__ == "__main__":
    main()
