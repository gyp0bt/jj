[READMEへ戻る](../../README.md)

# status-033: Daily紐付け強化、info/diff/export拡張、verbose_name、材料プロパティ、Obsidianタグ

**日付**: 2026-02-07

## 概要

7つの機能を実装:
1. Daily日報からの情報紐付けロジック強化（Obsidianリンク＋プロパティ記法、ファイルリンク値抽出）
2. `jj info` コマンド強化（-id, -v, 複数指定, -props）
3. `jj diff` コマンドの新規実装
4. parse時のverbose_name（表示名）登録
5. `jj export --target csv/json` CSV/JSON書き出し機能
6. parse時のelset/材料名をgo_inpプロパティに追加
7. Obsidianエクスポート時のタグ(#tagname)多用

## 変更内容

### 1. Daily紐付けロジック強化

日報パーサーが以下の記法を新たにサポート:
- `[[O-go_idx1.inp]]:備考:条件1` — Obsidianリンク＋プロパティ記法
- `[[go_idx1.inp|表示名]]:key:value` — 表示名付きリンク＋プロパティ
- `go_idx1.inp: image: [[image.png|画像1]]` — ファイルリンク値の自動抽出
- O-プレフィックスの自動除去（`O-go_idx1.inp` → `go_idx1.inp`）

**変更ファイル**:
- `services/connectors/daily_connector.py`: 新パターン追加、`_strip_obsidian_prefix()`、`_extract_file_path_from_value()`追加

### 2. `jj info` コマンド強化

- `jj info file1.inp file2.inp` — 複数ファイル名指定
- `jj info -id 1 2` — インデックスで検索
- `jj info -v 1` — バージョンで検索
- `jj info -props file.inp` — プロパティのみ表示（リレーション非表示）
- verbose_nameがある場合は表示名も出力

**変更ファイル**:
- `cli/graph.py`: `_add_info_args()`, `_run_info()` 拡張

### 3. `jj diff` コマンド

2つのファイル間の差分を表示する新コマンド:
- `jj diff file1.inp file2.inp` — Abaqusキーワードブロック差分のサマリー
- `jj diff file1.inp file2.inp --detail` — 詳細差分も表示
- テキストファイルの場合はunified diff形式

**新規関数**:
- `cli/graph.py`: `_add_diff_args()`, `_run_diff()`, `_resolve_file_path()`

### 4. verbose_name登録

parse時にconfig vocabで変換した後の表示名を`verbose_name`プロパティとして登録:
- `name`にはファイル名（raw）を保持
- `verbose_name`にはvocab変換後の名前を登録（異なる場合のみ）

**変更ファイル**:
- `services/graph/__init__.py`: `_build_verbose_name()` 追加、`file_to_node()` 拡張

### 5. CSV/JSONエクスポート

`jj export --target csv/json` で選択ファイルの属性をデータとして書き出し:
- 全キーの和集合でnull埋め
- `--type` でノードタイプフィルタリング
- `--select` で個別ファイル選択
- `-o` で出力ファイル名指定
- CSV: ヘッダー付きCSV、JSON: 配列形式

**変更ファイル**:
- `cli/graph.py`: `_add_export_args()` 拡張、`_run_export_data()` 追加

### 6. elset/材料名プロパティ追加

parse時にAbaqus材料割り当て情報をgo_*.inpのプロパティに直接追加:
- `materials`: 割り当てられた材料名リスト
- `material_elsets`: `{材料名: [elset名, ...]}` の辞書

**変更ファイル**:
- `services/graph/__init__.py`: `_enrich_material_assignment_props()` 追加、`parse_project()` に統合

### 7. Obsidianタグ出力強化

Obsidianエクスポート時にタグを積極的に付与:
- frontmatterの`tags`リストにタイプ(`go`等)と材料名(`material/Steel`等)を追加
- markdown本文に`#go #test #material/Steel`形式でタグ行を出力

**変更ファイル**:
- `services/connectors/obsidian.py`: `node_to_frontmatter()` タグ拡充、`_format_md()` タグ行追加

## テスト結果

- **272件パス**（+12件）、18件スキップ（CLI環境依存テスト）
- 新規テストクラス:
  - `TestDailyConnectorEnhanced`: Daily紐付けロジック強化テスト（6件）
  - `TestInfoCommandEnhanced`: info検索テスト（5件、CLI依存のためskip）
  - `TestDiffCommand`: diffコマンドテスト（2件、CLI依存のためskip）
  - `TestVerboseName`: verbose_name生成テスト（1件）
  - `TestExportCSVJSON`: CSV/JSONエクスポートテスト（4件、CLI依存のためskip）
  - `TestMaterialAssignmentProps`: 材料割り当てプロパティテスト（1件）
  - `TestObsidianTagExport`: Obsidianタグ出力テスト（3件）

## 変更ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `services/connectors/daily_connector.py` | 変更: Obsidianリンク＋プロパティ記法、ファイルリンク値抽出 |
| `cli/graph.py` | 変更: info強化、diffコマンド追加、export CSV/JSON |
| `cli/__init__.py` | 変更: diffコマンドルーティング追加 |
| `services/graph/__init__.py` | 変更: verbose_name、材料プロパティ追加 |
| `services/connectors/obsidian.py` | 変更: タグ出力強化 |
| `tests/test_graph_feature.py` | 変更: 22件のテスト追加 |

## TODO / 次のステップ

- [ ] `jj info --json` JSON出力オプション
- [ ] `jj diff` のグラフ保存済みデータとの連携（ファイル名からノード検索して前バージョンと自動比較）
- [ ] `jj export --target csv` のカスタムカラム選択オプション
- [ ] daily日報のブロック単位切り出しとNode逆輸入
- [ ] verbose_nameのObsidianエクスポートでの活用（表示名として使用）
- [ ] Obsidianタグの階層化対応（タイプ/カテゴリ/値の3階層）
- [ ] 大量ファイル環境でのCSV/JSONエクスポートパフォーマンス検証

## 確認事項・設計上の懸念

- daily_connector: `[[O-go_idx1.inp]]:key:value`でO-プレフィックスの除去と`.md`拡張子の除去ロジックが追加されたが、`O-`プレフィックスのカスタマイズ（ObsidianConfigで設定可能）との連携が今は固定値。
- verbose_name: vocab辞書が空の場合はraw_nameと同じになるため、propertyに登録しない（不要なデータ増加を防止）。
- CSV/JSON export: list/dict型のプロパティはJSON文字列にシリアライズ。大きなデータの場合はCSVのセルが巨大になる可能性あり。
