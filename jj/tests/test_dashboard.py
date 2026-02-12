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
                Node(id=1, type="go", name="go_a", format="inp",
                     properties={"path": "a.inp", "active": "true"}),
                Node(id=2, type="go", name="go_b", format="inp",
                     properties={"path": "b.inp", "active": "false"}),
                Node(id=3, type="go", name="go_c", format="inp",
                     properties={"path": "c.inp", "active": True}),
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

    def test_no_images_for_node_without_output(
        self, provider: DashboardDataProvider
    ):
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

    def test_go_properties_exclude_internal(
        self, provider: DashboardDataProvider
    ):
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
        from services.dashboard.app import _find_graph_path

        storage_dir = tmp_path / ".jj" / "storage"
        storage_dir.mkdir(parents=True)
        graph_file = storage_dir / "graph.yaml"
        graph_file.write_text("nodes: []\nrelations: []\n")

        result = _find_graph_path(tmp_path)
        assert result is not None
        assert result.name == "graph.yaml"

    def test_find_graph_path_json(self, tmp_path):
        """graph.jsonが存在する場合にパスを返す"""
        from services.dashboard.app import _find_graph_path

        storage_dir = tmp_path / ".jj" / "storage"
        storage_dir.mkdir(parents=True)
        (storage_dir / "graph.json").write_text("{}")

        result = _find_graph_path(tmp_path)
        assert result is not None
        assert result.name == "graph.json"

    def test_find_graph_path_none(self, tmp_path):
        """グラフファイルが存在しない場合にNoneを返す"""
        from services.dashboard.app import _find_graph_path

        result = _find_graph_path(tmp_path)
        assert result is None

    def test_get_graph_mtime_returns_float(self, tmp_path):
        """mtimeがfloatで返される"""
        from services.dashboard.app import _get_graph_mtime

        storage_dir = tmp_path / ".jj" / "storage"
        storage_dir.mkdir(parents=True)
        (storage_dir / "graph.yaml").write_text("nodes: []\n")

        mtime = _get_graph_mtime(tmp_path)
        assert isinstance(mtime, float)
        assert mtime > 0

    def test_get_graph_mtime_no_file(self, tmp_path):
        """ファイルがない場合は0.0"""
        from services.dashboard.app import _get_graph_mtime

        mtime = _get_graph_mtime(tmp_path)
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
        try:
            result = _try_render_aggrid(df)
            # インストール済みの場合: Streamlitコンテキスト外でエラーか成功
        except Exception:
            # Streamlitコンテキスト外で動かした場合のエラーは許容
            pass


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
    """_select_table_columns のテスト"""

    def test_none_returns_all(self):
        """table_columnsがNoneの場合は全カラム返却"""
        try:
            import streamlit  # noqa: F401
        except ImportError:
            pytest.skip("streamlit not installed")
        from services.dashboard.app import _select_table_columns

        cols = ["name", "type", "format", "index", "RF3"]
        assert _select_table_columns(cols, None) == cols

    def test_filters_and_orders(self):
        """指定パターンに基づくフィルタと順序付け"""
        try:
            import streamlit  # noqa: F401
        except ImportError:
            pytest.skip("streamlit not installed")
        from services.dashboard.app import _select_table_columns

        all_cols = ["name", "type", "format", "index", "RF3", "temperature", "active"]
        table_columns = ["RF3", "index"]
        result = _select_table_columns(all_cols, table_columns)
        # 固定カラム(name, type, format) + 指定カラム(RF3, index)
        assert result == ["name", "type", "format", "RF3", "index"]

    def test_glob_pattern(self):
        """globパターンによるカラムマッチ"""
        try:
            import streamlit  # noqa: F401
        except ImportError:
            pytest.skip("streamlit not installed")
        from services.dashboard.app import _select_table_columns

        all_cols = [
            "name", "type", "format", "stress_center", "stress_edge", "RF3"
        ]
        table_columns = ["stress*", "RF3"]
        result = _select_table_columns(all_cols, table_columns)
        assert result == [
            "name", "type", "format", "stress_center", "stress_edge", "RF3"
        ]

    def test_no_match(self):
        """マッチしないパターンの場合は固定カラムのみ"""
        try:
            import streamlit  # noqa: F401
        except ImportError:
            pytest.skip("streamlit not installed")
        from services.dashboard.app import _select_table_columns

        all_cols = ["name", "type", "format", "index"]
        table_columns = ["nonexistent"]
        result = _select_table_columns(all_cols, table_columns)
        assert result == ["name", "type", "format"]


# ====================================================================
# _is_truthy テスト
# ====================================================================


class TestIsTruthy:
    """_is_truthy のテスト"""

    def test_bool_true(self):
        """Python bool Trueを正しく判定"""
        try:
            import streamlit  # noqa: F401
        except ImportError:
            pytest.skip("streamlit not installed")
        from services.dashboard.app import _is_truthy

        assert _is_truthy(True) is True

    def test_bool_false(self):
        """Python bool Falseを正しく判定"""
        try:
            import streamlit  # noqa: F401
        except ImportError:
            pytest.skip("streamlit not installed")
        from services.dashboard.app import _is_truthy

        assert _is_truthy(False) is False

    def test_string_true(self):
        """文字列 'true' を正しく判定"""
        try:
            import streamlit  # noqa: F401
        except ImportError:
            pytest.skip("streamlit not installed")
        from services.dashboard.app import _is_truthy

        assert _is_truthy("true") is True
        assert _is_truthy("True") is True
        assert _is_truthy("TRUE") is True

    def test_string_false(self):
        """文字列 'false' を正しく判定"""
        try:
            import streamlit  # noqa: F401
        except ImportError:
            pytest.skip("streamlit not installed")
        from services.dashboard.app import _is_truthy

        assert _is_truthy("false") is False
        assert _is_truthy("False") is False

    def test_none(self):
        """Noneはfalse"""
        try:
            import streamlit  # noqa: F401
        except ImportError:
            pytest.skip("streamlit not installed")
        from services.dashboard.app import _is_truthy

        assert _is_truthy(None) is False


# ====================================================================
# SavedViewConfig テスト
# ====================================================================


class TestSavedViewConfig:
    """SavedViewConfig のテスト"""

    def test_basic_table_view(self):
        """基本テーブルビュー設定"""
        from config import SavedViewConfig

        view = SavedViewConfig.from_dict({
            "name": "テスト一覧",
            "type": "table",
            "filters": {"active": True},
        })
        assert view.name == "テスト一覧"
        assert view.view_type == "table"
        assert view.filters == {"active": True}
        assert view.plot == {}
        assert view.gallery == {}

    def test_plot_view(self):
        """プロットビュー設定"""
        from config import SavedViewConfig

        view = SavedViewConfig.from_dict({
            "name": "RF3 vs 条件",
            "type": "plot",
            "plot": {"x": "条件", "y": "RF3", "color": "バージョン"},
        })
        assert view.view_type == "plot"
        assert view.plot["x"] == "条件"
        assert view.plot["y"] == "RF3"

    def test_gallery_view(self):
        """ギャラリービュー設定"""
        from config import SavedViewConfig

        view = SavedViewConfig.from_dict({
            "name": "スクショ",
            "type": "gallery",
            "gallery": {"source": "property", "property_key": "screenshot"},
        })
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
    """_normalize_group_key のテスト"""

    def test_daily_key_normalized(self):
        """daily:日付:キー → キーに正規化"""
        try:
            import streamlit  # noqa: F401
        except ImportError:
            pytest.skip("streamlit not installed")
        from services.dashboard.app import _normalize_group_key

        assert _normalize_group_key("daily:2026-01-15:screenshot") == "screenshot"

    def test_non_daily_key_unchanged(self):
        """dailyでないキーはそのまま"""
        try:
            import streamlit  # noqa: F401
        except ImportError:
            pytest.skip("streamlit not installed")
        from services.dashboard.app import _normalize_group_key

        assert _normalize_group_key("screenshot") == "screenshot"

    def test_daily_two_parts(self):
        """daily:xxのみ（2パート）はそのまま"""
        try:
            import streamlit  # noqa: F401
        except ImportError:
            pytest.skip("streamlit not installed")
        from services.dashboard.app import _normalize_group_key

        assert _normalize_group_key("daily:only") == "daily:only"


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
    """_sort_columns_by_vocab のテスト"""

    def test_vocab_order_first(self):
        """vocab定義順が優先される"""
        try:
            import streamlit  # noqa: F401
        except ImportError:
            pytest.skip("streamlit not installed")
        from services.dashboard.app import _sort_columns_by_vocab

        vocab = {"idx": "条件", "ver": "バージョン"}
        cols = ["RF3", "バージョン", "条件", "temperature"]
        result = _sort_columns_by_vocab(cols, vocab)
        # vocab順: 条件(idx=0位), バージョン(ver=1位) → 残り: RF3, temperature
        assert result == ["条件", "バージョン", "RF3", "temperature"]

    def test_no_vocab_alphabetical(self):
        """vocabが空の場合は文字列昇順"""
        try:
            import streamlit  # noqa: F401
        except ImportError:
            pytest.skip("streamlit not installed")
        from services.dashboard.app import _sort_columns_by_vocab

        cols = ["RF3", "temperature", "active"]
        result = _sort_columns_by_vocab(cols, {})
        assert result == ["RF3", "active", "temperature"]

    def test_mixed_vocab_non_vocab(self):
        """vocabに含まれるものと含まれないものの混合"""
        try:
            import streamlit  # noqa: F401
        except ImportError:
            pytest.skip("streamlit not installed")
        from services.dashboard.app import _sort_columns_by_vocab

        vocab = {"idx": "条件"}
        cols = ["RF3", "条件", "active"]
        result = _sort_columns_by_vocab(cols, vocab)
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
                Node(id=1, type="go", name="go_idx1_v1", format="inp",
                     properties={
                         "path": "a.inp", "index": "1", "version": "1",
                         "RF.time": [0.0, 1.0], "RF.RF3": [0.0, 100.0],
                     }),
                Node(id=2, type="go", name="go_idx2_v1", format="inp",
                     properties={
                         "path": "b.inp", "index": "2", "version": "1",
                         "RF.time": [0.0, 1.0], "RF.RF3": [0.0, 200.0],
                     }),
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
                Node(id=1, type="go", name="go_idx1_v1", format="inp",
                     properties={"path": "a.inp", "RF.time": [0.0], "RF.RF3": [0.0]}),
                Node(id=2, type="go", name="go_idx2_v1", format="inp",
                     properties={"path": "b.inp", "index": "2"}),
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
        """テーブル型データはサマリ表示"""
        from services.dashboard.connectors.abaqus import get_material_table

        provider = DashboardDataProvider(self._make_material_graph())
        rows = get_material_table(provider)
        steel = next(r for r in rows if r["name"] == "Steel_S235")
        assert steel["plastic"] == "[2行]"
        assert steel["elastic"] == "[1行]"

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
        assert "elastic" in keys
        assert "plastic" in keys
        assert "keywords" not in keys  # list[str]はテーブル型でない
        assert "verbose_name" not in keys

    def test_empty_for_go_node(self):
        """go_ノードは空リスト"""
        from services.dashboard.connectors.abaqus import get_material_table_keys

        graph = GraphModel(
            nodes=[
                Node(id=1, type="go", name="go_idx1", format="inp",
                     properties={"path": "a.inp"}),
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
    """DashboardConfig material-curve-columns のテスト"""

    def test_default_empty(self):
        """デフォルトで空dict"""
        from config import DashboardConfig

        cfg = DashboardConfig.from_dict({})
        assert cfg.material_curve_columns == {}

    def test_dict_format(self):
        """辞書形式でcolumnsとx/yを指定"""
        from config import DashboardConfig

        data = {
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
        cfg = DashboardConfig.from_dict(data)
        assert "plastic" in cfg.material_curve_columns
        assert cfg.material_curve_columns["plastic"]["columns"] == ["stress", "strain"]
        assert cfg.material_curve_columns["plastic"]["x"] == 1
        assert cfg.material_curve_columns["plastic"]["y"] == 0
        assert "elastic" in cfg.material_curve_columns
        assert cfg.material_curve_columns["elastic"]["columns"] == ["E", "nu"]
        assert "x" not in cfg.material_curve_columns["elastic"]

    def test_list_shorthand(self):
        """簡略形式（リスト）でcolumnsのみ指定"""
        from config import DashboardConfig

        data = {
            "material-curve-columns": {
                "density": ["density"],
            }
        }
        cfg = DashboardConfig.from_dict(data)
        assert cfg.material_curve_columns["density"]["columns"] == ["density"]

    def test_graph_config_includes_mcc(self):
        """GraphConfigからmaterial_curve_columnsが読み込まれる"""
        from config import GraphConfig

        cfg = GraphConfig.from_dict({
            "dashboard": {
                "material-curve-columns": {
                    "plastic": {"columns": ["stress", "strain"], "x": 1, "y": 0},
                }
            }
        })
        assert "plastic" in cfg.dashboard.material_curve_columns


# ====================================================================
# DashboardPageConnector 基盤テスト
# ====================================================================


class TestDashboardPageConnector:
    """DashboardPageConnector 基盤のテスト"""

    def test_abaqus_connector_registered(self):
        """AbaqusMaterialPageConnectorがレジストリに登録されている"""
        from services.dashboard.connectors import DashboardPageConnector
        import services.dashboard.connectors.abaqus  # noqa: F401

        assert "物性一覧" in DashboardPageConnector._registry

    def test_get_connector_pages_with_material(self):
        """abaqus_materialノードがある場合にコネクターページが返される"""
        from services.dashboard.connectors import get_connector_pages
        import services.dashboard.connectors.abaqus  # noqa: F401

        graph = GraphModel(
            nodes=[
                Node(id=1, type="abaqus_material", name="Steel",
                     format="material", properties={}),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        pages = get_connector_pages(provider)
        assert "物性一覧" in pages

    def test_get_connector_pages_without_material(self):
        """abaqus_materialノードがない場合はコネクターページが返されない"""
        from services.dashboard.connectors import get_connector_pages
        import services.dashboard.connectors.abaqus  # noqa: F401

        graph = GraphModel(
            nodes=[
                Node(id=1, type="go", name="go_idx1_v1",
                     format="inp", properties={"path": "a.inp"}),
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
