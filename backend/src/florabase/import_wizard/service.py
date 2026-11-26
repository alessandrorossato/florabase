"""Single-sheet import wizard service reusing IMPORT-001 validation and domain create services."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid5

from pydantic import ValidationError
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import BotanicalIdentityCreate
from florabase.botanical_identities.service import create_botanical_identity
from florabase.import_export.service import (
    COLUMNS,
    PendingReference,
    PreviewRow,
    References,
    _candidate_details,
    _validation_message,
    build_rows,
    identity_label,
    identity_label_from_payload,
)
from florabase.import_wizard.mapping import (
    ALLOWED_FIELDS_BY_TYPE,
    SheetImportField,
    SheetImportRecordType,
    parse_approximate_flag,
    suggest_mapping,
)
from florabase.import_wizard.schemas import (
    SheetImportApplyResponse,
    SheetImportCandidate,
    SheetImportColumn,
    SheetImportCreatedRecord,
    SheetImportIdentityGroup,
    SheetImportInspectResponse,
    SheetImportLocationGroup,
    SheetImportOptions,
    SheetImportPreviewResponse,
    SheetImportPreviewRow,
    SheetImportSupplierGroup,
)
from florabase.import_wizard.sheet import ParsedRow, ParsedSheet, SheetFormatError, parse_sheet
from florabase.locations.model import Location
from florabase.locations.schemas import LocationCreate, LocationUsageScope
from florabase.locations.service import create_location
from florabase.locations.service import display_path as location_path
from florabase.plants.schemas import PlantCreate, PlantGroupCreate
from florabase.plants.service import create_plant, create_plant_group
from florabase.seed_lots.schemas import SeedLotCreate
from florabase.seed_lots.service import create_seed_lot
from florabase.suppliers.model import SupplierKind
from florabase.suppliers.schemas import SupplierCreate
from florabase.suppliers.service import create_supplier

_PENDING_NAMESPACE = UUID("8b70d52b-f5e6-49a5-8d2f-b9b24e334572")
_SAMPLE_LIMIT = 3
_DEFAULT_LOCATION_SCOPES: set[LocationUsageScope] = {
    LocationUsageScope.PLANTS,
    LocationUsageScope.SOWINGS,
    LocationUsageScope.SEED_LOTS,
    LocationUsageScope.HARVEST_INVENTORY,
}


class SheetImportConflictError(ValueError):
    """Raised when apply detects blocking rows or concurrent collection state changes."""


def _pending_id(category: str, key: str) -> str:
    return str(uuid5(_PENDING_NAMESPACE, f"{category}:{key}"))


def _collapse(value: str) -> str:
    return " ".join(value.split())


def _normalize_path_for_near_match(value: str) -> str:
    parts = [
        part.strip().casefold() for part in re.split(r"\s*(?:→|/|>|\\)\s*", value) if part.strip()
    ]
    return " / ".join(parts)


def _strip_cultivar_quotes(value: str) -> str:
    normalized = _collapse(value)
    if len(normalized) < 2:
        return normalized
    pairs = {("'", "'"), ('"', '"'), ("\u2018", "\u2019"), ("\u201c", "\u201d")}
    if (normalized[0], normalized[-1]) in pairs:
        return _collapse(normalized[1:-1])
    return normalized


def _identity_key_and_parts(
    scientific_name: str, cultivar_name: str
) -> tuple[str, str, str | None, str]:
    norm_sci = _collapse(scientific_name)
    norm_cult = _strip_cultivar_quotes(cultivar_name) if cultivar_name else ""
    cult_or_none = norm_cult or None
    display = norm_sci + (f"|{cult_or_none}" if cult_or_none else "")
    return display.casefold(), norm_sci, cult_or_none, display


def _location_supports(location: Location, record_type: SheetImportRecordType) -> bool:
    if record_type == "seed-lots":
        return bool(location.supports_seed_lots)
    return bool(location.supports_plants)


def _validate_mapping(
    parsed: ParsedSheet, options: SheetImportOptions
) -> dict[SheetImportField, str]:
    column_keys = {column.key for column in parsed.columns}
    allowed = set(ALLOWED_FIELDS_BY_TYPE[options.record_type])
    field_to_column: dict[SheetImportField, str] = {}
    for col_key, target_field in options.mapping.columns.items():
        if col_key not in column_keys:
            raise SheetFormatError(f'Unknown column key "{col_key}" in mapping')
        if target_field is None:
            continue
        if target_field not in allowed:
            raise SheetFormatError(
                f'Field "{target_field.value}" is not supported for {options.record_type}'
            )
        if target_field in field_to_column:
            raise SheetFormatError(
                f'Field "{target_field.value}" is mapped to more than one column'
            )
        field_to_column[target_field] = col_key
    if SheetImportField.SCIENTIFIC_NAME not in field_to_column:
        raise SheetFormatError("Map a column to scientific_name before previewing")
    return field_to_column


def inspect_sheet(
    data: bytes,
    *,
    filename: str | None = None,
    sheet_name: str | None = None,
    header_row: int | None = None,
    record_type: SheetImportRecordType = "plants",
) -> SheetImportInspectResponse:
    parsed = parse_sheet(
        data,
        filename=filename,
        sheet_name=sheet_name,
        header_row=header_row,
    )
    suggested = suggest_mapping(parsed.columns, record_type)
    sample_source_rows = parsed.rows[:_SAMPLE_LIMIT]
    columns_out: list[SheetImportColumn] = []
    for column in parsed.columns:
        samples = [
            "(formula)" if row.cells[column.key].uncached_formula else row.cells[column.key].text
            for row in sample_source_rows
        ]
        columns_out.append(
            SheetImportColumn(
                index=column.index,
                key=column.key,
                header=column.header,
                samples=samples,
                suggested_field=suggested.get(column.key),
            )
        )
    sample_rows = [
        [
            "(formula)" if row.cells[column.key].uncached_formula else row.cells[column.key].text
            for column in parsed.columns
        ]
        for row in sample_source_rows
    ]
    return SheetImportInspectResponse(
        format=parsed.format,
        sheets=parsed.sheets,
        selected_sheet=parsed.selected_sheet,
        detected_header_row=parsed.detected_header_row,
        header_row=parsed.header_row,
        row_count=len(parsed.rows),
        columns=columns_out,
        sample_rows=sample_rows,
        allowed_fields=list(ALLOWED_FIELDS_BY_TYPE[record_type]),
    )


@dataclass
class _ExtractedRow:
    parsed_row: ParsedRow
    identity_key: str | None
    identity_display: str
    location_key: str | None
    supplier_key: str | None
    base_fields: dict[str, str]
    extra_errors: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class SheetImportPlan:
    record_type: SheetImportRecordType
    parsed: ParsedSheet
    extracted_rows: list[_ExtractedRow]
    identities: list[SheetImportIdentityGroup]
    locations: list[SheetImportLocationGroup]
    suppliers: list[SheetImportSupplierGroup]
    identity_creates: dict[str, BotanicalIdentityCreate]
    location_creates: dict[str, LocationCreate]
    supplier_creates: dict[str, SupplierCreate]
    identity_refs: dict[str, str]
    location_refs: dict[str, str | None]
    supplier_refs: dict[str, str | None]
    skipped_locations: set[str]
    skipped_suppliers: set[str]
    group_errors_identity: dict[str, list[tuple[str, str]]]
    group_errors_location: dict[str, list[tuple[str, str]]]
    group_errors_supplier: dict[str, list[tuple[str, str]]]
    rows: list[PreviewRow]
    will_create_identities: int
    will_create_locations: int
    will_create_suppliers: int
    can_apply: bool


def _extract_rows(
    parsed: ParsedSheet,
    options: SheetImportOptions,
    field_to_col: dict[SheetImportField, str],
) -> list[_ExtractedRow]:
    col_by_key = {col.key: col for col in parsed.columns}
    mapped_col_keys = set(field_to_col.values())
    unmapped_columns = [col for col in parsed.columns if col.key not in mapped_col_keys]
    extracted: list[_ExtractedRow] = []

    for row in parsed.rows:
        errors: list[tuple[str, str]] = []
        values: dict[SheetImportField, str] = {}
        for target_field, col_key in field_to_col.items():
            cell = row.cells[col_key]
            if cell.uncached_formula:
                col_header = col_by_key[col_key].header
                errors.append(
                    (
                        "invalid",
                        f'Column "{col_header}" contains a formula without a cached value',
                    )
                )
                values[target_field] = ""
            else:
                values[target_field] = cell.text

        raw_sci = values.get(SheetImportField.SCIENTIFIC_NAME, "")
        raw_cult = values.get(SheetImportField.CULTIVAR_NAME, "")
        identity_key: str | None = None
        identity_display = ""
        if _collapse(raw_sci):
            identity_key, _sci, _cult, identity_display = _identity_key_and_parts(raw_sci, raw_cult)

        raw_loc = _collapse(values.get(SheetImportField.LOCATION, ""))
        location_key = raw_loc or None
        raw_sup = _collapse(values.get(SheetImportField.SUPPLIER, ""))
        supplier_key = raw_sup or None

        base: dict[str, str] = dict.fromkeys(COLUMNS[options.record_type], "")
        base["label"] = values.get(SheetImportField.LABEL, "").strip()
        base["lifecycle"] = values.get(SheetImportField.LIFECYCLE, "").strip()

        notes_parts: list[str] = []
        mapped_notes = values.get(SheetImportField.NOTES, "").strip()
        if mapped_notes:
            notes_parts.append(mapped_notes)
        if options.mapping.append_unmapped_to_notes:
            for col in unmapped_columns:
                cell = row.cells[col.key]
                if cell.uncached_formula:
                    continue
                val = cell.text.strip()
                if val:
                    notes_parts.append(f"{col.header}: {val}")
        base["notes"] = "\n".join(notes_parts)

        if options.record_type in {"plants", "plant-groups"}:
            base["collection_entry_date"] = values.get(
                SheetImportField.COLLECTION_ENTRY_DATE, ""
            ).strip()
            base["direct_origin_kind"] = values.get(SheetImportField.DIRECT_ORIGIN_KIND, "").strip()
            base["direct_origin_detail"] = values.get(
                SheetImportField.DIRECT_ORIGIN_DETAIL, ""
            ).strip()
            if options.record_type == "plant-groups":
                qty_val = values.get(SheetImportField.QUANTITY_VALUE, "").strip()
                qty_approx = values.get(SheetImportField.QUANTITY_APPROXIMATE, "").strip()
                base["quantity_value"] = qty_val
                if qty_val:
                    try:
                        base["quantity_certainty"] = parse_approximate_flag(qty_approx)
                    except ValueError as error:
                        errors.append(("invalid", str(error)))
                        base["quantity_certainty"] = "exact"
                else:
                    base["quantity_certainty"] = ""
        else:
            base["acquisition_date"] = values.get(SheetImportField.ACQUISITION_DATE, "").strip()
            base["harvest_date"] = values.get(SheetImportField.HARVEST_DATE, "").strip()
            base["expected_viability_until"] = values.get(
                SheetImportField.EXPECTED_VIABILITY_UNTIL, ""
            ).strip()
            base["source_kind"] = values.get(SheetImportField.SOURCE_KIND, "").strip()
            base["source_detail"] = values.get(SheetImportField.SOURCE_DETAIL, "").strip()
            qty_val = values.get(SheetImportField.QUANTITY_VALUE, "").strip()
            qty_approx = values.get(SheetImportField.QUANTITY_APPROXIMATE, "").strip()
            qty_kind = values.get(SheetImportField.QUANTITY_KIND, "").strip()
            qty_unit = values.get(SheetImportField.QUANTITY_UNIT, "").strip()
            base["quantity_value"] = qty_val
            if qty_val:
                base["quantity_kind"] = qty_kind or "seed_count"
                base["quantity_unit"] = qty_unit
                try:
                    base["quantity_certainty"] = parse_approximate_flag(qty_approx)
                except ValueError as error:
                    errors.append(("invalid", str(error)))
                    base["quantity_certainty"] = "exact"
            else:
                base["quantity_kind"] = qty_kind
                base["quantity_unit"] = qty_unit
                base["quantity_certainty"] = ""

        extracted.append(
            _ExtractedRow(
                parsed_row=row,
                identity_key=identity_key,
                identity_display=identity_display,
                location_key=location_key,
                supplier_key=supplier_key,
                base_fields=base,
                extra_errors=errors,
            )
        )
    return extracted


def _resolve_identities(
    extracted: list[_ExtractedRow],
    field_to_col: dict[SheetImportField, str],
    refs: References,
    options: SheetImportOptions,
) -> tuple[
    list[SheetImportIdentityGroup],
    dict[str, BotanicalIdentityCreate],
    dict[str, str],
    dict[str, PendingReference],
    dict[str, list[tuple[str, str]]],
    int,
]:
    existing_by_fold: dict[str, BotanicalIdentity] = {
        identity_label(item).casefold(): item for item in refs.identities
    }
    sci_col = field_to_col[SheetImportField.SCIENTIFIC_NAME]
    cult_col = field_to_col.get(SheetImportField.CULTIVAR_NAME)
    common_col = field_to_col.get(SheetImportField.COMMON_NAME)

    group_meta: dict[str, tuple[str, str | None, str | None]] = {}
    group_counts: dict[str, int] = defaultdict(int)
    for row in extracted:
        if row.identity_key is None:
            continue
        group_counts[row.identity_key] += 1
        raw_sci = row.parsed_row.cells[sci_col].text
        raw_cult = row.parsed_row.cells[cult_col].text if cult_col else ""
        raw_common = row.parsed_row.cells[common_col].text if common_col else ""
        _key, norm_sci, norm_cult, _display = _identity_key_and_parts(raw_sci, raw_cult)
        norm_common = _collapse(raw_common) or None
        if row.identity_key not in group_meta:
            group_meta[row.identity_key] = (norm_sci, norm_cult, norm_common)
        elif group_meta[row.identity_key][2] is None and norm_common is not None:
            sci_prev, cult_prev, _ = group_meta[row.identity_key]
            group_meta[row.identity_key] = (sci_prev, cult_prev, norm_common)

    groups: list[SheetImportIdentityGroup] = []
    creates: dict[str, BotanicalIdentityCreate] = {}
    ref_map: dict[str, str] = {}
    pending_entries: dict[str, PendingReference] = {}
    group_errors: dict[str, list[tuple[str, str]]] = {}
    unique_create_tuples: dict[str, PendingReference] = {}

    for key, (sci, cult, common) in group_meta.items():
        count = group_counts[key]
        choice = options.choices.identities.get(key)
        exact = existing_by_fold.get(key)
        candidates: list[SheetImportCandidate] = []
        if exact is not None:
            candidates.append(
                SheetImportCandidate(
                    id=exact.id,
                    label=identity_label(exact),
                    details=_candidate_details(exact, "identity"),
                    match_kind="exact",
                )
            )
        else:
            # Near-match suggestions sharing the same scientific name (e.g. different cultivar).
            sci_fold = sci.casefold()
            for item in refs.identities:
                if item.scientific_name.casefold() == sci_fold:
                    candidates.append(
                        SheetImportCandidate(
                            id=item.id,
                            label=identity_label(item),
                            details=_candidate_details(item, "identity"),
                            match_kind="near",
                        )
                    )

        if choice is not None and choice.action == "use_existing":
            target = (
                refs.ids["identity"].get(str(choice.existing_id)) if choice.existing_id else None
            )
            if target is None:
                msg = "Selected existing botanical identity was not found"
                group_errors[key] = [("unresolved_reference", f"identity: {msg}")]
                groups.append(
                    SheetImportIdentityGroup(
                        key=key,
                        scientific_name=sci,
                        cultivar_name=cult,
                        common_name=common,
                        row_count=count,
                        status="invalid",
                        action="use_existing",
                        candidates=candidates,
                        messages=[msg],
                    )
                )
            else:
                ref_map[key] = str(target.id)
                groups.append(
                    SheetImportIdentityGroup(
                        key=key,
                        scientific_name=sci,
                        cultivar_name=cult,
                        common_name=common,
                        row_count=count,
                        status="matched",
                        action="use_existing",
                        matched_id=target.id,
                        matched_label=identity_label(target),
                        candidates=candidates,
                    )
                )
            continue

        if choice is None and exact is not None:
            ref_map[key] = str(exact.id)
            groups.append(
                SheetImportIdentityGroup(
                    key=key,
                    scientific_name=sci,
                    cultivar_name=cult,
                    common_name=common,
                    row_count=count,
                    status="matched",
                    action="use_existing",
                    matched_id=exact.id,
                    matched_label=identity_label(exact),
                    candidates=candidates,
                )
            )
            continue

        # Create path (either default for new name, or explicit choice.action == "create").
        chosen_sci = (
            choice.scientific_name if (choice and choice.scientific_name is not None) else sci
        )
        chosen_cult = (
            choice.cultivar_name if (choice and choice.cultivar_name is not None) else cult
        )
        chosen_common = (
            choice.common_name if (choice and choice.common_name is not None) else common
        )
        try:
            validated = BotanicalIdentityCreate.model_validate(
                {
                    "scientific_name": chosen_sci,
                    "cultivar_name": chosen_cult,
                    "common_name": chosen_common,
                }
            )
        except ValidationError as error:
            msg = _validation_message(error)
            group_errors[key] = [("invalid", f"identity: {msg}")]
            groups.append(
                SheetImportIdentityGroup(
                    key=key,
                    scientific_name=chosen_sci,
                    cultivar_name=chosen_cult,
                    common_name=chosen_common,
                    row_count=count,
                    status="invalid",
                    action="create",
                    candidates=candidates,
                    messages=[msg],
                )
            )
            continue

        new_label = identity_label_from_payload(validated.model_dump())
        new_fold = new_label.casefold()
        colliding = existing_by_fold.get(new_fold)
        if colliding is not None:
            msg = (
                f'Botanical identity "{identity_label(colliding)}" already exists; '
                "choose Use existing instead"
            )
            group_errors[key] = [("conflict", f"identity: {msg}")]
            groups.append(
                SheetImportIdentityGroup(
                    key=key,
                    scientific_name=validated.scientific_name,
                    cultivar_name=validated.cultivar_name,
                    common_name=validated.common_name,
                    row_count=count,
                    status="invalid",
                    action="create",
                    matched_id=colliding.id,
                    matched_label=identity_label(colliding),
                    candidates=candidates,
                    messages=[msg],
                )
            )
            continue

        if new_fold in unique_create_tuples:
            pending_ref = unique_create_tuples[new_fold]
        else:
            pending_ref = PendingReference(
                id=_pending_id("identity", new_fold),
                label=new_label,
            )
            unique_create_tuples[new_fold] = pending_ref
            pending_entries[pending_ref.id] = pending_ref
        creates[key] = validated
        ref_map[key] = pending_ref.id
        groups.append(
            SheetImportIdentityGroup(
                key=key,
                scientific_name=validated.scientific_name,
                cultivar_name=validated.cultivar_name,
                common_name=validated.common_name,
                row_count=count,
                status="new",
                action="create",
                candidates=candidates,
            )
        )

    return groups, creates, ref_map, pending_entries, group_errors, len(unique_create_tuples)


def _resolve_locations(
    extracted: list[_ExtractedRow],
    refs: References,
    options: SheetImportOptions,
) -> tuple[
    list[SheetImportLocationGroup],
    dict[str, LocationCreate],
    dict[str, str | None],
    dict[str, PendingReference],
    set[str],
    dict[str, list[tuple[str, str]]],
]:
    counts: dict[str, int] = defaultdict(int)
    ordered_keys: list[str] = []
    for row in extracted:
        if row.location_key is None:
            continue
        if row.location_key not in counts:
            ordered_keys.append(row.location_key)
        counts[row.location_key] += 1

    active_locations = [loc for loc in refs.locations if loc.retired_at is None]
    loc_paths = {loc.id: location_path(loc, refs.locations) for loc in active_locations}

    groups: list[SheetImportLocationGroup] = []
    creates: dict[str, LocationCreate] = {}
    ref_map: dict[str, str | None] = {}
    pending_entries: dict[str, PendingReference] = {}
    skipped: set[str] = set()
    group_errors: dict[str, list[tuple[str, str]]] = {}

    for raw_value in ordered_keys:
        count = counts[raw_value]
        choice = options.choices.locations.get(raw_value)
        exact_matches = [
            loc for loc in refs.names["location"].get(raw_value, []) if loc.retired_at is None
        ]
        exact_ids = {loc.id for loc in exact_matches}
        norm_raw_path = _normalize_path_for_near_match(raw_value)
        raw_fold = raw_value.casefold()

        candidates: list[SheetImportCandidate] = [
            SheetImportCandidate(
                id=loc.id,
                label=loc_paths[loc.id],
                details=_candidate_details(loc, "location"),
                match_kind="exact",
            )
            for loc in exact_matches
        ]
        for loc in active_locations:
            if loc.id in exact_ids:
                continue
            path_str = loc_paths[loc.id]
            if (
                path_str.casefold() == raw_fold
                or loc.name.casefold() == raw_fold
                or _normalize_path_for_near_match(path_str) == norm_raw_path
            ):
                candidates.append(
                    SheetImportCandidate(
                        id=loc.id,
                        label=path_str,
                        details=_candidate_details(loc, "location"),
                        match_kind="near",
                    )
                )

        if choice is not None and choice.action == "skip":
            skipped.add(raw_value)
            ref_map[raw_value] = None
            groups.append(
                SheetImportLocationGroup(
                    key=raw_value,
                    raw_value=raw_value,
                    row_count=count,
                    status="skipped",
                    action="skip",
                    candidates=candidates,
                    messages=["Location will be left empty"],
                )
            )
            continue

        if choice is not None and choice.action == "use_existing":
            target = (
                refs.ids["location"].get(str(choice.existing_id)) if choice.existing_id else None
            )
            if target is None or target.retired_at is not None:
                msg = "Selected existing location was not found or is retired"
                group_errors[raw_value] = [("unresolved_reference", f"location: {msg}")]
                groups.append(
                    SheetImportLocationGroup(
                        key=raw_value,
                        raw_value=raw_value,
                        row_count=count,
                        status="invalid",
                        action="use_existing",
                        candidates=candidates,
                        messages=[msg],
                    )
                )
            elif not _location_supports(target, options.record_type):
                msg = f"Location does not support {options.record_type} assignments"
                ref_map[raw_value] = str(target.id)
                groups.append(
                    SheetImportLocationGroup(
                        key=raw_value,
                        raw_value=raw_value,
                        row_count=count,
                        status="invalid",
                        action="use_existing",
                        matched_id=target.id,
                        matched_label=location_path(target, refs.locations),
                        candidates=candidates,
                        messages=[msg],
                    )
                )
            else:
                ref_map[raw_value] = str(target.id)
                groups.append(
                    SheetImportLocationGroup(
                        key=raw_value,
                        raw_value=raw_value,
                        row_count=count,
                        status="matched",
                        action="use_existing",
                        matched_id=target.id,
                        matched_label=location_path(target, refs.locations),
                        candidates=candidates,
                    )
                )
            continue

        if choice is None and len(exact_matches) == 1:
            target = exact_matches[0]
            ref_map[raw_value] = str(target.id)
            if not _location_supports(target, options.record_type):
                msg = f"Location does not support {options.record_type} assignments"
                groups.append(
                    SheetImportLocationGroup(
                        key=raw_value,
                        raw_value=raw_value,
                        row_count=count,
                        status="invalid",
                        action="use_existing",
                        matched_id=target.id,
                        matched_label=loc_paths[target.id],
                        candidates=candidates,
                        messages=[msg],
                    )
                )
            else:
                groups.append(
                    SheetImportLocationGroup(
                        key=raw_value,
                        raw_value=raw_value,
                        row_count=count,
                        status="matched",
                        action="use_existing",
                        matched_id=target.id,
                        matched_label=loc_paths[target.id],
                        candidates=candidates,
                    )
                )
            continue

        if choice is None and len(exact_matches) > 1:
            msg = (
                f'Multiple existing locations match "{raw_value}"; choose one, create new, or skip'
            )
            group_errors[raw_value] = [("ambiguous_reference", f"location: {msg}")]
            groups.append(
                SheetImportLocationGroup(
                    key=raw_value,
                    raw_value=raw_value,
                    row_count=count,
                    status="ambiguous",
                    action="use_existing",
                    candidates=candidates,
                    messages=[msg],
                )
            )
            continue

        # Create path (either default for 0 exact matches, or explicit choice.action == "create").
        create_name = choice.name if (choice and choice.name is not None) else raw_value
        parent_id = choice.parent_id if choice is not None else None
        parent_label = ""
        if parent_id is not None:
            parent_loc = refs.ids["location"].get(str(parent_id))
            if parent_loc is None or parent_loc.retired_at is not None:
                msg = "Selected parent location was not found or is retired"
                group_errors[raw_value] = [("unresolved_reference", f"location: {msg}")]
                groups.append(
                    SheetImportLocationGroup(
                        key=raw_value,
                        raw_value=raw_value,
                        row_count=count,
                        status="invalid",
                        action="create",
                        create_name=create_name,
                        parent_id=parent_id,
                        candidates=candidates,
                        messages=[msg],
                    )
                )
                continue
            parent_label = location_path(parent_loc, refs.locations)

        try:
            validated = LocationCreate.model_validate(
                {
                    "name": create_name,
                    "parent_id": parent_id,
                    "usage_scopes": _DEFAULT_LOCATION_SCOPES,
                }
            )
        except ValidationError as error:
            msg = _validation_message(error)
            group_errors[raw_value] = [("invalid", f"location: {msg}")]
            groups.append(
                SheetImportLocationGroup(
                    key=raw_value,
                    raw_value=raw_value,
                    row_count=count,
                    status="invalid",
                    action="create",
                    create_name=create_name,
                    parent_id=parent_id,
                    candidates=candidates,
                    messages=[msg],
                )
            )
            continue

        display_new = f"{parent_label} → {validated.name}" if parent_label else validated.name
        pending_ref = PendingReference(
            id=_pending_id("location", raw_value),
            label=display_new,
            supports_plants=LocationUsageScope.PLANTS in validated.usage_scopes,
            supports_seed_lots=LocationUsageScope.SEED_LOTS in validated.usage_scopes,
        )
        creates[raw_value] = validated
        ref_map[raw_value] = pending_ref.id
        pending_entries[pending_ref.id] = pending_ref
        groups.append(
            SheetImportLocationGroup(
                key=raw_value,
                raw_value=raw_value,
                row_count=count,
                status="new",
                action="create",
                create_name=validated.name,
                parent_id=validated.parent_id,
                candidates=candidates,
            )
        )

    return groups, creates, ref_map, pending_entries, skipped, group_errors


def _resolve_suppliers(
    extracted: list[_ExtractedRow],
    refs: References,
    options: SheetImportOptions,
) -> tuple[
    list[SheetImportSupplierGroup],
    dict[str, SupplierCreate],
    dict[str, str | None],
    dict[str, PendingReference],
    set[str],
    dict[str, list[tuple[str, str]]],
]:
    counts: dict[str, int] = defaultdict(int)
    ordered_keys: list[str] = []
    for row in extracted:
        if row.supplier_key is None:
            continue
        if row.supplier_key not in counts:
            ordered_keys.append(row.supplier_key)
        counts[row.supplier_key] += 1

    active_suppliers = [sup for sup in refs.suppliers if sup.retired_at is None]

    groups: list[SheetImportSupplierGroup] = []
    creates: dict[str, SupplierCreate] = {}
    ref_map: dict[str, str | None] = {}
    pending_entries: dict[str, PendingReference] = {}
    skipped: set[str] = set()
    group_errors: dict[str, list[tuple[str, str]]] = {}

    for raw_value in ordered_keys:
        count = counts[raw_value]
        choice = options.choices.suppliers.get(raw_value)
        exact_matches = [
            sup for sup in refs.names["supplier"].get(raw_value, []) if sup.retired_at is None
        ]
        exact_ids = {sup.id for sup in exact_matches}
        raw_fold = raw_value.casefold()

        candidates: list[SheetImportCandidate] = [
            SheetImportCandidate(
                id=sup.id,
                label=sup.name,
                details=_candidate_details(sup, "supplier"),
                match_kind="exact",
            )
            for sup in exact_matches
        ]
        for sup in active_suppliers:
            if sup.id in exact_ids:
                continue
            if sup.name.casefold() == raw_fold:
                candidates.append(
                    SheetImportCandidate(
                        id=sup.id,
                        label=sup.name,
                        details=_candidate_details(sup, "supplier"),
                        match_kind="near",
                    )
                )

        if choice is not None and choice.action == "skip":
            skipped.add(raw_value)
            ref_map[raw_value] = None
            groups.append(
                SheetImportSupplierGroup(
                    key=raw_value,
                    raw_value=raw_value,
                    row_count=count,
                    status="skipped",
                    action="skip",
                    candidates=candidates,
                    messages=["Supplier will be left empty"],
                )
            )
            continue

        if choice is not None and choice.action == "use_existing":
            target = (
                refs.ids["supplier"].get(str(choice.existing_id)) if choice.existing_id else None
            )
            if target is None or target.retired_at is not None:
                msg = "Selected existing supplier was not found or is retired"
                group_errors[raw_value] = [("unresolved_reference", f"supplier: {msg}")]
                groups.append(
                    SheetImportSupplierGroup(
                        key=raw_value,
                        raw_value=raw_value,
                        row_count=count,
                        status="invalid",
                        action="use_existing",
                        candidates=candidates,
                        messages=[msg],
                    )
                )
            else:
                ref_map[raw_value] = str(target.id)
                groups.append(
                    SheetImportSupplierGroup(
                        key=raw_value,
                        raw_value=raw_value,
                        row_count=count,
                        status="matched",
                        action="use_existing",
                        matched_id=target.id,
                        matched_label=target.name,
                        candidates=candidates,
                    )
                )
            continue

        if choice is None and len(exact_matches) == 1:
            target = exact_matches[0]
            ref_map[raw_value] = str(target.id)
            groups.append(
                SheetImportSupplierGroup(
                    key=raw_value,
                    raw_value=raw_value,
                    row_count=count,
                    status="matched",
                    action="use_existing",
                    matched_id=target.id,
                    matched_label=target.name,
                    candidates=candidates,
                )
            )
            continue

        if choice is None and len(exact_matches) > 1:
            msg = (
                f'Multiple existing suppliers match "{raw_value}"; choose one, create new, or skip'
            )
            group_errors[raw_value] = [("ambiguous_reference", f"supplier: {msg}")]
            groups.append(
                SheetImportSupplierGroup(
                    key=raw_value,
                    raw_value=raw_value,
                    row_count=count,
                    status="ambiguous",
                    action="use_existing",
                    candidates=candidates,
                    messages=[msg],
                )
            )
            continue

        create_name = choice.name if (choice and choice.name is not None) else raw_value
        kind = choice.kind if choice is not None else SupplierKind.OTHER
        try:
            validated = SupplierCreate.model_validate({"name": create_name, "kind": kind})
        except ValidationError as error:
            msg = _validation_message(error)
            group_errors[raw_value] = [("invalid", f"supplier: {msg}")]
            groups.append(
                SheetImportSupplierGroup(
                    key=raw_value,
                    raw_value=raw_value,
                    row_count=count,
                    status="invalid",
                    action="create",
                    create_name=create_name,
                    kind=kind,
                    candidates=candidates,
                    messages=[msg],
                )
            )
            continue

        pending_ref = PendingReference(
            id=_pending_id("supplier", raw_value),
            label=f"{validated.name} ({validated.kind.value})",
        )
        creates[raw_value] = validated
        ref_map[raw_value] = pending_ref.id
        pending_entries[pending_ref.id] = pending_ref
        groups.append(
            SheetImportSupplierGroup(
                key=raw_value,
                raw_value=raw_value,
                row_count=count,
                status="new",
                action="create",
                create_name=validated.name,
                kind=validated.kind,
                candidates=candidates,
            )
        )

    return groups, creates, ref_map, pending_entries, skipped, group_errors


def _canonical_sources(
    extracted: list[_ExtractedRow],
    identity_refs: dict[str, str],
    location_refs: dict[str, str | None],
    supplier_refs: dict[str, str | None],
) -> list[tuple[int, dict[str, str]]]:
    sources: list[tuple[int, dict[str, str]]] = []
    for row in extracted:
        source = dict(row.base_fields)
        source["identity_ref"] = (
            identity_refs.get(row.identity_key, "") if row.identity_key is not None else ""
        )
        source["location_ref"] = (
            (location_refs.get(row.location_key) or "") if row.location_key is not None else ""
        )
        source["supplier_ref"] = (
            (supplier_refs.get(row.supplier_key) or "") if row.supplier_key is not None else ""
        )
        sources.append((row.parsed_row.row_number, source))
    return sources


def build_preview_plan(
    database: Session,
    data: bytes,
    options: SheetImportOptions,
    *,
    filename: str | None = None,
) -> SheetImportPlan:
    parsed = parse_sheet(
        data,
        filename=filename,
        sheet_name=options.sheet_name,
        header_row=options.header_row,
    )
    field_to_col = _validate_mapping(parsed, options)
    extracted = _extract_rows(parsed, options, field_to_col)
    base_refs = References(database)

    (
        identity_groups,
        identity_creates,
        identity_refs,
        pending_identities,
        identity_errors,
        unique_identity_creates,
    ) = _resolve_identities(extracted, field_to_col, base_refs, options)
    (
        location_groups,
        location_creates,
        location_refs,
        pending_locations,
        skipped_locations,
        location_errors,
    ) = _resolve_locations(extracted, base_refs, options)
    (
        supplier_groups,
        supplier_creates,
        supplier_refs,
        pending_suppliers,
        skipped_suppliers,
        supplier_errors,
    ) = _resolve_suppliers(extracted, base_refs, options)

    pending_refs = References(
        database,
        pending={
            "identity": pending_identities,
            "location": pending_locations,
            "supplier": pending_suppliers,
        },
    )
    sources = _canonical_sources(extracted, identity_refs, location_refs, supplier_refs)
    rows = build_rows(options.record_type, sources, pending_refs)

    for ext, row in zip(extracted, rows, strict=True):
        if not ext.base_fields["label"] and ext.identity_display:
            row.record = ext.identity_display[:255]
        for outcome, message in ext.extra_errors:
            row.issue(outcome, message)
        if ext.identity_key and ext.identity_key in identity_errors:
            # Replace the generic unresolved identity error if a specific group error explains it.
            row.messages = [msg for msg in row.messages if msg != "identity: reference is required"]
            for outcome, message in identity_errors[ext.identity_key]:
                row.issue(outcome, message)
        if ext.location_key and ext.location_key in location_errors:
            for outcome, message in location_errors[ext.location_key]:
                row.issue(outcome, message)
        if ext.supplier_key and ext.supplier_key in supplier_errors:
            for outcome, message in supplier_errors[ext.supplier_key]:
                row.issue(outcome, message)
        if ext.location_key and ext.location_key in skipped_locations:
            row.references.append("location: skipped (location will be left empty)")
        if ext.supplier_key and ext.supplier_key in skipped_suppliers:
            row.references.append("supplier: skipped (supplier will be left empty)")

    all_groups_ok = (
        all(group.status in {"matched", "new"} for group in identity_groups)
        and all(group.status in {"matched", "new", "skipped"} for group in location_groups)
        and all(group.status in {"matched", "new", "skipped"} for group in supplier_groups)
    )
    can_apply = bool(rows) and all_groups_ok and all(row.outcome == "ready" for row in rows)

    return SheetImportPlan(
        record_type=options.record_type,
        parsed=parsed,
        extracted_rows=extracted,
        identities=identity_groups,
        locations=location_groups,
        suppliers=supplier_groups,
        identity_creates=identity_creates,
        location_creates=location_creates,
        supplier_creates=supplier_creates,
        identity_refs=identity_refs,
        location_refs=location_refs,
        supplier_refs=supplier_refs,
        skipped_locations=skipped_locations,
        skipped_suppliers=skipped_suppliers,
        group_errors_identity=identity_errors,
        group_errors_location=location_errors,
        group_errors_supplier=supplier_errors,
        rows=rows,
        will_create_identities=unique_identity_creates,
        will_create_locations=len(location_creates),
        will_create_suppliers=len(supplier_creates),
        can_apply=can_apply,
    )


def preview_response_from_plan(
    plan: SheetImportPlan, confirmation_token: str
) -> SheetImportPreviewResponse:
    public_rows = [
        SheetImportPreviewRow.model_validate(
            {
                "row_number": row.row_number,
                "record": row.record,
                "outcome": row.outcome,
                "messages": row.messages,
                "references": row.references,
                "normalized": row.normalized,
                "hard_blocker": row.hard_blocker,
            }
        )
        for row in plan.rows
    ]
    ready = sum(row.outcome == "ready" for row in plan.rows)
    invalid = sum(row.outcome == "invalid" for row in plan.rows)
    needs_attention = sum(row.outcome != "ready" for row in plan.rows)
    return SheetImportPreviewResponse(
        record_type=plan.record_type,
        identities=plan.identities,
        locations=plan.locations,
        suppliers=plan.suppliers,
        rows=public_rows,
        ready=ready,
        needs_attention=needs_attention,
        invalid=invalid,
        will_create_identities=plan.will_create_identities,
        will_create_locations=plan.will_create_locations,
        will_create_suppliers=plan.will_create_suppliers,
        can_apply=plan.can_apply,
        confirmation_token=confirmation_token,
    )


def preview_state_digest(plan: SheetImportPlan) -> str:
    """Deterministic SHA-256 digest of the confirmed preview decision state."""
    payload = {
        "identities": [
            {
                "key": g.key,
                "action": g.action,
                "matched_id": str(g.matched_id) if g.matched_id is not None else None,
            }
            for g in plan.identities
        ],
        "locations": [
            {
                "key": g.key,
                "action": g.action,
                "matched_id": str(g.matched_id) if g.matched_id is not None else None,
            }
            for g in plan.locations
        ],
        "suppliers": [
            {
                "key": g.key,
                "action": g.action,
                "matched_id": str(g.matched_id) if g.matched_id is not None else None,
            }
            for g in plan.suppliers
        ],
        "row_count": len(plan.rows),
        "row_outcomes": [[row.row_number, row.outcome] for row in plan.rows],
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def apply_sheet(
    database: Session,
    data: bytes,
    options: SheetImportOptions,
    *,
    filename: str | None = None,
    expected_preview_digest: str | None = None,
) -> SheetImportApplyResponse:
    plan = build_preview_plan(database, data, options, filename=filename)
    if expected_preview_digest is not None and not hmac.compare_digest(
        preview_state_digest(plan), expected_preview_digest
    ):
        raise SheetImportConflictError("Collection state changed since preview; validate again")
    if not plan.can_apply:
        raise SheetImportConflictError("Spreadsheet needs attention; run preview again")

    # 1. Create botanical identities (deduplicated by casefolded tuple).
    real_identity_refs: dict[str, str] = {}
    created_by_tuple: dict[str, BotanicalIdentity] = {}
    identities_created = 0
    for id_group in plan.identities:
        if id_group.action == "use_existing":
            assert id_group.matched_id is not None
            real_identity_refs[id_group.key] = str(id_group.matched_id)
            continue
        payload = plan.identity_creates[id_group.key]
        tuple_key = identity_label_from_payload(payload.model_dump()).casefold()
        if tuple_key not in created_by_tuple:
            created_by_tuple[tuple_key] = create_botanical_identity(database, payload)
            identities_created += 1
        real_identity_refs[id_group.key] = str(created_by_tuple[tuple_key].id)

    # 2. Create suppliers.
    real_supplier_refs: dict[str, str | None] = {}
    suppliers_created = 0
    for sup_group in plan.suppliers:
        if sup_group.action == "skip":
            real_supplier_refs[sup_group.key] = None
        elif sup_group.action == "use_existing":
            assert sup_group.matched_id is not None
            real_supplier_refs[sup_group.key] = str(sup_group.matched_id)
        else:
            created_supplier = create_supplier(database, plan.supplier_creates[sup_group.key])
            real_supplier_refs[sup_group.key] = str(created_supplier.id)
            suppliers_created += 1

    # 3. Create locations.
    real_location_refs: dict[str, str | None] = {}
    locations_created = 0
    for loc_group in plan.locations:
        if loc_group.action == "skip":
            real_location_refs[loc_group.key] = None
        elif loc_group.action == "use_existing":
            assert loc_group.matched_id is not None
            real_location_refs[loc_group.key] = str(loc_group.matched_id)
        else:
            created_location = create_location(database, plan.location_creates[loc_group.key])
            real_location_refs[loc_group.key] = str(created_location.id)
            locations_created += 1

    database.flush()

    # 4. Rebuild References from the DB (no pending refs) and re-run build_rows.
    # If any row outcome differs from the confirmed preview, roll back and return 409.
    fresh_refs = References(database)
    real_sources = _canonical_sources(
        plan.extracted_rows, real_identity_refs, real_location_refs, real_supplier_refs
    )
    actual_rows = build_rows(plan.record_type, real_sources, fresh_refs)
    if len(actual_rows) != len(plan.rows) or any(
        actual.outcome != expected.outcome or actual.outcome != "ready" or actual.payload is None
        for actual, expected in zip(actual_rows, plan.rows, strict=True)
    ):
        raise SheetImportConflictError(
            "Collection state changed during import; validate the spreadsheet again"
        )

    # 5. Create collection records via existing domain services.
    created_records: list[SheetImportCreatedRecord] = []
    for row in actual_rows:
        assert row.payload is not None
        created_obj: Any
        if plan.record_type == "plants":
            created_obj = create_plant(database, PlantCreate.model_validate(row.payload))
        elif plan.record_type == "plant-groups":
            created_obj = create_plant_group(database, PlantGroupCreate.model_validate(row.payload))
        else:
            created_obj = create_seed_lot(database, SeedLotCreate.model_validate(row.payload))
        identity_obj = fresh_refs.ids["identity"][str(created_obj.botanical_identity_id)]
        id_label = identity_label(identity_obj)
        created_records.append(
            SheetImportCreatedRecord(
                id=created_obj.id,
                label=created_obj.label or id_label,
                identity_label=id_label,
            )
        )

    return SheetImportApplyResponse(
        record_type=plan.record_type,
        records_created=len(created_records),
        identities_created=identities_created,
        locations_created=locations_created,
        suppliers_created=suppliers_created,
        created_records=created_records,
    )
