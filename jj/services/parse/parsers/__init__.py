"""共通パーサーサブクラス群

AbstractFileParserのサブクラスとして、ファイル名解析・バージョン関係・
出力関係・ディレクトリ関係等の共通パーサーを提供する。

各モジュールをimportすると __init_subclass__ によりパーサーレジストリに
自動登録される。

[READMEへ戻る](../../../../README.md)
"""

# 全パーサーをimportして自動登録させる
from services.parse.parsers.version_parser import VersionRelationParser
from services.parse.parsers.output_parser import (
    AssetRelationParser,
    IncludesRelationParser,
    OutputRelationParser,
    ResultRelationParser,
)
from services.parse.parsers.directory_parser import (
    DirectoryRelationParser,
    RootDirectoryParser,
)
from services.parse.parsers.enrichment_filter import EnrichmentOnlyFilter
from services.parse.parsers.json_property_parser import JsonPropertyParser
from services.parse.parsers.vocab_finalizer import VocabFinalizer

__all__ = [
    "VersionRelationParser",
    "ResultRelationParser",
    "AssetRelationParser",
    "IncludesRelationParser",
    "OutputRelationParser",
    "DirectoryRelationParser",
    "RootDirectoryParser",
    "EnrichmentOnlyFilter",
    "JsonPropertyParser",
    "VocabFinalizer",
]
