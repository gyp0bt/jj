"""Vocab表示時変換ユーティリティ

parse時に生キーで保存されたプロパティを、
表示時（ダッシュボード・CLI・エクスポート）にvocab変換する。

vocabはparse時には適用せず、表示時のみ適用する設計。
これによりgraph.yamlは常に生キーで保存され、
vocab変更時に過去データとの互換性が維持される。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

from typing import Any


def translate_key(key: str, vocab: dict[str, str]) -> str:
    """キーをvocab変換する（表示用）"""
    return vocab.get(key, key)


def translate_value(value: Any, vocab: dict[str, str]) -> Any:
    """値にvocab変換を適用する（表示用）

    - 文字列: vocabで変換
    - 辞書: キーと値を再帰的に変換
    - リスト: 各要素を再帰的に変換
    - その他: そのまま
    """
    if isinstance(value, str):
        return vocab.get(value, value)
    if isinstance(value, dict):
        return translate_properties(value, vocab)
    if isinstance(value, list):
        return [translate_value(item, vocab) for item in value]
    return value


def translate_properties(props: dict[str, Any], vocab: dict[str, str]) -> dict[str, Any]:
    """プロパティ辞書のキーと文字列値をvocab変換する（表示用）"""
    result: dict[str, Any] = {}
    for key, value in props.items():
        translated_key = vocab.get(key, key)
        translated_value = translate_value(value, vocab)
        result[translated_key] = translated_value
    return result


def translate_columns(columns: list[str], vocab: dict[str, str]) -> list[str]:
    """カラム名リストをvocab変換する（表示用）"""
    return [vocab.get(col, col) for col in columns]


def reverse_vocab(vocab: dict[str, str]) -> dict[str, str]:
    """vocabの逆引き辞書を構築する

    変換後キー → 変換前キーのマッピング。
    表示キーから生キーを取得する際に使用。
    """
    return {v: k for k, v in vocab.items()}
