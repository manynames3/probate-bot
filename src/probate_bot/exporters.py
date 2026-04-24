from __future__ import annotations

import csv
import json
from pathlib import Path

from probate_bot.models import ProbateLead


def _normalize_row(lead: ProbateLead) -> dict[str, str | int]:
    return {
        "state": lead.state,
        "county": lead.county,
        "source_system": lead.source_system,
        "source_url": lead.source_url,
        "case_number": lead.case_number,
        "case_name": lead.case_name,
        "decedent_name": lead.decedent_name,
        "status": lead.status,
        "filing_date": lead.filing_date,
        "date_of_death": lead.date_of_death,
        "property_address": lead.property_address,
        "petitioner_names": " | ".join(lead.petitioner_names),
        "filings": " | ".join(lead.filings),
        "lead_score": lead.lead_score,
        "lead_reasons": " | ".join(lead.lead_reasons),
    }


def write_csv(leads: list[ProbateLead], output_path: str) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    rows = [_normalize_row(lead) for lead in leads]
    fieldnames = list(rows[0].keys()) if rows else [
        "state",
        "county",
        "source_system",
        "source_url",
        "case_number",
        "case_name",
        "decedent_name",
        "status",
        "filing_date",
        "date_of_death",
        "property_address",
        "petitioner_names",
        "filings",
        "lead_score",
        "lead_reasons",
    ]

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_json(leads: list[ProbateLead], output_path: str) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump([lead.to_dict() for lead in leads], handle, indent=2)
    return path
