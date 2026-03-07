"""Abaqus .sta ファイル収束情報パーサーテスト

T1 #6: カットバック・インクリメント収束情報の収集をテストする。
"""

from __future__ import annotations

import pytest

# Abaqus Standard 形式のサンプル .sta ファイル内容
SAMPLE_STA_STANDARD = """\
 Abaqus/Standard                   2024                   Date                   Time

 SUMMARY OF JOB INFORMATION:
  STEP      INC     ATT  SEVERE     EQUIL     TOTAL
                         DISCON     ITERS     ITERS
                          ITERS                       TOTAL     STEP      INC OF    DOF      IF
                                                      TIME/    TIME/LPF  TIME/LPF  MONITOR  RIKS

    1        1      1       0        2         2   5.000e-02  5.000e-02  5.000e-02
    1        2      1       0        3         3   1.000e-01  1.000e-01  5.000e-02
    1        3      1U      0        5         5   1.000e-01  1.000e-01  5.000e-02
    1        3      2       0        4         4   1.500e-01  1.500e-01  2.500e-02
    1        4      1       0        2         2   2.500e-01  2.500e-01  1.000e-01
    1        5      1U      0        5         5   2.500e-01  2.500e-01  1.000e-01
    1        5      2U      0        5         5   2.500e-01  2.500e-01  5.000e-02
    1        5      3       0        3         3   3.000e-01  3.000e-01  2.500e-02
    2        1      1       0        2         2   4.000e-01  1.000e-01  1.000e-01
    2        2      1       0        2         2   5.000e-01  2.000e-01  1.000e-01

 THE ANALYSIS HAS COMPLETED SUCCESSFULLY
"""

SAMPLE_STA_NO_CUTBACK = """\
 Abaqus/Standard

 SUMMARY OF JOB INFORMATION:
  STEP      INC     ATT  SEVERE     EQUIL     TOTAL
    1        1      1       0        2         2   1.000e-01  1.000e-01  1.000e-01
    1        2      1       0        3         3   2.000e-01  2.000e-01  1.000e-01
    1        3      1       0        2         2   5.000e-01  5.000e-01  3.000e-01
    1        4      1       0        2         2   1.000e+00  1.000e+00  5.000e-01

 THE ANALYSIS HAS COMPLETED SUCCESSFULLY
"""

SAMPLE_STA_FAILED = """\
 Abaqus/Standard

 SUMMARY OF JOB INFORMATION:
  STEP      INC     ATT  SEVERE     EQUIL     TOTAL
    1        1      1       0        2         2   1.000e-01  1.000e-01  1.000e-01
    1        2      1U      0        5         5   1.000e-01  1.000e-01  1.000e-01
    1        2      2U      0        5         5   1.000e-01  1.000e-01  5.000e-02
    1        2      3U      0        5         5   1.000e-01  1.000e-01  2.500e-02

***ERROR: TOO MANY CUTBACKS

 THE ANALYSIS HAS NOT BEEN COMPLETED
"""


class TestParseConvergenceInfo:
    """_parse_convergence_info 関数の単体テスト"""

    def test_standard_with_cutbacks(self):
        from services.parse.connectors.abaqus.result_parser import _parse_convergence_info

        info = _parse_convergence_info(SAMPLE_STA_STANDARD)
        assert info["increment_count"] == 10
        assert info["cutback_count"] == 3  # 1U, 1U, 2U
        assert info["step_count"] == 2
        assert info["max_equilibrium_iters"] == 5

    def test_no_cutback(self):
        from services.parse.connectors.abaqus.result_parser import _parse_convergence_info

        info = _parse_convergence_info(SAMPLE_STA_NO_CUTBACK)
        assert info["increment_count"] == 4
        assert info["cutback_count"] == 0
        assert info["step_count"] == 1
        assert info["max_equilibrium_iters"] == 3

    def test_failed_analysis(self):
        from services.parse.connectors.abaqus.result_parser import _parse_convergence_info

        info = _parse_convergence_info(SAMPLE_STA_FAILED)
        assert info["increment_count"] == 4
        assert info["cutback_count"] == 3
        assert info["step_count"] == 1

    def test_empty_content(self):
        from services.parse.connectors.abaqus.result_parser import _parse_convergence_info

        info = _parse_convergence_info("")
        assert info == {}

    def test_total_iterations(self):
        from services.parse.connectors.abaqus.result_parser import _parse_convergence_info

        info = _parse_convergence_info(SAMPLE_STA_STANDARD)
        # 2+3+5+4+2+5+5+3+2+2 = 33
        assert info["total_iterations"] == 33


class TestParseStaFileConvergence:
    """parse_sta_file で収束情報が返却されることのテスト"""

    def test_sta_file_returns_convergence(self, tmp_path):
        from services.parse.connectors.abaqus.result_parser import parse_sta_file

        sta = tmp_path / "test.sta"
        sta.write_text(SAMPLE_STA_STANDARD)

        result = parse_sta_file(sta)
        assert result["analysis_status"] == "completed"
        assert result["increment_count"] == 10
        assert result["cutback_count"] == 3
        assert result["step_count"] == 2

    def test_sta_file_failed_with_error(self, tmp_path):
        from services.parse.connectors.abaqus.result_parser import parse_sta_file

        sta = tmp_path / "test.sta"
        sta.write_text(SAMPLE_STA_FAILED)

        result = parse_sta_file(sta)
        assert result["analysis_status"] == "failed"
        assert result["cutback_count"] == 3
        assert any("TOO MANY CUTBACKS" in e for e in result["errors"])

    def test_sta_no_convergence_data(self, tmp_path):
        from services.parse.connectors.abaqus.result_parser import parse_sta_file

        sta = tmp_path / "empty.sta"
        sta.write_text("THE ANALYSIS HAS COMPLETED SUCCESSFULLY\n")

        result = parse_sta_file(sta)
        assert result["analysis_status"] == "completed"
        assert "increment_count" not in result

    def test_nonexistent_file(self, tmp_path):
        from services.parse.connectors.abaqus.result_parser import parse_sta_file

        result = parse_sta_file(tmp_path / "nonexistent.sta")
        assert result["analysis_status"] == "unknown"
        assert "increment_count" not in result


class TestAbaqusResultParserConvergenceIntegration:
    """AbaqusResultParser経由で収束情報がノードに付与されるテスト"""

    @pytest.fixture
    def config(self):
        from config import GraphConfig

        return GraphConfig.from_dict(
            {
                "file-relations": {
                    "input-extensions": [".inp"],
                },
            }
        )

    def test_convergence_props_on_sta_node(self, tmp_path, config):
        from services.graph import GraphService
        from services.graph.project_graph import ProjectGraph
        from services.parse.connectors.abaqus.result_parser import AbaqusResultParser

        # INPファイルとSTAファイルを作成
        inp = tmp_path / "go_idx1.inp"
        inp.write_text("*HEADING\ntest\n")
        sta = tmp_path / "go_idx1.sta"
        sta.write_text(SAMPLE_STA_STANDARD)

        gs = GraphService(project_root=tmp_path, config=config)
        inp_node = gs.file_to_node(inp)
        sta_node = gs.file_to_node(sta)

        pg = ProjectGraph(nodes=[inp_node, sta_node], relations=[], project_root=tmp_path, config=config)
        AbaqusResultParser().apply(pg)

        # STAノードに収束情報が付与される
        assert sta_node.properties.get("increment_count") == 10
        assert sta_node.properties.get("cutback_count") == 3
        assert sta_node.properties.get("step_count") == 2
        assert sta_node.properties.get("analysis_status") == "completed"

        # 対応するINPノードにも収束情報が伝搬される
        assert inp_node.properties.get("increment_count") == 10
        assert inp_node.properties.get("cutback_count") == 3
        assert inp_node.properties.get("analysis_status") == "completed"
