"""AI連携サービス — AIProviderプロトコルと共通インターフェース

AIProviderプロトコルをコア層で定義し、
OllamaProvider等のプロバイダ実装はプラグインとして分離する。

プロバイダ未設定時はgraceful skip（AI機能は無効化されるが、他機能に影響しない）。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AIProvider(Protocol):
    """AI プロバイダのプロトコル定義。

    chat(), summarize() を提供する。
    embed() はRAGフェーズ(T7-4)で追加予定。
    """

    @property
    def name(self) -> str:
        """プロバイダ名（例: "ollama", "openai"）"""
        ...

    @property
    def available(self) -> bool:
        """プロバイダが利用可能かどうか"""
        ...

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """チャット形式のメッセージを送信し、応答テキストを返す。

        Args:
            messages: [{"role": "user"|"system"|"assistant", "content": "..."}]
            **kwargs: モデル固有パラメータ（temperature, max_tokens等）

        Returns:
            応答テキスト
        """
        ...

    def summarize(self, text: str, **kwargs: Any) -> str:
        """テキストの要約を生成する。

        Args:
            text: 要約対象テキスト
            **kwargs: プロンプト上書き等

        Returns:
            要約テキスト
        """
        ...


# グローバルプロバイダレジストリ
_provider: AIProvider | None = None


def get_provider() -> AIProvider | None:
    """現在登録されているAIProviderを返す。未登録時はNone。"""
    return _provider


def set_provider(provider: AIProvider) -> None:
    """AIProviderを登録する。"""
    global _provider
    _provider = provider


def require_provider() -> AIProvider:
    """AIProviderを取得し、未設定時はValueErrorを送出する。"""
    p = get_provider()
    if p is None:
        raise ValueError(
            "AIプロバイダが設定されていません。\n"
            "  pip install jj[ollama] でOllamaプロバイダをインストールし、\n"
            "  config.yamlのai.providerを設定してください。"
        )
    if not p.available:
        raise ValueError(
            f"AIプロバイダ '{p.name}' は現在利用できません。\n  サーバーが起動しているか確認してください。"
        )
    return p


__all__ = [
    "AIProvider",
    "get_provider",
    "require_provider",
    "set_provider",
]
