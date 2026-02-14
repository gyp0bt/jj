[READMEへ戻る](../../README.md)

# status-086: SDK外部化・プラグインレジストリ・Abaqus/Obsidianプラグイン分離

**日付**: 2026-02-14
**担当**: Claude Code

---

## 概要

status-085のTODO「プラグイン化Phase 3: entry_points動的発見」「jj-sdk独立パッケージ化」「CacheProvider DI注入メカニズム確立」を実施:

1. **CacheProvider DI注入** — GraphServiceコンストラクタがCacheProviderプロトコル型を受け入れるよう変更
2. **プラグインレジストリ基盤** — `services/sdk/plugin_registry.py`で`entry_points`動的発見メカニズムを実装
3. **Abaqusプラグインパッケージ** — `services/plugins/abaqus/`にAbaqus関連ロジックを集約
4. **Obsidianプラグインパッケージ** — `services/plugins/obsidian/`にObsidian関連ロジックを集約
5. **pyproject.toml** — jjパッケージ定義、entry_pointsによるプラグイン登録、optional-dependencies定義
6. **コアからのハードコード除去** — `GraphService`と`services/parse/__init__.py`のAbaqus/Obsidian直接importを除去

---

## 1. CacheProvider DI注入メカニズム

### 変更前

```python
class GraphService:
    def __init__(
        self,
        storage: GraphStorage | None = None,  # 具体型に依存
    ) -> None:
        self.storage = storage or GraphStorage()
```

### 変更後

```python
class GraphService:
    def __init__(
        self,
        storage: Union[CacheProvider, GraphStorage, None] = None,  # Protocol型を受入
    ) -> None:
        self.storage: CacheProvider = storage or GraphStorage()
```

- `CacheProvider`プロトコル型を受け入れることで、テストやプラグインで独自のストレージ実装を注入可能
- `GraphStorage`は引き続きデフォルト実装として動作
- 既存コードへの影響なし（後方互換）

---

## 2. プラグインレジストリ基盤（`services/sdk/plugin_registry.py`）

### アーキテクチャ

```
load_all_plugins()
├── 1. _load_builtin_plugins()     # 内蔵プラグインのインポート（フォールバック）
│   ├── services.plugins.abaqus    # → Abaqusパーサー・ダッシュボードコネクター登録
│   └── services.plugins.obsidian  # → Obsidianパーサー・エクスポーター登録
├── 2. discover_entry_point_plugins("jj.plugins")  # pyproject.tomlのentry_points
│   └── 外部プラグインのregister()呼び出し
└── 3. discover_entry_point_plugins("jj.parsers" / "jj.exporters" / ...)
```

### 主要関数

| 関数 | 説明 |
|------|------|
| `load_all_plugins()` | 全プラグインの発見・ロード（冪等、初回のみ実行） |
| `discover_entry_point_plugins(group)` | 指定entry_pointsグループからプラグイン発見 |
| `reset_plugins()` | ロード状態リセット（テスト用） |

### entry_pointsグループ

| グループ | 説明 |
|----------|------|
| `jj.plugins` | プラグインパッケージのregister()関数 |
| `jj.parsers` | 個別AbstractFileParserモジュール |
| `jj.exporters` | 個別AbstractExporterモジュール |
| `jj.dashboard_connectors` | 個別DashboardPageConnectorモジュール |

---

## 3. Abaqusプラグインパッケージ（`services/plugins/abaqus/`）

### 登録されるコンポーネント

| カテゴリ | コンポーネント | 登録先 |
|----------|-------------|--------|
| パーサー | AbaqusInpParser (priority 60) | _parser_registry |
| パーサー | AbaqusResultParser (priority 70) | _parser_registry |
| パーサー | AbaqusMeshParser (priority 80) | _parser_registry |
| パーサー | AbaqusDiffParser (priority 90) | _parser_registry |
| ダッシュボード | AbaqusMaterialPageConnector | DashboardPageConnector._registry |

### 元のインポート箇所

```python
# Before (services/graph/__init__.py):
import services.parse.connectors.abaqus.inp_parser  # noqa: F401
import services.parse.connectors.abaqus.result_parser  # noqa: F401
import services.parse.connectors.abaqus.mesh_parser  # noqa: F401
import services.parse.connectors.abaqus.diff_parser  # noqa: F401

# After:
from services.sdk.plugin_registry import load_all_plugins
load_all_plugins()  # services.plugins.abaqus.register() が自動的に呼ばれる
```

---

## 4. Obsidianプラグインパッケージ（`services/plugins/obsidian/`）

### 登録されるコンポーネント

| カテゴリ | コンポーネント | 登録先 |
|----------|-------------|--------|
| パーサー | DailyNoteParser (priority 95) | _parser_registry |
| エクスポーター | ObsidianExporter (format "obsidian") | _exporter_registry |

---

## 5. pyproject.toml（jjパッケージ定義）

### entry_points定義

```toml
[project.entry-points."jj.plugins"]
abaqus = "services.plugins.abaqus:register"
obsidian = "services.plugins.obsidian:register"
```

### optional-dependencies

| グループ | 依存パッケージ |
|----------|---------------|
| abaqus | chardet, ftfy, numpy, pandas, scipy |
| obsidian | pyyaml |
| dashboard | streamlit, streamlit-aggrid, plotly |
| api | fastapi, uvicorn |
| neo4j | neo4j |
| ssh | paramiko |
| dev | pytest, pytest-cov |
| all | 全グループ |

---

## 6. SDK公開APIの拡充

`services/sdk/__init__.py`に以下を追加:

| エクスポート | 説明 |
|-------------|------|
| `load_all_plugins` | プラグインロード関数 |
| `discover_entry_point_plugins` | entry_points発見関数 |
| `reset_plugins` | プラグインリセット（テスト用） |

---

## テスト結果

```
1003 passed, 59 skipped, 4 failed (既存の依存パッケージ未インストール問題)
```

- **1003 passed**: 変更による回帰なし
- **4 failed**: 全て既存の問題（pandas/pymesh未インストール、_parse_material_curve_columnsインポートエラー）
- **59 skipped**: 変更なし

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `services/sdk/plugin_registry.py` | **新規**: プラグイン動的発見・登録メカニズム |
| `services/plugins/__init__.py` | **新規**: プラグインパッケージルート |
| `services/plugins/abaqus/__init__.py` | **新規**: Abaqusプラグインエントリ |
| `services/plugins/obsidian/__init__.py` | **新規**: Obsidianプラグインエントリ |
| `pyproject.toml` | **新規**: パッケージ定義・entry_points・optional-deps |
| `services/graph/__init__.py` | 更新: CacheProvider DI注入 + プラグイン動的発見 |
| `services/parse/__init__.py` | 更新: ハードコードimport除去 |
| `services/sdk/__init__.py` | 更新: plugin_registry関数エクスポート追加 |

---

## アーキテクチャ変更

```
Before:
  services/graph/__init__.py
    ├── import services.parse.connectors.abaqus.inp_parser    # ハードコード
    ├── import services.parse.connectors.abaqus.result_parser  # ハードコード
    ├── import services.parse.connectors.abaqus.mesh_parser    # ハードコード
    ├── import services.parse.connectors.abaqus.diff_parser    # ハードコード
    └── import services.parse.connectors.obsidian.daily_parser # ハードコード
  GraphService(storage: GraphStorage | None)  # 具体型

After:
  services/graph/__init__.py
    └── from services.sdk.plugin_registry import load_all_plugins
        load_all_plugins()  # entry_points + フォールバックで動的発見

  services/plugins/
    ├── abaqus/  → Abaqus全コンポーネントの集約エントリ
    └── obsidian/ → Obsidian全コンポーネントの集約エントリ

  services/sdk/plugin_registry.py → 動的発見メカニズム
    ├── load_all_plugins()         # 冪等な全プラグインロード
    ├── discover_entry_point_plugins() # entry_points API
    └── _load_builtin_plugins()    # フォールバック

  GraphService(storage: Union[CacheProvider, GraphStorage, None])  # Protocol型
```

### プラグイン登録フロー

```
pyproject.toml
  [project.entry-points."jj.plugins"]
  abaqus = "services.plugins.abaqus:register"
  obsidian = "services.plugins.obsidian:register"

          ↓ pip install -e . 時

importlib.metadata.entry_points(group="jj.plugins")
  → services.plugins.abaqus:register()
    → import services.parse.connectors.abaqus.inp_parser
      → AbaqusInpParser.__init_subclass__
        → _parser_registry.append(AbaqusInpParser)
```

---

## TODO / 次回引き継ぎ事項

### 本status由来
- [ ] 外部プラグイン開発者向けドキュメント整備（How to write a jj plugin）
- [ ] `pip install -e .` によるentry_points動的発見の実環境テスト
- [ ] Abaqusコアロジック（`services/parse/connectors/abaqus/__init__.py`の1890行）の物理的なファイル移動検討（現在はimport経由で集約のみ）
- [ ] jj-sdk独立パッケージとしてPyPI公開検討（jjと分離したwheelビルド）

### 過去status引き継ぎ（status-085から継続）
- [ ] services/query テストのQueryService部分がnumpy未インストールでskip — 実環境で確認要
- [ ] 実環境でCSV配列取り込みの動作確認
- [ ] 配列プロットページ: 保存済みビュー対応・フィルタ連携
- [ ] 物性一覧ページ: 物性比較機能・使用関係表示
- [ ] REST API拡張（追加エンドポイント検討）
- [ ] `_try_render_aggrid` / `_estimate_column_width` は widgets.py への委譲ラッパーとして残存
- [ ] dashboard分離時のconfigアクセス問題

---

## 設計上の懸念

- [ ] entry_points発見は`pip install -e .`が前提。開発環境でpip installしていない場合は内蔵フォールバック（`_load_builtin_plugins()`）が使われる。両方のパスでの動作確認が必要
- [ ] Abaqusプラグインの`chardet`/`numpy`等の依存は`optional-dependencies`に分離したが、現在の`requirements.txt`との二重管理を解消する必要がある
- [ ] CacheProviderの`load_abq_data`/`save_abq_data`メソッドはAbaqus固有。将来的にプラグインごとのキャッシュ名前空間に分離するか検討
