# jj

CAE業務データをグラフデータ化し、ObsidianやNeo4jなどの外部ソフトに渡すためのCLIコマンドモジュールです。jj内部でグラフデータを構築し、外部ソフトはあくまで出力先として扱う方針です。

## 目的と方針
- プロジェクトフォルダを解析してグラフデータを生成します。
- jjが保持するデータはテキスト形式（主にYAML）とし、`.j2/storage`に保存します。
- プロジェクトごとの語彙マッピングなどの設定は`.j2/config`に配置します（例: `vocab.yaml`, `.pyssh.yaml`）。
- ObsidianやNeo4jは外部ソフトとして扱い、jj内部で完結したグラフを出力する設計です。
- グラフデータの一時構築には `networkx` を採用します。

## コマンド構成
- グラフ管理（トップレベル）
  - `jj init`: 設定ファイルを初期化（`--overwrite`で上書き）
  - `jj parse`: プロジェクトをスキャンしてグラフデータを`.j2/storage/graph.yaml`に保存（`--full`で重い解析も含む、`-debug`でエラー時例外raise）
  - `jj show`: グラフデータを表示（`--summary`でサマリーのみ）
  - `jj export --target obsidian`: Obsidian向けにエクスポート
  - `jj export --parse`: parseしてからexport
  - `jj info <ファイル名>`: ファイルのproperty/relationを表示（-id, -v, -all, -type, -prop, -props, -activeオプション対応）
  - `jj diff <file1> <file2>`: ファイル間の差分を表示（Abaqusキーワードブロック差分対応）
  - `jj export --target csv/json`: ノード属性をCSV/JSON形式でエクスポート（`--flatten`でJSON平坦化、CSV UTF-8 BOM付き、`--unit-format`で単位表示形式、`--columns`でカラム選択）
  - `jj export --target neo4j`: Neo4jデータベースにグラフをエクスポート
  - `jj export --target cypher`: Cypherクエリファイルとしてエクスポート（Neo4j不要）
  - `jj credential set`: Neo4j等の認証情報を暗号化して保存
  - `jj credential show`: 保存済み認証情報を表示（マスキング付き）
  - `jj credential delete`: 保存済み認証情報を削除
  - `jj dashboard`: Streamlitダッシュボードを起動（`--port`でポート指定、`--no-browser`でブラウザ非起動）
  - `jj serve`: REST APIサーバーを起動（FastAPI + uvicorn、`--port`/`--host`でバインド設定）
  - `jj g ...`: 旧コマンド（互換性維持）
- `jj r` (run)
  - CAEソフトでの計算実行やプリ/ポスト処理の実行履歴、指定オプションのログ取得を担います。
  - `jj r -- <command>` でコマンドを実行し、`.j2/storage/run` に実行ログを保存します。
  - 実行ログには所要時間/実行ユーザー/ホスト情報を含めます。
- 凍結中（Phase 3まで）
  - `jj f` (file): ファイルテンプレート生成、関係を保持したフォルダ移動、リネーム、サーバー送受信
  - submit/list/check: ジョブ投入・構文チェック（SubmitService経由）
  - 旧互換フラグ: --use-gpu, --no-background, --jcf, --abq-version等

## データモデル
- **Node**: `id: int`, `type: str`, `name: str`, `format: str`, `properties: dict[str, Any]`
- **Relation**: `id: int`, `label: str`, `node1_id: int`, `node2_id: int`

例: タグ付け
- `Node(type=タグ, name=sample)`
- `Relation(label=tagged, node1_id=1, node2_id=2)`

## インストール

### 前提条件
- Python >= 3.10

### コアのみ（最小構成）

```bash
# 開発用（ソースを直接参照）
pip install -e .

# 通常インストール
pip install .
```

コア依存: pydantic, pyyaml, networkx, chardet, ftfy, numpy

`jj --help` / `jj init` / `jj parse` / `jj show` / `jj info` / `jj diff` / `jj export --target csv/json/obsidian/cypher` が使用可能。

### 個別オプション

用途に応じて必要なグループのみ追加インストールできる。

```bash
# Abaqusプラグイン拡張（メッシュ品質解析 pymesh / データ分析）
pip install -e '.[abaqus]'      # +pandas, scipy

# ダッシュボード（jj dashboard）
pip install -e '.[dashboard]'   # +streamlit, streamlit-aggrid, plotly

# REST API（jj serve）
pip install -e '.[api]'         # +fastapi, uvicorn

# Neo4jエクスポート（jj export --target neo4j）
pip install -e '.[neo4j]'       # +neo4j

# SSH操作（リモートジョブ投入）
pip install -e '.[ssh]'         # +paramiko

# 開発・テスト
pip install -e '.[dev]'         # +pytest, pytest-cov, httpx
```

### 複数グループの同時指定

```bash
# Abaqus + ダッシュボード
pip install -e '.[abaqus,dashboard]'

# Abaqus + API + SSH（解析ワークフロー一式）
pip install -e '.[abaqus,api,ssh]'
```

### フルインストール（全依存）

```bash
pip install -e '.[all]'
```

### テスト実行

```bash
pip install -e '.[dev]'         # dev依存が必要
pytest                          # jj/ディレクトリ内で実行

# API / ダッシュボードのテストも含める場合
pip install -e '.[all]'
pytest
```

### 依存グループ一覧

| グループ | 追加パッケージ | 用途 |
|----------|----------------|------|
| (コア) | pydantic, pyyaml, networkx, chardet, ftfy, numpy | 基本CLI・グラフ構築 |
| `abaqus` | pandas, scipy | メッシュ品質解析・データ分析 |
| `obsidian` | (pyyamlはコアに含む) | Obsidianプラグイン |
| `dashboard` | streamlit, streamlit-aggrid, plotly | Streamlitダッシュボード |
| `api` | fastapi, uvicorn | REST APIサーバー |
| `neo4j` | neo4j | Neo4jデータベース連携 |
| `ssh` | paramiko | SSHリモート操作 |
| `dev` | pytest, pytest-cov, httpx | テスト・開発 |
| `all` | 上記全て | フルインストール |

## 入力データの扱い
- 対象はバイナリ、テキスト、フォルダなど多様です。
- ソフト固有フォーマットの拡張を見据え、**アダプター**の概念を導入し、機能を独立させます。
- 計算inpは拡張子やフォルダで表現されることがあり、ソフト依存の解析が必要です。
- 現状は以下を計算inpとして集計しています。
  - 指定拡張子を持ち、`go_`で始まるファイル名
  - 例: Abaqusなら`.inp`、Fluentなら`.cas.h5`、Dynaなら`.k`/`.key`/`.dat`
- 共通選択記法: `jj {command} -id 1 2 3 -v 1 2 -type Abaqusインプット`。`-id`/`-v`では`1..3`の範囲展開に対応。
- ファイル/フォルダ名は `go_prop1_v1_idx1` のようにアンダースコア区切りでpropsを記載する。
- propsは `文字列+数値` または `文字列=数値` を満たすものを採用し、それ以外はtagとして扱う。
- versionが取得できない場合は旧式の `.v1` 形式も補完対象とする。

## ディレクトリ
- `.j2/storage/` : 解析で生成したグラフデータ（`graph.yaml`/`graph.json`）
- `.j2/config/` : プロジェクト固有の設定（例: `vocab.yaml`, `.pyssh.yaml`）
- `cli/` : CLIコマンド実装（argparseとCLI出力のみ担当）
  - `cli/graph.py` : `jj g` コマンドの実装
- `config/` : `.j2/config` や `.pyssh.yaml` を読み込む設定ローダー。
- `docs/roadmap.md` : 今後の計画
- `docs/detail.md` : 実装詳細と仕様リンク
- `services/` : CLI向けサービス群（詳細は各README）
  - `services/graph/` : プロジェクトツリーのスキャンと初期グラフ生成
  - `services/graph/storage/` : グラフデータの永続化（GraphStorage）
  - `services/parse/` : グラフへのtag/property/relation付与
    - `services/parse/base.py` : AbstractFileParser 抽象基底クラス
    - `services/parse/file_parse.py` : FileParse/ObsidianFileParse（レガシー）
    - `services/parse/connectors/abaqus/` : Abaqus INP読み込み、メッシュ統計、差分比較
    - `services/parse/connectors/obsidian/` : Obsidianエクスポート、daily連携
  - `services/dashboard/widgets.py` : 共有UIヘルパー（AgGrid等、コネクタからも利用）
  - `services/query/` : 汎用フィルタ/ソート層（props条件式フィルタ、vocab順ソート）
  - `services/export/connectors/` : 外部ツールへのエクスポート（Neo4jConnector等）
  - `services/api/` : REST APIサーバー（FastAPI、jj serve）
  - `services/run/` : スクリプトラッパー（jj r）
  - `services/service/` : サービス横断オーケストレーション（ApiService/QueryService等）
  - `services/sdk/` : プラグイン開発用公開インターフェース（jj-sdk）
    - `services/sdk/cache.py` : CacheProviderプロトコル（GraphStorage抽象化）
    - `services/sdk/plugin_registry.py` : プラグイン動的発見・登録メカニズム（entry_points）
  - `services/plugins/` : プラグインパッケージ
    - `services/plugins/abaqus/` : Abaqusプラグイン（INP解析・メッシュ統計・差分比較・物性一覧）
    - `services/plugins/obsidian/` : Obsidianプラグイン（Daily Note解析・Obsidianエクスポート）
  - `services/lib/` : 薄いユーティリティ（credentials, file等）
- `shared/` : jjrvとの共有パッケージ（Neo4jスキーマ契約、型定義、接続設定）
- `shared/tests/test_asset1/` : jj/jjrv共通テストアセット（Abaqusプロジェクト）
- `neo4j/` : Neo4j Docker設定と初期化スクリプト
- `jj_types/` : Pydanticモデル
- `tests/` : pytestテスト
- `assets/` : テストデータ/サンプル

## 運用メモ
- CodexとClaude Codeの2交代制を前提に、引き継ぎ可能な形で実装状況を記録します。
- v0.2.0以降のstatusファイルは `docs/status/status-{index}.md`（ルート共有）に記載します。
- v0.1.0のstatus（jj: 001〜090、jjrv: 001〜060）は [v0.1.0 statusインデックス](../docs/status/status-index-v0.1.0.md) および `docs/status/archive-v0.1.0/` にアーカイブ済みです。

## v0.1.0 開発サマリー
- テスト1,002件、パーサー16+クラス、エクスポーター6種
- Phase 0（基盤）→ Phase 1（graph）→ Phase R（構造改革）→ Phase 2（拡充）→ Phase 2.5（ダッシュボード）→ Phase P（プラグイン化）
- 詳細は [v0.1.0レビュー](../docs/review/review-v0.1.0.md) を参照

## 仕様リンク
- [機能ドメイン別仕様書](docs/specs/README.md)
- [出力層仕様書（Obsidianプラグイン構成含む）](docs/specs/08-export.md)
- [ダッシュボード仕様書](docs/specs/09-dashboard.md)
- [ダッシュボード要件定義](docs/specs/11-dashboard-requirements.md)
- [DB統合設計書](docs/specs/10-db-integration.md)
- [実装詳細](docs/detail.md)
- [ロードマップ](docs/roadmap.md)
- [services/README](services/README.md)
- [jj_types/README](jj_types/README.md)
- [tests/README](tests/README.md)
- [assets/README](assets/README.md)
