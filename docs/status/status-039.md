[← README.md](../../README.md)

# status-039 — HTMLエクスポート: plotスタイル反映・ギャラリー実装

**日付**: 2026-02-20
**マイルストーン**: M2
**ブランチ**: `claude/fix-plot-export-RH76n`

---

## 実施内容

### 1. DashboardConfigにplot_styleフィールド追加

- `DashboardConfig`に`plot_style: dict[str, int]`フィールドを追加
- YAML設定の`dashboard.plot.style`セクションから`marker_size`, `line_width`, `font_size`を読み取り
- ハイフン区切りキー（`marker-size`）にも対応
- デフォルトは空dict（従来の動作を維持）

### 2. `_create_plot_figure`にplot_styleパラメータ追加

- `plot_style`パラメータを追加（オプション）
- マーカーサイズ: `plot_style.marker_size` > デフォルト16
- 線幅: `plot_style.line_width` 指定時のみ適用
- フォントサイズ: `plot_style.font_size` > デフォルト20
- フォント比率計算: title=font_size*24/20, legend=font_size*16/20（`apply_style_to_fig`と統一）

### 3. `generate_plot_html`にスタイル・軸範囲適用

- `view.plot.plot_style`からビュー固有スタイルを読み取り
- `view.plot.axis_range`から軸範囲（x_min, x_max, y_min, y_max）を読み取り
- `_resolve_plot_style()`でDashboardConfigとビュー設定をマージ（ビュー優先）
- `_apply_axis_range()`で軸範囲を適用

### 4. `generate_array_plot_html`にスタイル・軸範囲適用

- `view.array_plot.plot_style`と`view.array_plot.axis_range`に対応
- `_apply_default_layout()`ヘルパーで配列プロットのレイアウトにstyle適用
- overlay/gridの両モードでスタイルと軸範囲を反映
- `display_name`の使用を統一（Streamlit側と同一）

### 5. ギャラリーHTMLエクスポートをbase64画像で実装

- `GalleryPage.generate_html()`を実装（従来は空文字列を返していた）
- has_output/property両ソースに対応
- 画像ファイルをbase64エンコードしてHTMLに埋め込み（スタンドアロン対応）
- プロジェクトルート基準 + notes/daily基準のフォールバックパス解決
- 画像なし/読み取りエラーの適切なフォールバック表示
- CSSグリッドレイアウトで表示

### 6. SavedViewConfig.plotの型拡張

- `dict[str, str | None]` → `dict[str, Any]`に変更
- `plot_style`や`axis_range`などのネスト辞書を許容

---

## テスト結果

- **新規テスト**: 15件追加（全通過）
  - `test_create_plot_figure_with_plot_style`: plot_styleでマーカー・フォント反映
  - `test_create_plot_figure_default_style`: デフォルトスタイル検証
  - `test_resolve_plot_style_merges_config_and_view`: config/view マージ
  - `test_resolve_plot_style_empty`: 空スタイル
  - `test_apply_axis_range`: 軸範囲適用
  - `test_apply_default_layout_with_style`: 配列プロットレイアウト
  - `test_generate_plot_html_with_style_and_range`: HTMLエクスポート統合テスト
  - `test_gallery_html_export_with_output_images`: base64画像エクスポート
  - `test_gallery_html_export_no_images`: 画像なし
  - `test_gallery_html_export_no_project_root`: project_root未指定
  - `test_gallery_html_export_missing_image`: 画像ファイル不在
  - `test_plot_style_from_config`: YAML設定読み取り
  - `test_plot_style_empty_default`: デフォルト空dict
  - `test_plot_style_partial`: 部分指定
  - `test_plot_style_hyphen_keys`: ハイフンキー対応
- **test_dashboard.py**: 352 passed, 30 skipped（ベースライン: 337 passed）
- **lint**: ruff check/format クリーン

---

## 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `config/__init__.py` | DashboardConfigにplot_style追加、SavedViewConfig.plotの型拡張 |
| `services/dashboard/html_export.py` | _create_plot_figureにplot_style対応、generate_plot/array_plot_htmlにスタイル・軸範囲適用、ヘルパー関数追加 |
| `services/dashboard/components/gallery.py` | generate_html実装（base64画像埋め込み）、_generate_gallery_html_grid追加 |
| `tests/test_dashboard.py` | 15件のテスト追加 |

---

## YAML設定例

```yaml
dashboard:
  plot:
    x: RF3
    y: temperature
    style:
      marker_size: 20
      line_width: 3
      font_size: 16
  saved-views:
    - name: "プロット（カスタムスタイル）"
      type: plot
      plot:
        x: RF3
        y: temperature
        plot_style:
          marker_size: 24
        axis_range:
          x_min: 0
          x_max: 100
          y_min: -50
          y_max: 50
    - name: "ギャラリー"
      type: gallery
      gallery:
        source: has_output
```

---

## TODO

- [ ] Streamlit UI側のスタイル設定をSavedViewConfigに永続化する機能
- [ ] contourプロットのvmin/vmax（カラーバー範囲）対応
- [ ] ギャラリーHTMLの画像ファイルサイズ上限設定（大量画像時のHTML肥大化対策）
