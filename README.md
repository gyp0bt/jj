# jj

CAE業務データをグラフ構造化し、検索・可視化・横断比較を可能にするツール群。

| モジュール | 役割 | 技術 | README |
|-----------|------|------|--------|
| **jj** | ローカルプロジェクトのフォルダ/ファイルを解析しグラフデータ化。Obsidian/Neo4j/CSV/JSON/ダッシュボードにエクスポート | Python, NetworkX, Pydantic, Streamlit | [jj/README.md](jj/README.md) |
| **jjrv** | jjで構造化したグラフデータをNeo4j経由で参照し、レポジトリダッシュボードとして可視化 | Next.js 15, React 19, TypeScript, Tailwind CSS v4 | [jjrv/README.md](jjrv/README.md) |
| **shared** | jj/jjrv共有パッケージ（Neo4jスキーマ契約、型定義、テストアセット） | Python | [shared/assets/README.md](shared/assets/README.md) |

### アーキテクチャ概要

```
ローカルCAEプロジェクト
    │
    ▼
[jj parse] ── フォルダ/ファイル解析 → グラフ構築 (.jj/storage/)
    │
    ├── [jj dashboard] ── Streamlitダッシュボード（ローカル即時確認）
    ├── [jj serve] ──── REST API (FastAPI)
    ├── [jj export --target obsidian] ── Obsidian Vault
    └── [jj export --target neo4j] ── Neo4j Database
                                            │
                                            ▼
                                      [jjrv] ── レポジトリダッシュボード（チーム共有・横断検索）
```

### v0.1.0 サマリー（2026-02-14）

- **jj**: テスト1,002件、パーサー16+クラス、エクスポーター6種、Abaqusプラグイン完全分離、Streamlitダッシュボード稼働
- **jjrv**: RM1〜5完了（検索/閲覧/操作性/本番運用）、RM6（jj統合）設計済み・実装未着手
- **レビュー**: [v0.1.0 レビュー・v0.2.0 ロードマップ案](docs/review/review-v0.1.0.md)

### 共有ドキュメント (docs/)

v0.2.0から `docs/` はjj/jjrv共有。

| ドキュメント | 説明 |
|-------------|------|
| [最新status](docs/status/status-001.md) | v0.2.0 実装状況の最新記録 |
| [v0.1.0 statusインデックス](docs/status/status-index-v0.1.0.md) | v0.1.0全statusファイルの索引（151件） |
| [v0.1.0レビュー](docs/review/review-v0.1.0.md) | 開発フェーズ総括・v0.2.0ロードマップ案 |

## 全体規約
- 実装作業はjjとjjrvの片方ずつで実施してください。
- 実装作業メモもjjとjjrvの片方ずつで記載してください。
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
