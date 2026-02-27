graph TD
    subgraph "Phase 1: Raw Data (Cloud)"
        A[Google Drive: メニュー.xlsx]
    end

    subgraph "Phase 2: Sync (Memory Stream)"
        B[drive_utils.py] -->|Fetch All| C{Memory DataFrames}
        C -.-> C1[シート: 商品マスタ]
        C -.-> C2[シート: イベントマスタ]
        C -.-> C3[シート: 個別イベント案]
    end

    subgraph "Phase 3: Transformation (Master Loader)"
        C2 -->|1. アクティブフラグ=True を探索| F[対象シート名の特定]
        F -->|2. シート名を指定| E[例: クリマ2605]
        C1 -->|3. IDで結合| G((JOIN))
        E -->|3. IDで結合| G
        G -->|4. 目標数・在庫を注入| H[json: production_master.json]
    end

    subgraph "Phase 4: AI Command (Zeus)"
        H --> I[zeus_chat.py: InitialStockAnalyzer]
        J[json: history_summary.json] --> I
        I -->|5. 戦況報告作成| K[Zeus Prompt]
        K -->|6. API Request| L[Gemini API]
    end

    style G fill:#f9f,stroke:#333,stroke-width:3px
    style C2 fill:#fff4dd,stroke:#d4a017
    style E fill:#fff4dd,stroke:#d4a017