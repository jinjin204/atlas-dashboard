import json
from logic.drive_utils import authenticate, download_content

def download_and_print():
    s = authenticate()
    
    id1 = "1LTM58WGFT27DpEZ_1TPBeQiJcSr6-uRT"
    id2 = "1UoijBb_Th06bHrOBR9HN18CO2mGnLAig"
    
    print("=== File 1 (1LTM...) ===")
    try:
        f1 = download_content(s, id1, "application/json")
        data1 = json.loads(f1.read().decode('utf-8'))
        print(f"File 1 contains {len(data1)} entries.")
        if data1:
            print("First entry date:", data1[0].get('date', 'N/A'))
            print("Last entry date:", data1[-1].get('date', 'N/A'))
    except Exception as e:
        print("Failed to read File 1:", e)
        
    print("\n=== File 2 (1Uoi...) ===")
    try:
        f2 = download_content(s, id2, "application/json")
        data2 = json.loads(f2.read().decode('utf-8'))
        print(f"File 2 contains {len(data2)} entries.")
        if data2:
            print("First entry date:", data2[0].get('date', 'N/A'))
            print("Last entry date:", data2[-1].get('date', 'N/A'))
    except Exception as e:
        print("Failed to read File 2:", e)

if __name__ == '__main__':
    download_and_print()
