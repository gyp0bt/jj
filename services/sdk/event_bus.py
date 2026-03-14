"""EventBus — シンプルなPub/Subイベントバス

プラグインはイベントを購読し、コアやプラグインが発行する
イベントに反応して処理を行う。

同期実行。スレッドセーフ性は考慮しない（シングルスレッド前提）。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from services.sdk.events import Event

logger = logging.getLogger(__name__)


class EventBus:
    """シンプルなPub/Subイベントバス

    プラグインはイベントを購読し、コアやプラグインが発行する
    イベントに反応して処理を行う。
    同期実行。スレッドセーフ性は考慮しない（シングルスレッド前提）。
    """

    def __init__(self) -> None:
        self._handlers: dict[type[Event], list[Callable[[Any], None]]] = defaultdict(list)

    def subscribe(self, event_type: type[Event], handler: Callable[[Any], None]) -> None:
        """イベントハンドラを登録する

        Args:
            event_type: 購読するイベントクラス
            handler: イベント発行時に呼ばれるコールバック
        """
        self._handlers[event_type].append(handler)
        logger.debug(f"イベントハンドラを登録: {event_type.__name__} -> {handler.__name__}")

    def unsubscribe(self, event_type: type[Event], handler: Callable[[Any], None]) -> bool:
        """イベントハンドラを解除する

        Args:
            event_type: 解除するイベントクラス
            handler: 解除するコールバック

        Returns:
            解除に成功した場合True
        """
        handlers = self._handlers.get(event_type, [])
        try:
            handlers.remove(handler)
            return True
        except ValueError:
            return False

    def publish(self, event: Event) -> None:
        """イベントを発行し、全ハンドラを同期実行する

        ハンドラ内で例外が発生しても他のハンドラの実行は継続する。

        Args:
            event: 発行するイベント
        """
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.warning(f"イベントハンドラ実行失敗: {event_type.__name__}: {handler.__name__}: {e}")

    def clear(self) -> None:
        """全ハンドラをクリアする（テスト用）"""
        self._handlers.clear()

    @property
    def handler_count(self) -> int:
        """登録済みハンドラの総数"""
        return sum(len(h) for h in self._handlers.values())
