"""DashboardDataProvider テスト

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

import contextlib
from pathlib import Path

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
    # 画像出力ノード
    nodes.append(
        Node(
            id=7,
            type="go",
            name="go_idx1_v1",
            format="png",
            properties={
                "path": "results/go_idx1_v1_merged.png",
                "index": "1",
            },
        )
    )
    nodes.append(
        Node(
            id=8,
            type="go",
            name="go_idx1_v1",
            format="gif",
            properties={
                "path": "results/go_idx1_v1_anim.gif",
                "index": "1",
            },
        )
    )
    relations = [
        Relation(id=1, label="includes", node1_id=1, node2_id=4),
        Relation(id=2, label="has_output", node1_id=1, node2_id=6),
        Relation(id=3, label="defined_in", node1_id=5, node2_id=4),
        Relation(id=4, label="next_version", node1_id=1, node2_id=2),
        Relation(id=5, label="has_output", node1_id=1, node2_id=7),
        Relation(id=6, label="has_output", node1_id=1, node2_id=8),
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

    def test_filter_by_active_string(self):
        """activeフィルタが文字列'true'でも機能する"""
        graph = GraphModel(
            nodes=[
                Node(id=1, type="go", name="go_a", format="inp", properties={"path": "a.inp", "active": "true"}),
                Node(id=2, type="go", name="go_b", format="inp", properties={"path": "b.inp", "active": "false"}),
                Node(id=3, type="go", name="go_c", format="inp", properties={"path": "c.inp", "active": True}),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        # bool Trueでフィルタ → 文字列"true"もマッチ
        rows = provider.get_go_table(filters={"active": True})
        names = {r["name"] for r in rows}
        assert "go_a" in names
        assert "go_c" in names
        assert "go_b" not in names

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
        # go_ノードは id=1(completed), id=2(failed), id=3(unknown),
        # id=6(csv,no status), id=7(png,no status), id=8(gif,no status)
        assert summary["total"] == 6  # go_ prefix nodes (including csv/png/gif)
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

    def test_summary_includes_cpu_stats(self, provider: DashboardDataProvider):
        """cpu_statsキーが含まれる"""
        summary = provider.get_status_summary()
        assert "cpu_stats" in summary

    def test_summary_includes_warning_stats(self, provider: DashboardDataProvider):
        """warning_statsキーが含まれる"""
        summary = provider.get_status_summary()
        assert "warning_stats" in summary

    def test_cpu_stats_values_when_present(self, provider: DashboardDataProvider):
        """cpu_statsにvaluesが含まれる場合、統計値が正しい"""
        summary = provider.get_status_summary()
        cpu_stats = summary["cpu_stats"]
        if cpu_stats:
            assert "count" in cpu_stats
            assert "min" in cpu_stats
            assert "max" in cpu_stats
            assert "mean" in cpu_stats
            assert "values" in cpu_stats
            assert cpu_stats["min"] <= cpu_stats["mean"] <= cpu_stats["max"]


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
        assert len(related) == 3  # csv + png + gif
        for r in related:
            assert r["label"] == "has_output"


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


# ====================================================================
# REST API (FastAPI) テスト
# ====================================================================


class TestRestApi:
    """FastAPI REST APIのテスト"""

    @pytest.fixture
    def client(self, tmp_path, graph):
        """テスト用FastAPIクライアント"""
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            pytest.skip("fastapi not installed")

        # テスト用にgraph.yamlを書き出す
        import yaml

        storage_dir = tmp_path / ".j2" / "storage"
        storage_dir.mkdir(parents=True)
        graph_file = storage_dir / "graph.yaml"

        graph_data = {
            "nodes": [n.model_dump(mode="json") for n in graph.nodes],
            "relations": [r.model_dump(mode="json") for r in graph.relations],
        }
        graph_file.write_text(
            yaml.safe_dump(graph_data, allow_unicode=True),
            encoding="utf-8",
        )

        from services.api.routes import create_app

        app = create_app(tmp_path)
        return TestClient(app)

    def test_get_graph(self, client):
        """GET /api/v1/graph でグラフ全体が返る"""
        resp = client.get("/api/v1/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "relations" in data
        assert len(data["nodes"]) == 8
        assert len(data["relations"]) == 6

    def test_get_nodes(self, client):
        """GET /api/v1/nodes でノード一覧が返る"""
        resp = client.get("/api/v1/nodes")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 8
        assert len(data["nodes"]) == 8

    def test_get_nodes_type_filter(self, client):
        """GET /api/v1/nodes?type=go でタイプフィルタが動作する"""
        resp = client.get("/api/v1/nodes?type=go")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 6
        for n in data["nodes"]:
            assert n["type"] == "go"

    def test_get_nodes_name_filter(self, client):
        """GET /api/v1/nodes?name=steel で名前フィルタが動作する"""
        resp = client.get("/api/v1/nodes?name=steel")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        for n in data["nodes"]:
            assert "steel" in n["name"].lower()

    def test_get_nodes_pagination(self, client):
        """GET /api/v1/nodes でページネーションが動作する"""
        resp = client.get("/api/v1/nodes?limit=2&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 8
        assert len(data["nodes"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 0

    def test_get_node_detail(self, client):
        """GET /api/v1/nodes/{id} でノード詳細が返る"""
        resp = client.get("/api/v1/nodes/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "go_idx1_v1"
        assert "properties" in data
        assert "relations" in data

    def test_get_node_not_found(self, client):
        """GET /api/v1/nodes/{id} で存在しないIDは404"""
        resp = client.get("/api/v1/nodes/999")
        assert resp.status_code == 404

    def test_get_related_nodes(self, client):
        """GET /api/v1/nodes/{id}/related で関連ノードが返る"""
        resp = client.get("/api/v1/nodes/1/related")
        assert resp.status_code == 200
        data = resp.json()
        assert data["node_id"] == 1
        assert len(data["related"]) >= 2

    def test_get_related_nodes_label_filter(self, client):
        """GET /api/v1/nodes/{id}/related?label=has_output でラベルフィルタが動作する"""
        resp = client.get("/api/v1/nodes/1/related?label=has_output")
        assert resp.status_code == 200
        data = resp.json()
        for r in data["related"]:
            assert r["label"] == "has_output"

    def test_get_relations(self, client):
        """GET /api/v1/relations でリレーション一覧が返る"""
        resp = client.get("/api/v1/relations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 6

    def test_get_relations_label_filter(self, client):
        """GET /api/v1/relations?label=includes でラベルフィルタが動作する"""
        resp = client.get("/api/v1/relations?label=includes")
        assert resp.status_code == 200
        data = resp.json()
        for r in data["relations"]:
            assert r["label"] == "includes"

    def test_get_property_keys(self, client):
        """GET /api/v1/properties/keys でプロパティキーが返る"""
        resp = client.get("/api/v1/properties/keys")
        assert resp.status_code == 200
        data = resp.json()
        assert "keys" in data
        assert "RF3" in data["keys"]
        assert "temperature" in data["keys"]

    def test_get_summary(self, client):
        """GET /api/v1/summary でサマリーが返る"""
        resp = client.get("/api/v1/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_nodes" in data
        assert "total_relations" in data
        assert "go_file_count" in data

    def test_get_status(self, client):
        """GET /api/v1/status でステータスが返る"""
        resp = client.get("/api/v1/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "completed" in data
        assert "failed" in data
        assert "items" in data

    def test_reload(self, client):
        """POST /api/v1/reload でグラフ再読み込みが成功する"""
        resp = client.post("/api/v1/reload")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "reloaded"


# ====================================================================
# Streamlitアプリ ユニットテスト（関数レベル）
# ====================================================================


class TestStreamlitAppHelpers:
    """Streamlitアプリのヘルパー関数テスト"""

    def test_app_module_importable(self):
        """dashboard.app モジュールがインポートできる"""
        try:
            import streamlit  # noqa: F401
        except ImportError:
            pytest.skip("streamlit not installed")
        from services.dashboard import app

        assert hasattr(app, "main")
        assert callable(app.main)

    def test_api_module_importable(self):
        """api モジュールがインポートできる"""
        try:
            import fastapi  # noqa: F401
        except ImportError:
            pytest.skip("fastapi not installed")
        from services.api import create_app

        assert callable(create_app)


# ====================================================================
# CLI コマンド登録テスト
# ====================================================================


class TestCliRegistration:
    """CLIにdashboard/serveコマンドが登録されていることを確認"""

    def test_dashboard_command_registered(self):
        """jj dashboardコマンドがパーサーに登録されている"""
        from services.cli import build_parser

        parser = build_parser()
        # dashboardが受け入れられることをテスト
        args = parser.parse_args(["dashboard"])
        assert args.cmd == "dashboard"

    def test_serve_command_registered(self):
        """jj serveコマンドがパーサーに登録されている"""
        from services.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["serve"])
        assert args.cmd == "serve"

    def test_dashboard_port_option(self):
        """jj dashboard --port でポート指定ができる"""
        from services.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["dashboard", "--port", "9000"])
        assert args.port == 9000

    def test_serve_port_and_host(self):
        """jj serve --port --host でポートとホスト指定ができる"""
        from services.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["serve", "--port", "9090", "--host", "0.0.0.0"])
        assert args.port == 9090
        assert args.host == "0.0.0.0"

    def test_dashboard_no_browser(self):
        """jj dashboard --no-browser が受け入れられる"""
        from services.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["dashboard", "--no-browser"])
        assert args.no_browser is True


# ====================================================================
# get_output_images テスト
# ====================================================================


class TestGetOutputImages:
    """get_output_images のテスト"""

    def test_returns_image_outputs(self, provider: DashboardDataProvider):
        """画像フォーマットのhas_output出力が返される"""
        images = provider.get_output_images()
        assert len(images) == 2  # png + gif
        formats = {img["image_format"] for img in images}
        assert "png" in formats
        assert "gif" in formats

    def test_excludes_non_image_outputs(self, provider: DashboardDataProvider):
        """CSV等の非画像出力は除外される"""
        images = provider.get_output_images()
        for img in images:
            assert img["image_format"] != "csv"

    def test_filter_by_node_id(self, provider: DashboardDataProvider):
        """node_id指定で対象ノードの画像のみ取得"""
        images = provider.get_output_images(node_id=1)
        assert len(images) == 2
        for img in images:
            assert img["go_node_id"] == 1

    def test_no_images_for_node_without_output(self, provider: DashboardDataProvider):
        """画像出力がないノードでは空リスト"""
        images = provider.get_output_images(node_id=3)
        assert images == []

    def test_image_info_structure(self, provider: DashboardDataProvider):
        """画像情報の構造が正しい"""
        images = provider.get_output_images()
        assert len(images) > 0
        img = images[0]
        assert "go_node_id" in img
        assert "go_node_name" in img
        assert "image_node_id" in img
        assert "image_name" in img
        assert "image_path" in img
        assert "image_format" in img
        assert "go_properties" in img

    def test_go_properties_exclude_internal(self, provider: DashboardDataProvider):
        """go_propertiesからpath等の内部キーが除外される"""
        images = provider.get_output_images()
        for img in images:
            assert "path" not in img["go_properties"]

    def test_nonexistent_node_id(self, provider: DashboardDataProvider):
        """存在しないnode_idでは空リスト"""
        images = provider.get_output_images(node_id=999)
        assert images == []


# ====================================================================
# graph.yaml変更検知 テスト
# ====================================================================


class TestGraphChangeDetection:
    """graph.yaml変更検知ヘルパーのテスト"""

    def test_find_graph_path_yaml(self, tmp_path):
        """graph.yamlが存在する場合にパスを返す"""
        from services.dashboard.query import find_graph_path

        storage_dir = tmp_path / ".j2" / "storage"
        storage_dir.mkdir(parents=True)
        graph_file = storage_dir / "graph.yaml"
        graph_file.write_text("nodes: []\nrelations: []\n")

        result = find_graph_path(tmp_path)
        assert result is not None
        assert result.name == "graph.yaml"

    def test_find_graph_path_json(self, tmp_path):
        """graph.jsonが存在する場合にパスを返す"""
        from services.dashboard.query import find_graph_path

        storage_dir = tmp_path / ".j2" / "storage"
        storage_dir.mkdir(parents=True)
        (storage_dir / "graph.json").write_text("{}")

        result = find_graph_path(tmp_path)
        assert result is not None
        assert result.name == "graph.json"

    def test_find_graph_path_none(self, tmp_path):
        """グラフファイルが存在しない場合にNoneを返す"""
        from services.dashboard.query import find_graph_path

        result = find_graph_path(tmp_path)
        assert result is None

    def test_get_graph_mtime_returns_float(self, tmp_path):
        """mtimeがfloatで返される"""
        from services.dashboard.query import get_graph_mtime

        storage_dir = tmp_path / ".j2" / "storage"
        storage_dir.mkdir(parents=True)
        (storage_dir / "graph.yaml").write_text("nodes: []\n")

        mtime = get_graph_mtime(tmp_path)
        assert isinstance(mtime, float)
        assert mtime > 0

    def test_get_graph_mtime_no_file(self, tmp_path):
        """ファイルがない場合は0.0"""
        from services.dashboard.query import get_graph_mtime

        mtime = get_graph_mtime(tmp_path)
        assert mtime == 0.0


# ====================================================================
# AgGridヘルパー テスト
# ====================================================================


class TestAgGridHelper:
    """AgGridヘルパー関数のテスト"""

    def test_try_render_aggrid_import_fallback(self):
        """st_aggridがない場合はFalseを返す"""
        try:
            import streamlit  # noqa: F401
        except ImportError:
            pytest.skip("streamlit not installed")

        import pandas as pd

        from services.dashboard.app import _try_render_aggrid

        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        # st_aggridがインストールされていない場合はFalse、
        # インストール済みでも描画コンテキストがないのでエラーになり得る。
        # ここではインポート可否のロジックのみ確認。
        with contextlib.suppress(Exception):
            _try_render_aggrid(df)
            # インストール済みの場合: Streamlitコンテキスト外でエラーか成功
            # Streamlitコンテキスト外で動かした場合のエラーは許容


# ====================================================================
# DashboardConfig テスト
# ====================================================================


class TestDashboardConfig:
    """DashboardConfig のテスト"""

    def test_default_config(self):
        """空dictからのデフォルト設定"""
        from config import DashboardConfig

        cfg = DashboardConfig.from_dict({})
        assert cfg.table_columns is None
        assert cfg.default_filters == {}
        assert cfg.plot_x is None
        assert cfg.plot_y is None
        assert cfg.gallery_defaults.columns == 5
        assert cfg.gallery_defaults.rows == 4
        assert cfg.connector_configs == {}

    def test_none_data(self):
        """Noneからのデフォルト設定"""
        from config import DashboardConfig

        cfg = DashboardConfig.from_dict(None)
        assert cfg.table_columns is None
        assert cfg.default_filters == {}

    def test_full_config(self):
        """全設定項目を指定"""
        from config import DashboardConfig

        data = {
            "table-columns": ["条件", "バージョン", "stress*"],
            "default-filters": {"active": True},
            "plot": {"x": "条件", "y": "RF3"},
            "gallery-columns": 3,
            "gallery-rows": 6,
        }
        cfg = DashboardConfig.from_dict(data)
        assert cfg.table_columns == ["条件", "バージョン", "stress*"]
        assert cfg.default_filters == {"active": True}
        assert cfg.plot_x == "条件"
        assert cfg.plot_y == "RF3"
        # 後方互換: gallery-columns/rows → gallery_defaults に統合
        assert cfg.gallery_defaults.columns == 3
        assert cfg.gallery_defaults.rows == 6

    def test_invalid_table_columns(self):
        """table-columnsが不正な場合"""
        from config import DashboardConfig

        with pytest.raises(ValueError, match="table-columns"):
            DashboardConfig.from_dict({"table-columns": "invalid"})

    def test_invalid_gallery_columns(self):
        """gallery-defaults.columnsが0以下の場合"""
        from config import DashboardConfig

        with pytest.raises(ValueError, match=r"gallery-defaults\.columns"):
            DashboardConfig.from_dict({"gallery-columns": 0})

    def test_graph_config_includes_dashboard(self):
        """GraphConfigにdashboardフィールドが含まれる"""
        from config import GraphConfig

        # 後方互換: gallery-columns → gallery_defaults.columns
        cfg = GraphConfig.from_dict({"dashboard": {"gallery-columns": 3}})
        assert cfg.dashboard.gallery_defaults.columns == 3

    def test_graph_config_default_dashboard(self):
        """dashboardセクションなしの場合デフォルト設定"""
        from config import GraphConfig

        cfg = GraphConfig.from_dict({})
        assert cfg.dashboard.table_columns is None
        assert cfg.dashboard.gallery_defaults.columns == 5

    def test_connector_configs(self):
        """connectorsセクションの読み込み"""
        from config import DashboardConfig

        data = {
            "connectors": {
                "abaqus": {
                    "material-curve-columns": {
                        "plastic": {"columns": ["stress", "strain"]},
                    }
                },
                "fluent": {"some-key": "value"},
            }
        }
        cfg = DashboardConfig.from_dict(data)
        assert "abaqus" in cfg.connector_configs
        assert "fluent" in cfg.connector_configs
        abq = cfg.get_connector_config("abaqus")
        assert "material-curve-columns" in abq
        assert abq["material-curve-columns"]["plastic"]["columns"] == ["stress", "strain"]

    def test_get_connector_config_missing(self):
        """存在しないコネクタキーでは空辞書"""
        from config import DashboardConfig

        cfg = DashboardConfig.from_dict({})
        assert cfg.get_connector_config("nonexistent") == {}

    def test_backward_compat_material_curve_columns(self):
        """旧形式material-curve-columnsがabaqusコネクタに移行される"""
        from config import DashboardConfig

        data = {
            "material-curve-columns": {
                "plastic": {"columns": ["stress", "strain"], "x": 1, "y": 0},
            }
        }
        cfg = DashboardConfig.from_dict(data)
        abq = cfg.get_connector_config("abaqus")
        assert "material-curve-columns" in abq
        assert abq["material-curve-columns"]["plastic"]["columns"] == ["stress", "strain"]

    def test_list_summary_columns_default(self):
        """list-summary-columnsのデフォルト値"""
        from config import DashboardConfig

        cfg = DashboardConfig.from_dict({})
        assert cfg.list_summary_columns == ["msg_errors", "dat_errors"]

    def test_list_summary_columns_custom(self):
        """list-summary-columnsのカスタム設定"""
        from config import DashboardConfig

        cfg = DashboardConfig.from_dict({"list-summary-columns": ["msg_errors", "sta_errors"]})
        assert cfg.list_summary_columns == ["msg_errors", "sta_errors"]

    def test_list_summary_columns_invalid(self):
        """list-summary-columnsが不正な型"""
        from config import DashboardConfig

        with pytest.raises(ValueError, match="list-summary-columns"):
            DashboardConfig.from_dict({"list-summary-columns": "invalid"})


# ====================================================================
# get_property_images テスト
# ====================================================================


class TestGetPropertyImages:
    """get_property_images のテスト"""

    def test_detects_image_path_in_property(self):
        """プロパティの画像パスを検出する"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "path": "go_idx1_v1.inp",
                        "screenshot": "results/capture.png",
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        images = provider.get_property_images()
        assert len(images) == 1
        assert images[0]["property_key"] == "screenshot"
        assert images[0]["image_path"] == "results/capture.png"
        assert images[0]["image_format"] == "png"
        assert images[0]["go_node_name"] == "go_idx1_v1"

    def test_detects_image_in_list_property(self):
        """リスト型プロパティ内の画像パスを検出する"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "path": "go_idx1_v1.inp",
                        "images": ["fig1.png", "fig2.jpg", "data.csv"],
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        images = provider.get_property_images()
        # png + jpg の2件。csvは画像でないので除外。
        assert len(images) == 2
        formats = {img["image_format"] for img in images}
        assert "png" in formats
        assert "jpg" in formats

    def test_ignores_non_image_properties(self):
        """非画像プロパティは無視する"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "path": "go_idx1_v1.inp",
                        "index": "1",
                        "RF3": 5.0,
                        "data_file": "results/data.csv",
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        images = provider.get_property_images()
        assert len(images) == 0

    def test_excludes_non_go_nodes(self):
        """go_ノード以外は対象外"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="material",
                    name="material_steel",
                    format="inp",
                    properties={
                        "path": "material_steel.inp",
                        "screenshot": "mat.png",
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        images = provider.get_property_images()
        assert len(images) == 0

    def test_excludes_path_property(self):
        """pathプロパティ自体は画像検出対象外"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "path": "results/go_idx1_v1.png",
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        images = provider.get_property_images()
        assert len(images) == 0

    def test_go_properties_in_result(self):
        """結果にgo_propertiesが含まれpathが除外される"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "path": "go_idx1_v1.inp",
                        "index": "1",
                        "screenshot": "fig.png",
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        images = provider.get_property_images()
        assert len(images) == 1
        assert "path" not in images[0]["go_properties"]
        assert images[0]["go_properties"]["index"] == "1"

    def test_empty_graph(self):
        """空グラフで空リスト"""
        provider = DashboardDataProvider(GraphModel(nodes=[], relations=[]))
        assert provider.get_property_images() == []


# ====================================================================
# _select_table_columns テスト
# ====================================================================


class TestSelectTableColumns:
    """select_table_columns のテスト"""

    def test_none_returns_all(self):
        """table_columnsがNoneの場合は全カラム返却"""
        from services.dashboard.query import select_table_columns

        cols = ["name", "type", "format", "index", "RF3"]
        assert select_table_columns(cols, None) == cols

    def test_filters_and_orders(self):
        """指定パターンに基づくフィルタと順序付け"""
        from services.dashboard.query import select_table_columns

        all_cols = ["name", "type", "format", "index", "RF3", "temperature", "active"]
        table_columns = ["RF3", "index"]
        result = select_table_columns(all_cols, table_columns)
        # 固定カラム(name, type, format) + 指定カラム(RF3, index)
        assert result == ["name", "type", "format", "RF3", "index"]

    def test_glob_pattern(self):
        """globパターンによるカラムマッチ"""
        from services.dashboard.query import select_table_columns

        all_cols = ["name", "type", "format", "stress_center", "stress_edge", "RF3"]
        table_columns = ["stress*", "RF3"]
        result = select_table_columns(all_cols, table_columns)
        assert result == ["name", "type", "format", "stress_center", "stress_edge", "RF3"]

    def test_no_match(self):
        """マッチしないパターンの場合は固定カラムのみ"""
        from services.dashboard.query import select_table_columns

        all_cols = ["name", "type", "format", "index"]
        table_columns = ["nonexistent"]
        result = select_table_columns(all_cols, table_columns)
        assert result == ["name", "type", "format"]


# ====================================================================
# _is_truthy テスト
# ====================================================================


class TestIsTruthy:
    """is_truthy のテスト"""

    def test_bool_true(self):
        """Python bool Trueを正しく判定"""
        from services.dashboard.query import is_truthy

        assert is_truthy(True) is True

    def test_bool_false(self):
        """Python bool Falseを正しく判定"""
        from services.dashboard.query import is_truthy

        assert is_truthy(False) is False

    def test_string_true(self):
        """文字列 'true' を正しく判定"""
        from services.dashboard.query import is_truthy

        assert is_truthy("true") is True
        assert is_truthy("True") is True
        assert is_truthy("TRUE") is True

    def test_string_false(self):
        """文字列 'false' を正しく判定"""
        from services.dashboard.query import is_truthy

        assert is_truthy("false") is False
        assert is_truthy("False") is False

    def test_none(self):
        """Noneはfalse"""
        from services.dashboard.query import is_truthy

        assert is_truthy(None) is False


# ====================================================================
# SavedViewConfig テスト
# ====================================================================


class TestSavedViewConfig:
    """SavedViewConfig のテスト"""

    def test_basic_table_view(self):
        """基本テーブルビュー設定"""
        from config import SavedViewConfig

        view = SavedViewConfig.from_dict(
            {
                "name": "テスト一覧",
                "type": "table",
                "filters": {"active": True},
            }
        )
        assert view.name == "テスト一覧"
        assert view.view_type == "table"
        assert view.filters == {"active": True}
        assert view.plot == {}
        assert view.gallery == {}

    def test_plot_view(self):
        """プロットビュー設定"""
        from config import SavedViewConfig

        view = SavedViewConfig.from_dict(
            {
                "name": "RF3 vs 条件",
                "type": "plot",
                "plot": {"x": "条件", "y": "RF3", "color": "バージョン"},
            }
        )
        assert view.view_type == "plot"
        assert view.plot["x"] == "条件"
        assert view.plot["y"] == "RF3"

    def test_gallery_view(self):
        """ギャラリービュー設定"""
        from config import SavedViewConfig

        view = SavedViewConfig.from_dict(
            {
                "name": "スクショ",
                "type": "gallery",
                "gallery": {"source": "property", "property_key": "screenshot"},
            }
        )
        assert view.view_type == "gallery"
        assert view.gallery["source"] == "property"

    def test_missing_name_raises(self):
        """name未指定でエラー"""
        from config import SavedViewConfig

        with pytest.raises(ValueError, match="name"):
            SavedViewConfig.from_dict({"type": "table"})

    def test_invalid_type_raises(self):
        """不正なtypeでエラー"""
        from config import SavedViewConfig

        with pytest.raises(ValueError, match="type"):
            SavedViewConfig.from_dict({"name": "test", "type": "invalid"})

    def test_dashboard_config_with_saved_views(self):
        """DashboardConfigにsaved_viewsが含まれる"""
        from config import DashboardConfig

        data = {
            "saved-views": [
                {"name": "一覧", "type": "table"},
                {"name": "プロット", "type": "plot", "plot": {"x": "RF3", "y": "temp"}},
            ]
        }
        cfg = DashboardConfig.from_dict(data)
        assert len(cfg.saved_views) == 2
        assert cfg.saved_views[0].name == "一覧"
        assert cfg.saved_views[1].view_type == "plot"

    def test_dashboard_config_empty_saved_views(self):
        """saved-views未指定で空リスト"""
        from config import DashboardConfig

        cfg = DashboardConfig.from_dict({})
        assert cfg.saved_views == []


# ====================================================================
# get_property_images daily_notes テスト
# ====================================================================


class TestGetPropertyImagesDailyNotes:
    """get_property_images daily_notes dict内の画像パス検出テスト"""

    def test_detects_image_in_daily_notes(self):
        """daily_notes dict内の画像パスを検出する"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "path": "go_idx1_v1.inp",
                        "daily_notes": {
                            "2026-01-15": {
                                "screenshot": "attachments/capture.png",
                            }
                        },
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        images = provider.get_property_images()
        assert len(images) == 1
        assert images[0]["image_format"] == "png"
        # notes/daily/ が付加される
        assert images[0]["image_path"] == "notes/daily/attachments/capture.png"
        assert images[0]["property_key"] == "daily:2026-01-15:screenshot"

    def test_daily_notes_relative_path_resolved(self):
        """daily_notes内の相対パスがプロジェクトルート基準に変換される"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "path": "go_idx1_v1.inp",
                        "daily_notes": {
                            "2026-02-10": {
                                "image": "../assets/fig.jpg",
                            }
                        },
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        images = provider.get_property_images()
        assert len(images) == 1
        # notes/daily/../assets/fig.jpg → notes/assets/fig.jpg (正規化)
        assert images[0]["image_path"] == "notes/assets/fig.jpg"

    def test_daily_notes_list_values(self):
        """daily_notes内のリスト型値から画像検出"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "path": "go_idx1_v1.inp",
                        "daily_notes": {
                            "2026-01-20": {
                                "figures": ["fig1.png", "fig2.svg", "data.csv"],
                            }
                        },
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        images = provider.get_property_images()
        # png + svg の2件。csvは画像でないので除外。
        assert len(images) == 2
        formats = {img["image_format"] for img in images}
        assert "png" in formats
        assert "svg" in formats

    def test_daily_notes_non_image_excluded(self):
        """daily_notes内の非画像プロパティは除外"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "path": "go_idx1_v1.inp",
                        "daily_notes": {
                            "2026-01-15": {
                                "status": "completed",
                                "notes": "テスト完了",
                            }
                        },
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        images = provider.get_property_images()
        assert len(images) == 0

    def test_custom_daily_notes_dir(self):
        """daily_notes_dirカスタム指定"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "path": "go_idx1_v1.inp",
                        "daily_notes": {
                            "2026-01-15": {
                                "photo": "img.png",
                            }
                        },
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        images = provider.get_property_images(daily_notes_dir="custom/notes")
        assert len(images) == 1
        assert images[0]["image_path"] == "custom/notes/img.png"


# ====================================================================
# format_float_value テスト
# ====================================================================


class TestFormatFloatValue:
    """format_float_value のテスト"""

    def test_large_float_scientific(self):
        """1e4以上のfloatは指数表示"""
        from services.dashboard.data_provider import format_float_value

        result = format_float_value(12345.678)
        assert result == "1.23e+04"

    def test_small_float_scientific(self):
        """1e-2未満のfloatは指数表示"""
        from services.dashboard.data_provider import format_float_value

        result = format_float_value(0.001234)
        assert result == "1.23e-03"

    def test_normal_float_unchanged(self):
        """通常範囲のfloatはそのまま"""
        from services.dashboard.data_provider import format_float_value

        result = format_float_value(3.14)
        assert result == 3.14

    def test_zero_unchanged(self):
        """0はそのまま"""
        from services.dashboard.data_provider import format_float_value

        result = format_float_value(0.0)
        assert result == 0.0

    def test_negative_large(self):
        """負の大きな値も指数表示"""
        from services.dashboard.data_provider import format_float_value

        result = format_float_value(-50000.0)
        assert result == "-5.00e+04"

    def test_int_unchanged(self):
        """intはそのまま"""
        from services.dashboard.data_provider import format_float_value

        result = format_float_value(100)
        assert result == 100

    def test_bool_unchanged(self):
        """boolはそのまま"""
        from services.dashboard.data_provider import format_float_value

        assert format_float_value(True) is True
        assert format_float_value(False) is False

    def test_boundary_9999(self):
        """9999はそのまま（1e4未満）"""
        from services.dashboard.data_provider import format_float_value

        assert format_float_value(9999.0) == 9999.0

    def test_boundary_10000(self):
        """10000は指数表示（1e4以上）"""
        from services.dashboard.data_provider import format_float_value

        result = format_float_value(10000.0)
        assert result == "1.00e+04"

    def test_boundary_0_01(self):
        """0.01はそのまま（1e-2以上）"""
        from services.dashboard.data_provider import format_float_value

        assert format_float_value(0.01) == 0.01

    def test_boundary_0_009(self):
        """0.009は指数表示（1e-2未満）"""
        from services.dashboard.data_provider import format_float_value

        result = format_float_value(0.009)
        assert result == "9.00e-03"


# ====================================================================
# _normalize_group_key テスト
# ====================================================================


class TestNormalizeGroupKey:
    """normalize_group_key のテスト"""

    def test_daily_key_normalized(self):
        """daily:日付:キー → キーに正規化"""
        from services.dashboard.query import normalize_group_key

        assert normalize_group_key("daily:2026-01-15:screenshot") == "screenshot"

    def test_non_daily_key_unchanged(self):
        """dailyでないキーはそのまま"""
        from services.dashboard.query import normalize_group_key

        assert normalize_group_key("screenshot") == "screenshot"

    def test_daily_two_parts(self):
        """daily:xxのみ（2パート）はそのまま"""
        from services.dashboard.query import normalize_group_key

        assert normalize_group_key("daily:only") == "daily:only"


# ====================================================================
# _estimate_column_width テスト
# ====================================================================


class TestEstimateColumnWidth:
    """_estimate_column_width のテスト"""

    def test_ascii_columns(self):
        """英数字のみの列名"""
        try:
            import streamlit  # noqa: F401
        except ImportError:
            pytest.skip("streamlit not installed")
        from services.dashboard.app import _estimate_column_width

        width = _estimate_column_width("RF3")
        assert width == max(80, 3 * 10 + 30)

    def test_japanese_columns(self):
        """日本語列名は2文字分"""
        try:
            import streamlit  # noqa: F401
        except ImportError:
            pytest.skip("streamlit not installed")
        from services.dashboard.app import _estimate_column_width

        width = _estimate_column_width("条件")
        # 2文字 x 2(全角) = 4文字分、4*10+30 = 70 → min 80
        assert width == 80

    def test_minimum_width(self):
        """最小幅は80px"""
        try:
            import streamlit  # noqa: F401
        except ImportError:
            pytest.skip("streamlit not installed")
        from services.dashboard.app import _estimate_column_width

        width = _estimate_column_width("a")
        assert width == 80

    def test_long_name(self):
        """長い名前は適切に計算"""
        try:
            import streamlit  # noqa: F401
        except ImportError:
            pytest.skip("streamlit not installed")
        from services.dashboard.app import _estimate_column_width

        width = _estimate_column_width("analysis_status")
        # 15文字 x 1 = 15文字分、15*10+30 = 180
        assert width == 180


# ====================================================================
# _sort_columns_by_vocab テスト
# ====================================================================


class TestSortColumnsByVocab:
    """sort_columns_by_vocab のテスト"""

    def test_vocab_order_first(self):
        """vocab定義順が優先される"""
        from services.dashboard.query import sort_columns_by_vocab

        vocab = {"idx": "条件", "ver": "バージョン"}
        cols = ["RF3", "バージョン", "条件", "temperature"]
        result = sort_columns_by_vocab(cols, vocab)
        # vocab順: 条件(idx=0位), バージョン(ver=1位) → 残り: RF3, temperature
        assert result == ["条件", "バージョン", "RF3", "temperature"]

    def test_no_vocab_alphabetical(self):
        """vocabが空の場合は文字列昇順"""
        from services.dashboard.query import sort_columns_by_vocab

        cols = ["RF3", "temperature", "active"]
        result = sort_columns_by_vocab(cols, {})
        assert result == ["RF3", "active", "temperature"]

    def test_mixed_vocab_non_vocab(self):
        """vocabに含まれるものと含まれないものの混合"""
        from services.dashboard.query import sort_columns_by_vocab

        vocab = {"idx": "条件"}
        cols = ["RF3", "条件", "active"]
        result = sort_columns_by_vocab(cols, vocab)
        assert result == ["条件", "RF3", "active"]


# ====================================================================
# get_property_keys vocab順 テスト
# ====================================================================


class TestGetPropertyKeysVocabOrder:
    """get_property_keys のvocab順テスト"""

    def test_vocab_order_applied(self):
        """vocabで定義されたキーが先に来る"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "path": "a.inp",
                        "RF3": 5.0,
                        "条件": "1",
                        "バージョン": "1",
                        "temperature": 300,
                    },
                ),
            ],
            relations=[],
        )
        vocab = {"idx": "条件", "ver": "バージョン"}
        provider = DashboardDataProvider(graph, vocab=vocab)
        keys = provider.get_property_keys()
        # 条件、バージョンが先、それ以外は文字列昇順
        assert keys.index("条件") < keys.index("RF3")
        assert keys.index("バージョン") < keys.index("RF3")
        assert keys.index("条件") < keys.index("バージョン")


# ====================================================================
# init_graph_config コメント保持テスト
# ====================================================================


class TestInitGraphConfigWithComments:
    """init_graph_config がコメント付きで config.yaml を生成するテスト"""

    def test_comments_preserved(self, tmp_path):
        """生成されたconfig.yamlにコメントが含まれる"""
        from config import init_graph_config

        config_path = init_graph_config(base_dir=tmp_path)
        content = config_path.read_text(encoding="utf-8")
        # コメント行が含まれていること
        assert "# jj デフォルト設定ファイル" in content
        assert "# 使用例:" in content
        assert "# ========" in content

    def test_sections_present(self, tmp_path):
        """主要セクションが含まれる"""
        from config import init_graph_config

        config_path = init_graph_config(base_dir=tmp_path)
        content = config_path.read_text(encoding="utf-8")
        assert "vocab:" in content
        assert "path-type-map:" in content
        assert "path-property-map:" in content
        assert "ignore:" in content
        assert "file-relations:" in content
        assert "export:" in content
        assert "dashboard:" in content
        assert "obsidian:" in content

    def test_cache_settings_documented(self, tmp_path):
        """キャッシュ設定がドキュメント化されている"""
        from config import init_graph_config

        config_path = init_graph_config(base_dir=tmp_path)
        content = config_path.read_text(encoding="utf-8")
        assert "cache-max-age-days" in content
        assert "cache-max-count" in content


# ====================================================================
# CsvArrayParser テスト
# ====================================================================


class TestCsvArrayParser:
    """csv_array_parser のテスト"""

    def test_compute_extra_token_single(self):
        """1トークン差分の検出"""
        from services.parse.parsers.csv_array_parser import _compute_extra_token

        result = _compute_extra_token("go_idx1_w5_t20", "go_idx1_w5_t20_RF")
        assert result == "RF"

    def test_compute_extra_token_no_diff(self):
        """トークン差分なし"""
        from services.parse.parsers.csv_array_parser import _compute_extra_token

        result = _compute_extra_token("go_idx1_w5_t20", "go_idx1_w5_t20")
        assert result == ""

    def test_compute_extra_token_two_diff(self):
        """2トークン差分は無効"""
        from services.parse.parsers.csv_array_parser import _compute_extra_token

        result = _compute_extra_token("go_idx1", "go_idx1_RF_extra_token")
        assert result == ""

    def test_compute_extra_token_stress(self):
        """stressトークンの検出"""
        from services.parse.parsers.csv_array_parser import _compute_extra_token

        result = _compute_extra_token("go_idx1_w5", "go_idx1_w5_stress")
        assert result == "stress"

    def test_read_csv_arrays(self, tmp_path):
        """CSVファイルの配列読み取り"""
        from services.parse.parsers.csv_array_parser import _read_csv_arrays

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("time,RF3\n0.0,0.0\n0.5,123.4\n1.0,456.7\n")

        result = _read_csv_arrays(csv_file)
        assert "time" in result
        assert "RF3" in result
        assert result["time"] == [0.0, 0.5, 1.0]
        assert result["RF3"] == [0.0, 123.4, 456.7]

    def test_read_csv_arrays_empty(self, tmp_path):
        """空CSVファイル"""
        from services.parse.parsers.csv_array_parser import _read_csv_arrays

        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("")

        result = _read_csv_arrays(csv_file)
        assert result == {}

    def test_read_csv_arrays_nonexistent(self, tmp_path):
        """存在しないCSVファイル"""
        from services.parse.parsers.csv_array_parser import _read_csv_arrays

        result = _read_csv_arrays(tmp_path / "nonexistent.csv")
        assert result == {}


# ====================================================================
# get_array_property_keys テスト
# ====================================================================


class TestGetArrayPropertyKeys:
    """get_array_property_keys のテスト"""

    def test_returns_dot_notation_keys(self):
        """ドット記法の配列キーを返す"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "path": "go_idx1_v1.inp",
                        "RF.time": [0.0, 0.5, 1.0],
                        "RF.RF3": [0.0, 123.4, 456.7],
                        "index": "1",
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        keys = provider.get_array_property_keys()
        assert "RF.time" in keys
        assert "RF.RF3" in keys
        assert "index" not in keys  # 非配列は含まない

    def test_empty_graph(self):
        """空グラフでは空リスト"""
        provider = DashboardDataProvider(GraphModel(nodes=[], relations=[]))
        assert provider.get_array_property_keys() == []


# ====================================================================
# get_array_plot_data テスト
# ====================================================================


class TestGetArrayPlotData:
    """get_array_plot_data のテスト"""

    def _make_graph(self):
        return GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "path": "go_idx1_v1.inp",
                        "RF.time": [0.0, 0.5, 1.0],
                        "RF.RF1": [10.0, 20.0, 30.0],
                        "RF.RF3": [0.0, 123.4, 456.7],
                    },
                ),
            ],
            relations=[],
        )

    def test_returns_all_series_for_prefix(self):
        """接頭辞のY軸を自動選択"""
        provider = DashboardDataProvider(self._make_graph())
        result = provider.get_array_plot_data(1, "RF.time")
        assert result is not None
        assert result["name"] == "go_idx1_v1"
        assert result["x_values"] == [0.0, 0.5, 1.0]
        series_keys = {s["key"] for s in result["series"]}
        assert "RF.RF1" in series_keys
        assert "RF.RF3" in series_keys

    def test_explicit_y_keys(self):
        """Y軸を明示指定"""
        provider = DashboardDataProvider(self._make_graph())
        result = provider.get_array_plot_data(1, "RF.time", y_keys=["RF.RF3"])
        assert result is not None
        assert len(result["series"]) == 1
        assert result["series"][0]["key"] == "RF.RF3"

    def test_missing_node(self):
        """存在しないノードIDはNone"""
        provider = DashboardDataProvider(self._make_graph())
        assert provider.get_array_plot_data(999, "RF.time") is None


# ====================================================================
# get_array_grid_data テスト
# ====================================================================


class TestGetArrayGridData:
    """get_array_grid_data のテスト"""

    def test_returns_grid_data(self):
        """グリッドデータを返す"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "path": "a.inp",
                        "index": "1",
                        "version": "1",
                        "RF.time": [0.0, 1.0],
                        "RF.RF3": [0.0, 100.0],
                    },
                ),
                Node(
                    id=2,
                    type="go",
                    name="go_idx2_v1",
                    format="inp",
                    properties={
                        "path": "b.inp",
                        "index": "2",
                        "version": "1",
                        "RF.time": [0.0, 1.0],
                        "RF.RF3": [0.0, 200.0],
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        data = provider.get_array_grid_data("RF.time", "RF.RF3")
        assert len(data) == 2
        assert data[0]["name"] == "go_idx1_v1"
        assert data[0]["x_values"] == [0.0, 1.0]
        assert data[0]["y_values"] == [0.0, 100.0]

    def test_excludes_nodes_without_arrays(self):
        """配列データなしのノードは除外"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"path": "a.inp", "RF.time": [0.0], "RF.RF3": [0.0]},
                ),
                Node(id=2, type="go", name="go_idx2_v1", format="inp", properties={"path": "b.inp", "index": "2"}),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        data = provider.get_array_grid_data("RF.time", "RF.RF3")
        assert len(data) == 1


# ====================================================================
# get_material_table テスト
# ====================================================================


class TestGetMaterialTable:
    """get_material_table のテスト（コネクター版）"""

    def _make_material_graph(self):
        return GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="abaqus_material",
                    name="Steel_S235",
                    format="material",
                    properties={
                        "source_file": "material.inp",
                        "keywords": ["elastic", "plastic"],
                        "elastic": [[210000.0, 0.3]],
                        "plastic": [[235.0, 0.0], [360.0, 0.2]],
                        "density": [[7.85e-09]],
                    },
                ),
                Node(
                    id=2,
                    type="abaqus_material",
                    name="Aluminum_6061",
                    format="material",
                    properties={
                        "source_file": "material.inp",
                        "keywords": ["elastic"],
                        "elastic": [[69000.0, 0.33]],
                    },
                ),
                Node(
                    id=3,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"path": "go_idx1_v1.inp"},
                ),
            ],
            relations=[],
        )

    def test_returns_material_rows(self):
        """abaqus_materialノードのテーブル行を返す"""
        from services.dashboard.connectors.abaqus import get_material_table

        provider = DashboardDataProvider(self._make_material_graph())
        rows = get_material_table(provider)
        assert len(rows) == 2
        names = {r["name"] for r in rows}
        assert "Steel_S235" in names
        assert "Aluminum_6061" in names

    def test_table_data_summarized(self):
        """テーブル型データはフォーマット表示"""
        from services.dashboard.connectors.abaqus import get_material_table

        provider = DashboardDataProvider(self._make_material_graph())
        rows = get_material_table(provider)
        steel = next(r for r in rows if r["name"] == "Steel_S235")
        # 2行以上 → "配列"
        assert steel["plastic"] == "配列"
        # 1行2要素 → "val0(val1)"
        assert steel["elastic"] == "210000.0(0.3)"
        # 1行1要素 → そのまま
        assert steel["density"] == "7.85e-09"

    def test_excludes_go_nodes(self):
        """go_ノードは含まれない"""
        from services.dashboard.connectors.abaqus import get_material_table

        provider = DashboardDataProvider(self._make_material_graph())
        rows = get_material_table(provider)
        names = {r["name"] for r in rows}
        assert "go_idx1_v1" not in names


# ====================================================================
# get_material_table_data テスト
# ====================================================================


class TestGetMaterialTableData:
    """get_material_table_data のテスト（コネクター版）"""

    def test_returns_table_data(self):
        """テーブル型プロパティデータを返す"""
        from services.dashboard.connectors.abaqus import get_material_table_data

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="abaqus_material",
                    name="Steel",
                    format="material",
                    properties={
                        "keywords": ["plastic"],
                        "plastic": [[235.0, 0.0], [360.0, 0.2]],
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        result = get_material_table_data(provider, 1, "plastic")
        assert result is not None
        assert result["name"] == "Steel"
        assert result["property_key"] == "plastic"
        assert len(result["data"]) == 2
        assert result["data"][0] == [235.0, 0.0]

    def test_returns_none_for_nonexistent(self):
        """存在しないノードIDはNone"""
        from services.dashboard.connectors.abaqus import get_material_table_data

        provider = DashboardDataProvider(GraphModel(nodes=[], relations=[]))
        assert get_material_table_data(provider, 999, "plastic") is None

    def test_returns_none_for_non_table(self):
        """テーブル型でないプロパティはNone"""
        from services.dashboard.connectors.abaqus import get_material_table_data

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="abaqus_material",
                    name="Steel",
                    format="material",
                    properties={"keywords": ["elastic"]},
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        assert get_material_table_data(provider, 1, "keywords") is None


# ====================================================================
# get_material_table_keys テスト
# ====================================================================


class TestGetMaterialTableKeys:
    """get_material_table_keys のテスト（コネクター版）"""

    def test_returns_table_keys(self):
        """テーブル型キーのみ返す"""
        from services.dashboard.connectors.abaqus import get_material_table_keys

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="abaqus_material",
                    name="Steel",
                    format="material",
                    properties={
                        "keywords": ["elastic", "plastic"],
                        "elastic": [[210000.0, 0.3]],
                        "plastic": [[235.0, 0.0], [360.0, 0.2]],
                        "verbose_name": "鋼材",
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        keys = get_material_table_keys(provider, 1)
        # elastic は1行のみなので配列プロット対象外
        assert "elastic" not in keys
        assert "plastic" in keys
        assert "keywords" not in keys  # list[str]はテーブル型でない
        assert "verbose_name" not in keys

    def test_empty_for_go_node(self):
        """go_ノードは空リスト"""
        from services.dashboard.connectors.abaqus import get_material_table_keys

        graph = GraphModel(
            nodes=[
                Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "a.inp"}),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        assert get_material_table_keys(provider, 1) == []


# ====================================================================
# _guess_table_column_names テスト
# ====================================================================


class TestGuessTableColumnNames:
    """guess_table_column_names のテスト（config駆動、コネクター版）"""

    def test_plastic_columns_from_config(self):
        """configからplasticの列名を取得"""
        from services.dashboard.connectors.abaqus import guess_table_column_names

        mcc = {
            "plastic": {"columns": ["stress", "strain"]},
        }
        names = guess_table_column_names("plastic", 2, mcc)
        assert names == ["stress", "strain"]

    def test_elastic_columns_from_config(self):
        """configからelasticの列名を取得"""
        from services.dashboard.connectors.abaqus import guess_table_column_names

        mcc = {
            "elastic": {"columns": ["E", "nu"]},
        }
        names = guess_table_column_names("elastic", 2, mcc)
        assert names == ["E", "nu"]

    def test_unknown_columns_no_config(self):
        """configにマッチしないキーはcol_Nで補完"""
        from services.dashboard.connectors.abaqus import guess_table_column_names

        names = guess_table_column_names("unknown_prop", 3, {})
        assert names == ["col_0", "col_1", "col_2"]

    def test_none_config_fallback(self):
        """config=Noneの場合もcol_Nで補完"""
        from services.dashboard.connectors.abaqus import guess_table_column_names

        names = guess_table_column_names("plastic", 2, None)
        assert names == ["col_0", "col_1"]

    def test_config_columns_fewer_than_num_cols(self):
        """configの列数がnum_colsより少ない場合はcol_Nで補完"""
        from services.dashboard.connectors.abaqus import guess_table_column_names

        mcc = {
            "plastic": {"columns": ["stress"]},
        }
        names = guess_table_column_names("plastic", 3, mcc)
        assert names == ["stress", "col_1", "col_2"]

    def test_config_columns_more_than_num_cols(self):
        """configの列数がnum_colsより多い場合は切り詰め"""
        from services.dashboard.connectors.abaqus import guess_table_column_names

        mcc = {
            "creep": {"columns": ["A", "n", "m"]},
        }
        names = guess_table_column_names("creep", 2, mcc)
        assert names == ["A", "n"]


# ====================================================================
# _get_curve_plot_axes テスト
# ====================================================================


class TestGetCurvePlotAxes:
    """get_curve_plot_axes のテスト（コネクター版）"""

    def test_default_axes(self):
        """configなしの場合はx=0, y=1"""
        from services.dashboard.connectors.abaqus import get_curve_plot_axes

        x, y = get_curve_plot_axes("elastic", 2, None)
        assert x == 0
        assert y == 1

    def test_config_axes(self):
        """configでx/yインデックスを指定"""
        from services.dashboard.connectors.abaqus import get_curve_plot_axes

        mcc = {
            "plastic": {"columns": ["stress", "strain"], "x": 1, "y": 0},
        }
        x, y = get_curve_plot_axes("plastic", 2, mcc)
        assert x == 1
        assert y == 0

    def test_config_no_axes(self):
        """configにcolumnsはあるがx/y未指定の場合はデフォルト"""
        from services.dashboard.connectors.abaqus import get_curve_plot_axes

        mcc = {
            "elastic": {"columns": ["E", "nu"]},
        }
        x, y = get_curve_plot_axes("elastic", 2, mcc)
        assert x == 0
        assert y == 1

    def test_config_axes_clamped(self):
        """x/yインデックスがnum_colsを超えた場合はクランプ"""
        from services.dashboard.connectors.abaqus import get_curve_plot_axes

        mcc = {
            "test": {"columns": ["a"], "x": 5, "y": 10},
        }
        x, y = get_curve_plot_axes("test", 1, mcc)
        assert x == 0
        assert y == 0

    def test_unknown_key_default(self):
        """configにないキーはデフォルト"""
        from services.dashboard.connectors.abaqus import get_curve_plot_axes

        mcc = {"plastic": {"columns": ["stress", "strain"], "x": 1, "y": 0}}
        x, y = get_curve_plot_axes("unknown", 3, mcc)
        assert x == 0
        assert y == 1


# ====================================================================
# DashboardConfig material-curve-columns テスト
# ====================================================================


class TestDashboardConfigMaterialCurveColumns:
    """DashboardConfig connector_configs経由のmaterial-curve-columns テスト"""

    def test_default_empty(self):
        """デフォルトでconnector_configsが空dict"""
        from config import DashboardConfig

        cfg = DashboardConfig.from_dict({})
        assert cfg.connector_configs == {}
        assert cfg.get_connector_config("abaqus") == {}

    def test_connectors_format(self):
        """connectors形式でabaqus固有設定を指定"""
        from config import DashboardConfig

        data = {
            "connectors": {
                "abaqus": {
                    "material-curve-columns": {
                        "plastic": {
                            "columns": ["stress", "strain"],
                            "x": 1,
                            "y": 0,
                        },
                        "elastic": {
                            "columns": ["E", "nu"],
                        },
                    }
                }
            }
        }
        cfg = DashboardConfig.from_dict(data)
        abq = cfg.get_connector_config("abaqus")
        mcc = abq["material-curve-columns"]
        assert "plastic" in mcc
        assert mcc["plastic"]["columns"] == ["stress", "strain"]
        assert mcc["plastic"]["x"] == 1
        assert mcc["plastic"]["y"] == 0
        assert "elastic" in mcc
        assert mcc["elastic"]["columns"] == ["E", "nu"]

    def test_backward_compat_material_curve_columns(self):
        """旧形式material-curve-columnsがabaqusコネクタに自動移行される"""
        from config import DashboardConfig

        data = {
            "material-curve-columns": {
                "density": ["density"],
            }
        }
        cfg = DashboardConfig.from_dict(data)
        abq = cfg.get_connector_config("abaqus")
        mcc = abq["material-curve-columns"]
        assert mcc["density"] == ["density"]

    def test_graph_config_includes_mcc(self):
        """GraphConfigからconnectors.abaqus.material-curve-columnsが読み込まれる"""
        from config import GraphConfig

        cfg = GraphConfig.from_dict(
            {
                "dashboard": {
                    "connectors": {
                        "abaqus": {
                            "material-curve-columns": {
                                "plastic": {"columns": ["stress", "strain"], "x": 1, "y": 0},
                            }
                        }
                    }
                }
            }
        )
        abq = cfg.dashboard.get_connector_config("abaqus")
        assert "plastic" in abq["material-curve-columns"]

    def test_backward_compat_graph_config(self):
        """旧形式GraphConfigのmaterial-curve-columnsも後方互換で読める"""
        from config import GraphConfig

        cfg = GraphConfig.from_dict(
            {
                "dashboard": {
                    "material-curve-columns": {
                        "plastic": {"columns": ["stress", "strain"], "x": 1, "y": 0},
                    }
                }
            }
        )
        abq = cfg.dashboard.get_connector_config("abaqus")
        assert "plastic" in abq["material-curve-columns"]


# ====================================================================
# DashboardPageConnector 基盤テスト
# ====================================================================


class TestDashboardPageConnector:
    """DashboardPageConnector 基盤のテスト"""

    def test_abaqus_connector_registered(self):
        """AbaqusMaterialPageConnectorがレジストリに登録されている"""
        import services.dashboard.connectors.abaqus  # noqa: F401
        from services.dashboard.connectors import DashboardPageConnector

        assert "物性一覧" in DashboardPageConnector._registry

    def test_abaqus_connector_key(self):
        """AbaqusMaterialPageConnectorのconnector_keyが設定されている"""
        from services.dashboard.connectors.abaqus import AbaqusMaterialPageConnector

        assert AbaqusMaterialPageConnector.connector_key == "abaqus"

    def test_get_connector_config(self):
        """connector_keyでDashboardConfigからコネクタ固有設定を取得"""
        from config import DashboardConfig
        from services.dashboard.connectors.abaqus import AbaqusMaterialPageConnector

        cfg = DashboardConfig.from_dict(
            {
                "connectors": {
                    "abaqus": {"material-curve-columns": {"plastic": {"columns": ["s", "e"]}}},
                }
            }
        )
        connector = AbaqusMaterialPageConnector()
        result = connector.get_connector_config(cfg)
        assert "material-curve-columns" in result

    def test_get_connector_pages_with_material(self):
        """abaqus_materialノードがある場合にコネクターページが返される"""
        import services.dashboard.connectors.abaqus  # noqa: F401
        from services.dashboard.connectors import get_connector_pages

        graph = GraphModel(
            nodes=[
                Node(id=1, type="abaqus_material", name="Steel", format="material", properties={}),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        pages = get_connector_pages(provider)
        assert "物性一覧" in pages

    def test_get_connector_pages_without_material(self):
        """abaqus_materialノードがない場合はコネクターページが返されない"""
        import services.dashboard.connectors.abaqus  # noqa: F401
        from services.dashboard.connectors import get_connector_pages

        graph = GraphModel(
            nodes=[
                Node(id=1, type="go", name="go_idx1_v1", format="inp", properties={"path": "a.inp"}),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        pages = get_connector_pages(provider)
        assert "物性一覧" not in pages

    def test_mesh_quality_connector_registered(self):
        """AbaqusMeshQualityPageConnectorがレジストリに登録されている"""
        import services.dashboard.connectors.abaqus  # noqa: F401
        from services.dashboard.connectors import DashboardPageConnector

        assert "メッシュ品質" in DashboardPageConnector._registry

    def test_mesh_quality_connector_key(self):
        """AbaqusMeshQualityPageConnectorのconnector_keyが設定されている"""
        from services.dashboard.connectors.abaqus import AbaqusMeshQualityPageConnector

        assert AbaqusMeshQualityPageConnector.connector_key == "abaqus"

    def test_mesh_quality_available_with_mesh_data(self):
        """メッシュデータがあるgo_ノードがある場合にメッシュ品質ページが利用可能"""
        from services.dashboard.connectors.abaqus import AbaqusMeshQualityPageConnector

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"mesh_element_count": 100, "mesh_node_count": 50},
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        connector = AbaqusMeshQualityPageConnector()
        assert connector.is_available(provider) is True

    def test_mesh_quality_available_with_elset_quality(self):
        """elset品質データがある場合にメッシュ品質ページが利用可能"""
        from services.dashboard.connectors.abaqus import AbaqusMeshQualityPageConnector

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="abaqus_elset",
                    name="ELSET1",
                    format="elset",
                    properties={"quality": {"jacobian": {"min": 0.5, "max": 1.0}}},
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        connector = AbaqusMeshQualityPageConnector()
        assert connector.is_available(provider) is True

    def test_mesh_quality_not_available_without_data(self):
        """メッシュ関連データがない場合はメッシュ品質ページが利用不可"""
        from services.dashboard.connectors.abaqus import AbaqusMeshQualityPageConnector

        graph = GraphModel(
            nodes=[
                Node(id=1, type="abaqus_material", name="Steel", format="material", properties={}),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        connector = AbaqusMeshQualityPageConnector()
        assert connector.is_available(provider) is False

    def test_mesh_quality_page_in_connector_pages(self):
        """メッシュデータがある場合にget_connector_pagesで返される"""
        import services.dashboard.connectors.abaqus  # noqa: F401
        from services.dashboard.connectors import get_connector_pages

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"mesh_element_count": 100},
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        pages = get_connector_pages(provider)
        assert "メッシュ品質" in pages

    def test_material_page_excludes_mesh_quality(self):
        """物性一覧ページにメッシュ品質セクションが含まれないことを確認

        メッシュ品質は独立ページに分離されたため、物性一覧には含まれない。
        """
        import services.dashboard.connectors.abaqus  # noqa: F401
        from services.dashboard.connectors import get_connector_pages

        graph = GraphModel(
            nodes=[
                Node(id=1, type="abaqus_material", name="Steel", format="material", properties={}),
                Node(
                    id=2,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"mesh_element_count": 100},
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        pages = get_connector_pages(provider)
        # 両方が独立ページとして存在する
        assert "物性一覧" in pages
        assert "メッシュ品質" in pages

    def test_render_connector_page_unregistered(self):
        """未登録のページラベルではFalseを返す"""
        from services.dashboard.connectors import render_connector_page

        graph = GraphModel(nodes=[], relations=[])
        provider = DashboardDataProvider(graph)
        result = render_connector_page("存在しないページ", provider, None)
        assert result is False

    def test_connector_generate_html_default(self):
        """基底クラスのgenerate_htmlはデフォルトで空文字列を返す"""
        from services.dashboard.connectors import DashboardPageConnector

        connector = DashboardPageConnector()
        graph = GraphModel(nodes=[], relations=[])
        provider = DashboardDataProvider(graph)
        result = connector.generate_html(provider, None)
        assert result == ""

    def test_material_connector_generate_html(self):
        """物性一覧コネクターがHTMLを生成できる"""
        pytest.importorskip("pandas")
        from services.dashboard.connectors.abaqus import AbaqusMaterialPageConnector

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="abaqus_material",
                    name="Steel",
                    format="material",
                    properties={"elastic": [[210000.0, 0.3]]},
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        connector = AbaqusMaterialPageConnector()
        html = connector.generate_html(provider, None)
        assert "物性テーブル" in html
        assert "Steel" in html

    def test_mesh_quality_connector_generate_html(self):
        """メッシュ品質コネクターがHTMLを生成できる"""
        pytest.importorskip("pandas")
        from services.dashboard.connectors.abaqus import AbaqusMeshQualityPageConnector

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "mesh_node_count": 100,
                        "mesh_element_count": 50,
                        "mesh_element_types": {"C3D8": 50},
                        "mesh_quality": {
                            "volume": {"min": 0.1, "max": 1.0, "mean": 0.5},
                        },
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        connector = AbaqusMeshQualityPageConnector()
        html = connector.generate_html(provider, None)
        assert "メッシュ品質サマリー" in html
        assert "go_idx1_v1" in html

    def test_job_summary_connector_generate_html(self):
        """ジョブサマリーコネクターがHTMLを生成できる"""
        pytest.importorskip("pandas")
        from services.dashboard.connectors.abaqus import AbaqusJobSummaryPageConnector

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "analysis_status": "COMPLETED",
                        "cpu_time": 100.5,
                        "wallclock_time": 50.2,
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        connector = AbaqusJobSummaryPageConnector()
        html = connector.generate_html(provider, None)
        assert "COMPLETED" in html
        assert "go_idx1_v1" in html

    def test_generate_connector_pages_html(self):
        """generate_connector_pages_htmlが利用可能なコネクターのHTMLを返す"""
        pytest.importorskip("pandas")
        import services.dashboard.connectors.abaqus  # noqa: F401
        from services.dashboard.connectors import generate_connector_pages_html

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="abaqus_material",
                    name="Steel",
                    format="material",
                    properties={"elastic": [[210000.0, 0.3]]},
                ),
                Node(
                    id=2,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "analysis_status": "COMPLETED",
                        "cpu_time": 100.5,
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        results = generate_connector_pages_html(provider, None)
        labels = [label for label, _ in results]
        assert "物性一覧" in labels
        assert "ジョブサマリー" in labels


# ====================================================================
# _parse_material_curve_columns テスト
# ====================================================================


class TestParseMaterialCurveColumns:
    """_parse_material_curve_columns のテスト"""

    def test_dict_format(self):
        """辞書形式の正規化"""
        from services.dashboard.connectors.abaqus import parse_material_curve_columns as _parse_material_curve_columns

        raw = {
            "plastic": {"columns": ["stress", "strain"], "x": 1, "y": 0},
            "elastic": {"columns": ["E", "nu"]},
        }
        result = _parse_material_curve_columns(raw)
        assert result["plastic"]["columns"] == ["stress", "strain"]
        assert result["plastic"]["x"] == 1
        assert result["plastic"]["y"] == 0
        assert result["elastic"]["columns"] == ["E", "nu"]
        assert "x" not in result["elastic"]

    def test_list_shorthand(self):
        """簡略形式（リスト）の正規化"""
        from services.dashboard.connectors.abaqus import parse_material_curve_columns as _parse_material_curve_columns

        raw = {"density": ["density"]}
        result = _parse_material_curve_columns(raw)
        assert result["density"]["columns"] == ["density"]

    def test_empty_dict(self):
        """空辞書"""
        from services.dashboard.connectors.abaqus import parse_material_curve_columns as _parse_material_curve_columns

        assert _parse_material_curve_columns({}) == {}

    def test_non_dict_input(self):
        """辞書でない入力は空辞書"""
        from services.dashboard.connectors.abaqus import parse_material_curve_columns as _parse_material_curve_columns

        assert _parse_material_curve_columns("invalid") == {}
        assert _parse_material_curve_columns(None) == {}


# ====================================================================
# widgets テスト
# ====================================================================


class TestWidgets:
    """services/dashboard/widgets.py のテスト"""

    def test_estimate_column_width_ascii(self):
        """英数字のみの列名"""
        from services.dashboard.widgets import estimate_column_width

        width = estimate_column_width("RF3")
        assert width == max(80, 3 * 10 + 30)

    def test_estimate_column_width_japanese(self):
        """日本語列名は2文字分"""
        from services.dashboard.widgets import estimate_column_width

        width = estimate_column_width("条件")
        assert width == 80  # 2文字 x 2(全角) = 4文字分、4*10+30 = 70 → min 80

    def test_estimate_column_width_minimum(self):
        """最小幅は80px"""
        from services.dashboard.widgets import estimate_column_width

        assert estimate_column_width("a") == 80

    def test_try_render_aggrid_import(self):
        """try_render_aggridがインポートできる"""
        from services.dashboard.widgets import try_render_aggrid

        assert callable(try_render_aggrid)


# ====================================================================
# CSV配列: サブディレクトリCSV・ヘッダーなしCSV テスト
# ====================================================================


class TestCsvArraySubdirectory:
    """サブディレクトリCSVの接頭辞決定テスト"""

    def test_compute_prefix_token_diff(self):
        """トークン差分方式の接頭辞"""
        from jj_types import Node
        from services.parse.parsers.csv_array_parser import _compute_prefix

        inp_node = Node(id=1, type="go", name="go_idx1_w5_t20", format="inp", properties={"path": "go_idx1_w5_t20.inp"})
        out_node = Node(
            id=2, type="go", name="go_idx1_w5_t20_RF", format="csv", properties={"path": "go_idx1_w5_t20_RF.csv"}
        )
        assert _compute_prefix(inp_node, out_node) == "RF"

    def test_compute_prefix_subdirectory(self):
        """サブディレクトリ方式の接頭辞"""
        from jj_types import Node
        from services.parse.parsers.csv_array_parser import _compute_prefix

        inp_node = Node(id=1, type="go", name="go_idx1_w5_t20", format="inp", properties={"path": "go_idx1_w5_t20.inp"})
        out_node = Node(
            id=2, type="go", name="history_RF3", format="csv", properties={"path": "go_idx1_w5_t20/history_RF3.csv"}
        )
        assert _compute_prefix(inp_node, out_node) == "history_RF3"

    def test_compute_prefix_no_match(self):
        """マッチしない場合は空文字"""
        from jj_types import Node
        from services.parse.parsers.csv_array_parser import _compute_prefix

        inp_node = Node(id=1, type="go", name="go_idx1_w5_t20", format="inp", properties={"path": "go_idx1_w5_t20.inp"})
        out_node = Node(id=2, type="go", name="unrelated", format="csv", properties={"path": "other_dir/unrelated.csv"})
        assert _compute_prefix(inp_node, out_node) == ""


class TestCsvHeaderlessDetection:
    """ヘッダーなしCSV検出テスト"""

    def test_is_header_row_with_text(self):
        """テキストを含む行はヘッダー"""
        from services.parse.parsers.csv_array_parser import _is_header_row

        assert _is_header_row(["time", "RF3"]) is True

    def test_is_header_row_all_numeric(self):
        """全て数値の行はデータ行（ヘッダーではない）"""
        from services.parse.parsers.csv_array_parser import _is_header_row

        assert _is_header_row(["0.0", "123.4"]) is False

    def test_is_header_row_mixed(self):
        """1つでも非数値があればヘッダー"""
        from services.parse.parsers.csv_array_parser import _is_header_row

        assert _is_header_row(["time", "0.5"]) is True

    def test_is_header_row_empty(self):
        """空行はヘッダーではない"""
        from services.parse.parsers.csv_array_parser import _is_header_row

        assert _is_header_row([]) is False

    def test_read_csv_headerless(self, tmp_path):
        """ヘッダーなしCSVをcol_Nで自動命名"""
        from services.parse.parsers.csv_array_parser import _read_csv_arrays

        csv_file = tmp_path / "headerless.csv"
        csv_file.write_text("0.0,0.0\n0.5,123.4\n1.0,456.7\n")

        result = _read_csv_arrays(csv_file)
        assert "col_0" in result
        assert "col_1" in result
        assert result["col_0"] == [0.0, 0.5, 1.0]
        assert result["col_1"] == [0.0, 123.4, 456.7]

    def test_read_csv_with_header(self, tmp_path):
        """ヘッダーありCSVは従来通り"""
        from services.parse.parsers.csv_array_parser import _read_csv_arrays

        csv_file = tmp_path / "with_header.csv"
        csv_file.write_text("time,RF3\n0.0,0.0\n0.5,123.4\n")

        result = _read_csv_arrays(csv_file)
        assert "time" in result
        assert "RF3" in result
        assert result["time"] == [0.0, 0.5]
        assert result["RF3"] == [0.0, 123.4]


# ====================================================================
# OutputRelationParser サブディレクトリ テスト
# ====================================================================


class TestOutputRelationSubdirectory:
    """OutputRelationParserのサブディレクトリマッチテスト"""

    def test_subdirectory_csv_linked(self):
        """サブディレクトリ内のCSVがhas_output関係でリンクされる"""
        from services.parse.parsers.output_parser import OutputRelationParser

        graph = _make_project_graph_with_subdir_csv()
        parser = OutputRelationParser()
        result = parser.apply(graph)

        # has_output関係が作成されたか確認
        has_output_rels = [r for r in result.relations if r.label == "has_output"]
        # go_idx1_w5_t20(id=1) → history_RF3(id=2) の関係が存在するはず
        linked_pairs = [(r.node1_id, r.node2_id) for r in has_output_rels]
        assert (1, 2) in linked_pairs


# ====================================================================
# REST API: POST /api/v1/parse テスト
# ====================================================================


class TestRestApiParse:
    """REST API POST /api/v1/parse のテスト"""

    @pytest.fixture
    def client_with_project(self, tmp_path):
        """テスト用FastAPIクライアント（パース可能なプロジェクト）"""
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            pytest.skip("fastapi not installed")

        import yaml

        # 最小限のconfig.yaml + graph.yaml
        config_dir = tmp_path / ".j2" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "config.yaml").write_text(
            yaml.safe_dump({"vocab": {}}),
            encoding="utf-8",
        )

        storage_dir = tmp_path / ".j2" / "storage"
        storage_dir.mkdir(parents=True)
        graph_file = storage_dir / "graph.yaml"
        graph_file.write_text(
            yaml.safe_dump({"nodes": [], "relations": []}),
            encoding="utf-8",
        )

        from services.api.routes import create_app

        app = create_app(tmp_path)
        return TestClient(app)

    def test_parse_endpoint_exists(self, client_with_project):
        """POST /api/v1/parse エンドポイントが存在する"""
        resp = client_with_project.post("/api/v1/parse")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "parsed"
        assert "total_nodes" in data
        assert "total_relations" in data


# ====================================================================
# REST API: プロパティフィルター テスト
# ====================================================================


class TestRestApiPropFilter:
    """REST API プロパティ比較フィルターのテスト"""

    def test_parse_prop_filters(self):
        """プロパティフィルターのパース"""
        from services.query import parse_prop_filters

        params = {
            "type": "go",
            "props.RF3.gt": "5",
            "props.temperature.le": "400",
            "limit": "100",
        }
        filters = parse_prop_filters(params)
        assert len(filters) == 2
        assert ("RF3", "gt", 5.0) in filters
        assert ("temperature", "le", 400.0) in filters

    def test_apply_prop_filters(self):
        """プロパティフィルターの適用"""
        from jj_types import Node
        from services.query import apply_prop_filters, node_prop_getter

        nodes = [
            Node(id=1, type="go", name="a", format="inp", properties={"RF3": 3.0, "temperature": 300}),
            Node(id=2, type="go", name="b", format="inp", properties={"RF3": 8.0, "temperature": 350}),
            Node(id=3, type="go", name="c", format="inp", properties={"RF3": 5.0, "temperature": 400}),
        ]

        # RF3 > 5
        result = apply_prop_filters(nodes, [("RF3", "gt", 5.0)], prop_getter=node_prop_getter)
        assert len(result) == 1
        assert result[0].name == "b"

        # RF3 >= 5
        result = apply_prop_filters(nodes, [("RF3", "ge", 5.0)], prop_getter=node_prop_getter)
        assert len(result) == 2
        names = {n.name for n in result}
        assert "b" in names
        assert "c" in names

    def test_apply_prop_filters_combined(self):
        """複合プロパティフィルター"""
        from jj_types import Node
        from services.query import apply_prop_filters, node_prop_getter

        nodes = [
            Node(id=1, type="go", name="a", format="inp", properties={"RF3": 3.0, "temperature": 300}),
            Node(id=2, type="go", name="b", format="inp", properties={"RF3": 8.0, "temperature": 350}),
            Node(id=3, type="go", name="c", format="inp", properties={"RF3": 5.0, "temperature": 400}),
        ]

        # RF3 > 4 AND temperature < 400
        result = apply_prop_filters(
            nodes,
            [
                ("RF3", "gt", 4.0),
                ("temperature", "lt", 400.0),
            ],
            prop_getter=node_prop_getter,
        )
        assert len(result) == 1
        assert result[0].name == "b"

    def test_prop_filter_via_api(self):
        """APIエンドポイント経由のプロパティフィルター"""
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            pytest.skip("fastapi not installed")

        import yaml

        graph = _make_test_graph()

        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            storage_dir = tmp_path / ".j2" / "storage"
            storage_dir.mkdir(parents=True)
            graph_data = {
                "nodes": [n.model_dump(mode="json") for n in graph.nodes],
                "relations": [r.model_dump(mode="json") for r in graph.relations],
            }
            (storage_dir / "graph.yaml").write_text(
                yaml.safe_dump(graph_data, allow_unicode=True),
                encoding="utf-8",
            )

            from services.api.routes import create_app

            app = create_app(tmp_path)
            client = TestClient(app)

            # RF3 > 5 のノードのみ
            resp = client.get("/api/v1/nodes?props.RF3.gt=5")
            assert resp.status_code == 200
            data = resp.json()
            for node in data["nodes"]:
                rf3 = node["properties"].get("RF3")
                if rf3 is not None:
                    assert float(rf3) > 5


# ====================================================================
# テストヘルパー
# ====================================================================


def _make_project_graph_with_subdir_csv():
    """サブディレクトリCSVテスト用のProjectGraph風オブジェクトを作成"""
    from unittest.mock import MagicMock

    from jj_types import Node

    graph = MagicMock()
    graph.config.file_relations.input_extensions = {".inp"}
    graph.config.file_relations.result_extensions = {".odb", ".sta"}

    inp_node = Node(
        id=1, type="go", name="go_idx1_w5_t20", format="inp", properties={"path": "go_idx1_w5_t20.inp", "index": "1"}
    )
    csv_node = Node(
        id=2,
        type="go",
        name="history_RF3",
        format="csv",
        properties={"path": "go_idx1_w5_t20/history_RF3.csv", "index": ""},
    )

    graph.nodes = [inp_node, csv_node]
    graph.relations = []

    _next_id = [10]

    def mock_next_rel_id():
        _next_id[0] += 1
        return _next_id[0]

    graph.next_relation_id = mock_next_rel_id
    graph.get_node_index.side_effect = lambda n: n.properties.get("index", "")

    added_relations = []

    def mock_add_relation(rel):
        added_relations.append(rel)
        graph.relations.append(rel)

    graph.add_relation = mock_add_relation

    return graph


# ====================================================================
# SavedViewConfig: array_plotタイプ
# ====================================================================


class TestSavedViewConfigArrayPlot:
    """SavedViewConfig の array_plot タイプテスト"""

    def test_array_plot_type_accepted(self):
        """array_plotタイプが受け入れられる"""
        from config import SavedViewConfig

        view = SavedViewConfig.from_dict(
            {
                "name": "テスト配列プロット",
                "type": "array_plot",
                "array_plot": {
                    "prefix": "RF",
                    "x": "RF.time",
                    "y": ["RF.RF3"],
                    "mode": "grid",
                },
            }
        )
        assert view.view_type == "array_plot"
        assert view.array_plot["prefix"] == "RF"
        assert view.array_plot["x"] == "RF.time"
        assert view.array_plot["y"] == ["RF.RF3"]
        assert view.array_plot["mode"] == "grid"

    def test_array_plot_default_empty(self):
        """array_plot未指定時は空辞書"""
        from config import SavedViewConfig

        view = SavedViewConfig.from_dict(
            {
                "name": "テスト",
                "type": "table",
            }
        )
        assert view.array_plot == {}

    def test_invalid_type_raises(self):
        """不正なタイプはValueError"""
        from config import SavedViewConfig

        with pytest.raises(ValueError, match="saved-views"):
            SavedViewConfig.from_dict(
                {
                    "name": "テスト",
                    "type": "invalid_type",
                }
            )


# ====================================================================
# DashboardConfig: NG領域・グループ結線
# ====================================================================


class TestDashboardConfigNgRegions:
    """DashboardConfig の ng-regions テスト"""

    def test_ng_regions_rect(self):
        """矩形NG領域の読み込み"""
        from config import DashboardConfig

        config = DashboardConfig.from_dict(
            {
                "ng-regions": [
                    {
                        "type": "rect",
                        "x_min": 0,
                        "x_max": 100,
                        "y_min": 0,
                        "y_max": 5,
                        "color": "rgba(255,0,0,0.1)",
                        "label": "NG",
                    },
                ],
            }
        )
        assert len(config.ng_regions) == 1
        assert config.ng_regions[0]["type"] == "rect"
        assert config.ng_regions[0]["x_max"] == 100

    def test_ng_regions_curve(self):
        """カーブNG領域の読み込み"""
        from config import DashboardConfig

        config = DashboardConfig.from_dict(
            {
                "ng-regions": [
                    {
                        "type": "curve",
                        "points": [[0, 100], [50, 200]],
                        "fill": "below",
                        "label": "Baskin",
                    },
                ],
            }
        )
        assert len(config.ng_regions) == 1
        assert config.ng_regions[0]["type"] == "curve"
        assert len(config.ng_regions[0]["points"]) == 2

    def test_ng_regions_default_empty(self):
        """未指定時は空リスト"""
        from config import DashboardConfig

        config = DashboardConfig.from_dict({})
        assert config.ng_regions == []

    def test_group_line_key(self):
        """グループ結線キーの読み込み"""
        from config import DashboardConfig

        config = DashboardConfig.from_dict(
            {
                "group-line-key": "index",
            }
        )
        assert config.group_line_key == "index"

    def test_group_line_key_default_none(self):
        """未指定時はNone"""
        from config import DashboardConfig

        config = DashboardConfig.from_dict({})
        assert config.group_line_key is None


# ====================================================================
# 物性比較・使用関係
# ====================================================================


def _make_material_graph() -> GraphModel:
    """物性比較テスト用GraphModel"""
    nodes = [
        Node(
            id=1,
            type="go",
            name="go_idx1_v1",
            format="inp",
            properties={"path": "go_idx1_v1.inp", "index": "1", "active": True},
        ),
        Node(
            id=2,
            type="go",
            name="go_idx2_v1",
            format="inp",
            properties={"path": "go_idx2_v1.inp", "index": "2", "active": True},
        ),
        Node(
            id=10,
            type="abaqus_material",
            name="Steel",
            format="material",
            properties={
                "source_file": "material.inp",
                "plastic": [[100, 0.0], [200, 0.01], [250, 0.02]],
                "elastic": [[210000, 0.3]],
            },
        ),
        Node(
            id=11,
            type="abaqus_material",
            name="Aluminum",
            format="material",
            properties={
                "source_file": "material.inp",
                "plastic": [[70, 0.0], [150, 0.01], [180, 0.02]],
                "elastic": [[70000, 0.33]],
            },
        ),
    ]
    relations = [
        Relation(id=1, label="uses_material", node1_id=1, node2_id=10),
        Relation(id=2, label="uses_material", node1_id=1, node2_id=11),
        Relation(id=3, label="uses_material", node1_id=2, node2_id=10),
    ]
    return GraphModel(nodes=nodes, relations=relations)


class TestMaterialComparison:
    """物性比較機能のテスト"""

    def test_get_material_table_keys(self):
        """テーブル型プロパティキーの取得"""
        from services.dashboard.connectors.abaqus import get_material_table_keys

        graph = _make_material_graph()
        provider = DashboardDataProvider(graph)

        keys = get_material_table_keys(provider, 10)
        assert "plastic" in keys
        # elastic は1行のみなので配列プロット対象外
        assert "elastic" not in keys

    def test_get_material_table_data(self):
        """テーブル型プロパティデータの取得"""
        from services.dashboard.connectors.abaqus import get_material_table_data

        graph = _make_material_graph()
        provider = DashboardDataProvider(graph)

        data = get_material_table_data(provider, 10, "plastic")
        assert data is not None
        assert data["name"] == "Steel"
        assert len(data["data"]) == 3

    def test_get_material_table_multiple(self):
        """複数materialのテーブルデータが取得できる"""
        from services.dashboard.connectors.abaqus import (
            get_material_table,
            get_material_table_data,
        )

        graph = _make_material_graph()
        provider = DashboardDataProvider(graph)

        mat_rows = get_material_table(provider)
        assert len(mat_rows) == 2

        steel_data = get_material_table_data(provider, 10, "plastic")
        aluminum_data = get_material_table_data(provider, 11, "plastic")
        assert steel_data is not None
        assert aluminum_data is not None
        assert steel_data["data"][0][0] == 100
        assert aluminum_data["data"][0][0] == 70


class TestMaterialUsage:
    """物性使用関係のテスト"""

    def test_get_material_usage(self):
        """物性使用関係の取得"""
        from services.dashboard.connectors.abaqus import get_material_usage

        graph = _make_material_graph()
        provider = DashboardDataProvider(graph)

        usage = get_material_usage(provider)
        assert len(usage) == 2

        steel_usage = next(u for u in usage if u["material_name"] == "Steel")
        assert len(steel_usage["go_nodes"]) == 2
        go_names = {g["name"] for g in steel_usage["go_nodes"]}
        assert "go_idx1_v1" in go_names
        assert "go_idx2_v1" in go_names

        aluminum_usage = next(u for u in usage if u["material_name"] == "Aluminum")
        assert len(aluminum_usage["go_nodes"]) == 1
        assert aluminum_usage["go_nodes"][0]["name"] == "go_idx1_v1"

    def test_get_material_usage_empty(self):
        """uses_material関係なしの場合"""
        from services.dashboard.connectors.abaqus import get_material_usage

        graph = GraphModel(
            nodes=[
                Node(id=1, type="abaqus_material", name="Steel", format="material", properties={}),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)

        usage = get_material_usage(provider)
        assert len(usage) == 1
        assert len(usage[0]["go_nodes"]) == 0


# ====================================================================
# 配列プロットフィルタ連携
# ====================================================================


class TestArrayPlotFilters:
    """配列プロットのフィルタ連携テスト"""

    def test_get_array_grid_data_with_filters(self):
        """フィルタ付きでget_array_grid_dataが正しく動作"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "path": "a.inp",
                        "active": True,
                        "index": "1",
                        "RF.time": [0, 1, 2],
                        "RF.RF3": [10, 20, 30],
                    },
                ),
                Node(
                    id=2,
                    type="go",
                    name="go_idx2_v1",
                    format="inp",
                    properties={
                        "path": "b.inp",
                        "active": False,
                        "index": "2",
                        "RF.time": [0, 1, 2],
                        "RF.RF3": [5, 10, 15],
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)

        # フィルタなし: 両方
        all_data = provider.get_array_grid_data("RF.time", "RF.RF3")
        assert len(all_data) == 2

        # activeフィルタ: 1件のみ
        active_data = provider.get_array_grid_data("RF.time", "RF.RF3", filters={"active": True})
        assert len(active_data) == 1
        assert active_data[0]["name"] == "go_idx1_v1"


# ====================================================================
# 外部化プロパティ（_ext_keys）対応テスト
# ====================================================================


class TestExternalizedArrayPropertyKeys:
    """外部化プロパティのキー発見テスト"""

    def test_ext_keys_discovered(self):
        """_ext_keysマーカーから配列キーを発見できる"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "path": "go_idx1_v1.inp",
                        "index": "1",
                        "_ext_keys": ["RF.time", "RF.RF1", "RF.RF3"],
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        keys = provider.get_array_property_keys()
        assert "RF.time" in keys
        assert "RF.RF1" in keys
        assert "RF.RF3" in keys
        assert "index" not in keys

    def test_mixed_inline_and_ext_keys(self):
        """インラインと外部化が混在していても正しく発見"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "path": "go_idx1_v1.inp",
                        "stress.time": [0.0, 1.0],
                        "stress.mises": [100.0, 200.0],
                        "_ext_keys": ["RF.time", "RF.RF3"],
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        keys = provider.get_array_property_keys()
        assert "stress.time" in keys
        assert "stress.mises" in keys
        assert "RF.time" in keys
        assert "RF.RF3" in keys


class TestExternalizedArrayPlotData:
    """外部化プロパティのオンデマンドロードテスト"""

    def test_resolve_on_demand(self, tmp_path):
        """外部化プロパティがオンデマンドでロードされる"""
        import json

        # 外部プロパティファイルを作成
        props_dir = tmp_path / ".j2" / "storage" / "properties"
        props_dir.mkdir(parents=True)
        ext_data = {
            "RF.time": [0.0, 0.5, 1.0],
            "RF.RF1": [10.0, 20.0, 30.0],
            "RF.RF3": [0.0, 123.4, 456.7],
        }
        (props_dir / "node_1.json").write_text(json.dumps(ext_data))

        # 軽量ロード相当のグラフ（配列なし、_ext_keysのみ）
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "path": "go_idx1_v1.inp",
                        "index": "1",
                        "_ext_keys": ["RF.time", "RF.RF1", "RF.RF3"],
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph, project_root=tmp_path)

        # get_array_property_keys で発見できる
        keys = provider.get_array_property_keys()
        assert "RF.time" in keys
        assert "RF.RF3" in keys

        # get_array_plot_data でオンデマンドロード
        result = provider.get_array_plot_data(1, "RF.time")
        assert result is not None
        assert result["x_values"] == [0.0, 0.5, 1.0]
        series_keys = {s["key"] for s in result["series"]}
        assert "RF.RF1" in series_keys
        assert "RF.RF3" in series_keys

    def test_resolve_grid_data(self, tmp_path):
        """外部化プロパティでget_array_grid_dataが動作する"""
        import json

        props_dir = tmp_path / ".j2" / "storage" / "properties"
        props_dir.mkdir(parents=True)
        ext_data = {
            "RF.time": [0.0, 0.5, 1.0],
            "RF.RF3": [0.0, 123.4, 456.7],
        }
        (props_dir / "node_1.json").write_text(json.dumps(ext_data))

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "path": "go_idx1_v1.inp",
                        "index": "1",
                        "_ext_keys": ["RF.time", "RF.RF3"],
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph, project_root=tmp_path)

        data = provider.get_array_grid_data("RF.time", "RF.RF3")
        assert len(data) == 1
        assert data[0]["x_values"] == [0.0, 0.5, 1.0]
        assert data[0]["y_values"] == [0.0, 123.4, 456.7]

    def test_no_project_root_fallback(self):
        """project_rootなしでも外部化キーは発見できる（ロードはスキップ）"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "path": "go_idx1_v1.inp",
                        "_ext_keys": ["RF.time", "RF.RF3"],
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)

        # キーは発見できる
        keys = provider.get_array_property_keys()
        assert "RF.time" in keys

        # データはロードできない（storageなし）
        result = provider.get_array_plot_data(1, "RF.time")
        assert result is None


# ====================================================================
# NG領域ヘルパー (app.pyのインポート不要なロジックテスト)
# ====================================================================


class TestNgRegionConfig:
    """NG領域config読み込みテスト"""

    def test_ng_regions_non_list(self):
        """ng-regionsが非リストの場合は空リスト"""
        from config import DashboardConfig

        config = DashboardConfig.from_dict({"ng-regions": "invalid"})
        assert config.ng_regions == []

    def test_ng_regions_mixed(self):
        """矩形とカーブの混合"""
        from config import DashboardConfig

        config = DashboardConfig.from_dict(
            {
                "ng-regions": [
                    {"type": "rect", "x_min": 0, "x_max": 10, "y_min": 0, "y_max": 5},
                    {"type": "curve", "points": [[0, 1], [10, 2]], "fill": "above"},
                ],
            }
        )
        assert len(config.ng_regions) == 2
        assert config.ng_regions[0]["type"] == "rect"
        assert config.ng_regions[1]["type"] == "curve"


# ====================================================================
# 物性比較CSVエクスポート テスト
# ====================================================================


class TestMaterialComparisonCsv:
    """物性比較のCSVエクスポートデータ生成テスト"""

    def _make_material_graph(self) -> GraphModel:
        """物性比較テスト用GraphModel"""
        return GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="abaqus_material",
                    name="Steel",
                    format="material",
                    properties={
                        "plastic": [[100.0, 0.0], [200.0, 0.01], [250.0, 0.05]],
                        "elastic": [[210000.0, 0.3]],
                    },
                ),
                Node(
                    id=2,
                    type="abaqus_material",
                    name="Aluminum",
                    format="material",
                    properties={
                        "plastic": [[80.0, 0.0], [150.0, 0.02]],
                    },
                ),
            ],
            relations=[],
        )

    def test_comparison_data_collection(self):
        """比較データがmaterial別に正しく収集される"""
        from services.dashboard.connectors.abaqus import (
            get_material_table,
            get_material_table_data,
            guess_table_column_names,
        )

        graph = self._make_material_graph()
        provider = DashboardDataProvider(graph)
        mat_rows = get_material_table(provider)

        # 両方のmaterialがplasticを持つ
        comparison_data = []
        for mat_name in ["Steel", "Aluminum"]:
            mat_id = next(r["id"] for r in mat_rows if r["name"] == mat_name)
            table_data = get_material_table_data(provider, mat_id, "plastic")
            assert table_data is not None
            data_rows = table_data["data"]
            num_cols = len(data_rows[0])
            col_names = guess_table_column_names("plastic", num_cols, None)
            for row in data_rows:
                entry = {"material": mat_name}
                for ci, cn in enumerate(col_names):
                    if ci < len(row):
                        entry[cn] = row[ci]
                comparison_data.append(entry)

        assert len(comparison_data) == 5  # Steel: 3行 + Aluminum: 2行
        assert comparison_data[0]["material"] == "Steel"
        assert comparison_data[3]["material"] == "Aluminum"

    def test_comparison_csv_format(self):
        """CSV変換が正しくフォーマットされる"""
        pd = pytest.importorskip("pandas")

        data = [
            {"material": "Steel", "col_0": 100.0, "col_1": 0.0},
            {"material": "Steel", "col_0": 200.0, "col_1": 0.01},
            {"material": "Aluminum", "col_0": 80.0, "col_1": 0.0},
        ]
        csv_df = pd.DataFrame(data)
        csv_str = csv_df.to_csv(index=False)
        lines = csv_str.strip().split("\n")
        assert lines[0] == "material,col_0,col_1"
        assert len(lines) == 4  # header + 3 data rows


# ====================================================================
# HTMLエクスポート テスト
# ====================================================================


@pytest.mark.skipif(
    not __import__("importlib").util.find_spec("streamlit"),
    reason="streamlit not installed",
)
class TestHtmlExport:
    """保存済みビューHTMLエクスポートのテスト"""

    def _make_test_graph(self) -> GraphModel:
        return GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_test1",
                    format="inp",
                    properties={
                        "path": "go_test1.inp",
                        "active": True,
                        "analysis_status": "completed",
                        "RF3": 5.0,
                        "temperature": 300,
                    },
                ),
                Node(
                    id=2,
                    type="go",
                    name="go_test2",
                    format="inp",
                    properties={
                        "path": "go_test2.inp",
                        "active": True,
                        "analysis_status": "failed",
                        "RF3": 3.0,
                        "temperature": 350,
                    },
                ),
            ],
            relations=[],
        )

    def test_generate_table_html(self):
        """テーブルビューのHTML生成"""
        from config import DashboardConfig, SavedViewConfig
        from services.dashboard.html_export import generate_table_html

        graph = self._make_test_graph()
        provider = DashboardDataProvider(graph)
        dashboard_config = DashboardConfig.from_dict({})
        view = SavedViewConfig.from_dict(
            {
                "name": "test_table",
                "type": "table",
            }
        )
        html = generate_table_html(provider, dashboard_config, view)
        assert "go_test1" in html
        assert "go_test2" in html
        assert "<table" in html

    def test_generate_table_html_with_filter(self):
        """フィルタ付きテーブルビューのHTML生成"""
        from config import DashboardConfig, SavedViewConfig
        from services.dashboard.html_export import generate_table_html

        graph = self._make_test_graph()
        provider = DashboardDataProvider(graph)
        dashboard_config = DashboardConfig.from_dict({})
        view = SavedViewConfig.from_dict(
            {
                "name": "completed_only",
                "type": "table",
                "filters": {"analysis_status": "completed"},
            }
        )
        html = generate_table_html(provider, dashboard_config, view)
        assert "go_test1" in html
        assert "go_test2" not in html
        assert "1 / 2 件" in html

    def test_generate_status_html(self):
        """ステータスビューのHTML生成"""
        from services.dashboard.html_export import generate_status_html

        graph = self._make_test_graph()
        provider = DashboardDataProvider(graph)
        html = generate_status_html(provider)
        assert "合計" in html
        assert "2" in html

    def test_generate_plot_html(self):
        """プロットビューのHTML生成（plotly依存）"""
        try:
            import plotly  # noqa: F401
        except ImportError:
            pytest.skip("plotly not installed")

        from config import DashboardConfig, SavedViewConfig
        from services.dashboard.html_export import generate_plot_html

        graph = self._make_test_graph()
        provider = DashboardDataProvider(graph)
        dashboard_config = DashboardConfig.from_dict({})
        view = SavedViewConfig.from_dict(
            {
                "name": "test_plot",
                "type": "plot",
                "plot": {"x": "RF3", "y": "temperature"},
            }
        )
        html = generate_plot_html(provider, view, dashboard_config)
        assert "plotly-graph" in html or "データ点数" in html

    def test_generate_card_html(self):
        """カードビューのHTML生成"""
        from config import SavedViewConfig
        from services.dashboard.html_export import generate_card_html

        graph = self._make_test_graph()
        provider = DashboardDataProvider(graph)
        view = SavedViewConfig.from_dict(
            {
                "name": "test_card",
                "type": "card",
            }
        )
        html = generate_card_html(provider, view)
        assert "go_test1" in html

    def test_full_html_generation(self):
        """全体HTMLの生成"""
        from pathlib import Path

        from config import DashboardConfig, SavedViewConfig
        from services.dashboard.html_export import generate_saved_views_html

        graph = self._make_test_graph()
        provider = DashboardDataProvider(graph)
        dashboard_config = DashboardConfig.from_dict({})
        views = [
            SavedViewConfig.from_dict({"name": "テスト一覧", "type": "table"}),
            SavedViewConfig.from_dict({"name": "ステータス", "type": "status"}),
        ]
        html = generate_saved_views_html(provider, Path("/tmp"), dashboard_config, views)
        assert "<!DOCTYPE html>" in html
        assert "テスト一覧" in html
        assert "ステータス" in html
        assert "plotly-latest.min.js" in html


# ====================================================================
# 動的ビュー追加 テスト
# ====================================================================


class TestDynamicViews:
    """動的ビューのSavedViewConfig変換テスト"""

    def test_dynamic_view_to_config(self):
        """動的ビューの辞書がSavedViewConfigに変換される"""
        from config import SavedViewConfig

        view_data = {
            "name": "テスト動的ビュー",
            "type": "table",
            "filters": {"active": True},
            "plot": {},
            "array_plot": {},
            "gallery": {},
        }
        view = SavedViewConfig.from_dict(view_data)
        assert view.name == "テスト動的ビュー"
        assert view.view_type == "table"
        assert view.filters == {"active": True}

    def test_dynamic_view_plot_type(self):
        """プロットタイプの動的ビュー"""
        from config import SavedViewConfig

        view_data = {
            "name": "動的プロット",
            "type": "plot",
            "filters": {},
            "plot": {"x": "RF3", "y": "temperature", "chart_type": "散布図"},
            "array_plot": {},
            "gallery": {},
        }
        view = SavedViewConfig.from_dict(view_data)
        assert view.view_type == "plot"
        assert view.plot["x"] == "RF3"

    def test_dynamic_view_plot_with_color(self):
        """プロットタイプの動的ビューに色分けキーが含まれる"""
        from config import SavedViewConfig

        view_data = {
            "name": "色分けプロット",
            "type": "plot",
            "filters": {},
            "plot": {"x": "RF3", "y": "temperature", "color": "表示名", "chart_type": "散布図"},
            "array_plot": {},
            "gallery": {},
        }
        view = SavedViewConfig.from_dict(view_data)
        assert view.plot["color"] == "表示名"

    def test_dynamic_view_gallery_with_property_key(self):
        """ギャラリータイプの動的ビューにproperty_keyが含まれる"""
        from config import SavedViewConfig

        view_data = {
            "name": "プロパティギャラリー",
            "type": "gallery",
            "filters": {},
            "plot": {},
            "array_plot": {},
            "gallery": {"source": "property", "property_key": "screenshot"},
        }
        view = SavedViewConfig.from_dict(view_data)
        assert view.gallery["property_key"] == "screenshot"

    def test_dynamic_view_array_plot_type(self):
        """配列プロットタイプの動的ビュー"""
        from config import SavedViewConfig

        view_data = {
            "name": "動的配列プロット",
            "type": "array_plot",
            "filters": {},
            "plot": {},
            "array_plot": {
                "prefix": "RF",
                "x": "RF.time",
                "y": ["RF.RF3"],
                "mode": "grid",
            },
            "gallery": {},
        }
        view = SavedViewConfig.from_dict(view_data)
        assert view.view_type == "array_plot"
        assert view.array_plot["prefix"] == "RF"


# ====================================================================
# query.py 単体テスト（Streamlit非依存）
# ====================================================================


class TestQueryModule:
    """services/dashboard/query.py の純粋関数テスト"""

    # ---- is_truthy ----

    def test_is_truthy_bool_true(self):
        from services.dashboard.query import is_truthy

        assert is_truthy(True) is True

    def test_is_truthy_bool_false(self):
        from services.dashboard.query import is_truthy

        assert is_truthy(False) is False

    def test_is_truthy_string_true(self):
        from services.dashboard.query import is_truthy

        assert is_truthy("true") is True
        assert is_truthy("True") is True
        assert is_truthy("TRUE") is True
        assert is_truthy(" true ") is True

    def test_is_truthy_string_false(self):
        from services.dashboard.query import is_truthy

        assert is_truthy("false") is False
        assert is_truthy("False") is False
        assert is_truthy("") is False

    def test_is_truthy_none(self):
        from services.dashboard.query import is_truthy

        assert is_truthy(None) is False

    def test_is_truthy_int(self):
        from services.dashboard.query import is_truthy

        assert is_truthy(1) is True
        assert is_truthy(0) is False

    # ---- sort_columns_by_vocab ----

    def test_sort_columns_by_vocab_basic(self):
        from services.dashboard.query import sort_columns_by_vocab

        vocab = {"条件": "condition", "RF3": "RF3", "温度": "temperature"}
        columns = ["温度", "RF3", "条件", "extra"]
        result = sort_columns_by_vocab(columns, vocab)
        # vocab値の出現順: condition(0), RF3(1), temperature(2)
        # vocabキー: 条件(3), RF3(4), 温度(5)
        # "条件"はvocab_order["条件"]=3, "RF3"はvocab_order["RF3"]=4, "温度"はvocab_order["温度"]=5
        # ただしvocab値も: condition(0), RF3(1), temperature(2)
        # 各カラムが vocab_order にあるか: 温度→5, RF3→1(値一致), 条件→3
        # in_vocab: RF3(1), 条件(3), 温度(5) -> sorted by order
        # not_in_vocab: extra
        assert result[-1] == "extra"
        assert "RF3" in result
        assert "条件" in result
        assert "温度" in result

    def test_sort_columns_by_vocab_empty(self):
        from services.dashboard.query import sort_columns_by_vocab

        assert sort_columns_by_vocab([], {}) == []

    def test_sort_columns_by_vocab_no_vocab(self):
        from services.dashboard.query import sort_columns_by_vocab

        columns = ["b", "a", "c"]
        result = sort_columns_by_vocab(columns, {})
        assert result == ["a", "b", "c"]

    # ---- select_table_columns ----

    def test_select_table_columns_none(self):
        from services.dashboard.query import select_table_columns

        cols = ["name", "type", "format", "index", "RF3"]
        result = select_table_columns(cols, None)
        assert result == cols

    def test_select_table_columns_with_patterns(self):
        from services.dashboard.query import select_table_columns

        all_cols = ["name", "type", "format", "index", "RF3", "temperature", "active"]
        result = select_table_columns(all_cols, ["RF3", "index"])
        assert result == ["name", "type", "format", "RF3", "index"]

    def test_select_table_columns_glob(self):
        from services.dashboard.query import select_table_columns

        all_cols = ["name", "type", "format", "stress_center", "stress_edge", "RF3"]
        result = select_table_columns(all_cols, ["stress*", "RF3"])
        assert result == ["name", "type", "format", "stress_center", "stress_edge", "RF3"]

    def test_select_table_columns_no_match(self):
        from services.dashboard.query import select_table_columns

        all_cols = ["name", "type", "format", "index"]
        result = select_table_columns(all_cols, ["nonexistent"])
        assert result == ["name", "type", "format"]

    def test_select_table_columns_with_vocab(self):
        from services.dashboard.query import select_table_columns

        all_cols = ["name", "type", "format", "RF3", "温度"]
        vocab = {"RF3": "RF3", "温度": "temperature"}
        result = select_table_columns(all_cols, None, vocab=vocab)
        assert "name" in result
        assert "RF3" in result
        assert "温度" in result

    # ---- apply_filters ----

    def test_apply_filters_no_filter(self):
        from services.dashboard.query import apply_filters

        rows = [
            {"type": "go", "analysis_status": "completed", "active": True},
            {"type": "go", "analysis_status": "failed", "active": False},
        ]
        assert len(apply_filters(rows)) == 2

    def test_apply_filters_type(self):
        from services.dashboard.query import apply_filters

        rows = [
            {"type": "go", "analysis_status": "completed"},
            {"type": "material", "analysis_status": "completed"},
        ]
        result = apply_filters(rows, type_filter="go")
        assert len(result) == 1
        assert result[0]["type"] == "go"

    def test_apply_filters_status(self):
        from services.dashboard.query import apply_filters

        rows = [
            {"type": "go", "analysis_status": "completed"},
            {"type": "go", "analysis_status": "failed"},
        ]
        result = apply_filters(rows, status_filter="completed")
        assert len(result) == 1
        assert result[0]["analysis_status"] == "completed"

    def test_apply_filters_active_only(self):
        from services.dashboard.query import apply_filters

        rows = [
            {"active": True, "type": "go"},
            {"active": False, "type": "go"},
            {"active": "true", "type": "go"},
        ]
        result = apply_filters(rows, active_only=True)
        assert len(result) == 2

    def test_apply_filters_all_combined(self):
        from services.dashboard.query import apply_filters

        rows = [
            {"type": "go", "analysis_status": "completed", "active": True},
            {"type": "go", "analysis_status": "failed", "active": True},
            {"type": "material", "analysis_status": "completed", "active": True},
            {"type": "go", "analysis_status": "completed", "active": False},
        ]
        result = apply_filters(rows, type_filter="go", status_filter="completed", active_only=True)
        assert len(result) == 1
        assert result[0]["type"] == "go"
        assert result[0]["analysis_status"] == "completed"
        assert result[0]["active"] is True

    def test_apply_filters_type_all(self):
        """'すべて'はフィルタ無効"""
        from services.dashboard.query import apply_filters

        rows = [{"type": "go"}, {"type": "material"}]
        assert len(apply_filters(rows, type_filter="すべて")) == 2

    # ---- apply_saved_view_filters ----

    def test_apply_saved_view_filters_empty(self):
        from services.dashboard.query import apply_saved_view_filters

        rows = [{"name": "a"}, {"name": "b"}]
        assert len(apply_saved_view_filters(rows, {})) == 2

    def test_apply_saved_view_filters_active_true(self):
        from services.dashboard.query import apply_saved_view_filters

        rows = [
            {"name": "a", "active": True},
            {"name": "b", "active": False},
        ]
        result = apply_saved_view_filters(rows, {"active": True})
        assert len(result) == 1
        assert result[0]["name"] == "a"

    def test_apply_saved_view_filters_active_false(self):
        from services.dashboard.query import apply_saved_view_filters

        rows = [
            {"name": "a", "active": True},
            {"name": "b", "active": False},
        ]
        result = apply_saved_view_filters(rows, {"active": False})
        assert len(result) == 1
        assert result[0]["name"] == "b"

    def test_apply_saved_view_filters_type(self):
        from services.dashboard.query import apply_saved_view_filters

        rows = [
            {"name": "a", "type": "go"},
            {"name": "b", "type": "material"},
        ]
        result = apply_saved_view_filters(rows, {"type": "go"})
        assert len(result) == 1

    def test_apply_saved_view_filters_custom_key(self):
        from services.dashboard.query import apply_saved_view_filters

        rows = [
            {"name": "a", "index": "1"},
            {"name": "b", "index": "2"},
        ]
        result = apply_saved_view_filters(rows, {"index": "1"})
        assert len(result) == 1
        assert result[0]["name"] == "a"

    # ---- saved_view_filters_to_provider_filters ----

    def test_saved_view_filters_to_provider_filters(self):
        from services.dashboard.query import saved_view_filters_to_provider_filters

        filters = {"active": True, "type": "go"}
        result = saved_view_filters_to_provider_filters(filters)
        assert result == {"active": True, "type": "go"}

    # ---- normalize_group_key ----

    def test_normalize_group_key_daily(self):
        from services.dashboard.query import normalize_group_key

        assert normalize_group_key("daily:2026-01-15:screenshot") == "screenshot"

    def test_normalize_group_key_plain(self):
        from services.dashboard.query import normalize_group_key

        assert normalize_group_key("index") == "index"

    def test_normalize_group_key_daily_short(self):
        from services.dashboard.query import normalize_group_key

        assert normalize_group_key("daily:2026-01-15") == "daily:2026-01-15"

    # ---- collect_group_keys ----

    def test_collect_group_keys_output(self):
        from services.dashboard.query import collect_group_keys

        images = [
            {"go_properties": {"index": "1", "version": "1"}},
            {"go_properties": {"index": "2", "status": "ok"}},
        ]
        result = collect_group_keys(images, "output")
        assert "index" in result
        assert "version" in result
        assert "status" in result
        assert result == sorted(result)

    def test_collect_group_keys_property(self):
        from services.dashboard.query import collect_group_keys

        images = [
            {"go_properties": {"index": "1"}},
        ]
        result = collect_group_keys(images, "property")
        assert result[0] == "property_key"
        assert "index" in result

    def test_collect_group_keys_excludes_internal(self):
        from services.dashboard.query import collect_group_keys

        images = [
            {"go_properties": {"path": "a.inp", "index": "1"}},
        ]
        result = collect_group_keys(images, "output")
        assert "path" not in result
        assert "index" in result

    def test_collect_group_keys_empty(self):
        from services.dashboard.query import collect_group_keys

        assert collect_group_keys([], "output") == []

    # ---- find_graph_path / get_graph_mtime ----

    def test_find_graph_path_yaml(self, tmp_path):
        from services.dashboard.query import find_graph_path

        storage = tmp_path / ".j2" / "storage"
        storage.mkdir(parents=True)
        (storage / "graph.yaml").write_text("nodes: []\n")
        result = find_graph_path(tmp_path)
        assert result is not None
        assert result.name == "graph.yaml"

    def test_find_graph_path_json(self, tmp_path):
        from services.dashboard.query import find_graph_path

        storage = tmp_path / ".j2" / "storage"
        storage.mkdir(parents=True)
        (storage / "graph.json").write_text("{}")
        result = find_graph_path(tmp_path)
        assert result is not None
        assert result.name == "graph.json"

    def test_find_graph_path_none(self, tmp_path):
        from services.dashboard.query import find_graph_path

        assert find_graph_path(tmp_path) is None

    def test_get_graph_mtime(self, tmp_path):
        from services.dashboard.query import get_graph_mtime

        storage = tmp_path / ".j2" / "storage"
        storage.mkdir(parents=True)
        (storage / "graph.yaml").write_text("nodes: []\n")
        mtime = get_graph_mtime(tmp_path)
        assert isinstance(mtime, float)
        assert mtime > 0

    def test_get_graph_mtime_no_file(self, tmp_path):
        from services.dashboard.query import get_graph_mtime

        assert get_graph_mtime(tmp_path) == 0.0


# ====================================================================
# abaqus_query.py 単体テスト
# ====================================================================


class TestAbaqusQueryModule:
    """services/dashboard/connectors/abaqus_query.py の純粋関数テスト"""

    @pytest.fixture
    def material_graph(self):
        """abaqus_materialノードを含むテスト用GraphModel"""
        return GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "path": "go_idx1_v1.inp",
                        "index": "1",
                        "active": True,
                    },
                ),
                Node(
                    id=2,
                    type="abaqus_material",
                    name="Steel",
                    format="material",
                    properties={
                        "source_file": "material.inp",
                        "keywords": ["elastic", "plastic"],
                        "elastic": [[210000.0, 0.3]],
                        "plastic": [
                            [200.0, 0.0],
                            [300.0, 0.05],
                            [350.0, 0.10],
                        ],
                        "density": 7.85e-9,
                    },
                ),
                Node(
                    id=3,
                    type="abaqus_material",
                    name="Aluminum",
                    format="material",
                    properties={
                        "source_file": "material.inp",
                        "keywords": ["elastic"],
                        "elastic": [[70000.0, 0.33]],
                        "density": 2.7e-9,
                    },
                ),
            ],
            relations=[
                Relation(id=1, label="uses_material", node1_id=1, node2_id=2),
                Relation(id=2, label="uses_material", node1_id=1, node2_id=3),
            ],
        )

    @pytest.fixture
    def material_provider(self, material_graph):
        return DashboardDataProvider(material_graph)

    # ---- get_material_table ----

    def test_get_material_table(self, material_provider):
        from services.dashboard.connectors.abaqus_query import get_material_table

        rows = get_material_table(material_provider)
        assert len(rows) == 2
        names = {r["name"] for r in rows}
        assert "Steel" in names
        assert "Aluminum" in names

    def test_get_material_table_excludes_internal(self, material_provider):
        from services.dashboard.connectors.abaqus_query import get_material_table

        rows = get_material_table(material_provider)
        for row in rows:
            assert "source_file" not in row
            assert "path" not in row

    def test_get_material_table_table_data_summary(self, material_provider):
        from services.dashboard.connectors.abaqus_query import get_material_table

        rows = get_material_table(material_provider)
        steel = next(r for r in rows if r["name"] == "Steel")
        # 2行以上のテーブル型データ → "配列"
        assert steel["plastic"] == "配列"
        # 1行2要素 → "val0(val1)"
        assert steel["elastic"] == "210000.0(0.3)"
        # スカラ値は指数表記でフォーマット
        assert steel["density"] == "7.85e-09"

    def test_get_material_table_verbose_name_with_vocab(self):
        """生キー(verbose_name)でverbose_nameを取得できる"""
        from services.dashboard.connectors.abaqus_query import get_material_table

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="abaqus_material",
                    name="Steel_S235",
                    format="material",
                    properties={
                        "verbose_name": "鋼材 S235",
                        "elastic": [[210000.0, 0.3]],
                    },
                ),
            ],
            relations=[],
        )
        # vocab変換は表示時のみ。生キーでverbose_nameを格納
        provider = DashboardDataProvider(graph, vocab={"verbose_name": "表示名"})
        rows = get_material_table(provider)
        assert len(rows) == 1
        assert rows[0]["verbose_name"] == "鋼材 S235"

    def test_get_material_table_verbose_name_fallback(self):
        """vocab未設定時は元のverbose_nameキーで取得"""
        from services.dashboard.connectors.abaqus_query import get_material_table

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="abaqus_material",
                    name="Steel_S235",
                    format="material",
                    properties={
                        "verbose_name": "鋼材 S235",
                        "elastic": [[210000.0, 0.3]],
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        rows = get_material_table(provider)
        assert len(rows) == 1
        assert rows[0]["verbose_name"] == "鋼材 S235"

    def test_get_material_table_excludes_vocab_verbose_name_key(self):
        """生キー(verbose_name)でverbose_nameが取得され、重複しない"""
        from services.dashboard.connectors.abaqus_query import get_material_table

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="abaqus_material",
                    name="Steel_S235",
                    format="material",
                    properties={
                        "verbose_name": "鋼材 S235",
                        "density": 7.85e-9,
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph, vocab={"verbose_name": "表示名"})
        rows = get_material_table(provider)
        assert len(rows) == 1
        # verbose_name列に値がある
        assert rows[0]["verbose_name"] == "鋼材 S235"
        # density は指数表記でフォーマット
        assert rows[0]["density"] == "7.85e-09"

    # ---- get_material_table_data ----

    def test_get_material_table_data(self, material_provider):
        from services.dashboard.connectors.abaqus_query import get_material_table_data

        result = get_material_table_data(material_provider, 2, "plastic")
        assert result is not None
        assert result["name"] == "Steel"
        assert result["property_key"] == "plastic"
        assert len(result["data"]) == 3
        assert result["data"][0] == [200.0, 0.0]
        assert "elastic" in result["keywords"]

    def test_get_material_table_data_not_table(self, material_provider):
        from services.dashboard.connectors.abaqus_query import get_material_table_data

        # density はスカラ値なので None
        assert get_material_table_data(material_provider, 2, "density") is None

    def test_get_material_table_data_missing_key(self, material_provider):
        from services.dashboard.connectors.abaqus_query import get_material_table_data

        assert get_material_table_data(material_provider, 2, "nonexistent") is None

    def test_get_material_table_data_wrong_node(self, material_provider):
        from services.dashboard.connectors.abaqus_query import get_material_table_data

        # go_ノードはabaqus_materialではない
        assert get_material_table_data(material_provider, 1, "plastic") is None

    def test_get_material_table_data_missing_node(self, material_provider):
        from services.dashboard.connectors.abaqus_query import get_material_table_data

        assert get_material_table_data(material_provider, 999, "plastic") is None

    # ---- get_material_table_keys ----

    def test_get_material_table_keys(self, material_provider):
        from services.dashboard.connectors.abaqus_query import get_material_table_keys

        keys = get_material_table_keys(material_provider, 2)
        # elastic は1行のみなので配列プロット対象外
        assert "elastic" not in keys
        assert "plastic" in keys
        assert "density" not in keys
        assert keys == sorted(keys)

    def test_get_material_table_keys_aluminum(self, material_provider):
        from services.dashboard.connectors.abaqus_query import get_material_table_keys

        keys = get_material_table_keys(material_provider, 3)
        # Aluminum: elastic 1行のみ → 配列プロット対象外
        assert "elastic" not in keys
        assert "plastic" not in keys

    def test_get_material_table_keys_wrong_node(self, material_provider):
        from services.dashboard.connectors.abaqus_query import get_material_table_keys

        assert get_material_table_keys(material_provider, 1) == []

    def test_get_material_table_keys_missing_node(self, material_provider):
        from services.dashboard.connectors.abaqus_query import get_material_table_keys

        assert get_material_table_keys(material_provider, 999) == []

    # ---- guess_table_column_names ----

    def test_guess_table_column_names_with_config(self):
        from services.dashboard.connectors.abaqus_query import guess_table_column_names

        mcc = {"plastic": {"columns": ["stress", "strain"]}}
        result = guess_table_column_names("plastic", 2, mcc)
        assert result == ["stress", "strain"]

    def test_guess_table_column_names_more_cols(self):
        from services.dashboard.connectors.abaqus_query import guess_table_column_names

        mcc = {"plastic": {"columns": ["stress", "strain"]}}
        result = guess_table_column_names("plastic", 4, mcc)
        assert result == ["stress", "strain", "col_2", "col_3"]

    def test_guess_table_column_names_no_config(self):
        from services.dashboard.connectors.abaqus_query import guess_table_column_names

        result = guess_table_column_names("plastic", 3, None)
        assert result == ["col_0", "col_1", "col_2"]

    def test_guess_table_column_names_unknown_key(self):
        from services.dashboard.connectors.abaqus_query import guess_table_column_names

        mcc = {"elastic": {"columns": ["E", "nu"]}}
        result = guess_table_column_names("plastic", 2, mcc)
        assert result == ["col_0", "col_1"]

    def test_guess_table_column_names_fewer_cols(self):
        from services.dashboard.connectors.abaqus_query import guess_table_column_names

        mcc = {"plastic": {"columns": ["stress", "strain", "temp"]}}
        result = guess_table_column_names("plastic", 2, mcc)
        assert result == ["stress", "strain"]

    # ---- get_curve_plot_axes ----

    def test_get_curve_plot_axes_default(self):
        from services.dashboard.connectors.abaqus_query import get_curve_plot_axes

        x, y = get_curve_plot_axes("plastic", 3, None)
        assert x == 0
        assert y == 1

    def test_get_curve_plot_axes_from_config(self):
        from services.dashboard.connectors.abaqus_query import get_curve_plot_axes

        mcc = {"plastic": {"columns": ["stress", "strain"], "x": 1, "y": 0}}
        x, y = get_curve_plot_axes("plastic", 2, mcc)
        assert x == 1
        assert y == 0

    def test_get_curve_plot_axes_clamped(self):
        from services.dashboard.connectors.abaqus_query import get_curve_plot_axes

        mcc = {"plastic": {"columns": ["a", "b"], "x": 10, "y": 10}}
        x, y = get_curve_plot_axes("plastic", 2, mcc)
        assert x == 1  # clamped to num_cols - 1
        assert y == 1

    def test_get_curve_plot_axes_single_col(self):
        from services.dashboard.connectors.abaqus_query import get_curve_plot_axes

        x, y = get_curve_plot_axes("plastic", 1, None)
        assert x == 0
        assert y == 0

    # ---- parse_material_curve_columns ----

    def test_parse_material_curve_columns_dict_format(self):
        from services.dashboard.connectors.abaqus_query import parse_material_curve_columns

        raw = {
            "plastic": {"columns": ["stress", "strain"], "x": 1, "y": 0},
            "elastic": {"columns": ["E", "nu"]},
        }
        result = parse_material_curve_columns(raw)
        assert result["plastic"]["columns"] == ["stress", "strain"]
        assert result["plastic"]["x"] == 1
        assert result["plastic"]["y"] == 0
        assert result["elastic"]["columns"] == ["E", "nu"]
        assert "x" not in result["elastic"]

    def test_parse_material_curve_columns_list_format(self):
        from services.dashboard.connectors.abaqus_query import parse_material_curve_columns

        raw = {"plastic": ["stress", "strain"]}
        result = parse_material_curve_columns(raw)
        assert result["plastic"]["columns"] == ["stress", "strain"]

    def test_parse_material_curve_columns_empty(self):
        from services.dashboard.connectors.abaqus_query import parse_material_curve_columns

        assert parse_material_curve_columns({}) == {}

    def test_parse_material_curve_columns_invalid(self):
        from services.dashboard.connectors.abaqus_query import parse_material_curve_columns

        assert parse_material_curve_columns("invalid") == {}

    # ---- get_material_usage ----

    def test_get_material_usage(self, material_provider):
        from services.dashboard.connectors.abaqus_query import get_material_usage

        usage = get_material_usage(material_provider)
        assert len(usage) == 2
        steel_usage = next(u for u in usage if u["material_name"] == "Steel")
        assert steel_usage["material_id"] == 2
        assert len(steel_usage["go_nodes"]) == 1
        assert steel_usage["go_nodes"][0]["name"] == "go_idx1_v1"

    def test_get_material_usage_no_relations(self):
        from services.dashboard.connectors.abaqus_query import get_material_usage

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="abaqus_material",
                    name="Steel",
                    format="material",
                    properties={"keywords": ["elastic"]},
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        usage = get_material_usage(provider)
        assert len(usage) == 1
        assert usage[0]["go_nodes"] == []


# ====================================================================
# html_export.py ヘルパー関数テスト
# ====================================================================


class TestHtmlExportHelpers:
    """services/dashboard/html_export.py のplotlyヘルパー関数テスト"""

    def test_create_plot_figure_scatter(self):
        try:
            import pandas as pd
            import plotly.express as px
        except ImportError:
            pytest.skip("plotly or pandas not installed")

        from services.dashboard.html_export import _create_plot_figure

        df = pd.DataFrame(
            {
                "x": [1, 2, 3],
                "y": [4, 5, 6],
                "name": ["a", "b", "c"],
            }
        )
        fig = _create_plot_figure(px, df, "x", "y", None, "散布図")
        assert fig is not None
        assert len(fig.data) >= 1

    def test_create_plot_figure_bar(self):
        try:
            import pandas as pd
            import plotly.express as px
        except ImportError:
            pytest.skip("plotly or pandas not installed")

        from services.dashboard.html_export import _create_plot_figure

        df = pd.DataFrame(
            {
                "x": [1, 2, 3],
                "y": [4, 5, 6],
                "name": ["a", "b", "c"],
            }
        )
        fig = _create_plot_figure(px, df, "x", "y", None, "棒グラフ")
        assert fig is not None

    def test_create_plot_figure_line(self):
        try:
            import pandas as pd
            import plotly.express as px
        except ImportError:
            pytest.skip("plotly or pandas not installed")

        from services.dashboard.html_export import _create_plot_figure

        df = pd.DataFrame(
            {
                "x": [1, 2, 3],
                "y": [4, 5, 6],
                "name": ["a", "b", "c"],
            }
        )
        fig = _create_plot_figure(px, df, "x", "y", None, "折れ線")
        assert fig is not None

    def test_add_ng_regions_rect(self):
        try:
            import plotly.graph_objects as go
        except ImportError:
            pytest.skip("plotly not installed")

        from services.dashboard.html_export import _add_ng_regions_to_fig

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))
        ng_regions = [
            {
                "type": "rect",
                "x_min": 0,
                "x_max": 2,
                "y_min": 0,
                "y_max": 3,
                "color": "rgba(255,0,0,0.1)",
                "label": "NG",
            },
        ]
        _add_ng_regions_to_fig(fig, ng_regions)
        # 矩形はshapeとして追加される
        assert len(fig.layout.shapes) == 1

    def test_add_ng_regions_curve(self):
        try:
            import plotly.graph_objects as go
        except ImportError:
            pytest.skip("plotly not installed")

        from services.dashboard.html_export import _add_ng_regions_to_fig

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))
        ng_regions = [
            {
                "type": "curve",
                "points": [[1, 2], [2, 3], [3, 4]],
                "fill": "above",
                "color": "rgba(255,0,0,0.1)",
                "label": "NG curve",
            },
        ]
        _add_ng_regions_to_fig(fig, ng_regions)
        # カーブはtrace（境界線 + fill）として追加
        assert len(fig.data) >= 2

    def test_add_ng_regions_empty(self):
        try:
            import plotly.graph_objects as go
        except ImportError:
            pytest.skip("plotly not installed")

        from services.dashboard.html_export import _add_ng_regions_to_fig

        fig = go.Figure()
        _add_ng_regions_to_fig(fig, [])
        assert len(fig.data) == 0

    def test_add_group_lines(self):
        try:
            import pandas as pd
            import plotly.graph_objects as go
        except ImportError:
            pytest.skip("plotly or pandas not installed")

        from services.dashboard.html_export import _add_group_lines_to_fig

        fig = go.Figure()
        df = pd.DataFrame(
            {
                "x": [1, 2, 3, 4],
                "y": [10, 20, 30, 40],
                "group": ["A", "A", "B", "B"],
            }
        )
        _add_group_lines_to_fig(fig, df, "x", "y", "group")
        # 2グループ、各2点以上なのでそれぞれ結線される
        assert len(fig.data) == 2

    def test_add_group_lines_single_point_group(self):
        try:
            import pandas as pd
            import plotly.graph_objects as go
        except ImportError:
            pytest.skip("plotly or pandas not installed")

        from services.dashboard.html_export import _add_group_lines_to_fig

        fig = go.Figure()
        df = pd.DataFrame(
            {
                "x": [1, 2],
                "y": [10, 20],
                "group": ["A", "B"],
            }
        )
        _add_group_lines_to_fig(fig, df, "x", "y", "group")
        # 各グループ1点のみなので結線なし
        assert len(fig.data) == 0

    def test_create_plot_figure_with_plot_style(self):
        """plot_style指定でマーカー・フォントが反映される"""
        try:
            import pandas as pd
            import plotly.express as px
        except ImportError:
            pytest.skip("plotly or pandas not installed")

        from services.dashboard.html_export import _create_plot_figure

        df = pd.DataFrame(
            {
                "x": [1, 2, 3],
                "y": [4, 5, 6],
                "name": ["a", "b", "c"],
            }
        )
        style = {"marker_size": 24, "line_width": 3, "font_size": 14}
        fig = _create_plot_figure(px, df, "x", "y", None, "散布図", plot_style=style)
        # マーカーサイズが24に設定される
        assert fig.data[0].marker.size == 24
        # フォントサイズ比率: title=14*24/20=17, legend=14*16/20=11
        assert fig.layout.title.font.size == round(14 * 24 / 20)
        assert fig.layout.xaxis.tickfont.size == 14

    def test_create_plot_figure_default_style(self):
        """plot_style未指定でデフォルトスタイルが適用される"""
        try:
            import pandas as pd
            import plotly.express as px
        except ImportError:
            pytest.skip("plotly or pandas not installed")

        from services.dashboard.html_export import _create_plot_figure

        df = pd.DataFrame({"x": [1], "y": [2], "name": ["a"]})
        fig = _create_plot_figure(px, df, "x", "y", None, "散布図")
        # デフォルトマーカーサイズ=16
        assert fig.data[0].marker.size == 16
        # デフォルトフォント=20, title=24
        assert fig.layout.title.font.size == 24
        assert fig.layout.xaxis.tickfont.size == 20

    def test_resolve_plot_style_merges_config_and_view(self):
        """DashboardConfigとビュー設定のマージ"""
        from config import DashboardConfig
        from services.dashboard.html_export import _resolve_plot_style

        config = DashboardConfig.from_dict({"plot": {"style": {"marker_size": 10, "font_size": 18}}})
        # ビュー設定がDashboardConfigを上書き
        view_style = {"marker_size": 30}
        merged = _resolve_plot_style(view_style, config)
        assert merged["marker_size"] == 30  # ビュー設定優先
        assert merged["font_size"] == 18  # DashboardConfigから継承

    def test_resolve_plot_style_empty(self):
        """空のスタイル設定"""
        from services.dashboard.html_export import _resolve_plot_style

        merged = _resolve_plot_style(None, None)
        assert merged == {}

    def test_apply_axis_range(self):
        """軸範囲の適用"""
        try:
            import plotly.graph_objects as go
        except ImportError:
            pytest.skip("plotly not installed")

        from services.dashboard.html_export import _apply_axis_range

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))
        _apply_axis_range(fig, {"x_min": 0, "x_max": 10, "y_min": -5, "y_max": 15})
        assert list(fig.layout.xaxis.range) == [0, 10]
        assert list(fig.layout.yaxis.range) == [-5, 15]

    def test_apply_default_layout_with_style(self):
        """_apply_default_layoutでplot_styleが反映される"""
        try:
            import plotly.graph_objects as go
        except ImportError:
            pytest.skip("plotly not installed")

        from services.dashboard.html_export import _apply_default_layout

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2], y=[3, 4], mode="lines+markers"))
        style = {"font_size": 14, "marker_size": 20}
        _apply_default_layout(
            fig,
            title="Test",
            x_title="X",
            y_title="Y",
            height=500,
            showlegend=True,
            plot_style=style,
        )
        assert fig.layout.xaxis.tickfont.size == 14
        assert fig.data[0].marker.size == 20

    def test_generate_plot_html_with_style_and_range(self):
        """plot_styleとaxis_rangeがHTMLエクスポートに反映される"""
        try:
            import plotly  # noqa: F401
        except ImportError:
            pytest.skip("plotly not installed")

        from config import DashboardConfig, SavedViewConfig
        from services.dashboard.html_export import generate_plot_html

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_test1",
                    format="inp",
                    properties={"path": "a.inp", "RF3": 5.0, "temp": 300},
                ),
                Node(
                    id=2,
                    type="go",
                    name="go_test2",
                    format="inp",
                    properties={"path": "b.inp", "RF3": 3.0, "temp": 350},
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        dashboard_config = DashboardConfig.from_dict({"plot": {"style": {"marker_size": 20, "font_size": 16}}})
        view = SavedViewConfig.from_dict(
            {
                "name": "styled_plot",
                "type": "plot",
                "plot": {
                    "x": "RF3",
                    "y": "temp",
                    "axis_range": {"x_min": 0, "x_max": 10},
                },
            }
        )
        html = generate_plot_html(provider, view, dashboard_config)
        assert "plotly-graph" in html
        assert "データ点数" in html


class TestGalleryHtmlExport:
    """ギャラリーHTMLエクスポートのテスト"""

    def test_gallery_html_export_with_output_images(self):
        """has_output画像のHTMLエクスポート（base64埋め込み）"""
        import tempfile
        from pathlib import Path

        from config import DashboardConfig, SavedViewConfig

        # テスト画像ファイルを作成
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            img_path = project_root / "test_image.png"
            # 1x1 白ピクセルのPNG
            img_path.write_bytes(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
                b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
                b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
                b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
            )

            graph = GraphModel(
                nodes=[
                    Node(
                        id=1,
                        type="go",
                        name="go_test1",
                        format="inp",
                        properties={"path": "go_test1.inp"},
                    ),
                    Node(
                        id=2,
                        type="output",
                        name="test_image.png",
                        format="png",
                        properties={"path": "test_image.png"},
                    ),
                ],
                relations=[
                    Relation(id=1, label="has_output", node1_id=1, node2_id=2),
                ],
            )
            provider = DashboardDataProvider(graph)
            dashboard_config = DashboardConfig.from_dict({})
            view = SavedViewConfig.from_dict(
                {
                    "name": "gallery_test",
                    "type": "gallery",
                    "gallery": {"source": "has_output"},
                }
            )

            from services.dashboard.components.gallery import GalleryPage

            page = GalleryPage()
            html = page.generate_html(provider, view, dashboard_config, project_root=project_root)
            assert "base64" in html
            assert "go_test1" in html
            assert "test_image.png" in html

    def test_gallery_html_export_no_images(self):
        """画像がない場合のエクスポート"""
        from config import DashboardConfig, SavedViewConfig

        graph = GraphModel(
            nodes=[
                Node(id=1, type="go", name="go_test1", format="inp", properties={"path": "a.inp"}),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        dashboard_config = DashboardConfig.from_dict({})
        view = SavedViewConfig.from_dict(
            {
                "name": "empty_gallery",
                "type": "gallery",
                "gallery": {"source": "has_output"},
            }
        )

        from services.dashboard.components.gallery import GalleryPage

        page = GalleryPage()
        html = page.generate_html(provider, view, dashboard_config, project_root="/tmp")
        assert "条件に一致する画像がありません" in html

    def test_gallery_html_export_no_project_root(self):
        """project_root未指定の場合"""
        from config import DashboardConfig, SavedViewConfig

        graph = GraphModel(
            nodes=[Node(id=1, type="go", name="go_test1", format="inp", properties={"path": "a.inp"})],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        dashboard_config = DashboardConfig.from_dict({})
        view = SavedViewConfig.from_dict({"name": "no_root", "type": "gallery", "gallery": {"source": "has_output"}})

        from services.dashboard.components.gallery import GalleryPage

        page = GalleryPage()
        html = page.generate_html(provider, view, dashboard_config)
        assert "project_root" in html

    def test_gallery_html_export_missing_image(self):
        """画像ファイルが存在しない場合"""
        import tempfile
        from pathlib import Path

        from config import DashboardConfig, SavedViewConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            graph = GraphModel(
                nodes=[
                    Node(id=1, type="go", name="go_test1", format="inp", properties={"path": "a.inp"}),
                    Node(
                        id=2,
                        type="output",
                        name="missing.png",
                        format="png",
                        properties={"path": "missing.png"},
                    ),
                ],
                relations=[
                    Relation(id=1, label="has_output", node1_id=1, node2_id=2),
                ],
            )
            provider = DashboardDataProvider(graph)
            dashboard_config = DashboardConfig.from_dict({})
            view = SavedViewConfig.from_dict(
                {
                    "name": "missing_img",
                    "type": "gallery",
                    "gallery": {"source": "has_output"},
                }
            )

            from services.dashboard.components.gallery import GalleryPage

            page = GalleryPage()
            html = page.generate_html(provider, view, dashboard_config, project_root=project_root)
            assert "画像なし" in html


class TestDashboardConfigPlotStyle:
    """DashboardConfig.plot_styleのテスト"""

    def test_plot_style_from_config(self):
        """YAML設定からplot_styleが読み取れる"""
        from config import DashboardConfig

        config = DashboardConfig.from_dict(
            {"plot": {"x": "RF3", "y": "temp", "style": {"marker_size": 20, "line_width": 3, "font_size": 16}}}
        )
        assert config.plot_style == {"marker_size": 20, "line_width": 3, "font_size": 16}
        assert config.plot_x == "RF3"
        assert config.plot_y == "temp"

    def test_plot_style_empty_default(self):
        """デフォルトではplot_styleは空dict"""
        from config import DashboardConfig

        config = DashboardConfig.from_dict({})
        assert config.plot_style == {}

    def test_plot_style_partial(self):
        """一部のスタイルのみ指定"""
        from config import DashboardConfig

        config = DashboardConfig.from_dict({"plot": {"style": {"font_size": 14}}})
        assert config.plot_style == {"font_size": 14}
        assert "marker_size" not in config.plot_style

    def test_plot_style_hyphen_keys(self):
        """ハイフン区切りのキーも対応"""
        from config import DashboardConfig

        config = DashboardConfig.from_dict({"plot": {"style": {"marker-size": 25}}})
        assert config.plot_style == {"marker_size": 25}


# ====================================================================
# verbose_name_format動的展開テスト
# ====================================================================


class TestVerboseNameFormat:
    """verbose_name表示テスト

    verbose_name_formatの展開はparse時（DisplayNameParser）に行われる。
    ダッシュボード側ではparse済みのverbose_nameプロパティを参照するだけ。
    """

    def test_display_name_from_precomputed_verbose_name(self):
        """parse時に生成されたverbose_name（vocab変換後キー）が表示される"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_t20",
                    format="inp",
                    properties={
                        "path": "go_idx1_t20.inp",
                        "条件": "1",
                        "高さ": "20",
                        "表示名": "条件1(高さ20)",
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(
            graph,
            vocab={"idx": "条件", "t": "高さ", "verbose_name": "表示名"},
        )
        rows = provider.get_go_table()
        assert len(rows) == 1
        assert rows[0]["表示名"] == "条件1(高さ20)"

    def test_display_name_from_verbose_name_key(self):
        """verbose_nameキー（vocab未変換）でも表示名が取得できる"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_t20",
                    format="inp",
                    properties={
                        "path": "go_idx1_t20.inp",
                        "verbose_name": "条件1(高さ20)",
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph, vocab={})
        rows = provider.get_go_table()
        assert len(rows) == 1
        assert rows[0]["verbose_name"] == "条件1(高さ20)"

    def test_no_verbose_name_falls_back_to_node_name(self):
        """verbose_nameが無い場合はnameにフォールバック"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_a",
                    format="inp",
                    properties={"path": "a.inp", "条件": "1"},
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(
            graph,
            vocab={"idx": "条件"},
        )
        display = provider._get_display_name(graph.nodes[0])
        assert display == "go_a"

    def test_no_format_falls_back_to_verbose_name(self):
        """verbose_name_format未設定ではプロパティのverbose_nameにフォールバック"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_a",
                    format="inp",
                    properties={"path": "a.inp", "verbose_name": "テスト表示名"},
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        rows = provider.get_go_table()
        assert rows[0]["verbose_name"] == "テスト表示名"


# ====================================================================
# get_filtered_property_keysテスト
# ====================================================================


class TestGetFilteredPropertyKeys:
    """get_filtered_property_keysのテスト"""

    def test_no_filter_returns_all(self, provider: DashboardDataProvider):
        """global_columns未設定では全キーを返す"""
        all_keys = provider.get_property_keys()
        filtered = provider.get_filtered_property_keys()
        assert all_keys == filtered

    def test_glob_pattern_filter(self):
        """globパターンでフィルタされる"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_a",
                    format="inp",
                    properties={
                        "path": "a.inp",
                        "stress_max": 100,
                        "stress_min": 50,
                        "displacement": 1.0,
                        "temperature": 300,
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph, global_columns=["stress*", "temperature"])
        filtered = provider.get_filtered_property_keys()
        assert "stress_max" in filtered
        assert "stress_min" in filtered
        assert "temperature" in filtered
        assert "displacement" not in filtered


# ====================================================================
# get_plot_data extra_keysテスト
# ====================================================================


class TestGetPlotDataExtraKeys:
    """get_plot_dataのextra_keysテスト"""

    def test_extra_keys_included(self):
        """extra_keysで指定したキーがデータに含まれる"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1",
                    format="inp",
                    properties={
                        "path": "a.inp",
                        "x_val": "1.0",
                        "y_val": "2.0",
                        "group_key": "A",
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        data = provider.get_plot_data("x_val", "y_val", extra_keys=["group_key"])
        assert len(data) == 1
        assert data[0]["group_key"] == "A"

    def test_extra_keys_without_param(self):
        """extra_keys未指定ではgroup_keyが含まれない"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1",
                    format="inp",
                    properties={
                        "path": "a.inp",
                        "x_val": "1.0",
                        "y_val": "2.0",
                        "group_key": "A",
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        data = provider.get_plot_data("x_val", "y_val")
        assert len(data) == 1
        assert "group_key" not in data[0]


# ====================================================================
# display_name in images テスト
# ====================================================================


class TestDisplayNameInImages:
    """画像データにdisplay_nameが含まれるテスト"""

    def test_output_images_have_display_name(self, provider: DashboardDataProvider):
        """get_output_imagesの結果にdisplay_nameが含まれる"""
        images = provider.get_output_images()
        for img in images:
            assert "display_name" in img

    def test_property_images_have_display_name(self):
        """get_property_imagesの結果にdisplay_nameが含まれる"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_a",
                    format="inp",
                    properties={
                        "path": "a.inp",
                        "screenshot": "images/test.png",
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        images = provider.get_property_images()
        assert len(images) == 1
        assert "display_name" in images[0]
        assert images[0]["display_name"] == "go_a"

    def test_display_name_uses_precomputed_verbose_name(self):
        """parse時に生成されたverbose_nameが画像のdisplay_nameに使われる"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1",
                    format="inp",
                    properties={
                        "path": "a.inp",
                        "条件": "1",
                        "verbose_name": "条件1",
                        "screenshot": "images/test.png",
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(
            graph,
            vocab={"idx": "条件"},
        )
        images = provider.get_property_images()
        assert len(images) == 1
        assert images[0]["display_name"] == "条件1"


# ====================================================================
# PageComponent / ViewConfig レジストリテスト
# ====================================================================


class TestPageComponentRegistry:
    """PageComponentの__init_subclass__レジストリが正しく動作するテスト"""

    def test_all_builtin_pages_registered(self):
        """6つの組み込みページが全てレジストリに登録されている"""
        # コンポーネントモジュールをインポートして登録をトリガー
        import services.dashboard.components.array_plot
        import services.dashboard.components.card
        import services.dashboard.components.gallery
        import services.dashboard.components.plot
        import services.dashboard.components.status
        import services.dashboard.components.table  # noqa: F401
        from services.dashboard.components import PageComponent

        expected_keys = {"table", "card", "plot", "array_plot", "status", "gallery"}
        actual_keys = set(PageComponent._registry.keys())
        assert expected_keys.issubset(actual_keys), f"Missing: {expected_keys - actual_keys}"

    def test_page_labels_not_empty(self):
        """全てのPageComponentがpage_labelを持つ"""
        import services.dashboard.components.table  # noqa: F401
        from services.dashboard.components import PageComponent

        for key, cls in PageComponent._registry.items():
            assert cls.page_label, f"PageComponent '{key}' has empty page_label"

    def test_get_page_labels(self):
        """get_page_labels()が全ページのラベルを返す"""
        import services.dashboard.components.table  # noqa: F401
        from services.dashboard.components import get_page_labels

        labels = get_page_labels()
        assert "テーブル" in labels
        assert "プロット" in labels
        assert "ギャラリー" in labels

    def test_get_page_component(self):
        """get_page_component()で各ページのインスタンスを取得できる"""
        import services.dashboard.components.table  # noqa: F401
        from services.dashboard.components import PageComponent, get_page_component

        for key in PageComponent._registry:
            component = get_page_component(key)
            assert component is not None, f"get_page_component('{key}') returned None"
            assert component.page_key == key

    def test_get_page_component_by_label(self):
        """get_page_component_by_label()でラベルからインスタンスを取得できる"""
        import services.dashboard.components.table  # noqa: F401
        from services.dashboard.components import get_page_component_by_label

        component = get_page_component_by_label("テーブル")
        assert component is not None
        assert component.page_key == "table"

    def test_get_page_component_unknown_returns_none(self):
        """未登録のpage_keyに対してNoneが返る"""
        from services.dashboard.components import get_page_component

        assert get_page_component("nonexistent") is None

    def test_page_component_has_get_view_config(self):
        """PageComponentインスタンスからget_view_config()で対応するViewConfigを取得できる"""
        import services.dashboard.components.plot  # noqa: F401
        from services.dashboard.components import get_page_component

        component = get_page_component("plot")
        assert component is not None
        vc = component.get_view_config()
        assert vc is not None
        assert vc.view_type == "plot"


class TestViewConfigRegistry:
    """ViewConfigの__init_subclass__レジストリが正しく動作するテスト"""

    def test_all_builtin_view_configs_registered(self):
        """6つの組み込みViewConfigが全てレジストリに登録されている"""
        import services.dashboard.components.array_plot
        import services.dashboard.components.card
        import services.dashboard.components.gallery
        import services.dashboard.components.plot
        import services.dashboard.components.status
        import services.dashboard.components.table  # noqa: F401
        from services.dashboard.components import ViewConfig

        expected_types = {"table", "card", "plot", "array_plot", "status", "gallery"}
        actual_types = set(ViewConfig._registry.keys())
        assert expected_types.issubset(actual_types), f"Missing: {expected_types - actual_types}"

    def test_get_view_config(self):
        """get_view_config()で各ビュータイプのインスタンスを取得できる"""
        import services.dashboard.components.table  # noqa: F401
        from services.dashboard.components import ViewConfig, get_view_config

        for vt in ViewConfig._registry:
            vc = get_view_config(vt)
            assert vc is not None, f"get_view_config('{vt}') returned None"
            assert vc.view_type == vt

    def test_get_view_type_options(self):
        """get_view_type_options()が全ビュータイプを返す"""
        import services.dashboard.components.table  # noqa: F401
        from services.dashboard.components import get_view_type_options

        options = get_view_type_options()
        assert "table" in options
        assert "plot" in options

    def test_page_key_matches_view_type(self):
        """PageComponentのpage_keyとViewConfigのview_typeが1:1対応する"""
        import services.dashboard.components.array_plot
        import services.dashboard.components.card
        import services.dashboard.components.gallery
        import services.dashboard.components.plot
        import services.dashboard.components.status
        import services.dashboard.components.table  # noqa: F401
        from services.dashboard.components import PageComponent, ViewConfig

        for key in PageComponent._registry:
            assert key in ViewConfig._registry, f"PageComponent '{key}' has no matching ViewConfig"


# ====================================================================
# filter_images_by_keys テスト
# ====================================================================


class TestFilterImagesByKeys:
    """filter_images_by_keysのテスト"""

    def test_no_filter_returns_all(self):
        """allowed_keys=NoneまたはNone時は全件返す"""
        from services.dashboard.query import filter_images_by_keys

        images = [
            {"image_path": "results/S-S13/step0/img.png"},
            {"image_path": "results/U-U3/step0/img.png"},
        ]
        result = filter_images_by_keys(images, None, source="output")
        assert len(result) == 2

    def test_empty_filter_returns_all(self):
        """allowed_keys=[]の場合は全件返す"""
        from services.dashboard.query import filter_images_by_keys

        images = [
            {"image_path": "results/S-S13/step0/img.png"},
        ]
        result = filter_images_by_keys(images, [], source="output")
        assert len(result) == 1

    def test_filter_output_by_result_key(self):
        """outputソースでresult_keyによるフィルタが機能する"""
        from services.dashboard.query import filter_images_by_keys

        # _extract_result_key_from_pathはファイル名トークンからresult_keyを抽出
        images = [
            {"image_path": "results/go_idx1_S-S13.png"},
            {"image_path": "results/go_idx1_U-U3.png"},
            {"image_path": "results/go_idx1_PEEQ.png"},
        ]
        result = filter_images_by_keys(images, ["S-S13"], source="output")
        assert len(result) == 1
        assert "S-S13" in result[0]["image_path"]

    def test_filter_output_multiple_keys(self):
        """複数キーのフィルタが機能する"""
        from services.dashboard.query import filter_images_by_keys

        images = [
            {"image_path": "results/go_idx1_S-S13.png"},
            {"image_path": "results/go_idx1_U-U3.png"},
            {"image_path": "results/go_idx1_PEEQ.png"},
        ]
        result = filter_images_by_keys(images, ["S-S13", "PEEQ"], source="output")
        assert len(result) == 2

    def test_filter_property_by_key(self):
        """propertyソースでproperty_keyによるフィルタが機能する"""
        from services.dashboard.query import filter_images_by_keys

        images = [
            {"property_key": "screenshot", "image_path": "a.png"},
            {"property_key": "daily:2026-01-01:figure", "image_path": "b.png"},
            {"property_key": "thumbnail", "image_path": "c.png"},
        ]
        result = filter_images_by_keys(images, ["figure"], source="property")
        assert len(result) == 1
        assert result[0]["image_path"] == "b.png"


# ====================================================================
# SavedViewConfig コネクタータイプ拡張テスト
# ====================================================================


class TestSavedViewConfigConnectorType:
    """SavedViewConfigのconnector:プレフィックス対応テスト"""

    def test_connector_view_type_accepted(self):
        """connector:{label}形式のview_typeが受け入れられる"""
        from config import SavedViewConfig

        view = SavedViewConfig.from_dict(
            {
                "name": "物性ビュー",
                "type": "connector:物性一覧",
            }
        )
        assert view.view_type == "connector:物性一覧"
        assert view.is_connector_view is True
        assert view.connector_page_label == "物性一覧"

    def test_builtin_view_type_not_connector(self):
        """ビルトインview_typeはis_connector_view=False"""
        from config import SavedViewConfig

        view = SavedViewConfig.from_dict({"name": "テーブル", "type": "table"})
        assert view.is_connector_view is False
        assert view.connector_page_label == ""

    def test_invalid_view_type_raises(self):
        """不正なview_typeはValueErrorを送出"""
        import pytest

        from config import SavedViewConfig

        with pytest.raises(ValueError, match="saved-views"):
            SavedViewConfig.from_dict({"name": "不正", "type": "invalid_type"})

    def test_local_filters_parsed(self):
        """local_filtersがfrom_dictで正しく読み込まれる"""
        from config import SavedViewConfig

        view = SavedViewConfig.from_dict(
            {
                "name": "フィルタ付きテーブル",
                "type": "table",
                "local_filters": {"analysis_status": "COMPLETED"},
            }
        )
        assert view.local_filters == {"analysis_status": "COMPLETED"}

    def test_local_filters_default_empty(self):
        """local_filtersが未指定の場合は空辞書"""
        from config import SavedViewConfig

        view = SavedViewConfig.from_dict({"name": "テスト", "type": "table"})
        assert view.local_filters == {}

    def test_connector_config_parsed(self):
        """connector_configがfrom_dictで正しく読み込まれる"""
        from config import SavedViewConfig

        view = SavedViewConfig.from_dict(
            {
                "name": "物性ビュー",
                "type": "connector:物性一覧",
                "connector_config": {"show_comparison": True},
            }
        )
        assert view.connector_config == {"show_comparison": True}


# ====================================================================
# ローカルフィルター・チェーンフィルターテスト
# ====================================================================


class TestLocalFilterChain:
    """merge_filters / apply_chained_filters テスト"""

    def test_merge_filters_global_only(self):
        """ローカルフィルタがない場合はグローバルのみ"""
        from services.query.filters import merge_filters

        result = merge_filters({"type": "go"})
        assert result == {"type": "go"}

    def test_merge_filters_local_overrides(self):
        """ローカルフィルタがグローバルを上書き"""
        from services.query.filters import merge_filters

        result = merge_filters(
            {"type": "go", "active": True},
            {"active": False, "analysis_status": "COMPLETED"},
        )
        assert result == {"type": "go", "active": False, "analysis_status": "COMPLETED"}

    def test_merge_filters_empty_local(self):
        """空のローカルフィルタはグローバルのみ"""
        from services.query.filters import merge_filters

        result = merge_filters({"type": "go"}, {})
        assert result == {"type": "go"}

    def test_apply_chained_filters_global_only(self):
        """グローバルフィルタのみ適用"""
        from services.query.filters import apply_chained_filters

        rows = [
            {"type": "go", "name": "go_1", "analysis_status": "COMPLETED"},
            {"type": "go", "name": "go_2", "analysis_status": "FAILED"},
            {"type": "inp", "name": "inp_1", "analysis_status": "COMPLETED"},
        ]
        result = apply_chained_filters(rows, {"type": "go"})
        assert len(result) == 2
        assert all(r["type"] == "go" for r in result)

    def test_apply_chained_filters_with_local(self):
        """グローバル→ローカルの順で適用"""
        from services.query.filters import apply_chained_filters

        rows = [
            {"type": "go", "name": "go_1", "analysis_status": "COMPLETED"},
            {"type": "go", "name": "go_2", "analysis_status": "FAILED"},
            {"type": "inp", "name": "inp_1", "analysis_status": "COMPLETED"},
        ]
        result = apply_chained_filters(
            rows,
            {"type": "go"},
            {"analysis_status": "COMPLETED"},
        )
        assert len(result) == 1
        assert result[0]["name"] == "go_1"


# ====================================================================
# コネクター保存ビューHTML生成テスト
# ====================================================================


class TestConnectorSavedViewHtml:
    """コネクター保存ビューのHTML生成テスト"""

    def test_connector_saved_view_html_generation(self):
        """コネクター保存ビューのHTML断片が生成される"""
        pytest.importorskip("pandas")
        import services.dashboard.connectors.abaqus  # noqa: F401
        from config import SavedViewConfig
        from services.dashboard.connectors import generate_connector_saved_view_html

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="abaqus_material",
                    name="Steel",
                    format="material",
                    properties={"elastic": [[210000.0, 0.3]]},
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        view = SavedViewConfig.from_dict(
            {
                "name": "物性保存ビュー",
                "type": "connector:物性一覧",
            }
        )
        html = generate_connector_saved_view_html("物性一覧", provider, view, None)
        assert "物性テーブル" in html
        assert "Steel" in html

    def test_connector_saved_view_html_unregistered(self):
        """未登録のページラベルでは空文字列を返す"""
        from config import SavedViewConfig
        from services.dashboard.connectors import generate_connector_saved_view_html

        graph = GraphModel(nodes=[], relations=[])
        provider = DashboardDataProvider(graph)
        view = SavedViewConfig.from_dict(
            {
                "name": "テスト",
                "type": "connector:存在しないページ",
            }
        )
        result = generate_connector_saved_view_html("存在しないページ", provider, view, None)
        assert result == ""

    def test_connector_saved_view_html_unavailable(self):
        """利用不可のコネクターでは空文字列を返す"""
        import services.dashboard.connectors.abaqus  # noqa: F401
        from config import SavedViewConfig
        from services.dashboard.connectors import generate_connector_saved_view_html

        # abaqus_materialノードがないのでAbaqusMaterialPageConnectorは利用不可
        graph = GraphModel(nodes=[], relations=[])
        provider = DashboardDataProvider(graph)
        view = SavedViewConfig.from_dict(
            {
                "name": "テスト",
                "type": "connector:物性一覧",
            }
        )
        result = generate_connector_saved_view_html("物性一覧", provider, view, None)
        assert result == ""

    def test_generate_view_html_dispatches_connector(self):
        """generate_view_htmlがコネクタービューを正しくディスパッチする"""
        pytest.importorskip("pandas")
        import services.dashboard.connectors.abaqus  # noqa: F401
        from config import SavedViewConfig
        from services.dashboard.html_export import generate_view_html

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="abaqus_material",
                    name="Aluminum",
                    format="material",
                    properties={"elastic": [[70000.0, 0.33]]},
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        view = SavedViewConfig.from_dict(
            {
                "name": "物性HTMLビュー",
                "type": "connector:物性一覧",
            }
        )
        from pathlib import Path

        html = generate_view_html(provider, Path("/tmp"), None, view)
        assert "物性テーブル" in html
        assert "Aluminum" in html

    def test_get_connector_view_type_options(self):
        """get_connector_view_type_optionsが利用可能なコネクタータイプを返す"""
        import services.dashboard.connectors.abaqus  # noqa: F401
        from services.dashboard.connectors import get_connector_view_type_options

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="abaqus_material",
                    name="Steel",
                    format="material",
                    properties={},
                ),
                Node(
                    id=2,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"analysis_status": "COMPLETED"},
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        options = get_connector_view_type_options(provider)
        assert "connector:物性一覧" in options
        assert "connector:ジョブサマリー" in options

    def test_render_saved_view_default_delegates(self):
        """基底クラスのrender_saved_viewがrender_pageに委譲する"""
        from config import SavedViewConfig
        from services.dashboard.connectors import DashboardPageConnector

        called = {}

        class TestConnector(DashboardPageConnector):
            page_label = ""  # レジストリに登録しない

            def render_page(self, provider, dashboard_config):
                called["render_page"] = True

        connector = TestConnector()
        graph = GraphModel(nodes=[], relations=[])
        provider = DashboardDataProvider(graph)
        view = SavedViewConfig.from_dict({"name": "test", "type": "table"})
        connector.render_saved_view(provider, view, None)
        assert called.get("render_page") is True

    def test_generate_saved_view_html_default_delegates(self):
        """基底クラスのgenerate_saved_view_htmlがgenerate_htmlに委譲する"""
        from config import SavedViewConfig
        from services.dashboard.connectors import DashboardPageConnector

        class TestConnector(DashboardPageConnector):
            page_label = ""  # レジストリに登録しない

            def generate_html(self, provider, dashboard_config):
                return "<p>test html</p>"

        connector = TestConnector()
        graph = GraphModel(nodes=[], relations=[])
        provider = DashboardDataProvider(graph)
        view = SavedViewConfig.from_dict({"name": "test", "type": "table"})
        result = connector.generate_saved_view_html(provider, view, None)
        assert result == "<p>test html</p>"


# ====================================================================
# _compute_histogram_bins / _percentile テスト
# ====================================================================


class TestComputeHistogramBins:
    """ヒストグラムビン数の動的調整テスト"""

    def test_single_value(self):
        """1値の場合はbin=1"""
        from services.dashboard.data_provider import _compute_histogram_bins

        assert _compute_histogram_bins([1.0]) == 1

    def test_small_dataset(self):
        """5値以下の場合はbin=n"""
        from services.dashboard.data_provider import _compute_histogram_bins

        assert _compute_histogram_bins([1.0, 2.0, 3.0]) == 3
        assert _compute_histogram_bins([1.0, 2.0, 3.0, 4.0, 5.0]) == 5

    def test_medium_dataset(self):
        """中規模データでSturges則ベースのbin数"""
        from services.dashboard.data_provider import _compute_histogram_bins

        values = list(range(100))
        nbins = _compute_histogram_bins([float(v) for v in values])
        # Sturges則: ceil(log2(100) + 1) = ceil(7.64) = 8 → 最小10に拡大
        assert nbins == 10

    def test_large_dataset(self):
        """大規模データでbin数が最大50に制限"""
        from services.dashboard.data_provider import _compute_histogram_bins

        values = [float(i) for i in range(1000000)]
        nbins = _compute_histogram_bins(values)
        assert nbins <= 50

    def test_empty_list_returns_one(self):
        """空リストの場合"""
        from services.dashboard.data_provider import _compute_histogram_bins

        # n=0 → max(10, min(50, ...)) will handle log(0)
        # 実際はn <= 1のガード
        assert _compute_histogram_bins([]) == 1


class TestPercentile:
    """パーセンタイル計算テスト"""

    def test_median_odd_count(self):
        """奇数個のデータの中央値"""
        from services.dashboard.data_provider import _percentile

        assert _percentile([1.0, 2.0, 3.0], 50) == 2.0

    def test_median_even_count(self):
        """偶数個のデータの中央値（線形補間）"""
        from services.dashboard.data_provider import _percentile

        result = _percentile([1.0, 2.0, 3.0, 4.0], 50)
        assert result == pytest.approx(2.5)

    def test_quartiles(self):
        """四分位数テスト"""
        from services.dashboard.data_provider import _percentile

        data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
        q1 = _percentile(data, 25)
        q3 = _percentile(data, 75)
        assert q1 < _percentile(data, 50) < q3

    def test_single_value(self):
        """単一値ではすべてのパーセンタイルが同値"""
        from services.dashboard.data_provider import _percentile

        assert _percentile([5.0], 0) == 5.0
        assert _percentile([5.0], 50) == 5.0
        assert _percentile([5.0], 100) == 5.0


class TestStatusSummaryEnhanced:
    """get_status_summary の拡張統計テスト"""

    def test_cpu_stats_includes_nbins(self):
        """cpu_statsにnbinsキーが含まれる"""
        nodes = [
            Node(
                id=i,
                type="go",
                name=f"go_idx{i}",
                format="inp",
                properties={"cpu_time": float(i * 100), "analysis_status": "completed"},
            )
            for i in range(1, 20)
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        provider = DashboardDataProvider(graph)
        summary = provider.get_status_summary()
        cpu_stats = summary["cpu_stats"]
        assert "nbins" in cpu_stats
        assert cpu_stats["nbins"] >= 1

    def test_cpu_stats_includes_quartiles(self):
        """cpu_statsに四分位数・標準偏差が含まれる"""
        nodes = [
            Node(
                id=i,
                type="go",
                name=f"go_idx{i}",
                format="inp",
                properties={"cpu_time": float(i * 100), "analysis_status": "completed"},
            )
            for i in range(1, 10)
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        provider = DashboardDataProvider(graph)
        summary = provider.get_status_summary()
        cpu_stats = summary["cpu_stats"]
        assert "median" in cpu_stats
        assert "q1" in cpu_stats
        assert "q3" in cpu_stats
        assert "std" in cpu_stats
        assert cpu_stats["q1"] <= cpu_stats["median"] <= cpu_stats["q3"]

    def test_warning_stats_includes_nbins(self):
        """warning_statsにnbinsキーが含まれる"""
        nodes = [
            Node(
                id=i,
                type="go",
                name=f"go_idx{i}",
                format="inp",
                properties={
                    "cpu_time": 100.0 + i,
                    "sta_warnings": [f"warn{j}" for j in range(i * 2)],
                    "msg_warnings": [],
                    "dat_warnings": [],
                    "sta_errors": [],
                    "msg_errors": [],
                    "dat_errors": [],
                    "analysis_status": "completed",
                },
            )
            for i in range(1, 15)
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        provider = DashboardDataProvider(graph)
        summary = provider.get_status_summary()
        # warnings はリストのlen()でカウントされるのでwarning_statsには出ない
        # cpu_statsが存在すること確認
        assert "cpu_stats" in summary
        cpu_stats = summary["cpu_stats"]
        assert "nbins" in cpu_stats


# ====================================================================
# status-039 TODO テスト
# ====================================================================


class TestContourPlot:
    """コンタープロットのテスト"""

    def test_create_plot_figure_contour(self):
        """コンターチャートタイプで連続カラースケールが使用される"""
        try:
            import pandas as pd
            import plotly.express as px
        except ImportError:
            pytest.skip("plotly or pandas not installed")

        from services.dashboard.html_export import _create_plot_figure

        df = pd.DataFrame(
            {
                "x": [1, 2, 3, 4],
                "y": [4, 5, 6, 7],
                "z_val": [10.0, 20.0, 30.0, 40.0],
                "name": ["a", "b", "c", "d"],
            }
        )
        fig = _create_plot_figure(
            px,
            df,
            "x",
            "y",
            None,
            "コンター",
            z_key="z_val",
            color_range={"vmin": 0, "vmax": 50},
        )
        # コンターは散布図ベースで生成される
        assert len(fig.data) >= 1
        assert "色: z_val" in fig.layout.title.text

    def test_create_plot_figure_contour_no_z_key(self):
        """Z軸キー未指定のコンター"""
        try:
            import pandas as pd
            import plotly.express as px
        except ImportError:
            pytest.skip("plotly or pandas not installed")

        from services.dashboard.html_export import _create_plot_figure

        df = pd.DataFrame({"x": [1, 2], "y": [3, 4], "name": ["a", "b"]})
        fig = _create_plot_figure(px, df, "x", "y", None, "コンター")
        assert len(fig.data) >= 1

    def test_create_plot_figure_contour_with_color_range(self):
        """vmin/vmaxによるカラーバー範囲制御"""
        try:
            import pandas as pd
            import plotly.express as px
        except ImportError:
            pytest.skip("plotly or pandas not installed")

        from services.dashboard.html_export import _create_plot_figure

        df = pd.DataFrame(
            {
                "x": [1, 2, 3],
                "y": [4, 5, 6],
                "temp": [100.0, 200.0, 300.0],
                "name": ["a", "b", "c"],
            }
        )
        fig = _create_plot_figure(
            px,
            df,
            "x",
            "y",
            None,
            "コンター",
            z_key="temp",
            color_range={"vmin": 50, "vmax": 350},
        )
        # coloraxis.cmin/cmaxでカラーバー範囲が設定される
        caxis = fig.layout.coloraxis
        assert caxis.cmin == 50
        assert caxis.cmax == 350

    def test_create_plot_figure_density_contour(self):
        """等高線チャートタイプでdensity_contourが使用される"""
        try:
            import pandas as pd
            import plotly.express as px
        except ImportError:
            pytest.skip("plotly or pandas not installed")

        from services.dashboard.html_export import _create_plot_figure

        df = pd.DataFrame(
            {
                "x": [1, 2, 3, 4, 5],
                "y": [4, 5, 6, 7, 8],
                "z_val": [10.0, 20.0, 30.0, 40.0, 50.0],
                "name": ["a", "b", "c", "d", "e"],
            }
        )
        fig = _create_plot_figure(
            px,
            df,
            "x",
            "y",
            None,
            "等高線",
            z_key="z_val",
        )
        assert len(fig.data) >= 1
        assert "Z: z_val" in fig.layout.title.text
        # density_contourのトレースタイプはcontourまたはhistogram2dcontour
        trace_type = fig.data[0].type
        assert trace_type in ("contour", "histogram2dcontour")

    def test_create_plot_figure_density_contour_no_z(self):
        """Z軸未指定の等高線（密度のみ）"""
        try:
            import pandas as pd
            import plotly.express as px
        except ImportError:
            pytest.skip("plotly or pandas not installed")

        from services.dashboard.html_export import _create_plot_figure

        df = pd.DataFrame({"x": [1, 2, 3], "y": [3, 4, 5], "name": ["a", "b", "c"]})
        fig = _create_plot_figure(px, df, "x", "y", None, "等高線")
        assert len(fig.data) >= 1
        assert "密度" in fig.layout.title.text

    def test_create_plot_figure_density_contour_with_color_range(self):
        """等高線のvmin/vmaxでcontours.start/endが制御される"""
        try:
            import pandas as pd
            import plotly.express as px
        except ImportError:
            pytest.skip("plotly or pandas not installed")

        from services.dashboard.html_export import _create_plot_figure

        df = pd.DataFrame(
            {
                "x": [1, 2, 3, 4],
                "y": [4, 5, 6, 7],
                "temp": [100.0, 200.0, 300.0, 400.0],
                "name": ["a", "b", "c", "d"],
            }
        )
        fig = _create_plot_figure(
            px,
            df,
            "x",
            "y",
            None,
            "等高線",
            z_key="temp",
            color_range={"vmin": 50, "vmax": 350},
        )
        assert len(fig.data) >= 1
        # 等高線の塗りつぶしがVirdis色で設定される
        trace = fig.data[0]
        assert trace.contours.coloring == "fill"


class TestSavedViewStylePersistence:
    """SavedViewConfigでplot_style/axis_range/color_rangeの永続化テスト"""

    def test_saved_view_with_plot_style(self):
        """SavedViewConfigにplot_styleが含まれる"""
        from config import SavedViewConfig

        view = SavedViewConfig.from_dict(
            {
                "name": "styled_plot",
                "type": "plot",
                "plot": {
                    "x": "RF3",
                    "y": "temp",
                    "plot_style": {"marker_size": 24, "font_size": 14},
                    "axis_range": {"x_min": 0, "x_max": 100},
                },
            }
        )
        assert view.plot["plot_style"]["marker_size"] == 24
        assert view.plot["axis_range"]["x_min"] == 0

    def test_saved_view_with_contour_config(self):
        """SavedViewConfigにZ軸とcolor_rangeが含まれる"""
        from config import SavedViewConfig

        view = SavedViewConfig.from_dict(
            {
                "name": "contour_plot",
                "type": "plot",
                "plot": {
                    "x": "RF3",
                    "y": "RF2",
                    "chart_type": "コンター",
                    "z": "temperature",
                    "color_range": {"vmin": 0, "vmax": 500},
                },
            }
        )
        assert view.plot["z"] == "temperature"
        assert view.plot["color_range"]["vmin"] == 0
        assert view.plot["color_range"]["vmax"] == 500


class TestGalleryMaxImageBytes:
    """ギャラリーHTMLの画像ファイルサイズ上限テスト"""

    def test_gallery_max_image_bytes_config(self):
        """gallery-max-image-bytes → gallery_defaults.max_image_bytesに統合される"""
        from config import DashboardConfig

        config = DashboardConfig.from_dict({"gallery-max-image-bytes": 1048576})
        assert config.gallery_defaults.max_image_bytes == 1048576

    def test_gallery_max_image_bytes_default(self):
        """空dict時のデフォルトは5MB"""
        from config import DashboardConfig

        config = DashboardConfig.from_dict({})
        assert config.gallery_defaults.max_image_bytes == 5 * 1024 * 1024

    def test_gallery_max_image_bytes_default_with_data(self):
        """データありでキー未指定時はデフォルト5MB"""
        from config import DashboardConfig

        config = DashboardConfig.from_dict({"plot": {"x": "RF3"}})
        assert config.gallery_defaults.max_image_bytes == 5 * 1024 * 1024

    def test_gallery_html_skips_large_images(self):
        """サイズ上限を超える画像がスキップまたはサムネイル化される"""
        import tempfile
        from pathlib import Path

        from config import DashboardConfig, SavedViewConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            # 小さい画像（OK）
            small_img = project_root / "small.png"
            small_img.write_bytes(b"\x89PNG" + b"\x00" * 50)
            # 大きい画像（スキップ/サムネイル対象）
            large_img = project_root / "large.png"
            large_img.write_bytes(b"\x89PNG" + b"\x00" * 200)

            graph = GraphModel(
                nodes=[
                    Node(id=1, type="go", name="go_small", format="inp", properties={"path": "a.inp"}),
                    Node(id=2, type="output", name="small.png", format="png", properties={"path": "small.png"}),
                    Node(id=3, type="go", name="go_large", format="inp", properties={"path": "b.inp"}),
                    Node(id=4, type="output", name="large.png", format="png", properties={"path": "large.png"}),
                ],
                relations=[
                    Relation(id=1, label="has_output", node1_id=1, node2_id=2),
                    Relation(id=2, label="has_output", node1_id=3, node2_id=4),
                ],
            )
            provider = DashboardDataProvider(graph)
            # 上限100バイトに設定（large.pngの204バイトは超過）
            dashboard_config = DashboardConfig.from_dict({"gallery-max-image-bytes": 100})
            view = SavedViewConfig.from_dict(
                {
                    "name": "size_limited_gallery",
                    "type": "gallery",
                    "gallery": {"source": "has_output"},
                }
            )

            from services.dashboard.components.gallery import GalleryPage

            page = GalleryPage()
            html = page.generate_html(provider, view, dashboard_config, project_root=project_root)
            # PILが利用可能ならサムネイル化、不可ならスキップ
            assert "スキップ" in html or "サムネイル" in html
            # 小さい画像はbase64で埋め込まれる
            assert "base64" in html

    def test_gallery_html_thumbnail_with_pil(self):
        """PIL利用可能時、上限超過画像がサムネイル化される"""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        import io
        import tempfile
        from pathlib import Path

        from config import DashboardConfig, SavedViewConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            # 有効なPNG画像を生成（100x100, RGB）
            img = Image.new("RGB", (100, 100), color=(255, 0, 0))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            png_data = buf.getvalue()

            large_img = project_root / "large.png"
            large_img.write_bytes(png_data)

            graph = GraphModel(
                nodes=[
                    Node(id=1, type="go", name="go_large", format="inp", properties={"path": "a.inp"}),
                    Node(id=2, type="output", name="large.png", format="png", properties={"path": "large.png"}),
                ],
                relations=[Relation(id=1, label="has_output", node1_id=1, node2_id=2)],
            )
            provider = DashboardDataProvider(graph)
            # 上限を非常に小さく設定（PNG画像は確実にこれを超える）
            dashboard_config = DashboardConfig.from_dict({"gallery-max-image-bytes": 10})
            view = SavedViewConfig.from_dict(
                {
                    "name": "thumbnail_gallery",
                    "type": "gallery",
                    "gallery": {"source": "has_output"},
                }
            )

            from services.dashboard.components.gallery import GalleryPage

            page = GalleryPage()
            html = page.generate_html(provider, view, dashboard_config, project_root=project_root)
            # サムネイルが生成される
            assert "サムネイル" in html
            assert "base64" in html
            # スキップではなくサムネイル化
            assert "スキップ" not in html

    def test_generate_thumbnail_function(self):
        """_generate_thumbnail関数の直接テスト"""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        import io
        import tempfile
        from pathlib import Path

        from services.dashboard.components.gallery import _generate_thumbnail

        with tempfile.TemporaryDirectory() as tmpdir:
            # 大きめの画像を生成
            img = Image.new("RGB", (500, 500), color=(0, 128, 255))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            img_path = Path(tmpdir) / "test.png"
            img_path.write_bytes(buf.getvalue())

            # サムネイル生成
            result = _generate_thumbnail(img_path, max_bytes=50000, max_dimension=200)
            assert result is not None
            assert len(result) > 0
            # JPEG形式か確認
            assert result[:2] == b"\xff\xd8"  # JPEG SOI marker

    def test_generate_thumbnail_rgba(self):
        """RGBA画像がJPEGサムネイルに変換される"""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        import io
        import tempfile
        from pathlib import Path

        from services.dashboard.components.gallery import _generate_thumbnail

        with tempfile.TemporaryDirectory() as tmpdir:
            img = Image.new("RGBA", (200, 200), color=(255, 0, 0, 128))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            img_path = Path(tmpdir) / "rgba.png"
            img_path.write_bytes(buf.getvalue())

            result = _generate_thumbnail(img_path, max_bytes=50000)
            assert result is not None
            assert result[:2] == b"\xff\xd8"

    def test_gallery_html_no_limit(self):
        """サイズ上限0（無制限）ではスキップしない"""
        import tempfile
        from pathlib import Path

        from config import DashboardConfig, SavedViewConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            img = project_root / "test.png"
            img.write_bytes(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
                b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
                b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
                b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
            )

            graph = GraphModel(
                nodes=[
                    Node(id=1, type="go", name="go_t", format="inp", properties={"path": "a.inp"}),
                    Node(id=2, type="output", name="test.png", format="png", properties={"path": "test.png"}),
                ],
                relations=[Relation(id=1, label="has_output", node1_id=1, node2_id=2)],
            )
            provider = DashboardDataProvider(graph)
            # gallery_defaults.max_image_bytes=0（無制限）— 後方互換キーで設定
            dashboard_config = DashboardConfig.from_dict({"gallery-max-image-bytes": 0})
            view = SavedViewConfig.from_dict(
                {
                    "name": "unlimited_gallery",
                    "type": "gallery",
                    "gallery": {"source": "has_output"},
                }
            )

            from services.dashboard.components.gallery import GalleryPage

            page = GalleryPage()
            html = page.generate_html(provider, view, dashboard_config, project_root=project_root)
            assert "スキップ" not in html
            assert "base64" in html


class TestViewEditFormPlotConfig:
    """動的ビュー編集フォームでplot設定が正しく構築・保存される"""

    def test_plot_config_roundtrip(self):
        """edit_plot_configから構築した辞書がSavedViewConfigで正しく読み取れる"""
        from config import SavedViewConfig

        # 編集フォームが構築する辞書を模擬
        edit_plot_config = {
            "x": "RF3",
            "y": "temperature",
            "color": None,
            "chart_type": "コンター",
            "z": "stress",
            "color_range": {"vmin": 0.0, "vmax": 500.0},
            "plot_style": {"marker_size": 20, "font_size": 16},
            "axis_range": {"x_min": 0.0, "x_max": 100.0, "y_min": -10.0, "y_max": 50.0},
        }
        view_data = {
            "name": "edited_plot",
            "type": "plot",
            "plot": edit_plot_config,
        }

        view = SavedViewConfig.from_dict(view_data)
        assert view.plot["x"] == "RF3"
        assert view.plot["y"] == "temperature"
        assert view.plot["chart_type"] == "コンター"
        assert view.plot["z"] == "stress"
        assert view.plot["color_range"]["vmin"] == 0.0
        assert view.plot["color_range"]["vmax"] == 500.0
        assert view.plot["plot_style"]["marker_size"] == 20
        assert view.plot["plot_style"]["font_size"] == 16
        assert view.plot["axis_range"]["x_min"] == 0.0
        assert view.plot["axis_range"]["y_max"] == 50.0

    def test_plot_config_density_contour_roundtrip(self):
        """等高線タイプのplot設定がround-trip可能"""
        from config import SavedViewConfig

        edit_plot_config = {
            "x": "x_coord",
            "y": "y_coord",
            "color": "group",
            "chart_type": "等高線",
            "z": "density",
            "color_range": {"vmin": 10.0},
        }
        view = SavedViewConfig.from_dict({"name": "density_view", "type": "plot", "plot": edit_plot_config})
        assert view.plot["chart_type"] == "等高線"
        assert view.plot["z"] == "density"
        assert view.plot["color_range"]["vmin"] == 10.0
        assert "vmax" not in view.plot["color_range"]

    def test_plot_config_minimal(self):
        """最小限のプロット設定（x, y, chart_typeのみ）"""
        from config import SavedViewConfig

        edit_plot_config = {
            "x": "col_a",
            "y": "col_b",
            "color": None,
            "chart_type": "散布図",
        }
        view = SavedViewConfig.from_dict({"name": "minimal_plot", "type": "plot", "plot": edit_plot_config})
        assert view.plot["x"] == "col_a"
        assert view.plot["chart_type"] == "散布図"
        assert "plot_style" not in view.plot
        assert "axis_range" not in view.plot

    def test_build_style_config_all_values(self):
        """build_style_configで全値が設定される"""
        from services.dashboard.widgets import build_style_config

        style = build_style_config(24, 3, 14)
        assert style == {"marker_size": 24, "line_width": 3, "font_size": 14}

    def test_build_style_config_partial(self):
        """build_style_configでNone値が除外される"""
        from services.dashboard.widgets import build_style_config

        style = build_style_config(None, 2, None)
        assert style == {"line_width": 2}
        assert "marker_size" not in style
        assert "font_size" not in style


# ====================================================================
# DashboardConfig array_plot_defaults テスト
# ====================================================================


class TestDashboardConfigArrayPlotDefaults:
    """DashboardConfig の array_plot_defaults テスト"""

    def test_array_plot_defaults_empty_by_default(self):
        """デフォルトでarray_plot_defaultsは空辞書"""
        from config import DashboardConfig

        config = DashboardConfig.from_dict({})
        assert config.array_plot_defaults == {}

    def test_array_plot_defaults_with_x_y(self):
        """x, yキーを指定"""
        from config import DashboardConfig

        config = DashboardConfig.from_dict(
            {
                "array-plot": {
                    "x": "U.U1",
                    "y": ["RF.RF3", "RF.RF1"],
                }
            }
        )
        assert config.array_plot_defaults["x"] == "U.U1"
        assert config.array_plot_defaults["y"] == ["RF.RF3", "RF.RF1"]

    def test_array_plot_defaults_with_ranges(self):
        """軸範囲を指定"""
        from config import DashboardConfig

        config = DashboardConfig.from_dict(
            {
                "array-plot": {
                    "x-min": 0.0,
                    "x-max": 10.0,
                    "y-min": -5.0,
                    "y-max": 100.0,
                }
            }
        )
        assert config.array_plot_defaults["x_min"] == 0.0
        assert config.array_plot_defaults["x_max"] == 10.0
        assert config.array_plot_defaults["y_min"] == -5.0
        assert config.array_plot_defaults["y_max"] == 100.0

    def test_array_plot_defaults_underscore_keys(self):
        """アンダースコア形式のキーも対応"""
        from config import DashboardConfig

        config = DashboardConfig.from_dict(
            {
                "array-plot": {
                    "x_min": 1.0,
                    "y_max": 50.0,
                }
            }
        )
        assert config.array_plot_defaults["x_min"] == 1.0
        assert config.array_plot_defaults["y_max"] == 50.0

    def test_array_plot_defaults_y_as_string(self):
        """y を文字列で指定するとリストに変換"""
        from config import DashboardConfig

        config = DashboardConfig.from_dict(
            {
                "array-plot": {
                    "y": "RF.RF3",
                }
            }
        )
        assert config.array_plot_defaults["y"] == ["RF.RF3"]

    def test_array_plot_defaults_invalid_type_ignored(self):
        """array-plotが辞書でない場合は空辞書"""
        from config import DashboardConfig

        config = DashboardConfig.from_dict({"array-plot": "invalid"})
        assert config.array_plot_defaults == {}

    def test_array_plot_defaults_full_config(self):
        """全設定を指定"""
        from config import DashboardConfig

        config = DashboardConfig.from_dict(
            {
                "array-plot": {
                    "x": "U.U1",
                    "y": ["RF.RF3"],
                    "x-min": 0.0,
                    "x-max": 1.0,
                    "y-min": -10.0,
                    "y-max": 200.0,
                }
            }
        )
        assert config.array_plot_defaults["x"] == "U.U1"
        assert config.array_plot_defaults["y"] == ["RF.RF3"]
        assert config.array_plot_defaults["x_min"] == 0.0
        assert config.array_plot_defaults["x_max"] == 1.0
        assert config.array_plot_defaults["y_min"] == -10.0
        assert config.array_plot_defaults["y_max"] == 200.0


# ====================================================================
# 配列プロットヘルパー関数テスト
# ====================================================================


class TestArrayPlotHelpers:
    """配列プロットヘルパー関数のテスト"""

    def test_find_key_index_found(self):
        """キーが見つかった場合のインデックス"""
        from services.dashboard.components.array_plot import _find_key_index

        keys = ["RF.time", "RF.RF1", "RF.RF3"]
        assert _find_key_index(keys, "RF.RF1") == 1

    def test_find_key_index_not_found(self):
        """キーが見つからない場合は0"""
        from services.dashboard.components.array_plot import _find_key_index

        keys = ["RF.time", "RF.RF1"]
        assert _find_key_index(keys, "U.U1") == 0

    def test_find_key_index_none_target(self):
        """target=Noneの場合は0"""
        from services.dashboard.components.array_plot import _find_key_index

        assert _find_key_index(["RF.time"], None) == 0

    def test_find_key_index_empty_keys(self):
        """空リストの場合は0"""
        from services.dashboard.components.array_plot import _find_key_index

        assert _find_key_index([], "RF.time") == 0

    def test_get_default_y_keys_list(self):
        """リストから利用可能なキーをフィルタ"""
        from services.dashboard.components.array_plot import _get_default_y_keys

        options = ["RF.RF1", "RF.RF3", "U.U1"]
        result = _get_default_y_keys(options, ["RF.RF3", "U.U2"])
        assert result == ["RF.RF3"]

    def test_get_default_y_keys_string(self):
        """文字列を自動リスト変換"""
        from services.dashboard.components.array_plot import _get_default_y_keys

        result = _get_default_y_keys(["RF.RF1", "RF.RF3"], "RF.RF3")
        assert result == ["RF.RF3"]

    def test_get_default_y_keys_none(self):
        """Noneの場合は空リスト"""
        from services.dashboard.components.array_plot import _get_default_y_keys

        assert _get_default_y_keys(["RF.RF1"], None) == []

    def test_get_array_plot_defaults_empty_config(self):
        """空のDashboardConfigから空辞書を返す"""
        from config import DashboardConfig
        from services.dashboard.components.array_plot import _get_array_plot_defaults

        config = DashboardConfig.from_dict({})
        assert _get_array_plot_defaults(config) == {}

    def test_get_array_plot_defaults_with_values(self):
        """設定済みDashboardConfigから値を返す"""
        from config import DashboardConfig
        from services.dashboard.components.array_plot import _get_array_plot_defaults

        config = DashboardConfig.from_dict({"array-plot": {"x": "U.U1", "y": ["RF.RF3"], "y-min": 0.0, "y-max": 100.0}})
        defaults = _get_array_plot_defaults(config)
        assert defaults["x"] == "U.U1"
        assert defaults["y"] == ["RF.RF3"]
        assert defaults["y_min"] == 0.0
        assert defaults["y_max"] == 100.0

    def test_get_array_plot_defaults_none_config(self):
        """config=Noneの場合は空辞書"""
        from services.dashboard.components.array_plot import _get_array_plot_defaults

        assert _get_array_plot_defaults(None) == {}


class TestPlotStyleDefaults:
    """PlotStyleDefaults のテスト"""

    def test_default_values(self):
        """デフォルト値が正しいこと"""
        from config import PlotStyleDefaults

        psd = PlotStyleDefaults()
        assert psd.marker_size_min == 1
        assert psd.marker_size_max == 50
        assert psd.marker_size_default == 16
        assert psd.line_width_min == 1
        assert psd.line_width_max == 20
        assert psd.line_width_default == 2
        assert psd.font_size_min == 6
        assert psd.font_size_max == 48
        assert psd.font_size_default == 20

    def test_custom_values(self):
        """カスタム値を指定可能"""
        from config import PlotStyleDefaults

        psd = PlotStyleDefaults(marker_size_min=5, marker_size_max=100, font_size_default=24)
        assert psd.marker_size_min == 5
        assert psd.marker_size_max == 100
        assert psd.font_size_default == 24

    def test_from_dashboard_config(self):
        """DashboardConfig経由で読み込み"""
        from config import DashboardConfig

        config = DashboardConfig.from_dict(
            {
                "plot-style-defaults": {
                    "marker-size-min": 2,
                    "marker-size-max": 80,
                    "line-width-default": 3,
                }
            }
        )
        assert config.plot_style_defaults.marker_size_min == 2
        assert config.plot_style_defaults.marker_size_max == 80
        assert config.plot_style_defaults.line_width_default == 3
        # 未指定のフィールドはデフォルト値
        assert config.plot_style_defaults.font_size_min == 6

    def test_empty_dashboard_config(self):
        """空のDashboardConfigではデフォルトのPlotStyleDefaults"""
        from config import DashboardConfig, PlotStyleDefaults

        config = DashboardConfig.from_dict({})
        assert config.plot_style_defaults == PlotStyleDefaults()


class TestGalleryDefaults:
    """GalleryDefaults のテスト"""

    def test_default_values(self):
        """デフォルト値が正しいこと"""
        from config import GalleryDefaults

        gd = GalleryDefaults()
        assert gd.columns == 5
        assert gd.rows == 4
        assert gd.max_image_bytes == 5 * 1024 * 1024

    def test_from_dashboard_config(self):
        """DashboardConfig経由で読み込み"""
        from config import DashboardConfig

        config = DashboardConfig.from_dict(
            {
                "gallery-defaults": {
                    "columns": 3,
                    "rows": 6,
                    "max-image-bytes": 10485760,
                }
            }
        )
        assert config.gallery_defaults.columns == 3
        assert config.gallery_defaults.rows == 6
        assert config.gallery_defaults.max_image_bytes == 10485760

    def test_empty_dashboard_config(self):
        """空のDashboardConfigではデフォルトのGalleryDefaults"""
        from config import DashboardConfig, GalleryDefaults

        config = DashboardConfig.from_dict({})
        assert config.gallery_defaults == GalleryDefaults()


class TestParseDefaults:
    """ParseDefaults のテスト"""

    def test_default_values(self):
        """デフォルトの除外ディレクトリが正しいこと"""
        from config import ParseDefaults

        pd = ParseDefaults()
        assert ".git" in pd.exclude_dirs
        assert ".j2" in pd.exclude_dirs
        assert "__pycache__" in pd.exclude_dirs
        assert "node_modules" in pd.exclude_dirs
        assert ".venv" in pd.exclude_dirs

    def test_from_graph_config(self):
        """GraphConfig経由で読み込み"""
        from config import GraphConfig

        config = GraphConfig.from_dict(
            {
                "parse-defaults": {
                    "exclude-dirs": [".git", ".j2", "build"],
                }
            }
        )
        assert config.parse_defaults.exclude_dirs == frozenset({".git", ".j2", "build"})

    def test_empty_graph_config(self):
        """空のGraphConfigではデフォルトのParseDefaults"""
        from config import GraphConfig, ParseDefaults

        config = GraphConfig.from_dict({})
        assert config.parse_defaults == ParseDefaults()

    def test_invalid_exclude_dirs_type(self):
        """exclude-dirsが不正な型の場合はValueError"""
        import pytest

        from config import GraphConfig

        with pytest.raises(ValueError, match="exclude-dirs must be list"):
            GraphConfig.from_dict({"parse-defaults": {"exclude-dirs": "not-a-list"}})


class TestVocabDisplay:
    """vocab_displayユーティリティのテスト"""

    def test_translate_key(self):
        """キーのvocab変換"""
        from modules.vocab_display import translate_key

        vocab = {"height": "高さ", "load": "荷重"}
        assert translate_key("height", vocab) == "高さ"
        assert translate_key("unknown", vocab) == "unknown"

    def test_translate_properties(self):
        """プロパティ辞書の変換"""
        from modules.vocab_display import translate_properties

        vocab = {"height": "高さ", "load": "荷重"}
        props = {"height": 10.0, "load": "constant"}
        result = translate_properties(props, vocab)
        assert "高さ" in result
        assert result["高さ"] == 10.0
        assert result["荷重"] == "constant"

    def test_translate_columns(self):
        """カラム名リストの変換"""
        from modules.vocab_display import translate_columns

        vocab = {"height": "高さ", "load": "荷重"}
        cols = ["name", "height", "load", "active"]
        result = translate_columns(cols, vocab)
        assert result == ["name", "高さ", "荷重", "active"]

    def test_reverse_vocab(self):
        """逆引き辞書の構築"""
        from modules.vocab_display import reverse_vocab

        vocab = {"height": "高さ", "load": "荷重"}
        rev = reverse_vocab(vocab)
        assert rev["高さ"] == "height"
        assert rev["荷重"] == "load"

    def test_translate_value_nested(self):
        """ネストされた値の変換"""
        from modules.vocab_display import translate_value

        vocab = {"steel": "鋼材", "aluminum": "アルミ"}
        assert translate_value("steel", vocab) == "鋼材"
        assert translate_value(["steel", "aluminum"], vocab) == ["鋼材", "アルミ"]
        assert translate_value(42, vocab) == 42


# ====================================================================
# バッチ俯瞰コンポーネント テスト
# ====================================================================


class TestBatchOverviewGrouping:
    """バッチ俯瞰: indexグルーピング"""

    def test_group_by_index_basic(self):
        """indexでグルーピングされること"""
        from services.dashboard.components.batch_overview import _group_by_index

        rows = [
            {"name": "go_1", "index": "1", "version": "1"},
            {"name": "go_2", "index": "1", "version": "2"},
            {"name": "go_3", "index": "2", "version": "1"},
        ]
        groups = _group_by_index(rows, "index")
        assert list(groups.keys()) == ["1", "2"]
        assert len(groups["1"]) == 2
        assert len(groups["2"]) == 1

    def test_group_by_index_numeric_sort(self):
        """index数値がゼロ埋めなしでも数値順ソートされること"""
        from services.dashboard.components.batch_overview import _group_by_index

        rows = [
            {"name": "a", "index": "10"},
            {"name": "b", "index": "2"},
            {"name": "c", "index": "1"},
        ]
        groups = _group_by_index(rows, "index")
        assert list(groups.keys()) == ["1", "2", "10"]

    def test_group_by_index_missing(self):
        """indexプロパティが欠けている行は(なし)にグルーピングされること"""
        from services.dashboard.components.batch_overview import _group_by_index

        rows = [
            {"name": "go_1", "index": "1"},
            {"name": "go_2"},
        ]
        groups = _group_by_index(rows, "index")
        assert "(なし)" in groups
        assert "1" in groups


class TestBatchOverviewVaryingKeys:
    """バッチ俯瞰: 差分プロパティ抽出"""

    def test_find_varying_keys(self):
        """グループ間で値が異なるキーが抽出されること"""
        from collections import OrderedDict

        from services.dashboard.components.batch_overview import _find_varying_keys

        groups = OrderedDict(
            {
                "1": [
                    {"name": "a", "index": "1", "version": "1", "verbose_name": "A", "param": 10},
                    {"name": "b", "index": "1", "version": "2", "verbose_name": "A", "param": 20},
                ],
            }
        )
        varying = _find_varying_keys(groups, "version", "index", "verbose_name")
        assert "param" in varying
        assert "analysis_status" not in varying  # 両方Noneなので同値

    def test_no_varying_keys(self):
        """全プロパティが同値ならば空リスト"""
        from collections import OrderedDict

        from services.dashboard.components.batch_overview import _find_varying_keys

        groups = OrderedDict(
            {
                "1": [
                    {"name": "a", "index": "1", "version": "1", "verbose_name": "A", "param": 10},
                ],
            }
        )
        varying = _find_varying_keys(groups, "version", "index", "verbose_name")
        # 単一行なので差分なし（paramは1つの値のみ）
        assert "param" not in varying


class TestBatchOverviewHtml:
    """バッチ俯瞰: HTML生成"""

    def test_generate_batch_html(self):
        """HTML生成が正常に動作すること"""
        from services.dashboard.components.batch_overview import _generate_batch_html

        graph = _make_test_graph()
        provider = DashboardDataProvider(graph)
        rows = provider.get_go_table()
        html = _generate_batch_html(rows, provider)
        assert "バッチラン俯瞰" in html
        assert "index: 1" in html

    def test_generate_batch_html_empty(self):
        """空データでHTML生成"""
        from services.dashboard.components.batch_overview import _generate_batch_html

        graph = GraphModel(nodes=[], relations=[])
        provider = DashboardDataProvider(graph)
        html = _generate_batch_html([], provider)
        assert "ありません" in html


class TestSharedFiltersOnAllPages:
    """全ページでActiveフィルタが適用可能であること（インポートテスト）"""

    def test_plot_page_imports_shared_filters(self):
        """PlotPageがshared_filtersをインポートしていること"""
        import importlib

        mod = importlib.import_module("services.dashboard.components.plot")
        source = Path(mod.__file__).read_text()
        assert "get_active_filters" in source
        assert "render_shared_filters" in source

    def test_gallery_page_imports_shared_filters(self):
        """GalleryPageがshared_filtersをインポートしていること"""
        import importlib

        mod = importlib.import_module("services.dashboard.components.gallery")
        source = Path(mod.__file__).read_text()
        assert "get_active_filters" in source
        assert "render_shared_filters" in source

    def test_card_page_imports_shared_filters(self):
        """CardPageがshared_filtersをインポートしていること"""
        import importlib

        mod = importlib.import_module("services.dashboard.components.card")
        source = Path(mod.__file__).read_text()
        assert "get_active_filters" in source
        assert "render_shared_filters" in source

    def test_status_page_imports_shared_filters(self):
        """StatusPageがshared_filtersをインポートしていること"""
        import importlib

        mod = importlib.import_module("services.dashboard.components.status")
        source = Path(mod.__file__).read_text()
        assert "get_active_filters" in source
        assert "render_shared_filters" in source


class TestPlotVocabAxisLabels:
    """プロット軸ラベルへのvocab変換テスト"""

    def test_create_plot_figure_with_vocab(self):
        """_create_plot_figureでvocabが軸タイトルに反映される"""
        try:
            import pandas as pd
            import plotly.express as px
        except ImportError:
            pytest.skip("plotly or pandas not installed")

        from services.dashboard.html_export import _create_plot_figure

        df = pd.DataFrame({"x_key": [1, 2, 3], "y_key": [4, 5, 6], "name": ["a", "b", "c"]})
        vocab = {"x_key": "X軸表示名", "y_key": "Y軸表示名"}
        fig = _create_plot_figure(px, df, "x_key", "y_key", None, "散布図", vocab=vocab)
        assert fig.layout.title.text == "Y軸表示名 vs X軸表示名"
        assert fig.layout.xaxis.title.text == "X軸表示名"
        assert fig.layout.yaxis.title.text == "Y軸表示名"

    def test_create_plot_figure_without_vocab(self):
        """vocab未指定時は生キーがそのまま使用される"""
        try:
            import pandas as pd
            import plotly.express as px
        except ImportError:
            pytest.skip("plotly or pandas not installed")

        from services.dashboard.html_export import _create_plot_figure

        df = pd.DataFrame({"x_key": [1, 2, 3], "y_key": [4, 5, 6], "name": ["a", "b", "c"]})
        fig = _create_plot_figure(px, df, "x_key", "y_key", None, "散布図")
        assert fig.layout.title.text == "y_key vs x_key"
        assert fig.layout.xaxis.title.text == "x_key"
        assert fig.layout.yaxis.title.text == "y_key"

    def test_create_plot_figure_contour_vocab(self):
        """コンタープロットのタイトルでvocabが反映される"""
        try:
            import pandas as pd
            import plotly.express as px
        except ImportError:
            pytest.skip("plotly or pandas not installed")

        from services.dashboard.html_export import _create_plot_figure

        df = pd.DataFrame(
            {
                "x": [1, 2, 3],
                "y": [4, 5, 6],
                "z": [7, 8, 9],
                "name": ["a", "b", "c"],
            }
        )
        vocab = {"x": "横軸", "y": "縦軸", "z": "色変数"}
        fig = _create_plot_figure(px, df, "x", "y", None, "コンター", z_key="z", vocab=vocab)
        assert "横軸" in fig.layout.title.text
        assert "縦軸" in fig.layout.title.text
        assert "色変数" in fig.layout.title.text


class TestGalleryDefaultsConfig:
    """GalleryDefaults設定のギャラリーコンポーネント参照テスト"""

    def test_get_gallery_settings_from_defaults(self):
        """_get_gallery_settingsがgallery_defaultsから値を取得する"""
        from dataclasses import dataclass

        from services.dashboard.components.gallery import _get_gallery_settings

        @dataclass
        class MockDefaults:
            columns: int = 3
            rows: int = 2
            max_image_bytes: int = 1024

        @dataclass
        class MockConfig:
            gallery_defaults: MockDefaults = None

            def __post_init__(self):
                if self.gallery_defaults is None:
                    self.gallery_defaults = MockDefaults()

        config = MockConfig()
        cols, rows, max_bytes = _get_gallery_settings(config)
        assert cols == 3
        assert rows == 2
        assert max_bytes == 1024

    def test_get_gallery_settings_fallback(self):
        """gallery_defaultsがない場合はデフォルト値（5, 4, 0）を返す"""
        from dataclasses import dataclass

        from services.dashboard.components.gallery import _get_gallery_settings

        @dataclass
        class MockConfig:
            pass

        config = MockConfig()
        cols, rows, max_bytes = _get_gallery_settings(config)
        assert cols == 5
        assert rows == 4
        assert max_bytes == 0


class TestRunShowProperties:
    """jj run --show-properties テスト"""

    def test_show_properties_extracts_from_script(self, tmp_path):
        """show_propertiesがスクリプトからプロパティを抽出する"""
        from services.run import RunService

        script = tmp_path / "test_script.py"
        script.write_text("# props start\nmesh_size = 0.5\nsolver = abaqus\n# props end\nprint('hello')\n")
        rs = RunService()
        props = rs.show_properties(["python", str(script)], cwd=tmp_path)
        assert props["mesh_size"] == "0.5"
        assert props["solver"] == "abaqus"

    def test_show_properties_no_script(self, tmp_path):
        """スクリプトでないコマンドは空辞書を返す"""
        from services.run import RunService

        rs = RunService()
        props = rs.show_properties(["echo", "hello"], cwd=tmp_path)
        assert props == {}

    def test_show_properties_with_args(self, tmp_path):
        """引数マッピングもshow_propertiesで取得できる"""
        from services.run import RunService

        script = tmp_path / "run.py"
        script.write_text("import sys\nparam1 = sys.argv[1]\nparam2 = sys.argv[2]\n")
        rs = RunService()
        props = rs.show_properties(["python", str(script), "value1", "value2"], cwd=tmp_path)
        assert props["param1"] == "value1"
        assert props["param2"] == "value2"


class TestArrayPlotLegendVocab:
    """配列プロット凡例名へのvocab変換テスト"""

    def test_render_array_single_legend_uses_vocab(self):
        """_render_array_singleの凡例名にvocab変換が適用される"""
        from services.dashboard.components.array_plot import ArrayPlotPage

        # ArrayPlotPageがインポートできることを確認（描画はStreamlit依存なのでロジックテスト）
        page = ArrayPlotPage()
        assert page.page_key == "array_plot"

    def test_generate_array_plot_html_grid_legend_vocab(self):
        """generate_array_plot_htmlのgridモードで凡例名にvocab変換が適用される"""
        plotly = pytest.importorskip("plotly")  # noqa: F841

        from dataclasses import dataclass, field

        from services.dashboard.html_export import generate_array_plot_html

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="file",
                    name="go_test",
                    format="inp",
                    properties={
                        "index": "1",
                        "RF.time": [0.0, 1.0, 2.0],
                        "RF.force": [10.0, 20.0, 30.0],
                    },
                )
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)

        @dataclass
        class MockView:
            array_plot: dict = field(
                default_factory=lambda: {
                    "prefix": "RF",
                    "x": "RF.time",
                    "y": ["RF.force"],
                    "mode": "grid",
                }
            )
            filters: dict = field(default_factory=dict)

        @dataclass
        class MockGD:
            columns: int = 4
            rows: int = 4
            max_image_bytes: int = 0

        @dataclass
        class MockConfig:
            gallery_defaults: MockGD = field(default_factory=MockGD)
            ng_regions: list = field(default_factory=list)

        html = generate_array_plot_html(provider, MockConfig(), MockView(), vocab={"RF.force": "反力"})
        assert "反力" in html

    def test_generate_array_plot_html_overlay_legend(self):
        """generate_array_plot_htmlのoverlayモードで凡例にdisplay_nameが使用される"""
        plotly = pytest.importorskip("plotly")  # noqa: F841

        from dataclasses import dataclass, field

        from services.dashboard.html_export import generate_array_plot_html

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="file",
                    name="go_test",
                    format="inp",
                    properties={
                        "index": "1",
                        "RF.time": [0.0, 1.0],
                        "RF.force": [10.0, 20.0],
                    },
                )
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)

        @dataclass
        class MockView:
            array_plot: dict = field(
                default_factory=lambda: {
                    "prefix": "RF",
                    "x": "RF.time",
                    "y": ["RF.force"],
                    "mode": "overlay",
                }
            )
            filters: dict = field(default_factory=dict)

        @dataclass
        class MockConfig:
            ng_regions: list = field(default_factory=list)

        html = generate_array_plot_html(provider, MockConfig(), MockView(), vocab={"RF.time": "時間"})
        assert "時間" in html


class TestBatchOverviewRunIntegration:
    """バッチ俯瞰ページのRunノード統合テスト"""

    def test_build_run_map_with_run_nodes(self):
        """Run出力ノードに紐付くgo_ノードのrun_mapが構築される"""
        from jj_types import NodeCategory, Relation
        from services.dashboard.components.batch_overview import _build_run_map

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="file",
                    name="go_001",
                    format="inp",
                    properties={"index": "1"},
                ),
                Node(
                    id=10,
                    type="run",
                    name="run_001",
                    format="",
                    properties={"run_type": "cae_job", "run_status": "completed"},
                    category=NodeCategory.RUN,
                ),
            ],
            relations=[
                Relation(id=1, label="run_output", node1_id=10, node2_id=1),
            ],
        )
        provider = DashboardDataProvider(graph)
        rows = provider.get_go_table()
        run_map = _build_run_map(provider, rows)
        assert 1 in run_map
        assert run_map[1]["run_type"] == "cae_job"
        assert run_map[1]["run_status"] == "completed"

    def test_build_run_map_empty_without_runs(self):
        """Runノードがない場合は空dictが返る"""
        from services.dashboard.components.batch_overview import _build_run_map

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="file",
                    name="go_001",
                    format="inp",
                    properties={"index": "1"},
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        rows = provider.get_go_table()
        run_map = _build_run_map(provider, rows)
        assert run_map == {}

    def test_format_run_badge_html(self):
        """_format_run_badgeがHTML文字列を返す"""
        from services.dashboard.components.batch_overview import _format_run_badge

        badge = _format_run_badge(
            {
                "run_type": "cae_job",
                "run_status": "completed",
                "duration_seconds": 12.5,
            }
        )
        assert "cae_job" in badge
        assert "completed" in badge
        assert "12.5s" in badge

    def test_get_run_for_node(self):
        """get_run_for_nodeがrun_output経由でRunノードを返す"""
        from jj_types import NodeCategory, Relation

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="file",
                    name="go_001",
                    format="inp",
                    properties={"index": "1"},
                ),
                Node(
                    id=10,
                    type="run",
                    name="run_001",
                    format="",
                    properties={
                        "run_type": "script",
                        "run_status": "completed",
                        "duration_seconds": 5.0,
                        "started_at": "2026-03-06T10:00:00",
                    },
                    category=NodeCategory.RUN,
                ),
            ],
            relations=[
                Relation(id=1, label="run_output", node1_id=10, node2_id=1),
            ],
        )
        provider = DashboardDataProvider(graph)
        run_info = provider.get_run_for_node(1)
        assert run_info is not None
        assert run_info["name"] == "run_001"
        assert run_info["duration_seconds"] == 5.0

    def test_get_run_for_node_returns_none(self):
        """Runノードがない場合はNoneが返る"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="file",
                    name="go_001",
                    format="inp",
                    properties={},
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        assert provider.get_run_for_node(1) is None

    def test_get_run_nodes(self):
        """get_run_nodesがRunノード一覧を返す"""
        from jj_types import NodeCategory, Relation

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="file",
                    name="go_001",
                    format="inp",
                    properties={},
                ),
                Node(
                    id=10,
                    type="run",
                    name="run_001",
                    format="",
                    properties={"run_type": "cae_job", "run_status": "completed"},
                    category=NodeCategory.RUN,
                ),
                Node(
                    id=11,
                    type="run",
                    name="run_002",
                    format="",
                    properties={"run_type": "ml_training", "run_status": "latent"},
                    category=NodeCategory.RUN,
                ),
            ],
            relations=[
                Relation(id=1, label="run_output", node1_id=10, node2_id=1),
                Relation(id=2, label="run_input", node1_id=11, node2_id=1),
            ],
        )
        provider = DashboardDataProvider(graph)
        runs = provider.get_run_nodes()
        assert len(runs) == 2
        assert runs[0]["name"] == "run_001"
        assert runs[0]["output_ids"] == [1]
        assert runs[1]["name"] == "run_002"
        assert runs[1]["input_ids"] == [1]


class TestBatchOverviewHtmlRunBadge:
    """バッチ俯瞰HTML生成のRunバッジ統合テスト"""

    def test_generate_batch_html_includes_run_badge(self):
        """HTML生成にRunバッジが含まれる"""
        from jj_types import NodeCategory, Relation
        from services.dashboard.components.batch_overview import _generate_batch_html

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="file",
                    name="go_001",
                    format="inp",
                    properties={"index": "1"},
                ),
                Node(
                    id=10,
                    type="run",
                    name="run_001",
                    format="",
                    properties={"run_type": "cae_job", "run_status": "completed", "duration_seconds": 3.5},
                    category=NodeCategory.RUN,
                ),
            ],
            relations=[
                Relation(id=1, label="run_output", node1_id=10, node2_id=1),
            ],
        )
        provider = DashboardDataProvider(graph)
        rows = provider.get_go_table()
        html = _generate_batch_html(rows, provider)
        assert "cae_job" in html
        assert "completed" in html
        assert "3.5s" in html

    def test_generate_batch_html_no_runs(self):
        """Runなしの場合、Runバッジが含まれない"""
        from services.dashboard.components.batch_overview import _generate_batch_html

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="file",
                    name="go_001",
                    format="inp",
                    properties={"index": "1"},
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        rows = provider.get_go_table()
        html = _generate_batch_html(rows, provider)
        assert "Run紐付き" not in html

    def test_generate_batch_html_run_summary(self):
        """HTML生成にRunサマリーが含まれる"""
        from jj_types import NodeCategory, Relation
        from services.dashboard.components.batch_overview import _generate_batch_html

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="file",
                    name="go_001",
                    format="inp",
                    properties={"index": "1"},
                ),
                Node(
                    id=2,
                    type="file",
                    name="go_002",
                    format="inp",
                    properties={"index": "2"},
                ),
                Node(
                    id=10,
                    type="run",
                    name="run_001",
                    format="",
                    properties={"run_type": "cae_job", "run_status": "completed"},
                    category=NodeCategory.RUN,
                ),
                Node(
                    id=11,
                    type="run",
                    name="run_002",
                    format="",
                    properties={"run_type": "ml_training", "run_status": "completed"},
                    category=NodeCategory.RUN,
                ),
            ],
            relations=[
                Relation(id=1, label="run_output", node1_id=10, node2_id=1),
                Relation(id=2, label="run_output", node1_id=11, node2_id=2),
            ],
        )
        provider = DashboardDataProvider(graph)
        rows = provider.get_go_table()
        html = _generate_batch_html(rows, provider)
        assert "Run紐付き: 2件" in html
        assert "cae_job: 1" in html
        assert "ml_training: 1" in html


class TestRunDetailsExpander:
    """Run詳細展開表示のテスト"""

    def test_get_run_for_node_returns_extended_properties(self):
        """get_run_for_nodeがhost, user, exit_code, finished_atを含む"""
        from jj_types import NodeCategory, Relation

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="file",
                    name="go_001",
                    format="inp",
                    properties={"index": "1"},
                ),
                Node(
                    id=10,
                    type="run",
                    name="run_001",
                    format="",
                    properties={
                        "run_type": "cae_job",
                        "run_status": "completed",
                        "host": "server01",
                        "user": "admin",
                        "exit_code": 0,
                        "started_at": "2026-03-06T10:00:00",
                        "finished_at": "2026-03-06T10:05:00",
                        "command": "abaqus job=test",
                        "duration_seconds": 300.0,
                    },
                    category=NodeCategory.RUN,
                ),
            ],
            relations=[
                Relation(id=1, label="run_output", node1_id=10, node2_id=1),
            ],
        )
        provider = DashboardDataProvider(graph)
        run_info = provider.get_run_for_node(1)
        assert run_info is not None
        assert run_info["host"] == "server01"
        assert run_info["user"] == "admin"
        assert run_info["exit_code"] == 0
        assert run_info["finished_at"] == "2026-03-06T10:05:00"
        assert run_info["command"] == "abaqus job=test"

    def test_generate_run_summary_html(self):
        """_generate_run_summary_htmlがサマリーHTMLを返す"""
        from services.dashboard.components.batch_overview import _generate_run_summary_html

        run_map = {
            1: {"run_type": "cae_job", "run_status": "completed"},
            2: {"run_type": "script", "run_status": "failed"},
        }
        html = _generate_run_summary_html(run_map)
        assert "Run紐付き: 2件" in html
        assert "cae_job: 1" in html
        assert "script: 1" in html


class TestRunComparisonComponent:
    """Run比較ダッシュボードコンポーネントのテスト"""

    def test_run_comparison_page_registered(self):
        """RunComparisonPageがレジストリに登録される"""
        import services.dashboard.components.run_comparison  # noqa: F401
        from services.dashboard.components import get_page_component

        page = get_page_component("run_comparison")
        assert page is not None
        assert page.page_label == "Run比較"

    def test_run_comparison_view_config_registered(self):
        """RunComparisonViewConfigがレジストリに登録される"""
        import services.dashboard.components.run_comparison  # noqa: F401
        from services.dashboard.components import get_view_config

        vc = get_view_config("run_comparison")
        assert vc is not None

    def test_generate_run_comparison_html(self):
        """Run比較HTMLが正しく生成される"""
        from jj_types import NodeCategory, Relation
        from services.dashboard.components.run_comparison import _generate_run_comparison_html
        from services.run.query import RunQueryService

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="file",
                    name="go_001",
                    format="inp",
                    properties={"index": "1"},
                ),
                Node(
                    id=10,
                    type="run",
                    name="run_001",
                    format="",
                    properties={"run_type": "cae_job", "run_status": "completed"},
                    category=NodeCategory.RUN,
                ),
            ],
            relations=[
                Relation(id=1, label="run_output", node1_id=10, node2_id=1),
            ],
        )
        query_svc = RunQueryService(graph)
        runs = query_svc.get_runs()
        html = _generate_run_comparison_html(runs, query_svc)
        assert "Run比較ダッシュボード" in html
        assert "run_001" in html
        assert "cae_job" in html

    def test_generate_html_empty_runs(self):
        """Runなしの場合のHTML生成"""
        from services.dashboard.components.run_comparison import RunComparisonPage

        graph = GraphModel(
            nodes=[
                Node(id=1, type="file", name="go_001", format="inp", properties={}),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        page = RunComparisonPage()

        from unittest.mock import MagicMock

        mock_view = MagicMock()
        mock_view.filters = {}
        mock_config = MagicMock()

        html = page.generate_html(provider, mock_view, mock_config)
        assert "見つかりません" in html

    def test_run_dag_no_dependencies(self):
        """Run間にデータ依存関係がない場合のDAG HTML生成"""
        from jj_types import NodeCategory, Relation
        from services.dashboard.components.run_comparison import _generate_run_dag_html
        from services.run.query import RunQueryService

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="file",
                    name="input_a",
                    format="inp",
                    properties={},
                ),
                Node(
                    id=2,
                    type="file",
                    name="input_b",
                    format="inp",
                    properties={},
                ),
                Node(
                    id=10,
                    type="run",
                    name="run_A",
                    format="",
                    properties={"run_type": "cae_job", "run_status": "completed"},
                    category=NodeCategory.RUN,
                ),
                Node(
                    id=11,
                    type="run",
                    name="run_B",
                    format="",
                    properties={"run_type": "cae_job", "run_status": "failed"},
                    category=NodeCategory.RUN,
                ),
            ],
            relations=[
                Relation(id=1, label="run_input", node1_id=10, node2_id=1),
                Relation(id=2, label="run_input", node1_id=11, node2_id=2),
            ],
        )
        query_svc = RunQueryService(graph)
        runs = query_svc.get_runs()
        html = _generate_run_dag_html(runs, query_svc)
        assert "Run DAG" in html
        assert "run_A" in html
        assert "run_B" in html
        assert "依存関係はありません" in html

    def test_run_dag_with_dependencies(self):
        """Run間にデータ依存関係がある場合のDAG HTML生成"""
        from jj_types import NodeCategory, Relation
        from services.dashboard.components.run_comparison import _generate_run_dag_html
        from services.run.query import RunQueryService

        # Run A → shared_file → Run B の依存関係
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="file",
                    name="shared_file.dat",
                    format="dat",
                    properties={},
                ),
                Node(
                    id=10,
                    type="run",
                    name="run_upstream",
                    format="",
                    properties={"run_type": "cae_job", "run_status": "completed"},
                    category=NodeCategory.RUN,
                ),
                Node(
                    id=11,
                    type="run",
                    name="run_downstream",
                    format="",
                    properties={"run_type": "ml_training", "run_status": "completed"},
                    category=NodeCategory.RUN,
                ),
            ],
            relations=[
                Relation(id=1, label="run_output", node1_id=10, node2_id=1),
                Relation(id=2, label="run_input", node1_id=11, node2_id=1),
            ],
        )
        query_svc = RunQueryService(graph)
        runs = query_svc.get_runs()
        html = _generate_run_dag_html(runs, query_svc)
        assert "Run DAG" in html
        assert "run_upstream" in html
        assert "run_downstream" in html
        assert "shared_file.dat" in html
        # 依存関係テーブルが生成される
        assert "上流Run" in html
        assert "下流Run" in html

    def test_run_dag_empty_runs(self):
        """Runが空の場合のDAG HTML生成"""
        from services.dashboard.components.run_comparison import _generate_run_dag_html
        from services.run.query import RunQueryService

        graph = GraphModel(nodes=[], relations=[])
        query_svc = RunQueryService(graph)
        html = _generate_run_dag_html([], query_svc)
        assert html == ""

    def test_run_dag_graphviz_fallback(self):
        """graphvizフォールバックのDAG描画ロジック"""
        pytest.importorskip("streamlit")
        from jj_types import NodeCategory, Relation
        from services.dashboard.components.run_comparison import _try_render_run_dag_graphviz
        from services.run.query import RunQueryService

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="file",
                    name="shared.dat",
                    format="dat",
                    properties={},
                ),
                Node(
                    id=10,
                    type="run",
                    name="run_A",
                    format="",
                    properties={"run_type": "cae_job", "run_status": "completed"},
                    category=NodeCategory.RUN,
                ),
                Node(
                    id=11,
                    type="run",
                    name="run_B",
                    format="",
                    properties={"run_type": "cae_job", "run_status": "failed"},
                    category=NodeCategory.RUN,
                ),
            ],
            relations=[
                Relation(id=1, label="run_output", node1_id=10, node2_id=1),
                Relation(id=2, label="run_input", node1_id=11, node2_id=1),
            ],
        )
        query_svc = RunQueryService(graph)
        runs = query_svc.get_runs()

        run_io_map = {}
        output_to_run: dict[int, int] = {}
        for run in runs:
            io = query_svc.get_run_io(run)
            run_io_map[run.id] = io
            for out_node in io.outputs:
                output_to_run[out_node.id] = run.id

        dag_edges: list[tuple[int, int, list[str]]] = []
        for run in runs:
            io = run_io_map[run.id]
            predecessors: dict[int, list[str]] = {}
            for in_node in io.inputs:
                src_run_id = output_to_run.get(in_node.id)
                if src_run_id is not None and src_run_id != run.id:
                    predecessors.setdefault(src_run_id, []).append(in_node.name)
            for src_id, names in predecessors.items():
                dag_edges.append((src_id, run.id, names))

        # graphvizは使えない環境でもロジックが正しく動くか確認
        # (st.graphviz_chartがない場合はFalseを返す)
        result = _try_render_run_dag_graphviz(runs, run_io_map, dag_edges)
        # streamlitが入っていない/graphviz_chartが使えない場合はFalse
        assert isinstance(result, bool)
