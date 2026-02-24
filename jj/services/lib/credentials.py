"""クレデンシャル管理サービス: Neo4j等の認証情報を暗号化して保存

config.yamlに平文パスワードを書く代わりに、暗号化されたクレデンシャル
ファイルを使用する。暗号鍵はユーザーホームディレクトリに保存される。

保存場所:
- 暗号鍵: ~/.j2/secret.key（ユーザーホーム、プロジェクト外）
- クレデンシャル: .j2/config/.credentials（プロジェクト内、.gitignore推奨）

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import json
import secrets
from pathlib import Path

# クレデンシャルファイル名（隠しファイル）
CREDENTIALS_FILENAME = ".credentials"
# 暗号鍵ファイル名
SECRET_KEY_FILENAME = "secret.key"
# 暗号鍵ディレクトリ（ユーザーホーム配下）
SECRET_KEY_DIR = ".j2"


def _get_secret_key_path() -> Path:
    """暗号鍵のパスを取得（~/.j2/secret.key）"""
    return Path.home() / SECRET_KEY_DIR / SECRET_KEY_FILENAME


def _get_credentials_path(project_root: Path) -> Path:
    """クレデンシャルファイルのパスを取得"""
    return project_root / ".j2" / "config" / CREDENTIALS_FILENAME


def _ensure_secret_key() -> bytes:
    """暗号鍵を取得。存在しなければ新規生成する。

    Returns:
        32バイトの暗号鍵
    """
    key_path = _get_secret_key_path()

    if key_path.exists():
        raw = key_path.read_bytes()
        return base64.urlsafe_b64decode(raw)

    # 新規生成
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key = secrets.token_bytes(32)
    key_path.write_bytes(base64.urlsafe_b64encode(key))

    # パーミッション制限（Unix系のみ）
    with contextlib.suppress(OSError, AttributeError):
        key_path.chmod(0o600)

    return key


def _encrypt(plaintext: str, key: bytes) -> str:
    """平文を暗号化してbase64文字列で返す

    暗号方式: ランダムIV(16bytes) + XOR(PBKDF2派生鍵)

    Args:
        plaintext: 暗号化する文字列
        key: 暗号鍵（32バイト）

    Returns:
        base64エンコードされた暗号文
    """
    iv = secrets.token_bytes(16)
    # IVと鍵からストリームキーを導出
    derived = hashlib.pbkdf2_hmac("sha256", key, iv, 100_000, dklen=len(plaintext.encode()))
    plainbytes = plaintext.encode("utf-8")
    cipher = bytes(a ^ b for a, b in zip(plainbytes, derived, strict=False))
    return base64.urlsafe_b64encode(iv + cipher).decode("ascii")


def _decrypt(ciphertext: str, key: bytes) -> str:
    """暗号文を復号して平文を返す

    Args:
        ciphertext: base64エンコードされた暗号文
        key: 暗号鍵（32バイト）

    Returns:
        復号された平文
    """
    raw = base64.urlsafe_b64decode(ciphertext.encode("ascii"))
    iv = raw[:16]
    cipher = raw[16:]
    derived = hashlib.pbkdf2_hmac("sha256", key, iv, 100_000, dklen=len(cipher))
    plainbytes = bytes(a ^ b for a, b in zip(cipher, derived, strict=False))
    return plainbytes.decode("utf-8")


def save_credentials(
    project_root: Path,
    service: str,
    credentials: dict[str, str],
) -> Path:
    """クレデンシャルを暗号化して保存

    Args:
        project_root: プロジェクトルート
        service: サービス名（例: "neo4j"）
        credentials: key-value形式のクレデンシャル

    Returns:
        保存先パス
    """
    key = _ensure_secret_key()
    cred_path = _get_credentials_path(project_root)
    cred_path.parent.mkdir(parents=True, exist_ok=True)

    # 既存のクレデンシャルを読み込み
    all_creds: dict[str, dict[str, str]] = {}
    if cred_path.exists():
        try:
            existing = json.loads(cred_path.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                all_creds = existing
        except (json.JSONDecodeError, OSError):
            pass

    # 暗号化して保存
    encrypted: dict[str, str] = {}
    for k, v in credentials.items():
        encrypted[k] = _encrypt(v, key)
    all_creds[service] = encrypted

    cred_path.write_text(
        json.dumps(all_creds, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # パーミッション制限
    with contextlib.suppress(OSError, AttributeError):
        cred_path.chmod(0o600)

    return cred_path


def load_credentials(
    project_root: Path,
    service: str,
) -> dict[str, str] | None:
    """暗号化されたクレデンシャルを復号して取得

    Args:
        project_root: プロジェクトルート
        service: サービス名（例: "neo4j"）

    Returns:
        復号されたクレデンシャル辞書。未設定やエラー時はNone。
    """
    cred_path = _get_credentials_path(project_root)
    if not cred_path.exists():
        return None

    key_path = _get_secret_key_path()
    if not key_path.exists():
        return None

    try:
        key = base64.urlsafe_b64decode(key_path.read_bytes())
        all_creds = json.loads(cred_path.read_text(encoding="utf-8"))
        if not isinstance(all_creds, dict):
            return None
        encrypted = all_creds.get(service)
        if not isinstance(encrypted, dict):
            return None

        decrypted: dict[str, str] = {}
        for k, v in encrypted.items():
            decrypted[k] = _decrypt(v, key)
        return decrypted
    except Exception:
        return None


def mask_value(value: str) -> str:
    """値をマスキングして表示用に変換

    先頭2文字のみ表示し、残りを*で隠す。
    短い値は全て*にする。
    """
    if len(value) <= 2:
        return "*" * len(value)
    return value[:2] + "*" * (len(value) - 2)
