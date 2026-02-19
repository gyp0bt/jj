"""Run発見基盤モジュール

AbstractRunDiscovererはAbstractFileParserを継承し、パーサーパイプライン内で
Run Nodeの生成とrun_input/run_output/run_mediaリレーションの構築を行う。

RunCandidateはRun発見の中間表現で、具象DiscovererがProjectGraphから
候補を発見し、基底クラスがNodeとRelationに変換する。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph


@dataclass
class RunCandidate:
    """Run発見の中間表現

    AbstractRunDiscoverer.discover_runs()が返す候補を表現する。
    基底クラスのapply()がこの候補をNodeとRelationに変換する。

    Attributes:
        name: Run名（表示用）
        run_type: Run種別（"cae_job", "ml_training" 等）
        input_node_ids: 入力ノードID群
        output_node_ids: 出力ノードID群
        media_node_ids: 実行媒体ノードID群
        properties: Run固有プロパティ
        discovery: "static"（パーサー発見）or "runtime"（実行時記録）
    """

    name: str
    run_type: str
    input_node_ids: list[int] = field(default_factory=list)
    output_node_ids: list[int] = field(default_factory=list)
    media_node_ids: list[int] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
    discovery: str = "static"


class AbstractRunDiscoverer(AbstractFileParser):
    """Run発見用抽象基底クラス

    AbstractFileParserを継承し、パーサーパイプライン内でRun Nodeを生成する。
    サブクラスはdiscover_runs()を実装してRunCandidateのリストを返す。
    基底クラスのapply()がそれらをNode/Relationに変換してグラフに追加する。

    priority指針: 200番台（ファイル解析パーサーの後に実行）
        200: CAE Run発見
        210: ML Run発見
        220: 最適化Run発見
        230: 層間Run連鎖発見
    """

    priority: int = 200

    @abstractmethod
    def discover_runs(self, graph: ProjectGraph) -> list[RunCandidate]:
        """グラフからRunの候補を発見する

        Args:
            graph: 処理対象のProjectGraph

        Returns:
            RunCandidateのリスト
        """
        ...

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        """AbstractFileParser互換のapplyメソッド

        discover_runs()で候補を取得し、それぞれをNode/Relationに変換して
        グラフに追加する。
        """
        candidates = self.discover_runs(graph)
        for candidate in candidates:
            graph.add_run_node(
                name=candidate.name,
                run_type=candidate.run_type,
                input_node_ids=candidate.input_node_ids,
                output_node_ids=candidate.output_node_ids,
                media_node_ids=candidate.media_node_ids,
                properties=candidate.properties,
                discovery=candidate.discovery,
            )
        return graph
