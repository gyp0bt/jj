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
[jj parse] ── フォルダ/ファイル解析 → グラフ構築 (.j2/storage/)
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
jj init                      # 設定ファイル初期化（.j2/config/ 生成）
jj parse                     # プロジェクトをスキャンしグラフ構築 → .j2/storage/graph.yaml
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

### ドキュメント

| ドキュメント | 説明 |
|-------------|------|
| [docs/roadmap.md](docs/roadmap.md) | **v0.2.0 統合ロードマップ**（マイルストーン・仕様書リンク） |
| [docs/status/status-index.md](docs/status/status-index.md) | v0.2.0 statusインデックス |
| [docs/README.md](docs/README.md) | 共有ドキュメント一覧 |
| [CLAUDE.md](CLAUDE.md) | コーディング規約・技術リファレンス |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 開発参加ガイド |
| [jj/docs/specs/](jj/docs/specs/) | jj機能ドメイン別仕様書（01〜11） |
| [jjrv/docs/](jjrv/docs/) | jjrv RM1-6仕様書 |

### v0.1.0 サマリー（2026-02-14）

- **jj**: テスト1,002件、パーサー16+クラス、エクスポーター6種、Abaqusプラグイン完全分離、Streamlitダッシュボード稼働
- **jjrv**: RM1〜5完了（検索/閲覧/操作性/本番運用）、RM6（jj統合）設計済み・実装未着手
- **レビュー**: [v0.1.0 レビュー](docs/review/review-v0.1.0.md)
