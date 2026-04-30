"""Ollamaプラグイン — OllamaProviderの登録

pip install jj[ollama] で有効化。
config.yamlのai.provider: "ollama" で使用開始。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def register() -> None:
    """Ollamaプラグインを登録する。

    config.yamlのai設定を読み取り、provider == "ollama" の場合に
    OllamaProviderを生成してAIProviderレジストリに登録する。
    """
    try:
        from config import load_project_config
        from services.ai import set_provider
        from services.ai.provider import create_provider_from_config

        config = load_project_config()
        ai_config = config.get("ai", {})

        provider = create_provider_from_config(ai_config)
        if provider is not None:
            # set_provider(provider)
            # logger.debug("OllamaProvider registered: %s", provider._base_url)
            pass
    except Exception:
        # プラグイン登録失敗は警告のみ（他の機能に影響させない）
        logger.debug("Ollamaプラグイン登録スキップ", exc_info=True)
