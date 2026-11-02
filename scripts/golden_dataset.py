"""TEST-DATA-001 golden dataset runtime; generates isolated copies in disposable PostgreSQL only."""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import hashlib
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, NoReturn
from urllib.parse import urlsplit
from uuid import UUID

import golden_plan
import httpx
import review_dataset_v5 as v5
import uat_fixture as v4
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import UploadFile
from PIL import Image, ImageDraw
from sqlalchemy import DateTime, Table, create_engine, event, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from starlette.datastructures import Headers

from florabase.attachments.model import Attachment
from florabase.attachments.storage import AttachmentStorage
from florabase.auth.model import User
from florabase.auth.service import bootstrap_owner
from florabase.botanical_identities.service import list_botanical_identities
from florabase.botanical_profiles.model import BotanicalProfileNativeRange
from florabase.collection_photos.model import BotanicalIdentityCoverImage, MediaAsset
from florabase.collection_photos.schemas import (
    ExternalCoverWrite,
    PrimaryPhotoSelection,
)
from florabase.collection_photos.service import set_external_identity_cover
from florabase.collection_views.dashboard import overview
from florabase.core.config import Environment, Settings, get_settings
from florabase.db.base import Base
from florabase.db.session import get_engine
from florabase.events.schemas import TransferCreate
from florabase.external_botany.provider import GbifBotanicalProvider
from florabase.external_botany.service import confirm_link
from florabase.harvests import conversion_service
from florabase.harvests.conversion_model import HarvestSeedLotConversion
from florabase.harvests.conversion_schemas import ConversionCreate
from florabase.harvests.inventory_model import HarvestMaterialDisposition
from florabase.harvests.inventory_schemas import DispositionCreate
from florabase.harvests.inventory_service import list_inventory, record_disposition
from florabase.history.service import list_history
from florabase.locations.model import Location
from florabase.locations.service import list_locations
from florabase.media.schemas import AssetMetadataWrite, ExternalAssetCreate
from florabase.plants.model import Plant, PlantGroup
from florabase.propagation import reversal
from florabase.propagation import service as propagation
from florabase.propagation.schemas import (
    PlantFromSowingCreate,
    PlantGroupFromSowingCreate,
    SeedLotSowingTransitionCreate,
)
from florabase.provenance_sites.model import ProvenanceSite
from florabase.provenance_sites.service import collection_provenance_map
from florabase.saved_views.model import SavedView
from florabase.saved_views.schemas import SavedViewCreate
from florabase.saved_views.service import create_view
from florabase.schedule.schemas import ScheduleComplete
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing
from florabase.suppliers.model import Supplier

LEDGER = ".golden-dataset.json"
COPY_ROOT = Path("/tmp/florabase-golden")
# COPY_NAME can never match this directory and retirement removes only COPY_ROOT/<name>.
LOCK_ROOT = COPY_ROOT / ".locks"
COPY_NAME = re.compile(r"golden_[a-z0-9_]{1,40}")
OWNER_PASSWORD = "disposable-golden-owner-password"
MODELS: dict[str, type[Base]] = {
    **v5.MODELS,
    "conversion": HarvestSeedLotConversion,
    "cover": BotanicalIdentityCoverImage,
    "disposition": HarvestMaterialDisposition,
    "saved_view": SavedView,
}
# Session state never describes the dataset; a salted hash and a random object name differ per copy.
# Media bytes are hashed separately, so excluding the object name hides no content.
EXCLUDED_TABLES = {"auth_sessions", "login_throttles"}
EXCLUDED_COLUMNS = {("users", "password_hash"), ("attachments", "storage_key")}
UUID_PATTERN = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
EXIT_DOMAIN_INVALID = 1
EXIT_BASELINE_MODIFIED = 3
EXIT_BASELINE_UNAVAILABLE = 4
EXIT_BUSY = 75
SYNTHETIC_LABELS: tuple[tuple[type[Any], Any], ...] = (
    (SeedLot, SeedLot.label),
    (Sowing, Sowing.label),
    (Plant, Plant.label),
    (PlantGroup, PlantGroup.label),
    (Supplier, Supplier.name),
    (Location, Location.name),
    (ProvenanceSite, ProvenanceSite.name),
)
Operation = Callable[[Session, AttachmentStorage, dict[str, Any], dict[str, Any]], Any]


class GoldenError(RuntimeError):
    pass


class GoldenBusy(GoldenError):
    """Another lifecycle action holds this copy; the loser changed nothing and may simply retry."""


def owner_node(database: Session, _: AttachmentStorage, payload: dict[str, Any], __: Any) -> User:
    return bootstrap_owner(
        database, payload["login_name"], OWNER_PASSWORD, payload.get("display_name")
    )


def generated_asset(
    database: Session, storage: AttachmentStorage, payload: dict[str, Any], ledger: dict[str, Any]
) -> MediaAsset:
    buffer = io.BytesIO()
    image = Image.new("RGB", (payload["width"], payload["height"]), tuple(payload["colour"]))
    ImageDraw.Draw(image).line(
        [(0, 0), (payload["width"] - 1, payload["height"] - 1)], fill="#47663a"
    )
    image.save(buffer, format="PNG")
    buffer.seek(0)
    row: MediaAsset = asyncio.run(
        v4.media.upload_asset(
            database,
            storage,
            UploadFile(
                file=buffer,
                filename="golden-generated.png",
                headers=Headers({"content-type": "image/png"}),
            ),
            AssetMetadataWrite(
                title=payload["title"],
                attribution="Repository-generated geometric fixture",
                licence_label="CC0-1.0",
            ),
            commit=False,
        )
    )
    attachment = database.get(Attachment, row.attachment_id)
    assert attachment is not None
    ledger["created_files"].append(attachment.storage_key)
    return row


def external_asset(
    database: Session, _: AttachmentStorage, payload: dict[str, Any], __: Any
) -> Any:
    return v4.media.create_external_asset(
        database, ExternalAssetCreate.model_validate(payload), commit=False
    )


def taxon_link(database: Session, _: AttachmentStorage, payload: dict[str, Any], __: Any) -> Any:
    """Same offline confirmation as UAT v4: the provider sees only this fixed snapshot."""
    snapshot = {
        "usage": {
            "key": payload["external_id"],
            "name": payload["scientific_name"],
            "canonicalName": payload["canonical_name"],
            "authorship": payload["authorship"],
            "rank": "SPECIES",
            "status": "ACCEPTED",
        },
        "classification": [
            {"name": "Plantae", "rank": "KINGDOM"},
            {"name": payload["family"], "rank": "FAMILY"},
            {"name": payload["genus"], "rank": "GENUS"},
        ],
        "diagnostics": {"matchType": "EXACT", "confidence": 98},
    }

    def offline(request: httpx.Request) -> httpx.Response:
        if request.url.host != "api.gbif.org":
            raise GoldenError("Unexpected synthetic taxon request")
        return httpx.Response(200, json=snapshot)

    provider = GbifBotanicalProvider(v4.get_settings(), transport=httpx.MockTransport(offline))
    return asyncio.run(
        confirm_link(
            database,
            provider,
            payload["identity_id"],
            payload["external_id"],
            payload["scientific_name"],
            86400,
        )
    )


def retire_supplier(
    database: Session, _: AttachmentStorage, payload: dict[str, Any], __: Any
) -> None:
    supplier = database.get(Supplier, payload["supplier_id"])
    assert supplier is not None
    v4.suppliers.set_supplier_retired(database, supplier, retired=True)


def sow_transition(
    database: Session, _: AttachmentStorage, payload: dict[str, Any], __: Any
) -> Any:
    source = payload.pop("seed_lot_id")
    return propagation.create_sowing_from_seed_lot(
        database, source, SeedLotSowingTransitionCreate.model_validate(payload)
    )[0]


def plant_from_sowing(
    database: Session, _: AttachmentStorage, payload: dict[str, Any], __: Any
) -> Any:
    return propagation.create_plant_from_sowing(
        database,
        payload["sowing_id"],
        PlantFromSowingCreate.model_validate(payload["plant"]),
        payload["resulting_sowing_lifecycle"],
    )[0]


def group_from_sowing(
    database: Session, _: AttachmentStorage, payload: dict[str, Any], __: Any
) -> Any:
    return propagation.create_plant_group_from_sowing(
        database,
        payload["sowing_id"],
        PlantGroupFromSowingCreate.model_validate(payload["plant_group"]),
        payload["resulting_sowing_lifecycle"],
    )[0]


def propagation_reverse(
    database: Session, _: AttachmentStorage, payload: dict[str, Any], __: Any
) -> None:
    reversal.reverse(database, payload["result_type"], payload["result_id"], confirm=True)


def transfer(database: Session, _: AttachmentStorage, payload: dict[str, Any], __: Any) -> Any:
    target_type, target_id = payload.pop("target_type"), payload.pop("target_id")
    return v4.events.transfer_target(
        database, target_type, target_id, TransferCreate.model_validate(payload)
    )[0]


def reintegrate(database: Session, _: AttachmentStorage, payload: dict[str, Any], __: Any) -> Any:
    return v4.plants.reintegrate_plant(
        database, payload["plant_id"], confirm_retained_observations=True
    )[2]


def disposition(database: Session, _: AttachmentStorage, payload: dict[str, Any], __: Any) -> Any:
    inventory = payload.pop("inventory_id")
    return record_disposition(database, inventory, DispositionCreate.model_validate(payload))


def conversion(database: Session, _: AttachmentStorage, payload: dict[str, Any], __: Any) -> Any:
    inventory = payload.pop("inventory_id")
    return conversion_service.create(database, inventory, ConversionCreate.model_validate(payload))


def conversion_reverse(
    database: Session, _: AttachmentStorage, payload: dict[str, Any], __: Any
) -> None:
    conversion_service.reverse(database, payload["conversion_id"])


def schedule_complete(
    database: Session, _: AttachmentStorage, payload: dict[str, Any], __: Any
) -> None:
    identifier = payload.pop("activity_id")
    v4.schedule.complete(database, identifier, ScheduleComplete.model_validate(payload))


def schedule_cancel(
    database: Session, _: AttachmentStorage, payload: dict[str, Any], __: Any
) -> None:
    v4.schedule.cancel(database, payload["activity_id"], payload["version"])


def saved_view(database: Session, _: AttachmentStorage, payload: dict[str, Any], __: Any) -> Any:
    owner = payload.pop("owner_id")
    return create_view(database, owner, SavedViewCreate.model_validate(payload))


def primary_photo(
    database: Session, storage: AttachmentStorage, payload: dict[str, Any], __: Any
) -> None:
    v4.primary.set_primary(
        database,
        storage,
        payload["target"],
        payload["target_id"],
        PrimaryPhotoSelection(kind="local", photo_id=payload["link_id"]),
    )


def external_cover(
    database: Session, storage: AttachmentStorage, payload: dict[str, Any], __: Any
) -> Any:
    identity = payload.pop("identity_id")
    set_external_identity_cover(database, storage, identity, ExternalCoverWrite(**payload))
    return database.scalars(
        select(BotanicalIdentityCoverImage).where(
            BotanicalIdentityCoverImage.botanical_identity_id == identity
        )
    ).one()


OPERATIONS: dict[str, Operation] = {
    "owner": owner_node,
    "generated_asset": generated_asset,
    "external_asset": external_asset,
    "taxon_link": taxon_link,
    "retire_supplier": retire_supplier,
    "sow_transition": sow_transition,
    "plant_from_sowing": plant_from_sowing,
    "group_from_sowing": group_from_sowing,
    "propagation_reverse": propagation_reverse,
    "transfer": transfer,
    "reintegrate": reintegrate,
    "disposition": disposition,
    "conversion": conversion,
    "conversion_reverse": conversion_reverse,
    "schedule_complete": schedule_complete,
    "schedule_cancel": schedule_cancel,
    "saved_view": saved_view,
    "primary": primary_photo,
    "external_cover": external_cover,
}
# These owning services always commit, so they run only after the atomic graph has committed.
COMMITTING_KINDS = {"primary", "external_cover"}


def apply_node(
    database: Session,
    storage: AttachmentStorage,
    node: dict[str, Any],
    refs: dict[str, Any],
    ledger: dict[str, Any],
) -> None:
    key, kind = node["key"], node["kind"]
    if kind not in OPERATIONS:
        local = key.split(":", 1)[1]
        node = {**node, "extraction_event": f"event:{local}#extraction"}
        v5.apply_node(database, storage, node, refs, ledger, {})
        return
    row = OPERATIONS[kind](database, storage, v5.resolve(node["payload"], refs), ledger)
    if row is not None:
        refs[key] = row.id
        ledger["records"][key] = str(row.id)


def refuse_commit(session: Session) -> None:
    """Prove the graph phase is one transaction, so a failure leaves no partial dataset."""
    if not session.in_nested_transaction():
        raise GoldenError("A service committed inside the atomic golden graph")


def deny_network() -> None:
    """Generation and validation never need a provider; a real attempt fails the run."""

    def refused(*_: object, **__: object) -> NoReturn:
        raise GoldenError("Golden dataset attempted unexpected network access")

    socket.create_connection = refused
    httpx.HTTPTransport.handle_request = refused
    httpx.AsyncHTTPTransport.handle_async_request = refused


def code_head() -> str:
    head = ScriptDirectory.from_config(Config(str(Path.cwd() / "alembic.ini"))).get_current_head()
    if head is None:
        raise GoldenError("Alembic has no single code head")
    return str(head)


def configured_copy(settings: Settings) -> str:
    """The copy this configuration names, checked without touching any database or file."""
    name = make_url(settings.database_url).database or ""
    if not (
        settings.database_disposable
        and settings.environment is Environment.TEST
        and not os.environ.get("FLORABASE_WORKFLOW_MODE")
        and COPY_NAME.fullmatch(name)
        and Path(settings.attachment_storage_root) == COPY_ROOT / name
    ):
        raise GoldenError("Golden target refused: not a disposable golden copy; no data changed")
    return name


def lock_copy(name: str) -> int:
    """Hold the copy's one exclusive lifecycle lock until the returned descriptor closes.

    Every action takes it exactly once, before touching the copy, and never waits. The file is never
    removed or replaced, so all actions on a name contend on one inode, and the kernel releases it if
    the holder dies. Python descriptors are not inherited, so a migration child cannot retain it.
    """
    if not COPY_NAME.fullmatch(name):
        raise GoldenError("A golden copy is named golden_<lowercase>; refused")
    LOCK_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(LOCK_ROOT / f"{name}.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        os.close(descriptor)
        raise GoldenBusy(f"Another golden action holds {name}; nothing changed") from error
    return descriptor


def require_target(settings: Settings, database: Session) -> Path:
    """Refuse everything except an explicitly disposable golden copy at the code's schema head."""
    name = configured_copy(settings)
    root = Path(settings.attachment_storage_root)
    if not root.is_dir():
        raise GoldenError(f"Golden media root is missing: {root}; create the copy first")
    actual = database.scalar(text("SELECT current_database()"))
    if actual != name:
        raise GoldenError("Connected database identity refused; no data changed")
    revision = database.scalar(text("SELECT version_num FROM alembic_version"))
    if revision != code_head():
        raise GoldenError(f"Golden copy schema {revision} is not code head; no data changed")
    return root


def read_ledger(root: Path) -> dict[str, Any] | None:
    path = root / LEDGER
    if not path.is_file():
        return None
    value: dict[str, Any] = json.loads(path.read_text())
    return value


def write_ledger(root: Path, ledger: dict[str, Any]) -> None:
    temporary = root / (LEDGER + ".tmp")
    with temporary.open("w") as stream:
        json.dump(ledger, stream, sort_keys=True, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(root / LEDGER)


def media_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name not in {LEDGER, LEDGER + ".tmp"}
    )


def require_pristine(database: Session, root: Path) -> None:
    v4.require_empty_review_collection(database)
    if database.scalar(select(func.count()).select_from(User)):
        raise GoldenError("Golden target already has users; no data changed")
    if media_files(root):
        raise GoldenError("Golden media root is not empty; no data changed")


def generate(
    database: Session, root: Path, plan: dict[str, Any], *, fail_after: int | None = None
) -> dict[str, Any]:
    digest = golden_plan.plan_digest(plan)
    existing = read_ledger(root)
    if existing is not None:
        if existing.get("plan_sha256") != digest:
            raise GoldenError("A different golden plan owns this copy; no data changed")
        if existing["state"] == "ready":
            return existing
        if existing["state"] != "failed" or not existing.get("clean"):
            raise GoldenError(f"Golden copy is {existing['state']}; retire it instead of repairing")
    require_pristine(database, root)
    ledger: dict[str, Any] = {
        "dataset": plan["dataset"],
        "version": plan["version"],
        "profile": plan["profile"],
        "seed": plan["seed"],
        "anchor_date": plan["anchor_date"],
        "volume": plan["volume"],
        "plan_sha256": digest,
        "schema_revision": code_head(),
        "state": "building",
        "records": {},
        "created_files": [],
    }
    write_ledger(root, ledger)
    refs = v5.canonical_country_refs(database)
    storage = AttachmentStorage(root)
    graph = [node for node in plan["nodes"] if node["kind"] not in COMMITTING_KINDS]
    finishing = [node for node in plan["nodes"] if node["kind"] in COMMITTING_KINDS]
    try:
        event.listen(database, "before_commit", refuse_commit)
        for index, node in enumerate(graph):
            if index == fail_after:
                raise GoldenError("Injected failure before golden completion")
            try:
                apply_node(database, storage, node, refs, ledger)
            except Exception as error:
                raise GoldenError(f"{node['key']}: {type(error).__name__}: {error}") from error
        database.flush()
        event.remove(database, "before_commit", refuse_commit)
        ledger["state"] = "prepared"
        write_ledger(root, ledger)
        database.commit()
        for index, node in enumerate(finishing, start=len(graph)):
            if index == fail_after:
                raise GoldenError("Injected failure after the graph committed")
            apply_node(database, storage, node, refs, ledger)
        database.commit()
    except Exception as error:
        database.rollback()
        ledger["diagnostic"] = f"{type(error).__name__}: {error}"
        # Before the commit, the DB rolled back and this run proved the media root was its own.
        ledger["clean"] = ledger["state"] == "building"
        if ledger["clean"]:
            for child in root.iterdir():
                if child.name != LEDGER:
                    shutil.rmtree(child) if child.is_dir() else child.unlink()
            ledger["records"], ledger["created_files"] = {}, []
        ledger["state"] = "failed"
        write_ledger(root, ledger)
        raise
    ledger["state"] = "ready"
    write_ledger(root, ledger)
    return ledger


def application_tables() -> list[Table]:
    return [table for _, table in sorted(Base.metadata.tables.items())]


def row_identity(table: Table) -> Any:
    return table.c.get("id")


def uuid_labels(database: Session) -> dict[str, str]:
    """UUIDv7 ids are monotonic per process, so a table ordinal is their stable logical name."""
    labels: dict[str, str] = {}
    for table in application_tables():
        column = row_identity(table)
        if column is None:
            continue
        if table.name == "geographic_places":
            for identifier, kind, code in database.execute(
                select(column, table.c.place_kind, table.c.source_code)
            ):
                if kind == "canonical":
                    labels[str(identifier)] = f"canonical:{code}"
            custom = select(column).where(table.c.place_kind == "custom").order_by(column)
            rows = list(database.scalars(custom))
        else:
            rows = list(database.scalars(select(column).order_by(column)))
        for ordinal, identifier in enumerate(rows):
            labels[str(identifier)] = f"{table.name}#{ordinal}"
    return labels


UNRESOLVED = "<unresolved-uuid>"


def canonical_value(value: Any, labels: dict[str, str]) -> Any:
    if isinstance(value, UUID):
        return labels.get(str(value), UNRESOLVED)
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: canonical_value(item, labels) for key, item in value.items()}
    if isinstance(value, list):
        return [canonical_value(item, labels) for item in value]
    if isinstance(value, str):
        return UUID_PATTERN.sub(lambda match: labels.get(match[0], UNRESOLVED), value)
    return value


def canonical_digest(database: Session, root: Path) -> dict[str, Any]:
    """Logical database and media content; only ids, wall clocks and secrets are normalized."""
    labels = uuid_labels(database)
    tables: dict[str, dict[str, Any]] = {}
    unresolved = 0
    for table in application_tables():
        if table.name in EXCLUDED_TABLES:
            continue
        lines = []
        for row in database.execute(select(table)).mappings():
            content = {}
            for column in table.columns:
                if (table.name, column.name) in EXCLUDED_COLUMNS:
                    continue
                value = row[column.name]
                if isinstance(column.type, DateTime) and value is not None:
                    content[column.name] = "<timestamp>"
                else:
                    content[column.name] = canonical_value(value, labels)
            line = json.dumps(content, sort_keys=True, ensure_ascii=False, default=str)
            unresolved += line.count(UNRESOLVED)
            lines.append(line)
        lines.sort()
        tables[table.name] = {
            "rows": len(lines),
            "sha256": hashlib.sha256("\n".join(lines).encode()).hexdigest(),
        }
    # Bytes of every file, managed or not; object names are random per copy, so only content counts.
    media = sorted(hashlib.sha256(path.read_bytes()).hexdigest() for path in media_files(root))
    ledger = read_ledger(root) or {}
    # The reviewed meaning of each stable scenario key: which logical row it names in this copy.
    scenario_keys = canonical_value(ledger.get("records", {}), labels)
    summary: dict[str, Any] = {
        "media_files": len(media),
        "media_sha256": hashlib.sha256("\n".join(media).encode()).hexdigest(),
        "scenario_keys_sha256": hashlib.sha256(
            json.dumps(scenario_keys, sort_keys=True).encode()
        ).hexdigest(),
        "tables": tables,
    }
    combined = json.dumps(summary, sort_keys=True).encode()
    return {
        **summary,
        "canonical_sha256": hashlib.sha256(combined).hexdigest(),
        "schema_revision": database.scalar(text("SELECT version_num FROM alembic_version")),
        # A UUID no table owns would otherwise vanish into a placeholder and hide a real difference.
        "unresolved_uuids": unresolved,
    }


def table_counts(database: Session) -> dict[str, int]:
    counts = {}
    for table in application_tables():
        statement = select(func.count()).select_from(table)
        if table.name == "geographic_places":
            statement = statement.where(table.c.place_kind == "custom")
        count = database.scalar(statement) or 0
        if count:
            counts[table.name] = int(count)
    return counts


def read_projections(database: Session, anchor: date) -> dict[str, Any]:
    """Real read services over the copy, at the fixed anchor rather than the wall clock."""
    dashboard = overview(database, anchor)
    mapped = collection_provenance_map(database)
    return {
        "dashboard.overdue": dashboard.overdue,
        "dashboard.due_today": dashboard.due_today,
        "dashboard.next_seven_days": dashboard.next_seven_days,
        "dashboard.sowings_unknown_germination": dashboard.sowings_unknown_germination,
        "dashboard.sowings_zero_germination": dashboard.sowings_zero_germination,
        "dashboard.purchase_packets_without_order": dashboard.purchase_packets_without_order,
        "identities": len(list_botanical_identities(database)),
        "locations": len(list_locations(database)),
        "seed_lots": len(v4.seeds.list_seed_lots(database)),
        "sowings": len(v4.sowings.list_sowings(database)),
        "plants": len(v4.plants.list_plants(database)),
        "plant_groups": len(v4.plants.list_plant_groups(database)),
        "harvests": len(v4.harvests.list_harvests(database)),
        "stored_material": len(list_inventory(database)),
        "suppliers": len(v4.suppliers.list_suppliers(database)),
        "orders": v4.orders.list_orders(database).total,
        "history": list_history(database).total,
        "media.local": v4.media.list_assets(database, kind="local").total,
        "media.external": v4.media.list_assets(database, kind="external").total,
        "media.unlinked": v4.media.list_assets(database, association="unlinked").total,
        "schedule.planned": v4.schedule.list_activities(database, today=anchor).total,
        "provenance.sites": mapped.total_provenance_sites,
        "provenance.without_coordinates": mapped.coordinate_less_sites,
    }


def check_invariant(
    database: Session, ledger: dict[str, Any], invariant: dict[str, Any]
) -> str | None:
    key, field = invariant["key"], invariant["field"]
    identifier = ledger["records"].get(key)
    if identifier is None:
        return f"{key}: not recorded"
    row = database.get(MODELS[key.split(":", 1)[0]], UUID(identifier))
    if row is None:
        return f"{key}: missing"
    actual = getattr(row, field)
    if "equals_ref" in invariant:
        expected = ledger["records"].get(invariant["equals_ref"])
        return None if str(actual) == expected else f"{key}.{field}: {actual} != {expected}"
    if invariant.get("is_null"):
        return None if actual is None else f"{key}.{field}: expected null"
    if invariant.get("not_null"):
        return None if actual is not None else f"{key}.{field}: expected a value"
    expected = invariant["equals"]
    normalized = canonical_value(actual, {}) if isinstance(actual, Decimal) else actual
    return None if normalized == expected else f"{key}.{field}: {normalized!r} != {expected!r}"


def media_problems(database: Session, root: Path) -> list[str]:
    problems = []
    expected: set[Path] = set()
    for attachment in database.scalars(select(Attachment)):
        path = root / attachment.storage_key
        expected.add(path)
        if not path.is_file():
            problems.append(f"media missing: attachment {attachment.id}")
            continue
        content = path.read_bytes()
        if (
            len(content) != attachment.byte_size
            or hashlib.sha256(content).hexdigest() != attachment.sha256
        ):
            problems.append(f"media differs: attachment {attachment.id}")
    for path in media_files(root):
        if path not in expected:
            problems.append(f"unmanaged media file: {path.relative_to(root)}")
    for asset in database.scalars(select(MediaAsset)):
        if asset.kind == "local":
            if asset.attachment_id is None:
                problems.append(f"local asset without attachment: {asset.id}")
            continue
        for url in (asset.image_url, asset.source_url):
            if urlsplit(url or "").hostname != "example.invalid":
                problems.append(f"external asset leaves example.invalid: {asset.id}")
        if asset.fetched_at is not None or asset.attachment_id is not None:
            problems.append(f"external asset was fetched: {asset.id}")
    return problems


def validate(database: Session, root: Path, plan: dict[str, Any]) -> list[str]:
    """Return every detected problem; an empty list is the only success."""
    ledger = read_ledger(root)
    if ledger is None:
        return ["golden ledger is missing"]
    problems = []
    if ledger.get("state") != "ready":
        problems.append(f"golden ledger state is {ledger.get('state')}")
    if ledger.get("plan_sha256") != golden_plan.plan_digest(plan):
        problems.append("golden ledger belongs to a different plan")
    records = ledger.get("records", {})
    for node in plan["nodes"]:
        if not node["key"].startswith("op:") and node["key"] not in records:
            problems.append(f"plan node not recorded: {node['key']}")
    for key, value in records.items():
        prefix = key.split(":", 1)[0]
        if prefix == "range":
            row = database.get(
                BotanicalProfileNativeRange, (UUID(value["identity"]), UUID(value["place"]))
            )
        else:
            row = database.get(MODELS[prefix], UUID(value))
        if row is None:
            problems.append(f"managed record missing: {key}")
    manifest = golden_plan.load_manifest()
    included = {node["scenario"] for node in plan["nodes"]}
    for entry in manifest["scenarios"]:
        if entry["id"] not in included:
            continue
        for invariant in entry["invariants"]:
            failure = check_invariant(database, ledger, invariant)
            if failure:
                problems.append(f"{entry['id']}: {failure}")
    problems.extend(media_problems(database, root))
    for model, column in SYNTHETIC_LABELS:
        unmarked = database.scalars(
            select(column).where(column.is_not(None), column.not_like("Golden%")).limit(1)
        ).first()
        if unmarked is not None:
            problems.append(f"{model.__name__} label is not marked synthetic: {unmarked}")
    profile = manifest["profiles"][plan["profile"]]
    expected = profile.get("expected")
    if expected and plan["volume"] == profile["volume"]:
        if expected["plan_sha256"] != golden_plan.plan_digest(plan):
            problems.append("plan digest differs from the reviewed manifest pin")
        actual = table_counts(database)
        if actual != expected["tables"]:
            problems.append(f"table counts differ from the pin: {actual}")
        projections = read_projections(database, date.fromisoformat(plan["anchor_date"]))
        if projections != expected["projections"]:
            problems.append(f"read projections differ from the pin: {projections}")
    return problems


def baseline_unavailable(plan: dict[str, Any], current: dict[str, Any]) -> str | None:
    """Why no reviewed baseline applies; never falls back to anything read from the target."""
    profile = golden_plan.load_manifest()["profiles"][plan["profile"]]
    baseline = profile.get("expected", {}).get("baseline")
    if baseline is None:
        return f"profile {plan['profile']} has no reviewed baseline"
    if plan["volume"] != baseline["volume"]:
        return f"volume {plan['volume']} has no reviewed baseline; pinned {baseline['volume']}"
    if golden_plan.plan_digest(plan) != baseline["plan_sha256"]:
        return "plan differs from the reviewed baseline's plan"
    if current["schema_revision"] != baseline["schema_revision"]:
        return (
            f"schema {current['schema_revision']} has no reviewed baseline; "
            f"pinned {baseline['schema_revision']}"
        )
    return None


def baseline_differences(baseline: dict[str, Any], current: dict[str, Any]) -> list[str]:
    differences = [
        f"{field}: {current[field]} != reviewed {baseline[field]}"
        for field in ("media_files", "media_sha256", "scenario_keys_sha256")
        if current[field] != baseline[field]
    ]
    tables = baseline["tables"].keys() | current["tables"].keys()
    differences += [
        f"table {table}: {current['tables'].get(table)} != reviewed {baseline['tables'].get(table)}"
        for table in sorted(tables)
        if current["tables"].get(table) != baseline["tables"].get(table)
    ]
    if current["unresolved_uuids"]:
        differences.append(f"unresolved UUIDs: {current['unresolved_uuids']}")
    if not differences and current["canonical_sha256"] != baseline["canonical_sha256"]:
        differences.append("canonical digest differs from the reviewed baseline")
    return differences


def verify_baseline(database: Session, root: Path, plan: dict[str, Any]) -> dict[str, Any]:
    """Domain validation plus comparison with the reviewed, version-controlled digest."""
    problems = validate(database, root, plan)
    current = canonical_digest(database, root)
    unavailable = baseline_unavailable(plan, current)
    differences = []
    if unavailable is None:
        profile = golden_plan.load_manifest()["profiles"][plan["profile"]]
        differences = baseline_differences(profile["expected"]["baseline"], current)
    if problems:
        state = "domain-invalid"
    elif unavailable:
        state = "baseline-unavailable"
    elif differences:
        state = "invariant-valid-baseline-modified"
    else:
        state = "baseline-verified"
    return {
        "baseline_differences": differences,
        "baseline_unavailable": unavailable,
        "canonical_sha256": current["canonical_sha256"],
        "domain_problems": problems,
        "schema_revision": current["schema_revision"],
        "state": state,
    }


def copy_environment(name: str, settings: Settings) -> dict[str, str]:
    if not COPY_NAME.fullmatch(name):
        raise GoldenError("A golden copy is named golden_<lowercase>; refused")
    if not (
        settings.database_disposable
        and settings.environment is Environment.TEST
        and not os.environ.get("FLORABASE_WORKFLOW_MODE")
    ):
        raise GoldenError("Golden copies exist only beside disposable test PostgreSQL; refused")
    url = make_url(settings.database_url).set(database=name)
    return {
        "FLORABASE_DATABASE_URL": url.render_as_string(hide_password=False),
        "FLORABASE_ATTACHMENT_STORAGE_ROOT": str(COPY_ROOT / name),
    }


def maintenance(settings: Settings, statement: str) -> None:
    engine = create_engine(settings.database_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql(statement)
    finally:
        engine.dispose()


def create_copy(name: str, settings: Settings) -> None:
    """A new, empty database and media root; the schema always comes from Alembic, never a clone."""
    environment = copy_environment(name, settings)
    if (COPY_ROOT / name).exists():
        raise GoldenError(f"Golden media root already exists: {COPY_ROOT / name}; no data changed")
    maintenance(settings, f'CREATE DATABASE "{name}"')
    (COPY_ROOT / name).mkdir(parents=True, mode=0o700)
    subprocess.run(
        ["alembic", "upgrade", "head"],
        env={**os.environ, **environment},
        check=True,
        capture_output=True,
    )


def retire_copy(name: str, settings: Settings) -> None:
    copy_environment(name, settings)
    maintenance(settings, f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
    shutil.rmtree(COPY_ROOT / name, ignore_errors=True)
    if (COPY_ROOT / name).exists():
        raise GoldenError(f"Golden media root survived retirement: {COPY_ROOT / name}")


def run_copy_action(args: argparse.Namespace, settings: Settings) -> int:
    deny_network()
    with Session(get_engine()) as database:
        root = require_target(settings, database)
        started = time.monotonic()
        result: dict[str, Any] = {"baseline": "not-checked"}
        if args.action == "digest":
            # Diagnostic only: reports what is there, including on a damaged copy, and claims nothing.
            result |= canonical_digest(database, root)
            result["seconds"] = round(time.monotonic() - started, 3)
            print(json.dumps(result, sort_keys=True))
            return 0
        plan = golden_plan.build_plan(args.profile)
        if args.action == "verify-baseline":
            report = verify_baseline(database, root, plan)
            print(json.dumps(report, sort_keys=True))
            return {
                "baseline-verified": 0,
                "domain-invalid": EXIT_DOMAIN_INVALID,
                "invariant-valid-baseline-modified": EXIT_BASELINE_MODIFIED,
                "baseline-unavailable": EXIT_BASELINE_UNAVAILABLE,
            }[report["state"]]
        if args.action == "generate":
            ledger = generate(database, root, plan, fail_after=args.fail_after)
            result |= {"state": ledger["state"], "records": len(ledger["records"])}
        problems = validate(database, root, plan)
        if problems:
            for problem in problems:
                print(f"Golden validation failed: {problem}", file=sys.stderr)
            return EXIT_DOMAIN_INVALID
        result |= {
            "domain": "valid",
            "plan_sha256": golden_plan.plan_digest(plan),
            "seconds": round(time.monotonic() - started, 3),
        }
        if args.action == "validate":
            result["counts"] = table_counts(database)
            result["projections"] = read_projections(
                database, date.fromisoformat(plan["anchor_date"])
            )
        print(json.dumps(result, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=["create-copy", "generate", "validate", "verify-baseline", "digest", "retire-copy"],
    )
    parser.add_argument("--copy", help="golden_<name>: run the action against that copy")
    parser.add_argument("--profile", default="smoke")
    parser.add_argument("--fail-after", type=int, help="Regression hook: fail before this node")
    args = parser.parse_args()
    descriptor = None
    try:
        settings = get_settings()
        if args.action in {"create-copy", "retire-copy"}:
            copy_environment(args.copy or "", settings)
            descriptor = lock_copy(args.copy)
            (create_copy if args.action == "create-copy" else retire_copy)(args.copy, settings)
            return 0
        if args.copy:
            # Nothing has connected yet, so the rebuilt settings and engine are the only ones used.
            os.environ.update(copy_environment(args.copy, settings))
            get_settings.cache_clear()
            get_engine.cache_clear()
            settings = get_settings()
        descriptor = lock_copy(configured_copy(settings))
        return run_copy_action(args, settings)
    except GoldenBusy as error:
        print(f"Golden dataset busy: {error}", file=sys.stderr)
        return EXIT_BUSY
    except Exception as error:
        print(f"Golden dataset refused/failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    finally:
        if descriptor is not None:
            os.close(descriptor)


if __name__ == "__main__":
    raise SystemExit(main())
