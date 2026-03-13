"""除外パターンマッチング

config.yamlのsync.excludeパターンを使って
同期対象からファイルを除外する。
config.IgnoreConfigを再利用する。
"""

from __future__ import annotations

from config import IgnoreConfig

DEFAULT_EXCLUDE_PATTERNS: list[str] = [
    "*.odb",
    "*.res",
    "*.lck",
    "__pycache__",
    ".j2",
    ".git",
]


def build_exclude_config(
    config_patterns: list[str] | None = None,
    extra_patterns: list[str] | None = None,
) -> IgnoreConfig:
    """除外パターンからIgnoreConfigを構築する

    Args:
        config_patterns: config.yamlから読み込んだパターン（Noneならデフォルト使用）
        extra_patterns: CLI等から追加指定されたパターン

    Returns:
        プリコンパイル済みIgnoreConfig
    """
    patterns = list(config_patterns or DEFAULT_EXCLUDE_PATTERNS)
    if extra_patterns:
        patterns.extend(extra_patterns)
    return IgnoreConfig.from_list(patterns)
