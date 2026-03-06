import json
from logic.drive_utils import authenticate

def check():
    s = authenticate()
    res = s.files().list(
        q="name='history_summary.json' and trashed=false",
        fields="files(id, name, modifiedTime, parents, owners(displayName, emailAddress))"
    ).execute()
    
    print(json.dumps(res.get('files'), indent=2, ensure_ascii=False))

if __name__ == '__main__':
    check()
