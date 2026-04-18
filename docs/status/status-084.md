[← README.md](../../README.md)

# status-084 — ダッシュボードのシングルページ化（enabled-pages制御）

| 項目 | 内容 |
|------|------|
| **日付** | 2026-04-18 |
| **ブランチ** | `claude/dashboard-single-page-YMTol` |
| **トラック** | ダッシュボード改善 |

---

## 背景

dashboardが機能ごとに個別ページ（ラジオボタンで切り替え）になっており、
ページ間を行き来しないと全体像が把握できず使いにくかった。一方で全ページを
毎回描画すると重くなるため、`config.dashboard.enabled-pages` で有効化する
ページを制御するシングルページ構成に切り替えた。

---

## 実施内容

### 1. DashboardConfig に `enabled_pages` を追加

`config/__init__.py`

- `DashboardConfig` に `enabled_pages: list[str]` を追加
- config.yaml 上のキーは `dashboard.enabled-pages`
- 未指定時のデフォルトは `["table", "array_plot", "gallery"]`
- 値は `PageComponent.page_key`（例: `"table"`）、またはコネクターページを
  指す `"connector:{page_label}"`（例: `"connector:物性一覧"`）

### 2. app.py をシングルページ構成に変更

`services/dashboard/app.py`

- サイドバーの「ページ」ラジオボタンを廃止
- `_render_single_page()` を追加し、`enabled_pages` の順に各セクションを
  上から下へ連続描画。各セクションは `st.markdown("---")` で区切る
- `_render_enabled_entry()` で `connector:` プレフィックスを判定して
  コネクターページとPageComponentページを振り分け
- 保存済みビューは最下段の `st.expander` に畳む（常時アクセス可能）
- `_render_quick_save_button()` のウィジェットキーを `view_type` で
  ユニーク化（同一画面に複数ビューが並ぶため）
- 実行開始時に `_shared_filters_rendered` フラグをリセット

### 3. render_shared_filters の冪等化

`services/dashboard/widgets.py`

- シングルページ構成では複数ページが同一実行中に `render_shared_filters()`
  を呼び出すため、2回目以降はウィジェットキー衝突を避けるため早期 return
  する `_shared_filters_rendered` ガードを追加
- フラグは `app.py` 側で実行ごとにリセット

### 4. テスト更新

| ファイル | 内容 |
|---------|------|
| `tests/test_dashboard.py` | `TestDashboardConfigEnabledPages` 追加（6ケース）: デフォルト値・カスタム値・空リスト・`connector:` プレフィックス・型バリデーション |
| `tests/test_dashboard_e2e.py` | `TestDashboardAppTest` からラジオ前提の3テストを削除し、シングルページ用に2テスト追加（セクション描画・保存済みビュー expander）。`TestDashboardPageNavigationE2E` をラジオ前提の4テストから `TestDashboardEnabledPagesE2E` の `enabled-pages` 設定テスト3件へ置き換え |

---

## 使用例（config.yaml）

```yaml
dashboard:
  # デフォルト（省略時と等価）
  enabled-pages:
    - table
    - array_plot
    - gallery
```

```yaml
dashboard:
  # コネクターページも含めたカスタム構成
  enabled-pages:
    - table
    - plot
    - "connector:物性一覧"
```

```yaml
dashboard:
  # 全ページ表示（重い）
  enabled-pages:
    - overview
    - table
    - plot
    - array_plot
    - gallery
    - card
    - status
    - batch_overview
    - run_comparison
```

---

## 確認結果

- `pytest tests/test_dashboard_e2e.py` → 38 passed
- `pytest tests/test_dashboard.py::TestDashboardConfigEnabledPages tests/test_dashboard.py::TestDashboardConfigDefaultPage tests/test_dashboard.py::TestConfigWriter` → 11 passed
- `pytest tests/test_app.py tests/test_app_integration.py` → 35 passed
- `pytest tests/config/test_config_loader.py` → 21 passed
- `ruff check` → All checks passed
- `ruff format --check` → 5 files already formatted

pre-existingな失敗（`TestSelectTableColumns`, `TestArrayPlotHelpers`, `TestQueryModule` 各一部）は本変更と無関係。

---

## 未完了TODO

### 継続TODO（他トラック）

- [ ] T7: Ollama AI連携 — フル統合テスト・マニュアル作成
- [ ] T8: 汎用データ管理 — 設計フェーズ以降の実装
- [ ] T9: 共有フォルダ同期 — Windows実環境テスト
- [ ] T10: プラグインコア — CLI統合、Abaqus CLICommand、FastAPI APIアダプター、get_page_data()
- [ ] W: Office連携 — Windows実環境テスト
- [ ] K-4: config property-key-aliases（オプション）
- [ ] M2: マルチソルバー検証環境確保後に本実装

### 本タスクのフォローアップ候補

- [ ] `default_page` フィールドの非推奨化検討（シングルページ構成では意味を
      持たなくなったため。今回は後方互換のため残置）
- [ ] サイドバーに「表示ページ切替UI」（チェックボックス）を追加して
      config更新なしで切替可能にする
- [ ] 保存済みビューの「開く」ボタン動作をシングルページ向けに再設計
      （現状は `_preset_page_label` を設定して st.rerun するが、シングル
      ページ構成ではスクロール誘導のみで十分）

---

## 開発運用メモ

- **効果的だった点**: `render_shared_filters` をフラグで冪等化することで
  複数ページが同一サイドバーフィルタUIを描画する問題を局所的に解決。
  `_render_quick_save_button` のキーを `view_type` 付きにするだけで
  複数セクション並置時のキー衝突を回避できた
- **注意点**: 各PageComponentが使用しているウィジェットキーの一意性は
  各コンポーネント作成時の責務。将来ページ追加時はキー命名を衝突しない
  よう注意（現状は `_gallery_*`, `_ap_*`, `_batch_*` 等でプレフィックス
  分離されており問題なし）
- **提案**: `enabled-pages` に `default-page` と同じ `save_dashboard_defaults`
  書き戻しルートを後日追加しても良い
