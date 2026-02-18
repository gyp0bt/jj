"""MLスクリプトパーサー: Pythonスクリプトのimport静的解析

PythonスクリプトのAST（抽象構文木）を解析してimport文を抽出し、
使用しているMLフレームワーク（PyTorch, scikit-learn, Optuna等）を検出する。

検出されたフレームワーク情報に基づき、ファイル名ヒューリスティクスと
合わせて「training_script」等のノードタイプに昇格させる。

コア依存（ast標準ライブラリ）のみで動作する。

[READMEへ戻る](../../../../../README.md)
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph

logger = logging.getLogger(__name__)

# フレームワーク検出用importマッピング
# キー: importモジュール名（前方一致）、値: フレームワーク識別子
FRAMEWORK_IMPORTS: dict[str, str] = {
    "torch": "pytorch",
    "torchvision": "pytorch",
    "pytorch_lightning": "pytorch-lightning",
    "lightning": "pytorch-lightning",
    "sklearn": "scikit-learn",
    "tensorflow": "tensorflow",
    "keras": "tensorflow",
    "optuna": "optuna",
    "botorch": "botorch",
    "mlflow": "mlflow",
    "wandb": "wandb",
    "tensorboard": "tensorboard",
    "scipy.optimize": "scipy-optimize",
}

# ファイル名 → MLロール推定
ROLE_PATTERNS: dict[str, str] = {
    "train": "training",
    "evaluate": "evaluation",
    "eval": "evaluation",
    "predict": "inference",
    "infer": "inference",
    "preprocess": "preprocessing",
    "model": "model_definition",
    "optimizer": "optimization",
    "optim": "optimization",
}


class MLScriptParser(AbstractFileParser):
    """Pythonスクリプトのimport解析・フレームワーク検出パーサー

    .pyファイルのAST解析でimport文を抽出し、MLフレームワークを検出する。
    検出された場合、ノードプロパティにフレームワーク情報とロール情報を付与し、
    training系スクリプトはtraining_scriptタイプに昇格させる。
    """

    priority = 57

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        for node in graph.nodes:
            if node.format != "py":
                continue
            # すでに他のタイプに昇格済みなら対象外
            if node.type not in ("file",):
                continue

            path_str = node.properties.get("path", "")
            if not path_str:
                continue

            file_path = graph.project_root / path_str
            if not file_path.exists():
                continue

            # import解析
            imports = self._extract_imports(file_path)
            if imports is None:
                continue

            # フレームワーク検出
            frameworks = self._detect_frameworks(imports)
            if not frameworks:
                continue

            # ML情報付与
            node.properties["ml_frameworks"] = sorted(frameworks)
            node.properties["ml_imports"] = sorted(imports)

            # ロール推定
            role = self._infer_role(node.name, imports)
            if role:
                node.properties["ml_role"] = role

            # training_scriptへの型昇格
            if role == "training":
                node.type = "training_script"

        return graph

    def _extract_imports(self, file_path: Path) -> list[str] | None:
        """Pythonファイルのimport文をAST解析で抽出

        Returns:
            importモジュール名のリスト。解析失敗時はNone。
        """
        try:
            source = file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(file_path))
        except (SyntaxError, ValueError):
            logger.debug("AST解析失敗: %s", file_path)
            return None

        imports: list[str] = []
        for ast_node in ast.walk(tree):
            if isinstance(ast_node, ast.Import):
                for alias in ast_node.names:
                    imports.append(alias.name)
            elif isinstance(ast_node, ast.ImportFrom) and ast_node.module:
                imports.append(ast_node.module)

        return imports

    def _detect_frameworks(self, imports: list[str]) -> set[str]:
        """import名からMLフレームワークを検出"""
        frameworks: set[str] = set()
        for imp in imports:
            for prefix, framework in FRAMEWORK_IMPORTS.items():
                if imp == prefix or imp.startswith(prefix + "."):
                    frameworks.add(framework)
                    break
        return frameworks

    def _infer_role(self, filename: str, imports: list[str]) -> str:
        """ファイル名とimportからMLロールを推定"""
        stem = Path(filename).stem.lower()

        # ファイル名ヒューリスティクス
        for pattern, role in ROLE_PATTERNS.items():
            if pattern in stem:
                return role

        # import内容からの推定
        import_str = " ".join(imports).lower()
        if "optuna" in import_str or "botorch" in import_str:
            return "optimization"

        return ""
