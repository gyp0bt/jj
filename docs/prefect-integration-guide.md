[← README.md](../README.md)

# Prefect連携ガイド — jj + Prefectによるワークフロー自動化

## 概要

[Prefect](https://www.prefect.io/) はPython製のワークフローオーケストレーションツールです。
jjのCLIコマンドやPython APIをPrefectのtask/flowに組み込むことで、
CAEシミュレーションのパラメトリックスタディやバッチ処理を自動化できます。

## 前提条件

```bash
pip install prefect
pip install -e ".[dev]"  # jjのインストール
```

## 基本パターン

### 1. jj CLIをPrefectタスクから呼び出す

```python
from prefect import flow, task
import subprocess

@task(name="parse-project")
def parse_project(project_dir: str) -> None:
    """jj parseでプロジェクトグラフを生成"""
    subprocess.run(["jj", "parse"], cwd=project_dir, check=True)

@task(name="export-csv")
def export_csv(project_dir: str, output: str = "results.csv") -> str:
    """jj export csvでCSVエクスポート"""
    subprocess.run(
        ["jj", "export", "csv", "-o", output],
        cwd=project_dir,
        check=True,
    )
    return f"{project_dir}/{output}"

@flow(name="jj-parse-export")
def parse_and_export(project_dir: str):
    parse_project(project_dir)
    csv_path = export_csv(project_dir)
    print(f"Exported: {csv_path}")

# 実行
parse_and_export("/path/to/project")
```

### 2. jj Python APIをPrefectタスクから使う

```python
from prefect import flow, task
import jj

@task(name="get-analysis-status")
def get_analysis_status(node_name: str, project_root: str) -> str:
    """ノードの解析ステータスを取得"""
    return jj.get_property(node_name, "analysis_status", project_root=project_root) or "unknown"

@task(name="get-result-nodes")
def get_result_nodes(project_root: str) -> list:
    """解析完了ノードの一覧を取得"""
    nodes = jj.get_nodes(project_root=project_root)
    return [n for n in nodes if n.name.startswith("go_")]

@flow(name="check-results")
def check_results(project_root: str):
    nodes = get_result_nodes(project_root)
    for node in nodes:
        status = get_analysis_status(node.name, project_root)
        print(f"{node.name}: {status}")

check_results("/path/to/project")
```

### 3. jj r によるコマンド実行をPrefectフローに組み込む

```python
from prefect import flow, task
import subprocess

@task(name="run-simulation", retries=2)
def run_simulation(script: str, project_dir: str) -> int:
    """jj r でシミュレーションスクリプトを実行"""
    result = subprocess.run(
        ["jj", "r", "python", script],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"STDERR: {result.stderr}")
    return result.returncode

@task(name="run-parse-after")
def parse_after(project_dir: str) -> None:
    subprocess.run(["jj", "parse"], cwd=project_dir, check=True)

@flow(name="parametric-study")
def parametric_study(project_dir: str, scripts: list[str]):
    """パラメトリックスタディ: 複数スクリプトを順次実行し、結果をパース"""
    for script in scripts:
        exit_code = run_simulation(script, project_dir)
        if exit_code != 0:
            print(f"Warning: {script} exited with code {exit_code}")
    parse_after(project_dir)

parametric_study("/path/to/project", [
    "run_case01.py",
    "run_case02.py",
    "run_case03.py",
])
```

## 応用パターン

### 4. パラメータスイープ（Prefect Map）

```python
from prefect import flow, task
import subprocess

@task(name="generate-inp")
def generate_inp(template: str, params: dict, output_dir: str) -> str:
    """テンプレートからINPファイルを生成"""
    import jj
    from pathlib import Path

    # テンプレートINPを読み込み、パラメータを置換
    template_path = Path(output_dir) / template
    content = template_path.read_text()
    for key, value in params.items():
        content = content.replace(f"<{key}>", str(value))

    out_name = f"go_case_{params.get('case_id', 'x')}.inp"
    out_path = Path(output_dir) / out_name
    out_path.write_text(content)
    return str(out_path)

@task(name="run-abaqus")
def run_abaqus(inp_path: str, project_dir: str) -> int:
    result = subprocess.run(
        ["jj", "r", "abaqus", "job=" + inp_path.split("/")[-1].replace(".inp", "")],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    return result.returncode

@flow(name="parameter-sweep")
def parameter_sweep(project_dir: str, param_sets: list[dict]):
    """パラメータスイープ"""
    for params in param_sets:
        inp_path = generate_inp("template.inp", params, project_dir)
        run_abaqus(inp_path, project_dir)

    # 全ケース完了後にparse
    subprocess.run(["jj", "parse"], cwd=project_dir, check=True)

parameter_sweep("/path/to/project", [
    {"case_id": 1, "load": 100, "thickness": 2.0},
    {"case_id": 2, "load": 200, "thickness": 2.0},
    {"case_id": 3, "load": 100, "thickness": 3.0},
])
```

### 5. 結果収集と通知

```python
from prefect import flow, task
import jj

@task(name="collect-results")
def collect_results(project_root: str) -> dict:
    """全ケースの結果を収集"""
    nodes = jj.get_nodes(project_root=project_root, name_filter="go_")
    results = {}
    for node in nodes:
        props = jj.get_properties(node.name, project_root)
        results[node.name] = {
            "status": props.get("analysis_status", "unknown"),
            "max_stress": props.get("max_stress"),
            "max_displacement": props.get("max_displacement"),
        }
    return results

@task(name="generate-report")
def generate_report(results: dict, output_path: str) -> str:
    """結果レポートを生成"""
    import json
    from pathlib import Path

    Path(output_path).write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path

@flow(name="result-collection")
def result_collection(project_root: str):
    results = collect_results(project_root)
    report = generate_report(results, f"{project_root}/report.json")
    print(f"Report: {report}")
    print(f"Total cases: {len(results)}")
    failed = [k for k, v in results.items() if v["status"] != "completed"]
    if failed:
        print(f"Failed cases: {failed}")
```

## Prefect UIでの監視

```bash
# Prefect サーバーを起動
prefect server start

# フローをデプロイ
prefect deploy --name "parametric-study" --pool default-agent-pool
```

Prefect UIでフローの実行状況、タスクの成功/失敗、実行時間をリアルタイムに監視できます。

## jjとの連携ポイント

| jj機能 | Prefect連携での用途 |
|--------|-------------------|
| `jj parse` | フロー開始時・終了時のグラフ更新 |
| `jj r` | シミュレーション/スクリプト実行（ログ記録付き） |
| `jj export csv` | 結果データのCSVエクスポート |
| `jj diff` | ケース間差分の自動検出 |
| `jj show` | ノード情報の確認 |
| `import jj` API | タスク内でのプログラマティックなデータアクセス |
| `jj dashboard` | 結果の可視化（Prefectフロー完了後に起動） |

## 今後の拡張予定（T5: リモートジョブ実行基盤）

v0.3.0のT5ワークトラックでは、jjとPrefectのより深い統合を計画しています：

- `jj submit` → Prefect flowとしてジョブをサブミット
- `jj watch` → Prefect UIへのリンクを提供
- `jj collect` → リモート実行結果の自動収集
- Prefect Blocks を使ったHPC接続設定管理
- Prefect Artifacts でjjグラフの可視化結果を保存
