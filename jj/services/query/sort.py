"""汎用ソート・カラム選択ロジック

vocab辞書に基づくカラムソートと、configパターンに基づく
テーブルカラム選択を提供する。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import fnmatch


def sort_columns_by_vocab(columns: list[str], vocab: dict[str, str]) -> list[str]:
    """vocab順でカラムをソート

    vocab辞書の値（日本語表記）の出現順を優先し、
    vocabに含まれないカラムは文字列昇順で後に配置する。

    Args:
        columns: ソート対象のカラムリスト
        vocab: vocabマッピング

    Returns:
        vocab順 -> 文字列昇順のリスト
    """
    vocab_order: dict[str, int] = {}
    for idx, v in enumerate(vocab.values()):
        if v not in vocab_order:
            vocab_order[v] = idx
    for idx, k in enumerate(vocab.keys()):
        if k not in vocab_order:
            vocab_order[k] = len(vocab) + idx

    in_vocab = [c for c in columns if c in vocab_order]
    not_in_vocab = [c for c in columns if c not in vocab_order]
    in_vocab.sort(key=lambda c: vocab_order[c])
    not_in_vocab.sort()
    return in_vocab + not_in_vocab


def select_table_columns(
    all_columns: list[str],
    table_columns: list[str] | None,
    vocab: dict[str, str] | None = None,
) -> list[str]:
    """config指定に基づいてテーブルカラムをフィルタ・並べ替え

    table_columnsが指定されていない場合はvocab順でソートして返す。

    Args:
        all_columns: DataFrameの全カラム名
        table_columns: config.dashboard.table-columns（globパターン対応）
        vocab: vocabマッピング（vocab順ソート用）

    Returns:
        表示するカラムのリスト（順序付き）
    """
    # 固定カラム（常に先頭に表示）
    fixed = ["name", "type", "format"]

    if table_columns is None:
        # table-columns未指定の場合: 固定カラム + vocab順でソート
        remaining = [c for c in all_columns if c not in fixed]
        if vocab:
            remaining = sort_columns_by_vocab(remaining, vocab)
        result = [c for c in fixed if c in all_columns] + remaining
        return result

    ordered: list[str] = []
    seen: set[str] = set(fixed)

    for pattern in table_columns:
        for col in all_columns:
            if col in seen:
                continue
            if fnmatch.fnmatch(col, pattern) or col == pattern:
                ordered.append(col)
                seen.add(col)

    # 固定カラム（存在するもののみ） + 指定カラム
    result = [c for c in fixed if c in all_columns] + ordered
    return result
