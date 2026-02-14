from .base import AbstractFileParser, FileNameParser, parse
from .connectors.abaqus import (
    ABQData,
    BlockDiff,
    diff_abq_blocks,
    format_diff_blocks_markdown,
    format_diff_summary_table,
    generate_diff_props,
    read_inp,
)
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

__all__ = [
    "ABQData",
    "AbstractFileParser",
    "BlockDiff",
    "FileGroup",
    "FileNameParser",
    "FileParse",
    "FileType",
    "ObsidianFileParse",
    "ObsidianMap",
    "TARGET_EXTENSIONS",
    "diff_abq_blocks",
    "format_diff_blocks_markdown",
    "format_diff_summary_table",
    "generate_diff_props",
    "get_basename",
    "get_basename_with_ext",
    "get_group_name",
    "get_index_and_version",
    "get_index_and_version_legacy",
    "normalize_extension_to_inp",
    "parse",
    "read_inp",
    "safe_relative_path",
]
