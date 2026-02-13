"""各サービスの複合ロジックを実装する。

CLIのビジネスロジックをここに集約し、CLI層は引数パース＋出力整形のみに責務を限定する。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from services.service.submit import SubmitService
from services.service.info import InfoService
from services.service.graph_command import GraphCommandService
from services.service.run_command import RunCommandService
from services.service.query_service import QueryService
from services.service.api_service import ApiService

__all__ = [
    "SubmitService",
    "InfoService",
    "GraphCommandService",
    "RunCommandService",
    "QueryService",
    "ApiService",
]
