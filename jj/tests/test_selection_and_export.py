"""共通選択・CSV平坦化・VocabFinalizerのテスト

status-047で追加された機能のテスト:
- expand_ranges(): 範囲展開ユーティリティ
- InfoService.search_nodes(): -all, -type フィルタ
- _flatten_properties(): プロパティ平坦化
- VocabFinalizer: 最終パスvocab置換

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
