# Google Drive Integration Walkthrough

## 変更内容
Google Drive API を利用して、クラウド上の `メニュー.xlsx` と `アトラス - シート1.csv` を直接読み込む機能を実装しました。

### **Files Modified**
- `requirements.txt`: 必要なライブラリ (`google-api-python-client` 等) を追加。
- `logic/drive_utils.py`: **[新規作成]** Google 認証とファイル取得のロジックを担当。
- `app.py`: ローカルファイル読み込みを廃止し、`drive_utils` を使用するように変更。

## 認証設定手順 (ユーザー作業)
アプリケーションを実行する前に、以下の手順で Google Cloud の設定と認証ファイルの配置が必要です。

1. **Google Cloud Console でプロジェクト作成**
   - [Google Cloud Console](https://console.cloud.google.com/) にアクセスし、新しいプロジェクトを作成します。
   - 左側メニューの「API とサービス」>「ライブラリ」から **Google Drive API** を検索し、有効化します。

2. **OAuth 同意画面の設定**
   - 「API とサービス」>「OAuth 同意画面」を開きます。
   - User Type を「外部」にし、作成。
   - アプリ情報（名前、メール）を入力。
   - **テストユーザー** にご自身の Google アカウント（メールアドレス）を追加します。

3. **認証情報 (credentials.json) の取得**
   - 「API とサービス」>「認証情報」を開きます。
   - 「認証情報を作成」>「OAuth クライアント ID」を選択。
   - アプリケーションの種類: **デスクトップ アプリ**
   - 名前: 任意（例: Atlas Hub Local）
   - 作成後、「JSON をダウンロード」をクリックし、ファイル名を `credentials.json` に変更します。
   - このファイルを `Atlas Hub` のプロジェクトルートフォルダ（`app.py` と同じ場所）に配置します。

4. **アプリケーションの実行**
   ```powershell
   pip install -r requirements.txt
   streamlit run app.py
   ```
   - 初回起動時、ブラウザが自動的に開き Google アカウントのログイン画面が表示されます。
   - 「このアプリは Google によって確認されていません」と出る場合は、「詳細」>「(アプリ名)（安全ではないページ）に移動」をクリックして進めてください（テストアプリのため）。
   - 必要な権限を許可すると、認証が完了し、アプリが起動します。

## 検証結果
- コード変更は完了しており、`credentials.json` さえあれば動作する状態です。
- エラーハンドリングも実装済み（ファイルが見つからない場合や認証失敗時に警告を表示）。
