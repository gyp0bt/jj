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


def _resolve_param_references(expr: str, params: dict[str, str]) -> str:
    """式中のパラメータ参照を解決する。

    Abaqusの ``<param_name>`` 形式と、Pythonライクな識別子形式の
    両方のパラメータ参照をサポートする。

    Parameters
    ----------
    expr : str
        評価対象の式文字列
    params : dict[str, str]
        利用可能なパラメータ辞書（name -> value）

    Returns
    -------
    str
        パラメータ参照が解決された式文字列
    """
    import re

    # 1) <param_name> 形式の参照を解決（Abaqus標準形式）
    def _replace_angle(m: re.Match) -> str:
        name = m.group(1)
        # 大文字小文字を区別しない検索
        for k, v in params.items():
            if k.lower() == name.lower():
                return str(v)
        return m.group(0)  # 未解決なら元の文字列を維持

    expr = re.sub(r"<([a-zA-Z_][a-zA-Z0-9_]*)>", _replace_angle, expr)

    # 2) 識別子形式の参照を解決（大文字小文字区別なし）
    params_lower = {k.lower(): str(v) for k, v in params.items()}

    def _replace_ident(m: re.Match) -> str:
        ident = m.group(0)
        return params_lower.get(ident.lower(), ident)

    expr = re.sub(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", _replace_ident, expr)

    return expr


class AbaqusParameterParser(AbstractFileParser):
    """INPファイルの *PARAMETER/**props ブロックからプロパティを抽出

    *PARAMETER キーワードの直後に **props コメントがある場合、
    そのブロック内のkey=value形式のパラメータをプロパティとして抽出する。
    vocabマッピングを適用してキーと値を変換する。

    include関係にある親ファイルのパラメータを子ファイルに伝搬し、
    演算式（Pythonライクな四則演算・べき乗）を評価してfloat化する。
    Abaqusの ``<param_name>`` 形式のパラメータ参照にも対応。
    """

    priority = 15

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        for node in graph.nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() != ".inp":
                continue

            file_path = graph.project_root / node.properties.get("path", "")
            if not file_path.exists():
                continue

            props = self._read_parameter_props(file_path, master_props={})

            if props:
                node.properties.update(props)

        return graph

    @staticmethod
    def _read_parameter_props(
        file_path: object,
        master_props: dict[str, str] | None = None,
        _visited: set[object] | None = None,
    ) -> dict[str, str]:
        """Read *PARAMETER/**props blocks from an INP file (including *include files).

        The method recursively processes *include directives, merging the
        resulting properties into the current context.  Circular includes are
        detected via the ``_visited`` set and ignored.
        """
        import re
        from pathlib import Path

        # 初期化
        if master_props is None:
            master_props = {}
        if _visited is None:
            _visited = set()

        path = Path(str(file_path)).resolve()
        if path in _visited:
            # 循環参照検出 – 何も追加せずに抜ける
            return {}
        _visited.add(path)

        if not path.exists():
            _visited.discard(path)
            return {}

        props: dict[str, str] = {}

        try:
            with path.open(encoding="utf-8", errors="ignore") as f:
                # pending_line: *PARAMETERブロック終了時に読み込んだ
                # 次のキーワード行を外側ループで再処理するためのバッファ
                pending_line: str | None = None

                while True:
                    if pending_line is not None:
                        line = pending_line
                        pending_line = None
                    else:
                        line = f.readline()
                        pass
                    if not line:
                        break
                    s = line.strip()
                    if not s:
                        continue

                    s_l = s.lower().replace(" ", "")

                    # --------------------------------------------------
                    # *include 行の処理（再帰的に同メソッドを呼び出す）
                    # --------------------------------------------------
                    if s_l.startswith("*include"):
                        include_match = re.search(r"^\*include\s*,\s*input\s*=\s*([^\s,]+)", s, re.IGNORECASE)
                        if include_match:
                            inc_name = include_match.group(1)
                            inc_path = (path.parent / inc_name).resolve()
                            inc_props = AbaqusParameterParser._read_parameter_props(
                                inc_path,
                                master_props={**master_props, **props},
                                _visited=_visited,
                            )
                            props.update(inc_props)
                        continue

                    # --------------------------------------------------
                    # *parameter ブロックの検出と処理
                    # --------------------------------------------------
                    if s_l.startswith("*parameter"):
                        # ヘッダー行を読み飛ばす
                        # header = f.readline()
                        # if not header:
                        # break

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
                                # 次のキーワード行を外側ループで再処理
                                pending_line = line2
                                break

                            u = t.replace(" ", "")
                            if "=" not in u:
                                continue
                            k_raw, v_raw = u.split("=", 1)

                            k = k_raw
                            v = v_raw

                            # パラメータ参照を解決（識別子と<param>形式の両方）
                            combined = {**master_props, **props}
                            v = _resolve_param_references(v, combined)

                            # 可能なら算術式を評価
                            try:
                                result = eval(v, {"__builtins__": None}, {})
                                if isinstance(result, (int, float)):
                                    if isinstance(result, float) and result.is_integer():
                                        v = str(int(result))
                                    else:
                                        v = str(result)
                            except Exception:
                                pass

                            # 数値の整形
                            if v.lstrip("-").isdigit():
                                v = str(int(v))
                            elif "." in v or "e" in v.lower():
                                with contextlib.suppress(ValueError):
                                    float(v)

                            props[k] = v
        except OSError:
            pass

        return props
