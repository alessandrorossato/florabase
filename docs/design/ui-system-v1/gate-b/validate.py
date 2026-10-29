"""Validate the bounded Gate B visual evidence without a browser or application API."""

import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

DOCS = Path(__file__).resolve().parent
manifest = json.loads((DOCS / "asset-manifest.json").read_text())
assets = Path(manifest["root"])
screenshots = manifest["screenshots"]
assert len(screenshots) == 72
for item in screenshots:
    path = (assets / item["file"]).resolve()
    assert path.is_relative_to(assets.resolve())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"], path
    assert path.stat().st_size == item["bytes"]
    assert all(dimension > 0 for dimension in item["raster"])

captures = json.loads((DOCS / "capture-metadata.json").read_text())
themes = json.loads((DOCS / "theme-metadata.json").read_text())
assert len(captures) == 27
assert len({(c["key"], c["device"]) for c in captures}) == 27
for capture in captures:
    assert capture["viewport"] == [
        {"desktop": 1440, "tablet": 1024, "mobile": 390}[capture["device"]],
        844,
    ]
    assert capture["scroll"][0] <= capture["client"], capture
assert len(themes) == 36
assert (
    len(
        {
            (c["key"], c.get("device", "desktop"), c["palette"], c["appearance"])
            for c in themes
        }
    )
    == 36
)
for theme in themes:
    assert theme["attributes"] == {
        "palette": theme["palette"],
        "appearance": theme["appearance"],
    }
    assert theme["scroll"][0] <= theme["client"]

dashboard = json.loads((DOCS / "dashboard-geometry.json").read_text())
assert dashboard["viewport"] == [1440, 844]
assert dashboard["document"] == {"width": 1440, "height": 844}
assert dashboard["dpr"] == dashboard["scale"] == 1
assert len(dashboard["images"]) == len(dashboard["cards"]) == 8
assert len({i["source"] for i in dashboard["images"]}) == 8
assert len({c["rect"]["y"] for c in dashboard["cards"]}) == 2
assert len({c["rect"]["x"] for c in dashboard["cards"]}) == 4
assert len({(c["rect"]["x"], c["rect"]["y"]) for c in dashboard["cards"]}) == 8
for image in dashboard["images"]:
    assert image["loaded"] and image["fit"] == "cover"
    assert abs(image["rect"]["width"] / image["rect"]["height"] - 4 / 3) < 0.01
for region in [dashboard["header"], dashboard["kpis"], dashboard["next"]] + [
    card["rect"] for card in dashboard["cards"]
]:
    assert 0 <= region["top"] < region["bottom"] <= 844


class Links(HTMLParser):
    def handle_starttag(self, _tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name not in {"src", "href"} or not value:
                continue
            url = urlsplit(value)
            if url.scheme or not url.path:
                continue
            path = unquote(url.path)
            target = (
                assets / path.removeprefix("/renders/gate-b/")
                if path.startswith("/renders/gate-b/")
                else assets.parent / path.removeprefix("/renders/")
                if path.startswith("/renders/")
                else DOCS / path
            )
            assert target.is_file(), target


Links().feed((DOCS / "index.html").read_text())
print(
    "Gate B evidence passed: 72 JPEGs, 27 responsive and 36 theme captures; 4x2 loaded Dashboard fits 1440x844"
)
