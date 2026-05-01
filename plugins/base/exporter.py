"""エクスポート基盤モジュール

parseで解析したグラフデータを外部形式に出力するロジックを提供する。

## エクスポーターパターン

AbstractExporterのサブクラスを定義すると __init_subclass__ により
自動的にエクスポーターレジストリに登録されます。

```python
class MyExporter(AbstractExporter):
    format = "my_format"
    priority = 50

    def export(self, graph, **kwargs):
        # エクスポート処理
        return {"output_path": path, "count": n}
```

対応形式:
- csv: CSV形式（UTF-8 BOM付き）
- json: JSON形式
- obsidian: Obsidianマークダウン
- neo4j: Neo4jデータベース直接書き込み
- cypher: Cypherクエリファイル出力
- dashboard-json: ダッシュボード向けJSON

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jj_types import GraphModel

# エクスポーターレジストリ: __init_subclass__ で自動登録される
_exporter_registry: list[type[AbstractExporter]] = []


class AbstractExporter(ABC):
    """グラフエクスポート用抽象基底クラス

    GraphModelを受け取り、指定形式でエクスポートする。
    サブクラスを定義すると自動的にエクスポーターレジストリに登録される。

    priority属性で実行順序を制御する（小さいほど先に実行）。
    format属性でエクスポート形式を識別する。

    エクスポーター実行順序の指針:
        10: CSV/JSONエクスポート（ファイルベース、軽量）
        20: Obsidianエクスポート（ファイルベース、中量）
        30: Neo4j/Cypherエクスポート（DB接続、重量）
        40: dashboard-jsonエクスポート
    """

    format: str = "unknown"
    priority: int = 100

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        # 抽象メソッドが残っているクラスは登録しない
        if not getattr(cls, "__abstractmethods__", None):
            _exporter_registry.append(cls)

    @abstractmethod
    def export(self, graph: GraphModel, **kwargs: Any) -> dict[str, Any]:
        """グラフをエクスポートする

        Args:
            graph: エクスポート対象のGraphModel
            **kwargs: エクスポーター固有のオプション

        Returns:
            エクスポート結果のメタデータ辞書
            （例: {"output_path": Path, "count": int}）
        """
        ...

    def format_cli_result(self, result: dict[str, Any], project_root: Path) -> str:
        """エクスポート結果をCLI出力用文字列にフォーマット

        デフォルト実装は汎用的なサマリーを返す。
        サブクラスでオーバーライドして形式固有の出力を生成できる。

        Args:
            result: export()の戻り値
            project_root: プロジェクトルートパス

        Returns:
            CLI出力用の文字列
        """
        output_path = result.get("output_path")
        count = result.get("count", 0)
        if output_path:
            try:
                rel = Path(output_path).relative_to(project_root)
            except ValueError:
                rel = output_path
            return f"{self.format}エクスポート完了: {rel} ({count}件)"
        return f"{self.format}エクスポート完了 ({count}件)"


def get_exporter_registry() -> list[type[AbstractExporter]]:
    """登録済みエクスポーターの一覧を返す（テスト・デバッグ用）"""
    return list(_exporter_registry)


def clear_exporter_registry() -> None:
    """エクスポーターレジストリをクリアする（テスト用）"""
    _exporter_registry.clear()


def get_exporter_for_format(fmt: str) -> type[AbstractExporter] | None:
    """指定形式に対応するエクスポータークラスを返す

    Args:
        fmt: エクスポート形式（"csv", "json", "obsidian"等）

    Returns:
        対応するエクスポータークラス。見つからない場合はNone。
    """
    sorted_exporters = sorted(_exporter_registry, key=lambda cls: cls.priority)
    for exporter_cls in sorted_exporters:
        if exporter_cls.format == fmt:
            return exporter_cls
    return None
