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
                Node(id=1, type="go", name="go_idx1_v1", format="inp",
                     properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"}),
                Node(id=2, type="go", name="go_idx1_v2", format="inp",
                     properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"}),
                Node(id=3, type="go", name="go_idx1_v3", format="inp",
                     properties={"path": "go_idx1_v3.inp", "index": "1", "version": "3"}),
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
        """.baseファイル名はnode.typeを使用する"""
        graph = GraphModel(
            nodes=[
                Node(id=1, type="Abaqusインプット", name="go_idx1_v1", format="inp",
                     properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"}),
                Node(id=2, type="Abaqusインプット", name="go_idx1_v2", format="inp",
                     properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"}),
            ],
            relations=[],
        )
        written = connector.export_graph(graph)

        # .baseファイル名がノードのtypeを使う
        base_files = [p for p in written if p.name.endswith(".base")]
        assert len(base_files) == 1
        assert base_files[0].name == "Abaqusインプット_idx1.base"

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
