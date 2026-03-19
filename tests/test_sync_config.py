"""同期設定のテスト"""

from config import SharedFolderMapping, SyncConfig


class TestSyncConfig:
    def test_from_dict_empty(self):
        config = SyncConfig.from_dict(None)
        assert config.exclude == []
        assert config.shared_folder_mappings == []
        assert config.gitlab_url == ""
        assert config.gitlab_token_env == "GITLAB_TOKEN"
        assert config.gitlab_default_group == ""

    def test_from_dict_full(self):
        data = {
            "exclude": ["*.odb", "*.res", "__pycache__"],
            "shared_folder": {
                "folder_mappings": [
                    {"local": "C:/projects/", "shared": "\\\\server\\share\\projects\\"},
                    {"local": "D:/work/", "shared": "\\\\nas01\\data\\work\\"},
                ]
            },
            "gitlab": {
                "url": "https://gitlab.example.com",
                "token_env": "MY_GL_TOKEN",
                "default_group": "cae-team",
            },
        }
        config = SyncConfig.from_dict(data)
        assert config.exclude == ["*.odb", "*.res", "__pycache__"]
        assert len(config.shared_folder_mappings) == 2
        assert config.shared_folder_mappings[0].local == "C:/projects/"
        assert config.shared_folder_mappings[0].shared == "\\\\server\\share\\projects\\"
        assert config.gitlab_url == "https://gitlab.example.com"
        assert config.gitlab_token_env == "MY_GL_TOKEN"
        assert config.gitlab_default_group == "cae-team"

    def test_from_dict_partial(self):
        data = {"exclude": ["*.odb"]}
        config = SyncConfig.from_dict(data)
        assert config.exclude == ["*.odb"]
        assert config.shared_folder_mappings == []
        assert config.gitlab_url == ""

    def test_resolve_shared_path(self):
        config = SyncConfig(
            exclude=[],
            shared_folder_mappings=[
                SharedFolderMapping(local="C:/projects/", shared="\\\\server\\share\\projects\\"),
            ],
            gitlab_url="",
            gitlab_token_env="GITLAB_TOKEN",
            gitlab_default_group="",
        )
        result = config.resolve_shared_path("C:/projects/myapp/v1")
        assert result == "\\\\server\\share\\projects\\myapp\\v1"

    def test_resolve_shared_path_exact_base(self):
        config = SyncConfig(
            exclude=[],
            shared_folder_mappings=[
                SharedFolderMapping(local="C:/projects/", shared="\\\\server\\share\\projects\\"),
            ],
            gitlab_url="",
            gitlab_token_env="GITLAB_TOKEN",
            gitlab_default_group="",
        )
        result = config.resolve_shared_path("C:/projects/")
        assert result == "\\\\server\\share\\projects"

    def test_resolve_shared_path_no_match(self):
        config = SyncConfig(
            exclude=[],
            shared_folder_mappings=[
                SharedFolderMapping(local="C:/projects/", shared="\\\\server\\share\\projects\\"),
            ],
            gitlab_url="",
            gitlab_token_env="GITLAB_TOKEN",
            gitlab_default_group="",
        )
        result = config.resolve_shared_path("D:/other/path")
        assert result is None

    def test_resolve_shared_path_no_mappings(self):
        config = SyncConfig.from_dict(None)
        assert config.resolve_shared_path("C:/anything") is None

    def test_resolve_local_path(self):
        config = SyncConfig(
            exclude=[],
            shared_folder_mappings=[
                SharedFolderMapping(local="C:/projects/", shared="\\\\server\\share\\projects\\"),
            ],
            gitlab_url="",
            gitlab_token_env="GITLAB_TOKEN",
            gitlab_default_group="",
        )
        result = config.resolve_local_path("\\\\server\\share\\projects\\myapp\\v1")
        assert result == "C:/projects/myapp/v1"

    def test_resolve_local_path_no_match(self):
        config = SyncConfig(
            exclude=[],
            shared_folder_mappings=[
                SharedFolderMapping(local="C:/projects/", shared="\\\\server\\share\\projects\\"),
            ],
            gitlab_url="",
            gitlab_token_env="GITLAB_TOKEN",
            gitlab_default_group="",
        )
        result = config.resolve_local_path("\\\\other\\server\\path")
        assert result is None

    def test_invalid_mapping_entries_skipped(self):
        data = {
            "shared_folder": {
                "folder_mappings": [
                    {"local": "C:/a/", "shared": "\\\\s\\a\\"},
                    {"local": "C:/b/"},  # sharedなし → スキップ
                    "invalid",  # dict以外 → スキップ
                ]
            }
        }
        config = SyncConfig.from_dict(data)
        assert len(config.shared_folder_mappings) == 1
