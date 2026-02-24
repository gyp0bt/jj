"""Neo4jコネクタのテスト

Neo4jサーバーが不要なテスト:
- shared/パッケージのスキーマ定義
- プロパティ変換ロジック
- Cypherファイルエクスポート
- Neo4jConfig設定読み込み

Neo4jサーバーが必要なテスト:
- export_graph() による直接書き込み（マーカーでスキップ）

[READMEへ戻る](../README.md)
"""

import json
from unittest.mock import MagicMock

import pytest

from jj_types import GraphModel, Node, Relation
from services.export.connectors.neo4j import (
    Neo4jConnector,
    _build_node_properties,
    _escape_cypher_string,
    _format_cypher_value,
    _is_homogeneous_list,
    _sanitize_property_value,
)
from shared.config import Neo4jConfig
from shared.neo4j_schema import (
    LABEL_TO_RELTYPE,
    TYPE_TO_LABEL,
    NodeLabel,
    RelType,
    get_neo4j_label,
    get_neo4j_reltype,
)
from shared.types import Neo4jNodeData, Neo4jRelationData

# ===== テストデータ =====


def _make_test_graph() -> GraphModel:
    """テスト用の小さなGraphModelを作成"""
    nodes = [
        Node(
            id=1,
            type="calculation_input",
            name="go_idx1_v1",
            format="inp",
            properties={
                "path": "go_idx1_v1.inp",
                "index": "1",
                "version": "1",
                "active": "true",
                "tags": ["sample", "test"],
            },
        ),
        Node(
            id=2,
            type="mesh",
            name="mesh_box",
            format="cdb",
            properties={
                "path": "mesh_box.cdb",
                "mesh_node_count": 1234,
                "mesh_element_count": 5678,
            },
        ),
        Node(
            id=3,
            type="abaqus_material",
            name="Steel",
            format="",
            properties={
                "defined_in": "material.inp",
                "keywords": {"elastic": [[210000, 0.3]], "density": [[7.85e-9]]},
            },
        ),
        Node(
            id=4,
            type="folder",
            name="reports",
            format="",
            properties={"path": "reports/"},
        ),
    ]
    relations = [
        Relation(id=1, label="includes", node1_id=1, node2_id=2),
        Relation(id=2, label="defined_in", node1_id=3, node2_id=1),
        Relation(id=3, label="contains", node1_id=4, node2_id=1),
        Relation(id=4, label="next_version", node1_id=1, node2_id=1),
    ]
    return GraphModel(nodes=nodes, relations=relations)


# ===== shared/neo4j_schema テスト =====


class TestNodeLabel:
    """NodeLabel定義のテスト"""

    def test_jj_labels_defined(self):
        assert NodeLabel.JJ_FILE == "JJFile"
        assert NodeLabel.JJ_MATERIAL == "JJMaterial"
        assert NodeLabel.JJ_RUN == "JJRun"
        assert NodeLabel.JJ_TAG == "JJTag"

    def test_jjdb_labels_defined(self):
        assert NodeLabel.JJDB_MATERIAL == "JJDBMaterial"
        assert NodeLabel.JJDB_TEST == "JJDBTest"


class TestRelType:
    """RelType定義のテスト"""

    def test_jj_reltypes_defined(self):
        assert RelType.INCLUDES == "INCLUDES"
        assert RelType.HAS_OUTPUT == "HAS_OUTPUT"
        assert RelType.DERIVED_FROM == "DERIVED_FROM"
        assert RelType.RESULT_OF == "RESULT_OF"
        assert RelType.CONTAINS == "CONTAINS"
        assert RelType.NEXT_VERSION == "NEXT_VERSION"
        assert RelType.SAME_INDEX_GROUP == "SAME_INDEX_GROUP"
        assert RelType.DEFINED_IN == "DEFINED_IN"
        assert RelType.ASSIGNED_TO == "ASSIGNED_TO"
        assert RelType.MENTIONED_IN == "MENTIONED_IN"

    def test_cross_reltypes_defined(self):
        assert RelType.MATCHES == "MATCHES"
        assert RelType.REFERENCES == "REFERENCES"


class TestLabelToReltype:
    """LABEL_TO_RELTYPEマッピングのテスト"""

    def test_all_jj_labels_mapped(self):
        """jjで使用される全ラベルがマッピングされている"""
        expected_labels = [
            "next_version",
            "same_index_group",
            "includes",
            "has_output",
            "derived_from",
            "result_of",
            "contains",
            "tagged",
            "uses_material",
            "executed_by",
            "generated",
            "defined_in",
            "assigned_to",
            "mentioned_in",
        ]
        for label in expected_labels:
            assert label in LABEL_TO_RELTYPE, f"{label} がLABEL_TO_RELTYPEに未定義"

    def test_values_are_uppercase(self):
        """マッピング先は全て大文字"""
        for label, reltype in LABEL_TO_RELTYPE.items():
            assert reltype == reltype.upper(), f"{label} → {reltype} が大文字でない"


class TestTypeToLabel:
    """TYPE_TO_LABELマッピングのテスト"""

    def test_file_types_map_to_jjfile(self):
        file_types = [
            "calculation_input",
            "mesh",
            "material",
            "step",
            "result",
            "asset",
            "folder",
            "output",
            "other",
        ]
        for t in file_types:
            assert TYPE_TO_LABEL[t] == NodeLabel.JJ_FILE

    def test_special_types(self):
        assert TYPE_TO_LABEL["abaqus_material"] == NodeLabel.JJ_MATERIAL
        assert TYPE_TO_LABEL["run"] == NodeLabel.JJ_RUN
        assert TYPE_TO_LABEL["tag"] == NodeLabel.JJ_TAG


class TestGetNeo4jLabel:
    """get_neo4j_label関数のテスト"""

    def test_known_types(self):
        assert get_neo4j_label("calculation_input") == "JJFile"
        assert get_neo4j_label("abaqus_material") == "JJMaterial"
        assert get_neo4j_label("run") == "JJRun"

    def test_unknown_type_defaults_to_jjfile(self):
        assert get_neo4j_label("unknown_type") == "JJFile"
        assert get_neo4j_label("") == "JJFile"


class TestGetNeo4jReltype:
    """get_neo4j_reltype関数のテスト"""

    def test_known_labels(self):
        assert get_neo4j_reltype("includes") == "INCLUDES"
        assert get_neo4j_reltype("has_output") == "HAS_OUTPUT"
        assert get_neo4j_reltype("next_version") == "NEXT_VERSION"

    def test_unknown_label_uppercased(self):
        assert get_neo4j_reltype("custom_relation") == "CUSTOM_RELATION"


# ===== shared/types テスト =====


class TestNeo4jNodeData:
    """Neo4jNodeDataのテスト"""

    def test_basic_creation(self):
        data = Neo4jNodeData(
            label="JJFile",
            jj_id=1,
            name="test",
            node_type="calculation_input",
            node_format="inp",
            project="test_project",
        )
        assert data.label == "JJFile"
        assert data.jj_id == 1
        assert data.properties == {}

    def test_with_properties(self):
        data = Neo4jNodeData(
            label="JJFile",
            jj_id=1,
            name="test",
            node_type="calculation_input",
            node_format="inp",
            project="test_project",
            properties={"index": "1", "version": "2"},
        )
        assert data.properties["index"] == "1"


class TestNeo4jRelationData:
    """Neo4jRelationDataのテスト"""

    def test_basic_creation(self):
        data = Neo4jRelationData(
            rel_type="INCLUDES",
            source_jj_id=1,
            target_jj_id=2,
            project="test_project",
        )
        assert data.rel_type == "INCLUDES"
        assert data.properties == {}


# ===== shared/config テスト =====


class TestNeo4jConfig:
    """Neo4jConfig設定のテスト"""

    def test_default_values(self):
        config = Neo4jConfig()
        assert config.uri == "bolt://localhost:7687"
        assert config.user == "neo4j"
        assert config.password == "password"
        assert config.database == "neo4j"

    def test_from_dict(self):
        config = Neo4jConfig.from_dict(
            {
                "uri": "bolt://db.example.com:7687",
                "user": "admin",
                "password": "secret",
                "database": "mydb",
            }
        )
        assert config.uri == "bolt://db.example.com:7687"
        assert config.user == "admin"
        assert config.password == "secret"
        assert config.database == "mydb"

    def test_from_dict_partial(self):
        """一部のみ指定した場合、残りはデフォルト値"""
        config = Neo4jConfig.from_dict({"uri": "bolt://custom:7687"})
        assert config.uri == "bolt://custom:7687"
        assert config.user == "neo4j"

    def test_from_jj_config_no_config(self, tmp_path):
        """config.yamlにneo4jセクションがない場合、デフォルト値"""
        config = Neo4jConfig.from_jj_config(tmp_path)
        assert config.uri == "bolt://localhost:7687"


# ===== services/connectors/neo4j プロパティ変換テスト =====


class TestSanitizePropertyValue:
    """_sanitize_property_value関数のテスト"""

    def test_none(self):
        assert _sanitize_property_value(None) is None

    def test_bool(self):
        assert _sanitize_property_value(True) is True
        assert _sanitize_property_value(False) is False

    def test_int(self):
        assert _sanitize_property_value(42) == 42

    def test_float(self):
        assert _sanitize_property_value(3.14) == 3.14

    def test_string(self):
        assert _sanitize_property_value("hello") == "hello"

    def test_homogeneous_list(self):
        assert _sanitize_property_value(["a", "b", "c"]) == ["a", "b", "c"]
        assert _sanitize_property_value([1, 2, 3]) == [1, 2, 3]

    def test_mixed_numeric_list(self):
        """int/floatの混在リストは許容"""
        result = _sanitize_property_value([1, 2.5, 3])
        assert result == [1, 2.5, 3]

    def test_mixed_type_list_becomes_json(self):
        """異なる型の混在リストはJSON文字列化"""
        result = _sanitize_property_value(["a", 1, True])
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed == ["a", 1, True]

    def test_dict_becomes_json(self):
        """dictはJSON文字列化"""
        result = _sanitize_property_value({"key": "value"})
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed == {"key": "value"}

    def test_empty_list(self):
        assert _sanitize_property_value([]) is None

    def test_list_with_none(self):
        """Noneを含むリストはNoneを除外"""
        result = _sanitize_property_value(["a", None, "b"])
        assert result == ["a", "b"]


class TestIsHomogeneousList:
    """_is_homogeneous_list関数のテスト"""

    def test_empty_list(self):
        assert _is_homogeneous_list([]) is True

    def test_all_strings(self):
        assert _is_homogeneous_list(["a", "b", "c"]) is True

    def test_all_ints(self):
        assert _is_homogeneous_list([1, 2, 3]) is True

    def test_mixed_numeric(self):
        """int/floatの混在は互換性あり"""
        assert _is_homogeneous_list([1, 2.5, 3]) is True

    def test_mixed_types(self):
        assert _is_homogeneous_list(["a", 1]) is False


class TestBuildNodeProperties:
    """_build_node_properties関数のテスト"""

    def test_basic_properties(self):
        node = Node(
            id=1,
            type="calculation_input",
            name="go_idx1",
            format="inp",
            properties={"path": "go_idx1.inp", "index": "1"},
        )
        props = _build_node_properties(node, "test_project")
        assert props["jj_id"] == 1
        assert props["name"] == "go_idx1"
        assert props["type"] == "calculation_input"
        assert props["format"] == "inp"
        assert props["project"] == "test_project"
        assert props["path"] == "go_idx1.inp"
        assert props["index"] == "1"

    def test_dict_property_serialized(self):
        node = Node(
            id=1,
            type="abaqus_material",
            name="Steel",
            format="",
            properties={"keywords": {"elastic": [[210000, 0.3]]}},
        )
        props = _build_node_properties(node, "proj")
        # dictはJSON文字列化される
        assert isinstance(props["keywords"], str)
        parsed = json.loads(props["keywords"])
        assert parsed == {"elastic": [[210000, 0.3]]}

    def test_none_property_excluded(self):
        node = Node(
            id=1,
            type="calculation_input",
            name="test",
            format="inp",
            properties={"value": None, "name_val": "ok"},
        )
        props = _build_node_properties(node, "proj")
        assert "value" not in props
        assert props["name_val"] == "ok"

    def test_hyphen_key_converted(self):
        """ハイフン含みキーはアンダースコアに変換"""
        node = Node(
            id=1,
            type="other",
            name="test",
            format="",
            properties={"some-key": "value"},
        )
        props = _build_node_properties(node, "proj")
        assert "some_key" in props
        assert props["some_key"] == "value"


# ===== Cypherフォーマットテスト =====


class TestEscapeCypherString:
    """_escape_cypher_string関数のテスト"""

    def test_no_escape_needed(self):
        assert _escape_cypher_string("hello") == "hello"

    def test_single_quote(self):
        assert _escape_cypher_string("it's") == "it\\'s"

    def test_double_quote(self):
        assert _escape_cypher_string('say "hi"') == 'say \\"hi\\"'

    def test_backslash(self):
        assert _escape_cypher_string("a\\b") == "a\\\\b"


class TestFormatCypherValue:
    """_format_cypher_value関数のテスト"""

    def test_null(self):
        assert _format_cypher_value(None) == "null"

    def test_bool(self):
        assert _format_cypher_value(True) == "true"
        assert _format_cypher_value(False) == "false"

    def test_int(self):
        assert _format_cypher_value(42) == "42"

    def test_float(self):
        assert _format_cypher_value(3.14) == "3.14"

    def test_string(self):
        assert _format_cypher_value("hello") == '"hello"'

    def test_list(self):
        assert _format_cypher_value([1, 2, 3]) == "[1, 2, 3]"

    def test_string_with_quotes(self):
        result = _format_cypher_value('say "hi"')
        assert result == '"say \\"hi\\""'


# ===== Cypherエクスポートテスト =====


class TestExportCypher:
    """export_cypher関数のテスト（ファイル出力）"""

    def test_basic_export(self, tmp_path):
        graph = _make_test_graph()
        connector = Neo4jConnector(project_root=tmp_path)
        output = tmp_path / "test.cypher"

        result_path = connector.export_cypher(graph, output_path=output)

        assert result_path == output
        assert output.exists()
        content = output.read_text(encoding="utf-8")

        # ヘッダーの確認
        assert "// jj Neo4j Export:" in content
        assert f"Nodes: {len(graph.nodes)}" in content

        # ノードのMERGE文が含まれる
        assert "MERGE (n:JJFile" in content
        assert "MERGE (n:JJMaterial" in content

        # リレーションのMERGE文が含まれる
        assert "MERGE (a)-[:INCLUDES" in content
        assert "MERGE (a)-[:DEFINED_IN" in content
        assert "MERGE (a)-[:CONTAINS" in content
        assert "MERGE (a)-[:NEXT_VERSION" in content

    def test_export_with_clear(self, tmp_path):
        graph = _make_test_graph()
        connector = Neo4jConnector(project_root=tmp_path)
        output = tmp_path / "test.cypher"

        connector.export_cypher(graph, output_path=output, clear_project=True)
        content = output.read_text(encoding="utf-8")

        assert "DETACH DELETE" in content

    def test_export_default_path(self, tmp_path):
        graph = GraphModel(
            nodes=[Node(id=1, type="other", name="test", format="txt")],
            relations=[],
        )
        connector = Neo4jConnector(project_root=tmp_path)

        result_path = connector.export_cypher(graph)

        assert result_path == tmp_path / ".j2" / "storage" / "export.cypher"
        assert result_path.exists()

    def test_export_empty_graph(self, tmp_path):
        graph = GraphModel.empty()
        connector = Neo4jConnector(project_root=tmp_path)
        output = tmp_path / "empty.cypher"

        connector.export_cypher(graph, output_path=output)
        content = output.read_text(encoding="utf-8")

        assert "Nodes: 0, Relations: 0" in content

    def test_export_node_properties_in_cypher(self, tmp_path):
        """Cypherエクスポートにノードプロパティが含まれる"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="calculation_input",
                    name="go_idx1",
                    format="inp",
                    properties={"index": "1", "active": "true"},
                ),
            ],
            relations=[],
        )
        connector = Neo4jConnector(project_root=tmp_path)
        output = tmp_path / "props.cypher"

        connector.export_cypher(graph, output_path=output)
        content = output.read_text(encoding="utf-8")

        assert 'name: "go_idx1"' in content
        assert 'index: "1"' in content
        assert 'active: "true"' in content

    def test_export_special_characters_escaped(self, tmp_path):
        """特殊文字がエスケープされる"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="other",
                    name='file_with"quotes',
                    format="txt",
                    properties={"note": "it's a test"},
                ),
            ],
            relations=[],
        )
        connector = Neo4jConnector(project_root=tmp_path)
        output = tmp_path / "escape.cypher"

        connector.export_cypher(graph, output_path=output)
        content = output.read_text(encoding="utf-8")

        # エスケープされている
        assert '\\"quotes' in content
        assert "\\'s" in content


# ===== Neo4jConnector初期化テスト =====


class TestNeo4jConnectorInit:
    """Neo4jConnector初期化のテスト"""

    def test_default_project_name(self, tmp_path):
        connector = Neo4jConnector(project_root=tmp_path)
        assert connector.project == tmp_path.name

    def test_custom_config(self, tmp_path):
        config = Neo4jConfig(
            uri="bolt://custom:7687",
            user="admin",
            password="secret",
        )
        connector = Neo4jConnector(project_root=tmp_path, config=config)
        assert connector.config.uri == "bolt://custom:7687"
        assert connector.config.user == "admin"

    def test_driver_not_initialized_at_creation(self, tmp_path):
        """ドライバはコンストラクタでは初期化されない（遅延初期化）"""
        connector = Neo4jConnector(project_root=tmp_path)
        assert connector._driver is None


# ===== Neo4jドライバのモックテスト =====


class TestNeo4jConnectorWithMock:
    """Neo4jドライバをモックしたテスト"""

    def test_export_graph_calls_session(self, tmp_path):
        """export_graphがセッションを使用してクエリを実行する"""
        graph = _make_test_graph()
        connector = Neo4jConnector(project_root=tmp_path)

        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_record = {"total": 4, "updated": 0}
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        connector._driver = mock_driver

        connector.export_graph(graph)

        # セッションが開かれたことを確認
        mock_driver.session.assert_called()
        # runが呼ばれたことを確認（ノードとリレーションのバッチ）
        assert mock_session.run.call_count > 0

    def test_export_graph_with_clear(self, tmp_path):
        """clear_project=Trueで削除クエリが発行される"""
        graph = GraphModel(
            nodes=[Node(id=1, type="other", name="test", format="txt")],
            relations=[],
        )
        connector = Neo4jConnector(project_root=tmp_path)

        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"total": 1, "updated": 0}
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        connector._driver = mock_driver

        connector.export_graph(graph, clear_project=True)

        # DETACH DELETE クエリが発行されたことを確認
        calls = mock_session.run.call_args_list
        delete_calls = [c for c in calls if "DETACH DELETE" in str(c)]
        assert len(delete_calls) > 0

    def test_verify_connection_success(self, tmp_path):
        connector = Neo4jConnector(project_root=tmp_path)
        mock_driver = MagicMock()
        mock_driver.verify_connectivity.return_value = None
        connector._driver = mock_driver

        assert connector.verify_connection() is True

    def test_verify_connection_failure(self, tmp_path):
        connector = Neo4jConnector(project_root=tmp_path)
        mock_driver = MagicMock()
        mock_driver.verify_connectivity.side_effect = Exception("Connection refused")
        connector._driver = mock_driver

        assert connector.verify_connection() is False

    def test_close_driver(self, tmp_path):
        connector = Neo4jConnector(project_root=tmp_path)
        mock_driver = MagicMock()
        connector._driver = mock_driver

        connector.close()

        mock_driver.close.assert_called_once()
        assert connector._driver is None

    def test_close_without_driver(self, tmp_path):
        """ドライバ未初期化でもcloseが安全に呼べる"""
        connector = Neo4jConnector(project_root=tmp_path)
        connector.close()  # エラーにならない


# ===== CLIテスト =====


class TestExportCLIArgs:
    """export CLIの引数テスト"""

    @pytest.fixture(autouse=True)
    def _skip_if_no_paramiko(self):
        """paramikoがない環境ではCLIテストをスキップ"""
        try:
            from cli.graph import add_top_level_graph_commands  # noqa: F401
        except (ImportError, ModuleNotFoundError):
            pytest.skip("paramikoが未インストール（CLI importチェーン依存）")

    def test_neo4j_target_in_choices(self):
        """neo4jとcypherがtargetの選択肢にある"""
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()

        from cli.graph import add_top_level_graph_commands

        add_top_level_graph_commands(subparsers)

        # neo4j
        args = parser.parse_args(["export", "--target", "neo4j"])
        assert args.target == "neo4j"

        # cypher
        args = parser.parse_args(["export", "--target", "cypher"])
        assert args.target == "cypher"

    def test_neo4j_options(self):
        """Neo4j固有オプションが利用可能"""
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()

        from cli.graph import add_top_level_graph_commands

        add_top_level_graph_commands(subparsers)

        args = parser.parse_args(
            [
                "export",
                "--target",
                "neo4j",
                "--clear",
                "--neo4j-uri",
                "bolt://custom:7687",
                "--neo4j-user",
                "admin",
                "--neo4j-password",
                "secret",
            ]
        )
        assert args.target == "neo4j"
        assert args.clear is True
        assert args.neo4j_uri == "bolt://custom:7687"
        assert args.neo4j_user == "admin"
        assert args.neo4j_password == "secret"


# ===== 統合テスト（GraphModel → Cypher変換の完全パス）=====


class TestEndToEndCypherExport:
    """GraphModelからCypherファイルまでの完全パステスト"""

    def test_all_node_types_have_labels(self, tmp_path):
        """全ノードタイプがNeo4jラベルにマッピングされる"""
        graph = _make_test_graph()
        connector = Neo4jConnector(project_root=tmp_path)
        output = tmp_path / "e2e.cypher"

        connector.export_cypher(graph, output_path=output)
        content = output.read_text(encoding="utf-8")

        # 各ラベルのMERGE文が存在する
        assert "MERGE (n:JJFile" in content  # calculation_input, mesh, folder
        assert "MERGE (n:JJMaterial" in content  # abaqus_material

    def test_all_relation_labels_mapped(self, tmp_path):
        """全リレーションラベルがNeo4jタイプにマッピングされる"""
        graph = _make_test_graph()
        connector = Neo4jConnector(project_root=tmp_path)
        output = tmp_path / "e2e.cypher"

        connector.export_cypher(graph, output_path=output)
        content = output.read_text(encoding="utf-8")

        # includes → INCLUDES
        assert ":INCLUDES" in content
        # defined_in → DEFINED_IN
        assert ":DEFINED_IN" in content
        # contains → CONTAINS
        assert ":CONTAINS" in content

    def test_project_name_in_cypher(self, tmp_path):
        """プロジェクト名がCypherに含まれる"""
        graph = GraphModel(
            nodes=[Node(id=1, type="other", name="test", format="txt")],
            relations=[],
        )
        connector = Neo4jConnector(project_root=tmp_path)
        output = tmp_path / "proj.cypher"

        connector.export_cypher(graph, output_path=output)
        content = output.read_text(encoding="utf-8")

        assert f'project: "{tmp_path.name}"' in content

    def test_large_graph_export(self, tmp_path):
        """大量ノードのエクスポートが正常に完了する"""
        nodes = [
            Node(
                id=i,
                type="calculation_input",
                name=f"go_idx{i}",
                format="inp",
                properties={"index": str(i)},
            )
            for i in range(1, 101)
        ]
        relations = [Relation(id=i, label="next_version", node1_id=i, node2_id=i + 1) for i in range(1, 100)]
        graph = GraphModel(nodes=nodes, relations=relations)

        connector = Neo4jConnector(project_root=tmp_path)
        output = tmp_path / "large.cypher"

        connector.export_cypher(graph, output_path=output)
        content = output.read_text(encoding="utf-8")

        # 全ノードとリレーションが出力されている
        assert content.count("MERGE (n:JJFile") == 100
        assert content.count(":NEXT_VERSION") == 99


# ===== メッシュプロパティのNeo4jエクスポートテスト =====


class TestMeshPropertiesExport:
    """mesh_element_quality/mesh_topology_groupsのCypherエクスポート検証"""

    def test_mesh_element_quality_exported_as_json(self, tmp_path):
        """mesh_element_qualityはJSON文字列としてエクスポートされる"""
        quality_data = {
            "C3D8": {
                "element_count": 100,
                "quality": {"min_volume": 0.001, "max_aspect_ratio": 3.5},
            },
            "C3D4": {
                "element_count": 50,
                "quality": {"min_volume": 0.0005, "max_aspect_ratio": 5.2},
            },
        }
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="mesh",
                    name="mesh_box",
                    format="inp",
                    properties={"mesh_element_quality": quality_data},
                ),
            ],
            relations=[],
        )
        connector = Neo4jConnector(project_root=tmp_path)
        output = tmp_path / "mesh_quality.cypher"
        connector.export_cypher(graph, output_path=output)
        content = output.read_text(encoding="utf-8")

        # dict型はJSON文字列化される
        assert "mesh_element_quality:" in content
        assert "C3D8" in content
        assert "element_count" in content

    def test_mesh_topology_groups_exported_as_json(self, tmp_path):
        """mesh_topology_groupsはJSON文字列としてエクスポートされる"""
        topology = [["BODY", "SKIN"], ["SUPPORT"]]
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="mesh",
                    name="mesh_box",
                    format="inp",
                    properties={"mesh_topology_groups": topology},
                ),
            ],
            relations=[],
        )
        connector = Neo4jConnector(project_root=tmp_path)
        output = tmp_path / "mesh_topo.cypher"
        connector.export_cypher(graph, output_path=output)
        content = output.read_text(encoding="utf-8")

        # list[list]型はJSON文字列化される（同種型でないため）
        assert "mesh_topology_groups:" in content
        assert "BODY" in content
        assert "SUPPORT" in content

    def test_version_diff_node_label(self, tmp_path):
        """version_diffタイプはJJFileラベルにマッピングされる"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="version_diff",
                    name="diff_v1_vs_v2",
                    format="diff",
                    properties={
                        "diff_unified": "```diff\n- old\n+ new\n```",
                        "has_diffs": True,
                    },
                ),
            ],
            relations=[],
        )
        connector = Neo4jConnector(project_root=tmp_path)
        output = tmp_path / "diff.cypher"
        connector.export_cypher(graph, output_path=output)
        content = output.read_text(encoding="utf-8")

        assert "MERGE (n:JJFile" in content
        assert "diff_unified:" in content

    def test_build_node_properties_sanitizes_mesh_data(self, tmp_path):
        """_build_node_propertiesがメッシュプロパティを正しくサニタイズする"""
        from services.export.connectors.neo4j import _build_node_properties

        node = Node(
            id=1,
            type="mesh",
            name="mesh_test",
            format="inp",
            properties={
                "mesh_node_count": 1000,
                "mesh_element_count": 500,
                "mesh_element_quality": {"C3D8": {"element_count": 500}},
                "mesh_topology_groups": [["A", "B"], ["C"]],
                "mesh_elset_summary": {"BODY": {"count": 300}},
            },
        )
        props = _build_node_properties(node, "test_project")

        # スカラー値はそのまま
        assert props["mesh_node_count"] == 1000
        assert props["mesh_element_count"] == 500
        # dict型はJSON文字列化
        assert isinstance(props["mesh_element_quality"], str)
        assert "C3D8" in props["mesh_element_quality"]
        # list[list]はJSON文字列化
        assert isinstance(props["mesh_topology_groups"], str)
        assert "A" in props["mesh_topology_groups"]
        # dictはJSON文字列化
        assert isinstance(props["mesh_elset_summary"], str)


class TestPropertyKeyConstants:
    """PropertyKeyクラスの定数定義テスト"""

    def test_property_key_values(self):
        """PropertyKeyの定数値が正しい"""
        from shared.neo4j_schema import PropertyKey

        assert PropertyKey.MESH_ELEMENT_QUALITY == "mesh_element_quality"
        assert PropertyKey.MESH_TOPOLOGY_GROUPS == "mesh_topology_groups"
        assert PropertyKey.MESH_NODE_COUNT == "mesh_node_count"
        assert PropertyKey.MESH_ELEMENT_COUNT == "mesh_element_count"
        assert PropertyKey.DIFF_UNIFIED == "diff_unified"

    def test_version_diff_in_type_to_label(self):
        """version_diffがTYPE_TO_LABELに含まれる"""
        from shared.neo4j_schema import TYPE_TO_LABEL, NodeLabel

        assert "version_diff" in TYPE_TO_LABEL
        assert TYPE_TO_LABEL["version_diff"] == NodeLabel.JJ_FILE
