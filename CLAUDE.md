[← README.md](README.md)

# CLAUDE.md — プロジェクト規約・コーディングガイドライン

## プロジェクト概要

CAE業務データをグラフ構造化し、検索・可視化・横断比較を可能にするツール群。

| モジュール | 役割 | 技術 |
|-----------|------|------|
| **jj** | Python CLI — フォルダ/ファイル解析→グラフデータ化→エクスポート | Python 3.10+, NetworkX, Pydantic, Streamlit |
| **jjrv** | Web Dashboard — Neo4j経由グラフ可視化 | Next.js 15, React 19, TypeScript, Tailwind CSS v4 |
| **shared** | 共有パッケージ（Neo4jスキーマ契約、型定義、テストアセット） | Python |

---

## 運用規約

### 開発体制
- Codex と Claude Code の**2交代制**。常に引き継ぎを意識すること
- 実装作業は **jj と jjrv の片方ずつ**で実施（同時変更しない）
- 各モジュールは **Neo4j契約のみ共有**し、直接通信しない

### ドキュメント言語
- すべての回答・設計仕様は**日本語**で記述
- コード中のコメント・docstringは日本語/英語いずれも可（既存に合わせる）

### statusファイル
- 実装状況は `docs/status/status-{index}.md` に記録（v0.2.0〜 共有docs配下）
- 最新indexのファイルが現在の状況
- **粒度基準**: 1 status = 1 PR 程度。1バグ修正でも大規模リファクタでも、PRとセットで1 status
- statusに書いた内容は **gitのcommitメッセージと整合**を取る
- 未完了TODOは次のstatusに明示的に引き継ぐ
- すべてのmarkdown文書にはproject直下の `README.md` にバックリンクを貼る

### gitルール
- **ブランチ命名**: `claude/{feature-keyword}-{hash}` — feature-keywordはstatusで使用する機能名と一致
- **コミットメッセージ**: `{type}: {日本語の変更概要} (status-{NNN})` — typeは feat/fix/refactor/docs/ci/test
- featureごとにコミットを切り、最後にpushする
- 確認事項や設計上の懸念はstatusファイルに書き出す

---

## コーディング規約（v0.1.0レビューからの教訓）

### 全体方針
- **テスト先行**: 構造変更時は既存テストを壊さず完遂し、テスト数を単調増加させる
- **ドキュメント先行**: 仕様書・ロードマップを実装より先に作成し、設計判断を文書化する
- **過度な抽象化の回避**: 1回しか使わない処理のためにヘルパーやユーティリティを作らない
- **暗黙の仮定の排除**: 特定のCAEソフト（Abaqus等）に暗黙的に依存するコアロジックを書かない

### jj（Python）固有

#### パーサー追加
- `AbstractFileParser` の `__init_subclass__` パターンに従い、ファイル1つで完結させる
- `priority` 属性でパーサー間の実行順序・依存関係を明示的に管理
- テストアセット（`shared/tests/test_asset1/`）を使ったE2Eテストを必ず含める
- パーサーはコネクタ配下（`services/parse/connectors/{solver}/`）に配置

#### エクスポーター追加
- `AbstractExporter` サブクラスとして実装（`__init_subclass__` 自動登録）
- `format_cli_result()` を必ずオーバーライドし、CLIフレンドリーな出力を返す
- `services/export/connectors/` に配置

#### ダッシュボードページ追加
- `DashboardPageConnector` 基底クラスのサブクラスとして実装
- `connector_key` 属性でコネクタ固有config参照
- コネクタは `services/dashboard/connectors/{solver}.py` に配置

#### プラグイン追加
- `services/plugins/{solver}/` にプラグインパッケージを作成
- `pyproject.toml` の `[project.entry-points]` と `[project.optional-dependencies]` を更新
- `plugin_registry.py` の entry_points 動的発見メカニズムで自動ロード
- コア層からのハードコードimportは禁止（entry_points経由のみ）

#### 依存管理
- コア依存は最小限に保つ（pydantic, pyyaml, networkx, chardet, ftfy, numpy）
- optional依存はグループ分け（abaqus/dashboard/api/neo4j/ssh/dev）
- モジュールレベルimportでoptional依存を使う場合はコア依存に移動するか、遅延importにする

#### テスト
- `pytest` 使用。`pip install -e ".[dev]"` でテスト環境構築
- optional依存のテストは `importorskip` でスキップ可能にする
- CIでは `.[dev]` のみでコアテストを実行

#### lint/format
- `ruff` を使用（E/W/F/I/UP/B/SIM/RUF ルール）
- `ruff check .` + `ruff format --check .` でCI検証

### jjrv（TypeScript/Next.js）固有

#### lint/format
- `biome` を使用（`pnpm lint` / `pnpm format`）

#### 型安全
- `tsc --noEmit` で型チェック
- `pnpm build` でビルド検証

#### データソース
- 現状: SQLite (sql.js) — ブラウザ内DB
- 計画: Neo4j対応（IEntityRepositoryインターフェース経由で切替）
- データソース切替はfactoryパターンで実装予定

---

## アーキテクチャの要所

### AbstractFileParser パターン（jj最重要設計）
```
AbstractFileParser
  ├── __init_subclass__() で自動登録
  ├── priority: int で実行順序制御
  ├── parse(project_graph) を各サブクラスが実装
  └── 16+ サブクラスが services/parse/ 配下に分散
```
- パーサー追加時に既存コードの変更が不要
- 同パターンを AbstractExporter / DashboardPageConnector にも適用

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
├── review/                    # レビュー文書
├── status/                    # 共有statusファイル
│   ├── status-{NNN}.md       # 最新の実装状況
│   ├── status-index-v0.1.0.md # v0.1.0全statusインデックス
│   └── archive-v0.1.0/       # v0.1.0 statusアーカイブ
jj/docs/                       # jj固有ドキュメント
├── roadmap.md                 # jjロードマップ
├── detail.md                  # 実装詳細
├── specs/                     # 仕様書（01〜11）
└── status/                    # 旧statusファイル（参照用、アーカイブ済み）
jjrv/docs/                     # jjrv固有ドキュメント
├── spec-roadmap{1-6}.md       # RM1〜RM6仕様書
├── spec-dashboard.md          # ダッシュボード詳細設計
└── status/                    # 旧statusファイル（参照用、アーカイブ済み）
```

---

## よくある作業の手順

### 新規セッション開始時
1. `docs/status/` の最大indexのstatusファイルを読む
2. README.md でプロジェクト全体像を把握
3. 未完了TODOを確認し、作業計画を立てる

### 作業完了時
1. statusファイルを新規作成（次のindex番号）
2. README, roadmap を必要に応じて更新
3. 実装とドキュメントの不整合を発見したらその場で修正 or TODOに追加
4. featureごとにコミットを切り、pushする

---

## v0.2.0 マイルストーン

```
M1: 基盤整備 → M2: Fluentコネクタ
      │
      └──→ M3: Neo4j統合 → M4: 横断ダッシュボード
                                  │
M5: ワークフロー自動化 ←─────────┘
```

詳細は [v0.1.0 レビュー・v0.2.0 ロードマップ案](docs/review/review-v0.1.0.md) を参照。
