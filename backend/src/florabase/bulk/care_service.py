"""Service layer for bulk care preview, atomic apply, and safe batch undo."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import cast
from uuid import UUID, uuid7

from sqlalchemy import select
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.bulk.care_schemas import (
    MAX_BULK_CARE_TARGETS,
    BulkCareApplyRequest,
    BulkCareApplyResponse,
    BulkCareKeptEvent,
    BulkCareLocationTargets,
    BulkCarePreviewRequest,
    BulkCarePreviewResponse,
    BulkCareRecordReference,
    BulkCareRecordTargets,
    BulkCareRow,
    BulkCareTargetKind,
    BulkCareUndoResponse,
)
from florabase.events.model import Event, EventKind
from florabase.events.schemas import EventCreate
from florabase.events.service import create_event
from florabase.locations.model import Location
from florabase.locations.service import display_path, list_locations
from florabase.plants.model import Plant, PlantGroup

TargetRecord = Plant | PlantGroup


@dataclass(frozen=True)
class BulkCareError(Exception):
    code: str
    message: str
    rows: tuple[BulkCareRow, ...] = ()


def _record_label(kind: BulkCareTargetKind, record: TargetRecord, scientific_name: str) -> str:
    prefix = record.label or ("Plant" if kind == "plant" else "Plant group")
    return f"{prefix} · {scientific_name}"


def _subtree_location_ids(
    database: Session, location_id: UUID, include_sublocations: bool
) -> list[UUID]:
    if not include_sublocations:
        return [location_id]
    # Reuse the recursive UNION containment pattern from locations/service.py so persisted
    # cycles terminate cleanly without duplicate rows.
    containment = (
        select(Location.id.label("descendant_id"))
        .where(Location.id == location_id)
        .cte("bulk_care_location_subtree", recursive=True)
    )
    containment = containment.union(
        select(Location.id).join(containment, Location.parent_id == containment.c.descendant_id)
    )
    return list(
        database.scalars(select(containment.c.descendant_id).order_by(containment.c.descendant_id))
    )


def _fetch_records_by_refs(
    database: Session,
    references: list[BulkCareRecordReference],
    *,
    lock: bool,
) -> dict[tuple[BulkCareTargetKind, UUID], tuple[TargetRecord, str]]:
    result: dict[tuple[BulkCareTargetKind, UUID], tuple[TargetRecord, str]] = {}
    for kind, model in (("plant", Plant), ("plant_group", PlantGroup)):
        target_kind = cast(BulkCareTargetKind, kind)
        ids = sorted({ref.id for ref in references if ref.kind == target_kind})
        if not ids:
            continue
        statement = (
            select(model, BotanicalIdentity.scientific_name)
            .join(BotanicalIdentity, BotanicalIdentity.id == model.botanical_identity_id)
            .where(model.id.in_(ids))
            .order_by(model.id)
            .execution_options(populate_existing=True)
        )
        if lock:
            statement = statement.with_for_update(of=model)
        for record, scientific_name in database.execute(statement):
            result[target_kind, record.id] = (cast(TargetRecord, record), str(scientific_name))
    return result


def _fetch_records_in_locations(
    database: Session,
    location_ids: list[UUID],
    *,
    lock: bool,
) -> list[tuple[BulkCareTargetKind, TargetRecord, str]]:
    found: list[tuple[BulkCareTargetKind, TargetRecord, str]] = []
    for kind, model in (("plant", Plant), ("plant_group", PlantGroup)):
        target_kind = cast(BulkCareTargetKind, kind)
        statement = (
            select(model, BotanicalIdentity.scientific_name)
            .join(BotanicalIdentity, BotanicalIdentity.id == model.botanical_identity_id)
            .where(model.location_id.in_(location_ids))
            .order_by(model.id)
            .execution_options(populate_existing=True)
        )
        if lock:
            statement = statement.with_for_update(of=model)
        for record, scientific_name in database.execute(statement):
            found.append((target_kind, cast(TargetRecord, record), str(scientific_name)))
    return found


def _signature(
    rows: list[tuple[BulkCareTargetKind, UUID, str, str | None]],
    *,
    location_scope: list[tuple[str, str]] | None = None,
) -> str:
    payload: dict[str, object] = {
        "targets": sorted(
            ([kind, str(target_id), status, updated] for kind, target_id, status, updated in rows),
            key=lambda item: (item[0], item[1]),
        ),
    }
    if location_scope is not None:
        payload["locations"] = sorted(location_scope)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _resolve_preview(
    database: Session,
    payload: BulkCarePreviewRequest,
    *,
    lock: bool,
) -> BulkCarePreviewResponse:
    all_locations = list_locations(database)
    location_paths = {loc.id: display_path(loc, all_locations) for loc in all_locations}
    rows: list[BulkCareRow] = []
    sig_entries: list[tuple[BulkCareTargetKind, UUID, str, str | None]] = []
    location_label: str | None = None
    sublocation_count = 0
    location_scope: list[tuple[str, str]] | None = None

    if isinstance(payload.targets, BulkCareLocationTargets):
        target_loc = database.get(
            Location,
            payload.targets.location_id,
            with_for_update=lock,
            populate_existing=True,
        )
        if target_loc is None:
            raise BulkCareError("location_not_found", "Location not found.")
        subtree_ids = _subtree_location_ids(
            database, target_loc.id, payload.targets.include_sublocations
        )
        loc_stmt = (
            select(Location)
            .where(Location.id.in_(subtree_ids))
            .order_by(Location.id)
            .execution_options(populate_existing=True)
        )
        if lock:
            loc_stmt = loc_stmt.with_for_update()
        subtree_locations = list(database.scalars(loc_stmt))
        location_label = location_paths.get(target_loc.id, target_loc.name)
        sublocation_count = max(0, len(subtree_locations) - 1)
        location_scope = [(str(loc.id), loc.updated_at.isoformat()) for loc in subtree_locations]

        candidates = _fetch_records_in_locations(database, subtree_ids, lock=lock)
        if len(candidates) > MAX_BULK_CARE_TARGETS:
            raise BulkCareError(
                "too_many_targets",
                f"This location contains {len(candidates)} records; bulk care supports at most "
                f"{MAX_BULK_CARE_TARGETS} targets at once.",
            )
        for target_kind, record, scientific_name in candidates:
            is_active = record.lifecycle == "active"
            status = "log" if is_active else "skipped"
            reason = None if is_active else f"Inactive ({record.lifecycle})"
            rows.append(
                BulkCareRow(
                    kind=target_kind,
                    id=record.id,
                    label=_record_label(target_kind, record, scientific_name),
                    scientific_name=scientific_name,
                    location=location_paths.get(record.location_id) if record.location_id else None,
                    lifecycle=record.lifecycle,
                    status=status,
                    reason=reason,
                )
            )
            sig_entries.append((target_kind, record.id, status, record.updated_at.isoformat()))
    else:
        assert isinstance(payload.targets, BulkCareRecordTargets)
        references = payload.targets.records
        if len(references) > MAX_BULK_CARE_TARGETS:
            raise BulkCareError(
                "too_many_targets",
                f"Bulk care supports at most {MAX_BULK_CARE_TARGETS} targets at once.",
            )
        found = _fetch_records_by_refs(database, references, lock=lock)
        for ref in references:
            entry = found.get((ref.kind, ref.id))
            if entry is None:
                rows.append(
                    BulkCareRow(
                        kind=ref.kind,
                        id=ref.id,
                        label=f"{ref.kind.replace('_', ' ')} · {ref.id}",
                        status="skipped",
                        reason="Record no longer exists",
                    )
                )
                sig_entries.append((ref.kind, ref.id, "skipped", None))
                continue
            record, scientific_name = entry
            is_active = record.lifecycle == "active"
            status = "log" if is_active else "skipped"
            reason = None if is_active else f"Inactive ({record.lifecycle})"
            rows.append(
                BulkCareRow(
                    kind=ref.kind,
                    id=record.id,
                    label=_record_label(ref.kind, record, scientific_name),
                    scientific_name=scientific_name,
                    location=location_paths.get(record.location_id) if record.location_id else None,
                    lifecycle=record.lifecycle,
                    status=status,
                    reason=reason,
                )
            )
            sig_entries.append((ref.kind, record.id, status, record.updated_at.isoformat()))

    log_rows = [row for row in rows if row.status == "log"]
    plant_count = sum(row.kind == "plant" for row in log_rows)
    plant_group_count = sum(row.kind == "plant_group" for row in log_rows)
    skipped_count = len(rows) - len(log_rows)
    return BulkCarePreviewResponse(
        kind=payload.kind,
        occurred_on=payload.occurred_on,
        notes=payload.notes,
        location_label=location_label,
        sublocation_count=sublocation_count,
        total_count=len(rows),
        log_count=len(log_rows),
        plant_count=plant_count,
        plant_group_count=plant_group_count,
        skipped_count=skipped_count,
        can_apply=len(log_rows) > 0,
        target_signature=_signature(sig_entries, location_scope=location_scope),
        rows=rows,
    )


def preview_bulk_care(
    database: Session, payload: BulkCarePreviewRequest
) -> BulkCarePreviewResponse:
    return _resolve_preview(database, payload, lock=False)


def apply_bulk_care(database: Session, payload: BulkCareApplyRequest) -> BulkCareApplyResponse:
    preview = _resolve_preview(database, payload, lock=True)
    if not hmac.compare_digest(preview.target_signature, payload.target_signature):
        raise BulkCareError(
            "stale_preview",
            "No care entries logged. Records or locations changed since preview; preview again.",
            tuple(preview.rows),
        )
    if preview.log_count == 0:
        raise BulkCareError(
            "nothing_to_log",
            "No active Plants or PlantGroups are available to log care for.",
            tuple(preview.rows),
        )
    batch_id = uuid7()
    event_payload = EventCreate(
        kind=EventKind(payload.kind),
        occurred_on=payload.occurred_on,
        notes=payload.notes,
    )
    for row in preview.rows:
        if row.status != "log":
            continue
        create_event(database, row.kind, row.id, event_payload, batch_id=batch_id)
    database.flush()
    return BulkCareApplyResponse(
        batch_id=batch_id,
        kind=payload.kind,
        logged_count=preview.log_count,
        plant_count=preview.plant_count,
        plant_group_count=preview.plant_group_count,
        skipped_count=preview.skipped_count,
    )


def undo_bulk_care(database: Session, batch_id: UUID) -> BulkCareUndoResponse:
    events = list(
        database.scalars(
            select(Event)
            .where(Event.batch_id == batch_id)
            .order_by(Event.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )
    if not events:
        raise BulkCareError(
            "batch_not_found",
            "Care batch not found or already undone.",
        )

    deleted_count = 0
    kept_events: list[Event] = []
    for event in events:
        if event.updated_at == event.created_at:
            database.delete(event)
            deleted_count += 1
        else:
            kept_events.append(event)

    kept_refs: list[BulkCareRecordReference] = []
    for event in kept_events:
        if event.plant_id is not None:
            kept_refs.append(BulkCareRecordReference(kind="plant", id=event.plant_id))
        elif event.plant_group_id is not None:
            kept_refs.append(BulkCareRecordReference(kind="plant_group", id=event.plant_group_id))
    record_lookup = _fetch_records_by_refs(database, kept_refs, lock=False) if kept_refs else {}

    kept: list[BulkCareKeptEvent] = []
    for event in kept_events:
        target_kind: BulkCareTargetKind = "plant" if event.plant_id is not None else "plant_group"
        target_id = event.plant_id if event.plant_id is not None else event.plant_group_id
        assert target_id is not None
        found = record_lookup.get((target_kind, target_id))
        label = (
            _record_label(target_kind, found[0], found[1])
            if found is not None
            else f"{target_kind.replace('_', ' ')} · {target_id}"
        )
        kept.append(
            BulkCareKeptEvent(
                id=event.id,
                target_kind=target_kind,
                target_id=target_id,
                label=label,
                reason="Edited after batch creation",
            )
        )
    database.flush()
    return BulkCareUndoResponse(
        batch_id=batch_id,
        deleted_count=deleted_count,
        kept_count=len(kept),
        kept=kept,
    )
