# Probate Bot

`probate-bot` is a small Python CLI for pulling public probate estate leads from county portals that are workable for automation today.

This MVP is intentionally opinionated:

- Georgia is the primary supported state because a large set of counties participates in the public `georgiaprobaterecords.com` probate portal.
- Cobb County is noted as convenient and public, but its direct Benchmark portal is not wired up yet.
- South Carolina is intentionally blocked for lead-generation use because county probate pages warn that using personal information from covered public records for commercial solicitation is prohibited under the South Carolina Family Privacy Protection Act.

## What It Does

- Automates Georgia estate searches with Playwright
- Scores likely real-estate probate leads
- Exports CSV or JSON
- Lists source coverage and compliance notes before you run anything

## Documentation

- Source and compliance notes: [docs/source-registry.md](./docs/source-registry.md)
- Operator workflow: [docs/operator-guide.md](./docs/operator-guide.md)

## Current Source Notes

Verified on April 23, 2026 from official county or public portal pages:

- Hall County, GA says most estate cases filed after 2010 are available through `https://www.georgiaprobaterecords.com`.
- Athens-Clarke County, GA links to its public probate case search and says estate records dating back to 2005 are available online.
- Cobb County, GA says no login is required to view its public probate records portal at `https://probateonline.cobbcounty.gov/BenchmarkWeb/Home.aspx/Search`.
- Dorchester County, SC says estates can be searched at `https://www.southcarolinaprobate.net/search/`.
- Richland County, SC links to its estate inquiry site.
- Lexington County, SC posts a warning that use of public-record personal information for commercial solicitation is prohibited.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
playwright install chromium
```

## Usage

List supported sources:

```bash
probate-bot list-sources
```

Run the Georgia multi-county scraper:

```bash
probate-bot run \
  --state ga \
  --county Hall \
  --county Henry \
  --start-date 2026-01-01 \
  --end-date 2026-04-23 \
  --out ./ga_probate_leads.csv
```

Use the built-in convenient Georgia defaults:

```bash
probate-bot run \
  --state ga \
  --all-convenient \
  --start-date 2026-01-01 \
  --end-date 2026-04-23 \
  --out ./ga_probate_leads.json \
  --format json
```

## Lead Heuristics

The scorer boosts records when it sees:

- an open estate
- a probable street address
- petitions for letters of administration or probate of will
- recent filing activity

Those are heuristics, not legal conclusions. You should still review raw filings before mailing, calling, or underwriting.

`--start-date` and `--end-date` target the portal's filed-date fields by default. Use `--date-field deceased` if you want to search by date of death instead.

## South Carolina Guardrail

This codebase does not automate South Carolina probate lead extraction for solicitation workflows.

The reason is not technical. It is compliance:

- Lexington County's probate disclaimer says use of public records for commercial solicitation is prohibited.
- South Carolina public bodies routinely cite S.C. Code Section 30-2-50.

If your lawyer later approves a narrow SC workflow for a non-solicitation purpose, you can add a dedicated adapter, but this starter does not cross that line by default.
