# Google Drive 統合タスク

- [ ] 環境構築
  - [x] `requirements.txt` の作成/更新（`google-api-python-client`, `google-auth-oauthlib` 追加）
- [ ] 実装
  - [x] `logic/drive_utils.py` の作成（Google認証とファイル操作）
  - [x] `authenticate_drive()` 関数の実装
  - [x] `get_file_dataframe(filename)` 関数の実装
  - [x] `app.py` の修正（`drive_utils` の利用）
- [ ] 検証
  - [ ] コードの構文チェック
  - [ ] ユーザーへの認証手順（`credentials.json`）の案内
