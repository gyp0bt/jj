"""表示名生成パーサー

VocabFinalizer(priority=100)の後に実行し、
verbose_name_formatテンプレートからgo_ノードの表示名を生成する。

verbose_name_formatが未設定の場合はスキップ。
既にverbose_nameプロパティが存在するノードも上書きする
（フォーマットテンプレートが明示的に設定されている場合）。

priority=101: VocabFinalizer直後に実行（vocab変換済みキーで展開）。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph


class DisplayNameParser(AbstractFileParser):
    """verbose_name_formatからgo_ノードの表示名を生成するパーサー

    VocabFinalizer後に実行し、vocab変換済みのプロパティキーを使って
    verbose_name_formatテンプレートを展開する。

    展開結果はverbose_nameキー（vocab変換後）に格納される。
    テンプレート内の{キー名}はvocab変換前・変換後どちらでも参照可能。
    """

    priority = 101

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        verbose_name_format = graph.config.verbose_name_format
        if not verbose_name_format:
            return graph

        vocab = graph.config.vocab
        # verbose_nameのvocab変換後キー名を特定（例: "表示名"）
        vn_key = vocab.get("verbose_name", "verbose_name")

        for node in graph.nodes:
            name_lower = node.name.lower()
            if not (name_lower.startswith("go_") or name_lower == "go"):
                continue

            display_name = _apply_verbose_name_format(verbose_name_format, node.properties, vocab)
            if display_name:
                node.properties[vn_key] = display_name

        return graph


def _apply_verbose_name_format(
    fmt: str,
    properties: dict[str, Any],
    vocab: dict[str, str],
) -> str:
    """verbose_name_formatテンプレートをプロパティ値で展開

    テンプレート内の{キー名}をプロパティ値で置換する。
    vocabの変換前・変換後どちらのキー名でも参照可能。
    存在しないキーは空文字に置換される。

    Args:
        fmt: フォーマットテンプレート（例: "条件{idx}(高さ{t})"）
        properties: ノードプロパティ（vocab変換済み）
        vocab: vocabマッピング

    Returns:
        フォーマット適用後の表示名
    """
    # プロパティ値の辞書を構築
    values: dict[str, str] = {}
    for key, value in properties.items():
        if key in ("path", "include_properties"):
            continue
        if isinstance(value, (list, dict)):
            continue
        values[key] = str(value)

    # vocab変換前のキー名でも参照可能にする
    # （例: {idx}と書いてあるが、propsでは"条件"キーになっている場合）
    for orig_key, translated_key in vocab.items():
        if translated_key in values and orig_key not in values:
            values[orig_key] = values[translated_key]
    # vocab変換後のキーでも参照可能にする
    # （例: {高さ}と書いてあるが、propsでは"t"キーになっている場合）
    for orig_key, translated_key in vocab.items():
        if orig_key in values and translated_key not in values:
            values[translated_key] = values[orig_key]

    safe_values = defaultdict(str, values)
    return fmt.format_map(safe_values)
