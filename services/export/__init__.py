"""組み込みエクスポーター層

CSV/JSON/Neo4j/Cypher 等のコア同梱エクスポーターを集約する。
本パッケージを import すると ``connectors`` 配下が読み込まれ、
``AbstractExporter.__init_subclass__`` による自動登録が発火する。

エクスポーター基底（AbstractExporter）とレジストリAPIは
``plugins.base.exporter`` が唯一の定義元。本層はその実装ではなく
「組み込みエクスポーターの置き場 + 登録トリガー」である。

[READMEへ戻る](../../README.md)
"""

# import 時に組み込みエクスポーターを自動登録（__init_subclass__ を発火）。
# トップレベル import だと循環参照になるため、サブパッケージを遅延 import する。
import services.export.connectors  # noqa: F401
