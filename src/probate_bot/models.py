from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


class ProbateBotError(Exception):
    """Base application error."""


class ComplianceError(ProbateBotError):
    """Raised when a workflow is blocked for compliance reasons."""


@dataclass(slots=True)
class CountySource:
    state: str
    county: str
    system: str
    portal_url: str
    official_reference_url: str
    last_verified: str
    convenience: str
    supported: bool = True
    solicitation_ok: bool = True
    notes: str = ""


@dataclass(slots=True)
class SearchRequest:
    state: str
    counties: list[str]
    start_date: str | None = None
    end_date: str | None = None
    date_field: str = "filed"
    headless: bool = True
    max_results_per_county: int = 100
    use_case: str = "research"


@dataclass(slots=True)
class ProbateLead:
    state: str
    county: str
    source_system: str
    source_url: str
    case_number: str = ""
    case_name: str = ""
    decedent_name: str = ""
    status: str = ""
    filing_date: str = ""
    date_of_death: str = ""
    property_address: str = ""
    petitioner_names: list[str] = field(default_factory=list)
    filings: list[str] = field(default_factory=list)
    lead_score: int = 0
    lead_reasons: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
