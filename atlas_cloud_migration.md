# Atlas クラウド化（Streamlit Cloud移行）および機能拡張 仕様書

## 1. プロジェクトの目的
現在のローカルPC上で稼働している「Atlas（生産管理ダッシュボード）」を Streamlit Community Cloud へ移行し、PCの電源がオフの状態でもスマートフォンから最新の進捗（売上目標達成率やNC稼働状況）を確認できるようにする。

## 2. アーキテクチャの変更点（重要）
- **現在:** マスタデータ（メニュー.xlsx等）はGoogleドライブから取得しているが、`history_summary.json`（実績履歴）と `アトラス - シート1.csv`（NC稼働ログ）はローカルPC内に保存されている。
- **クラウド化後:** ローカルにある履歴・ログファイルもすべてGoogleドライブ上に保存・一元管理し、Streamlit Cloud上の `app.py` はGoogleドライブのみをデータソースとして読み書きを行う。

## 3. 移行ステップと実装要件

### Phase 1: ローカルデータのGoogleドライブへの退避（I/O処理の実装）
クラウド化の事前準備として、実績ログの保存先をGoogleドライブに変更する。
1. **対象ファイル:** - `history_summary.json` (売上推移データ)
   - `アトラス - シート1.csv` (NCマシンの自動稼働ログ)
2. **実装内容:** - 既存の `logic.drive_utils` に、ファイルをGoogleドライブの特定フォルダへ上書きアップロード（エクスポート）する関数 `upload_to_drive(local_path, drive_file_id)` を追加する。
   - スキャン処理時やログ追記時に、ローカルへ保存した直後にこの関数を呼び出し、Googleドライブ上の同名ファイルを自動更新する仕組みにする。

### Phase 2: 売上目標フィーバーチャート（バーンアップチャート）の実装
Googleドライブから取得した履歴データを使い、ダッシュボード上に進捗グラフを描画する。
1. **データソース:** Googleドライブからダウンロードした最新の `history_summary.json`
2. **計算ロジック:** `history_summary.json` 内の各 `timestamp` ごとに、各アイテムの `count` × `商品マスタの単価1` を算出し、「総完成額」の時系列推移データを作成する。
3. **描画要件 (Plotly):**
   - X軸: 日付、Y軸: 金額
   - 実績ライン（総完成額の推移）
   - 目標ライン（起点日からイベント当日[2026-05-05]に向けた80万・70万・60万の右肩上がりの直線3本）

### Phase 3: GitHubへのPushとStreamlit Cloudのデプロイ
1. アプリケーションコード（`app.py`, `logic/` など）をGitHubリポジトリへPushする。
2. Streamlit Community Cloud と連携しデプロイする。
3. GoogleドライブAPIの認証情報（`credentials.json` 相当）を、Streamlitの `st.secrets` を用いてセキュアに読み込めるように `logic.drive_utils` の認証ロジックを改修する。

## 4. AIアシスタント（Antigravity）への指示ルール
- 作業は必ず Phase 1 → Phase 2 → Phase 3 の順番で、段階的に進めること。
- 既存のStreamlit (Python) のUI資産を活かすため、UIフレームワークの変更（GASへの移行など）は行わない。
- 常にこのドキュメントをシステムの全体像として意識し、局所的な修正によって既存のデータ連携（`logic.master_loader` 等）を破壊しないこと。