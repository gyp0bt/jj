from __future__ import annotations

import json
from pathlib import Path

import yaml

from jj_types import GraphModel, Node, Relation
from services.graph.storage import _EXT_KEYS_FIELD, GraphStorage


def test_graph_storage_save_and_load_yaml(tmp_path: Path) -> None:
    storage = GraphStorage(storage_dirname=".j2/storage")
    graph = GraphModel(
        nodes=[Node(id=1, type="run", name="job1", format="cmd")],
        relations=[Relation(id=1, label="generated", node1_id=1, node2_id=1)],
    )

    path = storage.save(tmp_path, graph)
    assert path.exists()
    assert path.name == "graph.yaml"

    loaded = storage.load(tmp_path)
    assert loaded.nodes[0].name == "job1"
    assert loaded.relations[0].label == "generated"


def test_graph_storage_detects_existing_json(tmp_path: Path) -> None:
    storage = GraphStorage(storage_dirname=".j2/storage")
    graph = GraphModel(nodes=[], relations=[])

    json_path = storage.save(tmp_path, graph, filename="graph.json")
    assert json_path.exists()

    loaded = storage.load(tmp_path)
    assert loaded.nodes == []
    assert loaded.relations == []


# =========================================================
# プロパティ外部化テスト
# =========================================================


def _make_graph_with_heavy_props() -> GraphModel:
    """テスト用: 重いプロパティを持つノードを含むグラフを生成"""
    return GraphModel(
        nodes=[
            Node(
                id=1,
                type="go_model",
                name="model_001",
                format="inp",
                properties={
                    "path": "models/model_001.inp",
                    "index": "1",
                    "active": "true",
                    "mesh_node_count": 15234,
                    "mesh_element_types": ["C3D8", "C3D10"],
                    "mesh_elset_summary": {"ELSET_1": 2000, "ELSET_2": 3000},
                    "mesh_topology_groups": [
                        {"id": 1, "node_count": 5000, "connected": True},
                    ],
                },
            ),
            Node(
                id=2,
                type="file",
                name="readme",
                format="md",
                properties={
                    "path": "README.md",
                    "active": "true",
                },
            ),
        ],
        relations=[Relation(id=1, label="contains", node1_id=1, node2_id=2)],
    )


def test_save_externalizes_heavy_properties(tmp_path: Path) -> None:
    """save時にlist/dictプロパティが外部ファイルに分離されること"""
    storage = GraphStorage(storage_dirname=".j2/storage")
    graph = _make_graph_with_heavy_props()

    storage.save(tmp_path, graph)

    # graph.yaml を直接読んで確認
    yaml_path = tmp_path / ".j2/storage/graph.yaml"
    with yaml_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    node1_props = raw["nodes"][0]["properties"]
    # スカラー値は残っている
    assert node1_props["path"] == "models/model_001.inp"
    assert node1_props["mesh_node_count"] == 15234
    # 重いプロパティはgraph.yamlから消えている
    assert "mesh_element_types" not in node1_props
    assert "mesh_elset_summary" not in node1_props
    assert "mesh_topology_groups" not in node1_props
    # _ext_keysマーカーが存在する
    assert _EXT_KEYS_FIELD in node1_props
    assert sorted(node1_props[_EXT_KEYS_FIELD]) == [
        "mesh_element_types",
        "mesh_elset_summary",
        "mesh_topology_groups",
    ]

    # node2 にはlist/dictプロパティがないので_ext_keysなし
    node2_props = raw["nodes"][1]["properties"]
    assert _EXT_KEYS_FIELD not in node2_props

    # 外部プロパティファイルが存在する
    ext_path = tmp_path / ".j2/storage/properties/node_1.json"
    assert ext_path.exists()
    with ext_path.open("r", encoding="utf-8") as f:
        ext_data = json.load(f)
    assert ext_data["mesh_element_types"] == ["C3D8", "C3D10"]
    assert ext_data["mesh_elset_summary"] == {"ELSET_1": 2000, "ELSET_2": 3000}

    # node2 の外部ファイルは存在しない
    assert not (tmp_path / ".j2/storage/properties/node_2.json").exists()


def test_load_default_lightweight(tmp_path: Path) -> None:
    """デフォルトload（軽量）では外部化プロパティが含まれないこと"""
    storage = GraphStorage(storage_dirname=".j2/storage")
    graph = _make_graph_with_heavy_props()
    storage.save(tmp_path, graph)

    loaded = storage.load(tmp_path)
    node1 = loaded.nodes[0]
    # スカラー値はある
    assert node1.properties["path"] == "models/model_001.inp"
    assert node1.properties["mesh_node_count"] == 15234
    # 重いプロパティは含まれない
    assert "mesh_element_types" not in node1.properties
    assert "mesh_elset_summary" not in node1.properties
    # _ext_keysマーカーはある
    assert _EXT_KEYS_FIELD in node1.properties


def test_load_with_resolve_externalized(tmp_path: Path) -> None:
    """resolve_externalized=Trueで全プロパティが結合されること"""
    storage = GraphStorage(storage_dirname=".j2/storage")
    graph = _make_graph_with_heavy_props()
    storage.save(tmp_path, graph)

    loaded = storage.load(tmp_path, resolve_externalized=True)
    node1 = loaded.nodes[0]
    # すべてのプロパティが復元されている
    assert node1.properties["mesh_element_types"] == ["C3D8", "C3D10"]
    assert node1.properties["mesh_elset_summary"] == {"ELSET_1": 2000, "ELSET_2": 3000}
    assert node1.properties["mesh_topology_groups"] == [
        {"id": 1, "node_count": 5000, "connected": True},
    ]
    # _ext_keysマーカーは解決後に除去される
    assert _EXT_KEYS_FIELD not in node1.properties
    # スカラー値も健在
    assert node1.properties["path"] == "models/model_001.inp"


def test_load_node_properties_on_demand(tmp_path: Path) -> None:
    """load_node_properties で個別ノードの外部プロパティが取得できること"""
    storage = GraphStorage(storage_dirname=".j2/storage")
    graph = _make_graph_with_heavy_props()
    storage.save(tmp_path, graph)

    ext_props = storage.load_node_properties(tmp_path, 1)
    assert ext_props["mesh_element_types"] == ["C3D8", "C3D10"]
    assert ext_props["mesh_elset_summary"]["ELSET_1"] == 2000

    # 存在しないノードIDは空dict
    assert storage.load_node_properties(tmp_path, 999) == {}


def test_save_node_properties_standalone(tmp_path: Path) -> None:
    """save_node_properties で直接外部プロパティを保存・読み込みできること"""
    storage = GraphStorage(storage_dirname=".j2/storage")

    props = {"materials": ["steel", "aluminum"], "counts": {"a": 10, "b": 20}}
    storage.save_node_properties(tmp_path, 42, props)

    loaded = storage.load_node_properties(tmp_path, 42)
    assert loaded == props


def test_scalar_only_node_no_externalization(tmp_path: Path) -> None:
    """スカラー値のみのノードは外部化されないこと"""
    storage = GraphStorage(storage_dirname=".j2/storage")
    graph = GraphModel(
        nodes=[
            Node(
                id=1,
                type="file",
                name="test",
                format="txt",
                properties={"path": "test.txt", "count": 5, "flag": True},
            ),
        ],
        relations=[],
    )
    storage.save(tmp_path, graph)

    loaded = storage.load(tmp_path)
    assert _EXT_KEYS_FIELD not in loaded.nodes[0].properties
    assert not (tmp_path / ".j2/storage/properties/node_1.json").exists()


def test_empty_list_dict_not_externalized(tmp_path: Path) -> None:
    """空のlist/dictは外部化されないこと"""
    storage = GraphStorage(storage_dirname=".j2/storage")
    graph = GraphModel(
        nodes=[
            Node(
                id=1,
                type="file",
                name="test",
                format="txt",
                properties={"path": "test.txt", "empty_list": [], "empty_dict": {}},
            ),
        ],
        relations=[],
    )
    storage.save(tmp_path, graph)

    loaded = storage.load(tmp_path)
    # 空list/dictはgraph.yamlに残る（外部化しない）
    assert _EXT_KEYS_FIELD not in loaded.nodes[0].properties


def test_orphan_properties_cleaned_up(tmp_path: Path) -> None:
    """ノードが削除された場合、対応する外部プロパティファイルも削除されること"""
    storage = GraphStorage(storage_dirname=".j2/storage")

    # ノード1, 2でsave
    graph = GraphModel(
        nodes=[
            Node(
                id=1,
                type="file",
                name="a",
                format="inp",
                properties={"data": [1, 2, 3]},
            ),
            Node(
                id=2,
                type="file",
                name="b",
                format="inp",
                properties={"data": [4, 5, 6]},
            ),
        ],
        relations=[],
    )
    storage.save(tmp_path, graph)
    assert (tmp_path / ".j2/storage/properties/node_1.json").exists()
    assert (tmp_path / ".j2/storage/properties/node_2.json").exists()

    # ノード2を削除してsave
    graph2 = GraphModel(
        nodes=[
            Node(
                id=1,
                type="file",
                name="a",
                format="inp",
                properties={"data": [1, 2, 3]},
            ),
        ],
        relations=[],
    )
    storage.save(tmp_path, graph2)
    assert (tmp_path / ".j2/storage/properties/node_1.json").exists()
    assert not (tmp_path / ".j2/storage/properties/node_2.json").exists()


def test_roundtrip_save_load_resolve(tmp_path: Path) -> None:
    """save → load(resolve) のラウンドトリップでデータが完全に復元されること"""
    storage = GraphStorage(storage_dirname=".j2/storage")
    original = _make_graph_with_heavy_props()

    storage.save(tmp_path, original)
    restored = storage.load(tmp_path, resolve_externalized=True)

    assert len(restored.nodes) == len(original.nodes)
    assert len(restored.relations) == len(original.relations)

    for orig_node, rest_node in zip(original.nodes, restored.nodes, strict=True):
        assert orig_node.id == rest_node.id
        assert orig_node.name == rest_node.name
        assert orig_node.type == rest_node.type
        # プロパティの完全一致（_ext_keysは含まれない）
        assert orig_node.properties == rest_node.properties
