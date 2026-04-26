# Probate Bot

`probate-bot` is a small Python CLI for pulling public probate estate leads from county portals that are workable for automation today.

This MVP is intentionally opinionated:

- Georgia is the primary supported state because a large set of counties participates in the public `georgiaprobaterecords.com` probate portal.
- Cobb County is supported through the public Benchmark Court Docket -> List Cases flow.
- South Carolina is intentionally blocked for lead-generation use because county probate pages warn that using personal information from covered public records for commercial solicitation is prohibited under the South Carolina Family Privacy Protection Act.

## What It Does

- Automates Georgia estate searches with Playwright
- Pulls Cobb probate case details through public docket-linked case pages
- Scores likely real-estate probate leads
- Exports CSV or JSON
- Lists source coverage and compliance notes before you run anything

## Documentation

- Source and compliance notes: [docs/source-registry.md](./docs/source-registry.md)
- Operator workflow: [docs/operator-guide.md](./docs/operator-guide.md)
- AWS deployment notes: [docs/aws-deployment.md](./docs/aws-deployment.md)
- Oracle POC deployment notes: [docs/oracle-poc.md](./docs/oracle-poc.md)
- Oracle deployment runbook: [docs/oracle-deployment-runbook.md](./docs/oracle-deployment-runbook.md)

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

Sync into SQLite with duplicate protection:

```bash
probate-bot sync \
  --state ga \
  --all-convenient \
  --days-back 1 \
  --db ./data/probate.sqlite
```

Back up the SQLite database:

```bash
probate-bot backup-db \
  --db ./data/probate.sqlite \
  --backup-dir ./backups \
  --keep 14
```

Export stored leads from SQLite:

```bash
probate-bot export-db \
  --db ./data/probate.sqlite \
  --out ./exports/probate-leads.csv \
  --format csv
```

Run the operator web UI:

```bash
probate-bot web \
  --db ./data/probate.sqlite \
  --host 127.0.0.1 \
  --port 8000
```

## Lead Heuristics

The scorer boosts records when it sees:

- an open estate
- a probable street address
- petitions for letters of administration or probate of will
- recent filing activity

Those are heuristics, not legal conclusions. You should still review raw filings before mailing, calling, or underwriting.

`--start-date` and `--end-date` target the portal's filed-date fields by default. Use `--date-field deceased` if you want to search by date of death instead.

For Georgia, results are sorted newest-first by case number and traversed across grid pages until `--max-results-per-county` is reached.

For Cobb, date range applies to court-docket event dates and then crawls linked case details from those events.

## Daily Sync And Deduping

The project can now run a daily sync into SQLite.

- `probate-bot sync` scrapes and writes results into a local SQLite database.
- Leads are deduped by state, county, source system, and case number.
- If a lead is seen again on a later run, the record is updated instead of inserted a second time.
- `probate-bot backup-db` creates rolling database backups.
- `probate-bot export-db` exports deduped stored leads without running a new scrape.
- `probate-bot web` provides a lightweight operator dashboard for sync, review, and export.

Example daily sync:

```bash
probate-bot sync \
  --state ga \
  --all-convenient \
  --days-back 1 \
  --db ./data/probate.sqlite
```

Example cron entry for a once-per-day run at 5:15 AM server time:

```cron
15 5 * * * cd /opt/probate-bot && /opt/probate-bot/.venv/bin/probate-bot sync --state ga --all-convenient --days-back 1 --db /opt/probate-bot/data/probate.sqlite >> /opt/probate-bot/logs/daily-sync.log 2>&1
```

## Oracle Free Tier POC

If the goal is a low-cost proof of concept, the recommended non-AWS target is one Oracle Cloud Free Tier Ubuntu VM running:

- the scraper code
- Playwright
- daily cron-based sync
- SQLite
- local exports and logs
- the operator web UI

That is a sensible POC because it is cheap and technically compatible with the browser-based workload.

It is not a production recommendation because Oracle Free Tier can reclaim idle instances and should not be trusted as the only durable home for the data.

The detailed deployment and success criteria are documented in [docs/oracle-poc.md](./docs/oracle-poc.md).

Deployment assets for Oracle are included in:

- `deploy/oracle/bootstrap.sh`
- `deploy/oracle/deploy-remote.sh`
- `deploy/oracle/run-sync.sh`
- `deploy/oracle/systemd/`
- `deploy/oracle/nginx-probate-bot.conf`

The practical deployment sequence is documented in [docs/oracle-deployment-runbook.md](./docs/oracle-deployment-runbook.md). The default Oracle starter sync set is `Hall`, `Henry`, `Douglas`, and `Cobb` to keep the proof of concept lighter than a full `--all-convenient` run.

### First Impressions Of OCI

First time spinning up anything on Oracle Cloud Infrastructure, the immediate takeaway is that the ARM pricing is difficult to ignore. The free tier is unusually generous, and on paid tiers the ARM instances can come in materially cheaper than comparable compute on AWS, Azure, or GCP. On raw compute-per-dollar, OCI is one of the strongest values available right now.

The tradeoffs are real. OCI has fewer regions and a less mature ecosystem than the big three, so the fit depends heavily on the workload. For a cost-sensitive proof of concept like this one, it is compelling. For teams that need broader service depth or very polished platform ergonomics, the tradeoff may be less attractive.

## Free Tier Provisioning Notes

This project is designed for `VM.Standard.A1.Flex` on OCI Free Tier, not because the code requires Arm specifically, but because the workload needs more runtime headroom than the micro x86 shape provides.

### Shape Evaluation

- `VM.Standard.A1.Flex` is the intended free-tier shape because it can allocate meaningful CPU and memory to one Ubuntu VM.
- `VM.Standard.E2.1.Micro` is **not** a good fallback for this repo as currently designed.

Why:

- Architecture compatibility is fine on both `arm64` and `x86-64`. The Python code is portable, there are no ARM-only Docker images, and Playwright supports Ubuntu on both `x86-64` and `arm64`.
- Memory is the blocker. This repo runs `nginx`, `gunicorn` + Flask, SQLite, and headless Playwright Chromium on the same machine. That is too tight for a `1 GB` VM once the browser is active.
- CPU is also a blocker. OCI documents `VM.Standard.E2.1.Micro` as `1/8th of an OCPU` with burst capacity, which is materially smaller than “1 full OCPU.” Browser automation and page parsing are not a good fit for that ceiling.
- Storage is not the main issue. The installed Python environment is modest, but Playwright browser binaries still consume hundreds of MB on disk. OCI's minimum `50 GB` boot volume is sufficient either way.

### Capacity Error

OCI documents the `Out of capacity` / `Out of host capacity` error as a temporary shortage of Always Free compute capacity in your home region. This is an OCI capacity limitation, not a project bug.

In this setup effort, `VM.Standard.A1.Flex` was attempted in all three availability domains:

- `AD-1`
- `AD-2`
- `AD-3`

All three returned the same `Out of capacity for shape VM.Standard.A1.Flex in availability domain ...` error. The same retries were attempted again the next day with the same result. That is what pushed this project toward automated retry logic instead of one-off manual retries in the console.

### Recommended Order

1. Stay on `VM.Standard.A1.Flex`.
2. Retry across every availability domain in your home region instead of retrying only `AD-1`.
3. Do not hardcode a fault domain. Let OCI select one automatically.
4. Use the provisioning helper in `deploy/oracle/provision-oci-free-tier.sh` to poll until A1 capacity is available.
5. Only proceed to app deployment after the A1 VM exists.

### Image Selection

The OCI provisioner no longer requires a manual `IMAGE_ID` by default.

- If `IMAGE_ID` is unset, `deploy/oracle/provision-oci-free-tier.sh` tries to auto-discover the latest available `Canonical Ubuntu 24.04` image for `VM.Standard.A1.Flex`.
- If OCI CLI image discovery in your tenancy does not return a usable result, you can still set `IMAGE_ID` explicitly.
- `SUBNET_ID` is still required. The provisioner does not create networking for you.

The Oracle deployment runbook is in [docs/oracle-deployment-runbook.md](./docs/oracle-deployment-runbook.md).

## AWS Deployment

This project can be deployed on AWS, but the lowest-cost sensible path is not Lambda.

### Why Lambda Was Considered

Lambda is an obvious first thought because this app looks like a batch-style job runner:

- a user submits a scrape
- the backend runs a job
- the job writes results
- the app returns a file or status

That usually maps well to event-driven serverless infrastructure.

### Why This Project Should Not Start on Lambda

This scraper is Playwright-driven browser automation, which changes the tradeoff:

- Playwright plus Chromium is more reliable in a normal container or VM than in Lambda packaging.
- Probate scrapes are not tiny request-response units; they can take minutes, retry, and wait on fragile county portals.
- The app needs durable job execution, status tracking, and file output, which fits a queue plus worker model better than one Lambda invocation doing everything.
- Browser automation is easier to debug and operate on a container host where runtime behavior is predictable.

Lambda can work, but it increases packaging and browser-runtime complexity without reducing total system complexity enough to be worth it for this project.

### Lowest-Cost AWS Recommendation

If cost is the primary constraint, start with a single Amazon Lightsail Linux instance and run:

- the web app
- the job queue
- the Playwright worker
- a small database such as SQLite or Postgres in-container

That keeps the browser runtime simple and avoids always-on managed-service overhead like an Application Load Balancer.

The practical starter architecture is:

- Amazon Lightsail instance for the app and worker
- Amazon S3 for CSV and JSON exports
- Amazon Route 53 for DNS

This is the lowest-cost option that preserves the core functionality of browser-based scraping, result review, and file export.

### Expected Monthly Cost

For a small deployment with one operator or a very small team:

- Lightsail instance: about $5 to $12 per month
- Route 53 hosted zone: about $0.50 per month
- S3 exports and storage: usually low single digits

Realistic total:

- about $8 to $20 per month for the cheapest workable AWS deployment

### When To Upgrade

Move off Lightsail only after there is real usage pressure such as:

- multiple users
- many concurrent scrape jobs
- need for stronger isolation between web and worker processes
- need for managed autoscaling

At that point, the next AWS architecture should be:

- frontend on S3 plus CloudFront
- API on App Runner
- workers on ECS Fargate
- SQS for queued jobs
- DynamoDB or RDS for persistent job metadata

## South Carolina Guardrail

This codebase does not automate South Carolina probate lead extraction for solicitation workflows.

The reason is not technical. It is compliance:

- Lexington County's probate disclaimer says use of public records for commercial solicitation is prohibited.
- South Carolina public bodies routinely cite S.C. Code Section 30-2-50.

If your lawyer later approves a narrow SC workflow for a non-solicitation purpose, you can add a dedicated adapter, but this starter does not cross that line by default.
