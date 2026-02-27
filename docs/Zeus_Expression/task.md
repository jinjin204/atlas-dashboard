# タスクリスト: Zeusロジックとマスタローダーの更新

- [ ] **分析と計画**
    - [x] `atlas-hub/logic/master_loader.py` の現状ロジック確認
    - [x] `atlas-hub/logic/zeus_chat.py` の現状ロジック確認
    - [x] 実装計画書 (`implementation_plan.md`) の作成（日本語）

- [ ] **`master_loader.py` の修正**
    - [x] `イベントマスタ` シートへのアクセス（`イベントマスタ.csv` ではなくシートとして処理）
    - [x] `表示フラグ == True` の対象シートを動的に特定
    - [x] 対象シートのデータ抽出（F列：目標在庫、G列：在庫数）
    - [x] `history_summary.json` の存在チェックと初期化ロジック（type: "initial"）の実装

- [ ] **`zeus_chat.py` の修正**
    - [x] `history_summary.json` の読み込み
    - [x] 【残量】計算ロジック（目標総額 - 現在在庫総額）
    - [x] 【実力】計算ロジック（最新データと過去データとの差分から日次ペース算出）
    - [x] 【予言】ロジック（2026-05-05 までの達成可否判定）
    - [x] システムプロンプトの修正（現状・予測・次の一手、簡潔化、ユーザー名「yjing」固定）

- [ ] **検証**
    - [x] `master_loader.py` のシート特定とデータロードの検証
    - [x] `history_summary.json` 生成・更新の検証
    - [x] Zeusチャットの応答内容の検証
