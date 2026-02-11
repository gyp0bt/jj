from __future__ import annotations

import hashlib
import json
import logging
import pickle
from pathlib import Path
from typing import Any, Optional

import yaml

from jj_types import GraphModel

logger = logging.getLogger(__name__)


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

    # =========================================================
    # タイムスタンプキャッシュの永続化
    # =========================================================

    _TIMESTAMP_FILENAME = "parse_timestamps.json"

    def load_timestamps(self, project_root: Path) -> dict[str, float]:
        """前回パース時のファイルタイムスタンプを読み込む

        Returns:
            {相対パス: mtime} のマッピング。ファイルが存在しない場合は空辞書。
        """
        storage_dir = self._storage_dir(project_root)
        path = storage_dir / self._TIMESTAMP_FILENAME
        if not path.exists():
            return {}
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return {k: float(v) for k, v in data.items()}
        except (json.JSONDecodeError, OSError, ValueError):
            pass
        return {}

    def save_timestamps(
        self, project_root: Path, timestamps: dict[str, float]
    ) -> Path:
        """パース時のファイルタイムスタンプを保存する

        Args:
            project_root: プロジェクトルート
            timestamps: {相対パス: mtime} のマッピング

        Returns:
            保存先パス
        """
        storage_dir = self._storage_dir(project_root)
        path = storage_dir / self._TIMESTAMP_FILENAME
        with path.open("w", encoding="utf-8") as f:
            json.dump(timestamps, f, ensure_ascii=False, indent=2)
        return path

    # =========================================================
    # ABQData永続化キャッシュ（pickle）
    # =========================================================

    _ABQ_CACHE_DIRNAME = "abq_cache"

    def _abq_cache_dir(self, project_root: Path) -> Path:
        """ABQDataキャッシュ用ディレクトリを取得"""
        cache_dir = self._storage_dir(project_root) / self._ABQ_CACHE_DIRNAME
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @staticmethod
    def _abq_cache_key(file_path: str) -> str:
        """ファイルパスからキャッシュキー（ファイル名）を生成

        パスのハッシュを使用してファイル名の衝突を回避する。
        """
        digest = hashlib.sha256(file_path.encode("utf-8")).hexdigest()[:16]
        return f"{digest}.pickle"

    def load_abq_data(
        self, project_root: Path, file_path: str, expected_mtime: float
    ) -> Any:
        """永続化されたABQDataキャッシュを読み込む

        キャッシュファイルが存在し、かつmtimeが一致する場合のみロードする。
        mtime不一致（ファイル変更）時はNoneを返す。

        Args:
            project_root: プロジェクトルート
            file_path: 元のINPファイルパス
            expected_mtime: 期待するファイルのmtime

        Returns:
            キャッシュされたABQData。キャッシュなしまたは無効の場合はNone。
        """
        cache_dir = self._abq_cache_dir(project_root)
        cache_key = self._abq_cache_key(file_path)
        cache_path = cache_dir / cache_key

        if not cache_path.exists():
            return None

        try:
            with cache_path.open("rb") as f:
                cached = pickle.load(f)
            if not isinstance(cached, dict):
                return None
            if cached.get("mtime") != expected_mtime:
                logger.debug(
                    f"ABQData cache mtime mismatch for {file_path}: "
                    f"cached={cached.get('mtime')}, expected={expected_mtime}"
                )
                return None
            if cached.get("source_path") != file_path:
                return None
            return cached.get("abq_data")
        except (pickle.UnpicklingError, OSError, EOFError, KeyError) as e:
            logger.debug(f"ABQData cache load failed for {file_path}: {e}")
            return None

    def save_abq_data(
        self, project_root: Path, file_path: str, abq_data: Any, mtime: float
    ) -> Path:
        """ABQDataをpickleでディスクに永続化

        Args:
            project_root: プロジェクトルート
            file_path: 元のINPファイルパス
            abq_data: 保存するABQData
            mtime: INPファイルのmtime（検証用）

        Returns:
            保存先パス
        """
        cache_dir = self._abq_cache_dir(project_root)
        cache_key = self._abq_cache_key(file_path)
        cache_path = cache_dir / cache_key

        cached = {
            "source_path": file_path,
            "mtime": mtime,
            "abq_data": abq_data,
        }
        try:
            with cache_path.open("wb") as f:
                pickle.dump(cached, f, protocol=pickle.HIGHEST_PROTOCOL)
        except (OSError, pickle.PicklingError) as e:
            logger.warning(f"ABQData cache save failed for {file_path}: {e}")
        return cache_path

    def clear_abq_cache(self, project_root: Path) -> int:
        """ABQDataキャッシュを全て削除

        Returns:
            削除したファイル数
        """
        cache_dir = self._abq_cache_dir(project_root)
        count = 0
        for f in cache_dir.glob("*.pickle"):
            try:
                f.unlink()
                count += 1
            except OSError:
                pass
        return count

    def cleanup_abq_cache(
        self,
        project_root: Path,
        *,
        max_age_days: int = 30,
        max_count: int = 100,
    ) -> int:
        """古いABQDataキャッシュを自動クリーンアップ

        以下のポリシーで不要なキャッシュを削除する:
        1. max_age_days日以上前のキャッシュを削除
        2. 残ったキャッシュがmax_countを超える場合、古い順に削除

        Args:
            project_root: プロジェクトルート
            max_age_days: キャッシュ保持期間（日数、デフォルト30日）
            max_count: キャッシュファイルの最大保持数（デフォルト100）

        Returns:
            削除したファイル数
        """
        import time

        cache_dir = self._abq_cache_dir(project_root)
        cache_files = list(cache_dir.glob("*.pickle"))

        if not cache_files:
            return 0

        now = time.time()
        max_age_seconds = max_age_days * 86400  # 1日 = 86400秒
        deleted = 0

        # 1. 古いキャッシュを削除
        remaining: list[tuple[Path, float]] = []
        for f in cache_files:
            try:
                mtime = f.stat().st_mtime
                if (now - mtime) > max_age_seconds:
                    f.unlink()
                    deleted += 1
                    logger.debug(f"ABQData cache expired: {f.name}")
                else:
                    remaining.append((f, mtime))
            except OSError:
                pass

        # 2. 残数制限: 古い順にソートして超過分を削除
        if len(remaining) > max_count:
            remaining.sort(key=lambda x: x[1])  # mtimeの古い順
            excess = remaining[: len(remaining) - max_count]
            for f, _ in excess:
                try:
                    f.unlink()
                    deleted += 1
                    logger.debug(f"ABQData cache evicted (over max_count): {f.name}")
                except OSError:
                    pass

        if deleted > 0:
            logger.info(f"ABQData cache cleanup: {deleted} files removed")

        return deleted
