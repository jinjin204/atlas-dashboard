# 軍師Zeus タブ追加 — Gemini AIチャットUI実装

アトラス工房の生産管理アプリ（Atlas Hub）に、Gemini APIを使ったAIチャットタブ「⚔️ 軍師Zeus」を追加する。マスタデータ（加工時間、材料、在庫等）と現在の在庫状況をコンテキストとして注入し、「大斧のNC加工時間は？」のような質問にマスタデータに基づいて回答できるようにする。

## User Review Required

> [!IMPORTANT]
> **Gemini APIキーの管理方法**: APIキーは `st.secrets`（Streamlit標準）で管理します。`.streamlit/secrets.toml` にキーを設定する前提です。別の方法（環境変数等）がよければ教えてください。

> [!IMPORTANT]
> **使用モデル**: `gemini-2.0-flash` を使用する予定です。別のモデルが良ければ指定してください。

## Proposed Changes

### 依存関係

#### [MODIFY] [requirements.txt](file:///c:/Users/yjing/.gemini/atlas-hub/requirements.txt)
- `google-generativeai` パッケージを追加

---

### チャットロジック

#### [NEW] [zeus_chat.py](file:///c:/Users/yjing/.gemini/atlas-hub/logic/zeus_chat.py)

Gemini APIとの対話ロジックを分離したモジュール。

- **`build_system_prompt(master_data, inventory_df)`**: マスタデータと在庫状況からシステムプロンプトを構築
  - AIキャラ：「アトラス工房の軍師Zeus」
  - コンテキスト：全商品の加工時間、材料、在庫数を構造化テキストで注入
  - 指示：マスタデータに基づいて正確に回答、データにない質問は「マスタにデータがありません」と回答

- **`get_chat_response(chat_session, user_message)`**: チャットセッションにメッセージを送信し応答を取得
  - エラーハンドリング（APIキー未設定、レート制限等）

---

### メインアプリ

#### [MODIFY] [app.py](file:///c:/Users/yjing/.gemini/atlas-hub/app.py)

1. **ナビゲーション更新**: `PAGES`リストに `"⚔️ 軍師Zeus"` を追加
2. **Zeusタブ追加**: 新しい `elif` ブロック
   - Streamlit `st.chat_message` / `st.chat_input` を使ったチャットUI
   - `st.session_state` でチャット履歴とGeminiセッションを管理
   - APIキーは `st.secrets["GEMINI_API_KEY"]` から取得
   - 初回アクセス時にシステムプロンプト構築 & セッション開始
   - 会話リセットボタン

---

### APIキー設定

#### [NEW] [secrets.toml](file:///c:/Users/yjing/.gemini/atlas-hub/.streamlit/secrets.toml)

```toml
GEMINI_API_KEY = "YOUR_API_KEY_HERE"
```

## Verification Plan

### 手動テスト
1. `pip install google-generativeai` を実行
2. `.streamlit/secrets.toml` に有効なGemini APIキーを設定
3. `streamlit run app.py` でアプリ起動
4. サイドバーに「⚔️ 軍師Zeus」タブが表示されることを確認
5. チャット入力欄に「大斧のNC加工時間は？」と入力 → マスタデータに基づいた回答が返ることを確認
6. 「リセット」ボタンで会話がクリアされることを確認
7. APIキー未設定時にエラーメッセージが表示されることを確認
