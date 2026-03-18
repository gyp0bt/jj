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

    vocab辞書のキー（生キー）の定義順を優先し、
    vocabに含まれないカラムは文字列昇順で後に配置する。

    生キーで保存されたプロパティに対して、vocabのキー定義順でソートする。
    vocab値（表示名）でもマッチ可能（後方互換）。

    接頭辞エスケープキー（child_name:key）はベースキー（key部分）で
    vocab照合を試み、ベースキーの直後にソートされる。

    Args:
        columns: ソート対象のカラムリスト（生キー）
        vocab: vocabマッピング（生キー→表示名）

    Returns:
        vocab順 -> 文字列昇順のリスト
    """
    # 生キー順序を構築
    vocab_order: dict[str, int] = {}
    for idx, k in enumerate(vocab.keys()):
        if k not in vocab_order:
            vocab_order[k] = idx
    # vocab値（表示名）でもマッチ可能（後方互換）
    for idx, v in enumerate(vocab.values()):
        if v not in vocab_order:
            vocab_order[v] = len(vocab) + idx

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


def sort_rows_by_index(
    rows: list[dict[str, object]],
    idx_key: str,
    ver_key: str,
) -> list[dict[str, object]]:
    """idx_key と ver_key を int に変換できる場合、(idx, ver) の順で昇順ソート

    どちらのキーも int に変換できる行がない場合は元の順序を維持する。
    bool 値は int 変換の対象外とする。

    Args:
        rows: ソート対象の行リスト
        idx_key: インデックスキー名
        ver_key: バージョンキー名

    Returns:
        ソート済みリスト（ソート不可の場合は元のリストをそのまま返す）
    """
    if not rows:
        return rows

    def _to_int(val: object) -> int | None:
        try:
            if isinstance(val, bool):
                return None
            return int(val)  # type: ignore[arg-type]
        except Exception:
            return None

    # どちらか一方でも int に変換できる行があるか判定
    can_sort = any(_to_int(row.get(idx_key)) is not None or _to_int(row.get(ver_key)) is not None for row in rows)

    if not can_sort:
        return rows

    sentinel = float("inf")

    def _sort_key(row: dict[str, object]) -> tuple[float, float]:
        idx_val = _to_int(row.get(idx_key))
        ver_val = _to_int(row.get(ver_key))
        return (
            idx_val if idx_val is not None else sentinel,
            ver_val if ver_val is not None else sentinel,
        )

    return sorted(rows, key=_sort_key)


def select_table_columns(
    all_columns: list[str],
    table_columns: list[str] | None,
    exclude_table_columns: list[str] | None = None,
    vocab: dict[str, str] | None = None,
) -> list[str]:
    """config指定に基づいてテーブルカラムをフィルタ・並べ替え

    table_columnsが指定されていない場合はvocab順でソートして返す。
    globパターンは接頭辞エスケープキーのベースキー部分にもマッチする。

    Args:
        all_columns: DataFrameの全カラム名
        table_columns: config.dashboard.table-columns（globパターン対応）
        exclude_table_columns: 表示から除外したいカラム名リスト
        vocab: vocabマッピング（vocab順ソート用）

    Returns:
        表示するカラムのリスト（順序付き）
    """
    # 固定カラム（常に先頭に表示）
    if table_columns is None:
        fixed = ["name", "type", "format"]
    else:
        fixed = []
    exclude_set: set[str] = set(exclude_table_columns or [])

    if table_columns is None:
        # table-columns未指定の場合: 固定カラム + vocab順でソート
        remaining = [c for c in all_columns if c not in fixed and c not in exclude_set]
        if vocab:
            remaining = sort_columns_by_vocab(remaining, vocab)
        result = [c for c in fixed if c in all_columns and c not in exclude_set] + remaining
        return result

    ordered: list[str] = []
    # 既に確定した固定カラムと除外対象はスキップ対象にする
    seen: set[str] = set(fixed) | exclude_set

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
    result = [c for c in fixed if c in all_columns and c not in exclude_set] + ordered
    return result
