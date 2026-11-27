"""Column-mapping model and EN/IT header suggestions for single-sheet imports."""

from __future__ import annotations

import re
import unicodedata
from enum import StrEnum
from typing import Literal

from florabase.import_wizard.sheet import ParsedColumn

SheetImportRecordType = Literal["plants", "plant-groups", "seed-lots"]


class SheetImportField(StrEnum):
    SCIENTIFIC_NAME = "scientific_name"
    CULTIVAR_NAME = "cultivar_name"
    COMMON_NAME = "common_name"
    LABEL = "label"
    LOCATION = "location"
    SUPPLIER = "supplier"
    COLLECTION_ENTRY_DATE = "collection_entry_date"
    ACQUISITION_DATE = "acquisition_date"
    HARVEST_DATE = "harvest_date"
    EXPECTED_VIABILITY_UNTIL = "expected_viability_until"
    QUANTITY_VALUE = "quantity_value"
    QUANTITY_APPROXIMATE = "quantity_approximate"
    QUANTITY_KIND = "quantity_kind"
    QUANTITY_UNIT = "quantity_unit"
    DIRECT_ORIGIN_KIND = "direct_origin_kind"
    DIRECT_ORIGIN_DETAIL = "direct_origin_detail"
    SOURCE_KIND = "source_kind"
    SOURCE_DETAIL = "source_detail"
    LIFECYCLE = "lifecycle"
    NOTES = "notes"


ALLOWED_FIELDS_BY_TYPE: dict[SheetImportRecordType, tuple[SheetImportField, ...]] = {
    "plants": (
        SheetImportField.SCIENTIFIC_NAME,
        SheetImportField.CULTIVAR_NAME,
        SheetImportField.COMMON_NAME,
        SheetImportField.LABEL,
        SheetImportField.LOCATION,
        SheetImportField.SUPPLIER,
        SheetImportField.COLLECTION_ENTRY_DATE,
        SheetImportField.DIRECT_ORIGIN_KIND,
        SheetImportField.DIRECT_ORIGIN_DETAIL,
        SheetImportField.LIFECYCLE,
        SheetImportField.NOTES,
    ),
    "plant-groups": (
        SheetImportField.SCIENTIFIC_NAME,
        SheetImportField.CULTIVAR_NAME,
        SheetImportField.COMMON_NAME,
        SheetImportField.LABEL,
        SheetImportField.LOCATION,
        SheetImportField.SUPPLIER,
        SheetImportField.COLLECTION_ENTRY_DATE,
        SheetImportField.QUANTITY_VALUE,
        SheetImportField.QUANTITY_APPROXIMATE,
        SheetImportField.DIRECT_ORIGIN_KIND,
        SheetImportField.DIRECT_ORIGIN_DETAIL,
        SheetImportField.LIFECYCLE,
        SheetImportField.NOTES,
    ),
    "seed-lots": (
        SheetImportField.SCIENTIFIC_NAME,
        SheetImportField.CULTIVAR_NAME,
        SheetImportField.COMMON_NAME,
        SheetImportField.LABEL,
        SheetImportField.LOCATION,
        SheetImportField.SUPPLIER,
        SheetImportField.ACQUISITION_DATE,
        SheetImportField.HARVEST_DATE,
        SheetImportField.EXPECTED_VIABILITY_UNTIL,
        SheetImportField.QUANTITY_VALUE,
        SheetImportField.QUANTITY_APPROXIMATE,
        SheetImportField.QUANTITY_KIND,
        SheetImportField.QUANTITY_UNIT,
        SheetImportField.SOURCE_KIND,
        SheetImportField.SOURCE_DETAIL,
        SheetImportField.LIFECYCLE,
        SheetImportField.NOTES,
    ),
}

_HEADER_SYNONYMS: dict[SheetImportField, frozenset[str]] = {
    SheetImportField.SCIENTIFIC_NAME: frozenset(
        {
            "scientific name",
            "species",
            "taxon",
            "taxon name",
            "binomial",
            "botanical name",
            "plant name",
            "nome scientifico",
            "specie",
            "nome botanico",
        }
    ),
    SheetImportField.CULTIVAR_NAME: frozenset(
        {
            "cultivar",
            "cultivar name",
            "cv",
            "variety",
            "varieta",
        }
    ),
    SheetImportField.COMMON_NAME: frozenset(
        {
            "common name",
            "vernacular",
            "vernacular name",
            "nome comune",
        }
    ),
    SheetImportField.LABEL: frozenset(
        {
            "label",
            "code",
            "tag",
            "accession",
            "accession code",
            "id",
            "etichetta",
            "codice",
            "sigla",
        }
    ),
    SheetImportField.LOCATION: frozenset(
        {
            "location",
            "place",
            "position",
            "spot",
            "bench",
            "shelf",
            "posizione",
            "collocazione",
            "luogo",
            "posto",
        }
    ),
    SheetImportField.SUPPLIER: frozenset(
        {
            "supplier",
            "nursery",
            "vendor",
            "seller",
            "shop",
            "source",
            "fornitore",
            "vivaio",
            "negozio",
        }
    ),
    SheetImportField.COLLECTION_ENTRY_DATE: frozenset(
        {
            "collection entry date",
            "entry date",
            "acquired",
            "acquisition date",
            "purchase date",
            "bought",
            "purchased",
            "sown entered",
            "entered",
            "date",
            "data acquisto",
            "data ingresso",
            "data acquisizione",
            "data",
        }
    ),
    SheetImportField.ACQUISITION_DATE: frozenset(
        {
            "acquisition date",
            "acquired",
            "purchase date",
            "bought",
            "purchased",
            "entry date",
            "date",
            "data acquisto",
            "data acquisizione",
            "data ingresso",
            "data",
        }
    ),
    SheetImportField.HARVEST_DATE: frozenset(
        {
            "harvest date",
            "harvest year",
            "harvested",
            "harvest",
            "data raccolta",
            "anno raccolta",
            "raccolta",
        }
    ),
    SheetImportField.EXPECTED_VIABILITY_UNTIL: frozenset(
        {
            "expected viability until",
            "viability",
            "viability until",
            "expires",
            "expiry",
            "scadenza",
            "vitalita",
        }
    ),
    SheetImportField.QUANTITY_VALUE: frozenset(
        {
            "quantity",
            "quantity value",
            "qty",
            "count",
            "seeds",
            "seed count",
            "number",
            "quantita",
            "numero",
            "semi",
        }
    ),
    SheetImportField.QUANTITY_APPROXIMATE: frozenset(
        {
            "approx",
            "approximate",
            "is approximate",
            "quantity certainty",
            "certainty",
            "estimated",
            "circa",
            "approssimata",
            "approssimativo",
            "stimata",
        }
    ),
    SheetImportField.QUANTITY_KIND: frozenset(
        {
            "quantity kind",
            "measurement type",
            "tipo quantita",
        }
    ),
    SheetImportField.QUANTITY_UNIT: frozenset(
        {
            "quantity unit",
            "unit",
            "weight unit",
            "unita",
        }
    ),
    SheetImportField.DIRECT_ORIGIN_KIND: frozenset(
        {
            "direct origin kind",
            "origin kind",
            "origin",
            "origine",
        }
    ),
    SheetImportField.DIRECT_ORIGIN_DETAIL: frozenset(
        {
            "direct origin detail",
            "origin detail",
            "dettaglio origine",
        }
    ),
    SheetImportField.SOURCE_KIND: frozenset(
        {
            "source kind",
            "provenance kind",
            "tipo provenienza",
        }
    ),
    SheetImportField.SOURCE_DETAIL: frozenset(
        {
            "source detail",
            "dettaglio provenienza",
        }
    ),
    SheetImportField.LIFECYCLE: frozenset(
        {
            "lifecycle",
            "status",
            "state",
            "stato",
        }
    ),
    SheetImportField.NOTES: frozenset(
        {
            "notes",
            "note",
            "comment",
            "comments",
            "remarks",
            "description",
            "osservazioni",
        }
    ),
}

_TRUTHY_APPROX = frozenset(
    {
        "yes",
        "y",
        "si",
        "true",
        "t",
        "1",
        "approx",
        "approximate",
        "approssimata",
        "approssimativo",
        "circa",
    }
)
_FALSY_APPROX = frozenset({"no", "n", "false", "f", "0", "exact", "esatta", "esatto"})


def normalize_header(header: str) -> str:
    decomposed = unicodedata.normalize("NFKD", header)
    ascii_folded = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    cleaned = re.sub(r"[^a-z0-9]+", " ", ascii_folded.casefold())
    return cleaned.strip()


def suggest_mapping(
    columns: list[ParsedColumn], record_type: SheetImportRecordType
) -> dict[str, SheetImportField | None]:
    allowed = ALLOWED_FIELDS_BY_TYPE[record_type]
    assigned_fields: set[SheetImportField] = set()
    suggestions: dict[str, SheetImportField | None] = {}
    for column in columns:
        normalized = normalize_header(column.raw_header or column.header)
        matched: SheetImportField | None = None
        for field in allowed:
            if field in assigned_fields:
                continue
            if normalized in _HEADER_SYNONYMS[field]:
                matched = field
                assigned_fields.add(field)
                break
        suggestions[column.key] = matched
    return suggestions


def parse_approximate_flag(value: str) -> Literal["exact", "approximate"]:
    normalized = normalize_header(value)
    if not normalized:
        return "exact"
    if normalized in _TRUTHY_APPROX:
        return "approximate"
    if normalized in _FALSY_APPROX:
        return "exact"
    raise ValueError(
        f'Approximate flag "{value[:80]}" is not recognized. '
        "Accepted values: yes, no, sì, true, false, exact, approximate"
    )
