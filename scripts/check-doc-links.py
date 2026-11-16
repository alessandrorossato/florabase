#!/usr/bin/env python3
"""Offline checks of relative links in repository Markdown."""

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
    print(
        "\n".join(sorted(errors))
        if errors
        else f"Document links passed ({len(documents)} documents)"
    )
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main())
