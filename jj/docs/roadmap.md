[READMEへ戻る](../README.md)

# ロードマップ

本ドキュメントは、jjプロジェクトの実装計画を機能ドメイン別に整理し、優先順位と実装フェーズを明確化したものです。

詳細な仕様は [機能ドメイン別仕様書](./specs/README.md) を参照してください。

---

## アーキテクチャ概要（2026-02-09 構造改革）

### 背景

従来の`services/graph/__init__.py`にparse・graph構築・コネクター連携のすべてが集中し、以下の問題が深刻化していた:

- parseロジックが増えるたびにgraph/__init__.pyが肥大化
- parseロジック同士の関係性が不明瞭で背反が続出
- コネクター（Abaqus/Obsidian）の境界が曖昧

### 新構造

```
services/
├── graph/                  # プロジェクトツリーのスキャンと初期グラフ生成
│   ├── __init__.py         # ProjectGraph 生成ロジック
│   └── storage/            # グラフデータの永続化(.jj/storage/)
├── parse/                  # グラフへのtag/property/relation付与
│   ├── base.py             # AbstractFileParser 抽象基底クラス
│   ├── file_parse.py       # FileParse/ObsidianFileParse（レガシー）
│   └── connectors/         # ソフト固有のparse/exportロジック
│       ├── abaqus/         # Abaqus INP読み込み、メッシュ統計、差分比較
│       │   ├── __init__.py # ABQData, read_inp, diff等
│       │   └── mesh.py     # pymesh統合メッシュ品質
│       └── obsidian/       # Obsidianエクスポート、daily連携
│           ├── __init__.py # ObsidianConnector, export_graph等
│           └── daily.py    # DailyNote解析
├── export/                 # グラフの外部出力（ローカル以外）
│   └── connectors/
│       └── neo4j.py        # Neo4jConnector
├── run/                    # スクリプトラッパー
├── service/                # サービス横断オーケストレーション
├── cli/                    # CLI（serviceからのみimport）
└── lib/                    # 薄いユーティリティ
    ├── credentials.py      # 秘匿情報管理
    ├── selection.py         # 共通選択ユーティリティ（範囲展開等）
    └── file/               # SSH・一括rename
```

### 抽象パーサーパターン

```python
parser_list = []

class AbstractFileParser(ABC):
    def __init_subclass__(cls):
        parser_list.append(cls)

    @abstractmethod
    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        """個々のparseロジックに従いグラフを更新"""

def parse(graph: ProjectGraph) -> ProjectGraph:
    """全パーサーを順次適用"""
    for parser_cls in parser_list:
        graph = parser_cls().apply(graph)
    return graph
```

### ProjectGraph型

```python
@dataclass
class ProjectFile:
    path: Path
    parent_directory: ProjectDirectory

@dataclass
class ProjectDirectory:
    path: Path
    parent_directory: ProjectDirectory | None
    child_directories: list[ProjectDirectory]
    files: list[ProjectFile]

@dataclass
class ProjectGraph:
    nodes: dict[int, Node]
    relations: list[Relation]

    def iterate_directories(self) -> Iterator[ProjectDirectory]:
        """ツリー構造をProjectDirectory/ProjectFileに変換してiterate"""
```

### テストデータ

`shared/tests/test_asset1/` にAbaqusプロジェクトのテストアセットを配置。jj/jj-db双方でテストデータとして利用する。

---

## 完了

### コアデータモデル層

- [x] `Node`, `Relation`, `GraphModel` の型定義（Pydantic）
- [x] `GraphStorage` の基本実装（YAML保存・読込）
- [x] 基本的なCRUD操作

### パーサー層

- [x] `FileParse` 基底クラスの実装
- [x] 命名規則の解析（index, version, props, tags）
- [x] 拡張子判定（複数ドット対応）
- [x] ファイルタイプ判別（接頭辞による）
- [x] `ObsidianFileParse` の実装
- [x] パス変換機能

### runコマンド層

- [x] `jj r -- <command>` の基本実装
- [x] 実行ログの保存（`.jj/storage/run/`）
- [x] メタ情報の記録（duration, user, host, script_path）
- [x] 単体テスト

### 設定管理層（Phase 1完了）

- [x] `vocab.yaml` の読込機能
- [x] `extensions.yaml` の読込機能
- [x] `prefixes.yaml` の読込機能
- [x] 各設定モデルの定義（`ExtensionsConfig`, `PrefixesConfig`）
- [x] `.jj/config/` の初期化処理
- [x] `AppConfig` への統合

### runコマンド層拡張（Phase 1完了）

- [x] コメント記法（`# props start` - `# props end`）の実装
- [x] `sys.argv` 解析の実装（Python）
- [x] Bash変数（`$1`, `$2`）の解析
- [x] 実行前後のスナップショット機能
- [x] 差分検出ロジック・除外ルール
- [x] `Relation(label=generated)` の自動生成

### Abaqusグラフ機能（Phase 2大部分完了）

- [x] 同一ファイルタイプの関連付け（has_output, same_index_group）
- [x] フォルダベースの関連付け（contains）
- [x] material.inpの高度な解析（abaqus_material Node化）
- [x] 解析結果ファイルの解析（analysis_status）
- [x] .msgファイルのERROR/WARNING抽出
- [x] 結果ファイル属性のAbaqusインプットNodeへの集約
- [x] active属性の自動判定（oldフォルダ判定）
- [x] *PARAMETER/**propsブロックのプロパティ読み取り
- [x] Obsidianエクスポート: frontmatter property化、バージョンリンク構造改善
- [x] メッシュキーワード要約（Node/Element/Nset/Elset→統計情報）
- [x] pymesh統合（メッシュ品質統計、材料割り当て関係）
- [x] Daily noteからのファイル参照・プロパティ・タグ情報抽出
- [x] verbose_name由来タグ生成、elset Node化
- [x] root directory Node化
- [x] 材料名・elset名ケース保持
- [x] vocab.yamlマージ修正（JSON keyのvocab置換） (status-048)
- [x] -id/-v検索のvocab対応（変換後キーでの検索） (status-048)
- [x] Obsidian frontmatterのvocab値消失バグ修正 (status-048)
- [x] CSVエクスポートUTF-8 BOM付き（日本語文字化け対策） (status-048)
- [x] JSONエクスポート平坦化オプション（--flatten） (status-048)
- [x] info -activeオプション（active=trueフィルタ） (status-048)
- [x] parse --full/--lite（重いパーサーの制御） (status-048)

### Neo4j統合基盤（Phase N1-N2完了）

- [x] `shared/` パッケージ作成（neo4j_schema.py, types.py, config.py）
- [x] `neo4j/docker-compose.yml` 作成
- [x] Neo4jConnector 実装（直接書き込み+Cypher出力）
- [x] CLI `--target neo4j/cypher` 追加
- [x] credential暗号化管理（jj credential set/show/delete）

### その他完了

- [x] SSH設定（`.pyssh.yaml`）の読込機能
- [x] CLI構造の整理（`services/service/entry.py`）
- [x] services構造の大幅リファクタリング設計（status-040追記）
- [x] shared/tests/test_asset1 テストアセット配置

---

## Phase R: services構造リファクタリング（最優先）

### 優先度: 最高

services/graph/__init__.pyへの過集中を解消し、抽象パーサーパターンによるプラグイン型parseアーキテクチャを確立する。

#### R1. ProjectGraph型の実装 ✅ (status-042)

- [x] `ProjectFile`, `ProjectDirectory`, `ProjectGraph` dataclass定義
- [x] `iterate_directories()` によるツリー走査
- [x] 既存の`GraphService.scan_directory()`をProjectGraph生成に変換
- [x] テスト（shared/tests/test_asset1を使用、7件パス）

**対象ファイル**: `services/graph/project_graph.py`（新規作成）

#### R2. AbstractFileParser.__init_subclass__パターン確立 ✅ (status-042)

- [x] `base.py` に `apply(graph: ProjectGraph) -> ProjectGraph` 抽象メソッド追加
- [x] `__init_subclass__` によるサブクラス自動登録
- [x] `parse(graph: ProjectGraph) -> ProjectGraph` オーケストレーション関数
- [x] パーサー実行順序の制御機構（priority属性）
- [x] テスト（4件パス）

**対象ファイル**: `services/parse/base.py`

#### R3. graph/__init__.py の分解 ✅ (status-042)

現在1ファイルに集中していたparse/enrich/connect ロジックを、16個のAbstractFileParserサブクラスとして分散完了。

- [x] **バージョン関係パーサー**: next_version/same_index_group → parse/parsers/version_parser.py (priority=20)
- [x] **出力ファイル関係パーサー**: result_of/derived_from/has_output/includes → parse/parsers/output_parser.py (priority=30-40)
- [x] **フォルダ関係パーサー**: contains → parse/parsers/directory_parser.py (priority=50)
- [x] **Abaqus INP解析パーサー**: material.inp解析 → parse/connectors/abaqus/inp_parser.py (priority=60,85,98)
- [x] **Abaqus結果パーサー**: .sta/.msg/.dat解析 → parse/connectors/abaqus/result_parser.py (priority=70,86)
- [x] **Abaqusメッシュパーサー**: pymesh統計 → parse/connectors/abaqus/mesh_parser.py (priority=80)
- [x] **Abaqus差分パーサー**: diff_abq_blocks → parse/connectors/abaqus/diff_parser.py (priority=90)
- [x] **Obsidian Dailyパーサー**: dailyノート解析 → parse/connectors/obsidian/daily_parser.py (priority=95)
- [x] **エンリッチメントフィルター**: .sta/.msg/.dat除外 → parse/parsers/enrichment_filter.py (priority=99)
- [x] **ルートディレクトリパーサー**: root Node化 → parse/parsers/directory_parser.py (priority=98)
- [x] graph/__init__.py の`parse_project()`をProjectGraph+パイプライン委譲に変更
- [x] 統合テスト29件パス（test_parser_pipeline.py）

#### R4. export層の整理 ✅ (status-043)

- [x] Obsidianエクスポートを `export/connectors/obsidian/` へ移動（後方互換re-export維持）
- [x] Neo4jエクスポートは `export/connectors/neo4j.py` に配置済み
- [ ] CSV/JSONエクスポートを `export/connectors/` へ移動（将来対応）
- [ ] `Exporter` 基底クラスの定義（将来対応）

#### R5. lib層の整理 ✅ (status-043)

- [x] `services/lib/credentials.py` に配置済み
- [x] SSH/file関連ユーティリティは `services/lib/file/` に配置済み

#### R6. テスト移行と検証 ✅ (status-043)

- [x] shared/tests/test_asset1 を活用した統合テスト作成（29件パス）
- [x] 既存テスト（レガシー）の新パイプライン対応（インポートパス修正、参照先パーサークラス更新）
- [x] parse()パイプラインのE2Eテスト
- [x] 各パーサーサブクラスの単体テスト追加（18件）
- [x] graph/__init__.pyの旧メソッド削除（2026行→510行）
- [x] pymeshインポートパス修正（services.pymesh→modules.pymesh）
- [x] テスト443件パス、0失敗、20スキップ

**参照**: [services/README.md](../services/README.md)

---

## Phase 2: グラフ機能の仕上げ（Phase R完了後）

### 優先度: 高

Phase R（構造リファクタリング）が完了した新アーキテクチャ上で、残存機能を実装する。

#### 2-1. パーサー層の拡張

- [x] NO_NODE_EXTENSIONS（.odb/.odb.json）: スキャンするがNode化しない拡張子 (status-044)
- [x] materialパーサーvocab/token-key-map対応 (status-044)
- [x] ディレクトリ階層構造のcontains relation (status-044)
- [x] JsonPropertyParser: go_*.inpへのJSON key-value割り当て (status-044)
- [x] ProjectGraph.iterate_directories()のnon_file_nodes反映 (status-044)
- [ ] services/cliのロジックをservices/serviceに切り出す
- [ ] ファイルグループ機能の実装（AbstractFileParserサブクラスとして）
- [ ] 旧形式（`.v1`）の完全対応
- [ ] バイナリファイルの判定と対応方針の明確化
- [ ] パフォーマンス最適化（大量ファイル対応）

**参照**: [02-parser.md](./specs/02-parser.md#6-実装計画)

#### 2-2. Abaqusコネクターの追加機能

- [ ] 個々のElsetごとの品質統計
- [ ] ODB連携（Abaqus 2024 Python 3.10対応）
- [ ] index.csv/yamlとファイルの紐付け
- [ ] dailyノートをブロックごとに切り出してNodeに逆輸入
- [ ] config.yamlの拡張
  - [ ] 配列のスライス指定機能
  - [ ] type=isoを指定された場合のelasticプロパティの列定義
  - [ ] type=aniso/orthoの場合の列と値の組み合わせ定義
  - [ ] パターン一致指示によるprops定義（例: RF3は長手方向荷重）
- [ ] 事前にラベリングした対処法の部分一致による紐付け

**参照**: `services/parse/connectors/abaqus/`

#### 2-3. コアデータモデル層の拡張

- [ ] グラフのマージ機能（複数グラフの統合）
- [ ] ノード/関係の更新・削除機能
- [ ] トランザクション管理（保存の原子性）
- [ ] バリデーション強化（循環参照チェック、孤立ノード検出）

**参照**: [01-core-data-model.md](./specs/01-core-data-model.md#4-実装計画)

---

## Phase 2.5: ダッシュボード・API基盤（直近〜中期）

### 優先度: 高

#### D1. データ供給基盤（DashboardDataProvider）

- [ ] `DashboardDataProvider` クラスの実装
  - [ ] `get_go_table()` → DataFrame変換（プロパティ展開済み）
  - [ ] `get_node_card()` → 詳細辞書（関連ノード含む）
  - [ ] `get_plot_data()` → 数値プロパティ抽出
  - [ ] `get_property_keys()` → 利用可能キー一覧
  - [ ] `get_status_summary()` → 実行ステータスサマリー
- [ ] `jj export --target dashboard-json` の実装
- [ ] テスト

#### D2. Streamlitダッシュボード

- [ ] `jj dashboard` CLIコマンド追加
- [ ] テーブルビュー（ag-grid + フィルター）
- [ ] カードビュー（ノード詳細 + 関連画像表示）
- [ ] プロットビュー（plotly散布図/線図、X/Y軸選択）
- [ ] ステータスモニター（実行中/完了/失敗の一覧）

#### D3. REST API（jj serve）

- [ ] `jj serve` CLIコマンド追加（FastAPI + uvicorn）
- [ ] `/api/v1/nodes`, `/api/v1/relations` エンドポイント
- [ ] `/api/v1/summary`, `/api/v1/status` エンドポイント
- [ ] クエリフィルター（type, index, status, props条件）

#### D4. jj-db統合

- [ ] `jj export --target jj-db` の実装（jj-dbアップロード形式）
- [ ] jj-db側にjjプロジェクトインポート機能追加
- [ ] API連携（jj serve → jj-db fetch）
- [ ] jj-db既存ビュー（テーブル/カード/グラフ）でjjデータ表示

**参照**: [09-dashboard.md](./specs/09-dashboard.md)

---

## Phase 2.N: DB統合基盤（jj × jj-db × Neo4j）

### 優先度: 中（Phase 2.5と並行）

### 統合方針

- **データ構造**: jjの`Node`, `Relation`, `GraphModel`を優先
- **レポジトリ概念**: jj-dbの`Repository`概念を保持（プロジェクト俯瞰機能として活用）
- **Neo4jスキーマ**: jjの`shared/neo4j_schema.py`を正とする
- **データフロー**: `jj parse → jj export --target neo4j → Neo4j ← jj-db（参照のみ）`
- **分離原則**: `services/`と`jj_db/`は直接通信禁止、`shared/`経由のNeo4j契約のみ共有

#### 統合で確認が必要な事項

- [ ] ID体系の統一: jjは`int`、jj-dbは`string` → Neo4j内での変換ルール
- [ ] ノードタイプマッピング: jj-db側のEntityとjjのNode.typeの対応表
- [ ] リレーションラベルの正規化
- [ ] レポジトリタイプのNeo4jラベル追加（JJRepository等）
- [ ] 全文検索戦略: Cypher CONTAINS vs Lucene index
- [ ] ユーザー/認証モデル: マルチテナント分離の設計
- [ ] 並行書き込み時の競合解決戦略

#### N1. 基盤構築 ✅ (status-037)

- [x] `shared/` パッケージ作成
- [x] `neo4j/docker-compose.yml` 作成
- [x] `neo4j/init/01-schema.cypher` 作成

#### N2. jj Neo4jエクスポーター ✅ (status-037)

- [x] `Neo4jConnector` 実装
- [x] CLI `--target neo4j/cypher` 追加
- [x] GraphModel → Neo4j Cypherマッピング
- [x] upsert対応（UNWIND + MERGE）

#### N3. jj-db Neo4jクライアント

- [ ] `jj_db/` ディレクトリ構築
- [ ] `jj_db/neo4j_client.py` 実装
- [ ] 材料データのNeo4j投入
- [ ] jjデータの読み取りインターフェース

#### N4. クロスリレーション

- [ ] 材料名マッチングロジック（MATCHES関係の自動生成）
- [ ] `jj import --source neo4j` 実装
- [ ] jj-db側のjjプロジェクトビュー

#### N5. submodule移行（アクセス復旧後）

- [ ] jj_db/ を別リポジトリに切り出し
- [ ] .gitmodules設定
- [ ] shared/ の独立パッケージ化検討
- [ ] CI/CD分離

**参照**: [10-db-integration.md](./specs/10-db-integration.md)

---

## Phase 3: コマンド機能の充実（中期 - 1〜3ヶ月）

### 優先度: 高

#### 3-1. runコマンド層のジョブ型実装

- [ ] `--mode=job` オプションの実装
- [ ] Abaqusジョブアダプター（parse/connectors/abaqus/ にパーサーとして実装）
- [ ] 生成ファイル予測機能
- [ ] ジョブ型の単体テスト
- [ ] 実行ログのGraphStorageへの反映

**参照**: [04-run-command.md](./specs/04-run-command.md#3-実行モードの分類)

#### 3-2. fileコマンド層の基本実装

- [ ] テンプレートディレクトリの構造定義
- [ ] Jinja2によるテンプレートレンダリング
- [ ] 基本テンプレート（Abaqus, Fluent, Dyna）の作成
- [ ] `jj f template` コマンドの実装
- [ ] 基本リネーム機能の実装
- [ ] 基本移動機能の実装

**参照**: [06-file-command.md](./specs/06-file-command.md#8-実装計画)

#### 3-3. runコマンド層のリモート実行統合

- [ ] `--remote` オプションの実装
- [ ] SSH経由の実行（lib/file/ を活用）
- [ ] 既存submit機能の移行
- [ ] リモートログの同期

**参照**: [04-run-command.md](./specs/04-run-command.md#7-既存submit機能のリファクタリング)

---

## Phase 4: 拡張性の強化（中期〜長期 - 3〜6ヶ月）

### 優先度: 中

#### 4-1. parseコネクター拡張（新アダプター層）

Phase Rで確立した抽象パーサーパターンにより、旧来の「アダプター層」はparse/connectors/配下のパーサーサブクラス群として実現する。

- [ ] Fluent向けparse connector (`parse/connectors/fluent/`)
- [ ] LS-DYNA向けparse connector (`parse/connectors/dyna/`)
- [ ] ANSYS向けparse connector (`parse/connectors/ansys/`)
- [ ] コネクターの自動検出（`__init_subclass__`で自動登録済み）

**参照**: [07-adapter.md](./specs/07-adapter.md#7-実装計画)

#### 4-2. export層の拡張

- [ ] `ExporterRegistry` の実装
- [ ] GraphMLExporter の実装
- [ ] `jj export` コマンドの統合
- [ ] カスタムテンプレートサポート
- [ ] インクリメンタルエクスポート

**参照**: [08-export.md](./specs/08-export.md#6-実装計画)

#### 4-3. fileコマンド層の高度な機能

- [ ] カスケードリネーム機能の実装
- [ ] 関係保持オプションの実装
- [ ] SSH送信機能の実装（lib/file/を活用）
- [ ] SSH受信機能の実装
- [ ] 送受信履歴のグラフ化

**参照**: [06-file-command.md](./specs/06-file-command.md#8-実装計画)

---

## Phase 5: 最適化と高度な機能（長期 - 6ヶ月以上）

### 優先度: 低

#### 5-1. コアデータモデル層の最適化

- [ ] 大規模グラフ対応（遅延読込、インデックス最適化）
- [ ] キャッシュ機構の導入
- [ ] JSON形式のパフォーマンス最適化

**参照**: [01-core-data-model.md](./specs/01-core-data-model.md#4-実装計画)

#### 5-2. 設定管理層の高度な機能

- [ ] 設定ファイルのバリデーション
- [ ] 設定エディタ機能（`jj config edit`）
- [ ] 設定テンプレート機能（`jj config init --template abaqus`）
- [ ] 環境変数からの設定上書き
- [ ] 設定のバージョン管理（migration）

**参照**: [03-config.md](./specs/03-config.md#6-実装計画)

#### 5-3. parseコネクターのプラグイン化

- [ ] 外部パッケージとしてのparseコネクター追加
- [ ] コネクターのバージョン管理
- [ ] コネクター間の連携（例: AbaqusからFluentへのデータ転送）

**参照**: [07-adapter.md](./specs/07-adapter.md#7-実装計画)

#### 5-4. 高度なファイル操作

- [ ] 複数ファイル一括操作
- [ ] ファイル比較機能（diff）
- [ ] ファイル履歴の可視化
- [ ] テンプレートのカスタマイズ機能

**参照**: [06-file-command.md](./specs/06-file-command.md#8-実装計画)

---

## マイルストーン

### M1: 基盤完成（Phase 1完了） ✅

**達成日**: 2026-02-04

**達成条件**:
- ✅ コアデータモデル層の基本機能完了
- ✅ 設定管理層の統合完了
- ✅ runコマンドのproperties抽出とファイル差分検出が完全動作
- ✅ CLI層とservice層の分離
- ✅ 全テスト成功

### M1.5: Abaqusグラフ機能完成 ✅

**達成日**: 2026-02-09

**達成条件**:
- ✅ Abaqusコネクターの主要機能が全て動作
- ✅ material解析、結果ファイル解析、メッシュ統計、daily連携完了
- ✅ Obsidianエクスポート機能完成
- ✅ Neo4jエクスポート機能完成
- ✅ テスト396件パス

### MR: services構造改革完了（Phase R完了） ✅

**達成日**: 2026-02-10

**達成条件**:
- ✅ ProjectGraph型が定義され、graph/がスキャン専任になっている
- ✅ AbstractFileParser.__init_subclass__パターンが確立
- ✅ graph/__init__.py から全てのparseロジックがパーサーサブクラスに移行完了（2026行→510行）
- ✅ export層が独立しObsidian/Neo4j各エクスポーターが配置
- ✅ lib層にcredentials/file等ユーティリティが整理
- ✅ 既存テストが全パス（443件パス、0失敗、20スキップ）
- ✅ shared/tests/test_asset1 を使った統合テスト追加（29件+18件単体テスト）

### M2: グラフ機能完成（Phase 2完了）

**達成条件**:
- パーサー層の拡張機能完了
- Abaqusコネクターの追加機能完了
- コアデータモデル層の拡張完了

### M2.5: ダッシュボード基盤完成（Phase 2.5 D1-D2完了）

**達成条件**:
- DashboardDataProviderが完全動作
- `jj dashboard` でStreamlitアプリが起動
- テーブル/カード/プロット/ステータスの4ビューが利用可能
- dashboard-jsonエクスポートが動作

### M3: コマンド機能完成（Phase 3完了）

**達成条件**:
- runコマンドのジョブ型実装完了
- fileコマンドの基本機能実装完了
- リモート実行の統合完了

### M4: 拡張性確保（Phase 4完了）

**達成条件**:
- parseコネクター3つ以上のCAEソフトに対応（Abaqus+2つ）
- export層の基盤完成
- jj serve REST APIが稼働

### M5: 最適化完了（Phase 5完了）

**達成条件**:
- 大規模プロジェクト（10,000ファイル以上）での安定動作
- 高度な設定管理機能の実装
- 外部プラグイン方式のparseコネクター追加が可能

---

## 参考資料

- [機能ドメイン別仕様書](./specs/README.md)
- [実装詳細](./detail.md)
- [ダッシュボード仕様書](./specs/09-dashboard.md)
- [DB統合設計書](./specs/10-db-integration.md)
- [最新ステータス](./status/status-044.md)
- [services/README](../services/README.md)
- [プロジェクトREADME](../README.md)
