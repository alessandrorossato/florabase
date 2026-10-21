"""Read existing ranges with shared collection representation; no geometry or provider I/O."""

from collections.abc import Sequence
from typing import Literal
from uuid import UUID

from sqlalchemy import Text, cast, distinct, func, literal, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.selectable import CTE, Subquery

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_profiles.model import BotanicalProfileNativeRange as NativeRange
from florabase.explore import service
from florabase.explore.schemas import (
    CollectionRecordCategory,
    NativeRangeIdentity,
    NativeRangeIdentityPage,
    NativeRangeOverview,
    NativeRangeSelection,
    RecordedPlaceCoverage,
    RecordedRangePlace,
    RepresentationScope,
    SelectedNativeRanges,
    SelectedTerritoryCoverage,
    TerritoryRangeEvidence,
    TerritoryRangeIdentity,
    TerritoryRangeIdentityPage,
)
from florabase.geographic_places.model import GeographicPlace as Place


def _identities(
    scope: RepresentationScope,
    q: str,
    with_range: bool,
    record: Sequence[CollectionRecordCategory] = (),
) -> Subquery:
    statement = service.filtered_projection(scope, q, record)
    if with_range:
        statement = statement.where(
            select(NativeRange.botanical_profile_id)
            .where(NativeRange.botanical_profile_id == BotanicalIdentity.id)
            .exists()
        )
    return statement.subquery("represented")


def _range_counts() -> Subquery:
    return (
        select(NativeRange.botanical_profile_id, func.count().label("range_count"))
        .group_by(NativeRange.botanical_profile_id)
        .subquery()
    )


def _places_with_paths(place_ids: Subquery) -> CTE:
    # Walk ancestors once for the selected set, never one query per row. Custom reparenting
    # is reflected immediately. Text cast prevents the recursive type from being varchar(255).
    paths = (
        select(
            Place.id,
            Place.parent_id,
            cast(Place.name, Text).label("path"),
        )
        .where(Place.id.in_(select(place_ids.c.geographic_place_id)))
        .cte("range_paths", recursive=True)
    )
    return paths.union_all(
        select(paths.c.id, Place.parent_id, Place.name + " → " + paths.c.path).join(
            paths, Place.id == paths.c.parent_id
        )
    )


def _place_rows(
    database: Session, ranges: Subquery, offset: int, limit: int
) -> list[RecordedPlaceCoverage]:
    paths = _places_with_paths(ranges)
    rows = database.execute(
        select(Place, paths.c.path, ranges.c.identity_count)
        .join(ranges, ranges.c.geographic_place_id == Place.id)
        .join(paths, paths.c.id == Place.id)
        .where(paths.c.parent_id.is_(None))
        .order_by(ranges.c.identity_count.desc(), func.lower(paths.c.path), Place.id)
        .offset(offset)
        .limit(limit)
    )
    return [
        RecordedPlaceCoverage(
            id=place.id,
            name=place.name,
            display_path=path,
            place_kind=place.place_kind,
            source_code_type=place.source_code_type,
            source_code=place.source_code,
            identity_count=count,
        )
        for place, path, count in rows
    ]


def _territory_ancestors() -> CTE:
    # Canonical ISO territories are fixed reference data. Ascend only canonical parents;
    # custom ranges never inherit parent polygons. No geometry is persisted or queried.
    ancestors = (
        select(
            Place.id.label("territory_id"),
            Place.id.label("ancestor_id"),
            Place.parent_id,
            Place.source_code_type.label("ancestor_code_type"),
        )
        .where(Place.place_kind == "canonical", Place.source_code_type == "iso_3166_1_alpha_2")
        .cte("territory_ancestors", recursive=True)
    )
    return ancestors.union_all(
        select(ancestors.c.territory_id, Place.id, Place.parent_id, Place.source_code_type)
        .join(ancestors, Place.id == ancestors.c.parent_id)
        .where(Place.place_kind == "canonical")
    )


def _territories(
    database: Session, represented: Subquery, *, contributors: bool = False
) -> list[SelectedTerritoryCoverage]:
    ancestors = _territory_ancestors()
    rows = database.execute(
        select(
            Place.id,
            Place.name,
            Place.source_code,
            func.count(distinct(represented.c.id)),
            func.array_agg(distinct(represented.c.id)) if contributors else literal(None),
        )
        .select_from(represented)
        .join(NativeRange, NativeRange.botanical_profile_id == represented.c.id)
        .join(ancestors, ancestors.c.ancestor_id == NativeRange.geographic_place_id)
        .join(Place, Place.id == ancestors.c.territory_id)
        .where(ancestors.c.ancestor_code_type.in_(("un_m49", "iso_3166_1_alpha_2")))
        .group_by(Place.id, Place.name, Place.source_code)
        .order_by(func.count(distinct(represented.c.id)).desc(), Place.source_code)
    )
    return [
        SelectedTerritoryCoverage(
            id=id_,
            name=name,
            source_code=code,
            identity_count=count,
            identity_ids=sorted(ids or [], key=str),
        )
        for id_, name, code, count, ids in rows
    ]


def list_identities(
    database: Session,
    *,
    q: str = "",
    scope: RepresentationScope = "all",
    with_range: bool = False,
    record: Sequence[CollectionRecordCategory] = (),
    offset: int = 0,
    limit: int = 50,
) -> NativeRangeIdentityPage:
    represented = _identities(scope, q, with_range, record)
    return _identity_page(database, represented, scope, offset, limit)


def _identity_page(
    database: Session, represented: Subquery, scope: RepresentationScope, offset: int, limit: int
) -> NativeRangeIdentityPage:
    total = database.scalar(select(func.count()).select_from(represented)) or 0
    counts = _range_counts()
    # Reuse the exact response derivation, but omit occurrence-only fields in this surface.
    rows = database.execute(
        select(
            BotanicalIdentity,
            represented.c.retained,
            represented.c.current,
            represented.c.living,
            func.coalesce(counts.c.range_count, 0),
        )
        .join(represented, represented.c.id == BotanicalIdentity.id)
        .outerjoin(counts, counts.c.botanical_profile_id == BotanicalIdentity.id)
        .order_by(
            func.lower(BotanicalIdentity.scientific_name),
            func.lower(BotanicalIdentity.cultivar_name).nulls_first(),
            BotanicalIdentity.id,
        )
        .offset(offset)
        .limit(limit)
    )
    items = [
        NativeRangeIdentity(
            **service.collection_response(identity, retained, current, living, scope).model_dump(),
            native_range_count=count,
        )
        for identity, retained, current, living, count in rows
    ]
    return NativeRangeIdentityPage(items=items, total=total, offset=offset, limit=limit)


def overview(
    database: Session,
    *,
    q: str = "",
    scope: RepresentationScope = "all",
    with_range: bool = False,
    record: Sequence[CollectionRecordCategory] = (),
    offset: int = 0,
    limit: int = 50,
) -> NativeRangeOverview:
    represented = _identities(scope, q, with_range, record)
    counts = _range_counts()
    total, with_count = database.execute(
        select(func.count(), func.count(counts.c.botanical_profile_id))
        .select_from(represented)
        .outerjoin(counts, counts.c.botanical_profile_id == represented.c.id)
    ).one()
    ranges = (
        select(NativeRange.geographic_place_id, func.count().label("identity_count"))
        .join(represented, represented.c.id == NativeRange.botanical_profile_id)
        .group_by(NativeRange.geographic_place_id)
        .subquery()
    )
    places_total = database.scalar(select(func.count()).select_from(ranges)) or 0
    return NativeRangeOverview(
        represented=total,
        with_range=with_count,
        without_range=total - with_count,
        territories=_territories(database, represented),
        places=_place_rows(database, ranges, offset, limit),
        places_total=places_total,
        offset=offset,
        limit=limit,
    )


def selected(
    database: Session,
    identity_id: UUID,
    scope: RepresentationScope = "all",
    *,
    q: str = "",
    with_range: bool = False,
    record: Sequence[CollectionRecordCategory] = (),
    offset: int = 0,
    limit: int = 50,
) -> SelectedNativeRanges | None:
    identities = _selected_identities(database, [identity_id], scope, q, with_range, record)
    if not identities:
        return None
    identity = identities[0]
    represented = _identities(scope, q, with_range, record)
    represented = select(represented).where(represented.c.id == identity_id).subquery()
    ranges = (
        select(NativeRange.geographic_place_id, func.count().label("identity_count"))
        .where(NativeRange.botanical_profile_id == identity_id)
        .group_by(NativeRange.geographic_place_id)
        .subquery()
    )
    total = database.scalar(select(func.count()).select_from(ranges)) or 0
    return SelectedNativeRanges(
        identity=identity,
        ranges=[
            RecordedRangePlace(**place.model_dump())
            for place in _place_rows(database, ranges, offset, limit)
        ],
        territories=_territories(database, represented),
        total=total,
        offset=offset,
        limit=limit,
    )


def _selected_identities(
    database: Session,
    identity_ids: Sequence[UUID],
    scope: RepresentationScope,
    q: str,
    with_range: bool,
    record: Sequence[CollectionRecordCategory],
) -> list[NativeRangeIdentity]:
    represented = service.projection().subquery()
    eligible = _identities(scope, q, with_range, record)
    counts = _range_counts()
    rows = database.execute(
        select(
            BotanicalIdentity,
            represented.c.retained,
            represented.c.current,
            represented.c.living,
            func.coalesce(counts.c.range_count, 0),
            eligible.c.id.is_not(None),
        )
        .join(represented, represented.c.id == BotanicalIdentity.id)
        .outerjoin(eligible, eligible.c.id == BotanicalIdentity.id)
        .outerjoin(counts, counts.c.botanical_profile_id == BotanicalIdentity.id)
        .where(BotanicalIdentity.id.in_(identity_ids))
        .order_by(func.lower(BotanicalIdentity.scientific_name), BotanicalIdentity.id)
    )
    return [
        NativeRangeIdentity(
            **service.collection_response(identity, retained, current, living, scope).model_dump(),
            native_range_count=count,
            matches_filters=matches,
        )
        for identity, retained, current, living, count, matches in rows
    ]


def selection(
    database: Session,
    identity_ids: Sequence[UUID],
    *,
    scope: RepresentationScope = "all",
    q: str = "",
    with_range: bool = False,
    record: Sequence[CollectionRecordCategory] = (),
) -> NativeRangeSelection:
    ids = sorted(set(identity_ids), key=str)
    if len(ids) > 20:
        raise ValueError("Select at most 20 species")
    identities = _selected_identities(database, ids, scope, q, with_range, record)
    represented = _identities(scope, q, with_range, record)
    represented = select(represented).where(represented.c.id.in_(ids)).subquery()
    found = {item.id for item in identities}
    return NativeRangeSelection(
        identities=identities,
        missing_ids=[id_ for id_ in ids if id_ not in found],
        territories=_territories(database, represented, contributors=True),
    )


def territory_identities(
    database: Session,
    codes: Sequence[str],
    *,
    match: Literal["any", "all"] = "any",
    identity_ids: Sequence[UUID] = (),
    q: str = "",
    scope: RepresentationScope = "all",
    with_range: bool = False,
    record: Sequence[CollectionRecordCategory] = (),
    offset: int = 0,
    limit: int = 50,
) -> TerritoryRangeIdentityPage:
    """Bounded union/intersection of explicit canonical drawing coverage, never occurrences."""
    codes = sorted(set(codes))
    ancestors = _territory_ancestors()
    links = (
        select(
            NativeRange.botanical_profile_id.label("identity_id"),
            Place.source_code.label("code"),
            Place.name.label("name"),
            ancestors.c.ancestor_id,
            ancestors.c.territory_id,
        )
        .join(ancestors, ancestors.c.ancestor_id == NativeRange.geographic_place_id)
        .join(Place, Place.id == ancestors.c.territory_id)
        .where(
            Place.source_code.in_(codes),
            ancestors.c.ancestor_code_type.in_(("un_m49", "iso_3166_1_alpha_2")),
        )
        .subquery("coverage_links")
    )
    matching = select(links.c.identity_id).group_by(links.c.identity_id)
    if match == "all":
        matching = matching.having(func.count(distinct(links.c.code)) == len(codes))
    represented = _identities(scope, q, with_range, record)
    filtered = select(represented).where(represented.c.id.in_(matching))
    if identity_ids:
        filtered = filtered.where(represented.c.id.in_(identity_ids))
    page = _identity_page(database, filtered.subquery(), scope, offset, limit)
    evidence: dict[UUID, dict[str, TerritoryRangeEvidence]] = {item.id: {} for item in page.items}
    if page.items:
        # One extra read for this page only; keep broad and exact links without duplicate IDs.
        rows = database.execute(
            select(links, Place.name.label("recorded_name"))
            .join(Place, Place.id == links.c.ancestor_id)
            .where(links.c.identity_id.in_(evidence))
            .order_by(links.c.code, Place.name)
        )
        for id_, code, name, ancestor_id, territory_id, recorded_name in rows:
            item = evidence[id_].setdefault(
                code,
                TerritoryRangeEvidence(
                    source_code=code, name=name, exact_recorded=False, broad_recorded_places=[]
                ),
            )
            if ancestor_id == territory_id:
                item.exact_recorded = True
            elif recorded_name not in item.broad_recorded_places:
                item.broad_recorded_places.append(recorded_name)
    return TerritoryRangeIdentityPage(
        items=[
            TerritoryRangeIdentity(
                **item.model_dump(), matching_territories=list(evidence[item.id].values())
            )
            for item in page.items
        ],
        total=page.total,
        offset=offset,
        limit=limit,
    )
