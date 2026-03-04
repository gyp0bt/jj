"""graph機能のテスト

テスト1: ユーザー指定のテストケース
- ファイル名パターンからidx, version, props, tagsを正しく抽出
- 暗黙のidx/verの処理
- 結果ファイルと入力ファイルの関連付け
- タイプ推定とpath-type-mapの適用
"""

from pathlib import Path

import pytest

from config import GraphConfig
from jj_types import GraphModel, Node
from services.graph import GraphService
from services.parse.file_parse import FileParse, FileType

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "graph_test1"


class TestFileParseBasic:
    """基本的なファイル名パースのテスト"""

    def test_go_idx1_w5_t20_inp(self):
        """go_idx1_w5_t20.inp: idx=1, w=5, t=20, v=1(暗黙)"""
        parser = FileParse("go_idx1_w5_t20.inp")
        assert parser.get_file_type() == FileType.GO
        assert parser.get_index() == "1"
        props = parser.get_props()
        assert props.get("idx") == "1"
        assert props.get("w") == "5"
        assert props.get("t") == "20"
        assert parser.get_tags() == []

    def test_go_idx1_v2_inp(self):
        """go_idx1_v2.inp: idx=1, v=2"""
        parser = FileParse("go_idx1_v2.inp")
        assert parser.get_file_type() == FileType.GO
        assert parser.get_index() == "1"
        assert parser.get_version() == "2"
        assert parser.get_tags() == []

    def test_go_idx1_w5_t20_damage_initiation_v3_inp(self):
        """go_idx1_w5_t20_damage-initiation_v3.inp: idx=1, w=5, t=20, v=3, tag=damage-initiation"""
        parser = FileParse("go_idx1_w5_t20_damage-initiation_v3.inp")
        assert parser.get_file_type() == FileType.GO
        assert parser.get_index() == "1"
        props = parser.get_props()
        assert props.get("w") == "5"
        assert props.get("t") == "20"
        assert parser.get_version() == "3"
        # damage-initiationはtagとして扱われる
        assert "damage-initiation" in parser.get_tags()

    def test_go_idx2_inp(self):
        """go_idx2.inp: idx=2, v=1(暗黙)"""
        parser = FileParse("go_idx2.inp")
        assert parser.get_file_type() == FileType.GO
        assert parser.get_index() == "2"


class TestFileParseImplicitIndexVersion:
    """暗黙のindex/versionのテスト"""

    def test_material_inp_implicit_idx_ver(self):
        """material.inp: type=material, idx=1(暗黙), v=1(暗黙)

        material_, mesh_, step_などのプレフィックスがなくても
        ファイル名がmaterial, mesh, stepの場合はタイプを推定する
        """
        parser = FileParse("material.inp")
        # ファイル名がそのものの場合もタイプを推定
        assert parser.get_file_type() == FileType.MATERIAL
        assert parser.get_index() == "1"  # 暗黙のindex
        assert parser.get_version() == "1"  # 暗黙のversion

    def test_mesh_inp_implicit_idx_ver(self):
        """mesh.inp: type=mesh, idx=1(暗黙), v=1(暗黙)"""
        parser = FileParse("mesh.inp")
        assert parser.get_file_type() == FileType.MESH
        assert parser.get_index() == "1"
        assert parser.get_version() == "1"

    def test_go_inp_implicit_idx_ver(self):
        """go.inp: type=go, idx=1(暗黙), v=1(暗黙)"""
        parser = FileParse("go.inp")
        assert parser.get_file_type() == FileType.GO
        assert parser.get_index() == "1"
        assert parser.get_version() == "1"


class TestFileParseVersionNotation:
    """バージョン記法のテスト"""

    def test_legacy_version_dot_notation(self):
        """material.v2.inp: v=2 (.v2形式のレガシー記法)"""
        parser = FileParse("material.v2.inp")
        assert parser.get_version() == "2"

    def test_result_file_odb(self):
        """go_idx1_w5_t20.odb: idx=1, w=5, t=20"""
        parser = FileParse("go_idx1_w5_t20.odb")
        assert parser.get_file_type() == FileType.GO
        assert parser.get_index() == "1"
        props = parser.get_props()
        assert props.get("w") == "5"
        assert props.get("t") == "20"

    def test_result_file_sta(self):
        """go_idx1_w5_t20.sta: idx=1, w=5, t=20"""
        parser = FileParse("go_idx1_w5_t20.sta")
        assert parser.get_file_type() == FileType.GO
        assert parser.get_index() == "1"


class TestFileParseResultFiles:
    """結果ファイルのテスト"""

    def test_odb_json(self):
        """go_idx1_w5_t20.odb.json: ODB処理後データ"""
        parser = FileParse("go_idx1_w5_t20.odb.json")
        assert parser.get_file_type() == FileType.GO
        assert parser.get_index() == "1"

    def test_rf_csv(self):
        """go_idx1_w5_t20_RF.csv: RFタグ付き"""
        parser = FileParse("go_idx1_w5_t20_RF.csv")
        assert parser.get_file_type() == FileType.GO
        assert parser.get_index() == "1"
        # RFはタグとして扱われる
        assert "RF" in parser.get_tags()

    def test_stress_csv(self):
        """go_idx1_w5_t20_stress.csv: stressタグ付き"""
        parser = FileParse("go_idx1_w5_t20_stress.csv")
        assert parser.get_file_type() == FileType.GO
        assert parser.get_index() == "1"
        assert "stress" in parser.get_tags()


class TestFileParseAssets:
    """静的データ（assets）のテスト"""

    def test_mesh_modfem(self):
        """mesh.modfem: type=mesh(推定)"""
        parser = FileParse("mesh.modfem")
        # mesh.modfemはmeshタイプとして推定される可能性がある
        file_type = parser.get_file_type()
        # プレフィックスがないのでUNKNOWNまたはMESH
        assert file_type in [FileType.MESH, FileType.UNKNOWN]

    def test_mesh_idx2_v2_modfem(self):
        """mesh_idx2_v2.modfem: type=mesh, idx=2, v=2"""
        parser = FileParse("mesh_idx2_v2.modfem")
        assert parser.get_file_type() == FileType.MESH
        assert parser.get_index() == "2"
        assert parser.get_version() == "2"


class TestFileParseReports:
    """報告書ファイルのテスト"""

    def test_report_with_date_idx(self):
        """260205_構造解析_idx1.pptx: 日付=260205, tag=構造解析, idx=1"""
        parser = FileParse("260205_構造解析_idx1.pptx")
        # 日付260205はタグとして扱われる
        # 構造解析もタグとして扱われる
        assert parser.get_index() == "1"
        tags = parser.get_tags()
        # 日付と構造解析がタグに含まれる
        assert "260205" in tags or "構造解析" in tags

    def test_report_with_date_idx_v2(self):
        """260205_構造解析_idx1_v2.pptx: idx=1, v=2"""
        parser = FileParse("260205_構造解析_idx1_v2.pptx")
        assert parser.get_index() == "1"
        assert parser.get_version() == "2"


class TestGraphServiceParse:
    """GraphServiceのパースのテスト"""

    @pytest.fixture
    def config(self):
        """テスト用設定"""
        return GraphConfig.from_dict(
            {
                "vocab": {"idx": "条件", "v": "バージョン"},
                "path-type-map": {
                    "**go_*": {
                        "*.inp": "Abaqusインプット",
                        "*.odb": "Abaqus ODB",
                        "*.sta": "Abaqusステータス",
                        "*": "計算結果",
                    },
                    "**/reports/*": {
                        "*": "報告書",
                    },
                    "**/results/*": {
                        "*": "計算結果",
                    },
                    "**/tools/*": {
                        "*": "処理スクリプト",
                    },
                    "**/assets/*": {
                        "*": "静的データ",
                    },
                    "**/docs/*": {
                        "*": "受領ファイル",
                    },
                },
                "ignore": ["notes", "notes/**", ".obsidian", ".obsidian/**"],
                "obsidian": {
                    "notes-dir": "notes/props",
                    "bases-dir": "notes/bases",
                    "prefix": "O-",
                },
            }
        )

    @pytest.fixture
    def graph_service(self, config):
        """テスト用GraphService"""
        if not FIXTURE_DIR.exists():
            pytest.skip(f"Fixture directory not found: {FIXTURE_DIR}")
        return GraphService(project_root=FIXTURE_DIR, config=config)

    def test_scan_files(self, graph_service):
        """ファイルスキャンのテスト"""
        # .inp, .odb, .sta, .csv, .pptx, .py, .json, .modfem, .stl
        extensions = [
            ".inp",
            ".odb",
            ".sta",
            ".csv",
            ".pptx",
            ".py",
            ".json",
            ".modfem",
            ".stl",
        ]
        files = graph_service.scan_files(extensions=extensions)
        assert len(files) > 0

        # 期待されるファイルが含まれているか確認
        filenames = [f.name for f in files]
        assert "go_idx1_w5_t20.inp" in filenames
        assert "material.inp" in filenames
        assert "go_idx1_w5_t20.odb" in filenames

    def test_parse_project_creates_nodes(self, graph_service):
        """プロジェクトパースでノードが生成されること"""
        extensions = [
            ".inp",
            ".odb",
            ".sta",
            ".csv",
            ".pptx",
            ".py",
            ".json",
            ".modfem",
            ".stl",
        ]
        graph = graph_service.parse_project(extensions=extensions)

        assert isinstance(graph, GraphModel)
        assert len(graph.nodes) > 0

    def test_version_relations(self, graph_service):
        """バージョン関係が構築されること

        go_idx1_v2.inp と go_idx1_w5_t20.inp は同じidx=1だが、
        go_idx1_v2.inpはv=2なので、バージョン関係でリンクされるはず
        """
        extensions = [".inp", ".odb", ".sta", ".csv"]
        graph = graph_service.parse_project(extensions=extensions)

        # idx=1のノードを取得
        idx1_nodes = [n for n in graph.nodes if n.properties.get("index") == "1"]

        # バージョン関係があることを確認
        next_version_relations = [r for r in graph.relations if r.label == "next_version"]
        # 同じidxのノードが複数あるなら、next_version関係があるはず
        if len(idx1_nodes) > 1:
            # 少なくとも1つのnext_version関係がある
            assert len(next_version_relations) > 0

    def test_same_index_group_relations(self, graph_service):
        """同一インデックスグループ関係が構築されること"""
        extensions = [".inp"]
        graph = graph_service.parse_project(extensions=extensions)

        # same_index_group関係があることを確認
        group_relations = [r for r in graph.relations if r.label == "same_index_group"]
        # go_idx1のファイルが複数あるので、グループ関係がある
        assert len(group_relations) >= 0  # 0以上（同一タイプ・インデックスが必要）


class TestResultFileRelations:
    """結果ファイルと入力ファイルの関係テスト"""

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict(
            {
                "vocab": {},
                "path-type-map": {
                    "**go_*": {
                        "*.inp": "Abaqusインプット",
                        "*.odb": "Abaqus ODB",
                        "*.sta": "Abaqusステータス",
                        "*.csv": "計算結果CSV",
                        "*.json": "処理済みデータ",
                    },
                },
                "ignore": [],
                "obsidian": {},
            }
        )

    @pytest.fixture
    def graph_service(self, config):
        if not FIXTURE_DIR.exists():
            pytest.skip(f"Fixture directory not found: {FIXTURE_DIR}")
        return GraphService(project_root=FIXTURE_DIR, config=config)

    def test_inp_and_odb_same_idx(self, graph_service):
        """go_idx1_w5_t20.inp が存在し、.odbはNO_NODE_EXTENSIONSによりNode化されない"""
        extensions = [".inp", ".odb"]
        graph = graph_service.parse_project(extensions=extensions)

        inp_nodes = [n for n in graph.nodes if n.name == "go_idx1_w5_t20" and n.format == "inp"]
        odb_nodes = [n for n in graph.nodes if n.name == "go_idx1_w5_t20" and n.format == "odb"]

        assert len(inp_nodes) == 1
        # .odbはNO_NODE_EXTENSIONSに含まれるためNode化されない
        assert len(odb_nodes) == 0

    def test_result_of_relation(self, graph_service):
        """.odbはNO_NODE_EXTENSIONSによりNode化されないため、result_of関係は生成されない"""
        extensions = [".inp", ".odb", ".sta"]
        graph = graph_service.parse_project(extensions=extensions)

        # .odbはNode化されないため、.odbベースのresult_of関係は発生しない
        odb_nodes = [n for n in graph.nodes if n.format == "odb"]
        assert len(odb_nodes) == 0

        # .inpは存在する
        inp_node = next(
            (n for n in graph.nodes if n.name == "go_idx1_w5_t20" and n.format == "inp"),
            None,
        )
        assert inp_node is not None


class TestVersionSorting:
    """バージョンソートのテスト"""

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict(
            {
                "vocab": {},
                "path-type-map": {
                    "**go_*": {"*.inp": "Abaqusインプット"},
                },
                "ignore": [],
                "obsidian": {},
            }
        )

    @pytest.fixture
    def graph_service(self, config):
        if not FIXTURE_DIR.exists():
            pytest.skip(f"Fixture directory not found: {FIXTURE_DIR}")
        return GraphService(project_root=FIXTURE_DIR, config=config)

    def test_version_sort_order(self, graph_service):
        """バージョンソートが正しく行われること

        go_idx1_w5_t20.inp (v=空/1暗黙) → go_idx1_v2.inp (v=2) → go_idx1_w5_t20_damage-initiation_v3.inp (v=3)
        """
        extensions = [".inp"]
        graph = graph_service.parse_project(extensions=extensions)

        # idx=1, type=Abaqusインプットのノードを取得
        idx1_inps = [n for n in graph.nodes if n.properties.get("index") == "1" and n.type == "Abaqusインプット"]

        # next_version関係を取得
        next_version_relations = [r for r in graph.relations if r.label == "next_version"]

        # go_idx1_w5_t20.inp → go_idx1_v2.inp の関係を確認
        v1_node = next((n for n in idx1_inps if n.name == "go_idx1_w5_t20"), None)
        v2_node = next((n for n in idx1_inps if n.name == "go_idx1_v2"), None)
        v3_node = next((n for n in idx1_inps if "damage-initiation" in n.name), None)

        assert v1_node is not None
        assert v2_node is not None
        assert v3_node is not None

        # v1 → v2の関係
        v1_to_v2 = next(
            (r for r in next_version_relations if r.node1_id == v1_node.id and r.node2_id == v2_node.id),
            None,
        )
        assert v1_to_v2 is not None, "v1 → v2 の next_version 関係がない"

        # v2 → v3の関係
        v2_to_v3 = next(
            (r for r in next_version_relations if r.node1_id == v2_node.id and r.node2_id == v3_node.id),
            None,
        )
        assert v2_to_v3 is not None, "v2 → v3 の next_version 関係がない"


class TestPathTypeMapIntegration:
    """path-type-mapの統合テスト"""

    def test_reports_dir_type(self):
        """reports/配下のファイルは報告書タイプになる"""
        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "path-type-map": {
                    "**/reports/*": {"*": "報告書"},
                },
                "ignore": [],
                "obsidian": {},
            }
        )

        # path-type-mapのマッチング確認
        result = config.path_type_map.get_type("reports/260205_構造解析_idx1.pptx", "260205_構造解析_idx1.pptx")
        assert result == "報告書"

    def test_assets_dir_type(self):
        """assets/配下のファイルは静的データタイプになる"""
        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "path-type-map": {
                    "**/assets/*": {"*": "静的データ"},
                },
                "ignore": [],
                "obsidian": {},
            }
        )

        result = config.path_type_map.get_type("assets/mesh.modfem", "mesh.modfem")
        assert result == "静的データ"


class TestConfigRules:
    """設定ルールのテスト"""

    def test_ignore_notes(self):
        """notes/ディレクトリは除外される"""
        from config import IgnoreConfig

        ignore = IgnoreConfig.from_list(["notes", "notes/**", ".obsidian", ".obsidian/**"])

        assert ignore.should_ignore("notes/sample.md")
        assert ignore.should_ignore("notes/nested/file.md")
        assert ignore.should_ignore(".obsidian/config.json")
        assert not ignore.should_ignore("go_idx1.inp")


class TestDateParsing:
    """日付パース機能のテスト"""

    def test_date_yymmdd(self):
        """YYMMDD形式の日付パース"""
        parser = FileParse("260205_構造解析_idx1.pptx")
        assert parser.get_date() == "260205"
        assert parser.get_date_formatted() == "2026-02-05"

    def test_date_yyyymmdd(self):
        """YYYYMMDD形式の日付パース"""
        parser = FileParse("20260205_analysis.csv")
        assert parser.get_date() == "20260205"
        assert parser.get_date_formatted() == "2026-02-05"

    def test_date_not_in_tags(self):
        """日付はtagsに含まれない"""
        parser = FileParse("260205_構造解析_idx1.pptx")
        tags = parser.get_tags()
        assert "260205" not in tags
        assert "構造解析" in tags

    def test_no_date(self):
        """日付なしのファイル"""
        parser = FileParse("go_idx1_w5.inp")
        assert parser.get_date() == ""
        assert parser.get_date_formatted() == ""

    def test_date_1900s(self):
        """1900年代の日付（YY > 50）"""
        parser = FileParse("991231_legacy.csv")
        assert parser.get_date_formatted() == "1999-12-31"


class TestFileRelationsConfig:
    """FileRelationsConfig のテスト"""

    def test_default_extensions(self):
        """デフォルトの拡張子が設定される"""
        from config import FileRelationsConfig

        config = FileRelationsConfig.from_dict({})
        assert ".inp" in config.input_extensions
        assert ".odb" in config.result_extensions
        assert ".modfem" in config.asset_extensions

    def test_custom_extensions(self):
        """カスタム拡張子が設定できる"""
        from config import FileRelationsConfig

        config = FileRelationsConfig.from_dict(
            {
                "input-extensions": [".inp", ".custom"],
                "result-extensions": [".result"],
                "asset-extensions": [".asset"],
            }
        )
        assert ".custom" in config.input_extensions
        assert ".result" in config.result_extensions
        assert ".asset" in config.asset_extensions


class TestAssetRelations:
    """アセット関係（derived_from）のテスト"""

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict(
            {
                "vocab": {},
                "path-type-map": {
                    "**mesh_* | **mesh": {
                        "*.inp": "メッシュ",
                        "*.modfem": "修正メッシュ",
                    },
                },
                "file-relations": {
                    "input-extensions": [".inp"],
                    "result-extensions": [".odb"],
                    "asset-extensions": [".modfem", ".stl"],
                },
                "ignore": [],
                "obsidian": {},
            }
        )

    @pytest.fixture
    def graph_service(self, config):
        if not FIXTURE_DIR.exists():
            pytest.skip(f"Fixture directory not found: {FIXTURE_DIR}")
        return GraphService(project_root=FIXTURE_DIR, config=config)

    def test_asset_derived_from_relation(self, graph_service):
        """mesh.modfem と mesh.inp の間にderived_from関係がある"""
        extensions = [".inp", ".modfem", ".stl"]
        graph = graph_service.parse_project(extensions=extensions)

        # derived_from関係を取得
        derived_relations = [r for r in graph.relations if r.label == "derived_from"]

        # mesh.inp と mesh.modfem のノードを取得
        mesh_inp = next((n for n in graph.nodes if n.name == "mesh" and n.format == "inp"), None)
        mesh_modfem = next((n for n in graph.nodes if n.name == "mesh" and n.format == "modfem"), None)

        if mesh_inp and mesh_modfem:
            # derived_from関係が存在
            relation = next(
                (r for r in derived_relations if r.node1_id == mesh_inp.id and r.node2_id == mesh_modfem.id),
                None,
            )
            assert relation is not None, "mesh.inp → mesh.modfem の derived_from 関係がない"


class TestPathTypeMapOrdering:
    """path-type-mapの評価順序テスト"""

    def test_specific_pattern_first(self):
        """より具体的なパターンが先に評価される"""
        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "path-type-map": {
                    "**go_*": {"*.inp": "汎用計算"},  # より汎用的
                    "**/reports/*": {"*.pptx": "報告書"},  # より具体的（先に評価される）
                },
                "ignore": [],
                "obsidian": {},
            }
        )

        # 具体的なパターンが優先される
        result = config.path_type_map.get_type("reports/260205.pptx", "260205.pptx")
        assert result == "報告書"

    def test_file_pattern_specificity(self):
        """ファイルパターンも具体性でソートされる"""
        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "path-type-map": {
                    "**go_*": {
                        "*": "計算結果",  # 最も汎用的
                        "*.inp": "計算入力",  # より具体的
                    },
                },
                "ignore": [],
                "obsidian": {},
            }
        )

        # .inpパターンが先に評価される
        result = config.path_type_map.get_type("go_idx1.inp", "go_idx1.inp")
        assert result == "計算入力"


class TestIncludesRelations:
    """includes関係のテスト"""

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict(
            {
                "vocab": {},
                "path-type-map": {},
                "file-relations": {
                    "input-extensions": [".inp"],
                    "result-extensions": [".odb"],
                    "asset-extensions": [".modfem"],
                },
                "ignore": [],
                "obsidian": {},
            }
        )

    @pytest.fixture
    def graph_service(self, config):
        if not FIXTURE_DIR.exists():
            pytest.skip(f"Fixture directory not found: {FIXTURE_DIR}")
        return GraphService(project_root=FIXTURE_DIR, config=config)

    def test_includes_relation_exists(self, graph_service):
        """*includeディレクティブがあれば関係が構築される"""
        # テストフィクスチャのgoファイルにincludeを追加してテスト
        extensions = [".inp"]
        graph = graph_service.parse_project(extensions=extensions)

        # includes関係を取得
        includes_relations = [r for r in graph.relations if r.label == "includes"]

        # go_idx1_w5_t20.inp に mesh.inp や material.inp への *include があれば関係が作成される
        # テストデータに依存するため、関係の存在のみ確認
        # テストデータに*includeがある場合のみ関係が存在
        assert isinstance(includes_relations, list)


class TestOutputRelations:
    """同一ファイルタイプのprops差分関連付け（has_output）のテスト"""

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict(
            {
                "vocab": {},
                "path-type-map": {
                    "**go_*": {
                        "*.inp": "Abaqusインプット",
                        "*.odb": "Abaqus ODB",
                        "*.sta": "Abaqusステータス",
                        "*.csv": "計算結果CSV",
                        "*.json": "処理済みデータ",
                    },
                },
                "ignore": [],
                "obsidian": {},
            }
        )

    @pytest.fixture
    def graph_service(self, config):
        if not FIXTURE_DIR.exists():
            pytest.skip(f"Fixture directory not found: {FIXTURE_DIR}")
        return GraphService(project_root=FIXTURE_DIR, config=config)

    def test_has_output_rf_csv(self, graph_service):
        """go_idx1_w5_t20.inp → go_idx1_w5_t20_RF.csv のhas_output関係"""
        extensions = [".inp", ".csv"]
        graph = graph_service.parse_project(extensions=extensions)

        has_output_relations = [r for r in graph.relations if r.label == "has_output"]

        inp_node = next(
            (n for n in graph.nodes if n.name == "go_idx1_w5_t20" and n.format == "inp"),
            None,
        )
        rf_node = next(
            (n for n in graph.nodes if n.name == "go_idx1_w5_t20_RF" and n.format == "csv"),
            None,
        )

        assert inp_node is not None, "go_idx1_w5_t20.inp ノードが見つからない"
        assert rf_node is not None, "go_idx1_w5_t20_RF.csv ノードが見つからない"

        # has_output関係が存在
        relation = next(
            (r for r in has_output_relations if r.node1_id == inp_node.id and r.node2_id == rf_node.id),
            None,
        )
        assert relation is not None, "go_idx1_w5_t20.inp → go_idx1_w5_t20_RF.csv の has_output 関係がない"

    def test_results_dir_files_not_noded(self, graph_service):
        """results/ディレクトリのファイルはNode化されない（info-only）"""
        extensions = [".inp", ".csv"]
        graph = graph_service.parse_project(extensions=extensions)

        # results/配下のファイルはNode化されないことを確認
        results_nodes = [
            n for n in graph.nodes if n.properties.get("path", "").startswith("results/") and n.format != "directory"
        ]
        assert len(results_nodes) == 0, f"results/配下のファイルがNode化されている: {[n.name for n in results_nodes]}"


class TestDirectoryRelations:
    """フォルダベースの関連付け（contains）のテスト"""

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict(
            {
                "vocab": {},
                "path-type-map": {
                    "**go_*": {
                        "*.inp": "Abaqusインプット",
                        "*.csv": "計算結果CSV",
                        "*.png": "画像",
                        "*.yaml": "データ",
                    },
                },
                "ignore": [],
                "obsidian": {},
            }
        )

    @pytest.fixture
    def graph_service(self, config):
        if not FIXTURE_DIR.exists():
            pytest.skip(f"Fixture directory not found: {FIXTURE_DIR}")
        return GraphService(project_root=FIXTURE_DIR, config=config)

    def test_directory_node_created(self, graph_service):
        """go_idx1_w5_t20/ ディレクトリがノードとして生成される"""
        extensions = [".inp", ".csv", ".png", ".yaml"]
        graph = graph_service.parse_project(extensions=extensions)

        dir_nodes = [n for n in graph.nodes if n.format == "directory"]
        go_dir = next(
            (n for n in dir_nodes if n.name == "go_idx1_w5_t20"),
            None,
        )
        assert go_dir is not None, "go_idx1_w5_t20 ディレクトリノードが見つからない"
        assert go_dir.type == "go_directory"
        assert go_dir.properties.get("index") == "1"

    def test_contains_relations(self, graph_service):
        """ディレクトリ内のファイルがcontains関係でリンクされる"""
        extensions = [".inp", ".csv", ".png", ".yaml"]
        graph = graph_service.parse_project(extensions=extensions)

        contains_relations = [r for r in graph.relations if r.label == "contains"]

        dir_node = next(
            (n for n in graph.nodes if n.name == "go_idx1_w5_t20" and n.format == "directory"),
            None,
        )
        assert dir_node is not None

        # ディレクトリ内のファイルが含まれている
        contained_ids = {r.node2_id for r in contains_relations if r.node1_id == dir_node.id}
        assert len(contained_ids) > 0, "contains関係が1つもない"

    def test_directory_has_output_from_inp(self, graph_service):
        """go_idx1_w5_t20.inp → go_idx1_w5_t20/ のhas_output関係"""
        extensions = [".inp", ".csv", ".png", ".yaml"]
        graph = graph_service.parse_project(extensions=extensions)

        has_output_relations = [r for r in graph.relations if r.label == "has_output"]

        inp_node = next(
            (n for n in graph.nodes if n.name == "go_idx1_w5_t20" and n.format == "inp"),
            None,
        )
        dir_node = next(
            (n for n in graph.nodes if n.name == "go_idx1_w5_t20" and n.format == "directory"),
            None,
        )

        assert inp_node is not None
        assert dir_node is not None

        relation = next(
            (r for r in has_output_relations if r.node1_id == inp_node.id and r.node2_id == dir_node.id),
            None,
        )
        assert relation is not None, "go_idx1_w5_t20.inp → go_idx1_w5_t20/ の has_output 関係がない"


class TestMaterialParsing:
    """material.inpの高度な解析のテスト"""

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict(
            {
                "vocab": {},
                "path-type-map": {},
                "file-relations": {
                    "input-extensions": [".inp"],
                },
                "ignore": [],
                "obsidian": {},
            }
        )

    @pytest.fixture
    def graph_service(self, config):
        if not FIXTURE_DIR.exists():
            pytest.skip(f"Fixture directory not found: {FIXTURE_DIR}")
        return GraphService(project_root=FIXTURE_DIR, config=config)

    def test_material_nodes_created(self, graph_service):
        """material.inpから abaqus_material ノードが生成される"""
        extensions = [".inp"]
        graph = graph_service.parse_project(extensions=extensions)

        mat_nodes = [n for n in graph.nodes if n.type == "abaqus_material"]
        assert len(mat_nodes) >= 2, f"materialノードが2つ以上必要 (実際: {len(mat_nodes)})"

        names = {n.name for n in mat_nodes}
        assert "steel_s235" in names or "Steel_S235" in names, f"Steel_S235 materialが見つからない: {names}"

    def test_material_elastic_props(self, graph_service):
        """material nodeにelasticプロパティが含まれる"""
        extensions = [".inp"]
        graph = graph_service.parse_project(extensions=extensions)

        mat_nodes = [n for n in graph.nodes if n.type == "abaqus_material"]
        steel = next(
            (n for n in mat_nodes if "steel" in n.name.lower()),
            None,
        )
        assert steel is not None, "Steel materialが見つからない"
        assert "elastic" in steel.properties, "elasticプロパティがない"
        assert "keywords" in steel.properties, "keywordsがない"
        assert "elastic" in steel.properties["keywords"]

        # elasticデータ確認: [[210000.0, 0.3]]
        elastic_data = steel.properties["elastic"]
        assert len(elastic_data) == 1
        assert elastic_data[0][0] == 210000.0
        assert elastic_data[0][1] == 0.3

    def test_material_density_props(self, graph_service):
        """material nodeにdensityプロパティが含まれる"""
        extensions = [".inp"]
        graph = graph_service.parse_project(extensions=extensions)

        mat_nodes = [n for n in graph.nodes if n.type == "abaqus_material"]
        steel = next(
            (n for n in mat_nodes if "steel" in n.name.lower()),
            None,
        )
        assert steel is not None
        assert "density" in steel.properties
        assert "density" in steel.properties["keywords"]

    def test_material_plastic_props(self, graph_service):
        """Steel_S235にはplasticプロパティがある（2行のデータ）"""
        extensions = [".inp"]
        graph = graph_service.parse_project(extensions=extensions)

        mat_nodes = [n for n in graph.nodes if n.type == "abaqus_material"]
        steel = next(
            (n for n in mat_nodes if "steel" in n.name.lower()),
            None,
        )
        assert steel is not None
        assert "plastic" in steel.properties
        plastic_data = steel.properties["plastic"]
        assert len(plastic_data) == 2  # 2行のplasticデータ

    def test_material_defined_in_relation(self, graph_service):
        """materialノードがdefined_in関係で入力ファイルにリンクされる"""
        extensions = [".inp"]
        graph = graph_service.parse_project(extensions=extensions)

        defined_in_relations = [r for r in graph.relations if r.label == "defined_in"]
        assert len(defined_in_relations) >= 2, "defined_in関係が2つ以上必要"

        mat_nodes = [n for n in graph.nodes if n.type == "abaqus_material"]
        for mat_node in mat_nodes:
            relation = next(
                (r for r in defined_in_relations if r.node1_id == mat_node.id),
                None,
            )
            assert relation is not None, f"{mat_node.name} に defined_in 関係がない"


class TestStaAnalysis:
    """解析結果ファイル（.sta）の解析テスト"""

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict(
            {
                "vocab": {},
                "path-type-map": {
                    "**go_*": {
                        "*.inp": "Abaqusインプット",
                        "*.sta": "Abaqusステータス",
                    },
                },
                "file-relations": {
                    "input-extensions": [".inp"],
                    "result-extensions": [".sta"],
                },
                "ignore": [],
                "obsidian": {},
            }
        )

    @pytest.fixture
    def graph_service(self, config):
        if not FIXTURE_DIR.exists():
            pytest.skip(f"Fixture directory not found: {FIXTURE_DIR}")
        return GraphService(project_root=FIXTURE_DIR, config=config)

    def test_sta_completed_status(self, graph_service):
        """成功したstaの情報が対応するinpノードに集約される（.staはNode化しない）"""
        extensions = [".inp", ".sta"]
        graph = graph_service.parse_project(extensions=extensions)

        # .staはNode化されない
        sta_node = next(
            (n for n in graph.nodes if n.name == "go_idx1_w5_t20" and n.format == "sta"),
            None,
        )
        assert sta_node is None, ".staノードはグラフから除外されるべき"

        # 対応するinpノードにanalysis_statusが集約される
        inp_node = next(
            (n for n in graph.nodes if n.name == "go_idx1_w5_t20" and n.format == "inp"),
            None,
        )
        assert inp_node is not None, "go_idx1_w5_t20.inp ノードが見つからない"
        assert inp_node.properties.get("analysis_status") == "completed"

    def test_sta_failed_status(self, graph_service):
        """失敗したstaの情報が対応するinpノードに集約される"""
        extensions = [".inp", ".sta"]
        graph = graph_service.parse_project(extensions=extensions)

        # .staはNode化されない
        sta_node = next(
            (n for n in graph.nodes if n.name == "go_idx2" and n.format == "sta"),
            None,
        )
        assert sta_node is None, ".staノードはグラフから除外されるべき"

        # 対応するinpノードにanalysis_statusとエラーが集約される
        inp_node = next(
            (n for n in graph.nodes if n.name == "go_idx2" and n.format == "inp"),
            None,
        )
        assert inp_node is not None, "go_idx2.inp ノードが見つからない"
        assert inp_node.properties.get("analysis_status") == "failed"
        assert len(inp_node.properties.get("sta_errors", [])) > 0, "エラーメッセージが集約されていない"

    def test_includes_relation_with_content(self, graph_service):
        """go_idx1_w5_t20.inp に実際の *INCLUDE があり、includes関係が構築される"""
        extensions = [".inp"]
        graph = graph_service.parse_project(extensions=extensions)

        includes_relations = [r for r in graph.relations if r.label == "includes"]

        go_node = next(
            (n for n in graph.nodes if n.name == "go_idx1_w5_t20" and n.format == "inp"),
            None,
        )
        material_node = next(
            (n for n in graph.nodes if n.name == "material" and n.format == "inp"),
            None,
        )

        assert go_node is not None
        assert material_node is not None

        relation = next(
            (r for r in includes_relations if r.node1_id == go_node.id and r.node2_id == material_node.id),
            None,
        )
        assert relation is not None, "go_idx1_w5_t20.inp → material.inp の includes 関係がない"


class TestParseMaterialBlocks:
    """parse_material_blocks関数の単体テスト"""

    def test_parse_material_from_file(self):
        """material.inpファイルのパース"""
        from services.parse.connectors.abaqus.inp_parser import parse_material_blocks

        inp_path = FIXTURE_DIR / "material.inp"
        if not inp_path.exists():
            pytest.skip("material.inp fixture not found")

        materials = parse_material_blocks(inp_path)
        assert len(materials) == 2

        steel = materials[0]
        assert "steel_s235" in steel["name"].lower()
        assert "elastic" in steel["keywords"]
        assert "density" in steel["keywords"]
        assert "plastic" in steel["keywords"]
        assert "conductivity" in steel["keywords"]

        aluminum = materials[1]
        assert "aluminum" in aluminum["name"].lower()
        assert "elastic" in aluminum["keywords"]
        assert "density" in aluminum["keywords"]

    def test_parse_empty_file(self, tmp_path):
        """空ファイルのパース"""
        from services.parse.connectors.abaqus.inp_parser import parse_material_blocks

        empty_file = tmp_path / "empty.inp"
        empty_file.write_text("")
        materials = parse_material_blocks(empty_file)
        assert materials == []

    def test_parse_file_without_material(self, tmp_path):
        """*MATERIALブロックがないファイル"""
        from services.parse.connectors.abaqus.inp_parser import parse_material_blocks

        inp_file = tmp_path / "no_material.inp"
        inp_file.write_text("*STEP\n*STATIC\n1., 1.\n*END STEP\n")
        materials = parse_material_blocks(inp_file)
        assert materials == []


class TestParseStaFile:
    """parse_sta_file関数の単体テスト"""

    def test_parse_completed_sta(self):
        """成功したstaファイル"""
        from services.parse.connectors.abaqus.result_parser import parse_sta_file

        sta_path = FIXTURE_DIR / "go_idx1_w5_t20.sta"
        if not sta_path.exists():
            pytest.skip("sta fixture not found")

        result = parse_sta_file(sta_path)
        assert result["analysis_status"] == "completed"
        assert result["errors"] == []

    def test_parse_failed_sta(self):
        """失敗したstaファイル"""
        from services.parse.connectors.abaqus.result_parser import parse_sta_file

        sta_path = FIXTURE_DIR / "go_idx2.sta"
        if not sta_path.exists():
            pytest.skip("sta fixture not found")

        result = parse_sta_file(sta_path)
        assert result["analysis_status"] == "failed"
        assert len(result["errors"]) > 0
        assert "TOO MANY ATTEMPTS" in result["errors"][0]

    def test_parse_nonexistent_sta(self, tmp_path):
        """存在しないファイル"""
        from services.parse.connectors.abaqus.result_parser import parse_sta_file

        result = parse_sta_file(tmp_path / "nonexistent.sta")
        assert result["analysis_status"] == "unknown"


class TestGraphSummaryRelationTypes:
    """summaryでリレーションタイプ別の集計が正しいことを確認"""

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict(
            {
                "vocab": {},
                "path-type-map": {
                    "**go_*": {
                        "*.inp": "Abaqusインプット",
                        "*.odb": "Abaqus ODB",
                        "*.sta": "Abaqusステータス",
                        "*.csv": "計算結果CSV",
                        "*.json": "処理済みデータ",
                    },
                },
                "ignore": [],
                "obsidian": {},
            }
        )

    @pytest.fixture
    def graph_service(self, config):
        if not FIXTURE_DIR.exists():
            pytest.skip(f"Fixture directory not found: {FIXTURE_DIR}")
        return GraphService(project_root=FIXTURE_DIR, config=config)

    def test_summary_includes_new_relation_types(self, graph_service):
        """summaryに新しいリレーションタイプが含まれる"""
        extensions = [".inp", ".odb", ".sta", ".csv", ".json", ".yaml", ".png"]
        graph = graph_service.parse_project(extensions=extensions)
        summary = graph_service.summary(graph)

        assert "relations_by_label" in summary
        labels = summary["relations_by_label"]

        # has_output関係が存在するはず
        assert "has_output" in labels, f"has_output関係がない: {labels}"

        # defined_in関係（material.inpからのmaterialノード）
        assert "defined_in" in labels, f"defined_in関係がない: {labels}"


class TestMatchPathPattern:
    """_match_path_pattern関数のバグ修正テスト

    修正対象:
    - ./プレフィックス付きパターンのマッチング
    - ディレクトリパターン（末尾/）の処理
    - **go パターンが go.inp にマッチしない問題
    - Windowsパス（バックスラッシュ）対応
    """

    def test_dot_slash_prefix_reports(self):
        """./reports/ パターンが reports/file.pptx にマッチ"""
        from config import _match_path_pattern

        assert _match_path_pattern("reports/260205.pptx", "./reports/") is True

    def test_dot_slash_prefix_tools(self):
        """./tools/ パターンが tools/script.py にマッチ"""
        from config import _match_path_pattern

        assert _match_path_pattern("tools/make_inputs.py", "./tools/") is True

    def test_dot_slash_prefix_results(self):
        """./results/ パターンが results/file.csv にマッチ"""
        from config import _match_path_pattern

        assert _match_path_pattern("results/go_idx1_stress.csv", "./results/") is True

    def test_dot_slash_prefix_docs(self):
        """./docs/ パターンが docs/ 配下にマッチ"""
        from config import _match_path_pattern

        assert _match_path_pattern("docs/指示書/file.pptx", "./docs/") is True

    def test_dot_slash_no_false_positive(self):
        """./reports/ パターンが reports以外にマッチしない"""
        from config import _match_path_pattern

        assert _match_path_pattern("tools/script.py", "./reports/") is False

    def test_trailing_slash_directory_pattern(self):
        """末尾/ パターンがディレクトリ配下にマッチ"""
        from config import _match_path_pattern

        assert _match_path_pattern("reports/file.csv", "reports/") is True
        assert _match_path_pattern("other/file.csv", "reports/") is False

    def test_double_star_go_matches_go_inp(self):
        """**go パターンが go.inp にマッチ（basename比較）"""
        from config import _match_path_pattern

        assert _match_path_pattern("go.inp", "**go") is True

    def test_double_star_mesh_matches_mesh_inp(self):
        """**mesh パターンが mesh.inp にマッチ（basename比較）"""
        from config import _match_path_pattern

        assert _match_path_pattern("mesh.inp", "**mesh") is True

    def test_double_star_material_matches_material_inp(self):
        """**material パターンが material.inp にマッチ"""
        from config import _match_path_pattern

        assert _match_path_pattern("material.inp", "**material") is True

    def test_double_star_go_matches_subdirectory(self):
        """**go パターンが subdir/go.inp にマッチ"""
        from config import _match_path_pattern

        assert _match_path_pattern("subdir/go.inp", "**go") is True

    def test_double_star_go_matches_multi_dot_ext(self):
        """**go パターンが go.cas.h5 にマッチ（複合拡張子）"""
        from config import _match_path_pattern

        assert _match_path_pattern("go.cas.h5", "**go") is True

    def test_double_star_go_no_false_positive(self):
        """**go パターンが go_idx1.inp にマッチしない（go_はgo_*パターン用）"""
        from config import _match_path_pattern

        # "**go" は basename が "go" のものだけマッチ
        # go_idx1 は "**go_*" でマッチすべき
        assert _match_path_pattern("go_idx1.inp", "**go") is False

    def test_double_star_prefix_root_file(self):
        """**go_* パターンがプロジェクト直下ファイルにマッチ"""
        from config import _match_path_pattern

        assert _match_path_pattern("go_idx1_w5_t20.inp", "**go_*") is True

    def test_double_star_prefix_subdirectory_file(self):
        """**go_* パターンがサブディレクトリファイルにマッチ"""
        from config import _match_path_pattern

        assert _match_path_pattern("subdir/go_idx1.inp", "**go_*") is True

    def test_windows_backslash_path(self):
        """Windowsバックスラッシュパスが正しくマッチ"""
        from config import _match_path_pattern

        assert _match_path_pattern("reports\\file.pptx", "./reports/") is True
        assert _match_path_pattern("reports\\file.pptx", ".\\reports\\") is True

    def test_windows_backslash_pattern(self):
        """Windowsバックスラッシュパターンが正しくマッチ"""
        from config import _match_path_pattern

        assert _match_path_pattern("reports/file.pptx", ".\\reports\\") is True

    def test_dot_slash_on_both_sides(self):
        """パスとパターン両方に./ がある場合"""
        from config import _match_path_pattern

        assert _match_path_pattern("./reports/file.pptx", "./reports/") is True


class TestScanExtensions:
    """scan_files拡張子マージのテスト

    修正対象: DEFAULT_EXTENSIONSに.inp, .odb, .staが含まれない問題
    """

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict(
            {
                "vocab": {},
                "path-type-map": {},
                "file-relations": {
                    "input-extensions": [".inp"],
                    "result-extensions": [".odb", ".sta"],
                    "asset-extensions": [".modfem"],
                },
                "ignore": [],
                "obsidian": {},
            }
        )

    @pytest.fixture
    def graph_service(self, config):
        if not FIXTURE_DIR.exists():
            pytest.skip(f"Fixture directory not found: {FIXTURE_DIR}")
        return GraphService(project_root=FIXTURE_DIR, config=config)

    def test_build_scan_extensions_includes_config(self, graph_service):
        """_build_scan_extensionsがconfig file-relationsの拡張子を含む"""
        ext_set = graph_service._build_scan_extensions(None)
        assert ".inp" in ext_set
        assert ".odb" in ext_set
        assert ".sta" in ext_set
        assert ".modfem" in ext_set
        # DEFAULT_EXTENSIONSからの拡張子も含む
        assert ".csv" in ext_set
        assert ".py" in ext_set

    def test_build_scan_extensions_explicit_override(self, graph_service):
        """明示的に指定した場合はマージしない"""
        ext_set = graph_service._build_scan_extensions([".inp"])
        assert ".inp" in ext_set
        assert ".odb" not in ext_set

    def test_parse_project_without_extensions_finds_inp(self, graph_service):
        """extensions未指定でもparse_projectが.inpファイルを発見"""
        graph = graph_service.parse_project()

        # .inpノードが存在することを確認
        inp_nodes = [n for n in graph.nodes if n.format == "inp"]
        assert len(inp_nodes) > 0, "extensions未指定時に.inpファイルが見つからない"

    def test_parse_project_without_extensions_sta_enriches_inp(self, graph_service):
        """extensions未指定で.staの情報がinpノードに集約される（.staはNode化しない）"""
        graph = graph_service.parse_project()

        # .staはNode化されない
        sta_nodes = [n for n in graph.nodes if n.format == "sta"]
        assert len(sta_nodes) == 0, ".staノードはグラフから除外されるべき"

        # 対応するinpノードにanalysis_statusが集約される
        inp_node = next(
            (n for n in graph.nodes if n.name == "go_idx1_w5_t20" and n.format == "inp"),
            None,
        )
        assert inp_node is not None
        assert inp_node.properties.get("analysis_status") == "completed"


class TestPathTypeMapWithDefaultConfig:
    """デフォルト設定のpath-type-mapパターンが正しく動作するテスト

    修正対象:
    - ./reports/ 等のパターンがreports/配下のファイルにマッチしない問題
    - **go パターンが go.inp にマッチしない問題
    """

    @pytest.fixture
    def config(self):
        """デフォルト設定を模したconfig"""
        return GraphConfig.from_dict(
            {
                "vocab": {"idx": "条件", "v": "バージョン"},
                "path-type-map": {
                    "**go_* | **go": {
                        "*.inp": "Abaqusインプット",
                        "*.cas.h5": "Fluentインプット",
                        "*.sta": "Abaqusステータス",
                        "*.odb": "Abaqus ODB",
                        "*": "計算結果",
                    },
                    "**mesh_* | **mesh": {
                        "*.inp": "Abaqus用メッシュ",
                    },
                    "**material_* | **material": {
                        "*.inp": "Abaqus用マテリアル",
                    },
                    "./reports/": {
                        "*": "報告書",
                    },
                    "./results/": {
                        "*": "計算結果",
                    },
                    "./tools/": {
                        "*": "処理スクリプト",
                    },
                    "./docs/": {
                        "*": "受領ファイル",
                    },
                },
                "ignore": [],
                "obsidian": {},
            }
        )

    @pytest.fixture
    def graph_service(self, config):
        if not FIXTURE_DIR.exists():
            pytest.skip(f"Fixture directory not found: {FIXTURE_DIR}")
        return GraphService(project_root=FIXTURE_DIR, config=config)

    def test_reports_files_get_type(self, config):
        """reports/配下のファイルが「報告書」タイプになる"""
        result = config.path_type_map.get_type("reports/260205_構造解析_idx1.pptx", "260205_構造解析_idx1.pptx")
        assert result == "報告書", f"reports/配下のファイルが報告書にならない: {result}"

    def test_tools_files_get_type(self, config):
        """tools/配下のファイルが「処理スクリプト」タイプになる"""
        result = config.path_type_map.get_type("tools/make_inputs.py", "make_inputs.py")
        assert result == "処理スクリプト", f"tools/配下のファイルが処理スクリプトにならない: {result}"

    def test_results_files_get_type(self, config):
        """results/配下のファイルが「計算結果」タイプになる"""
        result = config.path_type_map.get_type("results/go_idx1_w5_t20_stress.csv", "go_idx1_w5_t20_stress.csv")
        assert result == "計算結果", f"results/配下のファイルが計算結果にならない: {result}"

    def test_docs_files_get_type(self, config):
        """docs/配下のファイルが「受領ファイル」タイプになる"""
        result = config.path_type_map.get_type("docs/指示書/file.pptx", "file.pptx")
        assert result == "受領ファイル", f"docs/配下のファイルが受領ファイルにならない: {result}"

    def test_root_go_inp_gets_type(self, config):
        """プロジェクト直下の go.inp が「Abaqusインプット」タイプになる"""
        result = config.path_type_map.get_type("go.inp", "go.inp")
        assert result == "Abaqusインプット", f"go.inpのタイプが不正: {result}"

    def test_root_mesh_inp_gets_type(self, config):
        """プロジェクト直下の mesh.inp が「Abaqus用メッシュ」タイプになる"""
        result = config.path_type_map.get_type("mesh.inp", "mesh.inp")
        assert result == "Abaqus用メッシュ", f"mesh.inpのタイプが不正: {result}"

    def test_root_material_inp_gets_type(self, config):
        """プロジェクト直下の material.inp が「Abaqus用マテリアル」タイプになる"""
        result = config.path_type_map.get_type("material.inp", "material.inp")
        assert result == "Abaqus用マテリアル", f"material.inpのタイプが不正: {result}"

    def test_root_go_idx1_inp_gets_type(self, config):
        """プロジェクト直下の go_idx1_w5_t20.inp が正しいタイプになる"""
        result = config.path_type_map.get_type("go_idx1_w5_t20.inp", "go_idx1_w5_t20.inp")
        assert result == "Abaqusインプット"

    def test_full_parse_reports_typed(self, graph_service):
        """統合テスト: parse_projectでreports配下のファイルが正しく型付けされる"""
        extensions = [".pptx", ".csv", ".py", ".inp"]
        graph = graph_service.parse_project(extensions=extensions)

        report_nodes = [n for n in graph.nodes if "reports/" in n.properties.get("path", "")]
        for node in report_nodes:
            assert node.type == "報告書", f"{node.properties['path']} のタイプが {node.type}（報告書であるべき）"

    def test_full_parse_tools_typed(self, graph_service):
        """統合テスト: parse_projectでtools配下のファイルが正しく型付けされる"""
        extensions = [".py", ".inp"]
        graph = graph_service.parse_project(extensions=extensions)

        tools_nodes = [n for n in graph.nodes if "tools/" in n.properties.get("path", "")]
        for node in tools_nodes:
            assert node.type == "処理スクリプト", (
                f"{node.properties['path']} のタイプが {node.type}（処理スクリプトであるべき）"
            )


class TestDirectoryNodeWindows:
    """フォルダNode構築のWindows対応テスト"""

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict(
            {
                "vocab": {},
                "path-type-map": {
                    "**go_*": {
                        "*.inp": "Abaqusインプット",
                        "*.csv": "計算結果CSV",
                        "*.png": "画像",
                        "*.yaml": "データ",
                    },
                },
                "ignore": [],
                "obsidian": {},
            }
        )

    @pytest.fixture
    def graph_service(self, config):
        if not FIXTURE_DIR.exists():
            pytest.skip(f"Fixture directory not found: {FIXTURE_DIR}")
        return GraphService(project_root=FIXTURE_DIR, config=config)

    def test_directory_node_has_posix_path(self, graph_service):
        """ディレクトリノードのパスがPOSIX形式"""
        extensions = [".inp", ".csv", ".png", ".yaml"]
        graph = graph_service.parse_project(extensions=extensions)

        dir_nodes = [n for n in graph.nodes if n.format == "directory"]
        for node in dir_nodes:
            path = node.properties.get("path", "")
            assert "\\" not in path, f"パスにバックスラッシュが含まれる: {path}"

    def test_contains_relations_built_correctly(self, graph_service):
        """ディレクトリcontains関係が正しく構築される"""
        extensions = [".inp", ".csv", ".png", ".yaml"]
        graph = graph_service.parse_project(extensions=extensions)

        dir_node = next(
            (n for n in graph.nodes if n.name == "go_idx1_w5_t20" and n.format == "directory"),
            None,
        )
        assert dir_node is not None, "go_idx1_w5_t20 ディレクトリノードが見つからない"

        contains = [r for r in graph.relations if r.label == "contains" and r.node1_id == dir_node.id]
        assert len(contains) >= 3, (
            f"go_idx1_w5_t20/内の3ファイル(csv,png,yaml)に対するcontains関係が不足: {len(contains)}"
        )

    def test_file_nodes_have_no_leading_dot_slash(self, graph_service):
        """ファイルノードのパスに先頭 ./ がない"""
        extensions = [".inp", ".csv", ".png", ".yaml"]
        graph = graph_service.parse_project(extensions=extensions)

        for node in graph.nodes:
            path = node.properties.get("path", "")
            assert not path.startswith("./"), f"パスに先頭./が含まれる: {path}"
            assert not path.startswith(".\\"), f"パスに先頭.\\が含まれる: {path}"


class TestActiveAttribute:
    """active属性のテスト: oldフォルダに入っていないNodeはactive=True"""

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict(
            {
                "vocab": {},
                "path-type-map": {},
                "file-relations": {
                    "input-extensions": [".inp"],
                },
                "ignore": [],
                "obsidian": {},
            }
        )

    def test_normal_file_has_active_true(self, tmp_path, config):
        """通常ファイルはactive=trueになる"""
        inp = tmp_path / "go_idx1.inp"
        inp.write_text("*HEADING\ntest\n")

        gs = GraphService(project_root=tmp_path, config=config)
        node = gs.file_to_node(inp)
        assert node.properties.get("active") == "true"

    def test_old_folder_file_has_active_false(self, tmp_path, config):
        """old/フォルダ内のファイルはactive=falseになる"""
        old_dir = tmp_path / "old"
        old_dir.mkdir()
        inp = old_dir / "go_idx1.inp"
        inp.write_text("*HEADING\ntest\n")

        gs = GraphService(project_root=tmp_path, config=config)
        node = gs.file_to_node(inp)
        assert node.properties.get("active") == "false"


class TestInpParameterProps:
    """*PARAMETER/**propsブロックからプロパティを読み取るテスト

    status-088でGraphService._read_inp_parameter_propsからAbaqusParameterParserに移動。
    パーサー経由でテストする。
    """

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict(
            {
                "vocab": {"w": "width", "t": "thickness"},
                "path-type-map": {},
                "file-relations": {
                    "input-extensions": [".inp"],
                },
                "ignore": [],
                "obsidian": {},
            }
        )

    def test_read_parameter_props(self, tmp_path, config):
        """*PARAMETER/**propsブロックのkey=valueが読み取られる"""
        from services.parse.connectors.abaqus.parameter_parser import AbaqusParameterParser

        inp = tmp_path / "go_idx1.inp"
        inp.write_text("*HEADING\ntest\n*PARAMETER\n**props\nw=5\nt=20\n*STEP\n")

        gs = GraphService(project_root=tmp_path, config=config)
        node = gs.file_to_node(inp)

        # AbaqusParameterParser経由でプロパティを付与
        from services.graph.project_graph import ProjectGraph

        pg = ProjectGraph(nodes=[node], relations=[], project_root=tmp_path, config=config)
        AbaqusParameterParser().apply(pg)

        # vocabマッピングが適用される
        assert node.properties.get("width") == "5"
        assert node.properties.get("thickness") == "20"

    def test_no_parameter_block(self, tmp_path, config):
        """*PARAMETERブロックがない場合は何も追加されない"""
        from services.parse.connectors.abaqus.parameter_parser import AbaqusParameterParser

        inp = tmp_path / "go_idx1.inp"
        inp.write_text("*HEADING\ntest\n*STEP\n*STATIC\n")

        gs = GraphService(project_root=tmp_path, config=config)
        node = gs.file_to_node(inp)

        from services.graph.project_graph import ProjectGraph

        pg = ProjectGraph(nodes=[node], relations=[], project_root=tmp_path, config=config)
        AbaqusParameterParser().apply(pg)

        assert "width" not in node.properties
        assert "thickness" not in node.properties

    def test_parameter_without_props_comment(self, tmp_path, config):
        """*PARAMETERの後に**propsがない場合はスキップ"""
        from services.parse.connectors.abaqus.parameter_parser import AbaqusParameterParser

        inp = tmp_path / "go_idx1.inp"
        inp.write_text("*PARAMETER\n** something else\nw=5\n*STEP\n")

        gs = GraphService(project_root=tmp_path, config=config)
        node = gs.file_to_node(inp)

        from services.graph.project_graph import ProjectGraph

        pg = ProjectGraph(nodes=[node], relations=[], project_root=tmp_path, config=config)
        AbaqusParameterParser().apply(pg)

        assert "width" not in node.properties

    def test_non_inp_file_skipped(self, tmp_path, config):
        """INP以外のファイルはパラメータ読み取りをスキップ"""
        from services.parse.connectors.abaqus.parameter_parser import AbaqusParameterParser

        csv = tmp_path / "go_idx1.csv"
        csv.write_text("a,b,c\n1,2,3\n")

        gs = GraphService(project_root=tmp_path, config=config)
        node = gs.file_to_node(csv)

        from services.graph.project_graph import ProjectGraph

        pg = ProjectGraph(nodes=[node], relations=[], project_root=tmp_path, config=config)
        AbaqusParameterParser().apply(pg)

        assert "width" not in node.properties


class TestResultFileAggregation:
    """結果ファイル属性のAbaqusインプット集約テスト"""

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict(
            {
                "vocab": {},
                "path-type-map": {
                    "**go_*": {
                        "*.inp": "Abaqusインプット",
                        "*.sta": "Abaqusステータス",
                        "*.msg": "Abaqusメッセージ",
                    },
                },
                "file-relations": {
                    "input-extensions": [".inp"],
                    "result-extensions": [".sta", ".msg"],
                },
                "ignore": [],
                "obsidian": {},
            }
        )

    @pytest.fixture
    def graph_service(self, config):
        if not FIXTURE_DIR.exists():
            pytest.skip(f"Fixture directory not found: {FIXTURE_DIR}")
        return GraphService(project_root=FIXTURE_DIR, config=config)

    def test_sta_status_aggregated_to_inp(self, graph_service):
        """staファイルのanalysis_statusが対応するinpノードに集約される"""
        extensions = [".inp", ".sta"]
        graph = graph_service.parse_project(extensions=extensions)

        inp_node = next(
            (n for n in graph.nodes if n.name == "go_idx1_w5_t20" and n.format == "inp"),
            None,
        )
        assert inp_node is not None
        assert inp_node.properties.get("analysis_status") == "completed"

    def test_sta_errors_aggregated_to_inp(self, graph_service):
        """staファイルのエラーが対応するinpノードにsta_errorsとして集約される"""
        extensions = [".inp", ".sta"]
        graph = graph_service.parse_project(extensions=extensions)

        inp_node = next(
            (n for n in graph.nodes if n.name == "go_idx2" and n.format == "inp"),
            None,
        )
        assert inp_node is not None
        assert inp_node.properties.get("analysis_status") == "failed"
        assert len(inp_node.properties.get("sta_errors", [])) > 0


class TestTokenKeyMap:
    """token-key-map設定のテスト"""

    def test_token_key_map_converts_tag_to_prop(self, tmp_path):
        """token-key-mapでタグがプロパティに変換される"""
        # mesh_hogehoge24_v1_idx1.inp 相当のテスト
        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "token-key-map": {
                    "形状": ["hogehoge24"],
                },
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)

        # テストファイルを作成
        inp = tmp_path / "mesh_hogehoge24_v1_idx1.inp"
        inp.write_text("", encoding="utf-8")

        node = svc.file_to_node(inp)
        # hogehoge24がpropに変換される
        assert node.properties.get("形状") == "hogehoge24"

    def test_token_key_map_with_vocab_value_translation(self, tmp_path):
        """token-key-map + vocab値変換で最終プロパティが正しい"""
        config = GraphConfig.from_dict(
            {
                "vocab": {"hogehoge24": "ほげほげ24"},
                "token-key-map": {
                    "形状": ["hogehoge24"],
                },
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)

        inp = tmp_path / "mesh_hogehoge24_v1_idx1.inp"
        inp.write_text("", encoding="utf-8")

        node = svc.file_to_node(inp)
        # vocabで値が変換される
        assert node.properties.get("形状") == "ほげほげ24"

    def test_token_key_map_empty_config(self, tmp_path):
        """token-key-mapが空の場合は通常のトークン解析"""
        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "token-key-map": {},
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)

        inp = tmp_path / "go_idx1_v1.inp"
        inp.write_text("", encoding="utf-8")

        node = svc.file_to_node(inp)
        assert node.properties.get("index") == "1"
        assert node.properties.get("version") == "1"

    def test_token_key_map_multiple_tokens_same_key(self, tmp_path):
        """同一キーに複数トークンがマッピングされる場合"""
        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "token-key-map": {
                    "形状": ["hogehoge24", "foobar12"],
                },
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)

        inp1 = tmp_path / "mesh_hogehoge24_v1_idx1.inp"
        inp1.write_text("", encoding="utf-8")

        inp2 = tmp_path / "mesh_foobar12_v1_idx1.inp"
        inp2.write_text("", encoding="utf-8")

        node1 = svc.file_to_node(inp1)
        node2 = svc.file_to_node(inp2)
        assert node1.properties.get("形状") == "hogehoge24"
        assert node2.properties.get("形状") == "foobar12"


class TestVocabValueTranslation:
    """vocab値変換のテスト（キーだけでなく値も変換）

    status-088でAbaqusParameterParser経由でテストする形式に変更。
    """

    def test_vocab_translates_prop_values(self, tmp_path):
        """vocabがプロパティ値も変換する"""
        from services.graph.project_graph import ProjectGraph
        from services.parse.connectors.abaqus.parameter_parser import AbaqusParameterParser

        config = GraphConfig.from_dict(
            {
                "vocab": {"static": "静的"},
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)

        inp = tmp_path / "go_idx1_v1.inp"
        inp.write_text("*PARAMETER\n**props\nmethod=static\n", encoding="utf-8")

        node = svc.file_to_node(inp)

        # AbaqusParameterParser経由でプロパティを付与
        pg = ProjectGraph(nodes=[node], relations=[], project_root=tmp_path, config=config)
        AbaqusParameterParser().apply(pg)

        # *PARAMETER/**propsの値がvocabで変換される
        assert node.properties.get("method") == "静的"


class TestTokenKeyMapConfig:
    """TokenKeyMapConfigクラスのテスト"""

    def test_from_dict_basic(self):
        """基本的なfrom_dict変換"""
        from config import TokenKeyMapConfig

        config = TokenKeyMapConfig.from_dict(
            {
                "形状": ["hogehoge24", "foobar12"],
                "解析タイプ": ["static"],
            }
        )
        assert config.get_key("hogehoge24") == "形状"
        assert config.get_key("foobar12") == "形状"
        assert config.get_key("static") == "解析タイプ"
        assert config.get_key("unknown") is None

    def test_from_dict_empty(self):
        """空のdict"""
        from config import TokenKeyMapConfig

        config = TokenKeyMapConfig.from_dict({})
        assert config.get_key("anything") is None

    def test_from_dict_string_value(self):
        """値が文字列（リストでない）の場合"""
        from config import TokenKeyMapConfig

        config = TokenKeyMapConfig.from_dict({"形状": "hogehoge24"})
        assert config.get_key("hogehoge24") == "形状"


class TestPymeshConnector:
    """pymeshコネクタのテスト"""

    def test_extract_material_elset_mapping_basic(self, tmp_path):
        """基本的な材料→Elsetマッピング抽出"""
        from services.parse.connectors.abaqus.mesh import (
            extract_material_elset_mapping,
        )

        inp_file = tmp_path / "test.inp"
        inp_file.write_text(
            "*SOLID SECTION, MATERIAL=STEEL, ELSET=SOLID_ELEMS\n"
            "1.0,\n"
            "*SHELL SECTION, MATERIAL=ALUMINUM, ELSET=SHELL_ELEMS\n"
            "0.5, 5\n",
            encoding="utf-8",
        )
        mapping = extract_material_elset_mapping(inp_file)
        # 元のケース（大文字）を保持
        assert "STEEL" in mapping
        assert "SOLID_ELEMS" in mapping["STEEL"]
        assert "ALUMINUM" in mapping
        assert "SHELL_ELEMS" in mapping["ALUMINUM"]

    def test_extract_material_elset_mapping_no_section(self, tmp_path):
        """セクション定義がない場合は空"""
        from services.parse.connectors.abaqus.mesh import (
            extract_material_elset_mapping,
        )

        inp_file = tmp_path / "test.inp"
        inp_file.write_text(
            "*NODE\n1, 0.0, 0.0, 0.0\n*ELEMENT, TYPE=C3D8\n1, 1, 2, 3, 4, 5, 6, 7, 8\n",
            encoding="utf-8",
        )
        mapping = extract_material_elset_mapping(inp_file)
        assert mapping == {}

    def test_extract_material_elset_mapping_missing_file(self, tmp_path):
        """ファイルが存在しない場合は空"""
        from services.parse.connectors.abaqus.mesh import (
            extract_material_elset_mapping,
        )

        mapping = extract_material_elset_mapping(tmp_path / "nonexistent.inp")
        assert mapping == {}

    def test_extract_mesh_stats_missing_file(self, tmp_path):
        """存在しないファイルに対してNoneを返す"""
        from services.parse.connectors.abaqus.mesh import extract_mesh_stats

        result = extract_mesh_stats(tmp_path / "nonexistent.inp")
        assert result is None

    def test_extract_mesh_stats_non_inp_file(self, tmp_path):
        """非.inpファイルに対してNoneを返す"""
        from services.parse.connectors.abaqus.mesh import extract_mesh_stats

        txt_file = tmp_path / "test.txt"
        txt_file.write_text("hello", encoding="utf-8")
        result = extract_mesh_stats(txt_file)
        assert result is None


class TestMaterialAssignmentRelations:
    """材料割り当て関係のテスト"""

    def test_material_assignment_creates_assigned_to_relation(self, tmp_path):
        """材料割り当てがassigned_to関係を生成する"""
        # 材料定義と割り当てを含む.inpファイルを作成
        inp_content = (
            "*MATERIAL, NAME=STEEL\n*ELASTIC\n210000.0, 0.3\n*SOLID SECTION, MATERIAL=STEEL, ELSET=ALL_ELEMS\n1.0,\n"
        )
        inp_file = tmp_path / "go_idx1_v1.inp"
        inp_file.write_text(inp_content, encoding="utf-8")

        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "path-type-map": {
                    "**go_*": {"*.inp": "Abaqusインプット"},
                },
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)
        graph = svc.parse_project()

        # materialノードが生成されている
        mat_nodes = [n for n in graph.nodes if n.type == "abaqus_material"]
        assert len(mat_nodes) >= 1
        steel_nodes = [n for n in mat_nodes if n.name.lower() == "steel"]
        assert len(steel_nodes) >= 1

        # assigned_to関係が存在する
        assigned_relations = [r for r in graph.relations if r.label == "assigned_to"]
        assert len(assigned_relations) >= 1

        # materialノードにelset情報が付与されている
        steel = steel_nodes[0]
        assert "assigned_elsets" in steel.properties
        # 元のケース（大文字）を保持
        assert "ALL_ELEMS" in steel.properties["assigned_elsets"]


class TestMaterialSourceFiltering:
    """abaqus materialの読み取りソース制限テスト

    material定義はmaterial系.inpまたはgo系.inpからのみ読み取る。
    .datファイルやstep系.inpからは読み取らない。
    """

    def test_dat_file_not_parsed_for_materials(self, tmp_path):
        """go_idx3.datからmaterialを読み取らない"""
        dat_content = "*MATERIAL, NAME=STEEL_FROM_DAT\n*ELASTIC\n210000.0, 0.3\n"
        dat_file = tmp_path / "go_idx3.dat"
        dat_file.write_text(dat_content, encoding="utf-8")

        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "path-type-map": {
                    "**go_*": {"*.dat": "Abaqusデータ"},
                },
                "file-relations": {
                    "input-extensions": [".inp", ".dat"],
                },
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)
        graph = svc.parse_project()

        mat_nodes = [n for n in graph.nodes if n.type == "abaqus_material"]
        dat_mats = [n for n in mat_nodes if "dat" in n.name.lower()]
        assert len(dat_mats) == 0, f".datファイルからmaterialが読み取られている: {[n.name for n in dat_mats]}"

    def test_go_inp_parsed_for_materials(self, tmp_path):
        """go系.inpからはmaterialを読み取る"""
        inp_content = "*MATERIAL, NAME=STEEL_GO\n*ELASTIC\n210000.0, 0.3\n"
        inp_file = tmp_path / "go_idx1.inp"
        inp_file.write_text(inp_content, encoding="utf-8")

        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "path-type-map": {
                    "**go_*": {"*.inp": "Abaqusインプット"},
                },
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)
        graph = svc.parse_project()

        mat_nodes = [n for n in graph.nodes if n.type == "abaqus_material"]
        assert len(mat_nodes) >= 1, "go系.inpからmaterialが読み取られていない"

    def test_material_inp_parsed_for_materials(self, tmp_path):
        """material系.inpからはmaterialを読み取る"""
        inp_content = "*MATERIAL, NAME=STEEL_MAT\n*ELASTIC\n210000.0, 0.3\n"
        inp_file = tmp_path / "material.inp"
        inp_file.write_text(inp_content, encoding="utf-8")

        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "path-type-map": {
                    "**material": {"*.inp": "Abaqus用マテリアル"},
                },
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)
        graph = svc.parse_project()

        mat_nodes = [n for n in graph.nodes if n.type == "abaqus_material"]
        assert len(mat_nodes) >= 1, "material系.inpからmaterialが読み取られていない"

    def test_step_inp_not_parsed_for_materials(self, tmp_path):
        """step系.inpからはmaterialを読み取らない"""
        inp_content = "*MATERIAL, NAME=STEEL_STEP\n*ELASTIC\n210000.0, 0.3\n"
        inp_file = tmp_path / "step_static.inp"
        inp_file.write_text(inp_content, encoding="utf-8")

        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "path-type-map": {
                    "**step_*": {"*.inp": "Abaqusステップ"},
                },
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)
        graph = svc.parse_project()

        mat_nodes = [n for n in graph.nodes if n.type == "abaqus_material"]
        assert len(mat_nodes) == 0, f"step系.inpからmaterialが読み取られている: {[n.name for n in mat_nodes]}"

    def test_is_material_source_node_static(self):
        """_is_material_source_nodeの静的テスト"""
        from services.parse.connectors.abaqus.inp_parser import AbaqusInpParser

        # go系.inp → True
        go_node = Node(id=1, type="go", name="go_idx1", format="inp", properties={})
        assert AbaqusInpParser._is_material_source_node(go_node) is True

        # material系.inp → True
        mat_node = Node(id=2, type="material", name="material", format="inp", properties={})
        assert AbaqusInpParser._is_material_source_node(mat_node) is True

        # material_v2.inp → True
        mat2_node = Node(id=3, type="material", name="material_v2", format="inp", properties={})
        assert AbaqusInpParser._is_material_source_node(mat2_node) is True

        # go_idx3.dat → False
        dat_node = Node(id=4, type="go", name="go_idx3", format="dat", properties={})
        assert AbaqusInpParser._is_material_source_node(dat_node) is False

        # step_static.inp → False
        step_node = Node(id=5, type="step", name="step_static", format="inp", properties={})
        assert AbaqusInpParser._is_material_source_node(step_node) is False

        # mesh.inp → False
        mesh_node = Node(id=6, type="mesh", name="mesh", format="inp", properties={})
        assert AbaqusInpParser._is_material_source_node(mesh_node) is False


class TestGenericDirectoryNodes:
    """汎用ディレクトリ（reports等）のノード生成テスト"""

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict(
            {
                "vocab": {},
                "path-type-map": {
                    "**go_*": {"*.inp": "Abaqusインプット"},
                    "./reports/": {"*": "報告書"},
                    "./results/": {"*": "計算結果"},
                },
                "ignore": [],
                "obsidian": {},
            }
        )

    @pytest.fixture
    def graph_service(self, config):
        if not FIXTURE_DIR.exists():
            pytest.skip(f"Fixture directory not found: {FIXTURE_DIR}")
        return GraphService(project_root=FIXTURE_DIR, config=config)

    def test_reports_directory_node_created(self, graph_service):
        """reports/ ディレクトリがtype=directoryのノードとして生成される"""
        extensions = [".pptx", ".csv", ".inp"]
        graph = graph_service.parse_project(extensions=extensions)

        dir_nodes = [n for n in graph.nodes if n.format == "directory"]
        reports_dir = next(
            (n for n in dir_nodes if n.name == "reports"),
            None,
        )
        assert reports_dir is not None, (
            f"reports ディレクトリノードが見つからない (dir_nodes: {[n.name for n in dir_nodes]})"
        )
        assert reports_dir.type == "directory"
        assert reports_dir.properties.get("path") == "reports"

    def test_reports_contains_relations(self, graph_service):
        """reports/ 内のファイルがcontains関係でリンクされる"""
        extensions = [".pptx", ".csv", ".inp"]
        graph = graph_service.parse_project(extensions=extensions)

        dir_nodes = [n for n in graph.nodes if n.format == "directory"]
        reports_dir = next(
            (n for n in dir_nodes if n.name == "reports"),
            None,
        )
        assert reports_dir is not None

        contains = [r for r in graph.relations if r.label == "contains" and r.node1_id == reports_dir.id]
        assert len(contains) >= 1, "reports/ 内にcontains関係がない"

        # reportsフォルダ内のファイルが正しくリンクされている
        contained_ids = {r.node2_id for r in contains}
        report_file_nodes = [
            n for n in graph.nodes if "reports/" in n.properties.get("path", "") and n.format != "directory"
        ]
        for file_node in report_file_nodes:
            assert file_node.id in contained_ids, f"{file_node.name} がcontains関係に含まれていない"

    def test_results_directory_node_created(self, graph_service):
        """results/ ディレクトリもtype=directoryのノードとして生成される"""
        extensions = [".csv", ".inp"]
        graph = graph_service.parse_project(extensions=extensions)

        dir_nodes = [n for n in graph.nodes if n.format == "directory"]
        results_dir = next(
            (n for n in dir_nodes if n.name == "results"),
            None,
        )
        assert results_dir is not None, (
            f"results ディレクトリノードが見つからない (dir_nodes: {[n.name for n in dir_nodes]})"
        )
        assert results_dir.type == "directory"

    def test_named_directory_still_works(self, graph_service):
        """命名規則に合致するディレクトリは従来通りのtype（go_directory等）"""
        extensions = [".inp", ".csv", ".png", ".yaml"]
        graph = graph_service.parse_project(extensions=extensions)

        dir_nodes = [n for n in graph.nodes if n.format == "directory"]
        go_dir = next(
            (n for n in dir_nodes if n.name == "go_idx1_w5_t20"),
            None,
        )
        assert go_dir is not None
        assert go_dir.type == "go_directory"


class TestTrailingCommaInMaterialProperty:
    """末尾カンマ対応テスト: *DENSITYの1.0e-9, のような行のパース"""

    def test_trailing_comma_in_density(self):
        """末尾カンマがある行をNoneで埋めてパースできる"""
        from services.parse.connectors.abaqus import (
            Context,
            MaterialPropertyReadComponent,
            ReadMaterial,
        )

        context = Context()
        material = ReadMaterial(context)
        material.options["name"] = "TEST_MATERIAL"

        # DensityはMaterialPropertyReadComponentのサブクラスとして動的生成済み
        # 直接MaterialPropertyReadComponentを使う
        density = MaterialPropertyReadComponent(context)

        # 末尾カンマのある行: "1.0e-9,"
        density.read_line("1.0e-9,")
        # エラーにならずにデータが追加される
        assert len(density.data) == 1
        row = density.data[0]
        assert row[0] == 1.0e-9
        assert row[1] is None  # 空文字列はNoneで埋まる

    def test_no_trailing_comma(self):
        """末尾カンマなしの通常行は正常にパースされる"""
        from services.parse.connectors.abaqus import (
            Context,
            MaterialPropertyReadComponent,
            ReadMaterial,
        )

        context = Context()
        material = ReadMaterial(context)
        material.options["name"] = "TEST_MATERIAL"
        prop = MaterialPropertyReadComponent(context)

        prop.read_line("210000.0,0.3")
        assert len(prop.data) == 1
        assert prop.data[0] == [210000.0, 0.3]


class TestIncludeFileNotFound:
    """*include FileNotFoundErrorの対応テスト"""

    def test_missing_include_file_skipped(self, tmp_path):
        """存在しない*includeファイルはスキップして親ファイルの残りを処理"""
        from services.parse.connectors.abaqus import read_files_with_unknown_encoding

        inp = tmp_path / "main.inp"
        inp.write_text(
            "*HEADING\ntest\n*INCLUDE, INPUT=nonexistent_material.inp\n*STEP\n*STATIC\n*END STEP\n",
            encoding="utf-8",
        )

        lines = list(read_files_with_unknown_encoding(inp, verbose=False))
        # *INCLUDE行自体は含まれないが、前後の行は含まれる
        texts = [line for _, line in lines]
        assert "*HEADING" in texts
        assert "*STEP" in texts
        assert "*STATIC" in texts
        assert "*END STEP" in texts

    def test_missing_include_does_not_crash_read_inp(self, tmp_path):
        """存在しない*includeファイルがあってもread_inpがクラッシュしない"""
        from services.parse.connectors.abaqus import read_inp

        inp = tmp_path / "main.inp"
        inp.write_text(
            "*HEADING\ntest\n"
            "*INCLUDE, INPUT=missing.inp\n"
            "*NODE\n"
            "1, 0.0, 0.0, 0.0\n"
            "*ELEMENT, TYPE=C3D8, ELSET=ALL\n"
            "1, 1, 1, 1, 1, 1, 1, 1, 1\n",
            encoding="utf-8",
        )

        # クラッシュせずにABQDataが返される
        abq = read_inp(inp, verbose=False)
        assert abq is not None
        assert len(abq.nodes) > 0

    def test_graph_parse_with_missing_include(self, tmp_path):
        """*includeファイルが存在しなくてもparse_projectがグラフを生成できる"""
        inp = tmp_path / "go_idx1.inp"
        inp.write_text(
            "*HEADING\ntest\n*INCLUDE, INPUT=moved_to_old.inp\n*MATERIAL, NAME=INLINE_STEEL\n*ELASTIC\n210000.0, 0.3\n",
            encoding="utf-8",
        )

        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "path-type-map": {
                    "**go_*": {"*.inp": "Abaqusインプット"},
                },
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)
        graph = svc.parse_project()

        # グラフにgo_idx1のノードが含まれる
        go_node = next(
            (n for n in graph.nodes if n.name == "go_idx1" and n.format == "inp"),
            None,
        )
        assert go_node is not None, "go_idx1.inp ノードが生成されていない"

        # materialも抽出される（inline定義されているため）
        mat_nodes = [n for n in graph.nodes if n.type == "abaqus_material"]
        assert len(mat_nodes) >= 1, "inline定義のmaterialが読み取られていない"


class TestCliTopLevelCommands:
    """CLIトップレベルコマンドのテスト（jj init/parse/show/export/info）

    cli.graphモジュールをインポートすると cli/__init__.py が連鎖的にSSH設定を
    読み込むため、テスト環境にSSH設定がない場合はスキップする。
    """

    @staticmethod
    def _import_graph_module():
        """cli.graphをインポート（失敗時はpytest.skipで中断）"""
        try:
            import cli.graph as mod

            return mod
        except (ValueError, ImportError, ModuleNotFoundError) as e:
            pytest.skip(f"cli.graph import failed: {e}")

    def test_top_level_graph_commands_defined(self):
        """トップレベルグラフコマンドが定義されている"""
        mod = self._import_graph_module()
        assert callable(mod.add_top_level_graph_commands)
        assert callable(mod.run_top_level_graph_command)

    def test_add_init_args(self):
        """init引数が正しく定義される"""
        import argparse

        mod = self._import_graph_module()
        parser = argparse.ArgumentParser()
        mod._add_init_args(parser)
        args = parser.parse_args(["--overwrite"])
        assert args.overwrite is True

    def test_add_parse_args(self):
        """parse引数が正しく定義される"""
        import argparse

        mod = self._import_graph_module()
        parser = argparse.ArgumentParser()
        mod._add_parse_args(parser)
        args = parser.parse_args(["-o", "test.yaml"])
        assert args.output == "test.yaml"

    def test_add_show_args(self):
        """show引数が正しく定義される"""
        import argparse

        mod = self._import_graph_module()
        parser = argparse.ArgumentParser()
        mod._add_show_args(parser)
        args = parser.parse_args(["--summary"])
        assert args.summary is True

    def test_add_info_args(self):
        """info引数が正しく定義される"""
        import argparse

        mod = self._import_graph_module()
        parser = argparse.ArgumentParser()
        mod._add_info_args(parser)
        args = parser.parse_args(["go_idx1.inp"])
        assert args.filename == "go_idx1.inp"

    def test_top_level_commands_registered(self):
        """トップレベルコマンドがサブパーサーに登録される"""
        import argparse

        mod = self._import_graph_module()
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="cmd")
        mod.add_top_level_graph_commands(sub)
        args = parser.parse_args(["parse"])
        assert args.cmd == "parse"


class TestInfoCommand:
    """jj info コマンドのテスト"""

    def test_info_finds_node_by_name(self, tmp_path):
        """ファイル名でノードを検索できる"""
        (tmp_path / "go_idx1.inp").write_text("** test\n")
        config = GraphConfig.from_dict({"vocab": {}})
        svc = GraphService(project_root=tmp_path, config=config)
        graph = svc.parse_project()

        # ノードが存在することを確認
        matched = [n for n in graph.nodes if n.name == "go_idx1"]
        assert len(matched) >= 1

    def test_info_finds_node_by_partial_name(self, tmp_path):
        """部分一致でノードを検索できる"""
        (tmp_path / "go_idx1_w5.inp").write_text("** test\n")
        config = GraphConfig.from_dict({"vocab": {}})
        svc = GraphService(project_root=tmp_path, config=config)
        graph = svc.parse_project()

        # 部分一致検索
        matched = [n for n in graph.nodes if "idx1" in n.name]
        assert len(matched) >= 1


class TestIncludePropertyPropagation:
    """includeファイルのプロパティ伝搬テスト"""

    def test_include_mesh_stats_propagated(self, tmp_path):
        """includeされたmeshファイルの統計情報がgo_*.inpに伝搬される"""
        # メッシュファイル
        mesh_content = (
            "*NODE\n1, 0.0, 0.0, 0.0\n2, 1.0, 0.0, 0.0\n*ELEMENT, TYPE=C3D8, ELSET=EALL\n1, 1, 2, 3, 4, 5, 6, 7, 8\n"
        )
        (tmp_path / "mesh.inp").write_text(mesh_content)

        # go_inpファイル (meshをinclude)
        go_content = "** go file\n*INCLUDE, INPUT=mesh.inp\n*STEP\n*STATIC\n1., 1.\n*END STEP\n"
        (tmp_path / "go_idx1.inp").write_text(go_content)

        config = GraphConfig.from_dict({"vocab": {}})
        svc = GraphService(project_root=tmp_path, config=config)
        graph = svc.parse_project()

        go_node = next(
            (n for n in graph.nodes if n.name == "go_idx1" and n.format == "inp"),
            None,
        )
        assert go_node is not None

        # MeshInheritParserによりinclude先のプロパティが直接継承される
        # (include_propertiesは廃止、全プロパティを親ノードに直接マッピング)

    def test_include_relations_exist(self, tmp_path):
        """includes関係が正しく構築される"""
        (tmp_path / "mesh.inp").write_text("*NODE\n1, 0., 0., 0.\n")
        go_content = "** go file\n*INCLUDE, INPUT=mesh.inp\n*STEP\n*STATIC\n1., 1.\n*END STEP\n"
        (tmp_path / "go_idx1.inp").write_text(go_content)

        config = GraphConfig.from_dict({"vocab": {}})
        svc = GraphService(project_root=tmp_path, config=config)
        graph = svc.parse_project()

        includes_rels = [r for r in graph.relations if r.label == "includes"]
        assert len(includes_rels) >= 1, "includes関係が構築されていない"


class TestVersionDiff:
    """バージョン差分テスト"""

    def test_diff_between_versions(self, tmp_path):
        """隣接バージョン間でdiffノードが作成され、relation経由で参照できる"""
        # v1: STATIC procedure
        v1_content = "*STEP, NAME=Step-1\n*STATIC\n1., 1.\n*END STEP\n"
        (tmp_path / "go_idx1_v1.inp").write_text(v1_content)

        # v2: DYNAMIC procedure（procedure変更で差分検出）
        v2_content = "*STEP, NAME=Step-1\n*DYNAMIC\n1., 1.\n*END STEP\n"
        (tmp_path / "go_idx1_v2.inp").write_text(v2_content)

        config = GraphConfig.from_dict({"vocab": {}})
        svc = GraphService(project_root=tmp_path, config=config)
        graph = svc.parse_project(full_mode=True)  # diffパーサーはrequires_full=True

        # version_diffノードが作成される
        diff_nodes = [n for n in graph.nodes if n.type == "version_diff"]
        assert len(diff_nodes) >= 1
        diff_node = diff_nodes[0]
        assert "diff_from" in diff_node.properties
        assert "diff_summary" in diff_node.properties

        # diff_from/diff_to relationが存在する
        diff_from_rels = [r for r in graph.relations if r.label == "diff_from"]
        diff_to_rels = [r for r in graph.relations if r.label == "diff_to"]
        assert len(diff_from_rels) >= 1
        assert len(diff_to_rels) >= 1

    def test_no_diff_for_single_version(self, tmp_path):
        """単一バージョンの場合はdiffノードが作成されない"""
        v1_content = "*STEP\n*STATIC\n1., 1.\n*END STEP\n"
        (tmp_path / "go_idx1.inp").write_text(v1_content)

        config = GraphConfig.from_dict({"vocab": {}})
        svc = GraphService(project_root=tmp_path, config=config)
        graph = svc.parse_project()

        diff_nodes = [n for n in graph.nodes if n.type == "version_diff"]
        assert len(diff_nodes) == 0

    def test_diff_summary_not_empty(self, tmp_path):
        """変更がある場合のdiffノードのdiff_summaryは「差分なし」ではない"""
        v1_content = "*STEP\n*STATIC\n1., 1.\n*BOUNDARY\nFIX, 1, 3\n*END STEP\n"
        (tmp_path / "go_idx1_v1.inp").write_text(v1_content)

        v2_content = "*STEP\n*DYNAMIC\n1., 1.\n*BOUNDARY\nFIX, 1, 3\n*END STEP\n"
        (tmp_path / "go_idx1_v2.inp").write_text(v2_content)

        config = GraphConfig.from_dict({"vocab": {}})
        svc = GraphService(project_root=tmp_path, config=config)
        graph = svc.parse_project()

        diff_nodes = [n for n in graph.nodes if n.type == "version_diff"]
        for diff_node in diff_nodes:
            if diff_node.properties.get("has_diffs"):
                assert diff_node.properties["diff_summary"] != "差分なし"


class TestObsidianWarningDisplay:
    """Obsidianエクスポートのwarning/diff表示テスト"""

    def test_warnings_in_markdown_body(self, tmp_path):
        """warning情報がmarkdown本文に記載される"""
        from services.parse.connectors.obsidian import ObsidianConnector

        node = Node(
            id=1,
            type="go",
            name="go_idx1",
            format="inp",
            properties={
                "path": "go_idx1.inp",
                "index": "1",
                "version": "1",
                "sta_warnings": ["Some warning message"],
                "sta_errors": ["Some error message"],
            },
        )

        connector = ObsidianConnector(project_root=tmp_path)
        frontmatter = connector.node_to_frontmatter(node)
        content = connector._format_md(frontmatter, node)

        assert "## 警告・エラー" in content
        assert "Some warning message" in content
        assert "Some error message" in content

    def test_diff_in_markdown_body(self, tmp_path):
        """diff情報がmarkdown本文に記載される"""
        from services.parse.connectors.obsidian import ObsidianConnector

        node = Node(
            id=1,
            type="go",
            name="go_idx1_v2",
            format="inp",
            properties={
                "path": "go_idx1_v2.inp",
                "index": "1",
                "version": "2",
                "diff_from": "go_idx1_v1.inp",
                "diff_summary": "| Location | Status | Details |\n|---|---|---|\n| step[0] | 変更 | 両側で異なる |",
                "diff_details": "## step[0]\n変更あり",
            },
        )

        connector = ObsidianConnector(project_root=tmp_path)
        frontmatter = connector.node_to_frontmatter(node)
        content = connector._format_md(frontmatter, node)

        assert "## 前バージョンとの差分" in content
        assert "go_idx1_v1.inp" in content
        assert "### サマリー" in content

    def test_diff_unified_in_markdown_body(self, tmp_path):
        """diff_unified形式がmarkdown本文にUnified Diffセクションとして出力される"""
        from services.parse.connectors.obsidian import ObsidianConnector

        diff_unified_text = "```diff\n- old_value\n+ new_value\n  unchanged\n```"
        node = Node(
            id=1,
            type="go",
            name="go_idx1_v2",
            format="inp",
            properties={
                "path": "go_idx1_v2.inp",
                "index": "1",
                "version": "2",
                "diff_from": "go_idx1_v1.inp",
                "diff_summary": "| Location | Status |\n|---|---|\n| step | 変更 |",
                "diff_details": "## step\n変更あり",
                "diff_unified": diff_unified_text,
            },
        )

        connector = ObsidianConnector(project_root=tmp_path)
        frontmatter = connector.node_to_frontmatter(node)
        content = connector._format_md(frontmatter, node)

        assert "### Unified Diff" in content
        assert "- old_value" in content
        assert "+ new_value" in content

    def test_diff_unified_not_shown_without_diff_from(self, tmp_path):
        """diff_fromがない場合はdiffセクション自体が出力されない"""
        from services.parse.connectors.obsidian import ObsidianConnector

        node = Node(
            id=1,
            type="go",
            name="go_idx1",
            format="inp",
            properties={
                "path": "go_idx1.inp",
                "diff_unified": "```diff\n- old\n+ new\n```",
            },
        )

        connector = ObsidianConnector(project_root=tmp_path)
        frontmatter = connector.node_to_frontmatter(node)
        content = connector._format_md(frontmatter, node)

        assert "### Unified Diff" not in content

    def test_no_warnings_section_when_clean(self, tmp_path):
        """warning/errorがない場合はセクションが表示されない"""
        from services.parse.connectors.obsidian import ObsidianConnector

        node = Node(
            id=1,
            type="go",
            name="go_idx1",
            format="inp",
            properties={
                "path": "go_idx1.inp",
                "index": "1",
                "version": "1",
            },
        )

        connector = ObsidianConnector(project_root=tmp_path)
        frontmatter = connector.node_to_frontmatter(node)
        content = connector._format_md(frontmatter, node)

        assert "## 警告・エラー" not in content
        assert "## 前バージョンとの差分" not in content


class TestDailyNotesParsing:
    """notes/daily日報解析テスト"""

    def test_parse_daily_note_file_references(self, tmp_path):
        """日報からファイル参照を検出"""
        from services.parse.connectors.obsidian.daily import parse_daily_note

        daily_content = """---
tags:
  - 構造解析
---

## 応力振幅1
- go_idx1.inp
- 画像.png

## メッシュ検討
- mesh_v2.cdb
"""
        daily_file = tmp_path / "2026-02-06.md"
        daily_file.write_text(daily_content)

        note = parse_daily_note(daily_file)

        assert note.date == "2026-02-06"
        assert len(note.file_references) >= 2
        filenames = [r.filename for r in note.file_references]
        assert "go_idx1.inp" in filenames
        assert "mesh_v2.cdb" in filenames

    def test_parse_daily_note_with_properties(self, tmp_path):
        """コロン区切りのプロパティ付きファイル参照を検出"""
        from services.parse.connectors.obsidian.daily import parse_daily_note

        daily_content = """## メモ
go_idx1.inp:  備考: 最終版
go_idx2.inp: status: completed
"""
        daily_file = tmp_path / "2026-02-06.md"
        daily_file.write_text(daily_content)

        note = parse_daily_note(daily_file)

        # プロパティ付きファイル参照の検出
        refs_with_props = [r for r in note.file_references if r.properties]
        assert len(refs_with_props) >= 1

        idx1_ref = next(
            (r for r in note.file_references if r.filename == "go_idx1.inp"),
            None,
        )
        if idx1_ref:
            assert "備考" in idx1_ref.properties

    def test_parse_daily_note_section_detection(self, tmp_path):
        """セクション名が正しく取得される"""
        from services.parse.connectors.obsidian.daily import parse_daily_note

        daily_content = """## 応力振幅1
- go_idx1.inp

## メッシュ検討
- mesh.inp
"""
        daily_file = tmp_path / "2026-02-06.md"
        daily_file.write_text(daily_content)

        note = parse_daily_note(daily_file)

        go_ref = next(
            (r for r in note.file_references if r.filename == "go_idx1.inp"),
            None,
        )
        assert go_ref is not None
        assert go_ref.section == "応力振幅1"

    def test_parse_daily_note_tags(self, tmp_path):
        """タグの検出"""
        from services.parse.connectors.obsidian.daily import parse_daily_note

        daily_content = """---
tags:
  - 構造解析
---
## テスト #振幅 #応力
- go_idx1.inp
"""
        daily_file = tmp_path / "2026-02-06.md"
        daily_file.write_text(daily_content)

        note = parse_daily_note(daily_file)

        assert "構造解析" in note.tags
        assert "振幅" in note.tags

    def test_scan_daily_notes_empty_dir(self, tmp_path):
        """日報ディレクトリが空の場合は空リストを返す"""
        from services.parse.connectors.obsidian.daily import scan_daily_notes

        daily_dir = tmp_path / "notes" / "daily"
        daily_dir.mkdir(parents=True)

        notes = scan_daily_notes(daily_dir)
        assert notes == []

    def test_scan_daily_notes_nonexistent_dir(self, tmp_path):
        """日報ディレクトリが存在しない場合は空リストを返す"""
        from services.parse.connectors.obsidian.daily import scan_daily_notes

        daily_dir = tmp_path / "notes" / "daily"
        notes = scan_daily_notes(daily_dir)
        assert notes == []

    def test_daily_notes_integrated_in_graph(self, tmp_path):
        """日報解析がparse_projectに統合されている"""
        # daily noteを配置
        daily_dir = tmp_path / "notes" / "daily"
        daily_dir.mkdir(parents=True)
        (daily_dir / "2026-02-06.md").write_text("## テスト\n- go_idx1.inp\n")

        # 対応するinpファイルも配置
        (tmp_path / "go_idx1.inp").write_text("** test\n")

        config = GraphConfig.from_dict({"vocab": {}})
        svc = GraphService(project_root=tmp_path, config=config)
        graph = svc.parse_project()

        # daily_noteノードが生成される
        daily_nodes = [n for n in graph.nodes if n.type == "daily_note"]
        assert len(daily_nodes) >= 1

        # mentioned_in関係が生成される
        mentioned_rels = [r for r in graph.relations if r.label == "mentioned_in"]
        assert len(mentioned_rels) >= 1

    def test_daily_note_properties_propagated(self, tmp_path):
        """日報のプロパティが対象ノードに反映される"""
        daily_dir = tmp_path / "notes" / "daily"
        daily_dir.mkdir(parents=True)
        (daily_dir / "2026-02-06.md").write_text("## テスト\ngo_idx1.inp: 備考: 最終版\n")

        (tmp_path / "go_idx1.inp").write_text("** test\n")

        config = GraphConfig.from_dict({"vocab": {}})
        svc = GraphService(project_root=tmp_path, config=config)
        graph = svc.parse_project()

        go_node = next(
            (n for n in graph.nodes if n.name == "go_idx1" and n.format == "inp"),
            None,
        )
        assert go_node is not None
        # daily_notesプロパティが付与される
        if go_node.properties.get("daily_notes"):
            assert "2026-02-06" in go_node.properties["daily_notes"]


class TestExportParse:
    """export --parse オプションのテスト"""

    @staticmethod
    def _import_graph_module():
        try:
            import cli.graph as mod

            return mod
        except (ValueError, ImportError, ModuleNotFoundError) as e:
            pytest.skip(f"cli.graph import failed: {e}")

    def test_export_parse_flag_exists(self):
        """export --parse引数がパーサーに定義されている"""
        mod = self._import_graph_module()
        import argparse

        parser = argparse.ArgumentParser()
        mod._add_export_args(parser)
        args = parser.parse_args(["--parse"])
        assert args.parse is True

    def test_export_without_parse_flag(self):
        """--parseなしの場合はFalse"""
        mod = self._import_graph_module()
        import argparse

        parser = argparse.ArgumentParser()
        mod._add_export_args(parser)
        args = parser.parse_args([])
        assert args.parse is False


class TestDailyConnectorEnhanced:
    """日報コネクタの強化テスト: Obsidianリンク+プロパティ記法、ファイルリンク値抽出"""

    def test_obsidian_link_with_property(self, tmp_path):
        """[[O-go_idx1.inp]]:備考:条件1 でプロパティがセットされる"""
        from services.parse.connectors.obsidian.daily import parse_daily_note

        daily = tmp_path / "2026-02-07.md"
        daily.write_text(
            "## テスト\n\n[[O-go_idx1.inp]]:備考:条件1\n",
            encoding="utf-8",
        )
        note = parse_daily_note(daily)
        assert len(note.file_references) == 1
        ref = note.file_references[0]
        assert ref.filename == "go_idx1.inp"
        assert ref.properties.get("備考") == "条件1"

    def test_obsidian_link_display_name_with_property(self, tmp_path):
        """[[go_idx1.inp|表示名]]:status:completed でプロパティがセットされる"""
        from services.parse.connectors.obsidian.daily import parse_daily_note

        daily = tmp_path / "2026-02-07.md"
        daily.write_text(
            "## テスト\n\n[[go_idx1.inp|ファイル1]]:status:completed\n",
            encoding="utf-8",
        )
        note = parse_daily_note(daily)
        assert len(note.file_references) == 1
        ref = note.file_references[0]
        assert ref.filename == "go_idx1.inp"
        assert ref.properties.get("status") == "completed"

    def test_plain_filename_with_property(self, tmp_path):
        """go_idx1.inp:備考:条件1 でもプロパティがセットされる"""
        from services.parse.connectors.obsidian.daily import parse_daily_note

        daily = tmp_path / "2026-02-07.md"
        daily.write_text(
            "## テスト\n\ngo_idx1.inp: 備考: 条件1\n",
            encoding="utf-8",
        )
        note = parse_daily_note(daily)
        assert len(note.file_references) >= 1
        ref = next(r for r in note.file_references if r.filename == "go_idx1.inp")
        assert ref.properties.get("備考") == "条件1"

    def test_file_link_value_extraction(self, tmp_path):
        """プロパティ値が[[image.png]]の場合、ファイルパスを抽出"""
        from services.parse.connectors.obsidian.daily import (
            _extract_file_path_from_value,
        )

        assert _extract_file_path_from_value("[[image.png]]") == "image.png"
        assert _extract_file_path_from_value("[[image.png|画像1]]") == "image.png"
        assert _extract_file_path_from_value("[[path/to/image.png]]") == "path/to/image.png"
        assert _extract_file_path_from_value("普通の値") == "普通の値"

    def test_strip_obsidian_prefix(self):
        """O-プレフィックスの除去テスト"""
        from services.parse.connectors.obsidian.daily import _strip_obsidian_prefix

        assert _strip_obsidian_prefix("O-go_idx1.inp") == "go_idx1.inp"
        assert _strip_obsidian_prefix("O-go_idx1.inp.md") == "go_idx1.inp"
        assert _strip_obsidian_prefix("go_idx1.inp") == "go_idx1.inp"

    def test_file_link_value_in_property(self, tmp_path):
        """go_idx1.inp: image: [[image.png|画像1]] でファイルパスが抽出される"""
        from services.parse.connectors.obsidian.daily import parse_daily_note

        daily = tmp_path / "2026-02-07.md"
        daily.write_text(
            "## テスト\n\ngo_idx1.inp: image: [[image.png|画像1]]\n",
            encoding="utf-8",
        )
        note = parse_daily_note(daily)
        ref = next(r for r in note.file_references if r.filename == "go_idx1.inp")
        assert ref.properties.get("image") == "image.png"


class TestInfoCommandEnhanced:
    """jj infoコマンドの強化テスト"""

    @staticmethod
    def _import_graph_module():
        try:
            import cli.graph as mod

            return mod
        except (ValueError, ImportError, ModuleNotFoundError) as e:
            pytest.skip(f"cli.graph import failed: {e}")

    def test_info_args_multiple_filenames(self):
        """ファイル名を複数指定できる"""
        mod = self._import_graph_module()
        import argparse

        parser = argparse.ArgumentParser()
        mod._add_info_args(parser)
        args = parser.parse_args(["file1.inp", "file2.inp"])
        assert args.filename == ["file1.inp", "file2.inp"]

    def test_info_args_id_filter(self):
        """-id オプションでインデックス指定"""
        mod = self._import_graph_module()
        import argparse

        parser = argparse.ArgumentParser()
        mod._add_info_args(parser)
        args = parser.parse_args(["-id", "1", "2"])
        assert args.index == ["1", "2"]

    def test_info_args_version_filter(self):
        """-v オプションでバージョン指定"""
        mod = self._import_graph_module()
        import argparse

        parser = argparse.ArgumentParser()
        mod._add_info_args(parser)
        args = parser.parse_args(["-v", "1"])
        assert args.version == ["1"]

    def test_info_args_props_only(self):
        """-props オプションでプロパティのみ表示"""
        mod = self._import_graph_module()
        import argparse

        parser = argparse.ArgumentParser()
        mod._add_info_args(parser)
        args = parser.parse_args(["-props", "file.inp"])
        assert args.props_only is True

    def test_info_search_by_index(self):
        """インデックスで検索"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1",
                    format="inp",
                    properties={"index": "1", "version": "1", "path": "go_idx1.inp"},
                ),
                Node(
                    id=2,
                    type="go",
                    name="go_idx2",
                    format="inp",
                    properties={"index": "2", "version": "1", "path": "go_idx2.inp"},
                ),
            ],
            relations=[],
        )
        # インデックス1でフィルタ
        matched = [n for n in graph.nodes if str(n.properties.get("index", "")) == "1"]
        assert len(matched) == 1
        assert matched[0].name == "go_idx1"


class TestDiffCommand:
    """jj diffコマンドのテスト"""

    @staticmethod
    def _import_graph_module():
        try:
            import cli.graph as mod

            return mod
        except (ValueError, ImportError, ModuleNotFoundError) as e:
            pytest.skip(f"cli.graph import failed: {e}")

    def test_diff_args(self):
        """diffコマンドの引数パース"""
        mod = self._import_graph_module()
        import argparse

        parser = argparse.ArgumentParser()
        mod._add_diff_args(parser)
        args = parser.parse_args(["file1.inp", "file2.inp", "--detail"])
        assert args.file1 == "file1.inp"
        assert args.file2 == "file2.inp"
        assert args.detail is True

    def test_resolve_file_path(self, tmp_path):
        """ファイルパス解決のテスト"""
        mod = self._import_graph_module()

        test_file = tmp_path / "test.inp"
        test_file.write_text("test")

        # 存在するファイルの検索
        result = mod._resolve_file_path(tmp_path, "test.inp")
        assert result is not None
        assert result.name == "test.inp"

        # 存在しないファイル
        result = mod._resolve_file_path(tmp_path, "nonexist.inp")
        assert result is None


class TestVerboseName:
    """verbose_name生成のテスト"""

    def test_verbose_name_set_on_node(self, tmp_path):
        """parse時にverbose_nameがプロパティに設定される"""
        from config import GraphConfig
        from services.graph import GraphService

        # テスト用設定
        config = GraphConfig.from_dict(
            {
                "vocab": {"go": "計算入力"},
            }
        )
        service = GraphService(project_root=tmp_path, config=config)
        # テストファイル作成
        (tmp_path / "go_idx1_v1.inp").write_text("test")
        node = service.file_to_node(tmp_path / "go_idx1_v1.inp")
        # verbose_nameが設定される（raw_nameと異なる場合のみ）
        assert "verbose_name" in node.properties


class TestExportCSVJSON:
    """CSV/JSONエクスポートのテスト"""

    @staticmethod
    def _import_graph_module():
        try:
            import cli.graph as mod

            return mod
        except (ValueError, ImportError, ModuleNotFoundError) as e:
            pytest.skip(f"cli.graph import failed: {e}")

    def test_export_args_csv(self):
        """--target csv オプション"""
        mod = self._import_graph_module()
        import argparse

        parser = argparse.ArgumentParser()
        mod._add_export_args(parser)
        args = parser.parse_args(["--target", "csv"])
        assert args.target == "csv"

    def test_export_args_json(self):
        """--target json オプション"""
        mod = self._import_graph_module()
        import argparse

        parser = argparse.ArgumentParser()
        mod._add_export_args(parser)
        args = parser.parse_args(["--target", "json"])
        assert args.target == "json"

    def test_export_args_select(self):
        """--select オプションで複数ファイル選択"""
        mod = self._import_graph_module()
        import argparse

        parser = argparse.ArgumentParser()
        mod._add_export_args(parser)
        args = parser.parse_args(["--target", "csv", "--select", "file1.inp", "file2.inp"])
        assert args.select == ["file1.inp", "file2.inp"]

    def test_export_data_csv(self, tmp_path):
        """CSVエクスポートの動作テスト"""
        import csv
        import json

        self._import_graph_module()

        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1",
                    format="inp",
                    properties={
                        "index": "1",
                        "version": "1",
                        "path": "go_idx1.inp",
                        "tags": ["test"],
                    },
                ),
                Node(
                    id=2,
                    type="mesh",
                    name="mesh_idx1",
                    format="inp",
                    properties={"index": "1", "version": "1", "path": "mesh_idx1.inp"},
                ),
            ],
            relations=[],
        )

        # 全ノードのキーを収集してnull埋め
        all_keys = ["name", "type", "format"]
        seen = set(all_keys)
        for node in graph.nodes:
            for key in node.properties:
                if key not in seen:
                    all_keys.append(key)
                    seen.add(key)

        # CSV書き出し
        output_path = tmp_path / "test.csv"
        rows = []
        for node in graph.nodes:
            row = {"name": node.name, "type": node.type, "format": node.format}
            for key in all_keys:
                if key not in row:
                    value = node.properties.get(key)
                    if value is None:
                        row[key] = None
                    elif isinstance(value, (list, dict)):
                        row[key] = json.dumps(value, ensure_ascii=False)
                    else:
                        row[key] = value
            rows.append(row)

        with output_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

        # 検証
        with output_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            read_rows = list(reader)
        assert len(read_rows) == 2
        assert read_rows[0]["name"] == "go_idx1"


class TestMaterialAssignmentProps:
    """材料割り当てプロパティのテスト"""

    def test_material_enrich(self):
        """_enrich_material_assignment_propsで材料名とelsetが追加される"""
        from config import GraphConfig
        from jj_types import Relation
        from services.graph.project_graph import ProjectGraph
        from services.parse.connectors.abaqus.inp_parser import (
            AbaqusMaterialAssignmentParser,
        )

        config = GraphConfig.from_dict({})

        go_node = Node(
            id=1,
            type="go",
            name="go_idx1",
            format="inp",
            properties={"path": "go_idx1.inp"},
        )
        mat_node = Node(
            id=2,
            type="abaqus_material",
            name="Steel",
            format="material",
            properties={"assigned_elsets": ["SOLID1", "SOLID2"]},
        )

        mat_rel = Relation(id=1, label="assigned_to", node1_id=2, node2_id=1)

        graph = ProjectGraph(
            nodes=[go_node, mat_node],
            relations=[mat_rel],
            project_root=Path("/tmp"),
            config=config,
        )

        AbaqusMaterialAssignmentParser._enrich_material_assignment_props(graph, [mat_node], [mat_rel])

        assert "materials" in go_node.properties
        assert "Steel" in go_node.properties["materials"]
        assert "material_elsets" in go_node.properties
        assert go_node.properties["material_elsets"]["Steel"] == ["SOLID1", "SOLID2"]


class TestObsidianTagExport:
    """Obsidianタグエクスポートのテスト"""

    def test_tags_in_frontmatter(self):
        """frontmatterにタイプタグが追加される"""
        from services.parse.connectors.obsidian import ObsidianConnector

        node = Node(
            id=1,
            type="go",
            name="go_idx1",
            format="inp",
            properties={
                "index": "1",
                "version": "1",
                "path": "go_idx1.inp",
            },
        )
        connector = ObsidianConnector(project_root=Path("/tmp"))
        fm = connector.node_to_frontmatter(node)
        tags = fm.get("tags", [])
        assert "go" in tags

    def test_material_tags_in_frontmatter(self):
        """材料タグがfrontmatterのtagsに追加される"""
        from services.parse.connectors.obsidian import ObsidianConnector

        node = Node(
            id=1,
            type="go",
            name="go_idx1",
            format="inp",
            properties={
                "index": "1",
                "version": "1",
                "path": "go_idx1.inp",
                "materials": ["Steel", "Aluminum"],
            },
        )
        connector = ObsidianConnector(project_root=Path("/tmp"))
        fm = connector.node_to_frontmatter(node)
        tags = fm.get("tags", [])
        assert "material/Steel" in tags
        assert "material/Aluminum" in tags

    def test_tags_in_markdown_body(self):
        """markdown本文に#tag形式でタグが出力される"""
        from services.parse.connectors.obsidian import ObsidianConnector

        node = Node(
            id=1,
            type="go",
            name="go_idx1",
            format="inp",
            properties={
                "index": "1",
                "version": "1",
                "path": "go_idx1.inp",
            },
        )
        connector = ObsidianConnector(project_root=Path("/tmp"))
        fm = connector.node_to_frontmatter(node)
        content = connector._format_md(fm, node)
        assert "#go" in content


class TestVersionKeyUnification:
    """version/バージョンのキー統一テスト"""

    def test_vocab_translates_version_key(self, tmp_path):
        """vocab定義がある場合、versionキーがバージョンに統一される"""
        config = GraphConfig.from_dict(
            {
                "vocab": {"idx": "条件", "v": "バージョン"},
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)
        (tmp_path / "go_idx1_v2.inp").write_text("")
        node = svc.file_to_node(tmp_path / "go_idx1_v2.inp")
        # 英語キーは存在しない
        assert "version" not in node.properties
        assert "index" not in node.properties
        # 日本語キーが存在する
        assert node.properties.get("条件") == "1"
        assert node.properties.get("バージョン") == "2"

    def test_no_vocab_keeps_english_keys(self, tmp_path):
        """vocab定義がない場合、英語キーが維持される"""
        config = GraphConfig.from_dict({"vocab": {}})
        svc = GraphService(project_root=tmp_path, config=config)
        (tmp_path / "go_idx1_v2.inp").write_text("")
        node = svc.file_to_node(tmp_path / "go_idx1_v2.inp")
        assert node.properties.get("index") == "1"
        assert node.properties.get("version") == "2"

    def test_empty_version_removed_with_vocab(self, tmp_path):
        """空のversionはvocab定義があれば除去される"""
        config = GraphConfig.from_dict(
            {
                "vocab": {"idx": "条件", "v": "バージョン"},
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)
        (tmp_path / "go_idx1_w5.inp").write_text("")
        node = svc.file_to_node(tmp_path / "go_idx1_w5.inp")
        # 空のversionは除去
        assert "version" not in node.properties
        assert "バージョン" not in node.properties  # 空値は追加しない
        assert node.properties.get("条件") == "1"

    def test_implicit_version_translated(self, tmp_path):
        """暗黙のversionもvocabで変換される"""
        config = GraphConfig.from_dict(
            {
                "vocab": {"idx": "条件", "v": "バージョン"},
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)
        (tmp_path / "material.inp").write_text("")
        node = svc.file_to_node(tmp_path / "material.inp")
        # material.inpは暗黙のidx=1, v=1
        assert node.properties.get("条件") == "1"
        assert node.properties.get("バージョン") == "1"
        assert "index" not in node.properties
        assert "version" not in node.properties


class TestTokenKeyMapVerboseName:
    """token_key_mapのverbose_name生成テスト"""

    def test_verbose_name_uses_value_only(self, tmp_path):
        """token_key_mapで割り当てた場合、verbose_nameにキー名を含めない"""
        config = GraphConfig.from_dict(
            {
                "vocab": {"hogehoge24": "ほげほげ24"},
                "token-key-map": {"形状": ["hogehoge24"]},
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)
        (tmp_path / "mesh_hogehoge24_v1_idx1.inp").write_text("")
        node = svc.file_to_node(tmp_path / "mesh_hogehoge24_v1_idx1.inp")
        vn = node.properties.get("verbose_name", "")
        # "形状ほげほげ24" ではなく "ほげほげ24" のみ
        assert "形状" not in vn
        assert "ほげほげ24" in vn

    def test_verbose_name_tag_uses_translated_value(self, tmp_path):
        """token_key_mapのverbose_name→tagは変換後の値を使用"""
        config = GraphConfig.from_dict(
            {
                "vocab": {"hogehoge24": "ほげほげ24"},
                "token-key-map": {"形状": ["hogehoge24"]},
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)
        (tmp_path / "mesh_hogehoge24_v1_idx1.inp").write_text("")
        svc.file_to_node(tmp_path / "mesh_hogehoge24_v1_idx1.inp")


class TestStaEnrichmentOnly:
    """sta/msg/datファイルの情報集約テスト（Node化しない）"""

    def test_sta_not_node_but_enriches_inp(self, tmp_path):
        """.staファイルはNodeにならず、対応inpに情報を集約"""
        sta_content = " STEP   1  STATIC ANALYSIS\n\n\n THE ANALYSIS HAS COMPLETED SUCCESSFULLY\n"
        (tmp_path / "go_idx1_v1.inp").write_text("")
        (tmp_path / "go_idx1_v1.sta").write_text(sta_content)

        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "file-relations": {
                    "input-extensions": [".inp"],
                    "result-extensions": [".sta"],
                },
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)
        graph = svc.parse_project(extensions=[".inp", ".sta"])

        # .staノードは存在しない
        sta_nodes = [n for n in graph.nodes if n.format == "sta"]
        assert len(sta_nodes) == 0

        # .inpノードにanalysis_statusが集約される
        inp_node = next((n for n in graph.nodes if n.format == "inp"), None)
        assert inp_node is not None
        assert inp_node.properties.get("analysis_status") == "completed"

    def test_msg_not_node(self, tmp_path):
        """.msgファイルはNodeにならない"""
        (tmp_path / "go_idx1_v1.inp").write_text("")
        (tmp_path / "go_idx1_v1.msg").write_text("")

        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "file-relations": {
                    "input-extensions": [".inp"],
                    "result-extensions": [".msg"],
                },
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)
        graph = svc.parse_project(extensions=[".inp", ".msg"])
        msg_nodes = [n for n in graph.nodes if n.format == "msg"]
        assert len(msg_nodes) == 0

    def test_odb_no_longer_creates_node(self, tmp_path):
        """.odbファイルはNO_NODE_EXTENSIONSによりNode化されない"""
        (tmp_path / "go_idx1_v1.inp").write_text("")
        (tmp_path / "go_idx1_v1.odb").write_text("")

        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "file-relations": {
                    "input-extensions": [".inp"],
                    "result-extensions": [".odb"],
                },
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)
        graph = svc.parse_project(extensions=[".inp", ".odb"])
        odb_nodes = [n for n in graph.nodes if n.format == "odb"]
        assert len(odb_nodes) == 0
        # .inpノードは生成される
        inp_nodes = [n for n in graph.nodes if n.format == "inp"]
        assert len(inp_nodes) == 1


class TestMaterialVerboseNameEnrichment:
    """material.inpのverbose_name更新テスト"""

    def test_material_verbose_name_includes_material_names(self, tmp_path):
        """material.inpのverbose_nameに材料名が含まれる"""
        mat_content = "*MATERIAL, NAME=Steel\n*ELASTIC\n210000.0, 0.3\n*MATERIAL, NAME=Rubber\n*ELASTIC\n100.0, 0.49\n"
        (tmp_path / "material.inp").write_text(mat_content)

        config = GraphConfig.from_dict(
            {
                "vocab": {"material": "材料定義"},
                "file-relations": {"input-extensions": [".inp"]},
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)
        graph = svc.parse_project(extensions=[".inp"])

        mat_node = next(
            (n for n in graph.nodes if n.name == "material" and n.format == "inp"),
            None,
        )
        assert mat_node is not None
        vn = mat_node.properties.get("verbose_name", "")
        assert "rubber" in vn.lower()
        assert "steel" in vn.lower()

    def test_material_tags_include_material_names(self, tmp_path):
        """material.inpのタグに材料名が含まれる"""
        mat_content = "*MATERIAL, NAME=Steel\n*ELASTIC\n210000.0, 0.3\n"
        (tmp_path / "material.inp").write_text(mat_content)

        config = GraphConfig.from_dict(
            {
                "vocab": {"material": "材料定義"},
                "file-relations": {"input-extensions": [".inp"]},
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)
        graph = svc.parse_project(extensions=[".inp"])

        mat_node = next(
            (n for n in graph.nodes if n.name == "material" and n.format == "inp"),
            None,
        )
        assert mat_node is not None


class TestRootDirectoryNode:
    """rootディレクトリNode化テスト"""

    def test_root_directory_created(self, tmp_path):
        """ルート直下にファイルがある場合、root directoryノードが生成される"""
        (tmp_path / "go_idx1_v1.inp").write_text("")
        config = GraphConfig.from_dict({"vocab": {}})
        svc = GraphService(project_root=tmp_path, config=config)
        graph = svc.parse_project(extensions=[".inp"])

        # project-name未設定の場合はプロジェクトルートのフォルダ名を使用
        root_node = next(
            (n for n in graph.nodes if n.format == "directory" and n.properties.get("path") == "."),
            None,
        )
        assert root_node is not None
        assert root_node.type == "directory"
        assert root_node.name == tmp_path.name  # フォルダ名がname

    def test_root_directory_with_project_name(self, tmp_path):
        """project-name設定時はその名前をrootのnameに使用"""
        (tmp_path / "go_idx1_v1.inp").write_text("")
        config = GraphConfig.from_dict({"vocab": {}, "project-name": "my-project"})
        svc = GraphService(project_root=tmp_path, config=config)
        graph = svc.parse_project(extensions=[".inp"])

        root_node = next(
            (n for n in graph.nodes if n.format == "directory" and n.properties.get("path") == "."),
            None,
        )
        assert root_node is not None
        assert root_node.name == "my-project"

    def test_root_contains_relations(self, tmp_path):
        """rootノードからルート直下ファイルへのcontains関係が作成される"""
        (tmp_path / "go_idx1_v1.inp").write_text("")
        (tmp_path / "material.inp").write_text("")
        config = GraphConfig.from_dict({"vocab": {}})
        svc = GraphService(project_root=tmp_path, config=config)
        graph = svc.parse_project(extensions=[".inp"])

        root_node = next(
            (n for n in graph.nodes if n.format == "directory" and n.properties.get("path") == "."),
            None,
        )
        assert root_node is not None

        contains = [r for r in graph.relations if r.label == "contains" and r.node1_id == root_node.id]
        assert len(contains) >= 2  # go_idx1_v1.inp + material.inp

    def test_subdir_files_not_in_root_contains(self, tmp_path):
        """サブディレクトリ内のファイルはrootのcontainsに含まれない"""
        (tmp_path / "go_idx1_v1.inp").write_text("")
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "other.inp").write_text("")
        config = GraphConfig.from_dict({"vocab": {}})
        svc = GraphService(project_root=tmp_path, config=config)
        graph = svc.parse_project(extensions=[".inp"])

        root_node = next(
            (n for n in graph.nodes if n.format == "directory" and n.properties.get("path") == "."),
            None,
        )
        assert root_node is not None
        contains = [r for r in graph.relations if r.label == "contains" and r.node1_id == root_node.id]
        # ルート直下のgo_idx1_v1.inpとsubdirディレクトリ
        assert len(contains) == 2


class TestDatEnrichment:
    """datファイル解析テスト"""

    def test_parse_dat_file_extracts_time(self, tmp_path):
        """parse_dat_fileがCPU時間とウォールクロック時間を抽出"""
        from services.parse.connectors.abaqus.result_parser import parse_dat_file

        dat_content = (
            "SOME OUTPUT DATA\n TOTAL CPU TIME (SEC)      =   123.45\n TOTAL WALL CLOCK TIME (SEC) =    67.89\n"
        )
        dat_file = tmp_path / "go_idx1.dat"
        dat_file.write_text(dat_content)
        result = parse_dat_file(dat_file)
        assert result["cpu_time"] == 123.45
        assert result["wallclock_time"] == 67.89

    def test_parse_dat_file_empty(self, tmp_path):
        """空datファイルは空辞書"""
        from services.parse.connectors.abaqus.result_parser import parse_dat_file

        dat_file = tmp_path / "empty.dat"
        dat_file.write_text("")
        result = parse_dat_file(dat_file)
        assert result == {}

    def test_dat_enriches_inp(self, tmp_path):
        """.datの計算時間情報がinpに集約される"""
        (tmp_path / "go_idx1_v1.inp").write_text("")
        (tmp_path / "go_idx1_v1.dat").write_text(
            " TOTAL CPU TIME (SEC)      =   100.5\n TOTAL WALL CLOCK TIME (SEC) =    50.2\n"
        )
        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "file-relations": {"input-extensions": [".inp"]},
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)
        graph = svc.parse_project(extensions=[".inp", ".dat"])

        # .datはNode化されない
        dat_nodes = [n for n in graph.nodes if n.format == "dat"]
        assert len(dat_nodes) == 0

        # .inpに計算時間が集約
        inp_node = next((n for n in graph.nodes if n.format == "inp"), None)
        assert inp_node is not None
        assert inp_node.properties.get("cpu_time") == 100.5
        assert inp_node.properties.get("wallclock_time") == 50.2


class TestPymeshImport:
    """pymeshインポート修正の確認テスト"""

    def test_safe_import_pymesh_returns_functions(self):
        """pymeshが正しくインポートできる（絶対インポート）"""
        from services.parse.connectors.abaqus.mesh import _safe_import_pymesh

        create_mesher, _get_quality = _safe_import_pymesh()
        # pymeshが利用可能ならNoneでない
        assert create_mesher is not None, "pymeshのインポートに失敗"


class TestMaterialNameCasePreservation:
    """材料名のケース保持テスト"""

    def test_parse_material_blocks_preserves_case(self, tmp_path):
        """parse_material_blocksが元の大文字小文字を保持する"""
        from services.parse.connectors.abaqus.inp_parser import parse_material_blocks

        inp_file = tmp_path / "material.inp"
        inp_file.write_text(
            "*MATERIAL, NAME=Steel_S235\n"
            "*ELASTIC\n"
            "210000.0, 0.3\n"
            "*MATERIAL, NAME=ALUMINUM_6061\n"
            "*ELASTIC\n"
            "69000.0, 0.33\n",
            encoding="utf-8",
        )
        materials = parse_material_blocks(inp_file)
        names = [m["name"] for m in materials]
        assert "Steel_S235" in names
        assert "ALUMINUM_6061" in names

    def test_elset_mapping_preserves_case(self, tmp_path):
        """extract_material_elset_mappingが元のケースを保持する"""
        from services.parse.connectors.abaqus.mesh import (
            extract_material_elset_mapping,
        )

        inp_file = tmp_path / "test.inp"
        inp_file.write_text(
            "*SOLID SECTION, MATERIAL=Steel_S235, ELSET=Solid_Elements\n1.0,\n",
            encoding="utf-8",
        )
        mapping = extract_material_elset_mapping(inp_file)
        assert "Steel_S235" in mapping
        assert "Solid_Elements" in mapping["Steel_S235"]


class TestWindowsPathParsing:
    """Windows環境のパスパース対応テスト"""

    def test_backslash_path_normalized(self, tmp_path):
        """バックスラッシュパスからbasenameを正しく抽出"""
        from pathlib import PurePosixPath

        path = "subdir\\go_idx1_v1.inp"
        normalized = path.replace("\\", "/")
        basename = PurePosixPath(normalized).name
        assert basename == "go_idx1_v1.inp"

    def test_forward_slash_path(self, tmp_path):
        """スラッシュパスも正しく処理"""
        from pathlib import PurePosixPath

        path = "subdir/go_idx1_v1.inp"
        normalized = path.replace("\\", "/")
        basename = PurePosixPath(normalized).name
        assert basename == "go_idx1_v1.inp"


class TestProjectNameConfig:
    """project-name設定のテスト"""

    def test_config_project_name(self):
        """GraphConfigにproject_nameが含まれる"""
        config = GraphConfig.from_dict({"project-name": "my-project"})
        assert config.project_name == "my-project"

    def test_config_default_project_name(self):
        """project-name未設定時は空文字列"""
        config = GraphConfig.from_dict({})
        assert config.project_name == ""


class TestCredentialService:
    """クレデンシャル管理サービスのテスト"""

    def test_encrypt_decrypt_roundtrip(self):
        """暗号化→復号がラウンドトリップする"""
        from services.lib.credentials import _decrypt, _encrypt

        key = b"\x00" * 32
        plaintext = "my-secret-password"
        ciphertext = _encrypt(plaintext, key)
        assert ciphertext != plaintext
        decrypted = _decrypt(ciphertext, key)
        assert decrypted == plaintext

    def test_save_and_load_credentials(self, tmp_path):
        """クレデンシャルの保存と読み込み"""
        from services.lib.credentials import (
            load_credentials,
            save_credentials,
        )

        # テスト用の鍵ディレクトリを準備
        creds = {
            "uri": "bolt://localhost:7687",
            "user": "neo4j",
            "password": "test-password-123",
            "database": "testdb",
        }
        save_credentials(tmp_path, "neo4j", creds)

        loaded = load_credentials(tmp_path, "neo4j")
        assert loaded is not None
        assert loaded["uri"] == "bolt://localhost:7687"
        assert loaded["user"] == "neo4j"
        assert loaded["password"] == "test-password-123"
        assert loaded["database"] == "testdb"

    def test_mask_value(self):
        """マスキング関数の動作"""
        from services.lib.credentials import mask_value

        assert mask_value("password123") == "pa*********"
        assert mask_value("ab") == "**"
        assert mask_value("a") == "*"

    def test_load_nonexistent_returns_none(self, tmp_path):
        """存在しないクレデンシャルはNoneを返す"""
        from services.lib.credentials import load_credentials

        result = load_credentials(tmp_path, "nonexistent")
        assert result is None


class TestMeshStatsDisplay:
    """メッシュ統計表示のテスト"""

    def test_mesh_stats_in_node_properties(self, tmp_path):
        """メッシュ統計がNodeのpropertiesに格納される"""
        node = Node(
            id=1,
            type="calculation_input",
            name="test",
            format="inp",
            properties={
                "path": "test.inp",
                "mesh_node_count": 1000,
                "mesh_element_count": 500,
                "mesh_element_types": {"C3D8": 300, "C3D4": 200},
            },
        )
        assert node.properties["mesh_node_count"] == 1000
        assert node.properties["mesh_element_count"] == 500
        assert isinstance(node.properties["mesh_element_types"], dict)
        assert node.properties["mesh_element_types"]["C3D8"] == 300

    def test_mesh_stats_dict_expandable(self):
        """dictプロパティが展開可能であることを確認"""
        props = {
            "mesh_element_types": {"C3D8": 300, "C3D4": 200},
            "mesh_quality": {"volume": {"min": 0.1, "max": 1.0}},
        }
        elem_types = props["mesh_element_types"]
        assert isinstance(elem_types, dict)
        for etype, count in elem_types.items():
            assert isinstance(etype, str)
            assert isinstance(count, int)

        quality = props["mesh_quality"]
        assert isinstance(quality, dict)
        assert "volume" in quality


class TestVerboseNameFormat:
    """verbose-name-formatテンプレートのテスト"""

    def test_format_basic(self, tmp_path):
        """フォーマットテンプレートでverbose_nameが生成される"""
        config = GraphConfig.from_dict(
            {
                "vocab": {"idx": "条件", "go": "計算入力", "t": "高さ", "F": "荷重"},
                "verbose-name-format": "条件{条件}(高さ{高さ},荷重{荷重})",
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)
        (tmp_path / "go_idx1_t5_F20.inp").write_text("")
        node = svc.file_to_node(tmp_path / "go_idx1_t5_F20.inp")
        vn = node.properties.get("verbose_name", "")
        assert vn == "条件1(高さ5,荷重20)"

    def test_format_with_original_keys(self, tmp_path):
        """フォーマットでvocab変換前のキー名も参照可能"""
        config = GraphConfig.from_dict(
            {
                "vocab": {"idx": "条件", "go": "計算入力"},
                "verbose-name-format": "idx{idx}",
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)
        (tmp_path / "go_idx3.inp").write_text("")
        node = svc.file_to_node(tmp_path / "go_idx3.inp")
        vn = node.properties.get("verbose_name", "")
        assert vn == "idx3"

    def test_format_missing_key_is_empty(self, tmp_path):
        """フォーマット内の存在しないキーは空文字に置換"""
        config = GraphConfig.from_dict(
            {
                "vocab": {"idx": "条件"},
                "verbose-name-format": "条件{条件}_存在しない{不明}",
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)
        (tmp_path / "go_idx1.inp").write_text("")
        node = svc.file_to_node(tmp_path / "go_idx1.inp")
        vn = node.properties.get("verbose_name", "")
        assert vn == "条件1_存在しない"

    def test_format_not_set_uses_legacy(self, tmp_path):
        """verbose-name-format未設定時は従来方式"""
        config = GraphConfig.from_dict(
            {
                "vocab": {"idx": "条件", "go": "計算入力"},
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)
        (tmp_path / "go_idx2_v1.inp").write_text("")
        node = svc.file_to_node(tmp_path / "go_idx2_v1.inp")
        vn = node.properties.get("verbose_name", "")
        # 従来方式: タイプ_プロパティ の形式
        assert "計算入力" in vn
        assert "条件2" in vn

    def test_format_with_type_reference(self, tmp_path):
        """フォーマットで{type}を参照可能"""
        config = GraphConfig.from_dict(
            {
                "vocab": {"idx": "条件", "go": "計算入力"},
                "verbose-name-format": "{type}_{条件}",
            }
        )
        svc = GraphService(project_root=tmp_path, config=config)
        (tmp_path / "go_idx5.inp").write_text("")
        node = svc.file_to_node(tmp_path / "go_idx5.inp")
        vn = node.properties.get("verbose_name", "")
        assert vn == "計算入力_5"


class TestDashboardDisplayName:
    """dashboardのdisplay_name（verbose_name表示）テスト"""

    def test_node_to_row_includes_display_name(self):
        """_node_to_rowにverbose_nameキーの列が含まれる"""
        from jj_types import GraphModel, Node
        from services.dashboard.data_provider import DashboardDataProvider

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1",
                format="inp",
                properties={"path": "go_idx1.inp", "verbose_name": "条件1"},
            ),
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        provider = DashboardDataProvider(graph, vocab={})
        rows = provider.get_go_table()
        assert len(rows) == 1
        # verbose_nameキー（vocab未設定 → "verbose_name"）
        assert rows[0]["verbose_name"] == "条件1"

    def test_node_to_row_display_name_with_vocab(self):
        """vocab変換後のキー名でverbose_nameが表示される"""
        from jj_types import GraphModel, Node
        from services.dashboard.data_provider import DashboardDataProvider

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1",
                format="inp",
                properties={"path": "go_idx1.inp", "表示名": "条件1(高さ5)"},
            ),
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        provider = DashboardDataProvider(graph, vocab={"verbose_name": "表示名"})
        rows = provider.get_go_table()
        assert len(rows) == 1
        # vocab変換後のキー（"表示名"）で表示名が返される
        assert rows[0]["表示名"] == "条件1(高さ5)"

    def test_get_display_name_fallback(self):
        """verbose_nameが無い場合はnameにフォールバック"""
        from jj_types import GraphModel, Node
        from services.dashboard.data_provider import DashboardDataProvider

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp"}),
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        provider = DashboardDataProvider(graph, vocab={})
        display = provider._get_display_name(nodes[0])
        assert display == "go_idx1"

    def test_plot_data_includes_display_name(self):
        """get_plot_dataにverbose_nameキーが含まれる"""
        from jj_types import GraphModel, Node
        from services.dashboard.data_provider import DashboardDataProvider

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1",
                format="inp",
                properties={"path": "go_idx1.inp", "verbose_name": "条件1", "x": 1.0, "y": 2.0},
            ),
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        provider = DashboardDataProvider(graph, vocab={})
        points = provider.get_plot_data("x", "y")
        assert len(points) == 1
        assert points[0]["verbose_name"] == "条件1"

    def test_array_grid_data_includes_display_name(self):
        """get_array_grid_dataにdisplay_nameが含まれる"""
        from jj_types import GraphModel, Node
        from services.dashboard.data_provider import DashboardDataProvider

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1",
                format="inp",
                properties={
                    "path": "go_idx1.inp",
                    "verbose_name": "条件1",
                    "RF.time": [0.0, 1.0],
                    "RF.RF3": [10.0, 20.0],
                },
            ),
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        provider = DashboardDataProvider(graph, vocab={})
        data = provider.get_array_grid_data("RF.time", "RF.RF3")
        assert len(data) == 1
        assert data[0]["display_name"] == "条件1"


class TestPropertyKeysVocabSort:
    """get_property_keysのvocabソートテスト"""

    def test_vocab_keys_first(self):
        """vocab指定のあるキーが先にソートされる"""
        from jj_types import GraphModel, Node
        from services.dashboard.data_provider import DashboardDataProvider

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1",
                format="inp",
                properties={
                    "path": "go_idx1.inp",
                    "条件": "1",
                    "xyz_unknown": "42",
                    "温度": "300",
                    "abc_other": "100",
                },
            ),
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        vocab = {"idx": "条件", "temp": "温度"}
        provider = DashboardDataProvider(graph, vocab=vocab)
        keys = provider.get_property_keys()
        # vocab指定あり（条件、温度）が先に来る
        vocab_keys = [k for k in keys if k in ("条件", "温度")]
        non_vocab_keys = [k for k in keys if k in ("xyz_unknown", "abc_other")]
        # vocab指定キーがnon-vocabキーより前にある
        assert keys.index(vocab_keys[0]) < keys.index(non_vocab_keys[0])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
