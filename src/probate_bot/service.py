from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from probate_bot.config import GEORGIA_CONVENIENT_COUNTIES, find_source
from probate_bot.models import ComplianceError, ProbateBotError, SearchRequest
from probate_bot.scrapers.cobb_benchmark import CobbBenchmarkScraper
from probate_bot.scrapers.georgia_probate_records import GeorgiaProbateRecordsScraper
from probate_bot.storage import create_sync_run, ensure_database, finish_sync_run, upsert_leads


@dataclass(slots=True)
class SyncResult:
    leads_found: int
    inserted: int
    updated: int
    db_path: str
    run_id: int


def collect_leads_from_options(
    *,
    state: str,
    counties: list[str],
    all_convenient: bool,
    start_date: str | None,
    end_date: str | None,
    days_back: int | None,
    date_field: str,
    headless: bool,
    max_results_per_county: int,
    use_case: str,
) -> tuple[list, list[str], str, str]:
    start_date, end_date = resolve_relative_dates(start_date, end_date, days_back)
    counties = resolve_counties(state, counties, all_convenient)
    validate_request(state, counties, use_case)
    leads = collect_leads(
        state=state,
        counties=counties,
        start_date=start_date,
        end_date=end_date,
        date_field=date_field,
        headless=headless,
        max_results_per_county=max_results_per_county,
        use_case=use_case,
    )
    return leads, counties, start_date, end_date


def collect_leads(
    *,
    state: str,
    counties: list[str],
    start_date: str | None,
    end_date: str | None,
    date_field: str,
    headless: bool,
    max_results_per_county: int,
    use_case: str,
) -> list:
    counties_by_system: dict[str, list[str]] = {}
    for county in counties:
        source = find_source(state, county)
        if source is None:
            continue
        counties_by_system.setdefault(source.system, []).append(county)

    leads = []
    for system, system_counties in counties_by_system.items():
        request = SearchRequest(
            state=state,
            counties=system_counties,
            start_date=start_date,
            end_date=end_date,
            date_field=date_field,
            headless=headless,
            max_results_per_county=max_results_per_county,
            use_case=use_case,
        )
        scraper = build_scraper(system)
        leads.extend(scraper.run(request))
    return leads


def sync_leads_from_options(
    *,
    db_path: str,
    trigger_source: str,
    state: str,
    counties: list[str],
    all_convenient: bool,
    start_date: str | None,
    end_date: str | None,
    days_back: int | None,
    date_field: str,
    headless: bool,
    max_results_per_county: int,
    use_case: str,
) -> SyncResult:
    ensure_database(db_path)
    resolved_start, resolved_end = resolve_relative_dates(start_date, end_date, days_back)
    resolved_counties = resolve_counties(state, counties, all_convenient)
    validate_request(state, resolved_counties, use_case)

    run_id = create_sync_run(
        db_path,
        trigger_source=trigger_source,
        state=state,
        counties=resolved_counties,
        start_date=resolved_start,
        end_date=resolved_end,
    )
    try:
        leads = collect_leads(
            state=state,
            counties=resolved_counties,
            start_date=resolved_start,
            end_date=resolved_end,
            date_field=date_field,
            headless=headless,
            max_results_per_county=max_results_per_county,
            use_case=use_case,
        )
        stats = upsert_leads(db_path, leads)
        finish_sync_run(
            db_path,
            run_id,
            status="success",
            lead_count=len(leads),
            inserted_count=stats.inserted,
            updated_count=stats.updated,
        )
        return SyncResult(
            leads_found=len(leads),
            inserted=stats.inserted,
            updated=stats.updated,
            db_path=db_path,
            run_id=run_id,
        )
    except Exception as exc:
        finish_sync_run(
            db_path,
            run_id,
            status="failed",
            lead_count=0,
            inserted_count=0,
            updated_count=0,
            notes=str(exc),
        )
        raise


def resolve_relative_dates(
    start_date: str | None,
    end_date: str | None,
    days_back: int | None,
) -> tuple[str | None, str | None]:
    if days_back is None:
        return start_date, end_date
    if days_back < 1:
        raise ProbateBotError("--days-back must be at least 1.")
    if start_date or end_date:
        raise ProbateBotError("Use either --days-back or explicit --start-date/--end-date, not both.")
    end = date.today()
    start = end - timedelta(days=days_back - 1)
    return start.isoformat(), end.isoformat()


def resolve_counties(state: str, counties: list[str], all_convenient: bool) -> list[str]:
    resolved = list(counties)
    if state == "ga" and all_convenient:
        for county in GEORGIA_CONVENIENT_COUNTIES:
            if county not in resolved:
                resolved.append(county)
    if not resolved:
        raise ProbateBotError("Choose at least one county with --county or use --all-convenient.")
    return resolved


def validate_request(state: str, counties: list[str], use_case: str) -> None:
    if state == "sc":
        raise ComplianceError(
            "South Carolina automation is intentionally disabled in this starter. "
            "Official county probate pages warn that public-record personal information may not be used for commercial solicitation."
        )

    unsupported = []
    for county in counties:
        source = find_source(state, county)
        if source is None:
            unsupported.append(f"{county} (not in source registry)")
        elif not source.supported:
            unsupported.append(f"{county} ({source.system})")
        elif use_case == "solicitation" and not source.solicitation_ok:
            unsupported.append(f"{county} (solicitation blocked)")

    if unsupported:
        joined = ", ".join(unsupported)
        raise ProbateBotError(f"These counties are not runnable with the current adapter set: {joined}")


def build_scraper(system: str):
    if system == "georgiaprobaterecords":
        return GeorgiaProbateRecordsScraper()
    if system == "cobb-benchmark":
        return CobbBenchmarkScraper()
    raise ProbateBotError(f"No scraper is registered for source system '{system}'.")
