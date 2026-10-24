# Collection server on Oracle Cloud (Always Free)

Goal of Phase 3: prices are collected every day by a server, not the laptop. This page is the
first-time setup; releases later follow the deploy skill (`.claude/skills/deploy/SKILL.md`).

What runs there now: Postgres (`db`, not reachable from the internet) and a daily collection job per
brand (systemd timer -> `docker compose run app ...`), plus a nightly database dump. Nothing is exposed
except SSH. API and web join in later phases.

## 1. Account (owner, once)

Sign up at <https://signup.cloud.oracle.com/>. Home region **Germany Central (Frankfurt)**; it cannot
be changed later. The card is for identity verification; Always Free resources are never charged.
Do not upgrade to Pay As You Go without deciding that on purpose (it is what makes charges possible).

## 2. Create the server (owner, in the console, ~5 min)

Menu -> Compute -> Instances -> **Create instance**:

| Setting | Value |
|---|---|
| Name | `realdrop` |
| Image | **Canonical Ubuntu 24.04** (the aarch64 build is picked automatically for Ampere) |
| Shape | Change shape -> Ampere -> **VM.Standard.A1.Flex**, 4 OCPU, 24 GB (free limit) |
| Networking | Create new VCN + public subnet, **Assign a public IPv4 address: yes** |
| SSH keys | **Paste public key**: the contents of `~/.ssh/id_ed25519.pub` on the Mac |
| Boot volume | 100 GB (free total is 200 GB) |

"Out of capacity" for A1 is common: retry later, try another availability domain, or use 2 OCPU /
12 GB. Do not pick a paid shape.

Copy the **public IP** from the instance page when it shows "Running".

## 3. Set it up (from the Mac, ~10 min)

```bash
ssh ubuntu@<public-ip>
curl -fsSL https://raw.githubusercontent.com/AhmedElghazzawy/realdrop/main/infra/prod/setup.sh | bash
sudo systemctl start realdrop-collect@defacto.service    # first run now, don't wait for 03:00
journalctl -fu realdrop-collect@defacto.service           # Ctrl-C to stop watching
```

`setup.sh` is idempotent. It generates the database password into `/opt/realdrop/infra/prod/.env`
(readable only by the `ubuntu` user, never committed).

## Everyday commands (on the server)

```bash
cd /opt/realdrop
systemctl list-timers 'realdrop-*'                                   # when the next runs are
journalctl -u realdrop-collect@defacto.service --since today         # last run's output
sudo docker compose -f infra/prod/compose.yml exec db psql -U app -d realdrop \
  -c "select status, items_seen, items_failed, started_at from collection_runs order by started_at desc limit 5"
git pull && sudo docker compose -f infra/prod/compose.yml build app \
  && sudo docker compose -f infra/prod/compose.yml run --rm app alembic upgrade head   # update
```

## Known risks

- **Idle reclaim:** Oracle may reclaim Always Free instances that stay nearly idle for 7 days (low
  CPU, network and memory use). Daily collection plus the database usually avoids that, but check the
  console email notices. Upgrading the account removes the rule but makes charges possible; owner's call.
- **Backups** are on the same disk for now (`/var/backups/realdrop`, 14 days). Off-server copies and a
  tested restore are a Phase 12 item.
