[READMEへ戻る](../../README.md)

# status-042: Phase R1-R3 実装完了（抽象パーサーパイプライン確立）

**日付**: 2026-02-09

## 概要

Phase R（services構造リファクタリング）のR1-R3を実装完了。`ProjectGraph`型を定義し、`AbstractFileParser.__init_subclass__`パターンによるパーサー自動登録を確立。`graph/__init__.py`から16パーサーサブクラスへの分解を実施し、`parse()`パイプラインで`test_asset1`を丸ごと解析（47ノード、65リレーション）。統合テスト29件全パス。

## 変更内容

### 1. R1: ProjectGraph型の実装

**新規ファイル**: `services/graph/project_graph.py`

- `ProjectFile`, `ProjectDirectory`, `ProjectGraph` dataclass定義
- `iterate_directories()` によるツリー走査
- `from_graph_service()` / `to_graph_model()` 変換メソッド
- `next_node_id()` / `next_relation_id()` でID自動採番
- `add_node()` / `add_relation()` / `remove_nodes()` でグラフ操作
- `get_node_by_path()` / `get_node_by_id()` / `get_nodes_by_type()` で検索
- `safe_relative_path()` でパス正規化

### 2. R2: AbstractFileParser.__init_subclass__パターン確立

**変更ファイル**: `services/parse/base.py`

- 旧`AbstractFileParser`（ファイル名解析）を`FileNameParser`にリネーム
- 新`AbstractFileParser(ABC)`を定義:
  - `priority`属性（デフォルト100）
  - `apply(graph: ProjectGraph) -> ProjectGraph` 抽象メソッド
  - `__init_subclass__`でサブクラスを自動レジストリ登録
- `parse(graph: ProjectGraph) -> ProjectGraph` オーケストレーション関数
- `get_parser_registry()` / `clear_parser_registry()` ヘルパー

### 3. R3: graph/__init__.py の分解

16パーサーサブクラスを以下に配置:

#### 共通パーサー（`services/parse/parsers/`）

| priority | ファイル | クラス | 責務 |
|----------|---------|--------|------|
| 20 | `version_parser.py` | `VersionRelationParser` | `next_version`, `same_index_group` |
| 30 | `output_parser.py` | `ResultRelationParser` | `result_of` |
| 31 | `output_parser.py` | `AssetRelationParser` | `derived_from` |
| 32 | `output_parser.py` | `OutputRelationParser` | `has_output` |
| 40 | `output_parser.py` | `IncludesRelationParser` | `includes` (*INCLUDE解析) |
| 50 | `directory_parser.py` | `DirectoryRelationParser` | `contains` |
| 98 | `directory_parser.py` | `RootDirectoryParser` | ルートdirectory Node |
| 99 | `enrichment_filter.py` | `EnrichmentOnlyFilter` | .sta/.msg/.datノード除外 |

#### Abaqusコネクター（`services/parse/connectors/abaqus/`）

| priority | ファイル | クラス | 責務 |
|----------|---------|--------|------|
| 60 | `inp_parser.py` | `AbaqusInpParser` | material Node化 |
| 70 | `result_parser.py` | `AbaqusResultParser` | .sta/.msg/.dat解析 |
| 80 | `mesh_parser.py` | `AbaqusMeshParser` | pymeshメッシュ統計 |
| 85 | `inp_parser.py` | `AbaqusMaterialAssignmentParser` | 材料割り当て |
| 86 | `result_parser.py` | `AbaqusIncludePropertyParser` | プロパティ伝搬 |
| 90 | `diff_parser.py` | `AbaqusDiffParser` | バージョン差分 |
| 98 | `inp_parser.py` | `AbaqusElsetParser` | elset Node化 |

#### Obsidianコネクター（`services/parse/connectors/obsidian/`）

| priority | ファイル | クラス | 責務 |
|----------|---------|--------|------|
| 95 | `daily_parser.py` | `DailyNoteParser` | dailyノート解析 |

### 4. parse_project() パイプライン化

**変更ファイル**: `services/graph/__init__.py`

`parse_project()`をProjectGraph+パイプライン委譲に変更:
1. `scan_files()` でファイル一覧取得
2. `file_to_node()` でNode生成
3. `ProjectGraph.from_graph_service()` でProjectGraph構築
4. `run_parser_pipeline()` で全パーサー適用
5. `to_graph_model()` でGraphModel返却

旧メソッド（`_build_version_and_group_relations`等）はファイル内に残存するが`parse_project()`からは呼ばれない。

### 5. parse/__init__.py 更新

**変更ファイル**: `services/parse/__init__.py`

- `AbstractFileParser`, `FileNameParser`, `parse` をエクスポート
- 全パーサーサブクラスモジュールをimportして自動登録トリガー

### 6. 統合テスト作成

**新規ファイル**: `tests/test_parser_pipeline.py`（29テスト）

- `TestProjectGraph` (7件): ProjectGraph dataclass基本動作
- `TestParserRegistry` (4件): 自動登録、ソート、具象クラスのみ
- `TestPipelineIntegration` (11件): test_asset1全体パース
- `TestVersionRelations` (2件): go_idx2 v2→v3, go_idx3 v1→v2
- `TestIncludesRelations` (1件): go_idx1 includes mesh
- `TestDirectoryRelations` (1件): old/ contains検証
- 全29件パス

### 7. 仕様書更新

- `docs/specs/02-parser.md`: 新アーキテクチャ（2層構造、パーサー実行順序表、ProjectGraph型）に全面改変
- `docs/specs/07-adapter.md`: 旧「アダプター層仕様書」を「parseコネクター仕様書」に全面改変

## 変更ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `services/graph/project_graph.py` | 新規: ProjectGraph型定義 |
| `services/parse/base.py` | 変更: FileNameParser分離、新AbstractFileParser追加 |
| `services/parse/__init__.py` | 変更: 新エクスポート追加、自動登録import追加 |
| `services/graph/__init__.py` | 変更: parse_project()パイプライン化 |
| `services/parse/parsers/__init__.py` | 新規: 共通パーサーパッケージ |
| `services/parse/parsers/version_parser.py` | 新規: バージョン関係パーサー |
| `services/parse/parsers/output_parser.py` | 新規: 出力ファイル関係パーサー（4クラス） |
| `services/parse/parsers/directory_parser.py` | 新規: ディレクトリ関係パーサー（2クラス） |
| `services/parse/parsers/enrichment_filter.py` | 新規: エンリッチメントフィルター |
| `services/parse/connectors/abaqus/inp_parser.py` | 新規: Abaqus INP解析パーサー（3クラス） |
| `services/parse/connectors/abaqus/result_parser.py` | 新規: Abaqus結果パーサー（2クラス） |
| `services/parse/connectors/abaqus/mesh_parser.py` | 新規: Abaqusメッシュパーサー |
| `services/parse/connectors/abaqus/diff_parser.py` | 新規: Abaqus差分パーサー |
| `services/parse/connectors/obsidian/daily_parser.py` | 新規: Obsidian Dailyパーサー |
| `tests/test_parser_pipeline.py` | 新規: 統合テスト29件 |
| `docs/specs/02-parser.md` | 変更: 新アーキテクチャに全面改変 |
| `docs/specs/07-adapter.md` | 変更: parseコネクター仕様書に全面改変 |
| `docs/roadmap.md` | 変更: R1-R3完了マーク、R6部分更新 |
| `README.md` | 変更: status-042エントリ追加 |
| `docs/status/status-042.md` | 新規: 本ステータス |

## テスト結果

- 新テスト: `tests/test_parser_pipeline.py` 29件全パス
- 既存テスト: レガシーとして扱い（新パイプラインへの移行は別途R6で実施）

## TODO / 次のステップ

- [ ] Phase R4: export層の整理（ObsidianConnectorを`export/connectors/`へ移動）
- [ ] Phase R5: lib層の整理（credentials, file等のユーティリティ移動）
- [ ] Phase R6: 既存レガシーテストの新パイプライン対応
- [ ] graph/__init__.py の旧メソッド群の削除（parse_project()から呼ばれなくなった分）
- [ ] 各パーサーサブクラスの単体テスト追加

## 確認事項・設計上の懸念

1. **graph/__init__.py 旧メソッド残存**: `_build_version_and_group_relations`, `_build_result_relations`等の旧メソッドがファイル内に残っているが、`parse_project()`からは呼ばれない。レガシーテストが直接呼んでいる可能性があるため、R6（テスト移行）完了まで残す方針。

2. **既存テストとの互換性**: 既存テスト（315件パス、12件失敗は全てobsidian系で事前存在、18件スキップ）のうち、新パイプライン化により4件が新たに失敗。ユーザー指示により既存テストはレガシーとして扱い、test_asset1ベースの新テストを正とする。

3. **FileNameParser命名**: 旧`AbstractFileParser`を`FileNameParser`にリネーム。file_parse.pyの`FileParse`と機能が重複するが、`FileParse`はGraphServiceで直接使われているため両方残存。長期的には統合が望ましい。

4. **パーサー間の順序依存**: priority値で制御済み。特に以下の依存関係に注意:
   - `IncludesRelationParser`(40) → `AbaqusIncludePropertyParser`(86): includesリレーションが先に必要
   - `AbaqusInpParser`(60) → `AbaqusMaterialAssignmentParser`(85): materialノードが先に必要
   - 全パーサー → `EnrichmentOnlyFilter`(99): 最後にフィルタリング
