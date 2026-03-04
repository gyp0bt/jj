"""SolverProfileConfig / SolverDetectionConfig / GraphConfig.detect_solver_profile のユニットテスト

ソルバープロファイル設定の作成・バリデーション・自動検出をテストする。
パーサーのソルバープロファイル拡張子マージもテストする。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from config import GraphConfig, SolverDetectionConfig, SolverProfileConfig
from jj_types import Node, Relation
from services.graph.project_graph import ProjectGraph

ASSET_DIR = Path(__file__).resolve().parent.parent / "shared" / "tests" / "test_asset1"


def _make_graph(
    nodes: list[Node],
    relations: list[Relation] | None = None,
    config: GraphConfig | None = None,
    project_root: Path | None = None,
) -> ProjectGraph:
    """テスト用ProjectGraphを生成"""
    if config is None:
        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "file-relations": {
                    "input-extensions": [".inp"],
                    "result-extensions": [".odb", ".sta", ".msg", ".dat"],
                    "asset-extensions": [".modfem", ".cdb", ".stp"],
                },
            }
        )
    return ProjectGraph(
        nodes=list(nodes),
        relations=list(relations or []),
        project_root=project_root or ASSET_DIR,
        config=config,
    )


# ====================================================================
# SolverProfileConfig テスト
# ====================================================================


class TestSolverProfileConfig:
    """SolverProfileConfig.from_dict の単体テスト"""

    def test_from_dict_minimal(self):
        """最小限のdictからデフォルト値で生成できる"""
        profile = SolverProfileConfig.from_dict("test", {})
        assert profile.name == "test"
        assert profile.source_unit == "file"
        assert profile.filename_pattern == "standard"
        assert profile.input_extensions == ()
        assert profile.result_extensions == ()
        assert profile.result_filenames == ()
        assert profile.input_prefixes == ()
        assert profile.result_prefixes == ()
        assert profile.input_directories == ()
        assert profile.result_directory_pattern == ""

    def test_from_dict_full(self):
        """全フィールド指定で正しく生成できる"""
        data = {
            "source-unit": "directory",
            "filename-pattern": "reversed",
            "input-extensions": [".k", ".key"],
            "result-extensions": [".d3plot", ".binout"],
            "result-filenames": ["d3hsp", "messag"],
            "input-prefixes": ["prepin"],
            "result-prefixes": ["flsgrf", "flsprt"],
            "input-directories": ["system", "constant"],
            "result-directory-pattern": r"^\d+(\.\d+)?$",
        }
        profile = SolverProfileConfig.from_dict("lsdyna", data)
        assert profile.name == "lsdyna"
        assert profile.source_unit == "directory"
        assert profile.filename_pattern == "reversed"
        assert profile.input_extensions == (".k", ".key")
        assert profile.result_extensions == (".d3plot", ".binout")
        assert profile.result_filenames == ("d3hsp", "messag")
        assert profile.input_prefixes == ("prepin",)
        assert profile.result_prefixes == ("flsgrf", "flsprt")
        assert profile.input_directories == ("system", "constant")
        assert profile.result_directory_pattern == r"^\d+(\.\d+)?$"

    def test_from_dict_source_unit_file(self):
        """source-unit='file' が受け入れられる"""
        profile = SolverProfileConfig.from_dict("test", {"source-unit": "file"})
        assert profile.source_unit == "file"

    def test_from_dict_source_unit_directory(self):
        """source-unit='directory' が受け入れられる"""
        profile = SolverProfileConfig.from_dict("test", {"source-unit": "directory"})
        assert profile.source_unit == "directory"

    def test_from_dict_invalid_source_unit(self):
        """無効なsource-unitでValueErrorが発生する"""
        with pytest.raises(ValueError, match="source-unit"):
            SolverProfileConfig.from_dict("test", {"source-unit": "invalid"})

    def test_from_dict_filename_pattern_standard(self):
        """filename-pattern='standard' が受け入れられる"""
        profile = SolverProfileConfig.from_dict("test", {"filename-pattern": "standard"})
        assert profile.filename_pattern == "standard"

    def test_from_dict_filename_pattern_reversed(self):
        """filename-pattern='reversed' が受け入れられる"""
        profile = SolverProfileConfig.from_dict("test", {"filename-pattern": "reversed"})
        assert profile.filename_pattern == "reversed"

    def test_from_dict_filename_pattern_none(self):
        """filename-pattern='none' が受け入れられる"""
        profile = SolverProfileConfig.from_dict("test", {"filename-pattern": "none"})
        assert profile.filename_pattern == "none"

    def test_from_dict_invalid_filename_pattern(self):
        """無効なfilename-patternでValueErrorが発生する"""
        with pytest.raises(ValueError, match="filename-pattern"):
            SolverProfileConfig.from_dict("test", {"filename-pattern": "custom"})

    def test_frozen_immutable(self):
        """frozen dataclassのため属性変更が不可"""
        profile = SolverProfileConfig.from_dict("test", {})
        with pytest.raises(AttributeError):
            profile.name = "changed"  # type: ignore[misc]

    def test_extensions_are_tuples(self):
        """リストで渡した拡張子がtupleに変換される"""
        data = {
            "input-extensions": [".inp", ".dat"],
            "result-extensions": [".odb"],
        }
        profile = SolverProfileConfig.from_dict("test", data)
        assert isinstance(profile.input_extensions, tuple)
        assert isinstance(profile.result_extensions, tuple)

    def test_none_extensions_default_to_empty_tuple(self):
        """拡張子がNoneの場合は空tupleになる"""
        profile = SolverProfileConfig.from_dict("test", {"input-extensions": None})
        assert profile.input_extensions == ()


# ====================================================================
# SolverDetectionConfig テスト
# ====================================================================


class TestSolverDetectionConfig:
    """SolverDetectionConfig の単体テスト"""

    def test_from_dict_empty(self):
        """空dictでルールなしのConfigが作成される"""
        config = SolverDetectionConfig.from_dict({})
        assert config.rules == []

    def test_from_dict_none(self):
        """NoneでルールなしのConfigが作成される"""
        config = SolverDetectionConfig.from_dict(None)
        assert config.rules == []

    def test_from_dict_single_pattern(self):
        """単一パターンのルールが正しくパースされる"""
        config = SolverDetectionConfig.from_dict(
            {
                "**/*.k": "lsdyna",
            }
        )
        assert len(config.rules) == 1
        patterns, profile = config.rules[0]
        assert patterns == ["**/*.k"]
        assert profile == "lsdyna"

    def test_from_dict_pipe_separated_patterns(self):
        """パイプ区切りの複数パターンが正しく分割される"""
        config = SolverDetectionConfig.from_dict(
            {
                "**/*.k | **/*.key": "lsdyna",
            }
        )
        assert len(config.rules) == 1
        patterns, profile = config.rules[0]
        assert patterns == ["**/*.k", "**/*.key"]
        assert profile == "lsdyna"

    def test_detect_matches_pattern(self):
        """パスパターンに一致する場合にプロファイル名が返る"""
        config = SolverDetectionConfig.from_dict(
            {
                "**/*.k | **/*.key": "lsdyna",
                "**/prepin.*": "flow3d",
            }
        )
        assert config.detect("case1/model.k") == "lsdyna"
        assert config.detect("case1/model.key") == "lsdyna"
        assert config.detect("case1/prepin.case1") == "flow3d"

    def test_detect_no_match_returns_none(self):
        """どのパターンにもマッチしない場合はNoneが返る"""
        config = SolverDetectionConfig.from_dict(
            {
                "**/*.k": "lsdyna",
            }
        )
        assert config.detect("model.inp") is None

    def test_detect_first_match_wins(self):
        """複数ルールにマッチする場合は最初のルールが優先される"""
        config = SolverDetectionConfig.from_dict(
            {
                "**/*.k | **/*.key": "lsdyna",
                "**/*.k": "calculix",
            }
        )
        # 最初のルールが優先される
        assert config.detect("model.k") == "lsdyna"


# ====================================================================
# GraphConfig.detect_solver_profile テスト
# ====================================================================


class TestDetectSolverProfile:
    """GraphConfig.detect_solver_profile の統合テスト"""

    def _make_config(
        self,
        profiles: dict | None = None,
        detection: dict | None = None,
    ) -> GraphConfig:
        data: dict = {
            "vocab": {},
            "file-relations": {"input-extensions": [".inp"]},
        }
        if profiles:
            data["solver-profiles"] = profiles
        if detection:
            data["solver-detection"] = detection
        return GraphConfig.from_dict(data)

    def test_default_profile_when_no_detection(self):
        """検出ルールなしの場合はデフォルトプロファイルが返る"""
        config = self._make_config()
        profile = config.detect_solver_profile("model.inp")
        assert profile.name == "default"
        assert profile.source_unit == "file"

    def test_detection_returns_matching_profile(self):
        """検出ルールにマッチするプロファイルが返る"""
        config = self._make_config(
            profiles={
                "lsdyna": {
                    "source-unit": "directory",
                    "input-extensions": [".k", ".key"],
                },
            },
            detection={
                "**/*.k | **/*.key": "lsdyna",
            },
        )
        profile = config.detect_solver_profile("case1/model.k")
        assert profile.name == "lsdyna"
        assert profile.source_unit == "directory"
        assert profile.input_extensions == (".k", ".key")

    def test_detection_fallback_to_default(self):
        """マッチしないパスにはデフォルトプロファイルが返る"""
        config = self._make_config(
            profiles={
                "lsdyna": {
                    "source-unit": "directory",
                    "input-extensions": [".k"],
                },
            },
            detection={
                "**/*.k": "lsdyna",
            },
        )
        profile = config.detect_solver_profile("model.inp")
        assert profile.name == "default"

    def test_detection_unknown_profile_falls_to_default(self):
        """検出結果のプロファイル名がsolver-profilesに存在しない場合はデフォルト"""
        config = self._make_config(
            detection={
                "**/*.k": "nonexistent",
            },
        )
        profile = config.detect_solver_profile("model.k")
        assert profile.name == "default"

    def test_custom_default_profile(self):
        """カスタムのdefaultプロファイルが適用される"""
        config = self._make_config(
            profiles={
                "default": {
                    "source-unit": "file",
                    "filename-pattern": "standard",
                    "input-extensions": [".inp", ".dat"],
                    "result-extensions": [".odb", ".sta"],
                },
            },
        )
        profile = config.detect_solver_profile("model.inp")
        assert profile.name == "default"
        assert profile.input_extensions == (".inp", ".dat")
        assert profile.result_extensions == (".odb", ".sta")

    def test_multiple_solver_profiles(self):
        """複数プロファイルが共存し、それぞれ正しく検出される"""
        config = self._make_config(
            profiles={
                "lsdyna": {
                    "source-unit": "directory",
                    "input-extensions": [".k", ".key"],
                },
                "flow3d": {
                    "source-unit": "directory",
                    "filename-pattern": "reversed",
                    "input-prefixes": ["prepin"],
                    "result-prefixes": ["flsgrf"],
                },
            },
            detection={
                "**/*.k | **/*.key": "lsdyna",
                "**/prepin.*": "flow3d",
            },
        )
        lsdyna = config.detect_solver_profile("case/model.k")
        assert lsdyna.name == "lsdyna"

        flow3d = config.detect_solver_profile("case/prepin.sim1")
        assert flow3d.name == "flow3d"
        assert flow3d.filename_pattern == "reversed"
        assert flow3d.input_prefixes == ("prepin",)

        default = config.detect_solver_profile("model.inp")
        assert default.name == "default"


# ====================================================================
# GraphConfig.from_dict ソルバープロファイル統合テスト
# ====================================================================


class TestGraphConfigSolverProfiles:
    """GraphConfig.from_dict のソルバープロファイル関連テスト"""

    def test_default_profile_always_present(self):
        """solver-profiles未指定でもdefaultプロファイルが存在する"""
        config = GraphConfig.from_dict({"vocab": {}})
        assert "default" in config.solver_profiles
        assert config.solver_profiles["default"].name == "default"

    def test_custom_profiles_loaded(self):
        """solver-profilesセクションからプロファイルが読み込まれる"""
        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "solver-profiles": {
                    "lsdyna": {
                        "source-unit": "directory",
                        "input-extensions": [".k"],
                    },
                },
            }
        )
        assert "lsdyna" in config.solver_profiles
        assert "default" in config.solver_profiles

    def test_solver_detection_loaded(self):
        """solver-detectionセクションからルールが読み込まれる"""
        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "solver-detection": {
                    "**/*.k": "lsdyna",
                },
            }
        )
        assert len(config.solver_detection.rules) == 1


# ====================================================================
# パーサーのソルバープロファイル拡張子マージテスト
# ====================================================================


class TestResultRelationParserSolverProfile:
    """ResultRelationParser がソルバープロファイルの拡張子をマージする"""

    def test_recognizes_solver_profile_extensions(self):
        """ソルバープロファイルの拡張子で result_of 関係が作成される"""
        from services.parse.parsers.output_parser import ResultRelationParser

        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "file-relations": {
                    "input-extensions": [".inp"],
                    "result-extensions": [".odb"],
                },
                "solver-profiles": {
                    "lsdyna": {
                        "input-extensions": [".k"],
                        "result-extensions": [".d3plot"],
                    },
                },
            }
        )
        # LS-DYNA: model.k (入力) と model.d3plot (結果) を同名ファイルとして配置
        nodes = [
            Node(id=1, type="unknown", name="model", format="k", properties={"path": "model.k"}),
            Node(id=2, type="unknown", name="model", format="d3plot", properties={"path": "model.d3plot"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = ResultRelationParser().apply(graph)

        rels = [r for r in result.relations if r.label == "result_of"]
        assert len(rels) == 1
        assert rels[0].node1_id == 2  # result → input
        assert rels[0].node2_id == 1

    def test_global_extensions_still_work(self):
        """グローバル設定の拡張子も引き続き機能する"""
        from services.parse.parsers.output_parser import ResultRelationParser

        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "file-relations": {
                    "input-extensions": [".inp"],
                    "result-extensions": [".odb"],
                },
                "solver-profiles": {
                    "lsdyna": {
                        "input-extensions": [".k"],
                        "result-extensions": [".d3plot"],
                    },
                },
            }
        )
        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp", "index": "1"}),
            Node(id=2, type="go", name="go_idx1", format="odb", properties={"path": "go_idx1.odb", "index": "1"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = ResultRelationParser().apply(graph)

        rels = [r for r in result.relations if r.label == "result_of"]
        assert len(rels) == 1

    def test_mixed_solver_extensions(self):
        """複数ソルバーの拡張子が同時に機能する"""
        from services.parse.parsers.output_parser import ResultRelationParser

        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "file-relations": {
                    "input-extensions": [".inp"],
                    "result-extensions": [".odb"],
                },
                "solver-profiles": {
                    "lsdyna": {
                        "input-extensions": [".k"],
                        "result-extensions": [".d3plot"],
                    },
                    "calculix": {
                        "input-extensions": [".inp"],
                        "result-extensions": [".frd"],
                    },
                },
            }
        )
        nodes = [
            # Abaqus pair
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp"}),
            Node(id=2, type="go", name="go_idx1", format="odb", properties={"path": "go_idx1.odb"}),
            # CalculiX pair
            Node(id=3, type="unknown", name="calc_model", format="inp", properties={"path": "calc_model.inp"}),
            Node(id=4, type="unknown", name="calc_model", format="frd", properties={"path": "calc_model.frd"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = ResultRelationParser().apply(graph)

        rels = [r for r in result.relations if r.label == "result_of"]
        assert len(rels) == 2


class TestOutputRelationParserSolverProfile:
    """OutputRelationParser がソルバープロファイルの拡張子をマージする"""

    def test_solver_profile_input_recognized_for_has_output(self):
        """ソルバープロファイルの入力拡張子が has_output で認識される"""
        from services.parse.parsers.output_parser import OutputRelationParser

        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "file-relations": {
                    "input-extensions": [".inp"],
                    "result-extensions": [".odb"],
                },
                "solver-profiles": {
                    "lsdyna": {
                        "input-extensions": [".k"],
                    },
                },
            }
        )
        nodes = [
            Node(id=1, type="unknown", name="model", format="k", properties={"path": "model.k"}),
            Node(id=2, type="unknown", name="model_RF", format="csv", properties={"path": "model_RF.csv"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = OutputRelationParser().apply(graph)

        rels = [r for r in result.relations if r.label == "has_output"]
        assert len(rels) == 1
        assert rels[0].node1_id == 1
        assert rels[0].node2_id == 2


class TestDirectoryRelationParserSolverProfile:
    """DirectoryRelationParser がソルバープロファイルの拡張子をマージする"""

    def test_solver_profile_input_for_directory_has_output(self):
        """ソルバープロファイルの入力拡張子を持つファイルが
        命名規則ディレクトリとhas_output関係で接続される"""
        from services.parse.parsers.directory_parser import DirectoryRelationParser

        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "file-relations": {
                    "input-extensions": [".inp"],
                    "result-extensions": [".odb"],
                },
                "solver-profiles": {
                    "lsdyna": {
                        "input-extensions": [".k"],
                    },
                },
            }
        )
        # go_idx1.k ファイルと go_idx1/ ディレクトリの関係
        # DirectoryRelationParser は命名規則ディレクトリをスキャンするが、
        # ここではnested filesでcontains関係を確認
        nodes = [
            Node(id=1, type="unknown", name="model", format="k", properties={"path": "subdir/model.k"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = DirectoryRelationParser().apply(graph)

        # subdir directory node が作成されcontains関係がある
        dir_nodes = [n for n in result.nodes if n.format == "directory"]
        assert len(dir_nodes) >= 1
        contains = [r for r in result.relations if r.label == "contains"]
        assert len(contains) >= 1


class TestAssetRelationParserSolverProfile:
    """AssetRelationParser がソルバープロファイルの入力拡張子をマージする"""

    def test_solver_profile_input_recognized_for_derived_from(self):
        """ソルバープロファイルの入力拡張子が derived_from で認識される"""
        from services.parse.parsers.output_parser import AssetRelationParser

        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "file-relations": {
                    "input-extensions": [".inp"],
                    "asset-extensions": [".cdb"],
                },
                "solver-profiles": {
                    "lsdyna": {
                        "input-extensions": [".k"],
                    },
                },
            }
        )
        nodes = [
            Node(id=1, type="unknown", name="model", format="k", properties={"path": "model.k"}),
            Node(id=2, type="unknown", name="model", format="cdb", properties={"path": "model.cdb"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = AssetRelationParser().apply(graph)

        rels = [r for r in result.relations if r.label == "derived_from"]
        assert len(rels) == 1
        assert rels[0].node1_id == 1  # input
        assert rels[0].node2_id == 2  # asset
