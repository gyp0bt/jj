"""Obsidianコネクタのテスト

重要な命名規則のテスト:
- 実ファイル: "O-"プレフィックスなし
- Obsidianファイル: "O-"プレフィックス付き
- ディレクトリ: "O-"プレフィックスなし

[READMEへ戻る](../README.md)
"""

import pytest

from config import GraphConfig
from jj_types import GraphModel, Node
from services.parse.connectors.obsidian import (
    ObsidianConnector,
    _coerce_property_value,
    from_obsidian_filename,
    get_directory_for_type,
    to_obsidian_filename,
    to_obsidian_link,
)


class TestObsidianNaming:
    """O-プレフィックス命名規則のテスト"""

    def test_to_obsidian_filename_basic(self):
        """実ファイル名 → Obsidianファイル名"""
        assert to_obsidian_filename("go_test_v1.inp") == "O-go_test_v1.inp.md"
        assert to_obsidian_filename("mesh_box.cdb") == "O-mesh_box.cdb.md"
        assert to_obsidian_filename("material_steel.yaml") == "O-material_steel.yaml.md"

    def test_from_obsidian_filename_basic(self):
        """Obsidianファイル名 → 実ファイル名"""
        assert from_obsidian_filename("O-go_test_v1.inp.md") == "go_test_v1.inp"
        assert from_obsidian_filename("O-mesh_box.cdb.md") == "mesh_box.cdb"

    def test_roundtrip_filename_conversion(self):
        """ファイル名変換のラウンドトリップ"""
        real_names = [
            "go_test_v1.inp",
            "mesh_box.cdb",
            "material_steel.yaml",
            "step_load.dat",
            "report_final.pptx",
        ]
        for real_name in real_names:
            obsidian_name = to_obsidian_filename(real_name)
            converted_back = from_obsidian_filename(obsidian_name)
            assert converted_back == real_name, f"Failed for {real_name}"

    def test_to_obsidian_link(self):
        """実ファイル名 → Obsidianリンク形式"""
        assert to_obsidian_link("go_test_v1.inp") == "[[O-go_test_v1.inp]]"
        assert to_obsidian_link("mesh_box.cdb") == "[[O-mesh_box.cdb]]"

    def test_get_directory_for_type_no_prefix(self):
        """ディレクトリ名にはO-プレフィックスなし"""
        assert get_directory_for_type("go") == "go"
        assert get_directory_for_type("mesh") == "mesh"
        assert get_directory_for_type("docs") == "docs"

    def test_get_directory_for_type_strips_prefix(self):
        """入力にO-があっても除去される"""
        assert get_directory_for_type("O-go") == "go"
        assert get_directory_for_type("O-mesh") == "mesh"


class TestObsidianConnector:
    """ObsidianConnectorのテスト"""

    @pytest.fixture
    def connector(self, tmp_path):
        """テスト用コネクタ"""
        return ObsidianConnector(project_root=tmp_path)

    @pytest.fixture
    def sample_node(self):
        """テスト用ノード"""
        return Node(
            id=1,
            type="go",
            name="go_test_v1",
            format="inp",
            properties={
                "path": "inp/go_test_v1.inp",
                "index": "1",
                "version": "1",
            },
        )

    def test_get_md_path_go_type(self, connector, sample_node):
        """goタイプのmdファイルパス生成"""
        md_path = connector.get_md_path(sample_node)

        # ディレクトリはO-なし、ファイル名はO-付き
        # props直下の{type}/配下に配置（inp/は挟まない）
        path_str = str(md_path).replace("\\", "/")
        assert "/go/" in path_str
        assert "inp/go/" not in path_str  # inp/は挟まない
        assert md_path.name == "O-go_test_v1.inp.md"
        assert "O-go/" not in path_str  # ディレクトリにO-がないことを確認

    def test_get_md_path_docs_type(self, connector):
        """docsタイプのmdファイルパス生成"""
        node = Node(
            id=2,
            type="docs",
            name="readme",
            format="md",
            properties={"path": "docs/readme.md"},
        )
        md_path = connector.get_md_path(node)

        # docs/O-readme.md.md になる（docsタイプはinp配下にならない）
        assert "docs/" in str(md_path).replace("\\", "/")
        assert md_path.name == "O-readme.md.md"

    def test_node_to_frontmatter_includes_conversion(self, connector, sample_node):
        """includesが正しくObsidianリンク形式に変換される"""
        includes = ["mesh_box.cdb", "material_steel.yaml"]
        frontmatter = connector.node_to_frontmatter(sample_node, includes=includes)

        assert "includes" in frontmatter
        assert frontmatter["includes"] == [
            "[[O-mesh_box.cdb]]",
            "[[O-material_steel.yaml]]",
        ]

    def test_write_md_creates_correct_structure(self, connector, sample_node, tmp_path):
        """正しいディレクトリ構造でファイルが作成される"""
        path = connector.write_md(sample_node)

        assert path is not None
        assert path.exists()

        # ディレクトリ構造を確認
        rel_path = path.relative_to(tmp_path)
        parts = rel_path.parts

        # notes/props/go/O-xxx.md という構造（inp/は挟まない）
        assert "go" in parts
        assert "inp" not in parts  # inp/は挟まない
        assert "O-go" not in parts  # ディレクトリにO-がないことを確認
        assert path.name.startswith("O-")

    def test_export_graph(self, connector, tmp_path):
        """グラフ全体のエクスポート"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_test_v1",
                    format="inp",
                    properties={"path": "inp/go_test_v1.inp"},
                ),
                Node(
                    id=2,
                    type="mesh",
                    name="mesh_box",
                    format="cdb",
                    properties={"path": "mesh/mesh_box.cdb"},
                ),
            ],
            relations=[],
        )

        written = connector.export_graph(graph)

        # 3 Vault設定 + 2ノード + 1サマリーノート = 6ファイル
        assert len(written) == 6

        # ノードファイルはO-プレフィックス付き
        node_files = [p for p in written if p.name.startswith("O-")]
        assert len(node_files) == 2

        # サマリーノートが含まれる
        summary_files = [p for p in written if p.name == "jj-summary.md"]
        assert len(summary_files) == 1

        # Vault設定ファイルが含まれる
        vault_files = [p for p in written if ".obsidian" in str(p)]
        assert len(vault_files) == 3


class TestObsidianBaseAndGroupFiles:
    """base/groupファイル生成のテスト"""

    @pytest.fixture
    def connector(self, tmp_path):
        """テスト用コネクタ"""
        return ObsidianConnector(project_root=tmp_path)

    def test_export_graph_generates_base_files(self, connector, tmp_path):
        """同一indexのノードが2つ以上あれば.baseファイルが生成される（同一タイプ.baseも生成）"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"},
                ),
                Node(
                    id=2,
                    type="go",
                    name="go_idx1_v2",
                    format="inp",
                    properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"},
                ),
            ],
            relations=[],
        )
        written = connector.export_graph(graph)

        # .baseファイルが生成されている（同一index + 同一タイプ）
        base_files = [p for p in written if p.name.endswith(".base")]
        assert len(base_files) == 2
        base_names = {p.name for p in base_files}
        assert "go_idx1.base" in base_names
        assert "go.base" in base_names
        # idx .base はYAML形式（frontmatterの---で始まらない）
        idx_base = next(p for p in base_files if p.name == "go_idx1.base")
        content = idx_base.read_text(encoding="utf-8")
        assert not content.startswith("---")
        assert "views:" in content

    def test_group_files_abolished(self, connector, tmp_path):
        """同一idxグループの-group.mdは廃止され、生成されない"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"},
                ),
                Node(
                    id=2,
                    type="go",
                    name="go_idx1_v2",
                    format="inp",
                    properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"},
                ),
            ],
            relations=[],
        )
        written = connector.export_graph(graph)

        # -group.mdファイルは生成されない（廃止）
        group_files = [p for p in written if p.name.endswith("-group.md")]
        assert len(group_files) == 0

    def test_latest_version_links_to_base(self, connector, tmp_path):
        """最新verのNodeは.baseファイルへのリンクを持つ"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"},
                ),
                Node(
                    id=2,
                    type="go",
                    name="go_idx1_v2",
                    format="inp",
                    properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"},
                ),
            ],
            relations=[],
        )
        written = connector.export_graph(graph)

        # 最新ver (v2) のmdファイルを確認
        v2_md = [p for p in written if "go_idx1_v2" in p.name and p.name.endswith(".md")]
        assert len(v2_md) == 1
        content = v2_md[0].read_text(encoding="utf-8")
        # .baseへのリンクがincludesに含まれる
        assert "go_idx1.base" in content

    def test_non_latest_links_to_next_version(self, connector, tmp_path):
        """最新以外のNodeは次のNodeへのリンクを持つ"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"},
                ),
                Node(
                    id=2,
                    type="go",
                    name="go_idx1_v2",
                    format="inp",
                    properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"},
                ),
            ],
            relations=[],
        )
        written = connector.export_graph(graph)

        # v1のmdファイルを確認
        v1_md = [p for p in written if "go_idx1_v1" in p.name and p.name.endswith(".md")]
        assert len(v1_md) == 1
        content = v1_md[0].read_text(encoding="utf-8")
        # 次のバージョン(v2)へのリンクがincludesに含まれる
        assert "O-go_idx1_v2.inp" in content

    def test_no_base_or_group_for_single_node(self, connector, tmp_path):
        """ノードが1つだけの場合はbase/groupファイルが生成されない"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"},
                ),
            ],
            relations=[],
        )
        written = connector.export_graph(graph)

        base_files = [p for p in written if p.name.endswith(".base")]
        group_files = [p for p in written if p.name.endswith("-group.md")]
        assert len(base_files) == 0
        assert len(group_files) == 0


class TestObsidianFrontmatterProperties:
    """frontmatterにファイル情報がpropertyとして含まれることのテスト"""

    @pytest.fixture
    def connector(self, tmp_path):
        return ObsidianConnector(project_root=tmp_path)

    def test_frontmatter_has_node_type(self, connector):
        """frontmatterにnode_typeが含まれる"""
        node = Node(
            id=1,
            type="Abaqusインプット",
            name="go_idx1_v1",
            format="inp",
            properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"},
        )
        fm = connector.node_to_frontmatter(node)
        assert fm["node_type"] == "Abaqusインプット"

    def test_frontmatter_has_node_format(self, connector):
        """frontmatterにnode_formatが含まれる"""
        node = Node(
            id=1,
            type="go",
            name="go_idx1_v1",
            format="inp",
            properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"},
        )
        fm = connector.node_to_frontmatter(node)
        assert fm["node_format"] == "inp"

    def test_frontmatter_has_file_path(self, connector):
        """frontmatterにfile（実ファイルパス）が含まれる"""
        node = Node(
            id=1,
            type="go",
            name="go_idx1_v1",
            format="inp",
            properties={"path": "go/go_idx1_v1.inp", "index": "1", "version": "1"},
        )
        fm = connector.node_to_frontmatter(node)
        assert fm["file"] == "go/go_idx1_v1.inp"

    def test_frontmatter_file_path_uses_forward_slash(self, connector):
        """frontmatterのfileパスはバックスラッシュを/に変換する"""
        node = Node(
            id=1,
            type="go",
            name="go_idx1_v1",
            format="inp",
            properties={"path": "go\\go_idx1_v1.inp", "index": "1", "version": "1"},
        )
        fm = connector.node_to_frontmatter(node)
        assert "\\" not in fm["file"]
        assert fm["file"] == "go/go_idx1_v1.inp"


class TestObsidianVersionLinks:
    """バージョンリンク構造のテスト（3ノード以上）"""

    @pytest.fixture
    def connector(self, tmp_path):
        return ObsidianConnector(project_root=tmp_path)

    def test_three_versions_link_chain(self, connector, tmp_path):
        """v1→v2, v2→v3, v3→.base のリンクチェーン"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"},
                ),
                Node(
                    id=2,
                    type="go",
                    name="go_idx1_v2",
                    format="inp",
                    properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"},
                ),
                Node(
                    id=3,
                    type="go",
                    name="go_idx1_v3",
                    format="inp",
                    properties={"path": "go_idx1_v3.inp", "index": "1", "version": "3"},
                ),
            ],
            relations=[],
        )
        written = connector.export_graph(graph)

        # v1 → v2 リンク
        v1_md = [p for p in written if "go_idx1_v1" in p.name and p.name.endswith(".md")]
        assert len(v1_md) == 1
        v1_content = v1_md[0].read_text(encoding="utf-8")
        assert "O-go_idx1_v2.inp" in v1_content

        # v2 → v3 リンク
        v2_md = [p for p in written if "go_idx1_v2" in p.name and p.name.endswith(".md")]
        assert len(v2_md) == 1
        v2_content = v2_md[0].read_text(encoding="utf-8")
        assert "O-go_idx1_v3.inp" in v2_content

        # v3 → .base リンク
        v3_md = [p for p in written if "go_idx1_v3" in p.name and p.name.endswith(".md")]
        assert len(v3_md) == 1
        v3_content = v3_md[0].read_text(encoding="utf-8")
        assert "go_idx1.base" in v3_content

    def test_base_filename_uses_node_type(self, connector, tmp_path):
        """.baseファイル名はnode.typeを使用する（同一タイプ.baseも生成される）"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="Abaqusインプット",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"},
                ),
                Node(
                    id=2,
                    type="Abaqusインプット",
                    name="go_idx1_v2",
                    format="inp",
                    properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"},
                ),
            ],
            relations=[],
        )
        written = connector.export_graph(graph)

        # .baseファイル名がノードのtypeを使う（idx + タイプの2つ）
        base_files = [p for p in written if p.name.endswith(".base")]
        assert len(base_files) == 2
        base_names = {p.name for p in base_files}
        assert "Abaqusインプット_idx1.base" in base_names
        assert "Abaqusインプット.base" in base_names

        # 最新verのfrontmatterに.baseリンクが含まれる
        v2_md = [p for p in written if "go_idx1_v2" in p.name and p.name.endswith(".md")]
        v2_content = v2_md[0].read_text(encoding="utf-8")
        assert "Abaqusインプット_idx1.base" in v2_content


class TestObsidianConfigCustomPrefix:
    """カスタムプレフィックスのテスト"""

    def test_custom_prefix(self):
        """カスタムプレフィックスが使用できる"""
        assert to_obsidian_filename("test.inp", prefix="X-") == "X-test.inp.md"
        assert from_obsidian_filename("X-test.inp.md", prefix="X-") == "test.inp"
        assert to_obsidian_link("test.inp", prefix="X-") == "[[X-test.inp]]"


class TestCoercePropertyValue:
    """_coerce_property_value のテスト"""

    def test_int_string_to_int(self):
        """整数文字列はintに変換"""
        assert _coerce_property_value("1") == 1
        assert isinstance(_coerce_property_value("1"), int)
        assert _coerce_property_value("42") == 42
        assert _coerce_property_value("0") == 0

    def test_float_string_to_float(self):
        """小数文字列はfloatに変換"""
        assert _coerce_property_value("1.5") == 1.5
        assert isinstance(_coerce_property_value("1.5"), float)
        assert _coerce_property_value("0.001") == 0.001

    def test_bool_string_to_bool(self):
        """true/falseはboolに変換（クオートなし）"""
        assert _coerce_property_value("true") is True
        assert _coerce_property_value("false") is False
        assert _coerce_property_value("True") is True
        assert _coerce_property_value("False") is False

    def test_non_numeric_string_unchanged(self):
        """非数値文字列はそのまま"""
        assert _coerce_property_value("hello") == "hello"
        assert _coerce_property_value("go_idx1") == "go_idx1"

    def test_already_typed_values_unchanged(self):
        """既に型が付いた値はそのまま"""
        assert _coerce_property_value(42) == 42
        assert _coerce_property_value(1.5) == 1.5
        assert _coerce_property_value(True) is True

    def test_negative_int(self):
        """負の整数"""
        assert _coerce_property_value("-1") == -1
        assert isinstance(_coerce_property_value("-1"), int)

    def test_scientific_notation(self):
        """科学記法はfloatとして変換"""
        result = _coerce_property_value("1e3")
        assert result == 1000.0
        assert isinstance(result, float)


class TestFrontmatterPropertyTypes:
    """frontmatterのプロパティ型変換テスト"""

    @pytest.fixture
    def connector(self, tmp_path):
        return ObsidianConnector(project_root=tmp_path)

    def test_int_properties_in_frontmatter(self, connector):
        """整数値がintとしてfrontmatterに入る（vocabで変換後のキー名を使用）"""
        node = Node(
            id=1,
            type="go",
            name="go_idx1_v1",
            format="inp",
            properties={"path": "go_idx1_v1.inp", "index": "1", "version": "2", "w": "5"},
        )
        fm = connector.node_to_frontmatter(node)
        # デフォルトvocab: idx→条件, v→バージョン
        idx_key = connector.graph_config.vocab.get("idx", "idx")
        ver_key = connector.graph_config.vocab.get("v", connector.graph_config.vocab.get("ver", "ver"))
        assert fm[idx_key] == 1
        assert isinstance(fm[idx_key], int)
        assert fm[ver_key] == 2
        assert isinstance(fm[ver_key], int)
        assert fm["w"] == 5
        assert isinstance(fm["w"], int)

    def test_float_properties_in_frontmatter(self, connector):
        """小数値がfloatとしてfrontmatterに入る"""
        node = Node(
            id=1,
            type="go",
            name="go_idx1_v1",
            format="inp",
            properties={"path": "go.inp", "index": "1", "version": "1", "thickness": "2.5"},
        )
        fm = connector.node_to_frontmatter(node)
        assert fm["thickness"] == 2.5
        assert isinstance(fm["thickness"], float)

    def test_bool_properties_in_frontmatter(self, connector):
        """true/falseがboolとしてfrontmatterに入る"""
        node = Node(
            id=1,
            type="go",
            name="go_idx1_v1",
            format="inp",
            properties={"path": "go.inp", "index": "1", "version": "1", "active": "true"},
        )
        fm = connector.node_to_frontmatter(node)
        assert fm["active"] is True
        assert isinstance(fm["active"], bool)

    def test_bool_false_in_frontmatter(self, connector):
        """falseがbool Falseとしてfrontmatterに入る"""
        node = Node(
            id=1,
            type="go",
            name="go_idx1_v1",
            format="inp",
            properties={"path": "go.inp", "index": "1", "version": "1", "active": "false"},
        )
        fm = connector.node_to_frontmatter(node)
        assert fm["active"] is False

    def test_yaml_output_bool_unquoted(self, connector, tmp_path):
        """YAML出力でtrue/falseがクオートなしで書かれる"""
        node = Node(
            id=1,
            type="go",
            name="go_idx1_v1",
            format="inp",
            properties={"path": "go.inp", "index": "1", "version": "1", "active": "true"},
        )
        path = connector.write_md(node, overwrite=True)
        content = path.read_text(encoding="utf-8")
        # YAMLでboolはtrue（クオートなし）で出力される
        assert "active: true" in content
        # クオート付きで出力されていないことを確認
        assert "active: 'true'" not in content
        assert 'active: "true"' not in content


class TestBaseFilterSimplified:
    """.baseファイルのフィルター簡素化テスト"""

    @pytest.fixture
    def connector(self, tmp_path):
        return ObsidianConnector(project_root=tmp_path)

    def test_base_filter_folder_only(self, connector, tmp_path):
        """フィルターがfolder条件のみであること"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="Abaqusインプット",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"},
                ),
                Node(
                    id=2,
                    type="Abaqusインプット",
                    name="go_idx1_v2",
                    format="inp",
                    properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"},
                ),
            ],
            relations=[],
        )
        written = connector.export_graph(graph)
        idx_base = next(p for p in written if p.name == "Abaqusインプット_idx1.base")
        content = idx_base.read_text(encoding="utf-8")
        # folder条件のみ、andブロック不要
        assert 'file.folder == "notes/props/Abaqusインプット"' in content
        # andブロックが存在しないことを確認
        assert "and:" not in content

    def test_base_filter_no_extra_conditions(self, connector, tmp_path):
        """余計なand条件（endsWith等）がないこと"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"path": "go.inp", "index": "1", "version": "1"},
                ),
                Node(
                    id=2,
                    type="go",
                    name="go_idx1_v2",
                    format="inp",
                    properties={"path": "go2.inp", "index": "1", "version": "2"},
                ),
            ],
            relations=[],
        )
        written = connector.export_graph(graph)
        idx_base = next(p for p in written if p.name == "go_idx1.base")
        content = idx_base.read_text(encoding="utf-8")
        assert "endsWith" not in content
        assert "active ==" not in content


class TestBaseOrderIntersection:
    """.baseファイルのorderブロックにプロパティ積集合が追記されるテスト"""

    @pytest.fixture
    def connector(self, tmp_path):
        return ObsidianConnector(project_root=tmp_path)

    def test_order_includes_intersection_properties(self, connector, tmp_path):
        """orderブロックにグループ共通プロパティが含まれる"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"path": "a.inp", "index": "1", "version": "1", "w": "5", "t": "20", "active": "true"},
                ),
                Node(
                    id=2,
                    type="go",
                    name="go_idx1_v2",
                    format="inp",
                    properties={"path": "b.inp", "index": "1", "version": "2", "w": "5", "t": "20", "active": "true"},
                ),
            ],
            relations=[],
        )
        written = connector.export_graph(graph)
        idx_base = next(p for p in written if p.name == "go_idx1.base")
        content = idx_base.read_text(encoding="utf-8")
        # 共通プロパティ w, t, active がorderに含まれる
        assert "- w" in content
        assert "- t" in content
        assert "- active" in content

    def test_order_excludes_non_intersection_properties(self, connector, tmp_path):
        """片方のノードにしかないプロパティはorderに含まれない"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"path": "a.inp", "index": "1", "version": "1", "w": "5", "unique_prop": "x"},
                ),
                Node(
                    id=2,
                    type="go",
                    name="go_idx1_v2",
                    format="inp",
                    properties={"path": "b.inp", "index": "1", "version": "2", "w": "5"},
                ),
            ],
            relations=[],
        )
        written = connector.export_graph(graph)
        idx_base = next(p for p in written if p.name == "go_idx1.base")
        content = idx_base.read_text(encoding="utf-8")
        # unique_propは片方のみなのでorderに含まれない
        assert "unique_prop" not in content
        # wは共通なのでorderに含まれる
        assert "- w" in content


class TestSameTypeBaseFiles:
    """同一タイプグループの.baseファイル生成テスト"""

    @pytest.fixture
    def connector(self, tmp_path):
        return ObsidianConnector(project_root=tmp_path)

    def test_type_base_file_generated(self, connector, tmp_path):
        """同一タイプのノードが2つ以上あればタイプ.baseが生成される"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"path": "a.inp", "index": "1", "version": "1"},
                ),
                Node(
                    id=2,
                    type="go",
                    name="go_idx2_v1",
                    format="inp",
                    properties={"path": "b.inp", "index": "2", "version": "1"},
                ),
            ],
            relations=[],
        )
        written = connector.export_graph(graph)
        type_base = [p for p in written if p.name == "go.base"]
        assert len(type_base) == 1

    def test_type_base_has_intersection_properties(self, connector, tmp_path):
        """タイプ.baseにもプロパティ積集合がorderに含まれる"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"path": "a.inp", "index": "1", "version": "1", "w": "5"},
                ),
                Node(
                    id=2,
                    type="go",
                    name="go_idx2_v1",
                    format="inp",
                    properties={"path": "b.inp", "index": "2", "version": "1", "w": "10"},
                ),
            ],
            relations=[],
        )
        written = connector.export_graph(graph)
        type_base = next(p for p in written if p.name == "go.base")
        content = type_base.read_text(encoding="utf-8")
        # 共通のw がorderに含まれる
        assert "- w" in content

    def test_no_type_base_for_single_node(self, connector, tmp_path):
        """ノードが1つの場合はタイプ.baseは生成されない"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"path": "a.inp", "index": "1", "version": "1"},
                ),
            ],
            relations=[],
        )
        written = connector.export_graph(graph)
        type_base = [p for p in written if p.name == "go.base"]
        assert len(type_base) == 0

    def test_idx_and_type_base_both_generated(self, connector, tmp_path):
        """同一index .baseと同一タイプ.baseが両方生成される"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="Abaqusインプット",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"path": "a.inp", "index": "1", "version": "1"},
                ),
                Node(
                    id=2,
                    type="Abaqusインプット",
                    name="go_idx1_v2",
                    format="inp",
                    properties={"path": "b.inp", "index": "1", "version": "2"},
                ),
                Node(
                    id=3,
                    type="Abaqusインプット",
                    name="go_idx2_v1",
                    format="inp",
                    properties={"path": "c.inp", "index": "2", "version": "1"},
                ),
            ],
            relations=[],
        )
        written = connector.export_graph(graph)
        base_files = [p for p in written if p.name.endswith(".base")]
        base_names = {p.name for p in base_files}
        assert "Abaqusインプット_idx1.base" in base_names
        assert "Abaqusインプット.base" in base_names


class TestOverwriteBehavior:
    """props/bases上書き前提動作のテスト"""

    @pytest.fixture
    def connector(self, tmp_path):
        return ObsidianConnector(project_root=tmp_path)

    def test_props_always_overwritten(self, connector, tmp_path):
        """props/のmdファイルはoverwrite=Falseでも上書きされる"""
        node = Node(
            id=1,
            type="go",
            name="go_idx1_v1",
            format="inp",
            properties={"path": "go.inp", "index": "1", "version": "1", "w": "5"},
        )
        # 初回書き込み
        graph = GraphModel(nodes=[node], relations=[])
        connector.export_graph(graph, overwrite=False)

        # プロパティを変更して再エクスポート（overwrite=Falseでも上書き）
        node2 = Node(
            id=1,
            type="go",
            name="go_idx1_v1",
            format="inp",
            properties={"path": "go.inp", "index": "1", "version": "1", "w": "10"},
        )
        graph2 = GraphModel(nodes=[node2], relations=[])
        written = connector.export_graph(graph2, overwrite=False)

        # ノードファイル（O-プレフィックス付き.md）のみ対象
        node_md_files = [p for p in written if p.name.startswith("O-") and p.name.endswith(".md")]
        assert len(node_md_files) == 1
        content = node_md_files[0].read_text(encoding="utf-8")
        assert "w: 10" in content


class TestVocabPropsUnification:
    """props命名統一テスト: vocabで変換したキー名を正として混在解消"""

    @pytest.fixture
    def connector(self, tmp_path):
        return ObsidianConnector(project_root=tmp_path)

    def test_default_vocab_idx_to_jouken(self, connector):
        """デフォルトvocabでidx→条件に変換される"""
        node = Node(
            id=1,
            type="go",
            name="go_idx1_v1",
            format="inp",
            properties={"path": "go.inp", "index": "1", "version": "1"},
        )
        fm = connector.node_to_frontmatter(node)
        # デフォルトvocab: idx→条件
        assert "条件" in fm
        assert fm["条件"] == 1
        # 変換前のキーは存在しない
        assert "index" not in fm
        assert "idx" not in fm

    def test_default_vocab_ver_to_version(self, connector):
        """デフォルトvocabでv→バージョンに変換される"""
        node = Node(
            id=1,
            type="go",
            name="go_idx1_v1",
            format="inp",
            properties={"path": "go.inp", "index": "1", "version": "2"},
        )
        fm = connector.node_to_frontmatter(node)
        # デフォルトvocab: v→バージョン
        assert "バージョン" in fm
        assert fm["バージョン"] == 2
        # 変換前のキーは存在しない
        assert "version" not in fm
        assert "ver" not in fm
        assert "v" not in fm

    def test_no_duplicate_keys(self, connector):
        """translated_propsとindex/versionで重複が生じない"""
        node = Node(
            id=1,
            type="go",
            name="go_idx1_v1",
            format="inp",
            properties={
                "path": "go.inp",
                "index": "1",
                "version": "2",
                "条件": "99",  # 事前にvocab変換済みの重複
                "バージョン": "99",
            },
        )
        fm = connector.node_to_frontmatter(node)
        # indexの値が優先される
        assert fm["条件"] == 1
        assert fm["バージョン"] == 2

    def test_custom_vocab_connector(self, tmp_path):
        """カスタムvocabで任意のキー名に変換"""
        config = GraphConfig.from_dict(
            {
                "vocab": {"idx": "No.", "v": "Rev"},
            }
        )
        connector = ObsidianConnector(project_root=tmp_path, graph_config=config)
        node = Node(
            id=1,
            type="go",
            name="go_idx1_v1",
            format="inp",
            properties={"path": "go.inp", "index": "3", "version": "5"},
        )
        fm = connector.node_to_frontmatter(node)
        assert fm["No."] == 3
        assert fm["Rev"] == 5
        assert "idx" not in fm
        assert "ver" not in fm
        assert "index" not in fm
        assert "version" not in fm

    def test_empty_vocab_falls_back_to_idx_ver(self, tmp_path):
        """vocabが空の場合はidx/verにフォールバック"""
        config = GraphConfig.from_dict({"vocab": {}})
        connector = ObsidianConnector(project_root=tmp_path, graph_config=config)
        node = Node(
            id=1,
            type="go",
            name="go_idx1_v1",
            format="inp",
            properties={"path": "go.inp", "index": "1", "version": "1"},
        )
        fm = connector.node_to_frontmatter(node)
        assert "idx" in fm
        assert "ver" in fm

    def test_base_order_uses_vocab_keys(self, connector, tmp_path):
        """baseファイルのorderがvocab変換後のキー名を使用"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"path": "a.inp", "index": "1", "version": "1"},
                ),
                Node(
                    id=2,
                    type="go",
                    name="go_idx1_v2",
                    format="inp",
                    properties={"path": "b.inp", "index": "1", "version": "2"},
                ),
            ],
            relations=[],
        )
        written = connector.export_graph(graph)
        idx_base = next(p for p in written if p.name == "go_idx1.base")
        content = idx_base.read_text(encoding="utf-8")
        # vocab変換後のキー名がorderに含まれる
        assert "- 条件" in content or "条件" in content
        assert "- バージョン" in content or "バージョン" in content
        # 変換前のキー名がorderに含まれない
        assert "- idx\n" not in content
        assert "- ver\n" not in content

    def test_base_sort_uses_vocab_keys(self, connector, tmp_path):
        """baseファイルのsortがvocab変換後のキー名を使用"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"path": "a.inp", "index": "1", "version": "1"},
                ),
                Node(
                    id=2,
                    type="go",
                    name="go_idx1_v2",
                    format="inp",
                    properties={"path": "b.inp", "index": "1", "version": "2"},
                ),
            ],
            relations=[],
        )
        written = connector.export_graph(graph)
        idx_base = next(p for p in written if p.name == "go_idx1.base")
        content = idx_base.read_text(encoding="utf-8")
        # sortのproperty名もvocab変換済み
        assert (
            "property: 条件" in content
            or "property: '\\u6761\\u4EF6'" in content
            or 'property: "\\u6761\\u4EF6"' in content
            or "条件" in content
        )
        assert "property: idx" not in content

    def test_base_no_file_links(self, connector, tmp_path):
        """baseファイルにfile.linksが含まれない"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"path": "a.inp", "index": "1", "version": "1"},
                ),
                Node(
                    id=2,
                    type="go",
                    name="go_idx1_v2",
                    format="inp",
                    properties={"path": "b.inp", "index": "1", "version": "2"},
                ),
            ],
            relations=[],
        )
        written = connector.export_graph(graph)
        for path in written:
            if path.name.endswith(".base"):
                content = path.read_text(encoding="utf-8")
                assert "file.links" not in content
