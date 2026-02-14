[READMEへ戻る](../../README.md)

# status-057: Obsidian全ノード出力・Include解決改善・Elset material relation (2026-02-11)

## 概要

Obsidianエクスポートで全ノードを出力するように変更、*INCLUDEファイル探索を複数階層対応に改善、elsetノードにuses_material relationを追加。

## 変更内容

### 1. Obsidianエクスポート: 全ノード出力

**変更前**: `index_group`/`version_diff`タイプのメタノードはObsidian mdファイル・baseファイル生成の対象外
**変更後**: 全ノード（ファイル、ディレクトリ、非ファイルノード含む）をObsidianに出力

- **ファイル**: `services/export/connectors/obsidian/__init__.py`
- abaqus_material, version_diff, index_group, abaqus_elset等のメタノードもmdファイルとして書き出し
- baseファイル生成でもメタノードタイプを含む

### 2. Include解決ロジックの改善

**変更前**: `*INCLUDE`参照は`file_path.parent`のみで解決。`old/`フォルダ内のファイルが親ディレクトリの`material.inp`や`mesh_*.inp`を見つけられずdiff等が実行不可
**変更後**: 以下の優先順序でincludeファイルを探索

1. ファイルを含むフォルダ (`file_path.parent`)
2. スクリプト実行フォルダ (`cwd`)
3. cwd配下をN階層まで再帰的に探索（デフォルト5階層）

- **ファイル**:
  - `services/parse/connectors/abaqus/__init__.py`: `_resolve_include_path()`, `_walk_max_depth()` 追加
  - `modules/pymesh/read_inp.py`: 同様の探索ロジックを追加
- **新関数**:
  - `_resolve_include_path(include_name, file_path, max_depth=5)`: 優先順序に従いincludeファイルを探索
  - `_walk_max_depth(root, max_depth)`: ディレクトリを最大depth階層まで走査するジェネレータ

### 3. Elsetノード: uses_material relation追加

**変更前**: elsetノードはmaterial名をpropertiesに持つが、abaqus_materialノードへのrelationがない
**変更後**: 材料割り当てされたelsetノードは`uses_material` relationで対応するabaqus_materialノードを参照

- **ファイル**: `services/parse/connectors/abaqus/inp_parser.py` (`AbaqusElsetParser`)
- **リレーション**: `uses_material`: abaqus_elsetノード → abaqus_materialノード
- abaqus_materialノードを名前(小文字)でインデックス化し、elset作成時にマッチするmaterialがあればrelation追加

## テスト結果

- 594 passed, 21 skipped（pymesh未インストールの既存問題のみ）
- 既存テストの破壊なし

## 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| `services/export/connectors/obsidian/__init__.py` | 全ノード出力（meta_typesフィルタ除去） |
| `services/parse/connectors/abaqus/__init__.py` | include探索ロジック改善（_resolve_include_path追加） |
| `modules/pymesh/read_inp.py` | include探索ロジック改善（_resolve_include_path追加） |
| `services/parse/connectors/abaqus/inp_parser.py` | AbaqusElsetParserにuses_material relation追加 |

## TODO / 次のステップ

- [ ] パーサーキャッシュの実装（DRY: read_inp結果の共有キャッシュ）
- [ ] Obsidianでversion_diff/index_groupノードの表示テンプレートの検討（特にdiffノードの可視化）
- [ ] include解決の最大探索深度をconfig.yamlで設定可能にする検討
- [ ] uses_material relationのテスト追加（material割り当てがあるtest_asset1でのE2Eテスト）
