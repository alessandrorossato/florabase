import json
from pathlib import Path

from florabase.main import app

destination = Path(__file__).resolve().parents[1] / "openapi.json"
destination.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
