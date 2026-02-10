from __future__ import annotations

import fnmatch
import importlib.resources
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Optional

import yaml

CONFIG_DIRNAME = ".jj/config"
CONFIG_FILENAME = "config.yaml"
SSH_CONFIG_FILENAME = ".pyssh.yaml"
VOCAB_CONFIG_FILENAME = "vocab.yaml"
EXTENSIONS_CONFIG_FILENAME = "extensions.yaml"
PREFIXES_CONFIG_FILENAME = "prefixes.yaml"
DEFAULT_CONFIG_ASSET = "default-config.yaml"

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
    extensions: ExtensionsConfig
    prefixes: PrefixesConfig

    @classmethod
    def load(
        cls, base_dir: Optional[Path] = None, hostname: Optional[str] = None
    ) -> "AppConfig":
        ssh_config = load_ssh_config(base_dir=base_dir, hostname=hostname)
        vocab = load_vocab_config(base_dir=base_dir)
        extensions = load_extensions_config(base_dir=base_dir)
        prefixes = load_prefixes_config(base_dir=base_dir)
        return cls(
            ssh=ssh_config,
            vocab=vocab,
            extensions=extensions,
            prefixes=prefixes,
        )


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


# =============================================================================
# 拡張設定モデル (path-type-map, path-property-map, ignore等)
# =============================================================================


def get_default_config_path() -> Path:
    """デフォルト設定ファイル(assets/default-config.yaml)のパスを取得"""
    # パッケージ内のassetsディレクトリを探す
    package_dir = Path(__file__).parent.parent
    local_path = package_dir / "assets" / DEFAULT_CONFIG_ASSET
    if local_path.exists():
        return local_path
    # Phase R リファクタリングでassetsがshared/に移動された場合のフォールバック
    shared_path = package_dir.parent / "shared" / "assets" / DEFAULT_CONFIG_ASSET
    if shared_path.exists():
        return shared_path
    return local_path


def load_default_config() -> dict[str, Any]:
    """デフォルト設定を読み込む"""
    default_path = get_default_config_path()
    if default_path.exists():
        return read_yaml(default_path)
    return {}


def load_project_config(base_dir: Optional[Path] = None) -> dict[str, Any]:
    """プロジェクト固有の設定を読み込む（デフォルトとマージ）"""
    config_dir = get_config_dir(base_dir)
    config_path = config_dir / CONFIG_FILENAME

    # デフォルト設定を読み込み
    config = load_default_config()

    # プロジェクト固有設定があればマージ
    if config_path.exists():
        project_config = read_yaml(config_path)
        config = _deep_merge(config, project_config)

    return config


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """辞書を深くマージする（overrideが優先）"""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _pattern_specificity(pattern: str) -> tuple[int, int, int]:
    """パターンの具体性をスコア化（高いほど具体的）

    Returns:
        (ワイルドカード少なさ, ディレクトリ深さ, パターン長さ)
    """
    # ワイルドカードの数を数える（少ないほど具体的）
    wildcards = pattern.count("*") + pattern.count("?")
    # **は2つ分としてカウント（より汎用的）
    wildcards += pattern.count("**")

    # ディレクトリの深さ（深いほど具体的）
    depth = pattern.count("/")

    # パターンの長さ（長いほど具体的）
    length = len(pattern.replace("*", "").replace("?", ""))

    return (-wildcards, depth, length)


@dataclass(frozen=True)
class PathTypeMapConfig:
    """path-type-map設定: パスパターンとファイルタイプのマッピング

    評価順序: より具体的なパターン（ワイルドカードが少ない、パスが長い）を先に評価
    """
    rules: list[tuple[list[str], dict[str, str]]]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PathTypeMapConfig":
        rules: list[tuple[list[str], dict[str, str]]] = []
        if not data:
            return cls(rules=[])

        for pattern_key, type_map in data.items():
            # パターンを "|" で分割
            patterns = [p.strip() for p in pattern_key.split("|")]
            if isinstance(type_map, dict):
                rules.append((patterns, type_map))

        # パターンの具体性でソート（より具体的なパターンを先に）
        def rule_specificity(rule: tuple[list[str], dict[str, str]]) -> tuple[int, int, int]:
            patterns = rule[0]
            # 複数パターンの場合、最も具体的なものを基準にする
            return max(_pattern_specificity(p) for p in patterns)

        rules.sort(key=rule_specificity, reverse=True)
        return cls(rules=rules)

    def get_type(self, path: str, filename: str) -> Optional[str]:
        """パスとファイル名からタイプを取得（マッチしない場合はNone）

        より具体的なパターンが先に評価されるため、最初にマッチしたものが返されます。
        """
        for patterns, type_map in self.rules:
            for pattern in patterns:
                # ディレクトリパターンのマッチング
                if _match_path_pattern(path, pattern):
                    # ファイル名パターンも具体性でソート
                    sorted_file_patterns = sorted(
                        type_map.items(),
                        key=lambda x: _pattern_specificity(x[0]),
                        reverse=True
                    )
                    for file_pattern, file_type in sorted_file_patterns:
                        if fnmatch.fnmatch(filename, file_pattern):
                            return file_type
        return None


@dataclass(frozen=True)
class PathPropertyMapConfig:
    """path-property-map設定: パスパターンとプロパティのマッピング"""
    rules: list[tuple[list[str], dict[str, Any]]]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PathPropertyMapConfig":
        rules: list[tuple[list[str], dict[str, Any]]] = []
        if not data:
            return cls(rules=[])

        for pattern_key, props in data.items():
            patterns = [p.strip() for p in pattern_key.split("|")]
            if isinstance(props, dict):
                rules.append((patterns, props))
        return cls(rules=rules)

    def get_properties(self, path: str) -> dict[str, Any]:
        """パスからプロパティを取得（マッチしたすべてのプロパティをマージ）"""
        result: dict[str, Any] = {}
        for patterns, props in self.rules:
            for pattern in patterns:
                if _match_path_pattern(path, pattern):
                    result.update(props)
                    break
        return result


@dataclass(frozen=True)
class PathTagMapConfig:
    """path-tag-map設定: パスパターンとタグのマッピング"""
    rules: list[tuple[list[str], str]]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PathTagMapConfig":
        rules: list[tuple[list[str], str]] = []
        if not data:
            return cls(rules=[])

        for pattern_key, tag in data.items():
            patterns = [p.strip() for p in pattern_key.split("|")]
            if isinstance(tag, str):
                rules.append((patterns, tag))
        return cls(rules=rules)

    def get_tags(self, path: str) -> list[str]:
        """パスからタグを取得（マッチしたすべてのタグを返す）"""
        tags: list[str] = []
        for patterns, tag in self.rules:
            for pattern in patterns:
                if _match_path_pattern(path, pattern):
                    tags.append(tag)
                    break
        return tags


@dataclass(frozen=True)
class TokenKeyMapConfig:
    """token-key-map設定: ファイル名トークンをプロパティキーにマッピング

    設定例:
        token-key-map:
          形状:
            - hogehoge24
            - foobar12
          解析タイプ:
            - static

    mesh_hogehoge24_v1_idx1.inp の場合:
    トークン hogehoge24 は通常 _parse_prop_token で hogehoge: 24 と分割されるが、
    token-key-mapに定義があれば 形状: hogehoge24 として扱われる。
    さらにvocabで hogehoge24: ほげほげ24 と定義があれば、形状: ほげほげ24 に最終変換される。
    """
    rules: dict[str, list[str]]  # key → list of token values

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TokenKeyMapConfig":
        if not data:
            return cls(rules={})
        rules: dict[str, list[str]] = {}
        for key, tokens in data.items():
            if isinstance(tokens, list):
                rules[str(key)] = [str(t) for t in tokens]
            elif isinstance(tokens, str):
                rules[str(key)] = [str(tokens)]
        return cls(rules=rules)

    def get_key(self, token: str) -> Optional[str]:
        """トークンに対応するキーを返す（マッチしない場合はNone）"""
        for key, tokens in self.rules.items():
            if token in tokens:
                return key
        return None


@dataclass(frozen=True)
class IgnoreConfig:
    """ignore設定: 除外パターン（.gitignore相当）"""
    patterns: list[str]

    @classmethod
    def from_list(cls, data: list[str] | None) -> "IgnoreConfig":
        if not data:
            return cls(patterns=[])
        return cls(patterns=[str(p) for p in data])

    def should_ignore(self, path: str) -> bool:
        """パスを除外するべきかどうか判定"""
        for pattern in self.patterns:
            if fnmatch.fnmatch(path, pattern):
                return True
            # パス内の各コンポーネントにもマッチングを試みる
            parts = path.replace("\\", "/").split("/")
            for part in parts:
                if fnmatch.fnmatch(part, pattern):
                    return True
        return False


@dataclass(frozen=True)
class FileRelationsConfig:
    """ファイル関係設定: 入力/結果/アセットファイルの拡張子マッピング"""
    input_extensions: frozenset[str]
    result_extensions: frozenset[str]
    asset_extensions: frozenset[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileRelationsConfig":
        return cls(
            input_extensions=frozenset(data.get("input-extensions", [".inp", ".cas.h5", ".k", ".key", ".dat"])),
            result_extensions=frozenset(data.get("result-extensions", [".odb", ".sta", ".msg", ".csv", ".json"])),
            asset_extensions=frozenset(data.get("asset-extensions", [".modfem", ".stl", ".cdb", ".msh"])),
        )


@dataclass(frozen=True)
class ObsidianExportConfig:
    """Obsidianエクスポート設定"""
    notes_dir: str
    bases_dir: str
    prefix: str
    default_views: list[dict[str, Any]]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ObsidianExportConfig":
        return cls(
            notes_dir=data.get("notes-dir", "notes/props"),
            bases_dir=data.get("bases-dir", "notes/bases"),
            prefix=data.get("prefix", "O-"),
            default_views=data.get("default-views", []),
        )


@dataclass(frozen=True)
class GraphConfig:
    """グラフ機能用の統合設定"""
    vocab: dict[str, str]
    path_type_map: PathTypeMapConfig
    path_property_map: PathPropertyMapConfig
    path_tag_map: PathTagMapConfig
    ignore: IgnoreConfig
    file_relations: FileRelationsConfig
    obsidian: ObsidianExportConfig
    token_key_map: TokenKeyMapConfig
    project_name: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphConfig":
        return cls(
            vocab=data.get("vocab", {}),
            path_type_map=PathTypeMapConfig.from_dict(data.get("path-type-map", {})),
            path_property_map=PathPropertyMapConfig.from_dict(data.get("path-property-map", {})),
            path_tag_map=PathTagMapConfig.from_dict(data.get("path-tag-map", {})),
            ignore=IgnoreConfig.from_list(data.get("ignore", [])),
            file_relations=FileRelationsConfig.from_dict(data.get("file-relations", {})),
            obsidian=ObsidianExportConfig.from_dict(data.get("obsidian", {})),
            token_key_map=TokenKeyMapConfig.from_dict(data.get("token-key-map", {})),
            project_name=data.get("project-name", ""),
        )

    @classmethod
    def load(cls, base_dir: Optional[Path] = None) -> "GraphConfig":
        """プロジェクト設定を読み込んでGraphConfigを生成"""
        config_data = load_project_config(base_dir)
        return cls.from_dict(config_data)


def _match_path_pattern(path: str, pattern: str) -> bool:
    """パスパターンのマッチング

    Windowsパス（バックスラッシュ）とLinuxパス（スラッシュ）の両方に対応。
    以下のパターン形式をサポート:
    - ``**/prefix_*``: 任意の階層で prefix_ で始まるパスにマッチ
    - ``**name``: 任意の階層でファイル/ディレクトリ名が name にマッチ
      （拡張子を除いたbasename比較を含む）
    - ``./dir/``: プロジェクト直下のディレクトリ配下の全ファイルにマッチ
    - ``dir/``: ディレクトリ配下の全ファイルにマッチ（末尾/は再帰マッチ）
    - 通常のglobパターン

    Args:
        path: チェック対象のパス（POSIX形式推奨、Windows形式も可）
        pattern: globスタイルのパターン

    Returns:
        マッチした場合True
    """
    # パスとパターンを正規化（バックスラッシュ→スラッシュ、先頭の ./ を除去）
    normalized_path = path.replace("\\", "/")
    normalized_pattern = pattern.replace("\\", "/")

    # 先頭の ./ を除去（複数の ./ にも対応）
    while normalized_path.startswith("./"):
        normalized_path = normalized_path[2:]
    while normalized_pattern.startswith("./"):
        normalized_pattern = normalized_pattern[2:]

    # ディレクトリパターン（末尾が / ）: 配下の全ファイルにマッチ
    if normalized_pattern.endswith("/"):
        dir_prefix = normalized_pattern  # 例: "reports/"
        dir_name = normalized_pattern.rstrip("/")  # 例: "reports"
        return (normalized_path.startswith(dir_prefix) or
                normalized_path == dir_name)

    # ** を含むパターン
    if normalized_pattern.startswith("**/") or normalized_pattern.startswith("**"):
        # まず直接fnmatchを試行
        if fnmatch.fnmatch(normalized_path, normalized_pattern):
            return True

        # ** 以降のパターン部分を取得
        rest = normalized_pattern
        while rest.startswith("*"):
            rest = rest[1:]
        if rest.startswith("/"):
            rest = rest[1:]

        # パスの各サフィックスに対してマッチを試みる
        parts = normalized_path.split("/")
        for i in range(len(parts)):
            subpath = "/".join(parts[i:])
            if fnmatch.fnmatch(subpath, rest):
                return True

        # ファイル名のbasename（拡張子除去）でもマッチを試みる
        # 例: **go が go.inp, go.cas.h5 等にマッチするようにする
        filename = parts[-1]
        if "." in filename:
            dot_parts = filename.split(".")
            for j in range(1, len(dot_parts)):
                candidate = ".".join(dot_parts[:j])
                if fnmatch.fnmatch(candidate, rest):
                    return True

        return False

    # 通常のパターン
    return fnmatch.fnmatch(normalized_path, normalized_pattern)


def init_graph_config(base_dir: Optional[Path] = None, overwrite: bool = False) -> Path:
    """グラフ設定ファイルを初期化（デフォルト設定をコピー）

    Args:
        base_dir: プロジェクトルート
        overwrite: 既存ファイルを上書きするか

    Returns:
        作成された設定ファイルのパス
    """
    config_dir = get_config_dir(base_dir)
    config_path = config_dir / CONFIG_FILENAME

    # ディレクトリ作成
    config_dir.mkdir(parents=True, exist_ok=True)

    # 既存ファイルがあり、上書きしない場合はスキップ
    if config_path.exists() and not overwrite:
        return config_path

    # デフォルト設定をコピー
    default_config = load_default_config()
    with config_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(default_config, f, allow_unicode=True, sort_keys=False)

    return config_path
