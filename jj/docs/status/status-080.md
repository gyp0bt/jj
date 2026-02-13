[READMEへ戻る](../../README.md)

# status-080: ダッシュボード機能拡張（配列NG領域・物性CSV・動的ビュー・HTMLエクスポート）

**日付**: 2026-02-13
**担当**: Claude Code

---

## 概要

status-079のTODOから4項目を実装し、HTMLエクスポート機能を新規追加した。

1. **配列プロット: NG領域対応**: グリッド比較・個別ノード・保存済みビューの全配列プロットモードでNG領域塗りつぶしに対応。
2. **物性比較: CSVエクスポート**: 複数materialの比較データをCSVとしてダウンロード可能に。material名列+各列名でフォーマット。
3. **保存済みビューUIからの動的ビュー追加・編集**: session_stateベースで保存済みビューを動的に追加・編集・削除。config.yamlビューと共存。
4. **保存済みビュー: HTMLエクスポート**: 保存済みビュー一覧をスタンドアロンHTMLファイルとして出力。plotlyプロット・テーブル・ステータスをインライン化。

---

## 実装内容

### 1. 配列プロットNG領域対応

`app.py`:
- `_render_array_plot_page()`: `ng_regions`をdashboard_configから取得し下位関数に渡す
- `_render_array_grid()`: `ng_regions`引数追加、各グリッドプロットに`_add_ng_regions()`適用
- `_render_array_single()`: `ng_regions`引数追加、個別ノードプロットに`_add_ng_regions()`適用
- `_render_saved_array_plot()`: single/gridの両モードでNG領域適用

### 2. 物性比較CSVエクスポート

`connectors/abaqus.py`:
- `_render_material_comparison()`: 比較データをpandas DataFrameに収集
  - material名 + config由来列名でCSVフォーマット
  - `st.download_button()`でUTF-8 BOM付きCSVダウンロードを提供

### 3. 動的ビュー追加・編集

`app.py`:
- `_render_saved_views_page()`: session_state `_dynamic_views` で動的ビューを管理
  - config.yamlの静的ビュー + 動的ビューを統合表示
  - 動的ビューには編集・削除ボタンを表示
- `_render_view_add_form()`: 新規ビュー追加UI
  - ビュー名・タイプ・フィルタ・タイプ固有設定（plot/array_plot/gallery）
  - `SavedViewConfig.from_dict()`で検証してsession_stateに保存
- `_render_view_edit_form()`: 動的ビュー編集UI
  - 名前・タイプ・フィルタの変更に対応

### 4. HTMLエクスポート

`app.py`:
- `_render_html_export_button()`: 保存済みビューページにHTMLエクスポートボタンを配置
- `_generate_saved_views_html()`: 全ビューをまとめてスタンドアロンHTML生成
  - plotly CDN参照、CSSスタイル付き
  - プロジェクト名・生成日時のメタ情報含む
- `_generate_view_html()`: ビュータイプ別のHTML断片ディスパッチ
- `_generate_table_html()`: テーブルビューのHTML（pandas to_html）
- `_generate_plot_html()`: プロットビューのHTML（plotly to_html inline）
  - NG領域・グループ結線も反映
- `_generate_array_plot_html()`: 配列プロットのHTML（CSSグリッドでレイアウト）
  - NG領域も反映
- `_generate_status_html()`: ステータスモニターのHTML
- `_generate_card_html()`: カードビューのHTML

---

## アーキテクチャ

```
services/dashboard/
├── app.py                    # 配列NG領域・動的ビュー管理・HTMLエクスポート
│                              + _render_array_grid() ng_regions引数
│                              + _render_array_single() ng_regions引数
│                              + _render_html_export_button()
│                              + _generate_saved_views_html()
│                              + _generate_*_html() (table/plot/array_plot/status/card)
│                              + _render_view_add_form()
│                              + _render_view_edit_form()
└── connectors/
    └── abaqus.py             # 物性比較CSVエクスポート
                               + comparison_data収集 + st.download_button
```

---

## テスト結果

- 新規テスト: **11件**追加
  - `TestMaterialComparisonCsv`: 2件（比較データ収集、CSVフォーマット）
  - `TestHtmlExport`: 6件（テーブル/フィルタ付きテーブル/ステータス/プロット/カード/全体HTML生成）※streamlit未インストール時はスキップ
  - `TestDynamicViews`: 3件（テーブル/プロット/配列プロットの動的ビュー変換）
- 全テスト: 142パス、28スキップ（streamlit等未インストール起因）、5失敗（既存のstreamlit未インストール起因）

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `services/dashboard/app.py` | 配列プロットNG領域対応、動的ビュー管理UI、HTMLエクスポート機能追加 |
| `services/dashboard/connectors/abaqus.py` | 物性比較CSVエクスポート機能追加 |
| `tests/test_dashboard.py` | 11テスト追加（TestMaterialComparisonCsv/TestHtmlExport/TestDynamicViews） |
| `docs/status/status-080.md` | 本ステータスファイル |

---

## TODO / 次回引き継ぎ事項

- [ ] 動的ビューのconfig.yamlへの書き出し（永続化）
- [ ] HTMLエクスポート: ギャラリー画像のBase64インライン化対応
- [ ] HTMLエクスポート: CLIコマンド化（`jj export --target html`）
- [ ] 他ソフトウェアのダッシュボードコネクター追加（Fluent、HFSS、LS-DYNA）→ 着手時期はオーナー指示待ち
- [ ] プラグイン化Phase 1: jj-sdkパッケージの定義
- [ ] プラグイン化Phase 2: GraphStorage → CacheProviderプロトコル抽象化
- [ ] プラグイン化Phase 3: entry_points動的発見によるコネクタ登録

---

## 設計上の懸念

- [ ] HTMLエクスポートのplotlyプロットはCDN参照（`plotly-latest.min.js`）のため、オフライン環境では表示されない。`include_plotlyjs="cdn"`をTrue（インライン）に切り替えるオプションが必要になる可能性がある。
- [ ] 動的ビューはsession_stateに保存されるため、ブラウザリロードで消失する。config.yamlへの書き出し機能が必要。
- [ ] 物性使用関係はuses_material関係の存在を前提。parseで生成されていない場合は空テーブルになる。
