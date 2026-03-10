"""ファイル要約 — jj ai summarize の実装

単体ファイルまたは複数ファイルの内容をAIProviderで要約する。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

from pathlib import Path

from services.ai import require_provider

# ファイルサイズ制限（要約対象）
MAX_FILE_SIZE_BYTES = 100_000  # 100KB


def summarize_file(file_path: Path, **kwargs) -> str:
    """ファイルの内容を要約する。

    Args:
        file_path: 要約対象ファイルのパス
        **kwargs: AIProviderに渡す追加パラメータ

    Returns:
        要約テキスト

    Raises:
        FileNotFoundError: ファイルが存在しない
        ValueError: ファイルが大きすぎる、またはAIプロバイダ未設定
    """
    if not file_path.exists():
        raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

    size = file_path.stat().st_size
    if size > MAX_FILE_SIZE_BYTES:
        raise ValueError(f"ファイルが大きすぎます ({size:,} bytes > {MAX_FILE_SIZE_BYTES:,} bytes): {file_path}")

    provider = require_provider()

    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"テキストファイルとして読み込めません: {file_path}") from e

    prompt_text = f"=== ファイル: {file_path.name} ===\n\n{content}"
    return provider.summarize(prompt_text, **kwargs)


def summarize_files(file_paths: list[Path], **kwargs) -> dict[str, str]:
    """複数ファイルの要約を一括生成する。

    Args:
        file_paths: 要約対象ファイルのパスリスト
        **kwargs: AIProviderに渡す追加パラメータ

    Returns:
        {ファイル名: 要約テキスト} の辞書。エラー時は要約テキストにエラーメッセージ。
    """
    results = {}
    for path in file_paths:
        try:
            results[str(path)] = summarize_file(path, **kwargs)
        except (FileNotFoundError, ValueError) as e:
            results[str(path)] = f"[エラー] {e}"
    return results
