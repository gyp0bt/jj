[READMEへ戻る](../../README.md)

# status-079: ダッシュボード機能拡張（配列プロットビュー・物性比較・NG領域・グループ結線）

**日付**: 2026-02-13
**担当**: Claude Code

---

## 概要

status-078のTODOから6項目を実装した。

1. **配列プロットページ: 保存済みビュー対応**: `SavedViewConfig`に`array_plot`タイプを追加。saved-viewsからプレフィックス・X/Y軸・表示モードを設定可能。
2. **配列プロットページ: フィルタ連携**: 配列プロットビューに共有フィルタ（active/type/status）を統合。フィルタ適用後のノードのみグリッド/個別表示。
3. **物性一覧ページ: 物性比較機能**: 複数materialの同一プロパティカーブを重ね書きプロット。プロパティ選択→物性multiselect→overlay表示。
4. **物性一覧ページ: materialノードとgo_ノードの使用関係表示**: `uses_material`関係をたどり、各materialがどのgo_ノードで使われているかをテーブル表示。
5. **ダッシュボード: NG領域塗りつぶし**: config.yaml `ng-regions`で矩形/カーブ型のNG領域を定義。plotlyの`add_shape`/`add_trace`でプロットに赤い塗りつぶしを追加。Baskinカーブ等の参照曲線にも対応。
6. **ダッシュボード: グループ結線**: 同一条件（index等）のデータ点を灰色点線で結線。config `group-line-key`でデフォルト指定可能、UIでも動的選択可能。

---

## 実装内容

### 1. SavedViewConfig: array_plotタイプ

`config/__init__.py`:
- `SavedViewConfig.view_type`に`"array_plot"`を追加
- `array_plot`辞書フィールドを追加（`prefix`, `x`, `y`, `mode`）
- `from_dict()`でarray_plotの読み込み・バリデーション

`app.py`:
- `_render_saved_array_plot()`関数を新設
  - grid/singleモード対応
  - 保存済みフィルタのprovider用変換
  - `_saved_view_filters_to_provider_filters()`ヘルパー

### 2. 配列プロットフィルタ連携

`app.py`:
- `_render_array_plot_page()`に`_render_shared_filters()` + `_get_active_filters()`を追加
- `_get_active_filters()`: session_stateから現在のフィルタ条件をprovider用dictに変換
- `_render_array_grid()`/`_render_array_single()`に`filters`パラメータ追加
- `_render_array_single()`でフィルタ適用後のノードのみ表示

### 3. 物性比較機能

`connectors/abaqus.py`:
- `_render_material_comparison()`関数を新設
  - 全materialのテーブル型プロパティキーを収集
  - プロパティ選択 → 物性multiselect
  - plotly `go.Figure`に複数material traceをオーバーレイ
  - `get_curve_plot_axes()`/`guess_table_column_names()`で軸名・config連携

### 4. 物性使用関係表示

`connectors/abaqus.py`:
- `get_material_usage()`関数を新設
  - `uses_material`関係（go_node → material_node）をたどりgo_ノード一覧を返す
- `_render_material_usage()`関数を新設
  - 物性名・使用GOノード数・使用GOノード名の3列テーブル

### 5. NG領域塗りつぶし

`config/__init__.py`:
- `DashboardConfig.ng_regions`リストフィールド追加
- `from_dict()`で`ng-regions`読み込み

`app.py`:
- `_add_ng_regions()`関数を新設
  - 矩形: `fig.add_shape(type="rect")` + アノテーション
  - カーブ: `fig.add_trace(go.Scatter(fill=...))` 境界線+塗りつぶし
- `_render_plot_page()`の通常モードで適用
- `_render_saved_plot()`でも適用

### 6. グループ結線

`config/__init__.py`:
- `DashboardConfig.group_line_key`フィールド追加
- `from_dict()`で`group-line-key`読み込み

`app.py`:
- `_add_group_lines()`関数を新設
  - `df.groupby(group_key)`でグループ化
  - 2点以上のグループをX軸ソート後、灰色点線(`dash="dot"`)で結線
- `_render_plot_page()`にグループ結線キーselectbox追加
- `_render_saved_plot()`でも適用

---

## アーキテクチャ

```
services/dashboard/
├── app.py                    # 共有フィルタ強化、NG領域・グループ結線・配列プロット保存ビュー
│                              + _get_active_filters()
│                              + _add_ng_regions()
│                              + _add_group_lines()
│                              + _render_saved_array_plot()
├── data_provider.py          # （変更なし、既存filtersパラメータを活用）
└── connectors/
    └── abaqus.py             # 物性比較・使用関係表示
                               + _render_material_comparison()
                               + get_material_usage()
                               + _render_material_usage()

config/
└── __init__.py               # SavedViewConfig.array_plot追加
                               + DashboardConfig.ng_regions追加
                               + DashboardConfig.group_line_key追加

shared/assets/
└── default-config.yaml       # ng-regions/group-line-key/array_plotビュー設定例追加
```

---

## テスト結果

- 新規テスト: **16件**追加
  - `TestSavedViewConfigArrayPlot`: 3件（array_plot受入, デフォルト, 不正タイプ）
  - `TestDashboardConfigNgRegions`: 5件（矩形, カーブ, デフォルト, グループ結線キー, デフォルトNone）
  - `TestMaterialComparison`: 3件（テーブルキー取得, データ取得, 複数material）
  - `TestMaterialUsage`: 2件（使用関係取得, 空グラフ）
  - `TestArrayPlotFilters`: 1件（フィルタ付きgrid_data）
  - `TestNgRegionConfig`: 2件（非リスト, 混合）
- 全テスト: 137パス、30失敗（既存依存ライブラリ未インストール起因）、39スキップ（streamlit等未インストール）

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `config/__init__.py` | `SavedViewConfig`: `array_plot`フィールド+タイプ追加。`DashboardConfig`: `ng_regions`+`group_line_key`追加 |
| `services/dashboard/app.py` | `_get_active_filters()`新設、配列プロットフィルタ連携、`_add_ng_regions()`/`_add_group_lines()`/`_render_saved_array_plot()`新設、プロットビューにNG領域・グループ結線UI |
| `services/dashboard/connectors/abaqus.py` | `_render_material_comparison()`/`get_material_usage()`/`_render_material_usage()`新設 |
| `shared/assets/default-config.yaml` | `ng-regions`/`group-line-key`/`array_plot`保存ビュー設定例追加 |
| `tests/test_dashboard.py` | 16テスト追加（6クラス） |
| `docs/status/status-079.md` | 本ステータスファイル |

---

## TODO / 次回引き継ぎ事項

- [ ] 実環境でNG領域塗りつぶし・グループ結線の動作確認
- [ ] 配列プロット: NG領域対応（現在はプロットビューのみ対応）
- [ ] 物性比較: 異なるプロパティの複合プロット（例: plasticとelasticを同時表示）
- [ ] 物性比較: csvエクスポート
- [ ] 保存済みビューUIからの動的ビュー追加・編集（status-072引き継ぎ）
- [ ] 他ソフトウェアのダッシュボードコネクター追加（Fluent、LS-DYNA等）
- [ ] プラグイン化Phase 1: jj-sdkパッケージの定義
- [ ] プラグイン化Phase 2: GraphStorage → CacheProviderプロトコル抽象化
- [ ] プラグイン化Phase 3: entry_points動的発見によるコネクタ登録

---

## 設計上の懸念

- [ ] NG領域のカーブタイプでfill="above"の場合、plotlyのtonextyは直前のtraceとの間を塗るため、データの描画順序によっては意図しない結果になる可能性がある。実環境での確認が必要。
- [ ] 物性使用関係はuses_material関係の存在を前提。parseで生成されていない場合は空テーブルになる。
