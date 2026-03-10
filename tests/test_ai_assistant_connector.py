"""AIアシスタント ダッシュボードコネクター テスト (T7-6)

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# ====================================================================
# ヘルパー
# ====================================================================


def _make_tips_file(tmp_path: Path, tips: list[dict]) -> Path:
    """テスト用tips.jsonを作成"""
    storage_dir = tmp_path / ".j2" / "storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    tips_path = storage_dir / "tips.json"
    tips_path.write_text(json.dumps(tips, ensure_ascii=False), encoding="utf-8")
    return tips_path


def _make_rag_index_file(tmp_path: Path, entries: list[dict]) -> Path:
    """テスト用rag_index.jsonを作成"""
    storage_dir = tmp_path / ".j2" / "storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    rag_path = storage_dir / "rag_index.json"
    rag_path.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    return rag_path


# ====================================================================
# コネクター登録テスト
# ====================================================================


class TestAIAssistantConnectorRegistration:
    """AIAssistantPageConnectorの登録テスト"""

    def test_registered_in_registry(self):
        """page_label = 'AIアシスタント' でレジストリに登録されること"""
        from services.dashboard.connectors import DashboardPageConnector
        from services.dashboard.connectors.ai_assistant import AIAssistantPageConnector

        assert "AIアシスタント" in DashboardPageConnector._registry
        assert DashboardPageConnector._registry["AIアシスタント"] is AIAssistantPageConnector

    def test_connector_key(self):
        """connector_key = 'ai' であること"""
        from services.dashboard.connectors.ai_assistant import AIAssistantPageConnector

        assert AIAssistantPageConnector.connector_key == "ai"


# ====================================================================
# is_available テスト
# ====================================================================


class TestAIAssistantAvailability:
    """is_available判定のテスト"""

    def test_available_when_configured(self):
        """AI設定がある場合にTrueを返すこと"""
        from services.dashboard.connectors.ai_assistant import AIAssistantPageConnector

        connector = AIAssistantPageConnector()
        mock_provider = MagicMock()
        with patch(
            "services.dashboard.connectors.ai_assistant._is_ai_configured",
            return_value=True,
        ):
            assert connector.is_available(mock_provider) is True

    def test_unavailable_when_not_configured(self):
        """AI設定がない場合にFalseを返すこと"""
        from services.dashboard.connectors.ai_assistant import AIAssistantPageConnector

        connector = AIAssistantPageConnector()
        mock_provider = MagicMock()
        with patch(
            "services.dashboard.connectors.ai_assistant._is_ai_configured",
            return_value=False,
        ):
            assert connector.is_available(mock_provider) is False


# ====================================================================
# _is_ai_configured テスト
# ====================================================================


class TestIsAIConfigured:
    """_is_ai_configured関数のテスト"""

    def test_returns_true_for_ollama(self):
        """provider=ollamaでTrueを返すこと"""
        from services.dashboard.connectors.ai_assistant import _is_ai_configured

        with patch(
            "config.load_project_config",
            return_value={"ai": {"provider": "ollama"}},
        ):
            assert _is_ai_configured() is True

    def test_returns_false_for_disabled(self):
        """provider=disabledでFalseを返すこと"""
        from services.dashboard.connectors.ai_assistant import _is_ai_configured

        with patch(
            "config.load_project_config",
            return_value={"ai": {"provider": "disabled"}},
        ):
            assert _is_ai_configured() is False

    def test_returns_false_for_empty_config(self):
        """ai設定がない場合にFalseを返すこと"""
        from services.dashboard.connectors.ai_assistant import _is_ai_configured

        with patch(
            "config.load_project_config",
            return_value={},
        ):
            assert _is_ai_configured() is False

    def test_returns_false_on_exception(self):
        """例外発生時にFalseを返すこと"""
        from services.dashboard.connectors.ai_assistant import _is_ai_configured

        with patch(
            "config.load_project_config",
            side_effect=FileNotFoundError,
        ):
            assert _is_ai_configured() is False


# ====================================================================
# _init_provider テスト
# ====================================================================


class TestInitProvider:
    """_init_provider関数のテスト"""

    def test_returns_true_if_already_set(self):
        """既にプロバイダが設定済みならTrueを返すこと"""
        from services.dashboard.connectors.ai_assistant import _init_provider

        mock_provider = MagicMock()
        with patch("services.ai.get_provider", return_value=mock_provider):
            assert _init_provider() is True

    def test_returns_false_on_failure(self):
        """プロバイダ作成失敗時にFalseを返すこと"""
        from services.dashboard.connectors.ai_assistant import _init_provider

        with (
            patch("services.ai.get_provider", return_value=None),
            patch(
                "config.load_project_config",
                side_effect=FileNotFoundError,
            ),
        ):
            assert _init_provider() is False


# ====================================================================
# TipsStore読み込みテスト
# ====================================================================


class TestLoadTipsStore:
    """_load_tips_storeのテスト"""

    def test_loads_from_storage(self, tmp_path):
        """tips.jsonからTipsを正しくロードすること"""
        tips_data = [{"id": 1, "title": "Tip1", "body": "Body1", "tags": ["test"], "source": ""}]
        _make_tips_file(tmp_path, tips_data)

        from services.ai.tips import TipsStore

        store = TipsStore(storage_path=tmp_path / ".j2" / "storage" / "tips.json")
        store.load()

        assert store.size == 1
        assert store.list_all()[0]["title"] == "Tip1"

    def test_empty_when_no_file(self, tmp_path):
        """ファイルがない場合は空のストアを返すこと"""
        from services.ai.tips import TipsStore

        store = TipsStore(storage_path=tmp_path / ".j2" / "storage" / "tips.json")
        store.load()
        assert store.size == 0


# ====================================================================
# RagIndex読み込みテスト
# ====================================================================


class TestLoadRagIndex:
    """_load_rag_indexのテスト"""

    def test_loads_from_storage(self, tmp_path):
        """rag_index.jsonからインデックスを正しくロードすること"""
        entries = [
            {
                "file": "test.py",
                "chunk_index": 0,
                "text": "hello world",
                "embedding": [0.1, 0.2, 0.3],
            }
        ]
        _make_rag_index_file(tmp_path, entries)

        from services.ai.rag import RagIndex

        index = RagIndex(storage_path=tmp_path / ".j2" / "storage" / "rag_index.json")
        index.load()

        assert index.size == 1
        assert index.indexed_files == ["test.py"]

    def test_empty_when_no_file(self, tmp_path):
        """ファイルがない場合は空のインデックスを返すこと"""
        from services.ai.rag import RagIndex

        index = RagIndex(storage_path=tmp_path / ".j2" / "storage" / "rag_index.json")
        index.load()
        assert index.size == 0


# ====================================================================
# HTML生成テスト
# ====================================================================


class TestAIAssistantGenerateHTML:
    """generate_htmlのテスト"""

    def test_empty_tips_html(self):
        """Tipsが空の場合のHTML"""
        from services.dashboard.connectors.ai_assistant import AIAssistantPageConnector

        connector = AIAssistantPageConnector()
        mock_provider = MagicMock()
        mock_config = MagicMock()

        with patch("services.dashboard.connectors.ai_assistant._load_tips_store") as mock_store_fn:
            mock_store = MagicMock()
            mock_store.list_all.return_value = []
            mock_store_fn.return_value = mock_store

            html = connector.generate_html(mock_provider, mock_config)
            assert "AIアシスタント" in html
            assert "まだありません" in html

    def test_tips_html_with_data(self):
        """TipsがあるときのHTML"""
        from services.dashboard.connectors.ai_assistant import AIAssistantPageConnector

        connector = AIAssistantPageConnector()
        mock_provider = MagicMock()
        mock_config = MagicMock()

        tips = [
            {"title": "テストTip", "body": "テスト内容", "tags": ["python", "test"]},
            {"title": "Tip2", "body": "内容2", "tags": []},
        ]

        with patch("services.dashboard.connectors.ai_assistant._load_tips_store") as mock_store_fn:
            mock_store = MagicMock()
            mock_store.list_all.return_value = tips
            mock_store_fn.return_value = mock_store

            html = connector.generate_html(mock_provider, mock_config)
            assert "テストTip" in html
            assert "テスト内容" in html
            assert "python, test" in html
            assert "合計: 2件" in html
