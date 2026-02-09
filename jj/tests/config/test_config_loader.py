import tempfile
from pathlib import Path

import pytest
import yaml

from config import (
    DEFAULT_EXTENSIONS,
    DEFAULT_PREFIXES,
    ExtensionsConfig,
    PrefixesConfig,
    VocabConfig,
    get_config_dir,
    init_config_dir,
    load_extensions_config,
    load_prefixes_config,
    load_vocab_config,
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
        config_dir = tmp_path / ".jj" / "config"
        config_dir.mkdir(parents=True)
        extensions_path = config_dir / "extensions.yaml"
        data = {
            "calculation_input": [".inp", ".key"],
            "mesh": [".msh"],
            "multi_dot": [".tar.gz"],
        }
        with extensions_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

        config = load_extensions_config(base_dir=tmp_path)
        assert config.calculation_input == [".inp", ".key"]
        assert config.mesh == [".msh"]
        assert config.multi_dot == [".tar.gz"]

    def test_load_without_file(self, tmp_path):
        # No extensions.yaml file exists
        config_dir = tmp_path / ".jj" / "config"
        config_dir.mkdir(parents=True)

        config = load_extensions_config(base_dir=tmp_path)
        assert config.calculation_input == DEFAULT_EXTENSIONS["calculation_input"]
        assert config.mesh == DEFAULT_EXTENSIONS["mesh"]
        assert config.multi_dot == DEFAULT_EXTENSIONS["multi_dot"]


class TestLoadPrefixesConfig:
    def test_load_with_file(self, tmp_path):
        # Create config dir with prefixes.yaml
        config_dir = tmp_path / ".jj" / "config"
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

        config = load_prefixes_config(base_dir=tmp_path)
        assert config.prefixes == {"go_": "calculation_input", "custom_": "custom_type"}

    def test_load_without_file(self, tmp_path):
        # No prefixes.yaml file exists
        config_dir = tmp_path / ".jj" / "config"
        config_dir.mkdir(parents=True)

        config = load_prefixes_config(base_dir=tmp_path)
        assert config.prefixes == DEFAULT_PREFIXES


class TestInitConfigDir:
    def test_init_creates_dir_and_files(self, tmp_path):
        # Initialize config directory
        init_config_dir(base_dir=tmp_path)

        config_dir = get_config_dir(tmp_path)
        assert config_dir.exists()

        # Check that default files are created
        vocab_path = config_dir / "vocab.yaml"
        extensions_path = config_dir / "extensions.yaml"
        prefixes_path = config_dir / "prefixes.yaml"

        assert vocab_path.exists()
        assert extensions_path.exists()
        assert prefixes_path.exists()

        # Check vocab.yaml content
        with vocab_path.open("r", encoding="utf-8") as f:
            vocab_data = yaml.safe_load(f)
        assert vocab_data == {"mapping": {}, "categories": {}}

        # Check extensions.yaml content
        with extensions_path.open("r", encoding="utf-8") as f:
            extensions_data = yaml.safe_load(f)
        assert extensions_data == DEFAULT_EXTENSIONS

        # Check prefixes.yaml content
        with prefixes_path.open("r", encoding="utf-8") as f:
            prefixes_data = yaml.safe_load(f)
        assert prefixes_data == {"prefixes": DEFAULT_PREFIXES}

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
        config_dir = tmp_path / ".jj" / "config"
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
        config_dir = tmp_path / ".jj" / "config"
        config_dir.mkdir(parents=True)

        config = load_vocab_config(base_dir=tmp_path)
        assert config.mapping == {}
        assert config.categories == {}
