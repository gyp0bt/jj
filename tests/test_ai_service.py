"""T7: AI連携サービスのテスト

AIProviderプロトコル、OllamaProvider、summarizer、diff_analyzerのユニットテスト。
Ollamaサーバー不要（モック使用）。
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from typing import Any

import pytest

from services.ai import AIProvider, get_provider, require_provider, set_provider

# ================================================================
# AIProvider プロトコル
# ================================================================


class MockProvider:
    """テスト用AIプロバイダ"""

    def __init__(self, response: str = "テスト応答", is_available: bool = True):
        self._response = response
        self._available = is_available

    @property
    def name(self) -> str:
        return "mock"

    @property
    def available(self) -> bool:
        return self._available

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        return self._response

    def summarize(self, text: str, **kwargs: Any) -> str:
        return f"要約: {self._response}"

    def embed(self, text: str, **kwargs: Any) -> list[float]:
        """テキストの長さに基づく簡易ベクトルを返す（テスト用）"""
        # 簡易的に文字列のハッシュから4次元ベクトルを生成
        h = hash(text)
        return [
            ((h >> 0) & 0xFF) / 255.0,
            ((h >> 8) & 0xFF) / 255.0,
            ((h >> 16) & 0xFF) / 255.0,
            ((h >> 24) & 0xFF) / 255.0,
        ]


class TestAIProviderProtocol:
    """AIProviderプロトコルのテスト"""

    def test_mock_provider_is_ai_provider(self):
        """MockProviderがAIProviderプロトコルを満たす"""
        provider = MockProvider()
        assert isinstance(provider, AIProvider)

    def test_get_set_provider(self):
        """プロバイダの登録と取得"""
        # クリーンアップ
        import services.ai as ai_mod

        old = ai_mod._provider
        try:
            ai_mod._provider = None
            assert get_provider() is None

            provider = MockProvider()
            set_provider(provider)
            assert get_provider() is provider
        finally:
            ai_mod._provider = old

    def test_require_provider_raises_when_none(self):
        """プロバイダ未設定時にValueError"""
        import services.ai as ai_mod

        old = ai_mod._provider
        try:
            ai_mod._provider = None
            with pytest.raises(ValueError, match="AIプロバイダが設定されていません"):
                require_provider()
        finally:
            ai_mod._provider = old

    def test_require_provider_raises_when_unavailable(self):
        """プロバイダが利用不可時にValueError"""
        import services.ai as ai_mod

        old = ai_mod._provider
        try:
            provider = MockProvider(is_available=False)
            set_provider(provider)
            with pytest.raises(ValueError, match="利用できません"):
                require_provider()
        finally:
            ai_mod._provider = old

    def test_require_provider_returns_when_available(self):
        """プロバイダが利用可能時に正常取得"""
        import services.ai as ai_mod

        old = ai_mod._provider
        try:
            provider = MockProvider()
            set_provider(provider)
            result = require_provider()
            assert result is provider
        finally:
            ai_mod._provider = old


# ================================================================
# OllamaProvider
# ================================================================


class TestOllamaProvider:
    """OllamaProviderのテスト"""

    def test_name(self):
        from services.ai.provider import OllamaProvider

        provider = OllamaProvider()
        assert provider.name == "ollama"

    def test_available_returns_false_when_no_server(self):
        """サーバー未起動時にavailable=False"""
        from services.ai.provider import OllamaProvider

        provider = OllamaProvider(base_url="http://localhost:19999")
        assert provider.available is False

    def test_chat_raises_on_connection_error(self):
        """接続エラー時にValueError"""
        from services.ai.provider import OllamaProvider

        provider = OllamaProvider(base_url="http://localhost:19999")
        with pytest.raises(ValueError, match="接続できません"):
            provider.chat([{"role": "user", "content": "test"}])


class _MockOllamaHandler(BaseHTTPRequestHandler):
    """テスト用のOllama APIモックサーバー"""

    def do_GET(self):
        if self.path == "/api/tags":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"models": []}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            request = json.loads(body)

            user_msg = ""
            for msg in request.get("messages", []):
                if msg.get("role") == "user":
                    user_msg = msg.get("content", "")

            response = {
                "message": {
                    "role": "assistant",
                    "content": f"応答: {user_msg[:50]}",
                },
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        elif self.path == "/api/embed":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            request = json.loads(body)
            text = request.get("input", "")
            # 簡易的な4次元埋め込みベクトルを生成
            h = hash(text)
            embedding = [
                ((h >> 0) & 0xFF) / 255.0,
                ((h >> 8) & 0xFF) / 255.0,
                ((h >> 16) & 0xFF) / 255.0,
                ((h >> 24) & 0xFF) / 255.0,
            ]
            response = {"embeddings": [embedding]}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # テスト時のログ出力を抑制


@pytest.fixture
def mock_ollama_server():
    """モックOllamaサーバーを起動するフィクスチャ"""
    server = HTTPServer(("127.0.0.1", 0), _MockOllamaHandler)
    port = server.server_address[1]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


class TestOllamaProviderWithMock:
    """モックサーバーを使用したOllamaProviderテスト"""

    def test_available_with_mock_server(self, mock_ollama_server):
        from services.ai.provider import OllamaProvider

        provider = OllamaProvider(base_url=mock_ollama_server)
        assert provider.available is True

    def test_chat_with_mock_server(self, mock_ollama_server):
        from services.ai.provider import OllamaProvider

        provider = OllamaProvider(base_url=mock_ollama_server)
        result = provider.chat([{"role": "user", "content": "テストメッセージ"}])
        assert "応答:" in result
        assert "テストメッセージ" in result

    def test_summarize_with_mock_server(self, mock_ollama_server):
        from services.ai.provider import OllamaProvider

        provider = OllamaProvider(base_url=mock_ollama_server)
        result = provider.summarize("サンプルテキストの要約")
        assert "応答:" in result


# ================================================================
# create_provider_from_config
# ================================================================


class TestCreateProviderFromConfig:
    """create_provider_from_configのテスト"""

    def test_disabled_returns_none(self):
        from services.ai.provider import create_provider_from_config

        result = create_provider_from_config({"provider": "disabled"})
        assert result is None

    def test_empty_config_returns_none(self):
        from services.ai.provider import create_provider_from_config

        result = create_provider_from_config({})
        assert result is None

    def test_ollama_returns_provider(self):
        from services.ai.provider import OllamaProvider, create_provider_from_config

        result = create_provider_from_config(
            {
                "provider": "ollama",
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "model": "llama3:8b",
                },
            }
        )
        assert isinstance(result, OllamaProvider)
        assert result._model == "llama3:8b"

    def test_unknown_provider_returns_none(self):
        from services.ai.provider import create_provider_from_config

        result = create_provider_from_config({"provider": "unknown_provider"})
        assert result is None


# ================================================================
# Summarizer
# ================================================================


class TestSummarizer:
    """summarizer モジュールのテスト"""

    def test_summarize_file_not_found(self):
        from services.ai.summarizer import summarize_file

        with pytest.raises(FileNotFoundError):
            summarize_file(Path("/nonexistent/file.txt"))

    def test_summarize_file_too_large(self, tmp_path):
        from services.ai.summarizer import MAX_FILE_SIZE_BYTES, summarize_file

        big_file = tmp_path / "big.txt"
        big_file.write_text("x" * (MAX_FILE_SIZE_BYTES + 1))
        with pytest.raises(ValueError, match="大きすぎ"):
            summarize_file(big_file)

    def test_summarize_file_with_mock(self, tmp_path):
        """MockProviderで要約を取得"""
        import services.ai as ai_mod

        old = ai_mod._provider
        try:
            set_provider(MockProvider(response="要約結果"))
            test_file = tmp_path / "test.txt"
            test_file.write_text("テスト内容")

            from services.ai.summarizer import summarize_file

            result = summarize_file(test_file)
            assert "要約" in result
        finally:
            ai_mod._provider = old

    def test_summarize_files_with_errors(self, tmp_path):
        """複数ファイル要約（エラー含む）"""
        import services.ai as ai_mod

        old = ai_mod._provider
        try:
            set_provider(MockProvider(response="ok"))
            existing = tmp_path / "exists.txt"
            existing.write_text("content")
            missing = tmp_path / "missing.txt"

            from services.ai.summarizer import summarize_files

            results = summarize_files([existing, missing])
            assert str(existing) in results
            assert str(missing) in results
            assert "[エラー]" in results[str(missing)]
        finally:
            ai_mod._provider = old


# ================================================================
# Diff Analyzer
# ================================================================


class TestDiffAnalyzer:
    """diff_analyzer モジュールのテスト"""

    def test_analyze_diff_empty(self):
        from services.ai.diff_analyzer import analyze_diff

        result = analyze_diff("")
        assert "差分がありません" in result

    def test_analyze_diff_with_mock(self):
        """MockProviderでdiffを分析"""
        import services.ai as ai_mod

        old = ai_mod._provider
        try:
            set_provider(MockProvider(response="変更分析"))

            from services.ai.diff_analyzer import analyze_diff

            result = analyze_diff("--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new")
            assert result == "変更分析"
        finally:
            ai_mod._provider = old

    def test_analyze_diff_truncates_large_diff(self):
        """大きなdiffが切り詰められる"""
        import services.ai as ai_mod
        from services.ai.diff_analyzer import MAX_DIFF_SIZE_CHARS

        old = ai_mod._provider
        chat_calls = []

        class CapturingProvider(MockProvider):
            def chat(self, messages, **kwargs):
                chat_calls.append(messages)
                return "ok"

        try:
            set_provider(CapturingProvider())

            from services.ai.diff_analyzer import analyze_diff

            large_diff = "x" * (MAX_DIFF_SIZE_CHARS + 10000)
            analyze_diff(large_diff)

            # chatに渡されたメッセージのdiffが切り詰められている
            user_msg = chat_calls[0][1]["content"]
            assert "省略" in user_msg
        finally:
            ai_mod._provider = old

    def test_get_git_diff(self, tmp_path):
        """git diffの取得（空リポジトリ）"""
        import subprocess

        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "test"], cwd=tmp_path, capture_output=True)

        from services.ai.diff_analyzer import get_git_diff

        result = get_git_diff(cwd=tmp_path)
        assert isinstance(result, str)


# ================================================================
# CLI integration
# ================================================================


class TestAICLI:
    """AI CLIコマンドのテスト"""

    def test_ai_status_no_provider(self):
        """jj ai status — プロバイダ未設定"""
        import services.ai as ai_mod

        old = ai_mod._provider
        try:
            ai_mod._provider = None
            from services.cli import build_parser, dispatch, normalize_compat

            parser = build_parser()
            args = parser.parse_args(["ai", "status"])
            args = normalize_compat(args)
            result = dispatch(args)
            assert result == 0
        finally:
            ai_mod._provider = old

    def test_ai_status_with_provider(self):
        """jj ai status — プロバイダ設定済み"""
        import services.ai as ai_mod

        old = ai_mod._provider
        try:
            set_provider(MockProvider())
            from services.cli import build_parser, dispatch, normalize_compat

            parser = build_parser()
            args = parser.parse_args(["ai", "status"])
            args = normalize_compat(args)
            result = dispatch(args)
            assert result == 0
        finally:
            ai_mod._provider = old

    def test_ai_no_subcommand(self):
        """jj ai — サブコマンドなし"""
        from services.cli import build_parser, dispatch, normalize_compat

        parser = build_parser()
        args = parser.parse_args(["ai"])
        args = normalize_compat(args)
        result = dispatch(args)
        assert result == 1  # ヘルプ表示してexit 1


# ================================================================
# RAG — chunk_text
# ================================================================


class TestChunkText:
    """chunk_text関数のテスト"""

    def test_empty_text(self):
        from services.ai.rag import chunk_text

        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_short_text_single_chunk(self):
        from services.ai.rag import chunk_text

        result = chunk_text("短いテキスト", chunk_size=100)
        assert len(result) == 1
        assert result[0] == "短いテキスト"

    def test_long_text_multiple_chunks(self):
        from services.ai.rag import chunk_text

        text = "\n".join(f"行{i}" for i in range(100))
        result = chunk_text(text, chunk_size=50, overlap=10)
        assert len(result) > 1
        # 全テキストがカバーされている
        combined = " ".join(result)
        for i in range(100):
            assert f"行{i}" in combined

    def test_respects_line_boundaries(self):
        from services.ai.rag import chunk_text

        # 各行5文字（改行込み）、chunk_size=12で行境界を尊重
        text = "line1\nline2\nline3\nline4\nline5\nline6"
        result = chunk_text(text, chunk_size=12, overlap=0)
        assert len(result) >= 2
        # 各チャンクが空でない
        for chunk in result:
            assert len(chunk) > 0


# ================================================================
# RAG — cosine_similarity
# ================================================================


class TestCosineSimilarity:
    """_cosine_similarity関数のテスト"""

    def test_identical_vectors(self):
        from services.ai.rag import _cosine_similarity

        assert _cosine_similarity([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        from services.ai.rag import _cosine_similarity

        assert _cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)

    def test_zero_vector(self):
        from services.ai.rag import _cosine_similarity

        assert _cosine_similarity([0, 0], [1, 1]) == 0.0


# ================================================================
# RAG — RagIndex
# ================================================================


class TestRagIndex:
    """RagIndexのテスト"""

    def test_add_file(self, tmp_path):
        """ファイルをインデックスに追加"""
        import services.ai as ai_mod

        old = ai_mod._provider
        try:
            set_provider(MockProvider())

            from services.ai.rag import RagIndex

            index = RagIndex()
            test_file = tmp_path / "test.txt"
            test_file.write_text("テスト内容\n二行目\n三行目")

            count = index.add_file(test_file)
            assert count > 0
            assert index.size == count
            assert str(test_file) in index.indexed_files
        finally:
            ai_mod._provider = old

    def test_add_file_not_found(self):
        from services.ai.rag import RagIndex

        index = RagIndex()
        with pytest.raises(FileNotFoundError):
            index.add_file(Path("/nonexistent/file.txt"))

    def test_add_file_too_large(self, tmp_path):
        from services.ai.rag import MAX_FILE_SIZE_BYTES, RagIndex

        big_file = tmp_path / "big.txt"
        big_file.write_text("x" * (MAX_FILE_SIZE_BYTES + 1))
        index = RagIndex()
        with pytest.raises(ValueError, match="大きすぎ"):
            index.add_file(big_file)

    def test_remove_file(self, tmp_path):
        """ファイルをインデックスから削除"""
        import services.ai as ai_mod

        old = ai_mod._provider
        try:
            set_provider(MockProvider())

            from services.ai.rag import RagIndex

            index = RagIndex()
            test_file = tmp_path / "test.txt"
            test_file.write_text("テスト内容")
            index.add_file(test_file)
            assert index.size > 0

            removed = index.remove_file(test_file)
            assert removed > 0
            assert index.size == 0
        finally:
            ai_mod._provider = old

    def test_reindex_replaces_existing(self, tmp_path):
        """同じファイルを再インデックスすると既存エントリが置き換わる"""
        import services.ai as ai_mod

        old = ai_mod._provider
        try:
            set_provider(MockProvider())

            from services.ai.rag import RagIndex

            index = RagIndex()
            test_file = tmp_path / "test.txt"
            test_file.write_text("初期内容")
            index.add_file(test_file)

            test_file.write_text("更新内容\n追加行")
            count2 = index.add_file(test_file)

            # ファイルのエントリ数が初回と異なる可能性がある
            assert index.size == count2
        finally:
            ai_mod._provider = old

    def test_search(self, tmp_path):
        """検索が結果を返す"""
        import services.ai as ai_mod

        old = ai_mod._provider
        try:
            set_provider(MockProvider())

            from services.ai.rag import RagIndex

            index = RagIndex()
            test_file = tmp_path / "test.txt"
            test_file.write_text("Python は動的型付け言語です\nJava は静的型付け言語です")
            index.add_file(test_file)

            results = index.search("Python", top_k=3)
            assert len(results) > 0
            assert "text" in results[0]
            assert "score" in results[0]
            assert "file" in results[0]
        finally:
            ai_mod._provider = old

    def test_search_empty_index(self):
        """空インデックスの検索"""
        import services.ai as ai_mod

        old = ai_mod._provider
        try:
            set_provider(MockProvider())

            from services.ai.rag import RagIndex

            index = RagIndex()
            results = index.search("test")
            assert results == []
        finally:
            ai_mod._provider = old

    def test_save_and_load(self, tmp_path):
        """インデックスの永続化と復元"""
        import services.ai as ai_mod

        old = ai_mod._provider
        try:
            set_provider(MockProvider())

            from services.ai.rag import RagIndex

            index_path = tmp_path / "rag_index.json"
            index = RagIndex(storage_path=index_path)

            test_file = tmp_path / "test.txt"
            test_file.write_text("永続化テスト")
            index.add_file(test_file)
            original_size = index.size
            index.save()

            # 新しいインデックスで復元
            index2 = RagIndex(storage_path=index_path)
            index2.load()
            assert index2.size == original_size
        finally:
            ai_mod._provider = old


# ================================================================
# RAG — rag_query
# ================================================================


class TestRagQuery:
    """rag_query関数のテスト"""

    def test_empty_index(self):
        """空インデックスでのクエリ"""
        import services.ai as ai_mod

        old = ai_mod._provider
        try:
            set_provider(MockProvider())

            from services.ai.rag import RagIndex, rag_query

            index = RagIndex()
            result = rag_query("test", index)
            assert "インデックスにデータがありません" in result
        finally:
            ai_mod._provider = old

    def test_query_with_context(self, tmp_path):
        """コンテキスト付きクエリ"""
        import services.ai as ai_mod

        old = ai_mod._provider
        try:
            set_provider(MockProvider(response="AI回答"))

            from services.ai.rag import RagIndex, rag_query

            index = RagIndex()
            test_file = tmp_path / "test.txt"
            test_file.write_text("プロジェクトの概要説明")
            index.add_file(test_file)

            result = rag_query("プロジェクトについて教えて", index)
            assert result == "AI回答"
        finally:
            ai_mod._provider = old


# ================================================================
# OllamaProvider embed (mock server)
# ================================================================


class TestOllamaProviderEmbed:
    """OllamaProviderのembedメソッドテスト"""

    def test_embed_with_mock_server(self, mock_ollama_server):
        from services.ai.provider import OllamaProvider

        provider = OllamaProvider(base_url=mock_ollama_server)
        result = provider.embed("テストテキスト")
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(v, float) for v in result)

    def test_embed_connection_error(self):
        from services.ai.provider import OllamaProvider

        provider = OllamaProvider(base_url="http://localhost:19999")
        with pytest.raises(ValueError, match="接続できません"):
            provider.embed("test")


# ================================================================
# Tips — TipsStore
# ================================================================


class TestTipsStore:
    """TipsStoreのテスト"""

    def test_add_and_get(self):
        from services.ai.tips import TipsStore

        store = TipsStore()
        tip = store.add_tip("テストTip", "テスト本文", tags=["python"])
        assert tip["title"] == "テストTip"
        assert store.size == 1

    def test_get_random(self):
        from services.ai.tips import TipsStore

        store = TipsStore()
        store.add_tip("Tip1", "Body1")
        store.add_tip("Tip2", "Body2")
        store.add_tip("Tip3", "Body3")

        results = store.get_random(2)
        assert len(results) == 2

    def test_get_random_empty(self):
        from services.ai.tips import TipsStore

        store = TipsStore()
        assert store.get_random() == []

    def test_search_by_title(self):
        from services.ai.tips import TipsStore

        store = TipsStore()
        store.add_tip("Python型ヒント", "型ヒントを活用しよう")
        store.add_tip("テスト自動化", "pytestを使おう")

        results = store.search("Python")
        assert len(results) == 1
        assert results[0]["title"] == "Python型ヒント"

    def test_search_by_tag(self):
        from services.ai.tips import TipsStore

        store = TipsStore()
        store.add_tip("Tip1", "Body1", tags=["python", "testing"])
        store.add_tip("Tip2", "Body2", tags=["rust"])

        results = store.search("python")
        assert len(results) == 1

    def test_save_and_load(self, tmp_path):
        from services.ai.tips import TipsStore

        path = tmp_path / "tips.json"
        store = TipsStore(storage_path=path)
        store.add_tip("永続化テスト", "保存と復元")
        store.save()

        store2 = TipsStore(storage_path=path)
        store2.load()
        assert store2.size == 1
        assert store2.list_all()[0]["title"] == "永続化テスト"


# ================================================================
# Tips — extract / parse
# ================================================================


class TestTipsExtract:
    """Tips抽出のテスト"""

    def test_parse_tips_response_valid(self):
        from services.ai.tips import _parse_tips_response

        response = json.dumps(
            [
                {"title": "Tip1", "body": "Body1", "tags": ["tag1"]},
                {"title": "Tip2", "body": "Body2"},
            ]
        )
        result = _parse_tips_response(response)
        assert len(result) == 2
        assert result[0]["title"] == "Tip1"
        assert result[1]["tags"] == []

    def test_parse_tips_response_with_fence(self):
        from services.ai.tips import _parse_tips_response

        response = '```json\n[{"title": "Tip", "body": "Body"}]\n```'
        result = _parse_tips_response(response)
        assert len(result) == 1

    def test_parse_tips_response_invalid(self):
        from services.ai.tips import _parse_tips_response

        assert _parse_tips_response("not json") == []
        assert _parse_tips_response("{}") == []

    def test_extract_tips_from_file(self, tmp_path):
        """MockProviderでTipsを抽出"""
        import services.ai as ai_mod

        old = ai_mod._provider

        class TipsMockProvider(MockProvider):
            def chat(self, messages, **kwargs):
                return json.dumps([{"title": "抽出Tip", "body": "テスト本文", "tags": ["test"]}])

        try:
            set_provider(TipsMockProvider())
            test_file = tmp_path / "test.py"
            test_file.write_text("def hello(): pass")

            from services.ai.tips import extract_tips_from_file

            tips = extract_tips_from_file(test_file)
            assert len(tips) == 1
            assert tips[0]["title"] == "抽出Tip"
        finally:
            ai_mod._provider = old

    def test_extract_tips_from_text_empty(self):
        from services.ai.tips import extract_tips_from_text

        assert extract_tips_from_text("") == []
        assert extract_tips_from_text("   ") == []
