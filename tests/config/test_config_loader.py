import pytest
import yaml

from config import (
    DEFAULT_EXTENSIONS,
    DEFAULT_PREFIXES,
    ExtensionsConfig,
    PrefixesConfig,
    get_config_dir,
    init_config_dir,
    load_extensions_config,
    load_prefixes_config,
    load_vocab_config,
    migrate_legacy_configs,
)


class TestExtensionsConfig:
    def test_from_dict_valid(self):
        data = {
            "calculation_input": [".inp", ".cas.h5"],
            "mesh": [".cdb", ".msh"],
            "multi_dot": [".cas.h5", ".tar.gz"],
        }
        config = ExtensionsConfig.from_dict(data)
        assert config.calculation_input == [".inp", ".cas.h5"]
        assert config.mesh == [".cdb", ".msh"]
        assert config.multi_dot == [".cas.h5", ".tar.gz"]

    def test_from_dict_empty(self):
        data = {}
        config = ExtensionsConfig.from_dict(data)
        assert config.calculation_input == []
        assert config.mesh == []
        assert config.multi_dot == []

    def test_from_dict_invalid_type(self):
        data = {"calculation_input": "not a list"}
        with pytest.raises(ValueError, match="calculation_input must be list"):
            ExtensionsConfig.from_dict(data)


class TestPrefixesConfig:
    def test_from_dict_valid(self):
        data = {
            "prefixes": {
                "go_": "calculation_input",
                "mesh_": "mesh",
            }
        }
        config = PrefixesConfig.from_dict(data)
        assert config.prefixes == {"go_": "calculation_input", "mesh_": "mesh"}

    def test_from_dict_empty(self):
        data = {}
        config = PrefixesConfig.from_dict(data)
        assert config.prefixes == {}

    def test_from_dict_invalid_type(self):
        data = {"prefixes": ["not", "a", "dict"]}
        with pytest.raises(ValueError, match="prefixes must be dict"):
            PrefixesConfig.from_dict(data)


class TestLoadExtensionsConfig:
    def test_load_with_file(self, tmp_path):
        # Create config dir with extensions.yaml
        config_dir = tmp_path / ".j2" / "config"
        config_dir.mkdir(parents=True)
        extensions_path = config_dir / "extensions.yaml"
        data = {
            "calculation_input": [".inp", ".key"],
            "mesh": [".msh"],
            "multi_dot": [".tar.gz"],
        }
        with extensions_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            config = load_extensions_config(base_dir=tmp_path)
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "extensions.yaml" in str(w[0].message)
        assert config.calculation_input == [".inp", ".key"]
        assert config.mesh == [".msh"]
        assert config.multi_dot == [".tar.gz"]

    def test_load_without_file(self, tmp_path):
        # No extensions.yaml file exists
        config_dir = tmp_path / ".j2" / "config"
        config_dir.mkdir(parents=True)

        config = load_extensions_config(base_dir=tmp_path)
        assert config.calculation_input == DEFAULT_EXTENSIONS["calculation_input"]
        assert config.mesh == DEFAULT_EXTENSIONS["mesh"]
        assert config.multi_dot == DEFAULT_EXTENSIONS["multi_dot"]


class TestLoadPrefixesConfig:
    def test_load_with_file(self, tmp_path):
        # Create config dir with prefixes.yaml
        config_dir = tmp_path / ".j2" / "config"
        config_dir.mkdir(parents=True)
        prefixes_path = config_dir / "prefixes.yaml"
        data = {
            "prefixes": {
                "go_": "calculation_input",
                "custom_": "custom_type",
            }
        }
        with prefixes_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            config = load_prefixes_config(base_dir=tmp_path)
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "prefixes.yaml" in str(w[0].message)
        assert config.prefixes == {"go_": "calculation_input", "custom_": "custom_type"}

    def test_load_without_file(self, tmp_path):
        # No prefixes.yaml file exists
        config_dir = tmp_path / ".j2" / "config"
        config_dir.mkdir(parents=True)

        config = load_prefixes_config(base_dir=tmp_path)
        assert config.prefixes == DEFAULT_PREFIXES


class TestInitConfigDir:
    def test_init_creates_dir_and_files(self, tmp_path):
        # Initialize config directory
        init_config_dir(base_dir=tmp_path)

        config_dir = get_config_dir(tmp_path)
        assert config_dir.exists()

        # Check that minimal files are created
        vocab_path = config_dir / "vocab.yaml"
        config_path = config_dir / "config.yaml"

        assert vocab_path.exists()
        assert config_path.exists()

        # extensions.yaml/prefixes.yamlは二層config方式で不要になった
        extensions_path = config_dir / "extensions.yaml"
        prefixes_path = config_dir / "prefixes.yaml"
        assert not extensions_path.exists()
        assert not prefixes_path.exists()

        # Check vocab.yaml content
        with vocab_path.open("r", encoding="utf-8") as f:
            vocab_data = yaml.safe_load(f)
        assert vocab_data == {"mapping": {}, "categories": {}}

        # Check config.yaml is a template (comments only, no actual config)
        with config_path.open("r", encoding="utf-8") as f:
            config_content = f.read()
        assert "project-name" in config_content
        assert "default-config.yaml" in config_content

    def test_init_skips_if_exists(self, tmp_path):
        # Create config directory and files
        config_dir = get_config_dir(tmp_path)
        config_dir.mkdir(parents=True)
        vocab_path = config_dir / "vocab.yaml"
        custom_data = {"mapping": {"custom": "value"}, "categories": {}}
        with vocab_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(custom_data, f)

        # Initialize should skip
        init_config_dir(base_dir=tmp_path)

        # Check that custom data is preserved
        with vocab_path.open("r", encoding="utf-8") as f:
            vocab_data = yaml.safe_load(f)
        assert vocab_data == custom_data


class TestLoadVocabConfig:
    def test_load_with_file(self, tmp_path):
        # Create config dir with vocab.yaml
        config_dir = tmp_path / ".j2" / "config"
        config_dir.mkdir(parents=True)
        vocab_path = config_dir / "vocab.yaml"
        data = {
            "mapping": {"key1": "value1"},
            "categories": {"cat1": ["item1", "item2"]},
        }
        with vocab_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

        config = load_vocab_config(base_dir=tmp_path)
        assert config.mapping == {"key1": "value1"}
        assert config.categories == {"cat1": ["item1", "item2"]}

    def test_load_without_file(self, tmp_path):
        # No vocab.yaml file exists
        config_dir = tmp_path / ".j2" / "config"
        config_dir.mkdir(parents=True)

        config = load_vocab_config(base_dir=tmp_path)
        assert config.mapping == {}
        assert config.categories == {}


class TestMigrateLegacyConfigs:
    def test_no_legacy_files(self, tmp_path):
        """レガシーファイルなしの場合"""
        config_dir = tmp_path / ".j2" / "config"
        config_dir.mkdir(parents=True)

        result = migrate_legacy_configs(base_dir=tmp_path, check_only=True)
        assert result["legacy_files"] == []
        assert result["changes"] == []
        assert result["merged"] == {}

    def test_detect_extensions_diff(self, tmp_path):
        """extensions.yamlのデフォルトとの差分検出"""
        config_dir = tmp_path / ".j2" / "config"
        config_dir.mkdir(parents=True)
        ext_path = config_dir / "extensions.yaml"
        data = {
            "calculation_input": [".inp", ".key"],  # デフォルトと異なる
            "mesh": [".cdb", ".msh", ".unv"],  # デフォルトと同じ
        }
        with ext_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

        result = migrate_legacy_configs(base_dir=tmp_path, check_only=True)
        assert len(result["legacy_files"]) == 1
        assert len(result["changes"]) == 1
        assert "calculation_input" in result["changes"][0]
        assert "default-extensions" in result["merged"]

    def test_detect_prefixes_diff(self, tmp_path):
        """prefixes.yamlのデフォルトとの差分検出"""
        config_dir = tmp_path / ".j2" / "config"
        config_dir.mkdir(parents=True)
        pfx_path = config_dir / "prefixes.yaml"
        data = {
            "prefixes": {
                "go_": "calculation_input",
                "custom_": "custom_type",  # デフォルトにないキー
            }
        }
        with pfx_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

        result = migrate_legacy_configs(base_dir=tmp_path, check_only=True)
        assert len(result["legacy_files"]) == 1
        assert any("custom_" in c for c in result["changes"])
        assert "prefixes" in result["merged"]

    def test_check_only_does_not_write(self, tmp_path):
        """check_only=Trueで書き込みしない"""
        config_dir = tmp_path / ".j2" / "config"
        config_dir.mkdir(parents=True)
        ext_path = config_dir / "extensions.yaml"
        data = {"calculation_input": [".inp", ".key"]}
        with ext_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

        migrate_legacy_configs(base_dir=tmp_path, check_only=True)
        config_path = config_dir / "config.yaml"
        assert not config_path.exists()

    def test_migrate_writes_config(self, tmp_path):
        """実行時にconfig.yamlに書き込む"""
        config_dir = tmp_path / ".j2" / "config"
        config_dir.mkdir(parents=True)
        ext_path = config_dir / "extensions.yaml"
        data = {"calculation_input": [".inp", ".key"]}
        with ext_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

        migrate_legacy_configs(base_dir=tmp_path, check_only=False)
        config_path = config_dir / "config.yaml"
        assert config_path.exists()
        with config_path.open("r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        assert "default-extensions" in config_data
        assert config_data["default-extensions"]["calculation_input"] == [".inp", ".key"]

    def test_migrate_preserves_existing_config(self, tmp_path):
        """既存config.yamlの内容を保持"""
        config_dir = tmp_path / ".j2" / "config"
        config_dir.mkdir(parents=True)

        # 既存config.yaml
        config_path = config_dir / "config.yaml"
        existing = {"project-name": "test-project", "vocab": {"key": "value"}}
        with config_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(existing, f)

        # extensions.yaml
        ext_path = config_dir / "extensions.yaml"
        with ext_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump({"calculation_input": [".inp", ".key"]}, f)

        migrate_legacy_configs(base_dir=tmp_path, check_only=False)
        with config_path.open("r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        assert config_data["project-name"] == "test-project"
        assert config_data["vocab"] == {"key": "value"}
        assert "default-extensions" in config_data

    def test_default_values_no_changes(self, tmp_path):
        """デフォルト値と同一の場合は変更なし"""
        config_dir = tmp_path / ".j2" / "config"
        config_dir.mkdir(parents=True)
        ext_path = config_dir / "extensions.yaml"
        with ext_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(DEFAULT_EXTENSIONS, f)

        result = migrate_legacy_configs(base_dir=tmp_path, check_only=True)
        assert len(result["legacy_files"]) == 1
        assert result["changes"] == []
        assert result["merged"] == {}
