from decimal import Decimal
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock
from uuid import uuid7

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from florabase.auth.dependencies import AuthenticatedActor
from florabase.events.service import EventDomainConflictError
from florabase.harvests import inventory_api as api
from florabase.harvests import inventory_service
from florabase.harvests.inventory_schemas import (
    DispositionCreate,
    InventoryResponse,
    InventoryWrite,
)
from florabase.harvests.inventory_service import disposition_result
from florabase.harvests.model import MaterialKind
from florabase.harvests.schemas import HarvestQuantity
from florabase.locations.service import LocationIntegrityError, LocationNotFoundError


def test_inventory_api_list_filters_are_forwarded(monkeypatch: pytest.MonkeyPatch) -> None:
    database_mock = MagicMock(spec=Session)
    database = cast(Session, database_mock)
    harvest_id, location_id = uuid7(), uuid7()
    list_inventory = MagicMock(return_value=[])
    monkeypatch.setattr(inventory_service, "list_inventory", list_inventory)

    assert (
        api.list_all(
            database,
            cast(AuthenticatedActor, object()),
            harvest_id=harvest_id,
            state="active",
            material_kind=MaterialKind.SEED,
            location_id=location_id,
        )
        == []
    )
    list_inventory.assert_called_once_with(
        database,
        harvest_id=harvest_id,
        state="active",
        material_kind=MaterialKind.SEED,
        location_id=location_id,
    )


@pytest.mark.parametrize(
    ("failure", "status", "code"),
    [
        (LookupError("missing"), 404, "harvest_inventory_not_found"),
        (LocationNotFoundError("missing"), 404, "location_not_found"),
        (LocationIntegrityError("location_scope", "scope disabled"), 409, "location_scope"),
        (EventDomainConflictError("depleted", "already depleted"), 409, "depleted"),
        (RuntimeError("database constraint"), 409, "harvest_conflict"),
    ],
)
def test_inventory_api_errors_roll_back_and_translate(
    failure: Exception, status: int, code: str
) -> None:
    database_mock = MagicMock(spec=Session)
    database = cast(Session, database_mock)

    translated = api.error(database, failure)

    assert translated.status_code == status
    detail = cast(dict[str, str], translated.detail)
    assert detail["code"] == code
    database_mock.rollback.assert_called()


def test_inventory_api_write_routes_commit_and_return_fresh_views(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_mock = MagicMock(spec=Session)
    database = cast(Session, database_mock)
    actor = cast(AuthenticatedActor, SimpleNamespace(owner=True))
    item_id, inventory_id = uuid7(), uuid7()
    payload = InventoryWrite(state="active", quantity=q())
    inventory = cast(InventoryResponse, SimpleNamespace(id=inventory_id))
    response = cast(InventoryResponse, object())
    monkeypatch.setattr(inventory_service, "track", MagicMock(return_value=inventory))
    monkeypatch.setattr(inventory_service, "correct", MagicMock())
    monkeypatch.setattr(inventory_service, "remove_tracking", MagicMock())
    monkeypatch.setattr(inventory_service, "read_inventory", MagicMock(return_value=response))

    assert api.create(item_id, payload, database, actor) is response
    database_mock.commit.assert_called_once()
    database_mock.reset_mock()
    assert api.correct(inventory_id, payload, database, actor) is response
    database_mock.commit.assert_called_once()
    database_mock.reset_mock()
    assert api.remove(inventory_id, database, actor).status_code == 204
    database_mock.commit.assert_called_once()


def q(
    value: str = "10",
    *,
    approximate: bool = False,
    kind: str = "item_count",
    unit: str | None = None,
) -> HarvestQuantity:
    return HarvestQuantity.model_validate(
        {"kind": kind, "value": value, "unit": unit, "is_approximate": approximate}
    )


@pytest.mark.parametrize(
    "kind", ["consumed", "processed", "discarded", "gifted", "used_for_propagation"]
)
def test_exact_partial_categories(kind: str) -> None:
    used, after = disposition_result(
        q(), DispositionCreate.model_validate({"kind": kind, "mode": "partial", "quantity": q("3")})
    )
    assert used == q("3")
    assert after == q("7")


@pytest.mark.parametrize("before", [None, q(), q(approximate=True)])
def test_use_all_preserves_amount_precision_without_invention(
    before: HarvestQuantity | None,
) -> None:
    assert disposition_result(before, DispositionCreate(kind="discarded", mode="use_all")) == (
        before,
        None,
    )


@pytest.mark.parametrize(
    "used", [None, q("11"), q("10"), q("3", approximate=True), q("3", kind="weight", unit="g")]
)
def test_exact_partial_rejects_invalid_usage(used: HarvestQuantity | None) -> None:
    with pytest.raises(EventDomainConflictError):
        disposition_result(q(), DispositionCreate(kind="consumed", mode="partial", quantity=used))


def test_exact_subtraction_does_not_round_postgres_numeric() -> None:
    before = q("100000000000000000000000000000000000.00000000000000000001", kind="weight", unit="g")
    used = q("0.00000000000000000001", kind="weight", unit="g")
    _, after = disposition_result(
        before, DispositionCreate(kind="processed", mode="partial", quantity=used)
    )
    assert after is not None
    assert after.value == Decimal("100000000000000000000000000000000000")


def test_approximate_partial_requires_compatible_confirmed_estimate() -> None:
    before = q("100", approximate=True, kind="weight", unit="g")
    for after in [
        None,
        q("60", kind="weight", unit="g"),
        q("60", approximate=True, kind="weight", unit="mg"),
    ]:
        with pytest.raises(EventDomainConflictError):
            disposition_result(
                before,
                DispositionCreate(kind="processed", mode="partial", resulting_quantity=after),
            )
    confirmed = q("60", approximate=True, kind="weight", unit="g")
    assert disposition_result(
        before, DispositionCreate(kind="processed", mode="partial", resulting_quantity=confirmed)
    ) == (None, confirmed)


def test_unknown_partial_keeps_unknown_even_with_known_usage() -> None:
    assert disposition_result(
        None, DispositionCreate(kind="gifted", mode="partial", quantity=q("3"))
    ) == (q("3"), None)
    with pytest.raises(EventDomainConflictError):
        disposition_result(
            None, DispositionCreate(kind="gifted", mode="partial", resulting_quantity=q("3"))
        )


@pytest.mark.parametrize("value", ["0", "-1", "NaN", "Infinity"])
def test_active_numeric_must_be_positive_finite(value: str) -> None:
    with pytest.raises(ValidationError):
        InventoryWrite(state="active", quantity=q(value))


def test_depleted_has_no_quantity_and_all_has_no_supplied_delta() -> None:
    assert InventoryWrite(state="depleted", quantity=None).quantity is None
    with pytest.raises(ValidationError):
        InventoryWrite(state="depleted", quantity=q())
    with pytest.raises(ValidationError):
        DispositionCreate(kind="consumed", mode="use_all", quantity=q())
