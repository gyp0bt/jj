"""Abaqus INP *PARAMETERプロパティ抽出パーサー

INPファイルの *PARAMETER/**props ブロックからプロパティを読み取り、
ノードに追加する。vocabマッピングを適用してキーと値を変換する。

GraphServiceから分離されたAbaqus固有ロジック。

priority=15: ファイル名解析(10)の後、他のAbaqusパーサーの前に実行。

[READMEへ戻る](../../../../../README.md)
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph


class AbaqusParameterParser(AbstractFileParser):
    """INPファイルの *PARAMETER/**props ブロックからプロパティを抽出

    *PARAMETER キーワードの直後に **props コメントがある場合、
    そのブロック内のkey=value形式のパラメータをプロパティとして抽出する。
    vocabマッピングを適用してキーと値を変換する。
    """

    priority = 15

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        vocab = graph.config.vocab

        for node in graph.nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() != ".inp":
                continue

            file_path = graph.project_root / node.properties.get("path", "")
            if not file_path.exists():
                continue

            props = self._read_parameter_props(file_path, vocab)
            if props:
                node.properties.update(props)

        return graph

    @staticmethod
    def _read_parameter_props(file_path: object, vocab: dict[str, str]) -> dict[str, str]:
        """INPファイルの*PARAMETER/**propsブロックからプロパティを読み取る"""
        from pathlib import Path

        file_path = Path(str(file_path))
        if not file_path.exists():
            return {}

        props: dict[str, str] = {}
        try:
            with file_path.open(encoding="utf-8", errors="ignore") as f:
                while True:
                    line = f.readline()
                    if not line:
                        break
                    s = line.strip()
                    s_l = s.lower().replace(" ", "")
                    if s_l.startswith("*parameter"):
                        # print(s_l)
                        header = f.readline()
                        if not header:
                            break
                        # header_s = header.strip().lower().replace(" ", "")
                        # if not header_s.startswith("**props"):
                        # continue
                        while True:
                            line2 = f.readline()
                            if not line2:
                                break
                            t = line2.strip()
                            if not t:
                                continue
                            if t.startswith("**"):
                                continue
                            if t.lstrip().startswith("*"):
                                break
                            u = t.replace(" ", "")
                            if "=" not in u:
                                continue
                            k, v = u.split("=", 1)
                            # 数値の場合は整形、文字列はそのまま保持
                            if v.lstrip("-").isdigit():
                                v = str(int(v))
                            elif "." in v or "e" in v.lower():
                                with contextlib.suppress(ValueError):
                                    float(v)  # validate numeric
                                # 元の表記を保持（科学表記への変換はしない）
                            if k:
                                k = vocab.get(k, k)
                                v = vocab.get(v, v)
                                props[k] = v
                        return props
        except OSError:
            pass
        return props
