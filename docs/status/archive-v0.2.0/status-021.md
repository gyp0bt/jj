[← status-index](status-index.md)

# status-021: status-020 TODO実行

- **日付**: 2026-02-18
- **マイルストーン**: M2/M3
- **ブランチ**: claude/execute-status-todos-aP2p4

---

## 概要

status-020のTODO3件を実行。Neo4jスキーマへのメッシュプロパティ反映、接頭辞エスケープキーのダッシュボード表示対応、diff_unified形式のObsidianエクスポート対応を実施。

## 実施内容

### 1. M3設計に基づくNeo4jスキーマへのmesh_topology_groups/mesh_element_quality反映

Neo4jスキーマ定義にメッシュ解析プロパティとdiffプロパティの定数クラスを追加。

- **shared/neo4j_schema.py**: `PropertyKey`クラス新設（MESH_ELEMENT_QUALITY, MESH_TOPOLOGY_GROUPS, DIFF_UNIFIED等10定数）
- **shared/neo4j_schema.py**: `TYPE_TO_LABEL`に`version_diff`タイプを追加
- **shared/neo4j/init/01-schema.cypher**: mesh_node_count/mesh_element_countのインデックス追加
- **docs/specs/neo4j-pipeline-design.md**: メッシュ関連プロパティ・diff関連プロパティの格納形式を文書化
- **services/export/connectors/neo4j.py**: `_sanitize_property_value()`のネストリスト検出を修正（list[list]→JSON文字列化）
- **テスト**: 7件追加（Cypherエクスポート検証、PropertyKey定数、version_diffラベル、サニタイズ検証）

### 2. 接頭辞エスケープ付きキーのダッシュボード表示対応（ソート・フィルタリング）

MeshInheritParserが生成する`{child_name}:{key}`形式のキーをダッシュボードで適切に扱えるよう対応。

- **services/query/sort.py**: `get_base_key()`ユーティリティ関数を新設
- **services/query/sort.py**: `sort_columns_by_vocab()`を拡張。接頭辞キーはベースキーのvocab順位の直後にソートされる
- **services/query/sort.py**: `select_table_columns()`のglobマッチにベースキーでの照合を追加
- **services/dashboard/data_provider.py**: `_sort_by_vocab()`を`get_base_key()`ベースに書き換え
- **services/query/__init__.py**: `get_base_key`をパブリックAPIに追加
- **テスト**: 7件追加（接頭辞ソート、複数接頭辞グループ化、globマッチ、完全一致、get_base_key単体4件）

### 3. diff_unified形式のObsidianエクスポート対応

diff_unifiedプロパティがfrontmatterのみでマークダウン本文に出力されていなかった問題を修正。

- **services/export/connectors/obsidian/__init__.py**: 差分セクション内に「### Unified Diff」サブセクションを追加
- **テスト**: 2件追加（diff_unified表示確認、diff_from未設定時の非表示確認）

## テスト結果

- 変更関連テスト: **497 passed, 40 skipped**（7件pandas環境依存の既存失敗を除く）
- lint: ruff check + format **ALL PASSED**

## TODO

- [ ] Neo4j実環境でのmesh_element_quality/mesh_topology_groupsエクスポート動作検証
- [ ] 接頭辞キーのダッシュボードUI表示名改善（vocab翻訳の適用）
- [ ] M3 Phase 2: jjrvのIEntityRepository抽象化着手
