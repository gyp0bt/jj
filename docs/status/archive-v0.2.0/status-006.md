[← README.md](../../../README.md)

# status-006 — ダッシュボード表示改善（配列プロット・ギャラリー）

- **日付**: 2026-02-16
- **マイルストーン**: M2
- **ブランチ**: claude/fix-dashboard-display-CcLtb

---

## 実施内容

### 1. 配列プロット: 全条件比較モード追加

- `_render_array_overlay()` 関数を新設。全条件（GOノード）の配列データを凡例付きで同一Plotlyグラフに重ね書き
- 表示モードに「全条件比較」を追加（デフォルト選択）、既存の「グリッド比較」「個別ノード」も維持
- 保存済みビュー（`_render_saved_array_plot`）にも `mode: overlay` をサポート
- HTMLエクスポート（`generate_array_plot_html`）にもoverlayモードを実装
- `mode`のデフォルト値を `grid` → `overlay` に変更

**変更ファイル**:
- `jj/services/dashboard/app.py` — `_render_array_overlay()`新設、`_render_array_plot_page()`のモード追加、`_render_saved_array_plot()`のoverlay対応
- `jj/services/dashboard/html_export.py` — `generate_array_plot_html()`にoverlay/gridモード分岐追加

### 2. ギャラリービュー: デフォルトグループ表示

- has_output関係画像: グループ表示のデフォルトを最初の利用可能キーに変更（従来は「なし」）
- プロパティ画像パス: グループ表示のデフォルトを `property_key` に変更（同じキーの画像がグループ化される）

**変更ファイル**:
- `jj/services/dashboard/app.py` — `_render_gallery_output_images()`と`_render_gallery_property_images()`のデフォルトグループ設定

### 3. default-config.yaml更新

- `saved-views`のarray_plotサンプルの`mode`を`overlay`に更新
- array_plotの`mode`オプション説明（overlay/grid/single）を追記

**変更ファイル**:
- `shared/assets/default-config.yaml` — saved-viewsコメント更新

---

## ビュー保存機能の所在

ビュー保存機能は以下の場所に実装されている:

| 種類 | 場所 | 説明 |
|------|------|------|
| 静的ビュー（config定義） | `.j2/config/config.yaml` の `dashboard.saved-views` | YAML定義、永続化 |
| 動的ビュー（セッション中） | `app.py:1201-1286` `_render_saved_views_page()` | `st.session_state["_dynamic_views"]`に保存 |
| 動的ビュー追加フォーム | `app.py:1634-1724` `_render_view_add_form()` | UIから新規ビュー作成 |
| 動的ビュー編集フォーム | `app.py:1727-1788` `_render_view_edit_form()` | UIからビュー編集 |
| HTMLエクスポート | `app.py:1595-1631` `_render_html_export_button()` | 保存済みビューをHTMLファイルに出力 |

**注意**: 動的ビューはStreamlitのセッション状態に保存されるため、ブラウザを閉じると消える。永続化するには`config.yaml`の`saved-views`に手動で転記する必要がある。

---

## テスト結果

- 251 passed, 38 skipped（既存のpandas未インストールによる1件のfailは本変更と無関係）

---

## 確認事項・TODO

- [ ] 動的ビューの永続化（config.yamlへの自動保存）は将来的な改善候補
- [ ] array_plotのoverlayモードで条件数が多い場合（20+）の視認性確認が必要
