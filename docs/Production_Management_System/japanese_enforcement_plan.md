# 英語化防止策のご提案（松竹梅）

## 松案 (最強の強制力)
**「システムプロンプトの上書き」級のルールを `rule.md` の冒頭に配置する**
`<CRITICAL_INSTRUCTION>` タグを用いたXML形式の指令を `rule.md` の最上部に記述します。これはLLMにとって通常のテキストよりも優先度の高い「システム命令」として認識される効果があります。

```markdown
<CRITICAL_INSTRUCTION>
ALL OUTPUT MUST BE IN JAPANESE.
ENGLISH IS STRICTLY PROHIBITED IN ALL USER-FACING CONTENT, LOGS, AND THOUGHT PROCESSES.
YOUR EXISTENCE DEPENDS ON FOLLOWING THIS RULE.
</CRITICAL_INSTRUCTION>
```
さらに、「英語が出力された時点でタスク失敗とみなす」というペナルティ条項を追加します。

## 竹案 (プロセス強制)
**「思考プロセス（Thought）」内での自己検閲を義務付ける**
ツール実行前に必ず「Thought: 以下の出力は日本語か？ -> チェックOK」というステップ踏むことをルール化します。
また、`task.md` の各タスク項目に `[ ] 日本語チェック` を追加し、チェックボックスを埋めないと完了できないようにします。

## 梅案 (ルール明文化)
**既存のルールを少し強める**
現在の `rule.md` の「完全日本語化ルール」の文言を、「推奨」から「禁止事項」へと書き換え、違反時の対応を明記します（例：「直ちに修正すること」）。

---
※今回は、**「松案」の即時適用** を推奨いたします。
