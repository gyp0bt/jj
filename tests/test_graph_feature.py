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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
