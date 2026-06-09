"""Abaqus *PARAMETER 式評価・include間パラメータ伝搬テスト

T1 #5: parameter_parser.py の _resolve_param_references 関数と
include関係にある親→子のパラメータ伝搬をテストする。
"""

from __future__ import annotations

import pytest


class TestResolveParamReferences:
    """_resolve_param_references 関数の単体テスト"""

    def test_simple_identifier(self):
        """単純な識別子参照が置換される"""
        from plugins.abaqus.parse.parameter_parser import _resolve_param_references

        result = _resolve_param_references("w*2", {"w": "5"})
        assert result == "5*2"

    def test_angle_bracket_reference(self):
        """<param_name>形式の参照が置換される"""
        from plugins.abaqus.parse.parameter_parser import _resolve_param_references

        result = _resolve_param_references("<w>*2", {"w": "5"})
        assert result == "5*2"

    def test_multiple_references(self):
        """複数のパラメータ参照が同時に置換される"""
        from plugins.abaqus.parse.parameter_parser import _resolve_param_references

        result = _resolve_param_references("w+t", {"w": "5", "t": "10"})
        assert result == "5+10"

    def test_case_insensitive(self):
        """大文字小文字を区別しない参照解決"""
        from plugins.abaqus.parse.parameter_parser import _resolve_param_references

        result = _resolve_param_references("W*2", {"w": "5"})
        assert result == "5*2"

    def test_case_insensitive_angle_bracket(self):
        """<PARAM>形式でも大文字小文字を区別しない"""
        from plugins.abaqus.parse.parameter_parser import _resolve_param_references

        result = _resolve_param_references("<W>*2", {"w": "5"})
        assert result == "5*2"

    def test_unresolved_reference_preserved(self):
        """未定義のパラメータ参照は元の文字列を維持"""
        from plugins.abaqus.parse.parameter_parser import _resolve_param_references

        result = _resolve_param_references("<unknown>+1", {"w": "5"})
        assert result == "<unknown>+1"

    def test_expression_with_parentheses(self):
        """括弧を含む式が正しく処理される"""
        from plugins.abaqus.parse.parameter_parser import _resolve_param_references

        result = _resolve_param_references("(w+t)*2", {"w": "3", "t": "4"})
        assert result == "(3+4)*2"

    def test_expression_with_power(self):
        """べき乗を含む式が正しく処理される"""
        from plugins.abaqus.parse.parameter_parser import _resolve_param_references

        result = _resolve_param_references("w**2", {"w": "3"})
        assert result == "3**2"

    def test_no_references(self):
        """パラメータ参照がない式はそのまま"""
        from plugins.abaqus.parse.parameter_parser import _resolve_param_references

        result = _resolve_param_references("3.14*2", {})
        assert result == "3.14*2"

    def test_mixed_angle_and_identifier(self):
        """<param>形式と識別子形式の混在"""
        from plugins.abaqus.parse.parameter_parser import _resolve_param_references

        result = _resolve_param_references("<w>+t", {"w": "5", "t": "10"})
        assert result == "5+10"

    def test_numeric_only_not_replaced(self):
        """数値のみの文字列は置換されない"""
        from plugins.abaqus.parse.parameter_parser import _resolve_param_references

        result = _resolve_param_references("100+200", {"x": "5"})
        assert result == "100+200"


class TestParameterIncludePropagation:
    """include関係における親→子のパラメータ伝搬テスト"""

    def test_parent_params_propagate_to_child(self, tmp_path):
        """親ファイルのパラメータが子ファイルの式評価に使われる"""
        from plugins.abaqus.parse.parameter_parser import AbaqusParameterParser

        # 親ファイル: w=5 を定義し、子ファイルをinclude
        parent = tmp_path / "parent.inp"
        parent.write_text("*PARAMETER\n**props\nw=5\n*INCLUDE, INPUT=child.inp\n*STEP\n")

        # 子ファイル: 親のwを使ってarea=w*10を計算
        child = tmp_path / "child.inp"
        child.write_text("*PARAMETER\n**props\narea=w*10\n*STEP\n")

        props = AbaqusParameterParser._read_parameter_props(parent)
        assert props["w"] == "5"
        assert props["area"] == "50"

    def test_child_params_visible_in_parent_after_include(self, tmp_path):
        """子ファイルのパラメータがinclude後に親のコンテキストにマージされる"""
        from plugins.abaqus.parse.parameter_parser import AbaqusParameterParser

        parent = tmp_path / "parent.inp"
        parent.write_text("*INCLUDE, INPUT=child.inp\n*PARAMETER\n**props\ntotal=child_val*2\n*STEP\n")

        child = tmp_path / "child.inp"
        child.write_text("*PARAMETER\n**props\nchild_val=7\n*STEP\n")

        props = AbaqusParameterParser._read_parameter_props(parent)
        assert props["child_val"] == "7"
        assert props["total"] == "14"

    def test_angle_bracket_reference_in_expression(self, tmp_path):
        """<param>形式の参照が式中で正しく解決される"""
        from plugins.abaqus.parse.parameter_parser import AbaqusParameterParser

        inp = tmp_path / "test.inp"
        inp.write_text("*PARAMETER\n**props\nbase=100\nresult=<base>*2\n*STEP\n")

        props = AbaqusParameterParser._read_parameter_props(inp)
        assert props["base"] == "100"
        assert props["result"] == "200"

    def test_chained_parameter_evaluation(self, tmp_path):
        """パラメータの連鎖参照が正しく評価される"""
        from plugins.abaqus.parse.parameter_parser import AbaqusParameterParser

        inp = tmp_path / "test.inp"
        inp.write_text("*PARAMETER\n**props\na=2\nb=a*3\nc=b+a\n*STEP\n")

        props = AbaqusParameterParser._read_parameter_props(inp)
        assert props["a"] == "2"
        assert props["b"] == "6"
        assert props["c"] == "8"

    def test_power_expression(self, tmp_path):
        """べき乗式が正しく評価される"""
        from plugins.abaqus.parse.parameter_parser import AbaqusParameterParser

        inp = tmp_path / "test.inp"
        inp.write_text("*PARAMETER\n**props\nx=3\ny=x**2\n*STEP\n")

        props = AbaqusParameterParser._read_parameter_props(inp)
        assert props["x"] == "3"
        assert props["y"] == "9"

    def test_circular_include_detection(self, tmp_path):
        """循環includeが検出され、無限ループしない"""
        from plugins.abaqus.parse.parameter_parser import AbaqusParameterParser

        a = tmp_path / "a.inp"
        b = tmp_path / "b.inp"
        a.write_text("*PARAMETER\n**props\nx=1\n*INCLUDE, INPUT=b.inp\n")
        b.write_text("*PARAMETER\n**props\ny=2\n*INCLUDE, INPUT=a.inp\n")

        # 無限ループせずに完了すること
        props = AbaqusParameterParser._read_parameter_props(a)
        assert props["x"] == "1"
        assert props["y"] == "2"

    def test_parenthesized_expression(self, tmp_path):
        """括弧を含む式が正しく評価される"""
        from plugins.abaqus.parse.parameter_parser import AbaqusParameterParser

        inp = tmp_path / "test.inp"
        inp.write_text("*PARAMETER\n**props\na=3\nb=4\nc=(a+b)*2\n*STEP\n")

        props = AbaqusParameterParser._read_parameter_props(inp)
        assert props["c"] == "14"

    def test_float_expression(self, tmp_path):
        """浮動小数点の式が正しく評価される"""
        from plugins.abaqus.parse.parameter_parser import AbaqusParameterParser

        inp = tmp_path / "test.inp"
        inp.write_text("*PARAMETER\n**props\nr=2.5\narea=r*r*3.14\n*STEP\n")

        props = AbaqusParameterParser._read_parameter_props(inp)
        assert props["r"] == "2.5"
        assert float(props["area"]) == pytest.approx(19.625)
