"""Authenticated CSV preview, explicit apply, templates, and operator export."""

import base64
import binascii
import hashlib
import hmac
import time
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from florabase.auth.dependencies import (
    AuthenticatedActor,
    require_authenticated_actor,
    require_csrf,
    require_owner,
)
from florabase.botanical_identities.service import BotanicalIdentityConflictError
from florabase.db.session import get_database_session
from florabase.import_export.service import (
    COLUMNS,
    MAX_BYTES,
    CsvFormatError,
    DecisionOption,
    PreviewRow,
    apply,
    example_csv,
    export_csv,
    field_guide,
    preview,
    template_csv,
)
from florabase.lineage.service import LineageCycleError
from florabase.locations.service import (
    LocationHierarchyError,
    LocationIntegrityError,
    LocationNotFoundError,
)
from florabase.plants.service import PlantDomainConflictError, PlantReferenceNotFoundError
from florabase.seed_lots.service import SeedLotDomainConflictError, SeedLotReferenceNotFoundError

router = APIRouter(tags=["import-export"])
ImportKind = Literal[
    "botanical-identities", "suppliers", "locations", "seed-lots", "plants", "plant-groups"
]


class ImportDecisionOption(BaseModel):
    key: str
    action: Literal["use_existing", "update_existing", "create_separate", "choose_reference"]
    candidate_id: str
    label: str
    details: str
    changes: list[dict[str, str]]
    token: str


class ImportPreviewRow(BaseModel):
    row_number: int
    record: str
    outcome: Literal[
        "ready",
        "already_exists",
        "needs_choice",
        "invalid",
        "unresolved_reference",
        "ambiguous_reference",
        "conflict",
    ]
    messages: list[str]
    references: list[str]
    normalized: list[str]
    options: list[ImportDecisionOption]
    hard_blocker: bool


class ImportFieldGuide(BaseModel):
    field: str
    meaning: str
    required: bool
    accepted: str
    example: str
    notes: str


class ImportFormatResponse(BaseModel):
    fields: list[ImportFieldGuide]


class ImportApplyEnvelope(BaseModel):
    csv_base64: str
    decisions: dict[str, dict[str, str]]


class ImportPreviewResponse(BaseModel):
    rows: list[ImportPreviewRow]
    ready: int
    already_exists: int
    needs_attention: int
    confirmation_token: str


class ImportResultResponse(BaseModel):
    created: int
    already_exists: int
    updated: int


def _kind(kind: str) -> None:
    if kind not in COLUMNS:
        raise HTTPException(status_code=404, detail="Unsupported CSV record type")


async def _read_csv(request: Request, *, limit: int = MAX_BYTES) -> bytes:
    chunks = bytearray()
    async for chunk in request.stream():
        if len(chunks) + len(chunk) > limit:
            raise HTTPException(status_code=413, detail="Import request exceeds its size limit")
        chunks.extend(chunk)
    return bytes(chunks)


def _signature(actor: AuthenticatedActor, kind: str, data: bytes, issued: int) -> str:
    digest = hashlib.sha256(data).hexdigest()
    message = f"{actor.session.id}:{kind}:{digest}:{issued}".encode()
    return hmac.new(actor.session.token_digest, message, hashlib.sha256).hexdigest()


def _token(actor: AuthenticatedActor, kind: str, data: bytes) -> str:
    issued = int(time.time())
    return f"{issued}.{_signature(actor, kind, data, issued)}"


def _verify_token(actor: AuthenticatedActor, kind: str, data: bytes, token: str) -> bool:
    parts = token.split(".")
    if len(parts) != 2 or not parts[0].isdigit():
        return False
    issued = int(parts[0])
    now = int(time.time())
    return now - 900 <= issued <= now and hmac.compare_digest(
        parts[1], _signature(actor, kind, data, issued)
    )


def _option_token(
    actor: AuthenticatedActor,
    kind: str,
    data: bytes,
    issued: int,
    row_number: int,
    option: DecisionOption,
) -> str:
    digest = hashlib.sha256(data).hexdigest()
    message = (
        f"{actor.session.id}:{kind}:{digest}:{issued}:{row_number}:{option.signed_content()}"
    ).encode()
    return hmac.new(actor.session.token_digest, message, hashlib.sha256).hexdigest()


def _public_rows(
    rows: list[PreviewRow],
    actor: AuthenticatedActor,
    kind: str,
    data: bytes,
    issued: int,
) -> list[ImportPreviewRow]:
    public = []
    for row in rows:
        values = row.public()
        values["options"] = [
            {
                **option.public(),
                "token": _option_token(actor, kind, data, issued, row.row_number, option),
            }
            for option in row.options
        ]
        public.append(ImportPreviewRow.model_validate(values))
    return public


def _csv_response(content: str, filename: str) -> Response:
    return Response(
        content="\ufeff" + content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post(
    "/imports/{kind}/preview",
    response_model=ImportPreviewResponse,
    operation_id="previewCsvImport",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"text/csv": {"schema": {"type": "string", "format": "binary"}}},
        }
    },
)
async def preview_import(
    kind: ImportKind,
    request: Request,
    actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> ImportPreviewResponse:
    require_owner(actor)
    _kind(kind)
    data = await _read_csv(request)
    try:
        rows = preview(database, kind, data)
    except CsvFormatError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    token = _token(actor, kind, data)
    return ImportPreviewResponse(
        rows=_public_rows(rows, actor, kind, data, int(token.split(".")[0])),
        ready=sum(row.outcome == "ready" for row in rows),
        already_exists=sum(row.outcome == "already_exists" for row in rows),
        needs_attention=sum(row.outcome not in {"ready", "already_exists"} for row in rows),
        confirmation_token=token,
    )


@router.post(
    "/imports/{kind}/apply",
    response_model=ImportResultResponse,
    operation_id="applyCsvImport",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": ImportApplyEnvelope.model_json_schema()}},
        }
    },
)
async def apply_import(
    kind: ImportKind,
    request: Request,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
    confirmation_token: Annotated[str | None, Header(alias="X-Import-Confirmation")] = None,
) -> ImportResultResponse:
    require_owner(actor)
    _kind(kind)
    raw = await _read_csv(request, limit=3 * 1024 * 1024)
    decisions: dict[str, dict[str, str]] = {}
    if request.headers.get("content-type", "").startswith("application/json"):
        try:
            envelope = ImportApplyEnvelope.model_validate_json(raw)
            data = base64.b64decode(envelope.csv_base64, validate=True)
            decisions = envelope.decisions
        except (ValidationError, ValueError, binascii.Error) as error:
            raise HTTPException(
                status_code=422, detail="Invalid import confirmation request"
            ) from error
        if len(data) > MAX_BYTES:
            raise HTTPException(status_code=413, detail="CSV exceeds 2 MiB")
    else:
        data = raw
        if len(data) > MAX_BYTES:
            raise HTTPException(status_code=413, detail="CSV exceeds 2 MiB")
    if confirmation_token is None or not _verify_token(actor, kind, data, confirmation_token):
        raise HTTPException(
            status_code=409, detail="Preview expired or CSV changed; validate again"
        )
    try:
        current_rows = preview(database, kind, data)
        issued = int(confirmation_token.split(".")[0])
        selections: dict[tuple[int, str], DecisionOption] = {}
        for row_text, by_key in decisions.items():
            if not row_text.isdigit():
                raise CsvFormatError("Invalid row choice; validate again")
            row_number = int(row_text)
            row = next((item for item in current_rows if item.row_number == row_number), None)
            if row is None:
                raise CsvFormatError("Unknown row choice; validate again")
            for key, submitted in by_key.items():
                option = next(
                    (
                        item
                        for item in row.options
                        if item.key == key
                        and hmac.compare_digest(
                            submitted, _option_token(actor, kind, data, issued, row_number, item)
                        )
                    ),
                    None,
                )
                if option is None:
                    raise CsvFormatError(
                        "A selected record changed or the choice is stale; validate again"
                    )
                selections[(row_number, key)] = option
        created, existing, updated = apply(database, kind, data, selections)
        database.commit()
    except CsvFormatError as error:
        database.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (
        IntegrityError,
        BotanicalIdentityConflictError,
        LocationHierarchyError,
        LocationIntegrityError,
        LocationNotFoundError,
        PlantDomainConflictError,
        PlantReferenceNotFoundError,
        SeedLotDomainConflictError,
        SeedLotReferenceNotFoundError,
        LineageCycleError,
    ) as error:
        database.rollback()
        raise HTTPException(
            status_code=409, detail="Import conflicts with current collection state; validate again"
        ) from error
    except Exception:
        database.rollback()
        raise
    return ImportResultResponse(created=created, already_exists=existing, updated=updated)


@router.get(
    "/imports/formats/{kind}",
    response_model=ImportFormatResponse,
    operation_id="getCsvImportFormat",
)
def get_import_format(
    kind: ImportKind,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
) -> ImportFormatResponse:
    _kind(kind)
    return ImportFormatResponse(
        fields=[ImportFieldGuide.model_validate(item) for item in field_guide(kind)]
    )


@router.get(
    "/imports/examples/{kind}.csv", operation_id="downloadCsvExample", response_class=Response
)
def download_example(
    kind: ImportKind,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
) -> Response:
    _kind(kind)
    return _csv_response(example_csv(kind), f"{kind}-example.csv")


@router.get(
    "/imports/templates/{kind}.csv", operation_id="downloadCsvTemplate", response_class=Response
)
def download_template(
    kind: ImportKind,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
) -> Response:
    _kind(kind)
    return _csv_response(template_csv(kind), f"{kind}-template.csv")


@router.get("/exports/{kind}.csv", operation_id="exportCollectionCsv", response_class=Response)
def export_records(
    kind: ImportKind,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> Response:
    _kind(kind)
    return _csv_response(export_csv(database, kind), f"florabase-{kind}.csv")
