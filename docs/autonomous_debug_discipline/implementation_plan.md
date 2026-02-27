# Atlas Hub 安定稼働に向けた自律的デバッグ＆規律強化 - 実装計画

## 根本原因分析

### 🔴 致命的バグ #1: `logic.js` 構造破損
`logic.js` (990行) のPMオブジェクトリテラルが **途中で閉じてしまっている**。

```
L525: };                    ← ここで const PM = { ... } が閉じる
L527: (function () {        ← IIFE が PM.init() を呼ぶ
L536:     PM.init();
L537: })();
L538: drawLines() {         ← 以降の関数定義がPMオブジェクトの外に漏出！
                               → JS構文エラー → 全JSクラッシュ
```

ファイル後半（L800-988）に、**同じメソッド群を PM オブジェクト内部に正しく定義した複製**が存在する。つまり、L525-L737 の領域は**不正な重複ブロック**。

### 🔴 致命的バグ #2: `index.html` window.onerror 破損

```javascript
// L29 (現在の壊れたコード):
window.onerror = function(message, sourlinlno, error) {
//                                  ^^^^^^^^^^^^^^^^
// 引数が結合破損: "source, lineno, colno" が "sourlinlno" に

// L33 で undefined の source, lineno, colno を参照:
console.innerHTML += `[JS Error] ${message}\n  at ${source}:${lineno}:${colno}\n\n`;
```

→ `window.onerror` 自体が構文的には動くが、**参照する変数名が不一致**のため、エラー画面に情報を表示できない。結果として「真っ白画面」のままエラーの手がかりがゼロになる。

### ✅ データ形式は一致
`production_logic.py` が生成する JSON:
```json
{
  "title": "商品名 (部位名)",
  "start": "2026-02-10",
  "color": "#28a745",
  "extendedProps": {
    "details": "✅ Set (Front & Back)",
    "project": "商品名",
    "part": "部位名",
    "confidence": "high"
  }
}
```
`logic.js` の `renderCalendar()` が期待する形式:
- `e.start` (日付文字列) ✅
- `e.title` (文字列) ✅
- `e.extendedProps.confidence` ✅
- `e.extendedProps.details` ✅

**データ形式自体には不一致はない。** 日本語エンコーディングも `ensure_ascii=False` で正しく処理済み。問題は純粋に **JSの構文エラーで全コードが実行不能** であること。

---

## 修正計画

### コンポーネント1: JS構造修復

#### [MODIFY] [logic.js](file:///c:/Users/yjing/.gemini/atlas-hub/static/logic.js)
- **L524-L737 の不正ブロックを完全削除**。具体的には:
  - L525 の `};` (PMオブジェクトの不正な閉じ括弧)
  - L527-L537 のIIFE (init呼び出し) 
  - L538-L719 の孤立したメソッド定義群
  - L720-L737 の `renderProductionEvents()` 残骸
- L800 以降の正しいメソッド群は既に PM オブジェクト内に定義されているため、そのまま活用
- L988 の `};` と L990 の `PM.init();` の構造を確認・維持

---

### コンポーネント2: エラー画面修復

#### [MODIFY] [index.html](file:///c:/Users/yjing/.gemini/atlas-hub/static/index.html)
- L29 の `window.onerror` 関数シグネチャを修復:
  ```javascript
  window.onerror = function(message, source, lineno, colno, error) {
  ```
- L33 の変数参照も正しくなる

---

### コンポーネント3: ガードレール実装

#### [MODIFY] [index.html](file:///c:/Users/yjing/.gemini/atlas-hub/static/index.html)
- JS実行前のデータ健全性チェック機構を `<script>` ブロックに追加:
  - `PM.productionEvents` の型チェック（配列か？）
  - 各イベントに必須フィールド (`start`, `title`, `extendedProps`) が存在するか検証
  - 不正データ検出時にユーザーへアラート表示（真っ白にしない）

#### [MODIFY] [app.py](file:///c:/Users/yjing/.gemini/atlas-hub/app.py)
- `events_json` 生成後にバリデーションロジック追加:
  - JSON パース可能か再検証
  - イベント数をログ表示
  - 空配列の場合は info メッセージを出力

---

### コンポーネント4: 規律ドキュメント更新

#### [MODIFY] [skill.md](file:///c:/Users/yjing/.gemini/atlas-hub/skill.md)
- 「UI統合時のデバッグ規律」セクションを追加

#### [NEW] [仕様書.md](file:///c:/Users/yjing/.gemini/atlas-hub/仕様書.md)
- カレンダーが動くための「データの最小定義」を明文化
- 不純データ混入時の回避ロジックを設計・記述

---

## 検証計画

### ブラウザ検証
1. Streamlit を起動: `cd c:\Users\yjing\.gemini\atlas-hub && venv\Scripts\python.exe -m streamlit run app.py --server.port 8501`
2. ブラウザで http://localhost:8501 を開く
3. 📅 カレンダータブをクリック → カレンダーが表示され、月の切り替え（Prev/Next）が機能することを確認
4. コンソールに JS エラーが出ていないことを確認

### 手動テスト（ユーザーに依頼）
- Google Drive からのデータ取得が必要なため、最終的な本番データでのカレンダー表示確認はユーザーに依頼
