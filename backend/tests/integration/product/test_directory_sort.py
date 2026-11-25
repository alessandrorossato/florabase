"""UX-SORT-002: whitelisted server-side Sort by for paginated directories."""

from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid7

import pytest
from sqlalchemy import Connection
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.collection_photos.model import MediaAsset
from florabase.cuttings import api as cuttings
from florabase.cuttings.schemas import AttemptCreate, VegetativeLotCreate
from florabase.cuttings.service import create_lot, start_attempt
from florabase.db.ordering import DirectorySort
from florabase.media import service as media
from florabase.orders import service as orders
from florabase.orders.schemas import OrderCreate
from integration.test_seed_lot_api import authenticated_browser as authenticated_browser
from integration.test_seed_lot_api import request

pytestmark = pytest.mark.integration
SORTS: tuple[DirectorySort, ...] = ("name", "name_desc", "newest", "oldest")
Page = Callable[[DirectorySort | None, int, int], Sequence[Any]]


def _date(year: int, month: int | None = None, day: int | None = None) -> dict[str, object]:
    precision = "day" if day else "month" if month else "year"
    return {"precision": precision, "year": year, "month": month, "day": day}


def _assert_order(page: Page, expected: dict[DirectorySort | None, list[UUID]]) -> None:
    """Each order is exact and walking one-record pages repeats it (stable id tiebreak)."""
    mine = set(expected["name"])
    for sort, ids in expected.items():
        full = [item.id for item in page(sort, 0, 100) if item.id in mine]
        walked = [item.id for offset in range(len(full)) for item in page(sort, offset, 1)]
        assert full == ids, sort
        assert walked == full, sort


def test_orders_sort_by_reference_and_partial_order_date(database_connection: Connection) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        rows = [
            ("beta", _date(2025, 3, 10)),
            ("Alpha", _date(2026)),
            (None, None),
            ("gamma", _date(2025, 3)),
            ("alpha", _date(2025, 3, 10)),
        ]
        o1, o2, o3, o4, o5 = (
            orders.create_order(
                db, OrderCreate.model_validate({"order_reference": ref, "ordered_on": on})
            ).id
            for ref, on in rows
        )
        newest = [o2, o5, o1, o4, o3]
        _assert_order(
            lambda sort, offset, limit: (
                orders.list_orders(db, sort=sort, offset=offset, limit=limit).items
            ),
            {
                "name": [o2, o5, o1, o4, o3],
                "name_desc": [o4, o1, o5, o2, o3],
                "newest": newest,
                "oldest": [o4, o1, o5, o2, o3],
                None: newest,
            },
        )


def test_media_sort_by_displayed_title_and_date_added(database_connection: Connection) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        start = datetime(2026, 1, 1, tzinfo=UTC)
        assets = [
            MediaAsset(
                id=uuid7(),
                kind="external",
                state="active",
                title=title,
                attribution=attribution,
                image_url="https://images.example.test/a.jpg",
                source_url="https://example.test/a",
                created_at=start + timedelta(days=day),
            )
            for title, attribution, day in (
                ("banana", "Ann", 1),
                (None, "Cherry author", 2),
                ("apple", "Zed", 3),
                ("Apple", "Bo", 2),
            )
        ]
        db.add_all(assets)
        db.flush()
        m1, m2, m3, m4 = (asset.id for asset in assets)
        newest = [m3, m4, m2, m1]
        _assert_order(
            lambda sort, offset, limit: (
                media.list_assets(db, sort=sort, offset=offset, limit=limit).items
            ),
            {
                "name": [m3, m4, m1, m2],
                "name_desc": [m2, m1, m4, m3],
                "newest": newest,
                "oldest": [m1, m2, m4, m3],
                None: newest,
            },
        )


def test_cutting_lots_and_attempts_sort_by_record_name_and_date(
    database_connection: Connection,
) -> None:
    actor = MagicMock()
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity = BotanicalIdentity(scientific_name="Salvia rosmarinus", common_name="Rosemary")
        db.add(identity)
        db.flush()
        l1, l2, l3, l4 = (
            create_lot(
                db,
                VegetativeLotCreate.model_validate(
                    {
                        "botanical_identity_id": identity.id,
                        "material_type": "stem_cutting",
                        "label": label,
                        "taken_on": taken,
                    }
                ),
            ).id
            for label, taken in (
                ("Bench", _date(2025, 5)),
                (None, _date(2026, 1, 2)),
                ("west", None),
                ("apple", _date(2025, 5, 1)),
            )
        )
        _assert_order(
            lambda sort, offset, limit: cuttings.list_lots(
                actor, db, sort=sort, offset=offset, limit=limit
            ),
            {
                "name": [l4, l1, l2, l3],
                "name_desc": [l3, l2, l1, l4],
                "newest": [l2, l4, l1, l3],
                "oldest": [l1, l4, l2, l3],
                None: [l4, l3, l2, l1],
            },
        )
        a1, a2, a3 = (
            start_attempt(
                db,
                l1,
                AttemptCreate.model_validate(
                    {
                        "source_adjustment": {"mode": "none"},
                        "propagation_attempt": {"label": label, "started_on": started},
                    }
                ),
            )[1].id
            for label, started in (("Zeta", _date(2024)), (None, _date(2026, 2)), ("alpha", None))
        )
        _assert_order(
            lambda sort, offset, limit: cuttings.list_attempts(
                actor, db, sort=sort, offset=offset, limit=limit
            ),
            {
                "name": [a3, a2, a1],
                "name_desc": [a1, a2, a3],
                "newest": [a2, a1, a3],
                "oldest": [a1, a2, a3],
                None: [a3, a2, a1],
            },
        )


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/orders",
        "/api/v1/media-assets",
        "/api/v1/vegetative-lots",
        "/api/v1/propagation-attempts",
    ],
)
def test_sort_parameter_is_whitelisted(authenticated_browser: tuple[str, str], path: str) -> None:
    cookie = {"cookie": authenticated_browser[0]}
    for sort in SORTS:
        assert request("GET", f"{path}?sort={sort}", headers=cookie)[0] == 200
    for invalid in ("created", "id", "name;drop", ""):
        assert request("GET", f"{path}?sort={invalid}", headers=cookie)[0] == 422
