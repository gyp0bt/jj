"""メッシュ統計キャッシュのユニットテスト

メッシュコンテンツハッシュ計算、ディスクキャッシュ、
パラメーター/境界条件のみが異なる.inpファイル間でのキャッシュ共有をテストする。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from config import GraphConfig
from jj_types import Node
from services.graph.project_graph import ProjectGraph
from plugins.abaqus.parse.mesh_parser import (
    _compute_mesh_content_hash,
    _load_mesh_stats_cache,
    _save_mesh_stats_cache,
)

ASSET_DIR = Path(__file__).resolve().parent.parent / "shared" / "tests" / "test_asset1"


@pytest.fixture
def config() -> GraphConfig:
    return GraphConfig.from_dict(
        {
            "vocab": {},
            "file-relations": {"input-extensions": [".inp"]},
        }
    )


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """一時プロジェクトディレクトリ（.j2/storageを作成可能）"""
    (tmp_path / ".j2" / "storage").mkdir(parents=True)
    return tmp_path


# ====================================================================
# _compute_mesh_content_hash テスト
# ====================================================================


class TestComputeMeshContentHash:
    """メッシュコンテンツハッシュ計算のテスト"""

    def _write_inp(self, tmp_path: Path, name: str, content: str) -> Path:
        """テスト用.inpファイルを作成"""
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        return p

    def test_same_mesh_different_params_same_hash(self, tmp_path: Path):
        """パラメーターのみ異なるファイルが同じハッシュを返す"""
        mesh_content = "*NODE\n1, 0.0, 0.0, 0.0\n2, 1.0, 0.0, 0.0\n3, 0.0, 1.0, 0.0\n*ELEMENT, TYPE=C3D8\n1, 1, 2, 3\n"

        file1 = self._write_inp(
            tmp_path,
            "go_idx1.inp",
            "*PARAMETER\n"
            "**props\n"
            "thickness=5.0\n"
            "material=AL7075\n" + mesh_content + "*BOUNDARY\n"
            "1, 1, 6\n"
            "*STEP\n"
            "*STATIC\n",
        )

        file2 = self._write_inp(
            tmp_path,
            "go_idx2.inp",
            "*PARAMETER\n"
            "**props\n"
            "thickness=10.0\n"
            "material=SUS304\n" + mesh_content + "*BOUNDARY\n"
            "1, 1, 3\n"
            "*STEP\n"
            "*DYNAMIC\n",
        )

        h1 = _compute_mesh_content_hash(str(file1))
        h2 = _compute_mesh_content_hash(str(file2))

        assert h1 is not None
        assert h2 is not None
        assert h1 == h2

    def test_different_mesh_different_hash(self, tmp_path: Path):
        """メッシュが異なるファイルは異なるハッシュを返す"""
        file1 = self._write_inp(
            tmp_path,
            "mesh1.inp",
            "*NODE\n1, 0.0, 0.0, 0.0\n2, 1.0, 0.0, 0.0\n*ELEMENT, TYPE=C3D8\n1, 1, 2\n",
        )

        file2 = self._write_inp(
            tmp_path,
            "mesh2.inp",
            "*NODE\n1, 0.0, 0.0, 0.0\n2, 1.0, 0.0, 0.0\n3, 0.5, 0.5, 0.0\n*ELEMENT, TYPE=C3D8\n1, 1, 2, 3\n",
        )

        h1 = _compute_mesh_content_hash(str(file1))
        h2 = _compute_mesh_content_hash(str(file2))

        assert h1 is not None
        assert h2 is not None
        assert h1 != h2

    def test_no_mesh_content_returns_none(self, tmp_path: Path):
        """メッシュ定義がないファイルはNoneを返す"""
        file = self._write_inp(
            tmp_path,
            "params_only.inp",
            "*PARAMETER\n**props\nthickness=5.0\n*STEP\n*STATIC\n",
        )

        h = _compute_mesh_content_hash(str(file))
        assert h is None

    def test_nonexistent_file_returns_none(self):
        """存在しないファイルはNoneを返す"""
        h = _compute_mesh_content_hash("/nonexistent/path/file.inp")
        assert h is None

    def test_include_reference_in_hash(self, tmp_path: Path):
        """*INCLUDE参照がハッシュに含まれる"""
        # includeされるメッシュファイルを作成
        self._write_inp(
            tmp_path,
            "mesh_t50.inp",
            "*NODE\n1, 0.0, 0.0, 0.0\n*ELEMENT, TYPE=C3D8\n1, 1\n",
        )

        file1 = self._write_inp(
            tmp_path,
            "go_idx1.inp",
            "*PARAMETER\nthickness=5.0\n*INCLUDE, INPUT=mesh_t50.inp\n*BOUNDARY\n1, 1, 6\n",
        )

        file2 = self._write_inp(
            tmp_path,
            "go_idx2.inp",
            "*PARAMETER\nthickness=10.0\n*INCLUDE, INPUT=mesh_t50.inp\n*BOUNDARY\n1, 1, 3\n",
        )

        h1 = _compute_mesh_content_hash(str(file1))
        h2 = _compute_mesh_content_hash(str(file2))

        assert h1 is not None
        assert h2 is not None
        assert h1 == h2  # 同じメッシュファイルを参照

    def test_different_include_different_hash(self, tmp_path: Path):
        """異なるメッシュファイルを参照する場合は異なるハッシュ"""
        self._write_inp(
            tmp_path,
            "mesh_t50.inp",
            "*NODE\n1, 0.0, 0.0, 0.0\n",
        )
        self._write_inp(
            tmp_path,
            "mesh_t100.inp",
            "*NODE\n1, 0.0, 0.0, 0.0\n",
        )

        file1 = self._write_inp(
            tmp_path,
            "go_a.inp",
            "*INCLUDE, INPUT=mesh_t50.inp\n",
        )
        file2 = self._write_inp(
            tmp_path,
            "go_b.inp",
            "*INCLUDE, INPUT=mesh_t100.inp\n",
        )

        h1 = _compute_mesh_content_hash(str(file1))
        h2 = _compute_mesh_content_hash(str(file2))

        assert h1 is not None
        assert h2 is not None
        assert h1 != h2

    def test_elset_nset_included_in_hash(self, tmp_path: Path):
        """*ELSET, *NSETもハッシュに含まれる"""
        file1 = self._write_inp(
            tmp_path,
            "a.inp",
            "*NODE\n1, 0.0, 0.0, 0.0\n*ELSET, ELSET=ALL\n1\n",
        )
        file2 = self._write_inp(
            tmp_path,
            "b.inp",
            "*NODE\n1, 0.0, 0.0, 0.0\n*ELSET, ELSET=PARTIAL\n1\n",
        )

        h1 = _compute_mesh_content_hash(str(file1))
        h2 = _compute_mesh_content_hash(str(file2))

        assert h1 is not None
        assert h2 is not None
        assert h1 != h2

    def test_comments_ignored(self, tmp_path: Path):
        """コメント行（**）はハッシュに影響しない"""
        file1 = self._write_inp(
            tmp_path,
            "a.inp",
            "** This is version 1\n*NODE\n1, 0.0, 0.0, 0.0\n",
        )
        file2 = self._write_inp(
            tmp_path,
            "b.inp",
            "** This is version 2 with more comments\n** Another comment line\n*NODE\n1, 0.0, 0.0, 0.0\n",
        )

        h1 = _compute_mesh_content_hash(str(file1))
        h2 = _compute_mesh_content_hash(str(file2))

        assert h1 == h2

    def test_boundary_changes_dont_affect_hash(self, tmp_path: Path):
        """*BOUNDARY, *STEP, *MATERIAL等の変更はハッシュに影響しない"""
        base_mesh = "*NODE\n1, 0.0, 0.0, 0.0\n*ELEMENT, TYPE=C3D8\n1, 1\n"

        file1 = self._write_inp(
            tmp_path,
            "a.inp",
            base_mesh + "*MATERIAL, NAME=STEEL\n"
            "*ELASTIC\n200000, 0.3\n"
            "*BOUNDARY\n1, 1, 6\n"
            "*STEP\n*STATIC\n1.0, 1.0\n"
            "*CLOAD\n1, 2, 1000.0\n"
            "*END STEP\n",
        )

        file2 = self._write_inp(
            tmp_path,
            "b.inp",
            base_mesh + "*MATERIAL, NAME=ALUMINUM\n"
            "*ELASTIC\n70000, 0.33\n"
            "*BOUNDARY\n1, 1, 3\n"
            "*STEP\n*DYNAMIC\n0.001, 0.1\n"
            "*DLOAD\n1, P, 500.0\n"
            "*END STEP\n",
        )

        h1 = _compute_mesh_content_hash(str(file1))
        h2 = _compute_mesh_content_hash(str(file2))

        assert h1 == h2


# ====================================================================
# ディスクキャッシュ save/load テスト
# ====================================================================


class TestMeshStatsDiskCache:
    """メッシュ統計ディスクキャッシュのテスト"""

    def test_save_and_load(self, config: GraphConfig, tmp_project: Path):
        """保存したキャッシュをロードできる"""
        pg = ProjectGraph(nodes=[], relations=[], project_root=tmp_project, config=config)
        mesh_hash = "abcdef1234567890abcdef1234567890"
        data = {
            "stats": {
                "node_count": 100,
                "element_count": 50,
                "element_types": {"C3D8": 50},
            },
            "element_quality": {"C3D8": {"element_count": 50}},
            "topology_groups": [["ELSET1", "ELSET2"]],
        }

        _save_mesh_stats_cache(pg, mesh_hash, data)
        loaded = _load_mesh_stats_cache(pg, mesh_hash)

        assert loaded is not None
        assert loaded["stats"]["node_count"] == 100
        assert loaded["stats"]["element_count"] == 50
        assert loaded["element_quality"]["C3D8"]["element_count"] == 50
        assert loaded["topology_groups"] == [["ELSET1", "ELSET2"]]

    def test_load_nonexistent_returns_none(self, config: GraphConfig, tmp_project: Path):
        """存在しないハッシュのロードはNoneを返す"""
        pg = ProjectGraph(nodes=[], relations=[], project_root=tmp_project, config=config)
        loaded = _load_mesh_stats_cache(pg, "nonexistent_hash_000000000000")
        assert loaded is None

    def test_different_hashes_independent(self, config: GraphConfig, tmp_project: Path):
        """異なるハッシュのキャッシュは独立"""
        pg = ProjectGraph(nodes=[], relations=[], project_root=tmp_project, config=config)

        data1 = {"stats": {"node_count": 100}, "element_quality": None, "topology_groups": None}
        data2 = {"stats": {"node_count": 200}, "element_quality": None, "topology_groups": None}

        _save_mesh_stats_cache(pg, "hash_aaaa" + "0" * 24, data1)
        _save_mesh_stats_cache(pg, "hash_bbbb" + "0" * 24, data2)

        loaded1 = _load_mesh_stats_cache(pg, "hash_aaaa" + "0" * 24)
        loaded2 = _load_mesh_stats_cache(pg, "hash_bbbb" + "0" * 24)

        assert loaded1["stats"]["node_count"] == 100
        assert loaded2["stats"]["node_count"] == 200


# ====================================================================
# AbaqusMeshParser統合テスト（メッシュ統計キャッシュ）
# ====================================================================


class TestMeshStatsCacheIntegration:
    """メッシュ統計キャッシュとAbaqusMeshParserの統合テスト"""

    def _write_inp(self, tmp_path: Path, name: str, content: str) -> Path:
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        return p

    def test_apply_mesh_stats_to_node(self):
        """_apply_mesh_stats_to_nodeがプロパティを正しく設定"""
        from plugins.abaqus.parse.mesh_parser import AbaqusMeshParser

        node = Node(id=1, type="go", name="test", format="inp", properties={})
        cached = {
            "stats": {
                "node_count": 500,
                "element_count": 300,
                "element_types": {"C3D8": 200, "C3D10": 100},
                "elset_summary": {"ALL": 300},
                "quality": {"volume": {"min": 1.0, "max": 10.0, "mean": 5.0}},
            },
            "element_quality": {
                "C3D8": {"element_count": 200, "quality": {"volume": {"min": 1.0, "max": 8.0, "mean": 4.0}}}
            },
            "topology_groups": [["ELSET_A", "ELSET_B"]],
        }

        AbaqusMeshParser._apply_mesh_stats_to_node(node, cached)

        assert node.properties["mesh_node_count"] == 500
        assert node.properties["mesh_element_count"] == 300
        assert node.properties["mesh_element_types"] == {"C3D8": 200, "C3D10": 100}
        assert node.properties["mesh_elset_summary"] == {"ALL": 300}
        assert node.properties["mesh_quality"]["volume"]["mean"] == 5.0
        assert node.properties["mesh_element_quality"]["C3D8"]["element_count"] == 200
        assert node.properties["mesh_topology_groups"] == [["ELSET_A", "ELSET_B"]]

    def test_apply_mesh_stats_partial(self):
        """一部がNoneのキャッシュでも正しく適用"""
        from plugins.abaqus.parse.mesh_parser import AbaqusMeshParser

        node = Node(id=1, type="go", name="test", format="inp", properties={})
        cached = {
            "stats": {
                "node_count": 100,
                "element_count": 50,
            },
            "element_quality": None,
            "topology_groups": None,
        }

        AbaqusMeshParser._apply_mesh_stats_to_node(node, cached)

        assert node.properties["mesh_node_count"] == 100
        assert node.properties["mesh_element_count"] == 50
        assert "mesh_element_quality" not in node.properties
        assert "mesh_topology_groups" not in node.properties

    def test_hash_consistency_across_calls(self, tmp_path: Path):
        """同じファイルに対して複数回のハッシュ計算が一致する"""
        file = self._write_inp(
            tmp_path,
            "test.inp",
            "*NODE\n1, 0.0, 0.0, 0.0\n2, 1.0, 0.0, 0.0\n*ELEMENT, TYPE=C3D8\n1, 1, 2\n",
        )

        h1 = _compute_mesh_content_hash(str(file))
        h2 = _compute_mesh_content_hash(str(file))
        h3 = _compute_mesh_content_hash(str(file))

        assert h1 == h2 == h3

    def test_end_to_end_cache_sharing(self, config: GraphConfig, tmp_path: Path):
        """E2E: パラメーター違いファイル間でキャッシュ共有される"""
        # .j2/storage作成
        (tmp_path / ".j2" / "storage").mkdir(parents=True)

        mesh_section = (
            "*NODE\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 1.0, 0.0, 0.0\n"
            "3, 0.0, 1.0, 0.0\n"
            "*ELEMENT, TYPE=C3D8\n"
            "1, 1, 2, 3\n"
            "*ELSET, ELSET=ALL\n"
            "1\n"
        )

        file1 = self._write_inp(
            tmp_path,
            "go_idx1.inp",
            "*PARAMETER\nthickness=5.0\n" + mesh_section + "*BOUNDARY\n1, 1, 6\n",
        )
        file2 = self._write_inp(
            tmp_path,
            "go_idx2.inp",
            "*PARAMETER\nthickness=10.0\n" + mesh_section + "*BOUNDARY\n1, 1, 3\n",
        )

        # ハッシュ一致を確認
        h1 = _compute_mesh_content_hash(str(file1))
        h2 = _compute_mesh_content_hash(str(file2))
        assert h1 == h2

        pg = ProjectGraph(nodes=[], relations=[], project_root=tmp_path, config=config)

        # file1のメッシュ統計をキャッシュに保存
        test_data = {
            "stats": {"node_count": 3, "element_count": 1, "element_types": {"C3D8": 1}},
            "element_quality": None,
            "topology_groups": None,
        }
        _save_mesh_stats_cache(pg, h1, test_data)

        # file2のハッシュ（=h1と同じ）でキャッシュをロード
        loaded = _load_mesh_stats_cache(pg, h2)
        assert loaded is not None
        assert loaded["stats"]["node_count"] == 3
        assert loaded["stats"]["element_count"] == 1
