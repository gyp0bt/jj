from __future__ import annotations

import hashlib
import json
import logging
import pickle
from pathlib import Path
from typing import Any

import yaml

from jj_types import GraphModel

logger = logging.getLogger(__name__)


_EXT_KEYS_FIELD = "_ext_keys"


def _is_heavy_value(value: Any) -> bool:
    """プロパティ値が外部化対象（list/dict）かどうかを判定"""
    return isinstance(value, (list, dict)) and len(value) > 0


class GraphStorage:
    _PROPERTIES_DIRNAME = "properties"

    def __init__(
        self,
        storage_dirname: str = ".j2/storage",
        default_filename: str = "graph.yaml",
    ) -> None:
        self.storage_dirname = storage_dirname
        self.default_filename = default_filename

    def _storage_dir(self, project_root: Path) -> Path:
        storage_dir = project_root / self.storage_dirname
        storage_dir.mkdir(parents=True, exist_ok=True)
        return storage_dir

    def _detect_existing_path(self, storage_dir: Path) -> Path | None:
        candidates = [
            storage_dir / "graph.yaml",
            storage_dir / "graph.yml",
            storage_dir / "graph.json",
        ]
        for path in candidates:
            if path.exists():
                return path
        return None

    def _resolve_path(self, project_root: Path, filename: str | None = None) -> Path:
        storage_dir = self._storage_dir(project_root)
        if filename:
            return storage_dir / filename
        existing = self._detect_existing_path(storage_dir)
        if existing is not None:
            return existing
        return storage_dir / self.default_filename

    def _properties_dir(self, project_root: Path) -> Path:
        props_dir = self._storage_dir(project_root) / self._PROPERTIES_DIRNAME
        props_dir.mkdir(parents=True, exist_ok=True)
        return props_dir

    def _node_properties_path(self, project_root: Path, node_id: int) -> Path:
        return self._properties_dir(project_root) / f"node_{node_id}.json"

    def load(
        self,
        project_root: Path,
        filename: str | None = None,
        *,
        resolve_externalized: bool = False,
    ) -> GraphModel:
        """グラフデータを読み込む

        Args:
            project_root: プロジェクトルートパス
            filename: ファイル名（Noneでデフォルト検出）
            resolve_externalized: Trueの場合、外部化プロパティを結合してフルロード

        Returns:
            読み込んだGraphModel
        """
        path = self._resolve_path(project_root, filename)
        if not path.exists():
            return GraphModel.empty()

        data = self._read_file(path)
        if data is None:
            return GraphModel.empty()

        if resolve_externalized:
            self._resolve_all_externalized(project_root, data)

        if hasattr(GraphModel, "model_validate"):
            return GraphModel.model_validate(data)
        return GraphModel(**data)

    def _resolve_all_externalized(self, project_root: Path, data: dict[str, Any]) -> None:
        """グラフデータ内の全ノードの外部化プロパティを結合（in-place）"""
        nodes = data.get("nodes", [])
        for node_data in nodes:
            props = node_data.get("properties", {})
            ext_keys = props.get(_EXT_KEYS_FIELD)
            if not ext_keys:
                continue
            node_id = node_data.get("id")
            if node_id is None:
                continue
            ext_props = self.load_node_properties(project_root, node_id)
            props.update(ext_props)
            props.pop(_EXT_KEYS_FIELD, None)

    def save(
        self,
        project_root: Path,
        graph: GraphModel,
        filename: str | None = None,
    ) -> Path:
        path = self._resolve_path(project_root, filename)
        data = self._dump_graph(graph)
        self._externalize_heavy_properties(project_root, data)
        self._write_file(path, data)
        return path

    def _externalize_heavy_properties(self, project_root: Path, data: dict[str, Any]) -> None:
        """重いプロパティをノードごとに外部JSONファイルへ分離（in-place）

        list/dictのプロパティを外部ファイルに書き出し、
        graph.yamlには _ext_keys マーカーのみを残す。
        """
        nodes = data.get("nodes", [])
        # 現在のノードIDセットを記録（孤立ファイルの掃除用）
        current_node_ids: set[int] = set()
        for node_data in nodes:
            node_id = node_data.get("id")
            if node_id is None:
                continue
            current_node_ids.add(node_id)
            props = node_data.get("properties", {})
            heavy_keys: list[str] = []
            heavy_props: dict[str, Any] = {}
            for key, value in list(props.items()):
                if key == _EXT_KEYS_FIELD:
                    continue
                if _is_heavy_value(value):
                    heavy_keys.append(key)
                    heavy_props[key] = value
            if heavy_keys:
                self.save_node_properties(project_root, node_id, heavy_props)
                for key in heavy_keys:
                    del props[key]
                props[_EXT_KEYS_FIELD] = sorted(heavy_keys)
            else:
                props.pop(_EXT_KEYS_FIELD, None)
                # 外部ファイルが残っていたら削除
                ext_path = self._node_properties_path(project_root, node_id)
                if ext_path.exists():
                    ext_path.unlink(missing_ok=True)

        # グラフから消えたノードの外部ファイルを掃除
        self._cleanup_orphan_properties(project_root, current_node_ids)

    def _dump_graph(self, graph: GraphModel) -> dict[str, Any]:
        if hasattr(graph, "model_dump"):
            return graph.model_dump(mode="json")
        return graph.dict()  # type: ignore[no-any-return]

    def _read_file(self, path: Path) -> dict[str, Any] | None:
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
    # ノードプロパティの外部化（オンデマンドロード）
    # =========================================================

    def load_node_properties(self, project_root: Path, node_id: int) -> dict[str, Any]:
        """特定ノードの外部化プロパティをオンデマンドでロードする

        Args:
            project_root: プロジェクトルート
            node_id: ノードID

        Returns:
            外部化プロパティのdict。ファイルが存在しない場合は空dict。
        """
        path = self._node_properties_path(project_root, node_id)
        if not path.exists():
            return {}
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError) as e:
            logger.debug(f"外部プロパティの読み込み失敗 (node_id={node_id}): {e}")
        return {}

    def save_node_properties(self, project_root: Path, node_id: int, properties: dict[str, Any]) -> Path:
        """特定ノードの外部化プロパティをJSONファイルに保存する

        Args:
            project_root: プロジェクトルート
            node_id: ノードID
            properties: 外部化するプロパティのdict

        Returns:
            保存先パス
        """
        path = self._node_properties_path(project_root, node_id)
        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(properties, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.warning(f"外部プロパティの保存失敗 (node_id={node_id}): {e}")
        return path

    def _cleanup_orphan_properties(self, project_root: Path, current_node_ids: set[int]) -> int:
        """グラフから消えたノードの外部プロパティファイルを削除する

        Returns:
            削除したファイル数
        """
        props_dir = self._storage_dir(project_root) / self._PROPERTIES_DIRNAME
        if not props_dir.exists():
            return 0
        deleted = 0
        for f in props_dir.glob("node_*.json"):
            try:
                node_id_str = f.stem.replace("node_", "")
                node_id = int(node_id_str)
                if node_id not in current_node_ids:
                    f.unlink()
                    deleted += 1
            except (ValueError, OSError):
                pass
        if deleted > 0:
            logger.info(f"孤立プロパティファイルを削除: {deleted}件")
        return deleted

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

    def save_timestamps(self, project_root: Path, timestamps: dict[str, float]) -> Path:
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
    # プラグインデータ永続化キャッシュ（pickle）
    # namespace単位でキャッシュを分離する汎用メカニズム
    # =========================================================

    _PLUGIN_CACHE_DIRNAME = "plugin_cache"

    def _plugin_cache_dir(self, project_root: Path, namespace: str) -> Path:
        """プラグインキャッシュ用ディレクトリを取得（namespace単位で分離）"""
        cache_dir = self._storage_dir(project_root) / self._PLUGIN_CACHE_DIRNAME / namespace
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @staticmethod
    def _plugin_cache_key(file_path: str) -> str:
        """ファイルパスからキャッシュキー（ファイル名）を生成

        パスのハッシュを使用してファイル名の衝突を回避する。
        """
        digest = hashlib.sha256(file_path.encode("utf-8")).hexdigest()[:16]
        return f"{digest}.pickle"

    def load_plugin_data(self, project_root: Path, namespace: str, file_path: str, expected_mtime: float) -> Any:
        """プラグインキャッシュデータを読み込む

        キャッシュファイルが存在し、かつmtimeが一致する場合のみロードする。
        mtime不一致（ファイル変更）時はNoneを返す。

        Args:
            project_root: プロジェクトルート
            namespace: プラグイン名前空間（例: "abaqus"）
            file_path: 元のファイルパス
            expected_mtime: 期待するファイルのmtime

        Returns:
            キャッシュされたデータ。キャッシュなしまたは無効の場合はNone。
        """
        cache_dir = self._plugin_cache_dir(project_root, namespace)
        cache_key = self._plugin_cache_key(file_path)
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
                    f"Plugin cache mtime mismatch ({namespace}) for {file_path}: "
                    f"cached={cached.get('mtime')}, expected={expected_mtime}"
                )
                return None
            if cached.get("source_path") != file_path:
                return None
            return cached.get("data")
        except (pickle.UnpicklingError, OSError, EOFError, KeyError) as e:
            logger.debug(f"Plugin cache load failed ({namespace}) for {file_path}: {e}")
            return None

    def save_plugin_data(self, project_root: Path, namespace: str, file_path: str, data: Any, mtime: float) -> Path:
        """プラグインキャッシュデータをpickleでディスクに永続化

        Args:
            project_root: プロジェクトルート
            namespace: プラグイン名前空間（例: "abaqus"）
            file_path: 元のファイルパス
            data: 保存するデータ
            mtime: ファイルのmtime（検証用）

        Returns:
            保存先パス
        """
        cache_dir = self._plugin_cache_dir(project_root, namespace)
        cache_key = self._plugin_cache_key(file_path)
        cache_path = cache_dir / cache_key

        cached = {
            "source_path": file_path,
            "mtime": mtime,
            "data": data,
        }
        try:
            with cache_path.open("wb") as f:
                pickle.dump(cached, f, protocol=pickle.HIGHEST_PROTOCOL)
        except (OSError, pickle.PicklingError) as e:
            logger.warning(f"Plugin cache save failed ({namespace}) for {file_path}: {e}")
        return cache_path

    def clear_plugin_cache(self, project_root: Path, namespace: str | None = None) -> int:
        """プラグインキャッシュを削除

        Args:
            namespace: 指定時はそのnamespaceのみ。Noneで全namespace。

        Returns:
            削除したファイル数
        """
        storage_dir = self._storage_dir(project_root)
        plugin_cache_root = storage_dir / self._PLUGIN_CACHE_DIRNAME
        if not plugin_cache_root.exists():
            return 0

        count = 0
        if namespace:
            ns_dir = plugin_cache_root / namespace
            if ns_dir.exists():
                for f in ns_dir.glob("*.pickle"):
                    try:
                        f.unlink()
                        count += 1
                    except OSError:
                        pass
        else:
            for ns_dir in plugin_cache_root.iterdir():
                if ns_dir.is_dir():
                    for f in ns_dir.glob("*.pickle"):
                        try:
                            f.unlink()
                            count += 1
                        except OSError:
                            pass
        return count

    def cleanup_plugin_cache(
        self,
        project_root: Path,
        namespace: str | None = None,
        *,
        max_age_days: int = 30,
        max_count: int = 100,
    ) -> int:
        """古いプラグインキャッシュを自動クリーンアップ

        以下のポリシーで不要なキャッシュを削除する:
        1. max_age_days日以上前のキャッシュを削除
        2. 残ったキャッシュがmax_countを超える場合、古い順に削除

        Args:
            project_root: プロジェクトルート
            namespace: 指定時はそのnamespaceのみ。Noneで全namespace。
            max_age_days: キャッシュ保持期間（日数、デフォルト30日）
            max_count: キャッシュファイルの最大保持数（デフォルト100）

        Returns:
            削除したファイル数
        """
        import time

        storage_dir = self._storage_dir(project_root)
        plugin_cache_root = storage_dir / self._PLUGIN_CACHE_DIRNAME
        if not plugin_cache_root.exists():
            return 0

        # 対象ディレクトリを収集
        if namespace:
            ns_dirs = [plugin_cache_root / namespace]
        else:
            ns_dirs = [d for d in plugin_cache_root.iterdir() if d.is_dir()]

        cache_files: list[Path] = []
        for ns_dir in ns_dirs:
            if ns_dir.exists():
                cache_files.extend(ns_dir.glob("*.pickle"))

        if not cache_files:
            return 0

        now = time.time()
        max_age_seconds = max_age_days * 86400
        deleted = 0

        remaining: list[tuple[Path, float]] = []
        for f in cache_files:
            try:
                mtime = f.stat().st_mtime
                if (now - mtime) > max_age_seconds:
                    f.unlink()
                    deleted += 1
                    logger.debug(f"Plugin cache expired: {f.name}")
                else:
                    remaining.append((f, mtime))
            except OSError:
                pass

        if len(remaining) > max_count:
            remaining.sort(key=lambda x: x[1])
            excess = remaining[: len(remaining) - max_count]
            for f, _ in excess:
                try:
                    f.unlink()
                    deleted += 1
                    logger.debug(f"Plugin cache evicted (over max_count): {f.name}")
                except OSError:
                    pass

        if deleted > 0:
            logger.info(f"Plugin cache cleanup: {deleted} files removed")

        return deleted
