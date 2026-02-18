"""MLデータセットパーサー: データセットファイル検出・メタデータ抽出

データセットファイル（.csv, .parquet, .h5, .hdf5, .npy, .npz）を検出し、
ノードタイプを「dataset」に昇格させる。CSVファイルについてはヘッダー行から
カラム情報を抽出する。

コア依存のみで動作し、pandas等のoptional依存は使用しない。

[READMEへ戻る](../../../../../README.md)
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from jj_types import Node
from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph

logger = logging.getLogger(__name__)

# データセット拡張子
DATASET_EXTENSIONS = {"csv", "parquet", "h5", "hdf5", "npy", "npz"}

# データ分割名のヒューリスティクス
SPLIT_KEYWORDS = {"train", "val", "validation", "test", "dev", "eval"}


class MLDatasetParser(AbstractFileParser):
    """データセットファイル検出・メタデータ抽出パーサー

    対象拡張子のファイルノードをtype='dataset'に昇格させ、
    ファイル名からsplit情報を推定する。CSVファイルはヘッダー行を読み取り
    カラム情報を付与する。
    """

    priority = 55

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        for node in graph.nodes:
            if node.format not in DATASET_EXTENSIONS:
                continue

            # データセットノードに昇格
            node.type = "dataset"
            node.properties["ml_dataset"] = True

            # split推定（ファイル名ベース）
            name_lower = Path(node.name).stem.lower()
            for keyword in SPLIT_KEYWORDS:
                if keyword in name_lower:
                    node.properties["split"] = keyword
                    break

            # CSVファイルの場合、ヘッダー行を解析
            if node.format == "csv":
                self._enrich_csv_metadata(node, graph)

        return graph

    def _enrich_csv_metadata(self, node: Node, graph: ProjectGraph) -> None:
        """CSVファイルのヘッダー行を読み取りメタデータを付与"""
        path_str = node.properties.get("path", "")
        if not path_str:
            return

        file_path = graph.project_root / path_str
        if not file_path.exists():
            return

        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header:
                    node.properties["columns"] = header
                    node.properties["n_columns"] = len(header)
                # 行数カウント（ヘッダー除く）
                row_count = sum(1 for _ in reader)
                node.properties["n_rows"] = row_count
        except Exception:
            logger.debug("CSV解析失敗: %s", path_str)
