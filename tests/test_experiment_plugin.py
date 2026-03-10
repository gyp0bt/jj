"""物理実験プラグイン テスト (T8-2)

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

import csv
from pathlib import Path
from unittest.mock import MagicMock

import yaml

# ====================================================================
# ヘルパー
# ====================================================================


def _make_node(node_id: int, path: str, **extra_props: object) -> MagicMock:
    """テスト用ノードを作成"""
    node = MagicMock()
    node.id = node_id
    props = {"path": path}
    props.update(extra_props)
    node.properties = props
    return node


def _make_graph(nodes: list, project_root: Path | None = None) -> MagicMock:
    """テスト用ProjectGraphを作成"""
    graph = MagicMock()
    model = MagicMock()
    model.nodes = nodes
    model.add_node = MagicMock(return_value=100)
    model.add_relation = MagicMock()
    graph.model = model
    if project_root:
        graph.project_root = project_root
    return graph


def _create_csv(path: Path, headers: list[str], rows: list[list] | None = None) -> None:
    """テスト用CSVファイルを作成"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in rows or []:
            writer.writerow(row)


def _create_tsv(path: Path, headers: list[str], rows: list[list] | None = None) -> None:
    """テスト用TSVファイルを作成"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(headers)
        for row in rows or []:
            writer.writerow(row)


def _create_meta_yaml(path: Path, meta: dict) -> None:
    """テスト用メタデータファイルを作成"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(meta, f, allow_unicode=True)


# ====================================================================
# ExperimentDataParser テスト
# ====================================================================


class TestExperimentDataParser:
    """ExperimentDataParserのテスト"""

    def test_csv_header_extraction(self, tmp_path):
        """CSVのヘッダが正しく抽出されること"""
        from services.parse.connectors.experiment.data_parser import ExperimentDataParser

        csv_path = tmp_path / "exp" / "data.csv"
        _create_csv(csv_path, ["time", "force", "displacement"], [[0, 10.5, 0.1]])

        node = _make_node(1, str(csv_path.relative_to(tmp_path)))
        graph = _make_graph([node], project_root=tmp_path)

        parser = ExperimentDataParser()
        parser.apply(graph)

        assert node.properties["columns"] == ["time", "force", "displacement"]
        assert node.properties["column_count"] == 3
        assert node.properties["data_format"] == "csv"

    def test_tsv_header_extraction(self, tmp_path):
        """TSVのヘッダが正しく抽出されること"""
        from services.parse.connectors.experiment.data_parser import ExperimentDataParser

        tsv_path = tmp_path / "exp" / "data.tsv"
        _create_tsv(tsv_path, ["voltage", "current"])

        node = _make_node(1, str(tsv_path.relative_to(tmp_path)))
        graph = _make_graph([node], project_root=tmp_path)

        parser = ExperimentDataParser()
        parser.apply(graph)

        assert node.properties["columns"] == ["voltage", "current"]
        assert node.properties["data_format"] == "tsv"

    def test_row_count(self, tmp_path):
        """行数が正しくカウントされること"""
        from services.parse.connectors.experiment.data_parser import ExperimentDataParser

        csv_path = tmp_path / "data.csv"
        rows = [[i, i * 2] for i in range(50)]
        _create_csv(csv_path, ["x", "y"], rows)

        node = _make_node(1, str(csv_path.relative_to(tmp_path)))
        graph = _make_graph([node], project_root=tmp_path)

        parser = ExperimentDataParser()
        parser.apply(graph)

        assert node.properties["row_count"] == 50
        assert node.properties["row_count_truncated"] is False

    def test_metadata_loading(self, tmp_path):
        """メタデータファイルが正しく読み込まれること"""
        from services.parse.connectors.experiment.data_parser import ExperimentDataParser

        csv_path = tmp_path / "exp" / "tensile.csv"
        _create_csv(csv_path, ["time", "stress", "strain"])

        meta_path = tmp_path / "exp" / "tensile.meta.yaml"
        _create_meta_yaml(
            meta_path,
            {
                "experiment_name": "引張試験A",
                "operator": "田中",
                "date": "2026-03-10",
                "conditions": {"temperature": 25, "speed": "1mm/min"},
            },
        )

        node = _make_node(1, str(csv_path.relative_to(tmp_path)))
        graph = _make_graph([node], project_root=tmp_path)

        parser = ExperimentDataParser()
        parser.apply(graph)

        assert node.properties["experiment_name"] == "引張試験A"
        assert node.properties["operator"] == "田中"
        assert node.properties["condition_temperature"] == 25
        assert node.properties["condition_speed"] == "1mm/min"

    def test_nonexistent_file_skip(self, tmp_path):
        """存在しないファイルはスキップすること"""
        from services.parse.connectors.experiment.data_parser import ExperimentDataParser

        node = _make_node(1, "missing/data.csv")
        graph = _make_graph([node], project_root=tmp_path)

        parser = ExperimentDataParser()
        result = parser.apply(graph)
        # エラーが出ずに正常終了
        assert result is graph

    def test_non_csv_files_ignored(self, tmp_path):
        """CSV/TSV以外のファイルは無視されること"""
        from services.parse.connectors.experiment.data_parser import ExperimentDataParser

        node = _make_node(1, "exp/model.py")
        graph = _make_graph([node], project_root=tmp_path)

        parser = ExperimentDataParser()
        parser.apply(graph)
        assert "columns" not in node.properties


# ====================================================================
# ExperimentRunDiscoverer テスト
# ====================================================================


class TestExperimentRunDiscoverer:
    """ExperimentRunDiscovererのテスト"""

    def test_discovers_run_with_metadata(self):
        """メタデータ付きCSVからRunを発見すること"""
        from services.parse.connectors.experiment.data_parser import ExperimentRunDiscoverer

        nodes = [
            _make_node(1, "exp1/data.csv", experiment_name="引張試験"),
            _make_node(2, "exp1/result.csv"),
        ]
        graph = _make_graph(nodes)

        discoverer = ExperimentRunDiscoverer()
        runs = discoverer.discover_runs(graph)

        assert len(runs) == 1
        assert runs[0]["name"] == "experiment_引張試験"
        assert runs[0]["type"] == "experiment"
        assert 1 in runs[0]["inputs"]
        assert 2 in runs[0]["inputs"]

    def test_no_run_without_metadata(self):
        """メタデータなしのCSVではRunを作成しないこと"""
        from services.parse.connectors.experiment.data_parser import ExperimentRunDiscoverer

        nodes = [_make_node(1, "exp1/data.csv")]
        graph = _make_graph(nodes)

        discoverer = ExperimentRunDiscoverer()
        runs = discoverer.discover_runs(graph)

        assert len(runs) == 0

    def test_multiple_directories(self):
        """複数ディレクトリからそれぞれRunを発見すること"""
        from services.parse.connectors.experiment.data_parser import ExperimentRunDiscoverer

        nodes = [
            _make_node(1, "exp1/data.csv", experiment_name="試験A"),
            _make_node(2, "exp2/data.csv", experiment_name="試験B"),
        ]
        graph = _make_graph(nodes)

        discoverer = ExperimentRunDiscoverer()
        runs = discoverer.discover_runs(graph)

        assert len(runs) == 2
        names = {r["name"] for r in runs}
        assert "experiment_試験A" in names
        assert "experiment_試験B" in names

    def test_apply_registers_runs(self):
        """apply()がRunをグラフに登録すること"""
        from services.parse.connectors.experiment.data_parser import ExperimentRunDiscoverer

        nodes = [
            _make_node(1, "exp1/data.csv", experiment_name="テスト"),
        ]
        graph = _make_graph(nodes)

        discoverer = ExperimentRunDiscoverer()
        discoverer.apply(graph)

        # add_nodeが呼ばれた（Run登録）
        graph.model.add_node.assert_called_once()


# ====================================================================
# プラグイン登録テスト
# ====================================================================


class TestExperimentPluginRegistration:
    """物理実験プラグインの登録テスト"""

    def test_parsers_registered(self):
        """パーサーがレジストリに登録されること"""
        from services.parse.base import get_parser_registry
        from services.parse.connectors.experiment.data_parser import (
            ExperimentDataParser,
            ExperimentRunDiscoverer,
        )

        registry = get_parser_registry()
        parser_types = [type(p) if not isinstance(p, type) else p for p in registry]

        assert ExperimentDataParser in parser_types
        assert ExperimentRunDiscoverer in parser_types
