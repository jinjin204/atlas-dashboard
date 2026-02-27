# Atlas-Hub 実装計画

## 目標
Streamlitを使用して、製品カタログと在庫状況を可視化する「atlas-hub」を作成します。
パスから製品タイプ（本体/鞘）を解析し、「セット在庫」（本体と鞘の最小値）を計算し、在庫がゼロでも生産中の場合にステータスを表示するカタログを作成します。

## ユーザー確認事項
> [!IMPORTANT]
> **データファイルの配置について**
> `data/` フォルダではなく、プロジェクトのルート（`atlas-hub/` 直下）に以下のファイルを配置してください。
> - `メニュー.xlsx - 商品マスタ.csv`
> - `アトラス - シート1.csv`
>
> アプリケーションはこれらのファイルが存在することを前提に動作します。

## 変更内容

### プロジェクト構成
- `atlas-hub/`
    - `app.py`: メインアプリケーション (Streamlit)。
    - `logic/`
        - `parser.py`: パス解析ロジック。
        - `inventory.py`: 在庫計算ロジック。
        - `cost.py`: 原価計算用スタブ。
    - `components/`
        - `CatalogCard.py`: 商品表示用コンポーネント。
        - `ProgressView.py`: 進捗表示用コンポーネント。

### ロジック
#### [NEW] [parser.py](file:///c:/Users/yjing/.gemini/atlas-hub/logic/parser.py)
- 関数 `get_part_type(path)`:
    - パスに "saya" または "鞘" が含まれる場合、"鞘" を返します。
    - それ以外の場合、"本体" を返します。

#### [NEW] [inventory.py](file:///c:/Users/yjing/.gemini/atlas-hub/logic/inventory.py)
- 関数 `calculate_inventory(master_df, log_df)`:
    - ログを商品と部位でグループ化します。
    - マスタデータと結合します。
    - `セット在庫 = min(本体在庫, 鞘在庫)` を計算します。
    - 「製作中」の数を集計します。

### UI
#### [NEW] [app.py](file:///c:/Users/yjing/.gemini/atlas-hub/app.py)
- データを読み込みます (`./メニュー.xlsx - 商品マスタ.csv`, `./アトラス - シート1.csv`)。
- ユニークな商品ごとにループします。
- `CatalogCard` を使用して各商品を描画します。

#### [NEW] [CatalogCard.py](file:///c:/Users/yjing/.gemini/atlas-hub/components/CatalogCard.py)
- 商品名、セット価格（本体＋鞘）、在庫を表示します。
- 在庫が0でもログがあれば「製作中：〇個（本体〇、鞘〇）」と表示します。

## 検証計画
### 自動テスト
- テストスクリプト `tests/test_logic.py` を作成し、`parser` と `inventory` のロジックを検証します。
- `python tests/test_logic.py` を実行します。

### 手動検証
- `streamlit run atlas-hub/app.py` を実行します。
- カタログ表示を確認します：
    - セット価格が正しいか。
    - 在庫0でもログがある場合に「製作中」と表示されるか。
    - 本体と鞘の区別が正しいか。
