# Atlas Hub デバッグ＆規律強化 ウォークスルー

## 発見した致命的バグ

### バグ #1: `logic.js` 構造破損 (根本原因)
[logic.js](file:///c:/Users/yjing/.gemini/atlas-hub/static/logic.js) のL525 で `const PM = {...}` が途中で閉じ、
L538以降のメソッド群(`drawLines`, `startLink`, `setupEvents` 等)がオブジェクト外に漏出。
**JS構文エラーで全コードが実行不能** → カレンダー含む全機能が停止。

### バグ #2: `index.html` window.onerror 破損
[index.html](file:///c:/Users/yjing/.gemini/atlas-hub/static/index.html) のエラーハンドラ関数の引数名が壊れており(`sourlinlno`)、
エラー表示機能自体が死亡 → 原因特定のヒントがゼロに。

> [!IMPORTANT]
> データ形式の不一致ではなかった。`production_logic.py` の出力と `logic.js` の期待形式は完全一致していた。

---

## 修正内容

| ファイル | 修正概要 |
|---|---|
| [logic.js](file:///c:/Users/yjing/.gemini/atlas-hub/static/logic.js) | 不正重複ブロック(約280行)を削除、PMオブジェクト再構成、IIFE永続化パターン復元 |
| [index.html](file:///c:/Users/yjing/.gemini/atlas-hub/static/index.html) | `window.onerror` 引数修復 + データ健全性チェック(ガードレール)追加 |
| [app.py](file:///c:/Users/yjing/.gemini/atlas-hub/app.py) | Python側データバリデーション、イベント数通知、JSONパース検証追加 |
| [skill.md](file:///c:/Users/yjing/.gemini/atlas-hub/skill.md) | UI統合時のJSデバッグ規律チェックリスト追加 |
| [仕様書.md](file:///c:/Users/yjing/.gemini/atlas-hub/仕様書.md) | 新規作成: データ最小定義、フォールバック連鎖設計 |

---

## 検証結果

```
✅ ブラケットバランス: { 199/199 }, ( 537/537 ), [ 23/23 ]
✅ productionEvents: [] は line 16 に1回のみ → インジェクション正常動作
✅ PM.init() は IIFE 内から正しく呼び出し
✅ window.onerror の引数: (message, source, lineno, colno, error) 正常
```

---

## 残り確認事項
- ブラウザでの実動作確認（`streamlit run app.py` → カレンダータブ → Prev/Next 操作）
