from __future__ import annotations

import re
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

import chardet
import numpy as np
from ftfy import fix_text
from numpy.typing import NDArray

# ==========================
#  型エイリアス
# ==========================

PathLike = str | Path
PathList = PathLike | list[PathLike]


# ==========================
#  ファイル読み込み
# ==========================


def _resolve_include_path(
    include_name: str,
    file_path: Path,
    max_depth: int = 5,
) -> Path | None:
    """*INCLUDEで参照されるファイルを探索する

    探索順序:
    1. ファイルを含むフォルダ (file_path.parent)
    2. スクリプト実行フォルダ (cwd)
    3. cwd配下をN階層まで再帰的に探索

    Args:
        include_name: include対象のファイル名/相対パス
        file_path: includeディレクティブを含むファイルのパス
        max_depth: 再帰探索の最大階層数

    Returns:
        解決されたファイルパス。見つからない場合はNone。
    """
    # 1. ファイルを含むフォルダから探索
    candidate = (file_path.parent / include_name).resolve()
    if candidate.exists():
        return candidate

    # 2. スクリプト実行フォルダ (cwd) から探索
    cwd = Path.cwd()
    candidate = (cwd / include_name).resolve()
    if candidate.exists():
        return candidate

    # 3. cwd配下を再帰的にN階層まで探索
    include_filename = Path(include_name).name
    for depth_path in _walk_max_depth(cwd, max_depth):
        candidate = depth_path / include_filename
        if candidate.exists():
            return candidate

    return None


def _walk_max_depth(root: Path, max_depth: int) -> Generator[Path, None, None]:
    """ディレクトリをmax_depth階層まで走査する

    Args:
        root: 起点ディレクトリ
        max_depth: 最大走査階層数

    Yields:
        ディレクトリパス
    """
    if max_depth < 0:
        return
    try:
        yield root
        if max_depth > 0:
            for entry in sorted(root.iterdir()):
                if entry.is_dir() and not entry.name.startswith("."):
                    yield from _walk_max_depth(entry, max_depth - 1)
    except PermissionError:
        return


def _normalize_paths(file_paths: PathList) -> list[Path]:
    """内部用: パス引数を List[Path] に正規化"""
    if isinstance(file_paths, (str, Path)):
        file_paths = [file_paths]
    return [Path(p) for p in file_paths]


def _detect_encoding(raw: bytes) -> str:
    enc = chardet.detect(raw).get("encoding")
    return enc or "utf-8"


def detect_and_fix_encoding(text: bytes) -> str:
    """エンコーディングを判定し、適切にデコードする

    Args:
        text (bytes): 生バイト列

    Returns:
        str: デコード済みテキスト（文字化け補正済み）
    """
    enc = _detect_encoding(text)
    try:
        decoded = text.decode(enc, errors="strict")
    except (UnicodeDecodeError, LookupError):
        decoded = text.decode("utf-8", errors="ignore")
    return fix_text(decoded)


def read_files_with_unknown_encoding(
    file_paths: PathList, verbose: bool = True, include_max_depth: int = 5
) -> Generator[tuple[Path, str], None, None]:
    """未知のエンコーディングの複数ファイルを行単位で読み込む

    * chardetで先頭数KBから推定
    * *INCLUDE を再帰的に辿る（複数階層探索対応）
    * メモリ効率を意識して逐次yield

    include探索順序:
    1. ファイルを含むフォルダ
    2. スクリプト実行フォルダ (cwd)
    3. cwd配下をN階層まで再帰的に探索

    Args:
        file_paths (PathList): ファイルパス or そのリスト

    Yields:
        tuple[Path, str]: (現在のファイルパス, 行文字列)
    """
    paths = _normalize_paths(file_paths)

    for file_path in paths:
        try:
            with open(file_path, "rb") as f:
                raw_head = f.read(4096)
            enc = _detect_encoding(raw_head)

            with open(file_path, encoding=enc, errors="replace") as f:
                for raw_line in f:
                    line_stripped = raw_line.rstrip("\r\n")

                    # *INCLUDE 処理（大文字小文字無視）
                    if line_stripped.lstrip().lower().startswith("*include"):
                        m = re.search(
                            r"input\s*=\s*([^,\s]+)",
                            line_stripped,
                            flags=re.IGNORECASE,
                        )
                        if not m:
                            print(f"Warning: *INCLUDE 行の解析に失敗しました: {line_stripped}")
                            continue
                        include_name = m.group(1)
                        include_path = _resolve_include_path(include_name, file_path, max_depth=include_max_depth)
                        if include_path is None:
                            print(
                                f"Warning: *INCLUDE ファイルが見つかりません（スキップ）: "
                                f"{include_name} (from {file_path})"
                            )
                            continue
                        if verbose:
                            print(f"Reading included file: {include_path}")
                        yield from read_files_with_unknown_encoding(
                            include_path, verbose=verbose, include_max_depth=include_max_depth
                        )
                    else:
                        yield file_path, line_stripped

        except Exception as e:
            print(f"ファイル '{file_path}' の読み込み中にエラー発生: {e}")


# ==========================
#  Context & 基底クラス
# ==========================


class Context:
    """INP全体の状態を保持"""

    def __init__(self) -> None:
        self.parameters: dict[str, Any] = {}
        self.current_material: ReadMaterial | None = None

    def __str__(self) -> str:
        return str(self.parameters)


class ReadComponent:
    """対応キーワード用の基底クラス"""

    dtype: Any = "int32"
    read_component_list: ClassVar[list[type[ReadComponent]]] = []

    @staticmethod
    def iter_read_components() -> Generator[type[ReadComponent], None, None]:
        yield from ReadComponent.read_component_list

    def __init__(self, context: Context) -> None:
        self.data: list[Any] = []
        self.options: dict[str, Any] = {}
        self.context = context

    @property
    def key(self) -> str:
        return self.__class__.get_key()

    @classmethod
    def get_key(cls) -> str:
        return cls.__name__.lower().replace("read", "")

    def __init_subclass__(cls) -> None:
        new_key = cls.get_key()
        if new_key in (c.get_key() for c in ReadComponent.read_component_list):
            raise ValueError(f"class key({new_key}) is duplicated with other subclass")
        ReadComponent.read_component_list.append(cls)

    def read_line(self, line: str) -> list[str]:
        """共通の行パース

        * ','区切り
        * 末尾 '.' を削る
        * <param> を Context.parameters で展開
        """
        values: list[str] = []
        for token in line.split(","):
            token = token.strip()
            if token.endswith("."):
                token = token[:-1]
            if token.startswith("<") and token.endswith(">"):
                token_name = token[1:-1]
                token = str(self.context.parameters.get(token_name, token))
            values.append(token)
        return values

    def dump(self) -> NDArray:
        """内部dataをnumpy配列化"""
        try:
            return np.array(self.data, dtype=self.dtype)
        except (TypeError, ValueError):
            return np.array(self.data, dtype="U16")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ReadComponent):
            return False
        if getattr(other, "options", None) is None:
            return False
        return all(other.options[k] == self.options.get(k) for k in other.options)


# ==========================
#  Unknown キーワード用 RawBlock
# ==========================


@dataclass
class RawBlock:
    """未対応キーワードのブロック

    * keyword / options はキーワード行由来
    * lines は「1行ごとのカンマ区切りトークン列」
    """

    keyword: str  # 例: "amplitude", "restart"
    options: dict[str, Any]
    lines: list[list[str]]  # ← 各行は ["A1", "A2", ...] みたいな形
    file_path: Path


# ==========================
#  STEP ブロックの構造
# ==========================


@dataclass
class StepData:
    """*STEP〜*END STEP を表現する構造"""

    name: str  # STEP名 (なければ空文字)
    options: dict[str, Any]
    blocks: list[ReadComponent | RawBlock]


# ==========================
#  キーワード → options 解析
# ==========================


def _parse_rawblock_data_line(line: str, context: Context) -> list[str]:
    """RawBlock 用のデータ行パーサ

    * ',' 区切り
    * 前後スペース削除
    * 末尾 '.' を削除
    * <param> を context.parameters で置換
    """
    values: list[str] = []
    for token in line.split(","):
        token = token.strip()
        if not token:
            values.append("")
            continue

        if token.endswith("."):
            token = token[:-1]

        if token.startswith("<") and token.endswith(">"):
            key = token[1:-1]
            if key in context.parameters:
                token = str(context.parameters[key])

        values.append(token)

    return values


def _replace_param_token(value: str, context: Context | None) -> str:
    """<param> を context.parameters で置換するヘルパ

    Args:
        value: キー行オプションの値
        context: Context (parameters を保持)

    Returns:
        置換後文字列
    """
    if context is None:
        return value

    v = value.strip()
    if v.startswith("<") and v.endswith(">"):
        key = v[1:-1]
        if key in context.parameters:
            return str(context.parameters[key])
    return value


def _parse_keyline_options(
    line: str,
    context: Context | None = None,
) -> tuple[str, dict[str, Any]]:
    """キーワード行を解析して (key, options) を返す

    line は小文字・空白除去済みと想定:
        "*element,elset=eall,type=c3d8" →
        ("element", {"elset": "eall", "type": "c3d8"})
    """
    tokens = [s for s in line.split(",") if s]
    if not tokens:
        raise ValueError(f"invalid key line: {line}")

    key = tokens[0].replace("*", "")
    options: dict[str, Any] = {}

    for tok in tokens[1:]:
        if "=" in tok:
            k, v = tok.split("=", 1)
            v = _replace_param_token(v, context)
            options[k] = v
        elif tok == "generate":
            options["generate"] = True
        else:
            # その他フラグはそのまま True として持つ
            opt_key = _replace_param_token(tok, context)
            options[opt_key] = True

    return key, options


def get_or_create_read_component_from_line(
    line: str,
    context: Context,
    already_created_component_list: list[ReadComponent],
) -> ReadComponent | None:
    """キーワード行から対応する ReadComponent を生成 or 既存インスタンス再利用"""
    key, options = _parse_keyline_options(line, context=context)
    component_cls: type[ReadComponent] | None = None

    for cls in ReadComponent.iter_read_components():
        if cls.get_key() == key:
            component_cls = cls
            break

    if component_cls is None:
        return None

    temp = component_cls(context=context)
    temp.options.update(options)

    for existing in already_created_component_list:
        if isinstance(existing, component_cls) and existing == temp:
            return existing

    return temp


# ==========================
#  各コンポーネント実装
# ==========================


class ReadNode(ReadComponent):
    """*Node"""

    dtype: ClassVar[list] = [
        ("label", "int32"),
        ("x", "float32"),
        ("y", "float32"),
        ("z", "float32"),
    ]

    def read_line(self, line: str) -> None:
        values = super().read_line(line)
        try:
            value = (
                int(values[0]),
                float(values[1]),
                float(values[2]),
                float(values[3]),
            )
        except (IndexError, ValueError):
            value = (int(values[0]), None, None, None)
        self.data.append(value)


class ReadElement(ReadComponent):
    """*Element"""

    def read_line(self, line: str) -> None:
        values = super().read_line(line)
        try:
            self.data.append([int(v) for v in values if v != ""])
        except ValueError as err:
            raise ValueError(f"要素行のパースに失敗しました: {line}") from err


class ReadNset(ReadComponent):
    """*Nset"""

    def read_line(self, line: str) -> None:
        ReadNset._read_line(instance=self, line=line)

    @staticmethod
    def _read_line(instance: ReadComponent, line: str) -> None:
        # ReadComponent.read_line を直接呼ぶ
        values = ReadComponent.read_line(instance, line)

        if "generate" not in instance.options:
            try:
                instance.data.extend([int(v) for v in values if v != ""])
            except Exception:
                instance.data.extend([v for v in values if v != ""])
        else:
            # generate, i.e. start, stop, step
            start, stop, step = (int(i) for i in values)
            if step != 1:
                raise RuntimeError(f"{instance.__class__.__name__}: step '{step}' は未対応 (現状1のみ)")
            if start == stop:
                instance.data.append(start)
            else:
                instance.data.extend(start + i for i in range(stop - start + 1))


class ReadElset(ReadComponent):
    """*Elset"""

    def read_line(self, line: str) -> None:
        # Nset と同じ仕様を流用
        ReadNset._read_line(instance=self, line=line)


class ReadSurface(ReadComponent):
    """*Surface"""

    forbidden_surface_names = [f"s{i + 1}" for i in range(8)] + ["sneg", "spos"]

    def read_line(self, line: str) -> None:
        vals = [str(i) for i in line.split(",")]
        if any([f"s{i + 1}" in line.lower() for i in range(8)]):
            self.data.append([vals[0], vals[1]])
        else:
            self.data += vals


class ReadMaterial(ReadComponent):
    """*Material"""

    def __init__(self, context: Context) -> None:
        super().__init__(context)
        self.context.current_material = self


class MaterialPropertyReadComponent(ReadComponent):
    """*Elastic, *Plastic, *Density などの共通実装"""

    default_options: dict[str, str] | None = None

    def __init__(self, context: Context) -> None:
        super().__init__(context)
        if context.current_material is None:
            # *MATERIAL 外（例: *SURFACE INTERACTION 下）で出現した場合
            # エラーにせず、材料への紐付けをスキップする
            return
        context.current_material.data.append(self)
        if self.default_options:
            for k, v in self.default_options.items():
                self.options.setdefault(k, v)

    def read_line(self, line: str, store_data: bool = True) -> list[list[float]] | None:
        values = super().read_line(line)
        if len(values) == 1 and values[0] == "":
            return None

        # 空文字列（末尾カンマ等）はNoneで埋める
        try:
            rows = [[None if v == "" else float(v) for v in values]]
        except ValueError as e:
            mat = self.context.current_material
            mat_name = mat.options.get("name", "UNKNOWN") if mat else "UNKNOWN"
            print(f"Error: Failed to convert {values} to float (line:{line}, in {mat_name}/*{self.get_key()}) ({e})")
            return None

        if store_data:
            self.data.extend(rows)
            return None
        return rows


# 動的クラス生成（ReadSpecificHeat, ReadDensity, ...）
# globals() に登録しないと pickle が attribute lookup に失敗する
for _k in ["SpecificHeat", "Density", "DamageInitiation", "DamageEvolution", "Creep"]:
    globals()[f"Read{_k}"] = type(
        f"Read{_k}",
        (MaterialPropertyReadComponent,),
        {},
    )


class ReadElastic(MaterialPropertyReadComponent):
    default_options: ClassVar[dict] = dict(type="elastic")


class ReadPlastic(MaterialPropertyReadComponent):
    default_options: ClassVar[dict] = dict(hardening="isotropic")


class Expansion(MaterialPropertyReadComponent):
    default_options: ClassVar[dict] = dict(type="isotropic")


class Conductivity(MaterialPropertyReadComponent):
    default_options: ClassVar[dict] = dict(type="isotropic")


class ElectricalConductivity(MaterialPropertyReadComponent):
    default_options: ClassVar[dict] = dict(type="isotropic")


class ReadBoundary(ReadComponent):
    """*Boundary

    行は「文字列リスト」のまま保持しておき、
    利用側で (set名, dof1, dof2, value) 等に解釈すればよい。
    """

    def read_line(self, line: str) -> None:
        values = super().read_line(line)
        # ここでは文字列のまま保持しておく
        if any(values):
            self.data.append(values)


class ReadProcedure(ReadComponent):
    """*STEP 内で最初に現れるプロシージャキーワード用コンポーネント

    例:
        *STATIC
        *DYNAMIC
        *FREQUENCY
        etc...

    data:
        各行を float 配列化したもの (空文字は np.nan)
    """

    dtype = "float64"

    def __init__(self, context: Context, procedure_keyword: str):
        super().__init__(context)
        # 実際のキーワード名 (例: "static", "dynamic")
        self.procedure_keyword: str = procedure_keyword

    @classmethod
    def get_key(cls) -> str:
        """内部用のkey。実際のキーワードは procedure_keyword に入る。"""
        return "procedure"

    def read_line(self, line: str) -> None:
        """データ行を float 配列に変換（空文字は np.nan）

        例:
            " , 1., 0.1" → [nan, 1.0, 0.1]
        """
        tokens = super().read_line(line)  # <param> 置換済み
        row: list[float] = []
        for t in tokens:
            if t == "" or t is None:
                row.append(float("nan"))
            else:
                try:
                    row.append(float(t))
                except ValueError:
                    # 暴れ値が来たら nan に落とす or 例外にするかは好み次第
                    row.append(float("nan"))
        self.data.append(row)


@dataclass
class SurfaceInteractionBlock:
    """*Surface Interaction + その配下の behavior / friction 等をひとまとめにした論理ブロック"""

    main: RawBlock  # keyword == "surfaceinteraction"
    sub_blocks: list[RawBlock]  # keyword in {"surfacebehavior", "friction", ...}


# ==========================
#  Parameter (*Parameter)
# ==========================


def evaluate_expressions(expr: str) -> float | None:
    """文字列で与えられたPython数式を計算してfloatを返す

    注意:
        * __builtins__ を無効化
        * 数値以外は None を返す
    """
    allowed_globals = {"__builtins__": None}
    try:
        result = eval(expr, allowed_globals, {})
    except Exception:
        return None

    if isinstance(result, (int, float)):
        return float(result)
    return None


class ReadParameter(ReadComponent):
    """*Parameter"""

    def read_line(self, line: str) -> None:
        values = super().read_line(line)
        if not values or "=" not in values[0]:
            raise ValueError(f"*Parameter 行が不正です: {line}")

        key, expr = values[0].split("=", 1)
        key = key.strip()
        expr = self._replace_variables(expr.strip())
        value = evaluate_expressions(expr)

        if value is None:
            # raise ValueError(f"*Parameter の評価に失敗しました: {values[0]} -> {expr}")
            self.context.parameters[key] = None

        self.context.parameters[key] = value

    def _replace_variables(self, expr: str) -> str:
        """式中の識別子を context.parameters で置換（完全一致のみ）"""
        identifiers = set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", expr))
        if not identifiers:
            return expr

        for ident in identifiers:
            if ident in self.context.parameters:
                value = self.context.parameters[ident]
                expr = re.sub(
                    rf"\b{re.escape(ident)}\b",
                    str(value),
                    expr,
                )
        return expr


# ==========================
#  出力用データ構造
# ==========================


@dataclass
class MaterialData:
    name: str
    options: dict[str, Any]
    data: Any


@dataclass
class ABQData:
    """トップレベルの解析済みINP"""

    nodes: dict[str, ReadNode]
    elements: dict[str, ReadElement]
    nsets: dict[str, ReadNset]
    elsets: dict[str, ReadElset]
    surfaces: dict[str, ReadSurface]
    materials: dict[str, dict[str, MaterialData]]
    steps: list[StepData]
    raw_blocks: list[RawBlock]  # STEP外の未対応キーワード


# ==========================
#  メイン: INP 読み込み
# ==========================


def read_inp(inp_filepath: PathList, verbose: bool = True, include_max_depth: int = 5) -> ABQData:
    """Abaqus inpファイルを読み込み、ABQData に変換する

    要件:
        * 対応キーワード: 構造化して dict で取得
        * 未対応キーワード: RawBlock として list[str] 生データで保持
        * *STEP〜*END STEP: StepData としてブロック構造を保持
        * *BOUNDARY: ReadBoundary としてブロック化 (Step内で拾える)
    """
    context = Context()
    all_components: list[ReadComponent] = []

    current_component: ReadComponent | RawBlock | None = None
    current_step: StepData | None = None

    steps: list[StepData] = []
    raw_blocks_top: list[RawBlock] = []

    # ---- パースループ ----
    for file_path, raw_line in read_files_with_unknown_encoding(
        inp_filepath, verbose=verbose, include_max_depth=include_max_depth
    ):
        if not raw_line or raw_line.lstrip().startswith("**"):
            continue

        norm = re.sub(r"\s+", "", raw_line).lower().strip()
        if not norm:
            continue

        if norm.startswith("*"):
            # まず現在のコンポーネントは終了
            current_component = None

            # キー行解析（parameter置換込み）
            key_for_step, options_for_step = _parse_keyline_options(norm, context=context)
            normalized_key_only = re.sub(r"[^a-z]", "", key_for_step)

            # *STEP
            if normalized_key_only == "step":
                raw_name = options_for_step.get("name")
                if raw_name and str(raw_name).strip():
                    step_name = str(raw_name)
                else:
                    step_index = len(steps) + 1
                    step_name = f"Step-{step_index}"
                    options_for_step["name"] = step_name

                current_step = StepData(
                    name=step_name,
                    options=options_for_step,
                    blocks=[],
                )
                steps.append(current_step)
                continue

            # *END STEP
            if normalized_key_only in {"endstep"}:
                current_step = None
                continue

            # ---- STEP 内の最初のキーワード → Procedure ----
            if current_step is not None and not current_step.blocks:
                # ここで key_for_step が実際のプロシージャキーワード
                proc = ReadProcedure(context=context, procedure_keyword=key_for_step)
                proc.options.update(options_for_step)

                current_component = proc
                all_components.append(proc)
                current_step.blocks.append(proc)
                continue

            # ---- 通常キーワード処理 ----
            component = get_or_create_read_component_from_line(
                line=norm,
                context=context,
                already_created_component_list=all_components,
            )

            if component is not None:
                current_component = component
                if component not in all_components:
                    all_components.append(component)
                if current_step is not None and component not in current_step.blocks:
                    current_step.blocks.append(component)
            else:
                # 未対応キーワード → RawBlock
                rb = RawBlock(
                    keyword=key_for_step,
                    options=options_for_step,
                    lines=[],
                    file_path=file_path,
                )
                current_component = rb
                if current_step is not None:
                    current_step.blocks.append(rb)
                else:
                    raw_blocks_top.append(rb)

        else:
            # データ行
            if current_component is None:
                continue

            if isinstance(current_component, ReadComponent):
                current_component.read_line(line=norm)
            elif isinstance(current_component, RawBlock):
                tokens = _parse_rawblock_data_line(raw_line, context)
                current_component.lines.append(tokens)

    # ---- 辞書構築 ----
    nodes: dict[str, ReadNode] = {}
    elements: dict[str, ReadElement] = {}
    nsets: dict[str, ReadNset] = {}
    elsets: dict[str, ReadElset] = {}
    surfaces: dict[str, ReadSurface] = {}
    materials: dict[str, dict[str, MaterialData]] = {}

    for comp in all_components:
        opts = comp.options

        if isinstance(comp, ReadNode):
            nname = opts.get("nset", "default")
            nodes[nname] = comp

        elif isinstance(comp, ReadElement):
            ename = opts.get("elset", "default")
            etype = opts.get("type", "unknown")
            elements[f"{ename},type={etype}"] = comp

        elif isinstance(comp, ReadNset):
            if "nset" in opts:
                nsets[opts["nset"]] = comp

        elif isinstance(comp, ReadElset):
            if "elset" in opts:
                elsets[opts["elset"]] = comp

        elif isinstance(comp, ReadSurface):
            if "name" in opts:
                surfaces[opts["name"]] = comp

        elif isinstance(comp, ReadMaterial):
            if "name" not in opts:
                continue
            mat_name = fix_text(opts["name"])
            mat_dict: dict[str, MaterialData] = {}
            for sub in comp.data:
                sub_key = str(sub.key)
                mat_dict[sub_key] = MaterialData(
                    name=fix_text(sub_key),
                    options=sub.options,
                    data=sub.data,
                )
            materials[mat_name] = mat_dict

    return ABQData(
        nodes=nodes,
        elements=elements,
        nsets=nsets,
        elsets=elsets,
        surfaces=surfaces,
        materials=materials,
        steps=steps,
        raw_blocks=raw_blocks_top,
    )


def abq_to_dict(abq: ABQData) -> dict[str, Any]:
    """ABQData を辞書型へ変換する（JSON化可能な構造へ正規化）。

    メッシュ関連キーワード (Node, Element, Nset, Elset) は要約形式で出力する。

    Args:
        abq (ABQData): 解析データ

    Returns:
        Dict[str, Any]: JSON 変換可能な辞書
    """
    # ノード座標ルックアップテーブル（要素サイズ・ねじれ角計算用）
    nodes_lookup = _build_nodes_lookup(abq)

    def mesh_comp_to_dict(comp: ReadComponent) -> dict[str, Any]:
        """メッシュ関連コンポーネントを要約形式で変換"""
        return _serialize_mesh_component(comp, nodes_lookup)

    def comp_to_dict(comp: ReadComponent) -> dict[str, Any]:
        """メッシュ関連は要約、それ以外は従来通り変換"""
        if comp.key in MESH_SUMMARY_KEYS:
            return mesh_comp_to_dict(comp)
        # numpy array → list
        try:
            data = comp.dump().tolist()
        except Exception:
            data = comp.data
        return {
            "key": comp.key,
            "options": dict(comp.options),
            "data": data,
        }

    def raw_block_to_dict(rb: RawBlock) -> dict[str, Any]:
        return {
            "keyword": rb.keyword,
            "options": dict(rb.options),
            "lines": list(rb.lines),
            "file_path": str(rb.file_path),
        }

    def material_data_to_dict(md: MaterialData) -> dict[str, Any]:
        return {
            "name": md.name,
            "options": dict(md.options),
            "data": md.data,  # material property は list[list[float]] のため変換不要
        }

    def step_to_dict(step: StepData) -> dict[str, Any]:
        blocks = []
        for b in step.blocks:
            if isinstance(b, ReadComponent):
                blocks.append(comp_to_dict(b))
            elif isinstance(b, RawBlock):
                blocks.append(raw_block_to_dict(b))
            else:
                blocks.append({"unknown_block_type": str(type(b))})
        return {
            "name": step.name,
            "options": dict(step.options),
            "blocks": blocks,
        }

    # ---- トップレベル構造 ----

    return {
        "nodes": {name: comp_to_dict(c) for name, c in abq.nodes.items()},
        "elements": {name: comp_to_dict(c) for name, c in abq.elements.items()},
        "nsets": {name: comp_to_dict(c) for name, c in abq.nsets.items()},
        "elsets": {name: comp_to_dict(c) for name, c in abq.elsets.items()},
        "surfaces": {name: comp_to_dict(c) for name, c in abq.surfaces.items()},
        "materials": {
            mat_name: {prop_name: material_data_to_dict(md) for prop_name, md in props.items()}
            for mat_name, props in abq.materials.items()
        },
        "steps": [step_to_dict(s) for s in abq.steps],
        "raw_blocks": [raw_block_to_dict(rb) for rb in abq.raw_blocks],
    }


@dataclass
class BlockDiff:
    """ブロック間の差分情報

    Attributes:
        location: どこで差分が見つかったかを示すパス文字列
        left: 左側(基準)のブロック表現 (dict) または None
        right: 右側(比較対象)のブロック表現 (dict) または None
    """

    location: str
    left: dict[str, Any] | None
    right: dict[str, Any] | None


def _sort_component_data_for_diff(comp: ReadComponent, data: Any) -> Any:
    """差分比較用に、特定コンポーネントの data をソートして正規化する。

    要件:
        - Node, Element: 1列目のラベルでソート
        - Nset, Elset: data（1次元リスト）を文字列としてソート
    """
    key = comp.key

    # numpyの場合は list of list/tuple になっている前提
    # data が "list of row" でなければそのまま返す
    if key in ("node", "element"):
        try:
            # row[0] をラベルとしてソート
            return sorted(data, key=lambda row: row[0])
        except Exception:
            return data

    if key in ("nset", "elset"):
        try:
            return sorted(data, key=lambda v: str(v))
        except Exception:
            return data

    return data


# ==========================
#  メッシュキーワード要約
# ==========================

MESH_SUMMARY_KEYS = {"node", "element", "nset", "elset"}


def _build_nodes_lookup(abq: ABQData) -> dict[int, tuple]:
    """ABQData からノード座標のルックアップテーブルを構築

    Returns:
        {node_label: (x, y, z), ...}
    """
    lookup: dict[int, tuple] = {}
    for _name, comp in abq.nodes.items():
        for row in comp.data:
            label = row[0]
            x = float(row[1]) if row[1] is not None else 0.0
            y = float(row[2]) if row[2] is not None else 0.0
            z = float(row[3]) if row[3] is not None else 0.0
            lookup[int(label)] = (x, y, z)
    return lookup


def _summarize_node_data(data: list) -> dict[str, Any]:
    """Nodeデータを要約

    Args:
        data: [(label, x, y, z), ...]

    Returns:
        {"node_count": int, "x_range": {"min": float, "max": float}, ...}
    """
    if not data:
        return {"node_count": 0}

    xs, ys, zs = [], [], []
    for row in data:
        if len(row) >= 4 and row[1] is not None:
            xs.append(float(row[1]))
            ys.append(float(row[2]))
            zs.append(float(row[3]))

    summary: dict[str, Any] = {"node_count": len(data)}

    if xs:
        summary["x_range"] = {"min": round(min(xs), 6), "max": round(max(xs), 6)}
        summary["y_range"] = {"min": round(min(ys), 6), "max": round(max(ys), 6)}
        summary["z_range"] = {"min": round(min(zs), 6), "max": round(max(zs), 6)}

    return summary


def _quad_warp_angle(
    p1: tuple,
    p2: tuple,
    p3: tuple,
    p4: tuple,
) -> float | None:
    """四辺形のwarp角（度）を計算

    4頂点を2つの三角形に分割し、法線ベクトル間の角度を返す。
    """
    import math

    v1 = (p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2])
    v2 = (p3[0] - p1[0], p3[1] - p1[1], p3[2] - p1[2])
    v3 = (p4[0] - p1[0], p4[1] - p1[1], p4[2] - p1[2])

    # Triangle (P1, P2, P3) の法線
    n1 = (
        v1[1] * v2[2] - v1[2] * v2[1],
        v1[2] * v2[0] - v1[0] * v2[2],
        v1[0] * v2[1] - v1[1] * v2[0],
    )

    # Triangle (P1, P3, P4) の法線
    n2 = (
        v2[1] * v3[2] - v2[2] * v3[1],
        v2[2] * v3[0] - v2[0] * v3[2],
        v2[0] * v3[1] - v2[1] * v3[0],
    )

    norm1 = math.sqrt(n1[0] ** 2 + n1[1] ** 2 + n1[2] ** 2)
    norm2 = math.sqrt(n2[0] ** 2 + n2[1] ** 2 + n2[2] ** 2)

    if norm1 < 1e-10 or norm2 < 1e-10:
        return 0.0

    dot = n1[0] * n2[0] + n1[1] * n2[1] + n1[2] * n2[2]
    cos_angle = max(-1.0, min(1.0, dot / (norm1 * norm2)))

    return math.degrees(math.acos(cos_angle))


def _compute_element_skew(coords: list[tuple]) -> float | None:
    """要素のねじれ角（warp角）を計算

    四辺形/六面体面のwarp角を計算する。
    三角形要素 (3節点) の場合はNoneを返す。
    """
    n = len(coords)

    if n < 4:
        # 三角形: warp角なし
        return None

    if n == 4:
        # 四辺形: warp角を計算
        return _quad_warp_angle(coords[0], coords[1], coords[2], coords[3])

    if n >= 8:
        # 六面体: 各面のwarp角の最大値
        # C3D8ノード順: 底面(0,1,2,3), 上面(4,5,6,7)
        faces = [
            (coords[0], coords[1], coords[2], coords[3]),  # bottom
            (coords[4], coords[5], coords[6], coords[7]),  # top
            (coords[0], coords[1], coords[5], coords[4]),  # front
            (coords[1], coords[2], coords[6], coords[5]),  # right
            (coords[2], coords[3], coords[7], coords[6]),  # back
            (coords[3], coords[0], coords[4], coords[7]),  # left
        ]
        warps = []
        for face in faces:
            w = _quad_warp_angle(*face)
            if w is not None:
                warps.append(w)
        return max(warps) if warps else None

    if n >= 5:
        # 5-6節点: 底面が四辺形の要素（wedge等）の底面のみ
        return _quad_warp_angle(coords[0], coords[1], coords[2], coords[3])

    return None


def _summarize_element_data(
    data: list,
    nodes_lookup: dict[int, tuple] | None = None,
) -> dict[str, Any]:
    """Elementデータを要約

    Args:
        data: [[elem_id, node1, node2, ...], ...]
        nodes_lookup: {node_label: (x, y, z), ...}

    Returns:
        {"element_count": int, "size": {"min", "max", "mean"}, "skew": {"min", "max", "mean"}}
    """
    import math

    if not data:
        return {"element_count": 0}

    summary: dict[str, Any] = {"element_count": len(data)}

    if not nodes_lookup:
        return summary

    sizes: list[float] = []
    skews: list[float] = []

    for row in data:
        node_ids = row[1:]
        coords = [nodes_lookup[nid] for nid in node_ids if nid in nodes_lookup]

        if len(coords) < 2:
            continue

        # Element size: bounding box diagonal
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        zs = [c[2] for c in coords]
        dx = max(xs) - min(xs)
        dy = max(ys) - min(ys)
        dz = max(zs) - min(zs)
        size = math.sqrt(dx * dx + dy * dy + dz * dz)
        sizes.append(size)

        # Skew angle
        skew = _compute_element_skew(coords)
        if skew is not None:
            skews.append(skew)

    if sizes:
        summary["size"] = {
            "min": round(min(sizes), 6),
            "max": round(max(sizes), 6),
            "mean": round(sum(sizes) / len(sizes), 6),
        }

    if skews:
        summary["skew"] = {
            "min": round(min(skews), 6),
            "max": round(max(skews), 6),
            "mean": round(sum(skews) / len(skews), 6),
        }

    return summary


def _summarize_set_data(data: list) -> dict[str, Any]:
    """Nset/Elsetデータを要約

    文字列が割り当てられていればそのまま返す。
    IDのリストの場合はIDの数を返す。
    """
    if not data:
        return {"count": 0}

    # 文字列が含まれているかチェック
    has_strings = any(isinstance(v, str) for v in data)

    if has_strings:
        # 文字列のみ抽出して返す
        names = [str(v) for v in data]
        return {"names": names}
    else:
        return {"id_count": len(data)}


def _serialize_mesh_component(
    comp: ReadComponent,
    nodes_lookup: dict[int, tuple] | None = None,
) -> dict[str, Any]:
    """メッシュ関連コンポーネントを要約形式でシリアライズ"""
    d: dict[str, Any] = {
        "kind": "component",
        "key": comp.key,
        "options": dict(comp.options),
    }

    if comp.key == "node":
        d["summary"] = _summarize_node_data(comp.data)
    elif comp.key == "element":
        d["summary"] = _summarize_element_data(comp.data, nodes_lookup)
    elif comp.key in ("nset", "elset"):
        d["summary"] = _summarize_set_data(comp.data)

    return d


def _serialize_component(comp: ReadComponent, nodes_lookup: dict[int, tuple] | None = None) -> dict[str, Any]:
    """ReadComponent を比較用の dict に正規化

    - メッシュキーワード (node, element, nset, elset) は要約データに置換
    - その他は従来通り dump() → numpy → list 変換
    """
    # メッシュ関連キーワードは要約形式で返す
    if comp.key in MESH_SUMMARY_KEYS:
        return _serialize_mesh_component(comp, nodes_lookup)

    try:
        arr = comp.dump()
        data = arr.tolist()
    except Exception:
        data = comp.data

    data = _sort_component_data_for_diff(comp, data)

    d: dict[str, Any] = {
        "kind": "component",
        "key": comp.key,
        "options": dict(comp.options),
        "data": data,
    }

    # Procedure の procedure_keyword を比較対象に含める
    if isinstance(comp, ReadProcedure):
        d["procedure_keyword"] = comp.procedure_keyword

    return d


def _serialize_rawblock(rb: RawBlock) -> dict[str, Any]:
    """RawBlock を比較用の dict に正規化

    注意:
        - file_path は比較から除外するため含めない
    """
    return {
        "kind": "rawblock",
        "keyword": rb.keyword,
        "options": dict(rb.options),
        "lines": [list(row) for row in rb.lines],
    }


def _serialize_surface_interaction_block(
    sib: SurfaceInteractionBlock,
) -> dict[str, Any]:
    """SurfaceInteractionBlock を比較用の dict に正規化"""
    return {
        "kind": "surfaceinteraction_block",
        "main": _serialize_rawblock(sib.main),
        "sub_blocks": [_serialize_rawblock(b) for b in sib.sub_blocks],
    }


def _serialize_block(
    block: ReadComponent | RawBlock | SurfaceInteractionBlock,
    nodes_lookup: dict[int, tuple] | None = None,
) -> dict[str, Any]:
    """Step.blocks / top-level raw_blocks / SurfaceInteractionBlock を共通形式に変換"""
    if isinstance(block, SurfaceInteractionBlock):
        return _serialize_surface_interaction_block(block)
    if isinstance(block, ReadComponent):
        return _serialize_component(block, nodes_lookup=nodes_lookup)
    if isinstance(block, RawBlock):
        return _serialize_rawblock(block)

    return {
        "kind": "unknown",
        "type": str(type(block)),
        "repr": repr(block),
    }


def _get_block_group_key(
    block: ReadComponent | RawBlock | SurfaceInteractionBlock,
) -> tuple[str, str]:
    """kind/keyword ベースでブロックのグループキーを取得

    - ReadComponent: ("component", comp.key)
    - ReadBoundary:  ("component", "boundary")
    - RawBlock:      ("rawblock", rb.keyword)
    - SurfaceInteractionBlock: ("surfaceinteraction_block", name相当)
    """
    if isinstance(block, SurfaceInteractionBlock):
        # 名前が options にあるならそれをidに使う、なければ "unnamed"
        name = block.main.options.get("name", "unnamed")
        return ("surfaceinteraction_block", str(name))

    if isinstance(block, ReadComponent):
        # Procedure を特別扱いしたければここで条件分け可能
        # 例: if isinstance(block, ReadProcedure): return ("procedure", block.procedure_keyword)
        return ("component", block.key)

    if isinstance(block, RawBlock):
        return ("rawblock", block.keyword)

    return ("unknown", str(type(block)))


# surface interaction 配下として扱うキーワード
SURF_INT_SUB_KEYWORDS = {
    "surfacebehavior",
    "friction",
    "cohesivebehavior",
    "contactdamping",
}


def _build_logical_blocks(
    blocks: list[ReadComponent | RawBlock],
) -> list[ReadComponent | RawBlock | SurfaceInteractionBlock]:
    """元の Step.blocks から、SurfaceInteractionBlock を組み立てた論理ブロック列を構成する。

    仕様:
        - RawBlock.keyword == "surfaceinteraction" を見つけたら main とする
        - 直後に続く RawBlock.keyword が SURF_INT_SUB_KEYWORDS に含まれる間 sub_blocks に追加
        - 次の surfaceinteraction が来たら新しい SurfaceInteractionBlock を開始
    """
    logical: list[ReadComponent | RawBlock | SurfaceInteractionBlock] = []
    i = 0
    n = len(blocks)

    while i < n:
        b = blocks[i]

        if isinstance(b, RawBlock) and b.keyword == "surfaceinteraction":
            main = b
            subs: list[RawBlock] = []
            j = i + 1
            while j < n:
                bj = blocks[j]
                if isinstance(bj, RawBlock) and bj.keyword in SURF_INT_SUB_KEYWORDS:
                    subs.append(bj)
                    j += 1
                else:
                    break
            logical.append(SurfaceInteractionBlock(main=main, sub_blocks=subs))
            i = j
        else:
            logical.append(b)
            i += 1

    return logical


# 順不同で扱う (kind, id) の候補
# kind は _get_block_group_key が返す第1要素
# id   は 第2要素

ORDERLESS_GROUPS = {
    ("component", "surface"),  # *Surface
    ("component", "boundary"),  # *Boundary
    ("rawblock", "contact"),  # *Contact
    ("rawblock", "contact pair"),  # *Contact
    ("rawblock", "contactproperty"),  # *Contact Property
    # 必要なら追加
    ("surfaceinteraction_block", "unnamed"),  # nameなしの SurfaceInteraction
    # name付きも基本順不同でいいなら以下で一括扱い:
    # ("surfaceinteraction_block", "<ANY>") という指定はできないので、
    # 実装側では kind だけで判定してもよい
}

# kind だけで判定したい場合はこちらを併用
ORDERLESS_KINDS = {
    "surfaceinteraction_block",
}


def _is_orderless_group(kind: str, gid: str) -> bool:
    if (kind, gid) in ORDERLESS_GROUPS:
        return True
    return kind in ORDERLESS_KINDS


def _diff_block_groups(
    left_blocks: list[ReadComponent | RawBlock | SurfaceInteractionBlock],
    right_blocks: list[ReadComponent | RawBlock | SurfaceInteractionBlock],
    base_location: str,
    left_nodes_lookup: dict[int, tuple] | None = None,
    right_nodes_lookup: dict[int, tuple] | None = None,
) -> list[BlockDiff]:
    """ブロック列を kind/keyword グループ単位に分けて差分比較する。

    - group key: (kind, id) = _get_block_group_key(...)
    - 順不同扱いグループ: multisetとして比較（単純にはソート済みリスト比較）
    - それ以外: インデックス順に 1:1 対応で比較
    """
    diffs: list[BlockDiff] = []

    # グループ化
    from collections import defaultdict

    left_groups: dict[tuple[str, str], list[Any]] = defaultdict(list)
    right_groups: dict[tuple[str, str], list[Any]] = defaultdict(list)

    for b in left_blocks:
        k = _get_block_group_key(b)
        left_groups[k].append(b)

    for b in right_blocks:
        k = _get_block_group_key(b)
        right_groups[k].append(b)

    all_keys = set(left_groups.keys()) | set(right_groups.keys())

    for key in sorted(all_keys):
        kind, gid = key
        loc_group = f"{base_location}::{kind}:{gid}"

        lb = left_groups.get(key, [])
        rb = right_groups.get(key, [])

        # 片側にしかないグループ
        if not lb:
            # 右側のみ
            for idx, b in enumerate(rb):
                diffs.append(
                    BlockDiff(
                        location=f"{loc_group}[{idx}]",
                        left=None,
                        right=_serialize_block(b, nodes_lookup=right_nodes_lookup),
                    )
                )
            continue

        if not rb:
            # 左側のみ
            for idx, b in enumerate(lb):
                diffs.append(
                    BlockDiff(
                        location=f"{loc_group}[{idx}]",
                        left=_serialize_block(b, nodes_lookup=left_nodes_lookup),
                        right=None,
                    )
                )
            continue

        # 両方に存在する場合
        if _is_orderless_group(kind, gid):
            # 順不同比較 → serializeしてソート
            left_ser = [_serialize_block(b, nodes_lookup=left_nodes_lookup) for b in lb]
            right_ser = [_serialize_block(b, nodes_lookup=right_nodes_lookup) for b in rb]

            # ソートキーには repr(dict) を雑に使う（厳密さより簡便性優先）
            left_sorted = sorted(left_ser, key=lambda d: repr(d))
            right_sorted = sorted(right_ser, key=lambda d: repr(d))

            if left_sorted != right_sorted:
                # グループ単位で差分報告（細かい1つずつの対応付けは後で拡張）
                diffs.append(
                    BlockDiff(
                        location=loc_group,
                        left=left_sorted,
                        right=right_sorted,
                    )
                )

        else:
            # 順序を守って 1:1 対応で比較
            max_len = max(len(lb), len(rb))
            for idx in range(max_len):
                loc = f"{loc_group}[{idx}]"
                bl = lb[idx] if idx < len(lb) else None
                br = rb[idx] if idx < len(rb) else None

                if bl is None:
                    diffs.append(
                        BlockDiff(
                            location=loc,
                            left=None,
                            right=_serialize_block(br, nodes_lookup=right_nodes_lookup),
                        )
                    )
                    continue

                if br is None:
                    diffs.append(
                        BlockDiff(
                            location=loc,
                            left=_serialize_block(bl, nodes_lookup=left_nodes_lookup),
                            right=None,
                        )
                    )
                    continue

                sl = _serialize_block(bl, nodes_lookup=left_nodes_lookup)
                sr = _serialize_block(br, nodes_lookup=right_nodes_lookup)
                if sl != sr:
                    diffs.append(
                        BlockDiff(
                            location=loc,
                            left=sl,
                            right=sr,
                        )
                    )

    return diffs


def _diff_block_lists(
    left_blocks: list[ReadComponent | RawBlock],
    right_blocks: list[ReadComponent | RawBlock],
    base_location: str,
    left_nodes_lookup: dict[int, tuple] | None = None,
    right_nodes_lookup: dict[int, tuple] | None = None,
) -> list[BlockDiff]:
    """ブロックのリスト同士を単純比較し、差分だけ返す

    * インデックスごとに 1:1 対応させて比較
    * 長さが違う場合は足りない側を None として扱う
    """
    diffs: list[BlockDiff] = []

    max_len = max(len(left_blocks), len(right_blocks))
    for idx in range(max_len):
        loc = f"{base_location}[{idx}]"

        left_block = left_blocks[idx] if idx < len(left_blocks) else None
        right_block = right_blocks[idx] if idx < len(right_blocks) else None

        if left_block is None:
            if right_block is None:
                raise ValueError("ask GPT")
            diffs.append(
                BlockDiff(
                    location=loc,
                    left=None,
                    right=_serialize_block(right_block, nodes_lookup=right_nodes_lookup),
                )
            )
            continue

        if right_block is None:
            diffs.append(
                BlockDiff(
                    location=loc,
                    left=_serialize_block(left_block, nodes_lookup=left_nodes_lookup),
                    right=None,
                )
            )
            continue

        left_ser = _serialize_block(left_block, nodes_lookup=left_nodes_lookup)
        right_ser = _serialize_block(right_block, nodes_lookup=right_nodes_lookup)

        if left_ser != right_ser:
            diffs.append(
                BlockDiff(
                    location=loc,
                    left=left_ser,
                    right=right_ser,
                )
            )

    return diffs


def _diff_mesh_dicts(
    diffs: list[BlockDiff],
    left_dict: dict[str, ReadComponent],
    right_dict: dict[str, ReadComponent],
    category: str,
    left_nodes_lookup: dict[int, tuple] | None = None,
    right_nodes_lookup: dict[int, tuple] | None = None,
) -> None:
    """トップレベルのメッシュデータ辞書（nodes/elements/nsets/elsets）を比較

    要約形式で比較し、差分があればdiffsに追加する。
    """
    all_names = set(left_dict.keys()) | set(right_dict.keys())

    for name in sorted(all_names):
        loc = f"{category}.{name}"
        left_comp = left_dict.get(name)
        right_comp = right_dict.get(name)

        if left_comp is None and right_comp is not None:
            diffs.append(
                BlockDiff(
                    location=loc,
                    left=None,
                    right=_serialize_component(right_comp, nodes_lookup=right_nodes_lookup),
                )
            )
        elif right_comp is None and left_comp is not None:
            diffs.append(
                BlockDiff(
                    location=loc,
                    left=_serialize_component(left_comp, nodes_lookup=left_nodes_lookup),
                    right=None,
                )
            )
        elif left_comp is not None and right_comp is not None:
            left_ser = _serialize_component(left_comp, nodes_lookup=left_nodes_lookup)
            right_ser = _serialize_component(right_comp, nodes_lookup=right_nodes_lookup)
            if left_ser != right_ser:
                diffs.append(BlockDiff(location=loc, left=left_ser, right=right_ser))


def diff_abq_blocks(left: ABQData, right: ABQData) -> list[BlockDiff]:
    """2つの ABQData の差分を取り、差があるブロックのみ抽出する。

    現状仕様:
        - トップレベルのメッシュデータ (nodes, elements, nsets, elsets) を要約形式で比較
        - STEP 単位で、Step.blocks を論理ブロック (SurfaceInteractionBlock) に変換して比較
        - kind/keyword (=_get_block_group_key) が同じブロック同士をグループ化して比較
        - メッシュ関連キーワード (Node, Element, Nset, Elset) は要約データに置換して比較
        - surface, contact, contact property, boundary, surface interaction block は順不同扱い
    """
    diffs: list[BlockDiff] = []

    # ---- ノード座標ルックアップテーブルを構築 ----
    left_nodes_lookup = _build_nodes_lookup(left)
    right_nodes_lookup = _build_nodes_lookup(right)

    # ---- トップレベルのメッシュデータ比較（要約形式）----
    _diff_mesh_dicts(diffs, left.nodes, right.nodes, "nodes", left_nodes_lookup, right_nodes_lookup)
    _diff_mesh_dicts(diffs, left.elements, right.elements, "elements", left_nodes_lookup, right_nodes_lookup)
    _diff_mesh_dicts(diffs, left.nsets, right.nsets, "nsets", left_nodes_lookup, right_nodes_lookup)
    _diff_mesh_dicts(diffs, left.elsets, right.elsets, "elsets", left_nodes_lookup, right_nodes_lookup)

    # ---- STEP 配下の blocks の比較 ----
    max_steps = max(len(left.steps), len(right.steps))

    for si in range(max_steps):
        # 片側にしか step がない場合 → その step の全ブロックを丸ごと差分として扱う
        if si >= len(left.steps):
            step_loc = f"step[{si}]"
            step = right.steps[si]
            logical_blocks = _build_logical_blocks(step.blocks)
            for idx, blk in enumerate(logical_blocks):
                diffs.append(
                    BlockDiff(
                        location=f"{step_loc}.blocks[{idx}]",
                        left=None,
                        right=_serialize_block(blk, nodes_lookup=right_nodes_lookup),
                    )
                )
            continue

        if si >= len(right.steps):
            step_loc = f"step[{si}]"
            step = left.steps[si]
            logical_blocks = _build_logical_blocks(step.blocks)
            for idx, blk in enumerate(logical_blocks):
                diffs.append(
                    BlockDiff(
                        location=f"{step_loc}.blocks[{idx}]",
                        left=_serialize_block(blk, nodes_lookup=left_nodes_lookup),
                        right=None,
                    )
                )
            continue

        # 両方に step がある場合
        left_step = left.steps[si]
        right_step = right.steps[si]

        # STEPメタ情報の差
        if (left_step.name != right_step.name) or (left_step.options != right_step.options):
            diffs.append(
                BlockDiff(
                    location=f"step[{si}].meta",
                    left={"name": left_step.name, "options": dict(left_step.options)},
                    right={
                        "name": right_step.name,
                        "options": dict(right_step.options),
                    },
                )
            )

        # 論理ブロック列に変換
        left_logical = _build_logical_blocks(left_step.blocks)
        right_logical = _build_logical_blocks(right_step.blocks)

        # kind/keyword group 単位で比較
        diffs.extend(
            _diff_block_groups(
                left_blocks=left_logical,
                right_blocks=right_logical,
                base_location=f"step[{si}].blocks",
                left_nodes_lookup=left_nodes_lookup,
                right_nodes_lookup=right_nodes_lookup,
            )
        )

    # ---- STEP 外の raw_blocks の比較 ----
    left_top_logical = _build_logical_blocks(left.raw_blocks)
    right_top_logical = _build_logical_blocks(right.raw_blocks)

    diffs.extend(
        _diff_block_groups(
            left_blocks=left_top_logical,
            right_blocks=right_top_logical,
            base_location="top.raw_blocks",
            left_nodes_lookup=left_nodes_lookup,
            right_nodes_lookup=right_nodes_lookup,
        )
    )

    return diffs


# ==========================
#  Diff サマリー生成
# ==========================


def format_diff_summary_table(diffs: list[BlockDiff]) -> str:
    """BlockDiffのリストからMarkdownテーブル形式のサマリーを生成

    Args:
        diffs: BlockDiffのリスト

    Returns:
        Markdownテーブル形式の文字列
    """
    if not diffs:
        return "差分なし"

    lines = ["| Location | Status | Details |", "|----------|--------|---------|"]

    for diff in diffs:
        location = diff.location
        if diff.left is None:
            status = "追加"
            details = "右側のみに存在"
        elif diff.right is None:
            status = "削除"
            details = "左側のみに存在"
        else:
            status = "変更"
            details = "両側で異なる"

        lines.append(f"| {location} | {status} | {details} |")

    return "\n".join(lines)


def format_diff_blocks_markdown(diffs: list[BlockDiff]) -> str:
    """BlockDiffのリストからMarkdown形式の詳細差分ブロックを生成

    Args:
        diffs: BlockDiffのリスト

    Returns:
        Markdown形式の差分ブロック
    """
    if not diffs:
        return "差分なし"

    lines = []

    for diff in diffs:
        lines.append(f"## {diff.location}")
        lines.append("")

        if diff.left is None:
            lines.append("### 追加")
            lines.append("```json")
            lines.append(str(diff.right))
            lines.append("```")
        elif diff.right is None:
            lines.append("### 削除")
            lines.append("```json")
            lines.append(str(diff.left))
            lines.append("```")
        else:
            lines.append("### 変更")
            lines.append("#### 左側（基準）")
            lines.append("```json")
            lines.append(str(diff.left))
            lines.append("```")
            lines.append("#### 右側（比較対象）")
            lines.append("```json")
            lines.append(str(diff.right))
            lines.append("```")

        lines.append("")

    return "\n".join(lines)


def _format_dict_lines(d: dict[str, Any] | None, prefix: str) -> list[str]:
    """辞書をキー単位で+/-表記の行に変換する"""
    if d is None:
        return []
    lines = []
    for key, value in sorted(d.items()):
        val_str = str(value)
        # 長い値は1行にまとめる
        lines.append(f"{prefix} {key}: {val_str}")
    return lines


def format_diff_unified_markdown(diffs: list[BlockDiff]) -> str:
    """BlockDiffのリストから+/-形式のunified diff風Markdownを生成

    追加行は "+" 、削除行は "-" で表示し、変更箇所を視覚的に示す。
    既存のformat_diff_blocks_markdown()の補完として使用する。

    Args:
        diffs: BlockDiffのリスト

    Returns:
        +/-形式のunified diff風Markdown文字列
    """
    if not diffs:
        return "差分なし"

    lines: list[str] = []

    for diff in diffs:
        lines.append(f"## {diff.location}")
        lines.append("")

        if diff.left is None and diff.right is not None:
            # 追加: 右側のみ
            lines.append("```diff")
            for line in _format_dict_lines(diff.right, "+"):
                lines.append(line)
            lines.append("```")
        elif diff.right is None and diff.left is not None:
            # 削除: 左側のみ
            lines.append("```diff")
            for line in _format_dict_lines(diff.left, "-"):
                lines.append(line)
            lines.append("```")
        elif diff.left is not None and diff.right is not None:
            # 変更: 共通キーの差分を表示
            all_keys = sorted(set(list(diff.left.keys()) + list(diff.right.keys())))
            lines.append("```diff")
            for key in all_keys:
                left_val = diff.left.get(key)
                right_val = diff.right.get(key)
                if left_val == right_val:
                    lines.append(f"  {key}: {left_val}")
                elif left_val is None:
                    lines.append(f"+ {key}: {right_val}")
                elif right_val is None:
                    lines.append(f"- {key}: {left_val}")
                else:
                    lines.append(f"- {key}: {left_val}")
                    lines.append(f"+ {key}: {right_val}")
            lines.append("```")

        lines.append("")

    return "\n".join(lines)


def generate_diff_props(
    inp_filepath1: str,
    inp_filepath2: str,
    verbose: bool = False,
) -> dict[str, str]:
    """2つのinpファイルの差分を解析し、propsに追加する情報を生成

    Args:
        inp_filepath1: 比較元のinpファイルパス
        inp_filepath2: 比較先のinpファイルパス
        verbose: 詳細ログを出力するか

    Returns:
        propsに追加する辞書 {"diff_summary": テーブル, "diff_details": 詳細差分}
    """
    abq1 = read_inp(inp_filepath1, verbose=verbose)
    abq2 = read_inp(inp_filepath2, verbose=verbose)

    diffs = diff_abq_blocks(abq1, abq2)

    summary_table = format_diff_summary_table(diffs)
    details_markdown = format_diff_blocks_markdown(diffs)
    unified_markdown = format_diff_unified_markdown(diffs)

    return {
        "diff_summary": summary_table,
        "diff_details": details_markdown,
        "diff_unified": unified_markdown,
    }
