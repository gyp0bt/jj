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
        """jjの.jj/config/config.yamlからNeo4j設定を読み込む

        config.yamlのneo4jセクションを参照する。
        設定がない場合はデフォルト値を返す。
        """
        from pathlib import Path

        from config import load_project_config

        config_data = load_project_config(base_dir)
        neo4j_data = config_data.get("neo4j", {})
        if not neo4j_data:
            return cls()
        return cls.from_dict(neo4j_data)
