"""ダッシュボードコネクター基盤

ソフトウェア固有のダッシュボードページをプラグインとして追加するための
基底クラスとレジストリを提供する。

各コネクターは `DashboardPageConnector` を継承し、`page_label` を設定すると
自動的にレジストリに登録される。`is_available()` で利用可能性を判定し、
`render_page()` でページ描画を行う。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from services.dashboard.data_provider import DashboardDataProvider


class DashboardPageConnector:
    """ダッシュボードページコネクター基底クラス

    ソフトウェア固有のページ（例: Abaqus物性一覧）をプラグインとして
    追加するための基底クラス。__init_subclass__によりサブクラス定義時に
    自動的にレジストリに登録される。

    Attributes:
        page_label: サイドバーに表示するページ名
        connector_key: コネクタ固有config取得用キー（例: "abaqus"）
        _registry: 登録済みコネクターの辞書 {page_label: connector_class}
    """

    page_label: str = ""
    connector_key: str = ""
    _registry: dict[str, type["DashboardPageConnector"]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.page_label:
            cls._registry[cls.page_label] = cls

    def is_available(self, provider: "DashboardDataProvider") -> bool:
        """このコネクターのページが利用可能か判定

        グラフデータに対応するノードタイプが存在するかで判定する。

        Args:
            provider: DashboardDataProvider

        Returns:
            利用可能な場合True
        """
        return True

    def get_connector_config(self, dashboard_config: Any) -> dict[str, Any]:
        """DashboardConfigからコネクタ固有設定を取得

        Args:
            dashboard_config: DashboardConfig

        Returns:
            コネクタ固有設定の辞書
        """
        if not self.connector_key:
            return {}
        get_fn = getattr(dashboard_config, "get_connector_config", None)
        if get_fn is not None:
            return get_fn(self.connector_key)
        return {}

    def render_page(
        self,
        provider: "DashboardDataProvider",
        dashboard_config: Any,
    ) -> None:
        """ページをレンダリング

        Args:
            provider: DashboardDataProvider
            dashboard_config: DashboardConfig
        """
        raise NotImplementedError


def get_connector_pages(
    provider: "DashboardDataProvider",
) -> list[str]:
    """利用可能なコネクターページのラベル一覧を返す

    Args:
        provider: DashboardDataProvider

    Returns:
        ページラベルのリスト
    """
    pages: list[str] = []
    for label, cls in DashboardPageConnector._registry.items():
        connector = cls()
        if connector.is_available(provider):
            pages.append(label)
    return pages


def render_connector_page(
    page_label: str,
    provider: "DashboardDataProvider",
    dashboard_config: Any,
) -> bool:
    """コネクターページをレンダリング

    Args:
        page_label: ページラベル
        provider: DashboardDataProvider
        dashboard_config: DashboardConfig

    Returns:
        レンダリング成功時True、コネクター未登録時False
    """
    cls = DashboardPageConnector._registry.get(page_label)
    if cls is None:
        return False
    connector = cls()
    connector.render_page(provider, dashboard_config)
    return True
