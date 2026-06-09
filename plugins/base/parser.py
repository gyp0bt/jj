"""パーサー基盤モジュール

ファイル名解析ユーティリティ（FileNameParser）と
グラフエンリッチメント用抽象パーサー基底クラス（AbstractFileParser）を提供します。

## グラフパーサーパターン

AbstractFileParserのサブクラスを定義すると __init_subclass__ により
自動的にパーサーレジストリに登録されます。parse() 関数で全パーサーが
priority順に適用されます。

```python
class MyParser(AbstractFileParser):
    priority = 50

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        # グラフを更新して返す
        return graph
```

## どのパーサーがどこで何をしているか追う（自動登録の所在問題）

自動登録は便利な反面「実装がどのファイルにあるか分からない」という問題を生む。
そこで以下でパイプラインを可視化できる:

- `format_pipeline_plan()` — priority順に「パーサー名・定義ファイル:行・タスク
  （docstring1行目）」の一覧を文字列で返す。`jj parse --explain` で表示。
- `parse(..., trace=True)`（`jj parse --trace` / 環境変数 `JJ_PARSE_TRACE=1`）—
  実行しながら各パーサーの定義ファイル:行・ノード/リレーション増分・所要時間を出力。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

import inspect
import re
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph

DEFAULT_EXTENSIONS: tuple[str, ...] = (
    ".cas.h5",
    ".dat.h5",
    ".aedt.batchinfo",
    ".py",
    ".xlsx",
    ".csv",
    ".pptx",
    ".yaml",
    ".md",
    ".json",
    ".sh",
    ".msh",
    ".modfem",
    ".stp",
    ".step",
    ".catPart",
    ".dxf",
    ".dwg",
    ".png",
    ".gif",
)

# スキャンするがNodeの実体を作らない拡張子
NO_NODE_EXTENSIONS: tuple[str, ...] = (
    ".odb.json",
    ".odb",
)

FILE_TYPE_PREFIXES: tuple[tuple[str, str], ...] = (
    ("go_", "go"),
    ("mesh_", "mesh"),
    ("material_", "material"),
    ("step_", "step"),
)

# 暗黙的なタイプ認識用（ファイル名がそのものの場合: material.inp, mesh.inp等）
IMPLICIT_TYPE_BASENAMES: dict[str, str] = {
    "go": "go",
    "mesh": "mesh",
    "material": "material",
    "step": "step",
}

# 日付パターン（YYMMDD or YYYYMMDD）
DATE_PATTERN = re.compile(r"^(\d{6}|\d{8})$")


class FileType(Enum):
    GO = "go"
    MESH = "mesh"
    MATERIAL = "material"
    STEP = "step"
    UNKNOWN = "unknown"


TFileParse = TypeVar("TFileParse", bound="FileNameParser")


def _match_extension(filename: str, extension_candidates: Iterable[str] | None = None) -> str:
    candidates = tuple(extension_candidates or DEFAULT_EXTENSIONS)
    lower_name = filename.lower()
    for ext in sorted(candidates, key=len, reverse=True):
        if lower_name.endswith(ext.lower()):
            return ext
    if "." not in filename:
        return ""
    return f".{filename.split('.')[-1]}"


def _parse_prop_token(token: str) -> tuple[str, str] | None:
    if "=" in token:
        key, value = token.split("=", 1)
        if key and value:
            return key, value
        return None
    match = re.fullmatch(r"([A-Za-z]+)(\d+)", token)
    if match:
        return match.group(1), match.group(2)
    return None


@dataclass(frozen=True)
class FileGroup(Generic[TFileParse]):
    items: tuple[TFileParse, ...]
    file_type: FileType
    index: str

    def __len__(self) -> int:
        return len(self.items)

    def to_df(self):  # type: ignore[override]
        import pandas as pd

        rows: list[dict[str, str]] = []
        for item in self.items:
            row: dict[str, str] = {
                "path": str(item.true_file_path),
                "file_type": item.get_file_type().value,
                "index": item.get_index(),
                "version": item.get_version(),
            }
            row.update(item.get_props())
            rows.append(row)
        return pd.DataFrame(rows)


# ===========================================================================
# ファイル名解析クラス（旧AbstractFileParser）
# ===========================================================================


class FileNameParser:
    """ファイル名解析クラス

    ファイルパスからbasename, 拡張子, index, version, props, tags等を抽出する。
    旧名 AbstractFileParser。FileParse (file_parse.py) と同等の機能を提供。
    """

    def __init__(
        self,
        true_filepath: Path,
        extension_candidates: Iterable[str] | None = None,
    ):
        self.true_file_path = true_filepath
        self.extension_candidates = extension_candidates

    def _as_path(self) -> Path:
        return Path(self.true_file_path)

    def _split_extension(self) -> tuple[str, str]:
        filename = self._as_path().name
        ext = _match_extension(filename, self.extension_candidates)
        if ext and filename.lower().endswith(ext.lower()):
            return filename[: -len(ext)], ext
        return filename, ""

    def get_basename(self) -> str:
        basename, _ = self._split_extension()
        return basename

    def get_directory(self) -> str:
        return str(self._as_path().parent)

    def get_file_type(self) -> FileType:
        basename = self.get_basename().lower()
        # プレフィックスベースのタイプ判定
        for prefix, type_name in FILE_TYPE_PREFIXES:
            if basename.startswith(prefix):
                return FileType(type_name)
        # 暗黙のタイプ判定（ファイル名がそのものの場合: material, mesh等）
        # .v2などのサフィックスを除去して比較
        base_without_version = re.sub(r"\.v\d+$", "", basename)
        if base_without_version in IMPLICIT_TYPE_BASENAMES:
            return FileType(IMPLICIT_TYPE_BASENAMES[base_without_version])
        return FileType.UNKNOWN

    def _prefix_to_strip(self) -> str:
        basename = self.get_basename().lower()
        for prefix, _ in FILE_TYPE_PREFIXES:
            if basename.startswith(prefix):
                return self.get_basename()[: len(prefix)]
        return ""

    def _basename_without_prefix(self) -> str:
        basename = self.get_basename()
        prefix = self._prefix_to_strip()
        if prefix:
            return basename[len(prefix) :]
        return basename

    def _tokenize(self) -> list[str]:
        basename = self._basename_without_prefix()
        raw_tokens = [token for token in basename.split("_") if token]
        tokens: list[str] = []
        for token in raw_tokens:
            if "." in token:
                tokens.extend([segment for segment in token.split(".") if segment])
            else:
                tokens.append(token)
        return tokens

    def get_tokens(self) -> list[str]:
        """プレフィックス除去後のトークンリストを返す（外部からのトークン参照用）"""
        return self._tokenize()

    def _split_props_and_tags(self) -> tuple[dict[str, str], list[str]]:
        props: dict[str, str] = {}
        tags: list[str] = []
        for token in self._tokenize():
            parsed = _parse_prop_token(token)
            if parsed:
                key, value = parsed
                props[key] = value
            else:
                tags.append(token)
        legacy_version = self._legacy_version()
        if legacy_version and "v" not in props:
            props["v"] = legacy_version
        return props, tags

    def _legacy_version(self) -> str:
        basename = self._basename_without_prefix()
        match = re.search(r"\.v(\d+)$", basename)
        if match:
            return match.group(1)
        return ""

    def _is_implicit_type_file(self) -> bool:
        """暗黙のタイプファイルかどうかを判定（material.inp, mesh.inp等）"""
        basename = self.get_basename().lower()
        base_without_version = re.sub(r"\.v\d+$", "", basename)
        return base_without_version in IMPLICIT_TYPE_BASENAMES

    def get_index(self) -> str:
        props, _ = self._split_props_and_tags()
        idx = props.get("idx", "")
        # 暗黙のタイプファイルでidxがない場合は"1"を返す
        if not idx and self._is_implicit_type_file():
            return "1"
        return idx

    def get_version(self) -> str:
        props, _ = self._split_props_and_tags()
        if "v" in props:
            return props["v"]
        legacy = self._legacy_version()
        if legacy:
            return legacy
        # 暗黙のタイプファイルでversionがない場合は"1"を返す
        if self._is_implicit_type_file():
            return "1"
        return ""

    def get_props(self) -> dict[str, str]:
        props, _ = self._split_props_and_tags()
        return props

    def get_tags(self) -> list[str]:
        _, tags = self._split_props_and_tags()
        # 日付パターンは tagsから除外
        return [t for t in tags if not DATE_PATTERN.match(t)]

    def get_date(self) -> str:
        """ファイル名から日付を抽出（YYMMDD or YYYYMMDD形式）"""
        _, tags = self._split_props_and_tags()
        for token in tags:
            if DATE_PATTERN.match(token):
                return token
        return ""

    def get_date_formatted(self) -> str:
        """日付を標準形式（YYYY-MM-DD）に変換"""
        date_str = self.get_date()
        if not date_str:
            return ""

        if len(date_str) == 6:
            year = int(date_str[:2])
            if year > 50:
                full_year = 1900 + year
            else:
                full_year = 2000 + year
            return f"{full_year:04d}-{date_str[2:4]}-{date_str[4:6]}"
        elif len(date_str) == 8:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return ""

    def get_file_group(self, candidates: Iterable[str | Path] | None = None) -> FileGroup[FileNameParser]:
        file_type = self.get_file_type()
        index = self.get_index()
        targets = list(candidates) if candidates is not None else [self.true_file_path]
        items: list[FileNameParser] = []
        for candidate in targets:
            parser = FileNameParser(candidate, extension_candidates=self.extension_candidates)
            if parser.get_file_type() == file_type and parser.get_index() == index:
                items.append(parser)
        if self.true_file_path not in targets:
            parser = FileNameParser(self.true_file_path, extension_candidates=self.extension_candidates)
            if parser.get_file_type() == file_type and parser.get_index() == index:
                items.append(parser)
        return FileGroup(tuple(items), file_type=file_type, index=index)


# ===========================================================================
# グラフパーサー基底クラス（Phase R2: 新アーキテクチャ）
# ===========================================================================

# パーサーレジストリ: __init_subclass__ で自動登録される
_parser_registry: list[type[AbstractFileParser]] = []


class AbstractFileParser(ABC):
    """グラフエンリッチメント用抽象パーサー基底クラス

    ProjectGraphを受け取り、ノード・リレーションの追加や
    属性付与を行って返す。サブクラスを定義すると自動的に
    パーサーレジストリに登録される。

    priority属性で実行順序を制御する（小さいほど先に実行）。
    requires_full属性がTrueのパーサーは--fullオプション時のみ実行される。

    パーサー実行順序の指針:
        10: ファイル名解析（ノード生成）
        20: バージョン・グループ関係
        30: 入力-結果・アセット・出力関係
        40: includes関係
        50: ディレクトリ関係
        60: Abaqus INP解析（material, *PARAMETER）
        70: Abaqus結果ファイル解析（.sta, .msg, .dat）
        80: Abaqusメッシュ統計（requires_full）
        85: プロパティ伝搬（include, material assignment）
        90: Abaqusバージョン差分
        95: Daily note解析
        98: Elset Node化、root directory
        99: Enrichment-onlyノードフィルタ
    """

    priority: int = 100
    requires_full: bool = False  # Trueの場合は--fullオプション時のみ実行

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        # 抽象メソッドが残っているクラスは登録しない
        # Note: ABCMeta.__new__はtype.__new__の後に__abstractmethods__を設定するが、
        # __init_subclass__はtype.__new__内で呼ばれるため、新規定義された
        # abstractmethodが__abstractmethods__に反映されていない場合がある。
        # クラスの名前空間を直接チェックして補完する。
        has_abstract = getattr(cls, "__abstractmethods__", None) or any(
            getattr(v, "__isabstractmethod__", False) for v in cls.__dict__.values()
        )
        if not has_abstract:
            _parser_registry.append(cls)

    @abstractmethod
    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        """グラフを受け取り、エンリッチメントを適用して返す

        Args:
            graph: 処理対象のProjectGraph

        Returns:
            更新されたProjectGraph（通常は同一オブジェクト）
        """
        ...


def get_parser_registry() -> list[type[AbstractFileParser]]:
    """登録済みパーサーの一覧を返す（テスト・デバッグ用）"""
    return list(_parser_registry)


def clear_parser_registry() -> None:
    """パーサーレジストリをクリアする（テスト用）"""
    _parser_registry.clear()


def parser_location(cls: type) -> str:
    """パーサークラスが定義されているファイルと行番号を "path:line" で返す。

    自動登録（__init_subclass__）で「どこに実装があるか分からない」問題を
    解消するためのヘルパー。パスは可能ならカレントディレクトリからの相対パス。
    """
    try:
        src = inspect.getsourcefile(cls) or inspect.getfile(cls)
    except (TypeError, OSError):
        return f"{getattr(cls, '__module__', '?')} (場所不明)"
    try:
        line = inspect.getsourcelines(cls)[1]
    except (OSError, TypeError):
        line = 0
    path = Path(src)
    try:
        path = path.relative_to(Path.cwd())
    except ValueError:
        pass
    return f"{path}:{line}"


def parser_task(cls: type) -> str:
    """パーサーの「タスク」= docstring の1行目を返す（なければクラス名）。"""
    doc = inspect.getdoc(cls)
    if doc:
        first = doc.strip().splitlines()[0].strip()
        if first:
            return first
    return cls.__name__


def describe_registry(full_mode: bool = True) -> list[dict[str, object]]:
    """登録済みパーサーを実行順（priority昇順）で記述したリストを返す。

    各要素: {priority, name, location, task, requires_full}。
    full_mode=False の場合、requires_full=True のパーサーは除外する。
    """
    eligible = [c for c in _parser_registry if full_mode or not c.requires_full]
    ordered = sorted(eligible, key=lambda c: (c.priority, c.__name__))
    return [
        {
            "priority": c.priority,
            "name": c.__name__,
            "location": parser_location(c),
            "task": parser_task(c),
            "requires_full": c.requires_full,
        }
        for c in ordered
    ]


def format_pipeline_plan(full_mode: bool = True) -> str:
    """パーサーパイプラインを priority順の一覧文字列に整形して返す。

    `jj parse --explain` から呼ばれ、「誰が・どのファイルで・何をするか」を一望できる。
    """
    rows = describe_registry(full_mode=full_mode)
    if not rows:
        return "（登録済みパーサーがありません。プラグインがロードされていない可能性があります）"
    mode = "full" if full_mode else "lite"
    lines = [f"パーサーパイプライン（{mode}, 実行順 / 全{len(rows)}段）:"]
    for r in rows:
        flag = " [full]" if r["requires_full"] else ""
        lines.append(f"  [{r['priority']:>3}] {r['name']}{flag}")
        lines.append(f"        ファイル: {r['location']}")
        lines.append(f"        タスク  : {r['task']}")
    return "\n".join(lines)


def _group_parsers_by_priority(
    parsers: list[type[AbstractFileParser]],
) -> list[list[type[AbstractFileParser]]]:
    """パーサーを同一priority値でグルーピングする

    Returns:
        priority昇順のグループリスト。各グループ内のパーサーは同一priority。
    """
    from itertools import groupby

    sorted_parsers = sorted(parsers, key=lambda cls: cls.priority)
    return [list(group) for _, group in groupby(sorted_parsers, key=lambda cls: cls.priority)]


def parse(
    graph: ProjectGraph,
    *,
    full_mode: bool = False,
    debug: bool = False,
    parallel: bool = False,
    max_workers: int | None = None,
    trace: bool | None = None,
) -> ProjectGraph:
    """全登録パーサーをpriority順に適用する

    Args:
        graph: 処理対象のProjectGraph
        full_mode: Trueの場合、requires_full=Trueのパーサーも実行する
        debug: デバッグモード（True: パーサーエラーをraise）
        parallel: Trueの場合、同一priorityグループ内のパーサーを並列実行する
        max_workers: 並列実行時のワーカー数（Noneでcpu_count()ベースの自動決定）
        trace: Trueで各パーサーの定義ファイル:行・ノード/リレーション増分・所要時間を
               stderrに出力する。Noneのときは環境変数 JJ_PARSE_TRACE で判定。

    Returns:
        全パーサー適用後のProjectGraph
    """
    import os
    import sys
    import time

    if trace is None:
        trace = os.environ.get("JJ_PARSE_TRACE", "").strip().lower() in ("1", "true", "yes")

    eligible = [cls for cls in _parser_registry if full_mode or not cls.requires_full]
    groups = _group_parsers_by_priority(eligible)
    node_count = len(graph.nodes) or 1  # ゼロ除算防止

    if trace:
        mode = "full" if full_mode else "lite"
        print(f"=== parse pipeline trace ({mode}, {len(eligible)}段） ===", file=sys.stderr)

    for group in groups:
        if parallel and len(group) > 1:
            if trace:
                names = ", ".join(c.__name__ for c in group)
                print(f"[{group[0].priority:>3}] (parallel) {names}", file=sys.stderr)
            graph = _run_parser_group_parallel(graph, group, debug=debug, max_workers=max_workers)
            continue
        for parser_cls in group:
            n0, r0 = len(graph.nodes), len(graph.relations)
            start_time = time.monotonic()
            try:
                graph = parser_cls().apply(graph)
            except Exception as e:
                if debug:
                    raise
                print(
                    f"警告: {parser_cls.__name__} でエラーが発生しました: {e}",
                    file=sys.stderr,
                )
                continue
            elapsed = time.monotonic() - start_time

            if trace:
                dn = len(graph.nodes) - n0
                dr = len(graph.relations) - r0
                print(
                    f"[{parser_cls.priority:>3}] {parser_cls.__name__}  ({parser_location(parser_cls)})\n"
                    f"        {parser_task(parser_cls)}\n"
                    f"        ノード {dn:+d} / リレーション {dr:+d} / {elapsed:.3f}s",
                    file=sys.stderr,
                )

            if not full_mode and elapsed > 0 and (elapsed / node_count) > 0.1:
                print(
                    f"警告: {parser_cls.__name__} の実行に {elapsed:.1e}秒かかりました"
                    f"（{elapsed / node_count:.1e}秒/ファイル）。"
                    f"--fullオプションでの実行を推奨します。",
                    file=sys.stderr,
                )

    return graph


def _run_parser_group_parallel(
    graph: ProjectGraph,
    group: list[type[AbstractFileParser]],
    *,
    debug: bool = False,
    max_workers: int | None = None,
) -> ProjectGraph:
    """同一priorityグループ内のパーサーをThreadPoolExecutorで並列実行する

    注意: 各パーサーが生成するノード・リレーションは独立している前提。
    既存ノードのプロパティ変更を行うパーサー同士が同一priorityにいる場合、
    競合する可能性がある。

    Args:
        graph: 処理対象のProjectGraph
        group: 同一priorityのパーサークラスリスト
        debug: デバッグモード
        max_workers: ワーカー数

    Returns:
        全パーサー適用後のProjectGraph
    """
    import sys
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _apply_parser(parser_cls: type[AbstractFileParser]) -> None:
        parser_cls().apply(graph)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_apply_parser, cls): cls for cls in group}
        for future in as_completed(futures):
            parser_cls = futures[future]
            try:
                future.result()
            except Exception as e:
                if debug:
                    raise
                print(
                    f"警告: {parser_cls.__name__} でエラーが発生しました: {e}",
                    file=sys.stderr,
                )

    return graph
