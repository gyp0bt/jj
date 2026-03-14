[← status-index](status-index.md)

# status-020: M3前pymeshリファクタリング

- **日付**: 2026-02-18
- **マイルストーン**: M2/M3
- **ブランチ**: claude/setup-project-docs-PPYi8

---

## 概要

M3（Neo4j統合パイプライン）着手前に、pymesh関連のリファクタリングを5件実施。
ノードプロパティの整理・メッシュ解析機能の拡充・差分表示形式の追加を行った。

## 実施内容

### 1. tagsロジックの完全削除

ノードプロパティから`tags`を完全に削除。

- **変更ファイル**: graph/__init__.py, directory_parser.py, inp_parser.py, mesh_inherit_parser.py, abaqus_query.py, obsidian export
- **テスト**: 23件の修正/削除
- **影響**: tags用のロジック（FileParse.get_tags()→properties, path_tag_map, verbose_name→tags分割等）を除去。Obsidianエクスポートはtype+materialベースのタグ生成に変更。

### 2. mesh_elset_quality → mesh_element_quality

elset単位の品質統計を`*ELEMENT`キーワードブロック（要素タイプ）単位に変更。

- `extract_elset_quality_stats()` → `extract_element_quality_stats()`
- キーがelset名（BODY, SKIN等）から要素タイプ名（C3D8, C3D4等）に変更
- 同一要素タイプが複数ブロックに分散している場合のマージ処理を追加
- `_MERGE_DICT_KEYS`の`mesh_elset_quality`を`mesh_element_quality`に更新

### 3. メッシュトポロジーグループ（連結成分解析）

Union-Findアルゴリズムで要素間のノード共有関係を解析し、メッシュ整合集団を特定。

- `extract_mesh_topology_groups()` を mesh.py に新規実装
- `AbaqusMeshParser.apply()` で `mesh_topology_groups` プロパティとして付与
- 出力形式: `[[elset_a, elset_b], [elset_c]]`（同じ集団に属するelsetのグループ）
- テスト4件追加（連結/非連結/elsetなし/パーサー統合）

### 4. include_properties廃止・接頭辞エスケープ

`AbaqusIncludePropertyParser`を廃止し、`MeshInheritParser`で全プロパティを直接継承。

- `AbaqusIncludePropertyParser`（priority=86）を削除
- `MeshInheritParser`にキー競合時の接頭辞エスケープを追加
  - 形式: `{child_name}:{key}`（例: `mesh_t50:mesh_node_count`）
- `include_properties`参照をdashboard/display/test全体から除去
  - data_provider.py, card.py, html_export.py, query.py, abaqus_query.py, display_name_parser.py

### 5. diff +/-マークダウン形式追加

既存のリスト+dict形式に加え、unified diff風の+/-表記を追加。

- `format_diff_unified_markdown()` を __init__.py に新規実装
- `diff_unified` プロパティとして diffノードに格納
- `generate_diff_props()` の出力にも追加
- `\`\`\`diff` コードブロック内で:
  - 追加: `+` 行
  - 削除: `-` 行
  - 変更: キー単位で `-`/`+` 表示、共通行は無印

## テスト結果

- 全テスト: **863 passed, 57 skipped**
- lint: ruff check + format **ALL PASSED**

## TODO

- [ ] M3設計に基づくNeo4jスキーマへのmesh_topology_groups/mesh_element_quality反映
- [ ] 接頭辞エスケープ付きキーのダッシュボード表示対応（ソート・フィルタリング）
- [ ] diff_unified形式のObsidianエクスポート対応
