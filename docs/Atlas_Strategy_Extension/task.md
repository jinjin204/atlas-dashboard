# アトラス戦略機能拡張 - タスクリスト

- [x] **設計・分析**
    - [x] `master_loader.py` と `zeus_chat.py` の現状確認 <!-- id: 0 -->
    - [x] 実装計画書（`implementation_plan.md`）の作成（日本語） <!-- id: 1 -->
- [x] **実装: Master Loader**
    - [x] `master_loader.py` 修正: イベントマスタの「アクティブ/表示」フラグ読み込み <!-- id: 2 -->
    - [x] ロジック実装: 「アクティブ」イベントのみ生産目標に合算 <!-- id: 3 -->
    - [x] ロジック実装: 「表示」イベントを収集し `data/event_master.json` へ保存 <!-- id: 4 -->
- [x] **実装: Zeus Intelligence**
    - [x] `zeus_chat.py` 更新: `data/event_master.json` の読み込み処理追加 <!-- id: 5 -->
    - [x] システムプロンプト修正: アクティブ（進捗）と表示（期限監視）の区別を追加 <!-- id: 6 -->
- [x] **検証**
    - [x] `production_master.json`（合算結果）と `event_master.json`（監視リスト）の確認 <!-- id: 7 -->
    - [x] `zeus_chat.py` におけるプロンプト生成内容の確認 <!-- id: 8 -->
    - [x] 手順書/結果報告（`walkthrough.md`）の作成 <!-- id: 9 -->
