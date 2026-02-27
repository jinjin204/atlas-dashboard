
import unittest
import pandas as pd
import sys
import os
from datetime import datetime, timedelta

# プロジェクトルートをパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logic.production_logic import calculate_production_events, determine_side

class TestProductionLogic(unittest.TestCase):
    
    def test_side_determination(self):
        self.assertEqual(determine_side("Face_Op1"), "表")
        self.assertEqual(determine_side("Back_Op2"), "裏")
        self.assertEqual(determine_side("Other"), "不明")
        self.assertEqual(determine_side("test_base.nc"), "裏")

    def test_production_events_pair(self):
        # 現在の日付を使用して 90 日フィルタリングを回避
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = {
            'TIMESTAMP': [now, now],
            'PROJECT': ['ItemA', 'ItemA'],
            'PART': ['', ''],
            'PATH': ['ItemA_Face.nc', 'ItemA_Back.nc']
        }
        df = pd.DataFrame(data)
        events = calculate_production_events(df)
        
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['extendedProps']['project'], 'ItemA')
        self.assertEqual(events[0]['extendedProps']['confidence'], 'high')

    def test_production_events_single(self):
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = {
            'TIMESTAMP': [now],
            'PROJECT': ['ItemB'],
            'PART': ['Part1'],
            'PATH': ['ItemB_Part1_Face.nc']
        }
        df = pd.DataFrame(data)
        events = calculate_production_events(df)
        
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['title'], 'ItemB (Part1)')
        self.assertEqual(events[0]['extendedProps']['confidence'], 'low')

    def test_production_events_filtering(self):
        # 100日前（フィルタリングされるはず）と今日
        old_date = (datetime.now() - timedelta(days=100)).strftime('%Y-%m-%d %H:%M:%S')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = {
            'TIMESTAMP': [old_date, now],
            'PROJECT': ['OldItem', 'NewItem'],
            'PART': ['', ''],
            'PATH': ['Old.nc', 'New.nc']
        }
        df = pd.DataFrame(data)
        events = calculate_production_events(df)
        
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['extendedProps']['project'], 'NewItem')

if __name__ == '__main__':
    unittest.main()
