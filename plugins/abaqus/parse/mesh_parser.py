"""Abaqusメッシュパーサー

pymeshを使ってメッシュ統計情報をノードのプロパティに付与する。

メッシュ統計キャッシュ:
パラメーターや境界条件のみが異なる.inpファイル間でメッシュ部分が同一の場合、
メッシュ定義部分（*NODE, *ELEMENT, *ELSET, *NSET）のコンテンツハッシュで
メッシュ統計をディスクキャッシュし、pymesh解析をスキップする。

[READMEへ戻る](../../../../../README.md)
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph

logger = logging.getLogger(__name__)

# メッシュ定義キーワード（ハッシュ対象）
_MESH_KEYWORDS = frozenset(
    {
        "*NODE",
        "*ELEMENT",
        "*ELSET",
        "*NSET",
    }
)

# メッシュ統計キャッシュの namespace
_MESH_STATS_CACHE_NS = "mesh_stats"

# ディスクキャッシュ用の固定mtime（ハッシュベースキャッシュではmtime検証不要）
_HASH_CACHE_SENTINEL_MTIME = 0.0


def _compute_mesh_content_hash(file_path: str) -> str | None:
    """メッシュ定義部分のコンテンツハッシュを計算

    .inpファイルの*NODE, *ELEMENT, *ELSET, *NSETセクションのみを
    ハッシュ化する。*PARAMETER, *BOUNDARY, *STEP等は除外。
    *INCLUDE参照はファイルパス+mtimeをハッシュに含める。

    Args:
        file_path: .inpファイルの絶対パス

    Returns:
        SHA256ハッシュ（先頭32文字）。メッシュ内容なし/読み取り不可時はNone。
    """
    hasher = hashlib.sha256()
    in_mesh_section = False
    has_mesh_content = False
    parent_dir = Path(file_path).parent

    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("**"):
                    continue

                if stripped.startswith("*"):
                    keyword = stripped.split(",")[0].strip().upper()
                    in_mesh_section = keyword in _MESH_KEYWORDS

                    # *INCLUDE: 参照先ファイルのパス+mtimeをハッシュに含める
                    if keyword == "*INCLUDE":
                        for token in stripped.split(","):
                            token_stripped = token.strip()
                            if token_stripped.upper().startswith("INPUT="):
                                include_path = token_stripped.split("=", 1)[1].strip()
                                resolved = parent_dir / include_path
                                try:
                                    mtime = resolved.stat().st_mtime
                                    hasher.update(f"INCLUDE:{include_path}:{mtime}".encode())
                                    has_mesh_content = True
                                except OSError:
                                    # includeファイルが見つからない場合はパスのみ
                                    hasher.update(f"INCLUDE:{include_path}:MISSING".encode())
                        continue

                if in_mesh_section:
                    hasher.update(line.encode())
                    has_mesh_content = True
    except OSError:
        return None

    if not has_mesh_content:
        return None

    return hasher.hexdigest()[:32]


def _load_mesh_stats_cache(graph: ProjectGraph, mesh_hash: str) -> dict[str, Any] | None:
    """ディスクからメッシュ統計キャッシュをロード

    Args:
        graph: ProjectGraph（project_root取得用）
        mesh_hash: メッシュコンテンツハッシュ

    Returns:
        キャッシュされたメッシュ統計辞書。キャッシュなし時はNone。
    """
    from services.graph.storage import GraphStorage

    storage = GraphStorage()
    return storage.load_plugin_data(
        graph.project_root,
        _MESH_STATS_CACHE_NS,
        mesh_hash,
        _HASH_CACHE_SENTINEL_MTIME,
    )


def _save_mesh_stats_cache(graph: ProjectGraph, mesh_hash: str, data: dict[str, Any]) -> None:
    """メッシュ統計をディスクキャッシュに保存

    Args:
        graph: ProjectGraph（project_root取得用）
        mesh_hash: メッシュコンテンツハッシュ
        data: メッシュ統計データ
    """
    from services.graph.storage import GraphStorage

    try:
        storage = GraphStorage()
        storage.save_plugin_data(
            graph.project_root,
            _MESH_STATS_CACHE_NS,
            mesh_hash,
            data,
            _HASH_CACHE_SENTINEL_MTIME,
        )
        logger.debug(f"Mesh stats cache saved: hash={mesh_hash[:12]}")
    except Exception as e:
        logger.debug(f"Mesh stats cache save failed: {e}")


def _parse_inp_worker(args: tuple[str, int]) -> tuple[str, object]:
    """ProcessPoolExecutor用のワーカー関数

    モジュールレベルに配置することでpickle可能にする。
    子プロセスで実行されるため、グローバル状態に依存しない。

    Args:
        args: (file_path, include_max_depth)のタプル

    Returns:
        (file_path, ABQData)のタプル
    """
    import services.parse.connectors.abaqus as abaqus_mod

    fp_str, include_depth = args
    abq = abaqus_mod.read_inp(fp_str, verbose=False, include_max_depth=include_depth)
    return fp_str, abq


class AbaqusMeshParser(AbstractFileParser):
    """pymeshを使ってメッシュ統計情報をノードのプロパティに付与

    pymeshによる.inp読み込みは重いため、--fullオプション時のみ実行する。

    mesh_qualityが付加されないケースの原因:
    - get_element_node_coord_array()がNone/空を返す（要素タイプ未対応）
    - 品質メトリクス計算がすべてのモードで失敗（2D要素等）
    - NaN率100%で有効な統計値が得られない
    デバッグログ（DEBUG level）で詳細を確認可能。
    """

    priority = 80
    requires_full = True

    @staticmethod
    def _get_or_parse_inp(graph: ProjectGraph, file_path: str) -> object:
        """read_inp()結果をキャッシュから取得、なければパースしてキャッシュに保存

        キャッシュ探索順序:
        1. インメモリキャッシュ（_parser_cache）
        2. ディスク永続化キャッシュ（.j2/storage/plugin_cache/abaqus/）
        3. キャッシュなし → read_inp()で新規パースし、両方に保存
        """
        import services.parse.connectors.abaqus as abaqus_mod
        from services.graph.storage import GraphStorage

        # 1. インメモリキャッシュ
        cached = graph.get_cached_plugin_data("abaqus", file_path)
        if cached is not None:
            return cached

        # 2. ディスク永続化キャッシュ
        try:
            mtime = Path(file_path).stat().st_mtime
            storage = GraphStorage()
            disk_cached = storage.load_plugin_data(graph.project_root, "abaqus", file_path, mtime)
            if disk_cached is not None:
                logger.debug(f"ABQData disk cache hit: {file_path}")
                graph.set_cached_plugin_data("abaqus", file_path, disk_cached)
                return disk_cached
        except OSError:
            mtime = 0.0

        # 3. 新規パース → キャッシュに保存
        # モジュール属性経由で呼び出し（テストのmonkeypatch対応）
        include_depth = graph.config.include_search_depth
        abq = abaqus_mod.read_inp(file_path, verbose=False, include_max_depth=include_depth)
        graph.set_cached_plugin_data("abaqus", file_path, abq)

        # ディスクにも永続化
        try:
            storage = GraphStorage()
            storage.save_plugin_data(graph.project_root, "abaqus", file_path, abq, mtime)
            logger.debug(f"ABQData saved to disk cache: {file_path}")
        except Exception as e:
            logger.debug(f"ABQData disk cache save skipped: {e}")

        return abq

    @staticmethod
    def _apply_mesh_stats_to_node(node: Any, cached_stats: dict[str, Any]) -> None:
        """キャッシュ済みメッシュ統計をノードプロパティに適用"""
        stats = cached_stats.get("stats")
        if stats:
            if stats.get("node_count"):
                node.properties["mesh_node_count"] = stats["node_count"]
            if stats.get("element_count"):
                node.properties["mesh_element_count"] = stats["element_count"]
            if stats.get("element_types"):
                node.properties["mesh_element_types"] = stats["element_types"]
            if stats.get("elset_summary"):
                node.properties["mesh_elset_summary"] = stats["elset_summary"]
            if stats.get("quality"):
                node.properties["mesh_quality"] = stats["quality"]

        element_quality = cached_stats.get("element_quality")
        if element_quality:
            node.properties["mesh_element_quality"] = element_quality

        topology_groups = cached_stats.get("topology_groups")
        if topology_groups:
            node.properties["mesh_topology_groups"] = topology_groups

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        from services.parse.connectors.abaqus.mesh import (
            extract_element_quality_stats,
            extract_mesh_stats,
            extract_mesh_topology_groups,
        )

        # Phase 1: ノード分類（キャッシュヒット / 要parse）
        cache_hit_nodes: list[tuple[Any, dict[str, Any]]] = []
        parse_needed: list[tuple[Any, Path, str | None]] = []  # (node, file_path, mesh_hash)

        for node in graph.nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() != ".inp":
                continue

            file_path = graph.project_root / node.properties.get("path", "")
            if not file_path.exists():
                continue

            # タイムスタンプ差分: 変更されていなければスキップ
            if not graph.is_file_modified(str(file_path)):
                logger.debug(f"Skipping unchanged file: {node.name}")
                continue

            # メッシュコンテンツハッシュによるキャッシュ（パラメーター/境界条件違いの共有）
            mesh_hash = _compute_mesh_content_hash(str(file_path))
            if mesh_hash is not None:
                cached_stats = _load_mesh_stats_cache(graph, mesh_hash)
                if cached_stats is not None:
                    logger.debug(f"Mesh stats cache hit for {node.name} (hash={mesh_hash[:12]})")
                    cache_hit_nodes.append((node, cached_stats))
                    continue

            parse_needed.append((node, file_path, mesh_hash))

        # Phase 1.5: キャッシュヒットノードに即座に適用
        for node, cached_stats in cache_hit_nodes:
            self._apply_mesh_stats_to_node(node, cached_stats)

        # Phase 2: 複数ファイルのread_inp()を並列実行（キャッシュミス分）
        if len(parse_needed) > 1:
            self._prefetch_inp_parallel(graph, parse_needed)

        # Phase 3: メッシュ統計を抽出・適用（順次処理）
        for node, file_path, mesh_hash in parse_needed:
            cached_abq = self._get_or_parse_inp(graph, str(file_path))

            stats = extract_mesh_stats(file_path, verbose=False, cached_abq_data=cached_abq)
            if stats is None:
                logger.debug(f"extract_mesh_stats returned None for {node.name}")
                continue

            if stats.get("node_count"):
                node.properties["mesh_node_count"] = stats["node_count"]
            if stats.get("element_count"):
                node.properties["mesh_element_count"] = stats["element_count"]
            if stats.get("element_types"):
                node.properties["mesh_element_types"] = stats["element_types"]
            if stats.get("elset_summary"):
                node.properties["mesh_elset_summary"] = stats["elset_summary"]
            if stats.get("quality"):
                node.properties["mesh_quality"] = stats["quality"]
            else:
                logger.debug(
                    f"mesh_quality not computed for {node.name} "
                    f"(node_count={stats.get('node_count', 0)}, "
                    f"element_count={stats.get('element_count', 0)})"
                )

            # *ELEMENTキーワードブロック（要素タイプ）ごとの品質統計
            element_quality = extract_element_quality_stats(file_path, verbose=False, cached_abq_data=cached_abq)
            if element_quality:
                node.properties["mesh_element_quality"] = element_quality

            # メッシュトポロジーグループ（ノード共有による連結成分解析）
            topology_groups = extract_mesh_topology_groups(file_path, verbose=False, cached_abq_data=cached_abq)
            if topology_groups:
                node.properties["mesh_topology_groups"] = topology_groups

            # メッシュ統計をハッシュキーでディスクキャッシュに保存
            if mesh_hash is not None:
                cache_data: dict[str, Any] = {
                    "stats": stats,
                    "element_quality": element_quality,
                    "topology_groups": topology_groups,
                }
                _save_mesh_stats_cache(graph, mesh_hash, cache_data)

        return graph

    @staticmethod
    def _compute_optimal_workers(file_count: int, use_processes: bool = False) -> int:
        """並列プリフェッチの最適ワーカー数を計算

        read_inp()はI/Oバウンド（ファイル読み込み）とCPUバウンド（パース）の
        混合処理であるため、並列化方式に応じて最適ワーカー数を算出する。

        - ThreadPoolExecutor (use_processes=False): CPU数の2倍（I/O待ちの隠蔽）
        - ProcessPoolExecutor (use_processes=True): CPU数（GIL回避による真の並列化）

        Args:
            file_count: 処理対象ファイル数
            use_processes: ProcessPoolExecutor使用時True

        Returns:
            推奨ワーカー数（最小1、最大16、ファイル数以下）
        """
        import os

        cpu_count = os.cpu_count() or 4
        if use_processes:
            # ProcessPool: CPU数が上限（プロセス間オーバーヘッド考慮）
            optimal = min(cpu_count, 16)
        else:
            # ThreadPool: CPU数の2倍（I/O待ち隠蔽、GIL競合は許容）
            optimal = min(cpu_count * 2, 16)
        return max(1, min(optimal, file_count))

    # ProcessPoolExecutor使用の最小ファイル数閾値
    # ファイル数が少ない場合はプロセス起動オーバーヘッドが支配的になるため
    # ThreadPoolExecutorの方が高速
    _PROCESS_POOL_THRESHOLD = 3

    @staticmethod
    def _prefetch_inp_parallel(
        graph: ProjectGraph,
        parse_needed: list[tuple[Any, Path, str | None]],
        max_workers: int | None = None,
        use_processes: bool | None = None,
    ) -> None:
        """複数.inpファイルのread_inp()を並列実行してキャッシュにプリフェッチする

        read_inp()結果はインメモリキャッシュに保存されるため、
        後続の_get_or_parse_inp()呼び出しでキャッシュヒットする。

        並列化方式:
        - ProcessPoolExecutor: GIL回避による真の並列CPU処理。ファイル数3以上で自動選択。
          ABQDataのpickleシリアライゼーションを経由するため、プロセス間通信のオーバーヘッドあり。
        - ThreadPoolExecutor: ファイル数が少ない場合やProcessPoolが利用不可の場合のフォールバック。
          GILの制約はあるが、プロセス起動コストが不要で軽量。

        Args:
            graph: ProjectGraph（キャッシュ保存先）
            parse_needed: (node, file_path, mesh_hash)のリスト
            max_workers: 並列ワーカー数（Noneでcpu_countベースの自動決定）
            use_processes: ProcessPoolExecutor使用フラグ。
                None=自動（ファイル数>=閾値でProcess）、True=強制Process、False=強制Thread
        """
        from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed

        import services.parse.connectors.abaqus as abaqus_mod

        # 同一ファイルの重複parseを避けるためパス単位で一意化
        unique_paths: dict[str, Path] = {}
        for _, file_path, _ in parse_needed:
            fp_str = str(file_path)
            if fp_str not in unique_paths and graph.get_cached_plugin_data("abaqus", fp_str) is None:
                unique_paths[fp_str] = file_path

        if not unique_paths:
            return

        include_depth = graph.config.include_search_depth

        # 並列化方式の自動決定
        if use_processes is None:
            use_processes = len(unique_paths) >= AbaqusMeshParser._PROCESS_POOL_THRESHOLD

        # max_workers未指定時はCPU数ベースで自動決定
        if max_workers is None:
            max_workers = AbaqusMeshParser._compute_optimal_workers(len(unique_paths), use_processes=use_processes)

        pool_type = "process" if use_processes else "thread"
        logger.debug(
            f"Prefetching {len(unique_paths)} .inp files in parallel (workers={max_workers}, pool={pool_type})"
        )

        if use_processes:
            # ProcessPoolExecutor: モジュールレベル関数でpickle可能にする
            args_list = [(fp, include_depth) for fp in unique_paths]
            try:
                with ProcessPoolExecutor(max_workers=max_workers) as executor:
                    futures = {executor.submit(_parse_inp_worker, args): args[0] for args in args_list}
                    for future in as_completed(futures):
                        fp_str = futures[future]
                        try:
                            _, abq = future.result()
                            graph.set_cached_plugin_data("abaqus", fp_str, abq)
                        except Exception as e:
                            logger.warning(f"Parallel prefetch failed for {fp_str}: {e}")
                return
            except (OSError, RuntimeError) as e:
                # ProcessPoolExecutor起動失敗時はThreadPoolExecutorにフォールバック
                logger.debug(f"ProcessPoolExecutor unavailable, falling back to threads: {e}")

        # ThreadPoolExecutor（デフォルトまたはフォールバック）
        def _parse_single(fp_str: str) -> tuple[str, object]:
            abq = abaqus_mod.read_inp(fp_str, verbose=False, include_max_depth=include_depth)
            return fp_str, abq

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_parse_single, fp): fp for fp in unique_paths}
            for future in as_completed(futures):
                fp_str = futures[future]
                try:
                    _, abq = future.result()
                    graph.set_cached_plugin_data("abaqus", fp_str, abq)
                except Exception as e:
                    logger.warning(f"Parallel prefetch failed for {fp_str}: {e}")
