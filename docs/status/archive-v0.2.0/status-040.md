[← README.md](../../../README.md)

# status-040 — status-039 TODO実行: スタイル永続化・コンタープロット・ギャラリーサイズ上限

**日付**: 2026-02-21
**マイルストーン**: M2
**ブランチ**: `claude/execute-status-todos-Mlumt`

---

## 実施内容

### 1. Streamlit UI側のスタイル設定をSavedViewConfigに永続化

- `PlotViewConfig.render_add_form()`にスタイル設定（マーカーサイズ・線幅・フォントサイズ）のexpander UIを追加
- `PlotViewConfig.render_add_form()`に軸範囲設定（X/Y最小・最大）のexpander UIを追加
- 設定値を`plot_style`/`axis_range`としてSavedViewConfigのplot辞書に含めて保存
- `PlotPage.render_saved_view()`で保存済みの`plot_style`と`axis_range`を読み取り反映
- `_resolve_plot_style()`によるビュー設定 > DashboardConfig > デフォルトの優先マージを適用

### 2. コンタープロットのvmin/vmax（カラーバー範囲）対応

- チャートタイプ選択肢に「コンター」を追加（`render_page()`・`render_add_form()`・`render_saved_view()`）
- コンター選択時にZ軸キー選択UI・vmin/vmax設定UIを表示
- `_create_plot_figure()`に`z_key`・`color_range`パラメータを追加
- コンタープロットは`px.scatter`ベースで`color_continuous_scale="Viridis"`を使用
- `range_color=[vmin, vmax]`でカラーバー範囲を制御
- Z軸キーをextra_keysに含めてデータ取得時に含める
- HTMLエクスポート（`generate_plot_html`）にも同一のコンター対応

### 3. ギャラリーHTMLの画像ファイルサイズ上限設定

- `DashboardConfig`に`gallery_max_image_bytes: int`フィールドを追加
- YAML設定の`dashboard.gallery-max-image-bytes`で制御（デフォルト: 5MB、空dict時: 0=無制限）
- `_generate_gallery_html_grid()`に`max_image_bytes`パラメータを追加
- 上限超過時は「スキップ: X.XMB（上限 Y.YMB）」と表示（黄色文字）
- スキップ件数をキャプション表示に反映
- `GalleryPage.generate_html()`で`DashboardConfig`からmax_image_bytesを取得して渡す

---

## テスト結果

- **新規テスト**: 10件追加（全通過）
  - `test_create_plot_figure_contour`: コンターチャートタイプの基本テスト
  - `test_create_plot_figure_contour_no_z_key`: Z軸未指定のコンター
  - `test_create_plot_figure_contour_with_color_range`: vmin/vmaxカラーバー範囲テスト
  - `test_saved_view_with_plot_style`: SavedViewConfigにplot_style/axis_range永続化
  - `test_saved_view_with_contour_config`: SavedViewConfigにz/color_range永続化
  - `test_gallery_max_image_bytes_config`: 設定値の読み取り
  - `test_gallery_max_image_bytes_default`: デフォルト値（空dict=0）
  - `test_gallery_max_image_bytes_default_with_data`: データあり時のデフォルト（5MB）
  - `test_gallery_html_skips_large_images`: サイズ超過スキップ動作
  - `test_gallery_html_no_limit`: 無制限設定の動作
- **test_dashboard.py**: 362 passed, 30 skipped（ベースライン: 352 passed）
- **lint**: ruff check/format クリーン

---

## 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `config/__init__.py` | DashboardConfigにgallery_max_image_bytes追加、from_dictで読み取り |
| `services/dashboard/components/plot.py` | PlotViewConfigにスタイル/軸範囲/コンターUI追加、render_saved_viewにスタイル反映 |
| `services/dashboard/html_export.py` | _create_plot_figureにz_key/color_range追加、generate_plot_htmlにコンター対応 |
| `services/dashboard/components/gallery.py` | _generate_gallery_html_gridにmax_image_bytes対応、generate_htmlから設定値渡し |
| `tests/test_dashboard.py` | 10件の新規テスト追加 |

---

## YAML設定例

```yaml
dashboard:
  gallery-max-image-bytes: 5242880  # 5MB（デフォルト）
  saved-views:
    - name: "コンタープロット"
      type: plot
      plot:
        x: RF3
        y: RF2
        chart_type: コンター
        z: temperature
        color_range:
          vmin: 0
          vmax: 500
    - name: "スタイル付きプロット"
      type: plot
      plot:
        x: RF3
        y: temperature
        plot_style:
          marker_size: 24
          font_size: 14
        axis_range:
          x_min: 0
          x_max: 100
```

---

## TODO

- [ ] コンタープロットの等高線モード（`px.density_contour`）対応
- [ ] ギャラリーHTMLでの画像リサイズ（上限超過時にサムネイル生成）
- [ ] プロット設定の動的ビュー編集フォームへの反映（`_render_view_edit_form`でplot_style/axis_range/z/color_range編集）
