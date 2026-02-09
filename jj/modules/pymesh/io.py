import os
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator, Optional

import chardet
import numpy as np
from numpy.typing import NDArray

from .misc.data import create_custom_meta

read_component_list = []
ReadComponentMeta = create_custom_meta(
    subclasses_list=read_component_list, name_list=[]
)


class ReadComponent(metaclass=ReadComponentMeta):
    dtype = "int32"

    def __init__(self):
        self.data: list = []
        self.options: dict = {}

    @property
    def key(self) -> str:
        return ReadComponent.get_key_from_subclass(subcls=self.__class__)

    @staticmethod
    def get_key_from_subclass(subcls: "ReadComponent"):
        return subcls.__name__.lower().replace("read", "")

    @staticmethod
    def get_component_from_key_line_or_from_list(
        key_line: str, component_list: list["ReadComponent"]
    ) -> "ReadComponent":
        component = ReadComponent.get_component_from_key_line(key_line=key_line)
        for i in component_list:
            if component == i:
                component = i
                break
        return component

    @staticmethod
    def get_component_from_key_line(key_line: str) -> "ReadComponent":
        key = ReadComponent.get_key_from_line(key_line)
        for component in read_component_list:
            component: ReadComponent
            if ReadComponent.get_key_from_subclass(component) == key:
                return component.from_key_line(key_line=key_line)
        # raise ValueError(f"No match components with keywords('{key}')")
        return None

    @staticmethod
    def get_key_from_line(key_line: str) -> str:
        return key_line.split(",")[0].replace("*", "")

    @classmethod
    def from_key_line(cls, key_line: str) -> "ReadComponent":
        instance = cls()
        key, options = "", {}
        for i in key_line.split(","):
            if "=" in i:
                options_i = i.split("=")
                options[options_i[0]] = options_i[1]
            elif i == "generate":
                options["generate"] = True
            else:
                key = i.replace("*", "")
        if instance.key != key:
            raise ValueError
        instance.options = options
        return instance

    def __init_subclass__(cls):
        if ReadComponent.get_key_from_subclass(cls) in [
            ReadComponent.get_key_from_subclass(i) for i in read_component_list
        ]:
            raise ValueError(f"class key({cls.key}) is duplicated with other subclass")

    def read_line(self, line: str):
        raise NotImplementedError

    def dump(self) -> NDArray:
        try:
            return np.array(self.data, dtype=self.dtype)
        except Exception:
            return np.array(self.data, dtype="U16")

    def __eq__(self, other: "ReadComponent") -> bool:
        if getattr(other, "options", None) is None:
            return False
        return all([v == self.options.get(k, None) for k, v in other.options.items()])


class ReadNode(ReadComponent):
    dtype = [
        ("label", "int32"),
        ("x", "float32"),
        ("y", "float32"),
        ("z", "float32"),
    ]

    def __init__(self):
        super().__init__()

    def read_line(self, line: str):
        values = line.split(",")
        try:
            self.data.append(
                (int(values[0]), float(values[1]), float(values[2]), float(values[3]))
            )
        except Exception:
            self.data.append((int(values[0]), None, None, None))


class ReadElement(ReadComponent):
    def __init__(self):
        super().__init__()
        self._former_data = None

    def read_line(self, line: str):
        data = [int(j) for j in line.split(",") if j != ""]
        if line.endswith(","):
            if self._former_data is not None:
                raise RuntimeError("何かヤバい…！")
            self._former_data = data
        else:
            if self._former_data is not None:
                data = self._former_data + data
                self._former_data = None
            self.data.append(data)


class ReadNset(ReadComponent):
    def read_line(self, line: str):
        ReadNset._read_line(instance=self, line=line)

    @staticmethod
    def _read_line(instance, line: str):
        if "generate" not in instance.options.keys():
            instance.data += [str(i) for i in line.split(",")]
        else:
            start, stop, step = (int(i) for i in line.split(","))
            if step != 1:
                raise RuntimeError(
                    f"{instance.__class__.__name__}: step '{step}' is specified for generate option, only step '1' is currently allowed"
                )
            if start == stop:
                instance.data += [start]
            else:
                instance.data += [start + i for i in range(stop - start + 1)]


class ReadElset(ReadComponent):
    def read_line(self, line: str):
        ReadNset._read_line(instance=self, line=line)


class ReadSurface(ReadComponent):
    def read_line(self, line: str):
        vals = [str(i) for i in line.split(",")]
        if any([f"s{i + 1}" in line.lower() for i in range(8)]):
            self.data.append([vals[0], vals[1]])
        else:
            self.data += vals


@dataclass
class MeshData:
    nodes: dict[str, ReadNode]
    elements: dict[str, ReadElement]
    nsets: dict[str, ReadNset]
    elsets: dict[str, ReadElset]
    surfaces: dict[str, ReadSurface]


def detect_file_encoding(file_path: str, n: int = 100, sample_size: int = 1024) -> str:
    """
    ファイル全体からランダムサンプリングしてエンコーディングを推定する。

    Args:
        file_path (str): 対象ファイルのパス
        n (int): サンプリング回数（行単位）
        sample_size (int): 各サンプルの最大バイト数（過剰なメモリ使用を避ける）

    Returns:
        str: 推定エンコーディング。失敗時は None。
    """
    file_size = os.path.getsize(file_path)
    samples = []

    with open(file_path, "rb") as f:
        for _ in range(n):
            # ランダムな位置にseek（安全のため、sample_size分の余裕を見て制限）
            pos = random.randint(0, max(0, file_size - sample_size))
            f.seek(pos)
            chunk = f.read(sample_size)
            samples.append(chunk)

    # バイト列を結合して推定
    data = b"".join(samples)
    result = chardet.detect(data)
    return result.get("encoding")


def read_inp(inp_filepath: list[str] | str) -> MeshData:
    if not isinstance(inp_filepath, list):
        inp_filepath = [inp_filepath]

    for i in inp_filepath:
        normalize_file(i, target_encoding="utf-8", newline="\n")

    # exit()

    def get_lines(inp_filepath: str, _n: int = 100) -> Generator[str, None, None]:
        def _read(encoding: str) -> Generator[str, None, None]:
            with open(inp_filepath, encoding=encoding) as f:
                for line in f:
                    line = re.sub(r"\s+", "", line.strip())
                    if line.startswith("**"):
                        continue
                    elif line.lower().startswith("*include"):
                        include_file = line.lower().split("input=")[-1]
                        dirpath = os.path.dirname(inp_filepath)
                        if not dirpath:
                            dirpath += "./"
                        else:
                            dirpath += "/"
                        include_file = dirpath + include_file
                        if os.path.exists(include_file):
                            yield from get_lines(include_file)
                        else:
                            print(
                                UserWarning(
                                    f"FileNotFoundWarning: {include_file} does not exists. ({inp_filepath})"
                                )
                            )
                    else:
                        yield line.lower()

        success = False
        encoding = detect_file_encoding(inp_filepath, n=100)
        encoding_list = ["utf-8"] + [encoding] + ["shift_jis", "ascii", "cp932"]
        encoding_list = list(dict.fromkeys(encoding_list))
        # print(encoding_list)
        for encoding_i in encoding_list:
            lines = []
            try:
                # yield from _read(encoding_i)
                lines = list(_read(encoding_i))
                success = True
                break
            except Exception:
                print(
                    f"Failed to open {inp_filepath} with encoding '{encoding_i}'. Retrying to open with the others"
                )
        if not isinstance(lines, list):
            raise ValueError
        if success:
            yield from lines
        else:
            # print(f"Failed to open {inp_filepath} with encoding '{encoding_i}'.")
            raise RuntimeError(
                f"Failed to open {inp_filepath} with encoding '{encoding_i}'."
            )

    lines = []
    for inp_filepath in inp_filepath:
        lines += list(get_lines(inp_filepath))

    # for i in lines:
    # print(i)

    all_components = []
    current_component = None
    for i, line in enumerate(lines):
        line: str
        line = line.strip()
        if line.startswith("*"):
            current_component = ReadComponent.get_component_from_key_line_or_from_list(
                key_line=line, component_list=all_components
            )
            if current_component is not None:
                all_components.append(current_component)
        elif current_component is None:
            # raise ValueError(
            # f"first line '{line}'is not key line ('not starts with *')"
            # )
            pass
        else:
            try:
                current_component.read_line(line=line)
            except Exception as e:
                print(line)
                raise RuntimeError(
                    f"Error: Failed to read inp file, line:{i + 1}"
                ) from e

    return MeshData(
        nodes={i.options["nset"]: i for i in all_components if i.key == "node"},
        elements={
            f"{i.options['elset']},type={i.options['type']}": i
            for i in all_components
            if i.key == "element"
        },
        nsets={i.options["nset"]: i for i in all_components if i.key == "nset"},
        elsets={i.options["elset"]: i for i in all_components if i.key == "elset"},
        surfaces={i.options["name"]: i for i in all_components if i.key == "surface"},
    )


def normalize_file(
    filepath: str | Path,
    target_encoding: str = "utf-8",
    newline: str = "\n",
) -> None:
    """
    改行コードとエンコーディングを強制的に統一する関数。

    Args:
        filepath (str | Path): 対象ファイルのパス
        target_encoding (str): 出力ファイルの文字コード（例: "utf-8", "utf-8-sig", "cp932"）
        newline (str): 改行コード。"\n" (LF), "\r\n" (CRLF), "\r" (CR) のいずれか

    Raises:
        UnicodeDecodeError: デコード失敗時
    """
    filepath = Path(filepath)

    # テキストを読み込み
    try:
        lines = filepath.read_text(encoding="utf-8").splitlines()
    except Exception:
        lines = filepath.read_text(encoding="shift_jis").splitlines()

    # 空白や改行だけの行を除去
    non_blank_lines = [line for line in lines if line.strip() != ""]

    # 改行コードは \n に統一して再保存
    filepath.write_text(newline.join(non_blank_lines), encoding="utf-8")


def merge_included_inp_files(
    inp_filepath: str, output_filepath: Optional[str] = None
) -> str:
    def get_lines(inp_filepath: str, _n: int = 100) -> Generator[str, None, None]:
        def _read(encoding: str) -> Generator[str, None, None]:
            with open(inp_filepath, encoding=encoding) as f:
                for line in f:
                    # line = re.sub(r"\s+", "", line.strip())
                    line = line.strip()
                    if line.lower().startswith("*include"):
                        include_file = line.lower().split("input=")[-1]
                        dirpath = os.path.dirname(inp_filepath)
                        if not dirpath:
                            dirpath += "./"
                        else:
                            dirpath += "/"
                        include_file = dirpath + include_file
                        if os.path.exists(include_file):
                            yield from get_lines(include_file)
                        else:
                            print(
                                UserWarning(
                                    f"FileNotFoundWarning: {include_file} does not exists."
                                )
                            )
                    else:
                        yield line.lower()

        success = False
        encoding = detect_file_encoding(inp_filepath, n=100)
        encoding_list = ["utf-8"] + [encoding] + ["shift_jis", "ascii", "cp932"]
        encoding_list = list(dict.fromkeys(encoding_list))
        # print(encoding_list)
        for encoding_i in encoding_list:
            lines = []
            try:
                # yield from _read(encoding_i)
                lines = list(_read(encoding_i))
                success = True
                break
            except Exception:
                print(
                    f"Failed to open {inp_filepath} with encoding '{encoding_i}'. Retrying to open with the others"
                )
        if not isinstance(lines, list):
            raise ValueError
        if success:
            yield from lines
        else:
            # print(f"Failed to open {inp_filepath} with encoding '{encoding_i}'.")
            raise RuntimeError(
                f"Failed to open {inp_filepath} with encoding '{encoding_i}'."
            )

    lines = list(get_lines(inp_filepath))
    # 元は text = lines[0] + "\n".join(lines[0:]) になっているが、
    # 1 行目が重複するのでシンプルに join する
    text = "\n".join(lines)
    if output_filepath:
        with open(output_filepath, "w") as f:
            f.write(text)
    return text


@dataclass
class LinearElasticMaterial:
    """線形等方弾性材料."""

    name: str
    young: float
    poisson: float


@dataclass
class SolidSectionAssignment:
    """solid section による elset→material 割当."""

    elset: str
    material: str


@dataclass
class BoundaryConditionSpec:
    """*boundary 1 行分の情報."""

    set_name: str
    dof_start: int
    dof_end: int
    value: float
    bc_type: str = "displacement"  # type=displacement 前提


@dataclass
class LoadConditionSpec:
    """*boundary 1 行分の情報."""

    set_name: str
    dof: int
    value: float
    bc_type: str = "cload"


@dataclass
class InpStructure:
    """物性・割当・境界条件の構造化結果."""

    materials: dict[str, LinearElasticMaterial]
    solid_sections: list[SolidSectionAssignment]
    boundaries: list[BoundaryConditionSpec]
    loads: list[LoadConditionSpec]


def parse_inp_structure_from_text(text: str) -> InpStructure:
    """Abaqus .inp テキストから物性・solid section・境界を抽出する.

    想定するキーワード:
        *material, name=NAME
        *elastic
          E, nu
        *solid section, material=NAME, elset=P1
        *boundary, type=displacement
          GFIX, 1, 3, 0.
          GMOVE, 1, 1, 1.

    Args:
        text: include 展開済み・小文字化済みの .inp テキスト

    Returns:
        InpStructure: 物性・solid section・境界条件のまとめ
    """
    materials: dict[str, LinearElasticMaterial] = {}
    solid_sections: list[SolidSectionAssignment] = []
    boundaries: list[BoundaryConditionSpec] = []
    loads: list[LoadConditionSpec] = []

    current_material_name: Optional[str] = None
    expect_elastic: bool = False
    in_boundary: bool = False
    in_load: bool = False
    current_boundary_type: str = "displacement"
    current_load_type: str = "cload"

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("**"):
            # 空行・コメント行はスキップ
            continue

        line_l = line.lower()

        # キーワード行
        if line_l.startswith("*"):
            in_boundary = False  # 他のキーワードが来たら boundary ブロック終了
            in_load = False

            # "*material, name=cu" → key="material", options={"name": "cu"}
            parts = [p.strip() for p in line_l.split(",")]
            key = parts[0].lstrip("*").strip()
            opts: dict[str, str] = {}
            for p in parts[1:]:
                if "=" in p:
                    k, v = p.split("=", 1)
                    opts[k.strip()] = v.strip()

            if key == "material":
                current_material_name = opts.get("name")
                expect_elastic = False

            elif key == "elastic":
                # 直前の *material の elastic ブロックだと解釈
                if current_material_name is not None:
                    expect_elastic = True

            elif key in ("solid section", "solidsection"):
                mat = opts.get("material")
                elset = opts.get("elset")
                if mat and elset:
                    solid_sections.append(
                        SolidSectionAssignment(elset=elset, material=mat)
                    )

            elif key == "boundary":
                in_boundary = True
                current_boundary_type = opts.get("type", "displacement")

            elif key == "cload":
                in_load = True
                current_load_type = "cload"

            else:
                # 他のキーワードが来たら elastic ブロックも打ち切る
                expect_elastic = False

            continue  # 次行へ

        # ここからはデータ行

        # elastic の最初の 1 行だけ読む（線形等方弾性）
        if expect_elastic and current_material_name is not None:
            vals = [v.strip() for v in line_l.split(",") if v.strip()]
            try:
                E = float(vals[0])
                nu = float(vals[1])
            except (IndexError, ValueError):
                # 数値変換に失敗したら無視
                continue

            materials[current_material_name] = LinearElasticMaterial(
                name=current_material_name,
                young=E,
                poisson=nu,
            )
            # 線形等方弾性なので 1 行だけ採用
            expect_elastic = False
            continue

        # boundary ブロック内
        if in_boundary:
            # 例: "gfix, 1, 3, 0."
            vals = [v.strip() for v in line_l.split(",") if v.strip()]
            if len(vals) < 4:
                vals.append(0.0)
                # continue
            set_name = vals[0]
            try:
                dof_start = int(vals[1])
                dof_end = int(vals[2])
                value = float(vals[3])
            except ValueError:
                continue

            boundaries.append(
                BoundaryConditionSpec(
                    set_name=set_name,
                    dof_start=dof_start,
                    dof_end=dof_end,
                    value=value,
                    bc_type=current_boundary_type,
                )
            )

        # cload ブロック内
        if in_load:
            # 例: "gfix, 1, 1.e-3"
            vals = [v.strip() for v in line_l.split(",") if v.strip()]
            if len(vals) < 3:
                continue
            set_name = vals[0]
            try:
                dof = int(vals[1])
                value = float(vals[2])
            except ValueError:
                continue

            loads.append(
                LoadConditionSpec(
                    set_name=set_name,
                    dof=dof,
                    value=value,
                    bc_type=current_load_type,
                )
            )

    return InpStructure(
        materials=materials,
        solid_sections=solid_sections,
        boundaries=boundaries,
        loads=loads,
    )


def parse_inp_structure(inp_filepath: str) -> InpStructure:
    """Abaqus .inp ファイルから物性・solid section・境界条件を抽出する.

    include を展開し、小文字化されたテキストを元に parse する。
    メッシュ情報は扱わない（pymesh 側で処理する前提）。

    Args:
        inp_filepath: 対象 .inp ファイルパス

    Returns:
        InpStructure: 抽出された情報
    """
    text = merge_included_inp_files(inp_filepath)
    return parse_inp_structure_from_text(text)


def get_global_linear_material_from_inp(inp_filepath: str) -> tuple[float, float]:
    """solid section に割当済みの線形等方弾性物性からグローバル (E, nu) を決める.

    現状 pycae.api が E, nu グローバル前提のため、
    solid section に出てくる材料が 1 種類だけであることを要求する。

    Args:
        inp_filepath: 対象 .inp ファイルパス

    Returns:
        (E, nu): グローバルに用いるヤング率とポアソン比

    Raises:
        RuntimeError: 割当済み材料が複数種類ある場合
        KeyError: solid section で参照されている material が *material 定義に存在しない場合
    """
    struct = parse_inp_structure(inp_filepath)

    # solid section で実際に使われている material 名の集合
    used_mats = {sec.material for sec in struct.solid_sections}
    if not used_mats:
        raise RuntimeError("solid section が見つかりませんでした。")

    # (E, nu) セットを抽出
    mat_props = set()
    for name in used_mats:
        mat = struct.materials.get(name)
        if mat is None:
            raise KeyError(f"*material name={name} が定義されていません。")
        mat_props.add((mat.young, mat.poisson))

    if len(mat_props) != 1:
        raise RuntimeError(
            f"solid section に複数種類の (E, nu) が割り当てられています: {mat_props}"
        )

    ((E, nu),) = mat_props  # 1 要素のタプルを unpack
    return E, nu


def get_boundary_and_load_condition_from_inp(
    inp_path: str,
) -> tuple[
    dict[int, tuple[float | bool | None, float | bool | None]],
    dict[int, tuple[float, float]],
]:
    from . import mesher

    mesh = mesher(inp_filepath=inp_path, verbose=False)
    inp_structure = parse_inp_structure(inp_filepath=inp_path)
    node_label_df_mapping = {}
    node_label_load_mapping = {}
    for b in inp_structure.boundaries:
        if b.bc_type == "displacement":
            try:
                labels = [int(b.set_name)]
            except Exception:
                labels = [i for i in mesh.get_node_labels(name=b.set_name)]
                labels += [i for i in mesh.get_node_labels_with_nset(name=b.set_name)]
            for label_i in labels:
                ux, uy = node_label_df_mapping.get(label_i, (True, True))
                # dofs = list(range(b.dof_start, b.dof_end))
                dofs = list(range(b.dof_start, b.dof_end + 1))
                val = 0.0 if b.value is None else float(b.value)
                if 1 in dofs:
                    ux = val
                if 2 in dofs:
                    uy = val
                if ux == 0.0:
                    ux = False
                if uy == 0.0:
                    uy = False
                node_label_df_mapping[label_i] = (ux, uy)
        else:
            raise ValueError

    for load in inp_structure.loads:
        if load.bc_type == "cload":
            try:
                labels = [int(load.set_name)]
            except Exception:
                labels = [i for i in mesh.get_node_labels(name=load.set_name)]
                labels += [
                    i for i in mesh.get_node_labels_with_nset(name=load.set_name)
                ]
            for label_i in labels:
                f1, f2 = node_label_load_mapping.get(label_i, (0.0, 0.0))
                if load.dof == 1:
                    f1 = load.value
                elif load.dof == 2:
                    f2 = load.value
                node_label_load_mapping[label_i] = (f1, f2)
        else:
            raise ValueError

    return node_label_df_mapping, node_label_load_mapping
