# Task List

- [x] 設計 (Planning)
    - [x] 現状のプロンプト欠落原因の特定（ユーザー指摘）
    - [x] 修正方針の策定（検索方向の反転、工数計算の修正、在庫リストへの追記）
- [ ] 実装 (Execution)
    - [ ] `zeus_chat.py`: `search_products_by_query`
        - `if query in name` (部分一致) のロジックを追加。
        - 正規化（スペース除去）を徹底。
    - [ ] `zeus_chat.py`: `build_system_prompt`
        - `total_nc_min`, `total_manual_min` の集計ロジックを再確認・修正。
        - `inventory_context` 生成ループ内で、各商品の `process` データから工数を計算し、文字列に追加。
- [ ] 検証 (Verification)
    - [ ] `tests/test_zeus_prompt_fix.py` 作成と実行
        - 検索が「伝説剣」で「伝説剣　長」をヒットさせるか。
        - プロンプト内に `NC: ...` が含まれているか。
