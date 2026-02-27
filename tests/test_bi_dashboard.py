"""
test_bi_dashboard.py - BIダッシュボードロジックのユニットテスト
"""
import pytest
from datetime import datetime
import sys
import os

# テスト用にパスを追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.bi_dashboard import (
    calc_countdown,
    calc_sales_gap,
    calc_remaining_hours,
    calc_today_tasks,
    calc_material_alerts,
    calc_dev_slot,
)

# =========================================
# テストデータ
# =========================================

MOCK_EVENT_MASTER = [
    {
        "name": "テストイベント",
        "sheet": "テスト2605",
        "date": "2026-05-05 00:00:00",
        "venue": "テスト会場",
        "booth": "A-01",
        "is_active": True,
    },
    {
        "name": "未来イベント",
        "sheet": "未",
        "date": "2026-08-15 00:00:00",
        "venue": "別会場",
        "is_active": False,
    },
]

MOCK_MASTER_DATA = [
    {
        "id": "ITEM_A_BDY",
        "category": "剣",
        "name": "テスト剣",
        "part": "本体",
        "price": 5000,
        "current_stock": 3,
        "event_sheet_stock": 3,
        "target_quantity": 10,
        "remaining": 7,
        "requirements": {
            "yield": 2.0,
            "material_type": "SPF",
            "nc_machine_type": "Gigas",
        },
        "process": {
            "prep": {"setup_min": 20, "unit_min": 10, "drying_hr": 5},
            "nc": {
                "front_rough_min": 30,
                "front_finish_min": 25,
                "back_rough_min": 30,
                "back_finish_min": 25,
            },
            "assembly": {"cut_off_min": 5, "bonding_min": 0, "drying_hr": 0},
            "manual": {
                "fitting_min": 0,
                "machine_work_min": 30,
                "sanding_min": 30,
                "assembly_min": 10,
            },
        },
    },
    {
        "id": "ITEM_A_SCB",
        "category": "剣",
        "name": "テスト剣",
        "part": "鞘",
        "price": 0,  # 鞘はprice=0
        "current_stock": 3,
        "event_sheet_stock": 3,
        "target_quantity": 10,
        "remaining": 7,
        "requirements": {
            "yield": 1.0,
            "material_type": "マツ",
            "nc_machine_type": "Gigas",
        },
        "process": {
            "prep": {"setup_min": 20, "unit_min": 10, "drying_hr": 5},
            "nc": {
                "front_rough_min": 20,
                "front_finish_min": 15,
                "back_rough_min": 20,
                "back_finish_min": 15,
            },
            "assembly": {"cut_off_min": 5, "bonding_min": 10, "drying_hr": 5},
            "manual": {
                "fitting_min": 10,
                "machine_work_min": 20,
                "sanding_min": 20,
                "assembly_min": 0,
            },
        },
    },
    {
        "id": "ITEM_B_BDY",
        "category": "盾",
        "name": "テスト盾",
        "part": "本体",
        "price": 8000,
        "current_stock": 5,
        "event_sheet_stock": 5,
        "target_quantity": 5,
        "remaining": 0,  # 完了品
        "requirements": {
            "yield": 1.0,
            "material_type": "ヒノキ",
            "nc_machine_type": "Gigas",
        },
        "process": {
            "prep": {"setup_min": 20, "unit_min": 10, "drying_hr": 5},
            "nc": {
                "front_rough_min": 40,
                "front_finish_min": 50,
                "back_rough_min": 40,
                "back_finish_min": 50,
            },
            "assembly": {"cut_off_min": 5, "bonding_min": 0, "drying_hr": 0},
            "manual": {
                "fitting_min": 0,
                "machine_work_min": 30,
                "sanding_min": 30,
                "assembly_min": 10,
            },
        },
    },
]


# =========================================
# KPI 1: イベントカウントダウン
# =========================================

class TestCalcCountdown:
    def test_basic(self):
        now = datetime(2026, 2, 23, 21, 0)
        result = calc_countdown(now=now, event_master=MOCK_EVENT_MASTER)
        assert result is not None
        assert result['event_name'] == "テストイベント"
        assert result['days_remaining'] == (datetime(2026, 5, 5) - now).days

    def test_no_active_event(self):
        inactive = [{"name": "X", "date": "2026-01-01", "is_active": False}]
        result = calc_countdown(event_master=inactive)
        assert result is None

    def test_past_event(self):
        now = datetime(2026, 6, 1)
        result = calc_countdown(now=now, event_master=MOCK_EVENT_MASTER)
        assert result['days_remaining'] == 0


# =========================================
# KPI 2: 売上ギャップ
# =========================================

class TestCalcSalesGap:
    def test_basic(self):
        result = calc_sales_gap(MOCK_MASTER_DATA)
        # ITEM_A_BDY: target=10 × 5000 = 50000, current=3 × 5000 = 15000
        # ITEM_A_SCB: price=0 → 除外
        # ITEM_B_BDY: target=5 × 8000 = 40000, current=5 × 8000 = 40000
        assert result['target_revenue'] == 50000 + 40000  # 90000
        assert result['current_revenue'] == 15000 + 40000  # 55000
        assert result['gap'] == 35000
        assert 0 < result['progress_ratio'] < 1

    def test_empty_data(self):
        result = calc_sales_gap([])
        assert result['target_revenue'] == 0
        assert result['progress_ratio'] == 0.0


# =========================================
# KPI 3: 残り加工時間
# =========================================

class TestCalcRemainingHours:
    def test_basic(self):
        result = calc_remaining_hours(MOCK_MASTER_DATA)
        # ITEM_A_BDY: remaining=7, NC=110, Manual=85 → NC=770, Manual=595
        # ITEM_A_SCB: remaining=7, NC=70, Manual=75 → NC=490, Manual=525
        # ITEM_B_BDY: remaining=0 → 除外
        assert result['total_nc_hours'] > 0
        assert result['total_manual_hours'] > 0
        assert result['total_hours'] == result['total_nc_hours'] + result['total_manual_hours']

    def test_efficiency_ranking_excludes_zero_remaining(self):
        result = calc_remaining_hours(MOCK_MASTER_DATA)
        ids_in_ranking = [i['id'] for i in result['efficiency_ranking']]
        assert "ITEM_B_BDY" not in ids_in_ranking


# =========================================
# KPI 4: 本日タスク
# =========================================

class TestCalcTodayTasks:
    def test_daytime(self):
        result = calc_today_tasks(MOCK_MASTER_DATA, current_hour=14)
        assert result['nc_available'] is True
        assert result['is_night_mode'] is False
        assert result['recommended_nc'] is not None

    def test_nighttime(self):
        result = calc_today_tasks(MOCK_MASTER_DATA, current_hour=21)
        assert result['nc_available'] is False
        assert result['is_night_mode'] is True
        assert result['recommended_nc'] is None
        assert result['recommended_manual'] is not None

    def test_all_done(self):
        done_data = [dict(d, remaining=0) for d in MOCK_MASTER_DATA]
        result = calc_today_tasks(done_data, current_hour=14)
        assert result['all_done'] is True


# =========================================
# KPI 5: 材料アラート
# =========================================

class TestCalcMaterialAlerts:
    def test_basic(self):
        result = calc_material_alerts(MOCK_MASTER_DATA, days_remaining=60)
        assert "SPF" in result['materials']
        assert "マツ" in result['materials']

    def test_spf_boards(self):
        result = calc_material_alerts(MOCK_MASTER_DATA, days_remaining=60)
        # ITEM_A_BDY: remaining=7, yield=2 → 7/2 = 3.5 → 4枚
        spf = result['materials']['SPF']
        assert spf['boards_needed'] == 4
        assert spf['remaining_count'] == 7

    def test_matsu_boards(self):
        result = calc_material_alerts(MOCK_MASTER_DATA, days_remaining=60)
        # ITEM_A_SCB: remaining=7, yield=1 → 7枚 → alert
        matsu = result['materials']['マツ']
        assert matsu['boards_needed'] == 7
        assert matsu['alert'] is True


# =========================================
# KPI 6: 新作開発枠
# =========================================

class TestCalcDevSlot:
    def test_ok(self):
        # progress >= 50% and days >= 30
        high_progress_data = [
            dict(MOCK_MASTER_DATA[0], target_quantity=10, event_sheet_stock=6),  # 60%
            dict(MOCK_MASTER_DATA[2], target_quantity=5, event_sheet_stock=5),   # 100%
        ]
        now = datetime(2026, 2, 23)
        result = calc_dev_slot(high_progress_data, event_master=MOCK_EVENT_MASTER, now=now)
        assert result['is_ok'] is True

    def test_ng_low_progress(self):
        low_progress_data = [
            dict(MOCK_MASTER_DATA[0], target_quantity=10, event_sheet_stock=1),  # 10%
        ]
        now = datetime(2026, 2, 23)
        result = calc_dev_slot(low_progress_data, event_master=MOCK_EVENT_MASTER, now=now)
        assert result['is_ok'] is False
