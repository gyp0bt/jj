[← README.md](README.md)

# CLAUDE.md — コーディング規約・技術リファレンス

> 運用規約（status管理、ブランチ命名、コミット形式、日本語回答）はプロンプトで毎回注入される。
> 本ファイルはコードベースに関する**技術的規約**と**アーキテクチャ参照**に特化する。

---

## コーディング規約

### 全体方針
- **テスト先行**: 構造変更時は既存テストを壊さず完遂し、テスト数を単調増加させる
- **ドキュメント先行**: 仕様書・ロードマップを実装より先に作成し、設計判断を文書化する
- **過度な抽象化の回避**: 1回しか使わない処理のためにヘルパーやユーティリティを作らない
- **暗黙の仮定の排除**: 特定のCAEソフト（Abaqus等）に暗黙的に依存するコアロジックを書かない

### jj（Python）

| 項目 | 規約 |
|------|------|
| テスト | `pytest`。`pip install -e ".[dev]"`。optional依存は `importorskip` |
| lint/format | `ruff check .` + `ruff format --check .`（E/W/F/I/UP/B/SIM/RUF） |
| 依存管理 | コア最小（pydantic, pyyaml, networkx, chardet, ftfy, numpy）。optional依存はグループ分け |

### jjrv（TypeScript/Next.js）

| 項目 | 規約 |
|------|------|
| lint/format | `biome`（`pnpm lint` / `pnpm format`） |
| 型安全 | `tsc --noEmit` + `pnpm build` |
| データソース | SQLite (sql.js) → Neo4j対応予定（IEntityRepository経由で切替） |

---

## アーキテクチャの要所

### モジュール構成

| モジュール | 役割 | 技術 |
|-----------|------|------|
| **jj** | Python CLI — フォルダ/ファイル解析→グラフデータ化→エクスポート | Python 3.10+, NetworkX, Pydantic, Streamlit |
| **jjrv** | Web Dashboard — Neo4j経由グラフ可視化 | Next.js 15, React 19, TypeScript, Tailwind CSS v4 |
| **shared** | 共有パッケージ（Neo4jスキーマ契約、型定義、テストアセット） | Python |

### AbstractFileParser パターン（jj最重要設計）

```
AbstractFileParser
  ├── __init_subclass__() で自動登録
  ├── priority: int で実行順序制御
  ├── apply(project_graph) を各サブクラスが実装
  └── 16+ サブクラスが services/parse/ 配下に分散
```

同パターンを AbstractExporter / DashboardPageConnector にも適用。

### プラグイン拡張パターン

| 拡張種別 | 配置先 | 基底クラス | 登録方式 |
|---------|--------|-----------|---------|
| パーサー | `services/parse/connectors/{solver}/` | `AbstractFileParser` | `__init_subclass__` |
| エクスポーター | `services/export/connectors/` | `AbstractExporter` | `__init_subclass__` |
| ダッシュボードページ | `services/dashboard/connectors/{solver}.py` | `DashboardPageConnector` | `__init_subclass__` |
| プラグインパッケージ | `services/plugins/{solver}/` | — | `pyproject.toml` entry_points |

プラグイン追加時: `pyproject.toml` の `[project.entry-points]` と `[project.optional-dependencies]` を更新。コア層からのハードコードimportは禁止（entry_points経由のみ）。

### CacheProvider プロトコル

- `load_plugin_data(namespace)` / `save_plugin_data(namespace)` で汎用キャッシュ
- GraphStorage が実装を提供し、GraphService コンストラクタ経由でDI注入
- プラグインは namespace で隔離（例: `plugin_cache/abaqus/`）

### データモデル

- **Node**: `id: int, type: str, name: str, format: str, properties: dict[str, Any]`
- **Relation**: `id: int, label: str, node1_id: int, node2_id: int`
- グラフは `.jj/storage/graph.yaml` に永続化

---

## ドキュメント構成

```
docs/                          # 共有ドキュメント（v0.2.0〜）
├── roadmap.md                 # v0.2.0 統合ロードマップ
├── review/                    # レビュー文書
├── status/                    # 共有statusファイル
│   ├── status-index.md        # v0.2.0 statusインデックス
│   ├── status-{NNN}.md        # 実装状況
│   └── archive-v0.1.0/        # v0.1.0 statusアーカイブ
├── specs/                     # マルチソルバー仕様書
jj/docs/                       # jj固有ドキュメント
├── roadmap.md                 # jj v0.1.0 ロードマップ（アーカイブ）
├── detail.md                  # 実装詳細
├── specs/                     # 仕様書（01〜11）
jjrv/docs/                     # jjrv固有ドキュメント
├── spec-roadmap{1-6}.md       # RM1〜RM6仕様書
├── spec-dashboard.md          # ダッシュボード詳細設計
```

---

## よくある作業の手順

### 新規セッション開始時
1. `docs/status/status-index.md` でマイルストーン進捗を確認
2. 最新 `docs/status/status-{NNN}.md` を読む
3. 未完了TODOを確認し、作業計画を立てる

### 作業完了時
1. statusファイルを新規作成（次のindex番号）
2. `docs/status/status-index.md` を更新
3. README, roadmap を必要に応じて更新
4. featureごとにコミットを切り、pushする
