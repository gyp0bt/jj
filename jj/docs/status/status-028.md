# status-028

**日付**: 2026-02-06

[READMEへ戻る](../../README.md)

## 概要

Obsidianエクスポート改善とGraphService機能拡充。frontmatterのproperty化、バージョンリンク構造改善、結果ファイル属性のインプット集約、active属性自動判定、*PARAMETER/**propsプロパティ読み取り。

## 変更内容

### 1. frontmatterにファイル情報をpropertyとして追加
- `node_to_frontmatter()` に `node_type`, `node_format`, `file` プロパティを追加
- `file` プロパティはバックスラッシュを `/` に正規化
- 既存の本文中ファイル情報表記は維持

### 2. Obsidian export: バージョンリンク構造改善
- 同一idxの `-group.md` ファイル生成を廃止
- 最新verのNodeが `{type}_idx{index}.base` へのリンクを持つ
  - 例: `go_idx1_v{最新}.inp` → `[[Abaqusインプット_idx1.base]]`
- 最新以外のNodeは次のバージョンNodeへのリンクを持つ
  - 例: `go_idx1_v1.inp` → `[[O-go_idx1_v2.inp]]`
- `_build_version_groups()`, `_build_parent_links()` メソッドを新規追加
- `export_graph()` でバージョングループに基づくincludes自動設定

### 3. 結果ファイル属性のAbaqusインプット集約
- `_enrich_sta_status()`: .staの `analysis_status`, `sta_errors`, `sta_warnings` を同名の入力ファイル(.inp)にも集約
- `_enrich_msg_status()`: .msgの `msg_errors`, `msg_warnings` を同名の入力ファイル(.inp)にも集約
- 結果ファイルノード自体のプロパティも維持

### 4. .baseパスのバックスラッシュ修正
- `_format_base_filter()` で `notes_dir` を文字列化する際にバックスラッシュを `/` に変換

### 5. active属性の自動判定（GraphService）
- `file_to_node()` でファイルの親ディレクトリが `old` かどうかを判定
- `old/` 配下 → `active: "false"`、それ以外 → `active: "true"`

### 6. *PARAMETER/**propsプロパティ読み取り
- `_read_inp_parameter_props()` メソッドを `GraphService` に追加
- INPファイルの `*PARAMETER` キーワード直後の `**props` コメントブロックを解析
- `key=value` 形式のパラメータを抽出し、vocabマッピングを適用
- `file_to_node()` から自動的に呼び出し

## テスト

- **185件パス** (170件 → 185件、+15件)
- 新規テストクラス:
  - `TestObsidianFrontmatterProperties` (4件): frontmatterのproperty化
  - `TestObsidianVersionLinks` (2件): バージョンリンクチェーン、.base命名
  - `TestActiveAttribute` (2件): active属性の自動判定
  - `TestInpParameterProps` (4件): *PARAMETER/**props読み取り
  - `TestResultFileAggregation` (2件): 結果ファイル集約
- 変更テスト:
  - `test_group_files_abolished`: group.md廃止確認
  - `test_latest_version_links_to_base`: 最新ver→.baseリンク
  - `test_non_latest_links_to_next_version`: 非最新→次verリンク

## 変更ファイル

- `services/connectors/obsidian.py`: frontmatter property化、バージョンリンク構造、group.md廃止、.baseパス修正
- `services/graph/__init__.py`: active属性、*PARAMETER/**props読み取り、結果ファイル集約
- `tests/test_obsidian_connector.py`: テスト更新・追加
- `tests/test_graph_feature.py`: テスト追加

## TODO / 次回への引き継ぎ

- `_format_group_file()` メソッドは未使用状態だが残存している。削除しても問題ない
- notes/__init__.pyの旧 `get_properties_by_inp_parameter()` と `get_properties_by_filepath()` はlegacy。GraphServiceが同等機能を持つようになった
- dat, odb結果ファイルの解析（計算時間抽出等）は未実装。現状はsta, msgのみ
