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
import re


def get_file_base_name(filename: str) -> str:
    """ファイル名からversion/index修飾子を除去してベース名を返す

    末尾の ``_v{N}`` や ``_idx{N}`` を除去し、正規化されたベース名を返す。
    バージョン/インデックスでない修飾子（``_fine``, ``_coarse`` 等）はそのまま保持する。

    Examples:
        >>> get_file_base_name("mesh_v2")
        'mesh'
        >>> get_file_base_name("mesh_v3")
        'mesh'
        >>> get_file_base_name("mesh_idx1")
        'mesh'
        >>> get_file_base_name("mesh_idx2")
        'mesh'
        >>> get_file_base_name("mesh_fine")
        'mesh_fine'
        >>> get_file_base_name("step_v10_idx3")
        'step_v10'

    Args:
        filename: ファイル名（拡張子なし）

    Returns:
        バージョン/インデックス修飾子を除去したベース名
    """
    return re.sub(r"_(v\d+|idx\d+)$", "", filename)


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


# 内部マーカー: graph.yamlの内部用フィールド（テーブル表示には不要）
_INTERNAL_EXCLUDES: frozenset[str] = frozenset({"id", "_ext_keys", "related_files"})

# 正規化キー → ファイル名トークンキーの対応（重複検出用）
# 両方が存在する場合、トークン側を優先してnormalizedを除外する
_NORMALIZED_TO_TOKEN: dict[str, str] = {
    "index": "idx",
    "version": "v",
}


def _auto_dedup_excludes(all_columns: list[str], explicit_exclude: set[str]) -> set[str]:
    """正規化キーと同義のトークンキーが両方存在する場合、正規化側を自動除外

    例: `idx` と `index` が両方ある場合、`index` を除外（`idx` の vocab表示を優先）。
    ユーザーが exclude-table-columns で明示的にどちらかを除外指定している場合は
    自動除外を発動しない（ユーザー意図を尊重）。
    """
    auto: set[str] = set()
    cols = set(all_columns)
    for normalized, token in _NORMALIZED_TO_TOKEN.items():
        if normalized not in cols or token not in cols:
            continue
        # ユーザーが片方を明示除外している場合はそちらに任せる
        if normalized in explicit_exclude or token in explicit_exclude:
            continue
        auto.add(normalized)
    return auto


def select_table_columns(
    all_columns: list[str],
    table_columns: list[str] | None,
    exclude_table_columns: list[str] | None = None,
    vocab: dict[str, str] | None = None,
) -> list[str]:
    """config指定に基づいてテーブルカラムをフィルタ・並べ替え

    table_columnsが指定されていない場合はvocab順でソートして返す。
    globパターンは接頭辞エスケープキーのベースキー部分にもマッチする。

    内部マーカー（``_ext_keys`` 等）は常に除外される。
    また、正規化キー（``index``/``version``）とそのトークン形（``idx``/``v``）が
    両方存在する場合は、トークン形を優先して正規化キーを自動除外する。

    Args:
        all_columns: DataFrameの全カラム名
        table_columns: config.dashboard.table-columns（globパターン対応）
        exclude_table_columns: 表示から除外したいカラム名リスト
        vocab: vocabマッピング（vocab順ソート用）

    Returns:
        表示するカラムのリスト（順序付き）
    """
    # 固定カラム（常に先頭に表示）
    fixed = ["name", "type", "format"]
    explicit_exclude: set[str] = set(exclude_table_columns or [])
    auto_exclude = _auto_dedup_excludes(all_columns, explicit_exclude)
    exclude_set: set[str] = explicit_exclude | _INTERNAL_EXCLUDES | auto_exclude

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
