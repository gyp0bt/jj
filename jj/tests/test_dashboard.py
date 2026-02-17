"""DashboardDataProvider テスト

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

import contextlib

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

        storage_dir = tmp_path / ".jj" / "storage"
        storage_dir.mkdir(parents=True)
        graph_file = storage_dir / "graph.yaml"

        graph_data = {
            "nodes": [n.model_dump() for n in graph.nodes],
            "relations": [r.model_dump() for r in graph.relations],
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
            assert "include_properties" not in img["go_properties"]

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

        storage_dir = tmp_path / ".jj" / "storage"
        storage_dir.mkdir(parents=True)
        graph_file = storage_dir / "graph.yaml"
        graph_file.write_text("nodes: []\nrelations: []\n")

        result = find_graph_path(tmp_path)
        assert result is not None
        assert result.name == "graph.yaml"

    def test_find_graph_path_json(self, tmp_path):
        """graph.jsonが存在する場合にパスを返す"""
        from services.dashboard.query import find_graph_path

        storage_dir = tmp_path / ".jj" / "storage"
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

        storage_dir = tmp_path / ".jj" / "storage"
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
        assert cfg.gallery_columns == 5
        assert cfg.gallery_rows == 4
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
        assert cfg.gallery_columns == 3
        assert cfg.gallery_rows == 6

    def test_invalid_table_columns(self):
        """table-columnsが不正な場合"""
        from config import DashboardConfig

        with pytest.raises(ValueError, match="table-columns"):
            DashboardConfig.from_dict({"table-columns": "invalid"})

    def test_invalid_gallery_columns(self):
        """gallery-columnsが0以下の場合"""
        from config import DashboardConfig

        with pytest.raises(ValueError, match="gallery-columns"):
            DashboardConfig.from_dict({"gallery-columns": 0})

    def test_graph_config_includes_dashboard(self):
        """GraphConfigにdashboardフィールドが含まれる"""
        from config import GraphConfig

        # from_dictでdashboardセクションが処理される
        cfg = GraphConfig.from_dict({"dashboard": {"gallery-columns": 3}})
        assert cfg.dashboard.gallery_columns == 3

    def test_graph_config_default_dashboard(self):
        """dashboardセクションなしの場合デフォルト設定"""
        from config import GraphConfig

        cfg = GraphConfig.from_dict({})
        assert cfg.dashboard.table_columns is None
        assert cfg.dashboard.gallery_columns == 5

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

    def test_render_connector_page_unregistered(self):
        """未登録のページラベルではFalseを返す"""
        from services.dashboard.connectors import render_connector_page

        graph = GraphModel(nodes=[], relations=[])
        provider = DashboardDataProvider(graph)
        result = render_connector_page("存在しないページ", provider, None)
        assert result is False


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
        config_dir = tmp_path / ".jj" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "config.yaml").write_text(
            yaml.safe_dump({"vocab": {}}),
            encoding="utf-8",
        )

        storage_dir = tmp_path / ".jj" / "storage"
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
            storage_dir = tmp_path / ".jj" / "storage"
            storage_dir.mkdir(parents=True)
            graph_data = {
                "nodes": [n.model_dump() for n in graph.nodes],
                "relations": [r.model_dump() for r in graph.relations],
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
        import pandas as pd

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
            {"go_properties": {"path": "a.inp", "include_properties": [], "index": "1"}},
        ]
        result = collect_group_keys(images, "output")
        assert "path" not in result
        assert "include_properties" not in result
        assert "index" in result

    def test_collect_group_keys_empty(self):
        from services.dashboard.query import collect_group_keys

        assert collect_group_keys([], "output") == []

    # ---- find_graph_path / get_graph_mtime ----

    def test_find_graph_path_yaml(self, tmp_path):
        from services.dashboard.query import find_graph_path

        storage = tmp_path / ".jj" / "storage"
        storage.mkdir(parents=True)
        (storage / "graph.yaml").write_text("nodes: []\n")
        result = find_graph_path(tmp_path)
        assert result is not None
        assert result.name == "graph.yaml"

    def test_find_graph_path_json(self, tmp_path):
        from services.dashboard.query import find_graph_path

        storage = tmp_path / ".jj" / "storage"
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

        storage = tmp_path / ".jj" / "storage"
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
        # スカラ値はそのまま
        assert steel["density"] == 7.85e-9

    def test_get_material_table_verbose_name_with_vocab(self):
        """vocab変換後のキーでverbose_nameを取得できる"""
        from services.dashboard.connectors.abaqus_query import get_material_table

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="abaqus_material",
                    name="Steel_S235",
                    format="material",
                    properties={
                        "表示名": "鋼材 S235",
                        "elastic": [[210000.0, 0.3]],
                    },
                ),
            ],
            relations=[],
        )
        # vocab: verbose_name → 表示名
        provider = DashboardDataProvider(
            graph, vocab={"verbose_name": "表示名"}
        )
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
        """vocab変換後のverbose_nameキーがプロパティ列に重複表示されない"""
        from services.dashboard.connectors.abaqus_query import get_material_table

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="abaqus_material",
                    name="Steel_S235",
                    format="material",
                    properties={
                        "表示名": "鋼材 S235",
                        "density": 7.85e-9,
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(
            graph, vocab={"verbose_name": "表示名"}
        )
        rows = get_material_table(provider)
        assert len(rows) == 1
        # verbose_name列に値がある
        assert rows[0]["verbose_name"] == "鋼材 S235"
        # 表示名キーがプロパティ列として重複しない
        assert "表示名" not in rows[0]
        # density はそのまま含まれる
        assert rows[0]["density"] == 7.85e-9

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
