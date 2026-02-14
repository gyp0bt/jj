[READMEへ戻る](../../README.md)

# status-085: API層リファクタリング・プラグイン化・CLI/Dashboard分離

**日付**: 2026-02-13
**担当**: Claude Code

---

## 概要

status-084のTODO「API層の完全なservices.service依存化」「プラグイン化Phase 1-3」「jj-cli、jj-dashboard分離」を実施:

1. **ApiServiceクラス新設** — API層がGraphService/DashboardDataProviderを直接参照せず、services.service経由で操作
2. **routes.pyのservices.service完全依存化** — 全遅延インポートをApiServiceに集約
3. **jj-sdkパッケージ新設（プラグイン化Phase 1）** — プラグイン開発者向け公開インターフェース集約
4. **CacheProviderプロトコル定義（プラグイン化Phase 2）** — GraphStorage抽象化でストレージバックエンド差し替え可能に
5. **jj-cli分離** — dashboard/serveランチャーをlaunchers.pyに抽出、graph.pyからの依存分離
6. **jj-dashboard分離** — 分離境界の明確化、オプショナル依存関係定義

---

## 1. ApiService（API層のservices.service完全依存化）

### 変更前

```python
# services/api/routes.py が直接参照
from services.graph import GraphService          # 直接参照
from services.dashboard.data_provider import DashboardDataProvider  # 直接参照
from config import GraphConfig                    # 直接参照
```

### 変更後

```python
# services/api/routes.py は services.service のみに依存
from services.service import ApiService, QueryService
# GraphService, DashboardDataProvider は ApiService 内部で遅延ロード
```

### ApiServiceのメソッド

| メソッド | 説明 |
|----------|------|
| `get_graph()` | GraphModel取得（遅延ロード） |
| `get_nodes()` | 全ノードリスト取得 |
| `get_relations()` | 全リレーションリスト取得 |
| `get_node_card(id)` | ノード詳細カード情報 |
| `get_related_files(id, label)` | 関連ノード一覧 |
| `get_property_keys()` | プロパティキー一覧 |
| `get_summary()` | サマリー統計（go_file_count含む） |
| `get_status_summary()` | 実行ステータスサマリー |
| `parse_project(full)` | 再パース実行 |
| `reload_graph()` | キャッシュクリア＆再ロード |
| `filter_relations(label)` | ラベルフィルタ付きリレーション取得 |

---

## 2. jj-sdk パッケージ（プラグイン化Phase 1）

### パッケージ構成

```
services/sdk/
├── __init__.py     # 公開API（全インターフェースを再エクスポート）
└── cache.py        # CacheProviderプロトコル定義
```

### 公開API一覧

| カテゴリ | エクスポート | 由来 |
|----------|------------|------|
| 型定義 | `Node`, `Relation`, `GraphModel` | jj_types |
| パーサー基盤 | `AbstractFileParser` | services.parse.base |
| プロジェクトグラフ | `ProjectGraph`, `ProjectFile`, `ProjectDirectory`, `ProjectNonFileNode` | services.graph.project_graph |
| エクスポーター基盤 | `AbstractExporter` | services.export |
| ダッシュボード基盤 | `DashboardPageConnector` | services.dashboard.connectors |
| キャッシュ | `CacheProvider` | services.sdk.cache |

### 使用例

```python
# プラグイン開発者はsdkパッケージのみインポート
from services.sdk import AbstractFileParser, ProjectGraph

class MyParser(AbstractFileParser):
    priority = 50
    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        # カスタムパーサーロジック
        return graph
```

---

## 3. CacheProviderプロトコル（プラグイン化Phase 2）

`typing.Protocol`を使用したGraphStorageの抽象インターフェース:

```python
@runtime_checkable
class CacheProvider(Protocol):
    def load(self, project_root, filename=None) -> GraphModel: ...
    def save(self, project_root, graph, filename=None) -> Path: ...
    def load_timestamps(self, project_root) -> dict[str, float]: ...
    def save_timestamps(self, project_root, timestamps) -> Path: ...
    def load_abq_data(self, project_root, file_path, expected_mtime) -> Any: ...
    def save_abq_data(self, project_root, file_path, abq_data, mtime) -> Path: ...
```

- `GraphStorage`はこのプロトコルを満たす（テスト検証済み）
- プラグインはCacheProviderプロトコルに依存し、具体実装に依存しない
- 将来的にDB/リモートバックエンドへの差し替えが可能

---

## 4. jj-cli分離

### 変更内容

- `services/cli/launchers.py` 新設: dashboard/serveの起動ロジックを`graph.py`から分離
- `graph.py`の`_run_dashboard()`/`_run_serve()`をlaunchers.pyへの薄い委譲に変更
- `_add_dashboard_args()`/`_add_serve_args()`もlaunchers.pyから再エクスポート

### 分離前

```
graph.py (1147行)
├── グラフコマンドロジック（init/parse/show/export/info/diff/credential）
├── dashboard引数定義 + ランチャー（streamlit subprocess）
└── serve引数定義 + ランチャー（uvicorn直接起動）
```

### 分離後

```
graph.py (1007行) → グラフコマンドロジックに集中
launchers.py (新規) → dashboard/serve起動ロジック
  ├── add_dashboard_args() / add_serve_args()
  ├── run_dashboard() → streamlit subprocess
  └── run_serve() → FastAPI + uvicorn
```

---

## 5. jj-dashboard分離

### 分離境界の定義

```
services/dashboard/
├── __init__.py         # 分離境界文書 + OPTIONAL_DEPS定義
├── data_provider.py    # [jjコア残留] DashboardDataProvider（UI非依存）
├── connectors/         # [jjコア残留] DashboardPageConnector基盤
├── query.py            # [jjコア残留] services/queryの再エクスポート
├── app.py              # [jj-dashboard候補] Streamlit UI
├── widgets.py          # [jj-dashboard候補] UI共有ヘルパー
└── html_export.py      # [jj-dashboard候補] HTMLエクスポート
```

### オプショナル依存関係

```python
OPTIONAL_DEPS = {
    "ui": ["streamlit>=1.30.0", "plotly>=5.0.0"],
    "aggrid": ["streamlit-aggrid>=1.0.0"],
    "excel": ["openpyxl>=3.0.0"],
}
```

---

## テスト結果

### test_api_service.py（新規: 14テスト）

```
14 passed
```

| テストクラス | テスト数 | 内容 |
|---|---|---|
| TestApiServiceGetGraph | 4 | get_graph/get_nodes/get_relations/遅延ロード |
| TestApiServiceFilter | 3 | filter_relations（ラベル有/無/全件） |
| TestApiServiceReload | 2 | reload_graph/parse_project |
| TestApiServiceProvider | 5 | get_summary/get_node_card/get_property_keys/get_status_summary |

### test_sdk.py（新規: 15テスト）

```
15 passed
```

| テストクラス | テスト数 | 内容 |
|---|---|---|
| TestSdkExports | 6 | 全公開APIのインポート検証 |
| TestCacheProviderProtocol | 3 | GraphStorageプロトコル準拠/メソッド存在/モック実装 |
| TestSdkTypes | 6 | SDK型と元モジュール型の同一性検証 |

### 既存テスト（回帰テスト）

```
974 passed, 59 skipped, 8 failed
```

- **974 passed**: 変更による回帰なし（status-084のテスト結果を維持）
- **8 failed**: 全て既存の問題（pandas/pymesh未インストール、_parse_material_curve_columnsインポートエラー）
- **59 skipped**: 変更なし

### 合計

```
新規テスト 29件: 29 passed
既存テスト: 974 passed, 59 skipped, 8 failed（変更前と同数）
```

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `services/service/api_service.py` | **新規**: ApiServiceクラス |
| `services/service/__init__.py` | 更新: ApiServiceエクスポート追加 |
| `services/api/routes.py` | 更新: ApiService/QueryService経由に変更 |
| `services/sdk/__init__.py` | **新規**: SDK公開API |
| `services/sdk/cache.py` | **新規**: CacheProviderプロトコル |
| `services/cli/launchers.py` | **新規**: dashboard/serveランチャー |
| `services/cli/graph.py` | 更新: launchers.pyへの委譲 |
| `services/dashboard/__init__.py` | 更新: 分離境界文書+OPTIONAL_DEPS |
| `tests/test_api_service.py` | **新規**: ApiService単体テスト14件 |
| `tests/test_sdk.py` | **新規**: SDK/CacheProviderテスト15件 |
| `docs/status/status-085.md` | 本ステータスファイル（新規） |

---

## アーキテクチャ変更

```
Before:
  services/api/routes.py → GraphService / DashboardDataProvider / GraphConfig 直接参照
  services/cli/graph.py  → dashboard/serve ランチャーロジックが混在（1147行）
  プラグインAPI → 内部モジュール直接参照が必要

After:
  services/api/routes.py → services.service.ApiService / QueryService のみに依存
  services/cli/graph.py  → launchers.py に dashboard/serve を分離（1007行 + launchers.py）
  services/sdk/           → プラグイン開発者向け公開インターフェース集約
    ├── __init__.py        ← 全公開APIの再エクスポート
    └── cache.py           ← CacheProvider Protocol（GraphStorage抽象化）
  services/dashboard/     → 分離境界を明確化、オプショナル依存定義
```

### 依存関係グラフ（リファクタリング後）

```
jj_types (型定義)
    ↓
services.sdk (公開API) ← プラグイン開発者はここのみ参照
    ├── AbstractFileParser, ProjectGraph
    ├── AbstractExporter
    ├── DashboardPageConnector
    └── CacheProvider (Protocol)
        ↑
        services.graph.storage.GraphStorage (実装)

services.service (オーケストレーション層)
    ├── ApiService      ← API専用サービス（NEW）
    ├── QueryService    ← クエリフィルタ
    ├── GraphCommandService ← CLI向けビジネスロジック
    └── InfoService     ← ノード情報検索

services.api.routes → services.service.{ApiService, QueryService} のみ
services.cli/
    ├── graph.py   → services.service.GraphCommandService
    └── launchers.py → services.api / streamlit subprocess
services.dashboard/
    ├── data_provider.py (jjコア: UI非依存)
    └── app.py / widgets.py / html_export.py (jj-dashboard候補)
```

---

## TODO / 次回引き継ぎ事項

### 本status由来
- [ ] プラグイン化Phase 3: entry_points動的発見によるコネクタ登録（pyproject.tomlベース）
- [ ] jj-sdkの独立パッケージ化検討（pip installable化）
- [ ] CacheProviderの実際のDI注入メカニズム確立（GraphServiceのコンストラクタ経由が有力）

### 過去status引き継ぎ（status-084から継続）
- [ ] services/query テストのQueryService部分がnumpy未インストールでskip — 実環境で確認要
- [ ] 実環境でCSV配列取り込みの動作確認
- [ ] 配列プロットページ: 保存済みビュー対応・フィルタ連携
- [ ] 物性一覧ページ: 物性比較機能・使用関係表示
- [ ] REST API拡張（追加エンドポイント検討）

---

## 設計上の懸念

- [ ] `_try_render_aggrid` / `_estimate_column_width` は widgets.py への委譲ラッパーとして残存。widgets.py自体がStreamlit依存のため、テスト移行はStreamlitモック or 統合テストが必要（status-083から継続）
- [ ] jj-sdkのバージョニング戦略: jj本体と同一バージョンにするか独立にするか
- [ ] CacheProviderのDI: 現状GraphServiceのコンストラクタでGraphStorageを受け取る形。CacheProvider Protocol経由にするにはGraphServiceの型アノテーションを更新する必要がある
- [ ] dashboard分離時のconfigアクセス: DashboardDataProviderはconfig.vocabを受け取るが、dashboard.app.pyはGraphConfig.loadを直接呼んでいる
