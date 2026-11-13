"""Optional read-only qualification CLI against official local WFO and WCVP SQLite indexes."""

# ruff: noqa: T201
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from florabase.botanical_matching import (
    IdentityMatchInput,
    MatchBatchReport,
    discover_and_classify,
    format_match_report_markdown,
    match_collection_identities,
)
from florabase.core.config import Settings, get_settings
from florabase.explore.schemas import RepresentationScope
from florabase.native_range_enrichment.source import WcvpSource
from florabase.taxonomy.source import WfoSource


def _load_inputs_from_json(source_arg: str) -> list[IdentityMatchInput]:
    raw_text = (
        sys.stdin.read() if source_arg == "-" else Path(source_arg).read_text(encoding="utf-8")
    )
    payload: Any = json.loads(raw_text)
    if isinstance(payload, dict) and "identities" in payload:
        payload = payload["identities"]
    return TypeAdapter(list[IdentityMatchInput]).validate_python(payload)


def run_qualification(
    *,
    wfo_source: WfoSource | None,
    wcvp_v16_source: WcvpSource | None,
    wcvp_v15_source: WcvpSource | None = None,
    input_json: str | None = None,
    database_url: str | None = None,
    scope: RepresentationScope = "all",
    represented_only: bool = False,
    limit: int = 1000,
    include_fuzzy_advisory: bool = True,
    max_examples: int = 5,
    include_results: bool = True,
) -> MatchBatchReport:
    if input_json is not None:
        inputs = _load_inputs_from_json(input_json)
        return discover_and_classify(
            inputs,
            wfo_source=wfo_source,
            wcvp_v16_source=wcvp_v16_source,
            wcvp_v15_source=wcvp_v15_source,
            include_fuzzy_advisory=include_fuzzy_advisory,
            max_examples=max_examples,
            include_results=include_results,
        )

    assert database_url is not None
    engine = create_engine(database_url)
    try:
        with Session(engine) as session:
            if engine.dialect.name == "postgresql":
                session.execute(text("SET TRANSACTION READ ONLY"))
            return match_collection_identities(
                session,
                wfo_source=wfo_source,
                wcvp_v16_source=wcvp_v16_source,
                wcvp_v15_source=wcvp_v15_source,
                scope=scope,
                represented_only=represented_only,
                limit=limit,
                include_fuzzy_advisory=include_fuzzy_advisory,
                max_examples=max_examples,
                include_results=include_results,
            )
    finally:
        engine.dispose()


def _resolve_sources(
    args: argparse.Namespace, settings: Settings | None
) -> tuple[WfoSource | None, WcvpSource | None, WcvpSource | None]:
    wfo_path = (
        Path(args.wfo_path) if args.wfo_path else (settings.wfo_snapshot_path if settings else None)
    )
    v16_path = (
        Path(args.wcvp_v16_path)
        if args.wcvp_v16_path
        else (settings.wcvp_v16_snapshot_path if settings else None)
    )
    v15_path = Path(args.wcvp_v15_path) if args.wcvp_v15_path else None
    require_seal = (
        args.wcvp_v16_require_seal
        if args.wcvp_v16_require_seal is not None
        else (settings.wcvp_v16_require_seal if settings else False)
    )

    wfo = WfoSource(wfo_path) if wfo_path is not None else None
    wcvp_v16 = WcvpSource(v16_path, "16", require_seal=require_seal) if v16_path else None
    wcvp_v15 = WcvpSource(v15_path, "15") if v15_path else None
    return wfo, wcvp_v16, wcvp_v15


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--input-json",
        help="Path to JSON identity list (or '-' for stdin) for offline qualification.",
    )
    mode.add_argument(
        "--database-url",
        help="PostgreSQL/SQLite URL to inspect strictly inside a READ ONLY transaction.",
    )
    parser.add_argument("--wfo-path", help="Path to WFO 2026-06 SQLite index.")
    parser.add_argument("--wcvp-v16-path", help="Path to Kew WCVP v16 SQLite index.")
    parser.add_argument("--wcvp-v15-path", help="Optional Kew WCVP v15 SQLite index.")
    parser.add_argument(
        "--wcvp-v16-require-seal",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Override WCVP v16 sibling .sha256 seal enforcement.",
    )
    parser.add_argument(
        "--scope",
        choices=("all", "living", "current", "historical"),
        default="all",
        help="Collection representation scope when reading --database-url.",
    )
    parser.add_argument(
        "--represented-only",
        action="store_true",
        help="Limit --database-url scan to represented identities.",
    )
    parser.add_argument("--limit", type=int, default=1000, help="Maximum identities to inspect.")
    parser.add_argument("--max-examples", type=int, default=5, help="Examples per exception code.")
    parser.add_argument("--no-fuzzy", action="store_true", help="Disable fuzzy genus advisory.")
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Omit per-identity detailed results from JSON output.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Report output format.",
    )
    parser.add_argument("--output", help="Optional file path to write report output.")
    parser.add_argument(
        "--require-sources",
        action="store_true",
        help="Exit non-zero if either WFO or WCVP v16 is unavailable.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings: Settings | None = None
    if args.wfo_path is None or args.wcvp_v16_path is None or args.wcvp_v16_require_seal is None:
        try:
            settings = get_settings()
        except Exception:
            settings = None

    wfo, wcvp_v16, wcvp_v15 = _resolve_sources(args, settings)
    report = run_qualification(
        wfo_source=wfo,
        wcvp_v16_source=wcvp_v16,
        wcvp_v15_source=wcvp_v15,
        input_json=args.input_json,
        database_url=args.database_url,
        scope=args.scope,
        represented_only=args.represented_only,
        limit=args.limit,
        include_fuzzy_advisory=not args.no_fuzzy,
        max_examples=args.max_examples,
        include_results=not args.summary_only,
    )

    rendered = (
        report.model_dump_json(indent=2)
        if args.format == "json"
        else format_match_report_markdown(report)
    )
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)

    if args.require_sources:
        available = {src.provider: src.available for src in report.sources}
        if not (available.get("wfo") and available.get("wcvp_v16")):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
