"""OllamaProvider — Ollama APIを使用したAIProvider実装

Ollamaのローカルサーバー (http://localhost:11434) と通信し、
chat/summarize機能を提供する。

依存: httpリクエスト用にurllibのみ使用（追加パッケージ不要）。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

# デフォルト設定
DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.1:8b"
DEFAULT_EMBED_MODEL = "nomic-embed-text"

# 要約用プロンプト
SUMMARIZE_SYSTEM_PROMPT = (
    "あなたは技術文書の要約アシスタントです。"
    "与えられたテキストを簡潔に要約してください。"
    "重要なポイントを箇条書きで示し、全体を3〜5文で要約してください。"
    "日本語で回答してください。"
)

DIFF_SYSTEM_PROMPT = (
    "あなたはコードレビューアシスタントです。"
    "与えられたdiff（差分）を分析し、以下の形式で要約してください:\n"
    "1. 変更の概要（1〜2文）\n"
    "2. 主な変更点（箇条書き）\n"
    "3. 潜在的な影響やリスク（あれば）\n"
    "日本語で回答してください。"
)


class OllamaProvider:
    """Ollama APIを使用したAIProvider実装。

    urllib.requestでOllamaのREST APIと通信する。
    外部パッケージへの追加依存なし。
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        embed_model: str = DEFAULT_EMBED_MODEL,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._embed_model = embed_model

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def available(self) -> bool:
        """Ollamaサーバーに接続可能かチェックする。"""
        try:
            req = urllib.request.Request(f"{self._base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except (urllib.error.URLError, OSError, TimeoutError):
            return False

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Ollama /api/chat エンドポイントを呼び出す。"""
        model = kwargs.pop("model", self._model)
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            **kwargs,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self._base_url}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("message", {}).get("content", "")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            logger.error("Ollama API error: %s %s — %s", e.code, e.reason, body)
            raise ValueError(f"Ollama APIエラー: {e.code} {e.reason}") from e
        except (urllib.error.URLError, OSError) as e:
            raise ValueError(f"Ollamaサーバーに接続できません ({self._base_url}): {e}") from e

    def summarize(self, text: str, **kwargs: Any) -> str:
        """テキストを要約する。"""
        system_prompt = kwargs.pop("system_prompt", SUMMARIZE_SYSTEM_PROMPT)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]
        return self.chat(messages, **kwargs)

    def embed(self, text: str, **kwargs: Any) -> list[float]:
        """Ollama /api/embed エンドポイントでテキストの埋め込みベクトルを生成する。"""
        model = kwargs.pop("model", self._embed_model)
        payload = {"model": model, "input": text, **kwargs}

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self._base_url}/api/embed",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                embeddings = result.get("embeddings", [])
                if embeddings:
                    return embeddings[0]
                return []
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            logger.error("Ollama embed error: %s %s — %s", e.code, e.reason, body)
            raise ValueError(f"Ollama embed APIエラー: {e.code} {e.reason}") from e
        except (urllib.error.URLError, OSError) as e:
            raise ValueError(f"Ollamaサーバーに接続できません ({self._base_url}): {e}") from e


def create_provider_from_config(ai_config: dict[str, Any]) -> OllamaProvider | None:
    """config.yamlのai設定からOllamaProviderを生成する。

    Args:
        ai_config: config.yamlの "ai" セクション

    Returns:
        OllamaProvider or None (provider == "disabled" 時)
    """
    provider_type = ai_config.get("provider", "disabled")
    if provider_type == "disabled":
        return None

    if provider_type == "ollama":
        ollama_config = ai_config.get("ollama", {})
        return OllamaProvider(
            base_url=ollama_config.get("base_url", DEFAULT_BASE_URL),
            model=ollama_config.get("model", DEFAULT_MODEL),
            embed_model=ollama_config.get("embed_model", DEFAULT_EMBED_MODEL),
        )

    logger.warning("未知のAIプロバイダ: %s（ollamaのみ対応）", provider_type)
    return None
