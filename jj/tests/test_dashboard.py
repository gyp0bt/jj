"""DashboardDataProvider テスト

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

import pytest

from jj_types import GraphModel, Node, Relation
from services.dashboard.data_provider import DashboardDataProvider


# ====================================================================
# テストフィクスチャ
# ====================================================================


def _make_test_graph() -> GraphModel:
    """テスト用GraphModelを構築"""
    nodes = [
        Node(
            id=1,
            type="go",
            name="go_idx1_v1",
            format="inp",
            properties={
                "path": "go_idx1_v1.inp",
                "index": "1",
                "version": "1",
                "active": True,
                "analysis_status": "completed",
                "cpu_time": 3600.0,
                "RF3": 5.0,
                "temperature": 300,
                "materials": ["Steel", "Aluminum"],
                "sta_warnings": ["Element distortion in elset PART-A"],
            },
        ),
        Node(
            id=2,
            type="go",
            name="go_idx1_v2",
            format="inp",
            properties={
                "path": "go_idx1_v2.inp",
                "index": "1",
                "version": "2",
                "active": True,
                "analysis_status": "failed",
                "RF3": 3.0,
                "temperature": 350,
                "materials": ["Steel"],
                "sta_errors": ["Element excessively distorted"],
            },
        ),
        Node(
            id=3,
            type="go",
            name="go_idx2_v1",
            format="inp",
            properties={
                "path": "sub/go_idx2_v1.inp",
                "index": "2",
                "version": "1",
                "active": False,
                "analysis_status": "unknown",
                "RF3": 8.0,
                "temperature": 200,
            },
        ),
        Node(
            id=4,
            type="material",
            name="material_steel",
            format="inp",
            properties={
                "path": "material_steel.inp",
            },
        ),
        Node(
            id=5,
            type="abaqus_material",
            name="Steel",
            format="material",
            properties={
                "source_file": "material_steel.inp",
                "keywords": ["elastic", "plastic"],
            },
        ),
        Node(
            id=6,
            type="go",
            name="go_idx1_v1",
            format="csv",
            properties={
                "path": "go_idx1_v1_RF3.csv",
                "index": "1",
            },
        ),
    ]
    relations = [
        Relation(id=1, label="includes", node1_id=1, node2_id=4),
        Relation(id=2, label="has_output", node1_id=1, node2_id=6),
        Relation(id=3, label="defined_in", node1_id=5, node2_id=4),
        Relation(id=4, label="next_version", node1_id=1, node2_id=2),
    ]
    return GraphModel(nodes=nodes, relations=relations)


@pytest.fixture
def graph() -> GraphModel:
    return _make_test_graph()


@pytest.fixture
def provider(graph: GraphModel) -> DashboardDataProvider:
    return DashboardDataProvider(graph)


# ====================================================================
# get_go_table
# ====================================================================


class TestGetGoTable:
    """get_go_table のテスト"""

    def test_returns_only_go_nodes(self, provider: DashboardDataProvider):
        """go_ノードのみがテーブルに含まれる"""
        rows = provider.get_go_table()
        names = {r["name"] for r in rows}
        assert "go_idx1_v1" in names
        assert "go_idx1_v2" in names
        assert "go_idx2_v1" in names
        # material, abaqus_materialは含まれない
        assert "material_steel" not in names
        assert "Steel" not in names

    def test_properties_are_expanded(self, provider: DashboardDataProvider):
        """プロパティがカラムとして展開される"""
        rows = provider.get_go_table()
        v1_rows = [r for r in rows if r["name"] == "go_idx1_v1" and r["format"] == "inp"]
        assert len(v1_rows) == 1
        row = v1_rows[0]
        assert row["index"] == "1"
        assert row["version"] == "1"
        assert row["RF3"] == 5.0
        assert row["temperature"] == 300
        assert row["materials"] == ["Steel", "Aluminum"]

    def test_path_not_in_row(self, provider: DashboardDataProvider):
        """pathプロパティは行に含まれない"""
        rows = provider.get_go_table()
        for row in rows:
            assert "path" not in row

    def test_filter_by_active(self, provider: DashboardDataProvider):
        """activeフィルタが機能する"""
        rows = provider.get_go_table(filters={"active": True})
        names = {r["name"] for r in rows}
        assert "go_idx1_v1" in names
        assert "go_idx1_v2" in names
        assert "go_idx2_v1" not in names

    def test_filter_by_analysis_status(self, provider: DashboardDataProvider):
        """analysis_statusフィルタが機能する"""
        rows = provider.get_go_table(filters={"analysis_status": "completed"})
        assert len(rows) == 1
        assert rows[0]["name"] == "go_idx1_v1"

    def test_related_files_included(self, provider: DashboardDataProvider):
        """関連ファイル情報が含まれる"""
        rows = provider.get_go_table()
        v1_rows = [r for r in rows if r["name"] == "go_idx1_v1" and r["format"] == "inp"]
        row = v1_rows[0]
        assert "related_files" in row
        related_names = {rf["name"] for rf in row["related_files"]}
        assert "material_steel" in related_names


# ====================================================================
# get_node_card
# ====================================================================


class TestGetNodeCard:
    """get_node_card のテスト"""

    def test_returns_card_for_existing_node(self, provider: DashboardDataProvider):
        """存在するノードのカードを取得できる"""
        card = provider.get_node_card(1)
        assert card is not None
        assert card["name"] == "go_idx1_v1"
        assert card["type"] == "go"
        assert card["properties"]["RF3"] == 5.0

    def test_returns_none_for_missing_node(self, provider: DashboardDataProvider):
        """存在しないノードIDではNoneを返す"""
        assert provider.get_node_card(999) is None

    def test_card_includes_relations(self, provider: DashboardDataProvider):
        """カードに関連ノード情報が含まれる"""
        card = provider.get_node_card(1)
        assert card is not None
        labels = {r["label"] for r in card["relations"]}
        assert "includes" in labels
        assert "has_output" in labels


# ====================================================================
# get_plot_data
# ====================================================================


class TestGetPlotData:
    """get_plot_data のテスト"""

    def test_returns_numeric_data_points(self, provider: DashboardDataProvider):
        """数値プロパティのデータポイントが返される"""
        points = provider.get_plot_data("RF3", "temperature")
        assert len(points) == 3  # 3つのgo_ノード
        for p in points:
            assert "RF3" in p
            assert "temperature" in p
            assert isinstance(p["RF3"], float)
            assert isinstance(p["temperature"], float)

    def test_with_color_key(self, provider: DashboardDataProvider):
        """color_key指定時にその値が含まれる"""
        points = provider.get_plot_data("RF3", "temperature", color_key="version")
        for p in points:
            assert "version" in p

    def test_missing_property_excluded(self, graph: GraphModel):
        """プロパティが欠如するノードは除外される"""
        provider = DashboardDataProvider(graph)
        points = provider.get_plot_data("RF3", "cpu_time")
        # go_idx1_v1のみcpu_timeを持つ
        assert len(points) == 1
        assert points[0]["name"] == "go_idx1_v1"


# ====================================================================
# get_property_keys
# ====================================================================


class TestGetPropertyKeys:
    """get_property_keys のテスト"""

    def test_returns_sorted_keys(self, provider: DashboardDataProvider):
        """ソート済みキーリストを返す"""
        keys = provider.get_property_keys()
        assert keys == sorted(keys)

    def test_excludes_internal_keys(self, provider: DashboardDataProvider):
        """内部キー（path等）は除外される"""
        keys = provider.get_property_keys()
        assert "path" not in keys
        assert "include_properties" not in keys

    def test_includes_property_keys(self, provider: DashboardDataProvider):
        """主要プロパティキーが含まれる"""
        keys = provider.get_property_keys()
        assert "RF3" in keys
        assert "temperature" in keys
        assert "analysis_status" in keys


# ====================================================================
# get_status_summary
# ====================================================================


class TestGetStatusSummary:
    """get_status_summary のテスト"""

    def test_counts_are_correct(self, provider: DashboardDataProvider):
        """ステータスカウントが正しい"""
        summary = provider.get_status_summary()
        # go_ノードは id=1(completed), id=2(failed), id=3(unknown), id=6(format=csv, no status)
        assert summary["total"] == 4  # go_ prefix nodes (including csv)
        assert summary["completed"] == 1
        assert summary["failed"] == 1

    def test_items_include_status_info(self, provider: DashboardDataProvider):
        """各アイテムにステータス情報が含まれる"""
        summary = provider.get_status_summary()
        items = summary["items"]
        completed_items = [i for i in items if i["analysis_status"] == "completed"]
        assert len(completed_items) == 1
        assert "cpu_time" in completed_items[0]

    def test_items_include_errors_warnings(self, provider: DashboardDataProvider):
        """エラー/警告情報が含まれる"""
        summary = provider.get_status_summary()
        items = summary["items"]
        v1_items = [i for i in items if i["name"] == "go_idx1_v1" and "warnings" in i]
        assert len(v1_items) == 1


# ====================================================================
# get_related_files
# ====================================================================


class TestGetRelatedFiles:
    """get_related_files のテスト"""

    def test_returns_related_nodes(self, provider: DashboardDataProvider):
        """関連ノードが返される"""
        related = provider.get_related_files(1)
        assert len(related) >= 2  # includes, has_output, next_version

    def test_filter_by_label(self, provider: DashboardDataProvider):
        """ラベルフィルタが機能する"""
        related = provider.get_related_files(1, label="has_output")
        assert len(related) == 1
        assert related[0]["label"] == "has_output"


# ====================================================================
# to_dashboard_json
# ====================================================================


class TestToDashboardJson:
    """to_dashboard_json のテスト"""

    def test_metadata_present(self, provider: DashboardDataProvider):
        """メタデータが含まれる"""
        result = provider.to_dashboard_json(project_name="test-project")
        assert result["metadata"]["project"] == "test-project"
        assert result["metadata"]["node_count"] > 0
        assert result["metadata"]["relation_count"] > 0
        assert "generated_at" in result["metadata"]

    def test_rows_are_go_nodes(self, provider: DashboardDataProvider):
        """rowsにはgo_ノードのデータが含まれる"""
        result = provider.to_dashboard_json()
        assert len(result["rows"]) > 0
        for row in result["rows"]:
            name = row["name"].lower()
            assert name.startswith("go_") or name == "go"

    def test_columns_present(self, provider: DashboardDataProvider):
        """カラム定義が含まれる"""
        result = provider.to_dashboard_json()
        assert "columns" in result
        assert "id" in result["columns"]
        assert "name" in result["columns"]

    def test_graph_data_present(self, provider: DashboardDataProvider):
        """完全なグラフデータが含まれる"""
        result = provider.to_dashboard_json()
        assert "graph" in result
        assert len(result["graph"]["nodes"]) > 0
        assert len(result["graph"]["relations"]) > 0
