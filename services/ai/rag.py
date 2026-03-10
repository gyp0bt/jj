"""簡易RAG — embedding + コサイン類似度による検索

プロジェクト内のファイルをチャンク分割し、ベクトル埋め込みでインデックス化。
質問に対して関連チャンクを検索し、AIに文脈付きで回答させる。

ストレージ: .j2/storage/rag_index.json にローカル永続化。
numpy依存: コサイン類似度計算に使用（コア依存に含まれる）。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any

from services.ai import require_provider

logger = logging.getLogger(__name__)

# デフォルト設定
DEFAULT_CHUNK_SIZE = 500  # 文字数
DEFAULT_CHUNK_OVERLAP = 50  # 重複文字数
DEFAULT_TOP_K = 5  # 検索結果上位件数
MAX_FILE_SIZE_BYTES = 200_000  # 200KB

# RAG用プロンプト
RAG_SYSTEM_PROMPT = (
    "あなたはプロジェクト内ファイルの知識を持つアシスタントです。\n"
    "以下のコンテキスト（プロジェクト内ファイルからの抜粋）を参照して、"
    "ユーザーの質問に正確に回答してください。\n"
    "コンテキストに含まれない情報については「コンテキストに該当情報がありません」と回答してください。\n"
    "日本語で回答してください。"
)


def chunk_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> list[str]:
    """テキストをチャンクに分割する。

    行境界を尊重しつつ、chunk_size文字程度で分割する。

    Args:
        text: 分割対象テキスト
        chunk_size: チャンクあたりの目標文字数
        overlap: チャンク間の重複文字数

    Returns:
        チャンクのリスト
    """
    if not text.strip():
        return []

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)

        # 行境界で切断する（chunk_sizeを少し超えてもOK）
        if end < text_len:
            newline_pos = text.rfind("\n", start, end)
            if newline_pos > start:
                end = newline_pos + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap if end < text_len else text_len

    return chunks


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """コサイン類似度を計算する（numpy不要の純Python実装）。"""
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class RagIndex:
    """簡易RAGインデックス。

    チャンク化されたテキストとその埋め込みベクトルを管理する。
    .j2/storage/rag_index.json に永続化する。
    """

    def __init__(self, storage_path: Path | None = None) -> None:
        self._storage_path = storage_path
        self._entries: list[dict[str, Any]] = []
        # entries: [{"file": str, "chunk_index": int, "text": str, "embedding": list[float]}]

    @property
    def size(self) -> int:
        return len(self._entries)

    @property
    def indexed_files(self) -> list[str]:
        return sorted(set(e["file"] for e in self._entries))

    def save(self, path: Path | None = None) -> None:
        """インデックスをJSONファイルに永続化する。"""
        save_path = path or self._storage_path
        if save_path is None:
            raise ValueError("保存先パスが指定されていません。")
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(self._entries, f, ensure_ascii=False)
        logger.info("RAGインデックスを保存: %s (%d エントリ)", save_path, len(self._entries))

    def load(self, path: Path | None = None) -> None:
        """JSONファイルからインデックスを復元する。"""
        load_path = path or self._storage_path
        if load_path is None or not load_path.exists():
            return
        with open(load_path, encoding="utf-8") as f:
            self._entries = json.load(f)
        logger.info("RAGインデックスを復元: %s (%d エントリ)", load_path, len(self._entries))

    def add_file(
        self,
        file_path: Path,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> int:
        """ファイルをチャンク化し、埋め込みベクトル付きでインデックスに追加する。

        Args:
            file_path: インデックス対象ファイル
            chunk_size: チャンクサイズ
            overlap: 重複文字数

        Returns:
            追加されたチャンク数

        Raises:
            FileNotFoundError: ファイルが存在しない
            ValueError: AIプロバイダ未設定、ファイルが大きすぎる
        """
        if not file_path.exists():
            raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

        size = file_path.stat().st_size
        if size > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"ファイルが大きすぎます ({size:,} bytes): {file_path}")

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            raise ValueError(f"テキストとして読み込めません: {file_path}") from e

        provider = require_provider()
        file_str = str(file_path)

        # 既存エントリを削除（再インデックス）
        self._entries = [e for e in self._entries if e["file"] != file_str]

        chunks = chunk_text(content, chunk_size=chunk_size, overlap=overlap)
        added = 0
        for i, chunk in enumerate(chunks):
            embedding = provider.embed(chunk)
            self._entries.append(
                {
                    "file": file_str,
                    "chunk_index": i,
                    "text": chunk,
                    "embedding": embedding,
                }
            )
            added += 1

        return added

    def remove_file(self, file_path: Path) -> int:
        """指定ファイルのエントリをインデックスから削除する。"""
        file_str = str(file_path)
        before = len(self._entries)
        self._entries = [e for e in self._entries if e["file"] != file_str]
        removed = before - len(self._entries)
        return removed

    def search(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[dict[str, Any]]:
        """クエリに類似するチャンクを検索する。

        Args:
            query: 検索クエリ
            top_k: 返す結果の上位件数

        Returns:
            [{"file": str, "chunk_index": int, "text": str, "score": float}]
        """
        if not self._entries:
            return []

        provider = require_provider()
        query_embedding = provider.embed(query)

        if not query_embedding:
            return []

        scored = []
        for entry in self._entries:
            emb = entry.get("embedding", [])
            if not emb:
                continue
            score = _cosine_similarity(query_embedding, emb)
            scored.append(
                {
                    "file": entry["file"],
                    "chunk_index": entry["chunk_index"],
                    "text": entry["text"],
                    "score": score,
                }
            )

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]


def rag_query(
    query: str,
    index: RagIndex,
    top_k: int = DEFAULT_TOP_K,
    **kwargs: Any,
) -> str:
    """RAG検索 + AI回答を実行する。

    Args:
        query: ユーザーの質問
        index: RagIndex インスタンス
        top_k: 検索結果上位件数
        **kwargs: AIProviderに渡す追加パラメータ

    Returns:
        AI回答テキスト
    """
    results = index.search(query, top_k=top_k)

    if not results:
        return "インデックスにデータがありません。`jj ai index <file>` でファイルをインデックスしてください。"

    # コンテキスト構築
    context_parts = []
    for r in results:
        context_parts.append(f"--- {r['file']} (chunk {r['chunk_index']}, score {r['score']:.3f}) ---\n{r['text']}")
    context = "\n\n".join(context_parts)

    provider = require_provider()
    messages = [
        {"role": "system", "content": RAG_SYSTEM_PROMPT},
        {"role": "user", "content": f"## コンテキスト\n\n{context}\n\n## 質問\n\n{query}"},
    ]
    return provider.chat(messages, **kwargs)
