"""Bounded, explicit CSV exchange. Preview performs SELECTs and schema validation only."""

import csv
import io
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import BotanicalIdentityCreate
from florabase.botanical_identities.service import create_botanical_identity
from florabase.geographic_places.model import GeographicPlace
from florabase.geographic_places.service import display_path as place_path
from florabase.locations.model import Location
from florabase.locations.schemas import LocationCreate, LocationUsageScope
from florabase.locations.service import create_location
from florabase.locations.service import display_path as location_path
from florabase.plants.model import (
    DirectOriginKind,
    Plant,
    PlantGroup,
    PlantGroupLifecycle,
    PlantLifecycle,
)
from florabase.plants.schemas import PlantCreate, PlantGroupCreate
from florabase.plants.service import create_plant, create_plant_group
from florabase.provenance_sites.model import ProvenanceSite
from florabase.seed_lots.model import (
    SeedLot,
    SeedLotLifecycle,
    SeedLotSourceKind,
    SeedQuantityKind,
    SeedWeightUnit,
)
from florabase.seed_lots.schemas import SeedLotCreate
from florabase.seed_lots.service import create_seed_lot
from florabase.suppliers.model import Supplier, SupplierKind
from florabase.suppliers.schemas import SupplierCreate, SupplierUpdate
from florabase.suppliers.service import create_supplier, update_supplier

MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 2000
RecordType = Literal[
    "botanical-identities", "suppliers", "locations", "seed-lots", "plants", "plant-groups"
]
COLUMNS: dict[str, tuple[str, ...]] = {
    "botanical-identities": ("record_ref", "scientific_name", "cultivar_name", "common_name"),
    "suppliers": ("record_ref", "name", "kind", "website", "email", "phone", "notes"),
    "locations": ("record_ref", "import_key", "name", "parent_ref", "usage_scopes"),
    "seed-lots": (
        "record_ref",
        "identity_ref",
        "label",
        "source_kind",
        "source_detail",
        "producer_plant_ref",
        "producer_plant_group_ref",
        "supplier_ref",
        "geographic_place_ref",
        "provenance_site_ref",
        "acquisition_date",
        "harvest_date",
        "quantity_kind",
        "quantity_value",
        "quantity_unit",
        "quantity_certainty",
        "expected_viability_until",
        "location_ref",
        "lifecycle",
        "notes",
    ),
    "plants": (
        "record_ref",
        "identity_ref",
        "label",
        "direct_origin_kind",
        "direct_origin_detail",
        "supplier_ref",
        "geographic_place_ref",
        "provenance_site_ref",
        "collection_entry_date",
        "location_ref",
        "lifecycle",
        "notes",
    ),
    "plant-groups": (
        "record_ref",
        "identity_ref",
        "label",
        "direct_origin_kind",
        "direct_origin_detail",
        "supplier_ref",
        "geographic_place_ref",
        "provenance_site_ref",
        "collection_entry_date",
        "location_ref",
        "quantity_value",
        "quantity_certainty",
        "lifecycle",
        "notes",
    ),
}
IMPORT_COLUMNS: dict[str, tuple[str, ...]] = {
    kind: tuple(column for column in columns if column != "record_ref")
    for kind, columns in COLUMNS.items()
}


class QuantityCertainty(StrEnum):
    EXACT = "exact"
    APPROXIMATE = "approximate"
    UNKNOWN = "unknown"


ENUMS: dict[str, type[StrEnum]] = {
    "kind": SupplierKind,
    "source_kind": SeedLotSourceKind,
    "quantity_kind": SeedQuantityKind,
    "quantity_unit": SeedWeightUnit,
    "lifecycle:seed-lots": SeedLotLifecycle,
    "lifecycle:plants": PlantLifecycle,
    "lifecycle:plant-groups": PlantGroupLifecycle,
    "direct_origin_kind": DirectOriginKind,
    "quantity_certainty": QuantityCertainty,
}


def enum_values(kind: str, key: str) -> list[str] | None:
    enum_type = ENUMS.get(f"{key}:{kind}") or ENUMS.get(key)
    if enum_type is None:
        return None
    values = [member.value for member in enum_type]
    if key == "lifecycle" and kind == "plants":
        return [value for value in values if value not in {"reversed", "reintegrated"}]
    if key == "lifecycle" and kind == "plant-groups":
        return [value for value in values if value != "reversed"]
    return values


EXPORT_EXTRA_COLUMNS: dict[str, tuple[str, ...]] = {
    "botanical-identities": (),
    "suppliers": (),
    "locations": ("parent_path",),
    "seed-lots": (
        "identity_label",
        "supplier_name",
        "geographic_place_path",
        "provenance_site_name",
        "location_path",
        "producer_plant_label",
        "producer_plant_group_label",
    ),
    "plants": (
        "identity_label",
        "supplier_name",
        "geographic_place_path",
        "provenance_site_name",
        "location_path",
    ),
    "plant-groups": (
        "identity_label",
        "supplier_name",
        "geographic_place_path",
        "provenance_site_name",
        "location_path",
    ),
}

EXAMPLE_ROWS: dict[str, list[dict[str, str]]] = {
    "botanical-identities": [
        {"scientific_name": "Acmella oleracea", "common_name": "Paracress"},
        {"scientific_name": "Allium fistulosum"},
    ],
    "suppliers": [
        {"name": "Cercatoridisemì", "kind": "nursery", "website": "https://example.org"},
    ],
    "locations": [
        {"import_key": "cabinet", "name": "Seed cabinet", "usage_scopes": "plants|seed_lots"},
        {
            "import_key": "drawer",
            "name": "Drawer 3",
            "parent_ref": "@cabinet",
            "usage_scopes": "seed_lots",
        },
    ],
    "seed-lots": [
        {
            "identity_ref": "Acmella oleracea",
            "label": "Paracress, 2024",
            "source_kind": "gift_exchange",
            "supplier_ref": "Cercatoridisemì",
            "acquisition_date": "2024-05",
            "quantity_kind": "seed_count",
            "quantity_value": "12",
            "quantity_certainty": "approximate",
            "location_ref": "Seed cabinet → Drawer 3",
        },
        {
            "identity_ref": "Allium fistulosum",
            "label": "Spring onion",
            "source_kind": "unknown",
            "quantity_certainty": "unknown",
        },
    ],
    "plants": [
        {
            "identity_ref": "Acmella oleracea",
            "label": "Paracress specimen",
            "direct_origin_kind": "gift_exchange",
            "collection_entry_date": "2024",
            "location_ref": "Seed cabinet",
        },
    ],
    "plant-groups": [
        {
            "identity_ref": "Allium fistulosum",
            "label": "Spring onion clump",
            "direct_origin_kind": "unknown",
            "collection_entry_date": "2024-05",
            "quantity_value": "8",
            "quantity_certainty": "approximate",
            "location_ref": "Seed cabinet",
        },
    ],
}

GUIDE_EXAMPLES: dict[str, str] = {
    "cultivar_name": "Borlotto",
    "email": "seeds@example.org",
    "phone": "+39 055 123 4567",
    "notes": "Stored in cool, dry conditions",
    "source_detail": "Local seed swap",
    "producer_plant_ref": "01900000-0000-7000-8000-000000000001",
    "producer_plant_group_ref": "01900000-0000-7000-8000-000000000002",
    "geographic_place_ref": "Europe → Italy",
    "provenance_site_ref": "North meadow",
    "harvest_date": "2024-07-12",
    "quantity_unit": "g",
    "expected_viability_until": "2027",
    "direct_origin_detail": "Gift from neighbour",
    "lifecycle": "active",
    "supplier_ref": "Cercatoridisemì",
}

FIELD_INFO: dict[str, tuple[str, str, str]] = {
    "scientific_name": (
        "Scientific taxon name",
        "Taxon name, up to 255 characters",
        "The name and cultivar together identify a botanical identity.",
    ),
    "cultivar_name": (
        "Optional cultivar qualifier",
        "Cultivar name, up to 120 characters",
        "Leave blank when no cultivar is known.",
    ),
    "common_name": (
        "Common or familiar name",
        "Text, up to 160 characters",
        "A matching existing identity is not overwritten.",
    ),
    "name": (
        "Name of this Supplier or physical Location",
        "Text, up to 255 characters",
        "Exact names are used to find existing candidates.",
    ),
    "kind": (
        "Type of Supplier or acquisition party",
        "seller, nursery, supermarket, person, exchange, other",
        "Capitalization and surrounding spaces are normalized.",
    ),
    "website": (
        "Supplier website",
        "HTTP or HTTPS URL",
        "Blank leaves an existing Supplier website unchanged on Update existing.",
    ),
    "email": (
        "Supplier contact email",
        "Email address",
        "Blank leaves an existing value unchanged.",
    ),
    "phone": (
        "Supplier contact phone",
        "Text, up to 120 characters",
        "Blank leaves an existing value unchanged.",
    ),
    "notes": (
        "Operator notes",
        "Text, up to 20,000 characters; quoted newlines allowed",
        "Blank leaves an existing Supplier note unchanged on Update existing.",
    ),
    "import_key": (
        "Local key for this Location row",
        "1-64 letters, digits, dots, underscores or hyphens",
        "Only used within this CSV; it is not a permanent Florabase identifier.",
    ),
    "parent_ref": (
        "Parent physical Location",
        "@local_key, exact existing full path, or optional existing UUID",
        "A child can precede its parent. Missing parents and cycles block import.",
    ),
    "usage_scopes": (
        "Kinds of collection records this Location can hold",
        "plants, sowings, seed_lots; separate multiple with |",
        "Scopes do not inherit from parents.",
    ),
    "identity_ref": (
        "Existing botanical identity",
        "Exact scientific name or name|cultivar; optional UUID",
        "One exact match resolves in Preview; several require a choice; none is unresolved.",
    ),
    "label": (
        "Operator label for the collection record",
        "Text, up to 255 characters",
        "Optional; this is not the botanical identity.",
    ),
    "source_kind": (
        "How a Seed lot entered the collection",
        "See accepted source kinds below",
        "Blank means unknown; capitalization and spaces are normalized.",
    ),
    "source_detail": (
        "More detail for an Other source",
        "Text, up to 255 characters",
        "Only valid when source_kind is other.",
    ),
    "producer_plant_ref": (
        "Existing producer Plant for a collection-produced Seed lot",
        "Optional existing Plant UUID",
        "Use only when source_kind is collection_produced; no safe unique Plant label is assumed.",
    ),
    "producer_plant_group_ref": (
        "Existing producer PlantGroup for a collection-produced Seed lot",
        "Optional existing PlantGroup UUID",
        "Mutually exclusive with producer_plant_ref.",
    ),
    "supplier_ref": (
        "Supplier acquisition/source party",
        "Exact Supplier name; optional existing UUID",
        "One match resolves in Preview; multiple candidates require a choice.",
    ),
    "geographic_place_ref": (
        "Geographic origin of the material",
        "Exact GeographicPlace full path; optional existing UUID",
        "This is not the physical collection Location; ambiguous paths require a choice.",
    ),
    "provenance_site_ref": (
        "Precise collection origin site",
        "Exact ProvenanceSite name; optional existing UUID",
        "This is not a Supplier or physical Location; ambiguous names require a choice.",
    ),
    "location_ref": (
        "Where the item is physically stored or grown",
        "Exact Location full path; optional existing UUID",
        "The Location must support this record type; ambiguous paths require a choice.",
    ),
    "acquisition_date": (
        "When the Seed lot was acquired",
        "YYYY, YYYY-MM, or YYYY-MM-DD",
        "Known precision is preserved; missing month or day is never invented.",
    ),
    "harvest_date": (
        "When seed was harvested",
        "YYYY, YYYY-MM, or YYYY-MM-DD",
        "Known precision is preserved.",
    ),
    "expected_viability_until": (
        "Expected viability date",
        "YYYY, YYYY-MM, or YYYY-MM-DD",
        "Known precision is preserved.",
    ),
    "collection_entry_date": (
        "When a Plant or PlantGroup entered the collection",
        "YYYY, YYYY-MM, or YYYY-MM-DD",
        "Known precision is preserved.",
    ),
    "quantity_kind": (
        "Seed quantity measurement type",
        "seed_count or weight",
        "Leave blank with unknown quantity.",
    ),
    "quantity_value": (
        "Known Seed count, weight, or PlantGroup count",
        "Whole count or decimal weight; PlantGroup is whole count",
        "Blank with unknown certainty; zero follows current lifecycle rules.",
    ),
    "quantity_unit": (
        "Seed weight unit",
        "g or mg for weight",
        "Blank for seed_count or unknown quantity.",
    ),
    "quantity_certainty": (
        "How certain the quantity is",
        "exact, approximate, or unknown",
        "Unknown has no value; approximate retains the estimate rather than inventing precision.",
    ),
    "direct_origin_kind": (
        "Direct origin of a Plant or PlantGroup",
        "purchased, gift_exchange, collection_produced, other, unknown",
        "Sowing-origin records require their operational workflow and are excluded.",
    ),
    "direct_origin_detail": (
        "More detail for Other direct origin",
        "Text, up to 255 characters",
        "Only valid when direct_origin_kind is other.",
    ),
    "lifecycle": (
        "Current collection lifecycle state",
        "See type-specific allowed values",
        "Blank means active; operation-only states cannot be imported.",
    ),
}

REQUIRED_FIELDS: dict[str, set[str]] = {
    "botanical-identities": {"scientific_name"},
    "suppliers": {"name", "kind"},
    "locations": {"name", "usage_scopes"},
    "seed-lots": {"identity_ref"},
    "plants": {"identity_ref"},
    "plant-groups": {"identity_ref"},
}


def field_guide(kind: str) -> list[dict[str, object]]:
    if kind not in IMPORT_COLUMNS:
        raise CsvFormatError("Unsupported record type")
    result = []
    for field_name in IMPORT_COLUMNS[kind]:
        meaning, accepted, notes = FIELD_INFO[field_name]
        if field_name == "name":
            meaning = (
                "Name of this Supplier" if kind == "suppliers" else "Name of this physical Location"
            )
        if field_name == "notes" and kind != "suppliers":
            notes = "Optional notes about this record; blank means no note."
        if field_name == "quantity_value" and kind == "plant-groups":
            meaning = "Number of individuals in this managed Plant group"
            accepted = "Nonnegative whole count"
        if field_name in {"producer_plant_ref", "producer_plant_group_ref"}:
            notes += " The UUID example shows the format and must identify an existing producer."
        values = enum_values(kind, field_name)
        if values is not None:
            accepted = ", ".join(values)
        example = next(
            (row[field_name] for row in EXAMPLE_ROWS[kind] if row.get(field_name)),
            GUIDE_EXAMPLES.get(field_name, "(leave blank)"),
        )
        result.append(
            {
                "field": field_name,
                "meaning": meaning,
                "required": field_name in REQUIRED_FIELDS[kind],
                "accepted": accepted,
                "example": example,
                "notes": notes,
            }
        )
    return result


def example_csv(kind: str) -> str:
    if kind not in IMPORT_COLUMNS:
        raise CsvFormatError("Unsupported record type")
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=IMPORT_COLUMNS[kind], lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(EXAMPLE_ROWS[kind])
    return output.getvalue()


class CsvFormatError(ValueError):
    pass


@dataclass
class DecisionOption:
    key: str
    action: str
    candidate_id: str
    label: str
    details: str
    snapshot: str
    changes: list[dict[str, str]] = field(default_factory=list)
    payload: dict[str, Any] | None = None

    def signed_content(self) -> str:
        return json.dumps(
            [
                self.key,
                self.action,
                self.candidate_id,
                self.label,
                self.details,
                self.snapshot,
                self.changes,
            ],
            ensure_ascii=False,
            separators=(",", ":"),
        )

    def public(self) -> dict[str, object]:
        return {
            "key": self.key,
            "action": self.action,
            "candidate_id": self.candidate_id,
            "label": self.label,
            "details": self.details,
            "changes": self.changes,
        }


@dataclass
class PreviewRow:
    row_number: int
    record: str
    outcome: str = "ready"
    messages: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    payload: dict[str, Any] | None = None
    parent_key: str | None = None
    options: list[DecisionOption] = field(default_factory=list)
    normalized: list[str] = field(default_factory=list)
    selected_action: DecisionOption | None = None
    source: dict[str, str] | None = None
    hard_blocker: bool = False

    def issue(self, outcome: str, message: str, *, resolvable: bool = False) -> None:
        order = {
            "ready": 0,
            "already_exists": 0,
            "needs_choice": 1,
            "unresolved_reference": 1,
            "ambiguous_reference": 2,
            "conflict": 3,
            "invalid": 4,
        }
        if order[outcome] > order[self.outcome]:
            self.outcome = outcome
        self.messages.append(message)
        if outcome not in {"needs_choice", "ready"} and not resolvable:
            self.hard_blocker = True

    def public(self) -> dict[str, object]:
        return {
            "row_number": self.row_number,
            "record": self.record,
            "outcome": self.outcome,
            "messages": self.messages,
            "references": self.references,
            "normalized": self.normalized,
            "options": [option.public() for option in self.options],
            "hard_blocker": self.hard_blocker,
        }


def parse_csv(data: bytes, kind: str) -> list[tuple[int, dict[str, str]]]:
    if kind not in COLUMNS:
        raise CsvFormatError("Unsupported record type")
    if not data or len(data) > MAX_BYTES:
        raise CsvFormatError("CSV must be nonempty and at most 2 MiB")
    try:
        content = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise CsvFormatError("CSV must be UTF-8") from error
    try:
        reader = csv.reader(io.StringIO(content, newline=""), strict=True)
        raw_header = next(reader)
        header = [name.strip().lower() for name in raw_header]
        if len(header) != len(set(header)):
            raise CsvFormatError("Duplicate CSV headers")
        missing = set(IMPORT_COLUMNS[kind]) - set(header)
        unknown = set(header) - set(COLUMNS[kind])
        if missing or unknown:
            raise CsvFormatError(
                f"CSV headers differ: missing {', '.join(sorted(missing)) or 'none'}; "
                f"unknown {', '.join(sorted(unknown)) or 'none'}"
            )
        rows: list[tuple[int, dict[str, str]]] = []
        for record_number, cells in enumerate(reader, start=2):
            if len(cells) == 0 or all(not cell.strip() for cell in cells):
                continue
            if len(cells) != len(header):
                raise CsvFormatError(
                    f"CSV record {record_number} has {len(cells)} fields; expected {len(header)}"
                )
            source = dict(zip(header, cells, strict=True))
            source.setdefault("record_ref", "")
            rows.append((record_number, source))
            if len(rows) > MAX_ROWS:
                raise CsvFormatError(f"CSV exceeds {MAX_ROWS} nonblank rows")
    except (csv.Error, StopIteration) as error:
        raise CsvFormatError(f"Malformed CSV: {error}") from error
    if not rows:
        raise CsvFormatError("CSV contains no data rows")
    return rows


def optional(value: str) -> str | None:
    return value if value != "" else None


def normalize_source(kind: str, source: dict[str, str], row: PreviewRow) -> dict[str, str]:
    normalized = dict(source)
    for key, value in source.items():
        if (
            key.endswith(("_ref", "_date"))
            or key in {"import_key", "parent_ref", "quantity_value"}
            or key in {"expected_viability_until", "collection_entry_date"}
        ):
            cleaned = value.strip()
            if cleaned != value:
                normalized[key] = cleaned
                row.normalized.append(f"{key}: surrounding spaces removed")
        accepted_values = enum_values(kind, key)
        if accepted_values is None:
            continue
        if not value.strip():
            normalized[key] = ""
            if value:
                row.normalized.append(f"{key.replace('_', ' ')}: whitespace treated as blank")
            continue
        matching = next(
            (item for item in accepted_values if item.casefold() == value.strip().casefold()),
            None,
        )
        if matching is None:
            accepted = ", ".join(accepted_values)
            raise ValueError(
                f'{key.replace("_", " ").capitalize()} "{value[:80]}" is not recognized. '
                f"Accepted values: {accepted}"
            )
        normalized[key] = matching
        if matching != value:
            row.normalized.append(f"{key.replace('_', ' ')}: {value!r} → {matching}")
    if "usage_scopes" in source and not source["usage_scopes"].strip():
        normalized["usage_scopes"] = ""
    if "usage_scopes" in source and source["usage_scopes"].strip():
        scopes = []
        for part in source["usage_scopes"].split("|"):
            value = part.strip()
            match = next(
                (
                    scope.value
                    for scope in LocationUsageScope
                    if scope.value.casefold() == value.casefold()
                ),
                None,
            )
            if match is None:
                accepted = ", ".join(scope.value for scope in LocationUsageScope)
                raise ValueError(
                    f'Location usage scope "{value[:80]}" is not recognized. '
                    f"Accepted values: {accepted}"
                )
            scopes.append(match)
        normalized["usage_scopes"] = "|".join(scopes)
        if normalized["usage_scopes"] != source["usage_scopes"]:
            row.normalized.append(
                f"usage scopes: {source['usage_scopes']!r} → {normalized['usage_scopes']}"
            )
    return normalized


def partial_date(value: str) -> dict[str, object] | None:
    if not value:
        return None
    if not re.fullmatch(r"[0-9]{4}(-[0-9]{2})?(-[0-9]{2})?", value):
        raise ValueError("Date must be YYYY, YYYY-MM, or YYYY-MM-DD")
    parts = [int(part) for part in value.split("-")]
    if len(parts) == 3:
        date(*parts)
    return {
        "precision": ("year", "month", "day")[len(parts) - 1],
        "year": parts[0],
        "month": parts[1] if len(parts) > 1 else None,
        "day": parts[2] if len(parts) > 2 else None,
    }


def quantity(row: dict[str, str], *, group: bool = False) -> dict[str, object] | None:
    value = row["quantity_value"]
    certainty = row["quantity_certainty"]
    if not value and certainty in {"", "unknown"}:
        if not group and (row["quantity_kind"] or row["quantity_unit"]):
            raise ValueError("Unknown quantity cannot have kind or unit")
        return None
    if not value or certainty not in {"exact", "approximate"}:
        raise ValueError("Quantity needs a value and exact or approximate certainty")
    if group:
        if not re.fullmatch(r"[0-9]+", value):
            raise ValueError("PlantGroup quantity must be a whole number")
        return {"value": int(value), "is_approximate": certainty == "approximate"}
    return {
        "kind": row["quantity_kind"],
        "value": value,
        "unit": optional(row["quantity_unit"]),
        "is_approximate": certainty == "approximate",
    }


def _indexed(items: list[Any], label: Any) -> dict[str, list[Any]]:
    result: dict[str, list[Any]] = defaultdict(list)
    for item in items:
        result[label(item)].append(item)
    return result


def _snapshot(item: Any, label: str) -> str:
    values = [label]
    for column in item.__table__.columns:
        values.append(f"{column.name}={getattr(item, column.name)!s}")
    return "|".join(values)


def _candidate_details(item: Any, category: str) -> str:
    if category == "supplier":
        return ", ".join(
            part
            for part in (
                f"Type: {item.kind}",
                f"Website: {item.website}" if item.website else "",
                f"Email: {item.email}" if item.email else "",
                f"Phone: {item.phone}" if item.phone else "",
                f"Notes: {item.notes[:120]}" if item.notes else "",
                f"Added: {item.created_at.date()}" if item.created_at else "",
                "Retired" if item.retired_at else "Current",
            )
            if part
        )
    status = "Retired" if getattr(item, "retired_at", None) else "Current"
    created = getattr(item, "created_at", None)
    return status + (f"; added {created.date()}" if created else "")


def _display_item(
    item: Any, category: str, locations: list[Location], places: list[GeographicPlace]
) -> str:
    if category == "location":
        return location_path(item, locations)
    if category == "geographic place":
        return place_path(item, places)
    if category == "identity":
        return identity_label(item)
    return str(getattr(item, "name", None) or getattr(item, "label", None) or item.id)


class References:
    def __init__(
        self, database: Session, selections: dict[tuple[int, str], DecisionOption] | None = None
    ) -> None:
        self.selections = selections or {}
        self.identities = list(database.scalars(select(BotanicalIdentity)))
        self.suppliers = list(database.scalars(select(Supplier)))
        self.locations = list(database.scalars(select(Location)))
        self.places = list(database.scalars(select(GeographicPlace)))
        self.sites = list(database.scalars(select(ProvenanceSite)))
        self.plants = list(database.scalars(select(Plant)))
        self.groups = list(database.scalars(select(PlantGroup)))
        self.seed_lots = list(database.scalars(select(SeedLot)))
        self.ids: dict[str, dict[str, Any]] = {
            "identity": {str(item.id): item for item in self.identities},
            "supplier": {str(item.id): item for item in self.suppliers},
            "location": {str(item.id): item for item in self.locations},
            "geographic place": {str(item.id): item for item in self.places},
            "provenance site": {str(item.id): item for item in self.sites},
            "producer plant": {str(item.id): item for item in self.plants},
            "producer plant group": {str(item.id): item for item in self.groups},
            "seed lot": {str(item.id): item for item in self.seed_lots},
        }
        self.names = {
            "identity": _indexed(self.identities, lambda item: identity_label(item)),
            "supplier": _indexed(self.suppliers, lambda item: item.name),
            "location": _indexed(self.locations, lambda item: location_path(item, self.locations)),
            "geographic place": _indexed(self.places, lambda item: place_path(item, self.places)),
            "provenance site": _indexed(self.sites, lambda item: item.name),
        }

    def resolve(
        self, row: PreviewRow, category: str, value: str, field_name: str, *, required: bool = False
    ) -> str | None:
        if not value:
            if required:
                row.issue("unresolved_reference", f"{category}: reference is required")
            return None
        try:
            key = str(UUID(value))
        except ValueError:
            key = value
        item = self.ids[category].get(key)
        matches = [item] if item is not None else self.names.get(category, {}).get(value, [])
        display_value = value[:160] + ("…" if len(value) > 160 else "")
        available = [match for match in matches if getattr(match, "retired_at", None) is None]
        if matches and not available:
            row.issue("conflict", f"{category}: all exact matches are retired: {display_value}")
            return None
        matches = available
        if len(matches) > 1:
            for match in matches:
                label = _display_item(match, category, self.locations, self.places)
                row.options.append(
                    DecisionOption(
                        key=field_name,
                        action="choose_reference",
                        candidate_id=str(match.id),
                        label=label,
                        details=_candidate_details(match, category),
                        snapshot=_snapshot(match, label),
                    )
                )
            selected = self.selections.get((row.row_number, field_name))
            if selected is not None and any(
                option.candidate_id == selected.candidate_id
                and option.signed_content() == selected.signed_content()
                for option in row.options
                if option.key == field_name
            ):
                item = self.ids[category][selected.candidate_id]
                row.references.append(f"{category}: {display_value} → {selected.label}")
                return str(item.id)
        if len(matches) == 1:
            resolved = matches[0]
            if getattr(resolved, "retired_at", None) is not None:
                row.issue("conflict", f"{category}: retired reference {display_value}")
                return None
            label = _display_item(resolved, category, self.locations, self.places)
            detail = _candidate_details(resolved, category)
            row.references.append(f"{category}: {display_value} → {label} ({detail})")
            return str(resolved.id)
        row.issue(
            "ambiguous_reference" if len(matches) > 1 else "unresolved_reference",
            f"{category}: {'ambiguous' if len(matches) > 1 else 'not found'}: {display_value}",
            resolvable=len(matches) > 1,
        )
        return None


def identity_label(item: BotanicalIdentity) -> str:
    return item.scientific_name + (f"|{item.cultivar_name}" if item.cultivar_name else "")


def _validation_message(error: ValidationError) -> str:
    messages = []
    for item in error.errors():
        field_name = str(item["loc"][-1]).replace("_", " ").capitalize() if item["loc"] else "Row"
        if item["type"] == "missing":
            detail = "is required"
        elif item["type"] == "string_too_long":
            detail = (
                f"is too long (maximum {item.get('ctx', {}).get('max_length', '?')} characters)"
            )
        elif item["type"] in {"enum", "literal_error"}:
            detail = "has an unsupported value; see the field guide for accepted values"
        else:
            detail = str(item["msg"]).removeprefix("Value error, ")
        messages.append(f"{field_name}: {detail}")
    return "; ".join(messages)


def _uuid_record_ref(row: PreviewRow, value: str) -> str | None:
    if not value:
        return None
    try:
        return str(UUID(value))
    except ValueError:
        row.issue(
            "invalid",
            "The optional existing record identifier is not valid; "
            "omit this advanced column for new records",
        )
        return None


def _build_row(kind: str, source: dict[str, str], row: PreviewRow, refs: References) -> None:
    record_id = _uuid_record_ref(row, source["record_ref"])
    if kind == "botanical-identities":
        identity_model = BotanicalIdentityCreate.model_validate(
            {
                key: optional(source[key]) if key != "scientific_name" else source[key]
                for key in ("scientific_name", "cultivar_name", "common_name")
            }
        )
        payload = identity_model.model_dump()
        row.record = identity_label_from_payload(payload)
        matches = [
            item
            for item in refs.identities
            if identity_label(item).casefold() == row.record.casefold()
        ]
        existing = refs.ids["identity"].get(record_id) if record_id else None
        if record_id and existing is None:
            row.issue(
                "unresolved_reference", f"record_ref: botanical identity {record_id} not found"
            )
        elif existing is not None and existing not in matches:
            row.issue("conflict", "record_ref identifies a different botanical identity")
        elif matches:
            existing = matches[0]
            differences = (
                [
                    {
                        "field": "common_name",
                        "before": existing.common_name or "",
                        "after": payload["common_name"] or "",
                    }
                ]
                if existing.common_name != payload["common_name"]
                else []
            )
            option = DecisionOption(
                key="record",
                action="use_existing",
                candidate_id=str(existing.id),
                label=identity_label(existing),
                details="Existing botanical identity; its current values remain unchanged",
                snapshot=_snapshot(existing, identity_label(existing)),
                changes=differences,
            )
            row.options.append(option)
            selected = refs.selections.get((row.row_number, "record"))
            if (
                row.outcome == "ready"
                and selected is not None
                and selected.signed_content() == option.signed_content()
            ):
                row.outcome = "already_exists"
                row.selected_action = option
            elif row.outcome == "ready":
                row.issue(
                    "needs_choice",
                    "Choose Use existing for this exact botanical identity; "
                    "a separate identity with the same name and cultivar is not allowed",
                )
        row.payload = payload
        return
    if kind == "suppliers":
        supplier_model = SupplierUpdate.model_validate(
            {
                "name": source["name"],
                "kind": source["kind"] or "other",
                **{key: optional(source[key]) for key in ("website", "email", "phone", "notes")},
            }
        )
        provided = supplier_model.model_dump(mode="json")
        row.record = supplier_model.name
        candidates = (
            [refs.ids["supplier"][record_id]]
            if record_id in refs.ids["supplier"]
            else []
            if record_id
            else refs.names["supplier"].get(supplier_model.name, [])
        )
        if record_id and not candidates:
            row.issue(
                "unresolved_reference",
                "The optional existing Supplier identifier does not match a record",
            )
        create_payload = None
        if source["kind"]:
            create_payload = SupplierCreate.model_validate(provided).model_dump(mode="json")
        elif not candidates:
            row.issue("invalid", "Supplier type is required when creating a new Supplier")
        for candidate in candidates:
            current = {
                key: getattr(candidate, key)
                for key in ("name", "kind", "website", "email", "phone", "notes")
            }
            label = candidate.name
            snapshot = _snapshot(candidate, label)
            details = _candidate_details(candidate, "supplier")
            updated = dict(current)
            for key in current:
                if source[key] != "":
                    updated[key] = provided[key]
            validated = SupplierUpdate.model_validate(updated).model_dump(mode="json")
            changes = [
                {
                    "field": key,
                    "before": str(current[key] or ""),
                    "after": str(validated[key] or ""),
                }
                for key in current
                if current[key] != validated[key]
            ]
            row.options.append(
                DecisionOption(
                    key="record",
                    action="use_existing",
                    candidate_id=str(candidate.id),
                    label=label,
                    details=details + "; CSV values are not applied",
                    snapshot=snapshot,
                    changes=changes,
                )
            )
            if changes and candidate.retired_at is None:
                row.options.append(
                    DecisionOption(
                        key="record",
                        action="update_existing",
                        candidate_id=str(candidate.id),
                        label=label,
                        details=details + "; blank CSV cells retain current values",
                        snapshot=snapshot,
                        changes=changes,
                        payload=validated,
                    )
                )
        if candidates and create_payload is not None and not record_id:
            row.options.append(
                DecisionOption(
                    key="record",
                    action="create_separate",
                    candidate_id="",
                    label=supplier_model.name,
                    details="Create another Supplier with this exact name",
                    snapshot="",
                    payload=create_payload,
                )
            )
        if candidates:
            selected = refs.selections.get((row.row_number, "record"))
            chosen = next(
                (
                    option
                    for option in row.options
                    if selected is not None and option.signed_content() == selected.signed_content()
                ),
                None,
            )
            if chosen is None and row.outcome == "ready":
                row.issue(
                    "needs_choice",
                    f"{len(candidates)} exact Supplier candidate(s) found; choose an action",
                )
            elif chosen is not None and row.outcome == "ready":
                row.selected_action = chosen
                row.payload = chosen.payload
                row.outcome = "already_exists" if chosen.action == "use_existing" else "ready"
        else:
            row.payload = create_payload
        return
    if kind == "locations":
        if source["import_key"] and not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", source["import_key"]
        ):
            raise ValueError(
                "import_key must be 1-64 letters, digits, dots, underscores or hyphens"
            )
        scopes = [part.strip() for part in source["usage_scopes"].split("|") if part.strip()]
        if not scopes:
            raise ValueError("usage_scopes must list at least one scope")
        parent = source["parent_ref"]
        parent_id = None
        if parent.startswith("@"):
            row.parent_key = parent[1:]
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", row.parent_key):
                row.issue("invalid", "parent_ref must name a valid @import_key")
                row.parent_key = None
        elif parent:
            parent_id = refs.resolve(row, "location", parent, "parent_ref")
        location_model = LocationCreate.model_validate(
            {"name": source["name"], "parent_id": parent_id, "usage_scopes": scopes}
        )
        row.record = location_model.name
        payload = location_model.model_dump(mode="json")
        row.payload = payload
        existing = refs.ids["location"].get(record_id) if record_id else None
        if record_id and existing is None:
            row.issue(
                "unresolved_reference",
                "The optional existing Location identifier does not match a record",
            )
        if record_id and row.parent_key:
            row.issue("conflict", "An existing Location cannot use a parent defined in this file")
        if existing is not None and (
            existing.name != location_model.name or existing.parent_id != location_model.parent_id
        ):
            row.issue("conflict", "The selected Location has a different name or parent path")
        candidates = (
            [existing]
            if existing is not None
            else []
            if record_id or row.parent_key or (parent and parent_id is None)
            else [
                item
                for item in refs.locations
                if item.name == location_model.name and item.parent_id == location_model.parent_id
            ]
        )
        for candidate in candidates:
            if candidate.retired_at is not None:
                continue
            label = location_path(candidate, refs.locations)
            differences = [
                {
                    "field": scope,
                    "before": str(getattr(candidate, f"supports_{scope}")),
                    "after": str(scope in scopes),
                }
                for scope in ("plants", "sowings", "seed_lots")
                if getattr(candidate, f"supports_{scope}") != (scope in scopes)
            ]
            row.options.append(
                DecisionOption(
                    key="record",
                    action="use_existing",
                    candidate_id=str(candidate.id),
                    label=label,
                    details="Existing Location; CSV scopes are not applied",
                    snapshot=_snapshot(candidate, label),
                    changes=differences,
                )
            )
        if candidates and not record_id:
            row.options.append(
                DecisionOption(
                    key="record",
                    action="create_separate",
                    candidate_id="",
                    label=location_model.name,
                    details="Create another Location at this parent path",
                    snapshot="",
                    payload=payload,
                )
            )
        if candidates:
            selected = refs.selections.get((row.row_number, "record"))
            chosen = next(
                (
                    option
                    for option in row.options
                    if selected is not None and option.signed_content() == selected.signed_content()
                ),
                None,
            )
            if chosen is None and row.outcome == "ready":
                row.issue(
                    "needs_choice",
                    f"{len(candidates)} exact Location candidate(s) found; choose an action",
                )
            elif chosen is not None and row.outcome == "ready":
                row.selected_action = chosen
                row.outcome = "already_exists" if chosen.action == "use_existing" else "ready"
        return
    if kind in {"seed-lots", "plants", "plant-groups"}:
        identity_id = refs.resolve(
            row, "identity", source["identity_ref"], "identity_ref", required=True
        )
        supplier_id = (
            refs.resolve(row, "supplier", source["supplier_ref"], "supplier_ref")
            if source["supplier_ref"]
            else None
        )
        place_id = (
            refs.resolve(
                row, "geographic place", source["geographic_place_ref"], "geographic_place_ref"
            )
            if source["geographic_place_ref"]
            else None
        )
        site_id = (
            refs.resolve(
                row, "provenance site", source["provenance_site_ref"], "provenance_site_ref"
            )
            if source["provenance_site_ref"]
            else None
        )
        location_id = (
            refs.resolve(row, "location", source["location_ref"], "location_ref")
            if source["location_ref"]
            else None
        )
        values: dict[str, Any] = {
            "botanical_identity_id": identity_id or str(UUID(int=0)),
            "supplier_id": supplier_id,
            "material_provenance_place_id": place_id,
            "provenance_site_id": site_id,
            "location_id": location_id,
            "label": optional(source["label"]),
            "notes": optional(source["notes"]),
            "lifecycle": source["lifecycle"] or "active",
        }
        row.record = source["label"] or source["identity_ref"] or f"CSV record {row.row_number}"
        if kind == "seed-lots":
            values.update(
                source_kind=source["source_kind"] or "unknown",
                source_detail=optional(source["source_detail"]),
                producer_plant_id=refs.resolve(
                    row, "producer plant", source["producer_plant_ref"], "producer_plant_ref"
                )
                if source["producer_plant_ref"]
                else None,
                producer_plant_group_id=refs.resolve(
                    row,
                    "producer plant group",
                    source["producer_plant_group_ref"],
                    "producer_plant_group_ref",
                )
                if source["producer_plant_group_ref"]
                else None,
                acquisition_date=partial_date(source["acquisition_date"]),
                harvest_date=partial_date(source["harvest_date"]),
                expected_viability_until=partial_date(source["expected_viability_until"]),
                quantity=quantity(source),
            )
            collection_payload = SeedLotCreate.model_validate(values).model_dump(mode="json")
            existing_ids = refs.ids["seed lot"]
            for producer_category, producer_id in (
                ("producer plant", values["producer_plant_id"]),
                ("producer plant group", values["producer_plant_group_id"]),
            ):
                producer = refs.ids[producer_category].get(producer_id) if producer_id else None
                if producer is not None and producer.lifecycle in {"reversed", "reintegrated"}:
                    row.issue(
                        "conflict", f"{producer_category}: historical producer is unavailable"
                    )
        else:
            values.update(
                direct_origin_kind=source["direct_origin_kind"] or "unknown",
                direct_origin_detail=optional(source["direct_origin_detail"]),
                collection_entry_date=partial_date(source["collection_entry_date"]),
            )
            if kind == "plants":
                collection_payload = PlantCreate.model_validate(values).model_dump(mode="json")
                existing_ids = refs.ids["producer plant"]
            else:
                values["quantity"] = quantity(source, group=True)
                collection_payload = PlantGroupCreate.model_validate(values).model_dump(mode="json")
                existing_ids = refs.ids["producer plant group"]
        row.payload = collection_payload
        if record_id:
            existing = existing_ids.get(record_id)
            if existing is None:
                row.issue("unresolved_reference", f"record_ref: {record_id} not found")
            else:
                row.issue(
                    "conflict",
                    "Existing collection records are never updated or silently skipped by import",
                )
        if location_id:
            item = refs.ids["location"][location_id]
            supported = item.supports_seed_lots if kind == "seed-lots" else item.supports_plants
            if not supported:
                row.issue("conflict", f"Location does not support {kind} assignments")
        return
    raise AssertionError("Unsupported kind")


def identity_label_from_payload(payload: dict[str, Any]) -> str:
    cultivar = payload["cultivar_name"]
    return str(payload["scientific_name"]) + (f"|{cultivar}" if cultivar else "")


def preview(
    database: Session,
    kind: str,
    data: bytes,
    selections: dict[tuple[int, str], DecisionOption] | None = None,
) -> list[PreviewRow]:
    sources = parse_csv(data, kind)
    refs = References(database, selections)
    rows: list[PreviewRow] = []
    for number, source in sources:
        result = PreviewRow(
            row_number=number,
            record=(
                source.get("name")
                or source.get("label")
                or source.get("scientific_name")
                or f"CSV record {number}"
            )[:255],
        )
        try:
            result.source = normalize_source(kind, source, result)
            _build_row(kind, result.source, result, refs)
        except (ValidationError, ValueError) as error:
            result.issue(
                "invalid",
                _validation_message(error) if isinstance(error, ValidationError) else str(error),
            )
        rows.append(result)
    if kind == "botanical-identities":
        identity_keys = [row.record.casefold() for row in rows]
        identity_counts = Counter(identity_keys)
        for row, key in zip(rows, identity_keys, strict=True):
            if identity_counts[key] > 1:
                row.issue("conflict", "Duplicate identity tuple in CSV")
    if kind == "suppliers":
        supplier_keys = [row.record.casefold() for row in rows]
        supplier_counts = Counter(supplier_keys)
        for row, key in zip(rows, supplier_keys, strict=True):
            if supplier_counts[key] > 1:
                row.issue("ambiguous_reference", "Repeated Supplier name in CSV")
    if kind == "locations":
        location_keys: dict[str, PreviewRow] = {}
        counts = Counter(
            row.source["import_key"]
            for row in rows
            if row.source is not None
            if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", row.source["import_key"])
        )
        for row in rows:
            if row.source is None:
                continue
            source = row.source
            key = source["import_key"]
            if key in counts:
                if counts[key] > 1:
                    row.issue("ambiguous_reference", f"Duplicate import_key: {key}")
                else:
                    location_keys[key] = row
        for row in rows:
            if row.parent_key:
                parent = location_keys.get(row.parent_key)
                if counts[row.parent_key] > 1:
                    row.issue("ambiguous_reference", f"parent_ref @{row.parent_key} is duplicated")
                elif parent is None:
                    row.issue("unresolved_reference", f"parent_ref @{row.parent_key} not found")
                elif parent is row:
                    row.issue("conflict", "Location cannot parent itself")
                else:
                    parent_status = (
                        "will create"
                        if parent.outcome == "ready"
                        else "already exists"
                        if parent.outcome == "already_exists"
                        else "requires a choice"
                    )
                    row.references.append(
                        f"parent Location: @{row.parent_key} (CSV record {parent.row_number}; "
                        f"{parent_status})"
                    )
        for row in rows:
            seen: set[int] = set()
            current = row
            while current.parent_key and current.parent_key in location_keys:
                if current.row_number in seen:
                    row.issue("conflict", "Location parent cycle")
                    break
                seen.add(current.row_number)
                current = location_keys[current.parent_key]
        for row in rows:
            if (
                row.parent_key
                and row.parent_key in location_keys
                and location_keys[row.parent_key].outcome
                not in {"ready", "already_exists", "needs_choice"}
            ):
                row.issue("conflict", "Parent Location row needs attention")
    return rows


def apply(
    database: Session,
    kind: str,
    data: bytes,
    selections: dict[tuple[int, str], DecisionOption] | None = None,
) -> tuple[int, int, int]:
    rows = preview(database, kind, data, selections)
    if any(row.outcome not in {"ready", "already_exists"} for row in rows):
        raise CsvFormatError("CSV needs attention; run preview again")
    ready = [row for row in rows if row.outcome == "ready"]
    updated = 0
    if kind == "locations":
        keys = {
            row.source["import_key"]: row
            for row in rows
            if row.source is not None and row.source["import_key"]
        }
        created: dict[str, UUID] = {
            row.source["import_key"]: UUID(row.selected_action.candidate_id)
            for row in rows
            if row.source is not None
            and row.source["import_key"]
            and row.outcome == "already_exists"
            and row.selected_action is not None
        }
        pending = list(ready)
        while pending:
            progress = False
            for row in pending[:]:
                if row.parent_key and row.parent_key not in created:
                    continue
                assert row.payload is not None
                payload = dict(row.payload)
                if row.parent_key:
                    payload["parent_id"] = created[row.parent_key]
                location = create_location(database, LocationCreate.model_validate(payload))
                for key, target in keys.items():
                    if target is row:
                        created[key] = location.id
                pending.remove(row)
                progress = True
            if not progress:
                raise CsvFormatError("Location hierarchy cannot be applied")
    else:
        for row in ready:
            assert row.payload is not None
            if kind == "botanical-identities":
                create_botanical_identity(
                    database, BotanicalIdentityCreate.model_validate(row.payload)
                )
            elif kind == "suppliers":
                if (
                    row.selected_action is not None
                    and row.selected_action.action == "update_existing"
                ):
                    supplier = database.get(Supplier, UUID(row.selected_action.candidate_id))
                    if supplier is None:
                        raise CsvFormatError("A selected Supplier changed; validate the CSV again")
                    database.refresh(supplier, with_for_update=True)
                    if _snapshot(supplier, supplier.name) != row.selected_action.snapshot:
                        raise CsvFormatError("A selected Supplier changed; validate the CSV again")
                    update_supplier(database, supplier, SupplierUpdate.model_validate(row.payload))
                    updated += 1
                else:
                    create_supplier(database, SupplierCreate.model_validate(row.payload))
            elif kind == "seed-lots":
                create_seed_lot(database, SeedLotCreate.model_validate(row.payload))
            elif kind == "plants":
                create_plant(database, PlantCreate.model_validate(row.payload))
            elif kind == "plant-groups":
                create_plant_group(database, PlantGroupCreate.model_validate(row.payload))
    return len(ready) - updated, len(rows) - len(ready), updated


def safe_cell(value: object, *, text_field: bool = False) -> str:
    if value is None:
        return ""
    result = str(value)
    if text_field and result.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + result
    return result


def date_cell(item: Any, prefix: str) -> str:
    year = getattr(item, f"{prefix}_year")
    if year is None:
        return ""
    month = getattr(item, f"{prefix}_month")
    day = getattr(item, f"{prefix}_day")
    return (
        f"{year:04d}"
        + (f"-{month:02d}" if month is not None else "")
        + (f"-{day:02d}" if day is not None else "")
    )


def _quantity_cells(item: Any, *, group: bool = False) -> dict[str, str]:
    value = item.quantity_value
    if value is None:
        return {
            "quantity_value": "",
            "quantity_certainty": "unknown",
            **({} if group else {"quantity_kind": "", "quantity_unit": ""}),
        }
    result = {
        "quantity_value": str(value),
        "quantity_certainty": "approximate" if item.quantity_is_approximate else "exact",
    }
    if not group:
        result.update(quantity_kind=item.quantity_kind, quantity_unit=item.quantity_unit or "")
    return result


def export_csv(database: Session, kind: str) -> str:
    if kind not in COLUMNS:
        raise CsvFormatError("Unsupported record type")
    refs = References(database)
    models: dict[str, list[Any]] = {
        "botanical-identities": refs.identities,
        "suppliers": refs.suppliers,
        "locations": refs.locations,
        "seed-lots": refs.seed_lots,
        "plants": refs.plants,
        "plant-groups": refs.groups,
    }
    output = io.StringIO(newline="")
    export_columns = COLUMNS[kind] + EXPORT_EXTRA_COLUMNS[kind]
    writer = csv.DictWriter(output, fieldnames=export_columns, lineterminator="\r\n")
    writer.writeheader()
    for item in sorted(models[kind], key=lambda value: str(value.id)):
        values: dict[str, object] = {"record_ref": str(item.id)}
        if kind == "botanical-identities":
            values.update(
                scientific_name=item.scientific_name,
                cultivar_name=item.cultivar_name,
                common_name=item.common_name,
            )
        elif kind == "suppliers":
            values.update(
                name=item.name,
                kind=item.kind,
                website=item.website,
                email=item.email,
                phone=item.phone,
                notes=item.notes,
            )
        elif kind == "locations":
            values.update(
                import_key="",
                name=item.name,
                parent_ref=item.parent_id,
                parent_path=location_path(refs.ids["location"][str(item.parent_id)], refs.locations)
                if item.parent_id
                else "",
                usage_scopes="|".join(
                    scope
                    for scope, active in (
                        ("plants", item.supports_plants),
                        ("sowings", item.supports_sowings),
                        ("seed_lots", item.supports_seed_lots),
                    )
                    if active
                ),
            )
        else:
            identity = refs.ids["identity"][str(item.botanical_identity_id)]
            supplier = refs.ids["supplier"].get(str(item.supplier_id))
            place = refs.ids["geographic place"].get(str(item.material_provenance_place_id))
            site = refs.ids["provenance site"].get(str(item.provenance_site_id))
            location = refs.ids["location"].get(str(item.location_id))
            values.update(
                identity_ref=item.botanical_identity_id,
                identity_label=identity_label(identity),
                label=item.label,
                supplier_ref=item.supplier_id,
                supplier_name=supplier.name if supplier else "",
                geographic_place_ref=item.material_provenance_place_id,
                geographic_place_path=place_path(place, refs.places) if place else "",
                provenance_site_ref=item.provenance_site_id,
                provenance_site_name=site.name if site else "",
                location_ref=item.location_id,
                location_path=location_path(location, refs.locations) if location else "",
                lifecycle=item.lifecycle,
                notes=item.notes,
            )
            if kind == "seed-lots":
                producer_plant = refs.ids["producer plant"].get(str(item.producer_plant_id))
                producer_group = refs.ids["producer plant group"].get(
                    str(item.producer_plant_group_id)
                )
                values.update(
                    source_kind=item.source_kind,
                    source_detail=item.source_detail,
                    producer_plant_ref=item.producer_plant_id,
                    producer_plant_label=producer_plant.label if producer_plant else "",
                    producer_plant_group_ref=item.producer_plant_group_id,
                    producer_plant_group_label=producer_group.label if producer_group else "",
                    acquisition_date=date_cell(item, "acquisition_date"),
                    harvest_date=date_cell(item, "harvest_date"),
                    expected_viability_until=date_cell(item, "expected_viability_until"),
                    **_quantity_cells(item),
                )
            else:
                values.update(
                    direct_origin_kind=item.direct_origin_kind,
                    direct_origin_detail=item.direct_origin_detail,
                    collection_entry_date=date_cell(item, "collection_entry_date"),
                )
                if kind == "plant-groups":
                    values.update(**_quantity_cells(item, group=True))
        writer.writerow(
            {
                key: safe_cell(
                    values.get(key),
                    text_field=key
                    in {
                        "scientific_name",
                        "cultivar_name",
                        "common_name",
                        "name",
                        "website",
                        "email",
                        "phone",
                        "notes",
                        "label",
                        "source_detail",
                        "direct_origin_detail",
                        *EXPORT_EXTRA_COLUMNS[kind],
                    },
                )
                for key in export_columns
            }
        )
    return output.getvalue()


def template_csv(kind: str) -> str:
    if kind not in COLUMNS:
        raise CsvFormatError("Unsupported record type")
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(IMPORT_COLUMNS[kind])
    return output.getvalue()
