"""Vocab最終置換パーサー

全パーサーが実行された後に、全ノードのプロパティに対して
config.vocabの置換を一括適用する。

JsonPropertyParser、ResultParser、MeshParser等のパーサーが
追加したプロパティは、file_to_node()のvocab置換を経由しないため、
この最終パスで漏れなく置換する。

priority=100: 全パーサー（enrichment_filter含む）の後に実行。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph


class VocabFinalizer(AbstractFileParser):
    """全ノードプロパティにvocab置換を一括適用する最終パスパーサー

    実行タイミング: 全パーサーの最後（priority=100）
    処理内容:
    - 各ノードのpropertiesのキーをvocabで変換
    - 各ノードのpropertiesの文字列値をvocabで変換
    - ネストされた辞書のキーも再帰的に変換

    既にvocab変換済みのキー/値は、vocabに該当がないため
    そのまま保持される（二重変換の心配なし）。
    """

    priority = 100

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        vocab = graph.config.vocab
        if not vocab:
            return graph

        for node in graph.nodes:
            node.properties = _apply_vocab_to_dict(node.properties, vocab)

        return graph


def _apply_vocab_to_dict(d: dict[str, Any], vocab: dict[str, str]) -> dict[str, Any]:
    """辞書のキーと文字列値にvocab置換を再帰的に適用する

    Args:
        d: 対象の辞書
        vocab: 置換マッピング

    Returns:
        置換後の辞書
    """
    result: dict[str, Any] = {}
    for key, value in d.items():
        translated_key = vocab.get(key, key)
        translated_value = _apply_vocab_to_value(value, vocab)
        result[translated_key] = translated_value
    return result


def _apply_vocab_to_value(value: Any, vocab: dict[str, str]) -> Any:
    """値にvocab置換を適用する

    - 文字列: vocabで変換
    - 辞書: キーと値を再帰的に変換
    - リスト: 各要素を再帰的に変換
    - その他: そのまま
    """
    if isinstance(value, str):
        return vocab.get(value, value)
    if isinstance(value, dict):
        return _apply_vocab_to_dict(value, vocab)
    if isinstance(value, list):
        return [_apply_vocab_to_value(item, vocab) for item in value]
    return value
