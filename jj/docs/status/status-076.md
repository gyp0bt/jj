[READMEへ戻る](../../README.md)

# status-076: ダッシュボードAbaqus依存コネクター分離

**日付**: 2026-02-12
**担当**: Claude Code

---

## 概要

ダッシュボードの「物性一覧」ページおよび関連データプロバイダーメソッドをAbaqus固有のコネクターに分離。parse層と同じ`__init_subclass__`自動登録パターンを採用し、ソフトウェア固有ページをプラグインとして動的追加可能にした。

**設計原則**: Abaqusのみに依存する機能はコネクターとして切り出し、汎用と見做せる機能（テーブル/カード/プロット/配列プロット/ステータス/ギャラリー/保存済みビュー）は共通モジュールとして保持。

---

## 実装内容

### 1. DashboardPageConnector基底クラスの新設

`services/dashboard/connectors/__init__.py`に配置。parse層の`AbstractFileParser`と同じ`__init_subclass__`による自動登録パターンを採用。

| 項目 | 内容 |
|------|------|
| クラス | `DashboardPageConnector` |
| 自動登録 | `__init_subclass__`で`_registry`辞書に自動追加 |
| キー | `page_label`（ページ名文字列） |
| メソッド | `is_available(provider)` / `render_page(provider, config)` |
| ユーティリティ | `get_connector_pages()` / `render_connector_page()` |

### 2. Abaqus物性一覧コネクターの実装

`services/dashboard/connectors/abaqus.py`に以下を移動:

**app.pyから移動した関数**:
- `_render_material_page()` → コネクター内部の描画関数
- `_guess_table_column_names()` → `guess_table_column_names()`（公開関数化）
- `_get_curve_plot_axes()` → `get_curve_plot_axes()`（公開関数化）

**data_provider.pyから移動したメソッド**:
- `DashboardDataProvider.get_material_table()` → `get_material_table(provider)`
- `DashboardDataProvider.get_material_table_data()` → `get_material_table_data(provider, ...)`
- `DashboardDataProvider.get_material_table_keys()` → `get_material_table_keys(provider, ...)`

**コネクタークラス**:
```python
class AbaqusMaterialPageConnector(DashboardPageConnector):
    page_label = "物性一覧"

    def is_available(self, provider):
        return any(n.type == "abaqus_material" for n in provider.graph.nodes)

    def render_page(self, provider, dashboard_config):
        _render_material_page(provider, dashboard_config)
```

### 3. app.pyのコネクター動的登録対応

- ページリスト構築を静的リストからコネクター動的取得に変更
- `get_connector_pages(provider)`で利用可能なコネクターページを取得
- `render_connector_page(page, provider, config)`でページ描画を委譲
- コネクターモジュールは`import services.dashboard.connectors.abaqus`で自動登録

### 4. data_provider.pyの汎用化

以下の3メソッドを削除（コネクターに移動済み）:
- `get_material_table()` - abaqus_materialノード依存
- `get_material_table_data()` - abaqus_materialノード依存
- `get_material_table_keys()` - abaqus_materialノード依存

### 5. テスト更新

全テストのインポートパスをコネクターモジュールに変更:
- `TestGetMaterialTable` → `from services.dashboard.connectors.abaqus import get_material_table`
- `TestGetMaterialTableData` → `from services.dashboard.connectors.abaqus import get_material_table_data`
- `TestGetMaterialTableKeys` → `from services.dashboard.connectors.abaqus import get_material_table_keys`
- `TestGuessTableColumnNames` → `from services.dashboard.connectors.abaqus import guess_table_column_names`
- `TestGetCurvePlotAxes` → `from services.dashboard.connectors.abaqus import get_curve_plot_axes`
- `TestDashboardPageConnector` → 新規追加（コネクター基盤テスト4件）

---

## アーキテクチャ

```
services/dashboard/
├── __init__.py              # DashboardDataProvider公開
├── app.py                   # Streamlitアプリ本体（汎用ページのみ）
├── data_provider.py         # 汎用データプロバイダー
└── connectors/              # ソフト固有ダッシュボードページ
    ├── __init__.py           # DashboardPageConnector基底クラス・レジストリ
    └── abaqus.py             # Abaqus物性一覧ページ
```

**parse層コネクターとの対称性**:
```
services/parse/connectors/abaqus/   ← パーサー（INP解析、メッシュ統計等）
services/dashboard/connectors/abaqus.py ← ダッシュボードページ（物性一覧）
```

---

## テスト結果

- 新規テスト: **4件**追加（コネクター基盤テスト）
- 移行テスト: **23件**パス（インポートパス変更、既存テスト互換）
- 全テスト: 107パス、17失敗（既存の依存ライブラリ未インストール起因）、37スキップ（streamlit未インストール）
- 今回変更関連テスト: **27件全パス**

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `services/dashboard/connectors/__init__.py` | **新規**: DashboardPageConnector基底クラス・レジストリ |
| `services/dashboard/connectors/abaqus.py` | **新規**: Abaqus物性一覧ページコネクター（物性データプロバイダー関数含む） |
| `services/dashboard/__init__.py` | docstring更新（コネクター分離について記載） |
| `services/dashboard/app.py` | コネクター動的登録対応、物性一覧ページ関連コード削除（約170行削減） |
| `services/dashboard/data_provider.py` | Abaqus固有メソッド3つ削除（get_material_table/data/keys） |
| `tests/test_dashboard.py` | 6テストクラスのインポートパス変更、コネクター基盤テスト4件追加 |
| `docs/roadmap.md` | アーキテクチャ図・ダッシュボードセクション更新、最新ステータスリンク更新 |
| `docs/status/status-076.md` | 本ステータスファイル |

---

## TODO / 次回引き継ぎ事項

- [ ] 実環境でCSV配列取り込みの動作確認（実プロジェクトのparse実行）
- [ ] 配列プロットページ: 保存済みビュー対応（saved-viewsでarray_plot型追加）
- [ ] 配列プロットページ: フィルタ連携（activeフィルタ等との統合）
- [ ] 物性一覧ページ: 物性比較機能（複数materialの同一プロパティ重ね書き）
- [ ] 物性一覧ページ: materialノードとgo_ノードの使用関係表示
- [ ] CSV配列: サブディレクトリ内CSV（go_idx1_w5_t20/history_RF3.csv）の対応
- [ ] CSV配列: ヘッダーなしCSVへの対応（数値のみの場合のcol_N自動命名）
- [ ] status-072のTODO引き継ぎ（UIからの動的ビュー保存、Excelダウンロード等）
- [ ] ダッシュボード: Excelダウンロード機能（openpyxl利用）
- [ ] ダッシュボード: NG領域塗りつぶし（Baskinカーブ等のconfig定義対応）
- [ ] ダッシュボード: グループ結線（同一条件のデータ点を灰色点線で結線）
- [ ] REST API: POST /api/v1/parse（再パース実行）
- [ ] REST API: クエリフィルター拡張（props.RF3.gt=5等）
- [ ] 他ソフトウェアのダッシュボードコネクター追加（Fluent、LS-DYNA等）

---

## 設計上の懸念

- `DashboardConfig.material_curve_columns`はAbaqusキーワード名に依存するが、config.yaml側の設定として残している。他ソフトのコネクター追加時に同じDashboardConfigで良いか、コネクター固有configに分離すべきか検討が必要。
- `_render_material_page()`内でapp.pyの`_try_render_aggrid()`をimportしている（循環依存ではないが、結合度が残る）。
