# jj

CAE業務データをグラフデータ化し、ObsidianやNeo4jなどの外部ソフトに渡すためのCLIコマンドモジュールです。jj内部でグラフデータを構築し、外部ソフトはあくまで出力先として扱う方針です。

## 目的と方針
- プロジェクトフォルダを解析してグラフデータを生成します。
- jjが保持するデータはテキスト形式（主にYAML）とし、`.jj/storage`に保存します。
- プロジェクトごとの語彙マッピングなどの設定は`.jj/config`に配置します（例: `vocab.yaml`, `.pyssh.yaml`）。
- ObsidianやNeo4jは外部ソフトとして扱い、jj内部で完結したグラフを出力する設計です。
- グラフデータの一時構築には `networkx` を採用します。

## コマンド構成
- グラフ管理（トップレベル）
  - `jj init`: 設定ファイルを初期化（`--overwrite`で上書き）
  - `jj parse`: プロジェクトをスキャンしてグラフデータを`.jj/storage/graph.yaml`に保存（`--full`で重い解析も含む、`-debug`でエラー時例外raise）
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
  - `jj r -- <command>` でコマンドを実行し、`.jj/storage/run` に実行ログを保存します。
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
- `.jj/storage/` : 解析で生成したグラフデータ（`graph.yaml`/`graph.json`）
- `.jj/config/` : プロジェクト固有の設定（例: `vocab.yaml`, `.pyssh.yaml`）
- `cli/` : CLIコマンド実装（argparseとCLI出力のみ担当）
  - `cli/graph.py` : `jj g` コマンドの実装
- `config/` : `.jj/config` や `.pyssh.yaml` を読み込む設定ローダー。
- `docs/status/` : 実装状況の記録（最大indexが最新）
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
- 実装状況は`docs/status/status-{index}.md`に詳細を記載し、常に最新のindexを参照します。

## 最新ステータス
- 2026-02-14 / **status-090 (v0.1.0区切り)**: v0.1.0レビュー・v0.2.0ロードマップ案策定。全statusファイル（jj: 001〜089、jjrv: 001〜060）を遡り開発フェーズの変遷を整理。開発運用の考察、CAE業務観点での機能評価、次フェーズ優先機能(F1〜F12)、v0.2.0ロードマップ案(M1〜M5)を策定。([status-090](docs/status/status-090.md))([レビュー文書](../docs/review/review-v0.1.0.md))
- 2026-02-14 / status-089: Abaqusコネクター作り込み（v0.1.0完成準備）。材料テーブル表示改善（タグ非表示・特性値フォーマット）。Elsetノード生成をメッシュごとに分離（mesh_sourceプロパティ追加）。ダッシュボードにメッシュ/Elset品質サマリー、ジョブサマリーページ追加。AbaqusKeywordParser追加（*キーワードNode化＋uses_keyword relation）。STAカットバック・インクリメント収集TODO追加。1002テストパス。([status-089](docs/status/status-089.md))
- 2026-02-14 / status-088: Abaqus固有ロジック分離・CacheProvider汎用化・requirements.txt廃止。CacheProviderを`load/save_plugin_data(namespace)`に汎用化。GraphStorageの`abq_cache`→`plugin_cache/{namespace}/`に変更。GraphServiceから`_read_inp_parameter_props`除去→AbaqusParameterParser（priority=15）として再実装。MeshInheritParser・submit.pyをAbaqusプラグインに移動。parse層からAbaqus固有エクスポート除去。1003テストパス。([status-088](docs/status/status-088.md))
- 2026-02-14 / status-087: パッケージセットアップ修正。エントリポイントを`main:main`→`services.cli:main`に変更（main.pyがpackages.findに含まれず解決不能だった）。chardet/ftfy/numpyをコア依存に移動（Abaqusプラグイン自動ロードでモジュールレベルimportされるため必須）。sharedパッケージをpackages.findに追加。756テストパス。([status-087](docs/status/status-087.md))
- 2026-02-14 / status-086: SDK外部化・プラグインレジストリ・Abaqus/Obsidianプラグイン分離。CacheProvider DI注入（GraphServiceコンストラクタ経由）。entry_points動的発見メカニズム実装（plugin_registry.py）。Abaqus/Obsidianロジックをservices/plugins/に集約しプラグインパッケージ化。pyproject.toml定義（entry_points + optional-dependencies）。コアからのハードコードimport除去。回帰なし。([status-086](docs/status/status-086.md))
- 2026-02-13 / status-085: API層リファクタリング・プラグイン化・CLI/Dashboard分離。ApiServiceクラス新設でAPI層のservices.service完全依存化。jj-sdkパッケージ新設（プラグイン化Phase 1）。CacheProviderプロトコル定義（Phase 2）。dashboard/serveランチャー分離。29テスト新規。([status-085](docs/status/status-085.md))
- 2026-02-13 / status-084: services/queryパッケージ新設。props条件式フィルタ(props.KEY.OPERATOR=VALUE)を汎用化しdict/Node両対応に。QueryServiceクラス追加。API依存をservices.service経由に変更。55テスト新規。([status-084](docs/status/status-084.md))
- 2026-02-13 / status-083: テストインポート移行(app.*→query.*/html_export.*)。app.pyラッパー関数8件削除。([status-083](docs/status/status-083.md))
- 2026-02-13 / status-082: 純粋関数モジュール（query.py/html_export.py/abaqus_query.py）の単体テスト65件追加。app.py後方互換ラッパー削除計画を文書化。services/query（jjレベル）昇格の設計検討を文書化。([status-082](docs/status/status-082.md))
- 2026-02-13 / status-081: ダッシュボード描画/クエリロジック分離。app.pyから純粋関数群をquery.py/html_export.py/abaqus_query.pyに抽出。([status-081](docs/status/status-081.md))
- 2026-02-13 / status-080: ダッシュボード機能拡張。配列プロット全モードにNG領域対応。物性比較CSVエクスポート追加。保存済みビューの動的追加・編集・削除UI追加。保存済みビューのスタンドアロンHTMLエクスポート機能追加（plotlyインライン化、テーブル・ステータス対応）。11テスト追加。([status-080](docs/status/status-080.md))
- 2026-02-13 / status-079: ダッシュボード機能拡張。配列プロットに保存済みビュー（array_plot型）とフィルタ連携を追加。物性一覧に比較機能（複数materialカーブ重ね書き）とgo_ノード使用関係表示を追加。プロットにNG領域塗りつぶし（矩形/カーブ、config駆動）とグループ結線（同一条件データ点を灰色点線で結線）を追加。16テスト追加。([status-079](docs/status/status-079.md))
- 2026-02-13 / status-078: CSV配列拡張（サブディレクトリCSV/ヘッダーなしCSV）・Excelダウンロード・REST API拡張（POST parse/プロパティ比較フィルター）。15テスト追加。([status-078](docs/status/status-078.md))
- 2026-02-12 / status-077: コネクタ固有config分離・プラグイン化分析。DashboardConfig.material_curve_columnsをconnector_configs辞書方式に移行（後方互換あり）。DashboardPageConnectorにconnector_key属性追加。AgGridヘルパーをwidgets.pyに切り出しコネクタ→app.pyの逆依存を解消。Abaqusコネクタを完全分離するための3フェーズ計画（SDK定義/キャッシュIF抽象化/動的発見）を分析・文書化。48テスト全パス（12件追加）。([status-077](docs/status/status-077.md))
- 2026-02-12 / status-076: ダッシュボードAbaqus依存コネクター分離。物性一覧ページとデータプロバイダーメソッド3つをservices/dashboard/connectors/abaqus.pyに分離。DashboardPageConnector基底クラス（__init_subclass__自動登録）で動的ページ追加を実現。汎用ページ（テーブル/カード/プロット等）はapp.py/data_provider.pyに保持。27テスト全パス。([status-076](docs/status/status-076.md))
- 2026-02-12 / status-074: CSVパース配列取り込み・ダッシュボード配列プロット・物性一覧。CsvArrayParser追加（has_output関係CSVのトークン差分でプレフィックス決定、配列データをRF.time/RF.RF3形式でGOノードに格納）。配列プロットページ（グリッド比較+個別ノード重ね書き）。物性一覧ページ（abaqus_materialテーブル+plastic/elastic等のラインプロット）。22テスト追加。([status-074](docs/status/status-074.md))
- 2026-02-12 / status-073: ギャラリーgroupby・float指数表示・vocab順カラム・default-config拡充。ギャラリーに条件/キーによるグループ表示機能追加（`daily:日付:キー`→キー正規化対応）。float値の指数表示（|x|>=1e4 or |x|<1e-2で小数2桁指数表示）をダッシュボード・CLIに適用。テーブル列・プロット軸・プロパティキーをvocab定義順でソート。AgGrid列幅を列名文字幅から自動設定。default-config.yamlを全設定のコメント・使用例付きに拡充、init時にコメント保持コピー。25テスト追加。([status-073](docs/status/status-073.md))
- 2026-02-12 / status-072: activeフィルタバグ修正・画像パス解決・保存済みビュー。activeフィルタのbool/文字列混在バグを修正（`_is_truthy`追加）。Obsidian daily note由来の画像パスをプロジェクトルート基準に変換（`daily_notes`ネストdict探索、`posixpath.normpath`正規化）。保存済みビュー機能追加（`SavedViewConfig`データクラス、config.yaml `saved-views`でフィルタ・プロット・ギャラリー条件を定義し表示順に一括表示）。`_matches_filters`のbool正規化。13テスト追加。([status-072](docs/status/status-072.md))
- 2026-02-12 / status-071: ダッシュボード機能拡張（config駆動カラム・フィルタ永続化・ギャラリーNxM・プロット軸設定）。テーブルビューにconfig.yaml駆動のカラム選択と優先順位指定（globパターン対応）。デフォルトフィルタ（active=true）と共有フィルタのsession_state永続化（ビュー間共有）。ギャラリーにプロパティ画像パス対応（Obsidian daily由来、キー別一覧）とNxMグリッドレイアウト。プロットビューにconfig駆動デフォルトX/Y軸とグリッドモード（スクリーンショット用）。DashboardConfigデータクラス追加。18テスト追加。([status-071](docs/status/status-071.md))
- 2026-02-12 / status-069: ダッシュボード機能拡張（AgGrid・画像ギャラリー・自動リフレッシュ）。テーブルビューをAgGrid対応（チェックボックス選択・フィルタ・ソート・ページネーション、フォールバック付き）。ギャラリーページ追加（has_output関係の画像を5列グリッド表示、フォーマットフィルタ・最大表示数制御）。graph.yaml変更検知・自動リフレッシュ（mtime監視、手動/自動リフレッシュ、3-60秒間隔設定）。streamlit-aggrid依存追加。734テストパス（+13件追加）、リグレッションなし。([status-069](docs/status/status-069.md))
- 2026-02-12 / status-068: Streamlitダッシュボード・REST API実装（Phase 2.5 D2/D3）。`jj dashboard`でStreamlitアプリ起動（テーブル/カード/プロット/ステータスの4ビュー）。`jj serve`でFastAPI REST APIサーバー起動（9エンドポイント、OpenAPIドキュメント自動生成）。CLIにdashboard/serveコマンド追加。streamlit/plotly/fastapi/uvicorn依存追加。721テストパス（+22件追加）、リグレッションなし。([status-068](docs/status/status-068.md))
- 2026-02-12 / status-067: レガシーコード削除・Vault設定config.yaml駆動化・CLI凍結整理。旧メソッド(export_obsidian/export_data/export_neo4j/export_dashboard_json)と対応データクラス4件を完全削除。graph/__init__.pyの後方互換re-export(parse_sta_file等)を削除しテストを正規パスに修正。Obsidian Vault設定をconfig.yaml駆動化(ObsidianVaultConfigデータクラス追加)。submit/files/旧互換フラグをPhase 3まで凍結マーク。699テストパス、リグレッションなし。([status-067](docs/status/status-067.md))
- 2026-02-12 / status-066: Obsidian Vault自動セットアップ・GraphMLエクスポーター凍結。`jj export --target obsidian`実行時に`.obsidian/`ディレクトリを自動生成（初回のみ、既存Vaultは変更しない）。app.json/community-plugins.json/core-plugins-migration.jsonの推奨構成を自動セットアップ。CLI出力にVault初期化案内追加。GraphMLエクスポーターは使用していないため凍結。699テストパス（+6件追加）。([status-066](docs/status/status-066.md))
- 2026-02-11 / status-065: エクスポートロジック統一・CLIレジストリディスパッチ・Obsidianプラグイン構成。CLI `_run_export()`を if/elif チェーンからレジストリ経由統一ディスパッチに変更。AbstractExporter.format_cli_result()メソッド追加（全6エクスポーターにオーバーライド実装）。GraphCommandService.export_unified()統一パイプライン追加。Obsidianサマリーノート（jj-summary.md）自動生成。Obsidian推奨プラグイン構成ドキュメント（Dataview/DB Folder/Templater等）。693テストパス（+12件追加）。([status-065](docs/status/status-065.md))
- 2026-02-11 / status-064: エクスポートロジック統一・AbstractExporter全形式対応・3層Canvas。ObsidianExporter/Neo4jExporter/CypherExporter/DashboardJsonExporterをAbstractExporterサブクラスとして実装。全6形式がレジストリに登録され`get_exporter_for_format()`で統一取得可能。GraphCommandService.export_by_format()で統一呼び出し。Obsidian Canvas 3層（go-material-elset）関係グラフ生成。graph_command.pyの壊れたNeo4jインポートパス修正。117テストパス（+11件追加）。([status-064](docs/status/status-064.md))
- 2026-02-11 / status-063: Export基盤整備・キャッシュクリーンアップ・Obsidian Elset-材料可視化。AbstractExporter基底クラス定義（__init_subclass__自動登録）、CSV/JSONエクスポートをexport/connectors/に移動、Elset品質統計CSVエクスポート対応、ABQDataキャッシュ自動クリーンアップ（max_age_days/max_count）、Obsidian Dataviewクエリ（elset/material/goノード）、Obsidian Canvas elset-materialマップ生成。670テストパス、21スキップ。([status-063](docs/status/status-063.md))
- 2026-02-11 / status-062: Elset品質統計・ABQDataキャッシュ永続化・設定駆動include探索。Elsetごとの品質統計（extract_elset_quality_stats）、config-driven include search depth（include-search-depth設定）、ABQData永続化キャッシュ（pickle/.jj/storage/abq_cache/）、軽量パーサーキャッシュ展開（IncludesRelationParser/JsonPropertyParser）、Obsidian version_diff/elset可視化改善。649テストパス、21スキップ。([status-062](docs/status/status-062.md))
- 2026-02-11 / status-061: パーサーキャッシュ拡張 & タイムスタンプ差分パース。ABQDataキャッシュをAbaqusMeshParserに展開（mesher()にcached_abq_dataパラメータ追加）、タイムスタンプ差分による増分パース（parse_timestamps.json永続化、is_file_modified()判定、重いパーサーの未変更ファイルスキップ）、pymeshテスト追加（modules/pymesh使用）。641テストパス、21スキップ。([status-061](docs/status/status-061.md))
- 2026-02-11 / status-060: パーサーキャッシュ基盤実装、DashboardDataProvider完全実装。ABQDataキャッシュをAbaqusDiffParserで使用開始。([status-060](docs/status/status-060.md))
- 2026-02-11 / status-059: *SURFACE INTERACTION下の材料サブキーワード（*DAMAGE INITIATION等）パースエラー修正。MaterialPropertyReadComponentでcurrent_material未設定時にRuntimeErrorを投げず紐付けスキップに変更。2ファイル同一修正、テスト更新。599テストパス、リグレッションなし。([status-059](docs/status/status-059.md))
- 2026-02-11 / status-058: Obsidian全ノード出力（index_group/version_diff含む全メタノードをmd出力）、include解決ロジック改善（file親→cwd→再帰N階層探索でold/フォルダ対応）、elsetノードにuses_material relation追加。594テストパス、リグレッションなし。([status-058](docs/status/status-058.md))
- 2026-02-11 / status-057: CLI→Service分離完了。RunCommandService新規作成、SubmitServiceにlist_jobs()追加、cli/__init__.pyのモジュールレベル副作用除去（SSH設定遅延初期化）。FastAPIサーバー化準備完了。600テストパス、リグレッションなし。([status-057](docs/status/status-057.md))
- 2026-02-10 / status-055: cli/graph.pyからビジネスロジックを分離しservices/service/graph_command.pyに移動。GraphCommandServiceクラス新規作成。CLIアーキテクチャルール徹底。599テストパス、リグレッションなし。([status-055](docs/status/status-055.md))
- 2026-02-10 / status-049: エクスポート機能強化（CSV単位系・カラム選択・キー順保持）、JSONプロパティ"."繋ぎ平坦化、JSONファイル名vocab置換（_区切り）、MeshInheritParser新規追加、ダッシュボード要件定義（post.py分析）。50テストパス、14テスト追加。([status-049](docs/status/status-049.md))
- 2026-02-10 / status-048: vocab.yamlマージ修正、-id/-v vocab対応、Obsidian frontmatter修正、CSV UTF-8 BOM、JSON --flatten、info -active、parse --full/--lite。480テストパス、13テスト追加。([status-048](docs/status/status-048.md))
- 2026-02-10 / status-047: 共通選択コマンド（-id 1..3範囲展開）、jj info拡張（-all/-prop/-type）、CSVエクスポート改善（プロパティ平坦化・-prop絞り込み）、VocabFinalizer一括置換（パーサー追加プロパティの翻訳漏れ解消）。テスト467件パス、20スキップ。([status-047](docs/status/status-047.md))
- 2026-02-10 / status-046: warning/error重複排除（数値正規化）、cpu_time/wallclock_time最終値取得修正、jj info YAML出力化、results/ info-only（Node化除外）、Obsidian export directory実ファイルリンク除外、.dat warning/error抽出追加。テスト445件パス、20スキップ。([status-046](docs/status/status-046.md))
- 2026-02-10 / status-045: idx→条件統一、CLIビジネスロジックのservices.service分離。テスト443件パス、20スキップ。([status-045](docs/status/status-045.md))
- 2026-02-10 / status-044: NO_NODE_EXTENSIONS(.odb/.odb.json)追加、materialパーサーvocab/token-key-map対応、ディレクトリ階層contains relation追加、JsonPropertyParser新規追加（go_*.inpへのJSON key-value割り当て）、iterate_directories()のnon_file_nodes反映。テスト439件パス、20スキップ。([status-044](docs/status/status-044.md))
- 2026-02-10 / status-043: Phase R4-R6完了（services構造リファクタリング完了）。ObsidianConnectorをexport層へ移動、graph/__init__.pyの旧メソッド削除（2026行→510行）、全テスト新パイプライン対応。pymeshインポートパスをmodules/に修正。テスト443件パス、0失敗。MR（構造改革マイルストーン）達成。([status-043](docs/status/status-043.md))
- 2026-02-09 / status-042: Phase R1-R3実装完了。ProjectGraph型定義（project_graph.py）、AbstractFileParser.__init_subclass__自動登録パターン確立、graph/__init__.pyから16パーサーサブクラスに分解。parse()パイプラインでtest_asset1を丸ごと解析（47ノード、65リレーション）。統合テスト29件パス。specs/02-parser.md・specs/07-adapter.mdを新アーキテクチャに更新。([status-042](docs/status/status-042.md))
- 2026-02-09 / status-041: services構造改革に伴うロードマップ根本改変。Phase Rを新設（抽象パーサーパターン・ProjectGraph型・graph/__init__.py分解）、完了済みAbaqusグラフ機能をM1.5として整理、旧アダプター層をparseコネクターに再定義。detail.md・README.mdのディレクトリ構成を新構造に更新。([status-041](docs/status/status-041.md))
- 2026-02-09 / status-040: pymesh移動・jj info強化・材料名ケース保持・credential管理。pymeshをservicesに移動しシステムpymesh競合解消、jj infoメッシュ統計展開表示・Windowsパスparse対応、材料名/elset名の元ケース保持、root directory命名のconfig対応(project-name)、Neo4j認証情報の暗号化保存(`jj credential set/show/delete`)。テスト396件パス+20スキップ、12件追加。([status-040](docs/status/status-040.md))
- 2026-02-09 / status-039: parseタグ振り・verbose_name改善・Node方針変更。verbose_name由来タグ生成、version/バージョンキー統一、token_key_map verbose_name修正(値のみ)、material.inp材料タグ、elset Node化、.sta/.msg/.dat Node化廃止(情報のみinpに集約)、pymeshインポート修正、root directory Node化。テスト178件パス+18スキップ、20件追加。([status-039](docs/status/status-039.md))
- 2026-02-09 / status-038: parse export修正（pymesh相対パスインポート、タグ`_`分割、includes相対パス化、directoryノードroot.directoryタグ）+ jjrv統合ロードマップ整備。テスト363件パス+20スキップ、リグレッションなし。([status-038](docs/status/status-038.md))
- 2026-02-08 / status-037: Neo4jエクスポート実装（Phase N1+N2）。shared/パッケージ（スキーマ契約・型定義・接続設定）、Neo4j Docker設定、Neo4jConnector（直接書き込み+Cypherファイル出力）、CLI `--target neo4j/cypher`追加。テスト71件追加（69パス+2スキップ）、既存294件リグレッションなし。([status-037](docs/status/status-037.md))
- 2026-02-08 / status-036: jjrv統合設計。jjrv（旧mat-db）をNeo4j経由で統合する方針策定。submoduleアクセス不可のため一時モノレポ方式採用。shared/パッケージでデータ型共通化、Phase N1-N5の実装計画策定。jjrvの技術スタック（Next.js 15/SQLite）を確認、SQLite+Neo4j併用を推奨。([status-036](docs/status/status-036.md))
- 2026-02-08 / status-035: ダッシュボードアーキテクチャ設計。jj側Streamlit（即時一覧）+ jjrv側Next.js（高機能レンダリング）の役割分担決定。Phase 2.5・M2.5追加、仕様書09-dashboard.md作成。([status-035](docs/status/status-035.md))
- 2026-02-07 / status-034: メッシュキーワード要約。diff/propertyでNode/Element/Nset/Elsetの生データを統計情報（節点数、座標範囲、メッシュ数、メッシュサイズ、ねじれ角、ID数）に自動置換。トップレベルメッシュデータのdiff比較追加。テスト294件パス（+22件）。([status-034](docs/status/status-034.md))
- 2026-02-07 / status-033: Daily紐付け強化（[[O-file]]:key:value記法）、jj info強化（-id/-v/複数指定/-props）、jj diffコマンド追加、verbose_name登録、CSV/JSONエクスポート、elset/材料名プロパティ追加、Obsidianタグ出力強化。テスト272件パス（+12件）。([status-033](docs/status/status-033.md))
- 2026-02-06 / status-032: CLIコマンド省略化（jj g→jj）、jj infoコマンド追加、includeファイルproperty伝搬、前バージョンとのキーワードブロック差分、notes/daily日報解析、Obsidianエクスポートwarning/diff表示強化。テスト260件パス（+18件）。([status-032](docs/status/status-032.md))
- 2026-02-06 / status-031: abaqus material読み取りソースをmaterial系/go系.inpに限定、汎用ディレクトリノード（reports等）のグラフ追加、pymeshパーサーの末尾カンマ・*include FileNotFoundError対応。テスト242件パス（+14件）。([status-031](docs/status/status-031.md))
- 2026-02-06 / status-030: props命名統一（vocab変換を正）、.baseからfile.links削除、token-key-map設定追加、pymesh統合基盤構築、材料割り当て関係のグラフ化。テスト228件パス（+22件）。([status-030](docs/status/status-030.md))
- 2026-02-06 / status-029: Obsidianエクスポート改善。プロパティ型変換（int/float/bool）、.baseフィルター簡素化（folder条件のみ）、orderにプロパティ積集合追記、同一タイプ.base生成、props/bases上書き前提化。テスト206件パス（+21件）。([status-029](docs/status/status-029.md))
- 2026-02-06 / status-028: Obsidianエクスポート改善。frontmatterにファイル情報property化（node_type, node_format, file）。バージョンリンク構造改善（最新ver→.base、非最新→次ver）、-group.md廃止。結果ファイル(sta,msg)属性をAbaqusインプットに集約。active属性自動判定、*PARAMETER/**propsプロパティ読み取り。テスト185件パス（+15件）。([status-028](docs/status/status-028.md))
- 2026-02-06 / status-027: Obsidianエクスポート構造改善。props/inp/→props/へフラット化。.base.md→.base（YAMLフィルター形式）に変更、旧内容は-group.mdとしてprops配下に配置。Abaqusコネクタ拡張: .msg解析実装、read_inp()テスト40件追加。テスト170件パス（+40件）。([status-027](docs/status/status-027.md))
- 2026-02-06 / status-026: `jj g parse`パスパース・型判定バグ修正。`_match_path_pattern`の`./`プレフィックス対応・ディレクトリパターン対応・`**go`basename比較追加。`DEFAULT_EXTENSIONS`にconfigのfile-relations拡張子を自動マージ。フォルダNode構築のパス比較をWindows対応強化。テスト126件パス（+34件）。([status-026](docs/status/status-026.md))
- 2026-02-05 / status-025: グラフ機能の作り込み（Phase 2）。ロードマップ改定（notes削除、graph最優先化）。Abaqusコネクター4機能実装: has_output関係、contains関係、abaqus_material解析、sta解析。テスト92件パス。([status-025](docs/status/status-025.md))
- 2026-02-05 / status-024: CLIの大幅スリム化。`jj g notes`と`jj n`を完全廃止、`file_utils.py`を`file_parse.py`に統合。cli/__init__.pyを1752行→745行に削減（57%削減）。([status-024](docs/status/status-024.md))
- 2026-02-05 / status-023: CLIリファクタリング。cli/__init__.pyからビジネスロジック分離（services/parse/file_utils.py, services/notes/）。`jj n`を`jj g notes`に統合。テスト42件パス。([status-023](docs/status/status-023.md))
- 2026-02-05 / status-022: graph機能の作り込み。FileRelationsConfig追加（拡張子設定ファイル化）、derived_from関係構築、日付パース機能、path-type-map評価順序改善、includes関係構築。テスト38件パス。([status-022](docs/status/status-022.md))
- 2026-02-05 / status-021: graph機能の確実化。暗黙のタイプ/index/version認識、入力-結果ファイル関係（result_of）構築、バージョンソート修正。テストコード27件追加。([status-021](docs/status/status-021.md))
- 2026-02-05 / status-020: `jj g parse`の拡張（サブバージョン関係・グループ関係構築）、設定機能の大幅拡充（path-type-map, path-property-map, ignore等）、Obsidian記法対応の改善、`jj g init`サブコマンド追加。([status-020](docs/status/status-020.md))
- 2026-02-05 / status-019: `jj g` (graph) コマンドを実装。GraphService、Obsidianコネクタを独立モジュール化。relative_toのWindows対応バグ修正。O-プレフィックス処理のテスト追加。([status-019](docs/status/status-019.md))

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
