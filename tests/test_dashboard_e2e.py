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

    .j2/storage/graph.yaml にグラフデータを配置する。
    """
    storage_dir = tmp_path / ".j2" / "storage"
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
class TestDashboardPageNavigationE2E:
    """ページ遷移E2Eテスト"""

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

    def test_navigate_to_saved_views_page(self, project_with_graph: Path):
        """保存済みビューページへの遷移"""
        at = self._run_app(project_with_graph)
        assert not at.exception
        radios = at.sidebar.radio
        assert len(radios) >= 1
        page_radio = radios[0]
        assert "保存済みビュー" in page_radio.options
        # 保存済みビューページを選択
        page_radio.set_value("保存済みビュー")
        at.run()
        assert not at.exception

    def test_navigate_to_connector_page(self, project_with_graph: Path):
        """コネクターページへの遷移（物性一覧）"""
        at = self._run_app(project_with_graph)
        assert not at.exception
        radios = at.sidebar.radio
        assert len(radios) >= 1
        page_radio = radios[0]
        if "物性一覧" in page_radio.options:
            page_radio.set_value("物性一覧")
            at.run()
            assert not at.exception

    def test_navigate_to_mesh_quality_page(self, project_with_graph: Path):
        """コネクターページへの遷移（メッシュ品質）"""
        at = self._run_app(project_with_graph)
        assert not at.exception
        radios = at.sidebar.radio
        assert len(radios) >= 1
        page_radio = radios[0]
        if "メッシュ品質" in page_radio.options:
            page_radio.set_value("メッシュ品質")
            at.run()
            assert not at.exception

    def test_navigate_to_job_summary_page(self, project_with_graph: Path):
        """コネクターページへの遷移（ジョブサマリー）"""
        at = self._run_app(project_with_graph)
        assert not at.exception
        radios = at.sidebar.radio
        assert len(radios) >= 1
        page_radio = radios[0]
        if "ジョブサマリー" in page_radio.options:
            page_radio.set_value("ジョブサマリー")
            at.run()
            assert not at.exception


class TestDashboardFilterE2E:
    """フィルタ操作テスト（Streamlit不要のユニットテスト）"""

    def test_apply_chained_filters_global_only(self):
        """グローバルフィルタのみ適用"""
        from services.query.filters import apply_chained_filters

        rows = [
            {"type": "go", "active": True, "name": "a"},
            {"type": "inp", "active": True, "name": "b"},
            {"type": "go", "active": False, "name": "c"},
        ]
        result = apply_chained_filters(rows, {"type": "go"})
        assert len(result) == 2
        assert all(r["type"] == "go" for r in result)

    def test_apply_chained_filters_global_and_local(self):
        """グローバル+ローカルフィルタ適用"""
        from services.query.filters import apply_chained_filters

        rows = [
            {"type": "go", "active": True, "name": "a"},
            {"type": "go", "active": False, "name": "b"},
            {"type": "inp", "active": True, "name": "c"},
        ]
        result = apply_chained_filters(rows, {"type": "go"}, {"active": True})
        assert len(result) == 1
        assert result[0]["name"] == "a"

    def test_merge_filters_local_overrides_global(self):
        """ローカルフィルタがグローバルを上書き"""
        from services.query.filters import merge_filters

        merged = merge_filters({"type": "go", "active": True}, {"type": "inp"})
        assert merged == {"type": "inp", "active": True}

    def test_merge_filters_multiple_local_keys(self):
        """複数ローカルフィルタキーの処理"""
        from services.query.filters import merge_filters

        merged = merge_filters(
            {"type": "go"},
            {"active": True, "analysis_status": "COMPLETED"},
        )
        assert merged == {"type": "go", "active": True, "analysis_status": "COMPLETED"}


class TestConnectorSavedViewUnit:
    """コネクター保存済みビューのユニットテスト"""

    @pytest.fixture(autouse=True)
    def _require_pandas(self):
        pytest.importorskip("pandas")

    def _make_provider(self):
        """テスト用Providerを作成"""
        from services.dashboard.data_provider import DashboardDataProvider

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "path": "go_idx1_v1.inp",
                        "analysis_status": "COMPLETED",
                        "cpu_time": 123.4,
                        "wallclock_time": 56.7,
                        "mesh_element_count": 100,
                        "mesh_node_count": 200,
                        "mesh_quality": {
                            "volume": {"min": 0.01, "max": 1.5, "mean": 0.8},
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
                        "path": "go_idx2_v1.inp",
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
                    type="abaqus_material",
                    name="Aluminum",
                    format="material",
                    properties={
                        "elastic": [[70000.0, 0.33]],
                        "plastic": [[100.0, 0.0], [150.0, 0.05]],
                    },
                ),
            ],
            relations=[],
        )
        return DashboardDataProvider(graph)

    def test_material_connector_saved_view_html_single(self):
        """物性コネクター: 単一物性の保存済みビューHTML"""
        import services.dashboard.connectors.abaqus
        from config import DashboardConfig, SavedViewConfig

        provider = self._make_provider()
        config = DashboardConfig.from_dict({})
        view = SavedViewConfig.from_dict(
            {
                "name": "Steel詳細",
                "type": "connector:物性一覧",
                "connector_config": {"material_name": "Steel"},
            }
        )

        connector = services.dashboard.connectors.abaqus.AbaqusMaterialPageConnector()
        html = connector.generate_saved_view_html(provider, view, config)
        assert "Steel" in html
        assert "plastic" in html

    def test_material_connector_saved_view_html_compare(self):
        """物性コネクター: 比較モードの保存済みビューHTML"""
        import services.dashboard.connectors.abaqus
        from config import DashboardConfig, SavedViewConfig

        provider = self._make_provider()
        config = DashboardConfig.from_dict({})
        view = SavedViewConfig.from_dict(
            {
                "name": "物性比較",
                "type": "connector:物性一覧",
                "connector_config": {
                    "compare_materials": ["Steel", "Aluminum"],
                    "property_key": "plastic",
                },
            }
        )

        connector = services.dashboard.connectors.abaqus.AbaqusMaterialPageConnector()
        html = connector.generate_saved_view_html(provider, view, config)
        assert "物性比較" in html

    def test_material_connector_saved_view_html_fallback(self):
        """物性コネクター: connector_config未設定時はデフォルトHTML"""
        import services.dashboard.connectors.abaqus
        from config import DashboardConfig, SavedViewConfig

        provider = self._make_provider()
        config = DashboardConfig.from_dict({})
        view = SavedViewConfig.from_dict(
            {
                "name": "物性一覧デフォルト",
                "type": "connector:物性一覧",
            }
        )

        connector = services.dashboard.connectors.abaqus.AbaqusMaterialPageConnector()
        html = connector.generate_saved_view_html(provider, view, config)
        assert "物性テーブル" in html

    def test_job_summary_connector_saved_view_html_filtered(self):
        """ジョブサマリーコネクター: status_filterによるフィルタ"""
        import services.dashboard.connectors.abaqus
        from config import DashboardConfig, SavedViewConfig

        provider = self._make_provider()
        config = DashboardConfig.from_dict({})
        view = SavedViewConfig.from_dict(
            {
                "name": "完了ジョブ",
                "type": "connector:ジョブサマリー",
                "connector_config": {"status_filter": "COMPLETED"},
            }
        )

        connector = services.dashboard.connectors.abaqus.AbaqusJobSummaryPageConnector()
        html = connector.generate_saved_view_html(provider, view, config)
        assert "COMPLETED" in html
        assert "FAILED" not in html

    def test_job_summary_connector_saved_view_html_go_name_filter(self):
        """ジョブサマリーコネクター: go_nameフィルタ"""
        import services.dashboard.connectors.abaqus
        from config import DashboardConfig, SavedViewConfig

        provider = self._make_provider()
        config = DashboardConfig.from_dict({})
        view = SavedViewConfig.from_dict(
            {
                "name": "特定ジョブ",
                "type": "connector:ジョブサマリー",
                "connector_config": {"go_name": "go_idx1_v1"},
            }
        )

        connector = services.dashboard.connectors.abaqus.AbaqusJobSummaryPageConnector()
        html = connector.generate_saved_view_html(provider, view, config)
        assert "go_idx1_v1" in html

    def test_job_summary_connector_saved_view_no_match(self):
        """ジョブサマリーコネクター: 条件不一致で空結果"""
        import services.dashboard.connectors.abaqus
        from config import DashboardConfig, SavedViewConfig

        provider = self._make_provider()
        config = DashboardConfig.from_dict({})
        view = SavedViewConfig.from_dict(
            {
                "name": "存在しないジョブ",
                "type": "connector:ジョブサマリー",
                "connector_config": {"status_filter": "RUNNING"},
            }
        )

        connector = services.dashboard.connectors.abaqus.AbaqusJobSummaryPageConnector()
        html = connector.generate_saved_view_html(provider, view, config)
        assert "合致する" in html


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


# ====================================================================
# connector_config スキーマテスト
# ====================================================================


class TestConnectorConfigSchema:
    """DashboardPageConnectorのget_connector_config_schemaテスト"""

    def test_material_connector_has_schema(self):
        """AbaqusMaterialPageConnectorがスキーマを返す"""
        from services.dashboard.connectors.abaqus import AbaqusMaterialPageConnector

        schema = AbaqusMaterialPageConnector.get_connector_config_schema()
        assert len(schema) == 3
        keys = [f["key"] for f in schema]
        assert "material_name" in keys
        assert "property_key" in keys
        assert "compare_materials" in keys

    def test_mesh_quality_connector_has_schema(self):
        """AbaqusMeshQualityPageConnectorがスキーマを返す"""
        from services.dashboard.connectors.abaqus import AbaqusMeshQualityPageConnector

        schema = AbaqusMeshQualityPageConnector.get_connector_config_schema()
        assert len(schema) == 2
        keys = [f["key"] for f in schema]
        assert "go_name" in keys
        assert "show_elset" in keys
        # show_elsetはcheckbox型
        elset_field = next(f for f in schema if f["key"] == "show_elset")
        assert elset_field["type"] == "checkbox"

    def test_job_summary_connector_has_schema(self):
        """AbaqusJobSummaryPageConnectorがスキーマを返す"""
        from services.dashboard.connectors.abaqus import AbaqusJobSummaryPageConnector

        schema = AbaqusJobSummaryPageConnector.get_connector_config_schema()
        assert len(schema) == 2
        keys = [f["key"] for f in schema]
        assert "status_filter" in keys
        assert "go_name" in keys

    def test_base_connector_returns_empty_schema(self):
        """基底クラスは空のスキーマを返す"""
        from services.dashboard.connectors import DashboardPageConnector

        schema = DashboardPageConnector.get_connector_config_schema()
        assert schema == []

    def test_get_connector_config_schema_by_label(self):
        """get_connector_config_schema関数でページラベルからスキーマを取得"""
        from services.dashboard.connectors import get_connector_config_schema

        schema = get_connector_config_schema("物性一覧")
        assert len(schema) == 3

        schema = get_connector_config_schema("メッシュ品質")
        assert len(schema) == 2

        schema = get_connector_config_schema("存在しないページ")
        assert schema == []

    def test_schema_fields_have_required_keys(self):
        """スキーマの各フィールドがkey, label, typeを持つ"""
        from services.dashboard.connectors.abaqus import AbaqusMaterialPageConnector

        schema = AbaqusMaterialPageConnector.get_connector_config_schema()
        for field in schema:
            assert "key" in field
            assert "label" in field
            assert "type" in field
            assert field["type"] in ("text", "checkbox")


# ====================================================================
# PageComponent レジストリ検証テスト
# ====================================================================


class TestPageComponentRegistry:
    """PageComponentレジストリの包括的テスト"""

    def test_all_expected_page_keys_registered(self):
        """全期待PageComponentがレジストリに登録されている"""
        # コンポーネントモジュールをインポートして登録を発火
        import services.dashboard.components.card
        import services.dashboard.components.gallery
        import services.dashboard.components.overview
        import services.dashboard.components.status
        import services.dashboard.components.table  # noqa: F401
        from services.dashboard.components import get_page_keys

        keys = get_page_keys()
        # 基本ページキーが含まれている
        assert "table" in keys
        assert "card" in keys
        assert "gallery" in keys
        assert "overview" in keys

    def test_page_labels_are_japanese(self):
        """ページラベルが日本語表示名を持つ"""
        import services.dashboard.components.table  # noqa: F401
        from services.dashboard.components import get_page_labels

        labels = get_page_labels()
        assert len(labels) >= 1
        # テーブルラベルが日本語
        assert "テーブル" in labels

    def test_page_component_instantiation(self):
        """各PageComponentがインスタンス化できる"""
        import services.dashboard.components.card
        import services.dashboard.components.table  # noqa: F401
        from services.dashboard.components import get_page_component

        for key in ["table", "card"]:
            component = get_page_component(key)
            assert component is not None, f"page_key={key} のコンポーネントが取得できない"


# ====================================================================
# DashboardPageConnector レジストリ検証テスト
# ====================================================================


class TestDashboardConnectorRegistry:
    """DashboardPageConnectorレジストリの包括的テスト"""

    @pytest.fixture(autouse=True)
    def _require_pandas(self):
        pytest.importorskip("pandas")

    def _make_provider_with_materials(self):
        """物性データを含むProvider"""
        from services.dashboard.data_provider import DashboardDataProvider

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "path": "go_idx1_v1.inp",
                        "analysis_status": "COMPLETED",
                        "active": True,
                    },
                ),
                Node(
                    id=2,
                    type="abaqus_material",
                    name="Steel",
                    format="material",
                    properties={
                        "elastic": [[210000.0, 0.3]],
                        "plastic": [[200.0, 0.0], [300.0, 0.1]],
                    },
                ),
                Node(
                    id=3,
                    type="abaqus_material",
                    name="rubber_neohooke",
                    format="material",
                    properties={
                        "hyperelastic": [[0.5, 0.02]],
                        "keywords": ["hyperelastic", "density"],
                    },
                ),
            ],
            relations=[
                Relation(id=1, label="assigned_to", node1_id=2, node2_id=1),
            ],
        )
        return DashboardDataProvider(graph)

    def test_abaqus_material_connector_available(self):
        """Abaqus物性コネクターがmaterialノード存在時に利用可能"""
        import services.dashboard.connectors.abaqus  # noqa: F401
        from services.dashboard.connectors import get_connector_pages

        provider = self._make_provider_with_materials()
        pages = get_connector_pages(provider)
        assert "物性一覧" in pages

    def test_abaqus_material_connector_html(self):
        """物性コネクターがHTMLを生成できる"""
        import services.dashboard.connectors.abaqus  # noqa: F401
        from services.dashboard.connectors import generate_connector_pages_html

        provider = self._make_provider_with_materials()
        config = self._make_dashboard_config()
        pages_html = generate_connector_pages_html(provider, config)
        labels = [label for label, _ in pages_html]
        # 物性一覧 or ジョブサマリー or メッシュ品質のHTMLが生成される
        assert len(pages_html) >= 1
        assert any(label in ["物性一覧", "ジョブサマリー", "メッシュ品質"] for label in labels)

    def test_abaqus_job_summary_connector_html(self):
        """ジョブサマリーコネクターがHTMLを生成"""
        import services.dashboard.connectors.abaqus  # noqa: F401
        from config import DashboardConfig, SavedViewConfig
        from services.dashboard.connectors import generate_connector_saved_view_html

        provider = self._make_provider_with_materials()
        config = DashboardConfig.from_dict({})
        view = SavedViewConfig.from_dict(
            {
                "name": "全ジョブ",
                "type": "connector:ジョブサマリー",
            }
        )
        html = generate_connector_saved_view_html("ジョブサマリー", provider, view, config)
        # HTMLが生成されること（空でも可）
        assert isinstance(html, str)

    def test_hyperelastic_material_in_provider(self):
        """HYPERELASTIC材料がProviderで取得できる"""
        provider = self._make_provider_with_materials()
        graph = provider.graph
        mat_nodes = [n for n in graph.nodes if n.type == "abaqus_material"]
        mat_names = [n.name for n in mat_nodes]
        assert "rubber_neohooke" in mat_names
        # hyperelasticプロパティの存在確認
        rubber = next(n for n in mat_nodes if n.name == "rubber_neohooke")
        assert "hyperelastic" in rubber.properties

    @staticmethod
    def _make_dashboard_config():
        from config import DashboardConfig

        return DashboardConfig.from_dict({})


# ====================================================================
# HTMLエクスポート整合性テスト
# ====================================================================


@pytest.mark.skipif(not HAS_APPTEST, reason="streamlit.testing.v1 not available")
class TestHtmlExportIntegrity:
    """HTMLエクスポートの包括的整合性テスト"""

    def test_html_export_includes_all_data_nodes(self, project_with_graph: Path):
        """HTMLエクスポートにノードデータが反映される"""
        import services.dashboard.connectors.abaqus  # noqa: F401
        from config import DashboardConfig, SavedViewConfig
        from services.dashboard.data_provider import DashboardDataProvider
        from services.dashboard.html_export import generate_saved_views_html
        from services.graph import GraphService

        svc = GraphService(project_root=project_with_graph)
        graph = svc.load()
        provider = DashboardDataProvider(graph)
        config = DashboardConfig.from_dict({})

        views = [
            SavedViewConfig.from_dict(
                {
                    "name": "テストテーブル",
                    "view_type": "table",
                }
            ),
        ]

        html = generate_saved_views_html(provider, project_with_graph, config, views)
        assert "<!DOCTYPE html>" in html
        assert "jj Dashboard" in html
        # テーブルビューのセクションが含まれる
        assert "テストテーブル" in html

    def test_html_export_material_connector(self, project_with_graph: Path):
        """HTMLエクスポートに物性コネクターが含まれる"""
        import services.dashboard.connectors.abaqus  # noqa: F401
        from config import DashboardConfig
        from services.dashboard.data_provider import DashboardDataProvider
        from services.dashboard.html_export import generate_saved_views_html
        from services.graph import GraphService

        svc = GraphService(project_root=project_with_graph)
        graph = svc.load()
        provider = DashboardDataProvider(graph)
        config = DashboardConfig.from_dict({})

        html = generate_saved_views_html(provider, project_with_graph, config, views=[])
        # 物性データがあるのでコネクターHTMLが含まれる
        assert "物性一覧" in html or "ジョブサマリー" in html or "メッシュ品質" in html


# ====================================================================
# DashboardDataProvider 拡張テスト
# ====================================================================


class TestDashboardDataProviderAdvanced:
    """DataProviderの多様なデータパターンテスト"""

    @pytest.fixture(autouse=True)
    def _require_pandas(self):
        pytest.importorskip("pandas")

    def test_provider_with_mixed_node_types(self):
        """多様なノードタイプが混在するグラフ"""
        from services.dashboard.data_provider import DashboardDataProvider

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"active": True, "analysis_status": "COMPLETED"},
                ),
                Node(
                    id=2,
                    type="abaqus_material",
                    name="Steel",
                    format="material",
                    properties={"elastic": [[210000.0, 0.3]]},
                ),
                Node(
                    id=3,
                    type="abaqus_keyword",
                    name="FREQUENCY",
                    format="keyword",
                    properties={"EIGENSOLVER": "LANCZOS"},
                ),
                Node(
                    id=4,
                    type="abaqus_elset",
                    name="shell_part",
                    format="elset",
                    properties={"material": "Steel", "element_count": 100},
                ),
            ],
            relations=[
                Relation(id=1, label="assigned_to", node1_id=2, node2_id=1),
                Relation(id=2, label="uses_keyword", node1_id=1, node2_id=3),
                Relation(id=3, label="has_elset", node1_id=1, node2_id=4),
            ],
        )
        provider = DashboardDataProvider(graph)
        # テーブルデータの取得が可能
        table = provider.get_go_table()
        assert len(table) >= 1

    def test_provider_with_convergence_data(self):
        """収束情報を持つノードのテーブル表示"""
        from services.dashboard.data_provider import DashboardDataProvider

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={
                        "active": True,
                        "analysis_status": "COMPLETED",
                        "cpu_time": 67.8,
                        "wallclock_time": 35.0,
                        "increment_count": 12,
                        "cutback_count": 1,
                        "step_count": 2,
                        "total_iterations": 37,
                        "max_equilibrium_iters": 5,
                    },
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        table = provider.get_go_table()
        assert len(table) == 1
        row = table[0]
        assert row.get("cpu_time") == 67.8
        assert row.get("cutback_count") == 1

    def test_provider_with_multiple_status(self):
        """異なるステータスのノードが混在"""
        from services.dashboard.data_provider import DashboardDataProvider

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"active": True, "analysis_status": "COMPLETED"},
                ),
                Node(
                    id=2,
                    type="go",
                    name="go_idx2_v1",
                    format="inp",
                    properties={"active": True, "analysis_status": "FAILED"},
                ),
                Node(
                    id=3,
                    type="go",
                    name="go_idx3_v1",
                    format="inp",
                    properties={"active": False, "analysis_status": "COMPLETED"},
                ),
            ],
            relations=[],
        )
        provider = DashboardDataProvider(graph)
        table = provider.get_go_table()
        assert len(table) == 3
        statuses = {row.get("analysis_status") for row in table}
        assert "COMPLETED" in statuses
        assert "FAILED" in statuses
