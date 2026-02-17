"""サンプルソルバー用パーサー

AbstractFileParserを継承してカスタムパーサーを実装する例。
__init_subclass__により、このモジュールをインポートするだけで
パーサーレジストリに自動登録される。

実装のポイント:
- priority: 実行順序を制御（0=最優先, 100=最後）
- requires_full: True にすると --full オプション時のみ実行
- apply(): ProjectGraphを受け取り、ノード/リレーション追加して返す
"""

from __future__ import annotations

import logging
from typing import Any

from services.sdk import AbstractFileParser, ProjectGraph

logger = logging.getLogger(__name__)


class ExampleSolverParser(AbstractFileParser):
    """サンプルソルバー入力ファイルパーサー

    .example拡張子のファイルからメタデータを抽出し、
    グラフノードのプロパティに追加する。
    """

    priority = 60  # Abaqus INP解析と同じ優先度
    requires_full = False  # 通常モードで実行

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        """グラフを解析してソルバー固有情報を追加

        Args:
            graph: プロジェクトグラフ

        Returns:
            拡張されたProjectGraph
        """
        for node in graph.graph_model.nodes:
            # .exampleファイルを対象にする
            if not node.name.endswith(".example"):
                continue

            # ファイルの実在確認
            file_path = graph.resolve_node_path(node)
            if file_path is None or not file_path.exists():
                continue

            # ファイル内容からメタデータ抽出
            try:
                metadata = self._parse_example_file(file_path)
                node.properties.update(metadata)
                logger.debug(f"Parsed example file: {node.name}")
            except Exception as e:
                logger.warning(f"Failed to parse {node.name}: {e}")

        return graph

    def _parse_example_file(self, file_path: Any) -> dict[str, Any]:
        """サンプルファイルのパースロジック

        実際のプラグインではここにソルバー固有の
        パース処理を実装する。
        """
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        lines = content.strip().splitlines()

        metadata: dict[str, Any] = {
            "example_line_count": len(lines),
            "example_parsed": True,
        }

        # キーバリュー形式（KEY=VALUE）を抽出
        for line in lines:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, _, value = line.partition("=")
                key = key.strip().lower()
                value = value.strip()
                metadata[f"example_{key}"] = value

        return metadata
