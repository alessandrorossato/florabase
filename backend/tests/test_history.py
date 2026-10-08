from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid7

import pytest

from florabase.history import api
from florabase.history.schemas import HistoryCategory, HistoryResponse, HistorySubjectKind
from florabase.history.service import list_history
from florabase.saved_views.state import SavedViewSurface, canonical_state


@pytest.mark.parametrize("precision", [None, "year", "month", "day"])
def test_projection_preserves_date_basis_and_precision(precision: str | None) -> None:
    source_id = uuid7()
    row = {
        "total": 1,
        "key": f"event:{source_id}",
        "source_kind": "event",
        "source_id": source_id,
        "category": "event",
        "subtype": "observation",
        "title": "Observation",
        "context": "",
        "precision": precision,
        "year": "2026" if precision else None,
        "month": "10" if precision in {"month", "day"} else None,
        "day": "7" if precision == "day" else None,
        "recorded_at": datetime(2026, 10, 7, tzinfo=UTC),
        "occurred_at": None,
        "primary": {"kind": "plant", "id": uuid7(), "label": "Plant"},
        "related": [],
        "status": None,
    }
    database = MagicMock()
    database.execute.return_value.mappings.return_value.all.return_value = [row]
    result = list_history(database).items[0]
    assert result.date_basis == ("occurred" if precision else "recorded")
    if precision:
        assert result.occurred_on
        assert result.occurred_on.precision == precision
        assert result.occurred_on.day == (7 if precision == "day" else None)
    else:
        assert result.occurred_on is None
    assert result.key == row["key"]


def test_empty_page_total_and_api_filter_forwarding() -> None:
    database = MagicMock()
    database.execute.return_value.mappings.return_value.all.return_value = [
        {"total": 101, "key": None}
    ]
    assert list_history(database, offset=200).model_dump() == {
        "items": [],
        "total": 101,
        "offset": 200,
        "limit": 50,
    }
    expected = HistoryResponse(items=[], total=0, offset=0, limit=100)
    with patch.object(api, "list_history", return_value=expected) as projected:
        assert (
            api.read_history(
                MagicMock(),
                database,
                [HistoryCategory.EVENT, HistoryCategory.EVENT],
                HistorySubjectKind.PLANT,
                2026,
                0,
                100,
            )
            == expected
        )
        projected.assert_called_once_with(
            database,
            categories=(HistoryCategory.EVENT,),
            subject_kind=HistorySubjectKind.PLANT,
            year=2026,
            offset=0,
            limit=100,
        )


@pytest.mark.parametrize(
    "state",
    [
        {"offset": 50},
        {"year": 0},
        {"year": True},
        {"year": "2026"},
        {"category": ["unknown"]},
        {"subject_kind": "supplier"},
        {},
    ],
)
def test_history_saved_state_rejects_invalid_transient_and_defaults(state: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match=r"validation error|Choose a search"):
        canonical_state(SavedViewSurface.HISTORY, 1, state)


def test_history_saved_state_canonicalizes_only_stable_filters() -> None:
    assert canonical_state(
        SavedViewSurface.HISTORY,
        1,
        {"category": ["harvest", "event", "harvest"], "year": 2026, "subject_kind": "plant"},
    ) == {"category": ["event", "harvest"], "year": 2026, "subject_kind": "plant"}
