"""Whitelisted directory order for server-paginated lists (UX-SORT-002)."""

from collections.abc import Sequence
from typing import Any, Literal

from sqlalchemy import ColumnElement, UnaryExpression, func
from sqlalchemy.orm import InstrumentedAttribute

# Same vocabulary as the client-side directories (FN-02, UX-SORT-001).
DirectorySort = Literal["name", "name_desc", "newest", "oldest"]
Column = ColumnElement[Any] | InstrumentedAttribute[Any]


def directory_order(
    sort: DirectorySort,
    *,
    name: Column,
    date: Sequence[Column],
    record_id: Column,
) -> list[UnaryExpression[Any]]:
    """Order by name or date; missing values stay last and the id keeps pages stable.

    ``date`` is one timestamp column or a partial date as (year, month, day): a
    missing month or day sorts as the start of its year or month, like the client.
    """
    descending = sort in ("name_desc", "newest")
    if sort in ("name", "name_desc"):
        keys: list[Column] = [func.lower(name)]
    else:
        first, *parts = date
        keys = [first, *(func.coalesce(part, 0) for part in parts)]
    ordered = [key.desc() if descending else key.asc() for key in keys]
    ordered[0] = ordered[0].nulls_last()
    return [*ordered, record_id.desc() if descending else record_id.asc()]
