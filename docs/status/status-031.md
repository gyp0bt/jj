# status-031

**日付**: 2026-02-06

[READMEへ戻る](../../README.md)

## 概要

abaqus material読み取りソースの制限、汎用ディレクトリノードのグラフ追加、pymesh .inpパーサーの末尾カンマ・*include FileNotFoundError対応。

## 変更内容

### 1. abaqus material読み取りソースの制限

- **問題**: `_build_material_nodes()`が全`input_extensions`（`.dat`含む）を対象にしていたため、`go_idx3.dat`などからもmaterialが読み取られていた
- **修正**: `_is_material_source_node()`静的メソッドを追加し、material読み取り対象を以下に限定:
  - `go_`プレフィックス付き`.inp`ファイル（例: `go_idx1.inp`）
  - `material_`プレフィックス付き`.inp`ファイル（例: `material_v2.inp`）
  - `go`または`material`そのものの`.inp`ファイル（例: `material.inp`）
- `.dat`ファイル、`step_*.inp`、`mesh_*.inp`からはmaterialを読み取らない

### 2. 汎用ディレクトリノードのグラフ追加

- **問題**: ファイル命名規則に合致するディレクトリ（`go_idx1_v1/`等）のみがノード化されており、`reports/`や`results/`などの汎用ディレクトリはグラフに含まれなかった
- **修正**: `_build_directory_relations()`を拡張:
  - 従来通り命名規則合致ディレクトリ → `type="{fileType}_directory"`
  - ファイルノードを含む全ディレクトリ → `type="directory"`、`name=ディレクトリ名`
  - 各ディレクトリ内のファイルにcontains関係を作成
- Obsidianエクスポートは既存の`export_graph`ループで全ノードを処理するため、追加変更なしでディレクトリノードもObsidianに出力される（`notes/props/directory/`配下）

### 3. pymesh .inpパーサー: 末尾カンマ対応

- **問題**: `*DENSITY`の`1.0e-9,`のように末尾カンマで終わる行が`float("")`変換エラーを発生
- **修正**: `MaterialPropertyReadComponent.read_line()`で空文字列を`None`で埋めるように変更
  - 変更前: `[[float(v) for v in values]]`
  - 変更後: `[[None if v == "" else float(v) for v in values]]`

### 4. pymesh .inpパーサー: *include FileNotFoundError対応

- **問題**: `*INCLUDE`で参照されるファイルが存在しない場合（oldフォルダに移動済み等）にFileNotFoundErrorが発生
- **修正**: `read_files_with_unknown_encoding()`の`*INCLUDE`処理で、`include_path.exists()`を事前チェック
  - ファイルが存在しない場合は警告メッセージを出力してスキップ
  - 親ファイルの残りの行は通常通り処理を継続

## テスト

- **242件パス** (228件 → 242件、+14件)
- 新規テストクラス:
  - `TestMaterialSourceFiltering` (5件): material読み取りソース制限の検証
    - `.dat`ファイルからの読み取り拒否
    - `go`系・`material`系`.inp`からの読み取り確認
    - `step`系`.inp`からの読み取り拒否
    - `_is_material_source_node()`の静的テスト
  - `TestGenericDirectoryNodes` (4件): 汎用ディレクトリノードの検証
    - `reports/`ディレクトリのNode(type=directory)生成
    - `reports/`内ファイルのcontains関係
    - `results/`ディレクトリのノード生成
    - 命名規則合致ディレクトリの既存動作維持
  - `TestTrailingCommaInMaterialProperty` (2件): 末尾カンマ対応の検証
    - `1.0e-9,`行がNone埋めでパースされること
    - 通常行（カンマなし）の正常動作
  - `TestIncludeFileNotFound` (3件): *include FileNotFoundError対応の検証
    - 存在しない*includeファイルのスキップと残行処理
    - `read_inp()`のクラッシュ回避
    - `parse_project()`のグラフ生成

## 変更ファイル

- `services/graph/__init__.py`: `_is_material_source_node()`追加、`_build_material_nodes()`フィルタ変更、`_build_directory_relations()`汎用ディレクトリ対応
- `services/parse/abaqus_connector.py`: `MaterialPropertyReadComponent.read_line()`末尾カンマ対応、`read_files_with_unknown_encoding()`*include存在チェック追加
- `tests/test_graph_feature.py`: 14件の新規テスト追加

## TODO / 次回への引き継ぎ

- 汎用ディレクトリノードのObsidian表示を改善する場合は、`_format_md()`の「ファイル情報」セクションをディレクトリ向けに調整可能
- `_is_material_source_node()`は現在ファイル名ベースの判定。path-type-mapの設定に基づく判定への拡張も検討可能
- `MaterialPropertyReadComponent.read_line()`のNone埋めにより、下流でNone値のハンドリングが必要になる場合あり（現状は`data: list[list[float | None]]`）

## 設計上の懸念

- 特になし
