# Google Drive 統合 実装計画

## 目標
ローカルファイル（`メニュー.xlsx`, `アトラス - シート1.csv`）の代わりに、Google Drive 上の同名ファイルを直接読み込み、アプリケーションで利用可能にする。

## ユーザー確認事項
- **Google Cloud Project**: Google Cloud Console でプロジェクトを作成し、Google Drive API を有効化する必要があります。
- **OAuth Credentials**: `credentials.json`（OAuth デスクトップアプリ用クライアントID）を取得し、プロジェクトルートに配置する必要があります。
- **初回認証**: アプリ起動時にブラウザが開き、Google アカウントでのログインと権限リクエストが求められます。

## 変更内容

### 依存関係
#### [NEW] `requirements.txt`
- `google-api-python-client`
- `google-auth-oauthlib`
- `pandas`
- `openpyxl`
- `streamlit`

### ロジック層
#### [NEW] `logic/drive_utils.py`
Google Drive API との対話を担当するモジュールを作成します。
- `authenticate()`: OAuth 認証フローを実行し、`token.json` を保存/読み込みして `service` オブジェクトを返します。
- `get_drive_service()`: 認証済みの service を返します。
- `find_file_by_name(filename)`: ファイル名で Drive を検索し、ID を取得します。
- `download_file_to_stream(file_id)`: ファイルIDを使ってコンテンツをバイトストリームとしてダウンロードします。
- `load_data_from_drive()`: 上記を組み合わせて、指定された2つのファイルを DataFrame として返します。

### アプリケーション層
#### [MODIFY] `app.py`
- ローカルファイル読み込み処理 (`pd.read_excel`, `pd.read_csv`) を `logic.drive_utils.load_data_from_drive()` に置き換えます。
- 認証エラー時のハンドリングを追加します。

## 検証計画
### 自動テスト
- 現環境では E2E のブラウザ認証テストは困難なため、モックまたは構文チェックを行います。

### 手動検証
ユーザーに以下の手順を実行してもらいます。
1. `requirements.txt` のインストール。
2. `credentials.json` の配置。
3. `streamlit run app.py` の実行。
4. ブラウザでの Google 認証完了。
5. アプリ画面にデータが正しくロードされ、在庫が表示されることを確認。
