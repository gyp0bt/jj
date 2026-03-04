from __future__ import annotations

import contextlib
import getpass
import json
import re
import socket
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import GraphConfig
from jj_types import GraphModel, Node, NodeCategory
from services.graph.project_graph import ProjectGraph
from services.graph.storage import GraphStorage

__all__ = [
    "GraphModel",
]


@dataclass
class RunResult:
    command: list[str]
    cwd: Path
    mode: str
    stdout: str
    stderr: str
    exit_code: int
    started_at: str
    finished_at: str
    duration_seconds: float
    host: str
    user: str
    trace_files: list[str]
    properties: dict[str, str]
    log_path: Path | None = None
    script_path: Path | None = None


class RunService:
    def __init__(self, storage_dirname: str = ".j2/storage/run") -> None:
        self.storage_dirname = storage_dirname

    def execute(
        self,
        command: list[str],
        cwd: Path | None = None,
        mode: str | None = None,
        record: bool = True,
        no_parse: bool = False,
    ) -> RunResult:
        if not command:
            raise ValueError("実行コマンドが空です。")

        resolved_cwd = cwd or Path.cwd()
        resolved_cwd = resolved_cwd.resolve()

        resolved_mode = mode or self._detect_mode(command, resolved_cwd)
        script_path = self._detect_script_path(command, resolved_cwd)
        properties = (
            self._extract_properties(script_path, self._extract_script_args(command, script_path))
            if script_path
            else {}
        )

        started_dt = datetime.now(timezone.utc)
        started_at = started_dt.isoformat()
        before_snapshot = self._snapshot_files(resolved_cwd) if resolved_mode == "script" else {}

        result = subprocess.run(
            command,
            cwd=str(resolved_cwd),
            capture_output=True,
            text=True,
            check=False,
        )

        after_snapshot = self._snapshot_files(resolved_cwd) if resolved_mode == "script" else {}
        trace_files = (
            self._diff_snapshot(before_snapshot, after_snapshot, resolved_cwd) if resolved_mode == "script" else []
        )
        finished_dt = datetime.now(timezone.utc)
        finished_at = finished_dt.isoformat()
        duration_seconds = (finished_dt - started_dt).total_seconds()

        run_result = RunResult(
            command=command,
            cwd=resolved_cwd,
            mode=resolved_mode,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
            exit_code=result.returncode,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=duration_seconds,
            host=socket.gethostname(),
            user=getpass.getuser(),
            trace_files=trace_files,
            properties=properties,
            script_path=script_path,
        )

        if record:
            run_result.log_path = self._write_log(resolved_cwd, run_result)
            if resolved_mode == "script":
                self._update_graph_storage(resolved_cwd, run_result, no_parse=no_parse)

        return run_result

    def _detect_mode(self, command: list[str], cwd: Path) -> str:
        script_path = self._detect_script_path(command, cwd)
        return "script" if script_path else "job"

    def _detect_script_path(self, command: list[str], cwd: Path) -> Path | None:
        if not command:
            return None
        head = command[0]
        if head.endswith((".py", ".sh", ".bash")):
            candidate = self._resolve_script_path(Path(head), cwd)
            return candidate if candidate.exists() else None
        if head in {"python", "python3"} and len(command) > 1:
            if command[1].startswith("-"):
                return None
            candidate = self._resolve_script_path(Path(command[1]), cwd)
            return candidate if candidate.exists() else None
        return None

    def _resolve_script_path(self, path: Path, cwd: Path) -> Path:
        if path.is_absolute():
            return path
        return (cwd / path).resolve()

    def _snapshot_files(self, root: Path) -> dict[str, tuple[float, int]]:
        snapshot: dict[str, tuple[float, int]] = {}
        for path in self._iter_files(root):
            try:
                stat = path.stat()
                snapshot[str(path)] = (stat.st_mtime, stat.st_size)
            except OSError:
                continue
        return snapshot

    def _iter_files(self, root: Path) -> Iterable[Path]:
        ignore_names = {".j2", ".git", ".venv", "__pycache__", ".pytest_cache"}
        for path in root.rglob("*"):
            if any(part in ignore_names for part in path.parts):
                continue
            if path.is_file():
                yield path

    def _diff_snapshot(
        self,
        before: dict[str, tuple[float, int]],
        after: dict[str, tuple[float, int]],
        root: Path,
    ) -> list[str]:
        changed: list[str] = []
        for path, data in after.items():
            if path not in before or before[path] != data:
                try:
                    rel = Path(path).resolve().relative_to(root).as_posix()
                except ValueError:
                    rel = Path(path).as_posix()
                changed.append(rel)
        return sorted(set(changed))

    def _extract_properties(self, script_path: Path, args: list[str]) -> dict[str, str]:
        props: dict[str, str] = {}
        if not script_path.exists():
            return props

        text = script_path.read_text(encoding="utf-8", errors="ignore")
        props.update(self._extract_props_block(text))
        props.update(self._extract_arg_mappings(text, args, props))
        return props

    def _extract_script_args(self, command: list[str], script_path: Path) -> list[str]:
        if not command:
            return []
        if (
            command[0] in {"python", "python3"}
            and len(command) > 1
            and Path(command[1]).resolve() == script_path.resolve()
        ):
            return command[2:]
        return command[1:]

    def _extract_props_block(self, text: str) -> dict[str, str]:
        props: dict[str, str] = {}
        in_block = False
        for line in text.splitlines():
            normalized = line.strip().lower()
            if "props start" in normalized:
                in_block = True
                continue
            if "props end" in normalized:
                in_block = False
                continue
            if not in_block:
                continue
            m = re.match(r"^\s*([A-Za-z_][\w\-]*)\s*=\s*(.+?)\s*$", line)
            if not m:
                continue
            key, value = m.groups()
            value = value.strip().strip('"').strip("'")
            props[key] = value
        return props

    def _extract_arg_mappings(self, text: str, args: list[str], props: dict[str, str]) -> dict[str, str]:
        mapped: dict[str, str] = {}
        py_matches = re.findall(r"^\s*([A-Za-z_]\w*)\s*=\s*sys\.argv\[(\d+)\]", text, re.MULTILINE)
        sh_matches = re.findall(r"^\s*([A-Za-z_]\w*)\s*=\s*\"?\$([0-9]+)\"?", text, re.MULTILINE)
        for name, idx_str in py_matches + sh_matches:
            idx = int(idx_str) - 1
            if 0 <= idx < len(args) and name not in props:
                mapped[name] = args[idx]
        return mapped

    def _write_log(self, project_root: Path, result: RunResult) -> Path:
        log_dir = project_root / self.storage_dirname
        log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        log_path = log_dir / f"run-{stamp}.json"
        payload = {
            "command": result.command,
            "cwd": str(result.cwd),
            "mode": result.mode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
            "duration_seconds": result.duration_seconds,
            "host": result.host,
            "user": result.user,
            "trace_files": result.trace_files,
            "properties": result.properties,
            "script_path": str(result.script_path) if result.script_path else None,
        }
        with log_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return log_path

    def _detect_run_type(self, result: RunResult) -> str:
        """実行結果からrun_typeを推定する

        スクリプトの内容やコマンドからCAEジョブ/MLトレーニング/スクリプトを判定。
        """
        if result.script_path and result.script_path.exists():
            text = result.script_path.read_text(encoding="utf-8", errors="ignore").lower()
            # MLトレーニングパターンの検出
            ml_indicators = ["torch", "tensorflow", "sklearn", "model.fit", "model.train", "optuna"]
            if any(ind in text for ind in ml_indicators):
                return "ml_training"
        # CAEジョブパターンの検出（コマンド名ベース）
        if result.command:
            cmd = result.command[0].lower()
            cae_commands = ["abaqus", "abq", "ccx", "fluent", "lsdyna", "openfoam"]
            if any(c in cmd for c in cae_commands):
                return "cae_job"
        return "script"

    def _update_graph_storage(self, project_root: Path, result: RunResult, *, no_parse: bool = False) -> None:
        """parse実行後のグラフにRun Nodeを記録する

        parse-run統合: まずparse_and_save()でプロジェクトを再スキャンし、
        run実行で生成・変更されたファイルをパーサーパイプラインが検出する。
        その最新グラフ上にruntimeのRun Nodeを追加する。

        これにより:
        - trace_filesのノードはparseが正確に生成（手動作成不要）
        - RunDiscoverer（CaeRunDiscoverer等）がlatent runも同時に発見
        - parse結果とrun結果が同一グラフで統合される

        Args:
            project_root: プロジェクトルート
            result: コマンド実行結果
            no_parse: Trueの場合、parseをスキップして既存グラフをロード
        """
        if no_parse:
            # parseスキップ: 既存グラフをロードして従来通りRun Nodeのみ追加
            storage = GraphStorage()
            graph_model = storage.load(project_root)
            config = GraphConfig.load(project_root)
        else:
            from services.graph import GraphService

            graph_service = GraphService(project_root=project_root)
            # parse_and_saveでプロジェクトを再スキャン
            # → run実行で生成されたファイルがNodeとして検出される
            graph_model, _ = graph_service.parse_and_save()
            config = graph_service.config

        project_graph = ProjectGraph(
            nodes=list(graph_model.nodes),
            relations=list(graph_model.relations),
            project_root=project_root,
            config=config,
        )

        script_name = result.script_path.name if result.script_path else " ".join(result.command)
        run_type = self._detect_run_type(result)

        # parseが生成したノードからスクリプトをmediaとして特定
        media_node_ids: list[int] = []
        if result.script_path:
            rel_path = result.script_path.name
            with contextlib.suppress(ValueError):
                rel_path = str(result.script_path.relative_to(project_root))
            for node in project_graph.nodes:
                path_prop = node.properties.get("path", "")
                if path_prop == rel_path or node.name == result.script_path.stem:
                    media_node_ids.append(node.id)
                    break

        # parseが生成したノードからtrace_filesのoutputノードIDを収集
        output_node_ids: list[int] = []
        for trace_file in result.trace_files:
            file_node = next(
                (n for n in project_graph.nodes if n.properties.get("path") == trace_file),
                None,
            )
            if file_node is None:
                file_node = next(
                    (n for n in project_graph.nodes if n.name == trace_file),
                    None,
                )
            if file_node is None:
                # parseで検出されなかったファイル（.j2内等）は手動作成
                file_node = Node(
                    id=project_graph.next_node_id(),
                    type="file",
                    name=trace_file,
                    format=Path(trace_file).suffix.lstrip(".") if "." in trace_file else "",
                    properties={"path": trace_file},
                    category=NodeCategory.FILE,
                )
                project_graph.add_node(file_node)
            output_node_ids.append(file_node.id)

        # Run Nodeを生成（add_run_nodeがcategory=RUN、run_input/output/mediaリレーションを構築）
        run_props: dict[str, Any] = {
            "exit_code": str(result.exit_code),
            "started_at": result.started_at,
            "finished_at": result.finished_at,
            "duration_seconds": str(result.duration_seconds),
            "host": result.host,
            "user": result.user,
            "command": " ".join(result.command),
        }
        run_props.update(result.properties)

        project_graph.add_run_node(
            name=script_name,
            run_type=run_type,
            output_node_ids=output_node_ids,
            media_node_ids=media_node_ids,
            properties=run_props,
            discovery="runtime",
        )

        # Run Node追加後のグラフを保存
        graph_model = project_graph.to_graph_model()
        storage = GraphStorage()
        storage.save(project_root, graph_model)
