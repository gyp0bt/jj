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

### Getting Started

#### jj（Python CLI）

```bash
cd jj
pip install -e ".[dev]"     # 開発用インストール（コア + テスト依存）
jj init                      # 設定ファイル初期化（.jj/config/ 生成）
jj parse                     # プロジェクトをスキャンしグラフ構築 → .jj/storage/graph.yaml
jj show --summary            # グラフのサマリー表示
jj export --target csv       # ノード属性をCSVエクスポート
```

Abaqus解析やダッシュボードを使う場合:
```bash
pip install -e ".[abaqus,dashboard]"   # Abaqus + ダッシュボード依存を追加
jj dashboard                            # Streamlitダッシュボード起動
```

テスト実行:
```bash
pytest                       # テスト実行（1,002件）
```

#### jjrv（Web ダッシュボード）

```bash
cd jjrv
pnpm install                 # 依存インストール
pnpm dev                     # 開発サーバー起動 (http://localhost:3000)
```

詳細は各モジュールのREADMEを参照: [jj/README.md](jj/README.md) / [jjrv/README.md](jjrv/README.md)

### v0.1.0 サマリー（2026-02-14）

- **jj**: テスト1,002件、パーサー16+クラス、エクスポーター6種、Abaqusプラグイン完全分離、Streamlitダッシュボード稼働
- **jjrv**: RM1〜5完了（検索/閲覧/操作性/本番運用）、RM6（jj統合）設計済み・実装未着手
- **レビュー**: [v0.1.0 レビュー・v0.2.0 ロードマップ案](docs/review/review-v0.1.0.md)

### ドキュメント構成

v0.2.0からdocsは3層構成（ルート共有 + jj固有 + jjrv固有）。

| ドキュメント | 説明 |
|-------------|------|
| [docs/README.md](docs/README.md) | 共有ドキュメント一覧（status/review/全リンク集） |
| [最新status](docs/status/status-002.md) | v0.2.0 実装状況の最新記録 |
| [v0.1.0 statusインデックス](docs/status/status-index-v0.1.0.md) | v0.1.0全statusファイルの索引（151件） |
| [v0.1.0レビュー](docs/review/review-v0.1.0.md) | 開発フェーズ総括・v0.2.0ロードマップ案 |
| [CLAUDE.md](CLAUDE.md) | プロジェクト規約・コーディングガイドライン |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 開発参加ガイド・ブランチ命名規約 |
| [jj/docs/](jj/docs/) | jj固有ドキュメント（ロードマップ・仕様書） |
| [jjrv/docs/](jjrv/docs/) | jjrv固有ドキュメント（RM1-6仕様書） |

## 全体規約

詳細は [CLAUDE.md](CLAUDE.md) を参照。

- 実装作業はjjとjjrvの片方ずつで実施
- 各モジュールはNeo4j契約のみ共有し、直接通信しない
- Codex/Claude Code 2交代制 — 常に引き継ぎを意識
- statusファイルは `docs/status/status-{index}.md` に記録（最大indexが最新）
- すべてのmarkdown文書にREADME.mdへのバックリンクを貼る
- 作業完了時: README/status/roadmapを更新、TODOはstatusに記入
- 確認事項・設計上の懸念はstatusファイルに書き出す
