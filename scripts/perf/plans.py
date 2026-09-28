"""Explain exact PERF-001 fixture read statements; never operator data."""

import json

from florabase.core.config import get_settings
from florabase.db.session import get_engine
from florabase.events.service import list_all_events
from florabase.geographic_places.service import list_geographic_places
from florabase.seed_lots.service import list_seed_lots
from sqlalchemy import event
from sqlalchemy.orm import Session

settings = get_settings()
if not settings.database_disposable or not settings.database_url.endswith(
    "/florabase_perf"
):
    raise RuntimeError("Only the disposable PERF fixture may be explained")
result = {}
with Session(get_engine()) as db:
    for label, load in [
        ("seeds", lambda: list_seed_lots(db)),
        ("recent_events", lambda: list_all_events(db, limit=6)),
        ("geography", lambda: list_geographic_places(db)),
    ]:
        statements = []

        def capture(
            connection,
            cursor,
            statement,
            parameters,
            context,
            executemany,
            captured=statements,
        ):
            captured.append((statement, parameters))

        connection = db.connection()
        event.listen(connection, "before_cursor_execute", capture)
        try:
            load()
        finally:
            event.remove(connection, "before_cursor_execute", capture)
        result[label] = []
        for statement, parameters in statements:
            plan = connection.exec_driver_sql(
                "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + statement, parameters
            ).scalar_one()
            result[label].append({"sql": statement, "plan": plan})
print(json.dumps(result, indent=2, default=str))
