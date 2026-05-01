"""Obsidianコネクタ（後方互換ラッパー）

本体は services.export.connectors.obsidian に移動済み。
既存コードの互換性のため、ここからre-exportする。

[READMEへ戻る](../../../README.md)
"""

from plugins.obsidian.export import (
    ObsidianConfig,
    ObsidianConnector,
    _coerce_property_value,
    _split_tag,
    from_obsidian_filename,
    get_directory_for_type,
    to_labeled_link,
    to_obsidian_file_link,
    to_obsidian_filename,
    to_obsidian_link,
    to_obsidian_md_link,
)

__all__ = [
    "ObsidianConfig",
    "ObsidianConnector",
    "_coerce_property_value",
    "_split_tag",
    "from_obsidian_filename",
    "get_directory_for_type",
    "to_labeled_link",
    "to_obsidian_file_link",
    "to_obsidian_filename",
    "to_obsidian_link",
    "to_obsidian_md_link",
]
