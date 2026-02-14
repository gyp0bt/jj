# jjrv (jj-repository-viewer)

jjプロジェクト（Python CLI）が構造化したCAEプロジェクトのグラフデータを、Neo4j経由で参照・可視化するレポジトリダッシュボード。
従来のmat-db（材料/案件/タグ管理データベース）の検索・可視化機能を維持しつつ、jjとの統合によりレポジトリ単位のプロジェクト俯瞰機能を提供する。

---
```markdown
## 規約
- すべての設計仕様は日本語で文書化してください。
- 本プロジェクトはCodexとClaude Codeの2交代制運用します。常に互いへの引き継ぎを想定してください。
- 実装状況は`docs/status/status-{index}.md`に書いており、現在の状況はindexが一番大きいstatus-{index}.mdに書いています。
- 実装状況は細かく`docs/status/status-{index}.md`に書き出してください。あなたとは別のAIアシスタントが参照し、簡便に状況を把握することが目的です。
- statusに書いた内容はgitのcommitメッセージと整合を取ってください。
- すべてのmarkdown文書には原則project直下のREADME.mdにバックリンクを貼ってください。
- [ ] 作業が完了したらREADME,status,roadmapを更新。TODOはstatusに記入。実装とドキュメントの不整合を発見したらその場で修正するか、TODOに追加すること。
---
```
---

## プロジェクトサマリー

| 項目 | 内容 |
|------|------|
| 目的 | jjが構造化したCAEグラフデータのレポジトリダッシュボード＋検索・可視化 |
| 開発体制 | 個人開発（休日の趣味プロジェクト） |
| 開発者スキル | Python習熟、Next.js学習中 |
| 技術スタック | Next.js 15, React 19, Tailwind CSS v4, TypeScript, SQLite (sql.js) |
| 本番運用環境 | Windows |
| 現在フェーズ | ロードマップ5完了＋ロードマップ6（jj統合・レポジトリダッシュボード）策定済み |

### Commands

```bash
pnpm dev          # 開発サーバー起動 (http://localhost:3000)
pnpm build        # プロダクションビルド
pnpm lint         # Biomeでlint
pnpm format       # Biomeでフォーマット（自動修正）
```

---

## ドキュメント

| ドキュメント | 説明 |
|-------------|------|
| [最新status](docs/status/status-060.md) | 実装状況の最新記録 |
| [status一覧](docs/status/status-index.md) | 全statusファイルの索引 |
| [spec-roadmap1](docs/spec-roadmap1.md) | ロードマップ1: ユーザー運用の実現（完了） |
| [spec-roadmap2](docs/spec-roadmap2.md) | ロードマップ2: 検索・閲覧体験の拡張（2-13以外実装済み） |
| [spec-roadmap2.5](docs/spec-roadmap25.md) | ロードマップ2.5: 詳細ビューの作り込み（追加仕様あり） |
| [spec-roadmap3](docs/spec-roadmap3.md) | ロードマップ3: 操作性の調整（3-15〜3-18実装済み） |
| [spec-roadmap4](docs/spec-roadmap4.md) | ロードマップ4: 本番運用・neo4jグラフDB移行計画 |
| [spec-roadmap5](docs/spec-roadmap5.md) | ロードマップ5: レポジトリ階層制約（破壊的変更） |
| [spec-roadmap6](docs/spec-roadmap6.md) | ロードマップ6: jj統合・レポジトリダッシュボード |
| [spec-dashboard](docs/spec-dashboard.md) | レポジトリダッシュボード詳細設計 |
| [schema-keys](docs/schema-keys.md) | schema_keys / sysProps / sysTags 一覧 |
| [属性抽出起点](docs/attribute-extraction.md) | 典型パターン属性抽出ロジック起点 |
| [全仕様](docs/全仕様.md) | 詳細仕様（設計思想・ロードマップ・Import/Export・データモデル等） |
| [レビュー 00](docs/review/review-00.md) | プロジェクト状況・ロードマップ俯瞰レビュー (2026-01-31) |

---

## Specs Index（個別仕様書）

> 個別仕様書は実装ファイル直下に配置。

### Components
- [コンポーネント一覧](src/components/README.md)

### Lib
- [lib](src/lib/README.md)

### Pages
- [ページ一覧](src/app/README.md)
