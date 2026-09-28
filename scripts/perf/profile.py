"""Focused CPU profile of the measured expensive SeedLot/Geography response builders."""

import cProfile
import pstats
from io import StringIO

from florabase.core.config import get_settings
from florabase.db.session import get_engine
from florabase.geographic_places.api import list_all
from florabase.seed_lots.service import list_seed_lots, responses
from sqlalchemy.orm import Session

settings = get_settings()
if not settings.database_disposable or not settings.database_url.endswith(
    "/florabase_perf"
):
    raise RuntimeError("Only the disposable PERF fixture may be profiled")
with Session(get_engine()) as db:
    responses(db, list_seed_lots(db))
    profile = cProfile.Profile()
    profile.enable()
    for _ in range(7):
        responses(db, list_seed_lots(db))
        list_all(None, db)
    profile.disable()
    output = StringIO()
    pstats.Stats(profile, stream=output).strip_dirs().sort_stats(
        "cumulative"
    ).print_stats(35)
    print(output.getvalue())
