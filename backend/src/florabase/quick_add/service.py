"""QUICK-ADD-001: identity, optional WFO link and Plant/PlantGroup in one transaction.

Everything goes through the existing domain operations (identity creation with duplicate
detection, TAXONOMY-001 link confirmation, Plant/PlantGroup creation); this module only
orders them so a failure anywhere leaves nothing behind.
"""

from dataclasses import dataclass
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import (
    BotanicalIdentityCreate,
    format_identity_display_label,
)
from florabase.botanical_identities.service import (
    BotanicalIdentityConflictError,
    create_botanical_identity,
)
from florabase.plants.schemas import PlantCreate, PlantGroupCreate
from florabase.plants.service import create_plant, create_plant_group
from florabase.quick_add.schemas import QuickAddNewIdentity, QuickAddRequest, QuickAddResponse
from florabase.taxonomy import service as taxonomy
from florabase.taxonomy.model import WfoLink
from florabase.taxonomy.schemas import TaxonomyLinkWrite
from florabase.taxonomy.source import WfoSource


@dataclass(frozen=True)
class QuickAddError(Exception):
    status: int
    code: str
    message: str


def _name_key(value: str) -> str:
    return " ".join(value.split()).casefold()


def _identity(
    database: Session, new: QuickAddNewIdentity, source: WfoSource
) -> tuple[BotanicalIdentity, bool, bool]:
    """Create the identity (or reuse its exact duplicate) and confirm the picked WFO name."""
    payload = BotanicalIdentityCreate.model_validate(new.model_dump(exclude={"wfo"}))
    try:
        identity = create_botanical_identity(database, payload)
    except BotanicalIdentityConflictError as error:
        existing = database.get(BotanicalIdentity, error.existing_id) if error.existing_id else None
        if existing is None:
            raise QuickAddError(
                409, "identity_conflict", "That identity changed meanwhile. Try again."
            ) from error
        # An existing identity keeps its own taxonomy link: quick add never relinks it.
        return existing, False, database.get(WfoLink, existing.id) is not None
    if new.wfo is None:
        return identity, True, False
    nodes = source.hierarchy([new.wfo.source_taxon_id])
    taxon = nodes.get(new.wfo.source_taxon_id)
    if taxon is None or _name_key(taxon.scientific_name) != _name_key(identity.scientific_name):
        raise QuickAddError(
            422,
            "wfo_name_mismatch",
            "The scientific name no longer matches the WFO name you picked. Pick it again.",
        )
    taxonomy.confirm(
        database,
        identity.id,
        TaxonomyLinkWrite(
            source_taxon_id=taxon.source_taxon_id,
            # The suggestion came from this same local index moments ago.
            checksum=source.metadata().checksum,
            expected_version=None,
            identity_updated_at=identity.updated_at,
        ),
        source,
    )
    return identity, True, True


def quick_add(database: Session, payload: QuickAddRequest, source: WfoSource) -> QuickAddResponse:
    if payload.identity.new is not None:
        identity, created, linked = _identity(database, payload.identity.new, source)
        identity_id: UUID = identity.id
    else:
        assert payload.identity.existing_id is not None
        existing = database.get(BotanicalIdentity, payload.identity.existing_id)
        if existing is None:
            raise QuickAddError(
                404, "botanical_identity_not_found", "Botanical identity not found."
            )
        identity, created = existing, False
        identity_id = existing.id
        linked = database.get(WfoLink, identity_id) is not None
    fields = {
        "botanical_identity_id": identity_id,
        "label": payload.label,
        "location_id": payload.location_id,
        "supplier_id": payload.supplier_id,
        "direct_origin_kind": payload.direct_origin_kind,
        "collection_entry_date": payload.collection_entry_date,
        "notes": payload.notes,
    }
    try:
        if payload.material == "plant":
            record_id = create_plant(database, PlantCreate.model_validate(fields)).id
        else:
            group = PlantGroupCreate.model_validate(fields | {"quantity": payload.quantity})
            record_id = create_plant_group(database, group).id
    except ValidationError as error:
        raise QuickAddError(
            422, "invalid_record", "; ".join(str(item["msg"]) for item in error.errors())
        ) from error
    return QuickAddResponse(
        record_kind=payload.material,
        record_id=record_id,
        identity_id=identity_id,
        identity_display_label=format_identity_display_label(
            identity.scientific_name, identity.cultivar_name
        ),
        identity_created=created,
        wfo_linked=linked,
    )
