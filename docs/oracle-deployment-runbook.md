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

`VM.Standard.E2.1.Micro` is not the recommended fallback for this repository. The code is architecture-portable across `arm64` and `x86-64`, but the runtime profile is not small enough to rely on a `1 GB`, `1/8` OCPU instance for Playwright-based scraping.

## Capacity Errors

OCI documents the `out of host capacity` / `out of capacity` error as a temporary capacity shortage for Always Free shapes in the home region. This is an OCI supply issue, not a project bug.

Observed during setup for this project:

- `VM.Standard.A1.Flex` was tried in `AD-1`, `AD-2`, and `AD-3`
- all three availability domains returned the same capacity error
- retries the next day still returned the same error

That behavior is the reason this repository now includes an automated polling provisioner instead of assuming a quick manual retry will succeed.

For this repo:

1. Retry `VM.Standard.A1.Flex` across every availability domain in the home region.
2. Do not pin a fault domain.
3. Poll until A1 capacity becomes available.
4. Do not fall back to `VM.Standard.E2.1.Micro` for the full scraper + web workload.

The provisioning helper for this behavior is:

- `deploy/oracle/provision-oci-free-tier.sh`

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

If the console launch fails with an A1 capacity error, use the CLI polling helper instead of repeatedly retrying one AD manually.

## CLI Provisioning

From a machine with the OCI CLI already configured:

```bash
export COMPARTMENT_ID=ocid1.compartment.oc1...
export SUBNET_ID=ocid1.subnet.oc1...
export IMAGE_ID=ocid1.image.oc1...
export SSH_PUBLIC_KEY_FILE=$HOME/.ssh/id_ed25519.pub
export DISPLAY_NAME=probate-bot
deploy/oracle/provision-oci-free-tier.sh
```

Notes:

- The script lists all availability domains dynamically.
- The script never sets a fault domain, so OCI auto-selects one.
- The script keeps polling every 10 minutes until `VM.Standard.A1.Flex` capacity is available.
- `IMAGE_ID` should be an Ubuntu image that is compatible with `VM.Standard.A1.Flex`.

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
