[← README.md](../../README.md)

# ダッシュボード改善仕様書

> テーブルフィルタ強化・レイアウト統合・デフォルト保存機能

---

## 1. 概要

ダッシュボードの3つの改善を仕様化する:

1. **テーブルビューのAgGridフィルタ強化** — 数値大小・文字列判定フィルタの常時有効化
2. **テーブル+ギャラリー統合レイアウト** — 一覧性のためテーブルを上、ギャラリーを下に
3. **デフォルト設定保存機能** — saved_viewsに代わり、UIからconfigデフォルトを保存

---

## 2. テーブルビュー AgGridフィルタ強化

### 2.1 現状

`widgets.py` の `try_render_aggrid()` は既に `agNumberColumnFilter` / `agTextColumnFilter`
を dtype に基づいて自動設定している。ただし:

- AgGrid自体がオプション依存（`streamlit-aggrid`）で、未インストール時は `st.dataframe` にフォールバック
- `st.dataframe` にはフィルタ機能がない
- saved_view のレンダリングでは AgGrid を使っていない（`st.dataframe` のみ）

### 2.2 改善内容

| 項目 | 変更 |
|------|------|
| saved_view でも AgGrid 使用 | `render_saved_view()` で `try_render_aggrid()` を呼ぶ |
| フィルタのデフォルト表示 | `suppressMenu=False` を明示（現在はデフォルトで有効） |
| フロート列のフィルタ | `agNumberColumnFilter` + `filterParams: {allowedCharPattern: "\\d\\.\\-"}` |
| 日本語テキスト列 | `agTextColumnFilter` + `filterParams: {textMatcher: "contains"}` |
| フィルタ状態永続化 | session_stateにfilterModelを保存し、ページ遷移後も復元 |

### 2.3 AgGrid未インストール時のフォールバック

`st.dataframe` 使用時は `column_config` でフィルタに近い体験を提供:

```python
st.dataframe(
    df,
    width="stretch",
    hide_index=True,
    column_config={
        col: st.column_config.NumberColumn(col, format="%.4g")
        for col in numeric_cols
    },
)
```

---

## 3. テーブル+ギャラリー統合レイアウト

### 3.1 目的

テーブルとギャラリーは共に「一覧性」が目的。上下に配置して同時閲覧可能にする。

### 3.2 設計

新しいページコンポーネント `OverviewPage` を追加:

```
services/dashboard/components/overview.py
```

```python
class OverviewPage(PageComponent):
    """テーブル+ギャラリー統合ビュー"""

    page_key = "overview"
    page_label = "概要"

    def render_page(self, provider, dashboard_config, **kwargs):
        # --- テーブル部（上半分） ---
        st.subheader("テーブル")
        # TablePage と同じロジック（共通関数に抽出）
        _render_table_section(provider, dashboard_config)

        st.divider()

        # --- ギャラリー部（下半分） ---
        st.subheader("ギャラリー")
        # GalleryPage と同じロジック（共通関数に抽出）
        _render_gallery_section(provider, dashboard_config, **kwargs)
```

### 3.3 ロジック分離方針

既存の `TablePage.render_page()` と `GalleryPage.render_page()` の描画ロジックを
モジュールレベル関数に抽出し、各ページと OverviewPage の両方から呼ぶ。

```
TablePage.render_page()     → _render_table_section(...)
GalleryPage.render_page()   → _render_gallery_section(...)
OverviewPage.render_page()  → _render_table_section(...) + _render_gallery_section(...)
```

### 3.4 プロット統合

プロットも統合レイアウトに含めたい場合:

```
[テーブル]          ← 上
[プロット]          ← 中（オプション、サイドバーでON/OFF）
[ギャラリー]        ← 下
```

OverviewPage のサイドバーにチェックボックスで各セクションの表示/非表示を切り替え。

### 3.5 ページ遷移との関係

- 既存のテーブル/ギャラリー/プロット個別ページはそのまま残す
- OverviewPage は追加ページとして導入
- デフォルトタブを config で指定可能にする

```yaml
dashboard:
  default-page: "overview"  # "table" | "gallery" | "plot" | "overview"
```

---

## 4. デフォルト設定保存機能

### 4.1 現状の問題

`saved_views` はYAMLを手動編集する必要があり、UIからの操作性が低い。
ビュー保存UIもうまく機能していない。

### 4.2 新方針: configデフォルト保存

ダッシュボードの現在の設定状態（フィルタ、列選択、グループ化等）を
YAMLファイルに「デフォルト」として保存する「デフォルトとして保存」ボタンを設置。

### 4.3 保存対象

| 設定項目 | 保存先（config.yaml） | 対応session_state |
|---------|---------------------|------------------|
| テーブル列選択 | `dashboard.table-columns` | `_table_selected_cols` |
| テーブル除外列 | `dashboard.exclude-table-columns` | — |
| デフォルトフィルタ | `dashboard.default-filters` | 共有フィルタ状態 |
| プロットX/Y軸 | `dashboard.plot.x/y` | `_plot_x`, `_plot_y` |
| ギャラリー列数/行数 | `dashboard.gallery-defaults.columns/rows` | `_gallery_user_cols/rows` |
| ギャラリーグループキー | `dashboard.gallery-defaults.group-keys` | — |
| 配列プロット設定 | `dashboard.array-plot-defaults` | — |
| デフォルトページ | `dashboard.default-page` | 現在のタブ |

### 4.4 UI設計

```
サイドバー下部:
  ┌─────────────────────────┐
  │ [💾 デフォルトとして保存]  │  ← ボタン
  │                         │
  │ 保存項目:               │  ← 展開パネル(expander)
  │ ☑ フィルタ設定           │
  │ ☑ テーブル列            │
  │ ☑ ギャラリー設定         │
  │ ☐ プロット軸            │
  │ ☐ 配列プロット設定       │
  └─────────────────────────┘
```

### 4.5 保存ロジック

```python
def save_dashboard_defaults(
    project_root: Path,
    items: dict[str, Any],
) -> None:
    """現在のダッシュボード設定をconfig.yamlに書き戻す

    既存のconfig.yamlを読み込み、dashboard セクションのみを更新。
    他のセクション（parse, export等）は変更しない。
    """
    config_path = project_root / ".j2" / "config.yaml"
    # ... YAML読み込み → dashboard セクション更新 → 書き戻し
```

### 4.6 注意事項

- config.yamlの他セクションを壊さないよう、`ruamel.yaml` を使用してコメント保持
- 保存前に確認ダイアログ（`st.warning` + 確認ボタン）
- 保存後は `st.rerun()` で設定を即座に反映
- バックアップとして `.j2/config.yaml.bak` を自動作成

---

## 5. 実装フェーズ

| Phase | 内容 | 依存 |
|-------|------|------|
| D-1 | AgGridフィルタ強化（saved_viewでもAgGrid使用） | なし |
| D-2 | テーブル/ギャラリーロジック関数抽出 | なし |
| D-3 | OverviewPage 実装 | D-2 |
| D-4 | デフォルト保存ボタン + config書き戻し | なし |
| D-5 | default-page config対応 | D-3 |

---

## 6. 設定追加（config.yaml）

```yaml
dashboard:
  # 既存
  table-columns: [...]
  default-filters: {active: true}
  gallery-defaults:
    columns: 5
    rows: 4
    group-keys: [result_key, step, frame, vmax, vmin]

  # 新規追加
  default-page: "overview"   # デフォルト表示ページ
  overview:
    show-table: true
    show-plot: false
    show-gallery: true
```
