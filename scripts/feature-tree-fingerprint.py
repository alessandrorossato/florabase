#!/usr/bin/env python3
"""Create or compare the local content receipt used by feature delivery."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path


RECEIPT = Path(".git/info/florabase-feature-verification.json")


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, stdout=subprocess.PIPE, text=True
    ).stdout.strip()


def mode_for(path: Path) -> str:
    details = path.lstat()
    if stat.S_ISLNK(details.st_mode):
        return "120000"
    return "100755" if details.st_mode & stat.S_IXUSR else "100644"


def working_entries() -> list[dict[str, str]]:
    paths = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout.split(b"\0")
    entries: list[dict[str, str]] = []
    for raw_path in sorted({item for item in paths if item}):
        path_text = raw_path.decode("utf-8", "surrogateescape")
        path = Path(path_text)
        if not path.exists() and not path.is_symlink():
            continue
        entries.append(
            {
                "path": path_text,
                "mode": mode_for(path),
                "blob": git("hash-object", "--path", path_text, path_text),
            }
        )
    return entries


def head_entries() -> list[dict[str, str]]:
    output = subprocess.run(
        ["git", "ls-tree", "-r", "-z", "HEAD"], check=True, stdout=subprocess.PIPE
    ).stdout
    entries: list[dict[str, str]] = []
    for item in output.split(b"\0"):
        if not item:
            continue
        metadata, raw_path = item.split(b"\t", 1)
        mode, object_type, blob = metadata.decode().split()
        if object_type != "blob":
            continue
        entries.append(
            {"path": raw_path.decode("utf-8", "surrogateescape"), "mode": mode, "blob": blob}
        )
    return entries


def digest(entries: list[dict[str, str]]) -> str:
    value = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(value).hexdigest()


def fail(message: str) -> None:
    print(f"feature receipt: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    command = parser.add_subparsers(dest="command", required=True)
    write = command.add_parser("write")
    write.add_argument("--branch", required=True)
    write.add_argument("--base", required=True)
    verify = command.add_parser("verify")
    verify.add_argument("--branch", required=True)
    verify.add_argument("--base", required=True)
    args = parser.parse_args()

    if args.command == "write":
        receipt = {
            "version": 1,
            "branch": args.branch,
            "base": args.base,
            "working_tree_digest": digest(working_entries()),
        }
        RECEIPT.parent.mkdir(parents=True, exist_ok=True)
        RECEIPT.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
        print("feature receipt: recorded verified working tree")
        return

    try:
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"no usable verification receipt ({error}); rerun make feature-verify")
    if receipt.get("version") != 1 or receipt.get("branch") != args.branch:
        fail("receipt belongs to another branch; rerun make feature-verify")
    if receipt.get("base") != args.base:
        fail("receipt uses another main base; rerun make feature-verify")
    if receipt.get("working_tree_digest") != digest(head_entries()):
        fail("HEAD tree differs from verified working tree; rerun make feature-verify")
    print("feature receipt: current HEAD matches verified working tree")


if __name__ == "__main__":
    main()
