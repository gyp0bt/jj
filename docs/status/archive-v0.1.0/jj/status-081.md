[READMEへ戻る](../../README.md)

# status-081: ダッシュボード描画/クエリロジック分離

**日付**: 2026-02-13
**担当**: Claude Code

---

## 概要

status-077で分析されたプラグイン化・パッケージ分離の前段として、`services/dashboard`の描画ロジックとクエリロジックの責務分離を実施。

`app.py`（約2,200行）に混在していた以下を分離:
- **純粋クエリ/フィルタ/ソートロジック** → `query.py`（新規）
- **HTMLエクスポートロジック** → `html_export.py`（新規）
- **Abaqus物性クエリ関数** → `connectors/abaqus_query.py`（新規）

これにより、Streamlit非依存のテスト可能なモジュールが確立され、将来の`jj-cli`/`jj-dashboard`パッケージ分離の基盤が整った。

---

## 実装内容

### 1. services/dashboard/query.py（新規作成）

app.pyから抽出した、Streamlitに一切依存しない純粋関数群:

| 関数 | 旧配置 | 説明 |
|------|--------|------|
| `find_graph_path()` | `app._find_graph_path` | graph.yaml実パス検出 |
| `get_graph_mtime()` | `app._get_graph_mtime` | graph.yaml更新時刻取得 |
| `is_truthy()` | `app._is_truthy` | bool/文字列両対応truthy判定 |
| `sort_columns_by_vocab()` | `app._sort_columns_by_vocab` | vocab順カラムソート |
| `select_table_columns()` | `app._select_table_columns` | config駆動カラム選択 |
| `apply_filters()` | `app._apply_shared_filters`（純粋化） | 汎用フィルタ適用 |
| `apply_saved_view_filters()` | `app._apply_saved_view_filters` | 保存済みビューフィルタ適用 |
| `saved_view_filters_to_provider_filters()` | `app._saved_view_filters_to_provider_filters` | フィルタ形式変換 |
| `normalize_group_key()` | `app._normalize_group_key` | ギャラリーグループキー正規化 |
| `collect_group_keys()` | `app._collect_group_keys` | ギャラリーグループキー収集 |

### 2. services/dashboard/html_export.py（新規作成）

保存済みビューのスタンドアロンHTML変換ロジック:

| 関数 | 旧配置 | 説明 |
|------|--------|------|
| `generate_saved_views_html()` | `app._generate_saved_views_html` | ビュー一覧→HTML |
| `generate_view_html()` | `app._generate_view_html` | 個別ビュー→HTML断片 |
| `generate_table_html()` | `app._generate_table_html` | テーブル→HTML |
| `generate_plot_html()` | `app._generate_plot_html` | plotly→HTML |
| `generate_array_plot_html()` | `app._generate_array_plot_html` | 配列プロット→HTML |
| `generate_status_html()` | `app._generate_status_html` | ステータス→HTML |
| `generate_card_html()` | `app._generate_card_html` | カード→HTML |
| `_create_plot_figure()` | `app._create_plot_figure` | plotly Figure生成 |
| `_add_ng_regions_to_fig()` | `app._add_ng_regions` | NG領域追加 |
| `_add_group_lines_to_fig()` | `app._add_group_lines` | グループ結線追加 |

### 3. services/dashboard/connectors/abaqus_query.py（新規作成）

Abaqus物性データの純粋クエリ関数群:

| 関数 | 旧配置 | 説明 |
|------|--------|------|
| `get_material_table()` | `abaqus.get_material_table` | 物性テーブルデータ |
| `get_material_table_data()` | `abaqus.get_material_table_data` | テーブル型プロパティ取得 |
| `get_material_table_keys()` | `abaqus.get_material_table_keys` | テーブル型キーリスト |
| `guess_table_column_names()` | `abaqus.guess_table_column_names` | 列名推定 |
| `get_curve_plot_axes()` | `abaqus.get_curve_plot_axes` | プロット軸設定取得 |
| `parse_material_curve_columns()` | `abaqus._parse_material_curve_columns` | config正規化 |
| `get_material_usage()` | `abaqus.get_material_usage` | 物性-GO使用関係 |

### 4. app.py のリファクタ

- docstringに責務分離アーキテクチャを明記
- 旧関数は`query.py`/`html_export.py`への委譲ラッパーとして残存（後方互換）
- `fnmatch`インポート削除（`select_table_columns`がquery.pyに移動したため）
- HTML生成関数群（`_generate_*`）を全て削除（html_export.pyに移動）

### 5. connectors/abaqus.py のリファクタ

- docstringに責務分離を明記
- クエリ関数群を`abaqus_query.py`からのインポートに変更
- 描画関数（`_render_*`）のみ残存

---

## アーキテクチャ

### 変更後（status-081）

```
services/dashboard/
├── app.py              # 描画層のみ（Streamlit UI構築）
├── query.py            # NEW: クエリ/フィルタ/ソート純粋ロジック
├── html_export.py      # NEW: スタンドアロンHTML生成
├── data_provider.py    # GraphModelからのデータ取得
├── widgets.py          # AgGrid共有ヘルパー
└── connectors/
    ├── __init__.py      # DashboardPageConnector基底
    ├── abaqus.py        # 描画層のみ
    └── abaqus_query.py  # NEW: Abaqus物性クエリ純粋関数
```

### 責務分離の層構成

```
GraphModel
  ↓
data_provider.py  (GraphModelからの生データ取得)
  ↓
query.py / abaqus_query.py  (フィルタ・ソート・変換の純粋ロジック)
  ↓
app.py / abaqus.py  (Streamlit描画層)
  ↓                ↘
[Streamlit UI]    html_export.py (HTMLエクスポート)
```

---

## テスト結果

- 既存ダッシュボードテスト: **25パス**（変更なし）
- `query.py`関数テスト: 全関数の基本動作を確認
- `abaqus_query.py`関数テスト: 全関数の基本動作を確認
- CLI登録テスト: 1失敗（chardetモジュール未インストール = 既存の環境依存、本変更と無関係）

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `services/dashboard/query.py` | **新規**: 純粋クエリ/フィルタ/ソートロジック |
| `services/dashboard/html_export.py` | **新規**: HTMLエクスポート生成ロジック |
| `services/dashboard/connectors/abaqus_query.py` | **新規**: Abaqus物性クエリ関数 |
| `services/dashboard/app.py` | 描画層に特化、旧関数は委譲ラッパー化 |
| `services/dashboard/connectors/abaqus.py` | 描画層に特化、クエリはabaqus_query.pyからインポート |
| `docs/status/status-081.md` | 本ステータスファイル |

---

## TODO / 次回引き継ぎ事項

### 本status由来
- [ ] services/query（jjレベル）の検討: data_providerのクエリロジックをjj本体のservices/queryに昇格し、dashboard以外（REST API等）でも利用可能にする。jj-dashboardをさらに薄くするための設計検討
- [ ] query.py, html_export.py, abaqus_query.pyの単体テストを`tests/test_dashboard.py`に追加
- [ ] app.pyの後方互換ラッパー関数の将来的な削除計画

### 過去status引き継ぎ
- [ ] 実環境でCSV配列取り込みの動作確認
- [ ] 配列プロットページ: 保存済みビュー対応・フィルタ連携
- [ ] 物性一覧ページ: 物性比較機能・使用関係表示
- [ ] CSV配列: サブディレクトリ内CSV・ヘッダーなしCSV対応
- [ ] ダッシュボード: Excelダウンロード機能・UIからの動的ビュー保存
- [ ] REST API拡張（POST parse, クエリフィルター）
- [ ] プラグイン化Phase 1-3（jj-sdk定義、CacheProvider抽象化、entry_points動的発見）

---

## 設計上の懸念

- [ ] data_providerがdashboard専用のままだが、REST APIでも同様のクエリが必要。将来的にservices/queryに昇格してjj-dashboardを薄くすることを検討
- [ ] app.pyに後方互換ラッパー関数が残っている。外部テストが安定したら削除予定
- [ ] Abaqus parse層のキャッシュがGraphStorageに直接依存 → プラグイン化Phase 2で対応予定
