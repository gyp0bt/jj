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

# パーサーサブクラスをimportして自動登録
import services.parse.parsers  # noqa: F401
import services.parse.connectors.abaqus.inp_parser  # noqa: F401
import services.parse.connectors.abaqus.result_parser  # noqa: F401
import services.parse.connectors.abaqus.mesh_parser  # noqa: F401
import services.parse.connectors.abaqus.diff_parser  # noqa: F401
import services.parse.connectors.obsidian.daily_parser  # noqa: F401

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
