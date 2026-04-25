from __future__ import annotations

from probate_bot.models import CountySource


GEORGIA_CONVENIENT_COUNTIES = [
    "Hall",
    "Henry",
    "Douglas",
    "Fayette",
    "Forsyth",
    "Chatham",
    "Cobb",
]


COUNTY_SOURCES: list[CountySource] = [
    CountySource(
        state="ga",
        county="Hall",
        system="georgiaprobaterecords",
        portal_url="https://www.georgiaprobaterecords.com/Estates/SearchEstates.aspx",
        official_reference_url="https://www.hallcounty.org/484/Probate-Court",
        last_verified="2026-04-23",
        convenience="high",
        notes="Hall County says most estate cases filed after 2010 are available on georgiaprobaterecords.com.",
    ),
    CountySource(
        state="ga",
        county="Henry",
        system="georgiaprobaterecords",
        portal_url="https://www.georgiaprobaterecords.com/Estates/SearchEstates.aspx",
        official_reference_url="https://www.georgiaprobaterecords.com/Courts/CourtInformation.aspx",
        last_verified="2026-04-23",
        convenience="high",
        notes="Henry County appears in the participating courts list on Georgia Probate Records.",
    ),
    CountySource(
        state="ga",
        county="Douglas",
        system="georgiaprobaterecords",
        portal_url="https://www.georgiaprobaterecords.com/Estates/SearchEstates.aspx",
        official_reference_url="https://www.georgiaprobaterecords.com/Courts/CourtInformation.aspx",
        last_verified="2026-04-23",
        convenience="high",
        notes="Douglas County appears in the participating courts list on Georgia Probate Records.",
    ),
    CountySource(
        state="ga",
        county="Fayette",
        system="georgiaprobaterecords",
        portal_url="https://www.georgiaprobaterecords.com/Estates/SearchEstates.aspx",
        official_reference_url="https://www.georgiaprobaterecords.com/Courts/CourtInformation.aspx",
        last_verified="2026-04-23",
        convenience="high",
        notes="Fayette County appears in the participating courts list on Georgia Probate Records.",
    ),
    CountySource(
        state="ga",
        county="Forsyth",
        system="georgiaprobaterecords",
        portal_url="https://www.georgiaprobaterecords.com/Estates/SearchEstates.aspx",
        official_reference_url="https://www.georgiaprobaterecords.com/Courts/CourtInformation.aspx",
        last_verified="2026-04-23",
        convenience="high",
        notes="Forsyth County appears in the participating courts list on Georgia Probate Records.",
    ),
    CountySource(
        state="ga",
        county="Chatham",
        system="georgiaprobaterecords",
        portal_url="https://www.georgiaprobaterecords.com/Estates/SearchEstates.aspx",
        official_reference_url="https://www.georgiaprobaterecords.com/Courts/CourtInformation.aspx",
        last_verified="2026-04-23",
        convenience="high",
        notes="Chatham County appears in the participating courts list on Georgia Probate Records.",
    ),
    CountySource(
        state="ga",
        county="Athens-Clarke",
        system="athens-clarke-probate",
        portal_url="https://athensclarkeprobatecourt.com/",
        official_reference_url="https://athensclarkecounty.org/probatecourt",
        last_verified="2026-04-23",
        convenience="high",
        supported=False,
        notes="Official county page links to public case search and says decedent estate records dating back to 2005 are online.",
    ),
    CountySource(
        state="ga",
        county="Cobb",
        system="cobb-benchmark",
        portal_url="https://probateonline.cobbcounty.gov/BenchmarkWeb/Home.aspx/Search",
        official_reference_url="https://www.cobbcounty.gov/probate-court/case-status-records-search",
        last_verified="2026-04-23",
        convenience="high",
        supported=True,
        notes=(
            "Official county page says no login is required. Adapter uses the public Court Docket -> List Cases path "
            "to reach case detail pages without captcha-protected case search."
        ),
    ),
    CountySource(
        state="sc",
        county="Dorchester Probate",
        system="southcarolinaprobate",
        portal_url="https://www.southcarolinaprobate.net/search/",
        official_reference_url="https://www.dorchestercountysc.gov/government/courts-judicial-services/probate-court/public-records-requests",
        last_verified="2026-04-23",
        convenience="high",
        supported=False,
        solicitation_ok=False,
        notes="Official county page points to southcarolinaprobate.net/search and SC probate workflows may be restricted for solicitation use.",
    ),
    CountySource(
        state="sc",
        county="Richland",
        system="richland-estate-inquiry",
        portal_url="https://www7.richlandcountysc.gov/EstateInquiry/main.aspx",
        official_reference_url="https://www.richlandcountysc.gov/Courts-Safety/Probate-Court/Estates",
        last_verified="2026-04-23",
        convenience="high",
        supported=False,
        solicitation_ok=False,
        notes="Official county estate page links to Estate Inquiry. Review SC solicitation restrictions before use.",
    ),
    CountySource(
        state="sc",
        county="Lexington",
        system="lexington-probate-search",
        portal_url="https://lex-co.sc.gov/departments/probate-court/disclaimer-estate/acknowledgement-disclaimer",
        official_reference_url="https://lex-co.sc.gov/departments/probate-court",
        last_verified="2026-04-23",
        convenience="high",
        supported=False,
        solicitation_ok=False,
        notes="Lexington County probate disclaimer warns that use of public records for commercial solicitation is prohibited.",
    ),
]


def get_sources(state: str | None = None) -> list[CountySource]:
    if state is None:
        return list(COUNTY_SOURCES)
    return [source for source in COUNTY_SOURCES if source.state == state.lower()]


def find_source(state: str, county: str) -> CountySource | None:
    state = state.lower()
    county = county.strip().lower()
    for source in COUNTY_SOURCES:
        if source.state == state and source.county.lower() == county:
            return source
    return None
