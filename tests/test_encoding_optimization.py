"""UTF-8ファーストエンコーディング検出の最適化テスト"""

from __future__ import annotations

from pathlib import Path

import pytest

pd = pytest.importorskip("pandas", reason="pandas required for pymesh import chain")
scipy = pytest.importorskip("scipy", reason="scipy required for pymesh import chain")
plotly = pytest.importorskip("plotly", reason="plotly required for pymesh import chain")


class TestDetectFileEncoding:
    """io.py の detect_file_encoding のUTF-8ファースト最適化テスト"""

    def test_utf8_file_returns_utf8_fast(self, tmp_path: Path) -> None:
        """UTF-8ファイルはchardetを呼ばずにUTF-8を返す"""
        from modules.pymesh.io import detect_file_encoding

        f = tmp_path / "test.inp"
        f.write_text("*NODE\n1, 0.0, 0.0, 0.0\n", encoding="utf-8")
        result = detect_file_encoding(str(f))
        assert result == "utf-8"

    def test_ascii_file_returns_utf8(self, tmp_path: Path) -> None:
        """ASCII（UTF-8のサブセット）もUTF-8として返す"""
        from modules.pymesh.io import detect_file_encoding

        f = tmp_path / "test.inp"
        f.write_bytes(b"*NODE\n1, 0.0, 0.0, 0.0\n")
        result = detect_file_encoding(str(f))
        assert result == "utf-8"

    def test_non_utf8_file_does_not_return_utf8(self, tmp_path: Path) -> None:
        """UTF-8無効なバイト列を含むファイルはUTF-8ファストパスを使わない"""
        from modules.pymesh.io import detect_file_encoding

        f = tmp_path / "test.inp"
        # 先頭にUTF-8無効バイト列を配置（8KB以内でUTF-8デコード失敗を確実にする）
        invalid_bytes = b"\x80\x81\x82\x83" * 100
        f.write_bytes(invalid_bytes + b"\n*NODE\n1, 0.0, 0.0, 0.0\n")
        result = detect_file_encoding(str(f))
        # UTF-8ファストパスを通過しなかった（chardetフォールバック経由）
        # chardetは任意のエンコーディングまたはNoneを返し得る
        assert result != "utf-8" or result is None

    def test_empty_file_returns_utf8(self, tmp_path: Path) -> None:
        """空ファイルはUTF-8を返す"""
        from modules.pymesh.io import detect_file_encoding

        f = tmp_path / "test.inp"
        f.write_bytes(b"")
        result = detect_file_encoding(str(f))
        assert result == "utf-8"

    def test_large_utf8_file_fast_path(self, tmp_path: Path) -> None:
        """大きなUTF-8ファイルでも先頭8KBで判定"""
        from modules.pymesh.io import detect_file_encoding

        f = tmp_path / "large.inp"
        # 先頭8KB以上のUTF-8データ
        lines = ["*NODE\n"] + [f"{i}, {i * 0.1}, {i * 0.2}, {i * 0.3}\n" for i in range(1, 1001)]
        f.write_text("".join(lines), encoding="utf-8")
        result = detect_file_encoding(str(f))
        assert result == "utf-8"


class TestDetectEncodingReadInp:
    """read_inp.py の _detect_encoding のUTF-8ファースト最適化テスト"""

    def test_utf8_bytes_fast_path(self) -> None:
        """UTF-8バイト列はchardetをスキップ"""
        from modules.pymesh.read_inp import _detect_encoding

        raw = b"*NODE\n1, 0.0, 0.0, 0.0\n"
        assert _detect_encoding(raw) == "utf-8"

    def test_ascii_bytes_returns_utf8(self) -> None:
        """ASCII（UTF-8サブセット）はUTF-8として返す"""
        from modules.pymesh.read_inp import _detect_encoding

        raw = b"*NODE\n1, 0.0, 0.0, 0.0\n"
        assert _detect_encoding(raw) == "utf-8"

    def test_non_utf8_bytes_uses_chardet(self) -> None:
        """UTF-8でデコードできないバイト列はchardetにフォールバック"""
        from modules.pymesh.read_inp import _detect_encoding

        # 0x80-0xFF の不正なUTF-8バイト列
        raw = b"\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89"
        result = _detect_encoding(raw)
        # chardetが何らかの結果を返す
        assert result is not None

    def test_empty_bytes_returns_utf8(self) -> None:
        """空バイト列はUTF-8を返す"""
        from modules.pymesh.read_inp import _detect_encoding

        assert _detect_encoding(b"") == "utf-8"

    def test_utf8_with_japanese(self) -> None:
        """日本語を含むUTF-8バイト列は高速パスで判定"""
        from modules.pymesh.read_inp import _detect_encoding

        raw = "** 日本語コメント\n*NODE\n1, 0.0, 0.0, 0.0\n".encode()
        assert _detect_encoding(raw) == "utf-8"


class TestDetectAndFixEncoding:
    """read_inp.py の detect_and_fix_encoding テスト"""

    def test_utf8_text(self) -> None:
        """UTF-8テキストの正常処理"""
        from modules.pymesh.read_inp import detect_and_fix_encoding

        raw = "Hello World\n日本語テスト".encode()
        result = detect_and_fix_encoding(raw)
        assert "Hello World" in result
        assert "日本語テスト" in result

    def test_empty_bytes(self) -> None:
        """空バイト列の処理"""
        from modules.pymesh.read_inp import detect_and_fix_encoding

        result = detect_and_fix_encoding(b"")
        assert result == ""
