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
        assert "inp/go/" in str(md_path).replace("\\", "/")
        assert md_path.name == "O-go_test_v1.inp.md"
        assert "O-go/" not in str(md_path).replace("\\", "/")  # ディレクトリにO-がないことを確認

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

        # notes/props/inp/go/O-xxx.md という構造
        assert "inp" in parts
        assert "go" in parts
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


class TestObsidianConfigCustomPrefix:
    """カスタムプレフィックスのテスト"""

    def test_custom_prefix(self):
        """カスタムプレフィックスが使用できる"""
        assert to_obsidian_filename("test.inp", prefix="X-") == "X-test.inp.md"
        assert from_obsidian_filename("X-test.inp.md", prefix="X-") == "test.inp"
        assert to_obsidian_link("test.inp", prefix="X-") == "[[X-test.inp]]"
