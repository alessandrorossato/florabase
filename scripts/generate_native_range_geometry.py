"""Offline derivation of the reviewed Natural Earth 110m map-units presentation asset.

No download, name matching, inferred botanical knowledge or runtime GIS dependency.
"""

import hashlib
import json
import re
import sys
from pathlib import Path

SOURCE_SHA256 = "718ac51d68ed2bf5de4f563fff2e2e045db706c1d3222805f3e317140a64213b"
SOURCE_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "v5.1.2/geojson/ne_110m_admin_0_map_units.geojson"
)


def generate(source: Path, destination: Path) -> None:
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("Unreviewed geometry source; expected pinned Natural Earth map units")
    units: dict[str, str] = {}
    for feature in json.loads(raw)["features"]:
        props = feature["properties"]
        code = props["ISO_A2_EH"]
        # Unmapped disputed units remain background, never aliases for another territory.
        key = code if re.fullmatch(r"[A-Z]{2}", code) else f"unmapped:{props['GU_A3']}"
        geometry = feature["geometry"]
        polygons = (
            [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
        )
        paths = []
        for polygon in polygons:
            for ring in polygon:
                coordinates = [f"{(lon + 180) * 2:.2f},{(90 - lat) * 2:.2f}" for lon, lat in ring]
                paths.append("M" + "L".join(coordinates) + "Z")
        units[key] = units.get(key, "") + "".join(paths)
    snapshot_path = (
        Path(__file__).resolve().parent.parent
        / "backend/alembic/data/geographic_places_cldr_48_2_1.json"
    )
    snapshot = json.loads(snapshot_path.read_bytes())
    records = {row["source_code"]: row for row in snapshot["records"]}
    regions: dict[str, list[str]] = {
        code: [] for code, row in records.items() if row["source_code_type"] == "un_m49"
    }
    for code, row in records.items():
        if row["source_code_type"] != "iso_3166_1_alpha_2":
            continue
        parent = row["parent_source_code"]
        while parent is not None:
            if parent in regions:
                regions[parent].append(code)
            parent = records[parent]["parent_source_code"]
    asset = {
        "source": "Natural Earth",
        "version": "5.1.1",
        "release": "v5.1.2",
        "license": "Public domain",
        "scale": "1:110m",
        "source_url": SOURCE_URL,
        "source_sha256": SOURCE_SHA256,
        "viewBox": "0 0 720 360",
        "units": dict(sorted(units.items())),
        "regions": {code: sorted(codes) for code, codes in sorted(regions.items())},
        "containment_source": "Unicode CLDR 48.2.1, Unicode-3.0",
        "containment_sha256": hashlib.sha256(snapshot_path.read_bytes()).hexdigest(),
    }
    destination.write_text(json.dumps(asset, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    generate(Path(sys.argv[1]), Path(sys.argv[2]))
