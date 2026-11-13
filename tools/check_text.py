#!/usr/bin/env python3
"""Text, notes-index, directive, and pass-rule lint for the repository.

Checks:
1. Every tracked text file is valid UTF-8.
2. No non-exempt text file contains an em dash (U+2014). Exempt: docs/source/
   and files ending in -verbatim.md.
3. Every Markdown link in notes/index.md and notes/index/*.md resolves to an
   existing file, and every note under notes/<area>/*.md (except briefs and
   verbatim logs) is listed in notes/index/<area>.md or notes/index.md.
4. Every directive (root NN-*.md except 99-status.md) has '## Decided against'
   and '## Open' sections.
5. Every experiments/<id>/ (except _template) has PASS_RULE.md, and any
   RESULT.md names the git blob SHA of the current PASS_RULE.md and a
   'k of n rules pass' score. A mismatch means the rule changed after a result.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EM_DASH = chr(0x2014)
TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".toml",
    ".yml",
    ".yaml",
    ".json",
    ".html",
    ".css",
    ".js",
    ".ts",
    ".tsx",
    ".sh",
    ".txt",
    ".cfg",
    ".rs",
    ".scad",
}
TEXT_NAMES = {".gitignore", ".gitattributes"}
MD_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]*)?\)")
DIRECTIVE_RE = re.compile(r"^\d{2}-.+\.md$")
BLOB_RE = re.compile(r"PASS_RULE\.md blob:\s*`?([0-9a-f]{40})`?")
SCORE_RE = re.compile(r"\b\d+ of \d+ rules? pass")


def exempt(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    return rel.startswith("docs/source/") or rel.endswith("-verbatim.md")


def tracked_files() -> list[Path]:
    try:
        proc = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return [ROOT / line for line in proc.stdout.splitlines() if line]
    except (subprocess.SubprocessError, FileNotFoundError):
        skip_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__", "data", "runs"}
        return [
            p
            for p in ROOT.rglob("*")
            if p.is_file() and not any(part in skip_dirs for part in p.relative_to(ROOT).parts)
        ]


def check_notes_index(bad: list[str]) -> None:
    notes_dir = ROOT / "notes"
    if not notes_dir.is_dir():
        return

    index_files: list[Path] = []
    root_index = notes_dir / "index.md"
    if root_index.is_file():
        index_files.append(root_index)
    index_subdir = notes_dir / "index"
    if index_subdir.is_dir():
        index_files.extend(sorted(index_subdir.glob("*.md")))

    referenced_notes: set[Path] = set()
    index_text: dict[str, str] = {}

    for idx_file in index_files:
        try:
            content = idx_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        index_text[idx_file.relative_to(notes_dir).as_posix()] = content
        for match in MD_LINK_RE.finditer(content):
            target_str = match.group(1).strip()
            if target_str.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (idx_file.parent / target_str).resolve()
            if not resolved.exists():
                resolved_from_root = (ROOT / target_str).resolve()
                if resolved_from_root.exists():
                    resolved = resolved_from_root
                else:
                    bad.append(
                        f"{idx_file.relative_to(ROOT).as_posix()}: broken link target '{target_str}'"
                    )
                    continue
            referenced_notes.add(resolved)

    for note in sorted(notes_dir.rglob("*.md")):
        rel = note.relative_to(ROOT).as_posix()
        if (
            note == root_index
            or rel.startswith("notes/index/")
            or rel.startswith("notes/briefs/")
            or rel.endswith("-verbatim.md")
        ):
            continue
        area = note.relative_to(notes_dir).parts[0]
        own_index = index_text.get(f"index/{area}.md", "") + index_text.get("index.md", "")
        if note.resolve() not in referenced_notes and note.name not in own_index:
            bad.append(f"{rel}: note is not indexed in notes/index/{area}.md")


def check_directives(bad: list[str]) -> None:
    for path in sorted(ROOT.glob("*.md")):
        if not DIRECTIVE_RE.match(path.name) or path.name == "99-status.md":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for heading in ("## Decided against", "## Open"):
            if not re.search(rf"(?m)^{re.escape(heading)}\s*$", text):
                bad.append(f"{path.name}: missing '{heading}' section")


def git_blob_sha(data: bytes) -> str:
    """Same value as `git hash-object <file>` for an LF-normalised file."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def check_experiments(bad: list[str]) -> None:
    exp_dir = ROOT / "experiments"
    if not exp_dir.is_dir():
        return
    for exp in sorted(p for p in exp_dir.iterdir() if p.is_dir() and not p.name.startswith("_")):
        rel = exp.relative_to(ROOT).as_posix()
        rule, result = exp / "PASS_RULE.md", exp / "RESULT.md"
        if not rule.is_file():
            bad.append(f"{rel}: missing PASS_RULE.md")
            continue
        if not result.is_file():
            continue
        text = result.read_text(encoding="utf-8", errors="replace")
        match = BLOB_RE.search(text)
        if not match:
            bad.append(f"{rel}/RESULT.md: missing 'PASS_RULE.md blob: <sha>' line")
        elif match.group(1) != git_blob_sha(rule.read_bytes()):
            bad.append(f"{rel}: PASS_RULE.md changed after RESULT.md was written (blob SHA mismatch)")
        if not SCORE_RE.search(text):
            bad.append(f"{rel}/RESULT.md: missing 'k of n rules pass' score")


def main() -> int:
    bad: list[str] = []
    for path in tracked_files():
        if not path.is_file() or exempt(path):
            continue
        if path.suffix not in TEXT_SUFFIXES and path.name not in TEXT_NAMES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            bad.append(f"{path.relative_to(ROOT).as_posix()}: not valid UTF-8")
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if EM_DASH in line:
                bad.append(f"{path.relative_to(ROOT).as_posix()}:{number}: em dash (U+2014)")

    check_notes_index(bad)
    check_directives(bad)
    check_experiments(bad)

    if bad:
        print("\n".join(bad), file=sys.stderr)
        print(f"{len(bad)} problem(s). See AGENTS.md sections 2 and 3.", file=sys.stderr)
        return 1
    print("text check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
