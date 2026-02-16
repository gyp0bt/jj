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
        from services.query import is_truthy

        assert is_truthy(True) is True

    def test_bool_false(self):
        from services.query import is_truthy

        assert is_truthy(False) is False

    def test_string_true(self):
        from services.query import is_truthy

        assert is_truthy("true") is True
        assert is_truthy("True") is True
        assert is_truthy("TRUE") is True
        assert is_truthy("  true  ") is True

    def test_string_false(self):
        from services.query import is_truthy

        assert is_truthy("false") is False
        assert is_truthy("False") is False

    def test_none(self):
        from services.query import is_truthy

        assert is_truthy(None) is False

    def test_int(self):
        from services.query import is_truthy

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
        from services.query import apply_filters

        rows = self._make_rows()
        result = apply_filters(rows)
        assert len(result) == 4

    def test_type_filter(self):
        from services.query import apply_filters

        rows = self._make_rows()
        result = apply_filters(rows, type_filter="go")
        assert len(result) == 3
        assert all(r["type"] == "go" for r in result)

    def test_status_filter(self):
        from services.query import apply_filters

        rows = self._make_rows()
        result = apply_filters(rows, status_filter="completed")
        assert len(result) == 2

    def test_active_only(self):
        from services.query import apply_filters

        rows = self._make_rows()
        result = apply_filters(rows, active_only=True)
        assert len(result) == 2
        assert {r["name"] for r in result} == {"a", "c"}

    def test_combined(self):
        from services.query import apply_filters

        rows = self._make_rows()
        result = apply_filters(rows, type_filter="go", active_only=True)
        assert len(result) == 2

    def test_subete_skip(self):
        """'すべて'フィルタは無効化される"""
        from services.query import apply_filters

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
        from services.query import apply_saved_view_filters

        rows = self._make_rows()
        result = apply_saved_view_filters(rows, {})
        assert len(result) == 3

    def test_active_true(self):
        from services.query import apply_saved_view_filters

        rows = self._make_rows()
        result = apply_saved_view_filters(rows, {"active": True})
        assert len(result) == 2

    def test_type_filter(self):
        from services.query import apply_saved_view_filters

        rows = self._make_rows()
        result = apply_saved_view_filters(rows, {"type": "go"})
        assert len(result) == 2

    def test_custom_key(self):
        from services.query import apply_saved_view_filters

        rows = self._make_rows()
        result = apply_saved_view_filters(rows, {"name": "a"})
        assert len(result) == 1


class TestSavedViewFiltersToProviderFilters:
    """saved_view_filters_to_provider_filters のテスト"""

    def test_passthrough(self):
        from services.query import saved_view_filters_to_provider_filters

        filters = {"type": "go", "active": True}
        result = saved_view_filters_to_provider_filters(filters)
        assert result == {"type": "go", "active": True}


# ====================================================================
# props条件式フィルタテスト
# ====================================================================


class TestParsePropFilters:
    """parse_prop_filters のテスト"""

    def test_basic(self):
        from services.query import parse_prop_filters

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
        from services.query import parse_prop_filters

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
        from services.query import parse_prop_filters

        params = {"props.RF3.gt": "abc"}
        filters = parse_prop_filters(params)
        assert len(filters) == 0

    def test_empty_params(self):
        from services.query import parse_prop_filters

        filters = parse_prop_filters({})
        assert len(filters) == 0

    def test_non_matching_keys_ignored(self):
        from services.query import parse_prop_filters

        params = {"type": "go", "name": "test", "limit": "10"}
        filters = parse_prop_filters(params)
        assert len(filters) == 0


class TestApplyPropFilters:
    """apply_prop_filters のテスト（汎用）"""

    def test_dict_rows(self):
        """dict行データに対するフィルタ"""
        from services.query import apply_prop_filters

        rows = [
            {"name": "a", "RF3": 3.0, "temperature": 300},
            {"name": "b", "RF3": 8.0, "temperature": 350},
            {"name": "c", "RF3": 5.0, "temperature": 400},
        ]

        result = apply_prop_filters(rows, [("RF3", "gt", 5.0)])
        assert len(result) == 1
        assert result[0]["name"] == "b"

    def test_dict_rows_ge(self):
        from services.query import apply_prop_filters

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
        from services.query import apply_prop_filters

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
        from services.query import apply_prop_filters, node_prop_getter

        nodes = [
            Node(id=1, type="go", name="a", format="inp", properties={"RF3": 3.0, "temperature": 300}),
            Node(id=2, type="go", name="b", format="inp", properties={"RF3": 8.0, "temperature": 350}),
            Node(id=3, type="go", name="c", format="inp", properties={"RF3": 5.0, "temperature": 400}),
        ]

        result = apply_prop_filters(nodes, [("RF3", "gt", 5.0)], prop_getter=node_prop_getter)
        assert len(result) == 1
        assert result[0].name == "b"

    def test_node_objects_combined(self):
        from services.query import apply_prop_filters, node_prop_getter

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
        from services.query import apply_prop_filters

        rows = [
            {"name": "a", "RF3": 3.0},
            {"name": "b"},
        ]

        result = apply_prop_filters(rows, [("RF3", "gt", 1.0)])
        assert len(result) == 1
        assert result[0]["name"] == "a"

    def test_non_numeric_property(self):
        """数値変換できないプロパティは除外される"""
        from services.query import apply_prop_filters

        rows = [
            {"name": "a", "RF3": "abc"},
            {"name": "b", "RF3": 8.0},
        ]

        result = apply_prop_filters(rows, [("RF3", "gt", 5.0)])
        assert len(result) == 1
        assert result[0]["name"] == "b"

    def test_empty_filters(self):
        """フィルタが空の場合は全件返す"""
        from services.query import apply_prop_filters

        rows = [{"name": "a"}, {"name": "b"}]
        result = apply_prop_filters(rows, [])
        assert len(result) == 2

    def test_all_operators(self):
        """全オペレータのテスト"""
        from services.query import apply_prop_filters

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
        from services.query import apply_prop_filters

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


class TestSortColumnsByVocab:
    """sort_columns_by_vocab のテスト"""

    def test_vocab_order(self):
        from services.query import sort_columns_by_vocab

        vocab = {"a_key": "A表示", "b_key": "B表示", "c_key": "C表示"}
        columns = ["c_key", "a_key", "z_col", "b_key"]
        result = sort_columns_by_vocab(columns, vocab)
        assert result[:3] == ["a_key", "b_key", "c_key"]
        assert result[3] == "z_col"

    def test_empty_columns(self):
        from services.query import sort_columns_by_vocab

        result = sort_columns_by_vocab([], {"a": "A"})
        assert result == []

    def test_no_vocab(self):
        from services.query import sort_columns_by_vocab

        result = sort_columns_by_vocab(["c", "a", "b"], {})
        assert result == ["a", "b", "c"]


class TestSelectTableColumns:
    """select_table_columns のテスト"""

    def test_none_table_columns(self):
        from services.query import select_table_columns

        all_cols = ["name", "type", "format", "RF3", "temperature"]
        result = select_table_columns(all_cols, None)
        assert result[0] == "name"
        assert result[1] == "type"
        assert result[2] == "format"

    def test_pattern_match(self):
        from services.query import select_table_columns

        all_cols = ["name", "type", "format", "RF1", "RF2", "RF3", "temperature"]
        result = select_table_columns(all_cols, ["RF*"])
        assert "RF1" in result
        assert "RF2" in result
        assert "RF3" in result
        assert "temperature" not in result

    def test_glob_pattern(self):
        from services.query import select_table_columns

        all_cols = ["name", "type", "format", "a_prop", "b_prop", "c_other"]
        result = select_table_columns(all_cols, ["*_prop"])
        assert "a_prop" in result
        assert "b_prop" in result
        assert "c_other" not in result

    def test_no_match(self):
        from services.query import select_table_columns

        all_cols = ["name", "type", "format", "RF3"]
        result = select_table_columns(all_cols, ["nonexistent"])
        assert result == ["name", "type", "format"]

    def test_with_vocab(self):
        from services.query import select_table_columns

        all_cols = ["name", "type", "format", "c_col", "a_col", "b_col"]
        vocab = {"a_col": "A列", "b_col": "B列"}
        result = select_table_columns(all_cols, None, vocab=vocab)
        assert result[0] == "name"


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
        from services.dashboard.query import is_truthy

        assert is_truthy(True) is True
        assert is_truthy("false") is False

    def test_apply_filters(self):
        from services.dashboard.query import apply_filters

        rows = [{"type": "go"}, {"type": "material"}]
        result = apply_filters(rows, type_filter="go")
        assert len(result) == 1

    def test_sort_columns_by_vocab(self):
        from services.dashboard.query import sort_columns_by_vocab

        result = sort_columns_by_vocab(["b", "a"], {})
        assert result == ["a", "b"]

    def test_select_table_columns(self):
        from services.dashboard.query import select_table_columns

        result = select_table_columns(["name", "type", "format", "x"], None)
        assert "name" in result

    def test_apply_saved_view_filters(self):
        from services.dashboard.query import apply_saved_view_filters

        rows = [{"type": "go"}, {"type": "material"}]
        result = apply_saved_view_filters(rows, {"type": "go"})
        assert len(result) == 1

    def test_saved_view_filters_to_provider_filters(self):
        from services.dashboard.query import saved_view_filters_to_provider_filters

        result = saved_view_filters_to_provider_filters({"type": "go"})
        assert result == {"type": "go"}
