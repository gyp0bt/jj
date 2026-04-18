[← README.md](../../README.md)

# status-085 — ビュー保存/表示機能の統一化（config駆動シングルページ）

| 項目 | 内容 |
|------|------|
| **日付** | 2026-04-18 |
| **ブランチ** | `claude/dashboard-single-page-YMTol` |
| **トラック** | ダッシュボード改善 |

---

## 背景

status-084 でダッシュボードをシングルページ化したが、以下の課題が残っていた:

1. **保存機能のバグ**: 「ビューを保存」ボタンは空のSavedViewConfigを
   `.j2/storage/saved-views.yaml` に書き込むだけで、現在のUI状態は
   反映されない（configとビューが対応しない）
2. **二重のレンダリング経路**: シングルページは `render_page`（対話的UI）
   で描画する一方、保存済みビューは `render_saved_view`（config駆動）で
   描画する、という異なるロジックが存在していた
3. **2つの永続化先**: `config.yaml:dashboard.saved-views` と
   `.j2/storage/saved-views.yaml` が分離し、どちらが正かが不明確

本タスクでこれらを解消し、「configから表示オプションを読み取って、あれば反映、
なければplaceholder」という単一のレンダリングモデルに統一する。

---

## 実施内容

### 1. enabled_pages をSavedViewConfig駆動に変更

`config/__init__.py`

| 変更前 | 変更後 |
|--------|--------|
| `enabled_pages: list[str]` | `enabled_pages: list[SavedViewConfig]` |

- 各要素は保存済みビュー相当の完全な設定（name/type/filters/plot/gallery/
  array_plot/connector_config）を持つ
- 後方互換: YAMLでstring指定された場合は type だけの最小SavedViewConfig
  （name=type）として自動変換（`_parse_enabled_page_entry`）
- `_BUILTIN_VIEW_TYPES` に `overview`, `batch_overview`, `run_comparison` を追加
- `saved_view_to_dict(view)` ヘルパー追加（config書き戻し用シリアライザ。
  空フィールドは除外）

### 2. シングルページを render_saved_view 経由に統一

`services/dashboard/app.py`

- `_render_single_page()` が `enabled_pages` を順に走査し、各要素に対して
  `PageComponent.render_saved_view` または `render_connector_saved_view`
  を呼ぶ単一経路に変更
- 各セクションヘッダーは `view.name` を表示
- 各セクション右上に **[編集] [削除]** ボタンを配置。編集中は `_render_view_edit_form`
  を同じ場所に展開、削除は即時 `config.yaml` 書き戻し
- 最下段の「ビューを追加」expanderで新規ビュー追加（config.yamlへ書き戻し）

### 3. `.j2/storage/saved-views.yaml` 永続化の廃止

- `_SAVED_VIEWS_FILENAME` / `_saved_views_path` / `_load_persistent_views` /
  `_save_persistent_views` をすべて削除
- 書き込み先を `config.yaml:dashboard.enabled-pages` に統一
  （`_persist_enabled_pages()` → `save_enabled_pages(project_root, views)`）
- プリセット遷移（`_apply_preset_and_navigate`）も廃止（シングルページでは
  スクロールで全ビューが見えるため遷移不要）

### 4. 共通フォームヘルパー抽出

以下を重複排除のため関数化:
- `_render_global_filter_inputs(prefix, existing)` — type/analysis_status/active
- `_render_local_filter_inputs(prefix, count_key, existing)` — 複数ペア対応
- `_render_connector_config_inputs(page_label, prefix, existing)` — connector_config UI
- `_render_plot_edit_inputs(provider, prefix, existing_plot)` — プロット編集（x/y/color/chart/Z軸/スタイル/軸範囲）
- `_normalize_connector_config(cc)` — compare_materialsのカンマ区切り→list変換

これにより add form と edit form が同じヘルパーを使い回し、
ウィジェットキーの衝突を防ぐため `prefix` でユニーク化する。

### 5. plot render_saved_view のplaceholder強化

`services/dashboard/components/plot.py`

- `view.plot.x` / `view.plot.y` 未設定時は `dashboard_config.plot_x/plot_y`、
  さらに無ければプロパティキー先頭2つで自動補完
- 数値プロパティが皆無のときのみ `st.info` でplaceholder表示

### 6. config_writer に save_enabled_pages を追加

`services/dashboard/config_writer.py`

```python
def save_enabled_pages(project_root: Path, views: list[SavedViewConfig]) -> Path:
    serialized = [saved_view_to_dict(v) for v in views]
    return save_dashboard_defaults(project_root, {"enabled-pages": serialized})
```

### 7. デフォルト保存ボタンの簡素化

`_render_save_defaults_button` から「デフォルトページ」チェックボックスを削除。
シングルページ構成では default-page の概念がビュー列挙に吸収されたため、
このボタンはギャラリー設定（columns/rows）書き戻しのみ行う。

---

## 新しいconfig.yamlのスキーマ

```yaml
dashboard:
  # 最小指定: string→type名そのものがnameになる
  enabled-pages:
    - table
    - array_plot
    - gallery

  # フル指定: 保存済みビュー相当の設定を持てる
  enabled-pages:
    - name: メインテーブル
      type: table
      filters:
        active: true
    - name: 応力-ひずみ曲線
      type: array_plot
      filters:
        active: true
      array_plot:
        prefix: material
        x: material.strain
        y: [material.stress]
    - name: 出力画像
      type: gallery
      gallery:
        source: has_output
    - name: 物性比較
      type: connector:物性一覧
      connector_config:
        compare_materials: [Steel, Aluminum]
```

UI上で「編集」ボタンを押すと、そのビューの設定を対話的に変更し、
保存ボタンで上記YAMLの該当エントリを上書きする。

---

## テスト追加・更新

| ファイル | 内容 |
|---------|------|
| `tests/test_dashboard.py::TestDashboardConfigEnabledPages` | SavedViewConfig化対応の9ケースへ置換（string/dict/混在/コネクター/エラー系） |
| `tests/test_dashboard.py::TestSavedViewToDict` | シリアライザの3ケース（最小/フル/空フィールド除外） |
| `tests/test_dashboard.py::TestSaveEnabledPages` | config_writerのround-tripテスト（書いたYAMLがGraphConfig.loadで復元できる） |
| `tests/test_dashboard_e2e.py::TestDashboardAppTest` | 「ビューを追加」expanderの存在確認、セクションヘッダーに view.name が表示されることを検証 |
| `tests/test_dashboard_e2e.py::TestDashboardEnabledPagesE2E` | dict指定でnameがヘッダーに反映されるテスト追加 |

---

## 確認結果

- `pytest tests/test_dashboard_e2e.py` → 39 passed
- `pytest tests/test_dashboard.py::TestDashboardConfigEnabledPages tests/test_dashboard.py::TestSavedViewToDict tests/test_dashboard.py::TestSaveEnabledPages` → 13 passed
- `pytest tests/test_app.py tests/test_app_integration.py tests/config/` → 56 passed
- `pytest tests/test_dashboard.py` (除外付き) → 443 passed
- `pytest tests/` フルスイート（除外付き） → 2165 passed / 11 failed（失敗はmainで既存、本変更と無関係の parser/query/mesh 系）
- `ruff check` / `ruff format --check` → パス

---

## 未完了TODO

### 本タスク関連のフォローアップ

- [ ] array_plot / gallery のインタラクティブ調整（軸範囲等）を
      config.yaml に書き戻す「現在の状態を保存」ボタンの復活検討
      （今回はconfig駆動優先のためシンプル削除）
- [ ] 編集フォームでの array_plot / gallery の完全な編集UI
      （現状これらは type 変更や config.yaml 直接編集が前提）
- [ ] ビューのドラッグ＆ドロップによる並び替え（今は削除/追加で間接対応）

### 継続TODO（他トラック）

- [ ] T7: Ollama AI連携 — フル統合テスト・マニュアル作成
- [ ] T8: 汎用データ管理 — 設計フェーズ以降の実装
- [ ] T9: 共有フォルダ同期 — Windows実環境テスト
- [ ] T10: プラグインコア — CLI統合・APIアダプター・get_page_data()
- [ ] W: Office連携 — Windows実環境テスト
- [ ] K-4: config property-key-aliases（オプション）
- [ ] M2: マルチソルバー検証環境確保後に本実装

---

## 開発運用メモ

- **効果的だった点**: SavedViewConfigを単一の真実の源とし、レンダリング
  経路を `render_saved_view` に一本化したことでコードの理解と今後の拡張が
  大幅に簡単になった。config.yaml が単一の永続化先になり、
  「UIで変えた → config.yamlに書かれる → 次回起動時に復元」のフローが明快
- **注意点**: `render_page` メソッドは各PageComponentに残したまま（未使用）。
  外部プラグインが依存している可能性に配慮して削除は見送り。将来整理可
- **提案**: `DashboardConfig.saved_views` も legacy 化して `enabled_pages`
  に統合するのが自然な次段階。ただし後方互換性観点では現行併存でも問題ない
