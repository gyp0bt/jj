from .base import AbstractFileParser, FileNameParser, parse
from .file_parse import (
    TARGET_EXTENSIONS,
    FileGroup,
    FileParse,
    FileType,
    ObsidianFileParse,
    ObsidianMap,
    get_basename,
    get_basename_with_ext,
    get_group_name,
    get_index_and_version,
    get_index_and_version_legacy,
    normalize_extension_to_inp,
    safe_relative_path,
)

# 汎用パーサーサブクラスのimport（コア機能、自動登録用）
import services.parse.parsers  # noqa: F401

# Abaqus/Obsidian等のコネクターはプラグインレジストリ経由で動的に登録される。
# services.sdk.plugin_registry.load_all_plugins() を呼び出し済みであれば
# services.plugins.abaqus / services.plugins.obsidian が自動インポートされ、
# 各パーサーの__init_subclass__による自動登録が発動する。
# 後方互換: GraphServiceのimport時に load_all_plugins() が呼ばれる。
#
# Abaqus固有エクスポート（ABQData, read_inp, diff_abq_blocks等）はstatus-088で除去。
# Abaqus固有APIは services.parse.connectors.abaqus から直接importすること。

__all__ = [
    "AbstractFileParser",
    "FileGroup",
    "FileNameParser",
    "FileParse",
    "FileType",
    "ObsidianFileParse",
    "ObsidianMap",
    "TARGET_EXTENSIONS",
    "get_basename",
    "get_basename_with_ext",
    "get_group_name",
    "get_index_and_version",
    "get_index_and_version_legacy",
    "normalize_extension_to_inp",
    "parse",
    "safe_relative_path",
]
