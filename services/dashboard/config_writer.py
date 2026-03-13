"""ダッシュボード設定のconfig.yaml書き戻し

現在のダッシュボード設定状態をconfig.yamlに保存する。
dashboardセクションのみを更新し、他のセクションは変更しない。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import yaml

from config import CONFIG_DIRNAME, CONFIG_FILENAME


def save_dashboard_defaults(
    project_root: Path,
    items: dict[str, Any],
) -> Path:
    """現在のダッシュボード設定をconfig.yamlに書き戻す

    既存のconfig.yamlを読み込み、dashboardセクションのみを更新。
    他のセクション（parse, export等）は変更しない。
    バックアップとして .bak ファイルを自動作成する。

    Args:
        project_root: プロジェクトルート
        items: 保存する設定値の辞書（dashboardセクション内のキー）
            例: {"table-columns": [...], "default-page": "overview"}

    Returns:
        書き込んだconfig.yamlのパス
    """
    config_path = project_root / CONFIG_DIRNAME / CONFIG_FILENAME

    # 既存設定を読み込み
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        # バックアップ作成
        backup_path = config_path.with_suffix(".yaml.bak")
        shutil.copy2(config_path, backup_path)
    else:
        data = {}

    if not isinstance(data, dict):
        data = {}

    # dashboardセクションを更新
    dashboard = data.setdefault("dashboard", {})
    if not isinstance(dashboard, dict):
        dashboard = {}
        data["dashboard"] = dashboard

    for key, value in items.items():
        if value is None:
            dashboard.pop(key, None)
        else:
            dashboard[key] = value

    # 書き戻し
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as f:
        yaml.dump(
            data,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    return config_path


def collect_current_dashboard_state() -> dict[str, Any]:
    """現在のsession_stateからダッシュボード設定を収集する

    Returns:
        config.yamlのdashboardセクションに書き戻すための辞書
    """
    try:
        import streamlit as st
    except ImportError:
        return {}

    items: dict[str, Any] = {}

    # ギャラリー設定
    gallery_cols = st.session_state.get("_gallery_user_cols")
    gallery_rows = st.session_state.get("_gallery_user_rows")
    if gallery_cols is not None or gallery_rows is not None:
        gd: dict[str, Any] = {}
        if gallery_cols is not None:
            gd["columns"] = int(gallery_cols)
        if gallery_rows is not None:
            gd["rows"] = int(gallery_rows)
        items["gallery-defaults"] = gd

    return items
