from __future__ import annotations

import fnmatch
import re as _re
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

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


def get_config_dir(base_dir: Path | None = None) -> Path:
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


def find_ssh_config_path(base_dir: Path | None = None) -> Path | None:
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


def throw_yaml_nonexistent_error(msg: str | None = None) -> ValueError:
    config_dir = get_config_dir()
    text = (
        f"'{config_dir / SSH_CONFIG_FILENAME}'か'./{SSH_CONFIG_FILENAME}'"
        f"または'{Path.home() / SSH_CONFIG_FILENAME!s}'を設定してください。"
    )
    if msg is not None:
        text += f"({msg})"
    return ValueError(text)


@dataclass(frozen=True)
class VocabConfig:
    mapping: dict[str, str]
    categories: dict[str, list[str]]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VocabConfig:
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
    host: str | None = None
    port: str | None = None
    user: str | None = None
    password: str | None = None
    windows_local_basedirpath: str | None = None
    linux_local_basedirpath: str | None = None
    remote_basedirpath: str | None = None
    remote_abq_path: str | None = None

    _hostname: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], hostname: str | None = None) -> SSHConfig:
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
    def load(cls, base_dir: Path | None = None, hostname: str | None = None) -> AppConfig:
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


def load_vocab_config(base_dir: Path | None = None) -> VocabConfig:
    config_dir = get_config_dir(base_dir)
    path = config_dir / VOCAB_CONFIG_FILENAME
    if not path.exists():
        return VocabConfig(mapping={}, categories={})
    data = read_yaml(path)
    return VocabConfig.from_dict(data)


def load_ssh_config(base_dir: Path | None = None, hostname: str | None = None) -> SSHConfig:
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
    def from_dict(cls, data: dict[str, Any]) -> ExtensionsConfig:
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
    def from_dict(cls, data: dict[str, Any]) -> PrefixesConfig:
        prefixes = data.get("prefixes") or {}

        if not isinstance(prefixes, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in prefixes.items()
        ):
            raise ValueError("prefixes must be dict[str, str]")

        return cls(prefixes=prefixes)


def load_extensions_config(base_dir: Path | None = None) -> ExtensionsConfig:
    config_dir = get_config_dir(base_dir)
    path = config_dir / EXTENSIONS_CONFIG_FILENAME
    if not path.exists():
        return ExtensionsConfig.from_dict(DEFAULT_EXTENSIONS)
    data = read_yaml(path)
    return ExtensionsConfig.from_dict(data)


def load_prefixes_config(base_dir: Path | None = None) -> PrefixesConfig:
    config_dir = get_config_dir(base_dir)
    path = config_dir / PREFIXES_CONFIG_FILENAME
    if not path.exists():
        return PrefixesConfig.from_dict({"prefixes": DEFAULT_PREFIXES})
    data = read_yaml(path)
    return PrefixesConfig.from_dict(data)


def init_config_dir(base_dir: Path | None = None) -> None:
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


def load_project_config(base_dir: Path | None = None) -> dict[str, Any]:
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
    def from_dict(cls, data: dict[str, Any]) -> PathTypeMapConfig:
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

    def get_type(self, path: str, filename: str) -> str | None:
        """パスとファイル名からタイプを取得（マッチしない場合はNone）

        より具体的なパターンが先に評価されるため、最初にマッチしたものが返されます。
        """
        for patterns, type_map in self.rules:
            for pattern in patterns:
                # ディレクトリパターンのマッチング
                if _match_path_pattern(path, pattern):
                    # ファイル名パターンも具体性でソート
                    sorted_file_patterns = sorted(
                        type_map.items(), key=lambda x: _pattern_specificity(x[0]), reverse=True
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
    def from_dict(cls, data: dict[str, Any]) -> PathPropertyMapConfig:
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
    def from_dict(cls, data: dict[str, Any]) -> PathTagMapConfig:
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
    def from_dict(cls, data: dict[str, Any]) -> TokenKeyMapConfig:
        if not data:
            return cls(rules={})
        rules: dict[str, list[str]] = {}
        for key, tokens in data.items():
            if isinstance(tokens, list):
                rules[str(key)] = [str(t) for t in tokens]
            elif isinstance(tokens, str):
                rules[str(key)] = [str(tokens)]
        return cls(rules=rules)

    def get_key(self, token: str) -> str | None:
        """トークンに対応するキーを返す（マッチしない場合はNone）"""
        for key, tokens in self.rules.items():
            if token in tokens:
                return key
        return None


@dataclass(frozen=True)
class IgnoreConfig:
    """ignore設定: 除外パターン（.gitignore相当）

    パフォーマンス最適化: fnmatchパターンを正規表現にプリコンパイルし、
    大量ファイル（1000+）のスキャン時のオーバーヘッドを削減する。
    """

    patterns: list[str]
    _compiled_patterns: tuple[_re.Pattern[str], ...] = ()

    @classmethod
    def from_list(cls, data: list[str] | None) -> IgnoreConfig:
        if not data:
            return cls(patterns=[])
        patterns = [str(p) for p in data]
        compiled = tuple(_re.compile(fnmatch.translate(p)) for p in patterns)
        return cls(patterns=patterns, _compiled_patterns=compiled)

    def should_ignore(self, path: str) -> bool:
        """パスを除外するべきかどうか判定（プリコンパイル済み正規表現使用）"""
        for compiled in self._compiled_patterns:
            if compiled.match(path):
                return True
        # パス内の各コンポーネントにもマッチングを試みる
        parts = path.replace("\\", "/").split("/")
        for compiled in self._compiled_patterns:
            for part in parts:
                if compiled.match(part):
                    return True
        return False


@dataclass(frozen=True)
class FileRelationsConfig:
    """ファイル関係設定: 入力/結果/アセットファイルの拡張子マッピング"""

    input_extensions: frozenset[str]
    result_extensions: frozenset[str]
    asset_extensions: frozenset[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FileRelationsConfig:
        return cls(
            input_extensions=frozenset(data.get("input-extensions", [".inp", ".cas.h5", ".k", ".key", ".dat"])),
            result_extensions=frozenset(data.get("result-extensions", [".odb", ".sta", ".msg", ".csv", ".json"])),
            asset_extensions=frozenset(data.get("asset-extensions", [".modfem", ".stl", ".cdb", ".msh"])),
        )


@dataclass(frozen=True)
class ObsidianVaultConfig:
    """Obsidian Vault設定（.obsidian/ディレクトリの自動生成内容）"""

    app: dict[str, Any]
    community_plugins: list[str]
    core_plugins: dict[str, bool]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ObsidianVaultConfig:
        return cls(
            app=data.get(
                "app",
                {
                    "useMarkdownLinks": False,
                    "showFrontmatter": True,
                    "strictLineBreaks": False,
                    "readableLineLength": True,
                },
            ),
            community_plugins=data.get("community-plugins", ["dataview", "dbfolder"]),
            core_plugins=data.get(
                "core-plugins",
                {
                    "canvas": True,
                    "graph": True,
                    "outgoing-link": True,
                    "tag-pane": True,
                    "backlink": True,
                    "page-preview": True,
                    "file-explorer": True,
                    "global-search": True,
                    "switcher": True,
                    "markdown-importer": False,
                    "note-composer": True,
                    "command-palette": True,
                    "editor-status": True,
                    "bookmarks": True,
                    "outline": True,
                    "word-count": True,
                    "file-recovery": True,
                    "properties": True,
                },
            ),
        )


@dataclass(frozen=True)
class ObsidianExportConfig:
    """Obsidianエクスポート設定"""

    notes_dir: str
    bases_dir: str
    prefix: str
    default_views: list[dict[str, Any]]
    vault: ObsidianVaultConfig

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ObsidianExportConfig:
        return cls(
            notes_dir=data.get("notes-dir", "notes/props"),
            bases_dir=data.get("bases-dir", "notes/bases"),
            prefix=data.get("prefix", "O-"),
            default_views=data.get("default-views", []),
            vault=ObsidianVaultConfig.from_dict(data.get("vault", {})),
        )


_BUILTIN_VIEW_TYPES = frozenset({"table", "plot", "gallery", "card", "status", "array_plot"})
_CONNECTOR_VIEW_PREFIX = "connector:"


@dataclass(frozen=True)
class SavedViewConfig:
    """保存済みビュー設定

    dashboard.saved-viewsの各エントリに対応。
    フィルタ・プロット条件を保存し、ダッシュボードで順番に表示する。

    view_typeはビルトインタイプ（table, plot等）に加え、
    "connector:{page_label}" 形式でコネクターページも指定可能。
    """

    name: str  # ビュー名
    view_type: str  # "table" | "plot" | ... | "connector:{page_label}"
    filters: dict[str, Any]  # グローバルフィルタ条件
    local_filters: dict[str, Any]  # ローカルフィルタ条件（ページ/ビュー固有）
    plot: dict[
        str, Any
    ]  # プロット条件 {"x": ..., "y": ..., "color": ..., "chart_type": ..., "plot_style": {...}, "axis_range": {...}}
    gallery: dict[str, Any]  # ギャラリー条件 {"source": ..., "property_key": ..., "format": ...}
    array_plot: dict[str, Any]  # 配列プロット条件 {"prefix": ..., "x": ..., "y": [...], "mode": ...}
    connector_config: dict[str, Any]  # コネクター固有設定（connector:*タイプ用）

    @property
    def is_connector_view(self) -> bool:
        """コネクタービュータイプかどうかを判定"""
        return self.view_type.startswith(_CONNECTOR_VIEW_PREFIX)

    @property
    def connector_page_label(self) -> str:
        """コネクタービューのページラベルを返す（非コネクターの場合は空文字列）"""
        if self.is_connector_view:
            return self.view_type[len(_CONNECTOR_VIEW_PREFIX) :]
        return ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SavedViewConfig:
        name = data.get("name", "")
        if not name:
            raise ValueError("saved-views[].name is required")
        view_type = data.get("type", "table")
        # ビルトインタイプまたはconnector:プレフィックスを許可
        if view_type not in _BUILTIN_VIEW_TYPES and not view_type.startswith(_CONNECTOR_VIEW_PREFIX):
            raise ValueError(
                f"saved-views[].type must be one of: {', '.join(sorted(_BUILTIN_VIEW_TYPES))}, "
                f"or 'connector:{{page_label}}' (got '{view_type}')"
            )
        filters = data.get("filters", {})
        if not isinstance(filters, dict):
            filters = {}
        local_filters = data.get("local_filters", {})
        if not isinstance(local_filters, dict):
            local_filters = {}
        plot = data.get("plot", {})
        if not isinstance(plot, dict):
            plot = {}
        gallery = data.get("gallery", {})
        if not isinstance(gallery, dict):
            gallery = {}
        array_plot = data.get("array_plot", {})
        if not isinstance(array_plot, dict):
            array_plot = {}
        connector_config = data.get("connector_config", {})
        if not isinstance(connector_config, dict):
            connector_config = {}
        return cls(
            name=name,
            view_type=view_type,
            filters=filters,
            local_filters=local_filters,
            plot=plot,
            gallery=gallery,
            array_plot=array_plot,
            connector_config=connector_config,
        )


@dataclass(frozen=True)
class DashboardConfig:
    """ダッシュボード設定: テーブルカラム・フィルタ・プロット・ギャラリー・保存済みビュー・コネクタ固有設定"""

    table_columns: list[str] | None  # テーブルビュー表示カラム（globパターン対応、優先順位順）
    default_filters: dict[str, Any]  # デフォルトフィルタ（例: {"active": true}）
    plot_x: str | None  # プロットデフォルトX軸
    plot_y: str | None  # プロットデフォルトY軸
    gallery_columns: int  # ギャラリーグリッド列数
    gallery_rows: int  # ギャラリーグリッド行数
    saved_views: list[SavedViewConfig]  # 保存済みビュー（表示順）
    connector_configs: dict[str, dict[str, Any]]  # コネクタ固有設定（キー: コネクタ名）
    ng_regions: list[dict[str, Any]]  # NG領域定義（矩形/カーブ）
    group_line_key: str | None  # グループ結線キー（同一値のデータ点を結線）
    plot_style: dict[str, int]  # プロットスタイル（marker_size, line_width, font_size）

    def get_connector_config(self, connector_key: str) -> dict[str, Any]:
        """コネクタ固有設定を取得

        Args:
            connector_key: コネクタ名（例: "abaqus"）

        Returns:
            コネクタ固有設定の辞書。未設定の場合は空辞書。
        """
        return dict(self.connector_configs.get(connector_key, {}))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DashboardConfig:
        if not data:
            return cls(
                table_columns=None,
                default_filters={},
                plot_x=None,
                plot_y=None,
                gallery_columns=5,
                gallery_rows=4,
                saved_views=[],
                connector_configs={},
                ng_regions=[],
                group_line_key=None,
                plot_style={},
            )
        table_columns = data.get("table-columns")
        if table_columns is not None and not isinstance(table_columns, list):
            raise ValueError("dashboard.table-columns must be list[str]")
        default_filters = data.get("default-filters", {})
        if not isinstance(default_filters, dict):
            raise ValueError("dashboard.default-filters must be dict")
        plot = data.get("plot", {})
        if not isinstance(plot, dict):
            plot = {}
        gallery_columns = int(data.get("gallery-columns", 5))
        if gallery_columns < 1:
            raise ValueError("dashboard.gallery-columns must be >= 1")
        gallery_rows = int(data.get("gallery-rows", 4))
        if gallery_rows < 1:
            raise ValueError("dashboard.gallery-rows must be >= 1")
        # 保存済みビューの読み込み
        raw_views = data.get("saved-views", [])
        if not isinstance(raw_views, list):
            raise ValueError("dashboard.saved-views must be list")
        saved_views: list[SavedViewConfig] = []
        for v in raw_views:
            if isinstance(v, dict):
                saved_views.append(SavedViewConfig.from_dict(v))
        # コネクタ固有設定の読み込み
        raw_connectors = data.get("connectors", {})
        if not isinstance(raw_connectors, dict):
            raise ValueError("dashboard.connectors must be dict")
        connector_configs: dict[str, dict[str, Any]] = {}
        for ckey, cval in raw_connectors.items():
            if isinstance(cval, dict):
                connector_configs[str(ckey)] = dict(cval)
        # 後方互換: material-curve-columnsがトップレベルにある場合はabaqusコネクタに移行
        if "material-curve-columns" in data and "abaqus" not in connector_configs:
            raw_mcc = data["material-curve-columns"]
            if isinstance(raw_mcc, dict):
                connector_configs["abaqus"] = {"material-curve-columns": raw_mcc}
        # NG領域定義の読み込み
        raw_ng_regions = data.get("ng-regions", [])
        if not isinstance(raw_ng_regions, list):
            raw_ng_regions = []
        ng_regions: list[dict[str, Any]] = []
        for r in raw_ng_regions:
            if isinstance(r, dict):
                ng_regions.append(dict(r))
        # グループ結線キー
        group_line_key = data.get("group-line-key")
        if group_line_key is not None:
            group_line_key = str(group_line_key)
        # プロットスタイル（plot.style セクション）
        raw_plot_style = plot.get("style", {})
        if not isinstance(raw_plot_style, dict):
            raw_plot_style = {}
        plot_style: dict[str, int] = {}
        for ps_key in ("marker_size", "line_width", "font_size"):
            ps_val = raw_plot_style.get(ps_key) or raw_plot_style.get(ps_key.replace("_", "-"))
            if ps_val is not None:
                plot_style[ps_key] = int(ps_val)
        return cls(
            table_columns=[str(c) for c in table_columns] if table_columns else None,
            default_filters=default_filters,
            plot_x=str(plot["x"]) if plot.get("x") is not None else None,
            plot_y=str(plot["y"]) if plot.get("y") is not None else None,
            gallery_columns=gallery_columns,
            gallery_rows=gallery_rows,
            saved_views=saved_views,
            connector_configs=connector_configs,
            ng_regions=ng_regions,
            group_line_key=group_line_key,
            plot_style=plot_style,
        )


@dataclass(frozen=True)
class ExportConfig:
    """エクスポート設定: CSVカラム選択・単位マッピング"""

    csv_columns: list[str] | None
    units: dict[str, str]
    csv_unit_format: str  # "header" or "row"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExportConfig:
        if not data:
            return cls(csv_columns=None, units={}, csv_unit_format="header")
        csv_columns = data.get("csv-columns")
        if csv_columns is not None and not isinstance(csv_columns, list):
            raise ValueError("csv-columns must be list[str]")
        units = data.get("units", {})
        if not isinstance(units, dict):
            raise ValueError("units must be dict[str, str]")
        csv_unit_format = data.get("csv-unit-format", "header")
        if csv_unit_format not in ("header", "row"):
            raise ValueError("csv-unit-format must be 'header' or 'row'")
        return cls(
            csv_columns=[str(c) for c in csv_columns] if csv_columns else None,
            units={str(k): str(v) for k, v in units.items()},
            csv_unit_format=str(csv_unit_format),
        )


@dataclass(frozen=True)
class SolverProfileConfig:
    """ソルバー別のファイル解釈ルール

    各CAEソルバーのファイル構造の差異を吸収する設定。
    ソルバーごとに入力/結果ファイルの拡張子、命名パターン、
    ソース単位（ファイル/ディレクトリ）を定義する。

    参照: docs/specs/multi-solver.md
    """

    name: str
    source_unit: str  # "file" | "directory"
    filename_pattern: str  # "standard" | "reversed" | "none"
    input_extensions: tuple[str, ...]
    result_extensions: tuple[str, ...]
    result_filenames: tuple[str, ...]  # 拡張子なしの結果ファイル名
    input_prefixes: tuple[str, ...]  # Flow-3D: prepin等
    result_prefixes: tuple[str, ...]  # Flow-3D: flsgrf等
    input_directories: tuple[str, ...]  # OpenFOAM: system等
    result_directory_pattern: str  # OpenFOAM: 数字ディレクトリの正規表現

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> SolverProfileConfig:
        source_unit = str(data.get("source-unit", "file"))
        if source_unit not in ("file", "directory"):
            raise ValueError(f"source-unit must be 'file' or 'directory', got '{source_unit}'")
        filename_pattern = str(data.get("filename-pattern", "standard"))
        if filename_pattern not in ("standard", "reversed", "none"):
            raise ValueError(f"filename-pattern must be 'standard', 'reversed', or 'none', got '{filename_pattern}'")
        return cls(
            name=name,
            source_unit=source_unit,
            filename_pattern=filename_pattern,
            input_extensions=tuple(str(x) for x in (data.get("input-extensions") or [])),
            result_extensions=tuple(str(x) for x in (data.get("result-extensions") or [])),
            result_filenames=tuple(str(x) for x in (data.get("result-filenames") or [])),
            input_prefixes=tuple(str(x) for x in (data.get("input-prefixes") or [])),
            result_prefixes=tuple(str(x) for x in (data.get("result-prefixes") or [])),
            input_directories=tuple(str(x) for x in (data.get("input-directories") or [])),
            result_directory_pattern=str(data.get("result-directory-pattern", "")),
        )


# デフォルトのソルバープロファイル（Abaqus互換）
_DEFAULT_SOLVER_PROFILE = SolverProfileConfig(
    name="default",
    source_unit="file",
    filename_pattern="standard",
    input_extensions=(".inp",),
    result_extensions=(".odb", ".sta", ".msg", ".dat"),
    result_filenames=(),
    input_prefixes=(),
    result_prefixes=(),
    input_directories=(),
    result_directory_pattern="",
)


@dataclass(frozen=True)
class SolverDetectionConfig:
    """ソルバー自動検出設定: パスパターンからソルバープロファイルを特定

    solver-detection:
      "**/*.k | **/*.key": lsdyna
      "**/prepin.*": flow3d
    """

    rules: list[tuple[list[str], str]]  # (patterns, profile_name)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SolverDetectionConfig:
        rules: list[tuple[list[str], str]] = []
        if not data:
            return cls(rules=[])
        for pattern_key, profile_name in data.items():
            patterns = [p.strip() for p in pattern_key.split("|")]
            rules.append((patterns, str(profile_name)))
        return cls(rules=rules)

    def detect(self, path: str) -> str | None:
        """パスからソルバープロファイル名を検出（マッチしない場合はNone）"""
        for patterns, profile_name in self.rules:
            for pattern in patterns:
                if _match_path_pattern(path, pattern):
                    return profile_name
        return None


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
    export: ExportConfig
    dashboard: DashboardConfig
    directory_max_depth: int | None  # None=無制限（最終階層まで）
    include_search_depth: int  # *INCLUDEファイル探索の最大階層数（デフォルト5）
    cache_max_age_days: int  # プラグインキャッシュ保持期間（日数、デフォルト30）
    cache_max_count: int  # プラグインキャッシュ最大保持数（デフォルト100）
    verbose_name_format: str | None  # verbose_nameのフォーマットテンプレート（例: "条件{idx}(高さ{t},荷重{F})"）
    solver_profiles: dict[str, SolverProfileConfig]  # ソルバー別設定プロファイル
    solver_detection: SolverDetectionConfig  # ソルバー自動検出ルール
    csv_max_rows: int  # CSV読み込み最大行数（0=無制限、超過時はサマリーモード）

    def detect_solver_profile(self, path: str) -> SolverProfileConfig:
        """パスからソルバープロファイルを検出

        solver-detectionルールにマッチするパスの場合、対応するプロファイルを返す。
        マッチしない場合はデフォルト（Abaqus互換）プロファイルを返す。

        Args:
            path: チェック対象のパス（POSIX形式）

        Returns:
            該当するSolverProfileConfig
        """
        profile_name = self.solver_detection.detect(path)
        if profile_name and profile_name in self.solver_profiles:
            return self.solver_profiles[profile_name]
        return self.solver_profiles.get("default", _DEFAULT_SOLVER_PROFILE)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphConfig:
        raw_depth = data.get("directory-max-depth")
        if raw_depth is not None:
            raw_depth = int(raw_depth)
            if raw_depth < 1:
                raise ValueError("directory-max-depth must be >= 1")
        raw_include_depth = data.get("include-search-depth", 5)
        include_depth = int(raw_include_depth)
        if include_depth < 0:
            raise ValueError("include-search-depth must be >= 0")
        cache_max_age = int(data.get("cache-max-age-days", 30))
        cache_max_count = int(data.get("cache-max-count", 100))
        csv_max_rows = int(data.get("csv-max-rows", 0))

        # ソルバープロファイルの読み込み
        raw_profiles = data.get("solver-profiles", {})
        solver_profiles: dict[str, SolverProfileConfig] = {}
        if isinstance(raw_profiles, dict):
            for pname, pdata in raw_profiles.items():
                if isinstance(pdata, dict):
                    solver_profiles[str(pname)] = SolverProfileConfig.from_dict(str(pname), pdata)
        # デフォルトプロファイルが未定義の場合は追加
        if "default" not in solver_profiles:
            solver_profiles["default"] = _DEFAULT_SOLVER_PROFILE

        # ソルバー検出ルールの読み込み
        solver_detection = SolverDetectionConfig.from_dict(data.get("solver-detection", {}))

        # verbose-name-format: フォーマットテンプレート
        raw_vnf = data.get("verbose-name-format")
        verbose_name_format = str(raw_vnf) if raw_vnf is not None else None

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
            export=ExportConfig.from_dict(data.get("export", {})),
            dashboard=DashboardConfig.from_dict(data.get("dashboard", {})),
            directory_max_depth=raw_depth,
            include_search_depth=include_depth,
            cache_max_age_days=cache_max_age,
            cache_max_count=cache_max_count,
            verbose_name_format=verbose_name_format,
            solver_profiles=solver_profiles,
            solver_detection=solver_detection,
            csv_max_rows=csv_max_rows,
        )

    @classmethod
    def load(cls, base_dir: Path | None = None) -> GraphConfig:
        """プロジェクト設定を読み込んでGraphConfigを生成

        config.yamlのvocabセクションとvocab.yamlのmappingをマージする。
        vocab.yamlのmappingが優先される（config.yamlの同一キーを上書き）。
        """
        config_data = load_project_config(base_dir)
        # vocab.yamlのmappingをGraphConfig.vocabにマージ
        vocab_config = load_vocab_config(base_dir)
        config_vocab = config_data.get("vocab", {})
        if not isinstance(config_vocab, dict):
            config_vocab = {}
        merged_vocab = {**config_vocab, **vocab_config.mapping}
        config_data["vocab"] = merged_vocab
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
        return normalized_path.startswith(dir_prefix) or normalized_path == dir_name

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


def init_graph_config(base_dir: Path | None = None, overwrite: bool = False) -> Path:
    """グラフ設定ファイルを初期化（default-config.yamlをコメント付きでコピー）

    コメントや使用例を保持するため、yaml.safe_dumpではなく
    default-config.yamlをテキストとして直接コピーする。

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

    # default-config.yamlをコメント付きで直接コピー
    default_path = get_default_config_path()
    if default_path.exists():
        import shutil

        shutil.copy2(default_path, config_path)
    else:
        # フォールバック: 辞書からyaml生成
        default_config = load_default_config()
        with config_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(default_config, f, allow_unicode=True, sort_keys=False)

    return config_path
