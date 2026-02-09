"""共有設定定義 - Neo4j接続設定

[READMEへ戻る](../README.md)
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class Neo4jConfig(BaseModel):
    """Neo4j接続設定"""

    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = "password"
    database: str = "neo4j"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Neo4jConfig":
        return cls(
            uri=data.get("uri", "bolt://localhost:7687"),
            user=data.get("user", "neo4j"),
            password=data.get("password", "password"),
            database=data.get("database", "neo4j"),
        )

    @classmethod
    def from_jj_config(cls, base_dir: Optional["Path"] = None) -> "Neo4jConfig":
        """jjの設定からNeo4j接続情報を読み込む

        優先順位:
        1. 暗号化クレデンシャル（.jj/config/.credentials）
        2. config.yamlのneo4jセクション
        3. デフォルト値
        """
        from pathlib import Path

        from config import load_project_config

        if base_dir is None:
            base_dir = Path.cwd()

        # 暗号化クレデンシャルを優先的に読み込み
        try:
            from jj.services.lib.credentials import load_credentials

            creds = load_credentials(base_dir, "neo4j")
            if creds:
                return cls(
                    uri=creds.get("uri", "bolt://localhost:7687"),
                    user=creds.get("user", "neo4j"),
                    password=creds.get("password", "password"),
                    database=creds.get("database", "neo4j"),
                )
        except ImportError:
            pass

        # config.yamlからのフォールバック
        config_data = load_project_config(base_dir)
        neo4j_data = config_data.get("neo4j", {})
        if not neo4j_data:
            return cls()
        return cls.from_dict(neo4j_data)
