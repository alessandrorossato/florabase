"""Pydantic schemas for the single-sheet spreadsheet import wizard."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from florabase.import_wizard.mapping import SheetImportField, SheetImportRecordType
from florabase.import_wizard.sheet import SheetFormat
from florabase.suppliers.model import SupplierKind

SheetImportRowOutcome = Literal[
    "ready",
    "already_exists",
    "needs_choice",
    "invalid",
    "unresolved_reference",
    "ambiguous_reference",
    "conflict",
]


class SheetImportPreviewRow(BaseModel):
    row_number: int
    record: str
    outcome: SheetImportRowOutcome
    messages: list[str]
    references: list[str]
    normalized: list[str]
    hard_blocker: bool


class SheetImportColumn(BaseModel):
    index: int
    key: str
    header: str
    samples: list[str]
    suggested_field: SheetImportField | None


class SheetImportInspectResponse(BaseModel):
    format: SheetFormat
    sheets: list[str]
    selected_sheet: str | None
    detected_header_row: int
    header_row: int
    row_count: int
    columns: list[SheetImportColumn]
    sample_rows: list[list[str]]
    allowed_fields: list[SheetImportField]


class SheetImportMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")

    columns: dict[str, SheetImportField | None]
    append_unmapped_to_notes: bool = False


class SheetImportIdentityChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["use_existing", "create"]
    existing_id: UUID | None = None
    scientific_name: str | None = None
    cultivar_name: str | None = None
    common_name: str | None = None


class SheetImportLocationChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["use_existing", "create", "skip"]
    existing_id: UUID | None = None
    name: str | None = None
    parent_id: UUID | None = None


class SheetImportSupplierChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["use_existing", "create", "skip"]
    existing_id: UUID | None = None
    name: str | None = None
    kind: SupplierKind = SupplierKind.OTHER


class SheetImportChoices(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identities: dict[str, SheetImportIdentityChoice] = Field(default_factory=dict)
    locations: dict[str, SheetImportLocationChoice] = Field(default_factory=dict)
    suppliers: dict[str, SheetImportSupplierChoice] = Field(default_factory=dict)


class SheetImportOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_type: SheetImportRecordType
    sheet_name: str | None = None
    header_row: int | None = Field(default=None, ge=1, le=10)
    mapping: SheetImportMapping
    choices: SheetImportChoices = Field(default_factory=SheetImportChoices)


class SheetImportCandidate(BaseModel):
    id: UUID
    label: str
    details: str
    match_kind: Literal["exact", "near"]


class SheetImportIdentityGroup(BaseModel):
    key: str
    scientific_name: str
    cultivar_name: str | None
    common_name: str | None
    row_count: int
    status: Literal["matched", "new", "invalid"]
    action: Literal["use_existing", "create"]
    matched_id: UUID | None = None
    matched_label: str | None = None
    candidates: list[SheetImportCandidate] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)


class SheetImportLocationGroup(BaseModel):
    key: str
    raw_value: str
    row_count: int
    status: Literal["matched", "new", "ambiguous", "skipped", "invalid"]
    action: Literal["use_existing", "create", "skip"]
    matched_id: UUID | None = None
    matched_label: str | None = None
    create_name: str | None = None
    parent_id: UUID | None = None
    candidates: list[SheetImportCandidate] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)


class SheetImportSupplierGroup(BaseModel):
    key: str
    raw_value: str
    row_count: int
    status: Literal["matched", "new", "ambiguous", "skipped", "invalid"]
    action: Literal["use_existing", "create", "skip"]
    matched_id: UUID | None = None
    matched_label: str | None = None
    create_name: str | None = None
    kind: SupplierKind = SupplierKind.OTHER
    candidates: list[SheetImportCandidate] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)


class SheetImportPreviewResponse(BaseModel):
    record_type: SheetImportRecordType
    identities: list[SheetImportIdentityGroup]
    locations: list[SheetImportLocationGroup]
    suppliers: list[SheetImportSupplierGroup]
    rows: list[SheetImportPreviewRow]
    ready: int
    needs_attention: int
    invalid: int
    will_create_identities: int
    will_create_locations: int
    will_create_suppliers: int
    can_apply: bool
    confirmation_token: str


class SheetImportCreatedRecord(BaseModel):
    id: UUID
    label: str
    identity_label: str


class SheetImportApplyResponse(BaseModel):
    record_type: SheetImportRecordType
    records_created: int
    identities_created: int
    locations_created: int
    suppliers_created: int
    created_records: list[SheetImportCreatedRecord]
