"""共通選択・CSV平坦化・VocabFinalizerのテスト

status-047/048で追加された機能のテスト:
- expand_ranges(): 範囲展開ユーティリティ
- InfoService.search_nodes(): -all, -type, -active, vocab対応 フィルタ
- _flatten_properties(): プロパティ平坦化
- VocabFinalizer: 最終パスvocab置換
- CSVエクスポートUTF-8 BOM
- JSONエクスポート平坦化オプション

[READMEへ戻る](../README.md)
"""

import pytest

from jj_types import GraphModel, Node


# =========
# expand_ranges テスト
# =========
class TestExpandRanges:
    def test_none_returns_none(self):
        from services.lib.selection import expand_ranges

        assert expand_ranges(None) is None

    def test_single_values(self):
        from services.lib.selection import expand_ranges

        assert expand_ranges(["1", "3", "5"]) == ["1", "3", "5"]

    def test_range_expansion(self):
        from services.lib.selection import expand_ranges

        assert expand_ranges(["1..3"]) == ["1", "2", "3"]

    def test_range_expansion_single(self):
        from services.lib.selection import expand_ranges

        assert expand_ranges(["5..5"]) == ["5"]

    def test_range_expansion_reverse(self):
        from services.lib.selection import expand_ranges

        assert expand_ranges(["3..1"]) == ["3", "2", "1"]

    def test_mixed_values_and_ranges(self):
        from services.lib.selection import expand_ranges

        result = expand_ranges(["1..3", "5", "7..9"])
        assert result == ["1", "2", "3", "5", "7", "8", "9"]

    def test_non_numeric_passthrough(self):
        from services.lib.selection import expand_ranges

        assert expand_ranges(["abc", "def"]) == ["abc", "def"]

    def test_empty_list(self):
        from services.lib.selection import expand_ranges

        assert expand_ranges([]) == []


# =========
# InfoService.search_nodes テスト（-all, -type）
# =========
class TestSearchNodesExtended:
    @pytest.fixture
    def sample_graph(self):
        return GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="Abaqusインプット",
                    name="go_idx1.v1",
                    format="inp",
                    properties={"path": "go/go_idx1.v1.inp", "index": "1", "version": "1"},
                ),
                Node(
                    id=2,
                    type="Abaqusインプット",
                    name="go_idx2.v1",
                    format="inp",
                    properties={"path": "go/go_idx2.v1.inp", "index": "2", "version": "1"},
                ),
                Node(
                    id=3,
                    type="メッシュ",
                    name="mesh",
                    format="inp",
                    properties={"path": "mesh.inp", "index": "1", "version": "1"},
                ),
                Node(
                    id=4,
                    type="Abaqusインプット",
                    name="go_idx1.v2",
                    format="inp",
                    properties={
                        "path": "go/go_idx1.v2.inp",
                        "index": "1",
                        "version": "2",
                        "応力": {"0": 0.5, "1": 1.0},
                    },
                ),
            ],
            relations=[],
        )

    def test_all_nodes(self, sample_graph, tmp_path):
        from services.service.info import InfoService

        service = InfoService(project_root=tmp_path)
        result = service.search_nodes(sample_graph, all_nodes=True)
        assert len(result) == 4

    def test_all_nodes_with_type_filter(self, sample_graph, tmp_path):
        from services.service.info import InfoService

        service = InfoService(project_root=tmp_path)
        result = service.search_nodes(sample_graph, all_nodes=True, type_filter="Abaqusインプット")
        assert len(result) == 3
        assert all(n.type == "Abaqusインプット" for n in result)

    def test_type_filter_only(self, sample_graph, tmp_path):
        from services.service.info import InfoService

        service = InfoService(project_root=tmp_path)
        result = service.search_nodes(sample_graph, all_nodes=True, type_filter="メッシュ")
        assert len(result) == 1
        assert result[0].name == "mesh"

    def test_index_with_type_filter(self, sample_graph, tmp_path):
        from services.service.info import InfoService

        service = InfoService(project_root=tmp_path)
        result = service.search_nodes(
            sample_graph,
            index_filters=["1"],
            type_filter="Abaqusインプット",
        )
        assert len(result) == 2
        for n in result:
            assert n.properties["index"] == "1"
            assert n.type == "Abaqusインプット"


# =========
# _flatten_properties テスト
# =========
class TestFlattenProperties:
    def test_flat_properties(self):
        from services.service.info import _flatten_properties

        props = {"name": "test", "value": 42}
        result = _flatten_properties(props)
        assert result == {"name": "test", "value": 42}

    def test_nested_dict(self):
        from services.service.info import _flatten_properties

        props = {"mesh_quality": {"aspect_ratio": {"min": 0.5, "max": 1.0}}}
        result = _flatten_properties(props)
        assert result == {
            "mesh_quality.aspect_ratio.min": 0.5,
            "mesh_quality.aspect_ratio.max": 1.0,
        }

    def test_mixed_properties(self):
        from services.service.info import _flatten_properties

        props = {
            "name": "test",
            "stress": {"0(center)": 0.25, "1": None},
            "tags": ["a", "b"],
        }
        result = _flatten_properties(props)
        assert result == {
            "name": "test",
            "stress.0(center)": 0.25,
            "stress.1": None,
            "tags": ["a", "b"],
        }

    def test_empty_dict(self):
        from services.service.info import _flatten_properties

        assert _flatten_properties({}) == {}

    def test_deeply_nested(self):
        from services.service.info import _flatten_properties

        props = {"a": {"b": {"c": {"d": 1}}}}
        result = _flatten_properties(props)
        assert result == {"a.b.c.d": 1}


# =========
# VocabFinalizer テスト
# =========
class TestVocabFinalizer:
    """VocabFinalizerは廃止済み（空操作）。プロパティは変更されないことを確認。"""

    def test_vocab_finalizer_is_noop(self):
        """VocabFinalizer.apply()はグラフを変更しない"""
        from config import GraphConfig
        from services.graph.project_graph import ProjectGraph
        from services.parse.parsers.vocab_finalizer import VocabFinalizer

        config = GraphConfig.from_dict({"vocab": {"stress": "応力"}})
        node = Node(
            id=1,
            type="go",
            name="test",
            format="inp",
            properties={"stress": {"0": 0.5}, "displacement": 1.2, "other": "val"},
        )
        pg = ProjectGraph(nodes=[node], relations=[], project_root="/tmp", config=config)
        result = VocabFinalizer().apply(pg)
        # プロパティは変更されない（生キーのまま）
        assert "stress" in result.nodes[0].properties
        assert "displacement" in result.nodes[0].properties
        assert "other" in result.nodes[0].properties

    def test_properties_unchanged_with_string_values(self):
        """文字列値もvocab変換されない"""
        from config import GraphConfig
        from services.graph.project_graph import ProjectGraph
        from services.parse.parsers.vocab_finalizer import VocabFinalizer

        config = GraphConfig.from_dict({"vocab": {"active": "アクティブ", "true": "有効"}})
        node = Node(
            id=1,
            type="go",
            name="test",
            format="inp",
            properties={"active": "true", "count": 5},
        )
        pg = ProjectGraph(nodes=[node], relations=[], project_root="/tmp", config=config)
        result = VocabFinalizer().apply(pg)
        assert result.nodes[0].properties == {"active": "true", "count": 5}

    def test_properties_unchanged_with_nested_dict(self):
        """ネストされた辞書もvocab変換されない"""
        from config import GraphConfig
        from services.graph.project_graph import ProjectGraph
        from services.parse.parsers.vocab_finalizer import VocabFinalizer

        config = GraphConfig.from_dict({"vocab": {"min": "最小", "max": "最大"}})
        node = Node(
            id=1,
            type="go",
            name="test",
            format="inp",
            properties={"quality": {"min": 0.1, "max": 0.9}},
        )
        pg = ProjectGraph(nodes=[node], relations=[], project_root="/tmp", config=config)
        result = VocabFinalizer().apply(pg)
        assert result.nodes[0].properties == {"quality": {"min": 0.1, "max": 0.9}}

    def test_properties_unchanged_with_list_values(self):
        """リスト値もvocab変換されない"""
        from config import GraphConfig
        from services.graph.project_graph import ProjectGraph
        from services.parse.parsers.vocab_finalizer import VocabFinalizer

        config = GraphConfig.from_dict({"vocab": {"warning": "警告", "error": "エラー"}})
        node = Node(
            id=1,
            type="go",
            name="test",
            format="inp",
            properties={"messages": ["warning", "error", "info"]},
        )
        pg = ProjectGraph(nodes=[node], relations=[], project_root="/tmp", config=config)
        result = VocabFinalizer().apply(pg)
        assert result.nodes[0].properties["messages"] == ["warning", "error", "info"]

    def test_already_translated_values_unchanged(self):
        """既に日本語キーのプロパティも変更されない"""
        from config import GraphConfig
        from services.graph.project_graph import ProjectGraph
        from services.parse.parsers.vocab_finalizer import VocabFinalizer

        config = GraphConfig.from_dict({"vocab": {"stress": "応力"}})
        node = Node(
            id=1,
            type="go",
            name="test",
            format="inp",
            properties={"応力": {"0": 0.5}},
        )
        pg = ProjectGraph(nodes=[node], relations=[], project_root="/tmp", config=config)
        result = VocabFinalizer().apply(pg)
        assert result.nodes[0].properties == {"応力": {"0": 0.5}}

    def test_empty_vocab_properties_unchanged(self):
        """空vocabでもプロパティは変更されない"""
        from config import GraphConfig
        from services.graph.project_graph import ProjectGraph
        from services.parse.parsers.vocab_finalizer import VocabFinalizer

        config = GraphConfig.from_dict({"vocab": {}})
        node = Node(
            id=1,
            type="go",
            name="test",
            format="inp",
            properties={"stress": 1.0, "count": 5},
        )
        pg = ProjectGraph(nodes=[node], relations=[], project_root="/tmp", config=config)
        result = VocabFinalizer().apply(pg)
        assert result.nodes[0].properties == {"stress": 1.0, "count": 5}


# =========
# search_nodes vocab対応テスト（-id/-vでvocab変換後キーを検索）
# =========
class TestSearchNodesVocab:
    @pytest.fixture
    def vocab_graph(self):
        """生キー（index/version）でindex/versionが格納されたグラフ"""
        return GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="Abaqusインプット",
                    name="go_idx1.v1",
                    format="inp",
                    properties={"path": "go_idx1.v1.inp", "index": "1", "version": "1"},
                ),
                Node(
                    id=2,
                    type="Abaqusインプット",
                    name="go_idx2.v3",
                    format="inp",
                    properties={"path": "go_idx2.v3.inp", "index": "2", "version": "3"},
                ),
                Node(
                    id=3,
                    type="メッシュ",
                    name="mesh",
                    format="inp",
                    properties={"path": "mesh.inp", "index": "1", "version": "1"},
                ),
            ],
            relations=[],
        )

    def test_search_by_index_with_vocab_key(self, vocab_graph, tmp_path):
        from services.service.info import InfoService

        service = InfoService(project_root=tmp_path)
        result = service.search_nodes(vocab_graph, index_filters=["1"])
        assert len(result) == 2
        names = {n.name for n in result}
        assert "go_idx1.v1" in names
        assert "mesh" in names

    def test_search_by_version_with_vocab_key(self, vocab_graph, tmp_path):
        from services.service.info import InfoService

        service = InfoService(project_root=tmp_path)
        result = service.search_nodes(vocab_graph, version_filters=["3"])
        assert len(result) == 1
        assert result[0].name == "go_idx2.v3"

    def test_search_combined_vocab_keys(self, vocab_graph, tmp_path):
        from services.service.info import InfoService

        service = InfoService(project_root=tmp_path)
        result = service.search_nodes(vocab_graph, index_filters=["1"], version_filters=["1"])
        assert len(result) == 2
        names = {n.name for n in result}
        assert "go_idx1.v1" in names
        assert "mesh" in names


# =========
# active_only フィルタテスト
# =========
class TestSearchNodesActive:
    @pytest.fixture
    def active_graph(self):
        return GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1.v1",
                    format="inp",
                    properties={"path": "go_idx1.v1.inp", "index": "1", "version": "1", "active": "true"},
                ),
                Node(
                    id=2,
                    type="go",
                    name="go_idx1.v2",
                    format="inp",
                    properties={"path": "old/go_idx1.v2.inp", "index": "1", "version": "2", "active": "false"},
                ),
                Node(
                    id=3,
                    type="go",
                    name="go_idx2.v1",
                    format="inp",
                    properties={"path": "go_idx2.v1.inp", "index": "2", "version": "1", "active": "true"},
                ),
            ],
            relations=[],
        )

    def test_active_only_filter(self, active_graph, tmp_path):
        from services.service.info import InfoService

        service = InfoService(project_root=tmp_path)
        result = service.search_nodes(active_graph, all_nodes=True, active_only=True)
        assert len(result) == 2
        assert all(n.properties["active"] == "true" for n in result)

    def test_active_with_index(self, active_graph, tmp_path):
        from services.service.info import InfoService

        service = InfoService(project_root=tmp_path)
        result = service.search_nodes(active_graph, index_filters=["1"], active_only=True)
        assert len(result) == 1
        assert result[0].name == "go_idx1.v1"


# =========
# CSVエクスポート UTF-8 BOMテスト
# =========
class TestCsvExportBom:
    def test_csv_has_bom(self, tmp_path):
        from services.service.info import InfoService

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1",
                    format="inp",
                    properties={"path": "go_idx1.inp", "応力": "100MPa"},
                ),
            ],
            relations=[],
        )
        service = InfoService(project_root=tmp_path)
        output_path, _count = service.export_data(graph, "csv", nodes=graph.nodes, output_file="test.csv")
        raw = output_path.read_bytes()
        # UTF-8 BOM (EF BB BF) が先頭に付いていることを確認
        assert raw[:3] == b"\xef\xbb\xbf"
        # 日本語が含まれていることを確認
        content = raw.decode("utf-8-sig")
        assert "応力" in content
        assert "100MPa" in content


# =========
# JSONエクスポート 平坦化オプションテスト
# =========
class TestJsonExportFlatten:
    @pytest.fixture
    def nested_graph(self):
        return GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1",
                    format="inp",
                    properties={
                        "path": "go_idx1.inp",
                        "stress": {"center": 0.5, "edge": 1.0},
                    },
                ),
            ],
            relations=[],
        )

    def test_json_no_flatten_by_default(self, nested_graph, tmp_path):
        import json as json_mod

        service = __import__("services.service.info", fromlist=["InfoService"]).InfoService(project_root=tmp_path)
        output_path, _count = service.export_data(
            nested_graph, "json", nodes=nested_graph.nodes, output_file="test.json"
        )
        data = json_mod.loads(output_path.read_text(encoding="utf-8"))
        # デフォルトでは平坦化されない
        assert isinstance(data[0]["stress"], dict)
        assert data[0]["stress"]["center"] == 0.5

    def test_json_flatten_when_specified(self, nested_graph, tmp_path):
        import json as json_mod

        service = __import__("services.service.info", fromlist=["InfoService"]).InfoService(project_root=tmp_path)
        output_path, _count = service.export_data(
            nested_graph,
            "json",
            nodes=nested_graph.nodes,
            output_file="test.json",
            flatten=True,
        )
        data = json_mod.loads(output_path.read_text(encoding="utf-8"))
        # 平坦化される
        assert "stress.center" in data[0]
        assert data[0]["stress.center"] == 0.5

    def test_csv_always_flattens(self, nested_graph, tmp_path):
        service = __import__("services.service.info", fromlist=["InfoService"]).InfoService(project_root=tmp_path)
        output_path, _count = service.export_data(nested_graph, "csv", nodes=nested_graph.nodes, output_file="test.csv")
        content = output_path.read_text(encoding="utf-8-sig")
        assert "stress.center" in content


# =========
# parse full_mode テスト
# =========
class TestParseFullMode:
    def test_requires_full_default_false(self):
        from services.parse.base import AbstractFileParser

        assert AbstractFileParser.requires_full is False

    def test_mesh_parser_requires_full(self):
        from services.parse.connectors.abaqus.mesh_parser import AbaqusMeshParser

        assert AbaqusMeshParser.requires_full is True

    def test_parse_skips_full_parsers_in_lite_mode(self):
        from services.parse.base import get_parser_registry

        registry = get_parser_registry()
        full_parsers = [p for p in registry if p.requires_full]
        lite_parsers = [p for p in registry if not p.requires_full]
        # AbaqusMeshParserはfull_only
        assert any(p.__name__ == "AbaqusMeshParser" for p in full_parsers)
        # lite_parsersにAbaqusMeshParserは含まれない
        assert not any(p.__name__ == "AbaqusMeshParser" for p in lite_parsers)


# =========
# GraphConfig vocab.yamlマージテスト
# =========
class TestGraphConfigVocabMerge:
    def test_vocab_yaml_merged_into_graph_config(self, tmp_path):
        import yaml

        from config import GraphConfig

        config_dir = tmp_path / ".j2" / "config"
        config_dir.mkdir(parents=True)

        # config.yaml にvocab設定
        config_data = {"vocab": {"idx": "条件", "v": "バージョン"}}
        with (config_dir / "config.yaml").open("w", encoding="utf-8") as f:
            yaml.safe_dump(config_data, f, allow_unicode=True)

        # vocab.yaml にmapping追加（config.yamlにはない項目）
        vocab_data = {"mapping": {"stress-result": "応力結果"}, "categories": {}}
        with (config_dir / "vocab.yaml").open("w", encoding="utf-8") as f:
            yaml.safe_dump(vocab_data, f, allow_unicode=True)

        gc = GraphConfig.load(base_dir=tmp_path)
        # config.yamlのvocabが含まれる
        assert gc.vocab.get("idx") == "条件"
        assert gc.vocab.get("v") == "バージョン"
        # vocab.yamlのmappingもマージされている
        assert gc.vocab.get("stress-result") == "応力結果"


# =========
# ExportConfig テスト
# =========
class TestExportConfig:
    def test_default_export_config(self):
        from config import ExportConfig

        ec = ExportConfig.from_dict({})
        assert ec.csv_columns is None
        assert ec.units == {}
        assert ec.csv_unit_format == "header"

    def test_csv_columns_and_units(self):
        from config import ExportConfig

        data = {
            "csv-columns": ["条件", "バージョン", "応力"],
            "units": {"応力": "MPa", "変位": "mm"},
            "csv-unit-format": "row",
        }
        ec = ExportConfig.from_dict(data)
        assert ec.csv_columns == ["条件", "バージョン", "応力"]
        assert ec.units == {"応力": "MPa", "変位": "mm"}
        assert ec.csv_unit_format == "row"

    def test_invalid_unit_format_raises(self):
        from config import ExportConfig

        with pytest.raises(ValueError, match="csv-unit-format"):
            ExportConfig.from_dict({"csv-unit-format": "invalid"})

    def test_graph_config_includes_export(self, tmp_path):
        import yaml

        from config import GraphConfig

        config_dir = tmp_path / ".j2" / "config"
        config_dir.mkdir(parents=True)
        config_data = {
            "export": {
                "csv-columns": ["応力"],
                "units": {"応力": "MPa"},
                "csv-unit-format": "header",
            }
        }
        with (config_dir / "config.yaml").open("w", encoding="utf-8") as f:
            yaml.safe_dump(config_data, f, allow_unicode=True)

        gc = GraphConfig.load(base_dir=tmp_path)
        assert gc.export.csv_columns == ["応力"]
        assert gc.export.units == {"応力": "MPa"}


# =========
# CSVエクスポート 単位付きヘッダーテスト
# =========
class TestCsvExportUnits:
    @pytest.fixture
    def unit_graph(self):
        return GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1",
                    format="inp",
                    properties={"path": "go_idx1.inp", "応力": 100.5, "変位": 2.3},
                ),
            ],
            relations=[],
        )

    def test_csv_header_unit_format(self, unit_graph, tmp_path):
        import yaml

        from services.service.info import InfoService

        config_dir = tmp_path / ".j2" / "config"
        config_dir.mkdir(parents=True)
        config_data = {
            "export": {
                "units": {"応力": "MPa", "変位": "mm"},
                "csv-unit-format": "header",
            }
        }
        with (config_dir / "config.yaml").open("w", encoding="utf-8") as f:
            yaml.safe_dump(config_data, f, allow_unicode=True)

        service = InfoService(project_root=tmp_path)
        output_path, _count = service.export_data(unit_graph, "csv", nodes=unit_graph.nodes, output_file="test.csv")
        content = output_path.read_text(encoding="utf-8-sig")
        lines = content.strip().split("\n")
        header = lines[0]
        # ヘッダーに単位が含まれる
        assert "応力[MPa]" in header
        assert "変位[mm]" in header
        # name等は単位なし
        assert "name[" not in header

    def test_csv_row_unit_format(self, unit_graph, tmp_path):
        import yaml

        from services.service.info import InfoService

        config_dir = tmp_path / ".j2" / "config"
        config_dir.mkdir(parents=True)
        config_data = {
            "export": {
                "units": {"応力": "MPa", "変位": "mm"},
                "csv-unit-format": "row",
            }
        }
        with (config_dir / "config.yaml").open("w", encoding="utf-8") as f:
            yaml.safe_dump(config_data, f, allow_unicode=True)

        service = InfoService(project_root=tmp_path)
        output_path, _count = service.export_data(unit_graph, "csv", nodes=unit_graph.nodes, output_file="test.csv")
        content = output_path.read_text(encoding="utf-8-sig")
        lines = content.strip().split("\n")
        # 1行目: カラム名（単位なし）
        assert "応力[MPa]" not in lines[0]
        assert "応力" in lines[0]
        # 2行目: 単位行
        assert "MPa" in lines[1]
        assert "mm" in lines[1]
        # 3行目: データ
        assert "100.5" in lines[2]


# =========
# CSVエクスポート カラム制限テスト
# =========
class TestCsvExportColumns:
    def test_csv_columns_from_config(self, tmp_path):
        import yaml

        from services.service.info import InfoService

        config_dir = tmp_path / ".j2" / "config"
        config_dir.mkdir(parents=True)
        config_data = {
            "export": {
                "csv-columns": ["応力"],
            }
        }
        with (config_dir / "config.yaml").open("w", encoding="utf-8") as f:
            yaml.safe_dump(config_data, f, allow_unicode=True)

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1",
                    format="inp",
                    properties={"path": "go.inp", "応力": 100, "変位": 2.3, "dat_warning": "x"},
                ),
            ],
            relations=[],
        )
        service = InfoService(project_root=tmp_path)
        output_path, _count = service.export_data(graph, "csv", nodes=graph.nodes, output_file="test.csv")
        content = output_path.read_text(encoding="utf-8-sig")
        header = content.strip().split("\n")[0]
        # 応力はある
        assert "応力" in header
        # dat_warningはない
        assert "dat_warning" not in header
        # baseキー(name/type/format)は常に含まれる
        assert "name" in header

    def test_csv_columns_preserve_config_order(self, tmp_path):
        import yaml

        from services.service.info import InfoService

        config_dir = tmp_path / ".j2" / "config"
        config_dir.mkdir(parents=True)
        config_data = {
            "export": {
                "csv-columns": ["変位", "応力"],
            }
        }
        with (config_dir / "config.yaml").open("w", encoding="utf-8") as f:
            yaml.safe_dump(config_data, f, allow_unicode=True)

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1",
                    format="inp",
                    properties={"path": "go.inp", "応力": 100, "変位": 2.3},
                ),
            ],
            relations=[],
        )
        service = InfoService(project_root=tmp_path)
        output_path, _count = service.export_data(graph, "csv", nodes=graph.nodes, output_file="test.csv")
        content = output_path.read_text(encoding="utf-8-sig")
        header = content.strip().split("\n")[0]
        # config順: 変位 → 応力
        idx_henni = header.index("変位")
        idx_ouryoku = header.index("応力")
        assert idx_henni < idx_ouryoku


# =========
# JSONプロパティ平坦化テスト
# =========
class TestJsonPropertyFlatten:
    def test_flatten_json_simple(self):
        from services.parse.parsers.json_property_parser import _flatten_json

        data = {"center": 0.25, "edge": 1.0}
        result = _flatten_json(data, prefix="stress")
        assert result == {"stress.center": 0.25, "stress.edge": 1.0}

    def test_flatten_json_nested(self):
        from services.parse.parsers.json_property_parser import _flatten_json

        data = {"results": {"max": 1.5, "min": 0.1}}
        result = _flatten_json(data, prefix="stress")
        assert result == {
            "stress.results.max": 1.5,
            "stress.results.min": 0.1,
        }

    def test_flatten_json_no_prefix(self):
        from services.parse.parsers.json_property_parser import _flatten_json

        data = {"a": 1, "b": {"c": 2}}
        result = _flatten_json(data, prefix="")
        assert result == {"a": 1, "b.c": 2}

    def test_flatten_json_list_values(self):
        from services.parse.parsers.json_property_parser import _flatten_json

        data = {"values": [1, 2, 3], "scalar": 5}
        result = _flatten_json(data, prefix="test")
        assert result == {"test.values": [1, 2, 3], "test.scalar": 5}


# =========
# MeshInheritParser テスト
# =========
class TestMeshInheritParser:
    def test_parser_registered(self):
        from services.parse.base import get_parser_registry

        registry = get_parser_registry()
        assert any(p.__name__ == "MeshInheritParser" for p in registry)

    def test_priority_after_includes_and_mesh(self):
        from services.parse.parsers.mesh_inherit_parser import MeshInheritParser

        assert MeshInheritParser.priority > 40  # IncludesRelationParser
        assert MeshInheritParser.priority > 80  # AbaqusMeshParser


# =========
# CSVカラムglobパターンテスト
# =========
class TestCsvExportColumnsGlob:
    def test_csv_columns_glob_pattern(self, tmp_path):
        """csv-columnsでglobパターンが使える"""
        import yaml

        from services.service.info import InfoService

        config_dir = tmp_path / ".j2" / "config"
        config_dir.mkdir(parents=True)
        config_data = {
            "export": {
                "csv-columns": ["stress.*"],
            }
        }
        with (config_dir / "config.yaml").open("w", encoding="utf-8") as f:
            yaml.safe_dump(config_data, f, allow_unicode=True)

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1",
                    format="inp",
                    properties={
                        "path": "go.inp",
                        "stress.center": 100.5,
                        "stress.edge": 200.3,
                        "displacement": 2.3,
                    },
                ),
            ],
            relations=[],
        )
        service = InfoService(project_root=tmp_path)
        output_path, _count = service.export_data(graph, "csv", nodes=graph.nodes, output_file="test.csv")
        content = output_path.read_text(encoding="utf-8-sig")
        header = content.strip().split("\n")[0]
        # stress.*にマッチするカラムはある
        assert "stress.center" in header
        assert "stress.edge" in header
        # displacementはマッチしないので含まれない
        assert "displacement" not in header
        # baseキーは常に含まれる
        assert "name" in header

    def test_csv_columns_glob_preserves_order(self, tmp_path):
        """globパターンでもconfig順が保持される"""
        import yaml

        from services.service.info import InfoService

        config_dir = tmp_path / ".j2" / "config"
        config_dir.mkdir(parents=True)
        config_data = {
            "export": {
                "csv-columns": ["disp*", "stress*"],
            }
        }
        with (config_dir / "config.yaml").open("w", encoding="utf-8") as f:
            yaml.safe_dump(config_data, f, allow_unicode=True)

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1",
                    format="inp",
                    properties={
                        "path": "go.inp",
                        "stress.center": 100,
                        "displacement": 2.3,
                    },
                ),
            ],
            relations=[],
        )
        service = InfoService(project_root=tmp_path)
        output_path, _count = service.export_data(graph, "csv", nodes=graph.nodes, output_file="test.csv")
        content = output_path.read_text(encoding="utf-8-sig")
        header = content.strip().split("\n")[0]
        idx_disp = header.index("displacement")
        idx_stress = header.index("stress.center")
        # disp* が先に来る
        assert idx_disp < idx_stress


# =========
# CSV単位globパターンテスト
# =========
class TestCsvExportUnitsGlob:
    def test_units_glob_pattern_header_format(self, tmp_path):
        """unitsでglobパターンが使える（header形式）"""
        import yaml

        from services.service.info import InfoService

        config_dir = tmp_path / ".j2" / "config"
        config_dir.mkdir(parents=True)
        config_data = {
            "export": {
                "units": {"stress*": "MPa", "displacement": "mm"},
                "csv-unit-format": "header",
            }
        }
        with (config_dir / "config.yaml").open("w", encoding="utf-8") as f:
            yaml.safe_dump(config_data, f, allow_unicode=True)

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1",
                    format="inp",
                    properties={
                        "path": "go.inp",
                        "stress.center": 100.5,
                        "stress.edge": 200.3,
                        "displacement": 2.3,
                    },
                ),
            ],
            relations=[],
        )
        service = InfoService(project_root=tmp_path)
        output_path, _count = service.export_data(graph, "csv", nodes=graph.nodes, output_file="test.csv")
        content = output_path.read_text(encoding="utf-8-sig")
        header = content.strip().split("\n")[0]
        # globパターン stress* にマッチするカラムに単位が付く
        assert "stress.center[MPa]" in header
        assert "stress.edge[MPa]" in header
        # 完全一致のカラムにも単位が付く
        assert "displacement[mm]" in header
        # name等は単位なし
        assert "name[" not in header

    def test_units_glob_pattern_row_format(self, tmp_path):
        """unitsでglobパターンが使える（row形式）"""
        import yaml

        from services.service.info import InfoService

        config_dir = tmp_path / ".j2" / "config"
        config_dir.mkdir(parents=True)
        config_data = {
            "export": {
                "units": {"stress*": "MPa"},
                "csv-unit-format": "row",
            }
        }
        with (config_dir / "config.yaml").open("w", encoding="utf-8") as f:
            yaml.safe_dump(config_data, f, allow_unicode=True)

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1",
                    format="inp",
                    properties={
                        "path": "go.inp",
                        "stress.center": 100.5,
                        "stress.edge": 200.3,
                    },
                ),
            ],
            relations=[],
        )
        service = InfoService(project_root=tmp_path)
        output_path, _count = service.export_data(graph, "csv", nodes=graph.nodes, output_file="test.csv")
        content = output_path.read_text(encoding="utf-8-sig")
        lines = content.strip().split("\n")
        # 1行目: カラム名（単位なし）
        assert "stress.center[MPa]" not in lines[0]
        assert "stress.center" in lines[0]
        # 2行目: 単位行にMPaが含まれる
        assert "MPa" in lines[1]

    def test_units_exact_match_priority(self, tmp_path):
        """完全一致がglobパターンより優先される"""
        import yaml

        from services.service.info import InfoService

        config_dir = tmp_path / ".j2" / "config"
        config_dir.mkdir(parents=True)
        config_data = {
            "export": {
                "units": {"stress*": "MPa", "stress.center": "GPa"},
                "csv-unit-format": "header",
            }
        }
        with (config_dir / "config.yaml").open("w", encoding="utf-8") as f:
            yaml.safe_dump(config_data, f, allow_unicode=True)

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1",
                    format="inp",
                    properties={
                        "path": "go.inp",
                        "stress.center": 100.5,
                        "stress.edge": 200.3,
                    },
                ),
            ],
            relations=[],
        )
        service = InfoService(project_root=tmp_path)
        output_path, _count = service.export_data(graph, "csv", nodes=graph.nodes, output_file="test.csv")
        content = output_path.read_text(encoding="utf-8-sig")
        header = content.strip().split("\n")[0]
        # stress.centerは完全一致でGPa
        assert "stress.center[GPa]" in header
        # stress.edgeはglob stress* でMPa
        assert "stress.edge[MPa]" in header
