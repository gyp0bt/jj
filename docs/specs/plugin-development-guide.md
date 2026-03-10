[← README.md](../../README.md)

# プラグイン開発ガイド

> jj プラグインの作成・登録・テストの手順書

---

## 概要

jj はプラグインアーキテクチャにより、ドメイン固有の機能を拡張できる。
プラグインは以下のコンポーネントを提供できる:

| コンポーネント | 基底クラス | 登録方式 | 配置先 |
|---------------|-----------|---------|--------|
| パーサー | `AbstractFileParser` | `__init_subclass__` 自動登録 | `services/parse/connectors/{solver}/` |
| エクスポーター | `AbstractExporter` | `__init_subclass__` 自動登録 | `services/export/connectors/` |
| ダッシュボードページ | `DashboardPageConnector` | `__init_subclass__` 自動登録 | `services/dashboard/connectors/` |
| Run Discoverer | `RunDiscoveryMixin` + `AbstractFileParser` | `__init_subclass__` 自動登録 | `services/parse/connectors/{solver}/` |

---

## クイックスタート: 新規プラグインの作成

### 1. ディレクトリ構造

```
services/plugins/myformat/
  __init__.py              # プラグインエントリ（register関数）

services/parse/connectors/myformat/
  __init__.py              # 空ファイル
  data_parser.py           # パーサー実装

tests/
  test_myformat_plugin.py  # テスト
```

### 2. プラグインエントリ (`services/plugins/myformat/__init__.py`)

```python
"""myformatプラグイン — ○○データの解析

[READMEへ戻る](../../../../README.md)
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_registered = False


def register() -> None:
    """プラグインの全コンポーネントを登録する"""
    global _registered
    if _registered:
        return
    _registered = True

    # パーサーのインポートで__init_subclass__が発動
    import services.parse.connectors.myformat.data_parser  # noqa: F401

    # ダッシュボードコネクター（optional依存がある場合）
    try:
        import services.dashboard.connectors.myformat  # noqa: F401
    except ImportError:
        logger.debug("ダッシュボードコネクター スキップ（依存不足）")

    logger.debug("myformatプラグインを登録完了")


# モジュールインポート時に自動登録
register()
```

### 3. パーサー実装 (`services/parse/connectors/myformat/data_parser.py`)

```python
"""myformatデータパーサー

[READMEへ戻る](../../../../../README.md)
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph


class MyFormatParser(AbstractFileParser):
    """○○ファイルのプロパティ抽出パーサー。"""

    priority = 55  # 実行順序（小さいほど先に実行）

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        for node in list(graph.model.nodes):
            path_str = node.properties.get("path", "")
            if not path_str:
                continue
            path = Path(path_str)
            if path.suffix.lower() != ".myext":
                continue

            # ファイルのプロパティを抽出してノードに付与
            full_path = graph.project_root / path
            if full_path.exists():
                node.properties["my_property"] = "value"

        return graph
```

### 4. pyproject.toml に登録

```toml
# optional-dependencies に追加
[project.optional-dependencies]
myformat = []  # 追加依存がある場合はここに列挙

# entry-points に追加
[project.entry-points."jj.plugins"]
myformat = "services.plugins.myformat:register"

# all グループにも追加
all = [
    "jj[...,myformat,...,dev]",
]
```

---

## パーサーの priority ガイドライン

| 範囲 | 用途 | 例 |
|------|------|-----|
| 10-19 | プロパティ前処理 | AbaqusParameterParser (15) |
| 50-59 | データ抽出 | ExperimentDataParser (56), MyFormatParser (55) |
| 60-69 | 構造解析 | AbaqusInpParser (60) |
| 70-79 | Run発見 | ExperimentRunDiscoverer (76) |
| 80-89 | 重い解析（`requires_full`） | AbaqusMeshParser (80) |
| 90-99 | 後処理・差分 | AbaqusDiffParser (90) |

---

## Run Discovery パターン

### RunDiscoveryMixin の使用

Runを自動発見するパーサーは `RunDiscoveryMixin` と `AbstractFileParser` を多重継承する。

```python
from services.parse.base import AbstractFileParser
from services.parse.run_discovery import (
    RUN_STATUS_COMPLETED,
    RUN_STATUS_UNKNOWN,
    RunDiscoveryMixin,
)


class MyRunDiscoverer(RunDiscoveryMixin, AbstractFileParser):
    """○○ドメインのRunを自動発見する。"""

    priority = 75
    run_type = "my_domain"  # Runタイプ識別子

    def apply(self, graph):
        runs = self.discover_runs(graph)
        for run_info in runs:
            self.register_run(graph, run_info)
        return graph

    def discover_runs(self, graph):
        """ドメイン固有のRun発見ロジック。"""
        runs = []
        # 例: 同一ディレクトリの入出力ファイルをグループ化
        # runs.append({
        #     "name": "run_001",
        #     "type": self.run_type,
        #     "inputs": [input_node_id],
        #     "outputs": [output_node_id],
        #     "media": [],  # 実行スクリプト等
        #     "properties": {"key": "value"},
        #     "status": RUN_STATUS_COMPLETED,
        # })
        return runs
```

### Run情報の辞書構造

| キー | 型 | 説明 |
|------|-----|------|
| `name` | `str` | Run識別名 |
| `type` | `str` | ドメインタイプ (`"cae_job"`, `"ml_training"`, `"experiment"`) |
| `inputs` | `list[int]` | 入力ノードIDのリスト |
| `outputs` | `list[int]` | 出力ノードIDのリスト |
| `media` | `list[int]` | メディア（スクリプト等）ノードIDのリスト |
| `properties` | `dict` | Run付加プロパティ |
| `status` | `str` | ステータス定数（`RUN_STATUS_COMPLETED` / `FAILED` / `RUNNING` / `UNKNOWN`） |

### ユーティリティ関数

`services/parse/run_discovery.py` が以下のユーティリティを提供:

- **`find_input_output_pairs(graph, input_extensions, output_extensions)`**: 同一ディレクトリ内の入出力ファイルペアを自動発見
- **`detect_run_status(output_nodes)`**: 出力ノードプロパティからステータスを推定
- **`extract_run_properties(nodes, property_keys)`**: ノード群から共通プロパティを抽出

---

## テスト作成ガイド

### テストファイルの配置

```
tests/test_myformat_plugin.py
```

### テストの基本構造

```python
"""myformatプラグインのテスト"""
import pytest

from services.parse.base import _parser_registry


class TestMyFormatParser:
    """MyFormatParserのテスト"""

    def _make_graph(self, nodes_data):
        """テスト用のProjectGraphを作成する。"""
        from unittest.mock import MagicMock

        graph = MagicMock()
        nodes = []
        for data in nodes_data:
            node = MagicMock()
            node.id = data["id"]
            node.properties = dict(data.get("properties", {}))
            nodes.append(node)
        graph.model.nodes = nodes
        return graph

    def test_parser_registration(self):
        """パーサーがレジストリに登録されていることを確認。"""
        import services.plugins.myformat  # noqa: F401

        parser_names = [p.__name__ for p in _parser_registry]
        assert "MyFormatParser" in parser_names

    def test_enriches_properties(self, tmp_path):
        """ファイルプロパティが正しく付与されることを確認。"""
        # テスト用ファイル作成
        test_file = tmp_path / "data.myext"
        test_file.write_text("test content")

        graph = self._make_graph([
            {"id": 1, "properties": {"path": "data.myext"}},
        ])
        graph.project_root = tmp_path

        from services.parse.connectors.myformat.data_parser import MyFormatParser
        parser = MyFormatParser()
        parser.apply(graph)

        assert graph.model.nodes[0].properties.get("my_property") == "value"


class TestMyRunDiscoverer:
    """MyRunDiscovererのテスト"""

    def test_discovers_run(self):
        """Run発見ロジックが正しく動作することを確認。"""
        # ... テスト実装
        pass
```

### テスト実行

```bash
# プロジェクト全体
pip install -e ".[dev]"
pytest tests/ -q

# 特定テスト
pytest tests/test_myformat_plugin.py -v
```

---

## 実装例: 物理実験プラグイン

`services/plugins/experiment/` が完全な実装例として参照可能:

| ファイル | 内容 |
|---------|------|
| `services/plugins/experiment/__init__.py` | register() エントリ |
| `services/parse/connectors/experiment/data_parser.py` | ExperimentDataParser + ExperimentRunDiscoverer |
| `tests/test_experiment_plugin.py` | 11テストケース |

### ExperimentDataParser のポイント

- CSV/TSVのヘッダ抽出・行数カウント（軽量: 先頭1000行まで）
- `.meta.yaml` からメタデータ読み込み（experiment_name, operator, conditions等）

### ExperimentRunDiscoverer のポイント

- `RunDiscoveryMixin` を多重継承
- メタデータ付きCSVが存在するディレクトリのみRun化（保守的アプローチ）
- `run_type = "experiment"` でドメイン識別

---

## チェックリスト

新規プラグイン作成時に確認:

- [ ] `services/plugins/{name}/__init__.py` に `register()` 関数を定義
- [ ] パーサーが `AbstractFileParser` を継承し、`priority` と `apply()` を実装
- [ ] Run発見が必要なら `RunDiscoveryMixin` を組み合わせ
- [ ] `pyproject.toml` の `entry-points` と `optional-dependencies` を更新
- [ ] `pyproject.toml` の `all` グループにプラグインを追加
- [ ] テストファイルを `tests/` に作成
- [ ] `ruff check .` と `ruff format --check .` でlint通過
- [ ] `pytest tests/ -q` で全テスト通過
