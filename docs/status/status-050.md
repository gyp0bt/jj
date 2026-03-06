[← status-index.md](status-index.md) | [← README.md](../../README.md)

# status-050: プロット軸vocab変換・GalleryDefaults参照・Run --show-properties

- **日付**: 2026-03-06
- **マイルストーン**: M2（基盤改善）/ M7（Run中心スキーマ）
- **ブランチ**: `claude/execute-status-todos-ifjHD`

---

## 概要

status-049のTODOから3件を実行:

1. **プロット軸ラベルへのvocab変換適用**: プロットタイトル・軸ラベルにvocab表示名を反映
2. **GalleryDefaults.columns/rows参照**: ギャラリーコンポーネントのグリッド設定をGalleryDefaultsから取得
3. **Run-PropertyトレーサビリティCLI対応**: `jj run --show-properties` でスクリプトのプロパティをdry-run抽出

## 変更内容

### 1. プロット軸ラベルへのvocab変換適用

| ファイル | 変更 |
|---------|------|
| `services/dashboard/html_export.py` | `_create_plot_figure`にvocab引数追加。タイトル・軸ラベルにtranslate_key適用。`generate_plot_html`・`generate_array_plot_html`にvocab引数追加 |
| `services/dashboard/components/plot.py` | `render_page`・`render_saved_view`・`generate_html`でvocabをkwargsから取得し`_create_plot_figure`に渡す |
| `services/dashboard/components/array_plot.py` | `render_page`・`render_saved_view`・`generate_html`でvocab対応。`_render_array_overlay`・`_render_array_single`にvocab引数追加。軸ラベルにtranslate_key適用 |

**変換ロジック**:
- `_create_plot_figure`内でvocabを受け取り、`translate_key(x_key, vocab)`でx/y/z各軸の表示名を取得
- タイトル(`f"{y_label} vs {x_label}"`)と`fig.update_xaxes(title_text=x_label)`で表示名を設定
- vocab未指定時は従来通り生キーがそのまま使用される

### 2. GalleryDefaults.columns/rows参照

| ファイル | 変更 |
|---------|------|
| `services/dashboard/components/gallery.py` | `_get_gallery_settings()`ヘルパー関数追加。gallery_defaultsを優先参照し、未設定時はgallery_columns/rowsにフォールバック。全4箇所のgetattr呼び出しを統一 |

**設計**:
- `_get_gallery_settings()` → `(cols_per_row, rows_per_page, max_image_bytes)` タプルを返す
- `dashboard_config.gallery_defaults` が存在すればその `columns`, `rows`, `max_image_bytes` を使用
- 存在しなければ従来の `gallery_columns`, `gallery_rows` にフォールバック

### 3. Run-PropertyトレーサビリティCLI対応

| ファイル | 変更 |
|---------|------|
| `services/run/__init__.py` | `RunService.show_properties(command, cwd)`メソッド追加。コマンドを実行せずにプロパティを抽出 |
| `services/cli/__init__.py` | `--show-properties`フラグ追加。指定時はRunServiceを直接呼び出し、プロパティ表示のみで終了 |

**使い方**:
```bash
jj run --show-properties -- python run_script.py arg1 arg2
```

### 4. テスト追加

| ファイル | 変更 |
|---------|------|
| `tests/test_dashboard.py` | `TestPlotVocabAxisLabels`(3件)、`TestGalleryDefaultsConfig`(2件)、`TestRunShowProperties`(3件) = 計8件追加 |

## テスト結果

- **ruff check**: All checks passed
- **ruff format**: 213 files already formatted
- **pytest**: 1575 passed, 92 skipped（新規8件含む）

## TODO

- [ ] M7 Phase 5: Run比較ダッシュボード（RunQueryServiceとの統合）
- [ ] M7 Phase 6: Neo4j Run Node対応
- [ ] バッチ俯瞰ページでRunノード（NodeCategory.RUN）との統合表示
- [ ] 配列プロットの凡例名へのvocab変換適用
- [ ] generate_array_plot_htmlのモード別（overlay/grid）vocab対応確認

## 確認事項・懸念

- `_create_plot_figure`のvocab引数はオプショナルで後方互換。既存のテストは全件通過
- GalleryDefaults参照とgallery_columns/rowsの二重構造は残存。将来的にはGalleryDefaultsに一本化してgallery_columns/rowsを廃止する方が望ましい
- `--show-properties`は実行なしでプロパティを確認する機能。CI/CDパイプラインでの事前検証に有用
