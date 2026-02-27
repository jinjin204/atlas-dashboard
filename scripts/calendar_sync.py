"""
Atlas Hub - Calendar Sync Runner
カレンダーエージェントのスタンドアロン実行用エントリーポイント。

使い方:
    python scripts/calendar_sync.py [--no-drive] [--no-local]
    
定期実行（Windows タスクスケジューラ）:
    毎日 06:00 に実行する場合:
    schtasks /create /tn "AtlasCalendarSync" /tr "python C:\\...\\scripts\\calendar_sync.py" /sc daily /st 06:00
"""

import sys
import os
import argparse

# プロジェクトルートをPATHに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from logic.calendar_agent import run


def main():
    parser = argparse.ArgumentParser(description='Atlas Calendar Sync - 空き時間抽出とDrive同期')
    parser.add_argument('--no-drive', action='store_true', help='Driveへのアップロードをスキップ')
    parser.add_argument('--no-local', action='store_true', help='ローカルファイル出力をスキップ')
    args = parser.parse_args()
    
    result = run(
        output_local=not args.no_local,
        output_drive=not args.no_drive,
    )
    
    if result:
        print("\n✅ Calendar Sync 完了")
        return 0
    else:
        print("\n❌ Calendar Sync 失敗")
        return 1


if __name__ == '__main__':
    sys.exit(main())
