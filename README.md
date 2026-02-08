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
  - `jj parse`: プロジェクトをスキャンしてグラフデータを`.jj/storage/graph.yaml`に保存
  - `jj show`: グラフデータを表示（`--summary`でサマリーのみ）
  - `jj export --target obsidian`: Obsidian向けにエクスポート
  - `jj export --parse`: parseしてからexport
  - `jj info <ファイル名>`: ファイルのproperty/relationを表示（-id, -v, -propsオプション対応）
  - `jj diff <file1> <file2>`: ファイル間の差分を表示（Abaqusキーワードブロック差分対応）
  - `jj export --target csv/json`: ノード属性をCSV/JSON形式でエクスポート
  - `jj g ...`: 旧コマンド（互換性維持）
- `jj f` (file)
  - ファイルテンプレート生成、関係を保持したフォルダ移動、リネーム、サーバー送受信などを担当します。
- `jj r` (run)
  - CAEソフトでの計算実行やプリ/ポスト処理の実行履歴、指定オプションのログ取得を担います。
  - `jj r -- <command>` でコマンドを実行し、`.jj/storage/run` に実行ログを保存します。
  - 実行ログには所要時間/実行ユーザー/ホスト情報を含めます。
  - 既存のsubmit機能（Abaqusのサーバー投入）を`run`機能としてリファクタリングする方針です。

## データモデル
- **Node**: `id: int`, `type: str`, `name: str`, `format: str`, `properties: dict[str, Any]`
- **Relation**: `id: int`, `label: str`, `node1_id: int`, `node2_id: int`

例: タグ付け
- `Node(type=タグ, name=sample)`
- `Relation(label=tagged, node1_id=1, node2_id=2)`

## 入力データの扱い
- 対象はバイナリ、テキスト、フォルダなど多様です。
- ソフト固有フォーマットの拡張を見据え、**アダプター**の概念を導入し、機能を独立させます。
- 計算inpは拡張子やフォルダで表現されることがあり、ソフト依存の解析が必要です。
- 現状は以下を計算inpとして集計しています。
  - 指定拡張子を持ち、`go_`で始まるファイル名
  - 例: Abaqusなら`.inp`、Fluentなら`.cas.h5`、Dynaなら`.k`/`.key`/`.dat`
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
  - `services/graph/` : グラフデータの生成・管理（GraphService）
  - `services/connectors/` : 外部ツールへのエクスポート（ObsidianConnector等）
  - `services/parse/file_parse.py` : FileParse/ObsidianFileParse + レガシー関数
  - `services/storage/` : グラフデータの永続化（GraphStorage）
- `jj_types/` : Pydanticモデル
- `tests/` : pytestテスト
- `assets/` : テストデータ/サンプル

## 運用メモ
- CodexとClaude Codeの2交代制を前提に、引き継ぎ可能な形で実装状況を記録します。
- 実装状況は`docs/status/status-{index}.md`に詳細を記載し、常に最新のindexを参照します。

## 最新ステータス
- 2026-02-08 / status-035: ダッシュボードアーキテクチャ設計。jj側Streamlit（即時一覧）+ mat-db側Next.js（高機能レンダリング）の役割分担決定。Phase 2.5・M2.5追加、仕様書09-dashboard.md作成。([status-035](docs/status/status-035.md))
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
- [ダッシュボード仕様書](docs/specs/09-dashboard.md)
- [実装詳細](docs/detail.md)
- [ロードマップ](docs/roadmap.md)
- [services/README](services/README.md)
- [jj_types/README](jj_types/README.md)
- [tests/README](tests/README.md)
- [assets/README](assets/README.md)
