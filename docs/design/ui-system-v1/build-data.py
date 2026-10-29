"""Build design-only, provider-free examples from the approved v5 fixture and audit."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
plan = json.loads((ROOT / "scripts/fixtures/botanical-v5/plan.json").read_text())
nodes = {n["key"]: n for n in plan["nodes"]}


def ref(v):
    return v.get("$ref") if isinstance(v, dict) and "$ref" in v else None


def date(v):
    if v is None:
        return "Unknown"
    if isinstance(v, str):
        return v
    return "-".join(
        str(v[k]).zfill(4 if k == "year" else 2)
        for k in ["year", "month", "day"]
        if k in v
    )


def name(k):
    if not k:
        return "Not recorded"
    p = nodes[k]["payload"]
    return (
        p.get("scientific_name")
        or p.get("name")
        or p.get("label")
        or p.get("order_reference")
        or k
    )


records = []
for n in plan["nodes"]:
    p = n["payload"]
    kind = n["kind"]
    if kind not in {
        "seed",
        "plant",
        "group",
        "supplier",
        "order",
        "location",
        "identity",
        "schedule",
        "event",
    }:
        continue
    q = p.get("quantity")
    quantity = (
        "Unknown"
        if q is None
        else ("About " if q.get("is_approximate") else "")
        + str(q.get("value", "Unknown"))
        + " "
        + ("seeds" if q.get("kind") == "seed_count" else q.get("unit", ""))
    )
    identity = nodes.get(ref(p.get("botanical_identity_id")) or n["key"], {}).get(
        "payload", {}
    )
    records.append(
        {
            "key": n["key"],
            "kind": kind,
            "label": name(n["key"]),
            "scientificName": identity.get("scientific_name", ""),
            "cultivar": identity.get("cultivar_name"),
            "commonName": identity.get("common_name"),
            "quantity": quantity.strip(),
            "state": p.get("lifecycle", "active"),
            "location": name(ref(p.get("location_id"))),
            "supplier": name(ref(p.get("supplier_id")))
            if ref(p.get("supplier_id"))
            else "Unknown supplier",
            "date": date(
                p.get("acquisition_date")
                or p.get("collection_entry_date")
                or p.get("ordered_on")
                or p.get("occurred_on")
                or p.get("due_on")
            ),
            "price": f"{p['currency']} {p['total_price']}"
            if p.get("total_price") is not None
            else "Price unknown",
            "parent": ref(p.get("parent_id")),
            "usageScopes": p.get("usage_scopes", []),
            "activityKind": p.get("activity_kind"),
            "title": p.get("title"),
            "target": ref((p.get("target") or {}).get("id")),
        }
    )
for record in records:
    payload = nodes[record["key"]]["payload"]
    record["provenance"] = name(ref(payload.get("provenance_site_id")))
    record["order"] = name(ref(payload.get("order_id")))
# Exact active SeedLot/Plant coverage copied from audit 049's rendered directory.
capture_dir = (
    Path("/home/alessandro/.codex")
    / "visualizations/2026/10/26/01a178c9-0d81-73f2-96a2-42047619aba9/release-visual-audit-001"
)
capture_list = json.loads(
    (ROOT / "docs/review/release-visual-audit-001/capture-index.json").read_text()
)
cap = next(c for c in capture_list if c["id"] == "049")
snapshot = Path(str(capture_dir / cap["file"]) + ".txt").read_text()
for r in records:
    if r["kind"] != "identity":
        continue
    display = r["scientificName"] + (
        " ‘" + r["cultivar"] + "’" if r["cultivar"] else ""
    )
    matches = [
        line
        for line in snapshot.splitlines()
        if '- button "No cover image ' + display + " " in line
    ]
    # Exact rendered name prefix prevents a plain species inheriting a cultivar's count.
    matches = [
        line for line in matches if not (not r["cultivar"] and display + " ‘" in line)
    ]
    assert len(matches) == 1, (display, matches)
    match = re.search(
        r"(\d+ seed lots?(?: · \d+ plants?)?|\d+ plants?|No active records)", matches[0]
    )
    assert match, display
    r["coverage"] = match.group(0)
# Association-free reference illustrations: do not pretend these are record primary photos/covers.
photos = json.loads(
    (ROOT / "scripts/fixtures/botanical-v5/media-manifest.json").read_text()
)
cs = json.loads(
    (ROOT / "docs/review/release-visual-audit-001/capture-index.json").read_text()
)
consumer = json.loads(
    (ROOT / "docs/review/release-visual-audit-001/component-consumers.json").read_text()
)
data = {
    "sourceCommit": "ee3487412fe458cbdf7145154c54a58b66132cae",
    "fixture": "Extended Botanical Review Dataset v5",
    "snapshotDate": "2026-10-26",
    "records": records,
    "photos": photos,
    "counts": {
        "activePlants": 17,
        "activeGroups": 7,
        "activeSeedLots": 40,
        "activeSowings": 12,
        "identities": 37,
        "representedCurrentIdentities": 33,
        "overdue": 9,
        "today": 7,
        "next7": 5,
        "schedulePlanned": 24,
        "calendarOctober": 20,
        "journal": 7,
    },
    "baselines": {
        c["id"]: {
            "file": c["file"],
            "page": c["page"],
            "viewport": c["viewport"],
            "state": c["state"],
        }
        for c in cs
    },
    "components": {k: len(v) for k, v in consumer.items()},
}
assert len([r for r in records if r["kind"] == "identity"]) == 30
assert len({r["key"] for r in records}) == len(records)
assert all(
    p["licence"] in {"CC0-1.0", "CC-BY-2.0", "CC-BY-3.0", "CC-BY-4.0"} for p in photos
)
(OUT / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
print(
    f"Design data: {len(records)} fixture examples, {len(photos)} licensed reference illustrations; no API/provider requests"
)
