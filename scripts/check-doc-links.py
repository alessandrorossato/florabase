#!/usr/bin/env python3
"""Offline checks of relative links and documentation structure across repository Markdown."""

from __future__ import annotations

import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r'!?\[[^\]\n]*\]\(\s*(<[^>]*>|(?:[^()\s]|\([^()]*\))+)(?:\s+"[^"]*")?\s*\)')
REFERENCE = re.compile(r"!?\[([^\]\n]+)\]\[([^\]\n]*)\]")
DEFINITION = re.compile(r"^ {0,3}\[([^\]]+)\]:\s*(<[^>]*>|\S+)")
HEADING = re.compile(r"^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$")

TOMBSTONES = (
    "docs/installation.md",
    "docs/backup-restore.md",
    "docs/security.md",
    "docs/versioning.md",
    "docs/deployment.md",
    "docs/mobile.md",
    "docs/portable-installation.md",
)
ALLOWED_TOP_LEVEL_DOCS = frozenset(
    {
        "README.md",
        "agent-map.md",
        "progress.md",
        "features.json",
        *(Path(p).name for p in TOMBSTONES),
    }
)
LIVING_FOLDERS = (
    "docs/operate",
    "docs/develop",
    "docs/architecture",
    "docs/product",
    "docs/features/collection",
    "docs/features/activity",
    "docs/features/explore",
    "docs/features/sourcing",
    "docs/features/tools",
)
SPLIT_INDEX_FOLDERS = {
    "docs/develop/workflow": "docs/develop/development-workflow.md",
    "docs/architecture/domain-model": "docs/architecture/domain-model.md",
}
SIZE_WARNING_BYTES = 40 * 1024


def prose(text: str, *, heading_text: bool = False) -> str:
    result = []
    fence = ""
    for line in text.splitlines():
        match = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if match:
            mark = match.group(1)
            if not fence:
                fence = mark
            elif (
                mark[0] == fence[0] and len(mark) >= len(fence) and not line[match.end() :].strip()
            ):
                fence = ""
            result.append("")
        else:
            result.append(
                "" if fence else re.sub(r"`([^`]*)`", r"\1" if heading_text else "", line)
            )
    return "\n".join(result)


def anchors(text: str) -> set[str]:
    counts: dict[str, int] = defaultdict(int)
    found = set()
    for line in prose(text, heading_text=True).splitlines():
        match = HEADING.match(line)
        if not match:
            continue
        title = re.sub(r"[^\w\- ]", "", match.group(1).lower())
        slug = title.replace(" ", "-")
        candidate = slug
        while candidate in found:
            counts[slug] += 1
            candidate = f"{slug}-{counts[slug]}"
        found.add(candidate)
    return found


def local_link_targets(root: Path, source: Path) -> set[Path]:
    targets: set[Path] = set()
    lines = prose(source.read_text(encoding="utf-8")).splitlines()
    definitions = {}
    for line in lines:
        definition = DEFINITION.match(line)
        if definition:
            definitions[" ".join(definition.group(1).lower().split())] = definition.group(2)
    for line in lines:
        if DEFINITION.match(line):
            continue
        destinations = [match.group(1) for match in LINK.finditer(line)]
        for match in REFERENCE.finditer(line):
            key = " ".join((match.group(2) or match.group(1)).lower().split())
            if key in definitions:
                destinations.append(definitions[key])
        for raw in destinations:
            destination = raw.strip("<>")
            parts = urlsplit(destination)
            if parts.scheme or parts.netloc or destination.startswith("//") or not parts.path:
                continue
            target = (source.parent / unquote(parts.path)).resolve()
            if target.is_relative_to(root.resolve()):
                targets.add(target)
    return targets


def check(root: Path, documents: tuple[str, ...]) -> list[str]:
    errors = []
    for name in documents:
        source = root / name
        if not source.is_file():
            errors.append(f"{name}: missing document")
            continue
        lines = prose(source.read_text(encoding="utf-8")).splitlines()
        definitions = {}
        for line in lines:
            definition = DEFINITION.match(line)
            if definition:
                definitions[" ".join(definition.group(1).lower().split())] = definition.group(2)
        for number, line in enumerate(lines, 1):
            if DEFINITION.match(line):
                continue
            destinations = [match.group(1) for match in LINK.finditer(line)]
            for match in REFERENCE.finditer(line):
                key = " ".join((match.group(2) or match.group(1)).lower().split())
                if key in definitions:
                    destinations.append(definitions[key])
            for raw in destinations:
                destination = raw.strip("<>")
                parts = urlsplit(destination)
                if parts.scheme or parts.netloc or destination.startswith("//"):
                    continue
                target = (
                    (source.parent / unquote(parts.path)).resolve()
                    if parts.path
                    else source.resolve()
                )
                if not target.is_relative_to(root.resolve()) or not target.exists():
                    errors.append(f"{name}:{number}: missing local target {destination}")
                elif parts.fragment and target.is_file() and target.suffix.lower() == ".md":
                    if unquote(parts.fragment) not in anchors(target.read_text(encoding="utf-8")):
                        errors.append(f"{name}:{number}: missing anchor {destination}")
    return errors


def has_summary_line(path: Path) -> bool:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or not lines[0].startswith("# "):
        return False
    for line in lines[1:6]:
        if line.startswith("> Summary:") and line.removeprefix("> Summary:").strip():
            return True
    return False


def check_structure(root: Path, documents: tuple[str, ...]) -> tuple[list[str], list[str]]:
    """Enforce docs/ subfolder structure, index coverage, summaries, tombstones, and size warnings."""
    errors: list[str] = []
    warnings: list[str] = []
    docs_dir = root / "docs"
    if not docs_dir.is_dir():
        return errors, warnings

    # 1. Allowed top-level files in docs/
    for entry in sorted(docs_dir.iterdir()):
        if entry.is_file() and entry.name not in ALLOWED_TOP_LEVEL_DOCS:
            errors.append(
                f"docs/{entry.name}: unexpected top-level file in docs/ — "
                "put it in a subfolder or docs/archive/<FEATURE-ID>/"
            )

    # 2. Living folder index coverage + summaries + size warnings
    folder_indexes: list[tuple[str, str]] = [
        (folder, f"{folder}/README.md") for folder in LIVING_FOLDERS
    ] + list(SPLIT_INDEX_FOLDERS.items())

    for folder, index_rel in folder_indexes:
        folder_path = root / folder
        if not folder_path.is_dir():
            continue
        index_path = root / index_rel
        if not index_path.is_file():
            errors.append(f"{index_rel}: missing folder index")
            indexed: set[Path] = set()
        else:
            indexed = local_link_targets(root, index_path)
        for md in sorted(folder_path.glob("*.md")):
            if md.name == "README.md":
                continue
            rel = str(md.relative_to(root))
            if md.resolve() not in indexed:
                errors.append(f"{rel}: orphan living doc not linked from {index_rel}")
            if not has_summary_line(md):
                errors.append(
                    f"{rel}: missing one-line '> Summary: ...' after title"
                )
            size = md.stat().st_size
            if size > SIZE_WARNING_BYTES:
                warnings.append(
                    f"{rel}: living doc is {size / 1024:.1f} KB (> 40 KB); consider splitting"
                )

    # 3. Tombstones exist and point to an existing local target
    for tombstone_rel in TOMBSTONES:
        tombstone = root / tombstone_rel
        if not tombstone.is_file():
            errors.append(f"{tombstone_rel}: missing required tombstone")
            continue
        targets = [t for t in local_link_targets(root, tombstone) if t.is_file() and t != tombstone.resolve()]
        if not targets:
            errors.append(f"{tombstone_rel}: tombstone has no valid local target link")

    return errors, warnings


def main() -> int:
    paths = (
        subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", "*.md"],
            cwd=ROOT,
        )
        .decode()
        .split("\0")
    )
    documents = tuple(sorted({path for path in paths if path and (ROOT / path).is_file()}))
    errors = check(ROOT, documents)
    struct_errors, warnings = check_structure(ROOT, documents)
    all_errors = errors + struct_errors
    for warning in sorted(warnings):
        print(f"WARNING: {warning}")
    print(
        "\n".join(sorted(all_errors))
        if all_errors
        else f"Document links and structure passed ({len(documents)} documents)"
    )
    return bool(all_errors)


if __name__ == "__main__":
    sys.exit(main())
