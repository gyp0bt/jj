"""ファイル名解析ユーティリティ

cli/__init__.py から分離したファイル名解析関連のユーティリティ関数。
FileParse クラスとの互換性を保ちつつ、レガシーなインターフェースを提供します。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import os
from pathlib import Path

from .file_parse import FileParse, DEFAULT_EXTENSIONS


# 拡張子候補リスト（cli/__init__.pyのnormalize_extension_to_inpから移植）
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
