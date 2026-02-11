[READMEへ戻る](../../README.md)

# status-056: ノード化・Obsidian修正・デバッグフラグ (2026-02-11)

## 概要

diff/index_groupのノード化方式への変更、CLI -debugフラグ追加、Obsidianエクスポートの複数バグ修正、material.inpテスト対応を実施。

## 変更内容

### 1. diffブロックのノード化

**変更前**: diff情報はv2ノードのpropertiesに`diff_from`, `diff_summary`, `diff_details`として保存
**変更後**: `version_diff`タイプのdiffノードを作成し、relation経由で新旧ノードをリンク

- **ファイル**: `services/parse/connectors/abaqus/diff_parser.py`
- **ノード**: type=`version_diff`, format=`diff`
  - properties: `diff_from`, `diff_to`, `has_diffs`, `source_type`, `source_index`, `diff_summary`, `diff_details`
- **リレーション**:
  - `diff_from`: diffノード → 旧ノード
  - `diff_to`: diffノード → 新ノード

### 2. same_index_groupのノード化

**変更前**: 代表ノード（v1）から他メンバーへの`same_index_group`リレーション
**変更後**: `index_group`タイプのグループノードを作成し、全メンバーが`belongs_to`で参照

- **ファイル**: `services/parse/parsers/version_parser.py`
- **ノード**: type=`index_group`, format=`group`
  - name: `{type}_idx{index}` (例: `go_idx1`)
  - properties: `source_type`, `source_index`, `member_count`
- **リレーション**:
  - `belongs_to`: メンバーノード → index_groupノード

### 3. CLI -debugフラグ

- **ファイル**: `services/cli/graph.py`, `services/service/graph_command.py`, `services/graph/__init__.py`, `services/parse/base.py`
- `jj parse -debug` でデバッグモード有効
- debug=Trueの場合、パーサー実行中に例外が発生するとそのままraise
- debug=Falseの場合（デフォルト）、例外をcatchして警告出力後に継続

### 4. Obsidian export: daily_noteノードのO-プレフィックス除去

- **ファイル**: `services/export/connectors/obsidian/__init__.py`
- `_is_obsidian_origin(node)` メソッド追加
- daily_noteタイプのノードはObsidian export時にO-プレフィックスを付けない

### 5. Obsidian export: includes O-O-二重プレフィックス修正

- **原因**: `_build_parent_links`がObsidian形式名（O-付き）を返していたが、`node_to_frontmatter`で再度`to_obsidian_link`が呼ばれてO-O-になっていた
- **修正**: `_build_parent_links`で実ファイル名を返すように変更し、`node_to_frontmatter`側でO-変換を行う

### 6. Obsidian export: ネストされたvalue平坦化

- **ファイル**: `services/export/connectors/obsidian/__init__.py`
- `_flatten_properties()`静的メソッド追加
- ネストされたdictを`.`区切りで再帰的に平坦化（CSV exportと同様）
- 例: `{"mesh_quality": {"aspect_ratio": {"min": 0.5}}}` → `{"mesh_quality.aspect_ratio.min": 0.5}`

### 7. Obsidian export: メタノード除外

- `index_group`/`version_diff`タイプのメタノードはObsidian mdファイル・baseファイル生成の対象外

### 8. material.inp関連テスト修正

- test_asset1にmaterial.inpが追加されたため、テスト期待値を更新
- `test_missing_material_inp_not_in_includes` → `test_material_inp_in_includes`
- `test_go_idx0_includes_mesh_only` → `test_go_idx0_includes_mesh_and_material`
- includes件数: 8件 → 14件
- `test_go_inp_fails_without_material_inp` → `test_go_inp_reads_with_material_inp`

## テスト結果

- 599 passed, 21 skipped, 1 failed（pymesh未インストールのみ）
- 既存テストの破壊なし（pymeshは環境依存の既存問題）

## 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| `services/parse/connectors/abaqus/diff_parser.py` | diffノード化方式に変更 |
| `services/parse/parsers/version_parser.py` | index_groupノード化方式に変更 |
| `services/cli/graph.py` | -debugフラグ追加 |
| `services/service/graph_command.py` | debug引数追加 |
| `services/graph/__init__.py` | debug引数伝搬 |
| `services/parse/base.py` | debug対応（パーサーエラーハンドリング） |
| `services/export/connectors/obsidian/__init__.py` | O-プレフィックス修正、平坦化、メタノード除外 |
| `tests/test_parser_units.py` | diff/index_group/materialテスト更新 |
| `tests/test_parser_pipeline.py` | belongs_to/materialテスト更新 |
| `tests/test_graph_feature.py` | diffノード化テスト更新 |
| `tests/test_abaqus_connector.py` | materialテスト更新 |

## TODO / 次のステップ

- [ ] パーサーキャッシュの実装（DRY: read_inp結果の共有キャッシュ）
- [ ] Obsidianでversion_diff/index_groupノードの表示方針検討
- [ ] Obsidian baseファイルにindex_groupノードの情報を反映する検討
- [ ] material.inpの材料プロパティをより詳細にテストする
