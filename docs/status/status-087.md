[← README.md](../../README.md)

# status-087 — ダッシュボード ページビュー（対話UI）復元

| 項目 | 内容 |
|------|------|
| **日付** | 2026-04-20 |
| **ブランチ** | `claude/fix-dashboard-view-logic-sQTxz` |
| **トラック** | ダッシュボード改善 |

---

## 背景

status-086（commit 13d9179）で `PageComponent` の描画インタフェースを
`render(provider, view, dashboard_config)` に一本化した際、
対話UI（selectbox/shared_filters 等）を伴う `render_page()` 相当のロジックが
すべて削除され、`render_saved_view()` 相当の「config駆動・先頭行表示」の
最小描画に集約された。

その結果、シングルページ化後の実運用で以下の退化が発生:

- **配列プロット**: `view.array_plot` 未指定時に「全組み合わせのプロットが
  連続描画」される（デフォルトが全Yキーになる）
- **ギャラリー**: `view.gallery.source` 未指定時に `has_output` ソース
  （ログ画像等）が既定となり、プロパティ割当て画像ギャラリーが見えなくなる
- **テーブル/カード/ステータス/バッチ俯瞰**: 共有フィルタやノード選択の
  対話性が失われ、設定なしでは情報量が過少

ユーザー要求:
> 元のページビューの方に戻してほしい

status-086 の「render() 単一化」という契約（= view 引数だけで表示が決まる）は
有効。ただし UI を view の **デフォルト値** として採用し、対話UIは view ごとに
キーを分離したうえで重ねることで両立させる。

---

## 実施内容

### 1. 各 PageComponent の `render()` 内に対話UIを復元

`PageComponent.render(provider, view, dashboard_config, **kwargs)` の単一
エントリポイントは維持しつつ、**内部で旧 `render_page` 相当の対話UIを展開する**。
widgetキーは `view.name` でスコープし、シングルページ上に同種ビューが複数
存在しても state collision が起きないようにする。

| ファイル | 復元内容 |
|---------|---------|
| `array_plot.py` | prefix/x/y/group_line/mode 選択、軸範囲・スタイルExpander。widget prefix: `_ap_{view.name}` |
| `plot.py` | X/Y/color/chart selectbox、コンター時Z/vmin/vmax、軸範囲/スタイル。widget prefix: `_plot_{view.name}` |
| `gallery.py` | ソース/列数/行数/group_keys selectbox。`show_source_selector=True` で source を対話選択可能 |
| `table.py` | shared_filters + apply_filters で対話フィルタ適用、AgGrid表示 |
| `card.py` | ノード selectbox（`view.local_filters["node"]` を初期値）。shared_filters 対応 |
| `overview.py` | shared_filters → apply_saved_view_filters → apply_filters → table+gallery |
| `status.py` | shared_filters + view.filters をマージして active_filters を構築 |
| `batch_overview.py` | shared_filters + view_mode/index_filter を `view.name` スコープ化 |
| `run_comparison.py` | 既に対話的（比較対象選択は ephemeral UI）。維持 |

### 2. `widget_key_prefix` の view.name スコープ化

シングルページ上で複数の SavedViewConfig が同一ビュータイプを持つケース
（例: `table` ビューを2枚並べる）に備え、すべての st.selectbox/radio/multiselect
等のキーに `view.name` をサフィックスとして付与。

例: `batch_overview._render_batch_overview()` の `_batch_view_mode` →
`_batch_view_mode_{view_name}`。

### 3. `app.py` に共有フィルタ初期化処理を復元

`services/dashboard/app.py`

- `_init_shared_filters(default_filters)` を復元し、main() 内で呼び出す
- 実行ごとに `st.session_state["_shared_filters_rendered"] = False` をリセット
  （`render_shared_filters` は session_state フラグでの一度だけ描画契約を持つ）
- `is_truthy` を query モジュールから import

### 4. `array_plot.py` のヘルパー関数を再エクスポート

テスト（`TestArrayPlotHelpers`）が期待する:
- `_get_array_plot_defaults(dashboard_config)`
- `_find_key_index(keys, target)`
- `_get_default_y_keys(y_options, config_y)`

を末尾に追加して互換性を回復。

---

## 契約（status-086 の契約を維持）

status-086 で定義した契約は引き続き有効:

**Given**: 同じ `SavedViewConfig view` と同じ `provider`, `dashboard_config`、
かつ同一 session_state
**Then**: `component.render(provider, view, dashboard_config)` は同じ画面を描画する

違いは「対話UI があると session_state に依存する」点のみだが、
widget key を `view.name` でスコープするため他ビューの操作が干渉しない。
view.filters / view.plot / view.array_plot / view.gallery は widget の
**初期値**として採用されるため、保存→再読み込みで同じ初期状態を再現できる。

---

## 確認結果

- `ruff check services/dashboard/` → パス
- `ruff format --check services/dashboard/` → パス
- `pytest tests/test_dashboard.py::TestArrayPlotHelpers tests/test_dashboard.py::TestPageComponentSingleRender` → 全件パス
- `pytest tests/test_dashboard.py` → 6件事前失敗（`TestSelectTableColumns` / `TestQueryModule::test_select_table_columns_*` — 本refactorに無関係な既存バグ）、433 passed, 73 skipped
- `pytest tests/ --ignore=tests/test_dashboard.py` → 3件事前失敗（パーサー2件・select_table_columns 1件）、1691 passed

---

## 未完了TODO

### 継続TODO（他トラック）

- [ ] T7: Ollama AI連携 — フル統合テスト・マニュアル作成
- [ ] T8: 汎用データ管理 — 設計フェーズ以降の実装
- [ ] T9: 共有フォルダ同期 — Windows実環境テスト
- [ ] T10: プラグインコア — CLI統合・APIアダプター・get_page_data()
- [ ] W: Office連携 — Windows実環境テスト
- [ ] M2: マルチソルバー検証環境確保後に本実装

### 既存バグ（別途対応）

- [ ] `services/dashboard/query.py::select_table_columns` の固定カラム
  （name/type/format）自動挿入ロジックが壊れている可能性
  （`test_filters_and_orders` ほか複数テストがFAIL。本refactor対象外）

---

## 開発運用メモ

- **設計判断**: status-086 の「単一 render()」契約は保持したまま、
  対話UIを render() 内に復元することで「view 引数で決まる初期表示 + 対話で
  変化する ephemeral 状態」の両立を図った。これにより保存/復元の単純さを
  維持しつつ、ユーザーが慣れ親しんだ対話操作を取り戻している
- **widget key スコープ化**: シングルページ上で同一ビュータイプを並べるケース
  でも state collision が起きないよう、`view.name` を全 widget key の
  サフィックスとした。これが新しいルール
- **render_shared_filters の冪等性**: `_shared_filters_rendered` フラグで
  複数ビューが同時に呼び出しても一度だけ描画される。app.py 側で実行ごとに
  フラグをリセットすることで再実行時の描画漏れも防止
