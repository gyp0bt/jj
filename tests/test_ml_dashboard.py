"""MLダッシュボードコネクター テスト

ml_query.pyのクエリ関数、ml.pyのコネクター登録・HTML生成を検証する。
Streamlit依存部分はテスト対象外（クエリ層のみ対象）。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

from jj_types import GraphModel, Node, Relation
from services.dashboard.data_provider import DashboardDataProvider


def _make_provider(
    nodes: list[Node],
    relations: list[Relation] | None = None,
) -> DashboardDataProvider:
    """テスト用DashboardDataProviderを生成"""
    graph = GraphModel(nodes=nodes, relations=relations or [])
    return DashboardDataProvider(graph)


# ====================================================================
# テストデータ
# ====================================================================


def _ml_nodes() -> list[Node]:
    """典型的なMLプロジェクトのノードセット"""
    return [
        Node(
            id=1,
            type="dataset",
            name="train.csv",
            format="csv",
            properties={
                "path": "data/train.csv",
                "ml_dataset": True,
                "split": "train",
                "n_rows": 1000,
                "n_columns": 10,
                "columns": ["x1", "x2", "x3", "y"],
            },
        ),
        Node(
            id=2,
            type="dataset",
            name="test.csv",
            format="csv",
            properties={
                "path": "data/test.csv",
                "ml_dataset": True,
                "split": "test",
                "n_rows": 200,
                "n_columns": 10,
            },
        ),
        Node(
            id=3,
            type="training_script",
            name="train.py",
            format="py",
            properties={
                "path": "src/train.py",
                "ml_frameworks": ["pytorch"],
                "ml_role": "training",
            },
        ),
        Node(
            id=4,
            type="model_checkpoint",
            name="best_model.pt",
            format="pt",
            properties={
                "path": "experiments/exp_001/best_model.pt",
                "ml_checkpoint": True,
                "epoch": 50,
                "is_best": True,
                "file_size_bytes": 52428800,
            },
        ),
        Node(
            id=5,
            type="experiment_metrics",
            name="metrics.json",
            format="json",
            properties={
                "path": "experiments/exp_001/metrics.json",
                "experiment_id": "001",
                "experiment_dir": "exp_001",
                "ml_metrics": True,
                "ml_key_metrics": {
                    "best_val_accuracy": 0.95,
                    "best_val_loss": 0.12,
                },
            },
        ),
        Node(
            id=6,
            type="experiment_config",
            name="config.yaml",
            format="yaml",
            properties={
                "path": "configs/train_config.yaml",
                "ml_config": True,
                "ml_config_keys": ["learning_rate", "batch_size"],
            },
        ),
        Node(
            id=7,
            type="serialized_model",
            name="classifier.pkl",
            format="pkl",
            properties={
                "path": "models/classifier.pkl",
                "ml_serialized_model": True,
                "model_type": "classifier",
                "is_best": True,
                "file_size_bytes": 1048576,
            },
        ),
    ]


def _optimization_nodes() -> list[Node]:
    """最適化ノードセット"""
    return [
        Node(
            id=10,
            type="optimization_study",
            name="study.db",
            format="db",
            properties={
                "path": "optimization/study.db",
                "ml_optimization": True,
                "optimization_framework": "optuna",
                "study_name": "surrogate_opt",
                "n_trials_completed": 100,
                "direction": "minimize",
            },
        ),
        Node(
            id=11,
            type="optimization_config",
            name="optim_config.yaml",
            format="yaml",
            properties={
                "path": "optimization/optim_config.yaml",
                "ml_optimization": True,
                "optimization_params": {"objective": "mse", "n_trials": 200},
            },
        ),
        Node(
            id=12,
            type="trial_history",
            name="trial_history.csv",
            format="csv",
            properties={
                "path": "optimization/trial_history.csv",
                "ml_optimization": True,
            },
        ),
    ]


def _cae_nodes() -> list[Node]:
    """CAEノードセット（層間テスト用）"""
    return [
        Node(
            id=20,
            type="calculation_input",
            name="go_idx1_v1.inp",
            format="inp",
            properties={"path": "cae/go_idx1_v1.inp"},
        ),
        Node(
            id=21,
            type="result",
            name="go_idx1_v1.odb",
            format="odb",
            properties={"path": "cae/go_idx1_v1.odb"},
        ),
    ]


def _ml_relations() -> list[Relation]:
    """ML関連リレーション"""
    return [
        Relation(id=1, label="trains_with", node1_id=3, node2_id=1),
        Relation(id=2, label="produces_model", node1_id=3, node2_id=4),
        Relation(id=3, label="configured_by", node1_id=3, node2_id=6),
        Relation(id=4, label="logs_to", node1_id=5, node2_id=4),
    ]


def _cross_layer_relations() -> list[Relation]:
    """層間リレーション"""
    return [
        Relation(id=10, label="extracted_from", node1_id=1, node2_id=21),
        Relation(id=11, label="surrogate_of", node1_id=4, node2_id=20),
        Relation(id=12, label="optimizes", node1_id=10, node2_id=4),
    ]


# ====================================================================
# ml_query テスト
# ====================================================================


def _multi_experiment_nodes() -> list[Node]:
    """複数実験メトリクスノード（比較テスト用）"""
    return [
        Node(
            id=100,
            type="experiment_metrics",
            name="metrics.json",
            format="json",
            properties={
                "path": "experiments/exp_001/metrics.json",
                "experiment_id": "001",
                "experiment_dir": "exp_001",
                "ml_metrics": True,
                "ml_key_metrics": {
                    "best_val_accuracy": 0.91,
                    "best_val_loss": 0.15,
                    "best_epoch": 5,
                },
            },
        ),
        Node(
            id=101,
            type="experiment_metrics",
            name="metrics.json",
            format="json",
            properties={
                "path": "experiments/exp_002/metrics.json",
                "experiment_id": "002",
                "experiment_dir": "exp_002",
                "ml_metrics": True,
                "ml_key_metrics": {
                    "best_val_accuracy": 0.93,
                    "best_val_loss": 0.10,
                    "best_epoch": 8,
                },
            },
        ),
        Node(
            id=102,
            type="experiment_metrics",
            name="metrics.json",
            format="json",
            properties={
                "path": "experiments/exp_003/metrics.json",
                "experiment_id": "003",
                "experiment_dir": "exp_003",
                "ml_metrics": True,
                "ml_key_metrics": {
                    "best_val_accuracy": 0.89,
                    "best_val_loss": 0.20,
                },
            },
        ),
    ]


class TestMLQueryHasNodes:
    """has_ml_nodes のテスト"""

    def test_has_ml_nodes_true(self):
        from services.dashboard.connectors.ml_query import has_ml_nodes

        provider = _make_provider(_ml_nodes())
        assert has_ml_nodes(provider) is True

    def test_has_ml_nodes_false(self):
        from services.dashboard.connectors.ml_query import has_ml_nodes

        nodes = [Node(id=1, type="file", name="readme.md", format="md", properties={})]
        provider = _make_provider(nodes)
        assert has_ml_nodes(provider) is False


class TestMLQuerySummary:
    """get_ml_summary のテスト"""

    def test_summary_counts(self):
        from services.dashboard.connectors.ml_query import get_ml_summary

        all_nodes = _ml_nodes() + _optimization_nodes()
        provider = _make_provider(all_nodes)
        summary = get_ml_summary(provider)

        assert summary["datasets"] == 2
        assert summary["models"] == 2  # checkpoint + serialized
        assert summary["scripts"] == 1
        assert summary["configs"] == 2  # experiment_config + optimization_config
        assert summary["metrics"] == 1
        assert summary["optimizations"] == 2  # optimization_study + trial_history

    def test_summary_empty(self):
        from services.dashboard.connectors.ml_query import get_ml_summary

        provider = _make_provider([])
        summary = get_ml_summary(provider)
        assert all(v == 0 for v in summary.values())


class TestMLQueryExperimentTable:
    """get_experiment_table のテスト"""

    def test_experiment_rows(self):
        from services.dashboard.connectors.ml_query import get_experiment_table

        provider = _make_provider(_ml_nodes())
        rows = get_experiment_table(provider)

        assert len(rows) == 1
        row = rows[0]
        assert row["名前"] == "metrics.json"
        assert row["実験ID"] == "001"
        assert row["best_val_accuracy"] == 0.95
        assert row["best_val_loss"] == 0.12

    def test_experiment_empty(self):
        from services.dashboard.connectors.ml_query import get_experiment_table

        nodes = [Node(id=1, type="dataset", name="d.csv", format="csv", properties={})]
        provider = _make_provider(nodes)
        assert get_experiment_table(provider) == []


class TestMLQueryDatasetTable:
    """get_dataset_table のテスト"""

    def test_dataset_rows(self):
        from services.dashboard.connectors.ml_query import get_dataset_table

        provider = _make_provider(_ml_nodes())
        rows = get_dataset_table(provider)

        assert len(rows) == 2
        train_row = next(r for r in rows if r["名前"] == "train.csv")
        assert train_row["分割"] == "train"
        assert train_row["行数"] == 1000
        assert "カラム" in train_row

    def test_dataset_columns_truncated(self):
        from services.dashboard.connectors.ml_query import get_dataset_table

        nodes = [
            Node(
                id=1,
                type="dataset",
                name="wide.csv",
                format="csv",
                properties={
                    "path": "data/wide.csv",
                    "columns": [f"col_{i}" for i in range(20)],
                    "n_columns": 20,
                },
            ),
        ]
        provider = _make_provider(nodes)
        rows = get_dataset_table(provider)
        assert "+10" in rows[0]["カラム"]


class TestMLQueryModelTable:
    """get_model_table のテスト"""

    def test_model_rows(self):
        from services.dashboard.connectors.ml_query import get_model_table

        provider = _make_provider(_ml_nodes())
        rows = get_model_table(provider)

        assert len(rows) == 2
        pt_row = next(r for r in rows if r["名前"] == "best_model.pt")
        assert pt_row["エポック"] == 50
        assert pt_row["ベスト"] == "✓"
        assert "50.0 MB" in pt_row["サイズ"]

        pkl_row = next(r for r in rows if r["名前"] == "classifier.pkl")
        assert pkl_row["モデル種別"] == "classifier"


class TestMLQueryScriptTable:
    """get_script_table のテスト"""

    def test_script_rows(self):
        from services.dashboard.connectors.ml_query import get_script_table

        provider = _make_provider(_ml_nodes())
        rows = get_script_table(provider)

        assert len(rows) == 1
        assert rows[0]["フレームワーク"] == "pytorch"
        assert rows[0]["役割"] == "training"


class TestMLQueryOptimizationTable:
    """get_optimization_table のテスト"""

    def test_optimization_rows(self):
        from services.dashboard.connectors.ml_query import get_optimization_table

        provider = _make_provider(_optimization_nodes())
        rows = get_optimization_table(provider)

        assert len(rows) == 3
        study_row = next(r for r in rows if r["タイプ"] == "optimization_study")
        assert study_row["フレームワーク"] == "optuna"
        assert study_row["試行数"] == 100


class TestMLQueryRelations:
    """get_ml_relations のテスト"""

    def test_ml_relations(self):
        from services.dashboard.connectors.ml_query import get_ml_relations

        provider = _make_provider(_ml_nodes(), _ml_relations())
        rows = get_ml_relations(provider)

        assert len(rows) == 4
        labels = {r["リレーション"] for r in rows}
        assert "trains_with" in labels
        assert "produces_model" in labels

    def test_ml_relations_empty(self):
        from services.dashboard.connectors.ml_query import get_ml_relations

        provider = _make_provider(_ml_nodes(), [])
        assert get_ml_relations(provider) == []


# ====================================================================
# get_node_layer テスト
# ====================================================================


class TestNodeLayer:
    """get_node_layer のテスト"""

    def test_cae_layer(self):
        from services.dashboard.connectors.ml_query import get_node_layer

        node = Node(id=1, type="calculation_input", name="t.inp", format="inp", properties={})
        assert get_node_layer(node) == 1

    def test_cae_format_layer(self):
        from services.dashboard.connectors.ml_query import get_node_layer

        node = Node(id=1, type="file", name="t.odb", format="odb", properties={})
        assert get_node_layer(node) == 1

    def test_ml_layer(self):
        from services.dashboard.connectors.ml_query import get_node_layer

        node = Node(id=1, type="dataset", name="t.csv", format="csv", properties={})
        assert get_node_layer(node) == 2

    def test_optimization_layer(self):
        from services.dashboard.connectors.ml_query import get_node_layer

        node = Node(
            id=1,
            type="optimization_study",
            name="s.db",
            format="db",
            properties={"ml_optimization": True},
        )
        assert get_node_layer(node) == 3

    def test_unknown_layer(self):
        from services.dashboard.connectors.ml_query import get_node_layer

        node = Node(id=1, type="file", name="readme.md", format="md", properties={})
        assert get_node_layer(node) is None


# ====================================================================
# get_dataflow_graph_data テスト
# ====================================================================


class TestDataflowGraphData:
    """get_dataflow_graph_data のテスト"""

    def test_three_layer_graph(self):
        from services.dashboard.connectors.ml_query import get_dataflow_graph_data

        all_nodes = _ml_nodes() + _optimization_nodes() + _cae_nodes()
        all_rels = _ml_relations() + _cross_layer_relations()
        provider = _make_provider(all_nodes, all_rels)
        data = get_dataflow_graph_data(provider)

        assert data["layer_counts"][1] == 2  # CAE
        assert data["layer_counts"][2] >= 4  # ML
        assert data["layer_counts"][3] >= 2  # Optimization

        # ノードID一覧
        node_ids = {n["id"] for n in data["nodes"]}
        assert 1 in node_ids  # dataset
        assert 20 in node_ids  # CAE input
        assert 10 in node_ids  # optimization_study

        # 層間エッジ
        cross_edges = [e for e in data["edges"] if e["cross_layer"]]
        assert len(cross_edges) >= 2

    def test_ml_only_graph(self):
        from services.dashboard.connectors.ml_query import get_dataflow_graph_data

        provider = _make_provider(_ml_nodes(), _ml_relations())
        data = get_dataflow_graph_data(provider)

        assert data["layer_counts"][1] == 0
        assert data["layer_counts"][2] >= 4
        assert data["layer_counts"][3] == 0
        # 層間エッジなし
        cross_edges = [e for e in data["edges"] if e["cross_layer"]]
        assert len(cross_edges) == 0

    def test_empty_graph(self):
        from services.dashboard.connectors.ml_query import get_dataflow_graph_data

        provider = _make_provider([])
        data = get_dataflow_graph_data(provider)
        assert data["nodes"] == []
        assert data["edges"] == []


# ====================================================================
# コネクター登録テスト
# ====================================================================


class TestConnectorRegistration:
    """DashboardPageConnectorレジストリへの登録確認"""

    def test_ml_overview_registered(self):
        import services.dashboard.connectors.ml  # noqa: F401
        from services.dashboard.connectors import DashboardPageConnector

        assert "ML概要" in DashboardPageConnector._registry

    def test_ml_dataflow_registered(self):
        import services.dashboard.connectors.ml  # noqa: F401
        from services.dashboard.connectors import DashboardPageConnector

        assert "MLデータフロー" in DashboardPageConnector._registry

    def test_overview_is_available(self):
        import services.dashboard.connectors.ml as ml_mod

        provider = _make_provider(_ml_nodes())
        connector = ml_mod.MLOverviewPageConnector()
        assert connector.is_available(provider) is True

    def test_overview_not_available_without_ml(self):
        import services.dashboard.connectors.ml as ml_mod

        nodes = [Node(id=1, type="file", name="r.md", format="md", properties={})]
        provider = _make_provider(nodes)
        connector = ml_mod.MLOverviewPageConnector()
        assert connector.is_available(provider) is False


# ====================================================================
# HTMLエクスポート テスト
# ====================================================================


class TestHTMLExport:
    """HTML生成テスト"""

    def test_overview_html(self):
        from services.dashboard.connectors.ml import _generate_overview_html

        provider = _make_provider(_ml_nodes())
        html = _generate_overview_html(provider)

        assert "ML概要" in html
        assert "実験メトリクス" in html
        assert "モデル" in html
        assert "データセット" in html

    def test_dataflow_html(self):
        from services.dashboard.connectors.ml import _generate_dataflow_html

        all_nodes = _ml_nodes() + _optimization_nodes() + _cae_nodes()
        all_rels = _ml_relations() + _cross_layer_relations()
        provider = _make_provider(all_nodes, all_rels)
        html = _generate_dataflow_html(provider)

        assert "三層データフロー" in html
        assert "Layer 1" in html
        assert "Layer 2" in html
        assert "Layer 3" in html
        assert "層間リレーション" in html

    def test_overview_html_empty(self):
        from services.dashboard.connectors.ml import _generate_overview_html

        provider = _make_provider([])
        html = _generate_overview_html(provider)
        assert "ML概要" in html

    def test_dataflow_html_empty(self):
        from services.dashboard.connectors.ml import _generate_dataflow_html

        provider = _make_provider([])
        html = _generate_dataflow_html(provider)
        assert "三層データフロー" in html


# ====================================================================
# ファイルサイズフォーマット テスト
# ====================================================================


class TestFormatFileSize:
    """_format_file_size のテスト"""

    def test_bytes(self):
        from services.dashboard.connectors.ml_query import _format_file_size

        assert _format_file_size(500) == "500 B"

    def test_kilobytes(self):
        from services.dashboard.connectors.ml_query import _format_file_size

        assert _format_file_size(2048) == "2.0 KB"

    def test_megabytes(self):
        from services.dashboard.connectors.ml_query import _format_file_size

        assert _format_file_size(52428800) == "50.0 MB"

    def test_gigabytes(self):
        from services.dashboard.connectors.ml_query import _format_file_size

        assert _format_file_size(2147483648) == "2.0 GB"


# ====================================================================
# メトリクス比較 テスト
# ====================================================================


class TestExperimentMetricKeys:
    """get_experiment_metric_keys のテスト"""

    def test_metric_keys_collected(self):
        from services.dashboard.connectors.ml_query import get_experiment_metric_keys

        provider = _make_provider(_multi_experiment_nodes())
        keys = get_experiment_metric_keys(provider)

        assert "best_val_accuracy" in keys
        assert "best_val_loss" in keys
        assert "best_epoch" in keys

    def test_metric_keys_ordered_by_frequency(self):
        from services.dashboard.connectors.ml_query import get_experiment_metric_keys

        provider = _make_provider(_multi_experiment_nodes())
        keys = get_experiment_metric_keys(provider)

        # best_val_accuracy/best_val_loss: 3回, best_epoch: 2回
        assert keys.index("best_val_accuracy") < keys.index("best_epoch")

    def test_metric_keys_empty(self):
        from services.dashboard.connectors.ml_query import get_experiment_metric_keys

        provider = _make_provider([])
        assert get_experiment_metric_keys(provider) == []


class TestExperimentComparisonData:
    """get_experiment_comparison_data のテスト"""

    def test_all_experiments(self):
        from services.dashboard.connectors.ml_query import get_experiment_comparison_data

        provider = _make_provider(_multi_experiment_nodes())
        data = get_experiment_comparison_data(provider)

        assert len(data["experiments"]) == 3
        assert "best_val_accuracy" in data["metric_keys"]
        assert "best_val_loss" in data["metric_keys"]

    def test_filter_by_experiment_ids(self):
        from services.dashboard.connectors.ml_query import get_experiment_comparison_data

        provider = _make_provider(_multi_experiment_nodes())
        data = get_experiment_comparison_data(provider, experiment_ids=["001", "002"])

        assert len(data["experiments"]) == 2
        ids = {e["id"] for e in data["experiments"]}
        assert ids == {"001", "002"}

    def test_filter_by_metric_keys(self):
        from services.dashboard.connectors.ml_query import get_experiment_comparison_data

        provider = _make_provider(_multi_experiment_nodes())
        data = get_experiment_comparison_data(provider, metric_keys=["best_val_accuracy"])

        assert data["metric_keys"] == ["best_val_accuracy"]

    def test_filter_nonexistent_metric(self):
        from services.dashboard.connectors.ml_query import get_experiment_comparison_data

        provider = _make_provider(_multi_experiment_nodes())
        data = get_experiment_comparison_data(provider, metric_keys=["nonexistent"])

        assert data["metric_keys"] == []

    def test_empty_provider(self):
        from services.dashboard.connectors.ml_query import get_experiment_comparison_data

        provider = _make_provider([])
        data = get_experiment_comparison_data(provider)

        assert data["experiments"] == []
        assert data["metric_keys"] == []

    def test_experiment_values(self):
        from services.dashboard.connectors.ml_query import get_experiment_comparison_data

        provider = _make_provider(_multi_experiment_nodes())
        data = get_experiment_comparison_data(provider, experiment_ids=["001"])

        exp = data["experiments"][0]
        assert exp["best_val_accuracy"] == 0.91
        assert exp["best_val_loss"] == 0.15


# ====================================================================
# ビュー保存・コネクターconfig テスト
# ====================================================================


class TestMLOverviewConnectorConfig:
    """MLOverviewPageConnector connector_config テスト"""

    def test_schema_has_tab(self):
        import services.dashboard.connectors.ml as ml_mod

        schema = ml_mod.MLOverviewPageConnector.get_connector_config_schema()
        keys = {f["key"] for f in schema}
        assert "tab" in keys
        assert "metric_keys" in keys
        assert "experiment_ids" in keys

    def test_schema_tab_comparison(self):
        import services.dashboard.connectors.ml as ml_mod

        schema = ml_mod.MLOverviewPageConnector.get_connector_config_schema()
        tab_field = next(f for f in schema if f["key"] == "tab")
        assert "comparison" in tab_field["help"]


class TestMLDataFlowConnectorConfig:
    """MLDataFlowPageConnector connector_config テスト"""

    def test_schema_has_layer_filter(self):
        import services.dashboard.connectors.ml as ml_mod

        schema = ml_mod.MLDataFlowPageConnector.get_connector_config_schema()
        keys = {f["key"] for f in schema}
        assert "layer_filter" in keys


class TestComparisonHTML:
    """メトリクス比較HTML生成テスト"""

    def test_comparison_html(self):
        from services.dashboard.connectors.ml import _generate_comparison_html

        provider = _make_provider(_multi_experiment_nodes())
        html = _generate_comparison_html(provider)

        assert "メトリクス比較" in html
        assert "001" in html
        assert "002" in html
        assert "003" in html

    def test_comparison_html_with_filter(self):
        from services.dashboard.connectors.ml import _generate_comparison_html

        provider = _make_provider(_multi_experiment_nodes())
        html = _generate_comparison_html(
            provider,
            metric_keys=["best_val_accuracy"],
            experiment_ids=["001", "002"],
        )

        assert "メトリクス比較" in html
        assert "best_val_accuracy" in html

    def test_comparison_html_empty(self):
        from services.dashboard.connectors.ml import _generate_comparison_html

        provider = _make_provider([])
        html = _generate_comparison_html(provider)

        assert "比較データがありません" in html
