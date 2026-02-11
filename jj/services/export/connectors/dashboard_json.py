"""dashboard-jsonエクスポーター: GraphModelをダッシュボード向けJSONでエクスポート

DashboardDataProviderをAbstractExporterサブクラスとしてラップし、
レジストリ経由で呼び出し可能にする。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jj_types import GraphModel
from services.export import AbstractExporter


class DashboardJsonExporter(AbstractExporter):
    """dashboard-json形式エクスポーター（AbstractExporterサブクラス）

    DashboardDataProviderをラップし、AbstractExporterレジストリに登録する。
    """

    format = "dashboard-json"
    priority = 40

    def export(self, graph: GraphModel, **kwargs: Any) -> dict[str, Any]:
        """dashboard-jsonエクスポート

        kwargs:
            project_root: Path - プロジェクトルート
            output_file: str | None - 出力ファイルパス
            project_name: str | None - プロジェクト名
            vocab: dict[str, str] | None - vocab設定
            units: dict[str, str] | None - units設定
        """
        from services.dashboard.data_provider import DashboardDataProvider

        project_root = Path(kwargs.get("project_root") or Path.cwd())
        output_file = kwargs.get("output_file")
        project_name = kwargs.get("project_name") or project_root.name
        vocab = kwargs.get("vocab") or {}
        units = kwargs.get("units") or {}

        provider = DashboardDataProvider(
            graph,
            vocab=vocab,
            units=units,
        )

        data = provider.to_dashboard_json(project_name=project_name)

        if output_file:
            out_path = Path(output_file)
        else:
            storage_dir = project_root / ".jj" / "storage"
            storage_dir.mkdir(parents=True, exist_ok=True)
            out_path = storage_dir / "dashboard.json"

        with out_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        return {
            "output_path": out_path,
            "node_count": len(graph.nodes),
            "relation_count": len(graph.relations),
            "row_count": len(data["rows"]),
        }
