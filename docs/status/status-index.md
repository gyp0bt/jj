[← README.md](../../README.md)

# status-index — v0.2.0 実装状況インデックス

v0.2.0以降のstatusファイルの索引。各statusは1PR程度の粒度で記録する。

---

## v0.2.0 マイルストーン進捗

| マイルストーン | 状態 | 概要 |
|---------------|------|------|
| **M1: 基盤整備** | 完了 | CI/CD構築、ドキュメント再編、statusアーカイブ、CLAUDE.md/CONTRIBUTING.md |
| **M1.5: ドキュメント再構成** | 進行中 | roadmap分離、CLAUDE.md/README.mdスリム化、マルチソルバー仕様書 |
| **M2: マルチソルバー基盤** | 未着手 | コアconfig柔軟性向上、ソルバー別コネクタ設計（検証環境確保後に実施） |
| **M3: Neo4j統合パイプライン** | 未着手 | jj→Neo4j→jjrv パイプライン実稼働 |
| **M4: jjrv横断ダッシュボード** | 未着手 | Streamlit検証パターンのjjrv移植、横断視認性 |
| **M5: ワークフロー自動化** | 未着手 | runジョブ型、fileコマンド基本 |

---

## statusファイル一覧

| # | 日付 | マイルストーン | 概要 | ブランチ |
|---|------|---------------|------|---------|
| [001](status-001.md) | 2026-02-14 | M1 | CI/CD構築、statusアーカイブ、共有docs構成確立 | claude/setup-project-docs |
| [002](status-002.md) | 2026-02-14 | M1 | CLAUDE.md作成、Getting Started、CONTRIBUTING.md、旧status削除 | claude/setup-project-docs |
| [003](status-003.md) | 2026-02-14 | M1.5 | ドキュメント再構成: roadmap分離、CLAUDE.md/README.mdスリム化、マルチソルバー仕様書 | claude/docs-reorganization-BRtfN |

---

## 過去バージョン

- [v0.1.0 statusインデックス](status-index-v0.1.0.md) — 151件（jj: 90件、jjrv: 61件）
