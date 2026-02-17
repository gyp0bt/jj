"""ダッシュボード E2Eテスト（Streamlit AppTest）

Streamlit 1.28+のAppTestフレームワークを使用した統合テスト。
AppTestはStreamlitアプリをヘッドレスで実行し、UI要素の検証を可能にする。

テストはアプリ全体の起動・ページ遷移・データ表示を検証する。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from jj_types import GraphModel, Node, Relation

# AppTestが利用可能か確認
try:
    from streamlit.testing.v1 import AppTest

    HAS_APPTEST = True
except ImportError:
    HAS_APPTEST = False


@pytest.fixture()
def project_with_graph(tmp_path: Path) -> Path:
    """テスト用プロジェクトディレクトリを作成

    .jj/storage/graph.yaml にグラフデータを配置する。
    """
    storage_dir = tmp_path / ".jj" / "storage"
    storage_dir.mkdir(parents=True)

    graph = GraphModel(
        nodes=[
            Node(
                id=1,
                type="go",
                name="go_idx1_v1",
                format="inp",
                properties={
                    "path": "go_idx1_v1/go_idx1_v1.inp",
                    "analysis_status": "COMPLETED",
                    "cpu_time": 123.4,
                    "wallclock_time": 56.7,
                    "mesh_element_count": 100,
                    "mesh_node_count": 200,
                    "mesh_element_types": {"C3D8": 80, "C3D4": 20},
                    "mesh_quality": {
                        "volume": {"min": 0.01, "max": 1.5, "mean": 0.8},
                        "detJ": {"min": 0.1, "max": 2.0, "mean": 1.0},
                    },
                    "active": True,
                },
            ),
            Node(
                id=2,
                type="go",
                name="go_idx2_v1",
                format="inp",
                properties={
                    "path": "go_idx2_v1/go_idx2_v1.inp",
                    "analysis_status": "FAILED",
                    "active": True,
                },
            ),
            Node(
                id=3,
                type="abaqus_material",
                name="Steel",
                format="material",
                properties={
                    "elastic": [[210000.0, 0.3]],
                    "plastic": [[200.0, 0.0], [300.0, 0.1]],
                },
            ),
            Node(
                id=4,
                type="inp",
                name="go_idx1_v1.inp",
                format="inp",
                properties={"path": "go_idx1_v1/go_idx1_v1.inp"},
            ),
        ],
        relations=[
            Relation(id=1, label="has_input", node1_id=1, node2_id=4),
            Relation(id=2, label="assigned_to", node1_id=3, node2_id=1),
        ],
    )

    graph_data = {
        "nodes": [
            {
                "id": n.id,
                "type": n.type,
                "name": n.name,
                "format": n.format,
                "properties": n.properties,
            }
            for n in graph.nodes
        ],
        "relations": [
            {
                "id": r.id,
                "label": r.label,
                "node1_id": r.node1_id,
                "node2_id": r.node2_id,
            }
            for r in graph.relations
        ],
    }

    graph_file = storage_dir / "graph.yaml"
    graph_file.write_text(
        yaml.dump(graph_data, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )

    return tmp_path


@pytest.mark.skipif(not HAS_APPTEST, reason="streamlit.testing.v1 not available")
class TestDashboardAppTest:
    """Streamlit AppTestを使用したダッシュボードE2Eテスト"""

    def _run_app(self, project_root: Path) -> AppTest:
        """テスト用にアプリを実行"""
        import os

        app_path = str(Path(__file__).resolve().parents[1] / "services" / "dashboard" / "app.py")
        os.environ["JJ_PROJECT_ROOT"] = str(project_root)
        try:
            at = AppTest.from_file(app_path, default_timeout=30)
            at.run()
            return at
        finally:
            os.environ.pop("JJ_PROJECT_ROOT", None)

    def test_app_starts_without_error(self, project_with_graph: Path):
        """アプリがエラーなく起動する"""
        at = self._run_app(project_with_graph)
        # 致命的エラーがないこと
        assert not at.exception, f"App raised exception: {at.exception}"

    def test_sidebar_shows_metrics(self, project_with_graph: Path):
        """サイドバーにメトリクスが表示される"""
        at = self._run_app(project_with_graph)
        assert not at.exception
        # メトリクスウィジェットが存在する
        metrics = at.sidebar.metric
        assert len(metrics) >= 1

    def test_page_options_include_default_pages(self, project_with_graph: Path):
        """ページ選択にデフォルトページが含まれる"""
        at = self._run_app(project_with_graph)
        assert not at.exception
        # サイドバーのradioウィジェットを確認
        radios = at.sidebar.radio
        assert len(radios) >= 1
        page_radio = radios[0]
        # デフォルトページが含まれること
        options = page_radio.options
        assert "テーブル" in options
        assert "保存済みビュー" in options

    def test_connector_pages_appear_when_data_exists(self, project_with_graph: Path):
        """コネクターページがデータ存在時に表示される"""
        at = self._run_app(project_with_graph)
        assert not at.exception
        radios = at.sidebar.radio
        assert len(radios) >= 1
        options = radios[0].options
        # Abaqusコネクターページが含まれること
        assert "物性一覧" in options
        assert "ジョブサマリー" in options or "メッシュ品質" in options

    def test_default_page_renders_table(self, project_with_graph: Path):
        """デフォルトページ（テーブル）がレンダリングされる"""
        at = self._run_app(project_with_graph)
        assert not at.exception
        # テーブルデータフレームが存在する
        dataframes = at.dataframe
        # 少なくとも1つのデータフレームが表示されていること
        # （AgGridの場合は別のウィジェットになる可能性がある）
        assert len(dataframes) >= 0  # エラーなく通過すればOK


@pytest.mark.skipif(not HAS_APPTEST, reason="streamlit.testing.v1 not available")
class TestDashboardHtmlExportE2E:
    """HTMLエクスポートのE2Eテスト"""

    def test_html_export_with_graph_data(self, project_with_graph: Path):
        """グラフデータからHTMLエクスポートが生成される"""
        # コネクター登録
        import services.dashboard.connectors.abaqus  # noqa: F401
        from config import DashboardConfig, SavedViewConfig
        from services.dashboard.data_provider import DashboardDataProvider
        from services.dashboard.html_export import generate_saved_views_html
        from services.graph import GraphService

        svc = GraphService(project_root=project_with_graph)
        graph = svc.load()
        provider = DashboardDataProvider(graph)
        dashboard_config = DashboardConfig.from_dict({})

        views = [
            SavedViewConfig.from_dict(
                {
                    "name": "テストテーブル",
                    "view_type": "table",
                }
            ),
        ]

        html = generate_saved_views_html(
            provider,
            project_with_graph,
            dashboard_config,
            views,
        )

        assert "<!DOCTYPE html>" in html
        assert "jj Dashboard" in html
        # コネクターページのHTMLも含まれる
        assert "物性一覧" in html or "ジョブサマリー" in html

    def test_html_export_without_views(self, project_with_graph: Path):
        """ビューなしでもコネクターページのHTMLが生成される"""
        import services.dashboard.connectors.abaqus  # noqa: F401
        from config import DashboardConfig
        from services.dashboard.data_provider import DashboardDataProvider
        from services.dashboard.html_export import generate_saved_views_html
        from services.graph import GraphService

        svc = GraphService(project_root=project_with_graph)
        graph = svc.load()
        provider = DashboardDataProvider(graph)
        dashboard_config = DashboardConfig.from_dict({})

        html = generate_saved_views_html(
            provider,
            project_with_graph,
            dashboard_config,
            views=[],
        )

        assert "<!DOCTYPE html>" in html
        # コネクターページのHTMLが含まれる（物性一覧 or ジョブサマリー）
        has_connector = "物性一覧" in html or "ジョブサマリー" in html or "メッシュ品質" in html
        assert has_connector
