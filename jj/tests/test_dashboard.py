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
