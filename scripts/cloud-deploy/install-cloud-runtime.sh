#!/usr/bin/env bash
set -euo pipefail

app_root="${APP_ROOT:-/opt/ielts-vocab/current}"
venv_dir="${VENV_DIR:-/opt/ielts-vocab/venv}"
web_root="${WEB_ROOT:-/var/www/ielts-vocab}"
env_dir="${ENV_DIR:-/etc/ielts-vocab}"

dnf install -y git nginx postgresql-server postgresql-contrib python3 python3-pip \
  python3-devel gcc gcc-c++ make openssl-devel libffi-devel tar curl cronie

if ! command -v node >/dev/null 2>&1 || [[ "$(node -p 'Number(process.versions.node.split(`.`)[0])' 2>/dev/null || echo 0)" -lt 20 ]]; then
  curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
  dnf install -y nodejs
fi

if [[ ! -d /var/lib/pgsql/data/base ]]; then
  postgresql-setup --initdb
fi

systemctl enable --now postgresql nginx crond

mkdir -p "${env_dir}" "${web_root}" /var/backups/ielts-vocab/postgres
chmod 700 "${env_dir}" /var/backups/ielts-vocab

python3 -m venv "${venv_dir}"
"${venv_dir}/bin/pip" install --upgrade pip wheel
"${venv_dir}/bin/pip" install -r "${app_root}/backend/requirements.txt" -r "${app_root}/services/requirements.txt"
"${venv_dir}/bin/pip" install -e "${app_root}/packages/platform-sdk"

corepack enable
corepack prepare pnpm@9.0.0 --activate
pnpm --dir "${app_root}" install --frozen-lockfile
pnpm --dir "${app_root}" build
rm -rf "${web_root:?}/"*
cp -a "${app_root}/dist/." "${web_root}/"

chmod +x "${app_root}/scripts/cloud-deploy/"*.sh
cp "${app_root}/scripts/cloud-deploy/ielts-service@.service" /etc/systemd/system/
cp "${app_root}/scripts/cloud-deploy/ielts-vocab.nginx.conf" /etc/nginx/conf.d/ielts-vocab.conf

systemctl daemon-reload
nginx -t

cat >/etc/cron.d/ielts-vocab-postgres-backup <<'CRON'
17 3 * * * root /opt/ielts-vocab/current/scripts/cloud-deploy/backup-postgres.sh >/var/log/ielts-vocab-postgres-backup.log 2>&1
CRON

echo "Runtime installed. Ensure ${env_dir}/backend.env and ${env_dir}/microservices.env exist before starting services."
