"""最適化スタディパーサー: Optuna study構造認識・メタデータ抽出

Optunaスタディ（.dbファイル）、最適化設定ファイル、試行履歴CSVを検出し、
ノードタイプを昇格させてメタデータを付与する。

コア依存のみで動作する（sqlite3, json, re, pathlib標準ライブラリ）。

[READMEへ戻る](../../../../../README.md)
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any

from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph

logger = logging.getLogger(__name__)

# 最適化関連ディレクトリ名パターン
OPTIMIZATION_DIR_PATTERNS = [
    re.compile(r"^optim(ization)?$", re.IGNORECASE),
    re.compile(r"^optuna", re.IGNORECASE),
    re.compile(r"^search$", re.IGNORECASE),
    re.compile(r"^hyperopt$", re.IGNORECASE),
    re.compile(r"^sweep[s]?$", re.IGNORECASE),
]

# 最適化設定ファイルのキーワード（少なくとも2つ以上含む場合に判定）
OPTIMIZATION_CONFIG_KEYWORDS = {
    "n_trials",
    "objective",
    "search_space",
    "direction",
    "sampler",
    "pruner",
    "study_name",
    "optimize",
    "trial",
    "hyperparameter",
}

# 試行履歴ファイル名パターン
TRIAL_HISTORY_PATTERNS = [
    re.compile(r"trial[_\-]?history", re.IGNORECASE),
    re.compile(r"pareto[_\-]?front", re.IGNORECASE),
    re.compile(r"optimization[_\-]?result", re.IGNORECASE),
    re.compile(r"study[_\-]?result", re.IGNORECASE),
]

# 最適化設定から抽出するパラメータキー
EXTRACTABLE_OPTIM_PARAMS = {
    "n_trials",
    "objective",
    "direction",
    "sampler",
    "pruner",
    "study_name",
}


class OptimizationRunParser(AbstractFileParser):
    """最適化スタディ構造認識パーサー

    Optuna SQLite DB、最適化設定ファイル、試行履歴CSVを検出し、
    ノードタイプ昇格とメタデータ付与を行う。
    """

    priority = 62

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        for node in graph.nodes:
            path_str = node.properties.get("path", "")
            if not path_str:
                continue

            # 1. Optuna SQLite DB検出
            if node.format == "db":
                self._check_optuna_db(node, graph)
                continue

            # 2. 最適化関連ディレクトリ内判定
            in_optim_dir = self._is_in_optimization_dir(path_str)

            # 3. 最適化設定ファイル検出
            if node.format in ("yaml", "json", "toml"):
                self._check_optimization_config(node, graph, in_optim_dir)
                continue

            # 4. 試行履歴CSV検出
            if node.format == "csv" or node.type == "dataset":
                self._check_trial_history(node, in_optim_dir)
                continue

            # 5. 最適化スクリプト検出（MLScriptParserで既にoptuna検出済みの場合）
            if node.format == "py" and in_optim_dir:
                self._enrich_optimization_script(node)

        return graph

    def _is_in_optimization_dir(self, path_str: str) -> bool:
        """パスが最適化関連ディレクトリ内にあるか判定"""
        parts = Path(path_str).parts
        for part in parts:
            for pattern in OPTIMIZATION_DIR_PATTERNS:
                if pattern.match(part):
                    return True
        return False

    def _check_optuna_db(self, node: Any, graph: Any) -> None:
        """SQLite DBがOptunaスタディかどうかを検証"""
        path_str = node.properties.get("path", "")
        file_path = graph.project_root / path_str
        if not file_path.exists():
            # ファイルが存在しなくても名前ベースで判定
            if self._looks_like_optuna_db(node.name):
                self._promote_to_optimization_study(node, {})
            return

        # SQLiteスキーマを検証
        try:
            conn = sqlite3.connect(str(file_path))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}

            # Optunaの典型テーブルを確認
            optuna_tables = {"studies", "trials"}
            if optuna_tables.issubset(tables):
                metadata = self._extract_optuna_metadata(cursor)
                self._promote_to_optimization_study(node, metadata)

            conn.close()
        except (sqlite3.Error, OSError):
            # SQLiteエラーの場合は名前ベースでフォールバック
            if self._looks_like_optuna_db(node.name):
                self._promote_to_optimization_study(node, {})
            logger.debug("Optuna DB読込失敗: %s", path_str)

    def _looks_like_optuna_db(self, name: str) -> bool:
        """ファイル名からOptunaスタディらしいかを判定"""
        name_lower = name.lower()
        return "optuna" in name_lower or "study" in name_lower

    def _extract_optuna_metadata(self, cursor: sqlite3.Cursor) -> dict[str, Any]:
        """Optuna DBからメタデータを抽出"""
        metadata: dict[str, Any] = {}
        try:
            cursor.execute("SELECT study_name FROM studies LIMIT 1")
            row = cursor.fetchone()
            if row:
                metadata["study_name"] = row[0]

            cursor.execute("SELECT COUNT(*) FROM trials")
            row = cursor.fetchone()
            if row:
                metadata["n_trials_completed"] = row[0]

            cursor.execute("SELECT direction FROM study_directions LIMIT 1")
            row = cursor.fetchone()
            if row:
                metadata["direction"] = row[0].lower()
        except sqlite3.Error:
            pass
        return metadata

    def _promote_to_optimization_study(self, node: Any, metadata: dict[str, Any]) -> None:
        """ノードをoptimization_studyタイプに昇格"""
        node.type = "optimization_study"
        node.properties["ml_optimization"] = True
        node.properties["optimization_framework"] = "optuna"
        for key, value in metadata.items():
            node.properties[key] = value

    def _check_optimization_config(self, node: Any, graph: Any, in_optim_dir: bool) -> None:
        """設定ファイルが最適化設定かどうかを検証"""
        path_str = node.properties.get("path", "")
        file_path = graph.project_root / path_str

        # 既にexperiment_configに昇格済みの場合はスキップ
        if node.type == "experiment_config":
            # experiment_configのプロパティから最適化キーワードを確認
            config_keys = node.properties.get("ml_config_keys", [])
            optim_keywords_found = set(config_keys) & OPTIMIZATION_CONFIG_KEYWORDS
            if len(optim_keywords_found) >= 2 or in_optim_dir:
                self._promote_to_optimization_config(node, {})
                self._extract_optim_params_from_properties(node)
            return

        if not file_path.exists():
            # ファイルが存在しない場合はディレクトリ位置で判定
            if in_optim_dir:
                self._promote_to_optimization_config(node, {})
            return

        # ファイル内容を検査
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return

        data: dict[str, Any] = {}
        if node.format == "yaml":
            try:
                import yaml

                data = yaml.safe_load(content) or {}
            except Exception:
                return
        elif node.format == "json":
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                return

        if not isinstance(data, dict):
            return

        # 最適化キーワードの存在確認
        flat_keys = self._flatten_keys(data)
        optim_keywords_found = flat_keys & OPTIMIZATION_CONFIG_KEYWORDS
        if len(optim_keywords_found) >= 2 or (len(optim_keywords_found) >= 1 and in_optim_dir):
            params = self._extract_optim_params(data)
            self._promote_to_optimization_config(node, params)

    def _flatten_keys(self, data: dict[str, Any], prefix: str = "") -> set[str]:
        """辞書のキーを再帰的にフラット化"""
        keys: set[str] = set()
        for key, value in data.items():
            key_lower = key.lower()
            keys.add(key_lower)
            if isinstance(value, dict):
                keys |= self._flatten_keys(value, f"{prefix}{key_lower}.")
        return keys

    def _extract_optim_params(self, data: dict[str, Any]) -> dict[str, Any]:
        """最適化設定からパラメータを抽出"""
        params: dict[str, Any] = {}
        for key in EXTRACTABLE_OPTIM_PARAMS:
            if key in data:
                value = data[key]
                if isinstance(value, (str, int, float, bool)):
                    params[key] = value
        return params

    def _extract_optim_params_from_properties(self, node: Any) -> None:
        """既存のml_paramsから最適化パラメータを取得"""
        ml_params = node.properties.get("ml_params", {})
        optim_params: dict[str, Any] = {}
        for key in EXTRACTABLE_OPTIM_PARAMS:
            if key in ml_params:
                optim_params[key] = ml_params[key]
        if optim_params:
            node.properties["optimization_params"] = optim_params

    def _promote_to_optimization_config(self, node: Any, params: dict[str, Any]) -> None:
        """ノードをoptimization_configタイプに昇格"""
        node.type = "optimization_config"
        node.properties["ml_optimization"] = True
        if params:
            node.properties["optimization_params"] = params

    def _check_trial_history(self, node: Any, in_optim_dir: bool) -> None:
        """試行履歴CSVかどうかを検証"""
        name_lower = node.name.lower()
        stem = Path(name_lower).stem

        for pattern in TRIAL_HISTORY_PATTERNS:
            if pattern.search(stem):
                self._promote_to_trial_history(node)
                return

        # 最適化ディレクトリ内のCSVで "trial" や "pareto" を名前に含む
        if in_optim_dir and any(kw in name_lower for kw in ("trial", "pareto", "result")):
            self._promote_to_trial_history(node)

    def _promote_to_trial_history(self, node: Any) -> None:
        """ノードをtrial_historyタイプに昇格"""
        node.type = "trial_history"
        node.properties["ml_optimization"] = True

    def _enrich_optimization_script(self, node: Any) -> None:
        """最適化ディレクトリ内のスクリプトにメタデータ追加"""
        # MLScriptParserで既にフレームワーク検出済みの場合
        frameworks = node.properties.get("ml_frameworks", [])
        if "optuna" in frameworks or "botorch" in frameworks:
            node.properties["ml_optimization"] = True
            if "optuna" in frameworks:
                node.properties["optimization_framework"] = "optuna"
            elif "botorch" in frameworks:
                node.properties["optimization_framework"] = "botorch"
        elif node.properties.get("ml_role") == "optimization":
            node.properties["ml_optimization"] = True
