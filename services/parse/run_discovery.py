"""Run Discovery ユーティリティ (T8-1)

プラグインパーサーがRunを発見・登録する際の共通パターンを提供する。
AbstractFileParserのサブクラスに RunDiscoveryMixin を組み合わせて使用する。

## 使用例

```python
class MyExperimentParser(RunDiscoveryMixin, AbstractFileParser):
    priority = 75
    run_type = "experiment"

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        runs = self.discover_runs(graph)
        for run_info in runs:
            self.register_run(graph, run_info)
        return graph

    def discover_runs(self, graph: ProjectGraph) -> list[dict]:
        # ドメイン固有のRun発見ロジック
        ...
```

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph

logger = logging.getLogger(__name__)

# Run ステータス定数
RUN_STATUS_COMPLETED = "completed"
RUN_STATUS_FAILED = "failed"
RUN_STATUS_RUNNING = "running"
RUN_STATUS_UNKNOWN = "unknown"


class RunDiscoveryMixin:
    """Run発見・登録のためのMixin。

    AbstractFileParserサブクラスに組み合わせて使用する。
    discover_runs() をオーバーライドしてドメイン固有の発見ロジックを実装する。
    """

    run_type: str = ""
    run_status_key: str = "run_status"

    def discover_runs(self, graph: ProjectGraph) -> list[dict[str, Any]]:
        """プロジェクトグラフからRunを発見する。

        サブクラスでオーバーライドする。

        Args:
            graph: ProjectGraph

        Returns:
            Run情報のリスト。各要素は以下のキーを持つ:
            - name (str): Run名
            - type (str): Runタイプ（self.run_type がデフォルト）
            - inputs (list[int]): 入力ノードID
            - outputs (list[int]): 出力ノードID
            - media (list[int]): メディアノードID（スクリプト等）
            - properties (dict): Run付加プロパティ
            - status (str): Runステータス
        """
        return []

    def register_run(self, graph: ProjectGraph, run_info: dict[str, Any]) -> int | None:
        """RunをProjectGraphに登録する。

        Args:
            graph: ProjectGraph
            run_info: discover_runs()の戻り値の1要素

        Returns:
            作成されたRunノードのID。登録失敗時はNone。
        """
        from jj_types import NodeCategory

        name = run_info.get("name", "")
        run_type = run_info.get("type", self.run_type)
        properties = dict(run_info.get("properties", {}))
        properties["run_type"] = run_type
        properties["run_status"] = run_info.get("status", RUN_STATUS_UNKNOWN)

        # Runノード作成
        run_node_id = graph.model.add_node(
            node_type="run",
            name=name,
            fmt="run",
            properties=properties,
            category=NodeCategory.RUN,
        )

        if run_node_id is None:
            logger.warning("Runノード作成に失敗: %s", name)
            return None

        # 入力リレーション
        for input_id in run_info.get("inputs", []):
            graph.model.add_relation(label="RUN_INPUT", node1_id=run_node_id, node2_id=input_id)

        # 出力リレーション
        for output_id in run_info.get("outputs", []):
            graph.model.add_relation(label="RUN_OUTPUT", node1_id=run_node_id, node2_id=output_id)

        # メディアリレーション
        for media_id in run_info.get("media", []):
            graph.model.add_relation(label="RUN_MEDIA", node1_id=run_node_id, node2_id=media_id)

        logger.debug("Run登録: %s (type=%s, id=%d)", name, run_type, run_node_id)
        return run_node_id


def find_input_output_pairs(
    graph: ProjectGraph,
    input_extensions: tuple[str, ...] = (),
    output_extensions: tuple[str, ...] = (),
    same_directory: bool = True,
) -> list[dict[str, Any]]:
    """入出力ファイルペアを自動発見する。

    同一ディレクトリ内で入力拡張子と出力拡張子のファイルをペアにする。

    Args:
        graph: ProjectGraph
        input_extensions: 入力ファイルの拡張子（例: (".csv", ".tsv")）
        output_extensions: 出力ファイルの拡張子（例: (".png", ".pdf")）
        same_directory: Trueの場合、同一ディレクトリ内のファイルのみペアにする

    Returns:
        [{"directory": str, "inputs": [node], "outputs": [node]}]
    """
    from collections import defaultdict

    dir_inputs: dict[str, list[Any]] = defaultdict(list)
    dir_outputs: dict[str, list[Any]] = defaultdict(list)

    for node in graph.model.nodes:
        path_str = node.properties.get("path", "")
        if not path_str:
            continue
        path = Path(path_str)
        suffix = path.suffix.lower()
        dir_key = str(path.parent) if same_directory else ""

        if input_extensions and suffix in input_extensions:
            dir_inputs[dir_key].append(node)
        elif output_extensions and suffix in output_extensions:
            dir_outputs[dir_key].append(node)

    pairs = []
    for dir_key in set(dir_inputs.keys()) | set(dir_outputs.keys()):
        inputs = dir_inputs.get(dir_key, [])
        outputs = dir_outputs.get(dir_key, [])
        if inputs or outputs:
            pairs.append(
                {
                    "directory": dir_key,
                    "inputs": inputs,
                    "outputs": outputs,
                }
            )

    return pairs


def detect_run_status(
    output_nodes: list[Any],
    error_keywords: tuple[str, ...] = ("error", "failed", "exception"),
    success_keywords: tuple[str, ...] = ("completed", "success", "done"),
) -> str:
    """出力ノードのプロパティからRunステータスを推定する。

    Args:
        output_nodes: 出力ノードのリスト
        error_keywords: 失敗を示すキーワード
        success_keywords: 成功を示すキーワード

    Returns:
        ステータス文字列（completed/failed/unknown）
    """
    if not output_nodes:
        return RUN_STATUS_UNKNOWN

    for node in output_nodes:
        props_str = str(node.properties).lower()
        for keyword in error_keywords:
            if keyword in props_str:
                return RUN_STATUS_FAILED

    for node in output_nodes:
        props_str = str(node.properties).lower()
        for keyword in success_keywords:
            if keyword in props_str:
                return RUN_STATUS_COMPLETED

    return RUN_STATUS_UNKNOWN


def extract_run_properties(
    nodes: list[Any],
    property_keys: tuple[str, ...] = (),
) -> dict[str, Any]:
    """ノード群から共通プロパティを抽出する。

    Args:
        nodes: ノードのリスト
        property_keys: 抽出するプロパティキー。空の場合はすべてのキーを収集。

    Returns:
        プロパティの辞書
    """
    result: dict[str, Any] = {}
    for node in nodes:
        for key, value in node.properties.items():
            if property_keys and key not in property_keys:
                continue
            if key not in result:
                result[key] = value
    return result
