"""物理実験プラグイン — 実験データの取り込みとRun管理 (T8-2)

CSV/TSV形式の実験データを自動検出し、グラフノードとして登録する。
メタデータファイル（.meta.yaml）からの属性抽出にも対応。

## 登録されるパーサー

| パーサー | priority | 説明 |
|----------|----------|------|
| ExperimentDataParser | 56 | CSV/TSVデータ検出・メタデータ抽出 |
| ExperimentRunDiscoverer | 76 | 実験ディレクトリからRun発見・登録 |

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_registered = False


def register() -> None:
    """物理実験プラグインの全コンポーネントを登録する"""
    global _registered
    if _registered:
        return
    _registered = True

    import services.parse.connectors.experiment.data_parser  # noqa: F401

    logger.debug("物理実験プラグインを登録完了")


# モジュールインポート時に自動登録
register()
