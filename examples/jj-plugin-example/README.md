[← README.md](../../README.md)

# jj-plugin-example — 外部プラグインパッケージの実例

jjの外部プラグインシステムを使って独自のソルバー対応を追加するサンプルパッケージ。

## ディレクトリ構成

```
jj-plugin-example/
├── pyproject.toml              # entry_points設定
├── README.md
└── src/
    └── jj_plugin_example/
        ├── __init__.py         # register()関数（プラグインエントリ）
        ├── parser.py           # ExampleSolverParser（AbstractFileParser）
        └── dashboard.py        # ExampleSolverPageConnector（DashboardPageConnector）
```

## セットアップ

```bash
# 開発モードでインストール
cd examples/jj-plugin-example
pip install -e .

# jjのプラグインとして自動検出される
jj parse /path/to/project
```

## プラグインの仕組み

### 1. entry_points登録（pyproject.toml）

```toml
[project.entry-points."jj.plugins"]
example_solver = "jj_plugin_example:register"
```

jjの起動時に`jj.plugins`グループのentry_pointsが自動発見され、
`register()`関数が呼び出される。

### 2. register()関数（__init__.py）

```python
def register() -> None:
    import jj_plugin_example.parser     # パーサーが自動登録される
    import jj_plugin_example.dashboard  # コネクターが自動登録される
```

各モジュールのインポートにより`__init_subclass__`が発動し、
レジストリに自動登録される。

### 3. パーサー実装（parser.py）

```python
from services.sdk import AbstractFileParser, ProjectGraph

class ExampleSolverParser(AbstractFileParser):
    priority = 60
    requires_full = False

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        # ソルバー固有のパースロジック
        return graph
```

### 4. ダッシュボードコネクター実装（dashboard.py）

```python
from services.sdk import DashboardPageConnector

class ExampleSolverPageConnector(DashboardPageConnector):
    page_label = "Exampleサマリー"
    connector_key = "example_solver"

    def is_available(self, provider):
        # データが存在するか判定
        ...

    def render_page(self, provider, dashboard_config):
        # Streamlit描画
        ...

    def generate_html(self, provider, dashboard_config):
        # HTMLエクスポート
        ...
```

## 利用可能なentry_pointグループ

| グループ | 用途 | 登録方式 |
|----------|------|---------|
| `jj.plugins` | メインプラグイン（register()呼び出し） | 関数呼び出し |
| `jj.parsers` | 個別パーサー | モジュールインポート |
| `jj.exporters` | 個別エクスポーター | モジュールインポート |
| `jj.dashboard_connectors` | ダッシュボードコネクター | モジュールインポート |
| `jj.dashboard_pages` | PageComponent/ViewConfig | モジュールインポート |

## 公開SDK（services.sdk）

外部プラグインは`services.sdk`からのみインポートする:

```python
from services.sdk import (
    AbstractFileParser,    # パーサー基底
    AbstractExporter,      # エクスポーター基底
    DashboardPageConnector,# ダッシュボードコネクター基底
    ProjectGraph,          # プロジェクトグラフ
    Node, Relation,        # グラフ型定義
    GraphModel,            # グラフモデル
    CacheProvider,         # キャッシュプロトコル
)
```
