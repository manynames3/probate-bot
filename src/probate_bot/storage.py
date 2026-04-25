from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from shutil import copy2

from probate_bot.models import ProbateLead


@dataclass(slots=True)
class UpsertStats:
    inserted: int = 0
    updated: int = 0


@dataclass(slots=True)
class LeadSummary:
    total_leads: int
    open_leads: int
    counties: int
    last_seen_at: str


SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dedupe_key TEXT NOT NULL UNIQUE,
    state TEXT NOT NULL,
    county TEXT NOT NULL,
    source_system TEXT NOT NULL,
    source_url TEXT NOT NULL,
    case_number TEXT NOT NULL,
    case_name TEXT NOT NULL,
    decedent_name TEXT NOT NULL,
    status TEXT NOT NULL,
    filing_date TEXT NOT NULL,
    date_of_death TEXT NOT NULL,
    property_address TEXT NOT NULL,
    petitioner_names TEXT NOT NULL,
    filings TEXT NOT NULL,
    lead_score INTEGER NOT NULL,
    lead_reasons TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    run_count INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_leads_county ON leads(state, county);
CREATE INDEX IF NOT EXISTS idx_leads_last_seen ON leads(last_seen_at);

CREATE TABLE IF NOT EXISTS sync_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_source TEXT NOT NULL,
    state TEXT NOT NULL,
    counties_json TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    lead_count INTEGER NOT NULL DEFAULT 0,
    inserted_count INTEGER NOT NULL DEFAULT 0,
    updated_count INTEGER NOT NULL DEFAULT 0,
    notes TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_sync_runs_started_at ON sync_runs(started_at);
"""


def ensure_database(db_path: str) -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()
    return path


def upsert_leads(db_path: str, leads: list[ProbateLead]) -> UpsertStats:
    ensure_database(db_path)
    stats = UpsertStats()
    now = _utc_now()

    with sqlite3.connect(db_path) as conn:
        for lead in leads:
            dedupe_key = lead.dedupe_key()
            existing = conn.execute(
                "SELECT id FROM leads WHERE dedupe_key = ?",
                (dedupe_key,),
            ).fetchone()

            payload = (
                lead.state,
                lead.county,
                lead.source_system,
                lead.source_url,
                lead.case_number,
                lead.case_name,
                lead.decedent_name,
                lead.status,
                lead.filing_date,
                lead.date_of_death,
                lead.property_address,
                json.dumps(lead.petitioner_names),
                json.dumps(lead.filings),
                lead.lead_score,
                json.dumps(lead.lead_reasons),
                json.dumps(lead.raw),
                now,
            )

            if existing:
                conn.execute(
                    """
                    UPDATE leads
                    SET state = ?, county = ?, source_system = ?, source_url = ?, case_number = ?,
                        case_name = ?, decedent_name = ?, status = ?, filing_date = ?, date_of_death = ?,
                        property_address = ?, petitioner_names = ?, filings = ?, lead_score = ?,
                        lead_reasons = ?, raw_json = ?, last_seen_at = ?, run_count = run_count + 1
                    WHERE dedupe_key = ?
                    """,
                    payload + (dedupe_key,),
                )
                stats.updated += 1
            else:
                conn.execute(
                    """
                    INSERT INTO leads (
                        dedupe_key, state, county, source_system, source_url, case_number, case_name,
                        decedent_name, status, filing_date, date_of_death, property_address,
                        petitioner_names, filings, lead_score, lead_reasons, raw_json,
                        first_seen_at, last_seen_at, run_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (dedupe_key,) + payload + (now,),
                )
                stats.inserted += 1
        conn.commit()
    return stats


def create_sync_run(
    db_path: str,
    *,
    trigger_source: str,
    state: str,
    counties: list[str],
    start_date: str | None,
    end_date: str | None,
) -> int:
    ensure_database(db_path)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO sync_runs (
                trigger_source, state, counties_json, start_date, end_date, started_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trigger_source,
                state,
                json.dumps(counties),
                start_date or "",
                end_date or "",
                _utc_now(),
                "running",
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def finish_sync_run(
    db_path: str,
    run_id: int,
    *,
    status: str,
    lead_count: int,
    inserted_count: int,
    updated_count: int,
    notes: str = "",
) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            UPDATE sync_runs
            SET finished_at = ?, status = ?, lead_count = ?, inserted_count = ?,
                updated_count = ?, notes = ?
            WHERE id = ?
            """,
            (_utc_now(), status, lead_count, inserted_count, updated_count, notes, run_id),
        )
        conn.commit()


def get_summary(db_path: str) -> LeadSummary:
    ensure_database(db_path)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_leads,
                SUM(CASE WHEN UPPER(status) = 'OPEN' THEN 1 ELSE 0 END) AS open_leads,
                COUNT(DISTINCT county) AS counties,
                COALESCE(MAX(last_seen_at), '') AS last_seen_at
            FROM leads
            """
        ).fetchone()

    return LeadSummary(
        total_leads=int(row[0] or 0),
        open_leads=int(row[1] or 0),
        counties=int(row[2] or 0),
        last_seen_at=str(row[3] or ""),
    )


def list_recent_runs(db_path: str, limit: int = 10) -> list[dict]:
    ensure_database(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, trigger_source, state, counties_json, start_date, end_date,
                   started_at, finished_at, status, lead_count, inserted_count,
                   updated_count, notes
            FROM sync_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    results: list[dict] = []
    for row in rows:
        item = dict(row)
        item["counties"] = json.loads(item.pop("counties_json"))
        results.append(item)
    return results


def list_leads(
    db_path: str,
    *,
    limit: int = 100,
    county: str | None = None,
    min_score: int | None = None,
) -> list[dict]:
    ensure_database(db_path)
    conditions: list[str] = []
    params: list[object] = []

    if county:
        conditions.append("county = ?")
        params.append(county)
    if min_score is not None:
        conditions.append("lead_score >= ?")
        params.append(min_score)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"""
        SELECT state, county, source_system, source_url, case_number, case_name,
               decedent_name, status, filing_date, date_of_death, property_address,
               petitioner_names, filings, lead_score, lead_reasons, first_seen_at,
               last_seen_at, run_count
        FROM leads
        {where_clause}
        ORDER BY last_seen_at DESC, lead_score DESC, county ASC
        LIMIT ?
    """
    params.append(limit)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()

    results: list[dict] = []
    for row in rows:
        item = dict(row)
        item["petitioner_names"] = json.loads(item["petitioner_names"])
        item["filings"] = json.loads(item["filings"])
        item["lead_reasons"] = json.loads(item["lead_reasons"])
        results.append(item)
    return results


def export_leads(db_path: str) -> list[ProbateLead]:
    ensure_database(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT state, county, source_system, source_url, case_number, case_name,
                   decedent_name, status, filing_date, date_of_death, property_address,
                   petitioner_names, filings, lead_score, lead_reasons
            FROM leads
            ORDER BY last_seen_at DESC, lead_score DESC
            """
        ).fetchall()

    return [
        ProbateLead(
            state=row["state"],
            county=row["county"],
            source_system=row["source_system"],
            source_url=row["source_url"],
            case_number=row["case_number"],
            case_name=row["case_name"],
            decedent_name=row["decedent_name"],
            status=row["status"],
            filing_date=row["filing_date"],
            date_of_death=row["date_of_death"],
            property_address=row["property_address"],
            petitioner_names=json.loads(row["petitioner_names"]),
            filings=json.loads(row["filings"]),
            lead_score=int(row["lead_score"]),
            lead_reasons=json.loads(row["lead_reasons"]),
        )
        for row in rows
    ]


def backup_database(db_path: str, backup_dir: str, keep: int = 14) -> Path:
    ensure_database(db_path)
    backup_root = Path(backup_dir)
    backup_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = backup_root / f"probate-{timestamp}.sqlite"
    copy2(db_path, destination)

    if keep > 0:
        backups = sorted(backup_root.glob("probate-*.sqlite"))
        for old_file in backups[:-keep]:
            old_file.unlink(missing_ok=True)
    return destination


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
