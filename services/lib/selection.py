"""共通ノード選択ユーティリティ

CLI引数の範囲展開（1..3 → ["1","2","3"]）と
共通選択オプション（-id, -v, -type, -all）の処理を提供する。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import re


def expand_ranges(values: list[str] | None) -> list[str] | None:
    """引数リスト中の範囲記法を展開する

    "1..3" → ["1", "2", "3"]
    "5" → ["5"]
    ["1..3", "5", "7..9"] → ["1", "2", "3", "5", "7", "8", "9"]

    Args:
        values: CLI引数のリスト（Noneの場合はNoneを返す）

    Returns:
        展開後のリスト（Noneの場合はNone）
    """
    if values is None:
        return None

    result: list[str] = []
    for v in values:
        # ".." を含む場合は範囲展開
        match = re.fullmatch(r"(\d+)\.\.(\d+)", v)
        if match:
            start = int(match.group(1))
            end = int(match.group(2))
            if start <= end:
                result.extend(str(i) for i in range(start, end + 1))
            else:
                # 逆順の場合も対応（3..1 → 3, 2, 1）
                result.extend(str(i) for i in range(start, end - 1, -1))
        else:
            result.append(v)

    return result
