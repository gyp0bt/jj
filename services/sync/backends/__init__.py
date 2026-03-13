"""同期バックエンド抽象基底クラス

AbstractFileParserの__init_subclass__パターンを踏襲し、
バックエンドを自動登録する。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

from config import IgnoreConfig

from ..models import SyncState


class AbstractSyncBackend(ABC):
    """同期バックエンド基底クラス

    サブクラスは backend_name を定義するだけで自動登録される。
    """

    _registry: ClassVar[dict[str, type[AbstractSyncBackend]]] = {}
    backend_name: ClassVar[str] = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.backend_name:
            AbstractSyncBackend._registry[cls.backend_name] = cls

    @abstractmethod
    def push(
        self,
        source: Path,
        destination: str,
        exclude: IgnoreConfig,
        on_progress: Callable[[str, int], None] | None = None,
    ) -> SyncState:
        """ローカルからリモートへプッシュ

        Args:
            source: ローカルソースディレクトリ
            destination: リモート先パス
            exclude: 除外パターン
            on_progress: 進捗コールバック (file_path, bytes)
        """

    @abstractmethod
    def clone(
        self,
        source: str,
        destination: Path,
        exclude: IgnoreConfig,
        on_progress: Callable[[str, int], None] | None = None,
    ) -> SyncState:
        """リモートからローカルへクローン

        Args:
            source: リモートソースパス
            destination: ローカル先ディレクトリ
            exclude: 除外パターン
            on_progress: 進捗コールバック (file_path, bytes)
        """

    @classmethod
    def get_backend(cls, name: str) -> AbstractSyncBackend:
        """名前でバックエンドインスタンスを取得"""
        backend_cls = cls._registry.get(name)
        if backend_cls is None:
            available = ", ".join(sorted(cls._registry.keys()))
            raise ValueError(f"バックエンド '{name}' が見つかりません。利用可能: {available}")
        return backend_cls()

    @classmethod
    def available_backends(cls) -> list[str]:
        """登録済みバックエンド名一覧"""
        return sorted(cls._registry.keys())
