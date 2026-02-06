# status-029

**日付**: 2026-02-06

[READMEへ戻る](../../README.md)

## 概要

**破壊的変更**: レポジトリ階層制約の導入。全ノードがレポジトリの下に帰属し、レポジトリはレポジトリの下にしか存在できない制約をグラフデータモデルに追加。

## 変更内容

### 1. コアデータモデル拡張（jj_types/__init__.py）
- `NODE_TYPE_REPOSITORY = "repository"` 定数追加
- `RELATION_BELONGS_TO = "belongs_to"` 定数追加
- `GraphModel.validate_repository_hierarchy()` メソッド追加
  - 5項目のバリデーション: 帰属チェック、レポジトリ帰属、帰属先タイプ、ルート一意性、循環参照禁止

### 2. GraphService拡張（services/graph/__init__.py）
- `_create_root_repository_node()`: ルートレポジトリノードの自動生成
- `_scan_sub_repositories()`: `.jj/`ディレクトリを持つサブディレクトリをサブレポジトリとして検出
- `_create_sub_repository_node()`: サブレポジトリノードの生成
- `_build_belongs_to_relations()`: 全非レポジトリノードに最寄り親レポジトリへの`belongs_to`関係を構築
- `_build_repository_hierarchy_relations()`: レポジトリ間の親子`belongs_to`関係を構築
- `_find_nearest_repository()`: ノードパスから最寄り祖先レポジトリを検索
- `parse_project()`の処理順序を変更:
  1. ルートレポジトリノード生成
  2. サブレポジトリ検出・ノード生成
  3. ファイルスキャン・ノード生成（既存）
  4. リレーション構築（既存、非レポジトリノードのみ対象）
  5. belongs_to関係構築（新規）
  6. レポジトリ間belongs_to構築（新規）

### 3. Obsidianエクスポート対応（services/connectors/obsidian.py）
- `export_graph()`: レポジトリノードをエクスポート対象から除外
- `export_graph()`: belongs_to関係をリレーション出力から除外
- `write_md_with_relations()`: `repository`パラメータ追加、frontmatterに`repository`プロパティを出力
- `_write_base_files()`: レポジトリノードをグループ化対象から除外

### 4. 設計仕様書（docs/specs/09-repository-hierarchy.md）
- レポジトリ階層制約の完全な仕様を文書化
- データモデル変更、バリデーション、実装計画を記載

## テスト

- **211件パス** (185件 → 211件、+26件)
- 既存185テスト: 全パス（後方互換性維持）
- 新規テストファイル: `tests/test_repository_hierarchy.py`
  - `TestRootRepositoryCreation` (3件): ルートレポジトリ生成、プロパティ、belongs_to不在
  - `TestBelongsToRelations` (3件): 全ノード帰属、帰属先タイプ、カウント一致
  - `TestValidateRepositoryHierarchy` (7件): 正常、帰属欠損、ルートなし、ルート複数、非レポジトリ帰属先、サブレポジトリ帰属欠損、正常階層
  - `TestSubRepositoryDetection` (5件): .jj検出、サブレポジトリbelongs_to、ファイル帰属先、ルートファイル帰属、非レポジトリ除外
  - `TestNestedSubRepositories` (3件): ネスト検出、深さ、最寄りレポジトリ帰属
  - `TestGraphServiceSummaryWithRepository` (2件): summaryにrepository/belongs_to含有
  - `TestIntegrationValidation` (3件): 統合バリデーション、ディレクトリノード帰属、materialノード帰属

## 変更ファイル

- `jj_types/__init__.py`: NODE_TYPE_REPOSITORY, RELATION_BELONGS_TO定数, validate_repository_hierarchy()
- `services/graph/__init__.py`: レポジトリ階層構築ロジック全体
- `services/connectors/obsidian.py`: レポジトリノード除外、repository frontmatter
- `tests/test_repository_hierarchy.py`: 新規テストファイル（26件）
- `docs/specs/09-repository-hierarchy.md`: 設計仕様書
- `docs/status/status-029.md`: 本ステータスファイル

## 設計方針

### ルートレポジトリ
- `parse_project()`のproject_rootがルートレポジトリ
- `properties.is_root = "true"`, `properties.depth = "0"`, `properties.path = "."`

### サブレポジトリ
- `.jj/`ディレクトリを含むサブディレクトリを自動検出
- 深さはパスのセパレータ数+1で計算

### ノード帰属先決定
- 各ノードのパスから最も近い祖先レポジトリに帰属
- パスの長さ降順でレポジトリを走査し、最初にマッチしたものを採用

## TODO / 次回への引き継ぎ

- サブレポジトリの設定ファイルによる明示的指定は未実装（現状は`.jj/`ディレクトリのみ）
- `jj g show --summary` のCLI出力にレポジトリ情報を追加する可能性あり
- Neo4jエクスポート（将来）でのレポジトリノード取り扱い方針は未定
- `_format_group_file()` メソッドは未使用状態のまま残存（status-028から引き継ぎ）
