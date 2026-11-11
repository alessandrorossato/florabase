from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid7

import pytest
from fastapi import HTTPException

from florabase.lineage import api, service
from florabase.lineage.schemas import (
    AncestryChildren,
    BotanicalIdentitySummary,
    PlantGroupLineageNode,
    PlantLineageNode,
    SeedLotLineageNode,
    SowingLineageNode,
)
from florabase.lineage.service import LineageCycleError, LineageKey
from florabase.plants.model import Plant, PlantGroup
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing

IDENTITY = BotanicalIdentitySummary(id=uuid7(), display_label="Solanum lycopersicum")


def _record(key: LineageKey) -> Any:
    kind, item_id = key
    if kind == "sowing":
        return SowingLineageNode(id=item_id, label=None, lifecycle="active")
    model = {
        "seed_lot": SeedLotLineageNode,
        "plant": PlantLineageNode,
        "plant_group": PlantGroupLineageNode,
    }[kind]
    return model(id=item_id, label=str(item_id), lifecycle="active", botanical_identity=IDENTITY)


def _summaries(missing: frozenset[LineageKey] = frozenset()) -> Any:
    def summaries(_database: object, keys: list[LineageKey]) -> dict[LineageKey, Any]:
        origin = {"seed_lot": "collection_produced", "plant": "unknown"}
        return {key: (_record(key), origin.get(key[0])) for key in keys if key not in missing}

    return summaries


class FakeSession:
    """Answers each statement the explorer issues; records what was asked."""

    def __init__(
        self,
        child_rows: list[dict[str, Any]],
        count_rows: list[dict[str, Any]],
        conversions: list[tuple[Any, Any]],
        total: int = 0,
    ) -> None:
        self.child_rows, self.count_rows, self.conversions = child_rows, count_rows, conversions
        self.total = total
        self.calls: list[tuple[object, Any]] = []

    def execute(self, statement: object, params: Any = None) -> Any:
        self.calls.append((statement, params))
        result = MagicMock()
        if statement is service._CHILDREN:
            result.mappings.return_value = self.child_rows
        elif statement is service._COUNT_CHILDREN:
            result.scalar_one.return_value = self.total
        elif statement is service._PARENT_COUNTS:
            result.mappings.return_value = self.count_rows
        else:
            return self.conversions
        return result

    def asked(self, statement: object) -> list[Any]:
        return [params for called, params in self.calls if called is statement]


def test_children_page_counts_branches_and_attaches_harvest_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service, "_summaries", _summaries())
    sowing, group, lot = uuid7(), uuid7(), uuid7()
    harvest = SimpleNamespace(
        id=uuid7(),
        label="August seed heads",
        occurred_on_precision="month",
        occurred_on_year=2026,
        occurred_on_month=8,
        occurred_on_day=None,
    )
    conversion = SimpleNamespace(id=uuid7(), seed_lot_id=lot, status="reversed")
    database = FakeSession(
        child_rows=[
            {"kind": "sowing", "id": sowing, "total": 7},
            {"kind": "plant_group", "id": group, "total": 7},
            {"kind": "seed_lot", "id": lot, "total": 7},
        ],
        # A Sowing's Plants and Plant groups arrive as separate grouped rows.
        count_rows=[
            {"kind": "sowing", "id": sowing, "total": 2},
            {"kind": "sowing", "id": sowing, "total": 3},
            {"kind": "plant_group", "id": group, "total": 1},
        ],
        conversions=[(conversion, harvest)],
    )
    page = service.children(database, ("plant", uuid7()), offset=0, limit=500)  # type: ignore[arg-type]

    assert (page.total, page.limit) == (7, service.MAX_CHILDREN_PAGE)
    assert database.asked(service._CHILDREN)[0]["limit"] == service.MAX_CHILDREN_PAGE
    assert database.asked(service._PARENT_COUNTS) == [
        {
            "seed_lot": [lot],
            "sowing": [sowing],
            "plant": [],
            "plant_group": [group],
            "vegetative_lot": [],
            "propagation_attempt": [],
        }
    ]
    assert database.asked(service._COUNT_CHILDREN) == []
    by_id = {item.record.id: item for item in page.items}
    assert [item.record.id for item in page.items] == [sowing, group, lot]
    assert by_id[sowing].descendant_count == 5
    assert by_id[group].descendant_count == 1
    assert by_id[lot].descendant_count == 0
    assert by_id[lot].origin == "collection_produced"
    evidence = by_id[lot].harvest_conversion
    assert evidence is not None
    assert (evidence.status, evidence.harvest_label) == ("reversed", "August seed heads")
    assert evidence.harvested_on is not None
    assert (evidence.harvested_on.year, evidence.harvested_on.month) == (2026, 8)
    assert by_id[group].harvest_conversion is None

    harvest.occurred_on_precision = None
    undated = service.children(database, ("plant", uuid7()))  # type: ignore[arg-type]
    lot_node = next(item for item in undated.items if item.record.id == lot)
    assert lot_node.harvest_conversion is not None
    assert lot_node.harvest_conversion.harvested_on is None


def test_an_offset_past_the_end_still_reports_the_exact_total(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service, "_summaries", _summaries())
    database = FakeSession(child_rows=[], count_rows=[], conversions=[], total=27)
    parent: LineageKey = ("sowing", uuid7())

    page = service.children(database, parent, offset=50, limit=25)  # type: ignore[arg-type]

    assert (page.total, page.offset, page.items) == (27, 50, [])
    assert database.asked(service._COUNT_CHILDREN) == [{"kind": "sowing", "item_id": parent[1]}]
    # Nothing to count or convert for an empty page.
    assert database.asked(service._PARENT_COUNTS) == []
    assert len(database.calls) == 2


def test_ancestry_keeps_the_walk_order_and_refuses_a_missing_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    focus: LineageKey = ("plant", uuid7())
    sowing: LineageKey = ("sowing", uuid7())
    root: LineageKey = ("seed_lot", uuid7())
    monkeypatch.setattr(service, "_walk", lambda _database, _subject: [focus, sowing, root])
    monkeypatch.setattr(service, "_summaries", _summaries())
    database = FakeSession(child_rows=[], count_rows=[], conversions=[], total=0)

    response = service.ancestry(database, focus, limit=10)  # type: ignore[arg-type]

    assert response.focus.record.id == focus[1]
    assert response.focus.origin == "unknown"
    assert [node.record.id for node in response.ancestors] == [sowing[1], root[1]]
    assert response.children.total == 0
    assert database.asked(service._COUNT_CHILDREN) == [{"kind": "plant", "item_id": focus[1]}]

    monkeypatch.setattr(service, "_summaries", _summaries(frozenset({sowing})))
    with pytest.raises(RuntimeError, match="missing concrete record"):
        service.ancestry(database, focus)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("kind", "model"),
    [
        ("seed_lot", SeedLot),
        ("sowing", Sowing),
        ("plant", Plant),
        ("plant_group", PlantGroup),
    ],
)
def test_exists_reads_only_the_requested_concrete_table(kind: str, model: type) -> None:
    item_id = uuid7()
    database = MagicMock()
    database.get.return_value = None
    assert not service.exists(database, (kind, item_id))  # type: ignore[arg-type]
    database.get.assert_called_once_with(model, item_id)
    database.get.return_value = object()
    assert service.exists(database, (kind, item_id))  # type: ignore[arg-type]


def test_endpoints_return_not_found_conflict_and_delegate_paging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item_id, actor, database = uuid7(), MagicMock(), MagicMock()
    monkeypatch.setattr(api, "exists", lambda _database, _subject: False)
    for call in (
        lambda: api.read_ancestry("plant", item_id, actor, database),
        lambda: api.read_children("plant", item_id, actor, database),
    ):
        with pytest.raises(HTTPException) as missing:
            call()
        assert missing.value.status_code == 404
        detail: Any = missing.value.detail
        assert detail["code"] == "lineage_record_not_found"

    monkeypatch.setattr(api, "exists", lambda _database, _subject: True)

    def cycle(*_args: object, **_kwargs: object) -> None:
        raise LineageCycleError()

    monkeypatch.setattr(api, "ancestry", cycle)
    with pytest.raises(HTTPException) as conflict:
        api.read_ancestry("plant", item_id, actor, database, limit=5)
    assert conflict.value.status_code == 409
    conflict_detail: Any = conflict.value.detail
    assert conflict_detail["code"] == LineageCycleError().code

    seen: list[tuple[LineageKey, int, int]] = []

    stub = AncestryChildren(total=0, offset=25, limit=50, items=[])

    def page(_database: object, parent: LineageKey, *, offset: int, limit: int) -> AncestryChildren:
        seen.append((parent, offset, limit))
        return stub

    monkeypatch.setattr(api, "children", page)
    assert api.read_children("sowing", item_id, actor, database, offset=25, limit=50) is stub
    assert seen == [(("sowing", item_id), 25, 50)]
    assert isinstance(seen[0][0][1], UUID)
