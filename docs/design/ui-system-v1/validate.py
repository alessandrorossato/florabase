"""Small assert-based design-package check; not a canonical product gate."""

import hashlib
import json
import re
import struct
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from serve import ASSETS, CAPS, DOCS, ROOT, target_for


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, _tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.links.extend(
            value for key, value in attrs if key in {"href", "src"} and value
        )


# Boundary checks cover decoded traversal, mapped roots and unknown baseline keys.
assert target_for("/") == DOCS / "index.html"
assert target_for("/tokens.css") == ROOT / "frontend/src/styles/tokens.css"
assert target_for("/photos/aloe.jpg").is_file()
assert target_for("/baseline/049.jpg").is_file()
for request in [
    "/../features.json",
    "/%2e%2e/features.json",
    "/fonts/../../private",
    "/photos/../plan.json",
]:
    try:
        target_for(request)
    except PermissionError:
        pass
    else:
        raise AssertionError(f"Traversal accepted: {request}")
try:
    target_for("/baseline/not-a-capture.jpg")
except FileNotFoundError:
    pass
else:
    raise AssertionError("Unknown baseline accepted")

links_checked = 0
for page in DOCS.glob("*.html"):
    parser = Links()
    parser.feed(page.read_text())
    for link in parser.links:
        url = urlsplit(urljoin("/" + page.name, link))
        if url.scheme or url.netloc or not url.path:
            continue
        assert target_for(url.path).is_file(), (page.name, link)
        links_checked += 1

source = (DOCS / "prototype.js").read_text()
assert re.findall(r"fetch\(([^)]+)\)", source) == ['"./data.json"']
assert not any(
    word in source
    for word in ["localStorage", "sessionStorage", "/api/v1", "XMLHttpRequest"]
)
assert (
    "url('/fonts/" in (DOCS / "review.css").read_text()
    or 'url("/fonts/' in (DOCS / "review.css").read_text()
)
assert "tokens.css" in (DOCS / "prototype.css").read_text()
data = json.loads((DOCS / "data.json").read_text())
assert len(data["records"]) == 124
examples = {r["key"]: r for r in data["records"]}
assert examples["seed:00"]["quantity"] == "Unknown"
assert examples["seed:01"]["date"] == "2025"
assert examples["seed:03"]["quantity"] == "103 seeds"
assert examples["seed:03"]["order"] != "Not recorded"
assert len({r["key"] for r in data["records"]}) == 124
assert all(r.get("coverage") for r in data["records"] if r["kind"] == "identity")
for photo in data["photos"]:
    assert (
        digest(ROOT / "scripts/fixtures/botanical-v5" / photo["file"])
        == photo["sha256"]
    )
review = json.loads((DOCS / "ux-decisions.json").read_text())
assert len(review) == 28
assert Counter(r["decision"] for r in review) == {
    "KEEP": 13,
    "REFINE": 8,
    "REDESIGN": 7,
}
assert all(
    all(
        r.get(key)
        for key in [
            "goal",
            "attention",
            "waste",
            "navigation",
            "complexity",
            "change",
            "tradeoff",
            "evidence",
        ]
    )
    for r in review
)
assert all(key in CAPS for r in review for key in r["evidence"])

captures = json.loads((ASSETS / "renders/capture-metadata.json").read_text())
themes = json.loads((ASSETS / "renders/theme-metadata.json").read_text())
checks = json.loads((ASSETS / "renders/interaction-checks.json").read_text())
scenarios = json.loads((ASSETS / "renders/scenario-metadata.json").read_text())
assert len(scenarios) == 8
assert len(captures) == 75 and len({c["key"] for c in captures}) == 75
assert Counter(c["width"] for c in captures) == {1440: 25, 1024: 25, 390: 25}
assert len(themes) == 12
assert len(checks) >= 22 and all(c["pass"] for c in checks)
assert all(
    c["scrollWidth"] <= c["width"] and not c["brokenImages"]
    for c in captures + themes + scenarios
)
asset_manifest = []
for capture in captures + themes + scenarios:
    path = ASSETS / "renders" / (capture["key"] + ".jpg")
    raw = path.read_bytes()
    assert raw[:2] == b"\xff\xd8"
    offset = 2
    while offset < len(raw):
        assert raw[offset] == 255
        marker = raw[offset + 1]
        offset += 2
        length = struct.unpack(">H", raw[offset : offset + 2])[0]
        if (
            marker == 192
        ):  # Browser returns baseline JPEG, regardless of requested filename.
            height, width = struct.unpack(">HH", raw[offset + 3 : offset + 7])
            break
        offset += length
    else:
        raise AssertionError("Missing JPEG frame dimensions")
    asset_manifest.append(
        {
            "key": capture["key"],
            "cssViewport": [capture["width"], capture["height"]],
            "raster": [width, height],
            "sha256": digest(path),
            "file": str(path),
        }
    )
for font in (ASSETS / "fonts").rglob("*.woff2"):
    asset_manifest.append({"file": str(font), "sha256": digest(font)})
manifest_path = DOCS / "asset-manifest.json"
if (
    not manifest_path.exists()
    or json.loads(manifest_path.read_text()) != asset_manifest
):
    manifest_path.write_text(json.dumps(asset_manifest, indent=2) + "\n")
print(
    f"Design checks passed: {links_checked} local HTML references;124 records;8 photo hashes;28 decisions;75 responsive +12 theme +8 contextual captures;{len(checks)} interaction assertions;asset manifest generated"
)
