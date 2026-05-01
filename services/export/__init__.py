"""エクスポート基盤モジュール（後方互換）

このモジュールはplugins.base.exporterからre-exportしています。
新規コードでは plugins.base.exporter を直接importしてください。

[READMEへ戻る](../../README.md)
"""

# 後方互換のためのre-export
from plugins.base.exporter import (
    AbstractExporter,
    _exporter_registry,
    clear_exporter_registry,
    get_exporter_for_format,
    get_exporter_registry,
)


def _register_builtin_exporters() -> None:
    """組み込みエクスポーター（CSV/JSON等）を自動登録する。

    ``services.export.connectors`` のサブモジュールを import することで、
    ``__init_subclass__`` パターンによる自動登録が発火する。
    トップレベル import だと循環参照になるため、関数内で遅延 import する。
    """
    import services.export.connectors  # noqa: F401


_register_builtin_exporters()

__all__ = [
    "AbstractExporter",
    "_exporter_registry",
    "clear_exporter_registry",
    "get_exporter_for_format",
    "get_exporter_registry",
]
