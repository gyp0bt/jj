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

    TODO:
        include関係にある親ファイルから読み取る場合、親ファイルのパラメータを子ファイルに渡して演算式を評価してfloat化します。
        parameter数式はpythonライクな演算式です。
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

            props = self._read_parameter_props(file_path, vocab, master_props={})

            if props:
                node.properties.update(props)

        return graph

    @staticmethod
    def _read_parameter_props(
        file_path: object,
        vocab: dict[str, str],
        master_props: dict[str, str] | None = None,
        _visited: set[object] | None = None,
    ) -> dict[str, str]:
        """Read *PARAMETER/**props blocks from an INP file (including *include files).

        The method recursively processes *include directives, merging the
        resulting properties into the current context.  Circular includes are
        detected via the ``_visited`` set and ignored.
        """
        from pathlib import Path
        import re

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
                while True:
                    line = f.readline()
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
                            # 再帰的に子ファイルからプロパティを取得
                            inc_props = AbaqusParameterParser._read_parameter_props(
                                inc_path,
                                vocab,
                                master_props={**master_props, **props},
                                _visited=_visited,
                            )
                            # 取得したプロパティを現在のコンテキストにマージ
                            props.update(inc_props)
                        continue

                    # --------------------------------------------------
                    # *parameter ブロックの検出と処理
                    # --------------------------------------------------
                    if s_l.startswith("*parameter"):
                        # ヘッダー行を読み飛ばす
                        header = f.readline()
                        if not header:
                            break

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
                                # 次のキーワードに到達したらブロック終了
                                break

                            u = t.replace(" ", "")
                            if "=" not in u:
                                continue
                            k_raw, v_raw = u.split("=", 1)

                            # ----------------------------------------------
                            # 1) vocab マッピング
                            # ----------------------------------------------
                            k = vocab.get(k_raw, k_raw)
                            v = vocab.get(v_raw, v_raw)

                            # ----------------------------------------------
                            # 2) トークン置換：他のプロパティ参照を解決
                            # ----------------------------------------------
                            combined = {**master_props, **props}
                            tokens = re.split(r"([*+\-/])", v)
                            new_tokens = [
                                token if token in ("*", "+", "-", "/") else combined.get(vocab.get(token, token), token)
                                for token in tokens
                            ]
                            v = "".join([vocab.get(_v, _v) for _v in new_tokens])

                            # ----------------------------------------------
                            # 3) 可能なら算術式を評価
                            # ----------------------------------------------
                            try:
                                # 安全性を保つため、組み込み関数は全て除外
                                result = eval(v, {"__builtins__": None}, {})
                                if isinstance(result, (int, float)):
                                    # 整数表記に揃える
                                    if isinstance(result, float) and result.is_integer():
                                        v = str(int(result))
                                    else:
                                        v = str(result)
                            except Exception:
                                # 評価できなければそのまま文字列を保持
                                pass

                            # ----------------------------------------------
                            # 4) 数値の整形（整数は整数表記、実数は元表記保持）
                            # ----------------------------------------------
                            if v.lstrip("-").isdigit():
                                v = str(int(v))
                            elif "." in v or "e" in v.lower():
                                with contextlib.suppress(ValueError):
                                    float(v)  # 検証だけ

                            props[k] = v
        except OSError:
            pass
        finally:
            _visited.discard(path)

        return props
