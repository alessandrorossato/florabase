"""Unit tests for the single-sheet spreadsheet import wizard and IMPORT-001 refactor."""

from __future__ import annotations

import asyncio
import io
import zipfile
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast
from uuid import uuid4

import openpyxl
import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from florabase.auth.dependencies import AuthenticatedActor
from florabase.auth.model import AuthSession
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.import_export.service import (
    PendingReference,
    References,
    build_rows,
)
from florabase.import_wizard import api as wizard_api
from florabase.import_wizard.mapping import (
    SheetImportField,
    SheetImportRecordType,
    parse_approximate_flag,
    suggest_mapping,
)
from florabase.import_wizard.schemas import (
    SheetImportChoices,
    SheetImportIdentityChoice,
    SheetImportLocationChoice,
    SheetImportMapping,
    SheetImportOptions,
    SheetImportSupplierChoice,
)
from florabase.import_wizard.service import (
    SheetImportConflictError,
    apply_sheet,
    build_preview_plan,
    inspect_sheet,
    preview_response_from_plan,
)
from florabase.import_wizard.sheet import (
    MAX_BYTES,
    MAX_COLUMNS,
    MAX_ROWS,
    MAX_UNCOMPRESSED_BYTES,
    SheetFormatError,
    _format_xlsx_value,
    parse_sheet,
)
from florabase.locations.model import Location
from florabase.suppliers.model import Supplier, SupplierKind

FIXTURES = Path(__file__).parent / "fixtures" / "sheet"


class _FakeDatabase:
    def __init__(
        self,
        *,
        identities: list[BotanicalIdentity] | None = None,
        suppliers: list[Supplier] | None = None,
        locations: list[Location] | None = None,
    ) -> None:
        self._identities = identities or []
        self._suppliers = suppliers or []
        self._locations = locations or []
        self.committed = False
        self.rolled_back = False

    def scalars(self, statement: object) -> list[object]:
        text = str(statement)
        if "botanical_identities" in text:
            return list(self._identities)
        if "suppliers" in text:
            return list(self._suppliers)
        if "locations" in text:
            return list(self._locations)
        return []

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def flush(self) -> None:
        pass


def _session(db: _FakeDatabase) -> Session:
    return cast(Session, db)


def _actor(*, owner: bool = True, token_digest: bytes = b"k" * 32) -> AuthenticatedActor:
    return AuthenticatedActor(
        user_id=uuid4(),
        login_name="owner" if owner else "viewer",
        display_name="Owner" if owner else "Viewer",
        owner=owner,
        session=AuthSession(id=uuid4(), token_digest=token_digest),
    )


def _make_xlsx(rows: list[list[object]], *, merged: str | None = None) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    for row in rows:
        ws.append(row)
    if merged:
        ws.merge_cells(merged)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _make_zip_bytes(entries: dict[str, bytes], *, compress: int = zipfile.ZIP_DEFLATED) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=compress) as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return buf.getvalue()


@pytest.mark.parametrize("stem", ["plants", "plant-groups", "seed-lots"])
def test_csv_and_xlsx_fixture_equivalence(stem: str) -> None:
    csv_parsed = parse_sheet((FIXTURES / f"{stem}.csv").read_bytes(), filename=f"{stem}.csv")
    xlsx_parsed = parse_sheet((FIXTURES / f"{stem}.xlsx").read_bytes(), filename=f"{stem}.xlsx")

    assert csv_parsed.format == "csv"
    assert xlsx_parsed.format == "xlsx"
    assert [c.header for c in csv_parsed.columns] == [c.header for c in xlsx_parsed.columns]
    assert len(csv_parsed.rows) == len(xlsx_parsed.rows)
    for csv_row, xlsx_row in zip(csv_parsed.rows, xlsx_parsed.rows, strict=True):
        assert csv_row.row_number == xlsx_row.row_number
        assert csv_row.cells == xlsx_row.cells


def test_it_edge_cases_xlsx_sheets_header_dates_formula_and_notes() -> None:
    data = (FIXTURES / "it-edge-cases.xlsx").read_bytes()

    # Default first sheet ("Info") has only one row and no data rows.
    with pytest.raises(SheetFormatError, match="no data rows"):
        inspect_sheet(data, filename="it-edge-cases.xlsx", record_type="plants")

    inspected = inspect_sheet(
        data, filename="it-edge-cases.xlsx", sheet_name="Piante", record_type="plants"
    )
    assert inspected.sheets == ["Info", "Piante"]
    assert inspected.selected_sheet == "Piante"
    assert inspected.detected_header_row == 2
    assert inspected.header_row == 2
    assert inspected.row_count == 2

    suggested = {col.header: col.suggested_field for col in inspected.columns}
    assert suggested["Nome scientifico"] == SheetImportField.SCIENTIFIC_NAME
    assert suggested["Cultivar"] == SheetImportField.CULTIVAR_NAME
    assert suggested["Etichetta"] == SheetImportField.LABEL
    assert suggested["Posizione"] == SheetImportField.LOCATION
    assert suggested["Fornitore"] == SheetImportField.SUPPLIER
    assert suggested["Data acquisto"] == SheetImportField.COLLECTION_ENTRY_DATE
    assert suggested["Note"] == SheetImportField.NOTES
    # Quantita must NOT be auto-suggested for individual Plants; Prezzo stays unmapped.
    assert suggested["Quantità"] is None
    assert suggested["Prezzo"] is None

    # Sample row 2 shows "(formula)" for Prezzo.
    prezzo_col = next(c for c in inspected.columns if c.header == "Prezzo")
    assert prezzo_col.samples == ["12.5", "(formula)"]

    # Default mapping (Prezzo unmapped) ignores uncached formula; append_unmapped_to_notes skips it.
    db = _FakeDatabase()
    base_mapping = {col.key: col.suggested_field for col in inspected.columns}
    options = SheetImportOptions(
        record_type="plants",
        sheet_name="Piante",
        header_row=2,
        mapping=SheetImportMapping(columns=base_mapping, append_unmapped_to_notes=True),
    )
    plan = build_preview_plan(_session(db), data, options, filename="it-edge-cases.xlsx")
    assert plan.can_apply is True
    assert [row.row_number for row in plan.rows] == [3, 4]
    assert plan.rows[0].payload is not None
    assert plan.rows[0].payload["collection_entry_date"] == {
        "precision": "day",
        "year": 2024,
        "month": 9,
        "day": 1,
    }
    assert "Prezzo: 12.5" in (plan.rows[0].payload["notes"] or "")
    assert "Quantità: 1" in (plan.rows[0].payload["notes"] or "")
    assert plan.rows[1].payload is not None
    assert plan.rows[1].payload["collection_entry_date"] == {
        "precision": "month",
        "year": 2022,
        "month": 6,
        "day": None,
    }
    assert plan.rows[1].payload["notes"] == "Prezzo come formula"

    # Mapping Prezzo to notes reports the uncached formula on row 4 as invalid.
    mapped_formula = dict(base_mapping)
    note_col = next(c for c in inspected.columns if c.header == "Note")
    mapped_formula[note_col.key] = None
    mapped_formula[prezzo_col.key] = SheetImportField.NOTES
    bad_options = SheetImportOptions(
        record_type="plants",
        sheet_name="Piante",
        header_row=2,
        mapping=SheetImportMapping(columns=mapped_formula),
    )
    bad_plan = build_preview_plan(_session(db), data, bad_options, filename="it-edge-cases.xlsx")
    assert bad_plan.can_apply is False
    assert bad_plan.rows[0].outcome == "ready"
    assert bad_plan.rows[1].outcome == "invalid"
    assert any("formula without a cached value" in msg for msg in bad_plan.rows[1].messages)


def test_cached_formula_value_is_accepted() -> None:
    # Build an XLSX whose formula cell carries an explicit cached value <v>8</v>.
    raw = _make_xlsx([["Species", "Label"], ["Hoya kerrii", "PLACEHOLDER"]])
    patched_entries: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
        for info in zf.infolist():
            content = zf.read(info.filename)
            if info.filename == "xl/worksheets/sheet1.xml":
                text = content.decode("utf-8").replace(
                    '<c r="B2" t="inlineStr"><is><t>PLACEHOLDER</t></is></c>',
                    '<c r="B2"><f>4+4</f><v>8</v></c>',
                )
                # openpyxl may write sharedStrings or inlineStr; handle both cleanly.
                if "PLACEHOLDER" not in content.decode("utf-8"):
                    import re

                    text = re.sub(
                        r'<c r="B2"[^>]*>.*?</c>',
                        '<c r="B2"><f>4+4</f><v>8</v></c>',
                        content.decode("utf-8"),
                    )
                content = text.encode("utf-8")
            patched_entries[info.filename] = content
    xlsx = _make_zip_bytes(patched_entries)
    parsed = parse_sheet(xlsx, filename="cached.xlsx")
    assert parsed.rows[0].cells["col_1"].uncached_formula is False
    assert parsed.rows[0].cells["col_1"].text == "8"


def test_parser_security_and_limits() -> None:
    # Empty & oversize upload
    with pytest.raises(SheetFormatError, match="nonempty"):
        parse_sheet(b"", filename="empty.csv")
    with pytest.raises(SheetFormatError, match="2 MiB"):
        parse_sheet(b"a" * (MAX_BYTES + 1), filename="big.csv")

    # Legacy .xls & bad xlsx magic
    with pytest.raises(SheetFormatError, match=r"Legacy \.xls"):
        parse_sheet(b"dummy", filename="old.xls")
    with pytest.raises(SheetFormatError, match="Invalid XLSX"):
        parse_sheet(b"not a zip", filename="fake.xlsx")

    # Bad UTF-8 & malformed CSV
    with pytest.raises(SheetFormatError, match="UTF-8"):
        parse_sheet(b"\xff\xfe", filename="bad.csv")
    with pytest.raises(SheetFormatError, match="Malformed CSV"):
        parse_sheet(b'Species\n"unterminated\n', filename="bad.csv")
    with pytest.raises(SheetFormatError, match="XLSX files"):
        parse_sheet(b"Species\nHoya kerrii\n", filename="ok.csv", sheet_name="Sheet1")

    # UTF-8 BOM & merged cells
    bom_csv = '\ufeffSpecies,Notes\r\nHoya kerrii,"Line 1\nLine 2"\r\n'.encode()
    parsed_bom = parse_sheet(bom_csv, filename="bom.csv")
    assert parsed_bom.columns[0].header == "Species"
    assert parsed_bom.rows[0].cells["col_1"].text == "Line 1\nLine 2"

    merged_xlsx = _make_xlsx(
        [["Species", "Label", "Notes"], ["Hoya kerrii", "H-1", "ok"]],
        merged="A2:B2",
    )
    parsed_merged = parse_sheet(merged_xlsx, filename="merged.xlsx")
    assert parsed_merged.rows[0].cells["col_0"].text == "Hoya kerrii"

    # Zip bomb: compression ratio > 100:1
    high_ratio_zip = _make_zip_bytes({"xl/worksheets/sheet1.xml": b" " * 300_000})
    with pytest.raises(SheetFormatError, match="100:1"):
        parse_sheet(high_ratio_zip, filename="bomb.xlsx")

    # Test DTD / ENTITY rejection in XML member
    dtd_zip = _make_zip_bytes(
        {
            "xl/workbook.xml": (
                b'<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe "boom">]><workbook/>'
            )
        },
        compress=zipfile.ZIP_STORED,
    )
    with pytest.raises(SheetFormatError, match="DTD and external entity"):
        parse_sheet(dtd_zip, filename="xxe.xlsx")

    # Exceeding MAX_COLUMNS (61 columns)
    wide_header = ",".join(f"c{i}" for i in range(MAX_COLUMNS + 1))
    wide_row = ",".join("x" for _ in range(MAX_COLUMNS + 1))
    with pytest.raises(SheetFormatError, match=f"{MAX_COLUMNS} columns"):
        parse_sheet(f"{wide_header}\n{wide_row}\n".encode(), filename="wide.csv")

    # Exceeding MAX_ROWS (2001 data rows)
    many_rows = "Species\n" + ("Hoya kerrii\n" * (MAX_ROWS + 1))
    with pytest.raises(SheetFormatError, match=f"{MAX_ROWS} nonblank rows"):
        parse_sheet(many_rows.encode(), filename="many.csv")

    # Header row out of range / blank header row
    with pytest.raises(SheetFormatError, match="between 1 and 10"):
        parse_sheet(b"Species\nHoya kerrii\n", filename="ok.csv", header_row=11)
    with pytest.raises(SheetFormatError, match="is blank"):
        parse_sheet(b"\nSpecies\nHoya kerrii\n", filename="ok.csv", header_row=1)


def test_zip_uncompressed_total_over_30_mib_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    # Lower MAX_UNCOMPRESSED_BYTES temporarily to test the 30 MiB declared/actual cap cleanly
    # without constructing a multi-megabyte random fixture.
    monkeypatch.setattr("florabase.import_wizard.sheet.MAX_UNCOMPRESSED_BYTES", 1024)
    small_zip = _make_zip_bytes(
        {"xl/workbook.xml": b"<workbook>" + b"A" * 1200 + b"</workbook>"},
        compress=zipfile.ZIP_STORED,
    )
    assert MAX_UNCOMPRESSED_BYTES == 30 * 1024 * 1024
    with pytest.raises(SheetFormatError, match="30 MiB"):
        parse_sheet(small_zip, filename="over30.xlsx")


def test_format_xlsx_value_types() -> None:
    assert _format_xlsx_value(None) == ""
    assert _format_xlsx_value(True) == "true"
    assert _format_xlsx_value(False) == "false"
    assert _format_xlsx_value(datetime(2024, 9, 1, 14, 30, tzinfo=UTC)) == "2024-09-01"
    assert _format_xlsx_value(date(2024, 9, 1)) == "2024-09-01"
    assert _format_xlsx_value(42) == "42"
    assert _format_xlsx_value(42.0) == "42"
    assert _format_xlsx_value(12.5) == "12.5"
    assert _format_xlsx_value(Decimal("3.00")) == "3"
    assert _format_xlsx_value(Decimal("3.250")) == "3.25"
    assert _format_xlsx_value("2023-05") == "2023-05"


def test_mapping_suggestions_and_approximate_flag() -> None:
    for record_type, fixture, expected_fields in (
        (
            "plants",
            "plants.csv",
            {
                "Species": SheetImportField.SCIENTIFIC_NAME,
                "Cultivar": SheetImportField.CULTIVAR_NAME,
                "Common name": SheetImportField.COMMON_NAME,
                "Label": SheetImportField.LABEL,
                "Location": SheetImportField.LOCATION,
                "Supplier": SheetImportField.SUPPLIER,
                "Bought": SheetImportField.COLLECTION_ENTRY_DATE,
                "Notes": SheetImportField.NOTES,
            },
        ),
        (
            "plant-groups",
            "plant-groups.csv",
            {
                "Species": SheetImportField.SCIENTIFIC_NAME,
                "Label": SheetImportField.LABEL,
                "Location": SheetImportField.LOCATION,
                "Quantity": SheetImportField.QUANTITY_VALUE,
                "Approx": SheetImportField.QUANTITY_APPROXIMATE,
                "Sown/entered": SheetImportField.COLLECTION_ENTRY_DATE,
                "Notes": SheetImportField.NOTES,
            },
        ),
        (
            "seed-lots",
            "seed-lots.csv",
            {
                "Species": SheetImportField.SCIENTIFIC_NAME,
                "Label": SheetImportField.LABEL,
                "Supplier": SheetImportField.SUPPLIER,
                "Harvest year": SheetImportField.HARVEST_DATE,
                "Seeds": SheetImportField.QUANTITY_VALUE,
                "Location": SheetImportField.LOCATION,
                "Notes": SheetImportField.NOTES,
            },
        ),
    ):
        parsed = parse_sheet((FIXTURES / fixture).read_bytes(), filename=fixture)
        suggested = suggest_mapping(parsed.columns, cast(SheetImportRecordType, record_type))
        by_header = {col.header: suggested[col.key] for col in parsed.columns}
        assert by_header == expected_fields

    assert parse_approximate_flag("") == "exact"
    assert parse_approximate_flag("yes") == "approximate"
    assert parse_approximate_flag("Sì") == "approximate"
    assert parse_approximate_flag("no") == "exact"
    assert parse_approximate_flag("false") == "exact"
    with pytest.raises(ValueError, match="not recognized"):
        parse_approximate_flag("maybe")


def test_pending_references_and_skip_choices_and_near_matches() -> None:
    existing_identity = BotanicalIdentity(
        id=uuid4(), scientific_name="Hoya carnosa", cultivar_name="Krimson Queen"
    )
    greenhouse = Location(
        id=uuid4(),
        name="Greenhouse",
        parent_id=None,
        supports_plants=True,
        supports_sowings=True,
        supports_seed_lots=True,
    )
    bench2 = Location(
        id=uuid4(),
        name="Bench 2",
        parent_id=greenhouse.id,
        supports_plants=True,
        supports_sowings=True,
        supports_seed_lots=True,
    )
    existing_supplier = Supplier(
        id=uuid4(),
        name="green hands nursery",
        kind=SupplierKind.NURSERY.value,
    )
    db = _FakeDatabase(
        identities=[existing_identity],
        suppliers=[existing_supplier],
        locations=[greenhouse, bench2],
    )

    # Direct unit test of IMPORT-001's PendingReference support on References + build_rows.
    pending_id = str(uuid4())
    refs = References(
        _session(db),
        pending={
            "identity": {pending_id: PendingReference(id=pending_id, label="Mammillaria elongata")}
        },
    )
    built = build_rows(
        "plants",
        [
            (
                2,
                {
                    "record_ref": "",
                    "identity_ref": pending_id,
                    "label": "MAM-001",
                    "direct_origin_kind": "",
                    "direct_origin_detail": "",
                    "supplier_ref": "",
                    "geographic_place_ref": "",
                    "provenance_site_ref": "",
                    "collection_entry_date": "2023",
                    "location_ref": "",
                    "lifecycle": "",
                    "notes": "",
                },
            )
        ],
        refs,
    )
    assert built[0].outcome == "ready"
    assert any("(will create)" in ref for ref in built[0].references)

    # Grouped review on plants.csv:
    # - Hoya carnosa|Krimson Queen matches existing identity; Mammillaria elongata is new.
    # - "Greenhouse / Bench 2" does NOT auto-split, stays "new", and offers "Greenhouse → Bench 2"
    #   as a near-match candidate!
    # - "Green Hands Nursery" offers "green hands nursery" as a near-match candidate!
    data = (FIXTURES / "plants.csv").read_bytes()
    inspected = inspect_sheet(data, filename="plants.csv", record_type="plants")
    mapping = SheetImportMapping(columns={c.key: c.suggested_field for c in inspected.columns})

    plan = build_preview_plan(
        _session(db),
        data,
        SheetImportOptions(record_type="plants", mapping=mapping),
        filename="plants.csv",
    )
    assert plan.can_apply is True
    assert plan.will_create_identities == 1
    assert plan.will_create_locations == 2
    assert plan.will_create_suppliers == 1

    loc_group = next(g for g in plan.locations if g.raw_value == "Greenhouse / Bench 2")
    assert loc_group.status == "new"
    assert any(c.match_kind == "near" and c.id == bench2.id for c in loc_group.candidates)

    sup_group = next(g for g in plan.suppliers if g.raw_value == "Green Hands Nursery")
    assert sup_group.status == "new"
    assert sup_group.kind == SupplierKind.OTHER
    assert any(
        c.match_kind == "near" and c.id == existing_supplier.id for c in sup_group.candidates
    )

    # Explicit "skip" on location and supplier must show clearly in preview and stay deliberate.
    skip_options = SheetImportOptions(
        record_type="plants",
        mapping=mapping,
        choices=SheetImportChoices(
            locations={"Windowsill": SheetImportLocationChoice(action="skip")},
            suppliers={"Green Hands Nursery": SheetImportSupplierChoice(action="skip")},
        ),
    )
    skip_plan = build_preview_plan(_session(db), data, skip_options, filename="plants.csv")
    assert skip_plan.can_apply is True
    win_group = next(g for g in skip_plan.locations if g.raw_value == "Windowsill")
    assert win_group.status == "skipped"
    assert win_group.messages == ["Location will be left empty"]
    sup_skipped = next(g for g in skip_plan.suppliers if g.raw_value == "Green Hands Nursery")
    assert sup_skipped.status == "skipped"
    assert sup_skipped.messages == ["Supplier will be left empty"]
    assert any("location will be left empty" in ref for ref in skip_plan.rows[1].references)
    assert any("supplier will be left empty" in ref for ref in skip_plan.rows[0].references)

    # Colliding edited identity choice ("create" with existing tuple) blocks preview cleanly.
    collide_options = SheetImportOptions(
        record_type="plants",
        mapping=mapping,
        choices=SheetImportChoices(
            identities={
                "mammillaria elongata": SheetImportIdentityChoice(
                    action="create",
                    scientific_name="Hoya carnosa",
                    cultivar_name="Krimson Queen",
                )
            }
        ),
    )
    collide_plan = build_preview_plan(_session(db), data, collide_options, filename="plants.csv")
    assert collide_plan.can_apply is False
    response = preview_response_from_plan(collide_plan, "tok")
    assert response.needs_attention == 1
    assert response.rows[1].outcome == "conflict"


def test_confirmation_token_binds_session_file_options_and_ttl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = _actor()
    other = _actor()
    data = (FIXTURES / "plants.csv").read_bytes()
    options = SheetImportOptions(
        record_type="plants",
        mapping=SheetImportMapping(columns={"col_0": SheetImportField.SCIENTIFIC_NAME}),
    )
    changed_options = SheetImportOptions(
        record_type="plants",
        mapping=SheetImportMapping(
            columns={"col_0": SheetImportField.SCIENTIFIC_NAME},
            append_unmapped_to_notes=True,
        ),
    )
    monkeypatch.setattr("florabase.import_wizard.api.time.time", lambda: 1_800_000_000)
    token = wizard_api._confirmation_token(actor, data, options)
    assert wizard_api._verify_confirmation_token(actor, data, options, token)
    assert not wizard_api._verify_confirmation_token(other, data, options, token)
    assert not wizard_api._verify_confirmation_token(actor, data + b" ", options, token)
    assert not wizard_api._verify_confirmation_token(actor, data, changed_options, token)
    assert not wizard_api._verify_confirmation_token(actor, data, options, "malformed")

    monkeypatch.setattr("florabase.import_wizard.api.time.time", lambda: 1_800_000_901)
    assert not wizard_api._verify_confirmation_token(actor, data, options, token)


def test_upload_size_limit_and_invalid_options_errors() -> None:
    async def run() -> None:
        upload = UploadFile(file=io.BytesIO(b"x" * (MAX_BYTES + 1)), filename="huge.csv")
        with pytest.raises(HTTPException) as exc:
            await wizard_api._read_upload(upload)
        assert exc.value.status_code == 413

    asyncio.run(run())
    with pytest.raises(HTTPException) as bad_json:
        wizard_api._parse_options("{not-json")
    assert bad_json.value.status_code == 422


def test_mapping_validation_and_plant_group_and_seed_lot_preview() -> None:
    db = _FakeDatabase()
    plants_data = (FIXTURES / "plants.csv").read_bytes()
    inspected = inspect_sheet(plants_data, filename="plants.csv", record_type="plants")
    valid_map = {col.key: col.suggested_field for col in inspected.columns}

    # Unknown column key
    with pytest.raises(SheetFormatError, match="Unknown column key"):
        build_preview_plan(
            _session(db),
            plants_data,
            SheetImportOptions(
                record_type="plants",
                mapping=SheetImportMapping(columns={"col_99": SheetImportField.SCIENTIFIC_NAME}),
            ),
            filename="plants.csv",
        )

    # Disallowed field for record type (quantity_value on plants)
    with pytest.raises(SheetFormatError, match="not supported"):
        build_preview_plan(
            _session(db),
            plants_data,
            SheetImportOptions(
                record_type="plants",
                mapping=SheetImportMapping(
                    columns={**valid_map, "col_7": SheetImportField.QUANTITY_VALUE}
                ),
            ),
            filename="plants.csv",
        )

    # Duplicate field mapping
    with pytest.raises(SheetFormatError, match="more than one column"):
        build_preview_plan(
            _session(db),
            plants_data,
            SheetImportOptions(
                record_type="plants",
                mapping=SheetImportMapping(
                    columns={
                        "col_0": SheetImportField.SCIENTIFIC_NAME,
                        "col_1": SheetImportField.SCIENTIFIC_NAME,
                    }
                ),
            ),
            filename="plants.csv",
        )

    # Missing required scientific_name mapping
    with pytest.raises(SheetFormatError, match="scientific_name"):
        build_preview_plan(
            _session(db),
            plants_data,
            SheetImportOptions(
                record_type="plants",
                mapping=SheetImportMapping(columns={"col_3": SheetImportField.LABEL}),
            ),
            filename="plants.csv",
        )

    # Plant groups with valid and invalid approximate flags & blank quantity
    pg_csv = (
        b"Species,Label,Quantity,Approx,Notes\n"
        b"Echeveria elegans,E-1,10,yes,ok\n"
        b"Lithops lesliei,L-1,,no,empty qty\n"
        b"Haworthia attenuata,H-1,5,maybe,bad approx\n"
    )
    pg_inspected = inspect_sheet(pg_csv, filename="pg.csv", record_type="plant-groups")
    pg_plan = build_preview_plan(
        _session(db),
        pg_csv,
        SheetImportOptions(
            record_type="plant-groups",
            mapping=SheetImportMapping(
                columns={c.key: c.suggested_field for c in pg_inspected.columns}
            ),
        ),
        filename="pg.csv",
    )
    assert pg_plan.can_apply is False
    assert pg_plan.rows[0].outcome == "ready"
    assert pg_plan.rows[1].outcome == "ready"
    assert pg_plan.rows[2].outcome == "invalid"

    # Seed lots with bad approximate flag & empty quantity
    sl_csv = (
        b"Species,Label,Harvest year,Seeds,Approx\n"
        b"Phaseolus vulgaris,B-1,2024,50,si\n"
        b"Ferocactus latispinus,F-1,2023,,\n"
        b"Hoya kerrii,H-1,2024,10,dunno\n"
    )
    sl_inspected = inspect_sheet(sl_csv, filename="sl.csv", record_type="seed-lots")
    sl_plan = build_preview_plan(
        _session(db),
        sl_csv,
        SheetImportOptions(
            record_type="seed-lots",
            mapping=SheetImportMapping(
                columns={c.key: c.suggested_field for c in sl_inspected.columns}
            ),
        ),
        filename="sl.csv",
    )
    assert sl_plan.can_apply is False
    assert sl_plan.rows[0].outcome == "ready"
    assert sl_plan.rows[1].outcome == "ready"
    assert sl_plan.rows[2].outcome == "invalid"


def test_grouped_review_ambiguity_scope_and_invalid_choices() -> None:
    id1 = BotanicalIdentity(id=uuid4(), scientific_name="Hoya carnosa", cultivar_name=None)
    loc_a = Location(
        id=uuid4(),
        name="Bench",
        parent_id=None,
        supports_plants=True,
        supports_sowings=True,
        supports_seed_lots=False,
    )
    loc_b = Location(
        id=uuid4(),
        name="Bench",
        parent_id=None,
        supports_plants=True,
        supports_sowings=True,
        supports_seed_lots=True,
    )
    loc_seeds_only = Location(
        id=uuid4(),
        name="Seed Box",
        parent_id=None,
        supports_plants=False,
        supports_sowings=False,
        supports_seed_lots=True,
    )
    sup_a = Supplier(id=uuid4(), name="Vivaio", kind=SupplierKind.NURSERY.value)
    sup_b = Supplier(id=uuid4(), name="Vivaio", kind=SupplierKind.SELLER.value)
    db = _FakeDatabase(
        identities=[id1],
        suppliers=[sup_a, sup_b],
        locations=[loc_a, loc_b, loc_seeds_only],
    )

    csv_bytes = (
        b"Species,Cultivar,Location,Supplier\n"
        b"Hoya carnosa,'Krimson',Bench,Vivaio\n"
        b"Hoya carnosa,,Seed Box,Vivaio\n"
    )
    inspected = inspect_sheet(csv_bytes, filename="ambig.csv", record_type="plants")
    mapping = SheetImportMapping(columns={c.key: c.suggested_field for c in inspected.columns})

    # Default: ambiguous Bench + Vivaio + incompatible Seed Box scope
    plan = build_preview_plan(
        _session(db),
        csv_bytes,
        SheetImportOptions(record_type="plants", mapping=mapping),
        filename="ambig.csv",
    )
    assert plan.can_apply is False
    assert any(g.status == "ambiguous" for g in plan.locations)
    assert any(g.status == "invalid" for g in plan.locations)
    assert any(g.status == "ambiguous" for g in plan.suppliers)

    # Explicit invalid choices (missing UUIDs, missing parent_id, invalid blank names)
    bad_choices = SheetImportChoices(
        identities={
            "hoya carnosa|krimson": SheetImportIdentityChoice(
                action="use_existing", existing_id=uuid4()
            ),
            "hoya carnosa": SheetImportIdentityChoice(action="create", scientific_name="   "),
        },
        locations={
            "Bench": SheetImportLocationChoice(action="use_existing", existing_id=uuid4()),
            "Seed Box": SheetImportLocationChoice(action="create", name="Box", parent_id=uuid4()),
        },
        suppliers={
            "Vivaio": SheetImportSupplierChoice(action="use_existing", existing_id=uuid4()),
        },
    )
    bad_plan = build_preview_plan(
        _session(db),
        csv_bytes,
        SheetImportOptions(record_type="plants", mapping=mapping, choices=bad_choices),
        filename="ambig.csv",
    )
    assert bad_plan.can_apply is False
    assert all(g.status == "invalid" for g in bad_plan.identities)
    assert all(g.status == "invalid" for g in bad_plan.locations)
    assert all(g.status == "invalid" for g in bad_plan.suppliers)

    # Explicit valid use_existing + create with parent_id + incompatible use_existing location
    mixed_choices = SheetImportChoices(
        identities={
            "hoya carnosa|krimson": SheetImportIdentityChoice(
                action="use_existing", existing_id=id1.id
            ),
        },
        locations={
            "Bench": SheetImportLocationChoice(action="use_existing", existing_id=loc_b.id),
            "Seed Box": SheetImportLocationChoice(
                action="use_existing", existing_id=loc_seeds_only.id
            ),
        },
        suppliers={
            "Vivaio": SheetImportSupplierChoice(action="use_existing", existing_id=sup_a.id),
        },
    )
    mixed_plan = build_preview_plan(
        _session(db),
        csv_bytes,
        SheetImportOptions(record_type="plants", mapping=mapping, choices=mixed_choices),
        filename="ambig.csv",
    )
    assert mixed_plan.can_apply is False
    assert any(g.raw_value == "Bench" and g.status == "matched" for g in mixed_plan.locations)
    assert any(g.raw_value == "Seed Box" and g.status == "invalid" for g in mixed_plan.locations)
    assert any(g.raw_value == "Vivaio" and g.status == "matched" for g in mixed_plan.suppliers)

    # Invalid create names for location/supplier
    invalid_create = SheetImportChoices(
        locations={
            "Bench": SheetImportLocationChoice(action="create", name="   ", parent_id=loc_a.id),
            "Seed Box": SheetImportLocationChoice(action="skip"),
        },
        suppliers={
            "Vivaio": SheetImportSupplierChoice(action="create", name="   "),
        },
    )
    invalid_plan = build_preview_plan(
        _session(db),
        csv_bytes,
        SheetImportOptions(record_type="plants", mapping=mapping, choices=invalid_create),
        filename="ambig.csv",
    )
    assert invalid_plan.can_apply is False


def test_apply_sheet_unit_paths_and_api_handlers(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _FakeDatabase()
    data = (FIXTURES / "plants.csv").read_bytes()
    inspected = inspect_sheet(data, filename="plants.csv", record_type="plants")
    mapping = SheetImportMapping(columns={c.key: c.suggested_field for c in inspected.columns})
    options = SheetImportOptions(record_type="plants", mapping=mapping)

    # Fake create services mutate the FakeDatabase lists so fresh References(db) finds them!
    def fake_create_identity(target_db: Session, payload: object) -> BotanicalIdentity:
        from florabase.botanical_identities.schemas import BotanicalIdentityCreate

        assert isinstance(payload, BotanicalIdentityCreate)
        obj = BotanicalIdentity(
            id=uuid4(),
            scientific_name=payload.scientific_name,
            cultivar_name=payload.cultivar_name,
            common_name=payload.common_name,
        )
        cast(_FakeDatabase, target_db)._identities.append(obj)
        return obj

    def fake_create_supplier(target_db: Session, payload: object) -> Supplier:
        from florabase.suppliers.schemas import SupplierCreate

        assert isinstance(payload, SupplierCreate)
        obj = Supplier(id=uuid4(), name=payload.name, kind=payload.kind.value)
        cast(_FakeDatabase, target_db)._suppliers.append(obj)
        return obj

    def fake_create_location(target_db: Session, payload: object) -> Location:
        from florabase.locations.schemas import LocationCreate

        assert isinstance(payload, LocationCreate)
        obj = Location(
            id=uuid4(),
            name=payload.name,
            parent_id=payload.parent_id,
            supports_plants=True,
            supports_sowings=True,
            supports_seed_lots=True,
        )
        cast(_FakeDatabase, target_db)._locations.append(obj)
        return obj

    class _FakeCreated:
        def __init__(self, botanical_identity_id: object, label: str | None) -> None:
            self.id = uuid4()
            self.botanical_identity_id = botanical_identity_id
            self.label = label

    def fake_create_record(_db: Session, payload: object) -> _FakeCreated:
        from florabase.plants.schemas import PlantCreate, PlantGroupCreate
        from florabase.seed_lots.schemas import SeedLotCreate

        assert isinstance(payload, PlantCreate | PlantGroupCreate | SeedLotCreate)
        return _FakeCreated(payload.botanical_identity_id, payload.label)

    monkeypatch.setattr(
        "florabase.import_wizard.service.create_botanical_identity", fake_create_identity
    )
    monkeypatch.setattr("florabase.import_wizard.service.create_supplier", fake_create_supplier)
    monkeypatch.setattr("florabase.import_wizard.service.create_location", fake_create_location)
    monkeypatch.setattr("florabase.import_wizard.service.create_plant", fake_create_record)
    monkeypatch.setattr("florabase.import_wizard.service.create_plant_group", fake_create_record)
    monkeypatch.setattr("florabase.import_wizard.service.create_seed_lot", fake_create_record)

    result = apply_sheet(_session(db), data, options, filename="plants.csv")
    assert result.records_created == 2
    assert result.identities_created == 2
    assert result.locations_created == 2
    assert result.suppliers_created == 1

    # Also test plant-groups and seed-lots apply_sheet paths (reusing existing locations/suppliers).
    pg_data = (FIXTURES / "plant-groups.csv").read_bytes()
    pg_insp = inspect_sheet(pg_data, filename="plant-groups.csv", record_type="plant-groups")
    pg_opts = SheetImportOptions(
        record_type="plant-groups",
        mapping=SheetImportMapping(columns={c.key: c.suggested_field for c in pg_insp.columns}),
    )
    pg_res = apply_sheet(_session(db), pg_data, pg_opts, filename="plant-groups.csv")
    assert pg_res.records_created == 2

    sl_data = (FIXTURES / "seed-lots.csv").read_bytes()
    sl_insp = inspect_sheet(sl_data, filename="seed-lots.csv", record_type="seed-lots")
    sl_opts = SheetImportOptions(
        record_type="seed-lots",
        mapping=SheetImportMapping(columns={c.key: c.suggested_field for c in sl_insp.columns}),
    )
    sl_res = apply_sheet(_session(db), sl_data, sl_opts, filename="seed-lots.csv")
    assert sl_res.records_created == 2

    # Blocking sheet raises SheetImportConflictError on apply_sheet.
    bad_csv = b"Species\n\n"
    with pytest.raises(SheetFormatError):
        apply_sheet(
            _session(db),
            bad_csv,
            SheetImportOptions(
                record_type="plants",
                mapping=SheetImportMapping(columns={"col_0": SheetImportField.SCIENTIFIC_NAME}),
            ),
            filename="bad.csv",
        )

    # Direct API handler unit tests for inspect / preview / apply (success + error mappings).
    actor = _actor()
    options_json = options.model_dump_json()

    async def exercise_api() -> None:
        resp_inspect = await wizard_api.inspect_sheet_import(
            file=UploadFile(file=io.BytesIO(data), filename="plants.csv"),
            actor=actor,
            record_type="plants",
        )
        assert resp_inspect.row_count == 2

        with pytest.raises(HTTPException) as bad_inspect:
            await wizard_api.inspect_sheet_import(
                file=UploadFile(file=io.BytesIO(b""), filename="empty.csv"),
                actor=actor,
                record_type="plants",
            )
        assert bad_inspect.value.status_code == 422

        resp_preview = await wizard_api.preview_sheet_import(
            file=UploadFile(file=io.BytesIO(data), filename="plants.csv"),
            options=options_json,
            actor=actor,
            database=_session(db),
        )
        assert resp_preview.can_apply is True

        with pytest.raises(HTTPException) as bad_preview:
            await wizard_api.preview_sheet_import(
                file=UploadFile(file=io.BytesIO(b""), filename="empty.csv"),
                options=options_json,
                actor=actor,
                database=_session(db),
            )
        assert bad_preview.value.status_code == 422

        # Missing/bad confirmation token -> 409
        with pytest.raises(HTTPException) as bad_token:
            await wizard_api.apply_sheet_import(
                file=UploadFile(file=io.BytesIO(data), filename="plants.csv"),
                options=options_json,
                actor=actor,
                database=_session(db),
                confirmation_token="invalid",
            )
        assert bad_token.value.status_code == 409

        # Successful apply commits DB
        fresh_db = _FakeDatabase()
        resp_apply = await wizard_api.apply_sheet_import(
            file=UploadFile(file=io.BytesIO(data), filename="plants.csv"),
            options=options_json,
            actor=actor,
            database=_session(fresh_db),
            confirmation_token=resp_preview.confirmation_token,
        )
        assert resp_apply.records_created == 2
        assert fresh_db.committed is True

        # Conflict error rolls back and returns 409
        monkeypatch.setattr(
            "florabase.import_wizard.api.apply_sheet",
            lambda *_a, **_kw: (_ for _ in ()).throw(SheetImportConflictError("stale")),
        )
        err_db = _FakeDatabase()
        with pytest.raises(HTTPException) as conflict_exc:
            await wizard_api.apply_sheet_import(
                file=UploadFile(file=io.BytesIO(data), filename="plants.csv"),
                options=options_json,
                actor=actor,
                database=_session(err_db),
                confirmation_token=resp_preview.confirmation_token,
            )
        assert conflict_exc.value.status_code == 409
        assert err_db.rolled_back is True

    asyncio.run(exercise_api())
