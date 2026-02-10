"""各サービスの複合ロジックを実装する。

CLIのビジネスロジックをここに集約し、CLI層は引数パース＋出力整形のみに責務を限定する。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from services.service.submit import SubmitService
from services.service.info import InfoService

__all__ = ["SubmitService", "InfoService"]
