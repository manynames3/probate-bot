from __future__ import annotations

import re
from datetime import date

from probate_bot.models import ProbateLead


ADDRESS_PATTERN = re.compile(
    r"\b\d{1,6}\s+[A-Z0-9][A-Z0-9\s.'-]{2,}\b(?:RD|ROAD|ST|STREET|DR|DRIVE|AVE|AVENUE|LN|LANE|CT|COURT|HWY|HIGHWAY|BLVD|CIR|PKWY)\b",
    re.IGNORECASE,
)


REAL_ESTATE_TERMS = (
    "administration",
    "letters testamentary",
    "probate will",
    "real property",
    "petition",
    "inventory",
    "executor",
)


def looks_like_street_address(value: str) -> bool:
    return bool(value and ADDRESS_PATTERN.search(value))


def score_lead(lead: ProbateLead, today: date | None = None) -> ProbateLead:
    today = today or date.today()
    score = 0
    reasons: list[str] = []

    if lead.status.strip().upper() == "OPEN":
        score += 25
        reasons.append("open estate")

    if looks_like_street_address(lead.property_address):
        score += 35
        reasons.append("street address visible")

    filing_blob = " ".join(lead.filings).lower()
    for term in REAL_ESTATE_TERMS:
        if term in filing_blob:
            score += 8
            reasons.append(f"filing mentions {term}")
            break

    if lead.filing_date:
        score += 10
        reasons.append("filing date present")

    if lead.date_of_death:
        score += 10
        reasons.append("date of death present")

    if lead.petitioner_names:
        score += 10
        reasons.append("petitioner identified")

    lead.lead_score = min(score, 100)
    lead.lead_reasons = reasons
    return lead
