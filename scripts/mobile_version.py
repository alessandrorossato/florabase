#!/usr/bin/env python3
"""Single-source Florabase Android versionName / versionCode helper.

Derives a strictly monotonic positive 32-bit integer `versionCode` from the SemVer
release version in `frontend/package.json` (used by `mobile/android/app/build.gradle`,
`scripts/mobile-android-release.sh`, and `.github/workflows/mobile-android-release.yml`).

Formula:
    versionCode = major * 10_000_000 + minor * 100_000 + patch * 1_000 + stage_offset

Bounds:
    major in [0, 209], minor in [0, 99], patch in [0, 99]
    stage_offset:
        -alpha.N (1 <= N <= 299) -> N           (1..299)
        -beta.N  (1 <= N <= 299) -> 300 + N     (301..599)
        -rc.N    (1 <= N <= 299) -> 600 + N     (601..899)
        stable (no pre-release)  -> 900

Examples:
    0.1.0-beta.9  ->   100309
    0.1.0-beta.10 ->   100310
    0.1.0-rc.1    ->   100601
    0.1.0         ->   100900
    0.1.1         ->   101900
    1.0.0-rc.1    -> 10000601
    1.0.0         -> 10000900
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SEMVER_PATTERN = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-(alpha|beta|rc)\.([1-9][0-9]*))?$"
)

MAX_MAJOR = 209
MAX_MINOR = 99
MAX_PATCH = 99
MAX_PRERELEASE_NUM = 299
STAGE_BASE: dict[str, int] = {
    "alpha": 0,
    "beta": 300,
    "rc": 600,
}
STABLE_OFFSET = 900


def compute_version_code(version: str) -> int:
    """Compute the deterministic monotonic Android versionCode for a Florabase SemVer."""
    trimmed = version.strip()
    match = SEMVER_PATTERN.fullmatch(trimmed)
    if match is None:
        raise ValueError(
            f"Unsupported Florabase version '{version}': expected MAJOR.MINOR.PATCH"
            " with optional -alpha.N, -beta.N, or -rc.N (N >= 1, no leading zeros)."
        )

    major = int(match.group(1))
    minor = int(match.group(2))
    patch = int(match.group(3))
    stage = match.group(4)
    stage_num_raw = match.group(5)

    if major > MAX_MAJOR:
        raise ValueError(f"Major version {major} exceeds maximum supported value {MAX_MAJOR}.")
    if minor > MAX_MINOR:
        raise ValueError(f"Minor version {minor} exceeds maximum supported value {MAX_MINOR}.")
    if patch > MAX_PATCH:
        raise ValueError(f"Patch version {patch} exceeds maximum supported value {MAX_PATCH}.")

    if stage is None:
        stage_offset = STABLE_OFFSET
    else:
        assert stage_num_raw is not None
        stage_num = int(stage_num_raw)
        if stage_num < 1 or stage_num > MAX_PRERELEASE_NUM:
            raise ValueError(
                f"Pre-release number {stage_num} for -{stage} must be in 1..{MAX_PRERELEASE_NUM}."
            )
        stage_offset = STAGE_BASE[stage] + stage_num

    version_code = major * 10_000_000 + minor * 100_000 + patch * 1_000 + stage_offset
    if version_code <= 0 or version_code > 2_100_000_000:
        raise ValueError(f"Computed versionCode {version_code} is out of Android bounds.")
    return version_code


def read_frontend_version(root: Path = ROOT) -> str:
    pkg_path = root / "frontend" / "package.json"
    data = json.loads(pkg_path.read_text(encoding="utf-8"))
    version = data.get("version")
    if not isinstance(version, str) or not version.strip():
        raise ValueError(f"Missing string version in {pkg_path}")
    return version.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version",
        help="Explicit SemVer string to evaluate (defaults to frontend/package.json).",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repository root containing frontend/package.json.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--version-name", action="store_true", help="Print only versionName.")
    group.add_argument("--version-code", action="store_true", help="Print only versionCode.")
    group.add_argument(
        "--json",
        action="store_true",
        help="Print JSON object with versionName and versionCode.",
    )
    args = parser.parse_args(argv)

    version_name = args.version.strip() if args.version else read_frontend_version(args.root)
    version_code = compute_version_code(version_name)

    if args.version_name:
        print(version_name)
    elif args.version_code:
        print(version_code)
    else:
        print(json.dumps({"versionName": version_name, "versionCode": version_code}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"mobile_version error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
