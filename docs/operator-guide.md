# Operator Guide

## Intended Workflow

1. Start with a Georgia county that is already supported.
2. Pull a small sample using a narrow date range.
3. Review the CSV manually before treating any row as a marketing lead.
4. Validate title, heirs, occupancy, and property status outside the scraper.

## Recommended First Commands

Create a virtual environment and install the package:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
PLAYWRIGHT_BROWSERS_PATH=.playwright playwright install chromium
```

List current source coverage:

```bash
probate-bot list-sources
```

Run a Hall County sample:

```bash
PLAYWRIGHT_BROWSERS_PATH=.playwright probate-bot run \
  --state ga \
  --county Hall \
  --start-date 2026-01-01 \
  --end-date 2026-04-24 \
  --max-results-per-county 25 \
  --out ./tmp/hall.csv
```

Run a Cobb docket-linked sample:

```bash
PLAYWRIGHT_BROWSERS_PATH=.playwright probate-bot run \
  --state ga \
  --county Cobb \
  --start-date 2026-04-24 \
  --end-date 2026-04-24 \
  --max-results-per-county 20 \
  --out ./tmp/cobb.csv
```

## What the Score Means

The lead score is just a prioritization heuristic.

- Higher scores usually mean an open estate plus a visible street address and useful filing clues.
- Lower scores are still worth reviewing when the county is strategically important.
- No score in this project means a lead is legally marketable, title-clean, vacant, or discounted.

## Current Limitations

- The Georgia portal results grid currently needs a richer newest-first and pagination pass.
- Georgia results are now paginated and sorted newest-first, but portal filtering behavior can still vary by county/system data quality.
- Cobb extraction currently depends on docket events and linked cases for the selected dates.
- South Carolina automation is intentionally not enabled for solicitation workflows in this starter.
