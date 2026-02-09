"""ファイル名解析ユーティリティ

FileParse クラスとレガシーな関数インターフェースを提供します。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re
from typing import Generic, Iterable, TypeVar

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


TFileParse = TypeVar("TFileParse", bound="FileParse")


def _match_extension(
    filename: str, extension_candidates: Iterable[str] | None = None
) -> str:
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


@dataclass(frozen=True)
class FileParse:
    true_file_path: str | Path
    extension_candidates: Iterable[str] | None = None

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
        """ファイル名から日付を抽出（YYMMDD or YYYYMMDD形式）

        Returns:
            日付文字列（見つからない場合は空文字）
        """
        _, tags = self._split_props_and_tags()
        for token in tags:
            if DATE_PATTERN.match(token):
                return token
        return ""

    def get_date_formatted(self) -> str:
        """日付を標準形式（YYYY-MM-DD）に変換

        Returns:
            YYYY-MM-DD形式の日付文字列（見つからない場合は空文字）
        """
        date_str = self.get_date()
        if not date_str:
            return ""

        if len(date_str) == 6:
            # YYMMDD → 20YY-MM-DD（2000年代と仮定）
            year = int(date_str[:2])
            if year > 50:  # 50以上は1900年代
                full_year = 1900 + year
            else:
                full_year = 2000 + year
            return f"{full_year:04d}-{date_str[2:4]}-{date_str[4:6]}"
        elif len(date_str) == 8:
            # YYYYMMDD → YYYY-MM-DD
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return ""

    def get_file_group(
        self, candidates: Iterable[str | Path] | None = None
    ) -> FileGroup["FileParse"]:
        file_type = self.get_file_type()
        index = self.get_index()
        targets = list(candidates) if candidates is not None else [self.true_file_path]
        items: list[FileParse] = []
        for candidate in targets:
            parser = FileParse(candidate, extension_candidates=self.extension_candidates)
            if parser.get_file_type() == file_type and parser.get_index() == index:
                items.append(parser)
        if self.true_file_path not in targets:
            parser = FileParse(self.true_file_path, extension_candidates=self.extension_candidates)
            if parser.get_file_type() == file_type and parser.get_index() == index:
                items.append(parser)
        return FileGroup(tuple(items), file_type=file_type, index=index)


@dataclass(frozen=True)
class ObsidianMap:
    true_file_path: str | Path
    notes_dir: str | Path = "notes/props"
    base_path: str | Path = "notes/bases"
    extension_candidates: Iterable[str] | None = None

    def _file_parse(self) -> FileParse:
        return FileParse(self.true_file_path, extension_candidates=self.extension_candidates)

    def get_base_path(self) -> Path:
        return Path(self.base_path)

    def to_frontmatter_path(
        self,
        true_file_path: str | Path | None = None,
        notes_dir: str | Path | None = None,
    ) -> Path:
        target_path = true_file_path or self.true_file_path
        parser = FileParse(target_path, extension_candidates=self.extension_candidates)
        path = Path(target_path)
        if path.is_dir():
            basename = path.name
        else:
            basename, ext = parser._split_extension()
            if ext:
                basename = f"{basename}.{ext.lstrip('.')}"  # .inp → .inp.md に変更
        base_dir = Path(notes_dir or self.notes_dir)
        return base_dir / f"{basename}.md"

    def get_frontmatter_path(self) -> Path:
        return self.to_frontmatter_path()


@dataclass(frozen=True)
class ObsidianFileParse(FileParse):
    notes_dir: str | Path = "notes/props"
    base_path: str | Path = "notes/bases"

    def _obsidian_map(self) -> ObsidianMap:
        return ObsidianMap(
            self.true_file_path,
            notes_dir=self.notes_dir,
            base_path=self.base_path,
            extension_candidates=self.extension_candidates,
        )

    def get_frontmatter_path(self) -> Path:
        return self._obsidian_map().get_frontmatter_path()

    def get_base_path(self) -> Path:
        return self._obsidian_map().get_base_path()

    def to_frontmatter_path(self) -> Path:
        return self._obsidian_map().to_frontmatter_path()


# ===========================================================================
# レガシー関数インターフェース（旧file_utils.pyから統合）
# ===========================================================================

# 拡張子候補リスト
TARGET_EXTENSIONS: list[str] = [
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
    ".inp",
    ".odb",
    ".sta",
]


def normalize_extension_to_inp(filepath: str) -> tuple[str, str]:
    """拡張子を正規化して、.inp形式に変換する

    Args:
        filepath: ファイルパス

    Returns:
        (拡張子を.inpに置き換えたパス, 元の拡張子)

    Examples:
        >>> normalize_extension_to_inp("go_test.cas.h5")
        ('go_test.inp', '.cas.h5')
        >>> normalize_extension_to_inp("go_test.inp")
        ('go_test.inp', '.inp')
        >>> normalize_extension_to_inp("go_test")
        ('go_test', '')
    """
    if "." not in filepath:
        return filepath, ""

    ext = None
    for ext_i in TARGET_EXTENSIONS:
        if filepath.endswith(ext_i):
            ext = ext_i
            break

    if ext is None:
        ext = "." + filepath.split(".")[-1]

    # .inpに置き換え
    normalized = filepath.replace(ext, ".inp")
    return normalized, ext


def get_basename_with_ext(filepath: str) -> tuple[str, str]:
    """ファイルパスからbasename（拡張子なし）と拡張子を取得

    Args:
        filepath: ファイルパス

    Returns:
        (basename, 拡張子)

    Examples:
        >>> get_basename_with_ext("path/to/go_test.v1.inp")
        ('go_test.v1', '.inp')
        >>> get_basename_with_ext("go_test.cas.h5")
        ('go_test', '.cas.h5')
    """
    normalized, ext = normalize_extension_to_inp(filepath)
    if ext:
        # .inpを除去してbasenameを取得
        basename = normalized[:-4]
    else:
        basename = normalized

    # パス部分を除去
    basename = basename.split("/")[-1].split("\\")[-1]
    return basename, ext


def get_basename(filepath: str) -> str:
    """ファイルパスからbasename（拡張子なし）のみを取得

    Args:
        filepath: ファイルパス

    Returns:
        basename（拡張子なし）

    Examples:
        >>> get_basename("path/to/go_test.v1.inp")
        'go_test.v1'
    """
    basename, _ = get_basename_with_ext(filepath)
    return basename


def get_group_name(filepath: str) -> str:
    """ファイル名からグループ名を抽出（idx/verを除いた先頭部分）

    Args:
        filepath: ファイルパス

    Returns:
        グループ名（go, mesh等の先頭プレフィックス）

    Examples:
        >>> get_group_name("go_idx1_v2.inp")
        'go'
        >>> get_group_name("mesh_box.inp")
        'mesh'
    """
    if os.path.isdir(filepath):
        return ""

    basename, _ = get_basename_with_ext(filepath)
    # headを取得（例: go_1_v2 → go）
    head = basename.split("_")[0]
    return head


def get_index_and_version(inp_filepath: str) -> tuple[str, str]:
    """ファイルパスからindex(idx)とversion(v)を抽出

    Args:
        inp_filepath: ファイルパス

    Returns:
        (index, version) のタプル。存在しない場合は空文字

    Examples:
        >>> get_index_and_version("go_idx1.v2.inp")
        ('1', '2')
        >>> get_index_and_version("go_test.inp")
        ('', '')
    """
    if os.path.isdir(inp_filepath):
        return "", ""
    if inp_filepath.endswith(".py"):
        return "", ""

    # FileParseを使用して解析
    parser = FileParse(inp_filepath)
    return parser.get_index(), parser.get_version()


def get_index_and_version_legacy(inp_filepath: str) -> tuple[str, str]:
    """レガシーな実装（cli/__init__.pyから移植）

    互換性のために残しているが、新規コードでは get_index_and_version() を使用すること。

    Args:
        inp_filepath: ファイルパス

    Returns:
        (index, version) のタプル
    """
    if os.path.isdir(inp_filepath):
        return "", ""
    if inp_filepath.endswith(".py"):
        return "", ""

    inp_filepath_str, ext = get_basename_with_ext(inp_filepath)
    head = inp_filepath_str.split("_")[0]
    inp_filepath_str = inp_filepath_str[len(head) + 1:]

    # idx
    if inp_filepath_str.startswith("idx"):
        idx = inp_filepath_str.split(".")[0].split("_")[0].replace("idx", "")
    else:
        idx = ""

    # ver
    basename = inp_filepath_str.replace(ext, "") if ext else inp_filepath_str
    if basename.split(".")[-1].startswith("v"):
        version = basename.split(".")[-1].replace("v", "")
    else:
        version = ""

    return idx, version


def safe_relative_path(file_path: Path, base_path: Path | None = None) -> str:
    """Windowsでも安全に相対パスを生成（POSIX形式で返す）

    Args:
        file_path: 対象ファイルパス
        base_path: 基準パス（デフォルト: Path.cwd()）

    Returns:
        POSIX形式（/区切り）の相対パス文字列
    """
    base = base_path or Path.cwd()
    try:
        # resolve()で正規化してから比較
        resolved_file = file_path.resolve()
        resolved_base = base.resolve()
        rel = resolved_file.relative_to(resolved_base)
        # 常にPOSIX形式で返す
        return rel.as_posix()
    except ValueError:
        # relative_toが失敗した場合（異なるドライブ等）
        return file_path.as_posix()
