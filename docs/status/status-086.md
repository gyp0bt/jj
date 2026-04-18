[← README.md](../../README.md)

# status-086 — PageComponent描画インタフェースの単一化（render()一本化）

| 項目 | 内容 |
|------|------|
| **日付** | 2026-04-18 |
| **ブランチ** | `claude/dashboard-single-page-YMTol` |
| **トラック** | ダッシュボード改善 |

---

## 背景

status-085 で enabled_pages を `list[SavedViewConfig]` 駆動に統一したが、
`PageComponent` には依然として:

- `render_page(provider, dashboard_config)` — 対話ウィジェットで状態収集
- `render_saved_view(provider, view, dashboard_config)` — SavedViewConfig駆動

の2メソッドが並存していた。これが諸悪の根源だった:

1. `render_page` は内部で `st.selectbox`, `st.number_input` などを使って
   状態を収集するため、その状態は streamlit の `session_state` に一時的に
   存在する → 保存ボタンで snapshot するのが困難
2. `render_page` と `render_saved_view` で同じ画面に対し異なるコードパスが
   あるため、仕様・挙動が乖離する
3. plugin 作者が「どっちを実装すべきか」迷う

**指摘された設計原則**: ページを「引数で完全に状態を受け取る単一ロジック」に
すれば、保存機能は SavedViewConfig を永続化するだけで確実に機能する。

---

## 実施内容

### 1. PageComponent を単一 `render()` に統合

`services/dashboard/components/__init__.py`

- `render_page()` と `render_saved_view()` を削除
- 唯一のエントリポイントとして `render(provider, view, dashboard_config, **kwargs)`
  を定義。`view: SavedViewConfig` を必須引数化
- 「すべての表示状態は view 経由で受け取る。内部で対話ウィジェットで状態を
  収集しない」を契約としてdocstringに明示

### 2. 全9 PageComponent を render() に一本化

| ファイル | 変更内容 |
|---------|---------|
| table.py | render_page削除、render_saved_view→render、view.filters駆動 |
| plot.py | render_page（対話ウィジェット束）削除、render_saved_view→render |
| array_plot.py | render_page削除、render_saved_view→render |
| gallery.py | render_page削除、render_saved_view→render、view.filters対応 |
| card.py | render_page削除、render_saved_view→render、node選択は local_filters |
| status.py | render_page削除、render_saved_view→render |
| overview.py | render_page削除、render_saved_view→render、table+gallery統合 |
| batch_overview.py | render_page削除、render_saved_view→render |
| run_comparison.py | render_page→render（比較対象の ephemeral UI は残置） |

対話的UIが残るのは `run_comparison` のみ。「Run A vs Run B」は探索操作で
configに保存する性質ではない（`view.local_filters['run_type']` は保存）。

### 3. DashboardPageConnector も同様に統合

`services/dashboard/connectors/__init__.py`

- `render_page()` / `render_saved_view()` → `render(provider, view, dashboard_config)` に統合
- `render_connector_page` / `render_connector_saved_view` → `render_connector()` に統合
- 全4コネクター（abaqus 3種、ml 2種、ai_assistant、job_monitor）を更新

### 4. app.py とテストの整理

- `_render_enabled_view` は `component.render(provider, view, ...)` のみを呼ぶ
- `_init_shared_filters` / `_shared_filters_rendered` 等の対話フィルタ初期化を削除
  （render() では使われなくなったため）
- `TestSharedFiltersOnAllPages`（render_shared_filtersインポートを強制するテスト）
  を削除し、代わりに `TestPageComponentSingleRender` を追加:
  - `test_no_page_has_render_page`: 全PageComponentに render() のみが存在
  - `test_render_reflects_view_filters`: view.filters を変えると結果が変わる
    （= render() は view 引数にのみ依存）

### 5. プラグインドキュメント更新

`examples/jj-plugin-example/src/jj_plugin_example/dashboard.py`

- `render_page` → `render(provider, view, dashboard_config)` に更新
- docstring で「すべての表示状態は view (SavedViewConfig) 経由で受け取る」
  という契約を明示

---

## 契約（この refactor で保証されること）

**Given**: 同じ `SavedViewConfig view` と同じ `provider`, `dashboard_config`  
**Then**: `component.render(provider, view, dashboard_config)` は同じ画面を再現する

これにより:

- `save` ボタンは「現在の SavedViewConfig を config.yaml の enabled-pages に
  書き戻す」だけで良い。表示状態のスナップショットは不要（= バグが起きる余地がない）
- `load` は config.yaml を `SavedViewConfig` としてパースするだけで
  「保存時と同じ表示」を復元できる
- plugin 作者が実装すべきメソッドは `render()` の1個のみ

---

## 確認結果

- `pytest tests/test_dashboard_e2e.py tests/test_dashboard.py tests/test_app.py tests/test_app_integration.py tests/config/` (除外込み) → **546 passed**
- `TestPageComponentSingleRender` (2件): 全ページが単一 render() を持ち、
  render() の結果は view 引数にのみ依存することを検証
- `TestRenderSavedViewSmoke` (7件): 各 PageComponent.render() を直接呼び、
  最小/フル SavedViewConfig で正しく動作することを検証
- `TestEnabledPagesMutationRoundtrip` (4件): add/edit/delete → config.yaml
  への書き戻し → 再読み込みでのround-tripを検証
- `ruff check` / `ruff format --check` → パス

---

## 未完了TODO

### 継続TODO（他トラック）

- [ ] T7: Ollama AI連携 — フル統合テスト・マニュアル作成
- [ ] T8: 汎用データ管理 — 設計フェーズ以降の実装
- [ ] T9: 共有フォルダ同期 — Windows実環境テスト
- [ ] T10: プラグインコア — CLI統合・APIアダプター・get_page_data()
- [ ] W: Office連携 — Windows実環境テスト
- [ ] M2: マルチソルバー検証環境確保後に本実装

### 本refactorのフォローアップ候補

- [ ] `widgets.py::render_shared_filters` / `get_active_filters` は現在
      未使用のため削除検討（外部プラグイン後方互換観点で今回は残置）
- [ ] array_plot / gallery 等の UI 上の詳細編集（軸範囲・スタイル等）を
      SavedViewConfig へ反映する編集フォームの充実
- [ ] run_comparison の比較対象選択も SavedViewConfig に持たせるか検討

---

## 開発運用メモ

- **効果的だった点**: 契約を「render(view) は view のみに依存する」に
  絞ったことで、保存機能のバグの余地が構造的に消えた。テストでも
  「view.filters を変えると結果が変わる」を直接検証できる
- **設計の要諦**: Streamlit のように「UIで状態を集める」パターンと
  「configで状態を渡す」パターンは本質的に相性が悪い。後者に振り切って
  対話UIは「config編集フォーム」と「ephemeral な探索UI（run_comparison等）」
  に限定することで、保存と表示が自然に一致する
- **補足**: 従来の対話ウィジェット群（軸範囲入力、スタイル設定等）は
  `render()` 内から「編集フォーム」側に移動した（`_render_view_edit_form`）。
  編集→保存の流れが1本化された
