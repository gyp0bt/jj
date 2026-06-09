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

### Python規約

| 項目 | 規約 |
|------|------|
| テスト | `pytest`。`pip install -e ".[dev]"`。外部optional依存（pandas, plotly等）は `importorskip`。**pymesh（modules/pymesh/）はプロジェクト内パッケージであり、optionalではない。** pymeshのテスト失敗はimportパスや依存パッケージ不足の問題として調査すること。 |
| lint/format | `ruff check .` + `ruff format --check .`（E/W/F/I/UP/B/SIM/RUF） |
| 依存管理 | コア最小（pydantic, pyyaml, networkx, chardet, ftfy, numpy）。optional依存はグループ分け |

---

## アーキテクチャの要所

### ディレクトリ構成（v0.2.1）

```
jj/                            # プロジェクトルート
├── config/                    # 設定管理
├── jj_types/                  # データモデル（Node, Relation, GraphModel）
├── modules/                   # 共通モジュール（pymesh等）
├── plugins/                   # プラグインパッケージ（v0.2.1 新構造）
│   ├── base/                  # 基底クラス群
│   │   ├── parser.py          # AbstractFileParser
│   │   └── exporter.py        # AbstractExporter
│   ├── abaqus/                # Abaqusプラグイン
│   │   ├── parse/             # パーサー群
│   │   └── submit.py          # ジョブ投入サービス
│   └── obsidian/              # Obsidianプラグイン
│       ├── parse/             # パーサー群
│       └── export.py          # エクスポーター
├── services/                  # メインロジック
│   ├── cli/                   # CLIエントリポイント（jj = services.cli:main）
│   ├── service/               # CLIビジネスロジック（GraphCommand/Info/RunCommand）
│   ├── graph/                 # GraphService + query（データ供給層）
│   ├── parse/                 # パーサー共通（後方互換re-exportあり）
│   │   └── parsers/           # 組み込みパーサー
│   ├── export/                # エクスポーター共通
│   ├── run/                   # Runサービス（実行＋RunQueryService）
│   ├── dashboard/             # Streamlit UI（widgets + app/）
│   ├── lib/                   # 小物（selection, credentials）
│   └── sdk/                   # プラグインSDK（cache, plugin_manifest/registry）
├── shared/                    # 共有パッケージ（テストアセット）
├── tests/                     # テストスイート
├── docs/                      # ドキュメント
├── pyproject.toml             # パッケージ設定
└── CLAUDE.md                  # 本ファイル
```

### アクティブなCLIコマンド

| コマンド | 用途 |
|---------|------|
| `jj init` | 設定ファイル初期化 |
| `jj parse` | グラフ生成 |
| `jj show` | グラフ表示 |
| `jj export` | エクスポート |
| `jj info` | ファイル詳細 |
| `jj diff` | INP差分比較 |
| `jj jobs` | RUN（ジョブ）一覧 |
| `jj run` (jj r) | コマンド実行+ログ |
| `jj config migrate` | 設定移行 |

### AbstractFileParser パターン（最重要設計）

```
AbstractFileParser
  ├── __init_subclass__() で自動登録（_parser_registry へ）
  ├── priority: int で実行順序制御（小さいほど先。同値はグループ）
  ├── requires_full: bool（True は --full 時のみ実行）
  ├── apply(project_graph) を各サブクラスが実装
  └── plugins/{solver}/parse/ 配下に分散
```

同パターンを AbstractExporter にも適用。

#### 自動登録の所在を追う（「どこに実装があるか分からない」対策）

自動登録は便利な反面、実装の所在が見えにくい。パイプラインは可視化できる:

| 手段 | 効果 |
|------|------|
| `jj parse --explain` | パースせず、priority順に「パーサー名・定義ファイル:行・タスク（docstring1行目）」を一覧表示 |
| `jj parse --trace` / `JJ_PARSE_TRACE=1` | 実行しながら各パーサーの定義ファイル:行・ノード/リレーション増分・所要時間を出力 |
| `plugins.base.parser.format_pipeline_plan()` / `describe_registry()` / `parser_location(cls)` | 上記をコードから取得（`services.parse.base` からも re-export） |

パーサーの **docstring 1行目がそのまま「タスク」表示**になるため、1行目に役割を書く。

### プラグイン拡張パターン（v0.2.1）

| 拡張種別 | 配置先 | 基底クラス | 登録方式 |
|---------|--------|-----------|---------|
| パーサー | `plugins/{solver}/parse/` | `AbstractFileParser` | `__init_subclass__` |
| エクスポーター | `plugins/{solver}/export.py` | `AbstractExporter` | `__init_subclass__` |
| プラグインパッケージ | `plugins/{solver}/` | — | `pyproject.toml` entry_points |

現在有効なプラグイン: **abaqus**, **obsidian**

プラグイン追加時: `pyproject.toml` の `[project.entry-points]` と `[project.optional-dependencies]` を更新。コア層からのハードコードimportは禁止（entry_points経由のみ）。

### 後方互換パス

v0.2.1で旧パスからのimportも引き続きサポート（re-export）:

| 旧パス | 新パス |
|--------|--------|
| `services.parse.base` | `plugins.base.parser` |
| `services.export` | `plugins.base.exporter` |
| `services.plugins.abaqus` | `plugins.abaqus` |
| `services.parse.connectors.abaqus` | `plugins.abaqus.parse` |
| `services.plugins.obsidian` | `plugins.obsidian` |
| `services.parse.connectors.obsidian` | `plugins.obsidian.parse` |
| `services.export.connectors.obsidian` | `plugins.obsidian.export` |

### CacheProvider プロトコル

- `load_plugin_data(namespace)` / `save_plugin_data(namespace)` で汎用キャッシュ
- GraphStorage が実装を提供し、GraphService コンストラクタ経由でDI注入
- プラグインは namespace で隔離（例: `plugin_cache/abaqus/`）

### データモデル

- **Node**: `id: int, type: str, name: str, format: str, properties: dict[str, Any], category: NodeCategory`
- **Relation**: `id: int, label: str, node1_id: int, node2_id: int`
- **NodeCategory**: `FILE | DIRECTORY | DATA | REPOSITORY | RUN`
- グラフは `.j2/storage/graph.yaml` に永続化

---

## optional-dependencies（v0.2.1）

```toml
[project.optional-dependencies]
pymesh = ["pandas", "chardet", "ftfy", "scipy", "plotly"]
abaqus = ["jj[pymesh]", "scipy"]
obsidian = ["pyyaml"]
dashboard = ["streamlit", "streamlit-aggrid", "plotly", "pandas", "numpy"]
dev = ["pytest", "pytest-cov"]
all = ["jj[pymesh,abaqus,obsidian,dashboard,dev]"]
```

### ダッシュボード（データ層は query に統合）

軽量な復活版。フレームワーク（PageComponent / SavedView / connectors）は持たない。
**データ層は `services/graph/query/` に統合**し、UI（Streamlit）だけが `services/dashboard/` に残る。

| 要素 | 場所 | 内容 |
|------|------|------|
| データ供給 | `services/graph/query/graph_query.py` | `GraphQuery` にデータ供給メソッドを統合（`get_go_table` / `get_array_plot_data` / `get_output_images` / `get_status_summary` 等）+ vocab/units 表示変換。UI非依存 |
| 画像グルーピング | `services/graph/query/images.py` | 画像ファイル名パラメータによる複合キーグルーピング |
| UIウィジェット | `services/dashboard/widgets.py` | `try_render_aggrid`（フィルタ/選択結果を `st.session_state["filtered_df"]` に共有） |
| Streamlitアプリ | `services/dashboard/app/` | `streamlit run services/dashboard/app/Home.py`（応力–ひずみ / 画像ギャラリー） |

スクリプトからは `import jj.services.graph.query` で参照する（`jj/__init__.py` が
トップレベル `services` を `jj.services` にエイリアス）。`pip install -e ".[dashboard]"`
でUI依存を導入。`GraphQuery` 自体はコア依存のみで動作する。

### default-config.yaml（最小版）

出荷時デフォルトは「ダッシュボードと `jj export` が動く最小限」のみ
（`path-type-map` の go_ ブロック / `ignore` / `export.csv-unit-format`）。
省略キーは `config/__init__.py` のスキーマ既定値が使われる。

---

## よくある作業の手順

### 作業完了時
1. README, roadmap を必要に応じて更新
2. featureごとにコミットを切り、pushする
