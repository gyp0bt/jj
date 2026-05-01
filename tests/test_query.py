"""services/query パッケージのテスト

汎用フィルタ（filters.py）とソート（sort.py）の単体テスト。
props条件式フィルタの汎用化（dict行データ/Nodeオブジェクト両対応）を
重点的にテストする。

QueryServiceのノードフィルタリング統合テストも含む。
"""

from __future__ import annotations

import pytest

from jj_types import Node

# ====================================================================
# filters.py テスト
# ====================================================================


class TestIsTruthy:
    """is_truthy のテスト"""

    def test_bool_true(self):
        from services.graph.query import is_truthy

        assert is_truthy(True) is True

    def test_bool_false(self):
        from services.graph.query import is_truthy

        assert is_truthy(False) is False

    def test_string_true(self):
        from services.graph.query import is_truthy

        assert is_truthy("true") is True
        assert is_truthy("True") is True
        assert is_truthy("TRUE") is True
        assert is_truthy("  true  ") is True

    def test_string_false(self):
        from services.graph.query import is_truthy

        assert is_truthy("false") is False
        assert is_truthy("False") is False

    def test_none(self):
        from services.graph.query import is_truthy

        assert is_truthy(None) is False

    def test_int(self):
        from services.graph.query import is_truthy

        assert is_truthy(1) is True
        assert is_truthy(0) is False


class TestApplyFilters:
    """apply_filters のテスト"""

    def _make_rows(self):
        return [
            {"name": "a", "type": "go", "analysis_status": "completed", "active": True},
            {"name": "b", "type": "material", "analysis_status": "failed", "active": False},
            {"name": "c", "type": "go", "analysis_status": "completed", "active": "true"},
            {"name": "d", "type": "go", "analysis_status": "unknown", "active": "false"},
        ]

    def test_no_filter(self):
        from services.graph.query import apply_filters

        rows = self._make_rows()
        result = apply_filters(rows)
        assert len(result) == 4

    def test_type_filter(self):
        from services.graph.query import apply_filters

        rows = self._make_rows()
        result = apply_filters(rows, type_filter="go")
        assert len(result) == 3
        assert all(r["type"] == "go" for r in result)

    def test_status_filter(self):
        from services.graph.query import apply_filters

        rows = self._make_rows()
        result = apply_filters(rows, status_filter="completed")
        assert len(result) == 2

    def test_active_only(self):
        from services.graph.query import apply_filters

        rows = self._make_rows()
        result = apply_filters(rows, active_only=True)
        assert len(result) == 2
        assert {r["name"] for r in result} == {"a", "c"}

    def test_combined(self):
        from services.graph.query import apply_filters

        rows = self._make_rows()
        result = apply_filters(rows, type_filter="go", active_only=True)
        assert len(result) == 2

    def test_subete_skip(self):
        """'すべて'フィルタは無効化される"""
        from services.graph.query import apply_filters

        rows = self._make_rows()
        result = apply_filters(rows, type_filter="すべて")
        assert len(result) == 4


class TestApplySavedViewFilters:
    """apply_saved_view_filters のテスト"""

    def _make_rows(self):
        return [
            {"name": "a", "type": "go", "active": True},
            {"name": "b", "type": "material", "active": False},
            {"name": "c", "type": "go", "active": "true"},
        ]

    def test_empty_filters(self):
        from services.graph.query import apply_saved_view_filters

        rows = self._make_rows()
        result = apply_saved_view_filters(rows, {})
        assert len(result) == 3

    def test_active_true(self):
        from services.graph.query import apply_saved_view_filters

        rows = self._make_rows()
        result = apply_saved_view_filters(rows, {"active": True})
        assert len(result) == 2

    def test_type_filter(self):
        from services.graph.query import apply_saved_view_filters

        rows = self._make_rows()
        result = apply_saved_view_filters(rows, {"type": "go"})
        assert len(result) == 2

    def test_custom_key(self):
        from services.graph.query import apply_saved_view_filters

        rows = self._make_rows()
        result = apply_saved_view_filters(rows, {"name": "a"})
        assert len(result) == 1


class TestSavedViewFiltersToProviderFilters:
    """saved_view_filters_to_provider_filters のテスト"""

    def test_passthrough(self):
        from services.graph.query import saved_view_filters_to_provider_filters

        filters = {"type": "go", "active": True}
        result = saved_view_filters_to_provider_filters(filters)
        assert result == {"type": "go", "active": True}


# ====================================================================
# props条件式フィルタテスト
# ====================================================================


class TestParsePropFilters:
    """parse_prop_filters のテスト"""

    def test_basic(self):
        from services.graph.query import parse_prop_filters

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

    def test_all_operators(self):
        from services.graph.query import parse_prop_filters

        params = {
            "props.a.eq": "1",
            "props.b.ne": "2",
            "props.c.gt": "3",
            "props.d.ge": "4",
            "props.e.lt": "5",
            "props.f.le": "6",
        }
        filters = parse_prop_filters(params)
        assert len(filters) == 6

    def test_invalid_value_skipped(self):
        from services.graph.query import parse_prop_filters

        params = {"props.RF3.gt": "abc"}
        filters = parse_prop_filters(params)
        assert len(filters) == 0

    def test_empty_params(self):
        from services.graph.query import parse_prop_filters

        filters = parse_prop_filters({})
        assert len(filters) == 0

    def test_non_matching_keys_ignored(self):
        from services.graph.query import parse_prop_filters

        params = {"type": "go", "name": "test", "limit": "10"}
        filters = parse_prop_filters(params)
        assert len(filters) == 0


class TestApplyPropFilters:
    """apply_prop_filters のテスト（汎用）"""

    def test_dict_rows(self):
        """dict行データに対するフィルタ"""
        from services.graph.query import apply_prop_filters

        rows = [
            {"name": "a", "RF3": 3.0, "temperature": 300},
            {"name": "b", "RF3": 8.0, "temperature": 350},
            {"name": "c", "RF3": 5.0, "temperature": 400},
        ]

        result = apply_prop_filters(rows, [("RF3", "gt", 5.0)])
        assert len(result) == 1
        assert result[0]["name"] == "b"

    def test_dict_rows_ge(self):
        from services.graph.query import apply_prop_filters

        rows = [
            {"name": "a", "RF3": 3.0},
            {"name": "b", "RF3": 8.0},
            {"name": "c", "RF3": 5.0},
        ]

        result = apply_prop_filters(rows, [("RF3", "ge", 5.0)])
        assert len(result) == 2
        names = {r["name"] for r in result}
        assert names == {"b", "c"}

    def test_dict_rows_combined(self):
        from services.graph.query import apply_prop_filters

        rows = [
            {"name": "a", "RF3": 3.0, "temperature": 300},
            {"name": "b", "RF3": 8.0, "temperature": 350},
            {"name": "c", "RF3": 5.0, "temperature": 400},
        ]

        result = apply_prop_filters(
            rows,
            [
                ("RF3", "gt", 4.0),
                ("temperature", "lt", 400.0),
            ],
        )
        assert len(result) == 1
        assert result[0]["name"] == "b"

    def test_node_objects(self):
        """Nodeオブジェクトに対するフィルタ（node_prop_getter使用）"""
        from services.graph.query import apply_prop_filters, node_prop_getter

        nodes = [
            Node(id=1, type="go", name="a", format="inp", properties={"RF3": 3.0, "temperature": 300}),
            Node(id=2, type="go", name="b", format="inp", properties={"RF3": 8.0, "temperature": 350}),
            Node(id=3, type="go", name="c", format="inp", properties={"RF3": 5.0, "temperature": 400}),
        ]

        result = apply_prop_filters(nodes, [("RF3", "gt", 5.0)], prop_getter=node_prop_getter)
        assert len(result) == 1
        assert result[0].name == "b"

    def test_node_objects_combined(self):
        from services.graph.query import apply_prop_filters, node_prop_getter

        nodes = [
            Node(id=1, type="go", name="a", format="inp", properties={"RF3": 3.0, "temperature": 300}),
            Node(id=2, type="go", name="b", format="inp", properties={"RF3": 8.0, "temperature": 350}),
            Node(id=3, type="go", name="c", format="inp", properties={"RF3": 5.0, "temperature": 400}),
        ]

        result = apply_prop_filters(
            nodes,
            [("RF3", "gt", 4.0), ("temperature", "lt", 400.0)],
            prop_getter=node_prop_getter,
        )
        assert len(result) == 1
        assert result[0].name == "b"

    def test_missing_property(self):
        """プロパティが存在しないアイテムは除外される"""
        from services.graph.query import apply_prop_filters

        rows = [
            {"name": "a", "RF3": 3.0},
            {"name": "b"},
        ]

        result = apply_prop_filters(rows, [("RF3", "gt", 1.0)])
        assert len(result) == 1
        assert result[0]["name"] == "a"

    def test_non_numeric_property(self):
        """数値変換できないプロパティは除外される"""
        from services.graph.query import apply_prop_filters

        rows = [
            {"name": "a", "RF3": "abc"},
            {"name": "b", "RF3": 8.0},
        ]

        result = apply_prop_filters(rows, [("RF3", "gt", 5.0)])
        assert len(result) == 1
        assert result[0]["name"] == "b"

    def test_empty_filters(self):
        """フィルタが空の場合は全件返す"""
        from services.graph.query import apply_prop_filters

        rows = [{"name": "a"}, {"name": "b"}]
        result = apply_prop_filters(rows, [])
        assert len(result) == 2

    def test_all_operators(self):
        """全オペレータのテスト"""
        from services.graph.query import apply_prop_filters

        rows = [{"val": 5.0}]

        assert len(apply_prop_filters(rows, [("val", "eq", 5.0)])) == 1
        assert len(apply_prop_filters(rows, [("val", "eq", 4.0)])) == 0
        assert len(apply_prop_filters(rows, [("val", "ne", 4.0)])) == 1
        assert len(apply_prop_filters(rows, [("val", "ne", 5.0)])) == 0
        assert len(apply_prop_filters(rows, [("val", "gt", 4.0)])) == 1
        assert len(apply_prop_filters(rows, [("val", "gt", 5.0)])) == 0
        assert len(apply_prop_filters(rows, [("val", "ge", 5.0)])) == 1
        assert len(apply_prop_filters(rows, [("val", "ge", 6.0)])) == 0
        assert len(apply_prop_filters(rows, [("val", "lt", 6.0)])) == 1
        assert len(apply_prop_filters(rows, [("val", "lt", 5.0)])) == 0
        assert len(apply_prop_filters(rows, [("val", "le", 5.0)])) == 1
        assert len(apply_prop_filters(rows, [("val", "le", 4.0)])) == 0

    def test_custom_prop_getter(self):
        """カスタムprop_getterのテスト"""
        from services.graph.query import apply_prop_filters

        items = [
            {"data": {"x": 10}},
            {"data": {"x": 3}},
        ]

        def getter(item, key):
            return item.get("data", {}).get(key)

        result = apply_prop_filters(items, [("x", "gt", 5.0)], prop_getter=getter)
        assert len(result) == 1
        assert result[0]["data"]["x"] == 10


# ====================================================================
# sort.py テスト
# ====================================================================


class TestSortRowsByIndex:
    """sort_rows_by_index のテスト"""

    def test_sort_by_idx(self):
        from services.graph.query import sort_rows_by_index

        rows = [{"idx": "3"}, {"idx": "1"}, {"idx": "2"}]
        result = sort_rows_by_index(rows, "idx", "ver")
        assert [r["idx"] for r in result] == ["1", "2", "3"]

    def test_sort_by_idx_and_ver(self):
        from services.graph.query import sort_rows_by_index

        rows = [
            {"idx": "2", "ver": "1"},
            {"idx": "1", "ver": "2"},
            {"idx": "1", "ver": "1"},
        ]
        result = sort_rows_by_index(rows, "idx", "ver")
        assert [(r["idx"], r["ver"]) for r in result] == [
            ("1", "1"),
            ("1", "2"),
            ("2", "1"),
        ]

    def test_no_sortable_values(self):
        from services.graph.query import sort_rows_by_index

        rows = [{"name": "c"}, {"name": "a"}, {"name": "b"}]
        result = sort_rows_by_index(rows, "idx", "ver")
        assert result is rows  # 元のリストがそのまま返る

    def test_empty_list(self):
        from services.graph.query import sort_rows_by_index

        result = sort_rows_by_index([], "idx", "ver")
        assert result == []

    def test_bool_values_ignored(self):
        from services.graph.query import sort_rows_by_index

        rows = [{"idx": True, "ver": "1"}, {"idx": "2", "ver": "1"}]
        result = sort_rows_by_index(rows, "idx", "ver")
        # bool値はint変換対象外だが、2行目がsortable → ソートは実行される
        assert len(result) == 2

    def test_mixed_sortable(self):
        from services.graph.query import sort_rows_by_index

        rows = [{"idx": "3"}, {"idx": "abc"}, {"idx": "1"}]
        result = sort_rows_by_index(rows, "idx", "ver")
        # "abc"はint変換不可→sentinelで末尾
        assert result[0]["idx"] == "1"
        assert result[1]["idx"] == "3"
        assert result[2]["idx"] == "abc"


class TestSortColumnsByVocab:
    """sort_columns_by_vocab のテスト"""

    def test_vocab_order(self):
        from services.graph.query import sort_columns_by_vocab

        vocab = {"a_key": "A表示", "b_key": "B表示", "c_key": "C表示"}
        columns = ["c_key", "a_key", "z_col", "b_key"]
        result = sort_columns_by_vocab(columns, vocab)
        assert result[:3] == ["a_key", "b_key", "c_key"]
        assert result[3] == "z_col"

    def test_empty_columns(self):
        from services.graph.query import sort_columns_by_vocab

        result = sort_columns_by_vocab([], {"a": "A"})
        assert result == []

    def test_no_vocab(self):
        from services.graph.query import sort_columns_by_vocab

        result = sort_columns_by_vocab(["c", "a", "b"], {})
        assert result == ["a", "b", "c"]

    def test_prefixed_key_sorted_after_base(self):
        """接頭辞エスケープキーがベースキーの直後にソートされる"""
        from services.graph.query import sort_columns_by_vocab

        vocab = {"mesh_node_count": "ノード数", "mesh_element_count": "要素数"}
        columns = ["mesh_t50:mesh_node_count", "mesh_node_count", "mesh_element_count", "z_col"]
        result = sort_columns_by_vocab(columns, vocab)
        # ノード数 → mesh_t50:ノード数 → 要素数 → z_col
        assert result.index("mesh_node_count") < result.index("mesh_t50:mesh_node_count")
        assert result.index("mesh_t50:mesh_node_count") < result.index("mesh_element_count")
        assert result.index("mesh_element_count") < result.index("z_col")

    def test_multiple_prefixed_keys_grouped(self):
        """同じベースキーの接頭辞キーが近接してソートされる"""
        from services.graph.query import sort_columns_by_vocab

        vocab = {"mesh_node_count": "ノード数"}
        columns = ["mesh_t50:mesh_node_count", "mesh_t30:mesh_node_count", "mesh_node_count", "z_col"]
        result = sort_columns_by_vocab(columns, vocab)
        # mesh_node_count → (t30, t50の順で接頭辞付き) → z_col
        nc_idx = result.index("mesh_node_count")
        t30_idx = result.index("mesh_t30:mesh_node_count")
        t50_idx = result.index("mesh_t50:mesh_node_count")
        z_idx = result.index("z_col")
        assert nc_idx < t30_idx < t50_idx < z_idx


class TestSelectTableColumns:
    """select_table_columns のテスト"""

    def test_none_table_columns(self):
        from services.graph.query import select_table_columns

        all_cols = ["name", "type", "format", "RF3", "temperature"]
        result = select_table_columns(all_cols, None)
        assert result[0] == "name"
        assert result[1] == "type"
        assert result[2] == "format"

    def test_pattern_match(self):
        from services.graph.query import select_table_columns

        all_cols = ["name", "type", "format", "RF1", "RF2", "RF3", "temperature"]
        result = select_table_columns(all_cols, ["RF*"])
        assert "RF1" in result
        assert "RF2" in result
        assert "RF3" in result
        assert "temperature" not in result

    def test_glob_pattern(self):
        from services.graph.query import select_table_columns

        all_cols = ["name", "type", "format", "a_prop", "b_prop", "c_other"]
        result = select_table_columns(all_cols, ["*_prop"])
        assert "a_prop" in result
        assert "b_prop" in result
        assert "c_other" not in result

    def test_no_match(self):
        from services.graph.query import select_table_columns

        all_cols = ["name", "type", "format", "RF3"]
        result = select_table_columns(all_cols, ["nonexistent"])
        assert result == ["name", "type", "format"]

    def test_with_vocab(self):
        from services.graph.query import select_table_columns

        all_cols = ["name", "type", "format", "c_col", "a_col", "b_col"]
        vocab = {"a_col": "A列", "b_col": "B列"}
        result = select_table_columns(all_cols, None, vocab=vocab)
        assert result[0] == "name"

    def test_prefixed_key_matches_base_pattern(self):
        """接頭辞キーがベースキーのglobパターンにマッチする"""
        from services.graph.query import select_table_columns

        all_cols = ["name", "type", "format", "mesh_node_count", "mesh_t50:mesh_node_count", "other"]
        result = select_table_columns(all_cols, ["mesh_*"])
        assert "mesh_node_count" in result
        assert "mesh_t50:mesh_node_count" in result
        assert "other" not in result

    def test_prefixed_key_exact_match(self):
        """接頭辞キーがベースキーの完全一致でマッチする"""
        from services.graph.query import select_table_columns

        all_cols = ["name", "type", "format", "mesh_t50:mesh_node_count"]
        result = select_table_columns(all_cols, ["mesh_node_count"])
        assert "mesh_t50:mesh_node_count" in result


class TestGetFileBaseName:
    """get_file_base_name のテスト"""

    def test_version_suffix(self):
        from services.graph.query.sort import get_file_base_name

        assert get_file_base_name("mesh_v2") == "mesh"
        assert get_file_base_name("mesh_v3") == "mesh"
        assert get_file_base_name("mesh_v10") == "mesh"

    def test_index_suffix(self):
        from services.graph.query.sort import get_file_base_name

        assert get_file_base_name("mesh_idx1") == "mesh"
        assert get_file_base_name("mesh_idx2") == "mesh"
        assert get_file_base_name("mesh_idx100") == "mesh"

    def test_non_version_suffix_unchanged(self):
        from services.graph.query.sort import get_file_base_name

        assert get_file_base_name("mesh_fine") == "mesh_fine"
        assert get_file_base_name("mesh_coarse") == "mesh_coarse"
        assert get_file_base_name("material_steel") == "material_steel"

    def test_no_suffix(self):
        from services.graph.query.sort import get_file_base_name

        assert get_file_base_name("mesh") == "mesh"
        assert get_file_base_name("go") == "go"

    def test_multiple_parts_only_last_removed(self):
        from services.graph.query.sort import get_file_base_name

        assert get_file_base_name("step_v10_idx3") == "step_v10"
        assert get_file_base_name("mesh_fine_v2") == "mesh_fine"

    def test_middle_version_not_removed(self):
        from services.graph.query.sort import get_file_base_name

        # _v2 が末尾でない場合は除去しない
        assert get_file_base_name("mesh_v2_fine") == "mesh_v2_fine"

    def test_empty_string(self):
        from services.graph.query.sort import get_file_base_name

        assert get_file_base_name("") == ""


class TestGetBaseKey:
    """get_base_key のテスト"""

    def test_plain_key(self):
        from services.graph.query.sort import get_base_key

        assert get_base_key("mesh_node_count") == "mesh_node_count"

    def test_prefixed_key(self):
        from services.graph.query.sort import get_base_key

        assert get_base_key("mesh_t50:mesh_node_count") == "mesh_node_count"

    def test_multiple_colons(self):
        from services.graph.query.sort import get_base_key

        assert get_base_key("a:b:c") == "b:c"

    def test_empty_prefix(self):
        from services.graph.query.sort import get_base_key

        assert get_base_key(":key") == "key"


# ====================================================================
# QueryService テスト
# ====================================================================


def _import_query_service():
    """QueryServiceをインポート

    services.service.__init__.pyが重い依存（chardet/numpy等）を
    持つため、インポート失敗時はテストをスキップする。
    """
    try:
        from services.service.query_service import QueryService

        return QueryService
    except ImportError as e:
        pytest.skip(f"QueryService import failed: {e}")


class TestQueryService:
    """QueryService の統合テスト"""

    def _make_nodes(self):
        return [
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"RF3": 3.0, "active": True}),
            Node(id=2, type="go", name="go_idx2", format="inp", properties={"RF3": 8.0, "active": False}),
            Node(id=3, type="material", name="Steel", format="inp", properties={"RF3": 5.0, "active": True}),
            Node(id=4, type="go", name="go_idx3", format="inp", properties={"RF3": 10.0, "active": True}),
        ]

    def test_no_filter(self):
        QueryService = _import_query_service()

        nodes = self._make_nodes()
        result = QueryService.filter_nodes(nodes)
        assert len(result) == 4

    def test_type_filter(self):
        QueryService = _import_query_service()

        nodes = self._make_nodes()
        result = QueryService.filter_nodes(nodes, type_filter="go")
        assert len(result) == 3

    def test_active_filter(self):
        QueryService = _import_query_service()

        nodes = self._make_nodes()
        result = QueryService.filter_nodes(nodes, active_filter=True)
        assert len(result) == 3

    def test_name_filter(self):
        QueryService = _import_query_service()

        nodes = self._make_nodes()
        result = QueryService.filter_nodes(nodes, name_filter="idx1")
        assert len(result) == 1
        assert result[0].name == "go_idx1"

    def test_name_filter_case_insensitive(self):
        QueryService = _import_query_service()

        nodes = self._make_nodes()
        result = QueryService.filter_nodes(nodes, name_filter="STEEL")
        assert len(result) == 1
        assert result[0].name == "Steel"

    def test_props_filter(self):
        QueryService = _import_query_service()

        nodes = self._make_nodes()
        result = QueryService.filter_nodes(nodes, query_params={"props.RF3.gt": "5"})
        assert len(result) == 2
        names = {n.name for n in result}
        assert names == {"go_idx2", "go_idx3"}

    def test_combined_filters(self):
        QueryService = _import_query_service()

        nodes = self._make_nodes()
        result = QueryService.filter_nodes(
            nodes,
            type_filter="go",
            query_params={"props.RF3.gt": "5"},
        )
        assert len(result) == 2
        names = {n.name for n in result}
        assert names == {"go_idx2", "go_idx3"}

    def test_parse_prop_filters_static(self):
        QueryService = _import_query_service()

        filters = QueryService.parse_prop_filters({"props.RF3.gt": "5"})
        assert len(filters) == 1
        assert filters[0] == ("RF3", "gt", 5.0)

    def test_apply_prop_filters_to_nodes_static(self):
        QueryService = _import_query_service()

        nodes = self._make_nodes()
        filters = [("RF3", "gt", 5.0)]
        result = QueryService.apply_prop_filters_to_nodes(nodes, filters)
        assert len(result) == 2


# ====================================================================
# 後方互換テスト
# ====================================================================


class TestBackwardCompatibility:
    """services/dashboard/query.py からの再エクスポート互換テスト"""

    def test_is_truthy(self):
        from services.graph.query import is_truthy

        assert is_truthy(True) is True
        assert is_truthy("false") is False

    def test_apply_filters(self):
        from services.graph.query import apply_filters

        rows = [{"type": "go"}, {"type": "material"}]
        result = apply_filters(rows, type_filter="go")
        assert len(result) == 1

    def test_sort_columns_by_vocab(self):
        from services.graph.query import sort_columns_by_vocab

        result = sort_columns_by_vocab(["b", "a"], {})
        assert result == ["a", "b"]

    def test_select_table_columns(self):
        from services.graph.query import select_table_columns

        result = select_table_columns(["name", "type", "format", "x"], None)
        assert "name" in result

    def test_apply_saved_view_filters(self):
        from services.graph.query import apply_saved_view_filters

        rows = [{"type": "go"}, {"type": "material"}]
        result = apply_saved_view_filters(rows, {"type": "go"})
        assert len(result) == 1

    def test_saved_view_filters_to_provider_filters(self):
        from services.graph.query import saved_view_filters_to_provider_filters

        result = saved_view_filters_to_provider_filters({"type": "go"})
        assert result == {"type": "go"}


# ====================================================================
# transform.py テスト
# ====================================================================


class TestSummarizeListValue:
    """summarize_list_value のテスト"""

    def test_none_returns_none(self):
        from services.graph.query.transform import summarize_list_value

        assert summarize_list_value(None) is None

    def test_nan_returns_none(self):
        from services.graph.query.transform import summarize_list_value

        assert summarize_list_value(float("nan")) is None

    def test_empty_list_returns_none(self):
        from services.graph.query.transform import summarize_list_value

        assert summarize_list_value([]) is None

    def test_list_returns_first_element(self):
        from services.graph.query.transform import summarize_list_value

        assert summarize_list_value(["error1", "error2"]) == "error1"

    def test_single_element_list(self):
        from services.graph.query.transform import summarize_list_value

        assert summarize_list_value(["only"]) == "only"

    def test_dict_returns_as_is(self):
        from services.graph.query.transform import summarize_list_value

        d = {"key": "value"}
        assert summarize_list_value(d) == d

    def test_string_list_format(self):
        from services.graph.query.transform import summarize_list_value

        assert summarize_list_value("['error1','error2']") == "error1"

    def test_string_empty_list_format(self):
        from services.graph.query.transform import summarize_list_value

        result = summarize_list_value("[]")
        assert result is None

    def test_plain_string(self):
        from services.graph.query.transform import summarize_list_value

        assert summarize_list_value("hello") == "ell"  # [1:-1] → "ell", split(",")[0] → "ell"

    def test_integer_returns_as_is(self):
        from services.graph.query.transform import summarize_list_value

        assert summarize_list_value(42) == 42


class TestSummarizeListColumns:
    """summarize_list_columns のテスト"""

    def test_basic_columns(self):
        pd = pytest.importorskip("pandas")
        from services.graph.query.transform import summarize_list_columns

        df = pd.DataFrame(
            {
                "name": ["a", "b"],
                "msg_errors": [["err1", "err2"], []],
                "dat_errors": [["dat_err"], None],
            }
        )
        result = summarize_list_columns(df, ["msg_errors", "dat_errors"])
        assert result["msg_errors"].iloc[0] == "err1"
        assert pd.isna(result["msg_errors"].iloc[1])
        assert result["dat_errors"].iloc[0] == "dat_err"
        assert pd.isna(result["dat_errors"].iloc[1])

    def test_nonexistent_column_ignored(self):
        pd = pytest.importorskip("pandas")
        from services.graph.query.transform import summarize_list_columns

        df = pd.DataFrame({"name": ["a"]})
        result = summarize_list_columns(df, ["nonexistent"])
        assert list(result.columns) == ["name"]

    def test_original_df_unchanged(self):
        pd = pytest.importorskip("pandas")
        from services.graph.query.transform import summarize_list_columns

        df = pd.DataFrame({"msg_errors": [["err1", "err2"]]})
        summarize_list_columns(df, ["msg_errors"])
        assert df["msg_errors"].tolist() == [["err1", "err2"]]

    def test_empty_columns_list(self):
        pd = pytest.importorskip("pandas")
        from services.graph.query.transform import summarize_list_columns

        df = pd.DataFrame({"msg_errors": [["err1"]]})
        result = summarize_list_columns(df, [])
        assert result["msg_errors"].tolist() == [["err1"]]
