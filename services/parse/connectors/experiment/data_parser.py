"""物理実験データパーサー (T8-2)

CSV/TSV形式の実験データを検出し、メタデータを抽出する。
同一ディレクトリ内の .meta.yaml からの属性読み込みにも対応。

## 対応ファイル形式

- `.csv` — カンマ区切り
- `.tsv` — タブ区切り

## メタデータファイル

`<filename>.meta.yaml` が存在する場合、以下のフィールドを読み込む:
- experiment_name: 実験名
- operator: 実験者
- date: 実施日
- conditions: 実験条件（dict）
- description: 説明

[READMEへ戻る](../../../../../README.md)
"""

from __future__ import annotations

import csv
import io
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from services.parse.base import AbstractFileParser
from services.parse.run_discovery import (
    RUN_STATUS_COMPLETED,
    RunDiscoveryMixin,
)

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph

logger = logging.getLogger(__name__)

# 実験データの拡張子
EXPERIMENT_DATA_EXTENSIONS = (".csv", ".tsv")

# メタデータファイルの拡張子
META_EXTENSION = ".meta.yaml"

# CSVヘッダ行の最大サイズ
MAX_HEADER_READ_BYTES = 8192


class ExperimentDataParser(AbstractFileParser):
    """CSV/TSV実験データのパーサー。

    ファイルノードのプロパティにカラム名・行数・メタデータを付与する。
    """

    priority = 56

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        for node in list(graph.model.nodes):
            path_str = node.properties.get("path", "")
            if not path_str:
                continue
            path = Path(path_str)
            suffix = path.suffix.lower()
            if suffix not in EXPERIMENT_DATA_EXTENSIONS:
                continue

            self._enrich_data_node(graph, node, path, suffix)

        return graph

    def _enrich_data_node(
        self,
        graph: ProjectGraph,
        node: Any,
        path: Path,
        suffix: str,
    ) -> None:
        """データノードにカラム名・行数・メタデータを付与する。"""
        full_path = graph.project_root / path if hasattr(graph, "project_root") else path
        if not full_path.exists():
            return

        # CSVヘッダ読み込み
        columns = self._read_csv_header(full_path, suffix)
        if columns:
            node.properties["columns"] = columns
            node.properties["column_count"] = len(columns)
            node.properties["data_format"] = "csv" if suffix == ".csv" else "tsv"

        # 行数カウント（軽量: 先頭1000行まで）
        row_count = self._count_rows(full_path, max_rows=1000)
        if row_count is not None:
            node.properties["row_count"] = row_count
            node.properties["row_count_truncated"] = row_count >= 1000

        # メタデータ読み込み
        meta = self._load_metadata(full_path)
        if meta:
            for key in ("experiment_name", "operator", "date", "description"):
                if key in meta:
                    node.properties[key] = meta[key]
            if "conditions" in meta and isinstance(meta["conditions"], dict):
                for k, v in meta["conditions"].items():
                    node.properties[f"condition_{k}"] = v

    def _read_csv_header(self, path: Path, suffix: str) -> list[str]:
        """CSVファイルのヘッダ行を読み込む。"""
        delimiter = "\t" if suffix == ".tsv" else ","
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                header_text = f.read(MAX_HEADER_READ_BYTES)
            reader = csv.reader(io.StringIO(header_text), delimiter=delimiter)
            first_row = next(reader, None)
            if first_row:
                return [col.strip() for col in first_row if col.strip()]
        except Exception:
            logger.debug("CSVヘッダ読み込み失敗: %s", path, exc_info=True)
        return []

    def _count_rows(self, path: Path, max_rows: int = 1000) -> int | None:
        """ファイルの行数をカウントする（ヘッダ除く）。"""
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                count = 0
                next(f, None)  # ヘッダスキップ
                for _ in f:
                    count += 1
                    if count >= max_rows:
                        break
                return count
        except Exception:
            return None

    def _load_metadata(self, data_path: Path) -> dict[str, Any]:
        """対応するメタデータファイルを読み込む。"""
        meta_path = data_path.with_suffix(data_path.suffix + META_EXTENSION)
        if not meta_path.exists():
            # fallback: ファイル名.meta.yaml
            meta_path = data_path.parent / (data_path.stem + META_EXTENSION)
            if not meta_path.exists():
                return {}

        try:
            import yaml

            with open(meta_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            logger.debug("メタデータ読み込み失敗: %s", meta_path, exc_info=True)
            return {}


class ExperimentRunDiscoverer(RunDiscoveryMixin, AbstractFileParser):
    """実験ディレクトリからRunを自動発見・登録する。

    同一ディレクトリ内のCSV/TSVファイルをグループ化し、
    入力データと出力データのペアをRunとして登録する。
    """

    priority = 76
    run_type = "experiment"

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        runs = self.discover_runs(graph)
        for run_info in runs:
            self.register_run(graph, run_info)
        return graph

    def discover_runs(self, graph: ProjectGraph) -> list[dict[str, Any]]:
        """実験データディレクトリからRunを発見する。

        メタデータファイルが存在するCSV/TSVファイルがある
        ディレクトリをRun候補として検出する。
        """
        from collections import defaultdict

        dir_nodes: dict[str, list[Any]] = defaultdict(list)

        for node in graph.model.nodes:
            path_str = node.properties.get("path", "")
            if not path_str:
                continue
            path = Path(path_str)
            if path.suffix.lower() in EXPERIMENT_DATA_EXTENSIONS:
                dir_key = str(path.parent)
                dir_nodes[dir_key].append(node)

        runs = []
        for dir_key, nodes in dir_nodes.items():
            # メタデータ付きノードがある場合のみRun化
            meta_nodes = [n for n in nodes if n.properties.get("experiment_name")]
            if not meta_nodes:
                continue

            run_name = meta_nodes[0].properties.get("experiment_name", dir_key)
            node_ids = [n.id for n in nodes]

            runs.append(
                {
                    "name": f"experiment_{run_name}",
                    "type": self.run_type,
                    "inputs": node_ids,
                    "outputs": [],
                    "media": [],
                    "properties": {
                        "directory": dir_key,
                        "file_count": len(nodes),
                        "operator": meta_nodes[0].properties.get("operator", ""),
                    },
                    "status": RUN_STATUS_COMPLETED,
                }
            )

        return runs
