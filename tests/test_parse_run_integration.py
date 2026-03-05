"""Parse-Run統合テスト

jj run 実行後に parse_and_save() が自動実行され、
run実行で生成されたファイルがパーサーパイプラインで検出されることを確認する。
"""

from __future__ import annotations

from pathlib import Path

import yaml

from services.run import RunService


def _setup_project(tmp_path: Path) -> None:
    """テスト用プロジェクトのセットアップ"""
    storage_dir = tmp_path / ".j2" / "storage"
    storage_dir.mkdir(parents=True)
    graph_yaml = storage_dir / "graph.yaml"
    graph_yaml.write_text(yaml.dump({"nodes": [], "relations": []}), encoding="utf-8")

    config_dir = tmp_path / ".j2" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "config.yaml").write_text(yaml.dump({}), encoding="utf-8")


def test_run_triggers_parse_and_detects_new_files(tmp_path: Path) -> None:
    """jj run 後に parse が自動実行され、生成ファイルがNode化されること"""
    _setup_project(tmp_path)

    script_path = tmp_path / "generate.py"
    script_path.write_text(
        'with open("output.csv", "w") as f:\n    f.write("a,b\\n1,2\\n")\n',
        encoding="utf-8",
    )

    service = RunService(storage_dirname=".j2/storage/run")
    result = service.execute(
        command=["python", str(script_path)],
        cwd=tmp_path,
        mode="script",
    )

    assert result.exit_code == 0
    assert "output.csv" in result.trace_files

    # グラフを読み込んでparse結果を確認
    graph_yaml = tmp_path / ".j2" / "storage" / "graph.yaml"
    graph_data = yaml.safe_load(graph_yaml.read_text(encoding="utf-8"))
    nodes = graph_data.get("nodes", [])

    # parseが生成したファイルNode（スクリプト自体と生成ファイル）
    file_nodes = [n for n in nodes if n.get("category", "file") == "file"]
    file_names = [n["name"] for n in file_nodes]
    # parseがoutput.csvとgenerate.pyのNodeを検出しているはず
    assert any("output" in name for name in file_names), f"output.csvノードが見つからない: {file_names}"
    assert any("generate" in name for name in file_names), f"generate.pyノードが見つからない: {file_names}"

    # Run Nodeも存在すること
    run_nodes = [n for n in nodes if n.get("category") == "run"]
    assert len(run_nodes) >= 1, f"Run Nodeが見つからない: {nodes}"
    assert run_nodes[0]["properties"]["discovery"] == "runtime"


def test_run_with_no_parse_skips_parse(tmp_path: Path) -> None:
    """--no-parse でparseをスキップし、既存グラフにRun Nodeのみ追加"""
    _setup_project(tmp_path)

    script_path = tmp_path / "simple.py"
    script_path.write_text(
        'with open("result.txt", "w") as f:\n    f.write("done")\n',
        encoding="utf-8",
    )

    service = RunService(storage_dirname=".j2/storage/run")
    result = service.execute(
        command=["python", str(script_path)],
        cwd=tmp_path,
        mode="script",
        no_parse=True,
    )

    assert result.exit_code == 0

    # グラフを読み込み
    graph_yaml = tmp_path / ".j2" / "storage" / "graph.yaml"
    graph_data = yaml.safe_load(graph_yaml.read_text(encoding="utf-8"))
    nodes = graph_data.get("nodes", [])

    # Run Nodeは存在する
    run_nodes = [n for n in nodes if n.get("category") == "run"]
    assert len(run_nodes) >= 1

    # no_parseなのでparseが検出するノード数は少ない
    # （既存グラフが空なので、trace_files分のみ手動作成されるはず）
    file_nodes = [n for n in nodes if n.get("category", "file") == "file"]
    # スクリプト自体のNodeはparse無しでは検出されない
    file_names = [n["name"] for n in file_nodes]
    # trace_filesのresult.txtだけが手動作成されているはず
    assert any("result.txt" in name for name in file_names), f"result.txtノードが見つからない: {file_names}"


def test_run_parse_integration_preserves_run_node_properties(tmp_path: Path) -> None:
    """parse統合後もRun Nodeのプロパティが正しく記録されること"""
    _setup_project(tmp_path)

    script_path = tmp_path / "process.py"
    script_path.write_text(
        "# props start\nncpu=8\n# props end\nimport sys\nprint('ok')\n",
        encoding="utf-8",
    )

    service = RunService(storage_dirname=".j2/storage/run")
    result = service.execute(
        command=["python", str(script_path)],
        cwd=tmp_path,
        mode="script",
    )

    assert result.exit_code == 0

    graph_yaml = tmp_path / ".j2" / "storage" / "graph.yaml"
    graph_data = yaml.safe_load(graph_yaml.read_text(encoding="utf-8"))
    nodes = graph_data.get("nodes", [])

    run_nodes = [n for n in nodes if n.get("category") == "run"]
    assert len(run_nodes) >= 1

    run_node = run_nodes[0]
    props = run_node["properties"]
    assert props["run_status"] == "completed"
    assert props["discovery"] == "runtime"
    assert props["exit_code"] == "0"
    assert props["ncpu"] == "8"
    assert "started_at" in props
    assert "finished_at" in props
    assert "duration_seconds" in props


def test_run_parse_integration_run_output_relations(tmp_path: Path) -> None:
    """parse統合後もrun_outputリレーションが正しく構築されること"""
    _setup_project(tmp_path)

    script_path = tmp_path / "writer.py"
    script_path.write_text(
        'with open("data.csv", "w") as f:\n    f.write("x,y\\n")\n',
        encoding="utf-8",
    )

    service = RunService(storage_dirname=".j2/storage/run")
    result = service.execute(
        command=["python", str(script_path)],
        cwd=tmp_path,
        mode="script",
    )

    assert result.exit_code == 0

    graph_yaml = tmp_path / ".j2" / "storage" / "graph.yaml"
    graph_data = yaml.safe_load(graph_yaml.read_text(encoding="utf-8"))
    relations = graph_data.get("relations", [])

    run_output_rels = [r for r in relations if r.get("label") == "run_output"]
    assert len(run_output_rels) >= 1, f"run_outputリレーションが見つからない: {relations}"
