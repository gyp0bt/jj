"""RunCommandService: runコマンドのビジネスロジック

CLI cli/__init__.pyのrunコマンドで使用されるビジネスロジックを集約。
CLI層はargparse解析と出力整形のみに責務を限定する。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from pathlib import Path

from services.run import RunService, RunResult


class RunCommandService:
    """runコマンドのビジネスロジック

    RunServiceのラッパーとして、コマンド引数の前処理と
    実行ロジックを提供する。FastAPI等のAPI層からも利用可能。
    """

    def __init__(self) -> None:
        self._run_service = RunService()

    def execute(
        self,
        command: list[str],
        cwd: str | Path = ".",
        mode: str | None = None,
    ) -> RunResult:
        """コマンドを実行する

        Args:
            command: 実行コマンド（"--"を含む場合は自動除去）
            cwd: 実行ディレクトリ（文字列またはPath）
            mode: 実行モード（None or "auto"で自動判定, "script", "job"）

        Returns:
            RunResult: 実行結果

        Raises:
            ValueError: コマンドが空の場合
        """
        # "--" の除去
        cleaned = list(command)
        if cleaned and cleaned[0] == "--":
            cleaned = cleaned[1:]

        if not cleaned:
            raise ValueError("実行コマンドを指定してください。")

        resolved_cwd = Path(cwd).resolve()
        resolved_mode = None if mode in (None, "auto") else mode

        return self._run_service.execute(
            command=cleaned,
            cwd=resolved_cwd,
            mode=resolved_mode,
        )
