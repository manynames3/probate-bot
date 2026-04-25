# Oracle Free Tier POC

## Goal

Use Oracle Cloud Free Tier as a low-cost proof-of-concept platform for:

- daily probate scraping
- deduped lead storage in SQLite
- simple operator review
- proving the workflow is valuable before paying for more reliable infrastructure

This is a POC architecture, not a production architecture.

## Recommended Oracle Shape

Use one Ubuntu-based OCI Ampere A1 instance.

Reason:

- Playwright is better suited to a normal Linux VM than a serverless runtime.
- The A1 shape gives materially more headroom than the smallest micro instance.
- One box keeps the system simple and cheap.

## POC System Layout

Run everything on one VM:

- application code
- Playwright browser runtime
- local SQLite database
- cron-based daily sync
- CSV and JSON exports

Suggested layout:

- `/opt/probate-bot` for application code
- `/opt/probate-bot/.venv` for Python environment
- `/opt/probate-bot/data/probate.sqlite` for the lead database
- `/opt/probate-bot/exports` for output files
- `/opt/probate-bot/logs` for sync logs
- `/opt/probate-bot/backups` for rolling database backups

## Daily Operating Model

The POC should do one thing reliably:

- run a scrape every day
- upsert results into SQLite
- avoid duplicate leads
- keep the instance looking active enough to reduce free-tier reclaim risk

Use the existing sync command:

```bash
probate-bot sync \
  --state ga \
  --all-convenient \
  --days-back 1 \
  --db /opt/probate-bot/data/probate.sqlite
```

Use cron to run it daily.

For the operator-facing UI, run:

```bash
probate-bot web \
  --db /opt/probate-bot/data/probate.sqlite \
  --host 127.0.0.1 \
  --port 8000
```

In this repository, the preferred Oracle setup uses included deployment assets instead of raw cron:

- `deploy/oracle/bootstrap.sh`
- `deploy/oracle/systemd/probate-bot-web.service`
- `deploy/oracle/systemd/probate-bot-sync.timer`
- `deploy/oracle/systemd/probate-bot-backup.timer`
- `deploy/oracle/nginx-probate-bot.conf`

## Required Safeguards

Even for a POC, these are mandatory:

### 1. Process supervision

Use `systemd` for any web or API process you add later.

### 2. Daily local backup

Back up the SQLite database every day before or after sync.

Minimum POC backup pattern:

- copy `probate.sqlite` to a dated file
- keep the last 7 to 14 copies

Use the built-in command:

```bash
probate-bot backup-db \
  --db /opt/probate-bot/data/probate.sqlite \
  --backup-dir /opt/probate-bot/backups \
  --keep 14
```

### 3. Off-box backup

Push the SQLite backup to object storage or another machine. Oracle Free Tier is not a safe place for the only copy of the data.

### 4. Log review

Write daily sync logs to disk and check for scrape failures.

### 5. Export path

The operator must be able to export the stored lead set without running a new scrape.

Use:

```bash
probate-bot export-db \
  --db /opt/probate-bot/data/probate.sqlite \
  --out /opt/probate-bot/exports/probate-leads.csv \
  --format csv
```

## What Success Looks Like

The POC is successful if, after 30 days, all of these are true:

1. The daily job ran on at least 25 of 30 days.
2. The SQLite database contains accumulated leads with no duplicate rows for the same case.
3. At least one county adapter produced useful lead data consistently.
4. You can query, review, and export the stored data without manual reconstruction.
5. The Oracle instance remained usable for the full test period.

## What Failure Looks Like

The POC should be considered failed or incomplete if any of these happen:

1. Oracle reclaims or suspends the instance before the workflow proves value.
2. Daily scraping succeeds only sporadically.
3. The data model cannot support cumulative lead review.
4. You find that operator usage requires a real UI much sooner than expected.

## Architectural Judgment

This POC makes sense because it optimizes for learning at minimal cost.

It does not make sense as a long-term production platform because:

- Oracle Free Tier can reclaim idle resources
- free-tier reliability is not guaranteed
- the entire system lives on one VM
- SQLite on one VM is operationally fragile without disciplined backups

## Upgrade Trigger

Upgrade off Oracle Free Tier when one of these becomes true:

1. The workflow is generating enough value that downtime is unacceptable.
2. You need multiple users.
3. You need a real frontend and API running full-time.
4. Daily jobs are large enough that one VM becomes a bottleneck.
5. You need stronger durability than local SQLite plus backups.
