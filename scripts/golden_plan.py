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


# COMPREHENSIVE only from here on. Real accepted names make browsing and search realistic; every
# statement about these plants stays synthetic. (scientific name, common name, family)
CATALOGUE: tuple[tuple[str, str, str], ...] = (
    ("Achillea millefolium", "Yarrow", "Asteraceae"),
    ("Aeonium arboreum", "Tree aeonium", "Crassulaceae"),
    ("Agapanthus africanus", "African lily", "Amaryllidaceae"),
    ("Agave americana", "Century plant", "Asparagaceae"),
    ("Allium schoenoprasum", "Chives", "Amaryllidaceae"),
    ("Anethum graveolens", "Dill", "Apiaceae"),
    ("Anthurium andraeanum", "Flamingo flower", "Araceae"),
    ("Arbutus unedo", "Strawberry tree", "Ericaceae"),
    ("Artemisia absinthium", "Wormwood", "Asteraceae"),
    ("Asclepias tuberosa", "Butterfly weed", "Apocynaceae"),
    ("Begonia rex", "Painted leaf begonia", "Begoniaceae"),
    ("Beta vulgaris", "Beet", "Amaranthaceae"),
    ("Bougainvillea glabra", "Paper flower", "Nyctaginaceae"),
    ("Brassica oleracea", "Wild cabbage", "Brassicaceae"),
    ("Calendula officinalis", "Pot marigold", "Asteraceae"),
    ("Camellia sinensis", "Tea plant", "Theaceae"),
    ("Cereus repandus", "Peruvian apple cactus", "Cactaceae"),
    ("Citrus limon", "Lemon", "Rutaceae"),
    ("Coffea arabica", "Arabica coffee", "Rubiaceae"),
    ("Coriandrum sativum", "Coriander", "Apiaceae"),
    ("Crassula ovata", "Jade plant", "Crassulaceae"),
    ("Cucumis sativus", "Cucumber", "Cucurbitaceae"),
    ("Cucurbita pepo", "Courgette", "Cucurbitaceae"),
    ("Cyclamen hederifolium", "Ivy-leaved cyclamen", "Primulaceae"),
    ("Daucus carota", "Wild carrot", "Apiaceae"),
    ("Dianthus caryophyllus", "Carnation", "Caryophyllaceae"),
    ("Digitalis purpurea", "Foxglove", "Plantaginaceae"),
    ("Dionaea muscipula", "Venus flytrap", "Droseraceae"),
    ("Echeveria elegans", "Mexican snowball", "Crassulaceae"),
    ("Echinacea purpurea", "Purple coneflower", "Asteraceae"),
    ("Eschscholzia californica", "California poppy", "Papaveraceae"),
    ("Ficus carica", "Common fig", "Moraceae"),
    ("Foeniculum vulgare", "Fennel", "Apiaceae"),
    ("Fragaria vesca", "Woodland strawberry", "Rosaceae"),
    ("Helianthus annuus", "Sunflower", "Asteraceae"),
    ("Hibiscus rosa-sinensis", "Chinese hibiscus", "Malvaceae"),
    ("Hyssopus officinalis", "Hyssop", "Lamiaceae"),
    ("Jasminum officinale", "Common jasmine", "Oleaceae"),
    ("Lactuca sativa", "Lettuce", "Asteraceae"),
    ("Laurus nobilis", "Bay laurel", "Lauraceae"),
    ("Linum usitatissimum", "Flax", "Linaceae"),
    ("Lithops lesliei", "Living stones", "Aizoaceae"),
    ("Mammillaria elongata", "Ladyfinger cactus", "Cactaceae"),
    ("Melissa officinalis", "Lemon balm", "Lamiaceae"),
    ("Monstera deliciosa", "Swiss cheese plant", "Araceae"),
    ("Myrtus communis", "Common myrtle", "Myrtaceae"),
    ("Nepenthes alata", "Winged pitcher plant", "Nepenthaceae"),
    ("Nigella damascena", "Love-in-a-mist", "Ranunculaceae"),
    ("Olea europaea", "Olive", "Oleaceae"),
    ("Opuntia ficus-indica", "Prickly pear", "Cactaceae"),
    ("Origanum vulgare", "Oregano", "Lamiaceae"),
    ("Papaver rhoeas", "Corn poppy", "Papaveraceae"),
    ("Passiflora edulis", "Passion fruit", "Passifloraceae"),
    ("Pelargonium graveolens", "Rose geranium", "Geraniaceae"),
    ("Petroselinum crispum", "Parsley", "Apiaceae"),
    ("Phaseolus vulgaris", "Common bean", "Fabaceae"),
    ("Pisum sativum", "Pea", "Fabaceae"),
    ("Punica granatum", "Pomegranate", "Lythraceae"),
    ("Raphanus sativus", "Radish", "Brassicaceae"),
    ("Rosa canina", "Dog rose", "Rosaceae"),
    ("Ruta graveolens", "Common rue", "Rutaceae"),
    ("Sansevieria trifasciata", "Snake plant", "Asparagaceae"),
    ("Sarracenia purpurea", "Purple pitcher plant", "Sarraceniaceae"),
    ("Satureja montana", "Winter savory", "Lamiaceae"),
    ("Sedum acre", "Goldmoss stonecrop", "Crassulaceae"),
    ("Sempervivum tectorum", "Common houseleek", "Crassulaceae"),
    ("Spinacia oleracea", "Spinach", "Amaranthaceae"),
    ("Tagetes erecta", "Mexican marigold", "Asteraceae"),
    ("Tillandsia usneoides", "Spanish moss", "Bromeliaceae"),
    ("Tropaeolum majus", "Nasturtium", "Tropaeolaceae"),
    ("Vicia faba", "Broad bean", "Fabaceae"),
    ("Vitis vinifera", "Grape vine", "Vitaceae"),
    ("Yucca filamentosa", "Adam's needle", "Asparagaceae"),
    ("Zea mays", "Maize", "Poaceae"),
    ("Zinnia elegans", "Common zinnia", "Asteraceae"),
)
CULTIVARS = (
    ("Capsicum annuum", "Golden Corno di Toro", "Sweet pepper"),
    ("Capsicum annuum", "Golden Habanada", "Sweet habanero"),
    ("Cucurbita pepo", "Golden Tondo di Nizza", "Round courgette"),
    ("Helianthus annuus", "Golden Velvet Queen", "Red sunflower"),
    ("Lactuca sativa", "Golden Lollo Rosso", "Red coral lettuce"),
    ("Ocimum basilicum", "Golden Genovese", "Sweet basil"),
    ("Rosa canina", "Golden Inermis", "Thornless dog rose"),
    ("Solanum lycopersicum", "Golden San Marzano", "Plum tomato"),
    ("Solanum lycopersicum", "Golden Cuore di Bue", "Oxheart tomato"),
    ("Vitis vinifera", "Golden Sangiovese", "Sangiovese grape"),
    ("Zinnia elegans", "Golden Queen Lime", "Lime zinnia"),
)
COUNTRIES = ("IT", "ES", "GR", "TR", "MA", "ZA", "IN", "CN", "JP", "MX", "PE", "BR", "US", "AU")


def catalogue_key(index: int) -> str:
    return f"identity:identity-catalogue/c{index:03d}"


def cultivar_key(index: int) -> str:
    return f"identity:identity-catalogue/v{index:02d}"


def ago(s: Scenario, days: int) -> dict[str, int | str]:
    return day(s.anchor - timedelta(days=days))


@scenario("identity-catalogue")
def identity_catalogue(s: Scenario) -> None:
    for index, (name, common, family) in enumerate(CATALOGUE):
        identity = s.add(
            "identity", f"c{index:03d}", {"scientific_name": name, "common_name": common}
        )
        if index % 3:
            continue
        s.add(
            "profile",
            f"c{index:03d}",
            {
                "identity_id": ref(identity),
                "description": f"{NOTE} Family {family}, synthetic description of {common}.",
                "origin_distribution": "Synthetic comparison assertion; not botanical evidence.",
                "cultivation": "Synthetic cultivation note." if index % 2 else None,
                "uses": "Synthetic uses note." if index % 4 == 0 else None,
                "warnings": "Synthetic warning; do not rely on it." if index % 5 == 0 else None,
            },
        )
        for code in s.random.sample(COUNTRIES, k=1 + index % 3):
            s.add(
                "range",
                f"c{index:03d}-{code}",
                {"identity_id": ref(identity), "place_id": ref(f"country:{code}")},
            )
    for index, (name, cultivar, common) in enumerate(CULTIVARS):
        s.add(
            "identity",
            f"v{index:02d}",
            {"scientific_name": name, "cultivar_name": cultivar, "common_name": common},
        )


# Fabricated identifiers beside real names: the WFO service needs its reviewed metadata, but no
# content of this index comes from a WFO release.
WFO_ROOT, WFO_CODE = "wfo-4100001250", "wfo-9971000003"
WFO_NAMES: tuple[tuple[str, str, str, str | None], ...] = (
    # identifier, name, rank, accepted parent; a None parent is a synonym or unplaced name
    (WFO_ROOT, "Plantae", "kingdom", WFO_CODE),
    ("wfo-7000000010", "Lamiaceae", "family", WFO_ROOT),
    ("wfo-7000000020", "Asphodelaceae", "family", WFO_ROOT),
    ("wfo-7000000030", "Solanaceae", "family", WFO_ROOT),
    ("wfo-4000000011", "Salvia", "genus", "wfo-7000000010"),
    ("wfo-4000000012", "Lavandula", "genus", "wfo-7000000010"),
    ("wfo-4000000021", "Aloe", "genus", "wfo-7000000020"),
    ("wfo-4000000031", "Solanum", "genus", "wfo-7000000030"),
    ("wfo-5000000031", "Solanum sect. Lycopersicon", "section", "wfo-4000000031"),
    ("wfo-0000000101", "Salvia rosmarinus", "species", "wfo-4000000011"),
    ("wfo-0000000102", "Lavandula angustifolia", "species", "wfo-4000000012"),
    ("wfo-0000000103", "Aloe vera", "species", "wfo-4000000021"),
    ("wfo-0000000104", "Solanum lycopersicum", "species", "wfo-5000000031"),
    ("wfo-0000000201", "Rosmarinus officinalis", "species", None),
    ("wfo-0000000202", "Aloe barbadensis", "species", None),
    ("wfo-0000000203", "Lycopersicon esculentum", "species", None),
    ("wfo-0000000301", "Golden unplaced epithet", "species", None),
)
WFO_SYNONYMS = {
    "wfo-0000000201": "wfo-0000000101",
    "wfo-0000000202": "wfo-0000000103",
    "wfo-0000000203": "wfo-0000000104",
}


@scenario("taxonomy-wfo-links")
def taxonomy_wfo_links(s: Scenario) -> None:
    s.add(
        "taxonomy_source",
        "index",
        {
            "retrieved_at": f"{s.anchor.isoformat()}T00:00:00+00:00",
            "names": [
                {"ID": key, "scientificName": name, "authorship": "Golden", "rank": rank}
                for key, name, rank, _ in WFO_NAMES
            ],
            "concepts": [
                {"ID": key, "nameID": key, "parentID": parent}
                for key, _, _, parent in WFO_NAMES
                if parent
            ],
            "synonyms": [
                {"ID": f"{name}-2026-06", "nameID": name, "taxonID": accepted}
                for name, accepted in WFO_SYNONYMS.items()
            ],
        },
        record="op",
    )
    identities = {
        "accepted-section": ("Solanum lycopersicum", "Golden WFO accepted"),
        "synonym-rosemary": ("Rosmarinus officinalis", None),
        "synonym-aloe": ("Aloe barbadensis", None),
        "synonym-tomato": ("Lycopersicon esculentum", None),
        "accepted-rosemary": ("Salvia rosmarinus", None),
        "stale": ("Salvia rosmarinus", "Golden renamed after confirmation"),
        "relinked": ("Salvia rosmarinus", "Golden relinked"),
        "unlinked": ("Salvia rosmarinus", "Golden deliberately unlinked"),
    }
    for local, (name, cultivar) in identities.items():
        identity = s.add("identity", local, {"scientific_name": name, "cultivar_name": cultivar})
        # The tree shows represented identities only, so each needs a record to be read back.
        s.add(
            "seed",
            local,
            {"botanical_identity_id": ref(identity), "label": f"Golden — taxonomy record {local}"},
        )
    for local, identity, taxon in (
        ("lavender", BASE_LAVENDER, "wfo-0000000102"),
        ("aloe", BASE_ALOE, "wfo-0000000103"),
        ("accepted-section", s.key("identity", "accepted-section"), "wfo-0000000104"),
        ("synonym-rosemary", s.key("identity", "synonym-rosemary"), "wfo-0000000201"),
        ("synonym-aloe", s.key("identity", "synonym-aloe"), "wfo-0000000202"),
        ("synonym-tomato", s.key("identity", "synonym-tomato"), "wfo-0000000203"),
        ("accepted-rosemary", s.key("identity", "accepted-rosemary"), "wfo-0000000101"),
        ("stale", s.key("identity", "stale"), "wfo-0000000101"),
        ("relinked-first", s.key("identity", "relinked"), "wfo-0000000202"),
        ("relinked", s.key("identity", "relinked"), "wfo-0000000101"),
        ("unlinked", s.key("identity", "unlinked"), "wfo-0000000101"),
    ):
        s.add("wfo_link", local, {"identity_id": ref(identity), "source_taxon_id": taxon})
    s.add(
        "wfo_unlink",
        "unlinked",
        {
            "identity_id": ref(s.key("identity", "unlinked")),
            "removes": s.key("wfo_link", "unlinked"),
        },
        record="op",
    )
    s.add(
        "identity_update",
        "stale",
        {
            "identity_id": ref(s.key("identity", "stale")),
            "scientific_name": "Salvia rosmarinus",
            "cultivar_name": "Golden renamed after confirmation (changed)",
        },
        record="op",
    )
    s.add(
        "refused",
        "unplaced",
        {
            "kind": "wfo_link",
            "error": "TaxonomyConflictError",
            "payload": {
                "identity_id": ref(s.key("identity", "unlinked")),
                "source_taxon_id": "wfo-0000000301",
            },
        },
        record="op",
    )


def wcvp_name(
    identifier: str, name: str, *, status: str = "Accepted", accepted: str | None = None
) -> Payload:
    return {
        "plant_name_id": identifier,
        "taxon_name": name,
        "taxon_authors": "Golden",
        "taxon_rank": "Species",
        "taxon_status": status,
        "accepted_plant_name_id": accepted or identifier,
    }


def wcvp_rows(identifier: str, cases: tuple[tuple[str, str, str, str], ...]) -> list[Payload]:
    return [
        {
            "plant_locality_id": f"{identifier}-{index}",
            "plant_name_id": identifier,
            "area_code_l3": code,
            "introduced": introduced,
            "extinct": extinct,
            "location_doubtful": doubtful,
        }
        for index, (code, introduced, extinct, doubtful) in enumerate(cases)
    ]


@scenario("enrichment-wcvp-proposals")
def enrichment_wcvp(s: Scenario) -> None:
    mixed = (
        ("BOL", "0", "0", "0"),
        ("PER", "0", "0", "0"),
        ("ITA", "0", "0", "0"),
        ("CZE", "0", "0", "0"),
        ("BUL", "1", "0", "0"),
        ("HUN", "0", "1", "0"),
        ("THA", "0", "0", "1"),
        ("XXX", "0", "0", "0"),
    )
    for version in ("15", "16"):
        s.add(
            "wcvp_source",
            f"index-{version}",
            {
                "version": version,
                "retrieved_at": f"{s.anchor.isoformat()}T00:00:00+00:00",
                "names": [
                    wcvp_name("1001", "Golden enrichment accepted"),
                    wcvp_name("1002", "Golden enrichment open"),
                    wcvp_name("1003", "Golden enrichment stale"),
                    wcvp_name("1004", "Golden enrichment later release"),
                    wcvp_name("1005", "Golden old name", status="Synonym", accepted="1001"),
                ],
                "rows": wcvp_rows("1001", mixed)
                + wcvp_rows("1002", (("URU", "0", "0", "0"), ("PAR", "0", "0", "0")))
                + wcvp_rows("1003", (("LAO", "0", "0", "0"),))
                + wcvp_rows("1004", (("OMA", "0", "0", "0"), ("VIE", "0", "0", "0"))),
            },
            record="op",
        )
    identities = {
        "applied": "Golden enrichment accepted",
        "open": "Golden enrichment open",
        "stale": "Golden enrichment stale",
        "later": "Golden enrichment later release",
    }
    for local, name in identities.items():
        s.add("identity", local, {"scientific_name": name})
    applied, opened = s.key("identity", "applied"), s.key("identity", "open")
    # A range recorded before enrichment stays CURRENT-ONLY: nothing the source says removes it.
    s.add("profile", "applied", {"identity_id": ref(applied), "description": NOTE})
    s.add("range", "applied-prior", {"identity_id": ref(applied), "place_id": ref("country:IT")})
    for local, identity, external, version in (
        ("applied", applied, "1001", "15"),
        ("open", opened, "1002", "15"),
        ("stale", s.key("identity", "stale"), "1003", "15"),
        ("later", s.key("identity", "later"), "1004", "16"),
    ):
        s.add(
            "wcvp_link",
            local,
            {"identity_id": ref(identity), "external_id": external, "version": version},
        )
    s.add(
        "refused",
        "synonym-link",
        {
            "kind": "wcvp_link",
            "error": "EnrichmentConflictError",
            "payload": {"identity_id": ref(opened), "external_id": "1005", "version": "15"},
        },
        record="op",
    )
    applied_proposal = s.add(
        "wcvp_propose", "applied", {"identity_id": ref(applied), "version": "15"}, record="proposal"
    )
    s.add("wcvp_propose", "open", {"identity_id": ref(opened), "version": "15"}, record="proposal")
    later = s.add(
        "wcvp_propose",
        "later",
        {"identity_id": ref(s.key("identity", "later")), "version": "16"},
        record="proposal",
    )
    s.add(
        "wcvp_apply",
        "applied",
        {
            "identity_id": ref(applied),
            "proposal_id": ref(applied_proposal),
            # Bolivia only: a reviewed subset of the two mapped additions.
            "selected_place_ids": [ref("country:BO")],
        },
        record="application",
    )
    s.add(
        "wcvp_apply",
        "later",
        {
            "identity_id": ref(s.key("identity", "later")),
            "proposal_id": ref(later),
            "selected_place_ids": [ref("country:OM"), ref("country:VN")],
        },
        record="application",
    )
    s.add(
        "identity_update",
        "stale",
        {
            "identity_id": ref(s.key("identity", "stale")),
            "scientific_name": "Golden enrichment stale",
            "cultivar_name": "Golden renamed after confirmation",
        },
        record="op",
    )
    s.add(
        "refused",
        "stale-proposal",
        {
            "kind": "wcvp_propose",
            "error": "EnrichmentConflictError",
            "payload": {"identity_id": ref(s.key("identity", "stale")), "version": "15"},
        },
        record="op",
    )


@scenario("identity-synonyms-external")
def identity_synonyms_external(s: Scenario) -> None:
    def gbif(local: str, name: str, external: str, family: str, **extra: Any) -> None:
        genus = name.split()[0]
        identity = s.add("identity", local, {"scientific_name": name})
        s.add(
            "taxon_link",
            local,
            {
                "identity_id": ref(identity),
                "external_id": external,
                "scientific_name": f"{name} Golden",
                "canonical_name": name,
                "authorship": "Golden",
                "family": family,
                "genus": genus,
                **extra,
            },
            record="external_taxon",
        )

    gbif("accepted", "Rosmarinus eriocalyx", "G0001", "Lamiaceae")
    gbif(
        "synonym",
        "Lycopersicon pimpinellifolium",
        "G0002",
        "Solanaceae",
        status="SYNONYM",
        accepted={"key": "G0003", "name": "Solanum pimpinellifolium L."},
    )
    gbif("doubtful", "Golden doubtfulname", "G0004", "Asteraceae", status="DOUBTFUL")
    gbif("refreshed", "Thymus serpyllum", "G0005", "Lamiaceae")
    gbif("refresh-failed", "Thymus vulgaris", "G0006", "Lamiaceae")
    gbif("unlinked", "Mentha spicata", "G0007", "Lamiaceae")
    for local, status, family in (
        ("refreshed", 200, "Lamiaceae (revised)"),
        ("refresh-failed", 503, "Lamiaceae"),
    ):
        name = "Thymus serpyllum" if local == "refreshed" else "Thymus vulgaris"
        s.add(
            "taxon_refresh",
            local,
            {
                "identity_id": ref(s.key("identity", local)),
                "provider_status": status,
                "external_id": "G0005" if local == "refreshed" else "G0006",
                "scientific_name": f"{name} Golden",
                "canonical_name": name,
                "authorship": "Golden",
                "family": family,
                "genus": "Thymus",
            },
            record="op",
        )
    s.add(
        "taxon_unlink",
        "unlinked",
        {
            "identity_id": ref(s.key("identity", "unlinked")),
            "removes": s.key("external_taxon", "unlinked"),
        },
        record="op",
    )


@scenario("provenance-geography-hierarchy")
def provenance_geography(s: Scenario) -> None:
    region = s.add(
        "place",
        "region",
        {
            "name": "Golden Alpine region",
            "parent_id": ref("country:IT"),
            "place_type": "other_named_area",
        },
    )
    town = s.add(
        "place",
        "town",
        {"name": "Golden Alpine town", "parent_id": ref(region), "place_type": "city_town"},
    )
    valley = s.add(
        "place",
        "valley",
        {"name": "Golden Hidden valley", "parent_id": ref(town), "place_type": "locality"},
    )
    other = s.add(
        "place",
        "brazil",
        {"name": "Golden Serra locality", "parent_id": ref("country:BR"), "place_type": "locality"},
    )
    retired = s.add(
        "place",
        "retired",
        {
            "name": "Golden renamed former locality",
            "parent_id": ref(region),
            "place_type": "locality",
        },
    )
    sites = {
        "valley": (valley, "46.500001", "11.350000", "5"),
        "town": (town, "46.498765", "11.354321", None),
        "brazil": (other, "-22.900000", "-43.200000", "1000"),
        "retired": (retired, "46.111111", "11.111111", "50000"),
        "place-only": (region, None, None, None),
    }
    for local, (place, latitude, longitude, accuracy) in sites.items():
        s.add(
            "site",
            local,
            {
                "name": f"Golden site {local} (fabricated)",
                "geographic_place_id": ref(place),
                "latitude": latitude,
                "longitude": longitude,
                "coordinate_accuracy_m": accuracy,
                "notes": NOTE,
            },
        )
    # Distinct provenance on one species: the same plant name must not merge these records.
    for index, (local, fields) in enumerate(
        (
            ("site-coordinates", {"provenance_site_id": ref(s.key("site", "valley"))}),
            ("site-southern", {"provenance_site_id": ref(s.key("site", "brazil"))}),
            ("place-only", {"material_provenance_place_id": ref(valley)}),
            ("country-only", {"material_provenance_place_id": ref("country:GR")}),
            ("continent-only", {"material_provenance_place_id": ref("country:150")}),
            ("site-retired-place", {"provenance_site_id": ref(s.key("site", "retired"))}),
            ("site-without-coordinates", {"provenance_site_id": ref(s.key("site", "place-only"))}),
        )
    ):
        s.add(
            "seed",
            local,
            {
                "botanical_identity_id": ref(catalogue_key(index)),
                "label": f"Golden — provenance {local}",
                "source_kind": "self_collected",
                "acquisition_date": ago(s, 200 + index),
                "quantity": seeds(30 + index),
                **fields,
            },
        )
    s.add(
        "plant",
        "site-plant",
        {
            "botanical_identity_id": ref(catalogue_key(8)),
            "label": "Golden — direct plant from a mapped site",
            "direct_origin_kind": "other",
            "direct_origin_detail": "Golden fictitious rescue",
            "provenance_site_id": ref(s.key("site", "town")),
        },
    )
    s.add(
        "group",
        "place-group",
        {
            "botanical_identity_id": ref(catalogue_key(9)),
            "label": "Golden — direct group from a named place",
            "direct_origin_kind": "gift_exchange",
            "material_provenance_place_id": ref(other),
            "quantity": group_count(4),
        },
    )
    # Retired with history: the place stays readable through the site and lot that used it.
    s.add("retire_place", "retired", {"place_id": ref(retired)}, record="op")


@scenario("sourcing-acquisition-lineage")
def sourcing_lineage(s: Scenario) -> None:
    suppliers = {
        "nursery": ("Golden — Vivaio Alpino", "nursery"),
        "online": ("Golden — Online seed house", "seller"),
        "swap": ("Golden — Seed swap circle", "exchange"),
        "friend": ("Golden — Fictitious friend", "person"),
        "market": ("Golden — Town market", "supermarket"),
        "closed": ("Golden — Closed-down seller", "seller"),
        "unused": ("Golden — Retired before any purchase", "other"),
    }
    for local, (name, kind) in suppliers.items():
        s.add(
            "supplier",
            local,
            {
                "name": name,
                "kind": kind,
                "notes": NOTE,
            },
        )
    orders: tuple[tuple[str, str | None, Any, str | None, str | None], ...] = (
        ("spring-big", "online", ago(s, 400), "128.40", "EUR"),
        ("autumn", "online", ago(s, 200), "18.90", "EUR"),
        ("usd", "nursery", month(2025, 11), "9.99", "USD"),
        ("gbp-year", "market", year(2023), "3.00", "GBP"),
        ("free-swap", "swap", ago(s, 120), "0", "EUR"),
        ("no-price", "friend", ago(s, 90), None, None),
        ("closed-before", "closed", ago(s, 800), "45.00", "EUR"),
        ("empty", "nursery", ago(s, 15), "12.00", "EUR"),
        ("anonymous", None, None, "7.77", "EUR"),
        ("expensive", "online", ago(s, 60), "99999.99", "JPY"),
    )
    for local, supplier, when, price, currency in orders:
        s.add(
            "order",
            local,
            {
                "supplier_id": ref(s.key("supplier", supplier)) if supplier else None,
                "ordered_on": when,
                "order_reference": f"Golden {local}",
                "total_price": price,
                "currency": currency,
                "notes": NOTE,
            },
        )
    packets = (
        ("spring-1", "spring-big", "online", 10),
        ("spring-2", "spring-big", "online", 11),
        ("spring-3", "spring-big", "online", 12),
        ("autumn-1", "autumn", "online", 13),
        ("usd-1", "usd", "nursery", 14),
        ("swap-1", "free-swap", "swap", 15),
        ("closed-1", "closed-before", "closed", 16),
        ("anonymous-1", "anonymous", None, 17),
    )
    for local, order, supplier, species in packets:
        s.add(
            "seed",
            local,
            {
                "botanical_identity_id": ref(catalogue_key(species)),
                "label": f"Golden — packet {local}",
                "source_kind": "purchased",
                "supplier_id": ref(s.key("supplier", supplier)) if supplier else None,
                "order_id": ref(s.key("order", order)),
                "quantity": seeds(25 + species),
                "expected_viability_until": year(2030),
            },
        )
    s.add(
        "seed",
        "fruit",
        {
            "botanical_identity_id": ref(catalogue_key(18)),
            "label": "Golden — seed saved from a bought fruit",
            "source_kind": "purchased_fruit",
            "supplier_id": ref(s.key("supplier", "market")),
            "harvest_date": ago(s, 70),
            "quantity": seeds(12, approximate=True),
        },
    )
    s.add(
        "seed",
        "other-detail",
        {
            "botanical_identity_id": ref(catalogue_key(19)),
            "label": "Golden — found in a fictitious drawer",
            "source_kind": "other",
            "source_detail": "Golden fictitious drawer",
        },
    )
    s.add(
        "plant",
        "bought-direct",
        {
            "botanical_identity_id": ref(catalogue_key(20)),
            "label": "Golden — potted plant bought directly",
            "direct_origin_kind": "purchased",
            "supplier_id": ref(s.key("supplier", "nursery")),
            "collection_entry_date": ago(s, 300),
        },
    )
    s.add(
        "group",
        "bought-tray",
        {
            "botanical_identity_id": ref(catalogue_key(21)),
            "label": "Golden — tray bought directly",
            "direct_origin_kind": "purchased",
            "supplier_id": ref(s.key("supplier", "market")),
            "quantity": group_count(6),
        },
    )
    for local in ("closed", "unused"):
        s.add("retire_supplier", local, {"supplier_id": ref(s.key("supplier", local))}, record="op")
    s.add(
        "refused",
        "retired-supplier-unusable",
        {
            "kind": "order",
            "error": "OrderError",
            "payload": {
                "supplier_id": ref(s.key("supplier", "closed")),
                "order_reference": "Golden refused order at a closed seller",
            },
        },
        record="op",
    )


@scenario("seed-collection-produced")
def seed_collection_produced(s: Scenario) -> None:
    identity = ref(catalogue_key(22))
    mother = s.add(
        "plant",
        "mother",
        {
            "botanical_identity_id": identity,
            "label": "Golden — generation 0 mother plant",
            "direct_origin_kind": "purchased",
        },
    )
    stand = s.add(
        "group",
        "stand",
        {
            "botanical_identity_id": identity,
            "label": "Golden — generation 0 stand",
            "direct_origin_kind": "unknown",
            "quantity": group_count(15),
        },
    )
    first = s.add(
        "seed",
        "from-plant",
        {
            "botanical_identity_id": identity,
            "label": "Golden — generation 1 lot from one plant",
            "source_kind": "collection_produced",
            "producer_plant_id": ref(mother),
            "harvest_date": ago(s, 500),
            "quantity": seeds(40),
        },
    )
    s.add(
        "seed",
        "from-group",
        {
            "botanical_identity_id": identity,
            "label": "Golden — generation 1 lot from a stand",
            "source_kind": "collection_produced",
            "producer_plant_group_id": ref(stand),
            "harvest_date": month(2025, 8),
            "quantity": weight("3.5", "g"),
        },
    )
    sowing = s.add(
        "sow_transition",
        "second-generation",
        {
            "seed_lot_id": ref(first),
            "sowing": {"label": "Golden — generation 1 sowing", "quantity": seeds(10)},
            "source_adjustment": {"mode": "partial"},
        },
        record="sowing",
    )
    child = s.add(
        "plant_from_sowing",
        "second-generation",
        {
            "sowing_id": ref(sowing),
            "resulting_sowing_lifecycle": "completed",
            "plant": {
                "botanical_identity_id": identity,
                "label": "Golden — generation 2 plant",
            },
        },
        record="plant",
    )
    harvest = s.add(
        "harvest",
        "second-generation",
        {
            "plant_id": ref(child),
            "label": "Golden — generation 2 seed harvest",
            "occurred_on": ago(s, 120),
            "items": [{"material_kind": "seed", "quantity": items(50)}],
        },
    )
    stored = s.add(
        "inventory",
        "second-generation",
        {"item_id": ref("item:" + harvest), "state": "active", "quantity": items(50)},
    )
    s.add(
        "conversion",
        "third-generation",
        {
            "inventory_id": ref(stored),
            "mode": "use_all",
            "label": "Golden — generation 3 lot converted from stored seed",
            "quantity": seeds(50),
        },
    )
    s.add(
        "refused",
        "two-producers",
        {
            "kind": "seed",
            "error": "ValidationError",
            "payload": {
                "botanical_identity_id": identity,
                "label": "Golden — refused with two producers",
                "source_kind": "collection_produced",
                "producer_plant_id": ref(mother),
                "producer_plant_group_id": ref(stand),
            },
        },
        record="op",
    )


@scenario("sowing-attempts-outcomes")
def sowing_attempts(s: Scenario) -> None:
    identity = ref(catalogue_key(24))
    lot = s.add(
        "seed",
        "source",
        {
            "botanical_identity_id": identity,
            "label": "Golden — packet with repeated attempts",
            "quantity": seeds(100),
            "acquisition_date": ago(s, 400),
        },
    )
    attempts: tuple[tuple[str, Payload], ...] = (
        ("failed-cold", {"lifecycle": "failed", "germinated_count": 0, "pretreatment": "None"}),
        (
            "failed-damp",
            {"lifecycle": "failed", "germinated_count": 1, "substrate": "Golden damp peat"},
        ),
        ("abandoned-mould", {"lifecycle": "abandoned", "environment": "Golden mouldy propagator"}),
        (
            "stratified",
            {
                "pretreatment": "Golden cold stratification",
                "method_container": "Golden 9 cm pot",
                "temperature_min_c": "4",
                "temperature_max_c": "6.5",
                "germinated_count": 18,
                "lifecycle": "completed",
            },
        ),
    )
    for index, (local, fields) in enumerate(attempts):
        s.add(
            "sow_transition",
            local,
            {
                "seed_lot_id": ref(lot),
                "sowing": {
                    "label": f"Golden — attempt {local}",
                    "quantity": seeds(20),
                    "sowing_date": ago(s, 300 - index * 40),
                    **fields,
                },
                "source_adjustment": {"mode": "partial"},
            },
            record="sowing",
        )
    curve = s.key("sowing", "stratified")
    for index, (offset, count) in enumerate(((-170, 0), (-160, 3), (-150, 9), (-140, 6))):
        s.add(
            "observation",
            f"curve-{index}",
            {
                "sowing_id": ref(curve),
                "observed_on": s.relative(offset),
                "newly_germinated_count": count,
            },
        )
    s.add(
        "refused",
        "before-sowing",
        {
            "kind": "observation",
            "error": "GerminationConflictError",
            "payload": {
                "sowing_id": ref(curve),
                "observed_on": s.relative(-399),
                "newly_germinated_count": 1,
            },
        },
        record="op",
    )
    s.add(
        "refused",
        "exceed-stock",
        {
            "kind": "sow_transition",
            "error": "PropagationConflictError",
            "payload": {
                "seed_lot_id": ref(lot),
                "sowing": {"label": "Golden — refused over-sowing", "quantity": seeds(5000)},
                "source_adjustment": {"mode": "partial"},
            },
        },
        record="op",
    )


@scenario("plant-group-transitions")
def plant_group_transitions(s: Scenario) -> None:
    identity = ref(catalogue_key(25))
    lot = s.add(
        "seed",
        "source",
        {
            "botanical_identity_id": identity,
            "label": "Golden — transition source",
            "quantity": seeds(80),
        },
    )
    sowing = s.add(
        "sow_transition",
        "active",
        {
            "seed_lot_id": ref(lot),
            "sowing": {
                "label": "Golden — transition sowing",
                "quantity": seeds(40),
                "germinated_count": 30,
            },
            "source_adjustment": {"mode": "partial"},
        },
        record="sowing",
    )
    kept = s.add(
        "group_from_sowing",
        "kept",
        {
            "sowing_id": ref(sowing),
            "resulting_sowing_lifecycle": "active",
            "plant_group": {
                "botanical_identity_id": identity,
                "label": "Golden — seedlings tray",
                "quantity": group_count(20),
            },
        },
        record="group",
    )
    undone = s.add(
        "plant_from_sowing",
        "undone",
        {
            "sowing_id": ref(sowing),
            "resulting_sowing_lifecycle": "active",
            "plant": {"botanical_identity_id": identity, "label": "Golden — reversed plant"},
        },
        record="plant",
    )
    s.add(
        "propagation_reverse",
        "undone",
        {"result_type": "plant", "result_id": ref(undone)},
        record="op",
    )
    for index in range(6):
        s.add(
            "extract",
            f"pricked-{index}",
            {
                "plant_group_id": ref(kept),
                "label": f"Golden — pricked out seedling {index}",
                "collection_entry_date": ago(s, 90 - index),
            },
            record="plant",
        )
    back = s.key("plant", "pricked-5")
    s.add("reintegrate", "pricked-5", {"plant_id": ref(back)}, record="event")
    s.add(
        "refused",
        "historical-plant-cannot-die",
        {
            "kind": "event",
            "error": "EventDomainConflictError",
            "payload": {"plant_id": ref(back), "kind": "death"},
        },
        record="op",
    )
    gifted = s.add(
        "group",
        "gifted",
        {
            "botanical_identity_id": identity,
            "label": "Golden — group transferred away",
            "direct_origin_kind": "unknown",
            "quantity": group_count(5, approximate=True),
        },
    )
    s.add(
        "transfer",
        "gifted",
        {
            "target_type": "plant_group",
            "target_id": ref(gifted),
            "occurred_on": ago(s, 30),
            "recipient": "Golden fictitious school",
            "notes": NOTE,
        },
        record="event",
    )
    for lifecycle in ("dead", "lost", "discarded", "completed"):
        s.add(
            "group",
            lifecycle,
            {
                "botanical_identity_id": identity,
                "label": f"Golden — direct group {lifecycle}",
                "direct_origin_kind": "unknown",
                "lifecycle": lifecycle,
                "quantity": group_count(0) if lifecycle == "completed" else None,
            },
        )


@scenario("journal-terminal-events")
def journal_terminal_events(s: Scenario) -> None:
    identity = ref(catalogue_key(26))
    bench = ref(BASE_BENCH)
    for kind in ("death", "loss", "discarded"):
        plant = s.add(
            "plant",
            kind,
            {
                "botanical_identity_id": identity,
                "label": f"Golden — plant ended by {kind}",
                "location_id": bench,
                "collection_entry_date": ago(s, 500),
            },
        )
        s.add(
            "event",
            f"{kind}-before",
            {"plant_id": ref(plant), "kind": "repotting", "occurred_on": ago(s, 200)},
        )
        s.add(
            "event",
            kind,
            {"plant_id": ref(plant), "kind": kind, "occurred_on": ago(s, 50), "notes": NOTE},
        )
        group = s.add(
            "group",
            kind,
            {
                "botanical_identity_id": identity,
                "label": f"Golden — group ended by {kind}",
                "direct_origin_kind": "unknown",
                "quantity": group_count(3),
            },
        )
        s.add(
            "group_event",
            f"group-{kind}",
            {"plant_group_id": ref(group), "kind": kind, "occurred_on": month(2026, 6)},
            record="event",
        )
    survivor = s.add(
        "plant",
        "survivor",
        {"botanical_identity_id": identity, "label": "Golden — long journal", "location_id": bench},
    )
    for index, kind in enumerate(
        ("observation", "repotting", "flowering", "fruiting", "pruning", "treatment", "other")
    ):
        for year_value in (2023, 2024, 2025):
            s.add(
                "event",
                f"survivor-{kind}-{year_value}",
                {
                    "plant_id": ref(survivor),
                    "kind": kind,
                    "occurred_on": day(date(year_value, 3 + index, 10 + index)),
                },
            )
    s.add(
        "refused",
        "terminal-is-final",
        {
            "kind": "transfer",
            "error": "EventDomainConflictError",
            "payload": {"target_type": "plant", "target_id": ref(s.key("plant", "death"))},
        },
        record="op",
    )


@scenario("location-movement-history")
def location_movement(s: Scenario) -> None:
    site = s.add("location", "property", {"name": "Golden smallholding", "parent_id": None})
    structure = {
        "greenhouse": ("Golden greenhouse", site),
        "bench-a": ("Golden bench A", "greenhouse"),
        "bench-b": ("Golden bench B", "greenhouse"),
        "shed": ("Golden potting shed", site),
        "fridge": ("Golden seed fridge", "shed"),
        "bed": ("Golden raised bed", site),
        "former": ("Golden dismantled cold frame", site),
    }
    for local, (name, parent) in structure.items():
        key = parent if parent == site else s.key("location", parent)
        s.add("location", local, {"name": name, "parent_id": ref(key)})
    s.add(
        "location",
        "seeds-only",
        {
            "name": "Golden seed-only drawer",
            "parent_id": ref(s.key("location", "fridge")),
            "usage_scopes": ["seed_lots"],
        },
    )
    bench_a, bench_b = s.key("location", "bench-a"), s.key("location", "bench-b")
    bed, former = s.key("location", "bed"), s.key("location", "former")
    identity = ref(catalogue_key(27))
    plant = s.add(
        "plant",
        "traveller",
        {
            "botanical_identity_id": identity,
            "label": "Golden — plant moved repeatedly",
            "location_id": ref(bench_a),
        },
    )
    for index, destination in enumerate((bench_b, bed, former, bench_a)):
        s.add(
            "event",
            f"move-{index}",
            {
                "plant_id": ref(plant),
                "kind": "movement",
                "destination_location_id": ref(destination),
                "occurred_on": ago(s, 400 - index * 90),
            },
        )
    group = s.add(
        "group",
        "tray",
        {
            "botanical_identity_id": identity,
            "label": "Golden — tray moved outdoors",
            "direct_origin_kind": "unknown",
            "location_id": ref(bench_b),
            "quantity": group_count(8),
        },
    )
    s.add(
        "group_event",
        "tray-move",
        {
            "plant_group_id": ref(group),
            "kind": "movement",
            "destination_location_id": ref(bed),
            "occurred_on": ago(s, 20),
        },
        record="event",
    )
    lots = [
        s.add(
            "seed",
            f"bulk-{index}",
            {
                "botanical_identity_id": identity,
                "label": f"Golden — bulk-moved packet {index}",
                "location_id": ref(former),
            },
        )
        for index in range(4)
    ]
    sowing = s.add(
        "sowing",
        "bulk",
        {
            "seed_lot_id": ref(lots[0]),
            "label": "Golden — bulk-moved sowing",
            "location_id": ref(former),
        },
    )
    bulk_plant = s.add(
        "plant",
        "bulk",
        {
            "botanical_identity_id": identity,
            "label": "Golden — bulk-moved plant",
            "location_id": ref(former),
        },
    )
    harvest = s.add(
        "harvest",
        "bulk",
        {
            "plant_id": ref(bulk_plant),
            "label": "Golden — stored material bulk moved",
            "items": [{"material_kind": "seed", "quantity": items(12)}],
        },
    )
    stored = s.add(
        "inventory",
        "bulk",
        {
            "item_id": ref("item:" + harvest),
            "state": "active",
            "quantity": items(12),
            "location_id": ref(former),
        },
    )
    dead = s.add(
        "plant",
        "dead-at-former",
        {
            "botanical_identity_id": identity,
            "label": "Golden — dead plant remaining at a retired Location",
            "location_id": ref(former),
            "lifecycle": "dead",
        },
    )
    s.add(
        "refused",
        "bulk-conflict",
        {
            "kind": "bulk_move",
            "error": "BulkConflictError",
            "payload": {
                "records": [
                    {"kind": "seed_lot", "id": ref(lots[0])},
                    {"kind": "plant", "id": ref(dead)},
                ],
                "target_location_id": ref(bench_a),
            },
        },
        record="op",
    )
    s.add(
        "bulk_move",
        "clear-former",
        {
            "records": [
                *({"kind": "seed_lot", "id": ref(lot)} for lot in lots),
                {"kind": "sowing", "id": ref(sowing)},
                {"kind": "plant", "id": ref(bulk_plant)},
                {"kind": "harvest_inventory", "id": ref(stored)},
                {"kind": "plant", "id": ref(plant)},
            ],
            "target_location_id": ref(bench_a),
        },
        record="op",
    )
    s.add(
        "refused",
        "wrong-scope",
        {
            "kind": "plant",
            "error": "PlantDomainConflictError",
            "payload": {
                "botanical_identity_id": identity,
                "label": "Golden — refused at a seed-only Location",
                "location_id": ref(s.key("location", "seeds-only")),
            },
        },
        record="op",
    )
    s.add("retire_location", "former", {"location_id": ref(former)}, record="op")
    s.add(
        "refused",
        "active-descendants",
        {
            "kind": "retire_location",
            "error": "LocationHierarchyError",
            "payload": {"location_id": ref(site)},
        },
        record="op",
    )


@scenario("harvest-material-conversions")
def harvest_conversions(s: Scenario) -> None:
    identity = ref(catalogue_key(28))
    plant = s.add(
        "plant",
        "source",
        {"botanical_identity_id": identity, "label": "Golden — every-material source"},
    )
    group = s.add(
        "group",
        "source",
        {
            "botanical_identity_id": identity,
            "label": "Golden — group harvested then ended",
            "direct_origin_kind": "unknown",
            "quantity": group_count(4),
        },
    )
    materials = (
        ("fruit", weight("820", "g")),
        ("flower", items(40, approximate=True)),
        ("leaf", weight("12.5", "g", approximate=True)),
        ("root", None),
        ("seed", items(300)),
        ("stem_or_shoot", items(6)),
        ("whole_plant", items(1)),
        ("other", None),
    )
    for material, quantity in materials:
        s.add(
            "harvest",
            material,
            {
                "plant_id": ref(plant),
                "label": f"Golden — {material} harvest",
                "occurred_on": ago(s, 100),
                "items": [
                    {
                        "material_kind": material,
                        "description": f"Golden {material}",
                        "quantity": quantity,
                    }
                ],
            },
        )
    s.add(
        "harvest",
        "several-lines",
        {
            "plant_group_id": ref(group),
            "label": "Golden — one harvest, several material lines",
            "occurred_on": year(2025),
            "items": [
                {"material_kind": "fruit", "quantity": items(5)},
                {"material_kind": "seed", "quantity": weight("2", "g")},
                {"material_kind": "leaf"},
            ],
        },
    )
    s.add(
        "group_event",
        "ended",
        {"plant_group_id": ref(group), "kind": "death", "occurred_on": month(2026, 7)},
        record="event",
    )
    tracked = {
        material: s.add(
            "inventory",
            material,
            {
                "item_id": ref("item:" + s.key("harvest", material)),
                "state": "active",
                "quantity": quantity,
                "location_id": ref(BASE_LOCATION),
            },
        )
        for material, quantity in materials
        if quantity is not None
    }
    s.add(
        "inventory",
        "root",
        {"item_id": ref("item:" + s.key("harvest", "root")), "state": "active", "quantity": None},
    )
    for local, material, kind, mode, quantity, resulting in (
        ("eaten", "fruit", "consumed", "partial", weight("120", "g"), None),
        ("dried", "flower", "processed", "partial", None, items(30, approximate=True)),
        ("composted", "fruit", "discarded", "partial", weight("100", "g"), None),
        ("cuttings", "stem_or_shoot", "used_for_propagation", "use_all", None, None),
        ("whole-gift", "whole_plant", "gifted", "use_all", None, None),
    ):
        s.add(
            "disposition",
            local,
            {
                "inventory_id": ref(tracked[material]),
                "kind": kind,
                "mode": mode,
                "quantity": quantity,
                "resulting_quantity": resulting,
                "occurred_on": ago(s, 40),
                "notes": NOTE,
            },
        )
    s.add(
        "refused",
        "over-disposal",
        {
            "kind": "disposition",
            "error": "EventDomainConflictError",
            "payload": {
                "inventory_id": ref(tracked["seed"]),
                "kind": "gifted",
                "mode": "partial",
                "quantity": items(99999),
            },
        },
        record="op",
    )
    s.add(
        "conversion",
        "partial",
        {
            "inventory_id": ref(tracked["seed"]),
            "mode": "partial",
            "label": "Golden — stored seed partly converted",
            "quantity": seeds(100),
            "location_id": ref(BASE_LOCATION),
            "expected_viability_until": year(2031),
        },
    )
    s.add(
        "conversion",
        "other-identity",
        {
            "inventory_id": ref(tracked["seed"]),
            "mode": "partial",
            "botanical_identity_id": ref(cultivar_key(10)),
            "label": "Golden — converted as a named selection",
            "quantity": seeds(40),
        },
    )
    undone = s.add(
        "conversion",
        "undone",
        {
            "inventory_id": ref(tracked["seed"]),
            "mode": "partial",
            "label": "Golden — conversion reversed",
            "quantity": seeds(10),
        },
    )
    s.add("conversion_reverse", "undone", {"conversion_id": ref(undone)}, record="op")


@scenario("media-local-covers")
def media_local_covers(s: Scenario) -> None:
    for local, identity, colour in (
        ("local", catalogue_key(30), [120, 160, 90]),
        ("replaced", catalogue_key(31), [90, 120, 170]),
        ("replaced", catalogue_key(31), [170, 120, 90]),
        ("then-external", catalogue_key(32), [200, 200, 120]),
    ):
        suffix = "second" if colour == [170, 120, 90] else "first"
        s.add(
            "local_cover",
            f"{local}-{suffix}",
            {"identity_id": ref(identity), "width": 320, "height": 240, "colour": colour},
            record="cover",
        )
    s.add(
        "external_cover",
        "then-external",
        {
            "identity_id": ref(catalogue_key(32)),
            "image_url": "https://example.invalid/golden/cover-replaced.png",
            "source_url": "https://example.invalid/golden/cover-replaced",
            "attribution": "Synthetic external cover replacing a local one; never fetched",
            "privacy_acknowledged": True,
        },
        record="cover",
    )


@scenario("media-associations")
def media_associations(s: Scenario) -> None:
    def colour() -> list[int]:
        return [s.random.randrange(40, 230) for _ in range(3)]

    identity = ref(catalogue_key(33))
    lot = s.add(
        "seed", "target", {"botanical_identity_id": identity, "label": "Golden — media seed target"}
    )
    sowing = s.add(
        "sowing", "target", {"seed_lot_id": ref(lot), "label": "Golden — media sowing target"}
    )
    plant = s.add(
        "plant",
        "target",
        {"botanical_identity_id": identity, "label": "Golden — media plant target"},
    )
    group = s.add(
        "group",
        "target",
        {
            "botanical_identity_id": identity,
            "label": "Golden — media group target",
            "direct_origin_kind": "unknown",
        },
    )
    event = s.add(
        "event", "target", {"plant_id": ref(plant), "kind": "flowering", "occurred_on": ago(s, 12)}
    )
    harvest = s.add(
        "harvest",
        "target",
        {
            "plant_id": ref(plant),
            "label": "Golden — media harvest target",
            "items": [{"material_kind": "fruit"}],
        },
    )
    targets = {
        "seed_lot": lot,
        "sowing": sowing,
        "plant": plant,
        "plant_group": group,
        "event": event,
        "harvest": harvest,
        "supplier": BASE_SUPPLIER,
    }
    photos = {
        # Real camera-sized dimensions and a gradient texture, so media cost is not understated.
        "photo-jpeg": {"width": 1600, "height": 1200, "format": "JPEG", "texture": 1},
        "photo-webp": {"width": 1280, "height": 960, "format": "WEBP", "texture": 2},
        "photo-png": {"width": 800, "height": 600, "format": "PNG", "texture": 3},
        "portrait": {"width": 600, "height": 900, "format": "JPEG", "texture": 4},
        "tiny": {"width": 2, "height": 2, "format": "PNG"},
    }
    for local, fields in photos.items():
        s.add(
            "generated_asset",
            local,
            {"title": f"Golden {local}", "colour": colour(), **fields},
            record="asset",
        )
    shared = s.key("asset", "photo-jpeg")
    for target, record in targets.items():
        s.add(
            "link",
            f"shared-{target}",
            {
                "asset_id": ref(shared),
                "target_type": target,
                "target_id": ref(record),
                "caption": f"Golden shared caption on {target}",
            },
        )
    for index, asset in enumerate(("photo-webp", "photo-png", "portrait", "tiny")):
        s.add(
            "link",
            f"gallery-{index}",
            {
                "asset_id": ref(s.key("asset", asset)),
                "target_type": "plant",
                "target_id": ref(plant),
                "caption": None if index % 2 else f"Golden gallery position {index}",
            },
        )
    s.add(
        "refused",
        "duplicate-link",
        {
            "kind": "link",
            "error": "MediaError",
            "payload": {
                "asset_id": ref(shared),
                "target_type": "plant",
                "target_id": ref(plant),
                "caption": "Golden refused duplicate",
            },
        },
        record="op",
    )
    for target in ("seed_lot", "plant_group", "harvest", "supplier"):
        s.add(
            "primary",
            f"shared-{target}",
            {
                "target": target,
                "target_id": ref(targets[target]),
                "link_id": ref(s.key("link", f"shared-{target}")),
            },
            record="op",
        )
    # The later designation replaces the earlier one on the same Plant.
    for position in ("first", "second"):
        link = "shared-plant" if position == "first" else "gallery-1"
        s.add(
            "primary",
            f"plant-{position}",
            {"target": "plant", "target_id": ref(plant), "link_id": ref(s.key("link", link))},
            record="op",
        )


@scenario("media-external-copies")
def media_external_copies(s: Scenario) -> None:
    identity = ref(catalogue_key(34))
    plant = s.add(
        "plant",
        "target",
        {"botanical_identity_id": identity, "label": "Golden — external media target"},
    )
    for local in ("kept", "refreshed", "removed", "reference-only"):
        asset = s.add(
            "external_asset",
            local,
            {
                "title": f"Golden external {local}",
                "image_url": f"https://example.invalid/golden/{local}.png",
                "source_url": f"https://example.invalid/golden/{local}",
                "attribution": "Synthetic reference; bytes come from a fixed local stand-in",
                "licence_label": "CC-BY-4.0",
                "licence_url": "https://creativecommons.org/licenses/by/4.0/",
            },
            record="asset",
        )
        s.add(
            "link",
            local,
            {
                "asset_id": ref(asset),
                "target_type": "plant",
                "target_id": ref(plant),
                "caption": None,
            },
        )
    for local, asset, refresh, colour in (
        ("kept", "kept", False, [30, 90, 60]),
        ("refreshed-first", "refreshed", False, [90, 30, 60]),
        ("refreshed-second", "refreshed", True, [60, 90, 30]),
        ("removed-first", "removed", False, [20, 20, 90]),
    ):
        s.add(
            "media_copy",
            local,
            {
                "asset_id": ref(s.key("asset", asset)),
                "refresh": refresh,
                "width": 64,
                "height": 48,
                "colour": colour,
            },
            record="op",
        )
    s.add("media_copy_remove", "removed", {"asset_id": ref(s.key("asset", "removed"))}, record="op")


@scenario("schedule-history-states")
def schedule_history(s: Scenario) -> None:
    identity = catalogue_key(35)
    plant = s.add(
        "plant",
        "target",
        {"botanical_identity_id": ref(identity), "label": "Golden — scheduled long-term"},
    )
    ended = s.add(
        "plant",
        "ended",
        {
            "botanical_identity_id": ref(identity),
            "label": "Golden — ended with planned work",
            "location_id": ref(BASE_BENCH),
        },
    )
    kinds = (
        "repot",
        "water",
        "fertilize",
        "move",
        "check_germination",
        "inspect",
        "harvest",
        "follow_up",
    )
    for index, kind in enumerate(kinds):
        s.add(
            "schedule",
            kind,
            {
                "activity_kind": kind,
                "title": f"Golden — {kind} every kind",
                "due_on": s.relative(index * 3 - 10),
                "target": {"kind": "plant", "id": ref(plant)},
            },
        )
    for local, offset in (("far-past", -3650), ("far-future", 3650), ("leap-boundary", None)):
        s.add(
            "schedule",
            local,
            {
                "activity_kind": "follow_up",
                "title": f"Golden — {local}",
                "due_on": s.relative(offset) if offset is not None else "2028-02-29",
                "target": None,
            },
        )
    rescheduled = s.key("schedule", "repot")
    s.add(
        "schedule_update",
        "rescheduled",
        {
            "activity_id": ref(rescheduled),
            "activity_kind": "repot",
            "title": "Golden — repot rescheduled",
            "due_on": s.relative(21),
            "target": {"kind": "plant", "id": ref(plant)},
            "expected_version": 1,
        },
        record="op",
    )
    s.add(
        "schedule_complete",
        "rescheduled-done",
        {"activity_id": ref(rescheduled), "expected_version": 2},
        record="op",
    )
    s.add(
        "refused",
        "stale-version",
        {
            "kind": "schedule_cancel",
            "error": "ScheduleError",
            "payload": {"activity_id": ref(rescheduled), "version": 1},
        },
        record="op",
    )
    moved = s.key("schedule", "move")
    s.add(
        "schedule_complete",
        "move-event",
        {
            "activity_id": ref(moved),
            "expected_version": 1,
            "event": {
                "kind": "movement",
                "occurred_on": s.relative(-1),
                "destination_location_id": ref(BASE_BENCH),
            },
        },
        record="op",
    )
    # The work outlives its target: retained reference to a plant no longer active.
    s.add(
        "schedule",
        "on-ended",
        {
            "activity_kind": "inspect",
            "title": "Golden — still planned on an ended plant",
            "due_on": s.relative(4),
            "target": {"kind": "plant", "id": ref(ended)},
        },
    )
    s.add("event", "ended", {"plant_id": ref(ended), "kind": "death", "occurred_on": ago(s, 1)})


@scenario("saved-views-every-surface")
def saved_views_every_surface(s: Scenario) -> None:
    owner = ref("owner:base-reference/owner")
    states: tuple[tuple[str, str, Payload], ...] = (
        ("global_search", "search", {"q": "Golden", "kind": ["plant", "seed_lot"]}),
        ("sowings", "sowings", {"q": "attempt", "lifecycle": "all"}),
        ("stored_material", "stored", {"state": "all", "material": "seed"}),
        ("events", "events", {"q": "", "category": ["status"]}),
        ("history", "history", {"q": "Golden"}),
        ("media", "media", {"q": "photo"}),
        ("botanical_identities", "identities", {"q": "Salvia"}),
        ("suppliers", "suppliers", {"q": "Retired"}),
        ("orders", "orders", {"q": "Golden"}),
        ("locations", "retired-locations", {"state": "retired", "scope": "all"}),
        ("geography", "sites", {"mode": "sites", "q": "fabricated"}),
        ("species_distribution", "distribution", {"q": "Golden", "scope": "all"}),
        ("native_ranges", "ranges", {"scope": "all", "mode": "species", "withRange": True}),
        ("provenance_map", "map", {"seed_lots": True, "plants": False}),
    )
    for surface, local, state in states:
        s.add(
            "saved_view",
            local,
            {
                "owner_id": owner,
                "name": f"Golden view — {local}",
                "surface": surface,
                "state_version": 1,
                "state": state,
            },
        )
    s.add(
        "saved_view",
        "stale-reference",
        {
            "owner_id": owner,
            "name": "Golden view pointing at a retired Location",
            "surface": "stored_material",
            "state_version": 1,
            "state": {
                "state": "all",
                "location_id": ref("location:location-movement-history/former"),
            },
        },
    )
    s.add(
        "saved_view",
        "identity-filter",
        {
            "owner_id": owner,
            "name": "Golden view — one identity " + "é" * 60,
            "surface": "plants",
            "state_version": 1,
            "state": {"lifecycle": "all", "identity_id": ref(catalogue_key(25))},
        },
    )
    s.add(
        "saved_view",
        "longest-name",
        {
            "owner_id": owner,
            "name": "Golden " + "n" * 113,
            "surface": "seed_lots",
            "state_version": 1,
            "state": {"q": "Golden"},
        },
    )


@scenario("boundary-states")
def boundary_states(s: Scenario) -> None:
    identity = ref(catalogue_key(36))
    long_label = "Golden — " + "L" * 246
    text = "Golden boundary ☘ مرحبا 植物 \U0001f331 " * 10
    s.add(
        "identity",
        "longest",
        {
            "scientific_name": "Golden " + "a" * 248,
            "cultivar_name": "b" * 120,
            "common_name": "c" * 160,
        },
    )
    s.add("location", "longest", {"name": "Golden " + "l" * 248, "parent_id": None})
    s.add("supplier", "longest", {"name": "Golden " + "s" * 248, "kind": "other"})
    s.add(
        "seed",
        "longest-label",
        {
            "botanical_identity_id": identity,
            "label": long_label,
            "notes": ("Golden maximum notes. " * 1000)[:20000],
            "quantity": seeds(0),
            "lifecycle": "exhausted",
        },
    )
    for local, quantity, when, fields in (
        ("largest-count", seeds(999999), year(1), {}),
        ("smallest-weight", weight("0.001", "g"), year(9999), {}),
        ("heavy-approximate", weight("999.999", "g", approximate=True), month(2000, 1), {}),
        (
            "leap-day",
            seeds(1),
            day(date(2024, 2, 29)),
            {"expected_viability_until": day(date(2028, 2, 29))},
        ),
        ("anchor-day", seeds(1), day(s.anchor), {"harvest_date": day(s.anchor)}),
        ("year-end", seeds(1), day(date(2025, 12, 31)), {"harvest_date": day(date(2025, 1, 1))}),
        ("unicode", seeds(1), None, {"notes": text}),
    ):
        s.add(
            "seed",
            local,
            {
                "botanical_identity_id": identity,
                "label": f"Golden — {local}",
                "quantity": quantity,
                "acquisition_date": when,
                **fields,
            },
        )
    lot = s.key("seed", "largest-count")
    for local, sowing_fields in (
        ("hottest", {"temperature_min_c": "-273", "temperature_max_c": "99.9"}),
        ("equal-temperature", {"temperature_min_c": "21", "temperature_max_c": "21"}),
        ("all-germinated", {"quantity": seeds(3), "germinated_count": 3}),
        ("more-than-sown", {"quantity": seeds(3, approximate=True), "germinated_count": 4}),
    ):
        s.add(
            "sowing",
            local,
            {"seed_lot_id": ref(lot), "label": f"Golden — sowing {local}", **sowing_fields},
        )
    s.add(
        "plant",
        "longest-label",
        {"botanical_identity_id": identity, "label": long_label, "direct_origin_kind": "unknown"},
    )
    s.add(
        "group",
        "largest",
        {
            "botanical_identity_id": identity,
            "label": "Golden — largest group",
            "direct_origin_kind": "unknown",
            "quantity": group_count(1000000),
        },
    )
    # Refused rather than stored: these states are unreachable, and must stay so.
    for local, kind, error, payload in (
        (
            "duplicate-identity",
            "identity",
            "BotanicalIdentityConflictError",
            {"scientific_name": CATALOGUE[36][0]},
        ),
        (
            "unknown-supplier",
            "seed",
            "SeedLotReferenceNotFoundError",
            {
                "botanical_identity_id": identity,
                "label": "Golden — refused unknown supplier",
                "supplier_id": "00000000-0000-7000-8000-000000000000",
            },
        ),
        (
            "impossible-date",
            "seed",
            "ValidationError",
            {
                "botanical_identity_id": identity,
                "label": "Golden — refused impossible date",
                "acquisition_date": {"precision": "day", "year": 2025, "month": 2, "day": 30},
            },
        ),
    ):
        s.add("refused", local, {"kind": kind, "error": error, "payload": payload}, record="op")


COLLECTION_STAGES = (
    ("Golden mix greenhouse", ("north bench", "south bench", "propagator", "misting tent")),
    ("Golden mix indoors", ("windowsill", "terrarium", "seed fridge", "seed box")),
    ("Golden mix garden", ("raised bed", "orchard row", "herb spiral", "cold frame")),
)


@scenario("comprehensive-volume-mix")
def comprehensive_volume_mix(s: Scenario) -> None:
    """A collection's whole life, weighted like a real one: failures and endings are common."""
    rng = s.random
    suppliers: list[str] = []
    for index, kind in enumerate(
        (
            "seller",
            "seller",
            "seller",
            "nursery",
            "nursery",
            "exchange",
            "person",
            "supermarket",
            "other",
        )
    ):
        suppliers.append(
            s.add("supplier", f"s{index}", {"name": f"Golden mix supplier {index}", "kind": kind})
        )
    orders: list[tuple[str, str]] = []
    for index in range(36):
        supplier = suppliers[index % 5]
        orders.append(
            (
                s.add(
                    "order",
                    f"o{index:02d}",
                    {
                        "supplier_id": ref(supplier),
                        "ordered_on": ago(s, 30 + index * 25),
                        "order_reference": f"Golden mix order {index:02d}",
                        "total_price": f"{rng.randrange(300, 9000) / 100:.2f}",
                        "currency": "EUR",
                    },
                ),
                supplier,
            )
        )
    sites = [
        s.add(
            "site",
            f"site-{index}",
            {
                "name": f"Golden mix site {index} (fabricated)",
                "geographic_place_id": ref(f"country:{code}"),
                "latitude": f"{rng.uniform(-55, 65):.6f}" if index % 4 else None,
                "longitude": f"{rng.uniform(-170, 170):.6f}" if index % 4 else None,
            },
        )
        for index, code in enumerate(COUNTRIES)
    ]
    benches: list[str] = []
    for index, (name, leaves) in enumerate(COLLECTION_STAGES):
        parent = s.add("location", f"area-{index}", {"name": name, "parent_id": None})
        for leaf in leaves:
            local = leaf.replace(" ", "-")
            benches.append(
                s.add("location", local, {"name": f"Golden mix {leaf}", "parent_id": ref(parent)})
            )
    assets: list[str] = []
    for index in range(18):
        fields: Payload = (
            {"width": 640, "height": 480, "format": "JPEG", "texture": 100 + index}
            if index % 3 == 0
            else {"width": 160, "height": 120}
        )
        colour = [rng.randrange(40, 230) for _ in range(3)]
        assets.append(
            s.add(
                "generated_asset",
                f"a{index:02d}",
                {"title": f"Golden mix image {index:02d}", "colour": colour, **fields},
                record="asset",
            )
        )
    identities = [catalogue_key(i) for i in range(len(CATALOGUE))] + [
        cultivar_key(i) for i in range(len(CULTIVARS))
    ]

    def bench() -> dict[str, str]:
        return ref(rng.choice(benches))

    def life(key: str, target: str, local: str, identity: str, born: int) -> None:
        """Events, optional harvest and ending of one Plant or PlantGroup, oldest first."""
        offset = born
        for number in range(rng.choice((0, 1, 1, 2, 2, 3, 4, 5))):
            offset = max(1, offset - rng.randrange(5, 60))
            kind = rng.choice(
                (
                    "observation",
                    "observation",
                    "repotting",
                    "movement",
                    "flowering",
                    "fruiting",
                    "pruning",
                    "treatment",
                )
            )
            payload: Payload = {"kind": kind, "occurred_on": ago(s, offset)}
            if kind == "movement":
                payload["destination_location_id"] = bench()
            if rng.random() < 0.25:
                payload["notes"] = NOTE
            if target == "plant":
                s.add("event", f"{local}-e{number}", {"plant_id": ref(key), **payload})
            else:
                s.add(
                    "group_event",
                    f"{local}-e{number}",
                    {"plant_group_id": ref(key), **payload},
                    record="event",
                )
        if rng.random() < 0.18:
            source = {"plant_id": ref(key)} if target == "plant" else {"plant_group_id": ref(key)}
            material = rng.choice(("seed", "seed", "fruit", "leaf", "flower"))
            amount = rng.randrange(5, 200)
            harvest = s.add(
                "harvest",
                local,
                {
                    **source,
                    "label": f"Golden mix harvest {local}",
                    "occurred_on": ago(s, max(1, offset - 1)),
                    "items": [{"material_kind": material, "quantity": items(amount)}],
                },
            )
            if rng.random() < 0.7:
                stored = s.add(
                    "inventory",
                    local,
                    {
                        "item_id": ref("item:" + harvest),
                        "state": "active",
                        "quantity": items(amount),
                        "location_id": bench(),
                    },
                )
                roll = rng.random()
                if roll < 0.25:
                    s.add(
                        "disposition",
                        local,
                        {
                            "inventory_id": ref(stored),
                            "kind": rng.choice(("consumed", "processed", "gifted", "discarded")),
                            "mode": "use_all",
                        },
                    )
                elif roll < 0.45 and material == "seed":
                    s.add(
                        "conversion",
                        local,
                        {
                            "inventory_id": ref(stored),
                            "mode": "partial",
                            "label": f"Golden mix saved seed {local}",
                            "quantity": seeds(max(1, amount // 2)),
                        },
                    )
        ending = rng.random()
        if ending < 0.12:
            kind = rng.choice(("death", "death", "loss", "discarded"))
            if target == "plant":
                s.add("event", f"{local}-end", {"plant_id": ref(key), "kind": kind})
            else:
                s.add(
                    "group_event",
                    f"{local}-end",
                    {"plant_group_id": ref(key), "kind": kind},
                    record="event",
                )
        elif ending < 0.16:
            s.add(
                "transfer",
                f"{local}-end",
                {
                    "target_type": target,
                    "target_id": ref(key),
                    "recipient": "Golden fictitious friend",
                },
                record="event",
            )
        elif ending < 0.34:
            task = s.add(
                "schedule",
                local,
                {
                    "activity_kind": rng.choice(
                        ("water", "repot", "inspect", "fertilize", "follow_up")
                    ),
                    "title": f"Golden mix task {local}",
                    "due_on": s.relative(rng.randrange(-30, 90)),
                    "target": {"kind": target, "id": ref(key)},
                },
            )
            outcome = rng.random()
            if outcome < 0.35:
                s.add(
                    "schedule_complete",
                    f"{local}-done",
                    {"activity_id": ref(task), "expected_version": 1},
                    record="op",
                )
            elif outcome < 0.45:
                s.add(
                    "schedule_cancel",
                    f"{local}-off",
                    {"activity_id": ref(task), "version": 1},
                    record="op",
                )
        if rng.random() < 0.08:
            s.add(
                "link",
                local,
                {
                    "asset_id": ref(rng.choice(assets)),
                    "target_type": target,
                    "target_id": ref(key),
                    "caption": None,
                },
            )

    for index in range(s.volume):
        local = f"j{index:04d}"
        # Squared, so a few favourite species recur while the long tail stays sparse.
        identity = identities[int(len(identities) * rng.random() ** 2)]
        pathway = rng.random()
        if pathway < 0.17:
            target = "plant" if rng.random() < 0.75 else "plant_group"
            common: Payload = {
                "botanical_identity_id": ref(identity),
                "label": f"Golden mix direct {local}",
                "direct_origin_kind": rng.choice(("purchased", "gift_exchange", "unknown")),
                "location_id": bench(),
                "collection_entry_date": ago(s, rng.randrange(100, 900)),
            }
            if common["direct_origin_kind"] == "purchased":
                common["supplier_id"] = ref(rng.choice(suppliers))
            if target == "plant":
                key = s.add("plant", local, common)
            else:
                common["quantity"] = group_count(
                    rng.randrange(2, 30), approximate=rng.random() < 0.3
                )
                key = s.add("group", local, common)
            life(key, target, local, identity, 90)
            continue
        source = rng.random()
        born = rng.randrange(120, 1000)
        lot: Payload = {
            "botanical_identity_id": ref(identity),
            "label": f"Golden mix packet {local}",
            "acquisition_date": ago(s, born),
        }
        if source < 0.5:
            order, supplier = rng.choice(orders)
            lot |= {
                "source_kind": "purchased",
                "order_id": ref(order),
                "supplier_id": ref(supplier),
            }
        elif source < 0.62:
            lot |= {"source_kind": "purchased", "supplier_id": ref(rng.choice(suppliers))}
        elif source < 0.74:
            lot |= {"source_kind": "self_collected", "provenance_site_id": ref(rng.choice(sites))}
        elif source < 0.88:
            lot |= {"source_kind": "gift_exchange", "supplier_id": ref(suppliers[5 + index % 2])}
        elif source < 0.95:
            lot |= {"source_kind": "purchased_fruit"}
        else:
            lot |= {"source_kind": "unknown"}
        store = rng.random()
        remaining = rng.randrange(20, 400)
        if store < 0.72:
            lot["quantity"] = seeds(remaining)
        elif store < 0.82:
            lot["quantity"] = seeds(remaining, approximate=True)
            remaining = 0
        elif store < 0.92:
            lot["quantity"] = weight(f"{rng.randrange(1, 900) / 100:.2f}", "g")
            remaining = 0
        else:
            remaining = 0
        if rng.random() < 0.5:
            lot["location_id"] = bench()
        if rng.random() < 0.3:
            lot["expected_viability_until"] = year(s.anchor.year + rng.randrange(-3, 6))
        if pathway < 0.3:
            ending = rng.random()
            if ending < 0.15:
                lot |= {"quantity": seeds(0), "lifecycle": "exhausted"}
            elif ending < 0.25:
                lot["lifecycle"] = "discarded"
            elif ending < 0.3:
                lot["lifecycle"] = "lost"
            s.add("seed", local, lot)
            continue
        packet = s.add("seed", local, lot)
        for attempt in range(rng.choice((1, 1, 1, 2, 2, 3))):
            sown = max(40, born - rng.randrange(10, 80) - attempt * 30)
            sowing_local = f"{local}-s{attempt}"
            outcome = rng.random()
            take = min(remaining, rng.randrange(5, 40))
            attempted: Payload = {
                "label": f"Golden mix sowing {sowing_local}",
                "sowing_date": ago(s, sown),
                "location_id": bench(),
            }
            if rng.random() < 0.3:
                attempted |= {
                    "substrate": "Golden seed compost",
                    "method_container": "Golden cell tray",
                }
            if outcome < 0.22:
                attempted |= {"lifecycle": "failed", "germinated_count": 0}
            elif outcome < 0.32:
                attempted["lifecycle"] = "abandoned"
            germinated = 0
            if outcome >= 0.42:
                germinated = rng.randrange(1, max(2, take or 12))
                attempted["germinated_count"] = germinated
            if take:
                remaining -= take
                sowing = s.add(
                    "sow_transition",
                    sowing_local,
                    {
                        "seed_lot_id": ref(packet),
                        "sowing": {**attempted, "quantity": seeds(take)},
                        "source_adjustment": {"mode": "partial"},
                    },
                    record="sowing",
                )
            else:
                sowing = s.add("sowing", sowing_local, {"seed_lot_id": ref(packet), **attempted})
            if germinated:
                seen = 0
                for point in range(rng.choice((0, 1, 2, 3))):
                    count = rng.randrange(0, germinated - seen + 1)
                    seen += count
                    s.add(
                        "observation",
                        f"{sowing_local}-o{point}",
                        {
                            "sowing_id": ref(sowing),
                            "observed_on": s.relative(-sown + 7 + point * 7),
                            "newly_germinated_count": count,
                        },
                    )
                derived = rng.random()
                if derived < 0.45:
                    plant = s.add(
                        "plant_from_sowing",
                        sowing_local,
                        {
                            "sowing_id": ref(sowing),
                            "resulting_sowing_lifecycle": "completed"
                            if rng.random() < 0.5
                            else "active",
                            "plant": {
                                "botanical_identity_id": ref(identity),
                                "label": f"Golden mix plant {sowing_local}",
                                "location_id": bench(),
                            },
                        },
                        record="plant",
                    )
                    life(plant, "plant", sowing_local, identity, max(30, sown - 30))
                elif derived < 0.8:
                    tray = s.add(
                        "group_from_sowing",
                        sowing_local,
                        {
                            "sowing_id": ref(sowing),
                            "resulting_sowing_lifecycle": "completed",
                            "plant_group": {
                                "botanical_identity_id": ref(identity),
                                "label": f"Golden mix tray {sowing_local}",
                                "quantity": group_count(germinated),
                                "location_id": bench(),
                            },
                        },
                        record="group",
                    )
                    life(tray, "plant_group", sowing_local, identity, max(30, sown - 30))
    for index in (7, 8):
        s.add("retire_supplier", f"s{index}", {"supplier_id": ref(suppliers[index])}, record="op")


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


def runnable_profiles(manifest: dict[str, Any], entry: dict[str, Any]) -> list[str]:
    """Only an implemented scenario in an implemented profile can generate today."""
    if entry["status"] != "implemented":
        return []
    return [
        name
        for name, profile in manifest["profiles"].items()
        if profile["status"] == "implemented" and name in entry["profiles"]
    ]


def coverage_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# Golden dataset scenario coverage",
        "",
        "Generated by `python3 scripts/golden_plan.py coverage` from `scenarios.json`. Do not edit.",
        "",
        "## Profiles",
        "",
        "| Profile | Status | Executable now | Purpose |",
        "| --- | --- | --- | --- |",
    ]
    for name, profile in manifest["profiles"].items():
        executable = "yes" if profile["status"] == "implemented" else "no: refuses to generate"
        lines.append(f"| {name} | {profile['status']} | {executable} | {profile['purpose']} |")
    lines += [
        "",
        "## Scenarios",
        "",
        "| Domain | Scenario | Status | Runnable now | Planned for | Covered states |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for entry in manifest["scenarios"]:
        runnable = runnable_profiles(manifest, entry)
        planned = [name for name in entry["profiles"] if name not in runnable]
        lines.append(
            f"| {entry['domain']} | `{entry['id']}` | {entry['status']} | "
            f"{', '.join(runnable) or '—'} | {', '.join(planned) or '—'} | "
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
