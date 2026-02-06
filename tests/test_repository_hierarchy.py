"""レポジトリ階層制約のテスト

全ノードがレポジトリの下に帰属し、レポジトリはレポジトリの下にしか
存在できない制約を検証するテスト。

[READMEへ戻る](../README.md)
"""
from pathlib import Path
import pytest

from jj_types import (
    GraphModel,
    Node,
    Relation,
    NODE_TYPE_REPOSITORY,
    RELATION_BELONGS_TO,
)
from services.graph import GraphService
from config import GraphConfig


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "graph_test1"


class TestRootRepositoryCreation:
    """ルートレポジトリノードの生成テスト"""

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict({
            "vocab": {},
            "path-type-map": {},
            "ignore": [],
            "obsidian": {},
        })

    @pytest.fixture
    def graph_service(self, config):
        if not FIXTURE_DIR.exists():
            pytest.skip(f"Fixture directory not found: {FIXTURE_DIR}")
        return GraphService(project_root=FIXTURE_DIR, config=config)

    def test_root_repository_exists(self, graph_service):
        """parse_projectでルートレポジトリノードが生成される"""
        graph = graph_service.parse_project()
        repo_nodes = [n for n in graph.nodes if n.type == NODE_TYPE_REPOSITORY]
        assert len(repo_nodes) >= 1, "レポジトリノードが存在しない"

        root_repos = [
            n for n in repo_nodes
            if n.properties.get("is_root") == "true"
        ]
        assert len(root_repos) == 1, f"ルートレポジトリが1つでない: {len(root_repos)}"

    def test_root_repository_properties(self, graph_service):
        """ルートレポジトリのプロパティが正しい"""
        graph = graph_service.parse_project()
        root = next(
            n for n in graph.nodes
            if n.type == NODE_TYPE_REPOSITORY
            and n.properties.get("is_root") == "true"
        )
        assert root.name == FIXTURE_DIR.name
        assert root.format == "repository"
        assert root.properties["path"] == "."
        assert root.properties["depth"] == "0"

    def test_root_repository_has_no_belongs_to(self, graph_service):
        """ルートレポジトリはbelongs_to関係の子側に現れない"""
        graph = graph_service.parse_project()
        root = next(
            n for n in graph.nodes
            if n.type == NODE_TYPE_REPOSITORY
            and n.properties.get("is_root") == "true"
        )
        belongs_to_rels = [
            r for r in graph.relations
            if r.label == RELATION_BELONGS_TO and r.node1_id == root.id
        ]
        assert len(belongs_to_rels) == 0, "ルートレポジトリが belongs_to の子側にある"


class TestBelongsToRelations:
    """belongs_to関係のテスト"""

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

    def test_all_non_repo_nodes_have_belongs_to(self, graph_service):
        """全非レポジトリノードが belongs_to 関係を持つ"""
        graph = graph_service.parse_project()

        belongs_to_child_ids = {
            r.node1_id for r in graph.relations
            if r.label == RELATION_BELONGS_TO
        }

        non_repo_nodes = [
            n for n in graph.nodes if n.type != NODE_TYPE_REPOSITORY
        ]
        for node in non_repo_nodes:
            assert node.id in belongs_to_child_ids, (
                f"ノード '{node.name}' (type={node.type}) が "
                f"belongs_to 関係を持たない"
            )

    def test_belongs_to_points_to_repository(self, graph_service):
        """belongs_to の node2_id は必ず repository タイプ"""
        graph = graph_service.parse_project()
        node_map = {n.id: n for n in graph.nodes}

        belongs_to_rels = [
            r for r in graph.relations if r.label == RELATION_BELONGS_TO
        ]
        for rel in belongs_to_rels:
            parent = node_map[rel.node2_id]
            assert parent.type == NODE_TYPE_REPOSITORY, (
                f"belongs_to の先が repository でない: "
                f"{parent.name} (type={parent.type})"
            )

    def test_belongs_to_count_matches_non_repo_nodes(self, graph_service):
        """belongs_to関係の数が非レポジトリノード数と一致（サブレポジトリなしの場合）"""
        graph = graph_service.parse_project()

        belongs_to_rels = [
            r for r in graph.relations if r.label == RELATION_BELONGS_TO
        ]
        non_repo_nodes = [
            n for n in graph.nodes if n.type != NODE_TYPE_REPOSITORY
        ]
        # サブレポジトリがない場合、belongs_to数 == 非レポジトリノード数
        assert len(belongs_to_rels) == len(non_repo_nodes)


class TestValidateRepositoryHierarchy:
    """validate_repository_hierarchy() のテスト"""

    def test_valid_graph_no_errors(self):
        """正しいグラフではエラーが出ない"""
        repo = Node(
            id=1, type=NODE_TYPE_REPOSITORY, name="root",
            format="repository",
            properties={"path": ".", "is_root": "true", "depth": "0"},
        )
        file_node = Node(
            id=2, type="go", name="go_idx1", format="inp",
            properties={"path": "go_idx1.inp"},
        )
        rel = Relation(
            id=1, label=RELATION_BELONGS_TO,
            node1_id=2, node2_id=1,
        )
        graph = GraphModel(nodes=[repo, file_node], relations=[rel])
        errors = graph.validate_repository_hierarchy()
        assert errors == []

    def test_missing_belongs_to_for_non_repo(self):
        """非レポジトリノードが belongs_to を持たない場合エラー"""
        repo = Node(
            id=1, type=NODE_TYPE_REPOSITORY, name="root",
            format="repository",
            properties={"path": ".", "is_root": "true", "depth": "0"},
        )
        orphan = Node(
            id=2, type="go", name="orphan", format="inp",
            properties={"path": "orphan.inp"},
        )
        graph = GraphModel(nodes=[repo, orphan], relations=[])
        errors = graph.validate_repository_hierarchy()
        assert any("orphan" in e for e in errors)

    def test_no_root_repository(self):
        """ルートレポジトリがない場合エラー"""
        file_node = Node(
            id=1, type="go", name="go_idx1", format="inp",
            properties={"path": "go_idx1.inp"},
        )
        graph = GraphModel(nodes=[file_node], relations=[])
        errors = graph.validate_repository_hierarchy()
        assert any("ルートレポジトリが存在しません" in e for e in errors)

    def test_multiple_root_repositories(self):
        """ルートレポジトリが複数ある場合エラー"""
        repo1 = Node(
            id=1, type=NODE_TYPE_REPOSITORY, name="root1",
            format="repository",
            properties={"path": ".", "is_root": "true", "depth": "0"},
        )
        repo2 = Node(
            id=2, type=NODE_TYPE_REPOSITORY, name="root2",
            format="repository",
            properties={"path": ".", "is_root": "true", "depth": "0"},
        )
        graph = GraphModel(nodes=[repo1, repo2], relations=[])
        errors = graph.validate_repository_hierarchy()
        assert any("複数存在" in e for e in errors)

    def test_belongs_to_non_repository_target(self):
        """belongs_to の先がレポジトリでない場合エラー"""
        repo = Node(
            id=1, type=NODE_TYPE_REPOSITORY, name="root",
            format="repository",
            properties={"path": ".", "is_root": "true", "depth": "0"},
        )
        file1 = Node(
            id=2, type="go", name="go_idx1", format="inp",
            properties={"path": "go_idx1.inp"},
        )
        file2 = Node(
            id=3, type="mesh", name="mesh", format="inp",
            properties={"path": "mesh.inp"},
        )
        # file2 が file1 に belongs_to（不正: 先がレポジトリでない）
        bad_rel = Relation(
            id=1, label=RELATION_BELONGS_TO,
            node1_id=3, node2_id=2,
        )
        good_rel = Relation(
            id=2, label=RELATION_BELONGS_TO,
            node1_id=2, node2_id=1,
        )
        graph = GraphModel(
            nodes=[repo, file1, file2],
            relations=[bad_rel, good_rel],
        )
        errors = graph.validate_repository_hierarchy()
        assert any("レポジトリではありません" in e for e in errors)

    def test_sub_repository_without_belongs_to(self):
        """サブレポジトリが belongs_to を持たない場合エラー"""
        root = Node(
            id=1, type=NODE_TYPE_REPOSITORY, name="root",
            format="repository",
            properties={"path": ".", "is_root": "true", "depth": "0"},
        )
        sub = Node(
            id=2, type=NODE_TYPE_REPOSITORY, name="sub",
            format="repository",
            properties={"path": "sub", "is_root": "false", "depth": "1"},
        )
        graph = GraphModel(nodes=[root, sub], relations=[])
        errors = graph.validate_repository_hierarchy()
        assert any("ルートでないのに親がいない" in e for e in errors)

    def test_valid_sub_repository_hierarchy(self):
        """サブレポジトリの正しい階層ではエラーなし"""
        root = Node(
            id=1, type=NODE_TYPE_REPOSITORY, name="root",
            format="repository",
            properties={"path": ".", "is_root": "true", "depth": "0"},
        )
        sub = Node(
            id=2, type=NODE_TYPE_REPOSITORY, name="sub",
            format="repository",
            properties={"path": "sub", "is_root": "false", "depth": "1"},
        )
        file_node = Node(
            id=3, type="go", name="go_idx1", format="inp",
            properties={"path": "sub/go_idx1.inp"},
        )
        rels = [
            Relation(id=1, label=RELATION_BELONGS_TO, node1_id=2, node2_id=1),
            Relation(id=2, label=RELATION_BELONGS_TO, node1_id=3, node2_id=2),
        ]
        graph = GraphModel(nodes=[root, sub, file_node], relations=rels)
        errors = graph.validate_repository_hierarchy()
        assert errors == []


class TestSubRepositoryDetection:
    """サブレポジトリ検出のテスト"""

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict({
            "vocab": {},
            "path-type-map": {},
            "ignore": [],
            "obsidian": {},
        })

    def test_sub_repository_with_jj_dir(self, tmp_path, config):
        """サブディレクトリに .jj/ があればサブレポジトリとして検出"""
        # ルートにファイルを作成
        (tmp_path / "go_idx1.inp").write_text("*HEADING\ntest\n")

        # サブレポジトリを作成（.jj/ディレクトリ付き）
        sub_dir = tmp_path / "sub_project"
        sub_dir.mkdir()
        (sub_dir / ".jj").mkdir()
        (sub_dir / "go_idx2.inp").write_text("*HEADING\nsub\n")

        gs = GraphService(project_root=tmp_path, config=config)
        graph = gs.parse_project(extensions=[".inp"])

        repo_nodes = [n for n in graph.nodes if n.type == NODE_TYPE_REPOSITORY]
        assert len(repo_nodes) == 2, f"レポジトリが2つでない: {len(repo_nodes)}"

        root_repos = [n for n in repo_nodes if n.properties.get("is_root") == "true"]
        sub_repos = [n for n in repo_nodes if n.properties.get("is_root") == "false"]
        assert len(root_repos) == 1
        assert len(sub_repos) == 1
        assert sub_repos[0].name == "sub_project"

    def test_sub_repo_node_belongs_to_root(self, tmp_path, config):
        """サブレポジトリノードはルートレポジトリにbelongs_to"""
        sub_dir = tmp_path / "sub_project"
        sub_dir.mkdir()
        (sub_dir / ".jj").mkdir()
        (sub_dir / "go_idx1.inp").write_text("*HEADING\nsub\n")

        gs = GraphService(project_root=tmp_path, config=config)
        graph = gs.parse_project(extensions=[".inp"])

        root = next(
            n for n in graph.nodes
            if n.type == NODE_TYPE_REPOSITORY
            and n.properties.get("is_root") == "true"
        )
        sub = next(
            n for n in graph.nodes
            if n.type == NODE_TYPE_REPOSITORY
            and n.properties.get("is_root") == "false"
        )

        # サブレポジトリ→ルートの belongs_to
        bt = next(
            (r for r in graph.relations
             if r.label == RELATION_BELONGS_TO
             and r.node1_id == sub.id
             and r.node2_id == root.id),
            None,
        )
        assert bt is not None, "サブレポジトリ→ルートの belongs_to がない"

    def test_file_in_sub_repo_belongs_to_sub(self, tmp_path, config):
        """サブレポジトリ内のファイルはサブレポジトリにbelongs_to"""
        sub_dir = tmp_path / "sub_project"
        sub_dir.mkdir()
        (sub_dir / ".jj").mkdir()
        (sub_dir / "go_idx1.inp").write_text("*HEADING\nsub\n")

        gs = GraphService(project_root=tmp_path, config=config)
        graph = gs.parse_project(extensions=[".inp"])

        sub_repo = next(
            n for n in graph.nodes
            if n.type == NODE_TYPE_REPOSITORY
            and n.properties.get("is_root") == "false"
        )
        go_node = next(
            n for n in graph.nodes
            if n.name == "go_idx1" and n.format == "inp"
        )

        # ファイル→サブレポジトリの belongs_to
        bt = next(
            (r for r in graph.relations
             if r.label == RELATION_BELONGS_TO
             and r.node1_id == go_node.id
             and r.node2_id == sub_repo.id),
            None,
        )
        assert bt is not None, (
            "サブレポジトリ内のファイルがサブレポジトリに belongs_to しない"
        )

    def test_file_in_root_belongs_to_root(self, tmp_path, config):
        """ルートのファイルはルートレポジトリにbelongs_to"""
        (tmp_path / "go_idx1.inp").write_text("*HEADING\ntest\n")

        gs = GraphService(project_root=tmp_path, config=config)
        graph = gs.parse_project(extensions=[".inp"])

        root = next(
            n for n in graph.nodes
            if n.type == NODE_TYPE_REPOSITORY
            and n.properties.get("is_root") == "true"
        )
        go_node = next(
            n for n in graph.nodes
            if n.name == "go_idx1" and n.format == "inp"
        )

        bt = next(
            (r for r in graph.relations
             if r.label == RELATION_BELONGS_TO
             and r.node1_id == go_node.id
             and r.node2_id == root.id),
            None,
        )
        assert bt is not None, "ルート直下ファイルがルートレポジトリに belongs_to しない"

    def test_directory_without_jj_is_not_repo(self, tmp_path, config):
        """通常のディレクトリ（.jjなし）はレポジトリにならない"""
        normal_dir = tmp_path / "normal_dir"
        normal_dir.mkdir()
        (normal_dir / "go_idx1.inp").write_text("*HEADING\nnormal\n")

        gs = GraphService(project_root=tmp_path, config=config)
        graph = gs.parse_project(extensions=[".inp"])

        repo_nodes = [n for n in graph.nodes if n.type == NODE_TYPE_REPOSITORY]
        # ルートレポジトリのみ
        assert len(repo_nodes) == 1
        assert repo_nodes[0].properties.get("is_root") == "true"


class TestNestedSubRepositories:
    """ネストされたサブレポジトリのテスト"""

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict({
            "vocab": {},
            "path-type-map": {},
            "ignore": [],
            "obsidian": {},
        })

    def test_nested_repos(self, tmp_path, config):
        """ネストされたサブレポジトリが正しく検出される"""
        # root/
        #   sub1/
        #     .jj/
        #     sub2/
        #       .jj/
        #       go_idx1.inp
        sub1 = tmp_path / "sub1"
        sub1.mkdir()
        (sub1 / ".jj").mkdir()

        sub2 = sub1 / "sub2"
        sub2.mkdir()
        (sub2 / ".jj").mkdir()
        (sub2 / "go_idx1.inp").write_text("*HEADING\ndeep\n")

        gs = GraphService(project_root=tmp_path, config=config)
        graph = gs.parse_project(extensions=[".inp"])

        repo_nodes = [n for n in graph.nodes if n.type == NODE_TYPE_REPOSITORY]
        assert len(repo_nodes) == 3, f"レポジトリが3つでない: {len(repo_nodes)}"

        # バリデーション
        errors = graph.validate_repository_hierarchy()
        assert errors == [], f"バリデーションエラー: {errors}"

    def test_nested_repo_depth(self, tmp_path, config):
        """ネストされたレポジトリの深さが正しい"""
        sub1 = tmp_path / "sub1"
        sub1.mkdir()
        (sub1 / ".jj").mkdir()

        sub2 = sub1 / "sub2"
        sub2.mkdir()
        (sub2 / ".jj").mkdir()

        gs = GraphService(project_root=tmp_path, config=config)
        graph = gs.parse_project(extensions=[".inp"])

        repo_nodes = sorted(
            [n for n in graph.nodes if n.type == NODE_TYPE_REPOSITORY],
            key=lambda n: int(n.properties.get("depth", "0")),
        )
        assert repo_nodes[0].properties["depth"] == "0"  # root
        assert repo_nodes[1].properties["depth"] == "1"  # sub1
        assert repo_nodes[2].properties["depth"] == "2"  # sub2

    def test_file_belongs_to_nearest_repo(self, tmp_path, config):
        """ファイルは最も近い祖先レポジトリに帰属する"""
        sub1 = tmp_path / "sub1"
        sub1.mkdir()
        (sub1 / ".jj").mkdir()
        (sub1 / "go_idx1.inp").write_text("*HEADING\nsub1\n")

        sub2 = sub1 / "sub2"
        sub2.mkdir()
        (sub2 / ".jj").mkdir()
        (sub2 / "go_idx2.inp").write_text("*HEADING\nsub2\n")

        gs = GraphService(project_root=tmp_path, config=config)
        graph = gs.parse_project(extensions=[".inp"])

        sub1_repo = next(
            n for n in graph.nodes
            if n.type == NODE_TYPE_REPOSITORY and n.name == "sub1"
        )
        sub2_repo = next(
            n for n in graph.nodes
            if n.type == NODE_TYPE_REPOSITORY and n.name == "sub2"
        )
        go1 = next(
            n for n in graph.nodes
            if n.name == "go_idx1" and n.format == "inp"
        )
        go2 = next(
            n for n in graph.nodes
            if n.name == "go_idx2" and n.format == "inp"
        )

        # go_idx1 → sub1
        bt1 = next(
            r for r in graph.relations
            if r.label == RELATION_BELONGS_TO and r.node1_id == go1.id
        )
        assert bt1.node2_id == sub1_repo.id

        # go_idx2 → sub2
        bt2 = next(
            r for r in graph.relations
            if r.label == RELATION_BELONGS_TO and r.node1_id == go2.id
        )
        assert bt2.node2_id == sub2_repo.id


class TestGraphServiceSummaryWithRepository:
    """summaryにレポジトリ情報が含まれるテスト"""

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict({
            "vocab": {},
            "path-type-map": {},
            "ignore": [],
            "obsidian": {},
        })

    @pytest.fixture
    def graph_service(self, config):
        if not FIXTURE_DIR.exists():
            pytest.skip(f"Fixture directory not found: {FIXTURE_DIR}")
        return GraphService(project_root=FIXTURE_DIR, config=config)

    def test_summary_includes_repository_type(self, graph_service):
        """summaryにrepositoryタイプが含まれる"""
        graph = graph_service.parse_project()
        summary = graph_service.summary(graph)
        assert NODE_TYPE_REPOSITORY in summary["nodes_by_type"]

    def test_summary_includes_belongs_to_label(self, graph_service):
        """summaryにbelongs_toラベルが含まれる"""
        graph = graph_service.parse_project()
        summary = graph_service.summary(graph)
        assert RELATION_BELONGS_TO in summary["relations_by_label"]


class TestIntegrationValidation:
    """統合テスト: parse_projectの結果がバリデーションを通過する"""

    @pytest.fixture
    def config(self):
        return GraphConfig.from_dict({
            "vocab": {"idx": "番号"},
            "path-type-map": {
                "**go_*": {"*.inp": "Abaqusインプット", "*.odb": "Abaqus ODB"},
            },
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

    def test_full_parse_passes_validation(self, graph_service):
        """parse_projectの結果がバリデーションをパスする"""
        graph = graph_service.parse_project()
        errors = graph.validate_repository_hierarchy()
        assert errors == [], f"バリデーションエラー:\n" + "\n".join(errors)

    def test_directory_nodes_have_belongs_to(self, graph_service):
        """ディレクトリノードもbelongs_toを持つ"""
        extensions = [".inp", ".csv", ".png", ".yaml"]
        graph = graph_service.parse_project(extensions=extensions)

        dir_nodes = [n for n in graph.nodes if n.format == "directory"]
        belongs_to_child_ids = {
            r.node1_id for r in graph.relations
            if r.label == RELATION_BELONGS_TO
        }
        for dn in dir_nodes:
            assert dn.id in belongs_to_child_ids, (
                f"ディレクトリノード '{dn.name}' が belongs_to を持たない"
            )

    def test_material_nodes_have_belongs_to(self, graph_service):
        """abaqus_materialノードもbelongs_toを持つ"""
        graph = graph_service.parse_project(extensions=[".inp"])

        mat_nodes = [n for n in graph.nodes if n.type == "abaqus_material"]
        belongs_to_child_ids = {
            r.node1_id for r in graph.relations
            if r.label == RELATION_BELONGS_TO
        }
        for mn in mat_nodes:
            assert mn.id in belongs_to_child_ids, (
                f"materialノード '{mn.name}' が belongs_to を持たない"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
