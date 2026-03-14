"""ダッシュボードコネクター基盤

ソフトウェア固有のダッシュボードページをプラグインとして追加するための
基底クラスとレジストリを提供する。

各コネクターは `DashboardPageConnector` を継承し、`page_label` を設定すると
自動的にレジストリに登録される。`is_available()` で利用可能性を判定し、
`render_page()` でページ描画を行う。

`render_saved_view()` と `generate_html()` によりビュー保存およびHTMLエクスポートに
対応する。SavedViewConfigのview_typeに "connector:{page_label}" を指定することで
保存済みビューとして利用できる。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from config import SavedViewConfig
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
    _registry: ClassVar[dict[str, type[DashboardPageConnector]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.page_label:
            cls._registry[cls.page_label] = cls

    def is_available(self, provider: DashboardDataProvider) -> bool:
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
        provider: DashboardDataProvider,
        dashboard_config: Any,
    ) -> None:
        """ページをレンダリング

        Args:
            provider: DashboardDataProvider
            dashboard_config: DashboardConfig
        """
        raise NotImplementedError

    def render_saved_view(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: Any,
    ) -> None:
        """保存済みビューとしてレンダリング

        デフォルト実装はrender_page()に委譲する。
        サブクラスでオーバーライドしてビュー固有の表示を行える。

        Args:
            provider: DashboardDataProvider
            view: SavedViewConfig（local_filters, connector_config等を参照可能）
            dashboard_config: DashboardConfig
        """
        self.render_page(provider, dashboard_config)

    def get_page_data(
        self,
        provider: DashboardDataProvider,
        dashboard_config: Any,
    ) -> dict[str, Any]:
        """フレームワーク非依存のページデータを返す

        Streamlitに依存しないJSON-serializable なデータ辞書を返す。
        APIからはそのままJSON応答として返却でき、
        CLIからはテーブルやYAMLとして出力できる。

        サブクラスでオーバーライドして実際のデータを返す。
        デフォルト実装は空辞書を返す。

        Args:
            provider: DashboardDataProvider
            dashboard_config: DashboardConfig

        Returns:
            JSON-serializableなデータ辞書
        """
        return {}

    def generate_html(
        self,
        provider: DashboardDataProvider,
        dashboard_config: Any,
    ) -> str:
        """ページのHTML断片を生成（HTMLエクスポート用）

        Streamlit非依存。サブクラスがオーバーライドする。

        Args:
            provider: DashboardDataProvider
            dashboard_config: DashboardConfig

        Returns:
            HTML断片文字列。未対応の場合は空文字列。
        """
        return ""

    def generate_saved_view_html(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: Any,
    ) -> str:
        """保存済みビューのHTML断片を生成

        デフォルト実装はgenerate_html()に委譲する。

        Args:
            provider: DashboardDataProvider
            view: SavedViewConfig
            dashboard_config: DashboardConfig

        Returns:
            HTML断片文字列。未対応の場合は空文字列。
        """
        return self.generate_html(provider, dashboard_config)

    @classmethod
    def get_connector_config_schema(cls) -> list[dict[str, Any]]:
        """connector_configの入力フィールド定義を返す

        サブクラスでオーバーライドし、保存済みビューの
        connector_config編集UIに使用するフィールドを宣言する。

        Returns:
            フィールド定義のリスト。各要素は以下のキーを持つ:
            - key: connector_configのキー名（str）
            - label: UI表示ラベル（str）
            - type: フィールド型 "text" | "checkbox"（str）
            - help: 補足説明（str、optional）
        """
        return []


def get_connector_pages(
    provider: DashboardDataProvider,
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
    provider: DashboardDataProvider,
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


def render_connector_saved_view(
    page_label: str,
    provider: DashboardDataProvider,
    view: SavedViewConfig,
    dashboard_config: Any,
) -> bool:
    """コネクターの保存済みビューをレンダリング

    Args:
        page_label: ページラベル
        provider: DashboardDataProvider
        view: SavedViewConfig
        dashboard_config: DashboardConfig

    Returns:
        レンダリング成功時True、コネクター未登録時False
    """
    cls = DashboardPageConnector._registry.get(page_label)
    if cls is None:
        return False
    connector = cls()
    if not connector.is_available(provider):
        return False
    connector.render_saved_view(provider, view, dashboard_config)
    return True


def generate_connector_saved_view_html(
    page_label: str,
    provider: DashboardDataProvider,
    view: SavedViewConfig,
    dashboard_config: Any,
) -> str:
    """コネクターの保存済みビューHTML断片を生成

    Args:
        page_label: ページラベル
        provider: DashboardDataProvider
        view: SavedViewConfig
        dashboard_config: DashboardConfig

    Returns:
        HTML断片文字列。未登録・利用不可の場合は空文字列。
    """
    cls = DashboardPageConnector._registry.get(page_label)
    if cls is None:
        return ""
    connector = cls()
    if not connector.is_available(provider):
        return ""
    return connector.generate_saved_view_html(provider, view, dashboard_config)


def generate_connector_pages_html(
    provider: DashboardDataProvider,
    dashboard_config: Any,
) -> list[tuple[str, str]]:
    """利用可能なコネクターページのHTML断片を生成

    Args:
        provider: DashboardDataProvider
        dashboard_config: DashboardConfig

    Returns:
        (ページラベル, HTML断片) のリスト。HTML未対応のコネクターは除外。
    """
    results: list[tuple[str, str]] = []
    for label, cls in DashboardPageConnector._registry.items():
        connector = cls()
        if not connector.is_available(provider):
            continue
        html = connector.generate_html(provider, dashboard_config)
        if html:
            results.append((label, html))
    return results


def get_connector_config_schema(
    page_label: str,
) -> list[dict[str, Any]]:
    """指定ページラベルのconnector_configスキーマを取得

    Args:
        page_label: ページラベル

    Returns:
        フィールド定義のリスト。未登録の場合は空リスト。
    """
    cls = DashboardPageConnector._registry.get(page_label)
    if cls is None:
        return []
    return cls.get_connector_config_schema()


def get_connector_view_type_options(
    provider: DashboardDataProvider,
) -> list[str]:
    """利用可能なコネクターのview_type一覧を返す

    SavedViewConfig.view_type用の "connector:{page_label}" 形式の値を返す。

    Args:
        provider: DashboardDataProvider

    Returns:
        view_typeのリスト
    """
    from config import _CONNECTOR_VIEW_PREFIX

    return [f"{_CONNECTOR_VIEW_PREFIX}{label}" for label in get_connector_pages(provider)]
