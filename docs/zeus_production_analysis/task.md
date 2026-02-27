# タスクリスト: 動作フロー仕様書に基づく全面改修

## Phase 1: master_loader.py の改修
- [x] イベントマスタのアクティブ行から「備考」列を読み取り、持越元の初期在庫を動的に特定
- [x] `_import_initial_from_note()` 関数を新規追加
- [x] `merge_event_targets` の履歴記録に `details`（商品IDごとの個数）を確実に含める
- [ ] 古い details 無しエントリのクリーンアップ（オプション）

## Phase 2: zeus_chat.py の改修
- [x] `get_daily_achievements()`: 最新ログ vs 直前ログの比較ロジックに修正（details付きエントリのみ対象）
- [x] `load_history_stats()`: 全ログベースの平均ペース算出に改修
- [x] `build_system_prompt()`: 残工数ベースの未来予測ロジックを実装

## Phase 3: エラーハンドリング & 検証
- [x] NameError（today_str等）の根絶確認
- [x] ライブラリ不足時の警告確認
- [x] 構文チェック実行
- [x] 既存テスト実行（verify_zeus_logic 2件 PASS / test_master_loader は pytest 未インストールで skip）
- [ ] Drive同期 & スキャン実行による実動作確認（ユーザーに委託）
