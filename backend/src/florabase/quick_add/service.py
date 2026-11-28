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
from florabase.taxonomy.source import WfoSource, WfoTaxon, path


@dataclass(frozen=True)
class QuickAddError(Exception):
    status: int
    code: str
    message: str


def _name_key(value: str) -> str:
    return " ".join(value.split()).casefold()


def _picked_taxon(new: QuickAddNewIdentity, source: WfoSource) -> WfoTaxon | None:
    """The picked WFO taxon, refused unless it is classified and its name matches."""
    if new.wfo is None:
        return None
    nodes = source.hierarchy([new.wfo.source_taxon_id])
    taxon = nodes.get(new.wfo.source_taxon_id)
    if taxon is None or _name_key(taxon.scientific_name) != _name_key(new.scientific_name):
        raise QuickAddError(
            422,
            "wfo_name_mismatch",
            "The scientific name no longer matches the WFO name you picked. Pick it again.",
        )
    if not path(nodes, taxon.source_taxon_id):
        raise QuickAddError(
            422,
            "wfo_not_linkable",
            "This WFO name is unplaced in the WFO classification and cannot be linked. "
            "Save it without the WFO link or pick another name.",
        )
    return taxon


def _link(
    database: Session, identity: BotanicalIdentity, taxon: WfoTaxon, source: WfoSource
) -> None:
    taxonomy.confirm(
        database,
        identity.id,
        TaxonomyLinkWrite(
            source_taxon_id=taxon.source_taxon_id,
            # The suggestion came from this same local index moments ago; the name check above
            # guards against an index swapped in between.
            checksum=source.metadata().checksum,
            expected_version=None,
            identity_updated_at=identity.updated_at,
        ),
        source,
    )


def _identity(
    database: Session, new: QuickAddNewIdentity, source: WfoSource
) -> tuple[BotanicalIdentity, bool, bool]:
    """Create the identity (or reuse its exact duplicate) and confirm the picked WFO name."""
    taxon = _picked_taxon(new, source)
    fields = new.model_dump(exclude={"wfo"})
    if taxon is not None:
        # Store the WFO spelling of the name the user picked.
        fields["scientific_name"] = taxon.scientific_name
    payload = BotanicalIdentityCreate.model_validate(fields)
    try:
        identity = create_botanical_identity(database, payload)
        created = True
    except BotanicalIdentityConflictError as error:
        existing = database.get(BotanicalIdentity, error.existing_id) if error.existing_id else None
        if existing is None:
            raise QuickAddError(
                409, "identity_conflict", "That identity changed meanwhile. Try again."
            ) from error
        identity, created = existing, False
    linked = database.get(WfoLink, identity.id) is not None
    # A new identity, or an existing one without any link, takes the picked name; an existing
    # link is never replaced.
    if taxon is not None and not linked:
        _link(database, identity, taxon, source)
        linked = True
    return identity, created, linked


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
