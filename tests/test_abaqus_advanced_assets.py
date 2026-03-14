"""Abaqusアドバンストテストアセットによるパーサー検証

合成テストアセット（shared/tests/test_asset_abaqus_advanced/）を使用して、
既存パーサーのカバレッジギャップを検証する。

テスト対象:
- HYPERELASTIC, ORTHOTROPIC, KINEMATIC硬化, VISCOELASTIC材料タイプ
- SHELL SECTION, BEAM SECTION
- FREQUENCY, BUCKLE, COUPLED TEMPERATURE-DISPLACEMENT ステップ
- CLOAD, DLOAD, PRESSURE, FILM 荷重
- General Contact
- 3段INCLUDEネスト
- ケース違い材料名
- 負の固有値警告、失敗staファイル、複数ステップdat

[READMEへ戻る](../README.md)
"""

from __future__ import annotations

from pathlib import Path

import pytest

# テストアセットのルート
ADVANCED_ASSET_DIR = Path(__file__).resolve().parents[1] / "shared" / "tests" / "test_asset_abaqus_advanced"


# ====================================================================
# parse_material_blocks テスト
# ====================================================================


class TestParseMaterialBlocksAdvanced:
    """parse_material_blocks: アドバンスト材料タイプの解析"""

    def test_hyperelastic_neo_hooke(self):
        """HYPERELASTIC, NEO HOOKE が正しく解析される"""
        from services.parse.connectors.abaqus.inp_parser import parse_material_blocks

        materials = parse_material_blocks(ADVANCED_ASSET_DIR / "material_advanced.inp")
        mat_by_name = {m["name"]: m for m in materials}

        assert "rubber_neohooke" in mat_by_name
        mat = mat_by_name["rubber_neohooke"]
        assert "hyperelastic" in mat["keywords"]
        # NEO HOOKEの係数（C10, D1）
        assert "hyperelastic" in mat["properties"]
        assert len(mat["properties"]["hyperelastic"]) >= 1

    def test_hyperelastic_mooney_rivlin(self):
        """HYPERELASTIC, MOONEY-RIVLIN が正しく解析される"""
        from services.parse.connectors.abaqus.inp_parser import parse_material_blocks

        materials = parse_material_blocks(ADVANCED_ASSET_DIR / "material_advanced.inp")
        mat_by_name = {m["name"]: m for m in materials}

        assert "rubber_mooney" in mat_by_name
        mat = mat_by_name["rubber_mooney"]
        assert "hyperelastic" in mat["keywords"]
        assert "hyperelastic" in mat["properties"]

    def test_orthotropic_elastic(self):
        """ELASTIC, TYPE=ORTHOTROPIC が正しく解析される"""
        from services.parse.connectors.abaqus.inp_parser import parse_material_blocks

        materials = parse_material_blocks(ADVANCED_ASSET_DIR / "material_advanced.inp")
        mat_by_name = {m["name"]: m for m in materials}

        assert "composite_ortho" in mat_by_name
        mat = mat_by_name["composite_ortho"]
        assert "elastic" in mat["keywords"]
        # ORTHOTROPIC: 9つの弾性定数（2行に分かれる）
        assert "elastic" in mat["properties"]

    def test_kinematic_hardening(self):
        """PLASTIC, HARDENING=KINEMATIC が正しく解析される"""
        from services.parse.connectors.abaqus.inp_parser import parse_material_blocks

        materials = parse_material_blocks(ADVANCED_ASSET_DIR / "material_advanced.inp")
        mat_by_name = {m["name"]: m for m in materials}

        assert "steel_kinematic" in mat_by_name
        mat = mat_by_name["steel_kinematic"]
        assert "plastic" in mat["keywords"]
        assert "plastic" in mat["properties"]
        # 4つの応力-ひずみデータポイント
        assert len(mat["properties"]["plastic"]) == 4

    def test_viscoelastic_prony(self):
        """VISCOELASTIC, TIME=PRONY が正しく解析される"""
        from services.parse.connectors.abaqus.inp_parser import parse_material_blocks

        materials = parse_material_blocks(ADVANCED_ASSET_DIR / "material_advanced.inp")
        mat_by_name = {m["name"]: m for m in materials}

        assert "polymer_visco" in mat_by_name
        mat = mat_by_name["polymer_visco"]
        assert "viscoelastic" in mat["keywords"]
        assert "viscoelastic" in mat["properties"]
        # 2つのProny系列項
        assert len(mat["properties"]["viscoelastic"]) == 2

    def test_case_sensitive_materials(self):
        """Steel と STEEL が別材料として認識される"""
        from services.parse.connectors.abaqus.inp_parser import parse_material_blocks

        materials = parse_material_blocks(ADVANCED_ASSET_DIR / "material_advanced.inp")
        mat_names = [m["name"] for m in materials]

        # 両方存在すること
        assert "Steel" in mat_names
        assert "STEEL" in mat_names

    def test_total_material_count(self):
        """material_advanced.inp の全材料が解析される（7個）"""
        from services.parse.connectors.abaqus.inp_parser import parse_material_blocks

        materials = parse_material_blocks(ADVANCED_ASSET_DIR / "material_advanced.inp")
        assert len(materials) == 7


# ====================================================================
# parse_keyword_blocks テスト
# ====================================================================


class TestParseKeywordBlocksAdvanced:
    """parse_keyword_blocks: アドバンストキーワードの解析"""

    def test_shell_section_keyword(self):
        """SHELL SECTIONキーワードが検出される"""
        from services.parse.connectors.abaqus.inp_parser import parse_keyword_blocks

        keywords = parse_keyword_blocks(ADVANCED_ASSET_DIR / "go_idx1.v1.inp")
        kw_names = [kw["keyword"].upper() for kw in keywords]
        assert "SHELL SECTION" in kw_names

    def test_frequency_step_keyword(self):
        """FREQUENCYキーワードが検出される"""
        from services.parse.connectors.abaqus.inp_parser import parse_keyword_blocks

        keywords = parse_keyword_blocks(ADVANCED_ASSET_DIR / "go_idx1.v1.inp")
        kw_names = [kw["keyword"].upper() for kw in keywords]
        assert "FREQUENCY" in kw_names

    def test_cload_keyword(self):
        """CLOADキーワードが検出される"""
        from services.parse.connectors.abaqus.inp_parser import parse_keyword_blocks

        keywords = parse_keyword_blocks(ADVANCED_ASSET_DIR / "go_idx1.v1.inp")
        kw_names = [kw["keyword"].upper() for kw in keywords]
        assert "CLOAD" in kw_names

    def test_dload_keyword(self):
        """DLOADキーワードが検出される"""
        from services.parse.connectors.abaqus.inp_parser import parse_keyword_blocks

        keywords = parse_keyword_blocks(ADVANCED_ASSET_DIR / "go_idx1.v1.inp")
        kw_names = [kw["keyword"].upper() for kw in keywords]
        assert "DLOAD" in kw_names

    def test_general_contact_keyword(self):
        """CONTACT（General Contact）キーワードが検出される"""
        from services.parse.connectors.abaqus.inp_parser import parse_keyword_blocks

        keywords = parse_keyword_blocks(ADVANCED_ASSET_DIR / "go_idx2.v1.inp")
        kw_names = [kw["keyword"].upper() for kw in keywords]
        assert "CONTACT" in kw_names

    def test_coupled_temp_displacement_keyword(self):
        """COUPLED TEMPERATURE-DISPLACEMENTキーワードが検出される"""
        from services.parse.connectors.abaqus.inp_parser import parse_keyword_blocks

        keywords = parse_keyword_blocks(ADVANCED_ASSET_DIR / "go_idx2.v1.inp")
        kw_names = [kw["keyword"].upper() for kw in keywords]
        assert "COUPLED TEMPERATURE-DISPLACEMENT" in kw_names

    def test_pressure_keyword(self):
        """PRESSUREキーワードが検出される"""
        from services.parse.connectors.abaqus.inp_parser import parse_keyword_blocks

        keywords = parse_keyword_blocks(ADVANCED_ASSET_DIR / "go_idx2.v1.inp")
        kw_names = [kw["keyword"].upper() for kw in keywords]
        assert "PRESSURE" in kw_names

    def test_buckle_keyword(self):
        """BUCKLEキーワードが検出される"""
        from services.parse.connectors.abaqus.inp_parser import parse_keyword_blocks

        keywords = parse_keyword_blocks(ADVANCED_ASSET_DIR / "go_idx3.v1.inp")
        kw_names = [kw["keyword"].upper() for kw in keywords]
        assert "BUCKLE" in kw_names

    def test_beam_section_keyword(self):
        """BEAM SECTIONキーワードが検出される"""
        from services.parse.connectors.abaqus.inp_parser import parse_keyword_blocks

        keywords = parse_keyword_blocks(ADVANCED_ASSET_DIR / "go_idx3.v1.inp")
        kw_names = [kw["keyword"].upper() for kw in keywords]
        assert "BEAM SECTION" in kw_names


# ====================================================================
# extract_material_elset_mapping テスト
# ====================================================================


class TestExtractMaterialElsetMappingAdvanced:
    """extract_material_elset_mapping: セクション種別の解析"""

    def test_shell_section_mapping(self):
        """SHELL SECTIONからの材料-elsetマッピング抽出"""
        from services.parse.connectors.abaqus.mesh import extract_material_elset_mapping

        mapping = extract_material_elset_mapping(ADVANCED_ASSET_DIR / "go_idx1.v1.inp")

        # パラメータ参照 <material> が解決されないため、材料名は解決後の名前
        # もしくはパラメータ参照のまま
        # SHELL SECTION で rubber_neohooke が設定されている
        all_elsets = []
        for elsets in mapping.values():
            all_elsets.extend(elsets)
        assert "shell_part" in all_elsets

    def test_solid_section_mapping(self):
        """SOLID SECTIONからの材料-elsetマッピング抽出"""
        from services.parse.connectors.abaqus.mesh import extract_material_elset_mapping

        mapping = extract_material_elset_mapping(ADVANCED_ASSET_DIR / "go_idx1.v1.inp")
        all_elsets = []
        for elsets in mapping.values():
            all_elsets.extend(elsets)
        assert "solid_part" in all_elsets

    def test_multiple_section_types(self):
        """SOLID + SHELL SECTION が両方抽出される"""
        from services.parse.connectors.abaqus.mesh import extract_material_elset_mapping

        mapping = extract_material_elset_mapping(ADVANCED_ASSET_DIR / "go_idx1.v1.inp")
        all_elsets = []
        for elsets in mapping.values():
            all_elsets.extend(elsets)
        # shell_part と solid_part の両方が含まれる
        assert len(all_elsets) >= 2

    def test_beam_section_mapped(self):
        """BEAM SECTIONからの材料-elsetマッピング抽出"""
        from services.parse.connectors.abaqus.mesh import extract_material_elset_mapping

        mapping = extract_material_elset_mapping(ADVANCED_ASSET_DIR / "go_idx3.v1.inp")
        all_elsets = []
        for elsets in mapping.values():
            all_elsets.extend(elsets)
        assert "beam_set" in all_elsets
        assert "steel_beam" in mapping


# ====================================================================
# 結果ファイルパーサーテスト
# ====================================================================


class TestResultParserAdvanced:
    """結果ファイルパーサー: エッジケースの検証"""

    def test_sta_completed_with_cutback(self):
        """成功staファイルでカットバック検出"""
        from services.parse.connectors.abaqus.result_parser import parse_sta_file

        result = parse_sta_file(ADVANCED_ASSET_DIR / "go_idx1.v1.sta")
        assert result["analysis_status"] == "completed"
        assert result["cutback_count"] == 1  # 1U が1回
        assert result["step_count"] == 2  # 2ステップ

    def test_sta_multi_step_increments(self):
        """複数ステップの収束情報"""
        from services.parse.connectors.abaqus.result_parser import parse_sta_file

        result = parse_sta_file(ADVANCED_ASSET_DIR / "go_idx1.v1.sta")
        assert result["increment_count"] == 12  # 全インクリメント数
        assert result["total_iterations"] > 0

    def test_sta_failed_analysis(self):
        """失敗staファイルの解析"""
        from services.parse.connectors.abaqus.result_parser import parse_sta_file

        result = parse_sta_file(ADVANCED_ASSET_DIR / "results" / "go_idx2.v1.sta")
        assert result["analysis_status"] == "failed"
        assert result["cutback_count"] == 2  # 2U が2回
        assert len(result["errors"]) >= 1

    def test_msg_negative_eigenvalue_warnings(self):
        """負の固有値警告の解析（重複排除含む）"""
        from services.parse.connectors.abaqus.result_parser import parse_msg_file

        result = parse_msg_file(ADVANCED_ASSET_DIR / "go_idx1.v1.msg")
        assert len(result["warnings"]) >= 1
        # 数値のみ異なる固有値警告は重複排除される
        eigenvalue_warnings = [w for w in result["warnings"] if "NEGATIVE EIGENVALUES" in w]
        assert len(eigenvalue_warnings) == 1  # 重複排除で1件

    def test_msg_excessive_distortion_warning(self):
        """過大変形警告の検出"""
        from services.parse.connectors.abaqus.result_parser import parse_msg_file

        result = parse_msg_file(ADVANCED_ASSET_DIR / "go_idx1.v1.msg")
        distortion_warnings = [w for w in result["warnings"] if "DISTORTION" in w.upper()]
        assert len(distortion_warnings) >= 1

    def test_msg_multiple_errors(self):
        """複数エラーの検出"""
        from services.parse.connectors.abaqus.result_parser import parse_msg_file

        result = parse_msg_file(ADVANCED_ASSET_DIR / "results" / "go_idx2.v1.msg")
        assert len(result["errors"]) >= 2

    def test_msg_dedup_eigenvalue_warnings(self):
        """固有値警告の数値のみ異なるものが重複排除される"""
        from services.parse.connectors.abaqus.result_parser import parse_msg_file

        result = parse_msg_file(ADVANCED_ASSET_DIR / "results" / "go_idx2.v1.msg")
        eigenvalue_warnings = [w for w in result["warnings"] if "NEGATIVE EIGENVALUES" in w]
        # 45個と12個の固有値警告は数値のみ異なるため1件に
        assert len(eigenvalue_warnings) == 1

    def test_dat_multi_step_timing(self):
        """複数ステップのCPU時間（最終サマリーが採用される）"""
        from services.parse.connectors.abaqus.result_parser import parse_dat_file

        result = parse_dat_file(ADVANCED_ASSET_DIR / "go_idx1.v1.dat")
        # 最後のTOTAL CPU TIMEが採用される（ステップ2の67.8）
        assert result["cpu_time"] == pytest.approx(67.8)
        assert result["wallclock_time"] == pytest.approx(35.0)

    def test_dat_failed_with_warning(self):
        """失敗datファイルの警告抽出"""
        from services.parse.connectors.abaqus.result_parser import parse_dat_file

        result = parse_dat_file(ADVANCED_ASSET_DIR / "results" / "go_idx2.v1.dat")
        assert result["cpu_time"] == pytest.approx(12.3)
        assert len(result.get("warnings", [])) >= 1


# ====================================================================
# parse_material_blocks via include テスト
# ====================================================================


class TestMaterialParsingViaInclude:
    """INCLUDEされたmaterialの解析検証"""

    def test_go_idx1_includes_material_advanced(self):
        """go_idx1.v1.inp が material_advanced.inp をINCLUDEしている"""
        from services.parse.connectors.abaqus.inp_parser import parse_material_blocks

        # go_idx1.v1.inp はincludeで material_advanced.inp を参照
        # ただし parse_material_blocks はincludeを辿らない（単体ファイル解析）
        # materialファイル自体を直接パースできることを確認
        materials = parse_material_blocks(ADVANCED_ASSET_DIR / "material_advanced.inp")
        assert len(materials) == 7

    def test_go_idx3_inline_material(self):
        """go_idx3.v1.inp のインライン材料定義"""
        from services.parse.connectors.abaqus.inp_parser import parse_material_blocks

        materials = parse_material_blocks(ADVANCED_ASSET_DIR / "go_idx3.v1.inp")
        assert len(materials) == 1
        assert materials[0]["name"] == "steel_beam"
        assert "elastic" in materials[0]["keywords"]


# ====================================================================
# 3段ネストINCLUDE テスト
# ====================================================================


class TestNestedInclude:
    """3段ネストINCLUDEの解析検証"""

    def test_nested_main_has_include(self):
        """main.inp が sub/assembly.inp をINCLUDE"""
        from services.parse.connectors.abaqus.inp_parser import parse_keyword_blocks

        keywords = parse_keyword_blocks(ADVANCED_ASSET_DIR / "nested_include" / "main.inp")
        kw_names = [kw["keyword"].upper() for kw in keywords]
        assert "INCLUDE" in kw_names

    def test_nested_sub_has_include(self):
        """sub/assembly.inp が ../material_advanced.inp をINCLUDE"""
        from services.parse.connectors.abaqus.inp_parser import parse_keyword_blocks

        keywords = parse_keyword_blocks(ADVANCED_ASSET_DIR / "nested_include" / "sub" / "assembly.inp")
        kw_names = [kw["keyword"].upper() for kw in keywords]
        assert "INCLUDE" in kw_names

    def test_nested_sub_has_solid_section(self):
        """sub/assembly.inp が SOLID SECTIONを含む"""
        from services.parse.connectors.abaqus.mesh import extract_material_elset_mapping

        mapping = extract_material_elset_mapping(ADVANCED_ASSET_DIR / "nested_include" / "sub" / "assembly.inp")
        all_materials = list(mapping.keys())
        assert "Steel" in all_materials


# ====================================================================
# アセットファイル存在確認
# ====================================================================


class TestAssetFilesExist:
    """テストアセットファイルの存在確認"""

    @pytest.mark.parametrize(
        "filename",
        [
            "material_advanced.inp",
            "go_idx1.v1.inp",
            "go_idx2.v1.inp",
            "go_idx3.v1.inp",
            "go_idx1.v1.sta",
            "go_idx1.v1.msg",
            "go_idx1.v1.dat",
            "nested_include/main.inp",
            "nested_include/sub/assembly.inp",
            "results/go_idx2.v1.sta",
            "results/go_idx2.v1.msg",
            "results/go_idx2.v1.dat",
        ],
    )
    def test_asset_file_exists(self, filename: str):
        """アセットファイルが存在する"""
        path = ADVANCED_ASSET_DIR / filename
        assert path.exists(), f"テストアセットが見つかりません: {path}"
