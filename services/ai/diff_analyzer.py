"""Diff要約 — jj ai diff の実装

git diff / jj diff の出力をAIProviderで要約する。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from services.ai import require_provider
from services.ai.provider import DIFF_SYSTEM_PROMPT

# diff出力サイズ制限
MAX_DIFF_SIZE_CHARS = 50_000


def get_git_diff(cwd: Path | None = None, staged: bool = False, target: str | None = None) -> str:
    """git diffの出力を取得する。

    Args:
        cwd: 作業ディレクトリ
        staged: ステージ済み差分のみ (--cached)
        target: 比較対象（ブランチ名、コミットハッシュ等）

    Returns:
        diff出力テキスト
    """
    cmd = ["git", "diff"]
    if staged:
        cmd.append("--cached")
    if target:
        cmd.append(target)

    result = subprocess.run(
        cmd,
        cwd=cwd or Path.cwd(),
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout


def analyze_diff(diff_text: str, **kwargs) -> str:
    """diff出力をAIで分析・要約する。

    Args:
        diff_text: diff出力テキスト
        **kwargs: AIProviderに渡す追加パラメータ

    Returns:
        分析結果テキスト

    Raises:
        ValueError: AIプロバイダ未設定、またはdiffが空/大きすぎる
    """
    if not diff_text.strip():
        return "差分がありません。"

    if len(diff_text) > MAX_DIFF_SIZE_CHARS:
        diff_text = (
            diff_text[:MAX_DIFF_SIZE_CHARS] + f"\n\n... (残り {len(diff_text) - MAX_DIFF_SIZE_CHARS:,} 文字を省略)"
        )

    provider = require_provider()

    messages = [
        {"role": "system", "content": DIFF_SYSTEM_PROMPT},
        {"role": "user", "content": diff_text},
    ]
    return provider.chat(messages, **kwargs)


def analyze_git_diff(
    cwd: Path | None = None,
    staged: bool = False,
    target: str | None = None,
    **kwargs,
) -> str:
    """git diffを取得し、AIで分析する。

    Args:
        cwd: 作業ディレクトリ
        staged: ステージ済み差分のみ
        target: 比較対象
        **kwargs: AIProviderに渡す追加パラメータ

    Returns:
        分析結果テキスト
    """
    diff_text = get_git_diff(cwd=cwd, staged=staged, target=target)
    return analyze_diff(diff_text, **kwargs)
