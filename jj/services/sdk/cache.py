"""CacheProvider プロトコル

GraphStorageの公開インターフェースを Protocol として定義する。
プラグインはこのプロトコルに依存し、具体的なGraphStorage実装には
依存しない。これによりストレージバックエンドの差し替え
（ファイル→DB、ローカル→リモート等）が可能になる。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from jj_types import GraphModel


@runtime_checkable
class CacheProvider(Protocol):
    """グラフデータの永続化インターフェース

    GraphStorageが実装する公開プロトコル。
    プラグインやテストで差し替え可能にするための抽象境界を定義する。

    メソッド:
        load: グラフデータの読み込み
        save: グラフデータの保存
        load_timestamps: タイムスタンプキャッシュの読み込み
        save_timestamps: タイムスタンプキャッシュの保存
        load_abq_data: ABQDataキャッシュの読み込み
        save_abq_data: ABQDataキャッシュの保存
    """

    def load(self, project_root: Path, filename: str | None = None) -> GraphModel:
        """グラフデータを読み込む

        Args:
            project_root: プロジェクトルートパス
            filename: ファイル名（Noneでデフォルト検出）

        Returns:
            読み込んだGraphModel（ファイルなし時は空GraphModel）
        """
        ...

    def save(
        self,
        project_root: Path,
        graph: GraphModel,
        filename: str | None = None,
    ) -> Path:
        """グラフデータを保存する

        Args:
            project_root: プロジェクトルートパス
            graph: 保存対象のGraphModel
            filename: 出力ファイル名（Noneでデフォルト）

        Returns:
            保存先パス
        """
        ...

    def load_timestamps(self, project_root: Path) -> dict[str, float]:
        """前回パース時のファイルタイムスタンプを読み込む

        Returns:
            {相対パス: mtime} のマッピング
        """
        ...

    def save_timestamps(
        self, project_root: Path, timestamps: dict[str, float]
    ) -> Path:
        """パース時のファイルタイムスタンプを保存する

        Args:
            project_root: プロジェクトルート
            timestamps: {相対パス: mtime} のマッピング

        Returns:
            保存先パス
        """
        ...

    def load_abq_data(
        self, project_root: Path, file_path: str, expected_mtime: float
    ) -> Any:
        """永続化されたABQDataキャッシュを読み込む

        Args:
            project_root: プロジェクトルート
            file_path: 元のINPファイルパス
            expected_mtime: 期待するファイルのmtime

        Returns:
            キャッシュされたABQData（無効時None）
        """
        ...

    def save_abq_data(
        self, project_root: Path, file_path: str, abq_data: Any, mtime: float
    ) -> Path:
        """ABQDataをディスクに永続化する

        Args:
            project_root: プロジェクトルート
            file_path: 元のINPファイルパス
            abq_data: 保存するABQData
            mtime: INPファイルのmtime

        Returns:
            保存先パス
        """
        ...
