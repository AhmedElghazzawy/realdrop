#!/usr/bin/env bash
# First-time setup of the RealDrop collection server (Ubuntu 24.04 on Oracle Always Free ARM).
# Safe to re-run: every step checks before it changes anything.
#
#   curl -fsSL https://raw.githubusercontent.com/AhmedElghazzawy/realdrop/main/infra/prod/setup.sh | bash
#
# What it does: security updates, Docker, the repo in /opt/realdrop, a generated database password
# in infra/prod/.env (never committed), the database, migrations, and the daily timers.
set -euo pipefail

REPO=https://github.com/AhmedElghazzawy/realdrop.git
DIR=/opt/realdrop
BRANDS=(defacto)

echo "==> Packages: Docker, git, automatic security updates"
sudo apt-get update -q
sudo DEBIAN_FRONTEND=noninteractive apt-get install -yq docker.io docker-compose-v2 git unattended-upgrades
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"

echo "==> Code in $DIR"
if [ ! -d "$DIR/.git" ]; then
  sudo git clone "$REPO" "$DIR"
  sudo chown -R "$USER:$USER" "$DIR"
else
  git -C "$DIR" pull --ff-only
fi
cd "$DIR"

echo "==> Secrets in infra/prod/.env"
if [ ! -f infra/prod/.env ]; then
  umask 077
  cat > infra/prod/.env <<EOF
POSTGRES_PASSWORD=$(openssl rand -hex 24)
COLLECTOR_USER_AGENT=realdrop-bot/0.1 (+https://github.com/AhmedElghazzawy/realdrop)
EOF
fi

COMPOSE=(sudo docker compose -f infra/prod/compose.yml)

echo "==> Database, image, migrations"
"${COMPOSE[@]}" up -d db
"${COMPOSE[@]}" build app
"${COMPOSE[@]}" run --rm app alembic upgrade head

echo "==> Timers"
sudo cp infra/prod/systemd/* /etc/systemd/system/
sudo systemctl daemon-reload
for brand in "${BRANDS[@]}"; do
  sudo systemctl enable --now "realdrop-collect@${brand}.timer"
done
sudo systemctl enable --now realdrop-backup.timer
systemctl list-timers 'realdrop-*' --no-pager

echo
echo "Done. Next collection runs at the time shown above."
echo "Run one now:   sudo systemctl start realdrop-collect@defacto.service"
echo "Watch it:      journalctl -fu realdrop-collect@defacto.service"
