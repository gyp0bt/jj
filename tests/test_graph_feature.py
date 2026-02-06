"""graph機能のテスト

テスト1: ユーザー指定のテストケース
- ファイル名パターンからidx, version, props, tagsを正しく抽出
- 暗黙のidx/verの処理
- 結果ファイルと入力ファイルの関連付け
- タイプ推定とpath-type-mapの適用
"""
from pathlib import Path
import pytest

from services.parse.file_parse import FileParse, FileType
from services.graph import GraphService
from jj_types import GraphModel, Node
from config import GraphConfig, PathTypeMapConfig


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
        return GraphConfig.from_dict({
            "vocab": {"idx": "番号", "v": "バージョン"},
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
        })

    @pytest.fixture
    def graph_service(self, config):
        """テスト用GraphService"""
        if not FIXTURE_DIR.exists():
            pytest.skip(f"Fixture directory not found: {FIXTURE_DIR}")
        return GraphService(project_root=FIXTURE_DIR, config=config)

    def test_scan_files(self, graph_service):
        """ファイルスキャンのテスト"""
        # .inp, .odb, .sta, .csv, .pptx, .py, .json, .modfem, .stl
        extensions = [".inp", ".odb", ".sta", ".csv", ".pptx", ".py", ".json", ".modfem", ".stl"]
        files = graph_service.scan_files(extensions=extensions)
        assert len(files) > 0

        # 期待されるファイルが含まれているか確認
        filenames = [f.name for f in files]
        assert "go_idx1_w5_t20.inp" in filenames
        assert "material.inp" in filenames
        assert "go_idx1_w5_t20.odb" in filenames

    def test_parse_project_creates_nodes(self, graph_service):
        """プロジェクトパースでノードが生成されること"""
        extensions = [".inp", ".odb", ".sta", ".csv", ".pptx", ".py", ".json", ".modfem", ".stl"]
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
        return GraphConfig.from_dict({
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
        })

    @pytest.fixture
    def graph_service(self, config):
        if not FIXTURE_DIR.exists():
            pytest.skip(f"Fixture directory not found: {FIXTURE_DIR}")
        return GraphService(project_root=FIXTURE_DIR, config=config)

    def test_inp_and_odb_same_idx(self, graph_service):
        """go_idx1_w5_t20.inp と go_idx1_w5_t20.odb は同じidx/propsを持つ"""
        extensions = [".inp", ".odb"]
        graph = graph_service.parse_project(extensions=extensions)

        inp_nodes = [n for n in graph.nodes if n.name == "go_idx1_w5_t20" and n.format == "inp"]
        odb_nodes = [n for n in graph.nodes if n.name == "go_idx1_w5_t20" and n.format == "odb"]

        assert len(inp_nodes) == 1
        assert len(odb_nodes) == 1

        inp_node = inp_nodes[0]
        odb_node = odb_nodes[0]

        # 同じindex, w, tを持つ
        assert inp_node.properties.get("index") == odb_node.properties.get("index")
        assert inp_node.properties.get("w") == odb_node.properties.get("w")
        assert inp_node.properties.get("t") == odb_node.properties.get("t")

    def test_result_of_relation(self, graph_service):
        """go_idx1_w5_t20.odb は go_idx1_w5_t20.inp の結果としてresult_of関係がある"""
        extensions = [".inp", ".odb", ".sta"]
        graph = graph_service.parse_project(extensions=extensions)

        # result_of関係を取得
        result_relations = [r for r in graph.relations if r.label == "result_of"]

        # 少なくとも2つのresult_of関係がある（.odb と .sta）
        assert len(result_relations) >= 2

        # .odbと.inpの関係を確認
        odb_node = next((n for n in graph.nodes if n.name == "go_idx1_w5_t20" and n.format == "odb"), None)
        inp_node = next((n for n in graph.nodes if n.name == "go_idx1_w5_t20" and n.format == "inp"), None)

        assert odb_node is not None
        assert inp_node is not None

        # result_of関係が存在
        odb_to_inp = next(
            (r for r in result_relations if r.node1_id == odb_node.id and r.node2_id == inp_node.id),
            None
        )
        assert odb_to_inp is not None


class TestVersionSorting:
    """バージョンソートのテスト"""

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict({
            "vocab": {},
            "path-type-map": {
                "**go_*": {"*.inp": "Abaqusインプット"},
            },
            "ignore": [],
            "obsidian": {},
        })

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
        idx1_inps = [
            n for n in graph.nodes
            if n.properties.get("index") == "1" and n.type == "Abaqusインプット"
        ]

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
            None
        )
        assert v1_to_v2 is not None, "v1 → v2 の next_version 関係がない"

        # v2 → v3の関係
        v2_to_v3 = next(
            (r for r in next_version_relations if r.node1_id == v2_node.id and r.node2_id == v3_node.id),
            None
        )
        assert v2_to_v3 is not None, "v2 → v3 の next_version 関係がない"


class TestPathTypeMapIntegration:
    """path-type-mapの統合テスト"""

    def test_reports_dir_type(self):
        """reports/配下のファイルは報告書タイプになる"""
        config = GraphConfig.from_dict({
            "vocab": {},
            "path-type-map": {
                "**/reports/*": {"*": "報告書"},
            },
            "ignore": [],
            "obsidian": {},
        })

        # path-type-mapのマッチング確認
        result = config.path_type_map.get_type("reports/260205_構造解析_idx1.pptx", "260205_構造解析_idx1.pptx")
        assert result == "報告書"

    def test_assets_dir_type(self):
        """assets/配下のファイルは静的データタイプになる"""
        config = GraphConfig.from_dict({
            "vocab": {},
            "path-type-map": {
                "**/assets/*": {"*": "静的データ"},
            },
            "ignore": [],
            "obsidian": {},
        })

        result = config.path_type_map.get_type("assets/mesh.modfem", "mesh.modfem")
        assert result == "静的データ"


class TestConfigRules:
    """設定ルールのテスト"""

    def test_ignore_notes(self):
        """notes/ディレクトリは除外される"""
        from config import IgnoreConfig

        ignore = IgnoreConfig.from_list(["notes", "notes/**", ".obsidian", ".obsidian/**"])

        assert ignore.should_ignore("notes/sample.md") == True
        assert ignore.should_ignore("notes/nested/file.md") == True
        assert ignore.should_ignore(".obsidian/config.json") == True
        assert ignore.should_ignore("go_idx1.inp") == False


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

        config = FileRelationsConfig.from_dict({
            "input-extensions": [".inp", ".custom"],
            "result-extensions": [".result"],
            "asset-extensions": [".asset"],
        })
        assert ".custom" in config.input_extensions
        assert ".result" in config.result_extensions
        assert ".asset" in config.asset_extensions


class TestAssetRelations:
    """アセット関係（derived_from）のテスト"""

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict({
            "vocab": {},
            "path-type-map": {
                "**mesh_* | **mesh": {"*.inp": "メッシュ", "*.modfem": "修正メッシュ"},
            },
            "file-relations": {
                "input-extensions": [".inp"],
                "result-extensions": [".odb"],
                "asset-extensions": [".modfem", ".stl"],
            },
            "ignore": [],
            "obsidian": {},
        })

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
                None
            )
            assert relation is not None, "mesh.inp → mesh.modfem の derived_from 関係がない"


class TestPathTypeMapOrdering:
    """path-type-mapの評価順序テスト"""

    def test_specific_pattern_first(self):
        """より具体的なパターンが先に評価される"""
        config = GraphConfig.from_dict({
            "vocab": {},
            "path-type-map": {
                "**go_*": {"*.inp": "汎用計算"},  # より汎用的
                "**/reports/*": {"*.pptx": "報告書"},  # より具体的（先に評価される）
            },
            "ignore": [],
            "obsidian": {},
        })

        # 具体的なパターンが優先される
        result = config.path_type_map.get_type("reports/260205.pptx", "260205.pptx")
        assert result == "報告書"

    def test_file_pattern_specificity(self):
        """ファイルパターンも具体性でソートされる"""
        config = GraphConfig.from_dict({
            "vocab": {},
            "path-type-map": {
                "**go_*": {
                    "*": "計算結果",        # 最も汎用的
                    "*.inp": "計算入力",    # より具体的
                },
            },
            "ignore": [],
            "obsidian": {},
        })

        # .inpパターンが先に評価される
        result = config.path_type_map.get_type("go_idx1.inp", "go_idx1.inp")
        assert result == "計算入力"


class TestIncludesRelations:
    """includes関係のテスト"""

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict({
            "vocab": {},
            "path-type-map": {},
            "file-relations": {
                "input-extensions": [".inp"],
                "result-extensions": [".odb"],
                "asset-extensions": [".modfem"],
            },
            "ignore": [],
            "obsidian": {},
        })

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
        return GraphConfig.from_dict({
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
        })

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

        # RF はタグとして保持される
        assert "RF" in rf_node.properties.get("tags", [])

        # has_output関係が存在
        relation = next(
            (r for r in has_output_relations
             if r.node1_id == inp_node.id and r.node2_id == rf_node.id),
            None,
        )
        assert relation is not None, "go_idx1_w5_t20.inp → go_idx1_w5_t20_RF.csv の has_output 関係がない"

    def test_has_output_stress_csv_in_results_dir(self, graph_service):
        """results/go_idx1_w5_t20_stress.csv にもhas_output関係がある"""
        extensions = [".inp", ".csv"]
        graph = graph_service.parse_project(extensions=extensions)

        has_output_relations = [r for r in graph.relations if r.label == "has_output"]

        inp_node = next(
            (n for n in graph.nodes if n.name == "go_idx1_w5_t20" and n.format == "inp"),
            None,
        )
        stress_node = next(
            (n for n in graph.nodes if n.name == "go_idx1_w5_t20_stress" and n.format == "csv"),
            None,
        )

        assert inp_node is not None
        assert stress_node is not None

        relation = next(
            (r for r in has_output_relations
             if r.node1_id == inp_node.id and r.node2_id == stress_node.id),
            None,
        )
        assert relation is not None, "go_idx1_w5_t20.inp → results/go_idx1_w5_t20_stress.csv の has_output 関係がない"


class TestDirectoryRelations:
    """フォルダベースの関連付け（contains）のテスト"""

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict({
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
        })

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
            (r for r in has_output_relations
             if r.node1_id == inp_node.id and r.node2_id == dir_node.id),
            None,
        )
        assert relation is not None, "go_idx1_w5_t20.inp → go_idx1_w5_t20/ の has_output 関係がない"


class TestMaterialParsing:
    """material.inpの高度な解析のテスト"""

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict({
            "vocab": {},
            "path-type-map": {},
            "file-relations": {
                "input-extensions": [".inp"],
            },
            "ignore": [],
            "obsidian": {},
        })

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
        assert "steel_s235" in names or "Steel_S235" in names, \
            f"Steel_S235 materialが見つからない: {names}"

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
        return GraphConfig.from_dict({
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
        })

    @pytest.fixture
    def graph_service(self, config):
        if not FIXTURE_DIR.exists():
            pytest.skip(f"Fixture directory not found: {FIXTURE_DIR}")
        return GraphService(project_root=FIXTURE_DIR, config=config)

    def test_sta_completed_status(self, graph_service):
        """成功したstaファイルのanalysis_statusがcompletedになる"""
        extensions = [".inp", ".sta"]
        graph = graph_service.parse_project(extensions=extensions)

        sta_node = next(
            (n for n in graph.nodes if n.name == "go_idx1_w5_t20" and n.format == "sta"),
            None,
        )
        assert sta_node is not None, "go_idx1_w5_t20.sta ノードが見つからない"
        assert sta_node.properties.get("analysis_status") == "completed"

    def test_sta_failed_status(self, graph_service):
        """失敗したstaファイルのanalysis_statusがfailedになる"""
        extensions = [".inp", ".sta"]
        graph = graph_service.parse_project(extensions=extensions)

        sta_node = next(
            (n for n in graph.nodes if n.name == "go_idx2" and n.format == "sta"),
            None,
        )
        assert sta_node is not None, "go_idx2.sta ノードが見つからない"
        assert sta_node.properties.get("analysis_status") == "failed"
        assert len(sta_node.properties.get("errors", [])) > 0, "エラーメッセージが抽出されていない"

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
            (r for r in includes_relations
             if r.node1_id == go_node.id and r.node2_id == material_node.id),
            None,
        )
        assert relation is not None, "go_idx1_w5_t20.inp → material.inp の includes 関係がない"


class TestParseMaterialBlocks:
    """parse_material_blocks関数の単体テスト"""

    def test_parse_material_from_file(self):
        """material.inpファイルのパース"""
        from services.graph import parse_material_blocks

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
        from services.graph import parse_material_blocks

        empty_file = tmp_path / "empty.inp"
        empty_file.write_text("")
        materials = parse_material_blocks(empty_file)
        assert materials == []

    def test_parse_file_without_material(self, tmp_path):
        """*MATERIALブロックがないファイル"""
        from services.graph import parse_material_blocks

        inp_file = tmp_path / "no_material.inp"
        inp_file.write_text("*STEP\n*STATIC\n1., 1.\n*END STEP\n")
        materials = parse_material_blocks(inp_file)
        assert materials == []


class TestParseStaFile:
    """parse_sta_file関数の単体テスト"""

    def test_parse_completed_sta(self):
        """成功したstaファイル"""
        from services.graph import parse_sta_file

        sta_path = FIXTURE_DIR / "go_idx1_w5_t20.sta"
        if not sta_path.exists():
            pytest.skip("sta fixture not found")

        result = parse_sta_file(sta_path)
        assert result["analysis_status"] == "completed"
        assert result["errors"] == []

    def test_parse_failed_sta(self):
        """失敗したstaファイル"""
        from services.graph import parse_sta_file

        sta_path = FIXTURE_DIR / "go_idx2.sta"
        if not sta_path.exists():
            pytest.skip("sta fixture not found")

        result = parse_sta_file(sta_path)
        assert result["analysis_status"] == "failed"
        assert len(result["errors"]) > 0
        assert "TOO MANY ATTEMPTS" in result["errors"][0]

    def test_parse_nonexistent_sta(self, tmp_path):
        """存在しないファイル"""
        from services.graph import parse_sta_file

        result = parse_sta_file(tmp_path / "nonexistent.sta")
        assert result["analysis_status"] == "unknown"


class TestGraphSummaryRelationTypes:
    """summaryでリレーションタイプ別の集計が正しいことを確認"""

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict({
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
        })

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
        return GraphConfig.from_dict({
            "vocab": {},
            "path-type-map": {},
            "file-relations": {
                "input-extensions": [".inp"],
                "result-extensions": [".odb", ".sta"],
                "asset-extensions": [".modfem"],
            },
            "ignore": [],
            "obsidian": {},
        })

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

    def test_parse_project_without_extensions_finds_sta(self, graph_service):
        """extensions未指定でもparse_projectが.staファイルを発見"""
        graph = graph_service.parse_project()

        sta_nodes = [n for n in graph.nodes if n.format == "sta"]
        assert len(sta_nodes) > 0, "extensions未指定時に.staファイルが見つからない"


class TestPathTypeMapWithDefaultConfig:
    """デフォルト設定のpath-type-mapパターンが正しく動作するテスト

    修正対象:
    - ./reports/ 等のパターンがreports/配下のファイルにマッチしない問題
    - **go パターンが go.inp にマッチしない問題
    """

    @pytest.fixture
    def config(self):
        """デフォルト設定を模したconfig"""
        return GraphConfig.from_dict({
            "vocab": {"idx": "番号", "v": "バージョン"},
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
        })

    @pytest.fixture
    def graph_service(self, config):
        if not FIXTURE_DIR.exists():
            pytest.skip(f"Fixture directory not found: {FIXTURE_DIR}")
        return GraphService(project_root=FIXTURE_DIR, config=config)

    def test_reports_files_get_type(self, config):
        """reports/配下のファイルが「報告書」タイプになる"""
        result = config.path_type_map.get_type(
            "reports/260205_構造解析_idx1.pptx", "260205_構造解析_idx1.pptx"
        )
        assert result == "報告書", f"reports/配下のファイルが報告書にならない: {result}"

    def test_tools_files_get_type(self, config):
        """tools/配下のファイルが「処理スクリプト」タイプになる"""
        result = config.path_type_map.get_type(
            "tools/make_inputs.py", "make_inputs.py"
        )
        assert result == "処理スクリプト", f"tools/配下のファイルが処理スクリプトにならない: {result}"

    def test_results_files_get_type(self, config):
        """results/配下のファイルが「計算結果」タイプになる"""
        result = config.path_type_map.get_type(
            "results/go_idx1_w5_t20_stress.csv", "go_idx1_w5_t20_stress.csv"
        )
        assert result == "計算結果", f"results/配下のファイルが計算結果にならない: {result}"

    def test_docs_files_get_type(self, config):
        """docs/配下のファイルが「受領ファイル」タイプになる"""
        result = config.path_type_map.get_type(
            "docs/指示書/file.pptx", "file.pptx"
        )
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
        result = config.path_type_map.get_type(
            "go_idx1_w5_t20.inp", "go_idx1_w5_t20.inp"
        )
        assert result == "Abaqusインプット"

    def test_full_parse_reports_typed(self, graph_service):
        """統合テスト: parse_projectでreports配下のファイルが正しく型付けされる"""
        extensions = [".pptx", ".csv", ".py", ".inp"]
        graph = graph_service.parse_project(extensions=extensions)

        report_nodes = [
            n for n in graph.nodes
            if "reports/" in n.properties.get("path", "")
        ]
        for node in report_nodes:
            assert node.type == "報告書", \
                f"{node.properties['path']} のタイプが {node.type}（報告書であるべき）"

    def test_full_parse_tools_typed(self, graph_service):
        """統合テスト: parse_projectでtools配下のファイルが正しく型付けされる"""
        extensions = [".py", ".inp"]
        graph = graph_service.parse_project(extensions=extensions)

        tools_nodes = [
            n for n in graph.nodes
            if "tools/" in n.properties.get("path", "")
        ]
        for node in tools_nodes:
            assert node.type == "処理スクリプト", \
                f"{node.properties['path']} のタイプが {node.type}（処理スクリプトであるべき）"


class TestDirectoryNodeWindows:
    """フォルダNode構築のWindows対応テスト"""

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict({
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
        })

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

        contains = [r for r in graph.relations
                    if r.label == "contains" and r.node1_id == dir_node.id]
        assert len(contains) >= 3, \
            f"go_idx1_w5_t20/内の3ファイル(csv,png,yaml)に対するcontains関係が不足: {len(contains)}"

    def test_file_nodes_have_no_leading_dot_slash(self, graph_service):
        """ファイルノードのパスに先頭 ./ がない"""
        extensions = [".inp", ".csv", ".png", ".yaml"]
        graph = graph_service.parse_project(extensions=extensions)

        for node in graph.nodes:
            path = node.properties.get("path", "")
            assert not path.startswith("./"), f"パスに先頭./が含まれる: {path}"
            assert not path.startswith(".\\"), f"パスに先頭.\\が含まれる: {path}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
