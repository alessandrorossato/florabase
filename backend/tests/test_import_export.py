import csv
import io
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.import_export import service
from florabase.import_export.service import (
    COLUMNS,
    IMPORT_COLUMNS,
    MAX_BYTES,
    MAX_ROWS,
    CsvFormatError,
    PreviewRow,
    example_csv,
    field_guide,
    normalize_source,
    parse_csv,
    partial_date,
    quantity,
    safe_cell,
    template_csv,
)
from florabase.locations.model import Location
from florabase.plants.model import Plant, PlantGroup
from florabase.seed_lots.model import SeedLot
from florabase.suppliers.model import Supplier


class _Rows:
    def __init__(self, values: list[object]) -> None:
        self.values = values

    def __iter__(self) -> Iterator[object]:
        return iter(self.values)


class _PreviewDatabase:
    def __init__(self, *values: object) -> None:
        self.values: dict[type[object], list[object]] = {}
        for value in values:
            self.values.setdefault(type(value), []).append(value)

    def scalars(self, statement: object) -> _Rows:
        entity = statement.column_descriptions[0]["entity"]  # type: ignore[attr-defined]
        return _Rows(self.values.get(entity, []))

    def get(self, entity: type[object], identifier: UUID) -> object | None:
        return next(
            (
                item
                for item in self.values.get(entity, [])
                if getattr(item, "id") == identifier  # noqa: B009
            ),
            None,
        )

    def refresh(self, instance: object, *, with_for_update: bool = False) -> None:
        del instance, with_for_update

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


def _identity(name: str, cultivar: str | None = None) -> BotanicalIdentity:
    return BotanicalIdentity(
        id=uuid4(), scientific_name=name, cultivar_name=cultivar, common_name=None
    )


def _supplier(name: str, *, kind: str = "nursery", website: str | None = None) -> Supplier:
    return Supplier(
        id=uuid4(),
        name=name,
        kind=kind,
        website=website,
        email=None,
        phone=None,
        notes=None,
        retired_at=None,
    )


def _location(
    name: str, *, parent_id: UUID | None = None, plants: bool = True, seed_lots: bool = True
) -> Location:
    return Location(
        id=uuid4(),
        name=name,
        parent_id=parent_id,
        supports_plants=plants,
        supports_sowings=False,
        supports_seed_lots=seed_lots,
        retired_at=None,
    )


def _session(database: _PreviewDatabase) -> Session:
    return cast(Session, database)


def test_csv_parser_accepts_bom_quoted_newline_and_blank_records() -> None:
    data = b"\xef\xbb\xbfrecord_ref,name,kind,website,email,phone,notes\r\n"
    data += b' ,"Seeds, Inc",seller,,,,"first\nsecond"\r\n\r\n'
    rows = parse_csv(data, "suppliers")
    assert len(rows) == 1
    assert rows[0][0] == 2
    assert rows[0][1]["name"] == "Seeds, Inc"
    assert rows[0][1]["notes"] == "first\nsecond"


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"record_ref,name,name\na,b,c\n", "Duplicate"),
        (b"record_ref,name,kind,website,email,phone,extra\n,,,,,,\n", "headers differ"),
        (b"record_ref,name,kind,website,email,phone,notes\na,b\n", "fields"),
        (b'record_ref,name,kind,website,email,phone,notes\n"unclosed,b,c,,,,\n', "Malformed"),
        (b"\xff", "UTF-8"),
        (b"", "nonempty"),
    ],
)
def test_csv_parser_rejects_invalid_input(data: bytes, message: str) -> None:
    with pytest.raises(CsvFormatError, match=message):
        parse_csv(data, "suppliers")


def test_csv_bounds_and_exact_templates() -> None:
    with pytest.raises(CsvFormatError, match="2 MiB"):
        parse_csv(b"x" * (MAX_BYTES + 1), "suppliers")
    header = template_csv("botanical-identities")
    assert next(csv.reader(io.StringIO(header))) == list(IMPORT_COLUMNS["botanical-identities"])
    assert "record_ref" not in header
    with pytest.raises(CsvFormatError, match=str(MAX_ROWS)):
        parse_csv(
            (header + "\n".join("Quercus robur,," for _ in range(MAX_ROWS + 1))).encode(),
            "botanical-identities",
        )


def test_examples_and_guides_share_import_headers() -> None:
    for kind, columns in IMPORT_COLUMNS.items():
        assert "record_ref" not in columns
        assert next(csv.reader(io.StringIO(template_csv(kind)))) == list(columns)
        guide = field_guide(kind)
        assert [item["field"] for item in guide] == list(columns)
        assert all(item["example"] != "(leave blank)" for item in guide)
        examples = parse_csv(example_csv(kind).encode(), kind)
        assert examples
        assert all(set(row) == set(COLUMNS[kind]) for _, row in examples)
    with pytest.raises(CsvFormatError, match="Unsupported"):
        field_guide("unsupported")
    with pytest.raises(CsvFormatError, match="Unsupported"):
        example_csv("unsupported")
    with pytest.raises(CsvFormatError, match="Unsupported"):
        template_csv("unsupported")
    with pytest.raises(CsvFormatError, match="Unsupported"):
        parse_csv(b"a,b\n", "unsupported")
    with pytest.raises(CsvFormatError, match="no data rows"):
        parse_csv(template_csv("suppliers").encode(), "suppliers")


def test_header_whitespace_and_case_are_normalized_without_guessing() -> None:
    data = b" Scientific_Name , CULTIVAR_NAME , common_name\nAcmella oleracea,,Paracress\n"
    assert parse_csv(data, "botanical-identities")[0][1]["scientific_name"] == "Acmella oleracea"
    with pytest.raises(CsvFormatError, match="Duplicate"):
        parse_csv(b"name, NAME ,kind,website,email,phone,notes\nA,B,seller,,,,\n", "suppliers")


@pytest.mark.parametrize("value", ["nursery", "Nursery", "NURSERY", " nursery "])
def test_supplier_kind_normalization(value: str) -> None:
    row = PreviewRow(2, "Cercatoridisemì")
    normalized = normalize_source("suppliers", {"kind": value}, row)
    assert normalized["kind"] == "nursery"
    assert bool(row.normalized) is (value != "nursery")


def test_normalization_uses_canonical_enums_without_synonyms() -> None:
    row = PreviewRow(2, "Lot")
    normalized = normalize_source(
        "seed-lots",
        {
            "source_kind": " GIFT_EXCHANGE ",
            "quantity_kind": " SEED_COUNT ",
            "quantity_certainty": " APPROXIMATE ",
            "lifecycle": " ACTIVE ",
        },
        row,
    )
    assert normalized == {
        "source_kind": "gift_exchange",
        "quantity_kind": "seed_count",
        "quantity_certainty": "approximate",
        "lifecycle": "active",
    }
    with pytest.raises(ValueError, match="not recognized"):
        normalize_source("suppliers", {"kind": "garden center"}, PreviewRow(2, "Invalid"))
    assert (
        normalize_source(
            "locations", {"usage_scopes": " PLANTS | SEED_LOTS "}, PreviewRow(2, "Cabinet")
        )["usage_scopes"]
        == "plants|seed_lots"
    )
    assert (
        normalize_source("plants", {"lifecycle": " DEAD "}, PreviewRow(2, "Plant"))["lifecycle"]
        == "dead"
    )
    with pytest.raises(ValueError, match="not recognized"):
        normalize_source("plants", {"lifecycle": "reversed"}, PreviewRow(2, "Plant"))


def test_partial_dates_and_quantity_certainty() -> None:
    assert partial_date("2024") == {"precision": "year", "year": 2024, "month": None, "day": None}
    assert partial_date("2024-05")["precision"] == "month"  # type: ignore[index]
    assert partial_date("2024-05-13")["precision"] == "day"  # type: ignore[index]
    with pytest.raises(ValueError, match="day"):
        partial_date("2024-02-30")
    assert (
        quantity(
            {
                "quantity_kind": "",
                "quantity_value": "",
                "quantity_unit": "",
                "quantity_certainty": "unknown",
            }
        )
        is None
    )
    with pytest.raises(ValueError, match="Unknown quantity"):
        quantity(
            {
                "quantity_kind": "seed_count",
                "quantity_value": "",
                "quantity_unit": "",
                "quantity_certainty": "unknown",
            }
        )
    assert quantity(
        {
            "quantity_kind": "weight",
            "quantity_value": "1.25",
            "quantity_unit": "g",
            "quantity_certainty": "approximate",
        }
    ) == {"kind": "weight", "value": "1.25", "unit": "g", "is_approximate": True}
    with pytest.raises(ValueError, match="whole number"):
        quantity({"quantity_value": "1.5", "quantity_certainty": "exact"}, group=True)


def test_formula_protection_only_touches_authored_text() -> None:
    for text in ("=1+1", "+SUM(A1)", " -2+3", "@command"):
        assert safe_cell(text, text_field=True) == "'" + text
    assert safe_cell("-2") == "-2"
    assert safe_cell("2024-05") == "2024-05"


def _data(kind: str, rows: list[dict[str, str]], *, include_record_ref: bool = False) -> bytes:
    output = io.StringIO(newline="")
    columns = COLUMNS[kind] if include_record_ref else IMPORT_COLUMNS[kind]
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode()


def _example_references(kind: str) -> _PreviewDatabase:
    if kind in {"botanical-identities", "suppliers", "locations"}:
        return _PreviewDatabase()
    identity_one = _identity("Acmella oleracea")
    identity_two = _identity("Allium fistulosum")
    supplier = _supplier("Cercatoridisemì")
    cabinet = _location("Seed cabinet")
    drawer = _location("Drawer 3", parent_id=cabinet.id)
    return _PreviewDatabase(identity_one, identity_two, supplier, cabinet, drawer)


def test_preview_accepts_each_downloadable_example_against_exact_references() -> None:
    for kind in IMPORT_COLUMNS:
        report = service.preview(
            _session(_example_references(kind)),
            kind,
            example_csv(kind).encode(),
        )
        assert all(row.outcome == "ready" for row in report), (kind, report)


def test_preview_existing_identity_requires_use_existing_and_never_overwrites() -> None:
    existing = _identity("Phaseolus vulgaris", "Borlotto")
    data = _data(
        "botanical-identities",
        [
            {
                "scientific_name": "Phaseolus vulgaris",
                "cultivar_name": "Borlotto",
                "common_name": "Bean",
            }
        ],
    )
    database = _session(_PreviewDatabase(existing))
    first = service.preview(database, "botanical-identities", data)
    assert first[0].outcome == "needs_choice"
    assert first[0].options[0].changes == [{"field": "common_name", "before": "", "after": "Bean"}]
    choice = first[0].options[0]
    second = service.preview(
        database,
        "botanical-identities",
        data,
        {(2, "record"): choice},
    )
    assert second[0].outcome == "already_exists"
    assert second[0].payload == {
        "scientific_name": "Phaseolus vulgaris",
        "cultivar_name": "Borlotto",
        "common_name": "Bean",
    }


def test_preview_supplier_actions_preserve_blank_existing_fields() -> None:
    existing = _supplier("Cercatoridisemì", website="https://old.example")
    data = _data(
        "suppliers",
        [{"name": "Cercatoridisemì", "kind": " NURSERY ", "website": "https://new.example"}],
    )
    database = _session(_PreviewDatabase(existing))
    first = service.preview(database, "suppliers", data)
    assert first[0].outcome == "needs_choice"
    update = next(option for option in first[0].options if option.action == "update_existing")
    assert update.changes == [
        {"field": "website", "before": "https://old.example", "after": "https://new.example"}
    ]
    assert update.payload == {
        "name": "Cercatoridisemì",
        "kind": "nursery",
        "website": "https://new.example",
        "email": None,
        "phone": None,
        "notes": None,
    }
    current_use = next(option for option in first[0].options if option.action == "use_existing")
    assert current_use.details.endswith("CSV values are not applied")


def test_preview_reports_ambiguous_unresolved_and_retired_references() -> None:
    identity = _identity("Phaseolus vulgaris")
    suppliers = [_supplier("Same name"), _supplier("Same name", kind="seller")]
    retired = _supplier("Retired", kind="seller")
    retired.retired_at = datetime.now(UTC)
    data = _data(
        "seed-lots",
        [
            {"identity_ref": "Phaseolus vulgaris", "supplier_ref": "Same name"},
            {"identity_ref": "Missing identity"},
            {"identity_ref": "Phaseolus vulgaris", "supplier_ref": "Retired"},
        ],
    )
    rows = service.preview(
        _session(_PreviewDatabase(identity, *suppliers, retired)),
        "seed-lots",
        data,
    )
    assert rows[0].outcome == "ambiguous_reference"
    assert {option.candidate_id for option in rows[0].options} == {
        str(suppliers[0].id),
        str(suppliers[1].id),
    }
    assert rows[1].outcome == "unresolved_reference"
    assert rows[2].outcome == "conflict"


def test_preview_location_keys_detect_duplicates_missing_parents_and_cycles() -> None:
    data = _data(
        "locations",
        [
            {"import_key": "same", "name": "One", "usage_scopes": "plants"},
            {"import_key": "same", "name": "Two", "usage_scopes": "plants"},
            {
                "import_key": "child",
                "name": "Child",
                "parent_ref": "@missing",
                "usage_scopes": "plants",
            },
            {
                "import_key": "left",
                "name": "Left",
                "parent_ref": "@right",
                "usage_scopes": "plants",
            },
            {
                "import_key": "right",
                "name": "Right",
                "parent_ref": "@left",
                "usage_scopes": "plants",
            },
        ],
    )
    rows = service.preview(_session(_PreviewDatabase()), "locations", data)
    assert "Duplicate import_key" in rows[0].messages[0]
    assert "Duplicate import_key" in rows[1].messages[0]
    assert any("not found" in message for message in rows[2].messages)
    assert any("cycle" in message.lower() for row in rows[3:] for message in row.messages)


def test_preview_location_existing_choice_and_invalid_parent_and_scopes() -> None:
    cabinet = _location("Cabinet")
    data = _data(
        "locations",
        [
            {"import_key": "existing", "name": "Cabinet", "usage_scopes": "plants"},
            {"import_key": "self", "name": "Self", "parent_ref": "@self", "usage_scopes": "plants"},
            {
                "import_key": "bad",
                "name": "Bad",
                "parent_ref": "@wrong key",
                "usage_scopes": "unknown",
            },
        ],
    )
    first = service.preview(_session(_PreviewDatabase(cabinet)), "locations", data)
    assert first[0].outcome == "needs_choice"
    assert {option.action for option in first[0].options} == {"use_existing", "create_separate"}
    selected = first[0].options[0]
    done = service.preview(
        _session(_PreviewDatabase(cabinet)),
        "locations",
        data,
        {(2, "record"): selected},
    )
    assert done[0].outcome == "already_exists"
    assert any("itself" in message for message in done[1].messages)
    assert done[2].outcome == "invalid"


def test_preview_rejects_bad_record_refs_and_preserves_uuid_identity_resolution() -> None:
    identity = _identity("Phaseolus vulgaris")
    data = _data(
        "seed-lots",
        [
            {"identity_ref": str(identity.id), "record_ref": "not-a-uuid"},
            {"identity_ref": "", "record_ref": str(uuid4())},
        ],
        include_record_ref=True,
    )
    rows = service.preview(_session(_PreviewDatabase(identity)), "seed-lots", data)
    assert rows[0].outcome == "invalid"
    assert rows[1].outcome == "unresolved_reference"


def test_export_supports_every_record_type() -> None:
    identity = _identity("Acmella oleracea")
    supplier = _supplier("Cercatoridisemì")
    location = _location("Seed cabinet")
    values: list[object] = [identity, supplier, location]
    collection_base = {
        "id": uuid4(),
        "botanical_identity_id": identity.id,
        "originating_sowing_id": None,
        "direct_origin_kind": "unknown",
        "direct_origin_detail": None,
        "supplier_id": None,
        "material_provenance_place_id": None,
        "provenance_site_id": None,
        "label": "Record",
        "collection_entry_date_precision": "year",
        "collection_entry_date_year": 2024,
        "collection_entry_date_month": None,
        "collection_entry_date_day": None,
        "location_id": location.id,
        "lifecycle": "active",
        "notes": None,
    }
    values.extend(
        [
            Plant(**collection_base),
            PlantGroup(
                **collection_base,
                quantity_value=8,
                quantity_is_approximate=True,
            ),
        ]
    )
    database = _PreviewDatabase(*values)
    for kind in COLUMNS:
        exported = service.export_csv(_session(database), kind)
        assert next(csv.reader(io.StringIO(exported))) == list(
            COLUMNS[kind] + service.EXPORT_EXTRA_COLUMNS[kind]
        )


def test_apply_dispatches_each_supported_type_through_domain_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = _identity("Acmella oleracea")
    database = _session(_PreviewDatabase(identity))
    called: list[tuple[str, object]] = []
    for name in (
        "create_botanical_identity",
        "create_supplier",
        "create_seed_lot",
        "create_plant",
        "create_plant_group",
    ):
        monkeypatch.setattr(
            service, name, lambda _db, payload, _name=name: called.append((_name, payload))
        )

    cases = {
        "botanical-identities": [{"scientific_name": "Phaseolus vulgaris"}],
        "suppliers": [{"name": "ABC Seeds", "kind": "seller"}],
        "seed-lots": [{"identity_ref": "Acmella oleracea"}],
        "plants": [{"identity_ref": "Acmella oleracea"}],
        "plant-groups": [{"identity_ref": "Acmella oleracea"}],
    }
    for kind, rows in cases.items():
        result = service.apply(database, kind, _data(kind, rows))
        assert result == (1, 0, 0)
    assert len(called) == len(cases)

    created_locations: list[Location] = []

    def create_location(_db: object, payload: object) -> Location:
        item = Location(
            id=uuid4(),
            name=payload.name,  # type: ignore[attr-defined]
            parent_id=payload.parent_id,  # type: ignore[attr-defined]
            supports_plants=True,
            supports_sowings=False,
            supports_seed_lots=True,
            retired_at=None,
        )
        created_locations.append(item)
        return item

    monkeypatch.setattr(service, "create_location", create_location)
    location_rows = [
        {
            "import_key": "drawer",
            "name": "Drawer",
            "parent_ref": "@cabinet",
            "usage_scopes": "seed_lots",
        },
        {"import_key": "cabinet", "name": "Cabinet", "usage_scopes": "plants"},
    ]
    applied = service.apply(
        _session(_PreviewDatabase()),
        "locations",
        _data("locations", location_rows),
    )
    assert applied == (2, 0, 0)
    assert created_locations[0].name == "Cabinet"
    assert created_locations[1].parent_id == created_locations[0].id


def test_apply_updates_selected_supplier_after_snapshot_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing = _supplier("ABC Seeds", website="https://old.example")
    database = _session(_PreviewDatabase(existing))
    data = _data(
        "suppliers", [{"name": "ABC Seeds", "kind": "nursery", "website": "https://new.example"}]
    )
    row = service.preview(database, "suppliers", data)[0]
    update = next(option for option in row.options if option.action == "update_existing")
    updates: list[object] = []
    monkeypatch.setattr(
        service, "update_supplier", lambda _db, _item, payload: updates.append(payload)
    )
    result = service.apply(
        database,
        "suppliers",
        data,
        {(2, "record"): update},
    )
    assert result == (0, 0, 1)
    assert len(updates) == 1


def test_export_csv_is_stable_and_protects_authored_text() -> None:
    identity = _identity("=Acmella oleracea")
    supplier = _supplier("+Seed seller", kind="seller")
    identity_id = identity.id
    seed_lot = SeedLot(
        id=uuid4(),
        botanical_identity_id=identity_id,
        label="@packet",
        source_kind="unknown",
        acquisition_date_precision="month",
        acquisition_date_year=2024,
        acquisition_date_month=5,
        acquisition_date_day=None,
        harvest_date_precision=None,
        harvest_date_year=None,
        harvest_date_month=None,
        harvest_date_day=None,
        expected_viability_until_precision=None,
        expected_viability_until_year=None,
        expected_viability_until_month=None,
        expected_viability_until_day=None,
        quantity_kind=None,
        quantity_value=None,
        quantity_unit=None,
        quantity_is_approximate=None,
        lifecycle="active",
        notes="-unsafe note",
        supplier_id=supplier.id,
    )
    database = _session(_PreviewDatabase(identity, supplier, seed_lot))
    first = service.export_csv(database, "seed-lots")
    second = service.export_csv(database, "seed-lots")
    assert first == second
    rows = list(csv.DictReader(io.StringIO(first)))
    assert rows[0]["acquisition_date"] == "2024-05"
    assert rows[0]["identity_label"] == "'=Acmella oleracea"
    assert rows[0]["supplier_name"] == "'+Seed seller"
    assert rows[0]["notes"] == "'-unsafe note"
