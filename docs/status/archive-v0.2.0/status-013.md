[← README.md](../../../README.md) | [← status-index](status-index.md)

# status-013 — PageComponent描画ロジック移動・HTMLエクスポート統合・プラグインローダー

**日付**: 2026-02-17
**マイルストーン**: M2（マルチソルバー基盤）
**ブランチ**: claude/execute-status-todos-GIwd1

---

## 実施内容

status-012のTODO 3件をすべて実施。

### 1. 描画ロジック移動: app.py → PageComponent

app.pyの`_render_*`関数群（~1,350行）をPageComponentサブクラスに完全移動。app.pyを「オーケストレーション層」として薄くし、各ページの描画責務をコンポーネントに集約した。

- **移動元**（app.py から削除）:
  - `_render_table_page()`, `_render_saved_table()`
  - `_render_card_page()`, `_render_saved_card()`
  - `_render_plot_page()`, `_render_saved_plot()`
  - `_render_array_plot_page()`, `_render_array_overlay()`, `_render_array_single()`, `_render_saved_array_plot()`
  - `_render_status_page()`
  - `_render_gallery_page()`, `_render_gallery_output_images()`, `_render_gallery_property_images()`, `_render_gallery_grouped()`, `_render_image_grid()`, `_render_saved_gallery()`

- **移動先**（各コンポーネントに`render_page()`, `render_saved_view()`, `generate_html()`を完全実装）:
  - `components/table.py`: テーブルビュー（AgGrid、Excel出力、vocab列順序）
  - `components/card.py`: カードビュー（ノード選択、プロパティ・リレーション表示）
  - `components/plot.py`: プロットビュー（軸選択、チャートタイプ、NG領域、グループ結線、スタイル）
  - `components/array_plot.py`: 配列プロットビュー（全条件比較、個別ノード、スタイル）
  - `components/status.py`: ステータスビュー（メトリクス、ステータス別DataFrame）
  - `components/gallery.py`: ギャラリービュー（output/property画像、グループ表示、ページネーション）

- **共有ヘルパー**（`widgets.py`に新規追加）:
  - `render_shared_filters()`: 共有フィルタのサイドバー描画
  - `get_active_filters()`: 適用中のフィルタ取得
  - `render_excel_download()`: DataFrameのExcelダウンロードボタン
  - `build_axis_range()`: 軸範囲設定の構築
  - `build_style_config()`: スタイル設定の構築
  - `apply_style_to_fig()`: Plotly figureへのスタイル適用

- **app.py行数**: ~1,920行 → ~569行（約70%削減）
- **後方互換**: `_try_render_aggrid()`, `_estimate_column_width()` はテスト用にapp.pyに残置

### 2. HTMLエクスポート: PageComponentレジストリ統合

html_export.pyの`generate_view_html()`をif/elifディスパッチからPageComponentレジストリベースに変更。

- **変更前**: `if view.view_type == "table": ... elif "plot": ...`（6分岐）
- **変更後**: `get_page_component(view.view_type).generate_html(...)`（レジストリルックアップ）
- 各PageComponentサブクラスに`generate_html()`メソッドを実装:
  - table → `html_export.generate_table_html()`
  - card → `html_export.generate_card_html()`
  - plot → `html_export.generate_plot_html()`
  - array_plot → `html_export.generate_array_plot_html()`
  - status → `html_export.generate_status_html()`
  - gallery → 空文字列（ローカルパス依存のため未対応）
- 外部プラグインがPageComponentサブクラスでgenerate_html()を実装すれば自動的にHTMLエクスポート対応

### 3. プラグインパッケージ: エントリーポイントローダー

`components/__init__.py`に`load_dashboard_plugins()`を追加。`jj.dashboard_pages`エントリーポイントグループから外部プラグインのPageComponent/ViewConfigを動的ロード。

- `importlib.metadata.entry_points()` を使用（Python 3.10〜3.12+対応）
- 一度だけロード（`_plugins_loaded`フラグ）
- `app.py`の`main()`冒頭で呼び出し
- pyproject.tomlに使用例コメント追加

---

## アーキテクチャ変更

### 変更前の責務分離

```
app.py (描画層・1920行)
  ├── main() オーケストレーション
  ├── _render_table_page() ... 各ページの描画ロジック全部入り
  ├── _render_saved_table() ... 保存済みビュー描画も全部入り
  └── 共有ヘルパー

components/ (薄いブリッジ)
  └── render_page() → app._render_*() を呼ぶだけ

html_export.py
  └── generate_view_html() → if/elif 6分岐
```

### 変更後の責務分離

```
app.py (オーケストレーション層・569行)
  ├── main() グラフ読込・ページルーティング
  ├── _render_saved_views_page() ビュー管理UI
  ├── _render_view_add_form() / _render_view_edit_form()
  └── load_dashboard_plugins() 呼び出し

components/ (描画層)
  ├── __init__.py 基底クラス + レジストリ + プラグインローダー
  ├── table.py    render_page() + render_saved_view() + generate_html()
  ├── card.py     render_page() + render_saved_view() + generate_html()
  ├── plot.py     render_page() + render_saved_view() + generate_html()
  ├── array_plot.py render_page() + render_saved_view() + generate_html()
  ├── status.py   render_page() + render_saved_view() + generate_html()
  └── gallery.py  render_page() + render_saved_view() + generate_html()

widgets.py (共有UIヘルパー)
  └── render_shared_filters(), get_active_filters(), render_excel_download(), ...

html_export.py
  └── generate_view_html() → PageComponent._registry ルックアップ
```

---

## テスト結果

- **全テスト**: 588 passed, 57 skipped, 1 failed（pymesh依存の既存テスト）
- **既存テスト**: 全パス継続（破壊なし）
- ruff lint: All checks passed
- ruff format: 173 files already formatted

---

## 変更ファイル

| ファイル | 変更種別 | 概要 |
|---------|---------|------|
| `services/dashboard/components/__init__.py` | 修正 | `generate_html()`基底メソッド追加、`load_dashboard_plugins()`追加 |
| `services/dashboard/components/table.py` | 修正 | `render_page()`, `render_saved_view()`, `generate_html()` 完全実装 |
| `services/dashboard/components/card.py` | 修正 | `render_page()`, `render_saved_view()`, `generate_html()` 完全実装 |
| `services/dashboard/components/plot.py` | 修正 | `render_page()`, `render_saved_view()`, `generate_html()` 完全実装 |
| `services/dashboard/components/array_plot.py` | 修正 | `render_page()`, `render_saved_view()`, `generate_html()` 完全実装 |
| `services/dashboard/components/status.py` | 修正 | `render_page()`, `render_saved_view()`, `generate_html()` 完全実装 |
| `services/dashboard/components/gallery.py` | 修正 | `render_page()`, `render_saved_view()`, `generate_html()` 完全実装 |
| `services/dashboard/widgets.py` | 修正 | 共有ヘルパー追加（6関数） |
| `services/dashboard/html_export.py` | 修正 | `generate_view_html()`レジストリベース化 |
| `services/dashboard/app.py` | 修正 | 描画ロジック削除、オーケストレーション層に集約（~1920→~569行） |
| `pyproject.toml` | 修正 | `jj.dashboard_pages`エントリーポイント使用例コメント追加 |

---

## 次回TODO

- [ ] DashboardPageConnector（ソルバー別コネクターページ）もPageComponentパターンに統合検討
- [ ] ダッシュボードのE2Eテスト追加（Streamlit TestRunnerの導入検討）
- [ ] 外部プラグインパッケージの実例作成（pyproject.toml + entry_points設定のサンプル）


---

## 追記 (2026‑02‑17, nishioka)

- `DisplayNameParser` がインポートされていないため実行されなかったバグを発見し、修正しました。
- Plotly の描画設定ロジックを細かく調整しました。

## 追加 TODO

- [ ] 動的ビューの入力項目をページビューと一致させる。合わせられない場合は、ページビュー側のリファクタリングを行う。
- [ ] 解析結果の保存構造を見直す。現在の `results/` 配下のロジックは使いにくいため、`results/go_idx1_v1/` のようにディレクトリを作成し、その中に `S‑S33_step0_frame10.png` や `RF.csv` を配置する方式へ変更する。後方互換性は維持しつつ、新方式で対応する。この方式では、`results` 配下のディレクトリ・ファイルもノード化する。
- [ ] `material` 上部テーブルで `verbose_name` 列が空になっている問題を修正し、`verbose_name` を表示名（`vocab` で置換されたもの）に置き換える。
- [ ] テーブルビューにおいて、桁数の大きい浮動小数点が指数表記ではなく、普通の小数表記で表示されている不具合を修正する。
- [ ] メッシュ品質関連のバグを総括的に修正する。具体的には、`mesh_quality` が単一の mesh ファイル以外でパースされず、`elset` ごとのメッシュ統計が取得できない問題を解消する。
