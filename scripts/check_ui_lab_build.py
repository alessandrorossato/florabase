"""Prove the default production build does not contain the development UI laboratory."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKERS = (
    "lab-photo-overview",
    "ScaffoldDirectoryExample",
    "Saved Views compatibility exercise",
    "Development only · synthetic Review data",
)


def check_dist(dist: Path) -> None:
    if not (dist / "index.html").is_file():
        raise ValueError("Run the default frontend production build first")
    fixture_digests = {
        photo["sha256"]
        for photo in json.loads(
            (ROOT / "scripts/fixtures/botanical-v5/media-manifest.json").read_text()
        )
    }
    for path in dist.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(dist)
        if "ui-lab" in str(relative):
            raise ValueError(f"UI lab path in production build: {relative}")
        if hashlib.sha256(path.read_bytes()).hexdigest() in fixture_digests:
            raise ValueError(f"UI lab fixture in production build: {relative}")
        if path.suffix in {".js", ".html", ".css"}:
            content = path.read_text()
            if any(marker in content for marker in MARKERS):
                raise ValueError(f"UI lab content in production build: {relative}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist", type=Path, nargs="?", default=ROOT / "frontend/dist")
    args = parser.parse_args()
    try:
        check_dist(args.dist)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Production exclusion failed: {error}\n")
    print("Production exclusion passed: no lab entry, fixture UI, or showcase styles in dist")


if __name__ == "__main__":
    main()
