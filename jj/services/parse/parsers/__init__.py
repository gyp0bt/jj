"""共通パーサーサブクラス群

AbstractFileParserのサブクラスとして、ファイル名解析・バージョン関係・
出力関係・ディレクトリ関係等の共通パーサーを提供する。

各モジュールをimportすると __init_subclass__ によりパーサーレジストリに
自動登録される。

[READMEへ戻る](../../../../README.md)
"""

# 全パーサーをimportして自動登録させる
from services.parse.parsers.csv_array_parser import CsvArrayParser
from services.parse.parsers.directory_parser import (
    DirectoryRelationParser,
    RootDirectoryParser,
)
from services.parse.parsers.display_name_parser import DisplayNameParser
from services.parse.parsers.enrichment_filter import EnrichmentOnlyFilter
from services.parse.parsers.json_property_parser import JsonPropertyParser
from services.parse.parsers.output_parser import (
    AssetRelationParser,
    IncludesRelationParser,
    OutputRelationParser,
    ResultRelationParser,
)
from services.parse.parsers.results_metadata_parser import ResultsMetadataParser
from services.parse.parsers.version_parser import VersionRelationParser
from services.parse.parsers.vocab_finalizer import VocabFinalizer

# MeshInheritParserはstatus-088でAbaqusプラグインに移動。
# services.plugins.abaqus.register() 経由で自動登録される。

__all__ = [
    "AssetRelationParser",
    "CsvArrayParser",
    "DirectoryRelationParser",
    "DisplayNameParser",
    "EnrichmentOnlyFilter",
    "IncludesRelationParser",
    "JsonPropertyParser",
    "OutputRelationParser",
    "ResultRelationParser",
    "ResultsMetadataParser",
    "RootDirectoryParser",
    "VersionRelationParser",
    "VocabFinalizer",
]
