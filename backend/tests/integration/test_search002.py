"""SEARCH-002 real matching, deduplication, partial dates and bounded projections."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import Connection, event
from sqlalchemy.orm import Session

from florabase.attachments.model import Attachment
from florabase.collection_photos.model import BotanicalIdentityCoverImage, MediaAsset
from florabase.events.model import EventKind
from florabase.harvests.schemas import HarvestWrite
from florabase.harvests.service import list_harvests, write_harvest
from florabase.media import service as media
from florabase.media.schemas import ExternalAssetCreate, LinkWrite, MediaTarget
from florabase.plants.model import Plant, PlantGroup
from florabase.search.schemas import SearchKind
from florabase.search.service import SearchFilters, search

from .test_search import _api_get, _ids
from .test_search import records as records

pytestmark = pytest.mark.integration
pytest_plugins = ["integration.test_seed_lot_api"]


@pytest.fixture
def coverage_records(records: dict[str, UUID], database_connection: Connection) -> dict[str, UUID]:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        plant = db.get(Plant, records["plant"])
        assert plant is not None
        plant.supplier_id = records["supplier"]
        plant.material_provenance_place_id = records["place"]
        plant.provenance_site_id = records["site"]
        harvest = write_harvest(
            db,
            HarvestWrite.model_validate(
                {
                    "plant_id": plant.id,
                    "label": "Summer basket %_",
                    "notes": "Private balsamic harvest note",
                    "occurred_on": {"precision": "year", "year": 2026},
                    "items": [
                        {"material_kind": "leaf", "description": "Aromatic sprigs"},
                        {"material_kind": "leaf", "description": "Aromatic young leaves"},
                        {"material_kind": "stem_or_shoot", "description": "Tender stems"},
                        {"material_kind": "seed"},
                    ],
                }
            ),
        )
        group_harvest = write_harvest(
            db,
            HarvestWrite.model_validate(
                {
                    "plant_group_id": records["group"],
                    "items": [{"material_kind": "flower"}],
                    "occurred_on": {"precision": "month", "year": 2025, "month": 9},
                }
            ),
        )
        unknown = write_harvest(
            db,
            HarvestWrite.model_validate(
                {
                    "plant_id": plant.id,
                    "items": [{"material_kind": "fruit"}],
                }
            ),
        )
        attachment = Attachment(
            original_filename="summer-photo%_.png",
            storage_key="objects/aa/" + "a" * 32,
            media_type="image/png",
            byte_size=1,
            sha256="a" * 64,
        )
        db.add(attachment)
        db.flush()
        local = MediaAsset(
            kind="local", attachment_id=attachment.id, attribution="Garden photographer"
        )
        db.add(local)
        external = media.create_external_asset(
            db,
            ExternalAssetCreate(
                title="Summer shared image",
                attribution="Reference author",
                image_url="https://example.invalid/private.jpg",
                source_url="https://example.invalid/private-source",
                licence_label="Excluded licence text",
            ),
        )
        saved_copy = Attachment(
            original_filename="saved-reference-copy.png",
            storage_key="objects/bb/" + "b" * 32,
            media_type="image/png",
            byte_size=1,
            sha256="b" * 64,
        )
        db.add(saved_copy)
        db.flush()
        external.attachment_id = saved_copy.id
        external.fetched_at = datetime.now(UTC)
        db.flush()
        targets: list[tuple[MediaTarget, UUID]] = [
            ("plant", plant.id),
            ("plant_group", records["group"]),
            ("supplier", records["supplier"]),
            ("harvest", harvest.id),
        ]
        for target, target_id in targets:
            media.create_link(db, target, target_id, external.id, LinkWrite())
        db.add(
            BotanicalIdentityCoverImage(
                botanical_identity_id=records["identity"],
                media_asset_id=external.id,
                source_mode="external",
            )
        )
        db.commit()
        return {
            **records,
            "harvest": harvest.id,
            "group_harvest": group_harvest.id,
            "unknown_harvest": unknown.id,
            "owned_event": harvest.event_id,
            "local": local.id,
            "external": external.id,
        }


@pytest.mark.parametrize(
    "query",
    [
        "summer basket",
        "north plant",
        "ACMELLA",
        "toothache",
        "balsamic",
        "leaf",
        "leaves",
        "stem_or_shoot",
        "aromatic",
        "%_",
        "tender stems",
    ],
)
def test_harvest_authoritative_text_and_multiple_items(
    coverage_records: dict[str, UUID], database_connection: Connection, query: str
) -> None:
    with Session(bind=database_connection) as db:
        result = search(db, query, SearchFilters(kinds=(SearchKind.HARVEST,)))
        ids = _ids(result, SearchKind.HARVEST)
        assert coverage_records["harvest"] in ids
        assert len(ids) == len(set(ids))
        hit = next(
            hit
            for group in result.groups
            for hit in group.items
            if hit.id == coverage_records["harvest"]
        )
        assert hit.title == "Summer basket %_"
        assert hit.href == f"#/harvests/{hit.id}"
        assert "2026" in hit.context
        assert "2026-" not in hit.context
        assert "Private" not in hit.context
        assert "balsamic" not in hit.context
        assert "Plant: North plant" in hit.context


def test_derived_title_matches_directory_and_group_source(
    coverage_records: dict[str, UUID], database_connection: Connection
) -> None:
    with Session(bind=database_connection) as db:
        result = search(
            db, "South group — Flowers harvest", SearchFilters(kinds=(SearchKind.HARVEST,))
        )
        assert _ids(result, SearchKind.HARVEST) == [coverage_records["group_harvest"]]
        hit = result.groups[0].items[0]
        assert hit.title == next(h.display_title for h in list_harvests(db) if h.id == hit.id)
        assert "2025-09" in hit.context
        assert "2025-09-" not in hit.context
        # Removing the optional label also exercises distinct/order/+ more derivation.
        from florabase.harvests.model import Harvest

        row = db.get(Harvest, coverage_records["harvest"])
        assert row is not None
        row.label = None
        db.flush()
        title = next(h.display_title for h in list_harvests(db) if h.id == row.id)
        assert title == "North plant — Leaves + Stem / shoot + more harvest"
        assert (
            search(db, title, SearchFilters(kinds=(SearchKind.HARVEST,))).groups[0].items[0].title
            == title
        )


@pytest.mark.parametrize(
    ("query", "key"),
    [
        ("summer shared", "external"),
        ("reference author", "external"),
        ("summer-photo", "local"),
        ("garden photographer", "local"),
        ("%_", "local"),
    ],
)
def test_media_uses_exact_library_metadata(
    coverage_records: dict[str, UUID], database_connection: Connection, query: str, key: str
) -> None:
    with Session(bind=database_connection) as db:
        result = search(db, query, SearchFilters(kinds=(SearchKind.MEDIA_ASSET,)))
        assert _ids(result, SearchKind.MEDIA_ASSET) == [coverage_records[key]]
        assert result.total == 1
        assert set(_ids(result, SearchKind.MEDIA_ASSET)) == {
            a.id for a in media.list_assets(db, query=query).items
        }
        hit = result.groups[0].items[0]
        assert hit.href == f"#/media/{hit.id}"
        assert "storage" not in hit.context
        assert "https" not in hit.context
        assert hit.title == ("Summer shared image" if key == "external" else "summer-photo%_.png")
        assert ("External image" if key == "external" else "Local image") in hit.context


@pytest.mark.parametrize(
    "query",
    [
        "north plant",
        "cercatoridisemì",
        "toothache",
        "private-source",
        "Excluded licence",
        "private/storage",
    ],
)
def test_media_has_no_link_cover_or_url_inference(
    coverage_records: dict[str, UUID], database_connection: Connection, query: str
) -> None:
    with Session(bind=database_connection) as db:
        assert search(db, query, SearchFilters(kinds=(SearchKind.MEDIA_ASSET,))).total == 0


def test_media_search_matches_saved_external_copy_filename(
    coverage_records: dict[str, UUID], database_connection: Connection
) -> None:
    with Session(bind=database_connection) as db:
        result = search(
            db, "saved-reference-copy.png", SearchFilters(kinds=(SearchKind.MEDIA_ASSET,))
        )
        assert _ids(result, SearchKind.MEDIA_ASSET) == [coverage_records["external"]]
        hit = result.groups[0].items[0]
        assert hit.title == "Summer shared image"
        assert "https://example.invalid" not in hit.context


def test_harvest_filter_scope_and_event_independence(
    coverage_records: dict[str, UUID], database_connection: Connection
) -> None:
    r = coverage_records
    with Session(bind=database_connection) as db:
        identity = search(
            db, "", SearchFilters(kinds=(SearchKind.HARVEST,), identity_id=r["identity"])
        )
        assert set(_ids(identity, SearchKind.HARVEST)) == {
            r["harvest"],
            r["group_harvest"],
            r["unknown_harvest"],
        }
        assert (
            search(db, "", SearchFilters(kinds=(SearchKind.HARVEST,), identity_id=r["plant"])).total
            == 0
        )
        assert _ids(
            search(db, "", SearchFilters(kinds=(SearchKind.HARVEST,), year=2026)),
            SearchKind.HARVEST,
        ) == [r["harvest"]]
        assert _ids(
            search(db, "", SearchFilters(kinds=(SearchKind.HARVEST,), year=2025)),
            SearchKind.HARVEST,
        ) == [r["group_harvest"]]
        assert search(db, "", SearchFilters(kinds=(SearchKind.HARVEST,), year=2024)).total == 0
        incompatible = [
            SearchFilters(kinds=(SearchKind.HARVEST,), location_id=r["child"]),
            SearchFilters(kinds=(SearchKind.HARVEST,), supplier_id=r["supplier"]),
            SearchFilters(kinds=(SearchKind.HARVEST,), provenance_place_id=r["place"]),
            SearchFilters(kinds=(SearchKind.HARVEST,), provenance_site_id=r["site"]),
            SearchFilters(kinds=(SearchKind.HARVEST,), lifecycle="active"),
            SearchFilters(kinds=(SearchKind.HARVEST,), event_kind=EventKind.HARVEST),
        ]
        for filters in incompatible:
            assert search(db, "", filters).total == 0
        for query in (
            "glasshouse",
            "cercatoridisemì",
            "alta valley",
            "riverside",
            "does not exist",
        ):
            assert search(db, query, SearchFilters(kinds=(SearchKind.HARVEST,))).total == 0
        both = search(db, "balsamic", SearchFilters(kinds=(SearchKind.HARVEST, SearchKind.EVENT)))
        assert _ids(both, SearchKind.HARVEST) == [r["harvest"]]
        assert _ids(both, SearchKind.EVENT) == [r["owned_event"]]
        assert both.total == 2


def test_mixed_pagination_order_and_query_counts_do_not_grow_with_results(
    coverage_records: dict[str, UUID], database_connection: Connection
) -> None:
    with Session(bind=database_connection) as db:
        statements: list[str] = []

        def capture(_conn: object, _cursor: object, statement: str, *_args: object) -> None:
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        filters = SearchFilters(kinds=(SearchKind.HARVEST, SearchKind.MEDIA_ASSET))
        event.listen(database_connection, "before_cursor_execute", capture)
        try:
            first = search(db, "summer", filters, limit=1)
            assert first.total == 3
            assert len(statements) == 6
            assert [(g.kind, g.total) for g in first.groups] == [
                (SearchKind.HARVEST, 1),
                (SearchKind.MEDIA_ASSET, 2),
            ]
            statements.clear()
            second = search(db, "summer", filters, offset=1, limit=1)
            assert len(statements) == 6
            assert second.total == first.total
            assert not set(_ids(first, SearchKind.MEDIA_ASSET)) & set(
                _ids(second, SearchKind.MEDIA_ASSET)
            )
            assert _ids(second, SearchKind.HARVEST) == []
        finally:
            event.remove(database_connection, "before_cursor_execute", capture)
        group = db.get(PlantGroup, coverage_records["group"])
        assert group is not None
        for index in range(24):
            write_harvest(
                db,
                HarvestWrite.model_validate(
                    {
                        "plant_group_id": group.id,
                        "label": f"Summer basket {index:02}",
                        "items": [{"material_kind": "leaf"}] * 3,
                    }
                ),
            )
            media.create_external_asset(
                db,
                ExternalAssetCreate(
                    title=f"Summer image {index:02}",
                    image_url=f"https://example.invalid/{index}.png",
                    source_url="https://example.invalid/source",
                    attribution="Author",
                ),
            )
        db.flush()
        event.listen(database_connection, "before_cursor_execute", capture)
        try:
            statements.clear()
            page = search(db, "summer", filters, limit=10)
            assert len(statements) == 6
            assert page.total == 51
            again = search(db, "summer", filters, limit=10)
            assert again.model_dump() == page.model_dump()
            all_pages = [
                search(db, "summer", filters, limit=10, offset=offset) for offset in (0, 10, 20)
            ]
            for kind, count in ((SearchKind.HARVEST, 25), (SearchKind.MEDIA_ASSET, 26)):
                ids = [record_id for p in all_pages for record_id in _ids(p, kind)]
                assert len(ids) == len(set(ids)) == count
        finally:
            event.remove(database_connection, "before_cursor_execute", capture)
        # Reference-only fallback exposes neither UUID nor URL.
        asset = media.create_external_asset(
            db,
            ExternalAssetCreate(
                image_url="https://example.invalid/fallback.png",
                source_url="https://example.invalid/source",
                attribution="Author",
            ),
        )
        db.flush()
        hit = next(
            h
            for g in search(db, "", SearchFilters(kinds=(SearchKind.MEDIA_ASSET,))).groups
            for h in g.items
            if h.id == asset.id
        )
        assert hit.title == "External image reference"


def test_new_kinds_http_validation_and_auth(
    coverage_records: dict[str, UUID], authenticated_browser: tuple[str, str]
) -> None:
    cookie, _ = authenticated_browser
    for kind in ("harvest", "media_asset"):
        assert _api_get(f"/api/v1/search?kind={kind}", "")[0] == 401
        status, result = _api_get(f"/api/v1/search?q=summer&kind={kind}", cookie)
        assert status == 200
        assert isinstance(result["total"], int)
        assert result["total"] > 0
    status, result = _api_get(
        "/api/v1/search?q=summer&kind=plant&kind=harvest&kind=media_asset", cookie
    )
    assert status == 200
    assert result["total"] == 3
    assert _api_get("/api/v1/search?kind=harvest&year=2026", cookie)[0] == 200
    for query in (
        "kind=unknown",
        "kind=harvest&lifecycle=active",
        "kind=media_asset&year=2026",
        "kind=harvest&event_kind=harvest",
        "kind=harvest&kind=plant&year=2026",
    ):
        assert _api_get(f"/api/v1/search?{query}", cookie)[0] == 422


@pytest.mark.parametrize(
    ("kind", "query", "key", "route"),
    [
        (SearchKind.SEED_LOT, "summer packet", "seed", "seeds"),
        (SearchKind.SOWING, "tray one", "sowing", "sowings"),
        (SearchKind.PLANT, "north plant", "plant", "plants"),
        (SearchKind.PLANT_GROUP, "south group", "group", "plant-groups"),
        (SearchKind.EVENT, "bright flowers", "event", "plants"),
        (SearchKind.BOTANICAL_IDENTITY, "toothache", "identity", "identities"),
        (SearchKind.BOTANICAL_PROFILE, "edible flowers", "identity", "identities"),
        (SearchKind.SUPPLIER, "cercatoridisemì", "supplier", "suppliers"),
        (SearchKind.LOCATION, "warm bench", "child", "locations"),
        (SearchKind.GEOGRAPHIC_PLACE, "alta valley", "place", "geography"),
        (SearchKind.PROVENANCE_SITE, "riverside site", "site", "geography"),
    ],
)
def test_all_search001_kinds_keep_matching_and_routes(
    coverage_records: dict[str, UUID],
    database_connection: Connection,
    kind: SearchKind,
    query: str,
    key: str,
    route: str,
) -> None:
    with Session(bind=database_connection) as db:
        result = search(db, query, SearchFilters(kinds=(kind,)))
        assert _ids(result, kind) == [coverage_records[key]]
        assert result.total == 1
        assert result.groups[0].items[0].href.startswith(f"#/{route}")


def test_harvest_fallback_names_and_full_partial_date_preserve_directory_title(
    coverage_records: dict[str, UUID], database_connection: Connection
) -> None:
    from florabase.botanical_identities.model import BotanicalIdentity

    with Session(bind=database_connection) as db:
        plant = db.get(Plant, coverage_records["plant"])
        identity = db.get(BotanicalIdentity, coverage_records["identity"])
        assert plant is not None
        assert identity is not None
        plant.label = None
        identity.cultivar_name = "Golden queen"
        harvest = write_harvest(
            db,
            HarvestWrite.model_validate(
                {
                    "plant_id": plant.id,
                    "occurred_on": {"precision": "day", "year": 2026, "month": 1, "day": 2},
                    "items": [{"material_kind": "root"}],
                }
            ),
        )
        for expected in ("Toothache plant", "Golden queen", "Acmella oleracea"):
            title = f"{expected} — Roots harvest"
            result = search(db, title, SearchFilters(kinds=(SearchKind.HARVEST,)))
            assert _ids(result, SearchKind.HARVEST) == [harvest.id]
            hit = result.groups[0].items[0]
            assert hit.title == next(
                h.display_title for h in list_harvests(db) if h.id == harvest.id
            )
            assert "2026-01-02" in hit.context
            identity.common_name = None
            if expected == "Golden queen":
                identity.cultivar_name = None
            db.flush()


def test_equal_titles_sort_by_uuid_and_all_kind_queries_stay_bounded(
    coverage_records: dict[str, UUID], database_connection: Connection
) -> None:
    with Session(bind=database_connection) as db:
        for key in ("local", "external"):
            asset = db.get(MediaAsset, coverage_records[key])
            assert asset is not None
            asset.title = "Same title"
        db.flush()
        statements: list[str] = []

        def capture(_conn: object, _cursor: object, statement: str, *_args: object) -> None:
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        event.listen(database_connection, "before_cursor_execute", capture)
        try:
            result = search(db, "same title", SearchFilters())
            assert len(statements) == 30
            assert _ids(result, SearchKind.MEDIA_ASSET) == sorted(
                [coverage_records["local"], coverage_records["external"]]
            )
        finally:
            event.remove(database_connection, "before_cursor_execute", capture)
