"""Obsidian日報コネクタ: notes/dailyの日報を解析してグラフに追加

日報（dailyノート）を解析して、ファイル参照・プロパティ・タグ情報を
グラフに追加する。

検出パターン:
1. セクション内のファイル参照:
   ## 応力振幅1
   - go_idx1.inp
   - 画像.png

2. コロン区切りのプロパティ付きファイル参照:
   go_idx1.inp:  備考: 最終版
   go_idx1.inp: status: completed

3. Obsidianリンク形式:
   [[go_idx1.inp]]

4. タグ:
   #応力 #振幅

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class DailyFileReference:
    """日報内のファイル参照"""

    filename: str  # 参照されるファイル名
    section: str  # 所属セクション名
    properties: dict[str, str] = field(default_factory=dict)  # コロン区切りのプロパティ
    tags: list[str] = field(default_factory=list)  # タグ


@dataclass
class DailyNote:
    """解析済みの日報"""

    path: Path  # ファイルパス
    date: str  # 日付（ファイル名から）
    frontmatter: dict[str, Any] = field(default_factory=dict)  # YAMLフロントマター
    file_references: list[DailyFileReference] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)  # 文書全体のタグ


# ファイル参照のパターン
# go_idx1.inp, mesh_v2.cdb, 画像.png 等
_FILE_REF_PATTERN = re.compile(
    r"(?:^[-*]\s+|^)(\S+\.\w{1,6})(?:\s|$|:)",
    re.MULTILINE,
)

# コロン区切りのプロパティ付きファイル参照
# go_idx1.inp: 備考: 最終版
# go_idx1.inp:  key: value
_FILE_PROP_PATTERN = re.compile(
    r"^(\S+\.\w{1,6})\s*:\s*(.+)$",
    re.MULTILINE,
)

# Obsidianリンク形式 [[filename]] or [[path/to/filename|display]]
_OBSIDIAN_LINK_PATTERN = re.compile(
    r"\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]"
)

# タグパターン #tag
_TAG_PATTERN = re.compile(r"#([^\s#\[\]]+)")

# Markdownセクション見出し
_SECTION_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

# 既知のファイル拡張子
_KNOWN_EXTENSIONS = {
    ".inp", ".cdb", ".msh", ".modfem", ".dat", ".sta", ".msg",
    ".odb", ".csv", ".json", ".yaml", ".xlsx", ".pptx", ".pdf",
    ".png", ".gif", ".svg", ".html", ".txt", ".py", ".sh",
    ".cas.h5", ".dat.h5", ".stp", ".step", ".catpart", ".dxf", ".dwg",
    ".k", ".key",
}


def parse_daily_note(path: Path) -> DailyNote:
    """日報ファイルを解析

    Args:
        path: 日報ファイルのパス

    Returns:
        解析済みのDailyNote
    """
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, IOError):
        return DailyNote(path=path, date=_extract_date(path))

    date = _extract_date(path)
    frontmatter = _parse_frontmatter(content)
    body = _strip_frontmatter(content)

    # セクション構造を解析
    sections = _parse_sections(body)

    file_references: list[DailyFileReference] = []
    all_tags: list[str] = []

    # フロントマターからタグを取得
    fm_tags = frontmatter.get("tags", [])
    if isinstance(fm_tags, list):
        all_tags.extend(fm_tags)

    for section_name, section_content in sections:
        # セクション名からもタグを収集（## テスト #振幅 の形式）
        tags_in_name = _TAG_PATTERN.findall(section_name)
        all_tags.extend(tags_in_name)

        # セクション本文内のタグを収集
        tags_in_body = _TAG_PATTERN.findall(section_content)
        all_tags.extend(tags_in_body)

        # セクション全体のタグ（名前+本文）
        tags_in_section = tags_in_name + tags_in_body

        # ファイル参照（プロパティ付き）の検出
        for match in _FILE_PROP_PATTERN.finditer(section_content):
            filename = match.group(1)
            rest = match.group(2).strip()

            if not _looks_like_file(filename):
                continue

            # プロパティのパース: "key: value" or "備考: 最終版"
            props = _parse_inline_properties(rest)

            file_references.append(DailyFileReference(
                filename=filename,
                section=section_name,
                properties=props,
                tags=tags_in_section,
            ))

        # リスト項目としてのファイル参照（- go_idx1.inp）
        for line in section_content.split("\n"):
            line_stripped = line.strip()
            if line_stripped.startswith("- ") or line_stripped.startswith("* "):
                item = line_stripped[2:].strip()
                # プロパティ付きの場合はスキップ（_FILE_PROP_PATTERNで処理済み）
                if ":" in item and _looks_like_file(item.split(":")[0].strip()):
                    continue
                # 純粋なファイル名参照
                if _looks_like_file(item):
                    file_references.append(DailyFileReference(
                        filename=item,
                        section=section_name,
                        tags=tags_in_section,
                    ))

        # Obsidianリンク形式のファイル参照
        for match in _OBSIDIAN_LINK_PATTERN.finditer(section_content):
            link_target = match.group(1)
            filename = Path(link_target).name
            if _looks_like_file(filename):
                # 重複チェック
                if not any(r.filename == filename for r in file_references):
                    file_references.append(DailyFileReference(
                        filename=filename,
                        section=section_name,
                        tags=tags_in_section,
                    ))

    # タグの重複除去
    unique_tags = list(dict.fromkeys(all_tags))

    return DailyNote(
        path=path,
        date=date,
        frontmatter=frontmatter,
        file_references=file_references,
        tags=unique_tags,
    )


def scan_daily_notes(notes_dir: Path) -> list[DailyNote]:
    """notes/dailyディレクトリ内の日報をスキャン・解析

    Args:
        notes_dir: notes/dailyディレクトリのパス

    Returns:
        解析済みDailyNoteのリスト
    """
    if not notes_dir.exists():
        return []

    notes: list[DailyNote] = []
    for md_path in sorted(notes_dir.glob("*.md")):
        note = parse_daily_note(md_path)
        if note.file_references or note.tags:
            notes.append(note)

    return notes


def _extract_date(path: Path) -> str:
    """ファイル名から日付を抽出

    Obsidian daily noteは通常 YYYY-MM-DD.md の形式
    """
    stem = path.stem
    # YYYY-MM-DD形式の検出
    date_match = re.match(r"(\d{4}-\d{2}-\d{2})", stem)
    if date_match:
        return date_match.group(1)
    return stem


def _parse_frontmatter(content: str) -> dict[str, Any]:
    """YAMLフロントマターを解析"""
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        fm = yaml.safe_load(parts[1])
        return fm if isinstance(fm, dict) else {}
    except yaml.YAMLError:
        return {}


def _strip_frontmatter(content: str) -> str:
    """フロントマターを除去"""
    if not content.startswith("---"):
        return content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return content
    return parts[2]


def _parse_sections(body: str) -> list[tuple[str, str]]:
    """マークダウンのセクション構造を解析

    Returns:
        [(セクション名, セクション内容), ...] のリスト
        セクション見出しがない場合は("", 全体) を返す
    """
    matches = list(_SECTION_PATTERN.finditer(body))

    if not matches:
        return [("", body)]

    sections: list[tuple[str, str]] = []

    # 最初のセクション前のテキスト
    if matches[0].start() > 0:
        sections.append(("", body[: matches[0].start()]))

    # 各セクション
    for i, match in enumerate(matches):
        name = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections.append((name, body[start:end]))

    return sections


def _looks_like_file(text: str) -> bool:
    """テキストがファイル名のように見えるかチェック"""
    text = text.strip()
    if not text:
        return False
    # 空白を含む場合はファイル名ではない（日本語は除く）
    if " " in text and not any(ord(c) > 127 for c in text.split(".")[0]):
        return False
    # ドットが含まれていない場合はファイル名ではない
    if "." not in text:
        return False
    # 拡張子チェック
    lower = text.lower()
    for ext in _KNOWN_EXTENSIONS:
        if lower.endswith(ext):
            return True
    # 汎用的な拡張子チェック（1-6文字）
    parts = text.rsplit(".", 1)
    if len(parts) == 2 and 1 <= len(parts[1]) <= 6 and parts[1].isalnum():
        return True
    return False


def _parse_inline_properties(text: str) -> dict[str, str]:
    """インラインプロパティをパース

    "備考: 最終版" → {"備考": "最終版"}
    "status: completed, 備考: テスト" → {"status": "completed", "備考": "テスト"}
    """
    props: dict[str, str] = {}
    # カンマ区切りまたは改行区切りのプロパティ
    for part in re.split(r",\s*", text):
        part = part.strip()
        if ":" in part:
            key, value = part.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key:
                props[key] = value
        elif part:
            # キーのみの場合はフラグとして扱う
            props[part] = "true"
    return props
