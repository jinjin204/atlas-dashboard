import json
import os
from googleapiclient.http import MediaFileUpload
from logic.drive_utils import authenticate, download_content

def fix_drive():
    service = authenticate()
    
    id_target = "1LTM58WGFT27DpEZ_1TPBeQiJcSr6-uRT"
    id_trash  = "1UoijBb_Th06bHrOBR9HN18CO2mGnLAig"
    
    print("1. Deleting the duplicated file...")
    try:
        service.files().delete(fileId=id_trash).execute()
        print(f"Deleted duplicate file: {id_trash}")
    except Exception as e:
        print(f"Could not delete duplicate (maybe already deleted): {e}")

    local_path = os.path.abspath('data/history_summary.json')
    print(f"2. Updating the target file ({id_target}) with {local_path}...")
    try:
        media = MediaFileUpload(local_path, mimetype='application/json', resumable=True)
        service.files().update(
            fileId=id_target,
            media_body=media
        ).execute()
        print("Update executed.")
    except Exception as e:
        print(f"Update failed: {e}")

    print("3. Verifying the content...")
    try:
        f1 = download_content(service, id_target, "application/json")
        data1 = json.loads(f1.read().decode('utf-8'))
        print(f"Target file on Drive now contains {len(data1)} entries.")
    except Exception as e:
        print("Verification failed:", e)

if __name__ == '__main__':
    fix_drive()
