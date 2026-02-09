"""NotesService: Obsidian notes生成サービス

cli/__init__.py から分離したnotes関連のビジネスロジック。
jj n コマンドのバックエンドとして機能します。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from config import VocabConfig, load_vocab_config
from services.parse import (
    get_basename,
    get_basename_with_ext,
    get_group_name,
    get_index_and_version,
    normalize_extension_to_inp,
    safe_relative_path,
)


@dataclass
class NotesConfig:
    """Notes生成設定"""
    root: Path = Path("notes")
    base_path: Path = Path("notes/bases")
    notes_dir: Path = Path("notes/props")
    allow_duplicated: bool = False
    overwrite_props: bool = True
    overwrite_bases: bool = True


def safe_rglob_files(root: Path) -> list[Path]:
    """root配下の全ファイルを収集（存在しない/途中で消えた等は握りつぶす）"""
    if not root.exists():
        return []
    out: list[Path] = []
    try:
        for p in root.rglob("*"):
            try:
                if p.is_file():
                    out.append(p)
            except FileNotFoundError:
                continue
    except FileNotFoundError:
        return []
    return out


def safe_rglob_dirs(root: Path) -> list[Path]:
    """root配下の全ディレクトリを収集（root自身は除外）"""
    if not root.exists():
        return []
    out: list[Path] = []
    try:
        for p in root.rglob("*"):
            try:
                if p.is_dir():
                    out.append(p)
            except FileNotFoundError:
                continue
    except FileNotFoundError:
        return []
    return out


def frontmatter_keys(md_path: Path) -> set[str]:
    """frontmatterのキー集合（消えたファイルは空で返す）"""
    try:
        text = md_path.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return set()
    m = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
    if not m:
        return set()
    keys: set[str] = set()
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, _ = line.split(":", 1)
        k = k.strip()
        if k:
            keys.add(k)
    return keys


def base_template(
    folder: Path,
    ver: bool = True,
    idx: bool = True,
    active: bool = True,
    show_only_active: bool = True,
    additional_filters: Optional[list[str]] = None,
) -> dict:
    """baseテンプレート生成"""
    order = ["file.name", "idx", "ver", "success", "description", "file.links"]
    if not ver:
        order = [i for i in order if i != "ver"]
    if not idx:
        order = [i for i in order if i != "idx"]
    if not active:
        order.append("active")

    if additional_filters is None:
        additional_filters = []
    folder_str = str(folder).replace("\\", "/")
    filters = [
        f'file.folder == "{folder_str}"',
        'file.fullname.endsWith(".md")',
    ]
    if show_only_active:
        filters += ["active == true"]
    filters += additional_filters

    template = {
        "views": [
            {
                "type": "table",
                "name": "Table",
                "filters": {"and": filters},
                "order": order,
                "sort": [
                    {"property": "tmp", "direction": "ASC"},
                    {"property": "idx", "direction": "ASC"},
                    {"property": "ver", "direction": "ASC"},
                ],
            }
        ]
    }
    return template


def write_yaml_if_missing(path: Path, data: dict, overwrite: bool = True) -> None:
    """YAMLファイルを書き込み（存在しない場合のみまたは上書き）"""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not overwrite and path.exists():
        return
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def update_go_base(go_base: Path, keys: list[str]) -> None:
    """go.baseファイルのorderを更新"""
    with go_base.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    order: list[str] = data["views"][0].get("order", [])
    default_order = [
        "file.name",
        "idx",
        "ver",
        "success",
        "active",
        "description",
        "file.links",
    ]
    order = [i for i in default_order if i in order]
    ignore_keys = ["includes"]

    def reorder_keys(keys: list[str]) -> list[str]:
        front = [
            k for k in ("file.name", "idx", "ver", "success", "active") if k in keys
        ]
        back = [k for k in ("description", "file.links") if k in keys]
        middle = [k for k in keys if k not in set(front + back)]
        return front + middle + back

    keys = [i for i in keys if i not in default_order]
    order = order + keys
    order = [i for i in order if i not in ignore_keys]
    order = list(set(order))

    data["views"][0]["order"] = reorder_keys(order)
    with go_base.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def write_frontmatter_props(
    md_path: Path,
    base_name: str,
    all_basename_list: list[str],
    props: dict[str, str],
    includes: list[str] | None = None,
    folder_files: list[str] | None = None,
) -> None:
    """mdファイルを完全上書きで生成する"""
    includes = [] if includes is None else list(includes)
    folder_files = [] if folder_files is None else list(folder_files)

    ver = props.get("ver", "")
    basename = md_path.name.removesuffix(".md")
    basename, ext = get_basename_with_ext(basename)
    basename = basename + ext

    # base_name の補正
    if base_name == "O-go.base" and ver:
        candidate_base_name = "O-" + basename.replace(f".v{ver}", "") + ".base"
        base_dir = md_path.parent.parent / "bases"
        candidate_base_path = base_dir / "go" / candidate_base_name
        if candidate_base_path.exists():
            base_name = candidate_base_name

    # 親 include を決める
    try:
        if ver == "" or int(ver) == 1:
            parent = base_name
        else:
            parent_path_list = [
                basename.replace("v" + ver, "v" + str(int(ver) - 1)),
                basename.replace("v" + ver, ""),
            ]
            all_basename_list_i = [i for i in all_basename_list if i != basename]
            parent = base_name
            for parent_path in parent_path_list:
                if parent_path in all_basename_list_i:
                    parent = f"O-{parent_path}"
                    break
    except Exception:
        parent = base_name

    # includes の先頭に parent を入れる
    merged_includes: list[str] = []
    seen: set[str] = set()

    def _add_include(name: str) -> None:
        if name and name not in seen:
            merged_includes.append(name)
            seen.add(name)

    _add_include(parent)
    for inc in includes:
        _add_include(inc)

    # true filepath の生成
    true_filepath = (
        "_".join(basename.split("_")[:-1]) + "_" + basename.split("_")[-1]
        if "_" in basename
        else basename
    )
    match base_name:
        case "O-tools.base":
            true_filepath = "tools/" + true_filepath
        case "O-reports.base":
            true_filepath = "reports/" + true_filepath
        case "O-docs.base":
            true_filepath = "docs/" + true_filepath

    # frontmatter生成
    fm_lines: list[str] = ["---"]
    fm_lines.extend([f"{k}: {v}" for k, v in props.items()])

    if merged_includes:
        fm_lines.append("includes:")
        for inc in merged_includes:
            fm_lines.append(f"  - [[{inc}]]")

    fm_lines.append("---")
    if merged_includes:
        for inc in merged_includes:
            fm_lines.append(f"- [[{inc}]]")

    # 本文
    body_lines: list[str] = []
    if folder_files:
        for file in folder_files:
            body_lines.append(f"- [[{file}]]")
    else:
        body_lines.append(f"- [[{true_filepath}]]")
    body_lines.append("")

    text = "\n".join(fm_lines) + "\n" + "\n".join(body_lines)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(text, encoding="utf-8")


def update_frontmatter_props(
    md_path: Path,
    props: dict[str, str],
    includes: list[str] | None = None,
    include_key: str = "includes",
) -> None:
    """frontmatterを更新する"""
    text = md_path.read_text(encoding="utf-8", errors="ignore")

    m = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
    if not m:
        return

    fm_body = m.group(1)
    fm: dict[str, str] = {}

    include_links_existing: list[str] = []
    include_links_set: set[str] = set()
    include_key_present_as_list = False

    lines = fm_body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if ":" not in line:
            i += 1
            continue

        k, v = line.split(":", 1)
        k = k.strip()
        v = v.strip()
        fm[k] = v

        if includes is not None and k == include_key and v == "":
            include_key_present_as_list = True
            j = i + 1
            while j < len(lines):
                t = lines[j].rstrip()
                if not t.startswith("  - "):
                    break
                item = t[4:].strip()
                if item and item not in include_links_set:
                    include_links_existing.append(item)
                    include_links_set.add(item)
                j += 1
            i = j
            continue

        if includes is not None and k == include_key and v:
            if v not in include_links_set:
                include_links_existing.append(v)
                include_links_set.add(v)

        i += 1

    updated = False

    for k, v in props.items():
        if fm.get(k) != v:
            fm[k] = v
            updated = True

    include_links_new: list[str] = []
    if includes:
        for inc in includes:
            md_name = f"{inc}.md" if not inc.lower().endswith(".md") else inc
            link = f"[[{md_name}]]"
            if link not in include_links_set:
                include_links_new.append(link)
                include_links_set.add(link)

        if include_links_new:
            updated = True

    if not updated:
        return

    out_lines: list[str] = ["---"]

    for k, v in fm.items():
        if includes is not None and k == include_key:
            continue
        out_lines.append(f"{k}: {v}")

    if includes is not None:
        merged = include_links_existing + include_links_new
        if include_key_present_as_list or merged:
            out_lines.append(f"{include_key}:")
            for item in merged:
                out_lines.append(f"  - {item}")

    out_lines.append("---")

    new_fm = "\n".join(out_lines) + "\n"
    new_text = new_fm + text[m.end():]
    md_path.write_text(new_text, encoding="utf-8")


def clear_notes_props(dirpath: Path) -> None:
    """notesディレクトリをクリア"""
    if not dirpath.exists():
        return
    for p in dirpath.iterdir():
        if p.is_file() or p.is_symlink():
            p.unlink()
        elif p.is_dir():
            shutil.rmtree(p)


def parse_word_with_vocab(
    word: str, vocab: VocabConfig, category_mapping: bool = True
) -> tuple[str, str] | None:
    """vocabularyを使って単語をパース"""
    key, value = None, None
    if "=" in word:
        key, value = word.split("=", 1)
        key = vocab.mapping.get(key, key)
        value = vocab.mapping.get(value, value)
    elif category_mapping:
        for g, vals in vocab.categories.items():
            if word in vals:
                value = word
                key = g
                key = vocab.mapping.get(key, key)
                value = vocab.mapping.get(value, value)
    elif key is None or value is None:
        m = re.fullmatch(r"([A-Za-z]+)(\d+)", word)
        if m:
            key, value = m.group(1), m.group(2)
            key = vocab.mapping.get(key, key)
            value = vocab.mapping.get(value, value)
    if key is None or value is None:
        return None
    key = vocab.mapping.get(key, key)
    value = vocab.mapping.get(value, value)
    return key, value


def get_properties_by_filepath(
    inp_filepath: str, vocab: VocabConfig
) -> dict[str, str]:
    """ファイル名からプロパティを取得"""
    inp_filepath, _ = normalize_extension_to_inp(inp_filepath)
    name = inp_filepath.split("/")[-1].split("\\")[-1]

    if name.lower().endswith(".inp"):
        name = name[:-4]

    idx, ver = get_index_and_version(inp_filepath)
    if idx:
        name = name.replace(f"idx{idx}_", "").replace(f"idx{idx}", "")
    if ver:
        name = name.replace(f".v{ver}", "")

    name = re.sub(r"^(go_|mesh_|material_|step_)", "", name, flags=re.IGNORECASE)

    props: dict[str, str] = {}
    for token in filter(None, name.split("_")):
        result = parse_word_with_vocab(token, vocab)
        if result is None:
            continue
        key, value = result
        props[key] = value

    if Path(inp_filepath).parent.name == "old":
        props["active"] = "false"
    else:
        props["active"] = "true"

    return props


def get_properties_by_inp_parameter(
    inp_filepath: str, vocab: VocabConfig
) -> dict[str, str]:
    """inp内のparameterからプロパティを取得"""
    props: dict[str, str] = {}
    with open(inp_filepath, encoding="utf-8", errors="ignore") as f:
        while True:
            line = f.readline()
            if not line:
                break
            s = line.strip()
            s_l = s.lower().replace(" ", "")
            if s_l.startswith("*parameter"):
                header = f.readline()
                if not header:
                    break
                header_s = header.strip().lower().replace(" ", "")
                if not header_s.startswith("**props"):
                    continue
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
                    if k:
                        k = vocab.mapping.get(k, k)
                        v = vocab.mapping.get(v, v)
                        props[k] = v
                return props
    return props


def get_relations_by_inp_includes(inp_filepath: str) -> list[str]:
    """inpファイル内の*includeディレクティブを解析"""
    includes: list[str] = []
    pat = re.compile(r"^\*include\s*,\s*input\s*=\s*(.+)$", re.IGNORECASE)

    with Path(inp_filepath).open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("**"):
                continue
            m = pat.match(s)
            if m:
                include_name = Path(m.group(1).strip()).name
                project_root = Path.cwd()
                found_files = list(project_root.rglob(include_name))

                if found_files:
                    includes.append(found_files[0].name)
                else:
                    includes.append(include_name)

    if "mesh" in inp_filepath:
        basename = get_basename(inp_filepath)
        modfem_name = f"{basename}.modfem"
        project_root = Path.cwd()
        found_modfem = list(project_root.rglob(modfem_name))
        if found_modfem:
            includes.append(found_modfem[0].name)
        else:
            includes.append(modfem_name)

    return includes


class NotesService:
    """Obsidian notes生成サービス"""

    def __init__(self, config: NotesConfig | None = None) -> None:
        self.config = config or NotesConfig()

    def init_tree(self, init_bases: bool = True) -> None:
        """notesツリーを初期化"""
        root = self.config.root

        if init_bases:
            obsidian_config_path = Path(".obsidian")
            if not obsidian_config_path.exists():
                obsidian_config_path.mkdir(parents=True, exist_ok=True)
                # Obsidian設定ファイルをコピー
                json_filepath = str(
                    Path(__file__).parent.parent.parent / "cli" / ".obsidian" / "*.json"
                )
                for i in glob.glob(json_filepath):
                    os.system(f"cp {i} .obsidian/")

            # ディレクトリ構造を作成
            root.mkdir(parents=True, exist_ok=True)
            (root / "bases").mkdir(parents=True, exist_ok=True)
            (root / "bases" / "go").mkdir(parents=True, exist_ok=True)
            (root / "bases" / "group").mkdir(parents=True, exist_ok=True)
            (root / "daily").mkdir(parents=True, exist_ok=True)
            (root / "canvas").mkdir(parents=True, exist_ok=True)
            (root / "props").mkdir(parents=True, exist_ok=True)
            (root / "props" / "go").mkdir(parents=True, exist_ok=True)
            (root / "props" / "mesh").mkdir(parents=True, exist_ok=True)
            (root / "props" / "material").mkdir(parents=True, exist_ok=True)
            (root / "props" / "step").mkdir(parents=True, exist_ok=True)
            (root / "props" / "reports").mkdir(parents=True, exist_ok=True)
            (root / "props" / "docs").mkdir(parents=True, exist_ok=True)
            (root / "props" / "tools").mkdir(parents=True, exist_ok=True)

            # baseファイルを生成
            write_yaml_if_missing(
                root / "bases" / "O-go.base",
                base_template(root / "props" / "go"),
            )
            write_yaml_if_missing(
                root / "bases" / "O-mesh.base",
                base_template(root / "props" / "mesh"),
            )
            write_yaml_if_missing(
                root / "bases" / "O-material.base",
                base_template(root / "props" / "material", idx=False),
            )
            write_yaml_if_missing(
                root / "bases" / "O-step.base",
                base_template(root / "props" / "step", idx=False),
            )
            write_yaml_if_missing(
                root / "bases" / "O-docs.base",
                base_template(
                    root / "props" / "docs",
                    idx=False,
                    ver=False,
                    show_only_active=False,
                    active=False,
                ),
            )
            write_yaml_if_missing(
                root / "bases" / "O-reports.base",
                base_template(root / "props" / "reports", idx=False, active=False),
            )
            write_yaml_if_missing(
                root / "bases" / "O-tools.base",
                base_template(
                    root / "props" / "tools", idx=False, ver=False, active=False
                ),
            )
            write_yaml_if_missing(
                root / "bases" / "O-daily.base",
                base_template(
                    root / "daily",
                    idx=False,
                    ver=False,
                    show_only_active=False,
                    active=False,
                ),
            )

        self._generate_version_group_bases(root)

    def _generate_version_group_bases(self, root: Path) -> None:
        """バージョングループ用baseファイルを生成"""
        base_list = ["O-go.base", ""]

        all_category_bases = []
        for category in ["go", "mesh", "material", "step"]:
            category_list = list(glob.glob(str(root / "props" / category / "*.md")))
            if not category_list:
                continue

            category_list = ["_".join(i.split("_")[:-1]) + "." + i.split("_")[-1] for i in category_list]
            category_list = list([get_basename(i) for i in category_list])

            category_list_normalized = []
            for item in category_list:
                idx, ver = get_index_and_version(item)
                if ver:
                    normalized = item.replace(f".v{ver}", "")
                    category_list_normalized.append(normalized)
                else:
                    category_list_normalized.append(item)

            version_count = Counter(category_list_normalized)
            category_list_unique = sorted(set(category_list_normalized),
                key=lambda x: get_index_and_version(x)[0] if get_index_and_version(x)[0] else x)

            (root / "bases" / category).mkdir(parents=True, exist_ok=True)

            category_base_list = []
            for i in category_list_unique:
                if version_count[i] >= 2:
                    category_base_list.append(f"O-{i}.base")
                    write_yaml_if_missing(
                        root / "bases" / category / f"O-{i}.base",
                        base_template(
                            root / "props" / category,
                            additional_filters=[f'file.basename.startsWith("O-{i}")'],
                            idx=False,
                            show_only_active=False,
                        ),
                    )
                    if category == "go":
                        base_list.append(f"O-{i}.base")

            all_category_bases.extend(category_base_list)

            if category_base_list:
                with open(str(root / "bases" / category / f"O-{category}_index.md"), "w") as f:
                    f.write(f"[[O-{category}.base]]\n")
                    for base in category_base_list:
                        f.write(f"[[{base}]]\n")

        # グループbaseファイルの生成
        all_inp_files = []
        for subdir in ["go", "mesh", "material", "step"]:
            all_inp_files.extend(glob.glob(str(root / "props" / subdir / "*.md")))

        group_files = defaultdict(list)
        for filepath in all_inp_files:
            group_name = get_group_name(filepath)
            if group_name:
                group_files[group_name].append(filepath)

        group_base_list = []
        for group_name in sorted(group_files.keys()):
            if len(group_files[group_name]) >= 2:
                group_base_list.append(f"O-{group_name}.base")
                write_yaml_if_missing(
                    root / "bases" / "group" / f"O-{group_name}.base",
                    base_template(
                        root / "props",
                        additional_filters=[f'file.basename.startsWith("O-{group_name}_")'],
                        idx=False,
                        ver=False,
                        show_only_active=False,
                    ),
                )

        base_list.append("")
        base_list += [
            "O-mesh.base",
            "O-material.base",
            "O-step.base",
            "O-docs.base",
            "O-tools.base",
            "O-reports.base",
            "O-daily.base",
        ]

        with open(str(root / "bases" / "O-base.md"), "w") as f:
            for i in base_list:
                if i:
                    f.write(f"- [[{i}]]\n")
                else:
                    f.write("\n")

        with open(str(root / "bases" / "group" / "O-group_index.md"), "w") as f:
            f.write("# グループ一覧\n\n")
            for i in group_base_list:
                f.write(f"- [[{i}]]\n")


__all__ = [
    "NotesConfig",
    "NotesService",
    "base_template",
    "clear_notes_props",
    "frontmatter_keys",
    "get_properties_by_filepath",
    "get_properties_by_inp_parameter",
    "get_relations_by_inp_includes",
    "parse_word_with_vocab",
    "safe_rglob_dirs",
    "safe_rglob_files",
    "update_frontmatter_props",
    "update_go_base",
    "write_frontmatter_props",
    "write_yaml_if_missing",
]
