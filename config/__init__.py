from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Optional

import yaml

CONFIG_DIRNAME = ".jj/config"
SSH_CONFIG_FILENAME = ".pyssh.yaml"
VOCAB_CONFIG_FILENAME = "vocab.yaml"


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
