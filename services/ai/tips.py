"""Tips — プロジェクトファイルからTips/知見を抽出・蓄積・表示

ファイルやログからAIで有用なTipsを抽出し、.j2/storage/tips.json に蓄積する。
蓄積されたTipsはランダム表示やキーワード検索で参照できる。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

import json
import logging
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.ai import require_provider

logger = logging.getLogger(__name__)

# Tips抽出用プロンプト
TIPS_EXTRACT_PROMPT = (
    "あなたはソフトウェアエンジニアリングのTips抽出アシスタントです。\n"
    "与えられたテキストから、他の開発者に役立つTips・知見・ベストプラクティスを抽出してください。\n"
    "各Tipは以下のJSON配列形式で出力してください:\n"
    '[{"title": "短いタイトル", "body": "詳細説明（1-3文）", "tags": ["タグ1", "タグ2"]}]\n'
    "Tipsがない場合は空配列 [] を返してください。\n"
    "JSONのみを出力し、他のテキストは含めないでください。"
)

# ファイルサイズ制限
MAX_FILE_SIZE_BYTES = 100_000


class TipsStore:
    """Tips蓄積ストア。

    .j2/storage/tips.json に永続化する。
    """

    def __init__(self, storage_path: Path | None = None) -> None:
        self._storage_path = storage_path
        self._tips: list[dict[str, Any]] = []

    @property
    def size(self) -> int:
        return len(self._tips)

    def save(self, path: Path | None = None) -> None:
        save_path = path or self._storage_path
        if save_path is None:
            raise ValueError("保存先パスが指定されていません。")
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(self._tips, f, ensure_ascii=False, indent=2)

    def load(self, path: Path | None = None) -> None:
        load_path = path or self._storage_path
        if load_path is None or not load_path.exists():
            return
        with open(load_path, encoding="utf-8") as f:
            self._tips = json.load(f)

    def add_tip(self, title: str, body: str, tags: list[str] | None = None, source: str = "") -> dict[str, Any]:
        """Tipを追加する。"""
        tip = {
            "id": len(self._tips) + 1,
            "title": title,
            "body": body,
            "tags": tags or [],
            "source": source,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._tips.append(tip)
        return tip

    def get_random(self, count: int = 1) -> list[dict[str, Any]]:
        """ランダムにTipsを取得する。"""
        if not self._tips:
            return []
        return random.sample(self._tips, min(count, len(self._tips)))

    def search(self, keyword: str) -> list[dict[str, Any]]:
        """キーワードでTipsを検索する。"""
        keyword_lower = keyword.lower()
        results = []
        for tip in self._tips:
            if (
                keyword_lower in tip.get("title", "").lower()
                or keyword_lower in tip.get("body", "").lower()
                or any(keyword_lower in tag.lower() for tag in tip.get("tags", []))
            ):
                results.append(tip)
        return results

    def list_all(self) -> list[dict[str, Any]]:
        """全Tipsを返す。"""
        return list(self._tips)


def extract_tips_from_file(file_path: Path, **kwargs: Any) -> list[dict[str, Any]]:
    """ファイルからAIでTipsを抽出する。

    Args:
        file_path: 対象ファイル
        **kwargs: AIProviderに渡す追加パラメータ

    Returns:
        抽出されたTipsのリスト [{"title": str, "body": str, "tags": list[str]}]
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
    messages = [
        {"role": "system", "content": TIPS_EXTRACT_PROMPT},
        {"role": "user", "content": f"=== {file_path.name} ===\n\n{content}"},
    ]
    response = provider.chat(messages, **kwargs)

    return _parse_tips_response(response)


def extract_tips_from_text(text: str, **kwargs: Any) -> list[dict[str, Any]]:
    """テキストからAIでTipsを抽出する。"""
    if not text.strip():
        return []

    provider = require_provider()
    messages = [
        {"role": "system", "content": TIPS_EXTRACT_PROMPT},
        {"role": "user", "content": text},
    ]
    response = provider.chat(messages, **kwargs)

    return _parse_tips_response(response)


def _parse_tips_response(response: str) -> list[dict[str, Any]]:
    """AIレスポンスからTipsをパースする。"""
    response = response.strip()
    # ```json ... ``` のフェンスを除去
    if response.startswith("```"):
        lines = response.split("\n")
        # 最初の行（```json等）と最後の行（```）を除去
        lines = [line for line in lines if not line.strip().startswith("```")]
        response = "\n".join(lines)

    try:
        tips = json.loads(response)
        if not isinstance(tips, list):
            return []
        result = []
        for tip in tips:
            if isinstance(tip, dict) and "title" in tip and "body" in tip:
                result.append(
                    {
                        "title": str(tip["title"]),
                        "body": str(tip["body"]),
                        "tags": [str(t) for t in tip.get("tags", [])],
                    }
                )
        return result
    except (json.JSONDecodeError, TypeError):
        logger.warning("Tips応答のパースに失敗: %s", response[:200])
        return []
