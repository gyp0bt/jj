"""パフォーマンス最適化のユニットテスト

ProjectGraphインデックス、IgnoreConfigプリコンパイル、CsvArrayParserサマリーモードの
パフォーマンス最適化をテストする。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from config import GraphConfig, IgnoreConfig
from jj_types import Node, NodeCategory, Relation
from services.graph.project_graph import ProjectGraph
from services.parse.parsers.csv_array_parser import (
    _count_csv_rows,
    _read_csv_arrays,
    _read_csv_summary,
)

ASSET_DIR = Path(__file__).resolve().parent.parent / "shared" / "tests" / "test_asset1"


@pytest.fixture
def config() -> GraphConfig:
    return GraphConfig.from_dict(
        {
            "vocab": {},
            "file-relations": {"input-extensions": [".inp"]},
        }
    )


# ====================================================================
# ProjectGraph インデックステスト
# ====================================================================


class TestProjectGraphIndex:
    """ProjectGraphのインデックス最適化テスト"""

    def test_get_nodes_by_type_uses_index(self, config: GraphConfig):
        """get_nodes_by_typeがインデックスを使用して正しい結果を返す"""
        pg = ProjectGraph(nodes=[], relations=[], project_root=ASSET_DIR, config=config)
        n1 = Node(id=1, type="go", name="a", format="inp", properties={})
        n2 = Node(id=2, type="mesh", name="b", format="inp", properties={})
        n3 = Node(id=3, type="go", name="c", format="inp", properties={})
        pg.add_node(n1)
        pg.add_node(n2)
        pg.add_node(n3)

        go_nodes = pg.get_nodes_by_type("go")
        assert len(go_nodes) == 2
        assert n1 in go_nodes
        assert n3 in go_nodes

        mesh_nodes = pg.get_nodes_by_type("mesh")
        assert len(mesh_nodes) == 1
        assert n2 in mesh_nodes

    def test_get_nodes_by_type_empty(self, config: GraphConfig):
        """存在しないタイプの検索で空リストを返す"""
        pg = ProjectGraph(nodes=[], relations=[], project_root=ASSET_DIR, config=config)
        assert pg.get_nodes_by_type("nonexistent") == []

    def test_get_relations_by_label_uses_index(self, config: GraphConfig):
        """get_relations_by_labelがインデックスを使用して正しい結果を返す"""
        pg = ProjectGraph(nodes=[], relations=[], project_root=ASSET_DIR, config=config)
        r1 = Relation(id=1, label="has_output", node1_id=1, node2_id=2)
        r2 = Relation(id=2, label="result_of", node1_id=3, node2_id=4)
        r3 = Relation(id=3, label="has_output", node1_id=5, node2_id=6)
        pg.add_relation(r1)
        pg.add_relation(r2)
        pg.add_relation(r3)

        has_output = pg.get_relations_by_label("has_output")
        assert len(has_output) == 2
        assert r1 in has_output
        assert r3 in has_output

    def test_get_relations_for_node_uses_index(self, config: GraphConfig):
        """get_relations_for_nodeがインデックスを使用して正しい結果を返す"""
        pg = ProjectGraph(nodes=[], relations=[], project_root=ASSET_DIR, config=config)
        r1 = Relation(id=1, label="has_output", node1_id=1, node2_id=2)
        r2 = Relation(id=2, label="result_of", node1_id=3, node2_id=1)
        r3 = Relation(id=3, label="includes", node1_id=4, node2_id=5)
        pg.add_relation(r1)
        pg.add_relation(r2)
        pg.add_relation(r3)

        node1_rels = pg.get_relations_for_node(1)
        assert len(node1_rels) == 2
        assert r1 in node1_rels
        assert r2 in node1_rels

    def test_get_nodes_by_category_uses_index(self, config: GraphConfig):
        """get_nodes_by_categoryがインデックスを使用して正しい結果を返す"""
        pg = ProjectGraph(nodes=[], relations=[], project_root=ASSET_DIR, config=config)
        n1 = Node(id=1, type="go", name="a", format="inp", properties={}, category=NodeCategory.FILE)
        n2 = Node(id=2, type="dataset", name="d1", format="", properties={}, category=NodeCategory.DATA)
        n3 = Node(id=3, type="go", name="c", format="inp", properties={}, category=NodeCategory.FILE)
        pg.add_node(n1)
        pg.add_node(n2)
        pg.add_node(n3)

        file_nodes = pg.get_nodes_by_category(NodeCategory.FILE)
        assert len(file_nodes) == 2

        data_nodes = pg.get_nodes_by_category(NodeCategory.DATA)
        assert len(data_nodes) == 1

    def test_remove_nodes_rebuilds_all_indexes(self, config: GraphConfig):
        """remove_nodesが全インデックスを再構築する"""
        pg = ProjectGraph(nodes=[], relations=[], project_root=ASSET_DIR, config=config)
        n1 = Node(id=1, type="go", name="a", format="inp", properties={"path": "a.inp"})
        n2 = Node(id=2, type="go", name="b", format="inp", properties={"path": "b.inp"})
        r1 = Relation(id=1, label="has_output", node1_id=1, node2_id=2)
        pg.add_node(n1)
        pg.add_node(n2)
        pg.add_relation(r1)

        pg.remove_nodes({1})

        # ノードインデックス
        assert pg.get_node_by_id(1) is None
        assert pg.get_node_by_path("a.inp") is None
        assert pg.get_nodes_by_type("go") == [n2]

        # リレーションインデックス
        assert pg.get_relations_by_label("has_output") == []
        assert pg.get_relations_for_node(1) == []

    def test_add_relations_batch_updates_index(self, config: GraphConfig):
        """add_relationsが一括追加でもインデックスを更新する"""
        pg = ProjectGraph(nodes=[], relations=[], project_root=ASSET_DIR, config=config)
        rels = [
            Relation(id=1, label="has_output", node1_id=1, node2_id=2),
            Relation(id=2, label="has_output", node1_id=3, node2_id=4),
        ]
        pg.add_relations(rels)

        assert len(pg.get_relations_by_label("has_output")) == 2
        assert len(pg.get_relations_for_node(1)) == 1
        assert len(pg.get_relations_for_node(2)) == 1

    def test_post_init_builds_all_indexes(self, config: GraphConfig):
        """__post_init__で既存データのインデックスが構築される"""
        nodes = [
            Node(id=1, type="go", name="a", format="inp", properties={"path": "a.inp"}),
            Node(id=2, type="mesh", name="b", format="inp", properties={"path": "b.inp"}),
        ]
        rels = [
            Relation(id=1, label="has_output", node1_id=1, node2_id=2),
        ]
        pg = ProjectGraph(nodes=nodes, relations=rels, project_root=ASSET_DIR, config=config)

        assert len(pg.get_nodes_by_type("go")) == 1
        assert len(pg.get_nodes_by_type("mesh")) == 1
        assert len(pg.get_relations_by_label("has_output")) == 1
        assert len(pg.get_relations_for_node(1)) == 1


# ====================================================================
# IgnoreConfig プリコンパイルテスト
# ====================================================================


class TestIgnoreConfigOptimized:
    """IgnoreConfigの正規表現プリコンパイル最適化テスト"""

    def test_from_list_compiles_patterns(self):
        """from_listでパターンがプリコンパイルされる"""
        ic = IgnoreConfig.from_list(["*.csv", "results/*"])
        assert len(ic._compiled_patterns) == 2

    def test_should_ignore_full_path(self):
        """フルパスのマッチング"""
        ic = IgnoreConfig.from_list(["*.csv"])
        assert ic.should_ignore("data.csv") is True
        assert ic.should_ignore("data.inp") is False

    def test_should_ignore_path_component(self):
        """パスコンポーネントのマッチング"""
        ic = IgnoreConfig.from_list(["results"])
        assert ic.should_ignore("sub/results/data.csv") is True

    def test_should_ignore_glob_pattern(self):
        """グロブパターンのマッチング"""
        ic = IgnoreConfig.from_list(["go_idx*_*.csv"])
        assert ic.should_ignore("go_idx1_RF.csv") is True
        assert ic.should_ignore("mesh_idx1.csv") is False

    def test_empty_patterns(self):
        """空パターンの場合、何もignoreされない"""
        ic = IgnoreConfig.from_list([])
        assert ic.should_ignore("anything.csv") is False

    def test_none_patterns(self):
        """Noneの場合、何もignoreされない"""
        ic = IgnoreConfig.from_list(None)
        assert ic.should_ignore("anything.csv") is False

    def test_backward_compatible(self):
        """プリコンパイル結果がfnmatchと同じ結果を返す"""
        import fnmatch

        patterns = ["*.csv", "*.odb", "results*", "go_idx*_w*"]
        ic = IgnoreConfig.from_list(patterns)
        test_paths = [
            "data.csv",
            "data.inp",
            "results_summary.txt",
            "go_idx1_w5.inp",
            "mesh_idx1.inp",
        ]
        for path in test_paths:
            expected = any(fnmatch.fnmatch(path, p) for p in patterns)
            assert ic.should_ignore(path) == expected, f"Mismatch for path: {path}"


# ====================================================================
# CsvArrayParser サマリーモードテスト
# ====================================================================


class TestCsvSummaryMode:
    """CsvArrayParserのサマリーモード最適化テスト"""

    def _create_csv(self, rows: int, cols: int = 3, has_header: bool = True) -> Path:
        """テスト用CSVファイルを生成"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            if has_header:
                tmp.write(",".join(f"col{i}" for i in range(cols)) + "\n")
            for r in range(rows):
                tmp.write(",".join(str(float(r * cols + c)) for c in range(cols)) + "\n")
            return Path(tmp.name)

    def test_count_csv_rows(self):
        """CSV行数カウント"""
        csv_path = self._create_csv(100, has_header=True)
        assert _count_csv_rows(csv_path) == 101  # header + 100 data rows

    def test_read_csv_summary_stats(self):
        """サマリーモードで正しい統計量を返す"""
        csv_path = self._create_csv(100, cols=2, has_header=True)
        summary = _read_csv_summary(csv_path)

        assert "col0" in summary
        assert "col1" in summary
        assert summary["col0"]["count"] == 100
        assert summary["col0"]["min"] == 0.0
        assert summary["col0"]["max"] == 198.0  # (99*2+0)
        assert summary["col1"]["min"] == 1.0
        assert summary["col1"]["max"] == 199.0  # (99*2+1)

    def test_read_csv_arrays_normal_mode(self):
        """max_rows=0で従来通り全行を配列として返す"""
        csv_path = self._create_csv(10, cols=2, has_header=True)
        result = _read_csv_arrays(csv_path, max_rows=0)

        assert "col0" in result
        assert isinstance(result["col0"], list)
        assert len(result["col0"]) == 10

    def test_read_csv_arrays_summary_when_exceeds_max_rows(self):
        """max_rows超過時にサマリーモードで返す"""
        csv_path = self._create_csv(100, cols=2, has_header=True)
        result = _read_csv_arrays(csv_path, max_rows=50)

        # サマリーモード: dict型が返る
        assert "col0" in result
        assert isinstance(result["col0"], dict)
        assert "min" in result["col0"]
        assert "max" in result["col0"]
        assert "mean" in result["col0"]
        assert "count" in result["col0"]
        assert "last" in result["col0"]

    def test_read_csv_arrays_normal_when_within_max_rows(self):
        """max_rows以内の場合は従来通り配列で返す"""
        csv_path = self._create_csv(10, cols=2, has_header=True)
        result = _read_csv_arrays(csv_path, max_rows=50)

        assert "col0" in result
        assert isinstance(result["col0"], list)
        assert len(result["col0"]) == 10

    def test_summary_mode_no_header(self):
        """ヘッダーなしCSVのサマリーモード"""
        csv_path = self._create_csv(100, cols=2, has_header=False)
        result = _read_csv_arrays(csv_path, max_rows=50)

        assert "col_0" in result
        assert isinstance(result["col_0"], dict)
        assert result["col_0"]["count"] == 100

    def test_summary_empty_csv(self):
        """空CSVのサマリー"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            path = Path(tmp.name)
        result = _read_csv_summary(path)
        assert result == {}
