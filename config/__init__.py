from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Optional

import yaml

CONFIG_DIRNAME = ".jj/config"
SSH_CONFIG_FILENAME = ".pyssh.yaml"
VOCAB_CONFIG_FILENAME = "vocab.yaml"
EXTENSIONS_CONFIG_FILENAME = "extensions.yaml"
PREFIXES_CONFIG_FILENAME = "prefixes.yaml"

# デフォルト設定
DEFAULT_EXTENSIONS = {
    "calculation_input": [".inp", ".cas.h5", ".k", ".key", ".dat"],
    "mesh": [".cdb", ".msh", ".unv"],
    "multi_dot": [".cas.h5", ".dat.h5", ".tar.gz", ".tar.bz2", ".tar.xz"],
}

DEFAULT_PREFIXES = {
    "go_": "calculation_input",
    "mesh_": "mesh",
    "material_": "material",
    "step_": "step",
}


def get_config_dir(base_dir: Optional[Path] = None) -> Path:
    if base_dir is None:
        base_dir = Path.cwd()
    return base_dir / CONFIG_DIRNAME


def read_yaml(filepath: Path) -> dict[str, Any]:
    with filepath.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError("yaml must be a mapping at top-level")
    return data


def find_ssh_config_path(base_dir: Optional[Path] = None) -> Optional[Path]:
    config_dir = get_config_dir(base_dir)
    candidates = [
        config_dir / SSH_CONFIG_FILENAME,
        Path(SSH_CONFIG_FILENAME),
        Path.home() / SSH_CONFIG_FILENAME,
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def throw_yaml_nonexistent_error(msg: Optional[str] = None) -> ValueError:
    config_dir = get_config_dir()
    text = (
        f"'{config_dir / SSH_CONFIG_FILENAME}'か'./{SSH_CONFIG_FILENAME}'"
        f"または'{str(Path.home() / SSH_CONFIG_FILENAME)}'を設定してください。"
    )
    if msg is not None:
        text += f"({msg})"
    return ValueError(text)


@dataclass(frozen=True)
class VocabConfig:
    mapping: dict[str, str]
    categories: dict[str, list[str]]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VocabConfig":
        mapping = data.get("mapping") or {}
        categories = data.get("categories") or {}

        if not isinstance(mapping, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()
        ):
            raise ValueError("mapping must be dict[str, str]")
        if not isinstance(categories, dict):
            raise ValueError("categories must be dict[str, list[str]]")

        cat2: dict[str, list[str]] = {}
        for ck, lst in categories.items():
            if not isinstance(ck, str) or not isinstance(lst, list):
                raise ValueError("categories must be dict[str, list[str]]")
            cat2[ck] = [str(x) for x in lst]

        return cls(mapping=mapping, categories=cat2)


@dataclass
class SSHConfig:
    host: Optional[str] = None
    port: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None
    windows_local_basedirpath: Optional[str] = None
    linux_local_basedirpath: Optional[str] = None
    remote_basedirpath: Optional[str] = None
    remote_abq_path: Optional[str] = None

    _hostname: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], hostname: Optional[str] = None) -> "SSHConfig":
        hostkey = "HOST"
        passwordkey = "PASSWORD"
        if hostname:
            upper = hostname.upper()
            if upper not in ["GRID2024", "GRID2020", "GRID2016"]:
                raise ValueError(f"hostname: {hostname}は不正です")
            hostkey = f"{upper}_HOST"
            passwordkey = f"{upper}_PASSWORD"

        config = cls(
            host=data.get(hostkey),
            password=data.get(passwordkey),
            _hostname=hostname,
        )

        for f in fields(config):
            if f.name in ["host", "password", "_hostname"]:
                continue
            value = data.get(f.name.upper())
            setattr(config, f.name, value)

        return config

    def require(self, *names: str) -> None:
        missing = [name for name in names if getattr(self, name) in [None, ""]]
        if missing:
            msg = "'" + ", ".join(missing) + "' がNoneです。.pyssh.yaml定義を確認ください。"
            raise ValueError(msg)


@dataclass(frozen=True)
class AppConfig:
    ssh: SSHConfig
    vocab: VocabConfig

    @classmethod
    def load(
        cls, base_dir: Optional[Path] = None, hostname: Optional[str] = None
    ) -> "AppConfig":
        ssh_config = load_ssh_config(base_dir=base_dir, hostname=hostname)
        vocab = load_vocab_config(base_dir=base_dir)
        return cls(ssh=ssh_config, vocab=vocab)


def load_vocab_config(base_dir: Optional[Path] = None) -> VocabConfig:
    config_dir = get_config_dir(base_dir)
    path = config_dir / VOCAB_CONFIG_FILENAME
    if not path.exists():
        return VocabConfig(mapping={}, categories={})
    data = read_yaml(path)
    return VocabConfig.from_dict(data)


def load_ssh_config(
    base_dir: Optional[Path] = None, hostname: Optional[str] = None
) -> SSHConfig:
    path = find_ssh_config_path(base_dir)
    if path is None:
        raise throw_yaml_nonexistent_error("yaml定義が空です")
    data = read_yaml(path)
    return SSHConfig.from_dict(data, hostname=hostname)


@dataclass(frozen=True)
class ExtensionsConfig:
    calculation_input: list[str]
    mesh: list[str]
    multi_dot: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExtensionsConfig":
        calculation_input = data.get("calculation_input") or []
        mesh = data.get("mesh") or []
        multi_dot = data.get("multi_dot") or []

        if not isinstance(calculation_input, list):
            raise ValueError("calculation_input must be list[str]")
        if not isinstance(mesh, list):
            raise ValueError("mesh must be list[str]")
        if not isinstance(multi_dot, list):
            raise ValueError("multi_dot must be list[str]")

        return cls(
            calculation_input=[str(x) for x in calculation_input],
            mesh=[str(x) for x in mesh],
            multi_dot=[str(x) for x in multi_dot],
        )


@dataclass(frozen=True)
class PrefixesConfig:
    prefixes: dict[str, str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PrefixesConfig":
        prefixes = data.get("prefixes") or {}

        if not isinstance(prefixes, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in prefixes.items()
        ):
            raise ValueError("prefixes must be dict[str, str]")

        return cls(prefixes=prefixes)


def load_extensions_config(base_dir: Optional[Path] = None) -> ExtensionsConfig:
    config_dir = get_config_dir(base_dir)
    path = config_dir / EXTENSIONS_CONFIG_FILENAME
    if not path.exists():
        return ExtensionsConfig.from_dict(DEFAULT_EXTENSIONS)
    data = read_yaml(path)
    return ExtensionsConfig.from_dict(data)


def load_prefixes_config(base_dir: Optional[Path] = None) -> PrefixesConfig:
    config_dir = get_config_dir(base_dir)
    path = config_dir / PREFIXES_CONFIG_FILENAME
    if not path.exists():
        return PrefixesConfig.from_dict({"prefixes": DEFAULT_PREFIXES})
    data = read_yaml(path)
    return PrefixesConfig.from_dict(data)


def init_config_dir(base_dir: Optional[Path] = None) -> None:
    """
    .jj/config/ ディレクトリを初期化します。
    フォルダが既に存在する場合は、初期化処理をスキップします。
    """
    config_dir = get_config_dir(base_dir)

    # フォルダが既に存在する場合はスキップ
    if config_dir.exists():
        return

    # .jj/config/ ディレクトリを作成
    config_dir.mkdir(parents=True, exist_ok=True)

    # vocab.yaml の初期化（空の辞書）
    vocab_path = config_dir / VOCAB_CONFIG_FILENAME
    vocab_data = {
        "mapping": {},
        "categories": {},
    }
    with vocab_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(vocab_data, f, allow_unicode=True, sort_keys=False)

    # extensions.yaml の初期化
    extensions_path = config_dir / EXTENSIONS_CONFIG_FILENAME
    with extensions_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(DEFAULT_EXTENSIONS, f, allow_unicode=True, sort_keys=False)

    # prefixes.yaml の初期化
    prefixes_path = config_dir / PREFIXES_CONFIG_FILENAME
    prefixes_data = {"prefixes": DEFAULT_PREFIXES}
    with prefixes_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(prefixes_data, f, allow_unicode=True, sort_keys=False)
