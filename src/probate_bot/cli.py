from __future__ import annotations

import argparse
import sys

from probate_bot.config import GEORGIA_CONVENIENT_COUNTIES, find_source, get_sources
from probate_bot.exporters import write_csv, write_json
from probate_bot.models import ComplianceError, ProbateBotError, SearchRequest
from probate_bot.scrapers.cobb_benchmark import CobbBenchmarkScraper
from probate_bot.scrapers.georgia_probate_records import GeorgiaProbateRecordsScraper


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="probate-bot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_sources = subparsers.add_parser("list-sources", help="List source coverage and notes.")
    list_sources.add_argument("--state", choices=["ga", "sc"], default=None)

    run = subparsers.add_parser("run", help="Run a probate scraper.")
    run.add_argument("--state", choices=["ga", "sc"], required=True)
    run.add_argument("--county", action="append", default=[])
    run.add_argument("--all-convenient", action="store_true")
    run.add_argument("--start-date")
    run.add_argument("--end-date")
    run.add_argument(
        "--date-field",
        choices=["filed", "deceased"],
        default="filed",
        help="Which portal date range to search. Defaults to filed date.",
    )
    run.add_argument("--out", required=True)
    run.add_argument("--format", choices=["csv", "json"], default="csv")
    run.add_argument("--headed", action="store_true")
    run.add_argument("--max-results-per-county", type=int, default=100)
    run.add_argument(
        "--use-case",
        choices=["research", "solicitation"],
        default="research",
        help="Purpose of the run. SC solicitation workflows are intentionally blocked.",
    )
    return parser


def handle_list_sources(state: str | None) -> int:
    for source in get_sources(state):
        print(
            f"{source.state.upper():<3} | {source.county:<18} | {source.system:<24} | "
            f"supported={str(source.supported).lower():<5} | solicitation_ok={str(source.solicitation_ok).lower():<5}"
        )
        print(f"      last_verified={source.last_verified} portal={source.portal_url}")
        print(f"      notes={source.notes}")
    return 0


def handle_run(args: argparse.Namespace) -> int:
    counties = list(args.county)
    if args.state == "ga" and args.all_convenient:
        for county in GEORGIA_CONVENIENT_COUNTIES:
            if county not in counties:
                counties.append(county)

    if not counties:
        raise ProbateBotError("Choose at least one county with --county or use --all-convenient.")

    if args.state == "sc":
        raise ComplianceError(
            "South Carolina automation is intentionally disabled in this starter. "
            "Official county probate pages warn that public-record personal information may not be used for commercial solicitation."
        )

    unsupported = []
    for county in counties:
        source = find_source(args.state, county)
        if source is None:
            unsupported.append(f"{county} (not in source registry)")
        elif not source.supported:
            unsupported.append(f"{county} ({source.system})")
        elif args.use_case == "solicitation" and not source.solicitation_ok:
            unsupported.append(f"{county} (solicitation blocked)")

    if unsupported:
        joined = ", ".join(unsupported)
        raise ProbateBotError(f"These counties are not runnable with the current adapter set: {joined}")

    counties_by_system: dict[str, list[str]] = {}
    for county in counties:
        source = find_source(args.state, county)
        if source is None:
            continue
        counties_by_system.setdefault(source.system, []).append(county)

    leads = []
    for system, system_counties in counties_by_system.items():
        request = SearchRequest(
            state=args.state,
            counties=system_counties,
            start_date=args.start_date,
            end_date=args.end_date,
            date_field=args.date_field,
            headless=not args.headed,
            max_results_per_county=args.max_results_per_county,
            use_case=args.use_case,
        )
        scraper = _build_scraper(system)
        leads.extend(scraper.run(request))

    if args.format == "csv":
        output_path = write_csv(leads, args.out)
    else:
        output_path = write_json(leads, args.out)

    print(f"Wrote {len(leads)} leads to {output_path}")
    return 0


def _build_scraper(system: str):
    if system == "georgiaprobaterecords":
        return GeorgiaProbateRecordsScraper()
    if system == "cobb-benchmark":
        return CobbBenchmarkScraper()
    raise ProbateBotError(f"No scraper is registered for source system '{system}'.")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "list-sources":
            return handle_list_sources(args.state)
        if args.command == "run":
            return handle_run(args)
        raise ProbateBotError(f"Unknown command: {args.command}")
    except (ComplianceError, ProbateBotError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
