# Oracle Deployment Runbook

This runbook is the practical deployment path for the Oracle Free Tier proof of concept.

## Target Shape

Use one public Ubuntu instance on OCI Ampere A1.

Current Oracle docs confirm:

- OCI compute instances can be launched with Ubuntu platform images.
- Public IP assignment is available at launch time for instances in a public subnet.
- Oracle Always Free A1 capacity is subject to availability and idle reclaim rules.

References:

- https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/launchinginstance.htm
- https://docs.oracle.com/iaas/Content/Network/Tasks/assign-public-ip-instance-launch.htm
- https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm

## Network Rules

Open only the ports you need:

- TCP 22 from your own public IP for SSH
- TCP 80 from `0.0.0.0/0` for the dashboard

Oracle networking references:

- https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/securityrules.htm
- https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/networksecuritygroups.htm

## Recommended GA County Starter Set

For the Oracle proof of concept, start with four counties to keep runtime and browser churn lower:

- Hall
- Henry
- Douglas
- Cobb

That is the default in `deploy/oracle/systemd/probate-bot.env`.

If you want broader coverage later, switch to:

```ini
PROBATE_BOT_SYNC_MODE=all-convenient
PROBATE_BOT_SYNC_COUNTIES=
```

## Oracle Console Steps

1. In OCI, create a VCN with internet connectivity if you do not already have one.
2. Launch one Ubuntu VM in a public subnet.
3. Assign a public IPv4 address at launch.
4. Add ingress rules for TCP `22` and TCP `80`.
5. SSH to the instance as `ubuntu`.

## Remote Deployment

From this repository on your local machine:

```bash
deploy/oracle/deploy-remote.sh ubuntu@YOUR_PUBLIC_IP /opt/probate-bot
```

That command:

- copies the repo to the instance with `rsync`
- creates the virtualenv
- installs Python dependencies
- installs Playwright Chromium with system deps
- installs `nginx`
- installs the `systemd` services and timers
- starts the web UI and daily timers

## Post-Deploy Checks

SSH to the box and run:

```bash
sudo systemctl status probate-bot-web.service --no-pager
sudo systemctl status probate-bot-sync.timer --no-pager
sudo systemctl status probate-bot-backup.timer --no-pager
curl -I http://127.0.0.1:8000/
curl -I http://127.0.0.1/
```

Then trigger an immediate scrape:

```bash
sudo systemctl start probate-bot-sync.service
tail -n 200 /opt/probate-bot/logs/daily-sync.log
```

## Change The Daily Counties

Edit:

```bash
sudo nano /etc/default/probate-bot
```

Starter explicit-county configuration:

```ini
PROBATE_BOT_SYNC_MODE=explicit
PROBATE_BOT_SYNC_COUNTIES=Hall,Henry,Douglas,Cobb
PROBATE_BOT_SYNC_DAYS_BACK=1
PROBATE_BOT_SYNC_MAX_RESULTS=100
```

After changes:

```bash
sudo systemctl daemon-reload
sudo systemctl restart probate-bot-web.service
sudo systemctl start probate-bot-sync.service
```

## Export And Backup

Manual export:

```bash
/opt/probate-bot/.venv/bin/probate-bot export-db \
  --db /opt/probate-bot/data/probate.sqlite \
  --out /opt/probate-bot/exports/probate-leads.csv \
  --format csv
```

Manual backup:

```bash
/opt/probate-bot/.venv/bin/probate-bot backup-db \
  --db /opt/probate-bot/data/probate.sqlite \
  --backup-dir /opt/probate-bot/backups \
  --keep 14
```

## Operational Limits

This is still a proof of concept:

- one VM
- one local SQLite file
- one browser runtime
- no managed failover

Use it to prove the workflow, not to make uptime guarantees.
