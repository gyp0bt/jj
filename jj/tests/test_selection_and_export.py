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
from pathlib import Path

from jj_types import GraphModel, Node, Relation


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
        result = service.search_nodes(
            sample_graph, all_nodes=True, type_filter="Abaqusインプット"
        )
        assert len(result) == 3
        assert all(n.type == "Abaqusインプット" for n in result)

    def test_type_filter_only(self, sample_graph, tmp_path):
        from services.service.info import InfoService

        service = InfoService(project_root=tmp_path)
        result = service.search_nodes(
            sample_graph, all_nodes=True, type_filter="メッシュ"
        )
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
    def test_vocab_applied_to_property_keys(self):
        from services.parse.parsers.vocab_finalizer import _apply_vocab_to_dict

        vocab = {"stress": "応力", "displacement": "変位"}
        props = {"stress": {"0": 0.5}, "displacement": 1.2, "other": "val"}
        result = _apply_vocab_to_dict(props, vocab)
        assert "応力" in result
        assert "変位" in result
        assert "other" in result
        assert "stress" not in result
        assert "displacement" not in result

    def test_vocab_applied_to_string_values(self):
        from services.parse.parsers.vocab_finalizer import _apply_vocab_to_dict

        vocab = {"active": "アクティブ", "true": "有効"}
        props = {"active": "true", "count": 5}
        result = _apply_vocab_to_dict(props, vocab)
        assert result == {"アクティブ": "有効", "count": 5}

    def test_vocab_applied_to_nested_dict(self):
        from services.parse.parsers.vocab_finalizer import _apply_vocab_to_dict

        vocab = {"min": "最小", "max": "最大"}
        props = {"quality": {"min": 0.1, "max": 0.9}}
        result = _apply_vocab_to_dict(props, vocab)
        assert result == {"quality": {"最小": 0.1, "最大": 0.9}}

    def test_vocab_applied_to_list_values(self):
        from services.parse.parsers.vocab_finalizer import _apply_vocab_to_value

        vocab = {"warning": "警告", "error": "エラー"}
        result = _apply_vocab_to_value(["warning", "error", "info"], vocab)
        assert result == ["警告", "エラー", "info"]

    def test_no_double_replacement(self):
        from services.parse.parsers.vocab_finalizer import _apply_vocab_to_dict

        vocab = {"stress": "応力"}
        # 既に変換済みの値はそのまま
        props = {"応力": {"0": 0.5}}
        result = _apply_vocab_to_dict(props, vocab)
        assert result == {"応力": {"0": 0.5}}

    def test_empty_vocab(self):
        from services.parse.parsers.vocab_finalizer import _apply_vocab_to_dict

        props = {"stress": 1.0, "count": 5}
        result = _apply_vocab_to_dict(props, {})
        assert result == {"stress": 1.0, "count": 5}


# =========
# search_nodes vocab対応テスト（-id/-vでvocab変換後キーを検索）
# =========
class TestSearchNodesVocab:
    @pytest.fixture
    def vocab_graph(self):
        """vocab変換後のキー名でindex/versionが格納されたグラフ"""
        return GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="Abaqusインプット",
                    name="go_idx1.v1",
                    format="inp",
                    properties={"path": "go_idx1.v1.inp", "条件": "1", "バージョン": "1"},
                ),
                Node(
                    id=2,
                    type="Abaqusインプット",
                    name="go_idx2.v3",
                    format="inp",
                    properties={"path": "go_idx2.v3.inp", "条件": "2", "バージョン": "3"},
                ),
                Node(
                    id=3,
                    type="メッシュ",
                    name="mesh",
                    format="inp",
                    properties={"path": "mesh.inp", "条件": "1", "バージョン": "1"},
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
        result = service.search_nodes(
            vocab_graph, index_filters=["1"], version_filters=["1"]
        )
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
                    id=1, type="go", name="go_idx1.v1", format="inp",
                    properties={"path": "go_idx1.v1.inp", "index": "1", "version": "1", "active": "true"},
                ),
                Node(
                    id=2, type="go", name="go_idx1.v2", format="inp",
                    properties={"path": "old/go_idx1.v2.inp", "index": "1", "version": "2", "active": "false"},
                ),
                Node(
                    id=3, type="go", name="go_idx2.v1", format="inp",
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
        result = service.search_nodes(
            active_graph, index_filters=["1"], active_only=True
        )
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
                    id=1, type="go", name="go_idx1", format="inp",
                    properties={"path": "go_idx1.inp", "応力": "100MPa"},
                ),
            ],
            relations=[],
        )
        service = InfoService(project_root=tmp_path)
        output_path, count = service.export_data(
            graph, "csv", nodes=graph.nodes, output_file="test.csv"
        )
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
                    id=1, type="go", name="go_idx1", format="inp",
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

        service = __import__("services.service.info", fromlist=["InfoService"]).InfoService(
            project_root=tmp_path
        )
        output_path, count = service.export_data(
            nested_graph, "json", nodes=nested_graph.nodes, output_file="test.json"
        )
        data = json_mod.loads(output_path.read_text(encoding="utf-8"))
        # デフォルトでは平坦化されない
        assert isinstance(data[0]["stress"], dict)
        assert data[0]["stress"]["center"] == 0.5

    def test_json_flatten_when_specified(self, nested_graph, tmp_path):
        import json as json_mod

        service = __import__("services.service.info", fromlist=["InfoService"]).InfoService(
            project_root=tmp_path
        )
        output_path, count = service.export_data(
            nested_graph, "json", nodes=nested_graph.nodes, output_file="test.json",
            flatten=True,
        )
        data = json_mod.loads(output_path.read_text(encoding="utf-8"))
        # 平坦化される
        assert "stress.center" in data[0]
        assert data[0]["stress.center"] == 0.5

    def test_csv_always_flattens(self, nested_graph, tmp_path):
        service = __import__("services.service.info", fromlist=["InfoService"]).InfoService(
            project_root=tmp_path
        )
        output_path, count = service.export_data(
            nested_graph, "csv", nodes=nested_graph.nodes, output_file="test.csv"
        )
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
        from config import GraphConfig, get_config_dir

        config_dir = tmp_path / ".jj" / "config"
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
