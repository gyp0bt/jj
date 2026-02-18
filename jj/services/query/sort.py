"""汎用ソート・カラム選択ロジック

vocab辞書に基づくカラムソートと、configパターンに基づく
テーブルカラム選択を提供する。

接頭辞エスケープキー（{child_name}:{key}）への対応:
- MeshInheritParserがキー競合時に生成する「mesh_t50:mesh_node_count」形式
- vocab照合時に「:」以降のベースキーでもマッチを試みる
- ソート順はベースキーの直後に配置される

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import fnmatch


def get_base_key(column: str) -> str:
    """接頭辞エスケープキーからベースキーを取得

    「child_name:key」形式の場合「key」を返す。
    「:」を含まない場合はそのまま返す。

    Args:
        column: カラム名

    Returns:
        ベースキー
    """
    if ":" in column:
        return column.split(":", 1)[1]
    return column


def sort_columns_by_vocab(columns: list[str], vocab: dict[str, str]) -> list[str]:
    """vocab順でカラムをソート

    vocab辞書の値（日本語表記）の出現順を優先し、
    vocabに含まれないカラムは文字列昇順で後に配置する。

    接頭辞エスケープキー（child_name:key）はベースキー（key部分）で
    vocab照合を試み、ベースキーの直後にソートされる。

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

    max_order = len(vocab_order) + len(vocab)

    def _sort_key(col: str) -> tuple[int, int, str]:
        """(vocab順位, 接頭辞有無フラグ, カラム名) のソートキー"""
        if col in vocab_order:
            return (vocab_order[col], 0, col)
        base = get_base_key(col)
        if base != col and base in vocab_order:
            # 接頭辞付きキー: ベースキーの直後に配置
            return (vocab_order[base], 1, col)
        # vocab外: 大きい数値で後方配置、文字列昇順
        return (max_order, 0, col)

    return sorted(columns, key=_sort_key)


def select_table_columns(
    all_columns: list[str],
    table_columns: list[str] | None,
    vocab: dict[str, str] | None = None,
) -> list[str]:
    """config指定に基づいてテーブルカラムをフィルタ・並べ替え

    table_columnsが指定されていない場合はvocab順でソートして返す。
    globパターンは接頭辞エスケープキーのベースキー部分にもマッチする。

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
            # 完全一致 or globマッチ（フルキー）
            if fnmatch.fnmatch(col, pattern) or col == pattern:
                ordered.append(col)
                seen.add(col)
            else:
                # 接頭辞エスケープキーのベースキーでもマッチを試みる
                base = get_base_key(col)
                if base != col and (fnmatch.fnmatch(base, pattern) or base == pattern):
                    ordered.append(col)
                    seen.add(col)

    # 固定カラム（存在するもののみ） + 指定カラム
    result = [c for c in fixed if c in all_columns] + ordered
    return result
