"""Run Discovery ユーティリティ テスト (T8-1)

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

from unittest.mock import MagicMock

from services.parse.run_discovery import (
    RUN_STATUS_COMPLETED,
    RUN_STATUS_FAILED,
    RUN_STATUS_UNKNOWN,
    RunDiscoveryMixin,
    detect_run_status,
    extract_run_properties,
    find_input_output_pairs,
)

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


def _make_graph(nodes: list) -> MagicMock:
    """テスト用ProjectGraphを作成"""
    graph = MagicMock()
    model = MagicMock()
    model.nodes = nodes
    model.add_node = MagicMock(return_value=100)
    model.add_relation = MagicMock()
    graph.model = model
    return graph


# ====================================================================
# RunDiscoveryMixin テスト
# ====================================================================


class TestRunDiscoveryMixin:
    """RunDiscoveryMixinの基本テスト"""

    def test_discover_runs_default_empty(self):
        """デフォルト実装は空リストを返すこと"""
        mixin = RunDiscoveryMixin()
        graph = _make_graph([])
        assert mixin.discover_runs(graph) == []

    def test_register_run_creates_node(self):
        """register_runがノードとリレーションを作成すること"""
        mixin = RunDiscoveryMixin()
        mixin.run_type = "test_run"
        graph = _make_graph([])

        run_info = {
            "name": "test_run_1",
            "type": "test_run",
            "inputs": [1, 2],
            "outputs": [3],
            "media": [4],
            "properties": {"key": "value"},
            "status": RUN_STATUS_COMPLETED,
        }

        result = mixin.register_run(graph, run_info)
        assert result == 100  # add_node returns 100

        # ノード作成の確認
        graph.model.add_node.assert_called_once()
        call_kwargs = graph.model.add_node.call_args
        assert call_kwargs[1]["name"] == "test_run_1"
        assert call_kwargs[1]["node_type"] == "run"

        # リレーション作成の確認 (2 inputs + 1 output + 1 media = 4)
        assert graph.model.add_relation.call_count == 4

    def test_register_run_uses_default_type(self):
        """run_infoにtypeがない場合、self.run_typeを使用すること"""
        mixin = RunDiscoveryMixin()
        mixin.run_type = "default_type"
        graph = _make_graph([])

        run_info = {"name": "no_type_run", "properties": {}}
        mixin.register_run(graph, run_info)

        call_kwargs = graph.model.add_node.call_args[1]
        assert call_kwargs["properties"]["run_type"] == "default_type"

    def test_register_run_returns_none_on_failure(self):
        """ノード作成失敗時にNoneを返すこと"""
        mixin = RunDiscoveryMixin()
        graph = _make_graph([])
        graph.model.add_node.return_value = None

        result = mixin.register_run(graph, {"name": "fail", "properties": {}})
        assert result is None


# ====================================================================
# find_input_output_pairs テスト
# ====================================================================


class TestFindInputOutputPairs:
    """find_input_output_pairsのテスト"""

    def test_same_directory_pairing(self):
        """同一ディレクトリの入出力ファイルがペアになること"""
        nodes = [
            _make_node(1, "exp/data.csv"),
            _make_node(2, "exp/result.png"),
            _make_node(3, "other/data.csv"),
        ]
        graph = _make_graph(nodes)

        pairs = find_input_output_pairs(
            graph,
            input_extensions=(".csv",),
            output_extensions=(".png",),
            same_directory=True,
        )

        exp_pair = [p for p in pairs if p["directory"] == "exp"]
        assert len(exp_pair) == 1
        assert len(exp_pair[0]["inputs"]) == 1
        assert len(exp_pair[0]["outputs"]) == 1

    def test_empty_graph(self):
        """空グラフでは空リストを返すこと"""
        graph = _make_graph([])
        pairs = find_input_output_pairs(graph, input_extensions=(".csv",))
        assert pairs == []

    def test_no_matching_extensions(self):
        """拡張子が一致しない場合は空リストを返すこと"""
        nodes = [_make_node(1, "exp/data.txt")]
        graph = _make_graph(nodes)
        pairs = find_input_output_pairs(graph, input_extensions=(".csv",))
        assert pairs == []


# ====================================================================
# detect_run_status テスト
# ====================================================================


class TestDetectRunStatus:
    """detect_run_statusのテスト"""

    def test_empty_nodes(self):
        """空リストではunknownを返すこと"""
        assert detect_run_status([]) == RUN_STATUS_UNKNOWN

    def test_error_detected(self):
        """エラーキーワードがあればfailedを返すこと"""
        node = _make_node(1, "out.log", analysis_status="error in step 3")
        assert detect_run_status([node]) == RUN_STATUS_FAILED

    def test_success_detected(self):
        """成功キーワードがあればcompletedを返すこと"""
        node = _make_node(1, "out.log", analysis_status="completed successfully")
        assert detect_run_status([node]) == RUN_STATUS_COMPLETED

    def test_no_keywords(self):
        """キーワードがなければunknownを返すこと"""
        node = _make_node(1, "out.log", analysis_status="running step 5")
        assert detect_run_status([node]) == RUN_STATUS_UNKNOWN


# ====================================================================
# extract_run_properties テスト
# ====================================================================


class TestExtractRunProperties:
    """extract_run_propertiesのテスト"""

    def test_extracts_all_properties(self):
        """property_keysが空の場合すべてのプロパティを抽出すること"""
        nodes = [
            _make_node(1, "a.csv", temperature=300),
            _make_node(2, "b.csv", pressure=1.0),
        ]
        props = extract_run_properties(nodes)
        assert "temperature" in props
        assert "pressure" in props

    def test_filters_by_keys(self):
        """指定キーのみ抽出すること"""
        nodes = [_make_node(1, "a.csv", temperature=300, pressure=1.0)]
        props = extract_run_properties(nodes, property_keys=("temperature",))
        assert "temperature" in props
        assert "pressure" not in props

    def test_empty_nodes(self):
        """空リストでは空辞書を返すこと"""
        assert extract_run_properties([]) == {}
