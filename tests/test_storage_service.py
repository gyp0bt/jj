from __future__ import annotations

from pathlib import Path

from services.storage import GraphStorage
from types import GraphModel, Node, Relation


def test_graph_storage_save_and_load_yaml(tmp_path: Path) -> None:
    storage = GraphStorage(storage_dirname=".jj/storage")
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
    storage = GraphStorage(storage_dirname=".jj/storage")
    graph = GraphModel(nodes=[], relations=[])

    json_path = storage.save(tmp_path, graph, filename="graph.json")
    assert json_path.exists()

    loaded = storage.load(tmp_path)
    assert loaded.nodes == []
    assert loaded.relations == []
