from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import yaml

from types import GraphModel


class GraphStorage:
    def __init__(
        self,
        storage_dirname: str = ".jj/storage",
        default_filename: str = "graph.yaml",
    ) -> None:
        self.storage_dirname = storage_dirname
        self.default_filename = default_filename

    def _storage_dir(self, project_root: Path) -> Path:
        storage_dir = project_root / self.storage_dirname
        storage_dir.mkdir(parents=True, exist_ok=True)
        return storage_dir

    def _detect_existing_path(self, storage_dir: Path) -> Optional[Path]:
        candidates = [
            storage_dir / "graph.yaml",
            storage_dir / "graph.yml",
            storage_dir / "graph.json",
        ]
        for path in candidates:
            if path.exists():
                return path
        return None

    def _resolve_path(
        self, project_root: Path, filename: Optional[str] = None
    ) -> Path:
        storage_dir = self._storage_dir(project_root)
        if filename:
            return storage_dir / filename
        existing = self._detect_existing_path(storage_dir)
        if existing is not None:
            return existing
        return storage_dir / self.default_filename

    def load(self, project_root: Path, filename: Optional[str] = None) -> GraphModel:
        path = self._resolve_path(project_root, filename)
        if not path.exists():
            return GraphModel.empty()

        data = self._read_file(path)
        if data is None:
            return GraphModel.empty()

        if hasattr(GraphModel, "model_validate"):
            return GraphModel.model_validate(data)
        return GraphModel(**data)

    def save(
        self,
        project_root: Path,
        graph: GraphModel,
        filename: Optional[str] = None,
    ) -> Path:
        path = self._resolve_path(project_root, filename)
        data = self._dump_graph(graph)
        self._write_file(path, data)
        return path

    def _dump_graph(self, graph: GraphModel) -> dict[str, Any]:
        if hasattr(graph, "model_dump"):
            return graph.model_dump()
        return graph.dict()  # type: ignore[no-any-return]

    def _read_file(self, path: Path) -> Optional[dict[str, Any]]:
        if path.suffix.lower() in {".yaml", ".yml"}:
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        elif path.suffix.lower() == ".json":
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            raise ValueError("対応していない拡張子です。")

        if data is None:
            return None
        if not isinstance(data, dict):
            raise ValueError("グラフデータはdict形式である必要があります。")
        return data

    def _write_file(self, path: Path, data: dict[str, Any]) -> None:
        if path.suffix.lower() in {".yaml", ".yml"}:
            with path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
        elif path.suffix.lower() == ".json":
            with path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            raise ValueError("対応していない拡張子です。")
