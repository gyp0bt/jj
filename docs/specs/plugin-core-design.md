[← README.md](../../README.md)

# プラグインコア設計 — CI/Dashboard/Server統一アーキテクチャ

> **ステータス**: 設計仕様（P-1〜P-8実装完了）
> **作成日**: 2026-03-14
> **トラック**: T10 プラグイン完全分離・コア共通設計

---

## 1. 背景と課題

### 1.1 現行アーキテクチャの問題点

現在のjjは CLI / Dashboard(Streamlit) / REST API(FastAPI) の3つのインターフェースを持つが、
それぞれが異なるサービスラッパーを経由してGraphServiceにアクセスしている。

```
現行:
  CLI ──→ GraphCommandService ──→ GraphService
  Dashboard ──→ DashboardDataProvider ──→ GraphService
  API ──→ ApiService ──→ GraphService
```

| # | 課題 | 詳細 |
|---|------|------|
| C-1 | **インターフェース間の機能格差** | CLI にある機能が API にない、Dashboard にある可視化が CLI から使えない等 |
| C-2 | **サービスラッパーの重複** | GraphCommandService / ApiService / DashboardDataProvider が同じロジックを再実装 |
| C-3 | **プラグインの暗黙的登録** | `__init_subclass__` で自動登録されるが、プラグインが「何を提供するか」の宣言がない |
| C-4 | **ダッシュボードのStreamlit密結合** | `DashboardPageConnector.render_page()` が `streamlit` に直接依存 |
| C-5 | **プラグインのライフサイクル管理不在** | load順序制御、初期化/終了フック、依存関係宣言がない |
| C-6 | **新インターフェース追加コスト** | 新しいフロントエンド（TUI, Web SPA等）を追加するたびにサービスラッパーが必要 |

### 1.2 設計目標

1. **プラグイン完全分離**: プラグインがコアに一切依存せずに拡張を提供できる
2. **インターフェース均質化**: CI / Dashboard / Server が同一のコアAPIを消費する
3. **宣言的プラグイン**: プラグインが提供する機能を明示的に宣言する
4. **漸進的移行**: 既存の `__init_subclass__` パターンを壊さずに拡張する

---

## 2. 全体アーキテクチャ

### 2.1 目標構造

```
                  ┌──────────────────────────────┐
                  │        JJApp (統一コア)        │
                  │                              │
                  │  ┌─────────────────────────┐  │
                  │  │   PluginManager         │  │
                  │  │   ┌─ PluginManifest[]   │  │
                  │  │   └─ CapabilityRegistry │  │
                  │  └─────────────────────────┘  │
                  │                              │
                  │  ┌─────────────────────────┐  │
                  │  │   CoreServices           │  │
                  │  │   ┌─ GraphService        │  │
                  │  │   ├─ QueryService        │  │
                  │  │   ├─ ParsePipeline       │  │
                  │  │   ├─ ExportPipeline      │  │
                  │  │   └─ DataProvider        │  │
                  │  └─────────────────────────┘  │
                  │                              │
                  │  ┌─────────────────────────┐  │
                  │  │   EventBus (Pub/Sub)     │  │
                  │  └─────────────────────────┘  │
                  └──────────┬───────────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
         ┌────┴────┐   ┌────┴────┐   ┌────┴────┐
         │  CLI    │   │Dashboard│   │  API    │
         │Adapter  │   │Adapter  │   │Adapter  │
         └─────────┘   └─────────┘   └─────────┘
```

### 2.2 レイヤー定義

| レイヤー | 責務 | 依存方向 |
|---------|------|---------|
| **JJApp** | アプリケーションのライフサイクル管理、DI コンテナ | 下位レイヤーを保持 |
| **PluginManager** | プラグインの発見・登録・マニフェスト管理 | JJApp内部 |
| **CoreServices** | GraphService, ParsePipeline 等のビジネスロジック | データモデル(jj_types)のみに依存 |
| **EventBus** | コア⇔プラグイン間の疎結合通信 | JJApp内部 |
| **Interface Adapters** | CLI/Dashboard/API固有の入出力変換 | JJApp に依存（逆方向の依存は禁止） |

---

## 3. PluginManifest — 宣言的プラグイン

### 3.1 マニフェスト定義

```python
# services/sdk/plugin_manifest.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class PluginManifest:
    """プラグインの宣言的メタデータ

    プラグインが何を提供するかを明示的に宣言する。
    entry_pointsのregister()関数からこのオブジェクトを返すことで、
    PluginManagerがプラグインの能力を把握する。
    """

    # === 識別 ===
    name: str                          # 一意識別子 (例: "abaqus")
    version: str = "0.0.0"            # プラグインバージョン
    description: str = ""              # 説明文

    # === 提供機能 (Capabilities) ===
    parsers: list[str] = field(default_factory=list)
    # パーサーモジュールパス (例: ["services.parse.connectors.abaqus.inp_parser"])

    exporters: list[str] = field(default_factory=list)
    # エクスポーターモジュールパス

    dashboard_pages: list[str] = field(default_factory=list)
    # ダッシュボードコネクターモジュールパス

    cli_commands: list[str] = field(default_factory=list)
    # CLIサブコマンド拡張モジュールパス

    api_routes: list[str] = field(default_factory=list)
    # APIルート拡張モジュールパス

    # === 依存関係 ===
    depends_on: list[str] = field(default_factory=list)
    # 依存プラグイン名 (例: ["core"])

    optional_dependencies: dict[str, str] = field(default_factory=dict)
    # オプション依存 {パッケージ名: pip名} (例: {"h5py": "h5py>=3.0"})

    # === 設定 ===
    config_schema: dict[str, Any] = field(default_factory=dict)
    # プラグイン固有設定のJSONスキーマ

    # === ライフサイクルフック ===
    on_load: Callable[[], None] | None = None
    # プラグインロード時に実行されるフック

    on_unload: Callable[[], None] | None = None
    # プラグインアンロード時に実行されるフック
```

### 3.2 プラグイン実装例（移行後）

```python
# services/plugins/abaqus/__init__.py

from services.sdk.plugin_manifest import PluginManifest


def register() -> PluginManifest:
    """Abaqusプラグインを登録する

    Returns:
        プラグインマニフェスト
    """
    return PluginManifest(
        name="abaqus",
        version="0.3.0",
        description="Abaqus CAE解析ファイルの解析・可視化",
        parsers=[
            "services.parse.connectors.abaqus.parameter_parser",
            "services.parse.connectors.abaqus.inp_parser",
            "services.parse.connectors.abaqus.result_parser",
            "services.parse.connectors.abaqus.mesh_parser",
            "services.parse.connectors.abaqus.mesh_inherit_parser",
            "services.parse.connectors.abaqus.material_assignment_parser",
            "services.parse.connectors.abaqus.diff_parser",
            "services.parse.connectors.abaqus.elset_parser",
        ],
        dashboard_pages=[
            "services.dashboard.connectors.abaqus",
        ],
        cli_commands=[
            "services.plugins.abaqus.cli",   # jj submit 等
        ],
        depends_on=[],
        optional_dependencies={
            "pymesh": "modules/pymesh",       # メッシュ品質統計
        },
        config_schema={
            "type": "object",
            "properties": {
                "ssh_host": {"type": "string"},
                "ssh_user": {"type": "string"},
            },
        },
    )
```

### 3.3 後方互換性

現行の `register()` 関数は `None` を返す（暗黙的 import トリガー方式）。
PluginManager は戻り値が `PluginManifest` かどうかで新旧を判定する。

```python
# PluginManager内部
result = plugin_register_fn()
if isinstance(result, PluginManifest):
    # 新方式: マニフェストベースの登録
    self._register_manifest(result)
else:
    # 旧方式: __init_subclass__ による暗黙的登録（後方互換）
    pass
```

---

## 4. JJApp — 統一アプリケーションコア

### 4.1 クラス設計

```python
# services/app.py

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config import GraphConfig
from jj_types import GraphModel, Node, Relation
from services.sdk.cache import CacheProvider


@dataclass
class JJApp:
    """jjアプリケーションの統一コア

    CLI / Dashboard / API のすべてのインターフェースが
    このオブジェクトのみに依存する。
    """

    project_root: Path
    config: GraphConfig = field(init=False)
    plugin_manager: PluginManager = field(init=False)
    event_bus: EventBus = field(init=False)

    # コアサービス（遅延初期化）
    _graph_service: Any = field(default=None, init=False, repr=False)
    _data_provider: Any = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.config = GraphConfig.load(base_dir=self.project_root)
        self.event_bus = EventBus()
        self.plugin_manager = PluginManager(app=self)
        self.plugin_manager.load_all()

    # === Graph操作 (CLI/Dashboard/API共通) ===

    def parse(self, *, full: bool = False) -> ParseResult:
        """プロジェクトをパースしてグラフを生成・保存"""
        ...

    def load_graph(self, *, resolve_externalized: bool = False) -> GraphModel:
        """保存済みグラフをロード"""
        ...

    def export(self, format: str, **kwargs) -> ExportResult:
        """グラフを指定形式でエクスポート"""
        ...

    # === クエリ操作 (CLI/Dashboard/API共通) ===

    def query_nodes(
        self,
        *,
        types: list[str] | None = None,
        names: list[str] | None = None,
        properties: dict[str, Any] | None = None,
    ) -> list[Node]:
        """ノード検索"""
        ...

    def query_relations(
        self,
        *,
        labels: list[str] | None = None,
        node_id: int | None = None,
    ) -> list[Relation]:
        """リレーション検索"""
        ...

    def get_summary(self) -> dict[str, Any]:
        """グラフサマリー統計"""
        ...

    # === データプロバイダー (Dashboard/API共通) ===

    def get_table_data(self, **filters) -> list[dict[str, Any]]:
        """テーブル表示用データ"""
        ...

    def get_node_card(self, node_id: int) -> dict[str, Any] | None:
        """ノード詳細カード"""
        ...

    def get_status_summary(self) -> dict[str, Any]:
        """ステータスサマリー"""
        ...

    # === プラグイン情報 ===

    def get_plugins(self) -> list[PluginInfo]:
        """ロード済みプラグイン一覧"""
        ...

    def get_capabilities(self) -> dict[str, list[str]]:
        """利用可能な拡張機能一覧"""
        ...
```

### 4.2 インターフェースアダプター

各インターフェースは JJApp を受け取り、自身のフレームワーク固有の変換のみ行う。

```python
# CLI Adapter
class CLIAdapter:
    def __init__(self, app: JJApp): ...
    def run_parse(self, args: argparse.Namespace) -> None:
        result = self.app.parse(full=args.full)
        print(format_parse_result(result))  # CLI固有: テキスト整形

# Dashboard Adapter
class DashboardAdapter:
    def __init__(self, app: JJApp): ...
    def render_overview(self) -> None:
        summary = self.app.get_summary()
        st.metric("Nodes", summary["node_count"])  # Dashboard固有: Streamlit

# API Adapter
class APIAdapter:
    def __init__(self, app: JJApp): ...
    def get_graph(self) -> dict:
        graph = self.app.load_graph()
        return graph.model_dump()  # API固有: JSON変換
```

---

## 5. CapabilityRegistry — 拡張ポイントの型安全な管理

### 5.1 拡張ポイント定義

```python
# services/sdk/capabilities.py

from enum import Enum, auto


class Capability(Enum):
    """プラグインが提供できる拡張ポイント"""

    PARSER = auto()                # AbstractFileParser
    EXPORTER = auto()              # AbstractExporter
    DASHBOARD_PAGE = auto()        # DashboardPageConnector
    CLI_COMMAND = auto()           # CLIサブコマンド (新規)
    API_ROUTE = auto()             # APIルート (新規)
    EVENT_HANDLER = auto()         # イベントハンドラ (新規)
    CONFIG_SECTION = auto()        # 設定スキーマ拡張 (新規)
```

### 5.2 レジストリ

```python
@dataclass
class CapabilityRegistry:
    """プラグインが提供する機能の統合レジストリ

    既存の _parser_registry, _exporter_registry,
    DashboardPageConnector._registry を統合的に管理する。
    既存レジストリとの互換性を維持しつつ、メタデータを付加する。
    """

    _entries: dict[Capability, list[CapabilityEntry]] = field(default_factory=dict)

    def register(
        self,
        capability: Capability,
        provider: type | Callable,
        plugin_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """拡張ポイントを登録"""
        ...

    def get_all(self, capability: Capability) -> list[CapabilityEntry]:
        """特定の拡張ポイントの登録済み一覧を返す"""
        ...

    def get_by_plugin(self, plugin_name: str) -> dict[Capability, list[CapabilityEntry]]:
        """プラグイン名で登録済み機能をグループ化して返す"""
        ...


@dataclass(frozen=True)
class CapabilityEntry:
    """レジストリ登録エントリ"""

    capability: Capability
    provider: type | Callable    # 実際のクラスまたは関数
    plugin_name: str             # 提供元プラグイン名
    metadata: dict[str, Any] = field(default_factory=dict)
```

---

## 6. EventBus — コア⇔プラグイン間の疎結合通信

### 6.1 イベント定義

```python
# services/sdk/events.py

from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class Event:
    """基底イベント"""
    source: str  # 発行元プラグイン名 or "core"


@dataclass(frozen=True)
class GraphParsed(Event):
    """グラフパース完了イベント"""
    node_count: int
    relation_count: int
    full_mode: bool


@dataclass(frozen=True)
class GraphExported(Event):
    """グラフエクスポート完了イベント"""
    format: str
    output_path: str


@dataclass(frozen=True)
class PluginLoaded(Event):
    """プラグインロード完了イベント"""
    plugin_name: str
    capabilities: list[str]
```

### 6.2 EventBus実装

```python
# services/sdk/event_bus.py

from collections import defaultdict
from typing import Callable, Type

class EventBus:
    """シンプルなPub/Subイベントバス

    プラグインはイベントを購読し、コアやプラグインが発行する
    イベントに反応して処理を行う。
    同期実行。スレッドセーフ性は考慮しない（シングルスレッド前提）。
    """

    def __init__(self) -> None:
        self._handlers: dict[Type[Event], list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: Type[Event], handler: Callable) -> None:
        """イベントハンドラを登録"""
        self._handlers[event_type].append(handler)

    def publish(self, event: Event) -> None:
        """イベントを発行し、全ハンドラを同期実行"""
        for handler in self._handlers.get(type(event), []):
            handler(event)

    def clear(self) -> None:
        """全ハンドラをクリア（テスト用）"""
        self._handlers.clear()
```

---

## 7. CLI/APIプラグインコマンド拡張

### 7.1 CLIコマンド拡張ポイント

現行の `jj submit` はAbaqus固有だが、ハードコードされている。
プラグインがCLIサブコマンドを宣言的に追加できるようにする。

```python
# services/sdk/cli_extension.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class CLICommand:
    """プラグインが提供するCLIサブコマンド定義"""

    name: str                      # コマンド名 (例: "submit")
    help: str                      # ヘルプ文字列
    handler: Callable              # 実行関数 (args: argparse.Namespace) -> int
    add_arguments: Callable | None = None  # argparse.ArgumentParser → None
    parent: str = "root"           # 親コマンド ("root" or サブコマンドグループ)
```

### 7.2 APIルート拡張ポイント

```python
# services/sdk/api_extension.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class APIRoute:
    """プラグインが提供するAPIルート定義"""

    path: str                      # パス (例: "/api/v1/abaqus/materials")
    method: str = "GET"            # HTTPメソッド
    handler: Callable = None       # リクエストハンドラ
    summary: str = ""              # OpenAPI summary
    tags: list[str] = field(default_factory=list)
```

---

## 8. DashboardPageConnector の発展

### 8.1 レンダリング抽象化

現行の `render_page()` は Streamlit に直接依存する。
将来の SPA フロントエンド対応のため、データ取得とレンダリングを分離する。

```python
# 現行 (変更なし — 後方互換維持)
class DashboardPageConnector:
    def render_page(self, provider, config): ...      # Streamlit依存
    def generate_html(self, provider, config): ...    # HTML出力

# 新規追加 (オプショナル — 段階的移行)
class DashboardPageConnector:
    def get_page_data(self, provider, config) -> dict[str, Any]:
        """レンダリングに必要なデータを返す (フレームワーク非依存)

        Returns:
            JSON-serializableなデータ辞書。
            APIから呼べばそのままJSON応答として返せる。
        """
        return {}
```

### 8.2 API経由のダッシュボードデータ提供

```python
# JJApp に追加するメソッド
class JJApp:
    def get_dashboard_pages(self) -> list[DashboardPageInfo]:
        """利用可能なダッシュボードページ一覧"""
        ...

    def get_dashboard_page_data(
        self, page_label: str, **params
    ) -> dict[str, Any]:
        """指定ページのデータをJSON-serializable形式で返す

        CLI: テーブルとしてコンソール出力
        Dashboard: Streamlitウィジェットでレンダリング
        API: JSONレスポンスとして返却
        """
        ...
```

---

## 9. 移行戦略

### 9.1 フェーズ分割

| Phase | 内容 | 影響範囲 | 優先度 |
|-------|------|---------|--------|
| **P-1** | `PluginManifest` + `PluginManager` 実装 | `services/sdk/` 新規 | 高 |
| **P-2** | `JJApp` コアの実装 | `services/app.py` 新規 | 高 |
| **P-3** | 既存プラグインのマニフェスト対応 | `services/plugins/*/` 修正 | 中 |
| **P-4** | `EventBus` 実装 | `services/sdk/` 新規 | 中 |
| **P-5** | `CapabilityRegistry` 統合 | `services/sdk/` 新規 | 中 |
| **P-6** | CLIコマンド拡張ポイント | `services/sdk/`, CLI | 低 |
| **P-7** | APIルート拡張ポイント | `services/sdk/`, API | 低 |
| **P-8** | `DashboardPageConnector.get_page_data()` | Dashboard | 低 |

### 9.2 漸進的移行方針

1. **既存コードは壊さない**: `__init_subclass__` パターンはそのまま動作し続ける
2. **新規コードはJJApp経由**: 新機能は JJApp の API として追加する
3. **プラグインは段階的移行**: `register()` が `PluginManifest` を返すように順次変更
4. **テストは単調増加**: 各フェーズでテストを追加し、既存テストを壊さない

### 9.3 P-1: PluginManifest 実装詳細

```
新規ファイル:
  services/sdk/plugin_manifest.py   — PluginManifest dataclass
  services/sdk/capabilities.py      — Capability enum, CapabilityRegistry
  tests/test_plugin_manifest.py     — テスト

修正ファイル:
  services/sdk/plugin_registry.py   — load_all_plugins()でManifest対応分岐追加
```

### 9.4 P-2: JJApp 実装詳細

```
新規ファイル:
  services/app.py                   — JJApp クラス
  tests/test_app.py                 — テスト

修正方針:
  - GraphCommandService, ApiService の共通ロジックを JJApp に移動
  - 既存サービスはJJAppの薄いラッパーとして残す（後方互換）
  - DashboardDataProvider は JJApp 内部に統合
```

---

## 10. ファイル配置方針

### 10.1 SDK ディレクトリ（プラグイン開発者向けパブリックAPI）

```
services/sdk/
├── __init__.py                  # パブリックAPIの re-export
├── cache.py                     # CacheProvider (既存)
├── plugin_registry.py           # プラグインローダー (既存)
├── plugin_manifest.py           # PluginManifest (新規)
├── capabilities.py              # Capability, CapabilityRegistry (新規)
├── events.py                    # Event定義 (新規)
├── event_bus.py                 # EventBus (新規)
├── cli_extension.py             # CLICommand (新規)
└── api_extension.py             # APIRoute (新規)
```

### 10.2 プラグインパッケージの標準構成

```
services/plugins/{solver}/
├── __init__.py                  # register() → PluginManifest
├── parsers/                     # AbstractFileParser サブクラス
├── exporters/                   # AbstractExporter サブクラス
├── dashboard/                   # DashboardPageConnector サブクラス
├── cli.py                       # CLICommand 定義 (オプション)
├── api.py                       # APIRoute 定義 (オプション)
└── config_schema.json           # 設定スキーマ (オプション)
```

---

## 11. CI/Dashboard/Server の機能対照表

### 11.1 現行の機能対照

| 機能 | CLI | Dashboard | API | 備考 |
|------|-----|-----------|-----|------|
| parse | `jj parse` | — | `POST /parse` | Dashboard未対応 |
| show | `jj show` | テーブル表示 | `GET /nodes` | 表現形式が異なる |
| export | `jj export` | ダウンロードボタン | — | API未対応 |
| info | `jj info` | カード表示 | `GET /nodes/{id}` | |
| diff | `jj diff` | — | — | CLI限定 |
| run | `jj r` | — | — | CLI限定 |
| 物性一覧 | — | コネクター | — | Dashboard限定 |
| ML学習 | — | コネクター | — | Dashboard限定 |
| AI Assistant | — | コネクター | — | Dashboard限定 |
| submit | `jj submit` | Job Monitor | — | 部分的対応 |
| credential | `jj credential` | — | — | CLI限定 |

### 11.2 目標の機能対照（JJApp統一後）

| 機能 | JJApp メソッド | CLI | Dashboard | API |
|------|---------------|-----|-----------|-----|
| parse | `app.parse()` | テキスト出力 | ボタン+進捗 | JSON応答 |
| query | `app.query_nodes()` | テーブル出力 | AgGrid | JSON応答 |
| export | `app.export()` | ファイル保存 | ダウンロード | ファイル応答 |
| node detail | `app.get_node_card()` | 詳細テキスト | カードUI | JSON応答 |
| diff | `app.diff()` | unified diff | side-by-side | JSON diff |
| plugin pages | `app.get_dashboard_page_data()` | テーブル/YAML | Streamlit | JSON応答 |
| plugin info | `app.get_plugins()` | リスト出力 | サイドバー | JSON応答 |
| summary | `app.get_summary()` | テキスト | メトリクス | JSON応答 |

---

## 12. 設計判断の根拠

### 12.1 なぜ JJApp 単一オブジェクトか

- **Pros**: DIコンテナとして機能し、サービス間の依存関係を明示化。テスト時にモック注入が容易
- **Alternative**: サービスロケーターパターン → 暗黙的依存が増える。既存の問題を拡大するため不採用

### 12.2 なぜ EventBus か

- **Pros**: プラグイン間の通信をコアに依存せず実現。例: AbaqusプラグインがMLプラグインの学習結果を受信
- **Alternative**: コールバック直接呼び出し → プラグイン間の結合度が上がる。N×N依存になるため不採用
- **Scope**: シングルスレッド同期実行。非同期が必要になったら `asyncio.Queue` に移行可能

### 12.3 なぜ PluginManifest を dataclass にしたか

- **Pros**: 型安全、IDE補完、JSONスキーマへの変換が容易
- **Alternative**: dict / YAML ファイル → 型安全性がない。pyproject.toml に書くと表現力が不足
- **Design**: `frozen=True` で不変。プラグインロード後の変更を防ぐ

### 12.4 既存 `__init_subclass__` との共存

- `__init_subclass__` はPython的に自然なパターンであり、パーサー/エクスポーターの自動登録に最適
- PluginManifest は「何が登録されるか」のメタデータを提供するだけで、実際の登録メカニズムは変えない
- 結果として、既存プラグインは一切変更なしで動作し続ける

---

## 13. 未決事項・確認事項

| # | 事項 | 選択肢 | 推奨 |
|---|------|--------|------|
| Q-1 | JJApp のインスタンス化タイミング | CLI起動時 / on-demand | CLI起動時（軽量なので問題なし） |
| Q-2 | EventBus を async にするか | sync / async | sync（現行のシングルスレッド運用を前提） |
| Q-3 | プラグインの hot-reload 対応 | する / しない | しない（開発者はプロセス再起動前提） |
| Q-4 | 外部プラグイン（pip別パッケージ）の検証 | する / v0.4以降 | v0.4以降（現行は内蔵プラグインのみ） |
| Q-5 | DashboardPageConnector のデータ分離 | P-2で同時 / P-8で後発 | P-8で後発（Streamlit運用が安定している） |

---

## 14. 参照

- [02-parser.md](02-parser.md) — AbstractFileParser パターン
- [08-export.md](08-export.md) — AbstractExporter パターン
- [09-dashboard.md](09-dashboard.md) — DashboardPageConnector パターン
- [midterm-plan-v0.3.md](midterm-plan-v0.3.md) — v0.3.0 全体設計
- [t8-generic-data-management.md](t8-generic-data-management.md) — 汎用データ管理基盤
