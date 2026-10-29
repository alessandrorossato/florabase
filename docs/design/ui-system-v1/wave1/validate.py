"""Verify retained production review evidence; this is not a canonical verification receipt."""

import hashlib
import json
from pathlib import Path

from PIL import Image

DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parents[3]
ARTIFACTS = Path(
    "/home/alessandro/.codex/visualizations/2026/10/26/"
    "01a178c9-0d81-73f2-96a2-42047619aba9"
)
RENDERS = ARTIFACTS / "ui-system-v1/renders/wave1"


def validate() -> dict[str, int]:
    entries = json.loads((DOCS / "captures.json").read_text())
    indexed = {entry["id"]: entry for entry in entries}
    assert len(indexed) == len(entries)
    for entry in entries:
        path = RENDERS / f"{entry['id']}.jpg"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"], path
        with Image.open(path) as image:
            assert list(image.size) == entry["raster"], path
        assert (RENDERS / f"{entry['id']}.dom.txt").is_file()
        if "fullPageSupplement" in entry:
            full = RENDERS / entry["fullPageSupplement"]
            assert (
                hashlib.sha256(full.read_bytes()).hexdigest() == entry["fullPageSha256"]
            )
    cases = [
        "dashboard",
        "seeds-list",
        "seeds-gallery",
        "plants-list",
        "plants-gallery",
    ]
    for case in cases:
        for width in [1440, 1024, 880, 390]:
            for mode in ["light", "dark"]:
                entry = indexed[f"{case}-{width}-{mode}"]
                assert entry["viewport"] == [width, 844]
                assert entry["document"][0] <= width
                assert entry["theme"] == {"appearance": mode, "palette": "botanical"}
                assert entry["url"].startswith("http://localhost:15279/")
    geometry = json.loads((DOCS / "dashboard-geometry.json").read_text())
    for mode, measured in geometry.items():
        assert measured["viewport"] == measured["document"] == [1440, 844]
        assert measured["dpr"] == measured["scale"] == 1
        photos = measured["photos"]
        assert len(photos) == len({photo["src"] for photo in photos}) == 8
        assert all(photo["loaded"] for photo in photos)
        assert all(photo["src"].startswith("/api/v1/media-assets/") for photo in photos)
        assert len({photo["x"] for photo in photos}) == 4
        assert len({photo["y"] for photo in photos}) == 2
        assert all(
            abs(photo["width"] / photo["height"] - 4 / 3) < 0.001 for photo in photos
        )
        assert len(measured["work"]) == 5
        assert all(
            item["bottom"] <= 844 for item in measured["work"] + measured["cards"]
        )
        assert measured["footer"]["bottom"] <= 844
        entry = indexed[f"dashboard-1440-{mode}"]
        assert entry["document"] == entry["raster"] == [1440, 844]
        assert len(entry["photos"]) == 8
    sparse = indexed["dashboard-two-images-1440"]
    assert sparse["url"] == "http://127.0.0.1:15285/#/dashboard"
    assert len(sparse["photos"]) == 2
    assert len({photo["url"] for photo in sparse["photos"]}) == 2
    assert all(photo["loaded"] for photo in sparse["photos"])
    originals = json.loads(
        (ROOT / "docs/review/release-visual-audit-001/capture-index.json").read_text()
    )
    original_index = {entry["id"]: entry for entry in originals}
    baseline = json.loads((DOCS / "baseline.json").read_text())
    for item in baseline:
        original = original_index[item["id"]]
        path = ARTIFACTS / "release-visual-audit-001" / original["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == original["sha256"]
        assert original["state"] == "primary"
    source = json.loads((DOCS / "source-inventory.json").read_text())
    for item in source["files"]:
        assert (
            hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest()
            == item["sha256"]
        )
    return {
        "captures": len(entries),
        "production_matrix": 40,
        "baselines": len(baseline),
        "geometry_themes": 2,
    }


if __name__ == "__main__":
    result = validate()
    (DOCS / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
