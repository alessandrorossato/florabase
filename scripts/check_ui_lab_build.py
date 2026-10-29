"""Prove the default production build does not contain the development UI laboratory."""

import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
dist = root / "frontend/dist"
fixture_digests = {
    photo["sha256"]
    for photo in json.loads(
        (root / "scripts/fixtures/botanical-v5/media-manifest.json").read_text()
    )
}
assert (dist / "index.html").is_file(), (
    "Run the default frontend production build first"
)
for path in dist.rglob("*"):
    if not path.is_file():
        continue
    assert "ui-lab" not in str(path.relative_to(dist))
    assert hashlib.sha256(path.read_bytes()).hexdigest() not in fixture_digests, path
    if path.suffix in {".js", ".html", ".css"}:
        text = path.read_text()
        assert not any(
            marker in text
            for marker in [
                "lab-photo-overview",
                "ScaffoldDirectoryExample",
                "Saved Views compatibility exercise",
                "Development only · synthetic Review data",
            ]
        ), path
print(
    "Production exclusion passed: no lab entry, fixture UI, or showcase styles in dist"
)
