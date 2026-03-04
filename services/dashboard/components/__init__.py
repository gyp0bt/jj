"""ダッシュボードコンポーネント基盤

PageComponent[ViewConfig]パターンで各ビュータイプを実装する。
__init_subclass__で自動登録され、レジストリ経由で漏れなくイテレーションできる。

使用例::

    class PlotViewConfig(ViewConfig):
        view_type = "plot"
        def render_add_form(self, provider, **kwargs):
            ...

    class PlotPage(PageComponent[PlotViewConfig]):
        page_key = "plot"
        page_label = "プロット"
        def render_page(self, provider, dashboard_config, **kwargs):
            ...

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar

if TYPE_CHECKING:
    from config import DashboardConfig, SavedViewConfig
    from services.dashboard.data_provider import DashboardDataProvider


class ViewConfig:
    """ビュー設定コンポーネント基底クラス

    各ビュータイプの設定UI（軸選択、フィルタ等）を提供する。
    __init_subclass__によりサブクラス定義時に自動的にレジストリに登録される。

    動的ビュー追加フォームで各ビュータイプ固有の設定UIを描画する際に使用する。

    Attributes:
        view_type: ビュータイプ識別子（例: "table", "plot"）
        _registry: 登録済みコンポーネントの辞書 {view_type: config_class}
    """

    view_type: str = ""
    _registry: ClassVar[dict[str, type[ViewConfig]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.view_type:
            cls._registry[cls.view_type] = cls

    def render_add_form(
        self,
        provider: DashboardDataProvider,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """動的ビュー追加フォームのビュータイプ固有部分を描画

        Args:
            provider: DashboardDataProvider
            **kwargs: 追加パラメータ

        Returns:
            ビュータイプ固有の設定値辞書（plot/gallery/array_plot等）
        """
        return {}


VC = TypeVar("VC", bound=ViewConfig)


class PageComponent(Generic[VC]):
    """ページコンポーネント基底クラス

    ダッシュボードの各ページ（テーブル・プロット等）をプラグインとして
    追加するための基底クラス。PageComponent[ViewConfig]形式で使用し、
    __init_subclass__によりサブクラス定義時に自動的にレジストリに登録される。

    Attributes:
        page_key: ビュータイプ識別子（例: "table", "plot"）。
                   SavedViewConfigのview_typeと対応する。
        page_label: サイドバーに表示するページ名（例: "テーブル", "プロット"）
        _registry: 登録済みコンポーネントの辞書 {page_key: component_class}
    """

    page_key: str = ""
    page_label: str = ""
    _registry: ClassVar[dict[str, type[PageComponent[Any]]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.page_key:
            cls._registry[cls.page_key] = cls

    def get_view_config(self) -> VC | None:
        """対応するViewConfigインスタンスを返す

        page_keyに一致するview_typeのViewConfigをレジストリから取得する。
        """
        return get_view_config(self.page_key)  # type: ignore[return-value]

    def render_page(
        self,
        provider: DashboardDataProvider,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        """スタンドアロンページとして描画

        Args:
            provider: DashboardDataProvider
            dashboard_config: DashboardConfig
            **kwargs: 追加パラメータ（vocab, project_root等）
        """
        raise NotImplementedError

    def render_saved_view(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        """保存済みビューとして描画

        Args:
            provider: DashboardDataProvider
            view: SavedViewConfig
            dashboard_config: DashboardConfig
            **kwargs: 追加パラメータ（vocab, project_root等）
        """
        raise NotImplementedError

    def generate_html(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> str:
        """保存済みビューのHTML断片を生成（HTMLエクスポート用）

        Streamlit非依存。各サブクラスがhtml_export関数に委譲する。

        Args:
            provider: DashboardDataProvider
            view: SavedViewConfig
            dashboard_config: DashboardConfig
            **kwargs: 追加パラメータ（vocab, project_root等）

        Returns:
            HTML断片文字列。未対応の場合は空文字列。
        """
        return ""


# ====================================================================
# レジストリアクセス関数
# ====================================================================


def get_page_labels() -> list[str]:
    """登録済みページのラベル一覧を返す（登録順）"""
    return [cls.page_label for cls in PageComponent._registry.values() if cls.page_label]


def get_page_keys() -> list[str]:
    """登録済みページキーの一覧を返す"""
    return list(PageComponent._registry.keys())


def get_page_component(page_key: str) -> PageComponent[Any] | None:
    """page_keyに対応するPageComponentインスタンスを返す"""
    cls = PageComponent._registry.get(page_key)
    if cls is None:
        return None
    return cls()


def get_page_component_by_label(page_label: str) -> PageComponent[Any] | None:
    """page_labelに対応するPageComponentインスタンスを返す"""
    for cls in PageComponent._registry.values():
        if cls.page_label == page_label:
            return cls()
    return None


def get_view_config(view_type: str) -> ViewConfig | None:
    """view_typeに対応するViewConfigインスタンスを返す"""
    cls = ViewConfig._registry.get(view_type)
    if cls is None:
        return None
    return cls()


def get_view_type_options() -> list[str]:
    """登録済みビュータイプの一覧を返す"""
    return list(ViewConfig._registry.keys())


# ====================================================================
# エントリーポイント経由のプラグインローダー
# ====================================================================

_plugins_loaded = False


def load_dashboard_plugins() -> None:
    """jj.dashboard_pagesエントリーポイントからプラグインをロード

    外部パッケージがPageComponent/ViewConfigのサブクラスを
    entry_point経由で登録できるようにする。

    エントリーポイントの値はモジュールパス（インポートするだけで
    __init_subclass__により自動登録される）。

    グループ名: ``jj.dashboard_pages``

    pyproject.toml例::

        [project.entry-points."jj.dashboard_pages"]
        my_solver = "my_package.dashboard.pages"

    一度だけロードされ、2回目以降の呼び出しはスキップする。
    """
    global _plugins_loaded
    if _plugins_loaded:
        return
    _plugins_loaded = True

    try:
        from importlib.metadata import entry_points

        eps = entry_points()
        # Python 3.12+ ではeps.select()が使える
        if hasattr(eps, "select"):
            dashboard_eps = eps.select(group="jj.dashboard_pages")
        else:
            # Python 3.10-3.11 フォールバック
            dashboard_eps = eps.get("jj.dashboard_pages", [])

        for ep in dashboard_eps:
            with __import__("contextlib").suppress(Exception):
                ep.load()
    except Exception:
        pass
