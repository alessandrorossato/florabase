import argparse
import json
from pathlib import Path

from florabase.main import app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    destination = Path(__file__).resolve().parents[1] / "openapi.json"
    generated = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"

    if args.check:
        if destination.read_text(encoding="utf-8") != generated:
            raise SystemExit("backend/openapi.json is stale; run make api-generate")
        return

    destination.write_text(generated, encoding="utf-8")


if __name__ == "__main__":
    main()
