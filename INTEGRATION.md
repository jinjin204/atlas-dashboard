flowchart TD
    A[app.py] -->|1. Sync| B[drive_utils.py]
    B -->|2. Excel_Data| C[master_loader.py]
    C -->|3. Merge| D[production_master.json]
    D -->|4. AI_Read| E[Zeus]

    style C fill:#f96,stroke:#333,stroke-width:4px