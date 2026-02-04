from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable

DEFAULT_EXTENSIONS: tuple[str, ...] = (
    ".cas.h5",
    ".dat.h5",
    ".aedt.batchinfo",
    ".py",
    ".xlsx",
    ".csv",
    ".pptx",
    ".yaml",
    ".md",
    ".json",
    ".sh",
    ".msh",
    ".modfem",
    ".stp",
    ".step",
    ".catPart",
    ".dxf",
    ".dwg",
    ".png",
    ".gif",
)


def _match_extension(
    filename: str, extension_candidates: Iterable[str] | None = None
) -> str:
    candidates = tuple(extension_candidates or DEFAULT_EXTENSIONS)
    lower_name = filename.lower()
    for ext in sorted(candidates, key=len, reverse=True):
        if lower_name.endswith(ext.lower()):
            return ext
    if "." not in filename:
        return ""
    return f".{filename.split('.')[-1]}"


@dataclass(frozen=True)
class FileParse:
    true_file_path: str | Path
    extension_candidates: Iterable[str] | None = None

    def _as_path(self) -> Path:
        return Path(self.true_file_path)

    def _split_extension(self) -> tuple[str, str]:
        filename = self._as_path().name
        ext = _match_extension(filename, self.extension_candidates)
        if ext and filename.lower().endswith(ext.lower()):
            return filename[: -len(ext)], ext
        return filename, ""

    def get_basename(self) -> str:
        basename, _ = self._split_extension()
        return basename

    def get_directory(self) -> str:
        return str(self._as_path().parent)

    def _basename_without_prefix(self) -> str:
        basename = self.get_basename()
        if "_" in basename:
            return basename.split("_", 1)[1]
        return basename

    def get_index(self) -> str:
        target = self._basename_without_prefix()
        if target.startswith("idx"):
            return target.split(".")[0].split("_")[0].replace("idx", "")
        return ""

    def get_version(self) -> str:
        target = self._basename_without_prefix()
        last_segment = target.split(".")[-1]
        if last_segment.startswith("v"):
            return last_segment.replace("v", "")
        return ""

    def get_props(self) -> dict[str, str]:
        basename = self._basename_without_prefix()
        idx = self.get_index()
        ver = self.get_version()
        if idx:
            basename = basename.replace(f"idx{idx}_", "").replace(f"idx{idx}", "")
        if ver:
            basename = basename.replace(f".v{ver}", "")

        props: dict[str, str] = {}
        for token in filter(None, re.split(r"[_.]", basename)):
            if "=" in token:
                key, value = token.split("=", 1)
                if key:
                    props[key] = value
                continue
            match = re.fullmatch(r"([A-Za-z]+)(\d+)", token)
            if match:
                props[match.group(1)] = match.group(2)
                continue
            props[token] = token
        return props


@dataclass(frozen=True)
class ObsidianMap:
    true_file_path: str | Path
    notes_dir: str | Path = "notes/props"
    base_path: str | Path = "notes/bases"
    extension_candidates: Iterable[str] | None = None

    def _file_parse(self) -> FileParse:
        return FileParse(self.true_file_path, extension_candidates=self.extension_candidates)

    def get_base_path(self) -> Path:
        return Path(self.base_path)

    def to_frontmatter_path(
        self,
        true_file_path: str | Path | None = None,
        notes_dir: str | Path | None = None,
    ) -> Path:
        target_path = true_file_path or self.true_file_path
        parser = FileParse(target_path, extension_candidates=self.extension_candidates)
        path = Path(target_path)
        if path.is_dir():
            basename = path.name
        else:
            basename, ext = parser._split_extension()
            if ext:
                basename = f"{basename}_{ext.lstrip('.')}"
        base_dir = Path(notes_dir or self.notes_dir)
        return base_dir / f"{basename}.md"

    def get_frontmatter_path(self) -> Path:
        return self.to_frontmatter_path()


@dataclass(frozen=True)
class ObsidianFileParse(FileParse):
    notes_dir: str | Path = "notes/props"
    base_path: str | Path = "notes/bases"

    def _obsidian_map(self) -> ObsidianMap:
        return ObsidianMap(
            self.true_file_path,
            notes_dir=self.notes_dir,
            base_path=self.base_path,
            extension_candidates=self.extension_candidates,
        )

    def get_frontmatter_path(self) -> Path:
        return self._obsidian_map().get_frontmatter_path()

    def get_base_path(self) -> Path:
        return self._obsidian_map().get_base_path()

    def to_frontmatter_path(self) -> Path:
        return self._obsidian_map().to_frontmatter_path()
