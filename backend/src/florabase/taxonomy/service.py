"""Read-only collection projection and explicit version-checked source relationships."""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid7

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.explore import service as collection
from florabase.explore.schemas import CollectionRecordCategory, RepresentationScope
from florabase.taxonomy.model import WfoLink
from florabase.taxonomy.schemas import (
    IdentityTaxonomy,
    TaxonomyCounts,
    TaxonomyEvidence,
    TaxonomyIdentity,
    TaxonomyLink,
    TaxonomyLinkWrite,
    TaxonomyNode,
    TaxonomyNodeDetail,
    TaxonomyRelated,
    TaxonomyTree,
)
from florabase.taxonomy.source import (
    ROOT,
    SourceUnavailableError,
    WfoMetadata,
    WfoSource,
    WfoTaxon,
    path,
)


class TaxonomyConflictError(Exception):
    pass


class TaxonomyNotFoundError(Exception):
    pass


def link_response(link: WfoLink, identity: BotanicalIdentity) -> TaxonomyLink:
    evidence = TaxonomyEvidence.model_validate(link.evidence)
    return TaxonomyLink(
        version=link.version,
        evidence=evidence,
        confirmed_at=link.confirmed_at,
        stale=evidence.identity_updated_at != identity.updated_at,
    )


def confirm(
    database: Session, identity_id: UUID, payload: TaxonomyLinkWrite, source: WfoSource
) -> TaxonomyLink:
    metadata = source.metadata()
    nodes = source.hierarchy([payload.source_taxon_id])
    classification = path(nodes, payload.source_taxon_id)
    if metadata.checksum != payload.checksum or not classification:
        raise TaxonomyConflictError(
            "Inspect and confirm a classified taxon from the reviewed WFO release."
        )
    identity = database.scalar(
        select(BotanicalIdentity)
        .where(BotanicalIdentity.id == identity_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if identity is None:
        raise TaxonomyNotFoundError("Botanical identity not found.")
    link = database.get(WfoLink, identity_id, populate_existing=True)
    if (
        link.version if link else None
    ) != payload.expected_version or identity.updated_at != payload.identity_updated_at:
        raise TaxonomyConflictError(
            "Identity or taxonomy link changed. Reload and review before confirming."
        )
    if link is None:
        link = WfoLink(identity_id=identity_id)
        database.add(link)
    link.version = uuid7()
    link.external_id = payload.source_taxon_id
    link.evidence = TaxonomyEvidence(
        source=metadata,
        taxon=nodes[payload.source_taxon_id],
        classification=classification,
        identity_updated_at=identity.updated_at,
    ).model_dump(mode="json")
    link.confirmed_at = datetime.now(UTC)
    database.flush()
    return link_response(link, identity)


def unlink(database: Session, identity_id: UUID, version: UUID) -> None:
    identity = database.scalar(
        select(BotanicalIdentity).where(BotanicalIdentity.id == identity_id).with_for_update()
    )
    if identity is None:
        raise TaxonomyNotFoundError("Botanical identity not found.")
    link = database.get(WfoLink, identity_id, populate_existing=True)
    if link is None or link.version != version:
        raise TaxonomyConflictError("Taxonomy link changed. Reload before unlinking.")
    database.delete(link)
    database.flush()


def counts(identities: Sequence[TaxonomyIdentity]) -> TaxonomyCounts:
    return TaxonomyCounts(
        represented=len(identities),
        living=sum(i.living_records > 0 for i in identities),
        current=sum(i.current_records > 0 for i in identities),
        historical=sum(i.current_records == 0 for i in identities),
    )


def project(
    identities: list[TaxonomyIdentity],
    nodes: dict[str, WfoTaxon],
    metadata: WfoMetadata | None,
    message: str | None,
    q: str = "",
) -> TaxonomyTree:
    query = q.strip().casefold()
    filtered = [
        i
        for i in identities
        if not query
        or any(
            query in value.casefold()
            for value in (
                i.display_label,
                i.common_name or "",
                *[nodes[n].scientific_name for n in i.classification_ids],
            )
        )
    ]
    contributions: dict[str, list[TaxonomyIdentity]] = {}
    for identity in filtered:
        for node_id in identity.classification_ids:
            contributions.setdefault(node_id, []).append(identity)
    projected = [
        TaxonomyNode(
            taxon=nodes[key],
            parent_id=None if key == ROOT else nodes[key].parent_source_taxon_id,
            counts=counts(values),
            identity_ids=[i.id for i in values],
        )
        for key, values in contributions.items()
    ]
    projected.sort(key=lambda n: (n.taxon.scientific_name.casefold(), n.taxon.source_taxon_id))
    return TaxonomyTree(
        source=metadata,
        source_available=metadata is not None,
        message=message,
        identities=filtered,
        nodes=projected,
        counts=counts(filtered),
        unresolved=sum(not i.classification_ids for i in filtered),
    )


def tree(
    database: Session,
    source: WfoSource,
    *,
    scope: RepresentationScope = "all",
    record: Sequence[CollectionRecordCategory] = (),
    q: str = "",
) -> TaxonomyTree:
    statement = (
        collection.filtered_projection(scope, record=record)
        .order_by(
            BotanicalIdentity.scientific_name.collate("C"),
            BotanicalIdentity.cultivar_name.nulls_first(),
            BotanicalIdentity.id,
        )
        .limit(5001)
    )
    rows = database.execute(statement).all()
    if len(rows) > 5000:
        raise TaxonomyConflictError(
            "Collection taxonomy supports up to 5,000 eligible identities. Narrow the filters."
        )
    identities = [
        TaxonomyIdentity(
            **collection.collection_response(row[0], row[1], row[2], row[3], scope).model_dump()
        )
        for row in rows
    ]
    # Stable Unicode order, independent of database collation and result insertion order.
    identities.sort(
        key=lambda i: (
            i.scientific_name.casefold(),
            i.cultivar_name is not None,
            (i.cultivar_name or "").casefold(),
            str(i.id),
        )
    )
    local = {row[0].id: row[0] for row in rows}
    links = (
        {
            link.identity_id: link
            for link in database.scalars(select(WfoLink).where(WfoLink.identity_id.in_(local)))
        }
        if local
        else {}
    )
    metadata: WfoMetadata | None = None
    nodes: dict[str, WfoTaxon] = {}
    message: str | None = None
    try:
        metadata = source.metadata()
        nodes = source.hierarchy([link.external_id for link in links.values()])
        for identity in identities:
            link = links.get(identity.id)
            if link is None:
                identity.unresolved_reason = "Not linked to taxonomy source"
                continue
            identity.source_taxon_id = link.external_id
            try:
                saved = link_response(link, local[identity.id])
            except ValidationError:
                identity.unresolved_reason = "Stored source evidence is invalid; review the link"
                continue
            if saved.stale:
                identity.unresolved_reason = (
                    "Identity changed since source confirmation; review the link"
                )
            elif (
                saved.evidence.source.checksum != metadata.checksum
                or saved.evidence.source.version != metadata.version
            ):
                identity.unresolved_reason = "Source version mismatch; review the link"
            else:
                classification = path(nodes, link.external_id)
                if (
                    not classification
                    or classification != saved.evidence.classification
                    or nodes.get(link.external_id) != saved.evidence.taxon
                ):
                    identity.unresolved_reason = (
                        "Source placement no longer agrees with confirmed evidence"
                    )
                    continue
                identity.classification_ids = [n.source_taxon_id for n in classification]
                if saved.evidence.taxon.taxonomic_status == "synonym":
                    identity.synonym_of = classification[-1].scientific_name
    except SourceUnavailableError as error:
        metadata, nodes, message = None, {}, str(error)
        for identity in identities:
            identity.classification_ids = []
            identity.unresolved_reason = (
                "Taxonomy source unavailable"
                if identity.id in links
                else "Not linked to taxonomy source"
            )
    return project(identities, nodes, metadata, message, q)


def node_detail(result: TaxonomyTree, node_id: str) -> TaxonomyNodeDetail:
    node = next((n for n in result.nodes if n.taxon.source_taxon_id == node_id), None)
    if node is None:
        raise TaxonomyNotFoundError(
            "Selected taxon is missing or has no identities under these filters."
        )
    eligible = set(node.identity_ids)
    genera = [
        n.taxon
        for n in result.nodes
        if n.taxon.rank == "genus" and eligible.intersection(n.identity_ids)
    ]
    return TaxonomyNodeDetail(
        node=node,
        represented_genera=genera,
        identities=[i for i in result.identities if i.id in eligible],
    )


def identity_taxonomy(
    database: Session,
    source: WfoSource,
    identity_id: UUID,
    scope: RepresentationScope,
    record: Sequence[CollectionRecordCategory],
    q: str,
) -> IdentityTaxonomy:
    identity = database.get(BotanicalIdentity, identity_id)
    if identity is None:
        raise TaxonomyNotFoundError("Botanical identity not found.")
    link = database.get(WfoLink, identity_id)
    saved = link_response(link, identity) if link else None
    try:
        metadata = source.metadata()
    except SourceUnavailableError as error:
        return IdentityTaxonomy(source_available=False, message=str(error), link=saved)
    related: list[TaxonomyRelated] = []
    if (
        saved
        and not saved.stale
        and saved.evidence.source.checksum == metadata.checksum
        and saved.evidence.source.version == metadata.version
    ):
        result = tree(database, source, scope=scope, record=record, q=q)
        # Source identity may be reference-only; peers always use the filtered represented set.
        target_nodes = source.hierarchy([link.external_id]) if link else {}
        target = path(target_nodes, link.external_id) if link else []
        if target != saved.evidence.classification:
            return IdentityTaxonomy(
                source_available=True,
                source=metadata,
                link=saved,
                message="Source placement differs from confirmed evidence; review the link.",
            )
        rank_nodes = [
            (n.source_taxon_id, n.rank)
            for n in reversed(target)
            if n.rank in {"genus", "family", "order"}
        ]
        for peer in result.identities:
            if peer.id == identity_id or not peer.classification_ids:
                continue
            if peer.classification_ids[-1] == target[-1].source_taxon_id:
                related.append(TaxonomyRelated(identity=peer, relation="Same source taxon"))
            else:
                for ident, rank in rank_nodes:
                    if ident in peer.classification_ids:
                        relation = {
                            "genus": "Same genus",
                            "family": "Same family",
                            "order": "Same order",
                        }[rank]
                        related.append(TaxonomyRelated(identity=peer, relation=relation))
                        break
        priorities = {"Same source taxon": 0, "Same genus": 1, "Same family": 2, "Same order": 3}
        related.sort(
            key=lambda r: (
                priorities[r.relation],
                r.identity.display_label.casefold(),
                str(r.identity.id),
            )
        )
    return IdentityTaxonomy(source_available=True, source=metadata, link=saved, related=related)
