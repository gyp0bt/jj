"""Obsidianコネクタのテスト

重要な命名規則のテスト:
- 実ファイル: "O-"プレフィックスなし
- Obsidianファイル: "O-"プレフィックス付き
- ディレクトリ: "O-"プレフィックスなし

[READMEへ戻る](../README.md)
"""

import pytest
from pathlib import Path

from services.connectors.obsidian import (
    ObsidianConfig,
    ObsidianConnector,
    to_obsidian_filename,
    from_obsidian_filename,
    to_obsidian_link,
    get_directory_for_type,
)
from jj_types import Node, GraphModel


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

        assert len(written) == 2

        # 全ファイルがO-プレフィックス付き
        for path in written:
            assert path.name.startswith("O-")


class TestObsidianBaseAndGroupFiles:
    """base/groupファイル生成のテスト"""

    @pytest.fixture
    def connector(self, tmp_path):
        """テスト用コネクタ"""
        return ObsidianConnector(project_root=tmp_path)

    def test_export_graph_generates_base_files(self, connector, tmp_path):
        """同一indexのノードが2つ以上あれば.baseファイルが生成される"""
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

        # .baseファイルが生成されている
        base_files = [p for p in written if p.name.endswith(".base")]
        assert len(base_files) == 1
        assert base_files[0].name == "go_idx1.base"
        # .base はYAML形式（frontmatterの---で始まらない）
        content = base_files[0].read_text(encoding="utf-8")
        assert not content.startswith("---")
        assert "views:" in content

    def test_export_graph_generates_group_files(self, connector, tmp_path):
        """同一indexのノードが2つ以上あれば-group.mdファイルが生成される"""
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

        # -group.mdファイルが生成されている
        group_files = [p for p in written if p.name.endswith("-group.md")]
        assert len(group_files) == 1
        assert group_files[0].name == "go_idx1-group.md"
        # -group.md はfrontmatter形式
        content = group_files[0].read_text(encoding="utf-8")
        assert content.startswith("---")
        assert "nodegroup" in content
        assert "[[O-go_idx1_v1.inp]]" in content
        assert "[[O-go_idx1_v2.inp]]" in content

    def test_group_file_placed_in_props_type_dir(self, connector, tmp_path):
        """-group.mdファイルはprops/{type}/配下に配置される"""
        graph = GraphModel(
            nodes=[
                Node(
                    id=1,
                    type="mesh",
                    name="mesh_idx1_v1",
                    format="cdb",
                    properties={"path": "mesh_idx1_v1.cdb", "index": "1", "version": "1"},
                ),
                Node(
                    id=2,
                    type="mesh",
                    name="mesh_idx1_v2",
                    format="cdb",
                    properties={"path": "mesh_idx1_v2.cdb", "index": "1", "version": "2"},
                ),
            ],
            relations=[],
        )
        written = connector.export_graph(graph)

        group_files = [p for p in written if p.name.endswith("-group.md")]
        assert len(group_files) == 1
        # notes/props/mesh/mesh_idx1-group.md に配置される
        rel_path = group_files[0].relative_to(tmp_path)
        parts = rel_path.parts
        assert "props" in parts
        assert "mesh" in parts
        assert "inp" not in parts  # inp/は挟まない

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


class TestObsidianConfigCustomPrefix:
    """カスタムプレフィックスのテスト"""

    def test_custom_prefix(self):
        """カスタムプレフィックスが使用できる"""
        assert to_obsidian_filename("test.inp", prefix="X-") == "X-test.inp.md"
        assert from_obsidian_filename("X-test.inp.md", prefix="X-") == "test.inp"
        assert to_obsidian_link("test.inp", prefix="X-") == "[[X-test.inp]]"
