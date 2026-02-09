# jj
- jj: CLIベースのグラフデータ構築ツール [README](jj/README.md)
- jj-db: グラフデータの検索・可視化ツール [README](jj-db/README.md)

## 全体規約
- 実装作業はjjとjj-dbの片方ずつで実施してください。
- 実装作業メモもjjとjj-dbの片方ずつで記載してください。
- 各モジュールはneo4j契約のみ共有し、互いに通信を行いません。

---
## 共通のコーディング規約
- 全ての回答は日本語で行なってください
- すべての設計仕様は日本語で文書化してください。
- 本プロジェクトはCodexとClaude Codeの2交代制運用します。常に互いへの引き継ぎを想定してください。
- 実装状況は`docs/status/status-{index}.md`に書いており、現在の状況はindexが一番大きいstatus-{index}.mdに書いています。
- 実装状況は細かく`docs/status/status-{index}.md`に書き出してください。あなたとは別のAIアシスタントが参照し、簡便に状況を把握することが目的です。
- statusに書いた内容はgitのcommitメッセージと整合を取ってください。
- すべてのmarkdown文書には原則project直下のREADME.mdにバックリンクを貼ってください。
- [ ] 作業が完了したらREADME,status,roadmapを更新。TODOはstatusに記入。実装とドキュメントの不整合を発見したらその場で修正するか、TODOに追加すること。
- [ ] 私への確認事項や設計上の懸念がある場合はstatusファイルに書き出すこと。
---
