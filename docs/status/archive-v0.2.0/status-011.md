[← README.md](../../../README.md) | [← status-index](status-index.md)

# status-011 — 表示名parse時移動・プロットスタイル制御・ギャラリーグルーピング

**日付**: 2026-02-17
**マイルストーン**: M2（マルチソルバー基盤）
**ブランチ**: claude/setup-project-docs-GNDw6

---

## 実施内容

### 1. 表示名ロジックのparse時移動

- `DisplayNameParser`（priority=101）を新規作成
  - VocabFinalizer(100)の後に実行し、`verbose_name_format`テンプレートから表示名を生成
  - vocab変換前・変換後のキー名をどちらでもテンプレート内で参照可能
  - 結果はverbose_nameプロパティ（vocab変換後キー）に格納
- `DashboardDataProvider._get_display_name()`を簡素化
  - parse時に生成済みのverbose_nameプロパティを参照するだけに変更
  - `_apply_verbose_name_format()`メソッドをdata_providerから削除
  - `verbose_name_format`パラメータは後方互換のため残置（使用されない）

### 2. 配列プロットにvmin/vmax追加

- 配列プロットページに「軸範囲設定」expanderを追加
  - X最小/X最大/Y最小/Y最大のnumber_input（`%g`フォーマット）
  - `_render_array_overlay`、`_render_array_grid`、`_render_array_single`に`x_range`/`y_range`パラメータ追加

### 3. プロット/配列プロットにスタイル設定追加

- 「スタイル設定」expanderを追加（プロットビュー・配列プロットビュー両方）
  - マーカーサイズ（1〜50）
  - 線幅（1〜20）
  - フォントサイズ（6〜48）
- `_build_style_config()`ヘルパー関数で設定値をまとめる
- `_apply_style_to_fig()`でplotly Figureにスタイル適用

### 4. ギャラリービューのhas_outputグルーピング

- **負の値記法**: ハイフン直接記法を採用（`vmin-50.0` → vmin=-50.0）
  - `_FLOAT_PROP_PATTERN`を`(-?\d+(?:\.\d+)?)`に更新して負の値をサポート
  - result_key（`S-S13`等）のダッシュとは正規表現で区別可能
- `extract_path_metadata()`関数をquery.pyに新規追加
  - 画像パスからresult_keyとプロパティを抽出
  - ディレクトリ名からのプロパティ（step, frame等）も統合
- `collect_group_keys()`を拡張: outputソースの場合`result_key`グルーピングオプションを追加
- `_render_gallery_grouped()`でresult_keyグルーピングに対応

---

## テスト結果

- **全テスト**: 1085 passed, 59 skipped
- **新規テスト**: 13件追加
  - `TestResultsMetadataParserNegativeValues` (2件): 負の値パース
  - `TestDisplayNameParser` (5件): parse時表示名生成
  - `TestExtractPathMetadata` (6件): パスメタデータ抽出

---

## 変更ファイル

| ファイル | 変更種別 | 概要 |
|---------|---------|------|
| `services/parse/parsers/display_name_parser.py` | 新規 | verbose_name_formatをparse時に適用するパーサー |
| `services/parse/parsers/results_metadata_parser.py` | 修正 | 負の値対応（`_FLOAT_PROP_PATTERN`拡張） |
| `services/dashboard/data_provider.py` | 修正 | `_get_display_name`簡素化、`_apply_verbose_name_format`削除 |
| `services/dashboard/app.py` | 修正 | vmin/vmax、スタイル設定UI、result_keyグルーピング |
| `services/dashboard/query.py` | 修正 | `extract_path_metadata`関数追加、`collect_group_keys`拡張 |
| `tests/test_parser_units.py` | 修正 | 新規テスト13件追加 |
| `tests/test_dashboard.py` | 修正 | VerboseNameFormat関連テストをparse時ロジックに更新 |

---

## 次回TODO

- [ ] ViewConfigComponentサブクラス化: 動的ビュー以外の各ビューのconfig/inputをViewConfigComponentとして実装し、動的ビューは定義済みのPageComponent+ViewConfigComponentを流し込む薄い実装にする（DRY）
- [ ] プロット・配列プロットのグリッドビュー廃止: 基本的に同じグラフに重ねる。スクショ用はギャラリービューを使用
- [ ] ギャラリービューのフィルターロジックにキー名のリスト指定を追加
