"""Authenticated single-sheet spreadsheet import endpoints (inspect, preview, apply)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from pydantic import ValidationError
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
from florabase.import_wizard.mapping import SheetImportRecordType
from florabase.import_wizard.schemas import (
    SheetImportApplyResponse,
    SheetImportInspectResponse,
    SheetImportOptions,
    SheetImportPreviewResponse,
)
from florabase.import_wizard.service import (
    SheetImportConflictError,
    apply_sheet,
    build_preview_plan,
    inspect_sheet,
    preview_response_from_plan,
)
from florabase.import_wizard.sheet import MAX_BYTES, SheetFormatError
from florabase.lineage.service import LineageCycleError
from florabase.locations.service import (
    LocationHierarchyError,
    LocationIntegrityError,
    LocationNotFoundError,
)
from florabase.plants.service import PlantDomainConflictError, PlantReferenceNotFoundError
from florabase.seed_lots.service import SeedLotDomainConflictError, SeedLotReferenceNotFoundError

router = APIRouter(prefix="/sheet-imports", tags=["import-export"])

_UPLOAD_CHUNK = 64 * 1024
_MAX_OPTIONS_BYTES = 1024 * 1024
_TOKEN_TTL_SECONDS = 900


async def _read_upload(upload: UploadFile, *, limit: int = MAX_BYTES) -> bytes:
    chunks = bytearray()
    while True:
        chunk = await upload.read(_UPLOAD_CHUNK)
        if not chunk:
            break
        if len(chunks) + len(chunk) > limit:
            raise HTTPException(status_code=413, detail="Import file exceeds the 2 MiB size limit")
        chunks.extend(chunk)
    return bytes(chunks)


def _canonical_options(options: SheetImportOptions) -> bytes:
    return json.dumps(
        options.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _signature(
    actor: AuthenticatedActor, data: bytes, options: SheetImportOptions, issued: int
) -> str:
    file_digest = hashlib.sha256(data).hexdigest()
    options_digest = hashlib.sha256(_canonical_options(options)).hexdigest()
    message = f"{actor.session.id}:sheet-import:{file_digest}:{options_digest}:{issued}".encode()
    return hmac.new(actor.session.token_digest, message, hashlib.sha256).hexdigest()


def _confirmation_token(actor: AuthenticatedActor, data: bytes, options: SheetImportOptions) -> str:
    issued = int(time.time())
    return f"{issued}.{_signature(actor, data, options, issued)}"


def _verify_confirmation_token(
    actor: AuthenticatedActor, data: bytes, options: SheetImportOptions, token: str
) -> bool:
    parts = token.split(".")
    if len(parts) != 2 or not parts[0].isdigit():
        return False
    issued = int(parts[0])
    now = int(time.time())
    return now - _TOKEN_TTL_SECONDS <= issued <= now and hmac.compare_digest(
        parts[1], _signature(actor, data, options, issued)
    )


def _parse_options(raw_options: str) -> SheetImportOptions:
    if len(raw_options.encode("utf-8")) > _MAX_OPTIONS_BYTES:
        raise HTTPException(status_code=413, detail="Import options exceed size limit")
    try:
        return SheetImportOptions.model_validate_json(raw_options)
    except ValidationError as error:
        raise HTTPException(status_code=422, detail="Invalid sheet import options") from error


@router.post(
    "/inspect",
    response_model=SheetImportInspectResponse,
    operation_id="inspectSheetImport",
)
async def inspect_sheet_import(
    file: Annotated[UploadFile, File()],
    actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    record_type: Annotated[SheetImportRecordType, Form()] = "plants",
    sheet_name: Annotated[str | None, Form()] = None,
    header_row: Annotated[int | None, Form(ge=1, le=10)] = None,
) -> SheetImportInspectResponse:
    require_owner(actor)
    data = await _read_upload(file)
    try:
        return inspect_sheet(
            data,
            filename=file.filename,
            sheet_name=sheet_name or None,
            header_row=header_row,
            record_type=record_type,
        )
    except SheetFormatError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post(
    "/preview",
    response_model=SheetImportPreviewResponse,
    operation_id="previewSheetImport",
)
async def preview_sheet_import(
    file: Annotated[UploadFile, File()],
    options: Annotated[str, Form()],
    actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session, scope="function")],
) -> SheetImportPreviewResponse:
    require_owner(actor)
    data = await _read_upload(file)
    parsed_options = _parse_options(options)
    try:
        plan = build_preview_plan(database, data, parsed_options, filename=file.filename)
    except SheetFormatError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    token = _confirmation_token(actor, data, parsed_options)
    return preview_response_from_plan(plan, token)


@router.post(
    "/apply",
    response_model=SheetImportApplyResponse,
    operation_id="applySheetImport",
)
async def apply_sheet_import(
    file: Annotated[UploadFile, File()],
    options: Annotated[str, Form()],
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session, scope="function")],
    confirmation_token: Annotated[str | None, Header(alias="X-Import-Confirmation")] = None,
) -> SheetImportApplyResponse:
    require_owner(actor)
    data = await _read_upload(file)
    parsed_options = _parse_options(options)
    if confirmation_token is None or not _verify_confirmation_token(
        actor, data, parsed_options, confirmation_token
    ):
        raise HTTPException(
            status_code=409,
            detail="Preview expired or spreadsheet/options changed; validate again",
        )
    try:
        result = apply_sheet(database, data, parsed_options, filename=file.filename)
        database.commit()
    except SheetFormatError as error:
        database.rollback()
        raise HTTPException(status_code=422, detail=str(error)) from error
    except SheetImportConflictError as error:
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
            status_code=409,
            detail="Import conflicts with current collection state; validate again",
        ) from error
    except Exception:
        database.rollback()
        raise
    return result
