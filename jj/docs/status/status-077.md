[READMEへ戻る](../../README.md)

# status-077: コネクタ固有config分離・プラグイン化分析

**日付**: 2026-02-12
**担当**: Claude Code

---

## 概要

status-076で設計上の懸念として挙がっていた以下2点を解消し、コネクタプラグイン化の実現可能性を分析した。

1. **DashboardConfig.material_curve_columnsのコネクタ固有config化**: `DashboardConfig`にAbaqus固有の`material_curve_columns`が混在していた問題を解消。`connector_configs`辞書方式に移行し、各コネクタが自分のconfigを自律的に管理できる設計とした。
2. **app.py→コネクタ間の結合度解消**: `abaqus.py`が`app.py`の`_try_render_aggrid`をインポートしていた逆依存を、共有ウィジェットモジュール`widgets.py`への切り出しで解消。
3. **プラグイン化分析**: 現状のAbaqusコネクタを`jj-abaqus-connector`等の独立パッケージに分離するために必要な要件を整理・文書化。

---

## 実装内容

### 1. DashboardConfig: connector_configs方式への移行

`config/__init__.py`のDashboardConfigクラスを変更:

**旧設計**:
```python
@dataclass(frozen=True)
class DashboardConfig:
    material_curve_columns: dict[str, dict[str, Any]]  # Abaqus固有!
```

**新設計**:
```python
@dataclass(frozen=True)
class DashboardConfig:
    connector_configs: dict[str, dict[str, Any]]  # コネクタ名→設定辞書

    def get_connector_config(self, connector_key: str) -> dict[str, Any]:
        """コネクタ固有設定を取得"""
```

**config.yaml構造の変更**:
```yaml
# 旧形式（後方互換で引き続き読み込み可能）
dashboard:
  material-curve-columns:
    plastic: {columns: [stress, strain], x: 1, y: 0}

# 新形式
dashboard:
  connectors:
    abaqus:
      material-curve-columns:
        plastic: {columns: [stress, strain], x: 1, y: 0}
```

**後方互換**: `material-curve-columns`がトップレベルにある場合、自動的に`connectors.abaqus`に移行して読み込む。

### 2. DashboardPageConnector: connector_key属性の追加

`services/dashboard/connectors/__init__.py`にconnector_keyを追加:

```python
class DashboardPageConnector:
    page_label: str = ""
    connector_key: str = ""  # NEW: コネクタ固有config取得用キー

    def get_connector_config(self, dashboard_config: Any) -> dict[str, Any]:
        """DashboardConfigからコネクタ固有設定を取得"""
```

### 3. 共有ウィジェットモジュールの切り出し

`services/dashboard/widgets.py`を新規作成し、AgGridヘルパー関数を移動:

| 関数 | 旧配置 | 新配置 |
|------|--------|--------|
| `try_render_aggrid()` | `app.py._try_render_aggrid` | `widgets.py.try_render_aggrid` |
| `estimate_column_width()` | `app.py._estimate_column_width` | `widgets.py.estimate_column_width` |

`app.py`には後方互換のラッパー関数を残し、既存テストへの影響を最小化。
`abaqus.py`は`widgets.py`から直接インポートするよう変更。

### 4. Abaqusコネクタのconfig読み込み変更

`services/dashboard/connectors/abaqus.py`の変更:

- `_parse_material_curve_columns()`: 生の設定辞書を正規化する関数を新設
- `_render_material_page()`: `get_connector_config("abaqus")`経由でconfig取得
- 後方互換: 旧形式`material_curve_columns`属性があればそちらも読む

### 5. default-config.yaml の更新

`material-curve-columns`を`connectors.abaqus.material-curve-columns`に移動。

---

## アーキテクチャ

```
services/dashboard/
├── __init__.py              # DashboardDataProvider公開
├── app.py                   # Streamlitアプリ本体（汎用ページ）
├── data_provider.py         # 汎用データプロバイダー
├── widgets.py               # NEW: 共有UIヘルパー（AgGrid等）
└── connectors/              # ソフト固有ダッシュボードページ
    ├── __init__.py           # DashboardPageConnector基底クラス
    │                          + connector_key属性
    │                          + get_connector_config()メソッド
    └── abaqus.py             # Abaqus物性一覧ページ
                               + _parse_material_curve_columns()
                               + connector_key = "abaqus"
```

**config.yamlデータフロー**:
```
config.yaml
  └── dashboard.connectors.abaqus.material-curve-columns
           ↓
DashboardConfig.from_dict()
  → connector_configs["abaqus"] = {...}
           ↓
AbaqusMaterialPageConnector.get_connector_config(dashboard_config)
  → {"material-curve-columns": {...}}
           ↓
_parse_material_curve_columns(raw_mcc)
  → 正規化された{property_key: {columns, x, y}}
```

---

## テスト結果

- 新規テスト: **12件**追加
  - `TestDashboardConfig`: 3件（connector_configs, get_connector_config_missing, backward_compat）
  - `TestDashboardPageConnector`: 2件（connector_key, get_connector_config）
  - `TestParseMaterialCurveColumns`: 4件（dict, list, empty, non_dict）
  - `TestWidgets`: 3件（ascii, japanese, import）
- 更新テスト: 5件（TestDashboardConfigMaterialCurveColumnsクラス全体を新形式に）
- 今回変更関連テスト: **48件全パス**
- 全テスト: 121パス、17失敗（既存依存ライブラリ未インストール起因）、37スキップ（streamlit等未インストール）

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `config/__init__.py` | `DashboardConfig`:`material_curve_columns`→`connector_configs`、`get_connector_config()`追加、後方互換読み込み |
| `services/dashboard/widgets.py` | **新規**: AgGrid共有ヘルパー（`try_render_aggrid`, `estimate_column_width`） |
| `services/dashboard/connectors/__init__.py` | `connector_key`属性・`get_connector_config()`メソッド追加 |
| `services/dashboard/connectors/abaqus.py` | `connector_key="abaqus"`、`_parse_material_curve_columns()`追加、`widgets.py`インポート |
| `services/dashboard/app.py` | `_try_render_aggrid`/`_estimate_column_width`をwidgets.pyへの委譲ラッパーに変更 |
| `shared/assets/default-config.yaml` | `material-curve-columns`を`connectors.abaqus.`配下に移動 |
| `tests/test_dashboard.py` | 12テスト追加、5テスト更新（新config方式対応） |
| `docs/status/status-077.md` | 本ステータスファイル |

---

## コネクタプラグイン化分析

### 現状の構成

現在Abaqusコネクタは3層に分散している:

```
services/parse/connectors/abaqus/    # Parse層: INP解析、メッシュ統計、差分比較
  ├── __init__.py                     # ABQData, read_inp, diff_abq_blocks (1890行)
  ├── inp_parser.py                   # AbaqusInpParser等 3パーサー
  ├── mesh_parser.py                  # AbaqusMeshParser 1パーサー
  ├── result_parser.py                # AbaqusResultParser等 2パーサー
  ├── diff_parser.py                  # AbaqusDiffParser 1パーサー
  └── mesh.py                         # pymesh統合（スタンドアロン）

services/dashboard/connectors/
  └── abaqus.py                       # Dashboard層: 物性一覧ページ

services/export/connectors/
  ├── neo4j.py                        # Neo4j（Abaqus非固有だが参考）
  └── csv_json.py                     # CSV/JSON（同上）
```

### jj本体への依存ポイント

| 依存先 | 提供機能 | 分離難易度 |
|--------|---------|-----------|
| `jj_types` (Node, Relation, GraphModel) | グラフデータ型 | **低**: PyPIパッケージ化 or SDKとして切り出し可能 |
| `services.parse.base` (AbstractFileParser) | パーサー基底クラス・レジストリ | **低**: SDKとして切り出し可能 |
| `services.graph.project_graph` (ProjectGraph) | グラフ操作IF | **低**: TYPE_CHECKINGのみの依存（ダックタイピング可） |
| `services.graph.storage` (GraphStorage) | キャッシュ永続化 | **中**: キャッシュIFの抽象化が必要 |
| `services.dashboard.connectors` (DashboardPageConnector) | ダッシュボード基底クラス | **低**: SDKとして切り出し可能 |
| `services.dashboard.widgets` | 共有UIヘルパー | **低**: オプション依存 |
| `services.dashboard.data_provider` | データ供給IF | **低**: TYPE_CHECKINGのみ |
| `config` (GraphConfig, DashboardConfig) | 設定管理 | **中**: connector_configs方式で既に分離済み |
| `modules.pymesh` | メッシュ品質解析 | **中**: Abaqus固有なのでコネクタと同梱 |

### プラグイン化に必要な作業

#### Phase 1: SDKパッケージの定義（容易）

`jj-sdk`として以下を切り出す:

```
jj-sdk/
├── jj_types/           # Node, Relation, GraphModel
├── parse_base.py       # AbstractFileParser, parser_list, parse()
├── export_base.py      # AbstractExporter
├── dashboard_base.py   # DashboardPageConnector, get_connector_pages()
└── graph_interface.py   # ProjectGraphプロトコル（Protocol型）
```

**工数見積もり**: インターフェースの切り出しと型定義のみ。実装の変更は不要。

#### Phase 2: コネクタの独立パッケージ化（中程度）

```
jj-abaqus-connector/
├── setup.py           # depends: jj-sdk, chardet, ftfy, numpy
├── jj_abaqus/
│   ├── parse/         # Parse層パーサー群（7クラス）
│   ├── dashboard/     # Dashboard物性一覧コネクタ
│   └── mesh.py        # pymesh統合
└── tests/
```

**必要な変更**:

1. **キャッシュIF抽象化**: `GraphStorage`への直接依存を`CacheProvider`プロトコルに置換
   ```python
   class CacheProvider(Protocol):
       def get_cache(self, key: str) -> Any: ...
       def set_cache(self, key: str, value: Any) -> None: ...
   ```

2. **import パス変更**: `services.parse.connectors.abaqus` → `jj_abaqus.parse`
   - 後方互換re-exportは`services/parse/connectors/abaqus/__init__.py`に残す

3. **設定読み込みの自律化**: `config.yaml`の`connectors.abaqus`セクションを自分でパース
   - 今回の`connector_configs`方式で既にこの構造を確立済み

4. **パーサー登録の外部化**: `jj`本体の`services/parse/__init__.py`でのimportを動的発見に変更
   ```python
   # 現在: 静的import
   import services.parse.connectors.abaqus.inp_parser

   # 将来: エントリーポイントによる動的発見
   for ep in importlib.metadata.entry_points(group="jj.parse_connectors"):
       ep.load()
   ```

5. **テストアセットの分離**: `shared/tests/test_asset1/`のAbaqusファイルをコネクタパッケージに複製 or サブモジュールで共有

#### Phase 3: 動的コネクタ発見（やや複雑）

```python
# jj本体のparse/__init__.pyでの動的発見
import importlib.metadata

def _discover_connectors():
    for ep in importlib.metadata.entry_points(group="jj.parse_connectors"):
        ep.load()  # __init_subclass__でパーサー自動登録

def _discover_dashboard_connectors():
    for ep in importlib.metadata.entry_points(group="jj.dashboard_connectors"):
        ep.load()
```

各プラグインの`setup.py`:
```python
setup(
    name="jj-abaqus-connector",
    entry_points={
        "jj.parse_connectors": [
            "abaqus = jj_abaqus.parse:register",
        ],
        "jj.dashboard_connectors": [
            "abaqus = jj_abaqus.dashboard:register",
        ],
    },
)
```

### 結論: 分離の容易性

| 評価項目 | 状況 |
|---------|------|
| **パーサー自動登録** | `__init_subclass__`パターン確立済み → プラグインと互換 |
| **configの分離** | 本statusで`connector_configs`方式に移行済み → 自律管理可能 |
| **UI結合度** | 本statusで`widgets.py`切り出し済み → 逆依存なし |
| **型依存** | `jj_types`に集約されている → SDK切り出し容易 |
| **キャッシュ依存** | `GraphStorage`直接参照 → Protocol化が必要（唯一の中程度作業） |
| **テストデータ** | `shared/tests/test_asset1`に集約 → 再配置が必要 |

**総合評価**: 現在の構成から完全分離するための技術的障壁は低い。今回の`connector_configs`方式への移行と`widgets.py`切り出しにより、主要な結合ポイントが解消された。残る作業はSDK定義・キャッシュIF抽象化・動的発見の3点で、段階的に進められる。

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
- [ ] プラグイン化Phase 1: jj-sdkパッケージの定義（jj_types / parse_base / export_base / dashboard_base切り出し）
- [ ] プラグイン化Phase 2: GraphStorage → CacheProviderプロトコル抽象化
- [ ] プラグイン化Phase 3: entry_points動的発見によるコネクタ登録

---

## 設計上の懸念（status-076からの引き継ぎ）

- [x] ~~DashboardConfig.material_curve_columnsはAbaqusキーワード名に依存~~ → connector_configs方式で解消
- [x] ~~_render_material_page()内でapp.pyの_try_render_aggrid()をimport~~ → widgets.pyで解消
- [ ] Abaqus parse層のキャッシュがGraphStorageに直接依存 → プラグイン化Phase 2で対応予定
