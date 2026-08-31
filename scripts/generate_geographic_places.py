#!/usr/bin/env python3
"""Normalize the pinned CLDR territory hierarchy into Florabase seed data."""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

CLDR_ONLY_CODES = {"AC", "CP", "DG", "EA", "IC", "QO", "TA", "XK"}
PREFERRED_GROUPING_PARENTS = {"419": "019"}
DISPLAY_NAME_OVERRIDES = {
    "001": "World",
    "419": "Latin America and the Caribbean",
}
RELEASE_TIMESTAMP_MS = int(datetime(2026, 7, 8, tzinfo=UTC).timestamp() * 1000)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def code_type(code: str) -> str:
    if code.isdigit():
        return "un_m49"
    if code in CLDR_ONLY_CODES:
        return "cldr_territory"
    return "iso_3166_1_alpha_2"


def stable_uuid7(code: str) -> UUID:
    digest = hashlib.sha256(f"unicode_cldr:48.2.1:{code}".encode()).digest()
    random_bits = int.from_bytes(digest, "big") & ((1 << 74) - 1)
    random_a = random_bits >> 62
    random_b = random_bits & ((1 << 62) - 1)
    value = (
        (RELEASE_TIMESTAMP_MS << 80)
        | (0x7 << 76)
        | (random_a << 64)
        | (0b10 << 62)
        | random_b
    )
    return UUID(int=value)


def normalize(containment_path: Path, names_path: Path) -> dict[str, object]:
    containment = load_json(containment_path)["supplemental"]["territoryContainment"]
    names = load_json(names_path)["main"]["en"]["localeDisplayNames"]["territories"]
    parents: dict[str, str] = {}
    included = {"001"}
    grouped_children = {
        child
        for grouping in PREFERRED_GROUPING_PARENTS
        for child in containment[grouping]["_contains"]
    }
    for parent, value in containment.items():
        if "-status-" in parent or value.get("_grouping") == "true":
            continue
        included.add(parent)
        for child in value["_contains"]:
            if child in grouped_children:
                continue
            if child in parents:
                raise ValueError(f"Canonical node {child} has multiple parents")
            parents[child] = parent
            included.add(child)
    for grouping, parent in PREFERRED_GROUPING_PARENTS.items():
        parents[grouping] = parent
        included.add(grouping)
        for child in containment[grouping]["_contains"]:
            if child in parents:
                raise ValueError(f"Canonical node {child} has multiple parents")
            parents[child] = grouping
            included.add(child)
    if set(parents) != included - {"001"}:
        raise ValueError("Canonical hierarchy must have exactly one root")

    records = []
    for code in sorted(included):
        name = names.get(code)
        if not isinstance(name, str):
            raise ValueError(f"Missing English name for {code}")
        records.append(
            {
                "id": str(stable_uuid7(code)),
                "name": DISPLAY_NAME_OVERRIDES.get(code, name),
                "parent_source_code": parents.get(code),
                "source_code": code,
                "source_code_type": code_type(code),
            }
        )
    return {
        "dataset": "Unicode Common Locale Data Repository (CLDR)",
        "source": "unicode_cldr",
        "version": "48.2.1",
        "license": "Unicode-3.0",
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("containment", type=Path)
    parser.add_argument("names", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    normalized = normalize(args.containment, args.names)
    args.output.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
