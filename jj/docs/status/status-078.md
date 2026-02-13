[READMEへ戻る](../../README.md)

# status-078: CSV配列拡張・Excelダウンロード・REST API拡張

**日付**: 2026-02-13
**担当**: Claude Code

---

## 概要

status-077のTODOから5項目を実装した。

1. **CSV配列: サブディレクトリ内CSV対応**: `go_idx1_w5_t20/history_RF3.csv`のようなサブディレクトリ配置のCSVをhas_output関係でリンクし、配列プロパティとして取り込む。
2. **CSV配列: ヘッダーなしCSV対応**: 1行目が全て数値の場合、col_0, col_1, ... で自動命名してデータとして読み込む。
3. **ダッシュボード: Excelダウンロード機能**: テーブルビュー・保存済みビューにExcelダウンロードボタンを追加（openpyxl利用）。
4. **REST API: POST /api/v1/parse**: プロジェクトの再パースをAPI経由で実行可能にした。
5. **REST API: プロパティ比較フィルター**: `?props.RF3.gt=5&props.temperature.le=400`のようなクエリパラメータによるプロパティ値フィルタリング。

---

## 実装内容

### 1. サブディレクトリCSV対応（OutputRelationParser + CsvArrayParser）

**OutputRelationParser** (`output_parser.py`):
- 従来のbasename接頭辞マッチに加え、サブディレクトリマッチを追加
- パターン: 出力ファイルの親ディレクトリ名が入力ノードのbasenameと一致する場合にリンク
- 重複リンク防止用の`linked`セットを追加

**CsvArrayParser** (`csv_array_parser.py`):
- `_compute_prefix()`関数を新設し、2つの接頭辞決定方式を統合:
  1. トークン差分方式: `go_idx1_w5_t20_RF.csv` → 接頭辞 "RF"
  2. サブディレクトリ方式: `go_idx1_w5_t20/history_RF3.csv` → 接頭辞 "history_RF3"

### 2. ヘッダーなしCSV対応

**CsvArrayParser** (`csv_array_parser.py`):
- `_is_header_row()`関数: 1行目が全て数値に変換可能かで判定
- `_read_csv_arrays()`: ヘッダーなしの場合`col_0, col_1, ...`で自動命名
- csv.DictReaderから手動パースに変更し、ヘッダー有無を動的に判定

### 3. Excelダウンロード機能

**app.py**:
- `_render_excel_download()`関数を追加
- openpyxlが利用可能な場合のみダウンロードボタンを表示
- テーブルページ(`_render_table_page`)と保存済みビュー(`_render_saved_table`)の両方に適用

### 4. POST /api/v1/parse

**routes.py**:
- `POST /api/v1/parse`エンドポイントを追加
- `?full=true`パラメータで--fullモード対応
- パース後にグラフキャッシュをリセットし新しいグラフをロード
- レスポンスにサマリー統計を含む

### 5. プロパティ比較フィルター

**routes.py**:
- クエリパラメータ`props.KEY.OPERATOR`パターンをパース
- 対応オペレータ: eq, ne, gt, ge, lt, le
- `_parse_prop_filters()`: クエリパラメータからフィルター条件を抽出
- `_apply_prop_filters()`: ノードリストにフィルター条件を適用
- `GET /api/v1/nodes`の既存フィルター（type, active, name）と組み合わせ可能

---

## テスト結果

- 新規テスト: **15件**追加
  - `TestCsvArraySubdirectory`: 3件（token_diff, subdirectory, no_match）
  - `TestCsvHeaderlessDetection`: 6件（header_row判定4件, headerless読み込み, header付き読み込み）
  - `TestOutputRelationSubdirectory`: 1件（サブディレクトリCSVリンク確認）
  - `TestRestApiParse`: 1件（parseエンドポイント存在確認）
  - `TestRestApiPropFilter`: 4件（パース, 適用, 複合条件, API経由テスト）
- 全テスト: 164パス、5失敗（既存streamlit未インストール起因）、21スキップ

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `services/parse/parsers/output_parser.py` | サブディレクトリマッチ追加、重複リンク防止 |
| `services/parse/parsers/csv_array_parser.py` | `_compute_prefix()`新設、ヘッダーなしCSV対応、`_is_header_row()`新設 |
| `services/dashboard/app.py` | `_render_excel_download()`追加、テーブル/保存済みビューにボタン追加 |
| `services/api/routes.py` | `POST /api/v1/parse`追加、プロパティ比較フィルター追加 |
| `tests/test_dashboard.py` | 15テスト追加 |
| `docs/status/status-078.md` | 本ステータスファイル |

---

## TODO / 次回引き継ぎ事項

- [ ] 実環境でサブディレクトリCSV取り込みの動作確認
- [ ] 配列プロットページ: 保存済みビュー対応（saved-viewsでarray_plot型追加）
- [ ] 配列プロットページ: フィルタ連携（activeフィルタ等との統合）
- [ ] 物性一覧ページ: 物性比較機能（複数materialの同一プロパティ重ね書き）
- [ ] 物性一覧ページ: materialノードとgo_ノードの使用関係表示
- [ ] ダッシュボード: NG領域塗りつぶし（Baskinカーブ等のconfig定義対応）
- [ ] ダッシュボード: グループ結線（同一条件のデータ点を灰色点線で結線）
- [ ] 他ソフトウェアのダッシュボードコネクター追加（Fluent、LS-DYNA等）
- [ ] プラグイン化Phase 1: jj-sdkパッケージの定義
- [ ] プラグイン化Phase 2: GraphStorage → CacheProviderプロトコル抽象化
- [ ] プラグイン化Phase 3: entry_points動的発見によるコネクタ登録
