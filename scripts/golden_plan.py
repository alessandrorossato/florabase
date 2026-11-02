"""TEST-DATA-001 golden dataset plan: pure, seeded and stdlib only; performs no database access."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from typing import Any

MANIFEST = Path(__file__).resolve().parent / "fixtures" / "golden" / "scenarios.json"
COVERAGE = MANIFEST.parent / "COVERAGE.md"
NOTE = "Synthetic golden dataset; no real collection, provenance or botanical evidence."
Payload = dict[str, Any]


class PlanError(RuntimeError):
    pass


def load_manifest() -> dict[str, Any]:
    manifest: dict[str, Any] = json.loads(MANIFEST.read_text())
    return manifest


def ref(key: str) -> dict[str, str]:
    return {"$ref": key}


def day(value: date) -> dict[str, int | str]:
    return {"precision": "day", "year": value.year, "month": value.month, "day": value.day}


def month(year: int, value: int) -> dict[str, int | str]:
    return {"precision": "month", "year": year, "month": value}


def year(value: int) -> dict[str, int | str]:
    return {"precision": "year", "year": value}


def seeds(value: int | str, *, approximate: bool = False) -> Payload:
    return {"kind": "seed_count", "value": str(value), "is_approximate": approximate}


def weight(value: str, unit: str, *, approximate: bool = False) -> Payload:
    return {"kind": "weight", "value": value, "unit": unit, "is_approximate": approximate}


def items(value: int | str, *, approximate: bool = False) -> Payload:
    return {"kind": "item_count", "value": str(value), "is_approximate": approximate}


def group_count(value: int, *, approximate: bool = False) -> Payload:
    return {"value": value, "is_approximate": approximate}


class Scenario:
    """Nodes of one scenario; its RNG is independent, so adding a scenario shifts no other."""

    def __init__(self, identifier: str, seed: int, anchor: date, volume: int) -> None:
        self.id = identifier
        self.random = random.Random(f"{seed}:{identifier}")
        self.anchor = anchor
        self.volume = volume
        self.nodes: list[Payload] = []

    def key(self, kind: str, local: str) -> str:
        return f"{kind}:{self.id}/{local}"

    def add(self, kind: str, local: str, payload: Payload, *, record: str | None = None) -> str:
        """`record` names the model prefix when an operation differs from what it creates; `op` has none."""
        key = self.key(record or kind, local)
        self.nodes.append({"key": key, "kind": kind, "scenario": self.id, "payload": payload})
        return key

    def relative(self, days: int) -> str:
        return (self.anchor + timedelta(days=days)).isoformat()


SCENARIOS: dict[str, Callable[[Scenario], None]] = {}


def scenario(identifier: str) -> Callable[[Callable[[Scenario], None]], Callable[[Scenario], None]]:
    def register(function: Callable[[Scenario], None]) -> Callable[[Scenario], None]:
        SCENARIOS[identifier] = function
        return function

    return register


# Shared reference records; every later scenario may depend on these stable keys.
BASE_IDENTITY = "identity:base-reference/basil"
BASE_LAVENDER = "identity:base-reference/lavender"
BASE_ALOE = "identity:base-reference/aloe"
BASE_SUPPLIER = "supplier:base-reference/seller"
BASE_LOCATION = "location:base-reference/shelf"
BASE_BENCH = "location:base-reference/bench"
BASE_SITE = "site:base-reference/mapped"


@scenario("base-reference")
def base_reference(s: Scenario) -> None:
    s.add("owner", "owner", {"login_name": "golden-owner", "display_name": "Golden Owner"})
    for local, name, common in (
        ("basil", "Ocimum basilicum", "Golden — Basil"),
        ("lavender", "Lavandula angustifolia", "Golden — Lavender"),
        ("aloe", "Aloe vera", "Golden — Aloe"),
    ):
        s.add("identity", local, {"scientific_name": name, "common_name": common})
    s.add("supplier", "seller", {"name": "Golden — Base seller", "kind": "seller", "notes": NOTE})
    root = s.add("location", "root", {"name": "Golden collection", "parent_id": None})
    s.add("location", "shelf", {"name": "Golden seed shelf", "parent_id": ref(root)})
    s.add("location", "bench", {"name": "Golden greenhouse bench", "parent_id": ref(root)})
    place = s.add(
        "place",
        "garden",
        {
            "name": "Golden demonstration locality",
            "parent_id": ref("country:IT"),
            "place_type": "locality",
        },
    )
    s.add(
        "site",
        "mapped",
        {
            "name": "Golden mapped site (fabricated coordinates)",
            "geographic_place_id": ref(place),
            "latitude": "45.100000",
            "longitude": "11.200000",
            "coordinate_accuracy_m": "25",
            "notes": NOTE,
        },
    )


@scenario("identity-completeness")
def identity_completeness(s: Scenario) -> None:
    s.add("identity", "sparse", {"scientific_name": "Viola tricolor"})
    s.add(
        "identity",
        "unicode-hybrid",
        {"scientific_name": "Salvia × jamensis", "common_name": "Golden — Sálvia çœur 鼠尾草"},
    )
    s.add(
        "identity",
        "long-cultivar",
        {
            "scientific_name": "Capsicum annuum",
            "cultivar_name": "Golden deliberately long cultivar label " + "x" * 80,
            "common_name": "Golden — Long cultivar",
        },
    )
    s.add(
        "identity",
        "cultivar-a",
        {"scientific_name": "Solanum lycopersicum", "cultivar_name": "Golden A"},
    )
    s.add(
        "identity",
        "cultivar-b",
        {"scientific_name": "Solanum lycopersicum", "cultivar_name": "Golden B"},
    )


@scenario("identity-reference")
def identity_reference(s: Scenario) -> None:
    rich = s.add(
        "identity",
        "rich",
        {"scientific_name": "Chamaerops humilis", "common_name": "Golden — Rich reference"},
    )
    s.add(
        "profile",
        "rich",
        {
            "identity_id": ref(rich),
            "description": f"{NOTE} Rich text for layout. " * 12,
            "origin_distribution": "Synthetic comparison assertion; not botanical evidence.",
        },
    )
    custom = s.add(
        "place",
        "native",
        {
            "name": "Golden uncharted native area with a deliberately long label",
            "parent_id": ref("country:BR"),
            "place_type": "other_named_area",
        },
    )
    for local, place in (("broad", "country:005"), ("nested", "country:BR"), ("custom", custom)):
        s.add("range", local, {"identity_id": ref(rich), "place_id": ref(place)})
    s.add(
        "taxon_link",
        "basil",
        {
            "identity_id": ref(BASE_IDENTITY),
            "external_id": "48GBK",
            "scientific_name": "Ocimum basilicum L.",
            "canonical_name": "Ocimum basilicum",
            "authorship": "L.",
            "family": "Lamiaceae",
            "genus": "Ocimum",
        },
        record="external_taxon",
    )


@scenario("sourcing-suppliers-orders")
def sourcing(s: Scenario) -> None:
    for kind in ("nursery", "supermarket", "person", "exchange", "other"):
        s.add("supplier", kind, {"name": f"Golden — {kind} supplier", "kind": kind, "notes": NOTE})
    retired = s.add("supplier", "retired", {"name": "Golden — Retired seller", "kind": "seller"})
    exact = s.add(
        "order",
        "exact",
        {
            "supplier_id": ref(BASE_SUPPLIER),
            "ordered_on": day(s.anchor - timedelta(days=30)),
            "order_reference": "Golden PO-001",
            "total_price": "42.50",
            "currency": "EUR",
            "notes": NOTE,
        },
    )
    s.add(
        "order", "free", {"order_reference": "Golden gift", "total_price": "0", "currency": "USD"}
    )
    s.add(
        "order",
        "month-unknown-supplier",
        {"ordered_on": month(2026, 3), "order_reference": "Golden month-only purchase"},
    )
    s.add(
        "order",
        "retained-retired",
        {"supplier_id": ref(retired), "ordered_on": year(2024), "order_reference": "Golden 2024"},
    )
    s.add("retire_supplier", "retired", {"supplier_id": ref(retired)}, record="op")
    for local in ("first", "second"):
        s.add(
            "seed",
            local,
            {
                "botanical_identity_id": ref(BASE_IDENTITY),
                "label": f"Golden — {local} packet in one order",
                "source_kind": "purchased",
                "supplier_id": ref(BASE_SUPPLIER),
                "order_id": ref(exact),
                "location_id": ref(BASE_LOCATION),
            },
        )
    s.add(
        "seed",
        "outside-order",
        {
            "botanical_identity_id": ref(BASE_IDENTITY),
            "label": "Golden — Purchased outside any Order",
            "source_kind": "purchased",
            "supplier_id": ref(BASE_SUPPLIER),
        },
    )


@scenario("seed-quantity-states")
def seed_quantity_states(s: Scenario) -> None:
    identity = ref(BASE_LAVENDER)
    cases: tuple[tuple[str, Payload], ...] = (
        ("unknown", {"quantity": None, "source_kind": "unknown"}),
        (
            "approximate-year",
            {
                "quantity": seeds(100, approximate=True),
                "acquisition_date": year(2025),
                "source_kind": "gift_exchange",
            },
        ),
        (
            "exact-month",
            {
                "quantity": seeds(102),
                "acquisition_date": month(2026, 9),
                "source_kind": "self_collected",
                "provenance_site_id": ref(BASE_SITE),
            },
        ),
        ("weight-g", {"quantity": weight("4.250", "g"), "source_kind": "purchased_fruit"}),
        ("weight-mg", {"quantity": weight("750", "mg", approximate=True), "source_kind": "other"}),
        ("exhausted-zero", {"quantity": seeds(0), "lifecycle": "exhausted"}),
        ("discarded", {"quantity": seeds(3), "lifecycle": "discarded"}),
        ("lost", {"lifecycle": "lost", "expected_viability_until": year(2020)}),
    )
    for local, fields in cases:
        s.add(
            "seed",
            local,
            {
                "botanical_identity_id": identity,
                "label": f"Golden — seed {local}",
                "notes": NOTE,
                **fields,
            },
        )


@scenario("sowing-germination-states")
def sowing_states(s: Scenario) -> None:
    lot = s.add(
        "seed",
        "source",
        {
            "botanical_identity_id": ref(BASE_IDENTITY),
            "label": "Golden — sowing source",
            "quantity": seeds(200),
            "location_id": ref(BASE_LOCATION),
        },
    )
    cases: tuple[tuple[str, Payload], ...] = (
        ("germination-null", {"germinated_count": None}),
        ("germination-zero", {"germinated_count": 0}),
        ("germination-positive", {"germinated_count": 8, "quantity": seeds(12)}),
        ("completed", {"lifecycle": "completed", "sowing_date": year(2025)}),
        ("failed", {"lifecycle": "failed", "sowing_date": month(2026, 4), "germinated_count": 0}),
        ("abandoned", {"lifecycle": "abandoned"}),
        (
            "environment",
            {
                "substrate": "Golden seed compost",
                "temperature_min_c": "-2.5",
                "temperature_max_c": "24",
                "location_id": ref(BASE_BENCH),
                "sowing_date": day(s.anchor - timedelta(days=40)),
            },
        ),
    )
    for local, fields in cases:
        s.add(
            "sowing",
            local,
            {"seed_lot_id": ref(lot), "label": f"Golden — sowing {local}", "notes": NOTE, **fields},
        )
    observed = s.key("sowing", "environment")
    for local, offset, count in (("first", -20, 0), ("second", -15, 2)):
        s.add(
            "observation",
            local,
            {
                "sowing_id": ref(observed),
                "observed_on": s.relative(offset),
                "newly_germinated_count": count,
            },
        )


@scenario("propagation-operations")
def propagation_operations(s: Scenario) -> None:
    lot = s.add(
        "seed",
        "source",
        {
            "botanical_identity_id": ref(BASE_ALOE),
            "label": "Golden — propagated packet",
            "quantity": seeds(60),
        },
    )
    used = s.add(
        "seed",
        "use-all",
        {
            "botanical_identity_id": ref(BASE_ALOE),
            "label": "Golden — packet used entirely",
            "quantity": seeds(5),
        },
    )
    sowing = s.add(
        "sow_transition",
        "partial",
        {
            "seed_lot_id": ref(lot),
            "sowing": {"label": "Golden — partial transition", "quantity": seeds(20)},
            "source_adjustment": {"mode": "partial"},
        },
        record="sowing",
    )
    s.add(
        "sow_transition",
        "all",
        {
            "seed_lot_id": ref(used),
            "sowing": {"label": "Golden — used-all transition", "quantity": seeds(5)},
            "source_adjustment": {"mode": "use_all"},
        },
        record="sowing",
    )
    undone = s.add(
        "sow_transition",
        "undone",
        {
            "seed_lot_id": ref(lot),
            "sowing": {"label": "Golden — reversed transition", "quantity": seeds(4)},
            "source_adjustment": {"mode": "partial"},
        },
        record="sowing",
    )
    s.add(
        "propagation_reverse",
        "undone",
        {"result_type": "sowing", "result_id": ref(undone)},
        record="op",
    )
    s.add(
        "plant_from_sowing",
        "derived",
        {
            "sowing_id": ref(sowing),
            "resulting_sowing_lifecycle": "active",
            "plant": {
                "botanical_identity_id": ref(BASE_ALOE),
                "label": "Golden — sowing-derived plant",
            },
        },
        record="plant",
    )
    s.add(
        "group_from_sowing",
        "derived",
        {
            "sowing_id": ref(sowing),
            "resulting_sowing_lifecycle": "completed",
            "plant_group": {
                "botanical_identity_id": ref(BASE_ALOE),
                "label": "Golden — sowing-derived group",
                "quantity": group_count(9),
            },
        },
        record="group",
    )


@scenario("plant-lifecycle-states")
def plant_states(s: Scenario) -> None:
    for lifecycle in ("active", "dead", "lost", "discarded"):
        s.add(
            "plant",
            lifecycle,
            {
                "botanical_identity_id": ref(BASE_ALOE),
                "label": f"Golden — direct plant {lifecycle}",
                "direct_origin_kind": "purchased" if lifecycle == "active" else "unknown",
                "supplier_id": ref(BASE_SUPPLIER) if lifecycle == "active" else None,
                "lifecycle": lifecycle,
                "location_id": ref(BASE_BENCH) if lifecycle == "active" else None,
                "notes": NOTE,
            },
        )
    s.add(
        "plant",
        "no-label-unknown-origin",
        {"botanical_identity_id": ref(BASE_LAVENDER), "direct_origin_kind": "unknown"},
    )
    moving = s.add(
        "plant",
        "transferred",
        {"botanical_identity_id": ref(BASE_ALOE), "label": "Golden — Transferred away"},
    )
    s.add(
        "transfer",
        "plant",
        {
            "target_type": "plant",
            "target_id": ref(moving),
            "occurred_on": month(2026, 5),
            "recipient": "Golden fictitious recipient",
        },
        record="event",
    )
    for local, quantity, lifecycle in (
        ("exact", group_count(12), "active"),
        ("approximate", group_count(30, approximate=True), "active"),
        ("unknown", None, "active"),
        ("completed-zero", group_count(0), "completed"),
    ):
        s.add(
            "group",
            local,
            {
                "botanical_identity_id": ref(BASE_ALOE),
                "label": f"Golden — group {local}",
                "direct_origin_kind": "unknown",
                "quantity": quantity,
                "lifecycle": lifecycle,
            },
        )
    source = s.key("group", "exact")
    s.add(
        "extract",
        "extracted",
        {"plant_group_id": ref(source), "label": "Golden — extracted individual"},
        record="plant",
    )
    returned = s.add(
        "extract",
        "reintegrated",
        {"plant_group_id": ref(source), "label": "Golden — returned individual"},
        record="plant",
    )
    s.add("reintegrate", "reintegrated", {"plant_id": ref(returned)}, record="event")


@scenario("harvest-stored-material")
def harvest_stored_material(s: Scenario) -> None:
    source = s.add(
        "plant",
        "source",
        {"botanical_identity_id": ref(BASE_IDENTITY), "label": "Golden — harvest source"},
    )
    group = s.add(
        "group",
        "source",
        {
            "botanical_identity_id": ref(BASE_IDENTITY),
            "label": "Golden — harvest group",
            "direct_origin_kind": "unknown",
            "quantity": group_count(3),
        },
    )
    untracked = s.add(
        "harvest",
        "untracked",
        {
            "plant_id": ref(source),
            "label": "Golden — untracked harvest",
            "occurred_on": None,
            "items": [{"material_kind": "leaf", "description": "Golden unmeasured leaves"}],
        },
    )
    tracked = s.add(
        "harvest",
        "tracked",
        {
            "plant_id": ref(source),
            "label": "Golden — tracked seed harvest",
            "occurred_on": month(2026, 8),
            "notes": NOTE,
            "items": [{"material_kind": "seed", "quantity": items(100)}],
        },
    )
    weighed = s.add(
        "harvest",
        "weighed",
        {
            "plant_group_id": ref(group),
            "label": "Golden — group fruit by weight",
            "occurred_on": day(s.anchor - timedelta(days=10)),
            "items": [
                {"material_kind": "fruit", "quantity": weight("1.5", "kg", approximate=True)}
            ],
        },
    )
    active = s.add(
        "inventory",
        "active",
        {
            "item_id": ref("item:" + tracked),
            "state": "active",
            "quantity": items(100),
            "location_id": ref(BASE_LOCATION),
        },
    )
    consumed = s.add(
        "inventory",
        "consumed",
        {"item_id": ref("item:" + weighed), "state": "active", "quantity": weight("1.5", "kg")},
    )
    s.add(
        "disposition",
        "partial",
        {
            "inventory_id": ref(active),
            "kind": "gifted",
            "mode": "partial",
            "quantity": items(10),
            "occurred_on": month(2026, 9),
        },
    )
    s.add(
        "disposition",
        "use-all",
        {"inventory_id": ref(consumed), "kind": "consumed", "mode": "use_all"},
    )
    s.add(
        "conversion",
        "kept",
        {
            "inventory_id": ref(active),
            "mode": "partial",
            "label": "Golden — converted seed lot",
            "quantity": seeds(20),
        },
    )
    undone = s.add(
        "conversion",
        "undone",
        {
            "inventory_id": ref(active),
            "mode": "partial",
            "label": "Golden — converted then reversed",
            "quantity": seeds(5),
        },
    )
    s.add("conversion_reverse", "undone", {"conversion_id": ref(undone)}, record="op")
    s.add(
        "inventory",
        "untracked-depleted",
        {"item_id": ref("item:" + untracked), "state": "depleted", "quantity": None},
    )


@scenario("location-geography-edges")
def location_geography(s: Scenario) -> None:
    parent = BASE_BENCH
    for depth in range(5):
        parent = s.add(
            "location",
            f"depth-{depth}",
            {"name": f"Golden nested level {depth}", "parent_id": ref(parent)},
        )
    s.add("location", "empty-root", {"name": "Golden empty root location", "parent_id": None})
    for local, latitude, longitude in (
        ("north-pole", "90.000000", "0.000000"),
        ("antimeridian", "-16.500000", "-180.000000"),
        ("null-island", "0.000000", "0.000000"),
    ):
        s.add(
            "site",
            local,
            {
                "name": f"Golden fabricated extreme {local}",
                "latitude": latitude,
                "longitude": longitude,
                "notes": NOTE,
            },
        )
    s.add("site", "no-coordinates", {"name": "Golden site without coordinates", "notes": NOTE})
    s.add(
        "seed",
        "at-deep-location",
        {
            "botanical_identity_id": ref(BASE_ALOE),
            "label": "Golden — stored at depth, collected at an extreme site",
            "location_id": ref(parent),
            "provenance_site_id": ref(s.key("site", "antimeridian")),
            "source_kind": "self_collected",
        },
    )


@scenario("media-references")
def media_references(s: Scenario) -> None:
    def colour() -> list[int]:
        return [s.random.randrange(40, 230) for _ in range(3)]

    target = s.add(
        "seed",
        "with-media",
        {"botanical_identity_id": ref(BASE_IDENTITY), "label": "Golden — seed with media"},
    )
    plant = s.add(
        "plant",
        "with-media",
        {"botanical_identity_id": ref(BASE_IDENTITY), "label": "Golden — plant with media"},
    )
    shared = s.add(
        "generated_asset",
        "shared",
        {"title": "Golden shared image", "width": 96, "height": 96, "colour": colour()},
        record="asset",
    )
    s.add(
        "generated_asset",
        "wide",
        {"title": "Golden panorama image", "width": 480, "height": 32, "colour": colour()},
        record="asset",
    )
    s.add(
        "generated_asset",
        "orphan",
        {"title": None, "width": 1, "height": 1, "colour": colour()},
        record="asset",
    )
    external = s.add(
        "external_asset",
        "reference",
        {
            "title": "Golden external reference (intentionally offline)",
            "image_url": "https://example.invalid/golden/leaf.png",
            "source_url": "https://example.invalid/golden",
            "attribution": "Synthetic reference-only example",
            "licence_label": "CC0-1.0",
        },
        record="asset",
    )
    links = {
        "seed": ("seed_lot", target, shared),
        "plant": ("plant", plant, shared),
        "supplier": ("supplier", BASE_SUPPLIER, shared),
        "external": ("seed_lot", target, external),
    }
    for local, (kind, record, asset) in links.items():
        s.add(
            "link",
            local,
            {
                "asset_id": ref(asset),
                "target_type": kind,
                "target_id": ref(record),
                "caption": f"Golden {local} caption",
            },
        )
    for local in ("seed", "plant"):
        kind, record, _ = links[local]
        s.add(
            "primary",
            local,
            {"target": kind, "target_id": ref(record), "link_id": ref(s.key("link", local))},
            record="op",
        )
    s.add(
        "external_cover",
        "lavender",
        {
            "identity_id": ref(BASE_LAVENDER),
            "image_url": "https://example.invalid/golden/cover.png",
            "source_url": "https://example.invalid/golden/cover",
            "attribution": "Synthetic external cover; never fetched",
            "privacy_acknowledged": True,
        },
        record="cover",
    )


@scenario("journal-history")
def journal_history(s: Scenario) -> None:
    plant = s.add(
        "plant",
        "journaled",
        {
            "botanical_identity_id": ref(BASE_LAVENDER),
            "label": "Golden — journaled plant",
            "collection_entry_date": year(2020),
        },
    )
    cases = (
        ("observation-unknown-date", "observation", None),
        ("flowering-year", "flowering", year(2023)),
        ("fruiting-month", "fruiting", month(2024, 7)),
        ("pruning-day", "pruning", day(s.anchor - timedelta(days=100))),
        ("treatment-day", "treatment", day(s.anchor - timedelta(days=99))),
    )
    for local, kind, when in cases:
        s.add(
            "event",
            local,
            {"plant_id": ref(plant), "kind": kind, "occurred_on": when, "notes": NOTE},
        )
    s.add(
        "event",
        "long-notes",
        {"plant_id": ref(plant), "kind": "observation", "notes": "Golden long note. " * 500},
    )


@scenario("schedule-states")
def schedule_states(s: Scenario) -> None:
    plant = s.add(
        "plant",
        "scheduled",
        {"botanical_identity_id": ref(BASE_ALOE), "label": "Golden — scheduled plant"},
    )
    group = s.add(
        "group",
        "scheduled",
        {
            "botanical_identity_id": ref(BASE_ALOE),
            "label": "Golden — scheduled group",
            "direct_origin_kind": "unknown",
        },
    )
    lot = s.add(
        "seed",
        "scheduled",
        {"botanical_identity_id": ref(BASE_ALOE), "label": "Golden — scheduled seed"},
    )
    sowing = s.add(
        "sowing",
        "scheduled",
        {"seed_lot_id": ref(lot), "label": "Golden — scheduled sowing"},
    )
    targets: tuple[tuple[str, str, int, str | None, str | None], ...] = (
        ("overdue", "inspect", -3, "plant", plant),
        ("today", "water", 0, "plant_group", group),
        ("soon", "check_germination", 5, "sowing", sowing),
        ("later", "follow_up", 60, "seed_lot", lot),
        ("identity", "follow_up", 2, "botanical_identity", BASE_ALOE),
        ("location", "move", 3, "location", BASE_BENCH),
        ("collection", "fertilize", 1, None, None),
        ("completed", "water", -8, "plant", plant),
        ("completed-event", "inspect", -6, "plant", plant),
        ("cancelled", "repot", -2, "plant", plant),
    )
    for local, kind, offset, target, record in targets:
        s.add(
            "schedule",
            local,
            {
                "activity_kind": kind,
                "title": f"Golden — {local} activity",
                "due_on": s.relative(offset),
                "target": {"kind": target, "id": ref(record)} if target and record else None,
                "notes": NOTE,
            },
        )
    s.add(
        "schedule_complete",
        "completed",
        {"activity_id": ref(s.key("schedule", "completed")), "expected_version": 1},
        record="op",
    )
    s.add(
        "schedule_complete",
        "completed-event",
        {
            "activity_id": ref(s.key("schedule", "completed-event")),
            "expected_version": 1,
            "event": {"kind": "observation", "occurred_on": s.relative(-6), "notes": NOTE},
        },
        record="op",
    )
    s.add(
        "schedule_cancel",
        "cancelled",
        {"activity_id": ref(s.key("schedule", "cancelled")), "version": 1},
        record="op",
    )


@scenario("saved-views")
def saved_views(s: Scenario) -> None:
    owner = ref("owner:base-reference/owner")
    for surface, state in (
        ("seed_lots", {"q": "Golden", "lifecycle": "history"}),
        ("plants", {"q": "", "lifecycle": "all", "type": "group"}),
        ("harvests", {"q": "", "material": "seed"}),
    ):
        s.add(
            "saved_view",
            surface,
            {
                "owner_id": owner,
                "name": f"Golden {surface}",
                "surface": surface,
                "state_version": 1,
                "state": state,
            },
        )


@scenario("volume-background")
def volume_background(s: Scenario) -> None:
    """Seeded background mix; scale lives only in the profile, never in the coverage scenarios."""
    species = ["Thymus vulgaris", "Rosmarinus officinalis", "Mentha spicata", "Allium cepa"]
    for index in range(s.volume):
        identity = s.add(
            "identity",
            f"{index:05d}",
            {
                "scientific_name": s.random.choice(species),
                "cultivar_name": f"Golden volume {index:05d}",
            },
        )
        mix = s.random.random()
        lot = s.add(
            "seed",
            f"{index:05d}",
            {
                "botanical_identity_id": ref(identity),
                "label": f"Golden — volume packet {index:05d}",
                "quantity": seeds(s.random.randrange(1, 500)) if mix < 0.7 else None,
                "location_id": ref(BASE_LOCATION) if mix < 0.5 else None,
                "lifecycle": "active" if mix < 0.9 else "exhausted",
            },
        )
        if mix < 0.6:
            sowing = s.add(
                "sowing",
                f"{index:05d}",
                {
                    "seed_lot_id": ref(lot),
                    "label": f"Golden — volume sowing {index:05d}",
                    "germinated_count": s.random.randrange(0, 30),
                    "sowing_date": day(s.anchor - timedelta(days=s.random.randrange(1, 700))),
                },
            )
            if mix < 0.3:
                plant = s.add(
                    "plant",
                    f"{index:05d}",
                    {
                        "botanical_identity_id": ref(identity),
                        "label": f"Golden — volume plant {index:05d}",
                        "originating_sowing_id": ref(sowing),
                    },
                )
                s.add(
                    "event",
                    f"{index:05d}",
                    {
                        "plant_id": ref(plant),
                        "kind": "observation",
                        "occurred_on": day(s.anchor - timedelta(days=s.random.randrange(1, 300))),
                        "notes": NOTE,
                    },
                )


def build_plan(
    profile: str, *, manifest: dict[str, Any] | None = None, volume: int | None = None
) -> dict[str, Any]:
    """`volume` overrides only an experiment's scale; the result never matches a pinned digest."""
    manifest = manifest or load_manifest()
    selected = manifest["profiles"].get(profile)
    if selected is None:
        raise PlanError(f"Unknown golden profile: {profile}")
    if selected["status"] != "implemented":
        raise PlanError(f"Golden profile {profile} is {selected['status']}; not generated yet")
    anchor = date.fromisoformat(manifest["anchor_date"])
    scale = selected["volume"] if volume is None else volume
    nodes: list[Payload] = []
    for entry in manifest["scenarios"]:
        if entry["status"] != "implemented" or profile not in entry["profiles"]:
            continue
        built = Scenario(entry["id"], manifest["seed"], anchor, scale)
        SCENARIOS[entry["id"]](built)
        nodes.extend(built.nodes)
    plan = {
        "dataset": manifest["dataset"],
        "version": manifest["version"],
        "profile": profile,
        "seed": manifest["seed"],
        "anchor_date": manifest["anchor_date"],
        "volume": scale,
        "nodes": nodes,
    }
    check_plan(plan)
    return plan


def plan_digest(plan: dict[str, Any]) -> str:
    canonical = json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def references(value: Any) -> list[str]:
    if isinstance(value, dict):
        if set(value) == {"$ref"}:
            return [value["$ref"]]
        return [found for item in value.values() for found in references(item)]
    if isinstance(value, list):
        return [found for item in value for found in references(item)]
    return []


def check_plan(plan: dict[str, Any]) -> None:
    """Every key is unique and every reference names an earlier node or canonical country."""
    known: set[str] = set()
    for node in plan["nodes"]:
        for target in references(node["payload"]):
            if target not in known and not target.startswith("country:"):
                raise PlanError(f"{node['key']} references unknown or later node {target}")
        if node["key"] in known:
            raise PlanError(f"Duplicate golden key {node['key']}")
        known.add(node["key"])
        if node["kind"] == "harvest":
            known.add("item:" + node["key"])


def coverage_markdown(manifest: dict[str, Any]) -> str:
    profiles = list(manifest["profiles"])
    lines = [
        "# Golden dataset scenario coverage",
        "",
        "Generated by `python3 scripts/golden_plan.py coverage` from `scenarios.json`. Do not edit.",
        "",
        "| Domain | Scenario | Status | Profiles | Covered states |",
        "| --- | --- | --- | --- | --- |",
    ]
    for entry in manifest["scenarios"]:
        lines.append(
            f"| {entry['domain']} | `{entry['id']}` | {entry['status']} | "
            f"{', '.join(item for item in profiles if item in entry['profiles']) or '—'} | "
            f"{'; '.join(entry['covers'])} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["summary", "coverage"])
    parser.add_argument("--profile", default="smoke")
    args = parser.parse_args()
    try:
        manifest = load_manifest()
        if args.action == "coverage":
            print(coverage_markdown(manifest), end="")
            return 0
        plan = build_plan(args.profile, manifest=manifest)
    except PlanError as error:
        print(f"Golden plan refused: {error}", file=sys.stderr)
        return 1
    summary = {
        "profile": args.profile,
        "plan_sha256": plan_digest(plan),
        "nodes": len(plan["nodes"]),
        "kinds": dict(sorted(Counter(node["kind"] for node in plan["nodes"]).items())),
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
