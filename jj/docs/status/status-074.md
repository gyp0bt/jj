[READMEへ戻る](../../README.md)

# status-074: CSVパース配列取り込み・ダッシュボード配列プロット・物性一覧

**日付**: 2026-02-12
**担当**: Claude Code

---

## 概要

GOノードに紐づくCSVファイルの配列データ自動取り込みパーサーの追加と、ダッシュボードへの「配列プロット」「物性一覧」ページの追加を実施。

---

## 実装内容

### 1. CsvArrayParser（新規パーサー）

has_output関係で紐づいたCSVファイルを読み取り、GOノードのプロパティに配列データとして格納する。

**ファイル名トークン差分検出ロジック**:
- 入力ファイル: `go_idx1_w5_t20.inp` (トークン: go, idx1, w5, t20)
- CSVファイル: `go_idx1_w5_t20_RF.csv` (トークン: go, idx1, w5, t20, RF)
- 差分トークン: "RF" → 接頭辞として使用

**格納形式**:
```
node.properties["RF.time"] = [0.0, 0.1, 0.2, 0.5, 1.0]
node.properties["RF.RF1"] = [0.0, 10.5, 25.1, 50.0, 45.2]
node.properties["RF.RF3"] = [0.0, 15.3, 38.7, 80.5, 73.0]
```

| 項目 | 内容 |
|------|------|
| ファイル | `services/parse/parsers/csv_array_parser.py` (新規) |
| パーサー | `CsvArrayParser` (priority=33, OutputRelationParserの直後) |
| 関数 | `_compute_extra_token()`: トークン差分検出 |
| 関数 | `_read_csv_arrays()`: CSV→列名-数値配列の辞書変換 |
| 登録 | `services/parse/parsers/__init__.py` に追加 |

### 2. ダッシュボード: 配列プロットページ

GOノードの配列プロパティ（RF.time vs RF.RF3等）をラインプロットで可視化。

**機能**:
- データグループ選択（接頭辞: RF, stress等）
- X軸/Y軸選択（複数Y軸選択可能）
- 2つの表示モード:
  - **グリッド比較**: indexごとに個別プロットをNxMグリッドで並べて比較
  - **個別ノード**: 特定ノードの複数Y軸を重ね書き

| 関数 | 内容 |
|------|------|
| `_render_array_plot_page()` | 配列プロットページのメインUI |
| `_render_array_grid()` | グリッド比較表示（indexソート） |
| `_render_array_single()` | 個別ノードの重ね書き表示 |

### 3. ダッシュボード: 物性一覧ページ

abaqus_materialノードの物性情報をテーブル表示し、テーブル型データ（plastic, elastic等）をラインプロットで可視化。

**機能**:
- 物性テーブル: 全abaqus_materialノードの物性一覧（AgGrid対応）
- 物性カーブ: 選択した物性の応力-ひずみ曲線等をラインプロット
- テーブル型データのテーブル表示（数値行データ）
- 列名の自動推定（plastic→stress/strain, elastic→E/nu等）

| 関数 | 内容 |
|------|------|
| `_render_material_page()` | 物性一覧ページのメインUI |
| `_guess_table_column_names()` | プロパティキーから列名を推定 |

### 4. DashboardDataProvider 拡張

| メソッド | 内容 |
|------|------|
| `get_array_property_keys()` | ドット記法(PREFIX.列名)の配列キー一覧 |
| `get_array_plot_data()` | 特定ノードの配列データ（重ね書き用） |
| `get_array_grid_data()` | 全GOノードの配列データ（グリッド比較用） |
| `get_material_table()` | abaqus_materialノードの物性テーブル |
| `get_material_table_data()` | テーブル型プロパティの生データ取得 |
| `get_material_table_keys()` | テーブル型プロパティキー一覧 |

---

## テスト結果

- 新規テスト: **22件**追加
  - `TestCsvArrayParser`: 7件（トークン差分検出、CSV配列読み取り）
  - `TestGetArrayPropertyKeys`: 2件（キー抽出、空グラフ）
  - `TestGetArrayPlotData`: 3件（全系列自動選択、明示指定、存在しないノード）
  - `TestGetArrayGridData`: 2件（グリッドデータ、配列なし除外）
  - `TestGetMaterialTable`: 3件（物性行、テーブルサマリ、goノード除外）
  - `TestGetMaterialTableData`: 3件（テーブルデータ、存在しないノード、非テーブル型）
  - `TestGetMaterialTableKeys`: 2件（テーブルキー、goノード）
  - `TestGuessTableColumnNames`: 3件（plastic/elastic/不明キー列名推定、streamlitスキップ）
- 既存テスト: リグレッションなし

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `services/parse/parsers/csv_array_parser.py` | 新規: CsvArrayParserパーサー |
| `services/parse/parsers/__init__.py` | CsvArrayParserのimport・登録追加 |
| `services/dashboard/data_provider.py` | 6メソッド追加（配列データ・物性テーブル） |
| `services/dashboard/app.py` | 配列プロットページ・物性一覧ページ追加（5関数追加） |
| `tests/test_dashboard.py` | 22件テスト追加 |
| `tests/fixtures/graph_test1/go_idx1_w5_t20_RF.csv` | テスト用CSVデータ追加 |
| `docs/status/status-074.md` | 本ステータスファイル |

---

## TODO / 次回引き継ぎ事項

- [ ] 実環境でCSV配列取り込みの動作確認（実プロジェクトのparse実行）
- [ ] 配列プロットページ: 保存済みビュー対応（saved-viewsでarray_plot型追加）
- [ ] 配列プロットページ: フィルタ連携（activeフィルタ等との統合）
- [ ] 物性一覧ページ: 物性比較機能（複数materialの同一プロパティ重ね書き）
- [ ] 物性一覧ページ: materialノードとgo_ノードの使用関係表示
- [ ] CSV配列: サブディレクトリ内CSV（go_idx1_w5_t20/history_RF3.csv）の対応
- [ ] CSV配列: ヘッダーなしCSVへの対応（数値のみの場合のcol_N自動命名）
- [ ] status-072のTODO引き継ぎ（UIからの動的ビュー保存、Excelダウンロード等）

---

## 設計上の懸念

- `_compute_extra_token()` のトークンマッチングはリスト内の完全一致ベース。同一トークンが複数回出現するファイル名（例: `go_w5_w5_RF.csv`）では誤検出の可能性がある。実運用でのファイル命名規約との整合を要確認。
- `get_array_plot_data()` と `get_array_grid_data()` は配列データを全件メモリロードする。大量データの場合はページネーションまたはサンプリングの検討が必要。
- 物性カーブの列名推定（`_guess_table_column_names()`）はハードコード。Abaqusの各キーワードのオプション（ HARDENING=KINEMATIC等）に応じた列名推定は未対応。
