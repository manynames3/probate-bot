from __future__ import annotations

import argparse
import sys

from probate_bot.config import get_sources
from probate_bot.exporters import write_csv, write_json
from probate_bot.models import ComplianceError, ProbateBotError
from probate_bot.service import collect_leads_from_options, sync_leads_from_options
from probate_bot.storage import backup_database, ensure_database, export_leads


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
    run.add_argument("--days-back", type=int)
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

    sync = subparsers.add_parser("sync", help="Run a scrape and upsert deduped results into SQLite.")
    sync.add_argument("--state", choices=["ga", "sc"], required=True)
    sync.add_argument("--county", action="append", default=[])
    sync.add_argument("--all-convenient", action="store_true")
    sync.add_argument("--start-date")
    sync.add_argument("--end-date")
    sync.add_argument("--days-back", type=int)
    sync.add_argument(
        "--date-field",
        choices=["filed", "deceased"],
        default="filed",
        help="Which portal date range to search. Defaults to filed date.",
    )
    sync.add_argument("--db", default="./data/probate.sqlite")
    sync.add_argument("--headed", action="store_true")
    sync.add_argument("--max-results-per-county", type=int, default=100)
    sync.add_argument(
        "--use-case",
        choices=["research", "solicitation"],
        default="research",
        help="Purpose of the run. SC solicitation workflows are intentionally blocked.",
    )

    backup = subparsers.add_parser("backup-db", help="Create a timestamped SQLite backup and prune old copies.")
    backup.add_argument("--db", default="./data/probate.sqlite")
    backup.add_argument("--backup-dir", default="./backups")
    backup.add_argument("--keep", type=int, default=14)

    export_db = subparsers.add_parser("export-db", help="Export stored leads from SQLite to CSV or JSON.")
    export_db.add_argument("--db", default="./data/probate.sqlite")
    export_db.add_argument("--out", required=True)
    export_db.add_argument("--format", choices=["csv", "json"], default="csv")

    web = subparsers.add_parser("web", help="Run the operator web UI.")
    web.add_argument("--db", default="./data/probate.sqlite")
    web.add_argument("--host", default="127.0.0.1")
    web.add_argument("--port", type=int, default=8000)
    web.add_argument("--debug", action="store_true")
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
    leads, _, _, _ = collect_leads_from_options(
        state=args.state,
        counties=args.county,
        all_convenient=args.all_convenient,
        start_date=args.start_date,
        end_date=args.end_date,
        days_back=args.days_back,
        date_field=args.date_field,
        headless=not args.headed,
        max_results_per_county=args.max_results_per_county,
        use_case=args.use_case,
    )

    if args.format == "csv":
        output_path = write_csv(leads, args.out)
    else:
        output_path = write_json(leads, args.out)

    print(f"Wrote {len(leads)} leads to {output_path}")
    return 0


def handle_sync(args: argparse.Namespace) -> int:
    db_path = ensure_database(args.db)
    result = sync_leads_from_options(
        db_path=str(db_path),
        trigger_source="cli",
        state=args.state,
        counties=args.county,
        all_convenient=args.all_convenient,
        start_date=args.start_date,
        end_date=args.end_date,
        days_back=args.days_back,
        date_field=args.date_field,
        headless=not args.headed,
        max_results_per_county=args.max_results_per_county,
        use_case=args.use_case,
    )
    print(
        f"Synced {result.leads_found} leads to {db_path} "
        f"(inserted={result.inserted}, updated={result.updated}, run_id={result.run_id})"
    )
    return 0


def handle_backup_db(args: argparse.Namespace) -> int:
    ensure_database(args.db)
    backup_path = backup_database(args.db, args.backup_dir, keep=args.keep)
    print(f"Created backup at {backup_path}")
    return 0


def handle_export_db(args: argparse.Namespace) -> int:
    leads = export_leads(args.db)
    if args.format == "csv":
        output_path = write_csv(leads, args.out)
    else:
        output_path = write_json(leads, args.out)
    print(f"Exported {len(leads)} stored leads to {output_path}")
    return 0


def handle_web(args: argparse.Namespace) -> int:
    ensure_database(args.db)
    from probate_bot.web import create_app

    app = create_app(db_path=args.db)
    app.run(host=args.host, port=args.port, debug=args.debug)
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "list-sources":
            return handle_list_sources(args.state)
        if args.command == "run":
            return handle_run(args)
        if args.command == "sync":
            return handle_sync(args)
        if args.command == "backup-db":
            return handle_backup_db(args)
        if args.command == "export-db":
            return handle_export_db(args)
        if args.command == "web":
            return handle_web(args)
        raise ProbateBotError(f"Unknown command: {args.command}")
    except (ComplianceError, ProbateBotError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
