"""
test_master_loader.py - master_loader モジュールの単体テスト

テスト用CSVを動的に生成し、convert_csv_to_json の変換ロジックを検証する。
"""

import pytest
import os
import json
import tempfile
import pandas as pd
from unittest.mock import patch

# テスト対象モジュールのインポート前にパスを設定
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from logic.master_loader import convert_csv_to_json, load_master_json, get_val, get_str, find_latest_csv


# --- テスト用CSVデータ ---
SAMPLE_CSV_DATA = {
    'ID': ['P001', 'P002', None],
    'カテゴリ': ['万年筆', 'ボールペン', ''],
    '商品名': ['テスト商品A', 'テスト商品B', '合計'],
    '部位': ['本体', '本体', ''],
    '単価1': [50000, 30000, None],
    '在庫数': [5, 3, None],
    '取数': [1, 2, None],
    '材料種別': ['エボナイト', 'アクリル', ''],
    'NCマシン': ['Both', 'CNC-A', ''],
    '生地_固定': [10, 5, None],
    '生地_単体': [15, 8, None],
    '生地乾燥h': [24, 12, None],
    'NC表_粗分': [30, 20, None],
    'NC表_仕分': [45, 25, None],
    'NC裏_粗分': [25, 15, None],
    'NC裏_仕分': [40, 22, None],
    '切離分': [5, 3, None],
    '組付接着分': [10, 7, None],
    '組付乾燥h': [8, 4, None],
    '嵌合調整分': [20, 12, None],
    '機械加工分': [15, 10, None],
    '研磨手加分': [30, 18, None],
    '組立玉入分': [25, 15, None],
}


@pytest.fixture
def temp_data_dir(tmp_path):
    """テスト用の一時データディレクトリを作成"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def sample_csv(temp_data_dir):
    """テスト用CSVファイルを生成"""
    csv_path = temp_data_dir / "メニュー.xlsx - 商品マスタ.csv"
    df = pd.DataFrame(SAMPLE_CSV_DATA)
    df.to_csv(csv_path, index=False, encoding='utf-8')
    return str(csv_path)


class TestGetVal:
    def test_normal_value(self):
        row = pd.Series({'col': 42})
        assert get_val(row, 'col') == 42

    def test_nan_value(self):
        row = pd.Series({'col': float('nan')})
        assert get_val(row, 'col') == 0

    def test_empty_string(self):
        row = pd.Series({'col': ''})
        assert get_val(row, 'col') == 0

    def test_custom_default(self):
        row = pd.Series({'col': float('nan')})
        assert get_val(row, 'col', default=1) == 1

    def test_missing_column(self):
        row = pd.Series({'other': 42})
        assert get_val(row, 'col') == 0


class TestGetStr:
    def test_normal_value(self):
        row = pd.Series({'col': 'hello'})
        assert get_str(row, 'col') == 'hello'

    def test_numeric_to_string(self):
        row = pd.Series({'col': 123})
        assert get_str(row, 'col') == '123'

    def test_nan_value(self):
        row = pd.Series({'col': float('nan')})
        assert get_str(row, 'col') == ''

    def test_custom_default(self):
        row = pd.Series({'col': float('nan')})
        assert get_str(row, 'col', default='N/A') == 'N/A'


class TestConvertCsvToJson:
    def test_successful_conversion(self, sample_csv, temp_data_dir):
        json_path = str(temp_data_dir / "production_master.json")

        with patch('logic.master_loader.CSV_PATH', sample_csv), \
             patch('logic.master_loader.JSON_PATH', json_path):
            result = convert_csv_to_json(force=True)

        # ID=None の行はスキップされるので2件
        assert len(result) == 2
        assert result[0]['id'] == 'P001'
        assert result[0]['name'] == 'テスト商品A'
        assert result[0]['price'] == 50000
        assert result[0]['process']['nc']['front_rough_min'] == 30.0

        # JSONファイルが生成されていること
        assert os.path.exists(json_path)
        with open(json_path, 'r', encoding='utf-8') as f:
            saved = json.load(f)
        assert len(saved) == 2

    def test_skip_null_id_rows(self, sample_csv, temp_data_dir):
        json_path = str(temp_data_dir / "production_master.json")

        with patch('logic.master_loader.CSV_PATH', sample_csv), \
             patch('logic.master_loader.JSON_PATH', json_path):
            result = convert_csv_to_json(force=True)

        # 3行目(ID=None)はスキップされる
        ids = [item['id'] for item in result]
        assert 'P001' in ids
        assert 'P002' in ids
        assert len(ids) == 2

    def test_missing_csv_returns_empty(self, temp_data_dir):
        json_path = str(temp_data_dir / "production_master.json")

        with patch('logic.master_loader.CSV_PATH', '/nonexistent/path.csv'), \
             patch('logic.master_loader.JSON_PATH', json_path), \
             patch('logic.master_loader.DATA_DIR', str(temp_data_dir)):
            result = convert_csv_to_json(force=True)

        assert result == []

    def test_nan_handling(self, sample_csv, temp_data_dir):
        json_path = str(temp_data_dir / "production_master.json")

        with patch('logic.master_loader.CSV_PATH', sample_csv), \
             patch('logic.master_loader.JSON_PATH', json_path):
            result = convert_csv_to_json(force=True)

        item = result[0]
        # 数値フィールドの型チェック
        assert isinstance(item['price'], int)
        assert isinstance(item['current_stock'], int)
        assert isinstance(item['process']['prep']['setup_min'], float)

    def test_timestamp_skip(self, sample_csv, temp_data_dir):
        """JSONがCSVより新しい場合はスキップされること"""
        json_path = str(temp_data_dir / "production_master.json")

        # まず生成
        with patch('logic.master_loader.CSV_PATH', sample_csv), \
             patch('logic.master_loader.JSON_PATH', json_path):
            result1 = convert_csv_to_json(force=True)

        # force=Falseで再実行（スキップされるべき）
        with patch('logic.master_loader.CSV_PATH', sample_csv), \
             patch('logic.master_loader.JSON_PATH', json_path):
            result2 = convert_csv_to_json(force=False)

        assert len(result2) == len(result1)


class TestFindLatestCsv:
    def test_find_csv(self, temp_data_dir):
        # テスト用CSV作成
        csv1 = temp_data_dir / "test1.csv"
        csv1.write_text("a,b\n1,2", encoding='utf-8')

        result = find_latest_csv(str(temp_data_dir))
        assert result is not None
        assert result.endswith('.csv')

    def test_exclude_confirmed_log(self, temp_data_dir):
        # confirmed_log.csv は除外されること
        csv1 = temp_data_dir / "confirmed_log.csv"
        csv1.write_text("a,b\n1,2", encoding='utf-8')

        result = find_latest_csv(str(temp_data_dir))
        assert result is None

    def test_empty_directory(self, temp_data_dir):
        result = find_latest_csv(str(temp_data_dir))
        assert result is None


class TestLoadMasterJson:
    def test_load_existing(self, temp_data_dir):
        json_path = str(temp_data_dir / "production_master.json")
        test_data = [{"id": "P001", "name": "test"}]

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)

        with patch('logic.master_loader.JSON_PATH', json_path):
            result = load_master_json()

        assert len(result) == 1
        assert result[0]['id'] == 'P001'

    def test_load_nonexistent(self):
        with patch('logic.master_loader.JSON_PATH', '/nonexistent.json'):
            result = load_master_json()
        assert result == []


class TestConvertDataFrameToJson:
    def test_df_conversion(self, temp_data_dir):
        json_path = str(temp_data_dir / "production_master.json")
        df = pd.DataFrame(SAMPLE_CSV_DATA)

        with patch('logic.master_loader.JSON_PATH', json_path):
            from logic.master_loader import convert_dataframe_to_json
            result = convert_dataframe_to_json(df, force=True)

        assert len(result) == 2
        assert result[0]['id'] == 'P001'
        assert os.path.exists(json_path)

    def test_df_conversion_error(self, temp_data_dir):
        # JSON書き出しエラーのシミュレーション
        json_path = str(temp_data_dir / "dir/production_master.json") # ディレクトリ存在しない
        df = pd.DataFrame(SAMPLE_CSV_DATA)

        # makedirs を mock してエラーにするのは難しいので、書き込み権限などでエラーを起こすのが一般的だが
        # ここでは書き込みパスを無効なものにしてエラーを誘発
        with patch('logic.master_loader.JSON_PATH', json_path):
            with patch('os.makedirs', side_effect=OSError("Error")):
                from logic.master_loader import convert_dataframe_to_json
                result = convert_dataframe_to_json(df, force=True)

        # エラーでもメモリ上のリストは返る仕様
        assert len(result) == 2

