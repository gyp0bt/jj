from __future__ import annotations

from pathlib import Path

import yaml

from services.run import RunService


def test_run_service_script_mode_tracks_files_and_props(tmp_path: Path) -> None:
    script_path = tmp_path / "script.py"
    script_path.write_text(
        """
# props start
ncpu=4
# props end
import sys
size = sys.argv[1]
with open("output.txt", "w", encoding="utf-8") as f:
    f.write(size)
""".strip()
        + "\n",
        encoding="utf-8",
    )

    service = RunService(storage_dirname=".j2/storage/run")
    result = service.execute(
        command=["python", str(script_path), "128"],
        cwd=tmp_path,
        mode="script",
    )

    assert result.exit_code == 0
    assert result.script_path == script_path.resolve()
    assert "output.txt" in result.trace_files
    assert result.properties["ncpu"] == "4"
    assert result.properties["size"] == "128"
    assert result.log_path is not None
    assert result.log_path.exists()


def test_run_service_creates_run_node_with_category(tmp_path: Path) -> None:
    """M7 Phase 4: RunServiceが実行時RunをNodeCategory.RUNとして記録する"""
    # .j2/storage/graph.yamlに初期グラフを用意
    storage_dir = tmp_path / ".j2" / "storage"
    storage_dir.mkdir(parents=True)
    graph_yaml = storage_dir / "graph.yaml"
    graph_yaml.write_text(yaml.dump({"nodes": [], "relations": []}), encoding="utf-8")

    # config
    config_dir = tmp_path / ".j2" / "config"
    config_dir.mkdir(parents=True)
    config_yaml = config_dir / "config.yaml"
    config_yaml.write_text(yaml.dump({}), encoding="utf-8")

    script_path = tmp_path / "process.py"
    script_path.write_text(
        'with open("result.csv", "w") as f:\n    f.write("data")\n',
        encoding="utf-8",
    )

    service = RunService(storage_dirname=".j2/storage/run")
    result = service.execute(
        command=["python", str(script_path)],
        cwd=tmp_path,
        mode="script",
    )

    assert result.exit_code == 0

    # グラフを読み込んでRun Nodeが作成されているか確認
    graph_data = yaml.safe_load(graph_yaml.read_text(encoding="utf-8"))
    nodes = graph_data.get("nodes", [])

    # Run Nodeが存在するか
    run_nodes = [n for n in nodes if n.get("category") == "run"]
    assert len(run_nodes) >= 1, f"Run Nodeが見つからない: {nodes}"

    run_node = run_nodes[0]
    assert run_node["properties"]["run_type"] == "script"
    assert run_node["properties"]["run_status"] == "completed"
    assert run_node["properties"]["discovery"] == "runtime"
    assert run_node["properties"]["exit_code"] == "0"

    # run_outputリレーションが存在するか
    relations = graph_data.get("relations", [])
    run_output_rels = [r for r in relations if r.get("label") == "run_output"]
    assert len(run_output_rels) >= 1, f"run_outputリレーションが見つからない: {relations}"


def test_run_service_detects_ml_training_type(tmp_path: Path) -> None:
    """M7 Phase 4: MLスクリプトのrun_type推定テスト"""
    storage_dir = tmp_path / ".j2" / "storage"
    storage_dir.mkdir(parents=True)
    graph_yaml = storage_dir / "graph.yaml"
    graph_yaml.write_text(yaml.dump({"nodes": [], "relations": []}), encoding="utf-8")

    config_dir = tmp_path / ".j2" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "config.yaml").write_text(yaml.dump({}), encoding="utf-8")

    ml_script = tmp_path / "train.py"
    ml_script.write_text(
        "import torch\nprint('training complete')\n",
        encoding="utf-8",
    )

    service = RunService(storage_dirname=".j2/storage/run")
    service.execute(
        command=["python", str(ml_script)],
        cwd=tmp_path,
        mode="script",
    )

    # グラフからrun_typeを確認
    graph_data = yaml.safe_load(graph_yaml.read_text(encoding="utf-8"))
    run_nodes = [n for n in graph_data.get("nodes", []) if n.get("category") == "run"]
    assert len(run_nodes) >= 1
    assert run_nodes[0]["properties"]["run_type"] == "ml_training"


def test_run_service_job_mode_skips_trace(tmp_path: Path) -> None:
    service = RunService(storage_dirname=".j2/storage/run")
    result = service.execute(
        command=["python", "-c", "print('hello')"],
        cwd=tmp_path,
    )

    assert result.mode == "job"
    assert result.trace_files == []
    assert result.script_path is None
